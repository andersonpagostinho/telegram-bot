/**
 * useExecutions - Query executions using TanStack Query with filtering
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { ExecutionListResponse, PaginationParams } from '../types/api';

interface ExecutionFilters extends Partial<PaginationParams> {
  mission_id?: string;
  agent_id?: string;
}

export function useExecutions(params?: ExecutionFilters) {
  return useQuery<ExecutionListResponse>({
    queryKey: ['executions', params],
    queryFn: () => apiClient.getExecutions(params),
  });
}
