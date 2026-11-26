# WEBSOCKET PHASE 4 — PLANO DE VALIDAÇÃO INTEGRADA

**Data:** 2026-11-24  
**Status:** 🔵 **PRÉ-VALIDAÇÃO COMPLETA**

---

## ✅ PRÉ-VALIDAÇÃO

| Item | Status | Detalhe |
|------|--------|---------|
| Backend (8000) | ✅ ATIVO | Uvicorn respondendo |
| PostgreSQL (5432) | ✅ ATIVO | Banco acessível |
| Frontend (5173) | ⏳ AGUARDANDO | Iniciará quando necessário |
| Recovery Worker | ✅ DESATIVADO | Confirmado |
| Produção | ✅ PROTEGIDA | Sem acesso |

---

## 📋 CENÁRIOS DE TESTE (15 TOTAL)

### **GRUPO 1: Autenticação Básica**

#### Cenário 1: Login Normal
**Procedimento:**
1. Abrir http://localhost:5173 (ou .env `VITE_API_URL`)
2. Inserir credenciais válidas (desenvolvimento)
3. Clicar "Entrar"

**Esperado:**
```
✅ Login bem-sucedido
✅ JWT recebido (access_token)
✅ Refresh token recebido (cookie HttpOnly)
✅ Redirect para /
✅ Usuário exibido na Topbar
```

**Validação:**
- DevTools → Application → Cookies → `refresh_token` presente
- DevTools → Application → LocalStorage → `auth_token` presente
- DevTools → Network → POST /auth/login → 200 OK

---

#### Cenário 2: WebSocket com Token Válido
**Procedimento:**
1. Após login bem-sucedido
2. Verificar WebSocket no Topbar (indicador verde)

**Esperado:**
```
✅ WebSocket conectado imediatamente
✅ Topbar mostra "Connected" (verde)
✅ Activity Stream funcional
```

**Validação:**
- DevTools → Network → WebSocket → ws://localhost:8000/api/v1/websocket/ws
- DevTools → Console → Sem erros de conexão
- Activity Stream mostra eventos em tempo real

---

### **GRUPO 2: Expiração e Renovação de Token**

#### Cenário 3: Access Token Expirado Antes da Conexão
**Procedimento:**
1. Após login: Wait 1 segundo
2. Simular expiração: Modify localStorage `auth_token` para token expirado
3. Forçar reload: F5
4. Tentar qualquer ação API

**Esperado:**
```
✅ Interceptor detecta 401
✅ Interceptor chama refresh (automático)
✅ Novo access_token obtido
✅ Requisição original retentada
✅ Funcional (sem logout)
```

**Validação:**
- DevTools → Network → POST /auth/refresh → 200 OK
- DevTools → Network → Requisição original → 200 OK (retry)
- Sem redirect para /login

---

#### Cenário 4: Refresh Automático Antes do Ticket
**Procedimento:**
1. Após login (T=0min)
2. Simular passagem de tempo (ou usar DevTools para simular)
3. Fechar WebSocket (DevTools → Network → Right-click WebSocket → Disconnect)
4. Aguardar reconexão (backoff 1s)

**Esperado:**
```
✅ websocketService.connect() chamado
✅ Token verificado (useAuthStore)
✅ POST /websocket/ticket com token válido
✅ Ticket obtido
✅ Novo WebSocket abre
✅ Topbar volta a "Connected"
```

**Validação:**
- DevTools → Network → POST /websocket/ticket → 200 OK
- DevTools → Network → WebSocket novo → conecta
- Sem POST /auth/refresh (token ainda válido)

---

#### Cenário 5: Ticket Retorna 401 → Refresh + Retry
**Procedimento:**
1. Simular token expirado localmente (editar localStorage `auth_token`)
2. Fechar WebSocket (força reconexão)
3. Backoff vai tentar reconectar

**Esperado:**
```
✅ 1ª tentativa: POST /websocket/ticket
✅ Resposta: 401 Unauthorized
✅ Interceptor: POST /auth/refresh
✅ Novo token obtido
✅ 2ª tentativa: POST /websocket/ticket
✅ Sucesso: ticket obtido
✅ WebSocket abre
✅ Sem terceira tentativa
```

**Validação:**
- DevTools → Network → Sequência:
  1. POST /websocket/ticket → 401
  2. POST /auth/refresh → 200
  3. POST /websocket/ticket → 200
  4. WebSocket → conecta
- Sem loop infinito
- Sem terceira tentativa

---

### **GRUPO 3: Falhas de Autenticação**

#### Cenário 6: Refresh Token Expirado (7 dias)
**Procedimento:**
1. Expirar refresh token: Editar cookie `refresh_token` (ou deixar expirar naturalmente - não fazer em teste)
2. Fechar WebSocket
3. Backoff vai tentar reconectar

