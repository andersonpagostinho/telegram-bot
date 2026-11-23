import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ChartWrapper } from './ChartWrapper';
import { theme } from '../../lib/theme/tokens';

export interface DataPoint {
  timestamp: string;
  value: number;
}

interface MetricChartProps {
  data: DataPoint[];
  metric: 'agents' | 'missions' | 'executions';
  trend?: 'up' | 'down' | 'flat';
}

const colorMap: Record<string, string> = {
  agents: theme.colors.semantic.agentAnalyzing,
  missions: theme.colors.semantic.agentWorking,
  executions: theme.colors.semantic.agentTesting,
};

export const MetricChart: React.FC<MetricChartProps> = ({
  data,
  metric,
  trend,
}) => {
  const trendIcon = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→';

  return (
    <ChartWrapper
      title={`${metric.charAt(0).toUpperCase() + metric.slice(1)} ${trendIcon}`}
      isEmpty={data.length === 0}
    >
      {data.length > 0 ? (
        <ResponsiveContainer width="100%" height={256}>
          <LineChart data={data}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={theme.colors.baseline.border}
            />
            <XAxis
              dataKey="timestamp"
              stroke={theme.colors.baseline.text}
              tick={{ fontSize: 12 }}
            />
            <YAxis stroke={theme.colors.baseline.text} />
            <Tooltip
              contentStyle={{
                backgroundColor: theme.colors.baseline.card,
                border: `1px solid ${theme.colors.baseline.border}`,
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={colorMap[metric]}
              dot={{ fill: colorMap[metric] }}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : null}
    </ChartWrapper>
  );
};
