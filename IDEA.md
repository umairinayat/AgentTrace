# AgentTrace — Claude Code Master Prompt

> **What this file is:** Give this entire file to Claude Code at the start of every session.
> It contains the full project spec, architecture, file structure, coding standards,
> and phase-by-phase instructions. Claude Code should read this before writing a single line.

---

## 0. Who You Are Building This For

- **Author:** Umair (github.com/umairinayat)
- **Stack fluency:** Python 3.11+, FastAPI, PyTorch, asyncio, SQLAlchemy async, Pydantic v2, React, Docker
- **Hardware:** RTX 4090 (24GB VRAM) — local LLMs via Ollama available for testing
- **Existing project for reference:** DeepContext (https://github.com/umairinayat/DeepContext) — async agent memory system, same coding style expected
- **Goal:** Production-quality, fully open-source MIT-licensed project that gets starred on GitHub, used in production, and forms the basis of a research paper

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project name** | AgentTrace |
| **Tagline** | "See exactly what your agents are doing — every step, every decision, every cost." |
| **License** | MIT |
| **PyPI package** | `agenttrace` |
| **GitHub org/repo** | `agenttrace/agenttrace` (monorepo) |
| **Primary language** | Python (SDK + Collector + Drift Detector), TypeScript/React (Dashboard) |
| **Minimum Python** | 3.11 |

---

## 2. What AgentTrace Is

AgentTrace is a **fully open-source, self-hosted observability and debugging platform for multi-agent AI systems**.

It captures every LLM call, tool execution, sub-agent message, token cost, and latency across an entire agent pipeline — and correlates them into a visual trace timeline in a web dashboard.

**The killer feature no competitor has:** Behavioral Drift Detection. When a model provider (OpenAI, Anthropic, Google) silently updates their backend model, your agent's behavior changes without any code changes on your end. AgentTrace detects this automatically using embedding cosine similarity and statistical distribution tests, then alerts you.

### Problems It Solves

1. 89% of developers believe they have agent observability — but only 62% can actually monitor agent actions step by step (2026 industry survey of 1,300+ developers)
2. Multi-agent traces in LangSmith and Langfuse frequently merge or lose correlation across sub-agents
3. No open-source tool detects behavioral drift over time
4. Commercial tools (Arize AI, Galileo) are expensive and cloud-only
5. OpenTelemetry semantic conventions for AI agents are still in alpha — no stable standard exists

### Three Differentiators vs Competitors

| Feature | AgentTrace | LangSmith | Langfuse | Arize AI |
|---|---|---|---|---|
| Behavioral drift detection | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Fully self-hosted | ✅ Yes | ❌ Cloud only | ✅ Yes | ❌ Cloud only |
| Zero-config SDK (2 lines) | ✅ Yes | ❌ Complex setup | ❌ Complex setup | ❌ Complex setup |
| Open source (MIT) | ✅ Yes | ❌ Proprietary | ✅ AGPL | ❌ Proprietary |
| Local LLM support (Ollama)/ Open router / chatgpt also | ✅ Yes | ⚠️ Partial | ⚠️ Partial | ❌ No |

---

## 3. Full Repository Structure

Build this exact monorepo layout. Do not deviate from it.

```
agenttrace/
│
├── sdk/                              # Python SDK — pip install agenttrace
│   ├── agenttrace/
│   │   ├── __init__.py               # Exports: tracer, Tracer, trace_agent
│   │   ├── tracer.py                 # Core Tracer class — singleton
│   │   ├── decorators.py             # @trace_agent decorator
│   │   ├── context.py                # Async context vars for trace propagation
│   │   ├── models.py                 # Pydantic v2 models: SpanEvent, TraceContext
│   │   ├── client.py                 # Async HTTP client (httpx) to send events
│   │   ├── queue.py                  # Non-blocking async event queue + batch flusher
│   │   ├── pricing.py                # Cost calculator using pricing.json
│   │   ├── pricing.json              # Model pricing table (update manually)
│   │   └── integrations/
│   │       ├── __init__.py
│   │       ├── langchain.py          # LangChain BaseCallbackHandler
│   │       ├── langgraph.py          # LangGraph StateGraph middleware
│   │       ├── crewai.py             # CrewAI monkey-patch
│   │       ├── autogen.py            # AutoGen ConversableAgent patch
│   │       ├── openai_sdk.py         # OpenAI Agents SDK hook
│   │       └── ollama.py             # Ollama httpx middleware
│   ├── tests/
│   │   ├── test_tracer.py
│   │   ├── test_queue.py
│   │   ├── test_models.py
│   │   ├── test_integrations/
│   │   │   ├── test_langchain.py
│   │   │   └── test_langgraph.py
│   │   └── conftest.py
│   ├── examples/
│   │   ├── langchain_example.py
│   │   ├── langgraph_example.py
│   │   ├── crewai_example.py
│   │   └── ollama_example.py
│   ├── pyproject.toml
│   ├── README.md
│   └── CHANGELOG.md
│
├── collector/                        # FastAPI backend — receives + stores traces
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory
│   │   ├── config.py                 # Settings via pydantic-settings
│   │   ├── models.py                 # SQLAlchemy async ORM models
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── database.py               # Async DB engine + session factory
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── spans.py              # POST /api/v1/spans
│   │   │   ├── traces.py             # GET /api/v1/traces, GET /api/v1/traces/{id}
│   │   │   ├── stats.py              # GET /api/v1/stats
│   │   │   ├── drift.py              # GET /api/v1/drift/alerts
│   │   │   └── health.py             # GET /api/v1/health
│   │   └── middleware/
│   │       ├── cors.py
│   │       └── logging.py
│   ├── alembic/                      # DB migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── test_routes/
│   │   └── conftest.py
│   ├── Dockerfile
│   ├── alembic.ini
│   └── pyproject.toml
│
├── drift-detector/                   # Background worker — behavioral drift
│   ├── detector/
│   │   ├── __init__.py
│   │   ├── main.py                   # Entry point, continuous loop
│   │   ├── baseline.py               # Build + store response baselines
│   │   ├── comparator.py             # Cosine similarity + KS test logic
│   │   ├── alerter.py                # Send webhook/email alerts
│   │   └── models.py                 # DriftReport, BaselineRecord
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
│
├── dashboard/                        # React + TypeScript frontend
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── TraceList.tsx         # Page 1: all traces table
│   │   │   ├── TraceDetail.tsx       # Page 2: Gantt timeline + span inspector
│   │   │   ├── CostAnalytics.tsx     # Page 3: token spend charts
│   │   │   ├── DriftMonitor.tsx      # Page 4: drift score timeline + alerts
│   │   │   └── Settings.tsx          # Page 5: config UI
│   │   ├── components/
│   │   │   ├── GanttTimeline.tsx     # D3.js Gantt chart (custom)
│   │   │   ├── SpanInspector.tsx     # JSON viewer + prompt/response viewer
│   │   │   ├── DriftChart.tsx        # D3.js line chart
│   │   │   ├── CostBreakdown.tsx     # Bar charts
│   │   │   ├── AlertFeed.tsx
│   │   │   └── ui/                   # shadcn/ui components
│   │   ├── hooks/
│   │   │   ├── useTraces.ts          # React Query hooks
│   │   │   ├── useDrift.ts
│   │   │   └── useStats.ts
│   │   ├── store/
│   │   │   └── app.ts                # Zustand global state
│   │   ├── api/
│   │   │   └── client.ts             # Typed API client
│   │   └── types/
│   │       └── index.ts              # Shared TypeScript types
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── docs/                             # MkDocs Material documentation
│   ├── docs/
│   │   ├── index.md
│   │   ├── quickstart.md
│   │   ├── installation.md
│   │   ├── integrations/
│   │   │   ├── langchain.md
│   │   │   ├── langgraph.md
│   │   │   ├── crewai.md
│   │   │   ├── autogen.md
│   │   │   └── ollama.md
│   │   ├── configuration.md
│   │   ├── drift-detection.md
│   │   ├── api-reference.md
│   │   ├── deployment.md
│   │   └── contributing.md
│   └── mkdocs.yml
│
├── docker-compose.yml                # Production: all services
├── docker-compose.dev.yml            # Dev: with hot reload
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # lint + typecheck + test on PR
│   │   ├── publish-sdk.yml           # auto-publish to PyPI on tag
│   │   └── docs.yml                  # deploy docs to GitHub Pages
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       ├── feature_request.md
│       └── integration_request.md
├── README.md                         # The main README — critical for stars
├── CONTRIBUTING.md
├── LICENSE                           # MIT
└── .gitignore
```

---

## 4. Core Data Models

These are the exact Pydantic v2 models. Use these everywhere — SDK, Collector, and Dashboard API responses.

### SDK Models (`sdk/agenttrace/models.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid

class SpanEvent(BaseModel):
    """A single unit of trace data — one LLM call, tool call, or agent lifecycle event."""
    
    # Identity
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    
    # Classification
    agent_name: str
    event_type: Literal[
        "agent_start",
        "agent_end", 
        "llm_call",
        "tool_call",
        "tool_end",
        "message",
        "error"
    ]
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    latency_ms: Optional[float] = None
    
    # LLM-specific
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    
    # Payload
    input_data: Optional[dict] = None   # prompt or tool input
    output_data: Optional[dict] = None  # response or tool output
    
    # Extra
    error: Optional[str] = None
    metadata: Optional[dict] = None
    sdk_version: str = "0.1.0"


class BatchSpanRequest(BaseModel):
    """What the SDK sends to the Collector — a batch of spans."""
    spans: list[SpanEvent]
    agent_session_id: Optional[str] = None


class TraceContext(BaseModel):
    """Stored in contextvars for async propagation."""
    trace_id: str
    parent_span_id: Optional[str] = None
    agent_name: str
```

### Collector DB Models (`collector/app/models.py`)

```python
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Trace(Base):
    __tablename__ = "traces"
    
    id = Column(String, primary_key=True)           # UUID
    name = Column(String, nullable=False)            # agent name
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    total_cost_usd = Column(Float, nullable=True)
    status = Column(String, default="running")       # running | completed | error
    metadata_ = Column("metadata", JSON, nullable=True)
    spans = relationship("Span", back_populates="trace", cascade="all, delete-orphan")


class Span(Base):
    __tablename__ = "spans"
    
    id = Column(String, primary_key=True)
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False)
    parent_span_id = Column(String, nullable=True)
    agent_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    latency_ms = Column(Float, nullable=True)
    model = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    trace = relationship("Trace", back_populates="spans")


