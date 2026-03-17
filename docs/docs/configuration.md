# Configuration

## SDK Configuration

```python
from agenttrace import tracer

tracer.init(
    collector_url="http://localhost:8000",  # Collector endpoint
)
```

The SDK is designed for zero-config operation. Just provide the collector URL.

## Collector Configuration

The collector is configured via environment variables (powered by `pydantic-settings`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./agenttrace.db` | Database connection string |
| `COLLECTOR_HOST` | `0.0.0.0` | Bind host |
| `COLLECTOR_PORT` | `8000` | Bind port |
| `LOG_LEVEL` | `info` | Logging level |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

### Database Support

- **SQLite** (default) — Zero-config, file-based
- **PostgreSQL** — For production: `postgresql+asyncpg://user:pass@host/dbname`

## Drift Detector Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `COLLECTOR_URL` | `http://localhost:8000` | Collector API URL |
| `CHECK_INTERVAL_SECONDS` | `300` | Drift check interval |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |

## Dashboard Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_COLLECTOR_URL` | (empty, uses proxy) | Collector API URL |

## Docker Compose

See the provided `docker-compose.yml` for production and `docker-compose.dev.yml` for development with hot reload.
