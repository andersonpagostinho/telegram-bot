import React, { useEffect, useState, useMemo } from 'react';
import PageHeader from '../components/layout/PageHeader';
import { Timeline, EventItem } from '../components/timeline';
import { LoadingState, EmptyState, ErrorState } from '../components/common';
import { useWebSocket } from '../hooks/useWebSocket';
import { apiClient } from '../services/api';
import { theme } from '../lib/theme/tokens';

interface TimelineEvent {
  id: string;
  event_id: string;
  event_type: string;
  sequence: number;
  timestamp: Date;
  agent?: string;
  status: 'IDLE' | 'WORKING' | 'ANALYZING' | 'TESTING' | 'REVIEWING' | 'BLOCKED' | 'COMPLETED' | 'ERROR';
  description: string;
  mission_id?: string;
  payload?: any;
}

export default function ActivityStream() {
  const { isConnected } = useWebSocket({ eventTypes: ['AGENT_UPDATED', 'MISSION_UPDATED', 'EXECUTION_COMPLETED'] });

  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState<number | undefined>();
  const [hasMore, setHasMore] = useState(false);

  // Fetch historical events
  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setIsLoading(true);
        const response = await apiClient.getEvents({
          cursor: undefined,
          per_page: 50
        });

        if (response.events && Array.isArray(response.events)) {
          const mapped = response.events.map((evt: any) => ({
            id: evt.event_id,
            event_id: evt.event_id,
            event_type: evt.event_type,
            sequence: evt.sequence,
            timestamp: new Date(evt.created_at),
            agent: evt.payload?.source_agent || evt.payload?.agent_id,
            status: mapEventTypeToStatus(evt.event_type),
            description: formatEventDescription(evt),
            mission_id: evt.payload?.mission_id,
            payload: evt.payload,
          }));

          setEvents(mapped);
          setCursor(response.cursor);
          setHasMore(response.has_more || false);
        }
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load events');
      } finally {
        setIsLoading(false);
      }
    };

    fetchEvents();
  }, []);

  // Load more events
  const loadMore = async () => {
    if (!hasMore || cursor === undefined) return;

    try {
      const response = await apiClient.getEvents({
        cursor,
        per_page: 50,
      });

      if (response.events && Array.isArray(response.events)) {
        const mapped = response.events.map((evt: any) => ({
          id: evt.event_id,
          event_id: evt.event_id,
          event_type: evt.event_type,
          sequence: evt.sequence,
          timestamp: new Date(evt.created_at),
          agent: evt.payload?.source_agent || evt.payload?.agent_id,
          status: mapEventTypeToStatus(evt.event_type),
          description: formatEventDescription(evt),
          mission_id: evt.payload?.mission_id,
          payload: evt.payload,
        }));

        setEvents(prev => [...prev, ...mapped]);
        setCursor(response.cursor);
        setHasMore(response.has_more || false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load more events');
    }
  };

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Activity Stream" description="Real-time event log" />
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Activity Stream" description="Real-time event log" />
        <ErrorState message={error} />
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div>
        <PageHeader title="Activity Stream" description="Real-time event log" />
        <EmptyState message="No events available" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Activity Stream"
        description={`${events.length} events`}
      />

      <div style={{ margin: theme.spacing.md }}>
        {/* Connection status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: theme.spacing.sm,
            marginBottom: theme.spacing.md,
            fontSize: '0.875rem',
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
          <span style={{ color: theme.colors.baseline.text }}>
            {isConnected ? 'Live updates enabled' : 'Offline'}
          </span>
        </div>

        {/* Timeline */}
        <div style={{
          backgroundColor: theme.colors.baseline.card,
          border: `1px solid ${theme.colors.baseline.border}`,
          borderRadius: '0.5rem',
          padding: theme.spacing.md,
        }}>
          <Timeline
            items={events.map(evt => ({
              id: evt.event_id,
              type: evt.event_type as any,
              timestamp: evt.timestamp,
              agent: evt.agent || 'unknown',
              status: evt.status,
              description: evt.description,
            }))}
          />
        </div>

        {/* Load more */}
        {hasMore && (
          <div style={{ textAlign: 'center', marginTop: theme.spacing.lg }}>
            <button
              onClick={loadMore}
              style={{
                padding: `${theme.spacing.sm} ${theme.spacing.md}`,
                backgroundColor: theme.colors.semantic.agentIdle,
                color: theme.colors.baseline.bg,
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontSize: '0.875rem',
              }}
            >
              Load More
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function mapEventTypeToStatus(eventType: string): TimelineEvent['status'] {
  if (eventType.includes('COMPLETED')) return 'COMPLETED';
  if (eventType.includes('ERROR') || eventType.includes('FAILED')) return 'ERROR';
  if (eventType.includes('BLOCKED')) return 'BLOCKED';
  if (eventType.includes('TESTING')) return 'TESTING';
  if (eventType.includes('ANALYZING')) return 'ANALYZING';
  if (eventType.includes('REVIEWING')) return 'REVIEWING';
  if (eventType.includes('WORKING')) return 'WORKING';
  return 'IDLE';
}

function formatEventDescription(evt: any): string {
  const type = evt.event_type;
  const payload = evt.payload || {};

  if (type.includes('MISSION')) {
    return `Mission ${payload.mission_id}: ${type.replace(/_/g, ' ').toLowerCase()}`;
  }
  if (type.includes('EXECUTION')) {
    return `Execution by ${payload.source_agent}: ${type.replace(/_/g, ' ').toLowerCase()}`;
  }
  if (type.includes('AGENT')) {
    return `Agent ${payload.source_agent}: ${type.replace(/_/g, ' ').toLowerCase()}`;
  }
  return type.replace(/_/g, ' ').toLowerCase();
}
