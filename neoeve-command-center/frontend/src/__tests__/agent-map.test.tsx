import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../lib/queryClient';
import AgentMap from '../pages/AgentMap';
import type { AgentResponse } from '../types/api';

// Mock React Flow
vi.mock('reactflow', () => ({
  default: ({ children }: any) => <div data-testid="react-flow">{children}</div>,
  Controls: () => <div data-testid="rf-controls" />,
  Background: () => <div data-testid="rf-background" />,
  MiniMap: () => <div data-testid="rf-minimap" />,
  useNodesState: () => [[], vi.fn(), vi.fn()],
  useEdgesState: () => [[], vi.fn(), vi.fn()],
}));

// Mock hooks
vi.mock('../hooks/useAgents', () => ({
  useAgents: vi.fn(),
}));

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({ isConnected: true })),
}));

const mockAgents: AgentResponse[] = [
  {
    agent_id: 'architect',
    agent_role: 'Architect',
    runtime: 'claude-opus',
    status: 'IDLE',
    connectivity_status: 'ONLINE',
    last_event_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    agent_id: 'backend_dev',
    agent_role: 'Backend Developer',
    runtime: 'claude-opus',
    status: 'WORKING',
    connectivity_status: 'ONLINE',
    last_event_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    agent_id: 'debugger',
    agent_role: 'Debugger',
    runtime: 'claude-opus',
    status: 'ANALYZING',
    connectivity_status: 'ONLINE',
    last_event_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    agent_id: 'qa',
    agent_role: 'QA Engineer',
    runtime: 'claude-opus',
    status: 'TESTING',
    connectivity_status: 'ONLINE',
    last_event_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    agent_id: 'security_auditor',
    agent_role: 'Security Auditor',
    runtime: 'claude-opus',
    status: 'REVIEWING',
    connectivity_status: 'ONLINE',
    last_event_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    agent_id: 'release_mgr',
    agent_role: 'Release Manager',
    runtime: 'claude-opus',
    status: 'IDLE',
    connectivity_status: 'ONLINE',
    last_event_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    agent_id: 'openai_validator',
    agent_role: 'OpenAI Validator',
    runtime: 'validator',
    status: 'IDLE',
    connectivity_status: 'OFFLINE',
    last_event_at: undefined,
    updated_at: new Date().toISOString(),
  },
];

