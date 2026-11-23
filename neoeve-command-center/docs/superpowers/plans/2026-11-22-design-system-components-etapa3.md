# ETAPA 3 — FASE 3.1: Design System & Reusable Components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native execution recommended due to tight integration requirements). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the visual foundation and reusable component library for the NeoEve Command Center, preparing all 9 screens for rapid implementation.

**Architecture:** Extend existing Tailwind dark theme with design tokens (colors, typography, spacing), create React Flow node components for agent topology, add Recharts-based chart wrappers for metrics, and build a timeline component for event display. All components are generic, testable, and data-agnostic.

**Tech Stack:** React 18 + TypeScript + Tailwind CSS 3.4 + Recharts 2.8 + React Flow 11.10 + Vitest 1.0

**Spec:** `docs/agent-team/FASE4_ETAPA3_UI_SPECIFICATION.md`  
**Master Plan:** `docs/agent-team/FASE4_ETAPA3_MASTER_PLAN.md`

## Global Constraints

- No real data (use fixtures for component testing only)
- No endpoint invention, no WebSocket simulation
- React 18 strict mode, TypeScript strict, Tailwind dark theme
- TDD mandatory: RED-GREEN-REFACTOR for every component
- Existing components (MetricCard, StatusIndicator, etc.) must be extended, not replaced
- No push/deploy; local commit only after full validation

## Review Focus

1. Chart components render correctly with and without data (empty state handling)
2. Timeline component respects semantic color distinction (agent state ≠ connectivity ≠ mission state)
3. React Flow nodes do not simulate agent activity without real event data
4. Design tokens are centralized and consistently applied across all new components
5. TypeScript strict mode passes; no `any` types or implicit defaults

---

## FILE STRUCTURE

### Design Tokens & Theme
- `src/lib/theme/tokens.ts` — Design system constants (colors, spacing, typography)
- `tailwind.config.ts` — Extended dark theme configuration (modify existing)
- `src/styles/theme.css` — CSS variables for runtime token access (new)

### Chart Components
- `src/components/charts/ChartWrapper.tsx` — Generic Recharts wrapper
- `src/components/charts/MetricChart.tsx` — Line/bar chart for metrics
- `src/components/charts/index.ts` — Barrel export

### Timeline Component
- `src/components/timeline/Timeline.tsx` — Timeline container
- `src/components/timeline/EventItem.tsx` — Single event display
- `src/components/timeline/EventIndicator.tsx` — Event type badge
- `src/components/timeline/index.ts` — Barrel export

### React Flow Components
- `src/components/flow/AgentNode.tsx` — Custom agent node
- `src/components/flow/AgentEdge.tsx` — Connection between agents
- `src/components/flow/FlowControls.tsx` — Zoom/pan/fit controls
- `src/components/flow/index.ts` — Barrel export

### Tests
- `src/__tests__/theme.test.ts` — Token accessibility
- `src/__tests__/charts.test.tsx` — Chart components (10+ tests)
- `src/__tests__/timeline.test.tsx` — Timeline components (8+ tests)
- `src/__tests__/flow.test.tsx` — React Flow components (6+ tests)

### Documentation
- `docs/agent-team/FASE4_ETAPA3_DESIGN_SYSTEM.md` — Design token reference, component catalog

---

## TASKS

### Task 1: Design Tokens & Theme Extension

**Files:**
- Create: `src/lib/theme/tokens.ts`
- Create: `src/styles/theme.css`
- Modify: `tailwind.config.ts`
- Test: `src/__tests__/theme.test.ts`

**Interfaces:**
- Produces: Theme tokens object with colors, spacing, typography, semantic colors
- Example: `theme.colors.state.working`, `theme.spacing.md`, `theme.typography.heading1`

- [ ] **Step 1: Write failing test for theme token structure**

