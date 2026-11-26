# AUTH_COOKIE_HTTP_TRACE.md

**Data:** 2026-11-24  
**Status:** Investigação Concluída  
**Fase:** ETAPA 2 — Rastreamento HTTP

---

## 1. TESTES DE EMISSÃO DO SET-COOKIE

### Teste 1A: Endpoint Isolado SEM CORS - response.set_cookie()

**Configuração:**
```
Porta: 8002
CORS: Nenhum middleware
Método: response.set_cookie() + return JSONResponse()
```

**Requisição:**
```bash
POST http://127.0.0.1:8002/test-cookie-no-cors
Content-Type: application/json
```

**Resposta HTTP:**
```
HTTP/1.1 200 OK
content-length: 433
content-type: application/json

(sem Set-Cookie header)
```

**Resultado:**
```
Set-Cookie in headers: False
Cookies captured by session: NONE
```

**Conclusão:** ❌ Set-Cookie não emitido

---

### Teste 1B: Endpoint Isolado SEM CORS - Manual headers

**Configuração:**
```
Porta: 8002
CORS: Nenhum middleware
Método: Manual headers={"Set-Cookie": "..."}
```

**Requisição:**
```bash
POST http://127.0.0.1:8002/test-manual-header
Content-Type: application/json
```

**Resposta HTTP:**
```
HTTP/1.1 200 OK
content-type: application/json

Header: Set-Cookie = manual_cookie=manual_value_123; HttpOnly; SameSite=Lax
```

**Resultado:**
```
Set-Cookie in headers: True ✅
Set-Cookie value: manual_cookie=manual_value_123; HttpOnly; SameSite=Lax
```

**Conclusão:** ✅ Set-Cookie emitido corretamente

---

### Teste 2: Endpoint Isolado COM CORS - Manual headers

**Configuração:**
```
Porta: 8003
CORS: CORSMiddleware (allow_credentials=True)
Método: Manual headers={"Set-Cookie": "..."}
```

**Requisição:**
```bash
POST http://127.0.0.1:8003/test-manual-header
Origin: http://localhost:5173
Content-Type: application/json
```

**Resposta HTTP:**
```
HTTP/1.1 200 OK
content-type: application/json
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: http://localhost:5173

Header: Set-Cookie = manual_cookie=manual_value_123; HttpOnly; SameSite=Lax
```

**Resultado:**
```
Set-Cookie in headers: True ✅
Set-Cookie value: manual_cookie=manual_value_123; HttpOnly; SameSite=Lax
Cookies captured by session: (cookie foi adicionado à session)
```

**Conclusão:** ✅ Set-Cookie emitido corretamente COM CORS

---

## 2. RESULTADO NO ENDPOINT REAL

### Endpoint Real: /api/v1/auth/login

**Configuração:**
```
Porta: 8000
Middleware: CORSMiddleware (allow_credentials=True)
Método: Manual headers={"Set-Cookie": f"refresh_token={token}; ..."}
Backend: Uvicorn com reload=True
```

**Requisição:**
```bash
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json
{
  "email": "admin@test.com",
  "password": "Admin123!"
}
```

**Resposta HTTP (observada):**
```
HTTP/1.1 200 OK
date: Tue, 24 Nov 2026 21:...
server: uvicorn
content-length: 433
content-type: application/json
vary: Origin

{
  "access_token": "eyJ...",
  "token_type": "bearer",
  ...
}
```

**Resultado:**
```
Status: 200
Set-Cookie in headers: False ❌
Cookies captured by session: NONE
```

**Conclusão:** ❌ Set-Cookie não aparece na resposta

---

## 3. COMPARAÇÃO: Teste Isolado vs. Endpoint Real

### Headers Retornados

| Teste | Configuração | Manual Headers | Set-Cookie Recebido |
|-------|--------------|---|---|
| Isolado SEM CORS | response.set_cookie() | ❌ | ❌ |
| Isolado SEM CORS | Manual headers | ✅ | ✅ |
| Isolado COM CORS | Manual headers | ✅ | ✅ |
| **Endpoint Real** | Manual headers | ✅ | ❌ |

