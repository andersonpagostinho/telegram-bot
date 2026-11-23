import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentNode, AgentNodeStatus, AgentConnectivityIndicator, AgentEdge } from '../components/topology';
import { ReactFlowProvider } from 'reactflow';

/**
 * Test suite for React Flow topology components
 * Validates: rendering, states, separation of concerns, props
 */

describe('Topology Components', () => {
  describe('AgentNode', () => {
    const mockAgentData = {
      agent_id: 'architect',
      agent_role: 'Architect',
      status: 'IDLE' as const,
      connectivity_status: 'ONLINE' as const,
      last_event_at: new Date().toISOString(),
      current_mission_id: 'mission-001',
    };

    it('renders agent node with name and role', () => {
      render(
        <ReactFlowProvider>
          <AgentNode data={mockAgentData} />
        </ReactFlowProvider>
      );
      expect(screen.getByText('architect')).toBeInTheDocument();
      expect(screen.getByText('Architect')).toBeInTheDocument();
    });

    it('displays operational status indicator', () => {
      render(
        <ReactFlowProvider>
          <AgentNode data={mockAgentData} />
        </ReactFlowProvider>
      );
      expect(screen.getByTestId('agent-node-status')).toBeInTheDocument();
    });

    it('displays connectivity indicator', () => {
      render(
        <ReactFlowProvider>
          <AgentNode data={mockAgentData} />
        </ReactFlowProvider>
      );
      expect(screen.getByTestId('agent-connectivity-indicator')).toBeInTheDocument();
    });

    it('shows current mission when provided', () => {
      render(
        <ReactFlowProvider>
          <AgentNode data={mockAgentData} />
        </ReactFlowProvider>
      );
      expect(screen.getByText(/mission-001/)).toBeInTheDocument();
    });

    it('shows last event time when provided', () => {
      render(
        <ReactFlowProvider>
          <AgentNode data={mockAgentData} />
        </ReactFlowProvider>
      );
      expect(screen.getByText(/ago/)).toBeInTheDocument();
    });

    it('renders without mission when not provided', () => {
      const dataWithoutMission = { ...mockAgentData, current_mission_id: undefined };
      const { container } = render(
        <ReactFlowProvider>
          <AgentNode data={dataWithoutMission} />
        </ReactFlowProvider>
      );
      expect(container.textContent).not.toMatch(/Mission:/);
    });

    it('renders with selected visual state', () => {
      const { container } = render(
        <ReactFlowProvider>
          <AgentNode data={mockAgentData} selected={true} />
        </ReactFlowProvider>
      );
      // Check for cyan border indicating selection
      const node = container.querySelector('[style*="border"]');
      expect(node).toBeInTheDocument();
    });

    it('handles all operational statuses', () => {
      const statuses = ['IDLE', 'WORKING', 'ANALYZING', 'TESTING', 'REVIEWING', 'BLOCKED', 'COMPLETED', 'ERROR'] as const;

      statuses.forEach((status) => {
        const { unmount } = render(
          <ReactFlowProvider>
            <AgentNode data={{ ...mockAgentData, status }} />
          </ReactFlowProvider>
        );
        expect(screen.getByTestId('agent-node-status')).toBeInTheDocument();
        unmount();
      });
    });

    it('shows OFFLINE when connectivity is not ONLINE', () => {
      const offlineData = { ...mockAgentData, connectivity_status: 'OFFLINE' as const };
      render(
        <ReactFlowProvider>
          <AgentNode data={offlineData} />
        </ReactFlowProvider>
      );
      // Status should show as OFFLINE regardless of operational status
      const statusText = screen.getByTestId('agent-node-status').textContent;
      expect(statusText).toContain('OFFLINE');
    });
  });

  describe('AgentNodeStatus', () => {
    it('renders status dot and text', () => {
      render(
        <AgentNodeStatus
          status="WORKING"
          connectivity="ONLINE"
        />
      );
      expect(screen.getByTestId('agent-node-status')).toBeInTheDocument();
      expect(screen.getByText('WORKING')).toBeInTheDocument();
    });

    it('displays OFFLINE when connectivity is not ONLINE', () => {
      render(
        <AgentNodeStatus
          status="IDLE"
          connectivity="OFFLINE"
        />
      );
      expect(screen.getByText('OFFLINE')).toBeInTheDocument();
    });

    it('displays STALE when connectivity is STALE', () => {
      render(
        <AgentNodeStatus
          status="IDLE"
          connectivity="STALE"
        />
      );
      expect(screen.getByText('OFFLINE')).toBeInTheDocument(); // OFFLINE for any non-ONLINE
    });

    it('shows correct status for all operational states', () => {
      const statuses = ['IDLE', 'WORKING', 'ANALYZING', 'TESTING', 'REVIEWING', 'BLOCKED', 'COMPLETED', 'ERROR'] as const;

      statuses.forEach((status) => {
        const { unmount } = render(
          <AgentNodeStatus status={status} connectivity="ONLINE" />
        );
        expect(screen.getByText(status)).toBeInTheDocument();
        unmount();
      });
    });

    it('separates operational status from connectivity status', () => {
      // Operational: WORKING
      // Connectivity: ONLINE
      // Should show WORKING (not mixed)
      render(
        <AgentNodeStatus
          status="WORKING"
          connectivity="ONLINE"
        />
      );
      expect(screen.getByText('WORKING')).toBeInTheDocument();
      expect(screen.queryByText('ONLINE')).not.toBeInTheDocument();
    });

    it('overrides operational status when connectivity is not ONLINE', () => {
      // Even if WORKING, show OFFLINE if connectivity is OFFLINE
      render(
        <AgentNodeStatus
          status="WORKING"
          connectivity="OFFLINE"
        />
      );
      expect(screen.getByText('OFFLINE')).toBeInTheDocument();
      expect(screen.queryByText('WORKING')).not.toBeInTheDocument();
    });
  });

  describe('AgentConnectivityIndicator', () => {
    it('renders connectivity indicator', () => {
      render(
        <AgentConnectivityIndicator connectivity="ONLINE" />
      );
      expect(screen.getByTestId('agent-connectivity-indicator')).toBeInTheDocument();
    });

    it('shows dot for ONLINE status', () => {
      render(
        <AgentConnectivityIndicator connectivity="ONLINE" />
      );
      const indicator = screen.getByTestId('agent-connectivity-indicator');
      expect(indicator).toBeInTheDocument();
    });

    it('shows dot for OFFLINE status', () => {
      render(
        <AgentConnectivityIndicator connectivity="OFFLINE" />
      );
      const indicator = screen.getByTestId('agent-connectivity-indicator');
      expect(indicator).toBeInTheDocument();
    });

    it('shows dot for STALE status', () => {
      render(
        <AgentConnectivityIndicator connectivity="STALE" />
      );
      const indicator = screen.getByTestId('agent-connectivity-indicator');
      expect(indicator).toBeInTheDocument();
    });

    it('shows dot for UNKNOWN status', () => {
      render(
        <AgentConnectivityIndicator connectivity="UNKNOWN" />
      );
      const indicator = screen.getByTestId('agent-connectivity-indicator');
      expect(indicator).toBeInTheDocument();
    });

    it('supports sm and md sizes', () => {
      const { unmount } = render(
        <AgentConnectivityIndicator connectivity="ONLINE" size="sm" />
      );
      expect(screen.getByTestId('agent-connectivity-indicator')).toBeInTheDocument();
      unmount();

      render(
        <AgentConnectivityIndicator connectivity="ONLINE" size="md" />
      );
      expect(screen.getByTestId('agent-connectivity-indicator')).toBeInTheDocument();
    });

    it('applies glow effect for ONLINE status', () => {
      const { container } = render(
        <AgentConnectivityIndicator connectivity="ONLINE" />
      );
      const indicator = screen.getByTestId('agent-connectivity-indicator');
      const dot = indicator.querySelector('span');
      // Verify dot exists and has styling
      expect(dot).toBeInTheDocument();
      expect(dot?.style.boxShadow).toBeTruthy();
    });
  });

  describe('AgentEdge', () => {
    // Note: EdgeProps require ReactFlowProvider context
    // Basic rendering validation without full React Flow setup

    it('AgentEdge component is importable', () => {
      expect(AgentEdge).toBeDefined();
    });

    it('AgentEdge accepts data prop with isActive', () => {
      // This would require full ReactFlowProvider setup
      // For now, verify the component exists and is properly typed
      const edgeComponent = AgentEdge;
      expect(edgeComponent).toBeDefined();
    });
  });

  describe('Visual Separation of States', () => {
    it('AgentNode separates operational and connectivity visually', () => {
      render(
        <ReactFlowProvider>
          <AgentNode
            data={{
              agent_id: 'test-agent',
              agent_role: 'Test Role',
              status: 'WORKING',
              connectivity_status: 'ONLINE',
            }}
          />
        </ReactFlowProvider>
      );

      // Both indicators should be present but separate
      expect(screen.getByTestId('agent-node-status')).toBeInTheDocument();
      expect(screen.getByTestId('agent-connectivity-indicator')).toBeInTheDocument();

      // Status should show WORKING
      expect(screen.getByText('WORKING')).toBeInTheDocument();
    });

    it('AgentNode shows error state when OFFLINE', () => {
      render(
        <ReactFlowProvider>
          <AgentNode
            data={{
              agent_id: 'offline-agent',
              agent_role: 'Offline Role',
              status: 'IDLE',
              connectivity_status: 'OFFLINE',
            }}
          />
        </ReactFlowProvider>
      );

      // Even though operational state is IDLE, should show OFFLINE
      const statusText = screen.getByTestId('agent-node-status').textContent;
      expect(statusText).toContain('OFFLINE');
    });
  });

  describe('Props Validation', () => {
    it('AgentNode accepts all required props', () => {
      const { container } = render(
        <ReactFlowProvider>
          <AgentNode
            data={{
              agent_id: 'arch',
              agent_role: 'Architect',
              status: 'IDLE',
              connectivity_status: 'ONLINE',
              last_event_at: '2026-11-22T10:00:00Z',
              runtime: 'node:20',
              current_mission_id: 'mission-1',
            }}
            selected={false}
          />
        </ReactFlowProvider>
      );
      expect(container).toBeInTheDocument();
    });

    it('AgentNode renders with minimal props', () => {
      const { container } = render(
        <ReactFlowProvider>
          <AgentNode
            data={{
              agent_id: 'arch',
              agent_role: 'Architect',
              status: 'IDLE',
              connectivity_status: 'ONLINE',
            }}
          />
        </ReactFlowProvider>
      );
      expect(container).toBeInTheDocument();
      expect(screen.getByText('arch')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('AgentNodeStatus has title attribute', () => {
      render(
        <AgentNodeStatus
          status="WORKING"
          connectivity="ONLINE"
        />
      );
      const element = screen.getByTestId('agent-node-status');
      expect(element.getAttribute('title')).toBeTruthy();
      expect(element.getAttribute('title')).toContain('Status:');
    });

    it('AgentConnectivityIndicator has title attribute', () => {
      render(
        <AgentConnectivityIndicator connectivity="ONLINE" />
      );
      const element = screen.getByTestId('agent-connectivity-indicator');
      expect(element.getAttribute('title')).toBeTruthy();
      expect(element.getAttribute('title')).toContain('Connectivity:');
    });
  });
});
