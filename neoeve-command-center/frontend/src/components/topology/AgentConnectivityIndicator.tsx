/**
 * AgentConnectivityIndicator - Display network connectivity status
 * Separated from operational status
 * Shows ONLINE/OFFLINE/STALE/UNKNOWN states
 */

import React from 'react';
import { theme } from '../../lib/theme/tokens';

interface AgentConnectivityIndicatorProps {
  connectivity: 'ONLINE' | 'OFFLINE' | 'STALE' | 'UNKNOWN';
  size?: 'sm' | 'md';
}

export const AgentConnectivityIndicator: React.FC<AgentConnectivityIndicatorProps> = ({
  connectivity,
  size = 'sm',
}) => {
  const getConnectivityColor = (): string => {
    switch (connectivity) {
      case 'ONLINE':
        return theme.colors.connectivity.online;
      case 'OFFLINE':
        return theme.colors.connectivity.offline;
      case 'STALE':
        return theme.colors.connectivity.stale;
      case 'UNKNOWN':
        return theme.colors.connectivity.unknown;
      default:
        return theme.colors.connectivity.unknown;
    }
  };

  const getSizeClasses = (): { dot: string; text: string } => {
    switch (size) {
      case 'md':
        return {
          dot: '0.5rem',
          text: '0.7rem',
        };
      default:
        return {
          dot: '0.375rem',
          text: '0.65rem',
        };
    }
  };

  const color = getConnectivityColor();
  const { dot, text } = getSizeClasses();

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.25rem',
        fontSize: text,
      }}
      data-testid="agent-connectivity-indicator"
      title={`Connectivity: ${connectivity}`}
    >
      <span
        style={{
          display: 'inline-block',
          width: dot,
          height: dot,
          borderRadius: '50%',
          backgroundColor: color,
          boxShadow:
            connectivity === 'ONLINE'
              ? `0 0 ${parseFloat(dot) * 2}px ${color}`
              : 'none',
        }}
      />
    </div>
  );
};

export default AgentConnectivityIndicator;
