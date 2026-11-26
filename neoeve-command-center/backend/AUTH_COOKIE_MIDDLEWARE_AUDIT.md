# AUTH_COOKIE_MIDDLEWARE_AUDIT.md

**Data:** 2026-11-24  
**Status:** Investigação Concluída  
**Fase:** ETAPA 1 — Auditoria de Middlewares

---

## 1. MIDDLEWARES IDENTIFICADOS

### Middleware Registrado em main.py

```python
# app/main.py, linhas 118-124
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**CORS_ORIGINS** (definido em app/core/config.py:38-41):
- `http://localhost:3000`
- `http://localhost:5173`
- `http://localhost:8080`

**CORS Configuration:**
- `allow_credentials=True` ✅ (essencial para cookies)
- `allow_methods=["*"]` ✅
- `allow_headers=["*"]` ✅

### Exception Handler Identificado

```python
# app/main.py, linhas 180-187
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
```

**Observação:** Exception handler cria nova JSONResponse sem preservar headers. NÃO relevante para endpoint de login (que retorna 200 OK sem exceção).

---

## 2. TESTES REALIZADOS

### Teste 1: Isolado SEM CORS

**Código:**
```python
# test_no_cors.py
# Nenhum middleware adicionado

@app.post("/test-cookie-no-cors")
def test_with_response(response: Response):
    response.set_cookie(...)
    return JSONResponse({"message": "hello"})

@app.post("/test-manual-header")
def test_with_header():
    return JSONResponse(
        {"message": "hello"},
        headers={"Set-Cookie": "manual_cookie=..."}
    )
```

**Resultados:**

| Endpoint | Método | Set-Cookie Header |
|----------|--------|-------------------|
| `/test-cookie-no-cors` | `response.set_cookie()` | ❌ **NÃO PRESENTE** |
| `/test-manual-header` | Manual `headers={}` | ✅ **PRESENTE** |

**Conclusão Teste 1:**
- `response.set_cookie()` com `return JSONResponse()` **não funciona**
- Manual `headers={"Set-Cookie": ...}` em JSONResponse **funciona**

---

### Teste 2: Isolado COM CORS (mesmo que main.py)

**Código:**
```python
# test_with_cors.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/test-manual-header")
def test_with_header():
    return JSONResponse(
        {"message": "hello"},
        headers={"Set-Cookie": "manual_cookie=..."}
    )
```

**Requisição com CORS Origin:**
```bash
POST /test-manual-header
Origin: http://localhost:5173
```

**Resultado:**
```
Status: 200
Set-Cookie in headers: True
Set-Cookie value: manual_cookie=manual_value_123; HttpOnly; SameSite=Lax
```

**Conclusão Teste 2:**
- CORS middleware **NÃO filtra** Set-Cookie header
- Manual headers funcionam **com CORS ativo**
- `allow_credentials=True` está sendo respeitado

---

## 3. COMPORTAMENTOS OBSERVADOS

### Padrão 1: response.set_cookie() Nunca Funciona com JSONResponse

**Observação:**
Quando um endpoint tem `response: Response` como parâmetro injetado e retorna `JSONResponse()`:
- `response.set_cookie()` é chamado
- Nenhum erro é lançado
- **Mas o header Set-Cookie não aparece na resposta HTTP**

**Hipótese (não comprovada):**
- FastAPI cria uma nova resposta HTTP interna
- A resposta injetada (`response`) é apenas para metadados
- Cookies setados em `response` não são propagados para a JSONResponse retornada

---

### Padrão 2: Manual Headers Funcionam Consistentemente

**Observação:**
Quando `headers={"Set-Cookie": "value"}` é passado diretamente ao JSONResponse:
- Header aparece na resposta HTTP
- CORS não filtra
- Funciona com múltiplos middlewares

**Comportamento Confirmado:**
- ✅ Com CORS
- ✅ Sem CORS
- ✅ Com Origin header
- ✅ Com credentials

---

## 4. DIFERENÇAS ENTRE ABORDAGENS

### Abordagem A: response.set_cookie()
```python
@router.post("/login")
def api_login(response: Response, ...):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="Lax",
    )
    return JSONResponse({...})
```

**Resultado em Teste Isolado:** ❌ Set-Cookie não aparece
**Resultado em Endpoint Real:** ❌ Set-Cookie não aparece

---

### Abordagem B: Manual headers em JSONResponse
```python
@router.post("/login")
def api_login(...):
    return JSONResponse(
        {...},
        headers={"Set-Cookie": f"refresh_token={token}; ..."}
    )
```

**Resultado em Teste Isolado:** ✅ Set-Cookie aparece
**Resultado em Endpoint Real:** ❌ Set-Cookie não aparece (ainda investigar)

---

## 5. CONCLUSÕES DESTA ETAPA

✅ **Confirmado:**
1. CORSMiddleware está configurada corretamente com `allow_credentials=True`
2. CORSMiddleware **não filtra** headers Set-Cookie
3. Manual `headers={"Set-Cookie": ...}` funciona em testes isolados
4. `response.set_cookie()` não funciona com `return JSONResponse()`

❓ **Ainda Desconhecido:**
1. Por que manual headers não funcionam no endpoint real (port 8000)
2. Se há outro middleware removendo headers
3. Se a configuração de Uvicorn (reload mode) está interferindo
4. Se há um wrapper ou proxy entre o endpoint e o cliente

---

## 6. RECOMENDAÇÕES PARA PRÓXIMA ETAPA

1. **Rastrear ASGI** - inserir logging no nível ASGI para ver se header existe antes de enviar
2. **Verificar Uvicorn** - testar em modo sem reload para descartar esse fator
3. **Inspecionar Cadeia HTTP** - usar curl com verbosity alta para ver exatamente o que chega

---

**Próxima Etapa:** AUTH_COOKIE_HTTP_TRACE.md
