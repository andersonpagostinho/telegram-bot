import { TimelineEvent } from './Timeline';

interface EventTypeIndicatorProps {
  type: TimelineEvent['type'];
}

const typeColors: Record<string, string> = {
  AGENT_UPDATED: 'bg-cyan-500',
  MISSION_UPDATED: 'bg-amber-500',
  EXECUTION_STARTED: 'bg-violet-500',
  TASK_COMPLETED: 'bg-teal-500',
  VALIDATION_COMPLETED: 'bg-pink-500',
};

export const EventTypeIndicator: React.FC<EventTypeIndicatorProps> = ({ type }) => (
  <div className={`${typeColors[type] || 'bg-slate-500'} w-3 h-3 rounded-full flex-shrink-0 mt-1`} />
);