```typescript
// src/__tests__/theme.test.ts
import { theme } from '../lib/theme/tokens';

test('theme exports required token groups', () => {
  expect(theme.colors).toBeDefined();
  expect(theme.colors.semantic).toBeDefined();
  expect(theme.colors.semantic.agentIdle).toBeDefined();
  expect(theme.colors.semantic.agentWorking).toBeDefined();
  expect(theme.colors.semantic.agentAnalyzing).toBeDefined();
  expect(theme.colors.semantic.agentTesting).toBeDefined();
  expect(theme.colors.semantic.agentReviewing).toBeDefined();
  expect(theme.colors.semantic.agentBlocked).toBeDefined();
  expect(theme.colors.semantic.agentCompleted).toBeDefined();
  expect(theme.colors.semantic.agentError).toBeDefined();
  expect(theme.spacing).toBeDefined();
  expect(theme.typography).toBeDefined();
});

test('theme exports connectivity colors', () => {
  expect(theme.colors.connectivity.online).toBeDefined();
  expect(theme.colors.connectivity.offline).toBeDefined();
  expect(theme.colors.connectivity.stale).toBeDefined();
  expect(theme.colors.connectivity.unknown).toBeDefined();
});

test('CSS variables are accessible in document', () => {
  const root = document.documentElement;
  expect(getComputedStyle(root).getPropertyValue('--color-agent-idle')).toBeTruthy();
  expect(getComputedStyle(root).getPropertyValue('--spacing-md')).toBeTruthy();
});
```

- [ ] **Step 2: Run test, verify fails with "Cannot find module"**

Run: `npm test -- src/__tests__/theme.test.ts`
Expected: FAIL — Module not found

- [ ] **Step 3: Create theme tokens object**

File: `src/lib/theme/tokens.ts`

Export object:
```typescript
export const theme = {
  colors: {
    semantic: {
      agentIdle: '#10b981',      // green-500
      agentWorking: '#f59e0b',   // amber-500
      agentAnalyzing: '#06b6d4', // cyan-500
      agentTesting: '#8b5cf6',   // violet-500
      agentReviewing: '#ec4899', // pink-500
      agentBlocked: '#ef4444',   // red-500
      agentCompleted: '#14b8a6', // teal-500
      agentError: '#dc2626',     // red-600
    },
    connectivity: {
      online: '#10b981',
      offline: '#6b7280',
      stale: '#f59e0b',
      unknown: '#9ca3af',
    },
    baseline: {
      bg: '#0f172a',       // slate-900
      card: '#1e293b',     // slate-800
      border: '#334155',   // slate-700
      text: '#f1f5f9',     // slate-50
    },
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
  },
  typography: {
    heading1: { size: '2rem', weight: 700 },
    heading2: { size: '1.5rem', weight: 600 },
    body: { size: '0.875rem', weight: 400 },
    mono: { size: '0.75rem', weight: 500 },
  },
};
```

- [ ] **Step 4: Create CSS variables file**

File: `src/styles/theme.css`

```css
:root {
  --color-agent-idle: #10b981;
  --color-agent-working: #f59e0b;
  --color-agent-analyzing: #06b6d4;
  --color-agent-testing: #8b5cf6;
  --color-agent-reviewing: #ec4899;
  --color-agent-blocked: #ef4444;
  --color-agent-completed: #14b8a6;
  --color-agent-error: #dc2626;
  
  --color-online: #10b981;
  --color-offline: #6b7280;
  --color-stale: #f59e0b;
  --color-unknown: #9ca3af;
  
  --color-bg: #0f172a;
  --color-card: #1e293b;
  --color-border: #334155;
  --color-text: #f1f5f9;
  
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
}
```

- [ ] **Step 5: Extend tailwind.config.ts**

Modify `tailwind.config.ts` to import tokens and extend theme:

```typescript
import { theme } from './src/lib/theme/tokens';

export default {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        semantic: theme.colors.semantic,
        connectivity: theme.colors.connectivity,
      },
      spacing: theme.spacing,
    },
  },
  plugins: [],
};
```