class DriftBaseline(Base):
    __tablename__ = "drift_baselines"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False, index=True)
    built_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    n_samples = Column(Integer, nullable=False)
    avg_response_length = Column(Float)
    avg_latency_ms = Column(Float)
    avg_token_count = Column(Float)
    embedding_centroid = Column(JSON)   # list[float] — serialized numpy array
    tool_call_distribution = Column(JSON)


class DriftAlert(Base):
    __tablename__ = "drift_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False, index=True)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    alert_type = Column(String, nullable=False)   # semantic | distribution | token | tool
    severity = Column(String, default="warning")  # warning | critical
    score = Column(Float)
    threshold = Column(Float)
    description = Column(Text)
    resolved = Column(Integer, default=0)          # 0 = unresolved, 1 = resolved
```

---

## 5. REST API Contract

The Collector exposes these endpoints. The Dashboard calls them. The SDK calls only `POST /api/v1/spans`.

| Method | Path | Request Body | Response | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/spans` | `BatchSpanRequest` | `{"accepted": N}` | Ingest batch of spans from SDK |
| `GET` | `/api/v1/traces` | — | `PaginatedTraces` | List all traces, paginated |
| `GET` | `/api/v1/traces/{trace_id}` | — | `TraceDetail` | Full trace with all spans |
| `GET` | `/api/v1/traces/{trace_id}/timeline` | — | `TimelineData` | Gantt-format data |
| `GET` | `/api/v1/stats` | — | `StatsResponse` | Aggregated cost/latency/token stats |
| `GET` | `/api/v1/drift/alerts` | — | `list[DriftAlert]` | All unresolved drift alerts |
| `GET` | `/api/v1/drift/baseline/{agent}` | — | `DriftBaseline` | Current baseline for an agent |
| `POST` | `/api/v1/drift/baseline/{agent}/rebuild` | — | `{"status": "ok"}` | Trigger baseline rebuild |
| `GET` | `/api/v1/health` | — | `{"status": "ok"}` | Health check |

