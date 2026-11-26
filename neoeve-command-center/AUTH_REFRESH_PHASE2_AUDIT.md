# AUDITORIA READ-ONLY — PHASE 2 (FRONTEND)

**Data:** 2026-11-24  
**Status:** 🔴 **CRÍTICOS ENCONTRADOS — REPROVAR PHASE 2**

---

## 📋 RESUMO EXECUTIVO

PHASE 2 (Frontend) contém **3 falhas críticas** que impedem o funcionamento correto de token refresh:

| # | Severidade | Problema | Impacto |
|---|-----------|----------|--------|
| 1 | 🔴 CRÍTICO | Sem `withCredentials: true` | Cookies não são enviados; refresh nunca funciona |
| 2 | 🔴 CRÍTICO | 401 interceptor redireciona sem tentar refresh | Usuário logout sem oportunidade de renovar |
| 3 | 🟠 ALTO | Sem testes para token refresh | Comportamento não validado |

---

## 🔍 DETALHES DOS PROBLEMAS

### PROBLEMA 1: 🔴 CRÍTICO — Sem `withCredentials`

**Arquivo:** `frontend/src/services/api.ts` (linhas 25-32)

**Código Atual:**
```typescript
this.client = axios.create({
  baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  // FALTA: withCredentials: true
});
```

**Impacto:**
- ❌ Cookies HttpOnly NÃO são enviados em requisições CORS
- ❌ POST `/auth/refresh` recebe requisição SEM `refresh_token` cookie
- ❌ Backend retorna 401 (sem refresh_token, não consegue renovar)
- ❌ Refresh falha 100% do tempo
- ❌ Loop infinito: tentativa de refresh → falha → logout

**Necessário:**
```typescript
this.client = axios.create({
  baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
  timeout: 30000,
  withCredentials: true,  // OBRIGATÓRIO para CORS + cookies
  headers: {
    'Content-Type': 'application/json',
  },
});
```

**Verificação:**
- ✅ Grep por `withCredentials` retornou ZERO matches no frontend
- ✅ Padrão CORS+cookies requer `withCredentials: true`
- ✅ Backend tem `SameSite=Lax` mas frontend não envia cookies

---

### PROBLEMA 2: 🔴 CRÍTICO — 401 Redireciona sem Tentar Refresh

**Arquivo:** `frontend/src/services/api.ts` (linhas 44-70)

**Código Atual:**
```typescript
this.client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // 401 Unauthorized - token expired or invalid
    if (error.response?.status === 401) {
      // ❌ PROBLEMA: Redireciona IMEDIATAMENTE sem tentar refresh
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      
      const { reset } = useAuthStore.getState();
      reset();
      
      // REDIRECT IMEDIATO (sem renovação!)
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    
    const normalized = normalizeApiError({...});
    return Promise.reject(normalized);
  }
);
```

**Cenários de Falha:**

**Cenário A: Menos de 14 minutos após login**
```
T=5min:  Requisição HTTP qualquer
         → JWT ainda válido? SIM, mas EXPIRED conforme verificação backend
         → Recebe 401 inesperadamente
         → Interceptor redireciona para /login
         → Mas refresh_token ainda é válido por 7 dias!
         → ERRO: Usuário perdeu sessão válida
```

**Cenário B: Sem `withCredentials`**
```
T=14min: Hook tenta POST /auth/refresh
         → Cookies não são enviados (sem withCredentials)
         → Backend não encontra refresh_token
         → Retorna 401
         → performRefresh() chama window.location.href = '/login'
         → LOOP: Constant 401s e logouts
```

**Necessário:**
```typescript
if (error.response?.status === 401) {
  // ✅ TENTAR REFRESH PRIMEIRO antes de redirecionar
  
  // Estratégia A: Implementar retry com refresh
  // 1. Chamar POST /auth/refresh
  // 2. Se sucesso: retry requisição original com novo token
  // 3. Se falha: ENTÃO redirecionar para login
  
  // OU
  
  // Estratégia B: Deixar useTokenRefresh() handle
  // 1. useTokenRefresh() detecta refresh com falha
  // 2. useTokenRefresh() redireciona para /login
  // 3. Este interceptor NÃO redireciona
  // 4. Apenas nega a requisição
}
```

**Verificação:**
- ✅ Código atual redireciona SEM tentar refresh
- ✅ useTokenRefresh() só dispara a cada 14 minutos
- ✅ Se requisição falha dentro de 14 min, não há oportunidade de renovar

---

### PROBLEMA 3: 🟠 ALTO — Sem Testes para Token Refresh

**Arquivo:** Nenhum arquivo encontrado

**Achado:**
- ✅ Testes existem: `src/__tests__/`
  - `api.test.ts` — Testa API client
  - `hooks.test.ts` — Testa hooks
  - `store.test.ts` — Testa stores
  - Outros...

- ❌ MAS: Grep por `refresh|useTokenRefresh|token.*expir` retornou ZERO matches
- ❌ **NÃO HÁ TESTES PARA:**
  - Renovação automática a cada 14 minutos
  - Concorrência (10+ requisições simultâneas)
  - Compartilhamento de Promise
  - Retry após refresh
  - Loop infinito (se refresh falhar)
  - Cookies enviados (withCredentials)

