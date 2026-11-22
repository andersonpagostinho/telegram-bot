/**
 * Topbar - Application header with WebSocket indicator
 * Shows real connection state from Zustand store
 */

import React from 'react';
import { useAuthStore, useWebSocketStore } from '../../store';
import clsx from 'clsx';

export default function Topbar() {
  const { user } = useAuthStore();
  const { isConnected } = useWebSocketStore();

  return (
    <header
      role="banner"
      className="flex items-center justify-between border-b border-slate-800 bg-slate-800 px-6 py-4"
    >
      {/* Left side - Title */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-slate-50">
          NeoEve Command Center
        </h1>
      </div>

      {/* Right side - Status and User Info */}
      <div className="flex items-center gap-6">
        {/* WebSocket Indicator */}
        <div
          data-testid="ws-indicator"
          className="flex items-center gap-2"
        >
          <span
            className={clsx(
              'h-2 w-2 rounded-full transition-colors',
              isConnected
                ? 'bg-green-500'
                : 'bg-red-500'
            )}
          />
          <span className="text-xs text-slate-400">
            {isConnected ? 'Connected' : 'Offline'}
          </span>
        </div>

        {/* User Area */}
        {user && (
          <div
            data-testid="user-area"
            className="flex items-center gap-2 rounded-lg bg-slate-700 px-3 py-2"
          >
            <span className="text-sm text-slate-50">{user.actor_role}</span>
          </div>
        )}
      </div>
    </header>
  );
}
