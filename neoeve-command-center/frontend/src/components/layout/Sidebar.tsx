/**
 * Sidebar - Main navigation component
 * Integrates with Zustand for expand/collapse state
 */

import React, { useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useUIStore } from '../../store';
import clsx from 'clsx';

interface NavItem {
  label: string;
  path: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', path: '/', icon: '📊' },
  { label: 'Agent Map', path: '/agents', icon: '🕸️' },
  { label: 'Activity Stream', path: '/activity', icon: '📡' },
];

export default function Sidebar() {
  // Use memoized selectors to prevent unnecessary re-renders
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const navItems = useMemo(() => NAV_ITEMS, []);

  return (
    <aside
      data-testid="sidebar"
      className={clsx(
        'flex flex-col border-r border-slate-800 bg-slate-800 transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-20'
      )}
    >
      {/* Sidebar Header */}
      <div className="flex h-16 items-center justify-between border-b border-slate-700 px-4">
        {sidebarOpen && (
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-slate-50">NeoEve</span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded-lg p-2 hover:bg-slate-700 transition-colors"
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? '←' : '→'}
        </button>
      </div>

      {/* Navigation Items */}
      <nav role="navigation" className="flex-1 space-y-2 overflow-y-auto px-2 py-4">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={clsx(
              'flex items-center gap-3 rounded-lg px-3 py-2 transition-colors',
              isActive(item.path)
                ? 'bg-blue-600 text-slate-50'
                : 'text-slate-400 hover:bg-slate-700 hover:text-slate-50'
            )}
          >
            <span data-testid="nav-icon" className="text-xl">
              {item.icon}
            </span>
            {sidebarOpen && (
              <span className="truncate text-sm font-medium">{item.label}</span>
            )}
          </Link>
        ))}
      </nav>

      {/* Sidebar Footer */}
      <div className="border-t border-slate-700 p-4">
        {sidebarOpen && (
          <p className="text-xs text-slate-500">© 2026 NeoEve</p>
        )}
      </div>
    </aside>
  );
}
