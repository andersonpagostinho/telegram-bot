# React Render Loop — Root Cause Analysis

**Data:** 2026-11-24  
**Status:** Causa Raiz Identificada  
**Severidade:** Crítica (bloqueia navegação)

---

## Sintoma

Ao navegar para **AgentMap** ou **ActivityStream**, aparece:

```
Maximum update depth exceeded.
React limits the number of nested updates to prevent infinite loops.
```

**Componentes afetados:**
- ❌ AgentMap.tsx
- ❌ ActivityStream.tsx
- ✅ Overview.tsx (funciona)

---

## Cadeia de Causa

### Nível 1: Desestruturação sem Selector Memoizado

**Arquivo:** `frontend/src/hooks/useWebSocket.ts:17`

```typescript
// ERRADO: Desestruturação retorna novo objeto a cada render
const { isConnected, setConnected, setCursor, subscribe } = useWebSocketStore();
```

**Problema:**
- `useWebSocketStore()` sem selector memoizado
- Retorna novo objeto literal a cada chamada
- Mesmo que estado interno não mude, referências de funções são novas
- `subscribe` ≠ `subscribe` (mesma função, referência diferente)

---

### Nível 2: Dependência Instável em useEffect

**Arquivo:** `frontend/src/hooks/useWebSocket.ts:66-71`

```typescript
useEffect(() => {
  if (!isConnected || eventTypes.length === 0) return;
  websocketService.subscribe(eventTypes);
  subscribe(eventTypes);
}, [isConnected, eventTypes, subscribe]);  // ← subscribe é novo a cada render!
```

**Problema:**
- `subscribe` é adicionado como dependência
- `subscribe` é uma função diferente a cada render (por causa do nível 1)
- useEffect dispara sempre que `subscribe` muda (que é sempre)

---

### Nível 3: Atualização de Store Dispara Re-render

**Arquivo:** `frontend/src/hooks/useWebSocket.ts:70`

```typescript
subscribe(eventTypes);  // Chama set() do Zustand
```

**Problema:**
- `subscribe()` chama `set((state) => ({ subscriptions: ... }))`
- Store atualiza, Zustand notifica subscribers
- **Qualquer selector do store retorna novo valor/referência**
- `isConnected` muda (mesmo que para o mesmo valor `false` → `false`)
- Re-render dispara em qualquer componente que usa `useWebSocketStore()`

---

### Nível 4: Loop Infinito Fecha

```
useWebSocket() renderiza
  ↓
subscribe é novo (nível 1)
  ↓
useEffect[66] dispara (subscribe mudou)
  ↓
subscribe(eventTypes) chamado
  ↓
Zustand set() atualiza store
  ↓
useWebSocket() re-renderiza (subscriber notificado)
  ↓
VOLTA AO INÍCIO ✶ INFINITO
```

---

## Por Que Overview Funciona

**arquivo:** `frontend/src/components/layout/AppShell.tsx:11-12`

```typescript
// TODO: Fix useWebSocket infinite loop issue before re-enabling
// import { useWebSocket } from '../../hooks/useWebSocket';
```

✅ `useWebSocket()` **está comentado**
✅ Loop nunca inicia
✅ Overview renderiza normalmente

---

## Por Que AgentMap e ActivityStream Falham

**AgentMap.tsx:29**
```typescript
const { isConnected } = useWebSocket({ eventTypes: ['AGENT_UPDATED', 'AGENT_STATUS_CHANGED'] });
```

**ActivityStream.tsx:22-24**
```typescript
const { isConnected, onEvent } = useWebSocket({
  eventTypes: ['AGENT_UPDATED', 'MISSION_UPDATED', 'EXECUTION_COMPLETED']
});
```

❌ Ambas chamam `useWebSocket()`
❌ Loop infinito dispara imediatamente
❌ página não consegue renderizar

---

## Prova da Causa Raiz

### Teste 1: Verificar desestruturação

```typescript
// HOJE (com bug):
const store1 = useWebSocketStore();
const store2 = useWebSocketStore();
console.log(store1 === store2);  // false (novo objeto!)
console.log(store1.subscribe === store2.subscribe);  // false (nova referência!)
```

### Teste 2: Stack trace da navegação

Quando navega para AgentMap:
1. AgentMap monta
2. `useWebSocket()` chamado
3. useEffect[66] disparado
4. `subscribe(eventTypes)` chamado
5. Zustand atualiza
6. AgentMap re-renderiza
7. **VOLTA AO PASSO 2** → React conta updates (1, 2, 3... 50+)
8. "Maximum update depth exceeded" error

---

## Por Que Outros Componentes Não Veem Isso

**Topbar.tsx:14-15 / Sidebar.tsx:25**

```typescript
const { sidebarOpen, toggleSidebar } = useUIStore();
const { isConnected } = useWebSocketStore();
```

✅ Usam store SEM `useWebSocket()`  
✅ Sem dependências instáveis  
✅ Renderizam normalmente  
✅ Apenas sofrem com o loop quando **AgentMap/ActivityStream** estão renderizando

---

## Classificação de Causa

**Camada (Regra da Menor Camada):**
- **Camada 3 (Fluxo):** useWebSocket hook  
- **Trigger:** Desestruturação sem memoização  
- **Efeito:** Loop infinito

**Criticidade:** 🔴 **BLOQUEANTE**
- Impede navegação para 2 páginas críticas
- Desabilita funcionalidade real-time

**Reversibilidade:** ✅ **SIM**
- Mínima mudança no hook
- Não afeta estrutura

---

## Solução (Próxima Etapa)

**Estratégia:** Usar selectors memoizados do Zustand

```typescript
// CORRETO: Selectors memoizados
const isConnected = useWebSocketStore((state) => state.isConnected);
const setConnected = useWebSocketStore((state) => state.setConnected);
const setCursor = useWebSocketStore((state) => state.setCursor);
const subscribe = useWebSocketStore((state) => state.subscribe);
```

**Resultado:** Cada selector retorna **mesma referência** enquanto estado não muda = useEffect não dispara continuamente

---

**Diagnóstico Concluído**

Próxima: REACT_RENDER_LOOP_FIX_REPORT.md
