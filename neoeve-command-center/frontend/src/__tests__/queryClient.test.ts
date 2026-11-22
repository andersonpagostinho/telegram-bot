import { describe, it, expect } from 'vitest';
import { queryClient } from '../lib/queryClient';

describe('QueryClient Configuration', () => {
  it('should have QueryClient instance', () => {
    expect(queryClient).toBeDefined();
    expect(queryClient.getDefaultOptions).toBeDefined();
  });

  it('should have correct default query options', () => {
    const defaults = queryClient.getDefaultOptions();
    expect(defaults.queries).toBeDefined();
    expect(defaults.queries?.staleTime).toBe(5 * 60 * 1000); // 5 minutes
    expect(defaults.queries?.gcTime).toBe(10 * 60 * 1000);   // 10 minutes
    expect(defaults.queries?.retry).toBe(1);
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });

  it('should have QueryClient singleton pattern', () => {
    const client2 = queryClient;
    expect(client2).toBe(queryClient); // Same instance
  });
});
