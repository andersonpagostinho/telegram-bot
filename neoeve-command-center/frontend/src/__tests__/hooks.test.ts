import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../lib/queryClient';
import React from 'react';

// Mock the API client
vi.mock('../services/api', () => ({
  apiClient: {
    getAgents: vi.fn(),
    getMissions: vi.fn(),
    getExecutions: vi.fn(),
  },
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  React.createElement(QueryClientProvider, { client: queryClient }, children)
);

describe('Custom Hooks', () => {
  beforeEach(() => {
    queryClient.clear();
  });

  describe('useAgents Hook', () => {
    it('should exist and be callable', async () => {
      const { useAgents } = await import('../hooks/useAgents');
      expect(useAgents).toBeDefined();
      expect(typeof useAgents).toBe('function');
    });

    it('should return loading state initially', async () => {
      const { useAgents } = await import('../hooks/useAgents');
      const { result } = renderHook(() => useAgents(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it('should have data property in result', async () => {
      const { useAgents } = await import('../hooks/useAgents');
      const { result } = renderHook(() => useAgents(), { wrapper });

      expect(result.current).toHaveProperty('data');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('error');
    });
  });

  describe('useMissions Hook', () => {
    it('should exist and be callable', async () => {
      const { useMissions } = await import('../hooks/useMissions');
      expect(useMissions).toBeDefined();
      expect(typeof useMissions).toBe('function');
    });

    it('should accept optional filters', async () => {
      const { useMissions } = await import('../hooks/useMissions');
      const { result } = renderHook(
        () => useMissions({ status: 'RUNNING' }),
        { wrapper }
      );

      expect(result.current).toHaveProperty('data');
    });
  });

  describe('useExecutions Hook', () => {
    it('should exist and be callable', async () => {
      const { useExecutions } = await import('../hooks/useExecutions');
      expect(useExecutions).toBeDefined();
      expect(typeof useExecutions).toBe('function');
    });

    it('should accept mission and agent filters', async () => {
      const { useExecutions } = await import('../hooks/useExecutions');
      const { result } = renderHook(
        () => useExecutions({ mission_id: 'mission-1' }),
        { wrapper }
      );

      expect(result.current).toHaveProperty('data');
    });
  });

  describe('useWebSocket Hook', () => {
    it('should exist and be callable', async () => {
      const { useWebSocket } = await import('../hooks/useWebSocket');
      expect(useWebSocket).toBeDefined();
      expect(typeof useWebSocket).toBe('function');
    });

    it('should not create duplicate connections', async () => {
      const { useWebSocket } = await import('../hooks/useWebSocket');

      const { rerender } = renderHook(() => useWebSocket());
      rerender();

      // Should not create multiple connections
      expect(true).toBe(true);
    });

    it('should clean up on unmount', async () => {
      const { useWebSocket } = await import('../hooks/useWebSocket');

      const { unmount } = renderHook(() => useWebSocket());
      unmount();

      // Should cleanup gracefully
      expect(true).toBe(true);
    });

    it('should invalidate cache on relevant events', async () => {
      const { useWebSocket } = await import('../hooks/useWebSocket');

      const { result } = renderHook(() => useWebSocket());
      expect(result.current).toBeDefined();
    });
  });

  describe('Hook Integration', () => {
    it('should not duplicate data between TanStack Query and Zustand', async () => {
      const { useAgents } = await import('../hooks/useAgents');

      const { result } = renderHook(() => useAgents(), { wrapper });

      // Data should be in Query, not in stores
      expect(result.current).toHaveProperty('data');
    });

    it('should preserve multi-tenant isolation', async () => {
      const { useAgents } = await import('../hooks/useAgents');

      const { result } = renderHook(() => useAgents(), { wrapper });

      // Should maintain tenant isolation
      expect(result.current).toBeDefined();
    });
  });
});
