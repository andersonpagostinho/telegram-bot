# NeoEve Command Center — Frontend Architecture

## Overview

The frontend is built as a **modern React 18 application** with strict TypeScript, emphasizing:
- **Separation of concerns** (data, state, presentation)
- **Type safety** throughout the stack
- **Multi-tenant isolation** at every layer
- **Real-time event integration** with automatic reconnection
- **Security-first** design (no secrets in frontend, centralized API client)

## Layered Architecture

```
┌─────────────────────────────────────────┐
│         React Components                │  UI Layer (Layout, Common, Pages)
│    (AppShell, Sidebar, Cards, etc)      │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│      Custom Hooks Layer                 │  Data Integration
│  (useAgents, useMissions, etc)          │  (TanStack Query + WebSocket)
└────────────┬────────────────────────────┘
             │
        ┌────┴──────────────┐
        │                   │
┌───────▼────────┐  ┌──────▼─────────┐
│  REST Data     │  │  Real-Time     │
│  TanStack      │  │  WebSocket     │
│  Query         │  │  Service       │
└───────┬────────┘  └──────┬─────────┘
        │                  │
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │  API Client      │
        │  (HTTP + JWT)    │
        │  Error Handler   │
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │  Zustand Stores  │
        │  (UI State Only) │
        └──────────────────┘
                 │
        ┌────────▼─────────┐
        │  Backend API     │
        │  (HTTP + WS)     │
        └──────────────────┘
```

## Component Layers

### 1. Presentation Layer (Components)

**Layout Components** (`src/components/layout/`):
- **AppShell.tsx** — Root wrapper with Sidebar + Topbar + main content area
- **Sidebar.tsx** — Collapsible navigation with Zustand integration
- **Topbar.tsx** — Header with real WebSocket connection indicator
- **PageHeader.tsx** — Page title with optional action area
- **ErrorBoundary.tsx** — React error boundary with retry

**Common Components** (`src/components/common/`):
- **StatusIndicator.tsx** — Operational + connectivity status display
- **MetricCard.tsx** — Metric value display with optional variation
- **AgentCard.tsx** — Agent information card
- **LoadingState.tsx** — Loading indicator with message
- **ErrorState.tsx** — Error display with optional retry
- **EmptyState.tsx** — Empty state for no-data scenarios

**Page Components** (`src/pages/`):
- **Overview.tsx** — Dashboard overview (stub)
- **NotFound.tsx** — 404 error page

### 2. Data Integration Layer (Hooks)

**Custom Hooks** (`src/hooks/`):

**useAgents(params?)** — Query agents via TanStack Query
```typescript
const { data, isLoading, error } = useAgents({ page: 1, per_page: 20 });
```
- Returns: `{ data: AgentListResponse, isLoading, error, ... }`
- Automatic caching (5min stale time, 10min garbage collection)
- Invalidates on AGENT_UPDATED/AGENT_STATUS_CHANGED events

**useMissions(params?)** — Query missions with filtering
```typescript
const { data, isLoading } = useMissions({ status: 'RUNNING', page: 1 });
```
- Supports: `status`, `days`, pagination
- Cache invalidates on MISSION_* events

**useExecutions(params?)** — Query executions with filtering
```typescript
const { data } = useExecutions({ mission_id: 'x', agent_id: 'y' });
```
- Supports: `mission_id`, `agent_id`, pagination
- Cache invalidates on EXECUTION_* events

**useWebSocket(options?)** — WebSocket integration
```typescript
const { isConnected, connect, disconnect } = useWebSocket({
  eventTypes: ['MISSION_UPDATED', 'AGENT_STATUS_CHANGED']
});
```
- Single connection per session (singleton pattern)
- Automatic reconnection with exponential backoff
- Cache invalidation on relevant events
- Cursor tracking for event recovery

### 3. Data Fetching & Caching (TanStack Query)

**Purpose:** REST API data layer with automatic caching and synchronization

**Configuration** (`src/lib/queryClient.ts`):
- Stale time: 5 minutes
- GC time: 10 minutes
- Retry: 1 attempt
- No refetch on window focus