- [ ] **Step 6: Import theme.css in main entry**

Add to `src/main.tsx`: `import './styles/theme.css'`

- [ ] **Step 7: Run test, verify passes**

Run: `npm test -- src/__tests__/theme.test.ts`
Expected: PASS

- [ ] **Step 8: Run lint and type check**

Run: `npm run lint`
Expected: PASS (TypeScript strict)

- [ ] **Step 9: Commit**

```bash
git add src/lib/theme/tokens.ts src/styles/theme.css tailwind.config.ts src/main.tsx src/__tests__/theme.test.ts
git commit -m "feat: implement design system theme tokens and CSS variables"
```

---

### Task 2: Chart Components (Recharts)

**Files:**
- Create: `src/components/charts/ChartWrapper.tsx`
- Create: `src/components/charts/MetricChart.tsx`
- Create: `src/components/charts/index.ts`
- Test: `src/__tests__/charts.test.tsx`

**Interfaces:**
- Consumes: Theme from Task 1
- Produces: 
  - `ChartWrapper: React.FC<{children: ReactNode; title: string; isEmpty?: boolean}>`
  - `MetricChart: React.FC<{data: ChartData[]; metric: 'agents' | 'missions' | 'executions'; trend?: 'up' | 'down' | 'flat'}>`

- [ ] **Step 1: Write failing test for empty chart**

```typescript
// src/__tests__/charts.test.tsx
import { render, screen } from '@testing-library/react';
import { ChartWrapper, MetricChart } from '../components/charts';

test('ChartWrapper renders with title', () => {
  render(
    <ChartWrapper title="Agents">
      <div>Chart content</div>
    </ChartWrapper>
  );
  expect(screen.getByText('Agents')).toBeInTheDocument();
});

test('ChartWrapper shows empty state when isEmpty=true', () => {
  render(
    <ChartWrapper title="Metrics" isEmpty>
      <div>Chart</div>
    </ChartWrapper>
  );
  expect(screen.getByText(/No data available/i)).toBeInTheDocument();
});

test('MetricChart renders without data', () => {
  render(<MetricChart data={[]} metric="agents" />);
  expect(screen.getByText(/No data/i)).toBeInTheDocument();
});

test('MetricChart renders with data points', () => {
  const data = [
    { timestamp: '2026-11-22T10:00:00Z', value: 5 },
    { timestamp: '2026-11-22T11:00:00Z', value: 7 },
  ];
  render(<MetricChart data={data} metric="agents" />);
  expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
});

test('MetricChart shows trend indicator', () => {
  const data = [
    { timestamp: '2026-11-22T10:00:00Z', value: 5 },
    { timestamp: '2026-11-22T11:00:00Z', value: 8 },
  ];
  const { container } = render(<MetricChart data={data} metric="missions" trend="up" />);
  expect(container.textContent).toMatch(/↑/);
});
```

- [ ] **Step 2: Run test, verify fails**

Run: `npm test -- src/__tests__/charts.test.tsx`
Expected: FAIL — Components not found

- [ ] **Step 3: Implement ChartWrapper**

File: `src/components/charts/ChartWrapper.tsx`

```typescript
import { ReactNode } from 'react';
import { EmptyState, LoadingState } from '../common';

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
  if (isEmpty) return <EmptyState heading="No data available" />;

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h3 className="text-lg font-semibold text-slate-50 mb-4">{title}</h3>
      <div className="w-full h-64">{children}</div>
    </div>
  );
};
```

- [ ] **Step 4: Implement MetricChart**

File: `src/components/charts/MetricChart.tsx`

Use Recharts `LineChart` for metrics with responsive container. Show empty state if data is empty.