### Query Parameters for `GET /api/v1/traces`

```
page: int = 1
page_size: int = 50
agent_name: str = None       # filter by agent name
status: str = None           # running | completed | error
from_date: datetime = None
to_date: datetime = None
min_cost: float = None
sort_by: str = "started_at"  # started_at | cost | duration | tokens
sort_order: str = "desc"
```

---

## 6. SDK Usage — What It Looks Like From the Outside

This is the developer experience you are building toward. Every implementation decision should serve this simplicity.

### Minimum Setup (2 lines)

```python
from agenttrace import tracer

tracer.init(collector_url="http://localhost:8000")
```

### Tracing with LangChain (automatic — 0 code changes)

```python
from agenttrace import tracer
from agenttrace.integrations.langchain import AgentTraceCallback

tracer.init(collector_url="http://localhost:8000")
callback = AgentTraceCallback(agent_name="my_research_agent")

# Your existing LangChain code — unchanged
chain = LLMChain(llm=llm, prompt=prompt, callbacks=[callback])
result = chain.run("What is the capital of France?")
# Everything is traced automatically
```

### Tracing LangGraph (automatic — 1 line patch)

```python
from agenttrace import tracer
from agenttrace.integrations.langgraph import patch_langgraph

tracer.init(collector_url="http://localhost:8000")
patch_langgraph()  # patches all LangGraph StateGraph instances

# Your existing LangGraph code — unchanged
graph = StateGraph(AgentState)
graph.add_node("researcher", researcher_node)
graph.add_node("writer", writer_node)
# ...
```

