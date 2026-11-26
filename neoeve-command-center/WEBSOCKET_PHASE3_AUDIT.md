# WEBSOCKET PHASE 3 — AUDITORIA DO FLUXO EXISTENTE

**Data:** 2026-11-24  
**Status:** 🔵 **AUDITORIA COMPLETA**

---

## 📋 SUMÁRIO EXECUTIVO

Auditoria do fluxo WebSocket existente mapeou:

| Aspecto | Status | Achado |
|---------|--------|--------|
| **Fluxo de Conexão** | ✅ Mapeado | `connect()` → `issueWebSocketTicket()` → `establishConnection()` |
| **Token Management** | ⚠️ CRÍTICO | Sem refresh antes de ticket |
| **Reconexão** | ✅ Implementado | Backoff exponencial com max 5 retries |
| **Ticket Expirado** | ❌ NÃO TRATADO | Sem detecção de expiração de ticket |
| **Estado Global** | ✅ Implementado | Zustand store com `isConnected`, `cursor`, `subscriptions` |
| **Recuperação de Eventos** | ✅ Implementado | Cursor tracking para eventos perdidos |
| **Hook Integration** | ✅ Implementado | useWebSocket com subscriptions e cache invalidation |

---

## 🔍 ANÁLISE DETALHADA

### 1. Fluxo de Conexão Atual

**Arquivo:** `frontend/src/services/websocket.ts`

**Fluxo:**
```
App.tsx monta
  ↓
useWebSocket() dispara
  ↓
websocketService.connect()
  ├─ Sem verificação de token!
  ├─ Sem renovação!
  ├─ POST /websocket/ticket
  │   ├─ Se sucesso: ticket recebido
  │   └─ Se 401: erro, sem retry com refresh
  ├─ websocketService.establishConnection()
  │   └─ WebSocket aberto com ticket na URL
  ↓
onOpen()
  ├─ isConnected = true
  ├─ Envia subscriptions
  └─ Se reconnecting: request missed events
```

**Crítico:** Nenhuma verificação se token está expirado ANTES de solicitar ticket.

---

### 2. Tratamento de Erro 401

**Arquivo:** `frontend/src/services/websocket.ts:91-94`

**Código Atual:**
```typescript
catch (error: any) {
  this.emitError('CONNECTION_ERROR', error.message || 'Failed to connect');
  return false;
}
```

**Problema:**
- ❌ Não diferencia 401 (token expirado) de outros erros
- ❌ Não tenta refresh automaticamente
- ❌ Apenas emite erro genérico

**Hook Listener:**
```typescript
// em useWebSocket.ts:38-42
websocketService.onError((error) => {
  console.error('WebSocket error:', error);
  if (error.code === 'UNAUTHORIZED') {
    setConnected(false);
  }
});
```

**Problema:**
- ❌ Não tenta recuperação
- ❌ Apenas marca como desconectado

---

### 3. Reconexão Existente

**Arquivo:** `frontend/src/services/websocket.ts:216-228`

**Código:**
```typescript
private onClose(): void {
  this.isConnected = false;
  this.ws = null;

  if (this.retryCount < this.maxRetries) {
    const delay = this.getRetryDelay(this.retryCount);
    this.retryTimeout = setTimeout(() => {
      this.retryCount++;
      this.connect();
    }, delay);
  } else {
    this.emitError('MAX_RETRIES_EXCEEDED', 'Failed to reconnect after maximum retries');
  }
}
```

**Status:**
- ✅ Backoff exponencial implementado (1s → 2s → 4s → 8s → 16s + jitter)
- ✅ Max 5 retries
- ✅ Sem loop infinito
- ⚠️ Chama `this.connect()` que pode precisar novo token

---

### 4. Verificação de Token

**Arquivo:** `frontend/src/services/websocket.ts:71-74`

**Código:**
```typescript
public setToken(token: string): void {
  // Token is set on the API client via auth store
  // This method is here for hook compatibility
}
```

**Achado:**
- ⚠️ Método é "dummy" (não faz nada)
- ⚠️ Token não é armazenado no WebSocketService
- ⚠️ Hook passa token ao chamar, mas service não o conhece

---

### 5. Estado Global

**Arquivo:** `frontend/src/store/websocket.ts`

**Store Current:**
```typescript
isConnected: boolean        // true/false apenas
cursor: number | null       // para recuperação de eventos
subscriptions: string[]     // event types subscribed
reconnectAttempts: number  // contador de tentativas
```

**Achado:**
- ⚠️ Sem estado para distinguir:
  - CONNECTING vs CONNECTED
  - AUTH_EXPIRED vs API_OFFLINE
  - RECONNECTING vs DISCONNECTED
- ⚠️ `isConnected` é binário (precisa de mais granularidade)