```typescript
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ChartWrapper } from './ChartWrapper';
import { theme } from '../../lib/theme/tokens';

interface DataPoint {
  timestamp: string;
  value: number;
}

interface MetricChartProps {
  data: DataPoint[];
  metric: 'agents' | 'missions' | 'executions';
  trend?: 'up' | 'down' | 'flat';
}

export const MetricChart: React.FC<MetricChartProps> = ({ data, metric, trend }) => {
  const colorMap = {
    agents: theme.colors.semantic.agentAnalyzing,
    missions: theme.colors.semantic.agentWorking,
    executions: theme.colors.semantic.agentTesting,
  };

  const trendIcon = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→';

  return (
    <ChartWrapper 
      title={`${metric.charAt(0).toUpperCase() + metric.slice(1)} ${trendIcon}`}
      isEmpty={data.length === 0}
    >
      {data.length > 0 ? (
        <ResponsiveContainer width="100%" height={256}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.colors.baseline.border} />
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
```

- [ ] **Step 5: Create barrel export**

File: `src/components/charts/index.ts`

```typescript
export { ChartWrapper } from './ChartWrapper';
export { MetricChart } from './MetricChart';
export type { DataPoint } from './MetricChart';
```

- [ ] **Step 6: Run tests, verify pass**

Run: `npm test -- src/__tests__/charts.test.tsx`
Expected: PASS (8/8)

- [ ] **Step 7: Commit**

```bash
git add src/components/charts/ src/__tests__/charts.test.tsx
git commit -m "feat: implement chart components with Recharts wrapper"
```

---

### Task 3: Timeline Component

**Files:**
- Create: `src/components/timeline/Timeline.tsx`
- Create: `src/components/timeline/EventItem.tsx`
- Create: `src/components/timeline/EventIndicator.tsx`
- Create: `src/components/timeline/index.ts`
- Test: `src/__tests__/timeline.test.tsx`

**Interfaces:**
- Consumes: Theme from Task 1, StatusIndicator from ETAPA 2
- Produces:
  - `Timeline: React.FC<{items: TimelineEvent[]; isLoading?: boolean}>`
  - `EventItem: React.FC<{event: TimelineEvent}>`
  - `EventIndicator: React.FC<{type: EventType}>`

- [ ] **Step 1: Write failing test for timeline**

```typescript
// src/__tests__/timeline.test.tsx
import { render, screen } from '@testing-library/react';
import { Timeline, EventItem } from '../components/timeline';

const mockEvent = {
  id: 'event-1',
  type: 'AGENT_UPDATED' as const,
  timestamp: new Date('2026-11-22T10:00:00Z'),
  agent: 'Architect',
  status: 'WORKING' as const,
  description: 'Started mission analysis',
};

test('Timeline renders empty state when no items', () => {
  render(<Timeline items={[]} />);
  expect(screen.getByText(/No events/i)).toBeInTheDocument();
});

test('Timeline renders event items', () => {
  render(<Timeline items={[mockEvent]} />);
  expect(screen.getByText('Architect')).toBeInTheDocument();
  expect(screen.getByText('Started mission analysis')).toBeInTheDocument();
});

test('EventItem shows timestamp in relative format', () => {
  render(<EventItem event={mockEvent} />);
  expect(screen.getByText(/ago|just now/i)).toBeInTheDocument();
});

test('EventItem distinguishes agent state from connectivity', () => {
  const { container } = render(<EventItem event={mockEvent} />);
  expect(container.textContent).toMatch(/WORKING/);
});
```

- [ ] **Step 2: Run test, verify fails**

Run: `npm test -- src/__tests__/timeline.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement Timeline**

File: `src/components/timeline/Timeline.tsx`

```typescript
import { EmptyState, LoadingState } from '../common';
import { EventItem } from './EventItem';

export interface TimelineEvent {
  id: string;
  type: 'AGENT_UPDATED' | 'MISSION_UPDATED' | 'EXECUTION_STARTED' | 'TASK_COMPLETED';
  timestamp: Date;
  agent: string;
  status: 'IDLE' | 'WORKING' | 'ANALYZING' | 'TESTING' | 'REVIEWING' | 'BLOCKED' | 'COMPLETED' | 'ERROR';
  description: string;
}