**Impacto:**
- ❌ Comportamento não validado
- ❌ Regressões podem passar despercebidas
- ❌ Concorrência pode causar múltiplos refreshes

---

## ⚠️ PROBLEMAS SECUNDÁRIOS

### Token Armazenado em localStorage

**Arquivo:** `frontend/src/hooks/useAuthPersist.ts` (linhas 14-28)

**Status:** ✅ Aceitável mas NÃO ideal

**Achado:**
```typescript
const storedToken = localStorage.getItem('auth_token');  // ✅ Access token OK
const storedUser = localStorage.getItem('auth_user');    // ✅ User data OK
```

**Análise:**
- ✅ Access token armazenado em localStorage é prática comum (pode ser melhorado com memória)
- ✅ Refresh token NÃO está em localStorage (correto — está em cookie HttpOnly)
- ⚠️ localStorage é vulnerável a XSS (mas atenuado por HTTPS + SameSite)
- ✅ Sem `sessionStorage` ou outras armazenagens

**Relatório anterior dizia:** "Tokens não em localStorage" — mas isso é **incorreto**. Access token ESTÁ em localStorage.

---

### Ciclo de Vida do Hook

**Arquivo:** `frontend/src/hooks/useTokenRefresh.ts` (linhas 20-70)

**Status:** ✅ Cleanup correto, ⚠️ Possível duplicação

**Achado:**
```typescript
useEffect(() => {
  if (!token) return;
  
  const scheduleRefresh = () => {
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);
    }
    
    refreshIntervalRef.current = setInterval(async () => {
      // Refresh logic
    }, 14 * 60 * 1000);
  };
  
  scheduleRefresh();
  performRefreshIfNeeded();
  
  return () => {
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);  // ✅ Cleanup
    }
  };
}, [token, setAuth, reset]);  // Dependencies
```

**Análise:**
- ✅ Cleanup correto (clearInterval no return)
- ✅ Interval clearado antes de novo
- ⚠️ Dependencies include `setAuth` e `reset`
  - Se esses mudam frequentemente, novo interval é criado
  - Poderia causar múltiplos timers em background
  - **NÃO TESTADO** quanto a isso

---

## 🧪 TESTES EXECUTADOS

**Comando:** `npm test`  
**Status:** ⏳ Em background (timeout 60s)

**Resultado Parcial (antes de timeout):**
- ❌ Múltiplos testes falhando
- ❌ Sem testes específicos para token refresh
- ⚠️ Testes gerais de store e API estão falhando

**Teste crítico ausente:**
```typescript
describe('useTokenRefresh', () => {
  it('should refresh token before expiry', () => {
    // ❌ NÃO EXISTE
  });
  
  it('should handle concurrent requests', () => {
    // ❌ NÃO EXISTE
  });
  
  it('should send refresh_token cookie', () => {
    // ❌ NÃO EXISTE
  });
});
```

---

## 📊 MATRIZ DE SEVERIDADE

| ID | Severidade | Título | Risco | Bloqueador |
|----|-----------|--------|-------|-----------|
| 1 | 🔴 CRÍTICO | Sem `withCredentials` | Refresh não funciona 100% | ✅ SIM |
| 2 | 🔴 CRÍTICO | 401 Redireciona sem refresh | Logout prematuro | ✅ SIM |
| 3 | 🟠 ALTO | Sem testes | Regressões | ⚠️ PARCIAL |
| 4 | 🟡 MÉDIO | Possível duplicação de timer | Vazamento de memória | ❌ NÃO |
| 5 | 🟡 MÉDIO | localStorage em vez de memória | XSS (atenuado) | ❌ NÃO |

---

## ✅ O QUE ESTÁ CORRETO

- ✅ Axios interceptor estructura existe
- ✅ useTokenRefresh hook estrutura existe
- ✅ App.tsx chama hook corretamente
- ✅ Login.tsx extrai dados do JWT
- ✅ Topbar usa campos corretos (actor_id, actor_role)
- ✅ Refresh token NÃO em localStorage (apenas em cookie)
- ✅ Cleanup de interval implementado
- ✅ Compartilhamento de Promise (refreshPromise) para concorrência

---

## 🎯 RECOMENDAÇÃO FINAL

### 🔴 **REPROVAR PHASE 2**

**Razão:** 2 falhas críticas bloqueiam o funcionamento:

1. **Sem `withCredentials: true`**: Cookies não serão enviados, refresh falha 100%
2. **Sem retry com refresh no interceptor 401**: Usuários sofrem logout prematuro

### Correções Obrigatórias Antes de Aprovar

1. ✅ **Adicionar `withCredentials: true`** em api.ts
2. ✅ **Implementar retry com refresh** no interceptor 401
3. ✅ **Criar testes** para token refresh (mínimo 5 casos)

### Esforço Estimado

- Correção 1: 5 minutos (1 linha)
- Correção 2: 30 minutos (implementar retry logic)
- Correção 3: 1-2 horas (testes)

**Total:** ~2 horas

---

## 📌 CHECKPOINT

- **Status:** 🔴 **BLOQUEADO**
- **Próxima etapa:** Corrigir críticos e revalidar
- **Não prosseguir para PHASE 3** até críticos serem resolvidos

---

**Auditoria concluída:** 2026-11-24  
**Auditor:** Claude Haiku 4.5  
**Nível de confiança:** 95% (baseado em análise estática)
