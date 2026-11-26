/**
 * useValidations - Query validations using TanStack Query
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { ValidationListResponse, PaginationParams } from '../types/api';

export function useValidations(params?: Partial<PaginationParams>) {
  return useQuery<ValidationListResponse>({
    queryKey: ['validations', params],
    queryFn: () => apiClient.getValidations(params),
  });
}