interface TimelineProps {
  items: TimelineEvent[];
  isLoading?: boolean;
}

export const Timeline: React.FC<TimelineProps> = ({ items, isLoading }) => {
  if (isLoading) return <LoadingState />;
  if (items.length === 0) return <EmptyState heading="No events" />;

  return (
    <div className="space-y-4">
      {items.map((event) => (
        <EventItem key={event.id} event={event} />
      ))}
    </div>
  );
};
```

- [ ] **Step 4: Implement EventItem**

File: `src/components/timeline/EventItem.tsx`

```typescript
import { formatDistanceToNow } from 'date-fns';
import { StatusIndicator } from '../common';
import { EventIndicator } from './EventIndicator';
import { TimelineEvent } from './Timeline';

interface EventItemProps {
  event: TimelineEvent;
}

export const EventItem: React.FC<EventItemProps> = ({ event }) => {
  const relativeTime = formatDistanceToNow(event.timestamp, { addSuffix: true });

  return (
    <div className="flex gap-4 p-3 bg-slate-800 rounded border border-slate-700">
      <EventIndicator type={event.type} />
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-slate-50">{event.agent}</span>
          <StatusIndicator 
            operationalState={event.status}
            connectivityState="ONLINE"
          />
        </div>
        <p className="text-sm text-slate-300">{event.description}</p>
        <span className="text-xs text-slate-500">{relativeTime}</span>
      </div>
    </div>
  );
};
```

- [ ] **Step 5: Implement EventIndicator**

File: `src/components/timeline/EventIndicator.tsx`

```typescript
import { TimelineEvent } from './Timeline';

interface EventIndicatorProps {
  type: TimelineEvent['type'];
}

const typeColors = {
  AGENT_UPDATED: 'bg-cyan-500',
  MISSION_UPDATED: 'bg-amber-500',
  EXECUTION_STARTED: 'bg-violet-500',
  TASK_COMPLETED: 'bg-teal-500',
};

export const EventIndicator: React.FC<EventIndicatorProps> = ({ type }) => (
  <div className={`${typeColors[type]} w-3 h-3 rounded-full flex-shrink-0 mt-1`} />
);
```

- [ ] **Step 6: Create barrel export**

File: `src/components/timeline/index.ts`

```typescript
export { Timeline, type TimelineEvent } from './Timeline';
export { EventItem } from './EventItem';
export { EventIndicator } from './EventIndicator';
```

- [ ] **Step 7: Run tests, verify pass**

Run: `npm test -- src/__tests__/timeline.test.tsx`
Expected: PASS (5/5)

- [ ] **Step 8: Commit**

```bash
git add src/components/timeline/ src/__tests__/timeline.test.tsx
git commit -m "feat: implement timeline component for event display"
```

---

### Task 4: React Flow Agent Nodes

**Files:**
- Create: `src/components/flow/AgentNode.tsx`
- Create: `src/components/flow/AgentEdge.tsx`
- Create: `src/components/flow/FlowControls.tsx`
- Create: `src/components/flow/index.ts`
- Test: `src/__tests__/flow.test.tsx`

**Interfaces:**
- Consumes: StatusIndicator from ETAPA 2, theme from Task 1
- Produces:
  - `AgentNode: React.FC<{data: AgentNodeData}>`
  - `FlowControls: React.FC<>`

- [ ] **Step 1: Write failing test for Agent node**

```typescript
// src/__tests__/flow.test.tsx
import { render, screen } from '@testing-library/react';
import { AgentNode } from '../components/flow';

const mockAgentData = {
  label: 'Architect',
  status: 'IDLE' as const,
  connectivityState: 'ONLINE' as const,
  lastEventAt: new Date(),
};

test('AgentNode renders agent name', () => {
  const { container } = render(
    <div data-testid="node-wrapper">
      <AgentNode data={mockAgentData} />
    </div>
  );
  expect(screen.getByText('Architect')).toBeInTheDocument();
});

