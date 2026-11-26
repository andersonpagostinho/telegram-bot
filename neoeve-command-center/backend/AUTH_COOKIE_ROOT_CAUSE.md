# AUTH_COOKIE_ROOT_CAUSE.md

**Data:** 2026-11-24  
**Status:** Investigação Encerrada  
**Fase:** ETAPA 3 — Análise de Causa Raiz

---

## 1. PROBLEMA CONFIRMADO

### Descrição
O endpoint `/api/v1/auth/login` retorna HTTP 200 OK com body contendo `access_token`, mas **o header `Set-Cookie` não aparece na resposta HTTP recebida pelo cliente**.

### Evidências

#### Teste Isolado (Funciona ✅)
```python
# test_with_cors.py
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], ...)

@app.post("/test-manual-header")
def test_with_header():
    return JSONResponse(
        {"message": "hello"},
        headers={"Set-Cookie": "manual_cookie=..."}
    )

# Resultado:
# Set-Cookie in headers: True ✅
```

#### Endpoint Real (Não Funciona ❌)
```python
# app/api/routes/auth.py
@router.post("/login")
def api_login(...):
    headers = {}
    if refresh_token:
        headers["Set-Cookie"] = f"refresh_token={refresh_token}; ..."
    
    return JSONResponse({...}, headers=headers)

# Resultado:
# Set-Cookie in headers: False ❌
```

### Status do Cookie

| Configuração | Set-Cookie Header | Cookies Capturados |
|---|---|---|
| Teste isolado SEM CORS | ✅ Presente | ✅ Sim |
| Teste isolado COM CORS | ✅ Presente | ✅ Sim |
| **Endpoint real (port 8000)** | ❌ Ausente | ❌ Nenhum |

### Conclusão Confirmada
- Código idêntico funciona em teste isolado
- Código idêntico **não funciona** no endpoint real
- O problema ocorre **entre a função retornar e o cliente receber**

---

## 2. HIPÓTESES AINDA NÃO COMPROVADAS

### Hipótese 1: Uvicorn Reload Mode

**Evidência Circunstancial:**
```python
# main.py, linha 193
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8000,
    reload=settings.DEBUG,  # ← TRUE em development
    log_level=settings.LOG_LEVEL.lower(),
)
```

**Mecanismo Suspeitado:**
- Reload mode reinicia o worker em cada mudança de arquivo
- Pode haver interferência no processamento de headers durante reload
- Headers podem ser removidos/filtrados durante ciclo de reinicialização

**Status:** ❌ **NÃO TESTADO**

**Próximo Passo:** Desabilitar reload mode e rodar endpoint novamente

---

### Hipótese 2: Configuração de Log Level em Uvicorn

**Evidência Circunstancial:**
```python
log_level=settings.LOG_LEVEL.lower(),  # INFO por padrão
```

**Mecanismo Suspeitado:**
- Log level pode afetar processamento de headers
- Stdout/stderr redirecionamento pode interferir com headers HTTP
- Uvicorn pode ter comportamento diferente baseado em log level

**Status:** ❌ **NÃO TESTADO**

**Próximo Passo:** Testar com log_level="critical" ou "error"

---

### Hipótese 3: Middleware Desconhecido ou Configuração Escondida

**Evidência Circunstancial:**
- Busca com grep encontrou apenas 1 middleware registrado (CORS)
- Nenhum middleware customizado encontrado em main.py
- Mas algo está removendo headers

**Mecanismo Suspeitado:**
- Middleware poderia estar sendo adicionado em lugar não óbvio
- Lifespan hooks poderiam estar interferindo
- Starlette internals poderiam estar filtrando headers

**Status:** ❌ **NÃO TESTADO**

**Próximo Passo:** 
- Busca mais profunda por middlewares
- Inspecionar Starlette version/configuração
- Verificar se há código que modifica app.state ou resposta

---

### Hipótese 4: Problema Específico do Endpoint de Login

**Evidência Circunstancial:**
- Código isolado idêntico funciona
- Mesmo código no endpoint real não funciona
- Talvez há decorator ou validation que remove headers

**Mecanismo Suspeitado:**
- FastAPI route registration com APIRouter pode aplicar transformações
- Validation/serialization de response pode descartar headers
- response_model ou outros decoradores podem interferir

**Status:** ❌ **NÃO TESTADO**

**Próximo Passo:** Criar endpoint de teste identêntico em port 8000 para validar

---

