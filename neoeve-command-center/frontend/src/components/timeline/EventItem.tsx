import { formatDistanceToNow } from 'date-fns';
import { StatusIndicator } from '../common';
import { EventTypeIndicator } from './EventTypeIndicator';
import { TimelineEvent } from './Timeline';

interface EventItemProps {
  event: TimelineEvent;
}

export const EventItem: React.FC<EventItemProps> = ({ event }) => {
  const relativeTime = formatDistanceToNow(event.timestamp, { addSuffix: true });

  return (
    <div className="flex gap-4 p-3 bg-slate-800 rounded border border-slate-700">
      <EventTypeIndicator type={event.type} />
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-slate-50">{event.agent}</span>
          <StatusIndicator
            operationalState={event.status}
            connectivityState="ONLINE"
          />
        </div>
        <p className="text-sm text-slate-300">{event.description}</p>
        <span className="text-xs text-slate-500">{relativeTime}</span>
      </div>
    </div>
  );
};