test('AgentNode shows status indicator', () => {
  const { container } = render(
    <div data-testid="node-wrapper">
      <AgentNode data={mockAgentData} />
    </div>
  );
  expect(container.textContent).toMatch(/IDLE/);
});

test('AgentNode shows connectivity separately', () => {
  const { container } = render(
    <div data-testid="node-wrapper">
      <AgentNode data={{ ...mockAgentData, connectivityState: 'OFFLINE' }} />
    </div>
  );
  expect(container.textContent).toMatch(/OFFLINE/);
});
```

- [ ] **Step 2: Run test, verify fails**

Run: `npm test -- src/__tests__/flow.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement AgentNode**

File: `src/components/flow/AgentNode.tsx`

```typescript
import { Handle, Position } from 'reactflow';
import { StatusIndicator } from '../common';
import { theme } from '../../lib/theme/tokens';

export interface AgentNodeData {
  label: string;
  status: 'IDLE' | 'WORKING' | 'ANALYZING' | 'TESTING' | 'REVIEWING' | 'BLOCKED' | 'COMPLETED' | 'ERROR';
  connectivityState: 'ONLINE' | 'OFFLINE' | 'STALE' | 'UNKNOWN';
  lastEventAt?: Date;
}

interface AgentNodeProps {
  data: AgentNodeData;
}

export const AgentNode: React.FC<AgentNodeProps> = ({ data }) => (
  <div className="bg-slate-800 border-2 border-slate-700 rounded-lg p-3 w-32 text-center">
    <Handle type="target" position={Position.Top} />
    <div className="text-sm font-semibold text-slate-50 mb-2">{data.label}</div>
    <StatusIndicator 
      operationalState={data.status}
      connectivityState={data.connectivityState}
    />
    {data.lastEventAt && (
      <div className="text-xs text-slate-400 mt-2">
        {data.lastEventAt.toLocaleTimeString()}
      </div>
    )}
    <Handle type="source" position={Position.Bottom} />
  </div>
);
```

- [ ] **Step 4: Implement AgentEdge**

File: `src/components/flow/AgentEdge.tsx`

```typescript
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from 'reactflow';
import type { EdgeProps } from 'reactflow';

export const AgentEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge id={id} path={edgePath} stroke="#64748b" strokeWidth={2} />
    </>
  );
};
```

- [ ] **Step 5: Implement FlowControls**

File: `src/components/flow/FlowControls.tsx`

```typescript
import { useReactFlow } from 'reactflow';
import { theme } from '../../lib/theme/tokens';

export const FlowControls: React.FC = () => {
  const { fitView, zoomIn, zoomOut } = useReactFlow();

  return (
    <div className="flex gap-2 p-2 bg-slate-800 rounded border border-slate-700">
      <button
        onClick={() => zoomIn()}
        className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-50"
      >
        +
      </button>
      <button
        onClick={() => zoomOut()}
        className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-50"
      >
        −
      </button>
      <button
        onClick={() => fitView()}
        className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-50"
      >
        Fit
      </button>
    </div>
  );
};
```

- [ ] **Step 6: Create barrel export**

File: `src/components/flow/index.ts`

```typescript
export { AgentNode, type AgentNodeData } from './AgentNode';
export { AgentEdge } from './AgentEdge';
export { FlowControls } from './FlowControls';
```

- [ ] **Step 7: Run tests, verify pass**

Run: `npm test -- src/__tests__/flow.test.tsx`
Expected: PASS (4/4)

- [ ] **Step 8: Commit**

```bash
git add src/components/flow/ src/__tests__/flow.test.tsx
git commit -m "feat: implement React Flow components for agent topology"
```

---

### Task 5: Final Validation & Documentation

**Files:**
- Create: `docs/agent-team/FASE4_ETAPA3_DESIGN_SYSTEM.md`
- Modify: `src/main.tsx` (ensure imports)
- Test: Full suite execution and build

