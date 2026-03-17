/** Shared TypeScript types matching backend schemas. */

export interface SpanResponse {
  id: string;
  trace_id: string;
  parent_span_id: string | null;
  agent_name: string;
  event_type: string;
  started_at: string;
  ended_at: string | null;
  latency_ms: number | null;
  model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  error: string | null;
  metadata: Record<string, unknown> | null;
}

export interface TraceResponse {
  id: string;
  name: string;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  total_tokens: number | null;
  total_cost_usd: number | null;
  status: string;
  span_count: number;
}

export interface TraceDetailResponse {
  id: string;
  name: string;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  total_tokens: number | null;
  total_cost_usd: number | null;
  status: string;
  metadata: Record<string, unknown> | null;
  spans: SpanResponse[];
}

export interface TimelineSpan {
  span_id: string;
  parent_span_id: string | null;
  agent_name: string;
  event_type: string;
  start_offset_ms: number;
  duration_ms: number;
  model: string | null;
  total_tokens: number | null;
  cost_usd: number | null;
  error: string | null;
}

export interface TimelineData {
  trace_id: string;
  trace_start: string;
  total_duration_ms: number;
  spans: TimelineSpan[];
}

export interface PaginatedTraces {
  items: TraceResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface StatsResponse {
  total_traces: number;
  total_spans: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  avg_cost_per_trace: number;
  traces_by_status: Record<string, number>;
  top_agents: { name: string; total_cost: number; span_count: number }[];
  top_models: { name: string; total_tokens: number; total_cost: number; call_count: number }[];
}

export interface DriftAlertResponse {
  id: number;
  agent_name: string;
  detected_at: string;
  alert_type: string;
  severity: string;
  score: number | null;
  threshold: number | null;
  description: string | null;
  resolved: number;
}

export interface DriftBaselineResponse {
  id: number;
  agent_name: string;
  built_at: string;
  n_samples: number;
  avg_response_length: number | null;
  avg_latency_ms: number | null;
  avg_token_count: number | null;
}

export interface TraceFilters {
  page: number;
  page_size: number;
  agent_name?: string;
  status?: string;
  sort_by: string;
  sort_order: string;
}
