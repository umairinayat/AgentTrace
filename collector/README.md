# AgentTrace Collector

FastAPI backend that receives, stores, and serves trace data for AgentTrace.

## Responsibilities

- **Ingest** span batches from the SDK at `POST /api/v1/spans` (auto-creates
  `Trace` records; batches are capped at 1000 spans per request).
- **Serve** the dashboard: trace list/detail/timeline, aggregated stats, agent
  enumeration.
- **Persist drift state**: `POST /api/v1/drift/alerts` and
  `POST /api/v1/drift/baselines` let the drift detector store its findings and
  baselines here; rebuild requests queued via
  `POST /api/v1/drift/baseline/{agent}/rebuild` are polled by the detector.

## Configuration

All settings are environment variables (see `app/config.py`):

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./agenttrace.db` | Any SQLAlchemy async URL. Use `postgresql+asyncpg://...` for Postgres. |
| `COLLECTOR_HOST` | `0.0.0.0` | Bind host. |
| `COLLECTOR_PORT` | `8000` | Bind port. |
| `LOG_LEVEL` | `INFO` | |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins. `*` disables credentials. |

## Database migrations

The default SQLite DB is bootstrapped with `create_all` on startup. For
production / Postgres, use Alembic:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/agenttrace \
  alembic upgrade head
```

## Development

```bash
pip install -e ".[dev]"
pytest            # 25 tests
ruff check .
mypy .
```
