/**
 * AgentMap - Visualize agent topology and status in real-time
 * Shows 7 agents with their operational and connectivity status
 * Integrates with React Flow for visualization
 */

import React, { useCallback, useState, useMemo } from 'react';
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MiniMap,
  NodeMouseHandler,
} from 'reactflow';
import type { Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';

import { useAgents } from '../hooks/useAgents';
import { useWebSocket } from '../hooks/useWebSocket';
import { LoadingState, EmptyState, ErrorState } from '../components/common';
import { AgentNode, AgentEdge, type AgentNodeData } from '../components/topology';
import PageHeader from '../components/layout/PageHeader';
import AgentDetailModal from '../components/agent/AgentDetailModal';
import { theme } from '../lib/theme/tokens';

export default function AgentMap() {
  const { data: agentsData, isLoading, error } = useAgents({ per_page: 100 });
  const { isConnected } = useWebSocket({ eventTypes: ['AGENT_UPDATED', 'AGENT_STATUS_CHANGED'] });

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  // Define agent positions for the topology
  const positionMap: Record<string, { x: number; y: number }> = useMemo(() => ({
    architect: { x: 0, y: 0 },
    backend_dev: { x: -300, y: 150 },
    debugger: { x: 0, y: 150 },
    qa: { x: 300, y: 150 },
    security_auditor: { x: -150, y: 300 },
    release_mgr: { x: 150, y: 300 },
    openai_validator: { x: -150, y: 450 },
  }), []);

  // Build nodes and edges from agents
  React.useEffect(() => {
    if (!agentsData?.agents) return;

    const newNodes: Array<Node<AgentNodeData>> = agentsData.agents.map((agent) => {
      let nodeId = agent.agent_id.toLowerCase();
      let position = positionMap[nodeId] || { x: 0, y: 0 };

      return {
        id: nodeId,
        type: 'agentNode',
        data: {
          agent_id: agent.agent_id,
          agent_role: agent.agent_role,
          status: agent.status,
          connectivity_status: agent.connectivity_status,
          last_event_at: agent.last_event_at,
          runtime: agent.runtime,
          current_mission_id: agent.current_mission_id,
        } as AgentNodeData,
        position,
      };
    });

    // Define edges (connections between agents)
    const edgeDefinitions: Array<[string, string]> = [
      ['architect', 'backend_dev'],
      ['architect', 'debugger'],
      ['architect', 'qa'],
      ['backend_dev', 'security_auditor'],
      ['debugger', 'security_auditor'],
      ['qa', 'release_mgr'],
      ['security_auditor', 'openai_validator'],
    ];

    const newEdges: Edge[] = edgeDefinitions
      .map(([source, target]) => ({
        id: `${source}-${target}`,
        source,
        target,
        type: 'agentEdge',
        data: {
          isActive: false,
          label: undefined,
        },
      }))
      .filter(edge =>
        newNodes.some(n => n.id === edge.source) &&
        newNodes.some(n => n.id === edge.target)
      );

    setNodes(newNodes);
    setEdges(newEdges);
  }, [agentsData, positionMap, setNodes, setEdges]);

  const handleNodeClick: NodeMouseHandler = useCallback((event, node) => {
    setSelectedAgent(node.id);
  }, []);

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Agent Map" description="Real-time agent topology and status" />
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Agent Map" description="Real-time agent topology and status" />
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load agents'}
        />
      </div>
    );
  }

  if (!agentsData?.agents || agentsData.agents.length === 0) {
    return (
      <div>
        <PageHeader title="Agent Map" description="Real-time agent topology and status" />
        <EmptyState message="No agents available" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <PageHeader
        title="Agent Map"
        description={`Real-time topology of ${agentsData.agents.length} agents`}
      />

      <div
        style={{
          flex: 1,
          backgroundColor: theme.colors.baseline.bg,
          border: `1px solid ${theme.colors.baseline.border}`,
          margin: theme.spacing.md,
          borderRadius: '0.5rem',
          overflow: 'hidden',
        }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={{ agentNode: AgentNode as any }}
          edgeTypes={{ agentEdge: AgentEdge as any }}
          onNodeClick={handleNodeClick}
          fitView
        >
          <Background
            color={theme.colors.baseline.border}
            gap={16}
            size={1}
          />
          <Controls
            style={{
              backgroundColor: theme.colors.baseline.card,
              border: `1px solid ${theme.colors.baseline.border}`,
              borderRadius: '0.375rem',
            }}
          />
          <MiniMap
            style={{
              backgroundColor: theme.colors.baseline.card,
              border: `1px solid ${theme.colors.baseline.border}`,
              borderRadius: '0.375rem',
            }}
          />
        </ReactFlow>
      </div>

      {selectedAgent && (
        <AgentDetailModal
          agentId={selectedAgent}
          onClose={() => setSelectedAgent(null)}
          agents={agentsData.agents}
        />
      )}

      {/* Connection status indicator */}
      <div
        style={{
          padding: theme.spacing.md,
          backgroundColor: theme.colors.baseline.card,
          borderTop: `1px solid ${theme.colors.baseline.border}`,
          display: 'flex',
          alignItems: 'center',
          gap: theme.spacing.md,
          fontSize: '0.875rem',
          color: theme.colors.baseline.text,
        }}
      >
        <div
          style={{
            width: '0.5rem',
            height: '0.5rem',
            borderRadius: '50%',
            backgroundColor: isConnected ? theme.colors.connectivity.online : theme.colors.connectivity.offline,
          }}
        />
        <span>
          {isConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
        </span>
      </div>
    </div>
  );
}
