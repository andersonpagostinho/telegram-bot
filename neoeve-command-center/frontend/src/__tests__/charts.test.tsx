import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChartWrapper, MetricChart } from '../components/charts';

describe('Chart Components', () => {
  describe('ChartWrapper', () => {
    it('renders with title', () => {
      render(
        <ChartWrapper title="Test Chart">
          <div>Content</div>
        </ChartWrapper>
      );
      expect(screen.getByText('Test Chart')).toBeInTheDocument();
    });

    it('renders children', () => {
      render(
        <ChartWrapper title="Test">
          <div data-testid="test-content">Test Content</div>
        </ChartWrapper>
      );
      expect(screen.getByTestId('test-content')).toBeInTheDocument();
    });

    it('shows empty state when isEmpty=true', () => {
      render(
        <ChartWrapper title="Empty" isEmpty>
          <div>Should not see this</div>
        </ChartWrapper>
      );
      expect(screen.getByText(/no data/i)).toBeInTheDocument();
    });

    it('shows loading state when isLoading=true', () => {
      render(
        <ChartWrapper title="Loading" isLoading>
          <div>Should not see this</div>
        </ChartWrapper>
      );
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe('MetricChart', () => {
    it('renders without data (empty state)', () => {
      render(<MetricChart data={[]} metric="agents" />);
      expect(screen.getByText(/no data available/i)).toBeInTheDocument();
    });

    it('renders with data points', () => {
      const data = [
        { timestamp: '2026-11-22T10:00:00Z', value: 5 },
        { timestamp: '2026-11-22T11:00:00Z', value: 8 },
      ];
      render(<MetricChart data={data} metric="agents" />);
      // Chart should render title without empty state
      expect(screen.queryByText(/no data available/i)).not.toBeInTheDocument();
    });

    it('shows trend indicator when provided', () => {
      const data = [
        { timestamp: '2026-11-22T10:00:00Z', value: 5 },
        { timestamp: '2026-11-22T11:00:00Z', value: 8 },
      ];
      const { container } = render(
        <MetricChart data={data} metric="agents" trend="up" />
      );
      // Up trend should be indicated in title
      expect(container.textContent).toMatch(/agents.*↑/i);
    });

    it('renders with missions metric', () => {
      const data = [{ timestamp: '2026-11-22T10:00:00Z', value: 3 }];
      render(<MetricChart data={data} metric="missions" />);
      expect(screen.queryByText(/no data available/i)).not.toBeInTheDocument();
    });

    it('renders with executions metric', () => {
      const data = [{ timestamp: '2026-11-22T10:00:00Z', value: 15 }];
      render(<MetricChart data={data} metric="executions" />);
      expect(screen.queryByText(/no data available/i)).not.toBeInTheDocument();
    });
  });
});