### Manual Span API (for custom agents)

```python
from agenttrace import tracer

tracer.init(collector_url="http://localhost:8000")

async def my_custom_agent(query: str):
    with tracer.span("my_agent", agent_name="custom_agent") as span:
        # span.set_input({"query": query})
        response = await call_my_llm(query)
        # span.set_output({"response": response})
        return response
```

### Decorator API

```python
from agenttrace import tracer

tracer.init(collector_url="http://localhost:8000")

@tracer.trace_agent(name="summarizer")
async def summarize(text: str) -> str:
    return await llm.ainvoke(f"Summarize: {text}")
```

---

## 7. Drift Detection Algorithm

This is the core research contribution. Implement it exactly as described.

### Step 1 — Build Baseline

Triggered manually via dashboard or automatically after 50 traces.

```python
class BaselineBuilder:
    def __init__(self, db, embedding_model="all-MiniLM-L6-v2"):
        self.embedder = SentenceTransformer(embedding_model)
        # Model is 80MB, runs on CPU, zero cost, no API key
    
    async def build(self, agent_name: str, n_samples: int = 50) -> BaselineRecord:
        # 1. Fetch last n_samples completed spans where event_type = "llm_call"
        # 2. Extract response texts from output_data
        # 3. Compute embedding for each response text
        # 4. centroid = np.mean(embeddings, axis=0)
        # 5. Compute stats: avg_response_length, avg_latency_ms, avg_token_count
        # 6. Compute tool_call_distribution: {tool_name: frequency_ratio}
        # 7. Store in drift_baselines table
        pass
```

### Step 2 — Compare Against Baseline

Runs every 5 minutes as a background loop.