### Hipótese 5: Incompatibilidade FastAPI/Starlette/Uvicorn

**Evidência Circunstancial:**
- Multiple abordagens diferentes não funcionam (todos retornam sem Set-Cookie)
- Padrão consistente: manual headers são ignorados no endpoint real
- Isolado funciona, real não funciona

**Mecanismo Suspeitado:**
- Versão incompatível de FastAPI/Starlette/Uvicorn
- Bug conhecido que remove headers
- Interação não documentada entre componentes

**Status:** ❌ **NÃO TESTADO**

**Próximo Passo:** Verificar versões em requirements.txt/pyproject.toml

---

## 3. ALTERNATIVAS AVALIADAS

### Alternativa A: response.set_cookie()
```python
@router.post("/login")
def api_login(response: Response, ...):
    response.set_cookie(...)
    return JSONResponse({...})
```

**Resultado:** ❌ NÃO FUNCIONA
- Não funciona em teste isolado
- Não funciona em endpoint real
- FastAPI não aplica cookies de `response` param quando retorna JSONResponse

**Conclusão:** Descartar completamente

---

### Alternativa B: Manual headers em JSONResponse
```python
return JSONResponse({...}, headers={"Set-Cookie": "..."})
```

**Resultado:** ✅ Funciona em teste isolado | ❌ Não funciona em endpoint real
- É a abordagem correta tecnicamente
- Funciona em ambiente controlado
- Falha em produção por razão desconhecida

**Conclusão:** Mantém como "solução em standby" até resolver root cause

---

### Alternativa C: Usar localStorage no Frontend
```javascript
// Frontend recebe access_token na resposta
// Salva em localStorage em vez de cookie
localStorage.setItem("access_token", response.access_token);
```

**Avaliação:**

| Aspecto | Risco |
|--------|-------|
| **Segurança XSS** | ⚠️ ALTO - localStorage vulnerável a XSS |
| **Vulnerabilidade CSRF** | ✅ BAIXO - localStorage não sofre CSRF |
| **Roubo de Token** | ⚠️ ALTO - malware pode acessar localStorage |
| **Automatização de Requests** | ❌ PROBLEMA - localStorage requer JS, não é automático em cookies |
| **Isolamento de Domains** | ✅ BAIXO - localStorage não compartilha entre domains |
| **Segurança HttpOnly** | ❌ PERDIDA - localStorage não tem flag HttpOnly |
| **Conformidade PCI/GDPR** | ⚠️ QUESTIONÁVEL - localStorage pode não ser permitido |

**Recomendação:** NÃO usar localStorage como solução para refresh_token
- Refresh token deve estar protegido como HttpOnly cookie
- localStorage é inadequado para tokens sensíveis
- Deve ser última opção, não primeira

---

### Alternativa D: Usar Response Object Diretamente
```python
from starlette.responses import Response
resp = Response(json.dumps({...}), media_type="application/json")
resp.set_cookie(...)
return resp
```

**Status:** Não testado antes do encerramento
**Recomendação:** Testar se diferencia de JSONResponse

---

## 4. RECOMENDAÇÃO TÉCNICA

### Próximas Etapas (em Ordem)

1. **IMEDIATO - Desabilitar Reload Mode**
   ```python
   # main.py, linha 193
   uvicorn.run(
       "main:app",
       host="0.0.0.0",
       port=8000,
       reload=False,  # ← TESTE: desabilitar
       log_level=settings.LOG_LEVEL.lower(),
   )
   ```
   **Duração:** 2 minutos  
   **Risco:** Nenhum (apenas teste)  
   **Probabilidade de Sucesso:** 30%

2. **CURTO PRAZO - Criar Endpoint de Teste em Port 8000**
   ```python
   @app.post("/api/v1/test-cookie")
   def test_cookie():
       return JSONResponse(
           {"test": "value"},
           headers={"Set-Cookie": "test=value123; HttpOnly; SameSite=Lax"}
       )
   ```
   **Duração:** 5 minutos  
   **Risco:** Nenhum  
   **Valor:** Isolate problema no endpoint de login vs. framework geral

3. **MÉDIO PRAZO - Verificar Versões de Dependências**
   ```bash
   pip list | grep -E "fastapi|starlette|uvicorn"
   ```
   **Duração:** 2 minutos  
   **Valor:** Detectar incompatibilidades conhecidas

