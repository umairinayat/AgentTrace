/** Typed API client for the AgentTrace Collector. */

import type {
  DriftAlertResponse,
  DriftBaselineResponse,
  PaginatedTraces,
  StatsResponse,
  TimelineData,
  TraceDetailResponse,
  TraceFilters,
} from '../types';

const BASE_URL = import.meta.env.VITE_COLLECTOR_URL || '';

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  // Traces
  getTraces(filters: TraceFilters): Promise<PaginatedTraces> {
    const params = new URLSearchParams();
    params.set('page', String(filters.page));
    params.set('page_size', String(filters.page_size));
    params.set('sort_by', filters.sort_by);
    params.set('sort_order', filters.sort_order);
    if (filters.agent_name) params.set('agent_name', filters.agent_name);
    if (filters.status) params.set('status', filters.status);
    return fetchJson(`/api/v1/traces?${params}`);
  },

  getTrace(traceId: string): Promise<TraceDetailResponse> {
    return fetchJson(`/api/v1/traces/${traceId}`);
  },

  getTimeline(traceId: string): Promise<TimelineData> {
    return fetchJson(`/api/v1/traces/${traceId}/timeline`);
  },

  // Stats
  getStats(): Promise<StatsResponse> {
    return fetchJson('/api/v1/stats');
  },

  // Drift
  getDriftAlerts(agentName?: string): Promise<DriftAlertResponse[]> {
    const params = agentName ? `?agent_name=${agentName}` : '';
    return fetchJson(`/api/v1/drift/alerts${params}`);
  },

  getDriftBaseline(agentName: string): Promise<DriftBaselineResponse> {
    return fetchJson(`/api/v1/drift/baseline/${agentName}`);
  },

  rebuildBaseline(agentName: string): Promise<{ status: string }> {
    return postJson(`/api/v1/drift/baseline/${agentName}/rebuild`, {});
  },

  // Health
  healthCheck(): Promise<{ status: string }> {
    return fetchJson('/api/v1/health');
  },
};
