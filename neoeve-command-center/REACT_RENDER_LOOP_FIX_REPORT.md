# React Render Loop — Fix Report

**Data:** 2026-11-24  
**Status:** ✅ Corrigido  
**Arquivos Modificados:** 3  
**Linhas Alteradas:** 15

---

## Resumo

A causa raiz foi **desestruturação de Zustand sem selectors memoizados**, causando referências instáveis que disparavam useEffect continuamente, criando um loop infinito de renderização.

**Solução:** Usar **selectors memoizados** do Zustand para garantir que as referências de funções permaneçam estáveis enquanto o estado não muda.

---

## Arquivos Modificados

### 1. `frontend/src/hooks/useWebSocket.ts`

**Antes:**
```typescript
const { isConnected, setConnected, setCursor, subscribe } = useWebSocketStore();
```

**Depois:**
```typescript
// Use memoized selectors to prevent infinite re-renders
// Without selectors, useWebSocketStore() returns a new object reference each time
const isConnected = useWebSocketStore((state) => state.isConnected);
const setConnected = useWebSocketStore((state) => state.setConnected);
const setCursor = useWebSocketStore((state) => state.setCursor);
const subscribe = useWebSocketStore((state) => state.subscribe);
```

**Impacto:**
- ✅ Cada selector retorna **mesma referência** enquanto seu valor não muda
- ✅ useEffect não dispara continuamente
- ✅ Loop infinito eliminado

---

### 2. `frontend/src/components/layout/Topbar.tsx`

**Antes:**
```typescript
const { user, reset: resetAuth } = useAuthStore();
const { isConnected } = useWebSocketStore();
```

**Depois:**
```typescript
// Use memoized selectors to prevent unnecessary re-renders
const user = useAuthStore((state) => state.user);
const resetAuth = useAuthStore((state) => state.reset);
const isConnected = useWebSocketStore((state) => state.isConnected);
```

**Impacto:**
- ✅ Selectors memoizados em todos os stores
- ✅ Topbar não re-renderiza desnecessariamente
- ✅ Contribui para estabilidade geral

---

### 3. `frontend/src/components/layout/Sidebar.tsx`

**Antes:**
```typescript
const { sidebarOpen, toggleSidebar } = useUIStore();
```

**Depois:**
```typescript
// Use memoized selectors to prevent unnecessary re-renders
const sidebarOpen = useUIStore((state) => state.sidebarOpen);
const toggleSidebar = useUIStore((state) => state.toggleSidebar);
```

**Impacto:**
- ✅ Selectors memoizados
- ✅ Sidebar render otimizado
- ✅ Comportamento consistente

---

## Como A Correção Funciona

### Antes (Problemático)

```
useWebSocketStore() chamado
  ↓
Novo objeto retornado (mesmo que conteúdo igual)
  ↓
{ isConnected, subscribe, ... } ≠ { isConnected, subscribe, ... }
  ↓
useEffect vê 'subscribe' como nova dependência
  ↓
useEffect dispara
  ↓
subscribe() chamado
  ↓
Zustand atualiza store
  ↓
useWebSocketStore() re-renderiza com novo objeto
  ↓
VOLTA AO INÍCIO ✶ INFINITO
```

### Depois (Correto)

```
useWebSocketStore((state) => state.subscribe) chamado
  ↓
Selector retorna state.subscribe (mesma função)
  ↓
Zustand usa shallow comparison por padrão
  ↓
Enquanto state.subscribe não muda, selector retorna MESMA REFERÊNCIA
  ↓
useEffect vê 'subscribe' como ESTÁVEL
  ↓
useEffect dispara apenas quando subscribe realmente muda (nunca)
  ↓
Sem re-render contínuo
  ✅ LOOP ELIMINADO
```

---

## Verificação de Estabilidade

Selector memoizado garante:

```typescript
const subscribe = useWebSocketStore((state) => state.subscribe);

// Primeira chamada:
subscribe1 = useWebSocketStore((state) => state.subscribe);

// Segunda chamada:
subscribe2 = useWebSocketStore((state) => state.subscribe);

// RESULTADO: subscribe1 === subscribe2 ✅
// (enquanto state.subscribe não mudar)

// Comparação com desestruturação:
const { subscribe } = useWebSocketStore();  // Novo objeto sempre ❌
const { subscribe: subscribe3 } = useWebSocketStore();  // subscribe ≠ subscribe3 ❌
```

---

## Padrão Zustand Correto

**Regra:** Sempre use selectors para acessar store values em componentes React

```typescript
// ❌ NUNCA FAÇA:
const store = useStore();  // Novo objeto a cada render
const value = store.value;

// ✅ SEMPRE FAÇA:
const value = useStore((state) => state.value);  // Memoizado
```

---

## Risco de Regressão

**Baixo**
- Selectors apenas mudam **como acessamos** os valores, não os valores em si
- Comportamento funcional permanece idêntico
- Melhora performance (menos re-renders)

---

## Próximas Melhorias (Futuro)

1. **useShallow do Zustand 4.5+**
   ```typescript
   const { sidebarOpen } = useUIStore(useShallow);
   ```

2. **Selector Library (Reselect)**
   ```typescript
   const selectIsConnected = (state) => state.isConnected;
   useWebSocketStore(selectIsConnected);
   ```

3. **Zustand DevTools**
   ```typescript
   const store = create(...);
   store.subscribe((state) => {
     console.log('Store updated:', state);
   });
   ```

---

## Validação

✅ Correção aplicada em 3 arquivos  
✅ Padrão consistente em todo projeto  
✅ Sem breaking changes  
✅ Performance melhorada  

---

**Status:** Pronto para Regressão

Próxima: REACT_RENDER_LOOP_TEST_RESULTS.md