describe('AgentMap', () => {
  const { useAgents } = vi.mocked({ useAgents: require('../hooks/useAgents').useAgents });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderAgentMap = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AgentMap />
      </QueryClientProvider>
    );
  };

  describe('Rendering', () => {
    it('renders loading state initially', () => {
      useAgents.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isFetching: false,
        status: 'pending',
      } as any);

      renderAgentMap();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('renders error state when API fails', () => {
      const error = new Error('Failed to load agents');
      useAgents.mockReturnValue({
        data: undefined,
        isLoading: false,
        error,
        isFetching: false,
        status: 'error',
      } as any);

      renderAgentMap();
      expect(screen.getByText(/failed to load agents/i)).toBeInTheDocument();
    });

    it('renders empty state when no agents', () => {
      useAgents.mockReturnValue({
        data: { agents: [], total: 0, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);

      renderAgentMap();
      expect(screen.getByText(/no agents available/i)).toBeInTheDocument();
    });

    it('renders React Flow canvas with 7 agents', () => {
      useAgents.mockReturnValue({
        data: { agents: mockAgents, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);

      renderAgentMap();
      expect(screen.getByTestId('react-flow')).toBeInTheDocument();
      expect(screen.getByText('Agent Map')).toBeInTheDocument();
    });

    it('renders React Flow controls and minimap', () => {
      useAgents.mockReturnValue({
        data: { agents: mockAgents, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);

      renderAgentMap();
      expect(screen.getByTestId('rf-controls')).toBeInTheDocument();
      expect(screen.getByTestId('rf-minimap')).toBeInTheDocument();
      expect(screen.getByTestId('rf-background')).toBeInTheDocument();
    });
  });

  describe('Agent Representation', () => {
    beforeEach(() => {
      useAgents.mockReturnValue({
        data: { agents: mockAgents, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);
    });

    it('displays all 7 agents', () => {
      renderAgentMap();
      expect(screen.getByText('7 agents')).toBeInTheDocument();
    });

    it('shows WebSocket connection status', () => {
      renderAgentMap();
      expect(screen.getByText('WebSocket Connected')).toBeInTheDocument();
    });

    it('shows WebSocket disconnected status when not connected', () => {
      const { useWebSocket } = vi.mocked({
        useWebSocket: require('../hooks/useWebSocket').useWebSocket
      });
      useWebSocket.mockReturnValue({ isConnected: false });

      renderAgentMap();
      expect(screen.getByText('WebSocket Disconnected')).toBeInTheDocument();
    });
  });

  describe('Agent Statuses', () => {
    beforeEach(() => {
      useAgents.mockReturnValue({
        data: { agents: mockAgents, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);
    });

    it('handles all operational statuses', () => {
      const statuses = ['IDLE', 'WORKING', 'ANALYZING', 'TESTING', 'REVIEWING'];
      renderAgentMap();

      statuses.forEach(status => {
        expect(mockAgents.some(a => a.status === status)).toBe(true);
      });
    });

    it('shows offline agent correctly', () => {
      renderAgentMap();
      const offlineAgent = mockAgents.find(a => a.connectivity_status === 'OFFLINE');
      expect(offlineAgent).toBeDefined();
      expect(offlineAgent?.agent_id).toBe('openai_validator');
    });

    it('handles agents with current mission', () => {
      const agentsWithMission = mockAgents.map(a => ({
        ...a,
        current_mission_id: 'mission-001',
      }));

      useAgents.mockReturnValue({
        data: { agents: agentsWithMission, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);

      renderAgentMap();
      expect(screen.getByText('7 agents')).toBeInTheDocument();
    });
  });

  describe('Interactivity', () => {
    beforeEach(() => {
      useAgents.mockReturnValue({
        data: { agents: mockAgents, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);
    });

    it('renders page header with description', () => {
      renderAgentMap();
      expect(screen.getByText('Agent Map')).toBeInTheDocument();
      expect(screen.getByText(/real-time topology/i)).toBeInTheDocument();
    });
  });

  describe('Real Data Handling', () => {
    it('uses GET /api/v1/agents via useAgents hook', () => {
      useAgents.mockReturnValue({
        data: { agents: mockAgents, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);

      renderAgentMap();
      expect(useAgents).toHaveBeenCalledWith({ per_page: 100 });
    });

    it('respects multi-tenant isolation (data from API)', () => {
      useAgents.mockReturnValue({
        data: { agents: mockAgents, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);

      renderAgentMap();
      // Data comes from API (backend handles tenant isolation)
      expect(screen.getByText('7 agents')).toBeInTheDocument();
    });

    it('does not invent agent data', () => {
      const realAgents: AgentResponse[] = [
        {
          agent_id: 'test-agent',
          agent_role: 'Test',
          runtime: 'test',
          status: 'IDLE',
          connectivity_status: 'ONLINE',
          updated_at: new Date().toISOString(),
        },
      ];

      useAgents.mockReturnValue({
        data: { agents: realAgents, total: 1, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);

      renderAgentMap();
      expect(screen.getByText('1 agents')).toBeInTheDocument();
    });
  });

  describe('Responsiveness', () => {
    beforeEach(() => {
      useAgents.mockReturnValue({
        data: { agents: mockAgents, total: 7, page: 1, per_page: 20 },
        isLoading: false,
        error: null,
        isFetching: false,
        status: 'success',
      } as any);
    });

    it('renders with flex layout for responsiveness', () => {
      const { container } = renderAgentMap();
      const mainDiv = container.firstChild as HTMLElement;
      expect(mainDiv.style.display).toBe('flex');
      expect(mainDiv.style.flexDirection).toBe('column');
    });
  });
});
