# ROOT CAUSE ANALYSIS — OFFLINE INDICATOR

## 🔴 Problema Observado

Command Center frontend exibe status **OFFLINE** mesmo com backend respondendo em `/health`.

---

## 📍 Componentes Responsáveis pelo Indicador

### 1. **ActivityStream.tsx:197** (Display)
```typescript
{isConnected ? '🔴 Live updates enabled' : '⚪ Offline (historical only)'}
```
- Exibe "⚪ Offline (historical only)" quando `isConnected === false`
- Localização: `frontend/src/pages/ActivityStream.tsx` (linha 197)

### 2. **AgentMap.tsx:209** (Display)
```typescript
backgroundColor: isConnected ? theme.colors.connectivity.online : theme.colors.connectivity.offline,
```
- Muda cor do indicador de conectividade
- Localização: `frontend/src/pages/AgentMap.tsx` (linha 209)

### 3. **Topbar.tsx** (Display — presumido)
- Componente de topo que provavelmente também exibe status de conexão

---

## 🔄 Fluxo de Atualização do Estado

### Source: `frontend/src/store/websocket.ts`

```typescript
export const useWebSocketStore = create<WebSocketState>((set) => ({
  isConnected: false,  // DEFAULT = OFFLINE
  
  setConnected: (connected: boolean) =>
    set({ isConnected: connected }),
}));
```

**Estado inicial:** `isConnected: false` (OFFLINE)

---

## 🔀 Fluxo de Conexão WebSocket

### FLUXO 1: Inicialização (useWebSocket hook)

**Arquivo:** `frontend/src/hooks/useWebSocket.ts` (linhas 22-48)

```typescript
useEffect(() => {
  if (!token || connectionInitialized.current) return;
  
  connectionInitialized.current = true;
  websocketService.setToken(token);
  
  const connectWS = async () => {
    const success = await websocketService.connect();  // LINE 29
    if (success) {
      setConnected(true);  // LINE 31 — Marca como ONLINE
    }
  };
  
  connectWS();
  
  // Subscribe to errors
  const unsubscribeError = websocketService.onError((error) => {
    console.error('WebSocket error:', error);
    if (error.code === 'UNAUTHORIZED') {
      setConnected(false);  // LINE 41 — Marca como OFFLINE
    }
  });
  
  return () => unsubscribeError();
}, [token, setConnected]);
```

---

## 🔗 WebSocket Connection Process

### STEP 1: Issue Ticket

**Arquivo:** `frontend/src/services/websocket.ts` (linhas 79-95)

```typescript
async connect(): Promise<boolean> {
  try {
    // Get ticket from API
    const response = await apiClient.issueWebSocketTicket();  // LINE 82
    this.ticket = (response as any).ticket;
    
    if (!this.ticket) {
      this.emitError('TICKET_ERROR', 'Failed to obtain WebSocket ticket');
      return false;
    }
    
    return this.establishConnection();
  } catch (error: any) {
    this.emitError('CONNECTION_ERROR', error.message || 'Failed to connect');  // LINE 92
    return false;
  }
}
```

**API Call:**
```typescript
// frontend/src/services/api.ts (line 164)
async issueWebSocketTicket(): Promise<WebSocketTicketResponse> {
  const response = await this.client.post<WebSocketTicketResponse>('/websocket/ticket', {});
  return response.data;
}
```

**URL:** `POST http://localhost:8000/api/v1/websocket/ticket`

**Backend Handler:** `backend/app/api/routes/websocket.py` (lines 21-61)

```python
@router.post("/ticket")
async def issue_websocket_ticket(
    current_user: Identity = Depends(get_current_user),  # JWT REQUIRED
):
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many ticket requests..."
        )
```

---

### STEP 2: Establish WebSocket Connection

**Arquivo:** `frontend/src/services/websocket.ts` (linhas 100-119)

```typescript
private establishConnection(): boolean {
  if (!this.ticket) {
    return false;
  }
  
  try {
    const wsUrl = `${this.url}/api/v1/websocket/ws?ticket=${encodeURIComponent(this.ticket)}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => this.onOpen();
    this.ws.onmessage = (event) => this.onMessage(event);
    this.ws.onerror = (event) => this.onWSError(event);
    this.ws.onclose = () => this.onClose();
    
    return true;
  } catch (error: any) {
    this.emitError('CONNECTION_ERROR', error.message);
    return false;
  }
}
```

**WebSocket URL:** `ws://localhost:8000/api/v1/websocket/ws?ticket=...`

**Backend Handler:** `backend/app/api/routes/websocket.py` (lines 64-120)

```python
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: str = Query(...),
    db: Session = Depends(get_db),
):
    ws_ticket = ticket_service.validate_and_consume_ticket(ticket)
    
    if not ws_ticket:
        await websocket.close(code=1008, reason="Invalid or expired ticket")
        return
```

---

## 🚨 CAUSE ROOT CONFIRMADA

### Cenário 1: JWT Token Expirado/Inválido

**Requisição:** `POST /api/v1/websocket/ticket`

**Com JWT expirado:**
- Backend retorna: **401 Unauthorized** (via `get_current_user` dependency)
- Frontend recebe: `AxiosError` com status 401
- `websocket.ts.connect()` chama: `emitError('CONNECTION_ERROR', 'Request failed with status code 401')`
- `useWebSocket.ts` recebe: `{ code: 'CONNECTION_ERROR', message: '...' }`
- **Condição `if (error.code === 'UNAUTHORIZED')` é FALSE**
- `setConnected()` **NÃO é chamado**
- **Estado permanece:** `isConnected: false` (OFFLINE)

