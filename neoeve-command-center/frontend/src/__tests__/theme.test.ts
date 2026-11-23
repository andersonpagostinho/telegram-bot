import { describe, it, expect } from 'vitest';
import { theme } from '../lib/theme/tokens';

describe('Design System Tokens', () => {
  it('should export theme object with colors group', () => {
    expect(theme).toBeDefined();
    expect(theme.colors).toBeDefined();
  });

  it('should export semantic colors for all agent states', () => {
    expect(theme.colors.semantic).toBeDefined();
    expect(theme.colors.semantic.agentIdle).toBe('#10b981');
    expect(theme.colors.semantic.agentWorking).toBe('#f59e0b');
    expect(theme.colors.semantic.agentAnalyzing).toBe('#06b6d4');
    expect(theme.colors.semantic.agentTesting).toBe('#8b5cf6');
    expect(theme.colors.semantic.agentReviewing).toBe('#ec4899');
    expect(theme.colors.semantic.agentBlocked).toBe('#ef4444');
    expect(theme.colors.semantic.agentCompleted).toBe('#14b8a6');
    expect(theme.colors.semantic.agentError).toBe('#dc2626');
  });

  it('should export connectivity colors separately from agent states', () => {
    expect(theme.colors.connectivity).toBeDefined();
    expect(theme.colors.connectivity.online).toBe('#10b981');
    expect(theme.colors.connectivity.offline).toBe('#6b7280');
    expect(theme.colors.connectivity.stale).toBe('#f59e0b');
    expect(theme.colors.connectivity.unknown).toBe('#9ca3af');
  });

  it('should export baseline colors', () => {
    expect(theme.colors.baseline).toBeDefined();
    expect(theme.colors.baseline.bg).toBe('#0f172a');
    expect(theme.colors.baseline.card).toBe('#1e293b');
    expect(theme.colors.baseline.border).toBe('#334155');
    expect(theme.colors.baseline.text).toBe('#f1f5f9');
  });

  it('should export spacing tokens', () => {
    expect(theme.spacing).toBeDefined();
    expect(theme.spacing.xs).toBe('0.25rem');
    expect(theme.spacing.sm).toBe('0.5rem');
    expect(theme.spacing.md).toBe('1rem');
    expect(theme.spacing.lg).toBe('1.5rem');
    expect(theme.spacing.xl).toBe('2rem');
  });

  it('should export typography tokens', () => {
    expect(theme.typography).toBeDefined();
    expect(theme.typography.heading1).toBeDefined();
    expect(theme.typography.body).toBeDefined();
    expect(theme.typography.mono).toBeDefined();
  });
});
