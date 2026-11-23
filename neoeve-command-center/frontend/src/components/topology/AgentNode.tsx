/**
 * AgentNode - React Flow node component for displaying agent topology
 * Shows operational status and connectivity state separately
 */

import React from 'react';
import { Handle, Position } from 'reactflow';
import { theme } from '../../lib/theme/tokens';
import AgentNodeStatus from './AgentNodeStatus';
import AgentConnectivityIndicator from './AgentConnectivityIndicator';

export interface AgentNodeData {
  agent_id: string;
  agent_role: string;
  status: 'IDLE' | 'WORKING' | 'ANALYZING' | 'TESTING' | 'REVIEWING' | 'BLOCKED' | 'COMPLETED' | 'ERROR';
  connectivity_status: 'ONLINE' | 'OFFLINE' | 'STALE' | 'UNKNOWN';
  last_event_at?: string;
  runtime?: string;
  current_mission_id?: string;
}

interface AgentNodeProps {
  data: AgentNodeData;
  selected?: boolean;
}

export const AgentNode: React.FC<AgentNodeProps> = ({ data, selected }) => {
  const getStatusColor = (): string => {
    if (data.connectivity_status !== 'ONLINE') {
      return theme.colors.semantic.agentError;
    }

    switch (data.status) {
      case 'IDLE':
        return theme.colors.semantic.agentIdle;
      case 'WORKING':
        return theme.colors.semantic.agentWorking;
      case 'ANALYZING':
        return theme.colors.semantic.agentAnalyzing;
      case 'TESTING':
        return theme.colors.semantic.agentTesting;
      case 'REVIEWING':
        return theme.colors.semantic.agentReviewing;
      case 'BLOCKED':
        return theme.colors.semantic.agentBlocked;
      case 'COMPLETED':
        return theme.colors.semantic.agentCompleted;
      case 'ERROR':
        return theme.colors.semantic.agentError;
      default:
        return theme.colors.baseline.border;
    }
  };

  const formatLastEvent = (dateStr?: string): string => {
    if (!dateStr) return 'Never';
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSecs = Math.floor(diffMs / 1000);
      const diffMins = Math.floor(diffSecs / 60);
      const diffHours = Math.floor(diffMins / 60);

      if (diffSecs < 60) return `${diffSecs}s ago`;
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      return `${Math.floor(diffHours / 24)}d ago`;
    } catch {
      return 'Unknown';
    }
  };

  const borderColor = selected ? '#06b6d4' : theme.colors.baseline.border;

  return (
    <div
      style={{
        background: theme.colors.baseline.card,
        border: `2px solid ${borderColor}`,
        borderRadius: '0.5rem',
        padding: theme.spacing.md,
        minWidth: '220px',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        boxShadow: selected ? `0 0 0 2px ${theme.colors.baseline.bg}, 0 0 0 4px ${getStatusColor()}` : 'none',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Agent ID and Role */}
      <div style={{ marginBottom: theme.spacing.sm }}>
        <div
          style={{
            fontSize: '0.875rem',
            fontWeight: 600,
            color: theme.colors.baseline.text,
            marginBottom: '0.25rem',
          }}
        >
          {data.agent_id}
        </div>
        <div
          style={{
            fontSize: '0.75rem',
            color: '#94a3b8', // slate-400
            fontStyle: 'italic',
          }}
        >
          {data.agent_role}
        </div>
      </div>

      {/* Status Indicators Row */}
      <div
        style={{
          display: 'flex',
          gap: theme.spacing.sm,
          justifyContent: 'center',
          marginBottom: theme.spacing.sm,
          alignItems: 'center',
        }}
      >
        <AgentNodeStatus status={data.status} connectivity={data.connectivity_status} />
        <AgentConnectivityIndicator connectivity={data.connectivity_status} />
      </div>

      {/* Last Event */}
      {data.last_event_at && (
        <div
          style={{
            fontSize: '0.7rem',
            color: '#cbd5e1', // slate-300
            marginBottom: theme.spacing.xs,
          }}
        >
          {formatLastEvent(data.last_event_at)}
        </div>
      )}

      {/* Current Mission */}
      {data.current_mission_id && (
        <div
          style={{
            fontSize: '0.65rem',
            color: '#94a3b8', // slate-400
            marginBottom: theme.spacing.xs,
            wordBreak: 'break-word',
          }}
        >
          Mission: {data.current_mission_id}
        </div>
      )}

      {/* Handles */}
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default AgentNode;