```python
class DriftComparator:
    def compare(
        self, 
        baseline: BaselineRecord,
        recent_spans: list[Span],
        config: DriftConfig
    ) -> DriftReport:
        
        alerts = []
        
        # Check 1: Semantic drift (embedding cosine similarity)
        recent_embeddings = self.embedder.encode([s.output_data["text"] for s in recent_spans])
        recent_centroid = np.mean(recent_embeddings, axis=0)
        cosine_dist = 1 - cosine_similarity([baseline.embedding_centroid], [recent_centroid])[0][0]
        if cosine_dist > config.semantic_threshold:  # default 0.15
            alerts.append(DriftAlert(
                alert_type="semantic",
                score=cosine_dist,
                threshold=config.semantic_threshold,
                description=f"Semantic drift detected: cosine distance = {cosine_dist:.3f}"
            ))
        
        # Check 2: Response length distribution (KS test)
        baseline_lengths = baseline.response_length_distribution  # stored as list
        recent_lengths = [len(s.output_data.get("text", "")) for s in recent_spans]
        ks_stat, p_value = scipy.stats.ks_2samp(baseline_lengths, recent_lengths)
        if p_value < config.ks_pvalue_threshold:  # default 0.05
            alerts.append(DriftAlert(
                alert_type="distribution",
                score=ks_stat,
                threshold=config.ks_pvalue_threshold,
                description=f"Response length distribution shifted: KS p-value = {p_value:.4f}"
            ))
        
        # Check 3: Token count anomaly
        recent_avg_tokens = np.mean([s.total_tokens for s in recent_spans if s.total_tokens])
        pct_change = abs(recent_avg_tokens - baseline.avg_token_count) / baseline.avg_token_count
        if pct_change > config.token_change_threshold:  # default 0.20
            alerts.append(DriftAlert(
                alert_type="token",
                score=pct_change,
                threshold=config.token_change_threshold,
                description=f"Token usage changed by {pct_change*100:.1f}%"
            ))
        
        return DriftReport(
            agent_name=baseline.agent_name,
            checked_at=datetime.utcnow(),
            alerts=alerts,
            is_drifted=len(alerts) > 0,
            cosine_distance=cosine_dist,
            ks_p_value=p_value,
            token_pct_change=pct_change
        )
```

---

## 8. Dashboard Pages — Exact Spec

### Page 1 — Trace List (`/traces`)

- Table with columns: Trace Name | Agent | Started | Duration | Total Tokens | Total Cost ($) | Status badge
- Status badge: green "completed", yellow "running", red "error"
- Filters bar at top: date range picker, agent name dropdown, status dropdown
- Click any row → navigates to `/traces/{trace_id}`
- Pagination at bottom (50 per page)
- Sort by any column header (click to toggle asc/desc)

### Page 2 — Trace Detail (`/traces/:id`)

**Top section:**
- Breadcrumb: Traces > {trace_name}
- Summary chips: Total Duration | Total Tokens | Total Cost | Span Count

**Main section — Gantt Timeline (D3.js custom):**
- X axis = time (milliseconds from trace start)
- Y axis = one row per span (agent name + span type)
- Bars color-coded:
  - Blue `#3B82F6` = LLM call
  - Orange `#F59E0B` = Tool call
  - Green `#10B981` = Sub-agent / agent lifecycle
  - Red `#EF4444` = Error
- Hover tooltip: model name, token count, cost, latency
- Click a bar → opens SpanInspector panel on the right

**Right panel — SpanInspector:**
- Tabs: Input | Output | Metadata
- Input tab: formatted prompt text (syntax highlight if it contains JSON)
- Output tab: response text (scrollable)
- Metadata tab: raw JSON of all fields
- Copy button for prompt and response

### Page 3 — Cost Analytics (`/analytics`)

- Line chart (D3.js): daily token spend over last 30 days
- Bar chart: cost by agent name (top 10)
- Bar chart: cost by model (top 10)
- Summary cards: Total spend this week | Most expensive trace | Most expensive agent | Most used model

### Page 4 — Drift Monitor (`/drift`)

- One card per agent that has a baseline
- Each card shows:
  - Agent name
  - Baseline built: "X traces, built Y days ago"
  - Drift score line chart (cosine distance over time, last 30 days) using D3.js
  - Red horizontal dashed line at threshold (0.15)
  - Alert badges: "2 active alerts"
- Alert list at bottom: sortable by severity/date
- "Rebuild Baseline" button per agent (calls `POST /api/v1/drift/baseline/{agent}/rebuild`)

### Page 5 — Settings (`/settings`)

- Collector URL (text input + test connection button)
- Alert webhooks: Slack webhook URL, Discord webhook URL, custom webhook URL
- Email alerts: SMTP host, port, username, password (masked), recipient
- Pricing: upload custom `pricing.json` or view/edit current table
- Retention: auto-delete traces older than N days (dropdown: 7, 14, 30, 60, 90, never)
- Danger zone: "Delete all traces" (red button, requires typing "DELETE" to confirm)

---

## 9. Docker Compose — Full Stack

