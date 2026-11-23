/**
 * Design System Tokens
 * Centralized theme configuration for the NeoEve Command Center
 *
 * CRITICAL: Separation of concerns
 * - Agent Status: operational state (IDLE, WORKING, ANALYZING, etc.)
 * - Connectivity Status: network state (ONLINE, OFFLINE, STALE, UNKNOWN)
 * These are NEVER conflated or derived from each other.
 */

export const theme = {
  colors: {
    /**
     * Semantic colors for agent operational states
     * Never use for connectivity status
     */
    semantic: {
      agentIdle: '#10b981',        // green-500 - Agent is idle/waiting
      agentWorking: '#f59e0b',     // amber-500 - Agent is actively working
      agentAnalyzing: '#06b6d4',   // cyan-500 - Agent is analyzing/thinking
      agentTesting: '#8b5cf6',     // violet-500 - Agent is running tests
      agentReviewing: '#ec4899',   // pink-500 - Agent is reviewing code/results
      agentBlocked: '#ef4444',     // red-500 - Agent is blocked/failed
      agentCompleted: '#14b8a6',   // teal-500 - Agent completed task
      agentError: '#dc2626',       // red-600 - Agent encountered error
    },

    /**
     * Connectivity colors for network state
     * Independent from agent operational state
     */
    connectivity: {
      online: '#10b981',      // green-500 - Connected
      offline: '#6b7280',     // slate-500 - Disconnected
      stale: '#f59e0b',       // amber-500 - Connection stale/degraded
      unknown: '#9ca3af',     // slate-400 - Unknown state
    },

    /**
     * Baseline colors for UI structure
     */
    baseline: {
      bg: '#0f172a',      // slate-900 - Main background
      card: '#1e293b',    // slate-800 - Card/panel background
      border: '#334155',  // slate-700 - Border color
      text: '#f1f5f9',    // slate-50 - Primary text color
    },
  },

  /**
   * Spacing scale in rem units (1rem = 16px by default)
   */
  spacing: {
    xs: '0.25rem',  // 4px
    sm: '0.5rem',   // 8px
    md: '1rem',     // 16px
    lg: '1.5rem',   // 24px
    xl: '2rem',     // 32px
  },

  /**
   * Typography scale
   */
  typography: {
    heading1: { size: '2rem', weight: 700 },
    heading2: { size: '1.5rem', weight: 600 },
    body: { size: '0.875rem', weight: 400 },
    mono: { size: '0.75rem', weight: 500 },
  },
} as const;

// Type safety: export theme type for components
export type Theme = typeof theme;
