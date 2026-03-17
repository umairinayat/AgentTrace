# API Reference

The AgentTrace Collector exposes a REST API at `/api/v1`.

## Health

### `GET /api/v1/health`

Returns the service health status.

**Response:**

```json
{"status": "ok"}
```

## Spans

### `POST /api/v1/spans`

Ingest a batch of span events. This is the primary endpoint used by the SDK.

**Request Body:**

```json
{
  "spans": [
    {
      "trace_id": "uuid",
      "span_id": "uuid",
      "parent_span_id": null,
      "agent_name": "my_agent",
      "event_type": "llm_call",
      "started_at": "2024-01-01T00:00:00Z",
      "latency_ms": 1500.0,
      "model": "gpt-4o",
      "prompt_tokens": 100,
      "completion_tokens": 200,
      "total_tokens": 300,
      "cost_usd": 0.0045,
      "input_data": {"prompt": "..."},
      "output_data": {"response": "..."},
      "error": null,
      "metadata": {}
    }
  ]
}
```

**Response:**

```json
{"received": 1, "status": "ok"}
```

## Traces

### `GET /api/v1/traces`

List traces with pagination and filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 50 | Items per page |
| `agent_name` | string | — | Filter by agent |
| `status` | string | — | `running`, `completed`, `error` |
| `sort_by` | string | `started_at` | Sort column |
| `sort_order` | string | `desc` | `asc` or `desc` |

### `GET /api/v1/traces/{trace_id}`

Get a trace with all its spans.

### `GET /api/v1/traces/{trace_id}/timeline`

Get timeline data for the Gantt chart visualization.

## Statistics

### `GET /api/v1/stats`

Aggregated statistics across all traces.

**Response includes:** total traces, spans, tokens, cost, average latency, top agents, top models.

## Drift

### `GET /api/v1/drift/alerts`

List all drift alerts. Optional `agent_name` query parameter.

### `GET /api/v1/drift/baseline/{agent_name}`

Get the current baseline for an agent.

### `POST /api/v1/drift/baseline/{agent_name}/rebuild`

Trigger a baseline rebuild for an agent.