**Esperado:**
```
✅ websocketService.requestTicketWithRetry()
✅ POST /websocket/ticket → 401
✅ refreshAttempted = false, tenta refresh
✅ POST /auth/refresh → 401 (refresh expirado)
✅ Emite: AUTH_EXPIRED
✅ useWebSocket: authStore.reset()
✅ Logout: redirect /login
```

**Validação:**
- DevTools → Network → POST /auth/refresh → 401
- Redirect para /login
- localStorage limpo
- Cookie refresh_token removido

---

#### Cenário 7: Refresh Token Revogado (ou revoked)
**Procedimento:**
1. Revogar refresh token no backend: (executar SQL ou delete na BD)
2. Fechar WebSocket
3. Backoff vai tentar reconectar

**Esperado:**
```
✅ websocketService: POST /websocket/ticket
✅ Resposta: 401
✅ Retry: POST /auth/refresh
✅ Resposta: 401 (token revoked)
✅ Emite: AUTH_EXPIRED
✅ Logout
```

**Validação:**
- DevTools → Network → POST /auth/refresh → 401
- Redirect /login

---

### **GRUPO 4: Desconexão e Reconexão**

#### Cenário 8: Queda Inesperada do WebSocket
**Procedimento:**
1. Conectar WebSocket
2. DevTools → Network → Right-click WebSocket → Disconnect
3. Ou: Fechar abruptamente a conexão (Ctrl+Alt+Delete no Windows Task Manager, then Kill)

**Esperado:**
```
✅ onClose() acionado
✅ isConnected = false
✅ ticket = null
✅ refreshAttempted = false
✅ Backoff inicia: 1s
```

**Validação:**
- Topbar: "Offline" (vermelho)
- DevTools → Console: "WebSocket closed" (esperado)
- Não há novo WebSocket aberto imediatamente

---

#### Cenário 9: Reconexão com Ticket Novo
**Procedimento:**
1. WebSocket está desconectado
2. Aguardar 1s (backoff 1)
3. Verificar reconexão

**Esperado:**
```
✅ Backoff dispara: setTimeout 1s
✅ retryCount incrementa (0 → 1)
✅ websocketService.connect() chamado
✅ POST /websocket/ticket → novo ticket (não reutiliza anterior)
✅ WebSocket abre com novo ticket
✅ Topbar: "Connected" (verde)
✅ Eventos começam a chegar
```

**Validação:**
- Topbar volta a "Connected"
- Novo ticket na URL é diferente do anterior
- Activity Stream recebe eventos

---

#### Cenário 10: Concorrência - Dez Tentativas Sem Duplicação
**Procedimento:**
1. Conectar com sucesso
2. Forçar disconnect
3. Rapidamente abrir DevTools Network
4. Aguardar ~1s para reconexão
5. Verificar Network

**Esperado:**
```
✅ Apenas 1x POST /websocket/ticket
✅ Apenas 1x WebSocket novo
✅ NÃO múltiplas tentativas simultâneas
✅ refreshAttempted flag funciona
✅ Sem timers duplicados
```

**Validação:**
- DevTools → Network → Apenas 1 POST /websocket/ticket
- Sem múltiplas conexões WebSocket simultâneas
- retryCount incrementa sequencialmente (1, 2, 3...)

---

### **GRUPO 5: Disponibilidade da API**

#### Cenário 11: API Indisponível (503)
**Procedimento:**
1. Parar backend: Ctrl+C no terminal
2. Forçar reconexão WebSocket (desconectar)
3. Backoff vai tentar

**Esperado:**
```
✅ POST /websocket/ticket → Connection refused (ou timeout)
✅ Backoff continua: 1s, 2s, 4s, 8s, 16s
✅ Depois de 5 retries: MAX_RETRIES_EXCEEDED
✅ Emite erro: API_OFFLINE (ou similar)
✅ Topbar: "Offline" (vermelho)
```

**Validação:**
- DevTools → Network → Erros de conexão recusada
- Sem redirect para /login (diferente de AUTH_EXPIRED)
- Contador de retry visible no console (opcional)

**Nota:** Reiniciar backend após este teste: `python -m uvicorn app.main:app --reload`

---

#### Cenário 12: WebSocket Desconectado, API Online
**Procedimento:**
1. Backend online
2. Desconectar WebSocket apenas (não backend)
3. Fazer outra requisição HTTP (ex: GET /api/v1/agents)

**Esperado:**
```
✅ GET /api/v1/agents → 200 OK (API funciona)
✅ WebSocket reconecta em paralelo
✅ Ambos funcionam independentemente
✅ Activity Stream recupera após reconexão
```

**Validação:**
- DevTools → Network → GET /agents → 200 OK
- Topbar mostra: API responsivo, WebSocket reconectando
- Sem logout

---

### **GRUPO 6: Logout e Limpeza**

#### Cenário 13: Logout Durante Conexão
**Procedimento:**
1. WebSocket conectado
2. Clicar "Sair" (Logout button)