**Observação Crítica:**
- Teste isolado com CORS funciona
- Endpoint real com CORS **não funciona**
- Código é idêntico

---

## 4. EVIDÊNCIAS COLETADAS

### O que Funciona (Comprovado)

1. ✅ Manual `headers={"Set-Cookie": "..."}` em JSONResponse
2. ✅ CORS middleware não filtra Set-Cookie (testado)
3. ✅ `allow_credentials=True` está ativo
4. ✅ Resposta HTTP retorna 200 OK
5. ✅ Access-Control headers corretos em teste isolado

### O que NÃO Funciona (Comprovado)

1. ❌ `response.set_cookie()` com JSONResponse
2. ❌ Set-Cookie header no endpoint real (port 8000)
3. ❌ Manual headers no endpoint real (apesar de funcionar isolado)

### O que Não Foi Comprovado

1. ❓ Se Uvicorn reload mode remove headers
2. ❓ Se há outro middleware no backend real
3. ❓ Se há um wrapper HTTP entre FastAPI e cliente
4. ❓ Em que exato ponto do pipeline o header desaparece

---

## 5. ANÁLISE DO CAMINHO HTTP

### Fluxo Esperado (baseado em teste isolado que funciona)

```
Código do Endpoint
  ↓
JSONResponse(data, headers={"Set-Cookie": "..."})
  ↓
FastAPI Application
  ↓
CORSMiddleware (adiciona Access-Control headers)
  ↓
Uvicorn (encapsula em ASGI)
  ↓
HTTP Client recebe Set-Cookie ✅
```

### Fluxo Observado (endpoint real)

```
Código do Endpoint
  ↓
JSONResponse(data, headers={"Set-Cookie": "..."})
  ↓
FastAPI Application
  ↓
CORSMiddleware
  ↓
Uvicorn (reload mode? log level? other?)
  ↓
HTTP Client recebe SEM Set-Cookie ❌
```

---

## 6. HIPÓTESES AINDA NÃO COMPROVADAS

### H1: Uvicorn Reload Mode
- **Pista:** Backend main.py usa `reload=settings.DEBUG` (TRUE em dev)
- **Teste que valida:** Desabilitar reload e rodar novamente
- **Status:** Não testado

### H2: Configuração de Uvicorn Logging
- **Pista:** Logs aparecem, mas headers podem estar sendo filtrados internamente
- **Teste que valida:** Inserir logging no nível ASGI
- **Status:** Não testado

### H3: Outro Middleware Desconhecido
- **Pista:** Busca com grep encontrou apenas 1 middleware
- **Teste que valida:** Remover CORS temporariamente, testar
- **Status:** Não testado

### H4: Problema no Endpoint Específico
- **Pista:** Mesmo código isolado funciona, mas no endpoint real não
- **Teste que valida:** Copiar código exato para novo endpoint em port 8000
- **Status:** Não testado

---

## 7. O QUE PODE SER COMPROVADO AGORA

Sem fazer mais testes, o que podemos afirmar:

✅ **Fato Comprovado:**
- Manual `headers={"Set-Cookie": ...}` funciona em FastAPI com CORS

✅ **Fato Comprovado:**
- Teste isolado de código idêntico funciona

❌ **Fato NÃO Comprovado:**
- Por que o mesmo código não funciona no endpoint real

---

## 8. PRÓXIMOS PASSOS RECOMENDADOS

Para resolver, investigar (nesta ordem):

1. **Verificar logs do Uvicorn** - há linhas sobre Set-Cookie?
2. **Desabilitar reload mode** - testar sem reload
3. **Adicionar logging ASGI** - rastrear header no pipeline
4. **Teste simples em port 8000** - criar endpoint de teste identêntico no backend real

---

**Próxima Etapa:** AUTH_COOKIE_ROOT_CAUSE.md
