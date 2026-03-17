/** React Query hooks for drift detection data. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export function useDriftAlerts(agentName?: string) {
  return useQuery({
    queryKey: ['drift-alerts', agentName],
    queryFn: () => api.getDriftAlerts(agentName),
    refetchInterval: 30000,
  });
}

export function useDriftBaseline(agentName: string) {
  return useQuery({
    queryKey: ['drift-baseline', agentName],
    queryFn: () => api.getDriftBaseline(agentName),
    enabled: !!agentName,
  });
}

export function useRebuildBaseline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentName: string) => api.rebuildBaseline(agentName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drift-baseline'] });
    },
  });
}