```yaml
# docker-compose.yml
version: "3.9"

services:
  collector:
    build: ./collector
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////data/agenttrace.db
      - COLLECTOR_HOST=0.0.0.0
      - COLLECTOR_PORT=8000
    volumes:
      - agenttrace_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  drift_detector:
    build: ./drift-detector
    environment:
      - COLLECTOR_URL=http://collector:8000
      - CHECK_INTERVAL_SECONDS=300
      - EMBEDDING_MODEL=all-MiniLM-L6-v2
    depends_on:
      collector:
        condition: service_healthy
    volumes:
      - agenttrace_data:/data

  dashboard:
    build: ./dashboard
    ports:
      - "3000:80"
    environment:
      - VITE_COLLECTOR_URL=http://localhost:8000
    depends_on:
      - collector

volumes:
  agenttrace_data:
```

---

## 10. Collector FastAPI App — Main Setup

```python
# collector/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database import init_db
from .routes import spans, traces, stats, drift, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="AgentTrace Collector",
    description="Receives and stores AI agent trace events",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(spans.router, prefix="/api/v1")
app.include_router(traces.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(drift.router, prefix="/api/v1")
```

---

## 11. Coding Standards

Follow these strictly. Every file must meet these standards.

### Python

```toml
# pyproject.toml standards for all Python packages
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "UP", "B", "SIM"]
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- All async functions must use `async def` and `await` — never `threading`
- All database access must use SQLAlchemy async sessions — never sync
- All config via `pydantic-settings` — never `os.environ` directly
- Type hints on every function signature — no bare `dict` or `list`
- Docstrings on every public class and function
- No print statements — use Python `logging` module everywhere
- All errors must be caught and logged, never silently swallowed

### TypeScript / React

- Use TypeScript strict mode (`"strict": true` in tsconfig)
- All components must be functional (no class components)
- All API calls through the typed `api/client.ts` — never raw `fetch` in components
- React Query for all server state — no `useState` + `useEffect` for data fetching
- Zustand only for UI state (selected trace, sidebar open, etc.)
- All D3.js charts must be in dedicated components and accept typed props

### Git Commits

Follow Conventional Commits:
- `feat: add LangGraph integration`
- `fix: resolve span correlation bug in async context`
- `docs: add CrewAI quickstart guide`
- `test: add drift detector unit tests`
- `chore: update pricing.json for GPT-5`

---

## 12. pricing.json Format

```json
{
  "version": "2026-03-17",
  "models": {
    "gpt-4o": {
      "input_per_1k_tokens": 0.0025,
      "output_per_1k_tokens": 0.01
    },
    "gpt-4o-mini": {
      "input_per_1k_tokens": 0.00015,
      "output_per_1k_tokens": 0.0006
    },
    "claude-opus-4-6": {
      "input_per_1k_tokens": 0.015,
      "output_per_1k_tokens": 0.075
    },
    "claude-sonnet-4-6": {
      "input_per_1k_tokens": 0.003,
      "output_per_1k_tokens": 0.015
    },
    "llama4-scout": {
      "input_per_1k_tokens": 0.0,
      "output_per_1k_tokens": 0.0,
      "note": "local model via Ollama"
    },
    "qwen3:14b": {
      "input_per_1k_tokens": 0.0,
      "output_per_1k_tokens": 0.0,
      "note": "local model via Ollama"
    }
  }
}
```

Cost calculation: `cost = (prompt_tokens / 1000 * input_price) + (completion_tokens / 1000 * output_price)`
If model not in pricing.json → cost = null (do not assume zero for cloud models).

---

## 13. Phase Build Order

Build in this exact sequence. Do not skip ahead. Each phase must pass all tests before moving on.

### Phase 0 — Repo Setup (Do First)

1. Create the full directory tree from Section 3
2. Create all `__init__.py` files
3. Create `pyproject.toml` files with correct dependencies
4. Create `.github/workflows/ci.yml` that runs `ruff`, `mypy`, `pytest` on every PR
5. Create `README.md` skeleton with badges, installation, and 30-second quickstart
6. Create `LICENSE` file (MIT)
7. Create `CONTRIBUTING.md`
8. Create `docker-compose.yml` from Section 9
9. Create `.gitignore` for Python + Node
10. Verify `docker compose build` succeeds (even with empty apps)

**Dependencies for SDK `pyproject.toml`:**
```toml
[project]
name = "agenttrace"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
    "anyio>=4.0",
]

