# Deployment

## Docker Compose (Recommended)

```bash
git clone https://github.com/agenttrace/agenttrace.git
cd agenttrace
docker compose up -d
```

This starts all three services:

- **Collector** on port 8000
- **Dashboard** on port 3000
- **Drift Detector** (background, no exposed port)

### Production Configuration

For production, configure:

1. **Database** — Switch from SQLite to PostgreSQL:

    ```yaml
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/agenttrace
    ```

2. **CORS** — Restrict origins:

    ```yaml
    environment:
      - CORS_ORIGINS=["https://your-domain.com"]
    ```

3. **Volumes** — Persist data:

    ```yaml
    volumes:
      - agenttrace_data:/data
    ```

## Manual Deployment

### Collector

```bash
cd collector
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Dashboard

```bash
cd dashboard
npm install
npm run build
# Serve dist/ with nginx or any static file server
```

### Drift Detector

```bash
cd drift-detector
pip install -e .
python -m detector.main
```

## Health Checks

The collector exposes a health endpoint:

```bash
curl http://localhost:8000/api/v1/health
# {"status": "ok"}
```

Docker Compose is configured with health checks that use this endpoint.

## Reverse Proxy (Nginx)

The dashboard Docker image includes Nginx configured to:

- Serve the React SPA
- Proxy `/api/` requests to the collector
- Handle SPA routing (all paths serve `index.html`)
