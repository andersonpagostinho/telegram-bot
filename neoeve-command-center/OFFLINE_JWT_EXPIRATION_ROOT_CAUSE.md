# ROOT CAUSE ANALYSIS — JWT EXPIRATION & OFFLINE STATE

## 🔴 Descoberta Crítica

**O Command Center mostra OFFLINE após 15 minutos de uso porque o JWT expira e não existe mecanismo de renovação.**

---

## 🧬 Cadeia de Causas Confirmadas

### 1. **Token de Acesso Expira em 15 Minutos**

**Arquivo:** `backend/app/core/config.py:27`

```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
```

- **Padrão:** 15 minutos
- **Sem renovação:** Token se torna inválido após expiração

### 2. **Backend NÃO Implementa Refresh Token (Incompleto)**

**Arquivo:** `backend/app/api/routes/auth.py:65-72`

```python
# Case 1: Single tenant — issue refresh token cookie
if result.get("single_tenant"):
    # In production, would create RefreshSession here  ⚠️ TODO
    # For now, return access token only
    return LoginResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
    )
```

**Status:** ❌ **INCOMPLETO**
- Código comentário diz "would create RefreshSession" (NÃO faz)
- Backend tem `RefreshSession` model (linha 143 import)
- Backend tem código de logout com refresh tokens (linhas 172-181)
- **MAS:** Não cria refresh token no login

### 3. **Frontend NÃO Implementa Renovação de Token**

**Achado:** Grep por `refresh_token`, `renew`, `token.*expire` retornou **ZERO matches**

- **Frontend tem:** Armazenamento de JWT em localStorage
- **Frontend tem:** Extração de tenant_id do JWT
- **Frontend NÃO tem:** Mecanismo de renovação
- **Frontend NÃO tem:** Interceptor para detectar 401 e renovar

### 4. **Backend Retorna 401 para Token Expirado**

**Arquivo:** `backend/app/core/security.py:159-214`

```typescript
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Identity:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # ← Token expirado = 401
            detail="Invalid or expired token",
        )
```

- **Comportamento:** Token expirado → JWTError → HTTPException 401

### 5. **POST /api/v1/websocket/ticket Falha com 401**

**Requisição:**
```
POST /api/v1/websocket/ticket
Authorization: Bearer <EXPIRED_JWT>
```

**Resposta:**
```
401 Unauthorized
"Invalid or expired token"
```

**Por quê:** Rota requer `get_current_user` dependency (linha 23 de websocket.py)

### 6. **Axios Interceptor NÃO Trata 401 Especialmente**

**Arquivo:** `frontend/src/services/api.ts:42-53`

```typescript
this.client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const normalized = normalizeApiError({
      status: error.response?.status || 500,
      statusText: error.response?.statusText || 'Unknown Error',
      data: error.response?.data as any,
    });
    return Promise.reject(normalized);  // ← Sem ação especial
  }
);
```

**Comportamento:**
- 401 é normalizado e rejeitado
- **NÃO tenta renovar token**
- **NÃO limpa localStorage**
- **NÃO redireciona para login**

### 7. **WebSocket Recebe CONNECTION_ERROR (Genérico)**

**Arquivo:** `frontend/src/services/websocket.ts:91-94`

```typescript
catch (error: any) {
  this.emitError('CONNECTION_ERROR', error.message || 'Failed to connect');
  return false;
}
```

**Código de erro:** `'CONNECTION_ERROR'` (não `'UNAUTHORIZED'`)

### 8. **useWebSocket.ts Não Marca OFFLINE**

**Arquivo:** `frontend/src/hooks/useWebSocket.ts:40-42`

```typescript
const unsubscribeError = websocketService.onError((error) => {
  console.error('WebSocket error:', error);
  if (error.code === 'UNAUTHORIZED') {  // ← Muito restritivo
    setConnected(false);
  }
});
```

**Problema:**
- Condição: `error.code === 'UNAUTHORIZED'`
- Recebido: `error.code === 'CONNECTION_ERROR'`
- **Resultado:** `setConnected()` **NÃO é chamado**
- **Estado permanece:** `isConnected: false` (valor padrão)

### 9. **UI Renderiza OFFLINE**

**Arquivo:** `frontend/src/pages/ActivityStream.tsx:197`

```typescript
{isConnected ? '🔴 Live updates enabled' : '⚪ Offline (historical only)'}
```

**Resultado:** `'⚪ Offline (historical only)'` aparece

---

## 📊 Fluxo Completo (15+ minutos após login)

