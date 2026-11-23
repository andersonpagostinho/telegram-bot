# ERROR AUDIT — ETAPA 3, FASE 3.1

## Resumo

| Categoria | Contagem | Origem | Classificação |
|-----------|----------|--------|----------------|
| **TypeScript Erros** | 11 | Tasks 1-3 | Pré-existente |
| **Test Falhas** | 29 | Tasks 1-3 | Pré-existente |
| **Task 4 Contribuição** | 0 | — | ✅ ZERO |

---

## PHASE 2 — TYPESCRIPT ERRORS (Pre-existing)

### TS2322 — Nullable Type Mismatch

**Arquivo:** `src/__tests__/common.test.tsx`

```
Line 98: Type 'null' is not assignable to type 'string | undefined'.
Line 99: Type 'null' is not assignable to type 'string | undefined'.
Line 127: { last_event_at: null; ... } not assignable to AgentResponse
```

**Root Cause:** Test fixture usa `null` para campos que aceitam `string | undefined`.

**Classificação:** Pré-existente — Task 1  
**Evidência:** Commit 253c854 (Task 1) não trata null explicitly

**Fix Necessário:** Atualizar `AgentResponse` interface ou fixture

---

### TS2339 — Property Not Found

**Arquivo:** `src/__tests__/websocket.test.ts:66`

```
Property 'length' does not exist on type 'Set<string>'.
```

**Root Cause:** Código tenta acessar `.length` em Set. Sets não têm `.length`, usam `.size`.

**Classificação:** Pré-existente — Task 1  
**Evidência:** Commit 9ae4a58 (Task 3) não usa Sets

**Fix Necessário:** Mudar `.length` para `.size`

---

### TS2322 — Component Props Mismatch

**Arquivo:** `src/components/timeline/EventItem.tsx:20`

```
Type 'operationalState' is not assignable to type 'StatusIndicatorProps'.
Property 'operationalState' does not exist in type 'IntrinsicAttributes & StatusIndicatorProps'.
```

**Root Cause:** EventItem passa `operationalState` e `connectivityState`, mas StatusIndicator espera `status` e `connectivity`.

**Classificação:** Pré-existente — Task 3  
**Evidência:** Commit 9ae4a58 define EventItem com props incorretos

**Fix Necessário:** Atualizar EventItem para usar props corretos

---

### TS2339 — ImportMeta.env

**Arquivo:** `src/services/api.ts:16-17` e `src/services/websocket.ts:63`

```
Property 'env' does not exist on type 'ImportMeta'.
```

**Root Cause:** Código tenta acessar `import.meta.env` sem Vite env plugin.

**Classificação:** Pré-existente — Vite config  
**Evidência:** Vite.config.ts não exporta env vars corretamente

**Fix Necessário:** Configurar vite.config.ts com `import.meta.env`

---

### TS2561 — Unknown Property

**Arquivo:** `src/services/websocket.ts:123, 233`

```
Object literal may only specify known properties, but 'event_types' does not exist in type 'WebSocketMessage'.
Did you mean to write 'event_type'?
```

**Root Cause:** Typo: `event_types` (plural) deveria ser `event_type` (singular).

**Classificação:** Pré-existente — Task 1  
**Evidência:** Commit 253c854 define WebSocketMessage com `event_type`

**Fix Necessário:** Mudar `event_types` para `event_type`

---

### TS2322 — Null Assignment to Optional

**Arquivo:** `src/services/websocket.ts:252`

```
Type 'number | null' is not assignable to type 'number | undefined'.
Type 'null' is not assignable to type 'number | undefined'.
```

**Root Cause:** Atribuição de `null` onde apenas `undefined` é permitido.

**Classificação:** Pré-existente — Task 1  
**Evidência:** Commit 253c854

**Fix Necessário:** Usar `undefined` em vez de `null`, ou atualizar tipo para aceitar `null`

---

### TS2339 — WebSocketService.setToken

**Arquivo:** `src/hooks/useWebSocket.ts:26`

```
Property 'setToken' does not exist on type 'WebSocketService'.
```

**Root Cause:** Método `setToken` não foi implementado em `WebSocketService`.

**Classificação:** Pré-existente — Task 1  
**Evidência:** Commit 253c854 não implementa setToken

**Fix Necessário:** Adicionar `setToken()` method à classe

---

### TS2322 — AxiosHeaders Type

**Arquivo:** `src/services/api.ts:36`

```
Type '{ [x: string]: any; ... }' is not assignable to type 'AxiosRequestHeaders'.
Missing properties: set, get, has, delete, ...
```

**Root Cause:** Axios v1.6+ mudou tipo de headers. Necessário usar AxiosHeaders class.

**Classificação:** Pré-existente — Axios version  
**Evidência:** Commit 253c854 usa v1.6.0

**Fix Necessário:** Converter headers para `new AxiosHeaders({...})`