---

### 6. Recuperação de Eventos

**Arquivo:** `frontend/src/services/websocket.ts:257-263`

**Código:**
```typescript
public reconnect(): void {
  if (this.isConnected) {
    this.send({
      action: 'reconnect',
      cursor: this.cursor,
    });
  }
}
```

**Status:**
- ✅ Cursor tracking implementado
- ✅ Request de missed events após reconexão
- ✅ Deduplication de eventos por event_id

**Achado:**
- ⚠️ Sem documentação se eventos podem ser perdidos
- ✅ Cursor preservado em memória (OK para reconexão rápida)

---

## 🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. 🔴 Sem Renovação de Token Antes do Ticket

**Cenário:**
```
T=14min: Access token válido (renovado pela hook)
T=15min: Conexão WebSocket cai
         → Backoff reconecta
         → Chama websocketService.connect()
         → POST /websocket/ticket com access_token
         → SEM VERIFICAÇÃO se token ainda é válido
         → Se token expirou neste 1min:
            → 401 Unauthorized
            → Sem retry com refresh
            → Usuário fica offline
```

---

### 2. 🔴 Sem Diferenciação de Erros 401

**Código Atual:**
```typescript
catch (error: any) {
  this.emitError('CONNECTION_ERROR', error.message);
  return false;
}
```

**Necessário:**
```typescript
catch (error: any) {
  if (error.response?.status === 401) {
    // Tentar refresh + retry ANTES de dar erro
  } else if (error.response?.status >= 500) {
    // API offline
  } else {
    // Outro erro
  }
}
```

---

### 3. 🟡 Estado Global Binário

**Atual:** `isConnected: boolean`

**Necessário:** Estados específicos
- `CONNECTING` - aguardando ticket + WS abrir
- `CONNECTED` - websocket aberto
- `RECONNECTING` - tentando reconectar
- `AUTH_EXPIRED` - refresh falhou
- `API_OFFLINE` - 503+ da API
- `DISCONNECTED` - encerrado

---

## ✅ O QUE JÁ FUNCIONA

| Funcionalidade | Status | Detalhes |
|---|---|---|
| Backoff exponencial | ✅ | Implementado corretamente |
| Max retries | ✅ | Limite de 5 retries |
| Cursor tracking | ✅ | Eventos perdidos podem ser recuperados |
| Zustand store | ✅ | Gerenciamento de estado |
| Event deduplication | ✅ | Por event_id (5min window) |
| Hook integration | ✅ | useWebSocket coordena tudo |

---

## 🎯 O QUE PRECISA SER IMPLEMENTADO (PHASE 3)

### 1. Token Renewal Antes do Ticket

**Implementação:**
```typescript
async connect(): Promise<boolean> {
  // NOVO: Renovar token se necessário
  await this.ensureTokenValid();
  
  // Depois: Solicitar ticket
  try {
    const response = await apiClient.issueWebSocketTicket();
    // ... resto do fluxo
  } catch (error: any) {
    if (error.response?.status === 401) {
      // NOVO: Tentar refresh + retry uma vez
      return await this.retryWithRefresh();
    }
  }
}
```

---

### 2. Diferenciação de Erros 401

**Implementação:**
```typescript
// Capturar 401 e tentar refresh
if (error.response?.status === 401) {
  try {
    await refreshToken(); // Usar PHASE 2B
    return await this.connect(); // Retry
  } catch (refreshErr) {
    this.emitError('AUTH_EXPIRED', 'Token refresh failed');
    return false;
  }
}
```

---

### 3. Estados Global Refinados

**Implementação:**
```typescript
// Novo estado no store
connectionState: 
  | 'CONNECTING'
  | 'CONNECTED'
  | 'RECONNECTING'
  | 'AUTH_EXPIRED'
  | 'API_OFFLINE'
  | 'DISCONNECTED'
```

---

### 4. Novo Ticket em Cada Reconexão

**Implementação:**
```typescript
private onClose(): void {
  this.isConnected = false;
  this.ws = null;
  this.ticket = null; // NOVO: invalidar ticket
  
  if (this.retryCount < this.maxRetries) {
    // NOVO: cada reconexão solicita novo ticket
    // (evita ticket expirado)
  }
}
```

---

## 📌 CHECKPOINT

**Auditoria:** ✅ Completa  
**Próxima Etapa:** WEBSOCKET_PHASE3_IMPLEMENTATION_PLAN.md  
**Status:** 🟢 Pronto para implementação

---

**Auditoria concluída:** 2026-11-24  
**Arquivos auditados:** 3 (websocket.ts, useWebSocket.ts, store/websocket.ts)  
**Nível de confiança:** 95% (baseado em análise estática completa)
