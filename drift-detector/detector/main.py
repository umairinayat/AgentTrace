"""Entry point for the drift detector background service.

The detector is the consumer side of the drift pipeline:

1. Discover agents via ``GET /api/v1/agents`` (all agents, not just top-10).
2. For each agent, load its baseline from the collector
   (``GET /api/v1/drift/baseline/{agent}``); build + persist one if none exists.
3. Compare recent behavior against the baseline; on drift, post alerts back to the
   collector (``POST /api/v1/drift/alerts``) so the dashboard can surface them.
4. Consume rebuild requests queued from the dashboard and force a rebuild.

Baselines are persisted by the collector, so a detector restart does not lose them.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from detector.alerter import Alerter
from detector.baseline import BaselineBuilder
from detector.comparator import DriftComparator
from detector.models import BaselineRecord, DriftConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Keys the various SDK integrations use to stash response text / tool names.
_RESPONSE_KEYS = ("response", "output", "text", "content", "result")
_TOOL_KEYS = ("tool", "tool_name", "name", "tool_input")


def _extract_text(span: dict[str, Any]) -> str:
    """Extract response text from a span's output_data across integration shapes."""
    output = span.get("output_data") or {}
    for key in _RESPONSE_KEYS:
        value = output.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _extract_tool(span: dict[str, Any]) -> str:
    """Extract a tool name from a tool_call span's input_data/metadata."""
    source = span.get("input_data") or {}
    for key in _TOOL_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value:
            return value
    metadata = span.get("metadata") or {}
    for key in _TOOL_KEYS:
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


