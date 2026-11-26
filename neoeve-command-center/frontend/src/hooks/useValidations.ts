/**
 * useValidations - Query validations using TanStack Query
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { PaginationParams } from '../types/api';

interface Validation {
  validation_id: string;
  execution_id?: string;
  mission_id?: string;
  status: string;
  created_at?: string;
  completed_at?: string;
  scope?: string;
  result?: string;
  tests_executed?: number;
  tests_passed?: number;
  tests_failed?: number;
}

interface ValidationListResponse {
  validations: Validation[];
  total: number;
}

export function useValidations(params?: Partial<PaginationParams>) {
  return useQuery<ValidationListResponse>({
    queryKey: ['validations', params],
    queryFn: async () => {
      try {
        const response = await fetch('/api/validations');
        if (!response.ok) throw new Error('Failed to fetch validations');
        return response.json();
      } catch (error) {
        return { validations: [], total: 0 };
      }
    },
  });
}
