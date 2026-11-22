/**
 * useAgents - Query agents using TanStack Query
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { AgentListResponse, PaginationParams } from '../types/api';

export function useAgents(params?: Partial<PaginationParams>) {
  return useQuery<AgentListResponse>({
    queryKey: ['agents', params],
    queryFn: () => apiClient.getAgents(params),
  });
}