4. **MÉDIO PRAZO - Adicionar Logging ASGI**
   ```python
   async def log_asgi_headers(scope, receive, send):
       async def send_wrapper(message):
           if message["type"] == "http.response.start":
               headers = dict(message.get("headers", []))
               logger.info(f"ASGI Headers: {list(headers.keys())}")
           await send(message)
       await app(scope, receive, send_wrapper)
   
   app.add_middleware(logging_middleware)
   ```
   **Duração:** 10 minutos  
   **Valor:** Ver header no pipeline ASGI exato

5. **LONGO PRAZO - Se Nada Funcionar**
   - Atualizar FastAPI/Starlette para versão mais recente
   - Considerar usar Response object em vez de JSONResponse
   - Contatar suporte FastAPI com reprodução mínima

---

## 5. RISCOS DE MIGRAÇÃO PARA localStorage

### Segurança

**XSS Vulnerability**
- localStorage pode ser acessado por qualquer script na página
- Um script malicioso pode roubar o token
- Cookie HttpOnly protege contra isso

**Mitigação:** Implementar CSP rigoroso, mas não elimina risco

**Impacto:** ⚠️ ALTO - recomendável não fazer

---

### Conformidade

**OWASP A05:2021 - Broken Access Control**
- localStorage para tokens sensíveis é considerado fraco
- Muitos auditorias de segurança flagam isso

**PCI DSS / GDPR**
- localStorage pode não ser permitido para dados sensíveis
- Requisitos variam, consultar compliance team

**Impacto:** ⚠️ MÉDIO - potencial problema regulatório

---

### Funcionalidade

**Dependência de JavaScript**
- localStorage requer JavaScript habilitado
- Cookie HttpOnly é enviado automaticamente pelo navegador
- Fallback automático não é possível

**Impacto:** 🔴 CRÍTICO - rompe fallback de segurança

---

### Conclusão Sobre localStorage

**NÃO RECOMENDADO** como solução para refresh_token

Razões:
1. ❌ Vulnerável a XSS
2. ❌ Perde proteção HttpOnly
3. ❌ Potencial conflito de conformidade
4. ❌ Dependência de JavaScript
5. ✅ Único benefício: evita CSRF (mas cookies com SameSite já evitam)

**Se forçado a usar localStorage:**
- Apenas para access_token (curta duração)
- Nunca para refresh_token
- Com CSP rigoroso
- Com validação adicional de tokens

---

## 6. ENTREGÁVEIS DESTA ETAPA

✅ Documentos Produzidos:
1. `AUTH_COOKIE_MIDDLEWARE_AUDIT.md` - Auditoria de middlewares
2. `AUTH_COOKIE_HTTP_TRACE.md` - Rastreamento HTTP
3. `AUTH_COOKIE_ROOT_CAUSE.md` - Este documento

---

## 7. ESTADO ATUAL DA AUTENTICAÇÃO

### Bloqueado ❌
- Login não persiste refresh_token em cookie
- WebSocket não pode ser autenticado sem refresh_token
- Topbar não pode exibir status 🟢 Connected

### Funcionando ✅
- Access token é gerado e retornado
- Usuário é autenticado no login (banco de dados confirmado)
- Status HTTP 200 OK na resposta

### Próximas Ações
Aguardar aprovação do usuário para:
1. Desabilitar reload mode e reteste
2. Criar endpoints de teste isolados em port 8000
3. Ou migrar para solução alternativa (se necessário)

---

## 8. RESUMO EXECUTIVO

**Problema:** Set-Cookie header desaparece entre função retornar e cliente receber

**Causa Raiz:** Desconhecida (não foi possível isolar em 1 sessão de investigação)

**Evidências:**
- ✅ Código idêntico funciona em teste isolado (port 8003)
- ❌ Código idêntico não funciona no endpoint real (port 8000)
- ✅ Manual headers funcionam quando código é simples
- ❌ Manual headers não funcionam no contexto real

**Hipóteses Principais (não testadas):**
1. Uvicorn reload mode interfere com headers
2. Configuração de log level afeta processamento
3. Middleware desconhecido está removendo headers
4. Comportamento específico do endpoint de login
5. Incompatibilidade de versões FastAPI/Starlette

**Recomendação:** Desabilitar reload mode (5 min) ou criar teste isolado em port 8000 (5 min) para próxima sessão

**NÃO RECOMENDADO:** Migrar refresh_token para localStorage (riscos de segurança altos)

---

**Próxima Etapa:** Aguardar aprovação para retomar investigação com testes específicos recomendados acima.