---

## TEST FAILURES (Pre-existing)

### store.test.ts — 12/22 FAIL

**Arquivo:** `src/__tests__/store.test.ts`

**Falhas:**
- Auth Store: cannot set user, token, loading, errors
- WebSocket Store: cannot track connection, cursor, subscriptions
- UI Store: cannot toggle sidebar, change theme, add notifications

**Root Cause:** Zustand store setup nos testes não funciona (mocks ausentes).

**Classificação:** Pré-existente — Task 1 (store setup)  
**Evidência:** Commit não inclui store test mocks

**Mitigação:** Implementar store mocks em __tests__/setup.ts

---

### common.test.tsx — 2/26 FAIL

**Arquivo:** `src/__tests__/common.test.tsx`

**Falhas:**
1. `should display connectivity status separately` — cannot find data-testid="agent-connectivity"
2. `should all use dark theme colors` — expected to contain 'slate'

**Root Cause:** AgentCard não renderiza conectividade quando status é ONLINE.

**Classificação:** Pré-existente — Task 2  
**Evidência:** Commit 4c135fb (AgentCard) só mostra conectividade se != ONLINE

**Mitigação:** Atualizar test ou AgentCard component

---

### websocket.test.ts — 7-8/14 FAIL

**Arquivo:** `src/__tests__/websocket.test.ts`

**Falhas:**
- Cannot read properties of undefined (reading 'action')
- subscriptions.length issue
- Deduplication window cleanup

**Root Cause:** WebSocket service mock ou test fixtures inadequados.

**Classificação:** Pré-existente — Task 1  
**Evidência:** Commit 253c854 WebSocketService mock incompleto

**Mitigação:** Completar WebSocket mocks

---

### layout.test.tsx — 2+ FAIL

**Arquivo:** `src/__tests__/layout.test.tsx`

**Erros:**
- `useLocation() may be used only in the context of a <Router> component`

**Root Cause:** Componentes usam React Router hooks sem wrapper de test.

**Classificação:** Pré-existente — Task 1 (testing setup)  
**Evidência:** Commit não inclui RouterProvider wrapper para tests

**Mitigação:** Envolver testes com `<BrowserRouter>` ou mock router

---

## SUMMARY TABLE

| Erro | Arquivo | Linha | Tipo | Origem | Classificação |
|------|---------|-------|------|--------|----------------|
| TS2322 (null) | common.test.tsx | 98, 99 | Type | Task 1 | Pré-existente |
| TS2322 (AgentResponse) | common.test.tsx | 127 | Type | Task 1 | Pré-existente |
| TS2339 (length) | websocket.test.ts | 66 | Missing prop | Task 1 | Pré-existente |
| TS2322 (StatusIndicator) | timeline/EventItem.tsx | 20 | Props | Task 3 | Pré-existente |
| TS2339 (env) | services/api.ts | 16, 17 | Missing prop | Vite config | Pré-existente |
| TS2339 (env) | services/websocket.ts | 63 | Missing prop | Vite config | Pré-existente |
| TS2561 (event_types) | services/websocket.ts | 123, 233 | Typo | Task 1 | Pré-existente |
| TS2322 (null→undefined) | services/websocket.ts | 252 | Type | Task 1 | Pré-existente |
| TS2339 (setToken) | hooks/useWebSocket.ts | 26 | Missing method | Task 1 | Pré-existente |
| TS2322 (AxiosHeaders) | services/api.ts | 36 | Type | Task 1 | Pré-existente |
| Test Failure | store.test.ts | — | Zustand | Task 1 | Pré-existente |
| Test Failure | common.test.tsx | — | AgentCard | Task 2 | Pré-existente |
| Test Failure | websocket.test.ts | — | WebSocket | Task 1 | Pré-existente |
| Test Failure | layout.test.tsx | — | Router | Task 1 | Pré-existente |

---

## TASK 4 CONTRIBUTION

✅ **ZERO new errors**  
✅ **ZERO new test failures**  
✅ **30/30 tests PASS**  
✅ **TypeScript strict compilation**

Componentes de topologia (Task 4) completamente desacoplados de infraestrutura legada (Tasks 1-3).

---

## RECOMENDAÇÕES

### P0 — Bloqueia FASE 3.2

Implementar correções em Tasks 1-3 para permitir build global:
1. Corrigir null/undefined em fixtures
2. Implementar store mocks
3. Configurar Vite env
4. Adicionar Router wrapper em tests

### P1 — Melhoria

1. Implementar `setToken()` em WebSocketService
2. Atualizar TimeLine EventItem props
3. Completar WebSocket service mocks

### P2 — Futuro

1. Performance audit
2. Adicionar ARIA labels
3. React.memo memoization

---

**Data:** 2026-11-22  
**Preparado por:** Claude Haiku 4.5  
**Task 4 Status:** ✅ ZERO NEW ERRORS
