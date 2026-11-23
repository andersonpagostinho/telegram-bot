/**
 * AgentDetailModal - Display detailed information about an agent
 * Shows operational status, connectivity, current mission, and recent events
 */

import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { AgentResponse } from '../../types/api';
import StatusIndicator from '../common/StatusIndicator';
import { theme } from '../../lib/theme/tokens';

interface AgentDetailModalProps {
  agentId: string;
  onClose: () => void;
  agents: AgentResponse[];
}

export default function AgentDetailModal({
  agentId,
  onClose,
  agents,
}: AgentDetailModalProps) {
  const agent = agents.find(a => a.agent_id.toLowerCase() === agentId.toLowerCase());

  if (!agent) {
    return null;
  }

  const relativeTime = agent.last_event_at
    ? formatDistanceToNow(new Date(agent.last_event_at), { addSuffix: true })
    : 'Never';

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          zIndex: 40,
          backdropFilter: 'blur(4px)',
        }}
      />

      {/* Modal */}
      <div
        style={{
          position: 'fixed',
          bottom: '5rem',
          right: theme.spacing.md,
          width: '24rem',
          maxHeight: '50vh',
          backgroundColor: theme.colors.baseline.card,
          border: `1px solid ${theme.colors.baseline.border}`,
          borderRadius: '0.5rem',
          padding: theme.spacing.lg,
          zIndex: 50,
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3)',
          overflowY: 'auto',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: theme.spacing.lg,
          }}
        >
          <div>
            <h2
              style={{
                fontSize: '1.5rem',
                fontWeight: 600,
                color: theme.colors.baseline.text,
                marginBottom: '0.25rem',
              }}
            >
              {agent.agent_id}
            </h2>
            <p
              style={{
                fontSize: '0.875rem',
                color: '#94a3b8',
                fontStyle: 'italic',
              }}
            >
              {agent.agent_role}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: theme.colors.baseline.text,
              cursor: 'pointer',
              fontSize: '1.5rem',
              lineHeight: 1,
              padding: 0,
            }}
          >
            ✕
          </button>
        </div>

        {/* Status Section */}
        <div
          style={{
            marginBottom: theme.spacing.lg,
            paddingBottom: theme.spacing.lg,
            borderBottom: `1px solid ${theme.colors.baseline.border}`,
          }}
        >
          <h3
            style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              color: theme.colors.baseline.text,
              marginBottom: theme.spacing.sm,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Status
          </h3>
          <div
            style={{
              display: 'flex',
              gap: theme.spacing.sm,
              marginBottom: theme.spacing.sm,
            }}
          >
            <StatusIndicator
              status={agent.status}
              connectivity={agent.connectivity_status}
              size="md"
            />
          </div>
          <div
            style={{
              fontSize: '0.75rem',
              color: '#cbd5e1',
            }}
          >
            <div>
              <span style={{ color: '#94a3b8' }}>Operational:</span> {agent.status}
            </div>
            <div>
              <span style={{ color: '#94a3b8' }}>Connectivity:</span> {agent.connectivity_status}
            </div>
          </div>
        </div>

        {/* Activity Section */}
        <div
          style={{
            marginBottom: theme.spacing.lg,
            paddingBottom: theme.spacing.lg,
            borderBottom: `1px solid ${theme.colors.baseline.border}`,
          }}
        >
          <h3
            style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              color: theme.colors.baseline.text,
              marginBottom: theme.spacing.sm,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Activity
          </h3>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: theme.spacing.xs,
              fontSize: '0.75rem',
              color: '#cbd5e1',
            }}
          >
            <div>
              <span style={{ color: '#94a3b8' }}>Last Event:</span> {relativeTime}
            </div>
            {agent.last_error && (
              <div>
                <span style={{ color: '#94a3b8' }}>Last Error:</span> {agent.last_error}
              </div>
            )}
            {agent.runtime && (
              <div>
                <span style={{ color: '#94a3b8' }}>Runtime:</span> {agent.runtime}
              </div>
            )}
          </div>
        </div>

        {/* Mission Section */}
        {agent.current_mission_id && (
          <div
            style={{
              marginBottom: theme.spacing.lg,
              paddingBottom: theme.spacing.lg,
              borderBottom: `1px solid ${theme.colors.baseline.border}`,
            }}
          >
            <h3
              style={{
                fontSize: '0.875rem',
                fontWeight: 600,
                color: theme.colors.baseline.text,
                marginBottom: theme.spacing.sm,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Current Mission
            </h3>
            <div
              style={{
                fontSize: '0.875rem',
                color: '#cbd5e1',
                wordBreak: 'break-word',
              }}
            >
              {agent.current_mission_id}
            </div>
            {agent.current_task_id && (
              <div
                style={{
                  fontSize: '0.75rem',
                  color: '#94a3b8',
                  marginTop: theme.spacing.xs,
                }}
              >
                Task: {agent.current_task_id}
              </div>
            )}
          </div>
        )}

        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            width: '100%',
            padding: `${theme.spacing.sm} ${theme.spacing.md}`,
            backgroundColor: theme.colors.semantic.agentIdle,
            color: theme.colors.baseline.bg,
            border: 'none',
            borderRadius: '0.375rem',
            fontWeight: 500,
            cursor: 'pointer',
            fontSize: '0.875rem',
            transition: 'opacity 0.2s',
          }}
          onMouseOver={(e) => {
            (e.currentTarget as HTMLButtonElement).style.opacity = '0.8';
          }}
          onMouseOut={(e) => {
            (e.currentTarget as HTMLButtonElement).style.opacity = '1';
          }}
        >
          Close
        </button>
      </div>
    </>
  );
}
