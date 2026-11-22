/**
 * ErrorState - Display error message with optional retry action
 */

import React from 'react';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-lg bg-red-500/10 py-12 px-4">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-red-500 mb-2">Error</h3>
        <p className="text-sm text-slate-400">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