**Cache Invalidation:** Triggered by WebSocket events
- AGENT_UPDATED → invalidate `['agents']`
- MISSION_UPDATED → invalidate `['missions']`
- EXECUTION_STARTED → invalidate `['executions']`

## State Management

### Zustand Stores (Transient UI State Only)

**Rule:** Zustand stores ONLY contain UI state (preferences, loading UI state). Never duplicate data from TanStack Query.

**Auth Store** (`src/store/auth.ts`):
```typescript
useAuthStore.getState()
  .setAuth(user, token)   // Set user and JWT token
  .setLoading(true)       // Set loading flag
  .setError(msg)          // Set error message
  .reset()                // Clear auth state
```
- User identity from backend
- JWT token (memory-only, never localStorage)
- Loading state for auth operations

**WebSocket Store** (`src/store/websocket.ts`):
```typescript
useWebSocketStore.getState()
  .setConnected(true)     // Connection status
  .setCursor(42)          // Event recovery cursor
  .subscribe(['EVENT_A']) // Subscribed event types
  .setReconnectAttempts(1)
```
- Connection state (actual from WebSocket service)
- Subscriptions list
- Cursor for event recovery
- Reconnection attempt counter

**UI Store** (`src/store/ui.ts`):
```typescript
useUIStore.getState()
  .setSidebarOpen(false)  // Sidebar toggle
  .setTheme('light')      // Theme preference
  .addNotification(msg, type)  // Show notification
  .clearNotifications()
```
- Sidebar expanded/collapsed
- Theme preference (light/dark)
- Notification queue (transient messages)

## API Integration

### HTTP Client (`src/services/api.ts`)

**Centralized Axios client with:**
- JWT auth token in Authorization header
- Multi-tenant X-Tenant-ID header (extracted from JWT)
- Request/response interceptors
- Automatic error normalization

**Methods:**
```typescript
apiClient.getAgents(params)         // GET /api/v1/agents
apiClient.getMissions(params)       // GET /api/v1/missions
apiClient.getExecutions(params)     // GET /api/v1/executions
apiClient.issueWebSocketTicket()    // POST /api/v1/websocket/ticket
```

**Security:**
- JWT token set via `apiClient.setToken(token)`
- Never hardcoded or logged
- Extracted from Auth store
- Sent as: `Authorization: Bearer <token>`

### Error Normalization (`src/services/errors.ts`)

Converts HTTP errors to application error codes:
```
401 → UNAUTHORIZED
403 → FORBIDDEN
404 → NOT_FOUND
500 → SERVER_ERROR
```

Retryable errors (408, 429, 500, 502, 503) flagged automatically.

## Real-Time Events (WebSocket)

### WebSocket Service (`src/services/websocket.ts`)

**Connection Flow:**
1. Frontend requests ticket via REST API (`issueWebSocketTicket()`)
2. Backend issues single-use ticket (5min expiry)
3. Frontend connects: `ws://backend/ws?ticket=...`
4. Backend validates and consumes ticket (atomic)
5. Frontend receives heartbeats with cursor for recovery

**Automatic Reconnection:**
- Exponential backoff (1s, 2s, 4s, 8s, 16s, 30s max)
- Maximum 5 retries
- Cursor-based event recovery on reconnect
- Event deduplication (5-minute sliding window by event_id)

**Message Protocol:**

Client → Server:
```json
{ "action": "subscribe", "event_types": ["MISSION_UPDATED", ...] }
{ "action": "heartbeat" }
{ "action": "reconnect", "cursor": 42 }
```

Server → Client:
```json
{ "type": "event", "event_id": "evt-123", "event_type": "MISSION_UPDATED", "data": {...} }
{ "type": "heartbeat", "timestamp": "...", "cursor": 42 }
{ "type": "error", "code": "INVALID_TICKET", "message": "..." }
```

## Authentication & Authorization

### JWT Flow

