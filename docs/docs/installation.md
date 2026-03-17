# Installation

## SDK

```bash
pip install agenttrace
```

### Optional extras

```bash
# LangChain integration
pip install agenttrace[langchain]

# Drift detection support
pip install agenttrace[drift]

# All integrations
pip install agenttrace[langchain,langgraph,crewai,autogen,drift]
```

## Collector + Dashboard (Docker)

The fastest way to run the full stack:

```bash
git clone https://github.com/agenttrace/agenttrace.git
cd agenttrace
docker compose up -d
```

This starts:

| Service | Port | Description |
|---------|------|-------------|
| Collector | 8000 | FastAPI backend |
| Dashboard | 3000 | React UI |
| Drift Detector | — | Background service |

## Development Setup

For local development with hot reload:

```bash
docker compose -f docker-compose.dev.yml up -d
```

### Manual setup (without Docker)

**Collector:**

```bash
cd collector
pip install -e .
uvicorn app.main:app --reload --port 8000
```

**Dashboard:**

```bash
cd dashboard
npm install
npm run dev
```

**Drift Detector:**

```bash
cd drift-detector
pip install -e .
python -m detector.main
```

## Requirements

- Python 3.11+
- Node.js 20+ (for dashboard)
- Docker & Docker Compose (optional, recommended)
