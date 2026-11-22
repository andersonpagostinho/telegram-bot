/**
 * EmptyState - Display empty state for lists and areas without data
 */

import React from 'react';

interface EmptyStateProps {
  message: string;
  guidance?: string;
  icon?: string;
}

export default function EmptyState({
  message,
  guidance,
  icon = '📭',
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-lg bg-slate-800/50 py-12 px-4">
      <span className="text-4xl">{icon}</span>
      <div className="text-center">
        <h3 className="text-lg font-semibold text-slate-50">{message}</h3>
        {guidance && (
          <p className="mt-2 text-sm text-slate-400">{guidance}</p>
        )}
      </div>
    </div>
  );
}
