# AgentTrace Drift Detector

Background worker that detects behavioral drift in traced agents and records
alerts back in the Collector (so they surface in the dashboard).

## How it works

Every `CHECK_INTERVAL_SECONDS`, for each agent known to the collector:

1. Loads the agent's persisted baseline from `GET /api/v1/drift/baseline/{agent}`
   (building + persisting one via `POST /api/v1/drift/baselines` if none exists).
2. Compares recent `llm_call` / `tool_call` spans against the baseline using five
   independent checks:
   - **Semantic** -- embedding cosine distance (sentence-transformers).
   - **Distribution** -- response-length shift (Kolmogorov-Smirnov).
   - **Token** -- relative token-usage change.
   - **Tool** -- tool-call pattern shift.
   - **Latency** -- relative latency change.
3. On drift, delivers alerts (webhooks + email) and posts them to
   `POST /api/v1/drift/alerts`.

Rebuild requests queued from the dashboard are consumed each cycle and force a
fresh baseline. Baselines are persisted by the collector, so a detector restart
does not lose them.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `COLLECTOR_URL` | `http://localhost:8000` | Collector base URL. |
| `CHECK_INTERVAL_SECONDS` | `300` | Seconds between drift checks. |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model (~80MB, CPU). |
| `SLACK_WEBHOOK_URL` / `DISCORD_WEBHOOK_URL` / `CUSTOM_WEBHOOK_URL` | _unset_ | Alert webhooks. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `ALERT_EMAIL` | _unset_ | Email alerts (STARTTLS optional). |

## Development

```bash
pip install -e ".[dev]"
pytest            # comparator/baseline/alerter tests (embedder stubbed)
ruff check .
mypy .
```
