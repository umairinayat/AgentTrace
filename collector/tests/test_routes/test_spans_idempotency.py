"""Tests for idempotent span ingestion.

SDK delivery is at-least-once: a batch whose response is lost gets re-sent.
Ingestion must absorb that without failing the batch and without inflating the
trace's token and cost totals.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

_BASE_TIME = datetime(2026, 7, 28, 12, 0, 0, tzinfo=UTC)


def _make_span(
    trace_id: str = "trace-1",
    span_id: str = "span-1",
    *,
    event_type: str = "llm_call",
    total_tokens: int | None = 150,
    cost_usd: float | None = 0.0075,
    offset_ms: int = 0,
) -> dict:
    """Create a test span payload with deterministic timestamps."""
    started = _BASE_TIME + timedelta(milliseconds=offset_ms)
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "agent_name": "test_agent",
        "event_type": event_type,
        "started_at": started.isoformat(),
        "ended_at": (started + timedelta(milliseconds=150)).isoformat(),
        "latency_ms": 150.0,
        "model": "gpt-4o",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "input_data": {"prompt": "Hello"},
        "output_data": {"response": "Hi there"},
    }


async def _ingest(client: AsyncClient, spans: list[dict]) -> dict:
    response = await client.post("/api/v1/spans", json={"spans": spans})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_replayed_batch_does_not_error(client: AsyncClient) -> None:
    """Re-sending an identical batch must succeed, not raise an integrity error."""
    spans = [_make_span(span_id=f"span-{i}", offset_ms=i) for i in range(3)]

    first = await _ingest(client, spans)
    assert first == {"accepted": 3, "duplicates": 0}

    second = await _ingest(client, spans)
    assert second == {"accepted": 0, "duplicates": 3}


@pytest.mark.asyncio
async def test_replay_does_not_duplicate_stored_spans(client: AsyncClient) -> None:
    """The trace must hold one row per span_id however often it is delivered."""
    spans = [_make_span(span_id=f"span-{i}", offset_ms=i) for i in range(3)]
    await _ingest(client, spans)
    await _ingest(client, spans)
    await _ingest(client, spans)

    detail = await client.get("/api/v1/traces/trace-1")
    assert detail.status_code == 200
    assert len(detail.json()["spans"]) == 3


@pytest.mark.asyncio
async def test_replay_does_not_inflate_totals(client: AsyncClient) -> None:
    """Token and cost totals are recomputed, so a replay cannot double them."""
    spans = [
        _make_span(span_id="s1", total_tokens=100, cost_usd=0.01, offset_ms=0),
        _make_span(span_id="s2", total_tokens=200, cost_usd=0.02, offset_ms=10),
    ]

    await _ingest(client, spans)
    first = (await client.get("/api/v1/traces/trace-1")).json()
    assert first["total_tokens"] == 300
    assert first["total_cost_usd"] == pytest.approx(0.03)

    await _ingest(client, spans)
    replayed = (await client.get("/api/v1/traces/trace-1")).json()
    assert replayed["total_tokens"] == 300
    assert replayed["total_cost_usd"] == pytest.approx(0.03)


@pytest.mark.asyncio
async def test_partial_overlap_accepts_only_new_spans(client: AsyncClient) -> None:
    """An overlapping retry stores the new spans and skips the ones already held."""
    await _ingest(client, [_make_span(span_id="s1", total_tokens=100, cost_usd=0.01)])

    result = await _ingest(
        client,
        [
            _make_span(span_id="s1", total_tokens=100, cost_usd=0.01),
            _make_span(span_id="s2", total_tokens=200, cost_usd=0.02, offset_ms=10),
        ],
    )
    assert result == {"accepted": 1, "duplicates": 1}

    detail = (await client.get("/api/v1/traces/trace-1")).json()
    assert len(detail["spans"]) == 2
    assert detail["total_tokens"] == 300


@pytest.mark.asyncio
async def test_duplicate_span_ids_within_one_batch(client: AsyncClient) -> None:
    """A batch that repeats a span_id internally is de-duplicated, not rejected."""
    result = await _ingest(
        client,
        [
            _make_span(span_id="s1", total_tokens=100, cost_usd=0.01),
            _make_span(span_id="s1", total_tokens=100, cost_usd=0.01),
        ],
    )
    assert result == {"accepted": 1, "duplicates": 1}

    detail = (await client.get("/api/v1/traces/trace-1")).json()
    assert len(detail["spans"]) == 1
    assert detail["total_tokens"] == 100


@pytest.mark.asyncio
async def test_terminal_event_replay_keeps_status_and_duration(
    client: AsyncClient,
) -> None:
    """Closing a trace twice must not corrupt its status or duration."""
    spans = [
        _make_span(span_id="s1", offset_ms=0),
        _make_span(span_id="s2", event_type="agent_end", offset_ms=1000),
    ]

    await _ingest(client, spans)
    first = (await client.get("/api/v1/traces/trace-1")).json()
    assert first["status"] == "completed"
    assert first["duration_ms"] == pytest.approx(1150.0)

    await _ingest(client, spans)
    replayed = (await client.get("/api/v1/traces/trace-1")).json()
    assert replayed["status"] == "completed"
    assert replayed["duration_ms"] == pytest.approx(1150.0)


@pytest.mark.asyncio
async def test_trace_closed_by_a_later_batch(client: AsyncClient) -> None:
    """The terminal span usually arrives in a *separate* batch from the opener.

    The trace is then created by one request (timezone-aware, in-session) and
    closed by another (read back from SQLite, naive). Subtracting the two used
    to raise a TypeError.
    """
    await _ingest(client, [_make_span(span_id="s1", offset_ms=0)])
    await _ingest(
        client, [_make_span(span_id="s2", event_type="agent_end", offset_ms=2000)]
    )

    detail = (await client.get("/api/v1/traces/trace-1")).json()
    assert detail["status"] == "completed"
    assert detail["duration_ms"] == pytest.approx(2150.0)


@pytest.mark.asyncio
async def test_error_event_marks_trace_errored(client: AsyncClient) -> None:
    await _ingest(client, [_make_span(span_id="s1", event_type="error")])
    detail = (await client.get("/api/v1/traces/trace-1")).json()
    assert detail["status"] == "error"


@pytest.mark.asyncio
async def test_empty_batch(client: AsyncClient) -> None:
    assert await _ingest(client, []) == {"accepted": 0, "duplicates": 0}


@pytest.mark.asyncio
async def test_naive_timestamps_are_accepted(client: AsyncClient) -> None:
    """SDKs that send naive datetimes are treated as UTC rather than failing."""
    span = _make_span(span_id="s1")
    span["started_at"] = "2026-07-28T12:00:00"
    span["ended_at"] = "2026-07-28T12:00:01"
    assert (await _ingest(client, [span]))["accepted"] == 1


@pytest.mark.asyncio
async def test_spans_across_multiple_traces_in_one_batch(client: AsyncClient) -> None:
    """Totals are attributed per trace, not smeared across the batch."""
    await _ingest(
        client,
        [
            _make_span(trace_id="t1", span_id="s1", total_tokens=100, cost_usd=0.01),
            _make_span(trace_id="t2", span_id="s2", total_tokens=200, cost_usd=0.02),
        ],
    )

    assert (await client.get("/api/v1/traces/t1")).json()["total_tokens"] == 100
    assert (await client.get("/api/v1/traces/t2")).json()["total_tokens"] == 200
