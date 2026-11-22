/**
 * useMissions - Query missions using TanStack Query with filtering
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { MissionListResponse, PaginationParams } from '../types/api';

interface MissionFilters extends Partial<PaginationParams> {
  status?: string;
  days?: number;
}

export function useMissions(params?: MissionFilters) {
  return useQuery<MissionListResponse>({
    queryKey: ['missions', params],
    queryFn: () => apiClient.getMissions(params),
  });
}