### Cenário 2: Falha ao Conectar WebSocket

**WebSocket:** `ws://localhost:8000/api/v1/websocket/ws?ticket=...`

**Com ticket inválido:**
- Backend fecha conexão: `websocket.close(code=1008, reason="Invalid or expired ticket")`
- Frontend recebe: `onWSError()` ou `onClose()`
- `websocket.ts` chama: `emitError('WEBSOCKET_ERROR', 'Connection error')` ou `emitError('MAX_RETRIES_EXCEEDED', ...)`
- **Condição `if (error.code === 'UNAUTHORIZED')` é FALSE**
- `setConnected()` **NÃO é chamado**
- **Estado permanece:** `isConnected: false` (OFFLINE)

---

## 📊 Mapeamento de Estados

| Situação | Código de Erro | Condição em useWebSocket | Resultado |
|----------|---|---|---|
| JWT válido, ticket emitido, conexão ok | (nenhum) | N/A | ✅ `isConnected = true` |
| JWT expirado ao solicitar ticket | `CONNECTION_ERROR` | `code !== 'UNAUTHORIZED'` | ❌ `isConnected = false` |
| JWT inválido | `CONNECTION_ERROR` | `code !== 'UNAUTHORIZED'` | ❌ `isConnected = false` |
| Ticket inválido/expirado no WebSocket | `WEBSOCKET_ERROR` | `code !== 'UNAUTHORIZED'` | ❌ `isConnected = false` |
| Máximo de retentativas excedido | `MAX_RETRIES_EXCEEDED` | `code !== 'UNAUTHORIZED'` | ❌ `isConnected = false` |

---

## 🎯 DIAGNÓSTICO FINAL

### **Requisição que Falha**

```
POST http://localhost:8000/api/v1/websocket/ticket
Authorization: Bearer <JWT_TOKEN>
```

### **Código HTTP quando Falha**

**401 Unauthorized** (se JWT expirado/inválido)

**429 Too Many Requests** (se rate limit excedido)

### **Por que Mostra OFFLINE**

1. ✅ Requisição falha com 401 ou 429
2. ✅ Frontend não consegue obter ticket
3. ✅ WebSocket não pode ser estabelecido
4. ✅ `emitError()` é chamado com código diferente de 'UNAUTHORIZED'
5. ✅ Zustand store **permanece com `isConnected: false`** (valor padrão)
6. ✅ UI renderiza "⚪ Offline"

---

## 💡 Correção Mínima Recomendada

### **Opção 1: Expandir Condição de Erro (Quick Fix)**

**Arquivo:** `frontend/src/hooks/useWebSocket.ts` (linha 40-42)

**Código Atual:**
```typescript
if (error.code === 'UNAUTHORIZED') {
  setConnected(false);
}
```

**Correção:**
```typescript
if (error.code === 'UNAUTHORIZED' || 
    error.code === 'CONNECTION_ERROR' || 
    error.code === 'WEBSOCKET_ERROR' ||
    error.code === 'TICKET_ERROR') {
  setConnected(false);
}
```

**Problema:** Ainda não mostra OFFLINE. O problema é que `setConnected()` **nunca é chamado quando há erro**. O estado permanece em seu valor anterior (false por padrão, ou true se estava conectado antes).

### **Opção 2: Garantir que Erros Resultem em OFFLINE (Correto)**

A lógica atual está **correta**, mas há um **bug**: quando há erro, `setConnected(false)` **nunca é chamado** porque a condição `error.code === 'UNAUTHORIZED'` é muito restritiva.

**Revisão necessária:** Mudar para:

```typescript
if (error.code !== undefined) {
  // ANY error from WebSocket means we're offline
  setConnected(false);
}
```

Ou mais explicitamente:

```typescript
switch (error.code) {
  case 'UNAUTHORIZED':
  case 'CONNECTION_ERROR':
  case 'WEBSOCKET_ERROR':
  case 'TICKET_ERROR':
  case 'MAX_RETRIES_EXCEEDED':
    setConnected(false);
    break;
}
```

---

## 📌 Resumo Executivo

| Aspecto | Resultado |
|---------|-----------|
| **Componente que Exibe OFFLINE** | `ActivityStream.tsx:197`, `AgentMap.tsx:209` |
| **Variável de Estado** | `isConnected` (Zustand store em `store/websocket.ts:10`) |
| **Mecanismo de Atualização** | `setConnected()` chamado por `useWebSocket()` hook |
| **Requisição que Falha** | `POST /api/v1/websocket/ticket` (precisa JWT válido) |
| **Código HTTP ao Falhar** | `401 Unauthorized` ou `429 Too Many Requests` |
| **Causa Raiz** | JWT expirado/inválido impede obtenção de ticket WebSocket |
| **Por que Mostra OFFLINE** | Erro não dispara `setConnected(false)` corretamente |
| **Correção Recomendada** | Expandir condição de erro em `useWebSocket.ts:40-42` |

---

**Status da Investigação:** ✅ READ-ONLY  
**Nenhuma alteração realizada — Apenas diagnóstico.**
