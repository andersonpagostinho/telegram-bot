import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../lib/queryClient';
import ActivityStream from '../pages/ActivityStream';

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => ({ isConnected: true }),
}));

vi.mock('../services/api', () => ({
  apiClient: {
    getEvents: vi.fn(),
  },
}));

const mockEvents = {
  events: [
    {
      event_id: 'evt-1',
      event_type: 'MISSION_UPDATED',
      sequence: 1,
      tenant_id: 'tenant-1',
      project_id: 'project-1',
      created_at: new Date().toISOString(),
      payload: { mission_id: 'mission-1', source_agent: 'architect' },
    },
  ],
  total: 1,
  cursor: null,
  has_more: false,
};

describe('ActivityStream', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page header', async () => {
    const { apiClient } = await import('../services/api');
    vi.mocked(apiClient.getEvents).mockResolvedValue(mockEvents);

    render(
      <QueryClientProvider client={queryClient}>
        <ActivityStream />
      </QueryClientProvider>
    );

    expect(screen.getByText('Activity Stream')).toBeInTheDocument();
  });

  it('shows loading state initially', async () => {
    const { apiClient } = await import('../services/api');
    vi.mocked(apiClient.getEvents).mockImplementation(() =>
      new Promise(() => {}) // Never resolves
    );

    render(
      <QueryClientProvider client={queryClient}>
        <ActivityStream />
      </QueryClientProvider>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders events from API', async () => {
    const { apiClient } = await import('../services/api');
    vi.mocked(apiClient.getEvents).mockResolvedValue(mockEvents);

    render(
      <QueryClientProvider client={queryClient}>
        <ActivityStream />
      </QueryClientProvider>
    );

    // Wait for async fetch
    await new Promise(r => setTimeout(r, 100));
    expect(screen.queryByText(/no events/i)).not.toBeInTheDocument();
  });

  it('shows empty state when no events', async () => {
    const { apiClient } = await import('../services/api');
    vi.mocked(apiClient.getEvents).mockResolvedValue({
      events: [],
      total: 0,
      has_more: false,
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ActivityStream />
      </QueryClientProvider>
    );

    await new Promise(r => setTimeout(r, 100));
    expect(screen.getByText(/no events available/i)).toBeInTheDocument();
  });

  it('shows WebSocket connection status', async () => {
    const { apiClient } = await import('../services/api');
    vi.mocked(apiClient.getEvents).mockResolvedValue(mockEvents);

    render(
      <QueryClientProvider client={queryClient}>
        <ActivityStream />
      </QueryClientProvider>
    );

    await new Promise(r => setTimeout(r, 100));
    expect(screen.getByText(/live updates enabled/i)).toBeInTheDocument();
  });

  it('shows error state on API failure', async () => {
    const { apiClient } = await import('../services/api');
    vi.mocked(apiClient.getEvents).mockRejectedValue(new Error('API Error'));

    render(
      <QueryClientProvider client={queryClient}>
        <ActivityStream />
      </QueryClientProvider>
    );

    await new Promise(r => setTimeout(r, 100));
    expect(screen.getByText(/failed to load events/i)).toBeInTheDocument();
  });
});