[project.optional-dependencies]
langchain = ["langchain>=0.3"]
langgraph = ["langgraph>=0.2"]
crewai = ["crewai>=0.80"]
autogen = ["pyautogen>=0.4"]
drift = ["sentence-transformers>=3.0", "scipy>=1.13", "numpy>=2.0", "scikit-learn>=1.5"]
all = ["agenttrace[langchain,langgraph,crewai,autogen,drift]"]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "ruff", "mypy", "httpx"]
```

**Dependencies for Collector `pyproject.toml`:**
```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.20",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
]
```

### Phase 1 — SDK Core

Build in this order:
1. `models.py` — `SpanEvent`, `BatchSpanRequest`, `TraceContext`
2. `context.py` — `contextvars.ContextVar` for async trace propagation
3. `queue.py` — `asyncio.Queue`, batch flusher coroutine
4. `client.py` — `httpx.AsyncClient`, `send_batch()`, local SQLite fallback buffer
5. `tracer.py` — `Tracer` singleton class with `init()`, `span()`, `trace_agent()`
6. `decorators.py` — `@trace_agent` wraps sync and async functions
7. `pricing.py` — load `pricing.json`, `estimate_cost(model, prompt_tokens, completion_tokens)`
8. `__init__.py` — export `tracer`, `Tracer`
9. Write tests for all above
10. `integrations/langchain.py` — `AgentTraceCallback(BaseCallbackHandler)`
11. `integrations/langgraph.py` — StateGraph middleware
12. Write integration tests

### Phase 2 — Collector

Build in this order:
1. `database.py` — async engine factory, session dependency
2. `models.py` — SQLAlchemy ORM models from Section 4
3. `schemas.py` — Pydantic response schemas
4. `routes/health.py` — `GET /api/v1/health`
5. `routes/spans.py` — `POST /api/v1/spans` (bulk insert, auto-create Trace record)
6. `routes/traces.py` — list + detail endpoints
7. `routes/stats.py` — aggregate queries
8. `main.py` — app factory from Section 10
9. Alembic migration for initial schema
10. `Dockerfile` — slim Python image
11. Write route tests using `httpx.AsyncClient` test client

### Phase 3 — Drift Detector

Build in this order:
1. Install `sentence-transformers` in drift-detector container
2. `baseline.py` — `BaselineBuilder.build()` fetches spans from Collector API
3. `comparator.py` — `DriftComparator.compare()` from Section 7
4. `alerter.py` — POST to webhook URLs, send SMTP email
5. `main.py` — loop: every `CHECK_INTERVAL_SECONDS`, run comparator for each known agent
6. Write unit tests with mock baselines and intentionally drifted span sets

### Phase 4 — Dashboard

Build in this order:
1. `vite.config.ts` + `tsconfig.json` + `package.json` with correct deps
2. `api/client.ts` — typed API client with all endpoints
3. `types/index.ts` — TypeScript interfaces matching backend schemas
4. `hooks/useTraces.ts`, `hooks/useDrift.ts`, `hooks/useStats.ts` — React Query hooks
5. `store/app.ts` — Zustand store
6. `pages/TraceList.tsx` — table + filters
7. `components/GanttTimeline.tsx` — D3.js Gantt (most complex, build carefully)
8. `components/SpanInspector.tsx` — tabbed JSON viewer
9. `pages/TraceDetail.tsx` — combines Gantt + SpanInspector
10. `pages/CostAnalytics.tsx` + `components/CostBreakdown.tsx`
11. `components/DriftChart.tsx` — D3.js line chart
12. `pages/DriftMonitor.tsx`
13. `pages/Settings.tsx`
14. `Dockerfile` — multi-stage Node.js build + Nginx serve

### Phase 5 — Remaining Integrations

- `integrations/crewai.py`
- `integrations/autogen.py`
- `integrations/openai_sdk.py`
- `integrations/ollama.py`
- One example script per integration in `sdk/examples/`
- One doc page per integration in `docs/docs/integrations/`

### Phase 6 — Docs + PyPI

1. `mkdocs.yml` with Material theme, dark mode
2. Write all doc pages listed in directory structure
3. Auto-generate API reference from FastAPI OpenAPI spec
4. GitHub Actions: publish to PyPI on version tag push
5. GitHub Actions: deploy docs to GitHub Pages

---

## 14. README.md Template (Critical — This Gets People to Star)

The README must follow this exact structure:

```markdown
<div align="center">
  <h1>AgentTrace</h1>
  <p>Open-source observability for multi-agent AI systems</p>
  
  <!-- badges -->
  ![PyPI](https://img.shields.io/pypi/v/agenttrace)
  ![License](https://img.shields.io/badge/license-MIT-blue)
  ![Tests](https://github.com/agenttrace/agenttrace/actions/workflows/ci.yml/badge.svg)
</div>

## The Problem

89% of developers think they have agent observability.
Only 62% actually do.

When your agent breaks in production, can you answer:
- Which LLM call failed?
- What was the exact prompt that caused it?
- Which tool executed and what did it return?
- How much did that trace cost?
- Did your agent silently change behavior when OpenAI updated their model?

AgentTrace answers all of these.

## Quickstart (2 minutes)

\`\`\`bash
# Start AgentTrace
docker compose up -d

# Install the SDK
pip install agenttrace

# Trace your agent
\`\`\`

\`\`\`python
from agenttrace import tracer
from agenttrace.integrations.langchain import AgentTraceCallback

tracer.init(collector_url="http://localhost:8000")
callback = AgentTraceCallback(agent_name="my_agent")

# Add callback to your existing LangChain code — nothing else changes
chain = your_existing_chain.with_config(callbacks=[callback])
result = chain.invoke({"input": "your query"})
\`\`\`

# Open dashboard
open http://localhost:3000

## Features

- **Full trace visibility** — every LLM call, tool execution, and sub-agent message
- **Behavioral drift detection** — alerts when your agent changes behavior (unique)
- **Cost tracking** — token spend per trace, per agent, per model
- **Latency profiling** — Gantt timeline shows exactly where time is spent
- **Self-hosted** — your data never leaves your machine
- **Zero config** — one docker compose up, two lines of Python

## Framework Support

| Framework | Status |
|---|---|
| LangChain | ✅ Supported |
| LangGraph | ✅ Supported |
| CrewAI | ✅ Supported |
| AutoGen | ✅ Supported |
| Ollama (local LLMs) | ✅ Supported |
| OpenAI Agents SDK | ✅ Supported |
| Custom agents | ✅ Manual span API |
```

---

## 15. GitHub Issues to Create on Launch Day

Create these 10 issues immediately when the repo goes public. They signal an active project and give the community things to contribute.

1. `[Integration] Add Mistral API support` — label: `good first issue`, `integration`
2. `[Feature] Export traces to JSON/CSV` — label: `good first issue`, `enhancement`
3. `[Dashboard] Add dark mode` — label: `good first issue`, `dashboard`
4. `[Feature] Prometheus metrics endpoint` — label: `enhancement`
5. `[Docs] Write tutorial: tracing a CrewAI research pipeline` — label: `good first issue`, `documentation`
6. `[Integration] Add LlamaIndex support` — label: `integration`
7. `[Dashboard] Add keyboard shortcuts` — label: `good first issue`, `dashboard`
8. `[Feature] Add trace search by prompt text` — label: `enhancement`
9. `[Infra] PostgreSQL + TimescaleDB production setup guide` — label: `documentation`
10. `[Feature] Add OpenTelemetry export (OTLP)` — label: `enhancement`

---

## 16. What NOT to Do

- Do NOT add cloud/SaaS features — keep it 100% self-hosted
- Do NOT add authentication in v0.1 — keep setup frictionless (add in v0.2)
- Do NOT use `threading` anywhere — everything is async
- Do NOT make the SDK import heavy — keep base install < 5 dependencies
- Do NOT use any paid APIs for AgentTrace itself to function
- Do NOT make Docker required to use the SDK — it must work standalone
- Do NOT store raw prompts if they contain PII by default — add a `sanitize=True` option

---

## 17. Session Instructions for Claude Code

When you start a new Claude Code session with this file:

1. Read this entire file first
2. Ask which Phase to work on if not specified
3. Before writing any code, state which files you will create/modify
4. Write complete files — no `# ... rest of code ...` shortcuts
5. After each Phase, run `pytest` and fix all failures before declaring done
6. After Phase 2, run `docker compose up` and verify the full stack connects
7. Commit after each working phase with a conventional commit message

**Current status:** Not started. Begin with Phase 0.
```
