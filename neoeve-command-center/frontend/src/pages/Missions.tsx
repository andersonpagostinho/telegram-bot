/**
 * Missions - Manage and track all missions
 * Shows mission status, agent assignments, and progress
 */

import React, { useState } from 'react';
import { Plus, AlertCircle } from 'lucide-react';
import { useMissions } from '../hooks/useMissions';
import { useWebSocket } from '../hooks/useWebSocket';
import { LoadingState, EmptyState, ErrorState } from '../components/common';
import PageHeader from '../components/layout/PageHeader';
import { theme } from '../lib/theme/tokens';

const statusColors = {
  PENDING: '#FFA500',
  ASSIGNED: '#4169E1',
  IN_PROGRESS: '#32CD32',
  ANALYZING: '#1E90FF',
  TESTING: '#FF8C00',
  AWAITING_VALIDATION: '#FFD700',
  COMPLETED: '#008000',
  FAILED: '#FF0000',
  BLOCKED: '#DC143C',
};

const priorityColors = {
  LOW: '#90EE90',
  MEDIUM: '#FFD700',
  HIGH: '#FF6347',
  CRITICAL: '#DC143C',
};

export default function Missions() {
  const { data: missionsData, isLoading, error } = useMissions({ per_page: 100 });
  const { isConnected } = useWebSocket({ eventTypes: ['MISSION_CREATED', 'MISSION_UPDATED', 'MISSION_COMPLETED'] });
  const [selectedMission, setSelectedMission] = useState<string | null>(null);

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error as Error} />;
  if (!missionsData?.missions || missionsData.missions.length === 0) {
    return <EmptyState message="No missions found" />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: theme.palette.background.default }}>
      <PageHeader title="Missions" subtitle="Track and manage all missions" />

      <div style={{ flex: 1, overflow: 'auto', padding: '24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '16px' }}>
          {missionsData.missions.map((mission) => (
            <div
              key={mission.mission_id}
              onClick={() => setSelectedMission(mission.mission_id)}
              style={{
                padding: '16px',
                border: `2px solid ${statusColors[mission.status] || theme.palette.divider}`,
                borderRadius: '8px',
                backgroundColor: theme.palette.background.paper,
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                transform: selectedMission === mission.mission_id ? 'scale(1.02)' : 'scale(1)',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = `0 4px 12px rgba(0,0,0,0.15)`;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <h3 style={{ margin: '0 0 4px 0', color: theme.palette.text.primary, fontSize: '16px', fontWeight: 600 }}>
                    {mission.title}
                  </h3>
                  <p style={{ margin: '0', color: theme.palette.text.secondary, fontSize: '12px' }}>
                    ID: {mission.mission_id}
                  </p>
                </div>
                <div
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: statusColors[mission.status] || theme.palette.action.disabledBackground,
                    color: '#fff',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}
                >
                  {mission.status}
                </div>
              </div>

              <p style={{ margin: '0 0 12px 0', color: theme.palette.text.secondary, fontSize: '13px' }}>
                {mission.description}
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px', fontSize: '12px' }}>
                <div>
                  <span style={{ color: theme.palette.text.secondary }}>Agent: </span>
                  <span style={{ color: theme.palette.text.primary, fontWeight: 500 }}>
                    {mission.agent_id || 'Unassigned'}
                  </span>
                </div>
                <div>
                  <span style={{ color: theme.palette.text.secondary }}>Priority: </span>
                  <span
                    style={{
                      color: priorityColors[mission.priority] || theme.palette.text.primary,
                      fontWeight: 500,
                    }}
                  >
                    {mission.priority}
                  </span>
                </div>
              </div>

              {mission.progress !== undefined && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', color: theme.palette.text.secondary }}>Progress</span>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: theme.palette.text.primary }}>
                      {mission.progress}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: '6px',
                      borderRadius: '3px',
                      backgroundColor: theme.palette.action.disabledBackground,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${mission.progress}%`,
                        backgroundColor: statusColors[mission.status] || theme.palette.primary.main,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                </div>
              )}

              {mission.blocked && (
                <div
                  style={{
                    padding: '8px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(255, 0, 0, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  <AlertCircle size={14} color="#FF0000" />
                  <span style={{ fontSize: '12px', color: '#FF0000', fontWeight: 500 }}>Blocked: {mission.blocked}</span>
                </div>
              )}

              <div style={{ marginTop: '12px', fontSize: '11px', color: theme.palette.text.secondary }}>
                <div>Created: {new Date(mission.created_at || Date.now()).toLocaleDateString()}</div>
                {mission.completed_at && (
                  <div>Completed: {new Date(mission.completed_at).toLocaleDateString()}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {!isConnected && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            padding: '12px 16px',
            borderRadius: '4px',
            backgroundColor: '#FFA500',
            color: '#fff',
            fontSize: '12px',
            fontWeight: 500,
          }}
        >
          ⚠️ WebSocket disconnected - real-time updates unavailable
        </div>
      )}
    </div>
  );
}