class DriftDetectorService:
    """Background service that continuously checks for behavioral drift."""

    def __init__(
        self,
        collector_url: str = "http://localhost:8000",
        check_interval: int = 300,
        embedding_model: str = "all-MiniLM-L6-v2",
        embedder: Any | None = None,
    ) -> None:
        self._collector_url = collector_url.rstrip("/")
        self._check_interval = check_interval
        self._builder = BaselineBuilder(embedding_model=embedding_model, embedder=embedder)
        self._comparator = DriftComparator(
            embedding_model=embedding_model, embedder=embedder
        )
        self._alerter = Alerter(
            slack_webhook=os.environ.get("SLACK_WEBHOOK_URL"),
            discord_webhook=os.environ.get("DISCORD_WEBHOOK_URL"),
            custom_webhook=os.environ.get("CUSTOM_WEBHOOK_URL"),
            smtp_host=os.environ.get("SMTP_HOST"),
            smtp_port=int(os.environ.get("SMTP_PORT", "587")),
            smtp_user=os.environ.get("SMTP_USER"),
            smtp_password=os.environ.get("SMTP_PASSWORD"),
            email_recipient=os.environ.get("ALERT_EMAIL"),
        )
        self._config = DriftConfig()
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------ http

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=10.0)
        return self._http

    async def _get_json(self, path: str, **params: Any) -> Any:
        client = self._client()
        response = await client.get(f"{self._collector_url}{path}", params=params or None)
        response.raise_for_status()
        return response.json()

    async def _post_json(self, path: str, payload: Any) -> httpx.Response:
        client = self._client()
        response = await client.post(f"{self._collector_url}{path}", json=payload)
        response.raise_for_status()
        return response

    # ------------------------------------------------------------- discovery

    async def _fetch_agents(self) -> list[str]:
        """Get every agent name known to the collector (uncapped)."""
        try:
            data = await self._get_json("/api/v1/agents")
            return [a["name"] for a in data]
        except Exception:
            logger.exception("Failed to fetch agents from collector")
            return []

    async def _consume_rebuild_requests(self) -> set[str]:
        """Fetch and delete pending rebuild requests, returning their agent names."""
        try:
            requests = await self._get_json("/api/v1/drift/rebuild-requests")
        except Exception:
            logger.exception("Failed to fetch rebuild requests")
            return set()

        agents: set[str] = set()
        for req in requests:
            agents.add(req["agent_name"])
            try:
                client = self._client()
                await client.delete(
                    f"{self._collector_url}/api/v1/drift/rebuild-requests/{req['id']}"
                )
            except Exception:
                logger.exception("Failed to consume rebuild request %s", req.get("id"))
        return agents

    async def _fetch_recent_spans(
        self, agent_name: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch recent LLM-call and tool-call spans for an agent."""
        try:
            data = await self._get_json(
                "/api/v1/traces",
                agent_name=agent_name,
                page_size=limit,
                sort_by="started_at",
                sort_order="desc",
            )

            all_spans: list[dict[str, Any]] = []
            client = self._client()
            for trace in data.get("items", []):
                detail = await client.get(
                    f"{self._collector_url}/api/v1/traces/{trace['id']}"
                )
                detail.raise_for_status()
                for span in detail.json().get("spans", []):
                    if span.get("event_type") in ("llm_call", "tool_call"):
                        all_spans.append(span)
                if len(all_spans) >= limit:
                    break
            return all_spans[:limit]
        except Exception:
            logger.exception("Failed to fetch spans for %s", agent_name)
            return []

    # --------------------------------------------------------- persistence

    async def _load_baseline(self, agent_name: str) -> BaselineRecord | None:
        """Load the most recent persisted baseline for an agent, if any."""
        try:
            data = await self._get_json(f"/api/v1/drift/baseline/{agent_name}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.exception("Failed to load baseline for %s", agent_name)
            return None
        except Exception:
            logger.exception("Failed to load baseline for %s", agent_name)
            return None

        if not data.get("embedding_centroid"):
            # Baseline was built before persistence carried the centroid; rebuild.
            return None

        return BaselineRecord(
            agent_name=data["agent_name"],
            built_at=data["built_at"],
            n_samples=data["n_samples"],
            avg_response_length=data.get("avg_response_length") or 0.0,
            avg_latency_ms=data.get("avg_latency_ms") or 0.0,
            avg_token_count=data.get("avg_token_count") or 0.0,
            embedding_centroid=data["embedding_centroid"],
            response_length_distribution=data.get("response_length_distribution") or [],
            tool_call_distribution=data.get("tool_call_distribution") or {},
        )

    async def _persist_baseline(self, baseline: BaselineRecord) -> None:
        """Persist a freshly built baseline to the collector."""
        try:
            await self._post_json(
                "/api/v1/drift/baselines", baseline.model_dump(mode="json")
            )
        except Exception:
            logger.exception("Failed to persist baseline for %s", baseline.agent_name)

    async def _post_alert(self, alert_data: dict[str, Any]) -> None:
        """Post a drift alert to the collector so the dashboard can display it."""
        try:
            await self._post_json("/api/v1/drift/alerts", [alert_data])
        except Exception:
            logger.exception("Failed to post alert for %s", alert_data.get("agent_name"))

    # ------------------------------------------------------------- checking

    async def check_agent(self, agent_name: str, force_rebuild: bool = False) -> None:
        """Check a single agent for drift."""
        spans = await self._fetch_recent_spans(agent_name)
        llm_spans = [s for s in spans if s.get("event_type") == "llm_call"]
        tool_spans = [s for s in spans if s.get("event_type") == "tool_call"]

        texts = [t for t in (_extract_text(s) for s in llm_spans) if t]
        if len(texts) < self._config.min_samples:
            logger.debug(
                "Not enough LLM samples for %s (%d < %d)",
                agent_name,
                len(texts),
                self._config.min_samples,
            )
            return

        latencies = [s["latency_ms"] for s in llm_spans if s.get("latency_ms") is not None]
        tokens = [s["total_tokens"] for s in llm_spans if s.get("total_tokens") is not None]
        tools = [t for t in (_extract_tool(s) for s in tool_spans) if t]

        # Load existing baseline unless a rebuild was requested.
        baseline: BaselineRecord | None = None
        if not force_rebuild:
            baseline = await self._load_baseline(agent_name)

        if baseline is None:
            logger.info("Building baseline for %s (%d samples)", agent_name, len(texts))
            baseline = self._builder.build(
                agent_name=agent_name,
                response_texts=texts,
                latencies=latencies,
                token_counts=tokens,
                tool_calls=tools,
            )
            await self._persist_baseline(baseline)
            return  # Compare on the next cycle once a baseline exists.

        report = self._comparator.compare(
            baseline=baseline,
            recent_texts=texts,
            recent_latencies=latencies,
            recent_token_counts=tokens,
            recent_tool_calls=tools,
            config=self._config,
        )

        if report.is_drifted:
            logger.warning(
                "Drift detected for %s: %d alerts", agent_name, len(report.alerts)
            )
            for alert in report.alerts:
                await self._alerter.send_alert(alert)
                await self._post_alert(alert.model_dump(mode="json"))

    async def run(self) -> None:
        """Main loop -- check all agents for drift periodically."""
        logger.info(
            "Drift detector started: collector=%s, interval=%ds",
            self._collector_url,
            self._check_interval,
        )

        while True:
            try:
                rebuild_agents = await self._consume_rebuild_requests()
                agents = await self._fetch_agents()
                for agent_name in agents:
                    await self.check_agent(
                        agent_name, force_rebuild=agent_name in rebuild_agents
                    )
            except Exception:
                logger.exception("Error in drift detection loop")

            await asyncio.sleep(self._check_interval)


def main() -> None:
    """Entry point."""
    collector_url = os.environ.get("COLLECTOR_URL", "http://localhost:8000")
    check_interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))
    embedding_model = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    service = DriftDetectorService(
        collector_url=collector_url,
        check_interval=check_interval,
        embedding_model=embedding_model,
    )

    asyncio.run(service.run())


if __name__ == "__main__":
    main()
