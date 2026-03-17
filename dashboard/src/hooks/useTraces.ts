/** React Query hooks for trace data. */

import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { TraceFilters } from '../types';

export function useTraces(filters: TraceFilters) {
  return useQuery({
    queryKey: ['traces', filters],
    queryFn: () => api.getTraces(filters),
    refetchInterval: 5000,
  });
}

export function useTrace(traceId: string) {
  return useQuery({
    queryKey: ['trace', traceId],
    queryFn: () => api.getTrace(traceId),
    enabled: !!traceId,
  });
}

export function useTimeline(traceId: string) {
  return useQuery({
    queryKey: ['timeline', traceId],
    queryFn: () => api.getTimeline(traceId),
    enabled: !!traceId,
  });
}
