import { EmptyState, LoadingState } from '../common';
import { EventItem } from './EventItem';

export interface TimelineEvent {
  id: string;
  type: 'AGENT_UPDATED' | 'MISSION_UPDATED' | 'EXECUTION_STARTED' | 'TASK_COMPLETED' | 'VALIDATION_COMPLETED';
  timestamp: Date;
  agent: string;
  status: 'IDLE' | 'WORKING' | 'ANALYZING' | 'TESTING' | 'REVIEWING' | 'BLOCKED' | 'COMPLETED' | 'ERROR';
  description: string;
}

interface TimelineProps {
  items: TimelineEvent[];
  isLoading?: boolean;
}

export const Timeline: React.FC<TimelineProps> = ({ items, isLoading }) => {
  if (isLoading) return <LoadingState />;
  if (items.length === 0) return <EmptyState message="No events" />;

  return (
    <div className="space-y-4">
      {items.map((event) => (
        <EventItem key={event.id} event={event} />
      ))}
    </div>
  );
};