**Esperado:**
```
✅ Chamar apiClient.logout()
✅ authStore.reset()
✅ localStorage limpo
✅ Cookies limpos
✅ websocketService.disconnect()
✅ Sem reconexão automática
✅ Redirect /login
```

**Validação:**
- Redirect /login imediato
- localStorage: auth_token removido
- DevTools → Cookies → refresh_token removido
- WebSocket fecha (não reconecta)

---

### **GRUPO 7: Recuperação de Eventos**

#### Cenário 14: Recuperação de Eventos pelo Cursor
**Procedimento:**
1. Conectado e recebendo eventos
2. Activity Stream mostra eventos com cursor
3. Desconectar WebSocket
4. Enquanto desconectado: Backend emite 5 eventos (ou simular)
5. Reconectar

**Esperado:**
```
✅ Último cursor salvo (ex: cursor=100)
✅ Desconexão: eventos não chegam
✅ Reconexão: WebSocket abre
✅ onOpen() chama: reconnect() com cursor
✅ Backend retorna: eventos posteriores a cursor=100
✅ Activity Stream mostra eventos recuperados
✅ Sem duplicação (deduplication por event_id)
```

**Validação:**
- DevTools → Console: Vê "reconnect" action com cursor
- Activity Stream recebe eventos antigos + novos
- Sem duplicação visual

---

#### Cenário 15: Activity Stream Após Reconexão Sem Duplicação
**Procedimento:**
1. Activity Stream mostra eventos (ex: 10 eventos)
2. Desconectar/reconectar
3. Verificar Activity Stream após reconexão

**Esperado:**
```
✅ 10 eventos originais mantêm
✅ Eventos recuperados adicionados
✅ Sem duplicação de IDs
✅ Ordem chronológica mantida
✅ Novo evento pode chegar em tempo real após reconexão
```

**Validação:**
- Activity Stream mostra todos eventos sem duplicação
- Event IDs únicos
- Ordem temporal correta

---

## 🧪 TESTE CRÍTICO DE SESSÃO (Integrado)

**Fluxo completo em 5 minutos:**

```
1. T=0s:   Login
   ✅ JWT obtido
   ✅ Refresh token em cookie

2. T=1s:   WebSocket conectado
   ✅ Topbar: "Connected"

3. T=2s:   Simular expiração: Modify localStorage
   ✅ Interceptor detecta 401
   ✅ Refresh automático
   ✅ Novo token obtido

4. T=3s:   Desconectar WebSocket
   ✅ Backoff: 1s

5. T=4s:   Reconectar (backoff dispara)
   ✅ POST /websocket/ticket (com novo token)
   ✅ WebSocket novo
   ✅ Topbar: "Connected"

6. T=5s:   Activity Stream funcional
   ✅ Eventos chegando
   ✅ Sem duplicação
   ✅ Sem logout
```

---

## 📊 MATRIZ DE VALIDAÇÃO

| # | Cenário | Manual? | Automático? | Status |
|---|---------|---------|-------------|--------|
| 1 | Login | ✅ | ⏳ | ⏳ TESTE |
| 2 | WebSocket válido | ✅ | ✅ | ⏳ TESTE |
| 3 | Token expirado | ✅ | ✅ | ⏳ TESTE |
| 4 | Refresh antes ticket | ✅ | ✅ | ⏳ TESTE |
| 5 | 401 + Retry | ✅ | ✅ | ⏳ TESTE |
| 6 | Refresh expirado | ✅ | ⏳ | ⏳ TESTE |
| 7 | Refresh revogado | ✅ | ✅ | ⏳ TESTE |
| 8 | Queda WS | ✅ | ✅ | ⏳ TESTE |
| 9 | Reconexão novo ticket | ✅ | ✅ | ⏳ TESTE |
| 10 | Sem duplicação | ✅ | ✅ | ⏳ TESTE |
| 11 | API offline | ✅ | ✅ | ⏳ TESTE |
| 12 | WS offline, API online | ✅ | ✅ | ⏳ TESTE |
| 13 | Logout durante | ✅ | ✅ | ⏳ TESTE |
| 14 | Recuperar eventos | ✅ | ✅ | ⏳ TESTE |
| 15 | Activity Stream | ✅ | ✅ | ⏳ TESTE |

---

## 🔧 Ferramentas Necessárias

| Ferramenta | Status | Uso |
|-----------|--------|-----|
| Browser DevTools | ✅ | Network, Console, Storage |
| Localhost:8000 | ✅ | Backend API |
| Localhost:5173 | ✅ | Frontend dev server |
| PostgreSQL | ✅ | Banco de dados |

---

## ⏭️ Próximos Passos

1. ✅ Iniciar frontend dev server: `npm run dev`
2. ✅ Executar cenários 1-15 manualmente
3. ✅ Documentar resultados em WEBSOCKET_PHASE4_TEST_RESULTS.md
4. ✅ Criar relatório final

---

**Plano Pronto:** 🟢 Aguardando Execução dos Testes