```
Tempo: T+15min
   ↓
JWT expira
   ↓
Frontend tenta: POST /api/v1/websocket/ticket
   ↓
Backend: get_current_user() valida JWT
   ↓
JWT decode falha (expirado)
   ↓
Backend retorna: 401 Unauthorized "Invalid or expired token"
   ↓
Axios interceptor recebe 401
   ↓
Sem ação especial (nenhum refreshtoken, nenhum login redirect)
   ↓
websocket.ts.connect() captura erro
   ↓
Chama: emitError('CONNECTION_ERROR', '...')
   ↓
useWebSocket.ts recebe: { code: 'CONNECTION_ERROR' }
   ↓
Condição: if (error.code === 'UNAUTHORIZED') → FALSE
   ↓
setConnected(false) NÃO é chamado
   ↓
Estado permanece: isConnected: false
   ↓
ActivityStream renderiza: '⚪ Offline (historical only)'
   ↓
✅ Painel mostra OFFLINE (mesmo com backend online)
```

---

## 🎯 Causa Raiz Confirmada

| Fator | Status | Impacto |
|-------|--------|--------|
| **1. Token expira em 15 minutos** | ✅ Confirmado | 401 após 15min |
| **2. Backend NÃO implementa refresh** | ✅ Confirmado | Sem renovação automática |
| **3. Frontend NÃO implementa refresh** | ✅ Confirmado | Sem tentativa de renovar |
| **4. 401 não é tratado especialmente** | ✅ Confirmado | Sem redirect para login |
| **5. CONNECTION_ERROR não marca OFFLINE** | ✅ Confirmado | Estado permanece false |
| **6. UI mostra OFFLINE** | ✅ Confirmado | Painel aparece offline |

---

## 💡 Correção Mínima Proposta

### **Opção A: Curto Prazo (Sintoma)**

Expandir condição em `useWebSocket.ts:40-42` para capturar todos os erros:

```typescript
// ANTES:
if (error.code === 'UNAUTHORIZED') {
  setConnected(false);
}

// DEPOIS:
// ANY WebSocket error means we're offline
setConnected(false);
```

**Resultado:** UI mostrará corretamente OFFLINE quando há erro
**Problema:** Não resolve a causa raiz (token expirado após 15min)

### **Opção B: Raiz (Recomendado)**

**3 mudanças integradas:**

#### 1. Backend: Implementar Refresh Token

**Arquivo:** `backend/app/api/routes/auth.py:66-72`

Mudar de:
```python
# In production, would create RefreshSession here
# For now, return access token only
```

Para:
```python
# Create RefreshSession for token refresh
session = create_refresh_session(db, user_id=user["user_id"], tenant_id=tenant_id)
response.set_cookie(
    key="refresh_token",
    value=session.refresh_token,
    httponly=True,
    secure=True,
    samesite="Lax",
    max_age=7 * 24 * 60 * 60,  # 7 days
)
```

**Impacto:** Backend passa a emitir refresh tokens válidos

#### 2. Frontend: Implementar Renovação de Token

**Arquivo:** Novo arquivo `frontend/src/hooks/useTokenRefresh.ts`

```typescript
export function useTokenRefresh() {
  useEffect(() => {
    // Renovar token 1 minuto antes de expirar
    const refreshToken = async () => {
      try {
        const response = await apiClient.post('/auth/refresh', {});
        apiClient.setToken(response.access_token);
        useAuthStore.setState({ token: response.access_token });
      } catch (err) {
        // Falha ao renovar → fazer logout
        useAuthStore.setState({ user: null, token: null });
        window.location.href = '/login';
      }
    };

    // Agendar renovação a cada 14 minutos (1 min antes de expirar 15 min token)
    const interval = setInterval(refreshToken, 14 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);
}
```

**Impacto:** Frontend renova token automaticamente

#### 3. Frontend: Tratar 401 no Axios Interceptor

**Arquivo:** `frontend/src/services/api.ts:42-53`

Adicionar:
```typescript
(error: AxiosError) => {
  // 401 = Token expirado ou inválido
  if (error.response?.status === 401) {
    // Limpar auth e redirecionar
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    window.location.href = '/login';
    return Promise.reject(error);
  }
  
  const normalized = normalizeApiError({...});
  return Promise.reject(normalized);
}
```

**Impacto:** 401 é tratado como logout automático

---

## ✅ Resultado Esperado

Após implementar Opção B:

```
Tempo: T+10min (antes de expirar)
   ↓
useTokenRefresh() ativa
   ↓
Frontend chama: POST /auth/refresh com refresh_token (cookie)
   ↓
Backend valida refresh_token
   ↓
Backend retorna novo access_token (válido por 15 min)
   ↓
Frontend armazena novo token
   ↓
WebSocket reconnect com novo token
   ↓
✅ isConnected: true
   ↓
✅ UI mostra: '🔴 Live updates enabled'
```

---

## 🚫 Restrições

- ❌ Não alterar banco de dados
- ❌ Não modificar migrations
- ❌ Não alterar Recovery Worker
- ❌ Não executar agentes
- ❌ Não fazer commit, push ou deploy

---

## 📌 Próximos Passos

**Recomendação:** Implementar Opção B (correção de raiz) em 3 PRs:
1. Backend: Refresh token implementation
2. Frontend: Token refresh hook
3. Frontend: 401 interceptor handling

**Aguardando aprovação antes de editar arquivos.**
