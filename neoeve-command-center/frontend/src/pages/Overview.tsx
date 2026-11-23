import React, { useMemo } from 'react';
import PageHeader from '../components/layout/PageHeader';
import { MetricCard, LoadingState, EmptyState, ErrorState } from '../components/common';
import { ChartWrapper, MetricChart } from '../components/charts';
import { Timeline } from '../components/timeline';
import { useAgents } from '../hooks/useAgents';
import { useMissions } from '../hooks/useMissions';
import { useExecutions } from '../hooks/useExecutions';
import { theme } from '../lib/theme/tokens';

export default function Overview() {
  const { data: agentsData, isLoading: agentsLoading, error: agentsError } = useAgents();
  const { data: missionsData, isLoading: missionsLoading, error: missionsError } = useMissions();
  const { data: executionsData, isLoading: executionsLoading, error: executionsError } = useExecutions();

  const isLoading = agentsLoading || missionsLoading || executionsLoading;
  const hasError = agentsError || missionsError || executionsError;

  // Calculate metrics
  const metrics = useMemo(() => {
    if (!agentsData?.agents) return null;

    const agents = agentsData.agents;
    const totalAgents = agents.length;
    const onlineAgents = agents.filter(a => a.connectivity_status === 'ONLINE').length;
    const workingAgents = agents.filter(a => a.status === 'WORKING').length;
    const errorAgents = agents.filter(a => a.status === 'ERROR').length;

    const missions = missionsData?.missions || [];
    const activeMissions = missions.filter(m => m.status === 'RUNNING').length;

    const executions = executionsData?.executions || [];
    const totalExecutions = executions.length;

    return {
      totalAgents,
      onlineAgents,
      workingAgents,
      errorAgents,
      activeMissions,
      totalExecutions,
    };
  }, [agentsData, missionsData, executionsData]);

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Overview" description="System status and metrics" />
        <LoadingState />
      </div>
    );
  }

  if (hasError) {
    return (
      <div>
        <PageHeader title="Overview" description="System status and metrics" />
        <ErrorState message="Failed to load overview data" />
      </div>
    );
  }

  if (!metrics) {
    return (
      <div>
        <PageHeader title="Overview" description="System status and metrics" />
        <EmptyState message="No data available" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Overview" description="Real-time system status and metrics" />

      {/* Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: theme.spacing.md,
          margin: theme.spacing.md,
        }}
      >
        <MetricCard label="Total Agents" value={metrics.totalAgents} />
        <MetricCard label="Online" value={metrics.onlineAgents} />
        <MetricCard label="Working" value={metrics.workingAgents} />
        <MetricCard label="Errors" value={metrics.errorAgents} />
        <MetricCard label="Active Missions" value={metrics.activeMissions} />
        <MetricCard label="Executions" value={metrics.totalExecutions} />
      </div>

      {/* Charts Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: theme.spacing.md,
          margin: theme.spacing.md,
        }}
      >
        <ChartWrapper title="Agent Distribution" isEmpty={metrics.totalAgents === 0}>
          <MetricChart
            data={[
              { timestamp: new Date().toISOString(), value: metrics.onlineAgents },
            ]}
            metric="agents"
          />
        </ChartWrapper>
      </div>

      {/* Timeline */}
      {executionsData?.executions && executionsData.executions.length > 0 && (
        <div style={{ margin: theme.spacing.md }}>
          <h2
            style={{
              fontSize: '1.125rem',
              fontWeight: 600,
              color: theme.colors.baseline.text,
              marginBottom: theme.spacing.md,
            }}
          >
            Recent Activity
          </h2>
          <Timeline
            items={executionsData.executions.slice(0, 5).map(exec => ({
              id: exec.execution_id,
              type: 'EXECUTION_STARTED' as const,
              timestamp: exec.started_at ? new Date(exec.started_at) : new Date(),
              agent: exec.agent_id,
              status: 'WORKING' as const,
              description: `Execution ${exec.execution_id.slice(0, 8)}...`,
            }))}
          />
        </div>
      )}
    </div>
  );
}
