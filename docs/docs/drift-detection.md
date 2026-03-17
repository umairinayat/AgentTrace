# Behavioral Drift Detection

AgentTrace's killer feature: automatically detect when your agent's behavior changes without any code changes on your end.

## Why Drift Detection?

When a model provider (OpenAI, Anthropic, Google) silently updates their backend model, your agent's behavior changes. This can cause:

- Different response styles or lengths
- Changed reasoning patterns
- New failure modes
- Cost fluctuations

AgentTrace detects these changes automatically.

## How It Works

### 1. Build a Baseline

The drift detector collects the last N completed LLM call spans for an agent and computes:

- **Embedding centroid** — Average semantic embedding of responses using `all-MiniLM-L6-v2`
- **Response length distribution** — Statistical distribution of response lengths
- **Token count averages** — Mean token usage
- **Tool call patterns** — Frequency of different tool calls

### 2. Compare Against Baseline

Every 5 minutes, the detector runs four checks:

| Check | Method | Default Threshold |
|-------|--------|-------------------|
| Semantic drift | Cosine distance from centroid | 0.15 |
| Distribution shift | Kolmogorov-Smirnov test | p < 0.05 |
| Token anomaly | Percentage change | > 20% |
| Tool pattern change | Frequency shift | > 0.10 |

### 3. Alert

When drift is detected, alerts are:

- Shown in the dashboard's Drift Monitor page
- Sent via configured webhooks (Slack, Discord, custom)
- Sent via email (if SMTP is configured)

## Dashboard

The Drift Monitor page shows:

- One card per agent with drift score over time
- Red threshold line at 0.15
- Active alert count
- "Rebuild Baseline" button to reset

## Configuration

Configure thresholds in the drift detector service:

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CHECK_INTERVAL_SECONDS` | 300 | How often to check for drift |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Sentence transformer model |
| `SEMANTIC_THRESHOLD` | 0.15 | Cosine distance threshold |
| `KS_PVALUE_THRESHOLD` | 0.05 | KS test p-value threshold |
| `TOKEN_CHANGE_THRESHOLD` | 0.20 | Token % change threshold |

## Technical Details

The drift detector uses:

- **sentence-transformers** (`all-MiniLM-L6-v2`) — 80MB model, runs on CPU, no API key needed
- **scipy** — Kolmogorov-Smirnov two-sample test
- **numpy** — Cosine similarity, centroid computation
- **scikit-learn** — Cosine similarity utility
