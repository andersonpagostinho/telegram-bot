# NeoEve Command Center — Frontend

## Project Overview

NeoEve Command Center is a real-time agent orchestration and monitoring platform. The frontend provides a modern React 18 + TypeScript interface for observing multi-agent system activity and coordinating mission execution.

**Current Status:** Foundation infrastructure complete (10/13 tasks). Visual components and integration ready. UI screens to be implemented in subsequent phases.

## Scope

This frontend implementation provides:

- **Real-time monitoring** via WebSocket with automatic reconnection
- **REST API integration** with centralized HTTP client and JWT authentication
- **Data management** via TanStack Query for caching and state synchronization
- **Transient state** management via Zustand (UI state only)
- **Responsive dark theme** UI with premium Tailwind CSS styling
- **Multi-tenant isolation** throughout all layers
- **Comprehensive test coverage** (115+ tests)

What is **not** included:
- Dashboard visualizations (data layer ready, UI pending)
- Agent management screens (data layer ready, UI pending)
- Mission orchestration interface (API ready, UI pending)
- Real-time metrics display (WebSocket ready, UI pending)

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **UI Framework** | React | 18.2+ |
| **Language** | TypeScript | 5.3+ (strict mode) |
| **Build Tool** | Vite | 5.0+ |
| **Routing** | React Router | 6.20+ |
| **Data Fetching** | TanStack Query | 5.28+ |
| **State Management** | Zustand | 4.4+ |
| **HTTP Client** | Axios | 1.6+ |
| **Styling** | Tailwind CSS | 3.4+ |
| **Testing** | Vitest | 1.0+ |
| **CSS Processing** | PostCSS + Autoprefixer | 8.4+, 10.4+ |

## Prerequisites

- Node.js 18.0+ (not installed in this environment)
- npm 9.0+

## Installation

```bash
# Clone repository
git clone <repository-url>
cd neoeve-command-center/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your backend API URL and version
```

## Configuration

### Environment Variables

Create `.env.local` based on `.env.example`:

```env
# Backend API configuration
VITE_API_URL=http://localhost:8000
VITE_API_VERSION=v1
```

### Key Configuration Files

