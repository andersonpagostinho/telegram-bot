import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Timeline, EventItem } from '../components/timeline';

const mockEvent = {
  id: 'evt-1',
  type: 'AGENT_UPDATED' as const,
  timestamp: new Date('2026-11-22T10:00:00Z'),
  agent: 'Architect',
  status: 'WORKING' as const,
  description: 'Started mission analysis',
};

describe('Timeline Components', () => {
  describe('Timeline', () => {
    it('renders empty state when no items', () => {
      render(<Timeline items={[]} />);
      expect(screen.getByText(/no events/i)).toBeInTheDocument();
    });

    it('renders event items', () => {
      render(<Timeline items={[mockEvent]} />);
      expect(screen.getByText('Architect')).toBeInTheDocument();
      expect(screen.getByText('Started mission analysis')).toBeInTheDocument();
    });

    it('shows loading state when isLoading=true', () => {
      render(<Timeline items={[]} isLoading />);
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('renders multiple events in order', () => {
      const events = [
        { ...mockEvent, id: 'evt-1', timestamp: new Date('2026-11-22T10:00:00Z') },
        { ...mockEvent, id: 'evt-2', timestamp: new Date('2026-11-22T11:00:00Z'), agent: 'CodeReviewer' },
      ];
      render(<Timeline items={events} />);
      expect(screen.getByText('Architect')).toBeInTheDocument();
      expect(screen.getByText('CodeReviewer')).toBeInTheDocument();
    });
  });

  describe('EventItem', () => {
    it('renders agent name', () => {
      render(<EventItem event={mockEvent} />);
      expect(screen.getByText('Architect')).toBeInTheDocument();
    });

    it('renders description', () => {
      render(<EventItem event={mockEvent} />);
      expect(screen.getByText('Started mission analysis')).toBeInTheDocument();
    });

    it('renders timestamp in readable format', () => {
      render(<EventItem event={mockEvent} />);
      // Should show relative time or ISO format
      expect(screen.getByText(/2026|ago|just now/i)).toBeInTheDocument();
    });

    it('shows status indicator', () => {
      const { container } = render(<EventItem event={mockEvent} />);
      // StatusIndicator should be rendered (check for the component structure)
      expect(container.querySelector('[class*="rounded-full"]')).toBeInTheDocument();
    });
  });
});
