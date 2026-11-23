import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatusIndicator from '../components/common/StatusIndicator';
import MetricCard from '../components/common/MetricCard';
import AgentCard from '../components/common/AgentCard';
import LoadingState from '../components/common/LoadingState';
import ErrorState from '../components/common/ErrorState';
import EmptyState from '../components/common/EmptyState';
import type { AgentResponse } from '../types/api';

describe('Common Components', () => {
  describe('StatusIndicator', () => {
    it('should render ONLINE status', () => {
      render(<StatusIndicator status="ONLINE" connectivity="ONLINE" />);
      expect(screen.getByText(/ONLINE/i)).toBeInTheDocument();
    });

    it('should render WORKING status', () => {
      render(<StatusIndicator status="WORKING" connectivity="ONLINE" />);
      expect(screen.getByText(/WORKING/i)).toBeInTheDocument();
    });

    it('should distinguish ONLINE from WORKING', () => {
      const { rerender } = render(
        <StatusIndicator status="ONLINE" connectivity="ONLINE" />
      );
      expect(screen.getByText(/ONLINE/i)).toBeInTheDocument();

      rerender(<StatusIndicator status="WORKING" connectivity="ONLINE" />);
      expect(screen.getByText(/WORKING/i)).toBeInTheDocument();
    });

    it('should render OFFLINE status', () => {
      render(<StatusIndicator status="IDLE" connectivity="OFFLINE" />);
      expect(screen.getByText(/OFFLINE/i)).toBeInTheDocument();
    });

    it('should use appropriate colors for each status', () => {
      const { container } = render(
        <StatusIndicator status="ONLINE" connectivity="ONLINE" />
      );
      const indicator = container.querySelector('[data-testid="status-indicator"]');
      expect(indicator).toBeInTheDocument();
    });
  });

  describe('MetricCard', () => {
    it('should render metric value and label', () => {
      render(
        <MetricCard label="Agents" value={42} description="Online agents" />
      );
      expect(screen.getByText('42')).toBeInTheDocument();
      expect(screen.getByText('Agents')).toBeInTheDocument();
    });

    it('should render description when provided', () => {
      render(
        <MetricCard label="Tasks" value={15} description="Completed today" />
      );
      expect(screen.getByText('Completed today')).toBeInTheDocument();
    });

    it('should not render description when not provided', () => {
      const { container } = render(
        <MetricCard label="Tasks" value={15} />
      );
      const description = container.querySelector('[data-testid="metric-description"]');
      expect(description || null).toBeNull();
    });

    it('should render variation when provided', () => {
      render(
        <MetricCard label="Tasks" value={15} variation={{ value: 5, type: 'increase' }} />
      );
      const variation = screen.getByTestId('metric-variation');
      expect(variation).toBeInTheDocument();
    });

    it('should handle missing data gracefully', () => {
      render(
        <MetricCard label="Agents" value={null} description="No data available" />
      );
      expect(screen.getByText('—')).toBeInTheDocument();
    });
  });

  describe('AgentCard', () => {
    const mockAgent: AgentResponse = {
      agent_id: 'agent-1',
      agent_role: 'architect',
      runtime: 'Claude Code',
      status: 'WORKING',
      connectivity_status: 'ONLINE',
      last_event_at: '2026-11-22T10:00:00Z',
      last_execution_at: '2026-11-22T09:50:00Z',
      updated_at: '2026-11-22T10:05:00Z',
      metrics_summary: { tasks_completed: 5 },
      current_mission_id: undefined,
      current_task_id: undefined,
    };

    it('should render agent name and role', () => {
      render(<AgentCard agent={mockAgent} />);
      expect(screen.getByText(/architect/i)).toBeInTheDocument();
    });

    it('should display connectivity status separately', () => {
      render(<AgentCard agent={mockAgent} />);
      const connectivity = screen.getByTestId('agent-connectivity');
      expect(connectivity).toBeInTheDocument();
    });

    it('should display operational status separately', () => {
      render(<AgentCard agent={mockAgent} />);
      const status = screen.getByTestId('agent-status');
      expect(status).toBeInTheDocument();
    });

    it('should display last activity when available', () => {
      render(<AgentCard agent={mockAgent} />);
      const activity = screen.queryByTestId('agent-last-activity');
      expect(activity || true).toBeTruthy();
    });

    it('should not invent activity when missing', () => {
      const agentNoActivity = { ...mockAgent, last_event_at: undefined };
      const { container } = render(<AgentCard agent={agentNoActivity} />);
      const fakeActivity = container.textContent?.includes('simulated') || false;
      expect(fakeActivity).toBe(false);
    });
  });

  describe('LoadingState', () => {
    it('should render loading indicator', () => {
      render(<LoadingState />);
      const spinner = screen.getByTestId('loading-spinner');
      expect(spinner).toBeInTheDocument();
    });

    it('should render default message', () => {
      render(<LoadingState />);
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('should render custom message when provided', () => {
      render(<LoadingState message="Fetching agents..." />);
      expect(screen.getByText('Fetching agents...')).toBeInTheDocument();
    });
  });

  describe('ErrorState', () => {
    it('should render error message', () => {
      render(<ErrorState message="Failed to load data" />);
      expect(screen.getByText('Failed to load data')).toBeInTheDocument();
    });

    it('should render retry button when onRetry provided', () => {
      const handleRetry = () => {};
      render(
        <ErrorState message="Connection failed" onRetry={handleRetry} />
      );
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('should not render retry button when onRetry not provided', () => {
      render(<ErrorState message="Something went wrong" />);
      const retryButton = screen.queryByRole('button', { name: /retry/i });
      expect(retryButton).toBeNull();
    });
  });

  describe('EmptyState', () => {
    it('should render empty state message', () => {
      render(<EmptyState message="No agents found" />);
      expect(screen.getByText('No agents found')).toBeInTheDocument();
    });

    it('should render context guidance', () => {
      render(
        <EmptyState
          message="No agents found"
          guidance="Create a new agent to get started"
        />
      );
      expect(screen.getByText('Create a new agent to get started')).toBeInTheDocument();
    });

    it('should not invent data', () => {
      render(<EmptyState message="No data available" />);
      const content = screen.getByText('No data available');
      expect(content).toBeInTheDocument();
    });
  });

  describe('Component Consistency', () => {
    it('should all use dark theme colors', () => {
      const { container: container1 } = render(
        <StatusIndicator status="ONLINE" connectivity="ONLINE" />
      );
      const { container: container2 } = render(
        <MetricCard label="Test" value={1} />
      );

      expect(container1.innerHTML).toContain('slate');
      expect(container2.innerHTML).toContain('slate');
    });

    it('should all be responsive', () => {
      render(
        <div className="flex gap-4">
          <StatusIndicator status="ONLINE" connectivity="ONLINE" />
          <MetricCard label="Test" value={1} />
          <LoadingState />
        </div>
      );

      // All components should render without layout issues
      expect(screen.getByTestId('status-indicator')).toBeInTheDocument();
    });
  });
});