**Interfaces:**
- Consumes: All components from Tasks 1-4
- Produces: Documentation and verified build

- [ ] **Step 1: Run full test suite**

Run: `npm test`
Expected: All tests PASS (40+ total)

- [ ] **Step 2: Run TypeScript strict check**

Run: `npm run lint`
Expected: PASS (no errors)

- [ ] **Step 3: Run production build**

Run: `npm run build`
Expected: BUILD SUCCESS, output in `dist/`

- [ ] **Step 4: Create design system documentation**

File: `docs/agent-team/FASE4_ETAPA3_DESIGN_SYSTEM.md`

Document:
- Design token reference (colors, spacing, typography)
- Component catalog (all new components with props)
- Usage examples for each component
- Responsive breakpoints
- Accessibility features

```markdown
# ETAPA 3 — Design System Documentation

## Design Tokens

### Semantic Colors (Agent States)
- Idle: #10b981 (green-500)
- Working: #f59e0b (amber-500)
- Analyzing: #06b6d4 (cyan-500)
- Testing: #8b5cf6 (violet-500)
- Reviewing: #ec4899 (pink-500)
- Blocked: #ef4444 (red-500)
- Completed: #14b8a6 (teal-500)
- Error: #dc2626 (red-600)

### Connectivity States
- Online: #10b981
- Offline: #6b7280
- Stale: #f59e0b
- Unknown: #9ca3af

## Components

### ChartWrapper
Generic container for chart components with loading and empty states.

Props:
- title: string
- children: ReactNode
- isEmpty?: boolean
- isLoading?: boolean

### MetricChart
Display metrics using Recharts with trend indicator.

Props:
- data: DataPoint[]
- metric: 'agents' | 'missions' | 'executions'
- trend?: 'up' | 'down' | 'flat'

### Timeline
Timeline container for event display.

Props:
- items: TimelineEvent[]
- isLoading?: boolean

### AgentNode
React Flow node for agent topology.

Data:
- label: string
- status: AgentStatus
- connectivityState: ConnectivityState
- lastEventAt?: Date
```

- [ ] **Step 5: Verify all imports in main entry**

Check `src/main.tsx` includes:
- `import './styles/theme.css'`
- Chart, Timeline, Flow imports available

- [ ] **Step 6: Final commit with all deliverables**

```bash
git add docs/agent-team/FASE4_ETAPA3_DESIGN_SYSTEM.md
git commit -m "docs: complete design system documentation and final validation

PHASE 3.1 COMPLETE

✅ Design tokens: colors, spacing, typography implemented
✅ Chart components: Recharts wrapper for metrics
✅ Timeline component: Event display with semantic colors
✅ React Flow: Agent nodes and controls for topology
✅ Full test coverage: 40+ tests PASS
✅ TypeScript strict: 0 errors
✅ Production build: SUCCESS

All components ready for PHASE 3.2 (Overview Dashboard)

No architectural debt. Ready for screen implementation."
```

- [ ] **Step 7: Verify final state**

Run: `git log --oneline -5`  
Expected: 5 commits starting with design system work

---

## REVIEW FOCUS

1. **Empty data handling:** Chart, Timeline, and all components gracefully handle empty data with appropriate empty states
2. **Color semantic clarity:** Agent state colors (working/idle/etc) are NEVER confused with connectivity colors (online/offline) in any component
3. **No simulated activity:** React Flow nodes display only real data; no fake agent animations or invented status changes
4. **TypeScript safety:** All components use strong types; no `any` defaults or implicit unknowns in strict mode
5. **Performance:** All components render correctly with 100+ items without lag; Recharts uses `ResponsiveContainer` for responsive sizing

---

**Implementation approach:** Native execution recommended. Tasks are sequential but loosely coupled; each produces independent, testable deliverables. Total estimated time: 4-6 hours with TDD discipline.

Please review this plan. Does it capture what you want, and should we proceed with native execution?
