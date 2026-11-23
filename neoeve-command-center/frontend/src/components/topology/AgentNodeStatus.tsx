/**
 * AgentNodeStatus - Display operational status indicator
 * Shows agent operational state (IDLE/WORKING/ANALYZING/etc)
 * Separated from connectivity status
 */

import React from 'react';
import { theme } from '../../lib/theme/tokens';

interface AgentNodeStatusProps {
  status: 'IDLE' | 'WORKING' | 'ANALYZING' | 'TESTING' | 'REVIEWING' | 'BLOCKED' | 'COMPLETED' | 'ERROR';
  connectivity: 'ONLINE' | 'OFFLINE' | 'STALE' | 'UNKNOWN';
}

export const AgentNodeStatus: React.FC<AgentNodeStatusProps> = ({ status, connectivity }) => {
  const getStatusColor = (): string => {
    // Offline always shows as error
    if (connectivity !== 'ONLINE') {
      return theme.colors.semantic.agentError;
    }

    switch (status) {
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

  const displayText = connectivity !== 'ONLINE' ? 'OFFLINE' : status;
  const color = getStatusColor();

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.25rem',
        padding: `0.25rem ${theme.spacing.sm}`,
        borderRadius: '9999px',
        backgroundColor: `${color}20`, // Add transparency
        border: `1px solid ${color}`,
        fontSize: '0.65rem',
        fontWeight: 500,
        color: color,
      }}
      data-testid="agent-node-status"
      title={`Status: ${displayText}`}
    >
      <span
        style={{
          display: 'inline-block',
          width: '0.375rem',
          height: '0.375rem',
          borderRadius: '50%',
          backgroundColor: color,
        }}
      />
      {displayText}
    </div>
  );
};

export default AgentNodeStatus;
