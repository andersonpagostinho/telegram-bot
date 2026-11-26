/**
 * AppShell - Global application layout
 * Integrates Topbar, Sidebar, and main content area
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import Topbar from './Topbar';
import Sidebar from './Sidebar';
import ErrorBoundary from '../ErrorBoundary';
// TODO: Fix useWebSocket infinite loop issue before re-enabling
// import { useWebSocket } from '../../hooks/useWebSocket';

export default function AppShell() {
  // WebSocket connection with event subscriptions
  // TODO: Re-enable after fixing infinite update loop
  // useWebSocket({ eventTypes: ['AGENT_UPDATED', 'MISSION_UPDATED', 'EXECUTION_STARTED', 'EXECUTION_COMPLETED'] });
  return (
    <ErrorBoundary>
      <div
        data-testid="app-shell"
        className="flex min-h-screen bg-slate-900 text-slate-50"
      >
        {/* Sidebar */}
        <Sidebar />

        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Topbar */}
          <Topbar />

          {/* Page content */}
          <main
            role="main"
            className="flex-1 overflow-auto bg-slate-900 p-4 sm:p-6"
          >
            <Outlet />
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