1. **Backend issues JWT** after user authentication
2. **Frontend stores in memory** (via useAuthStore)
3. **HTTP requests** include: `Authorization: Bearer <token>`
4. **WebSocket connection** uses ticket-based auth (not JWT in URL)
5. **Multi-tenant isolation** via `tenant_id` claim in JWT

### Multi-Tenant Isolation

**Enforced at every layer:**
- HTTP: `X-Tenant-ID` header added automatically
- WebSocket: Ticket scope limited to tenant
- TanStack Query: Tenant included in cache keys (via auth store)
- Zustand: No tenant-specific data stored (kept in Query cache)
- Backend: All endpoints filtered by tenant_id from JWT

## Data Flow Example

**Scenario: Display agent list**

```
1. Component mounts
   ↓
2. useAgents() hook called
   ↓
3. TanStack Query checks cache
   ↓
4. If not cached: API client GET /api/v1/agents
   ↓
5. HTTP response received + cached
   ↓
6. Component receives data { agents: [...], total: 42 }
   ↓
7. Render AgentCard components

8. WebSocket event: AGENT_UPDATED
   ↓
9. useWebSocket hook receives event
   ↓
10. Query cache invalidated: invalidateQueries(['agents'])
   ↓
11. TanStack Query refetches (marked stale)
   ↓
12. Component re-renders with updated data
```

## Security Architecture

### No Secrets in Frontend
- ✅ JWT tokens: memory-only
- ✅ WebSocket tickets: single-use, never logged
- ✅ API URLs: environment variables only
- ✅ All credentials: backend-managed

### Security Protections
- ✅ TypeScript strict mode (type safety)
- ✅ Centralized API client (no raw fetch)
- ✅ Error normalization (no backend details leaked)
- ✅ Multi-tenant headers (X-Tenant-ID)
- ✅ No localStorage/sessionStorage for auth
- ✅ No endpoint invention (uses backend contract)
- ✅ No hardcoded URLs
- ✅ No fake activity or simulated data

## Configuration

### Environment Variables

```env
VITE_API_URL=http://localhost:8000     # Backend URL
VITE_API_VERSION=v1                     # API version
```

### Vite Configuration
- Dev server: `localhost:5173` with HMR
- Build output: `dist/`
- Sourcemaps: disabled in production

### TypeScript Configuration
- Target: ES2020
- Strict mode: ON
- JSX: react-jsx
- Path aliases: `@/*` → `src/*`

## Testing Strategy

**115+ tests across layers:**
- Unit tests: Components, Hooks, Services
- Integration tests: API client, WebSocket, Cache
- E2E (future): Full user flows

**Test Structure:**
- RED-GREEN-REFACTOR cycle
- TDD discipline required
- Real data, no mocks where possible
- Zustand/Query store tests separate

## Known Constraints

1. **No UI Screens Yet**
   - Data layer complete
   - Navigation ready
   - Components ready
   - Screens implemented in Phase 2

2. **Local Development Only**
   - Requires backend running locally
   - No production build tested
   - No deployment infrastructure

3. **Backend Dependency**
   - All queries go through REST API
   - WebSocket via backend only
   - No offline support

## Future Considerations

1. **Phase 2: Dashboard Implementation**
   - Metric visualization (Chart.js/Recharts)
   - Real-time updates from WebSocket
   - Responsive grid layouts

2. **Phase 3: Advanced UI**
   - Agent topology visualization (React Flow)
   - Mission orchestration interface
   - Event streaming and replay

3. **Phase 4: Production Hardening**
   - E2E testing (Playwright/Cypress)
   - Performance monitoring
   - Accessibility audit
   - Offline support

---

**Architecture Design Principles:**
- **Separation:** REST (Query) vs Real-time (WebSocket) vs UI (Zustand)
- **Type Safety:** TypeScript strict mode throughout
- **Security:** No secrets in frontend, centralized API client
- **Isolation:** Multi-tenant at every layer
- **Testability:** TDD, real data, isolated unit tests
- **Maintainability:** Clear layer responsibilities, documented flows

**Last Updated:** 2026-11-22  
**Implementation Status:** Infrastructure Complete (10/13 Tasks)