- **vite.config.ts** — Vite server (HMR on port 5173), build output
- **tsconfig.json** — TypeScript strict mode, path aliases (@/*)
- **tailwind.config.ts** — Dark theme (class-based), color palette
- **postcss.config.cjs** — Tailwind CSS and Autoprefixer
- **vitest.config.ts** — Test environment (jsdom), setup files

## Running

### Development Server

```bash
npm run dev
```

Starts Vite dev server on `http://localhost:5173` with HMR.

### Testing

```bash
# Run all tests
npm test

# Run tests with UI
npm run test:ui
```

**Current Coverage:** 115+ tests across 7 test files
- Setup validation (6 tests)
- Tailwind CSS (5 tests)
- TanStack Query (3 tests)
- API Client (11 tests)
- WebSocket Service (13 tests)
- Zustand Stores (21 tests)
- Layout Components (15+ tests)
- Common Components (28 tests)
- Custom Hooks (12+ tests)

### TypeScript Validation

```bash
npm run lint
```

Runs `tsc --noEmit` for type checking without emitting files.

### Production Build

```bash
npm run build
```

Runs TypeScript compiler then Vite build. Output goes to `dist/`.

### Preview Production Build

```bash
npm run preview
```

Preview built files locally before deployment.

## Project Structure

```
frontend/
├── public/                    # Static assets
├── src/
│   ├── components/           # React components
│   │   ├── layout/          # Layout (AppShell, Sidebar, Topbar, PageHeader)
│   │   ├── common/          # Reusable (StatusIndicator, MetricCard, AgentCard, etc)
│   │   └── ErrorBoundary.tsx
│   ├── hooks/               # Custom hooks
│   │   ├── useAgents.ts    # Query agents via TanStack Query
│   │   ├── useMissions.ts  # Query missions
│   │   ├── useExecutions.ts # Query executions
│   │   └── useWebSocket.ts  # WebSocket integration
│   ├── services/            # Service layer
│   │   ├── api.ts          # HTTP client (Axios + JWT)
│   │   ├── websocket.ts    # WebSocket with reconnection
│   │   └── errors.ts       # Error normalization
│   ├── store/              # Zustand stores (transient UI state only)
│   │   ├── auth.ts         # User identity and auth state
│   │   ├── websocket.ts    # Connection state and subscriptions
│   │   └── ui.ts           # UI preferences (sidebar, theme, notifications)
│   ├── types/              # TypeScript type definitions
│   │   ├── api.ts          # API response types
│   │   └── store.ts        # Store state types
│   ├── lib/                # Utilities
│   │   └── queryClient.ts  # TanStack Query configuration
│   ├── __tests__/          # Test files
│   │   ├── setup.test.ts
│   │   ├── tailwind.test.ts
│   │   ├── queryClient.test.ts
│   │   ├── api.test.ts
│   │   ├── websocket.test.ts
│   │   ├── store.test.ts
│   │   ├── layout.test.tsx
│   │   ├── common.test.tsx
│   │   └── hooks.test.ts
│   ├── pages/              # Page components (routed via React Router)
│   │   ├── Overview.tsx    # Overview stub
│   │   └── NotFound.tsx    # 404 fallback
│   ├── App.tsx             # Root component with QueryClientProvider
│   ├── router.tsx          # React Router configuration
│   ├── index.tsx           # React root
│   └── main.css            # Tailwind CSS directives
├── index.html              # Vite entry point
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite configuration
├── vitest.config.ts        # Test runner configuration
├── postcss.config.cjs      # PostCSS configuration
├── tailwind.config.ts      # Tailwind CSS configuration
├── .env.example            # Environment template
└── README.md               # This file
```

## Architecture

See **ARCHITECTURE.md** for detailed technical architecture, data flow, security model, and design decisions.

## Known Limitations

1. **UI Screens Not Yet Implemented**
   - Data layer complete (TanStack Query, API client, WebSocket)
   - Navigation structure ready (React Router)
   - Components ready (Layout, Common, Hooks)
   - Screens to be implemented in Phase 2

2. **Backend Dependency**
   - Requires running backend API on http://localhost:8000
   - WebSocket endpoint at /api/v1/websocket/ws
   - All agent/mission/execution queries via REST API

3. **Development Environment Only**
   - No npm modules installed (dev environment)
   - Build not yet executed
   - Database connectivity via backend only
   - No offline support

## Security Notes

- **JWT tokens** stored in memory only, never in localStorage
- **WebSocket tickets** are single-use, 5-minute expiry
- **Environment variables** required for backend API URL
- **Multi-tenant isolation** enforced via X-Tenant-ID header
- No hardcoded secrets or credentials
- All API calls centralized through apiClient

## Next Steps

1. **Phase 2: UI Implementation**
   - Create dashboard and monitoring screens
   - Implement agent management interface
   - Build mission orchestration controls

2. **Phase 3: Advanced Features**
   - Real-time metrics visualization
   - Agent topology visualization (React Flow)
   - Event streaming and playback

3. **Phase 4: Production Hardening**
   - E2E testing with Playwright
   - Performance profiling and optimization
   - Accessibility (a11y) audit and fixes

## Troubleshooting

### Port 5173 Already in Use
```bash
# Kill process using port 5173
# Or use: npm run dev -- --port 5174
```

### TypeScript Errors
```bash
npm run lint  # Check for type errors
```

### Test Failures
```bash
npm test -- --reporter=verbose  # Detailed test output
npm run test:ui                  # Visual test runner
```

## Contributing

See main repository guidelines. All changes require:
- TypeScript strict mode compliance
- Test coverage for new features
- No hardcoded secrets or URLs
- Multi-tenant isolation maintained

## License

[See main repository]

---

**Last Updated:** 2026-11-22  
**Status:** Infrastructure Complete (10/13 Tasks)  
**Next Phase:** UI Implementation
