# Task 1: Initialize Vite + React + TypeScript

## Context
First task: Foundation setup. This task creates the project structure at `neoeve-command-center/frontend/`.

## Deliverables
- ✅ `vite.config.ts` configured
- ✅ `tsconfig.json` with strict mode
- ✅ `index.html` Vite entrypoint
- ✅ `src/index.tsx` React root
- ✅ `src/App.tsx` stub component
- ✅ `package.json` with all dependencies
- ✅ `.env.example` template
- ✅ Dev server runnable on http://localhost:5173
- ✅ TypeScript compilation passes
- ✅ Commit created

## Acceptance Criteria
1. `npm install` succeeds
2. `npm run dev` starts server on :5173
3. Browser shows "NeoEve Command Center"
4. `npm run lint` passes (no TS errors)
5. Files exist and have correct content

## Steps (Red-Green order)

**Step 1:** Write test verifying package.json structure
**Step 2:** Create `package.json` with exact dependencies (see spec below)
**Step 3:** Write test verifying Vite config
**Step 4:** Create `vite.config.ts`
**Step 5:** Create `tsconfig.json`
**Step 6:** Create `index.html`
**Step 7:** Create `src/index.tsx`
**Step 8:** Create `src/App.tsx`
**Step 9:** Create `.env.example`
**Step 10:** Run `npm install`
**Step 11:** Run `npm run dev` and verify output
**Step 12:** Run `npm run lint` and verify passes
**Step 13:** Commit

## Spec Values (Verbatim from Plan)

**Dependencies (exact versions):**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.28.0",
    "zustand": "^4.4.0",
    "axios": "^1.6.0",
    "react-flow-renderer": "^11.10.0",
    "clsx": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "vitest": "^1.0.0",
    "@vitest/ui": "^1.0.0",
    "@testing-library/react": "^14.1.0",
    "@testing-library/jest-dom": "^6.1.0"
  }
}
```

**Global Constraints from Plan:**
- Node.js: 18+
- React: 18.2+
- TypeScript: 5.0+
- No hardcoded API URLs
- No localStorage for JWT
- No test data in production
