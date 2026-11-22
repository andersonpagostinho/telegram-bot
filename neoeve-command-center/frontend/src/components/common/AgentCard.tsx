/**
 * AgentCard - Display agent information
 * Shows operational status and connectivity separately
 */

import React from 'react';
import { AgentResponse } from '../../types/api';
import StatusIndicator from './StatusIndicator';

interface AgentCardProps {
  agent: AgentResponse;
  onClick?: () => void;
}

export default function AgentCard({ agent, onClick }: AgentCardProps) {
  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString();
    } catch {
      return null;
    }
  };

  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded-lg bg-slate-800 p-4 transition-colors hover:bg-slate-700"
    >
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-50">{agent.agent_id}</h3>
          <p className="text-sm text-slate-400">{agent.agent_role}</p>
        </div>
      </div>

      {/* Status Row */}
      <div className="mb-3 flex gap-2">
        {/* Operational Status */}
        <div data-testid="agent-status">
          <StatusIndicator
            status={agent.status}
            connectivity={agent.connectivity_status}
            size="sm"
          />
        </div>

        {/* Connectivity Status */}
        {agent.connectivity_status !== 'ONLINE' && (
          <div data-testid="agent-connectivity" className="text-xs text-slate-500">
            {agent.connectivity_status}
          </div>
        )}
      </div>

      {/* Activity Info */}
      <div className="space-y-2 text-xs text-slate-400">
        {agent.last_event_at && (
          <div data-testid="agent-last-activity">
            <span className="text-slate-500">Last event:</span>{' '}
            {formatDate(agent.last_event_at)}
          </div>
        )}

        {agent.runtime && (
          <div>
            <span className="text-slate-500">Runtime:</span> {agent.runtime}
          </div>
        )}

        {agent.current_mission_id && (
          <div>
            <span className="text-slate-500">Current mission:</span>{' '}
            {agent.current_mission_id}
          </div>
        )}
      </div>
    </div>
  );
}
