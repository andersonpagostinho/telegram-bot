/**
 * MissionHistory - Browse and analyze completed missions
 * Historical record of all mission executions with results
 */

import React, { useState } from 'react';
import { ChevronDown, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { useExecutions } from '../hooks/useExecutions';
import { LoadingState, EmptyState, ErrorState } from '../components/common';
import PageHeader from '../components/layout/PageHeader';
import { theme } from '../lib/theme/tokens';

const statusColors = {
  COMPLETED: '#008000',
  FAILED: '#FF0000',
  BLOCKED: '#DC143C',
  PARTIAL: '#FFD700',
};

export default function MissionHistory() {
  const { data: executionsData, isLoading, error } = useExecutions({ per_page: 100 });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error as Error} />;

  const executions = executionsData?.executions || [];
  const filtered = filterStatus ? executions.filter((e) => e.status === filterStatus) : executions;

  if (filtered.length === 0) {
    return <EmptyState message={filterStatus ? `No ${filterStatus} missions` : 'No mission history'} />;
  }

  // Calculate statistics
  const stats = {
    total: executions.length,
    completed: executions.filter((e) => e.status === 'COMPLETED').length,
    failed: executions.filter((e) => e.status === 'FAILED').length,
    successRate: executions.length > 0 ? Math.round((executions.filter((e) => e.status === 'COMPLETED').length / executions.length) * 100) : 0,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: theme.palette.background.default }}>
      <PageHeader title="Mission History" subtitle="Browse completed missions and execution results" />

      {/* Statistics */}
      <div style={{ padding: '16px 24px', borderBottom: `1px solid ${theme.palette.divider}` }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: theme.palette.background.paper }}>
            <div style={{ color: theme.palette.text.secondary, fontSize: '12px', marginBottom: '4px' }}>Total Missions</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: theme.palette.text.primary }}>{stats.total}</div>
          </div>
          <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: theme.palette.background.paper }}>
            <div style={{ color: theme.palette.text.secondary, fontSize: '12px', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <TrendingUp size={14} color="#008000" /> Completed
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#008000' }}>{stats.completed}</div>
          </div>
          <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: theme.palette.background.paper }}>
            <div style={{ color: theme.palette.text.secondary, fontSize: '12px', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <TrendingDown size={14} color="#FF0000" /> Failed
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#FF0000' }}>{stats.failed}</div>
          </div>
          <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: theme.palette.background.paper }}>
            <div style={{ color: theme.palette.text.secondary, fontSize: '12px', marginBottom: '4px' }}>Success Rate</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: stats.successRate >= 80 ? '#008000' : stats.successRate >= 50 ? '#FFD700' : '#FF0000' }}>
              {stats.successRate}%
            </div>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div style={{ padding: '16px 24px', display: 'flex', gap: '8px', borderBottom: `1px solid ${theme.palette.divider}` }}>
        <button
          onClick={() => setFilterStatus(null)}
          style={{
            padding: '6px 12px',
            borderRadius: '4px',
            border: 'none',
            backgroundColor: !filterStatus ? theme.palette.primary.main : theme.palette.action.disabledBackground,
            color: !filterStatus ? '#fff' : theme.palette.text.secondary,
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          All
        </button>
        {Object.keys(statusColors).map((status) => (
          <button
            key={status}
            onClick={() => setFilterStatus(status)}
            style={{
              padding: '6px 12px',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: filterStatus === status ? statusColors[status] : theme.palette.action.disabledBackground,
              color: filterStatus === status ? '#fff' : theme.palette.text.secondary,
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {status}
          </button>
        ))}
      </div>

      {/* History List */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filtered.map((execution) => (
            <div
              key={execution.execution_id}
              style={{
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onClick={() => setExpandedId(expandedId === execution.execution_id ? null : execution.execution_id)}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = `0 2px 8px rgba(0,0,0,0.1)`;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <ChevronDown
                  size={18}
                  style={{
                    transform: expandedId === execution.execution_id ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s ease',
                    color: theme.palette.text.secondary,
                  }}
                />
                <div style={{ flex: 1 }}>
                  <h4 style={{ margin: '0 0 2px 0', fontSize: '13px', fontWeight: 600, color: theme.palette.text.primary }}>
                    Mission {execution.mission_id?.slice(0, 8)} - Agent {execution.agent_id?.slice(0, 8)}
                  </h4>
                  <p style={{ margin: '0', fontSize: '12px', color: theme.palette.text.secondary }}>
                    {new Date(execution.started_at || Date.now()).toLocaleDateString()} at{' '}
                    {new Date(execution.started_at || Date.now()).toLocaleTimeString()}
                  </p>
                </div>
                <div
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: statusColors[execution.status] || theme.palette.action.disabledBackground,
                    color: '#fff',
                    fontSize: '11px',
                    fontWeight: 600,
                  }}
                >
                  {execution.status}
                </div>
              </div>

              {expandedId === execution.execution_id && (
                <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${theme.palette.divider}` }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px', marginBottom: '12px' }}>
                    <div>
                      <span style={{ color: theme.palette.text.secondary }}>Duration: </span>
                      <span style={{ color: theme.palette.text.primary, fontWeight: 500 }}>
                        {execution.total_duration_ms ? `${(execution.total_duration_ms / 1000).toFixed(1)}s` : 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: theme.palette.text.secondary }}>Execution ID: </span>
                      <span style={{ color: theme.palette.text.primary, fontFamily: 'monospace' }}>
                        {execution.execution_id?.slice(0, 12)}...
                      </span>
                    </div>
                  </div>

                  {execution.error && (
                    <div
                      style={{
                        padding: '8px 12px',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(255, 0, 0, 0.1)',
                        display: 'flex',
                        gap: '8px',
                        marginBottom: '12px',
                      }}
                    >
                      <AlertCircle size={14} color="#FF0000" style={{ flexShrink: 0 }} />
                      <span style={{ fontSize: '12px', color: '#FF0000' }}>{execution.error}</span>
                    </div>
                  )}

                  {execution.result && (
                    <div>
                      <span style={{ fontSize: '12px', fontWeight: 600, color: theme.palette.text.primary }}>Result:</span>
                      <pre
                        style={{
                          margin: '4px 0 0 0',
                          padding: '8px',
                          borderRadius: '4px',
                          backgroundColor: theme.palette.action.disabledBackground,
                          color: theme.palette.text.secondary,
                          fontSize: '11px',
                          overflow: 'auto',
                          maxHeight: '200px',
                        }}
                      >
                        {typeof execution.result === 'string' ? execution.result : JSON.stringify(execution.result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
