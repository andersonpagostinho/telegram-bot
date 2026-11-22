/**
 * LoadingState - Display loading indicator with optional message
 */

import React from 'react';

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({
  message = 'Loading...',
}: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12">
      <div data-testid="loading-spinner" className="flex gap-1">
        <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500" />
        <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500" style={{ animationDelay: '0.1s' }} />
        <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500" style={{ animationDelay: '0.2s' }} />
      </div>
      <p className="text-sm text-slate-400">{message}</p>
    </div>
  );
}
