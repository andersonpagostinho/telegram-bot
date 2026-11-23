import { ReactNode } from 'react';
import { LoadingState, EmptyState } from '../common';

interface ChartWrapperProps {
  title: string;
  children: ReactNode;
  isEmpty?: boolean;
  isLoading?: boolean;
}

export const ChartWrapper: React.FC<ChartWrapperProps> = ({
  title,
  children,
  isEmpty,
  isLoading,
}) => {
  if (isLoading) return <LoadingState />;
  if (isEmpty) return <EmptyState message="No data available" />;

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h3 className="text-lg font-semibold text-slate-50 mb-4">{title}</h3>
      <div className="w-full h-64">{children}</div>
    </div>
  );
};
