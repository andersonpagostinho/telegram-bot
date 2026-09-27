# GATE C3.15.3-A — AUDITORIA DA RESOLUÇÃO DE IDENTIDADE WHATSAPP EM PRODUÇÃO

**STATUS:** PASS (Auditoria Completa)  
**DATA:** 2026-09-26  
**ESCOPO:** Diagnóstico - ZERO alterações de código

---

## RESUMO EXECUTIVO

O webhook WhatsApp **resolve corretamente o tenant_id (7394370553)** a partir do phone_number_id, mas **não passa esse valor para o router**. O roteador então tenta resolver o tenant a partir do wa_id (5511991382080), falha, e cai em TENANT_FALLBACK que usa wa_id como tenant_id.

**Resultado:**
- ✅ Ponto A (webhook): tenant_id correto = 7394370553
- ❌ Ponto B (router): tenant_id incorreto = 5511991382080 (wa_id)
- ❌ Ponto C (sessão): carrega de `Clientes/5511991382080/Sessoes/5511991382080`
- ❌ Ponto D (onboarding): processa com tenant_id errado, antes de identidade

---

## 1. FLUXO COMPLETO (DO WEBHOOK AO ROUTER)

### Transição 1: Webhook → Resolver Endpoint

**arquivo:** `main.py:171-304`  
**função:** `whatsapp_webhook_post()`

```python
# main.py:190-192
metadata = value.get("metadata", {})
phone_number_id = metadata.get("phone_number_id")

# main.py:225
tenant_id = resolver_tenant_por_endpoint(phone_number_id)
# ✅ Retorna: 7394370553
```

**Status:** ✅ CORRETO

---

### Transição 2: Resolver Endpoint (Firestore)

**arquivo:** `services/whatsapp_endpoint_service.py:93-126`  
**função:** `resolver_tenant_por_endpoint(phone_number_id)`

```python
# Linha 112-119
doc = get_db().collection("WhatsAppEndpoints").document(phone_number_id).get()
if doc.exists:
    doc_data = doc.to_dict()
    if doc_data.get("status") == "ativo":
        tenant_id = doc_data.get("tenant_id")
        print(f"[OK] resolver_tenant_por_endpoint({phone_number_id}): {tenant_id}")
        return tenant_id
```

**Path consultado:** `WhatsAppEndpoints/{phone_number_id}`  
**Saída:** `7394370553` ✅

**Status:** ✅ CORRETO

---

### Transição 3: Webhook → Roteador (PROBLEMA!)

**arquivo:** `main.py:231-259`  
**função:** `whatsapp_webhook_post()` (continuação)

```python
# main.py:225
tenant_id = resolver_tenant_por_endpoint(phone_number_id)  # 7394370553 ✅

# ❌ PROBLEMA: tenant_id resolvido NÃO é passado para roteador

# main.py:237-242
future = asyncio.run_coroutine_threadsafe(
    roteador_principal(
        user_id=from_number,           # 5511991382080 (wa_id)
        mensagem=text_body,
        update=None,
        context=None
        # ❌ tenant_id=tenant_id DEVERIA ESTAR AQUI
    ),
    bot_loop
)
```

**Status:** ❌ **TENANT_ID RESOLVIDO NÃO É PASSADO PARA O ROTEADOR**

**Variável perdida aqui:** `tenant_id = 7394370553`

---

### Transição 4: Roteador Tenta Resolver Tenant (FALLBACK)

**arquivo:** `router/principal_router.py:3364-3379`  
**função:** `roteador_principal(user_id, mensagem, update=None, context=None)`

```python
# Linha 3376-3379
dono_id = await obter_id_dono(user_id)  # user_id = 5511991382080
if not dono_id:
    dono_id = str(user_id)  # ❌ FALLBACK INCORRETO!
    print(f"[TENANT_FALLBACK] obter_id_dono retornou None, usando user_id como fallback | user_id={user_id}")
```

**O que acontece:**
1. `obter_id_dono("5511991382080")` busca cliente com ID 5511991382080
2. Cliente não existe (é um wa_id, não um dono_id)
3. Retorna None
4. Fallback: `dono_id = "5511991382080"` (wa_id como string)

**Status:** ❌ **TENANT_ID RESOLVIDO INCORRETAMENTE. AGORA dono_id = 5511991382080**

**Comparação:**
- ✅ Deveria ser: `dono_id = 7394370553` (resolvido do webhook)
- ❌ Ficou sendo: `dono_id = "5511991382080"` (wa_id)

---

### Transição 5: Carregar Contexto com Tenant Errado

**arquivo:** `router/principal_router.py:3390`  
**função:** `roteador_principal()` (continuação)

```python
# Linha 3390
ctx = await carregar_contexto_temporario_v2(dono_id, user_id) or {}
#                                          ^^^^^^^  ^^^^^^^
#                                          errado  correto
```

**Alias expande para:**
```python
# utils/contexto_temporario.py:131-133
async def carregar_contexto_temporario_v2(dono_id: str, cliente_id: str):
    return await carregar_sessao_temporaria(cliente_id, dono_id)
    #                                       ^^^^^^^^^^  ^^^^^^^
    #                                       user_id     dono_id (errado!)
```

**Função real:**
```python
# utils/contexto_temporario.py:65-89
async def carregar_sessao_temporaria(actor_id: str, tenant_id: str):
    path_novo = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    #                            ^^^^^^^
    #                            5511991382080 (errado!)
```

**Path carregado:**
```
Clientes/5511991382080/Sessoes/5511991382080
```

**Path esperado:**
```
Clientes/7394370553/Sessoes/{actor_id_canonico}
```

**Status:** ❌ **CONTEXTO CARREGADO DO PATH ERRADO**

**Log evidência:**
```
[DIAG] [LOAD SESSAO v2] path=Clientes/5511991382080/Sessoes/5511991382080 | source=novo | tenant=5511991382080 | actor=5511991382080
```

Deveria ser:
```
[DIAG] [LOAD SESSAO v2] path=Clientes/7394370553/Sessoes/{actor_id} | source=novo | tenant=7394370553 | actor={actor_id}
```

---

### Transição 6: Detectar Onboarding e Processar Antes de Identidade

**arquivo:** `router/principal_router.py:3421-3436`  
**função:** `roteador_principal()` (continuação)

```python
# Linha 3421-3422
if ctx.get("estado_fluxo") == "onboarding_dono":
    print(f"[ROUTER] DETECTADO: estado_fluxo=onboarding_dono, processando resposta ANTES de identidade", flush=True)
    resultado_novo_onboarding = await processar_resposta_onboarding_dono(
        user_id=user_id,
        tenant_id=dono_id,        # ❌ Passa dono_id errado (5511991382080)
        texto_usuario=texto_usuario,
        ctx=ctx,
        context=context,
    )
```

**Status:** ❌ **ONBOARDING PROCESSADO COM TENANT_ID ERRADO, ANTES DE IDENTIDADE**

---

## 2. PONTO EXATO ONDE TENANT_ID É PERDIDO

**Local 1 (Perda):** `main.py:237-242`

```python
# ✅ tenant_id resolvido corretamente
tenant_id = resolver_tenant_por_endpoint(phone_number_id)  # 7394370553

# ❌ Mas não é passado para o roteador
future = asyncio.run_coroutine_threadsafe(
    roteador_principal(
        user_id=from_number,  # Só passa wa_id, não tenant_id
        mensagem=text_body,
        update=None,
        context=None
    ),
    bot_loop
)
```

**Consequência:** Roteador não tem informação do tenant_id resolvido, tenta resolver novamente (e falha).

---

## 3. PONTO EXATO ONDE ACTOR_ID É CRIADO INCORRETAMENTE

**Actor ID não é criado incorretamente per se, mas o TENANT é errado.**

No contexto atual:
- `user_id` (wa_id) = 5511991382080
- `actor_id` (normalizado) = "whatsapp:5511991382080"
- `tenant_id` (falso) = "5511991382080"

**Fluxo de normalização (correto em si, mas contexto errado):**

**arquivo:** `services/identidade_service.py:17-47`  
**função:** `normalizar_actor_id(canal, identificador)`

```python
# Linha 46
actor_id = f"{canal}:{identificador}"
return actor_id  # "whatsapp:5511991382080"
```

Isso está correto. O problema é que:
- ✅ actor_id está correto: `whatsapp:5511991382080`
- ❌ tenant_id está errado: `5511991382080` (deveria ser `7394370553`)

**Resultado:** Tentativa de carregar ator de:
```
Clientes/5511991382080/Atores/whatsapp:5511991382080  ❌ (tenant errado)
```

Em vez de:
```
Clientes/7394370553/Atores/whatsapp:5511991382080  ✅ (tenant correto)
```

---

## 4. ORIGEM DO TENANT_FALLBACK

**arquivo:** `router/principal_router.py:3376-3379`

```python
# Linha 3376
dono_id = await obter_id_dono(user_id)

# Linha 3377-3379
if not dono_id:
    dono_id = str(user_id)
    print(f"[TENANT_FALLBACK] obter_id_dono retornou None, usando user_id como fallback")
```

**Por que retorna None:**

**arquivo:** `services/firebase_service_async.py:419-433`  
**função:** `obter_id_dono(user_id)`

```python
# Linha 430-433
cliente = await buscar_cliente(user_id)  # Busca por user_id = "5511991382080"
if cliente:
    return cliente.get("id_negocio")  # Retorna tenant_id
return None  # ❌ Não encontra cliente com esse ID
```

**Problema:**
- `obter_id_dono` assume que `user_id` é um cliente ou ator existente em Firestore
- Quando recebe wa_id (número de telefone puro) que não está registrado, retorna None
- Fallback então usa wa_id como tenant_id, o que é semanticamente incorreto

**Contexto:** O fallback é legítimo para **Telegram** (onde user_id é numérico e pode ser tenant), mas **inválido para WhatsApp** (onde user_id é wa_id).

---

## 5. ORIGEM DO LOAD SESSAO V2

**arquivo:** `router/principal_router.py:3390`

```python
ctx = await carregar_contexto_temporario_v2(dono_id, user_id) or {}
```

**Alias:**

**arquivo:** `utils/contexto_temporario.py:131-133`

```python
async def carregar_contexto_temporario_v2(dono_id: str, cliente_id: str):
    """ALIAS: Use carregar_sessao_temporaria() em novo código."""
    return await carregar_sessao_temporaria(cliente_id, dono_id)
```

**Função real:**

**arquivo:** `utils/contexto_temporario.py:65-89`

```python
async def carregar_sessao_temporaria(actor_id: str, tenant_id: str):
    path_novo = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    data_novo = await buscar_dado_em_path(path_novo)
    if data_novo:
        print(f"[DIAG] [LOAD SESSAO v2] path={path_novo} | source=novo | tenant={tenant_id} | actor={actor_id}")
        return data_novo
    # Fallback legado...
```

**Problema:** O `tenant_id` passado é **incorreto desde o início** (é 5511991382080 em vez de 7394370553).

---

## 6. ORDEM ATUAL DO ROUTER

```
1. Detectar onboarding_dono (linha 3421)
   └─ SE SIM: processar resposta de onboarding ANTES de tudo
   └─ usa dono_id (que é 5511991382080 ❌)

2. Processar fluxo de identidade (linha 3446)
   └─ resolver ator e validar guard
   └─ tenta resolver canonicamente DEPOIS

3. P0 Normal
   └─ agendamento, confirmação, etc
```

---

## 7. ORDEM ARQUITETURAL ESPERADA

```
1. Webhook resolve tenant_id via phone_number_id
   └─ Path: WhatsAppEndpoints/{phone_number_id}
   └─ Retorna: tenant_id ✅

2. Webhook passa tenant_id para roteador
   └─ roteador_principal(user_id, mensagem, tenant_id=...)
   └─ FALTA NESTE MOMENTO ❌

3. Roteador resolve actor_id canonicamente
   └─ usar tenant_id + canal + wa_id
   └─ Procurar em Clientes/{tenant_id}/Atores/{actor_id}
   └─ VERIFICAR SE EXISTE E QUAL TIPO

4. Carregar sessão isolada
   └─ Path: Clientes/{tenant_id}/Sessoes/{actor_id}
   └─ Com tenant_id correto

5. Determinar estado e processar
   └─ onboarding_dono?
   └─ identidade?
   └─ P0 normal?

6. Processar mensagem
```

---

## 8. RESULTADO DA RESOLVER_ATOR_POR_CANAL_CANONICO

**arquivo:** `services/identidade_service.py:55-75`  
**função:** `resolver_ator_por_canal_canonico(tenant_id, canal, identificador)`

```python
async def resolver_ator_por_canal_canonico(tenant_id: str, canal: str, identificador: str) -> dict | None:
    # Procura em Clientes/{tenant_id}/Atores
    # Procura por ator com canais[] que contenha:
    # - canal == "whatsapp"
    # - identificador == "5511991382080"
    # - ativo == True
    
    return ator_encontrado ou None
```

**Não foi testado nesta auditoria** (seria necessário verificar Firestore), mas a estrutura está pronta.

**Presumido:**
- Se `tenant_id = 7394370553` (correto)
- E `canal = "whatsapp"`, `identificador = "5511991382080"`
- A função retornaria o ator correto (se existir e estiver ativo)

---

## 9. TESTES EXISTENTES

**Teste que valida resolver_tenant_por_endpoint:**
- Não encontrado em busca rápida

**Teste que valida WhatsApp E2E (C3.15.2-D):**
- `tests/test_gate_c3152d_whatsapp_e2e.py`
- Testa isolamento Actor A vs Actor B
- **MAS:** Testa em Firebase com tenant_id passado explicitamente ao teste
- **NÃO testa:** O fluxo real desde webhook até roteador

**Por que C3.15.2-D não detectou:**
- Teste cria cenário com tenant_id + actor_id conhecidos
- Mock ou passa tenant_id diretamente
- **Não testa:** webhook → resolver_tenant_por_endpoint → roteador

**Teste faltante:** E2E completo desde webhook WhatsApp (com phone_number_id) até resposta final.

---

## 10. CLASSIFICAÇÃO DO PROBLEMA

Causas (ordem de impacto):

**A) ❌ tenant_id resolvido não é passado para o roteador** (MAIOR IMPACTO)
   - Resolução correta do endpoint é descartada
   - Roteador tenta resolver novamente (e falha)

**B) ❌ TENANT_FALLBACK aplica wa_id como tenant_id quando resolve falha** (IMPACTO MÉDIO)
   - Legítimo para Telegram/legado
   - Inválido para WhatsApp moderno
   - Sem guard de canal

**C) ❌ Orden incorreta: onboarding processado ANTES de identidade canônica** (IMPACTO MÉDIO)
   - Viola arquitetura P1 (identidade deve vir primeiro)
   - Usa tenant errado para onboarding

**D) ❌ obter_id_dono(wa_id) assume wa_id é cliente registrado** (IMPACTO BAIXO)
   - Função funciona corretamente para seu propósito
   - Problema é o contexto de uso (wa_id não é cliente_id)

**E) ⚠️ Fallback legacy em carregar_sessao_temporaria** (IMPACTO BAIXO)
   - Tem guard_tenant validation
   - Funciona se contexto anterior existir
   - Problema é carregar contexto errado ANTES disso

---

## 11. ARQUIVOS QUE PROVAVELMENTE PRECISARÃO SER ALTERADOS

**CRÍTICO (bloqueador de fix):**
1. `main.py:237-242` — Passar `tenant_id` para `roteador_principal()`
2. `router/principal_router.py:3364` — Assinatura de `roteador_principal()` para aceitar `tenant_id`
3. `router/principal_router.py:3376-3379` — Usar `tenant_id` passado, não tentar resolver se já temos

**IMPORTANTE (arquitetura):**
4. `router/principal_router.py:3421-3436` — Mover onboarding para DEPOIS de identidade
5. `router/integracao_identidade_onboarding.py` — Validar que usar `tenant_id` canônico

**NICE-TO-HAVE (testes):**
6. `tests/` — Criar E2E desde webhook WhatsApp

---

## 12. MENOR CORREÇÃO ARQUITETURAL POSSÍVEL

**Opção A (Recomendada — 3 pontos críticos):**

1. **main.py:225** — Passar `tenant_id` resolvido
   ```python
   tenant_id = resolver_tenant_por_endpoint(phone_number_id)
   future = asyncio.run_coroutine_threadsafe(
       roteador_principal(
           user_id=from_number,
           mensagem=text_body,
           tenant_id=tenant_id,  # ← ADICIONAR
           update=None,
           context=None
       ),
       bot_loop
   )
   ```

2. **router/principal_router.py:3364** — Aceitar `tenant_id` como parâmetro
   ```python
   async def roteador_principal(user_id: str, mensagem: str, tenant_id: str = None, update=None, context=None):
   ```

3. **router/principal_router.py:3376-3379** — Usar `tenant_id` passado se disponível
   ```python
   if tenant_id:
       dono_id = tenant_id  # Usar tenant resolvido do webhook
   else:
       dono_id = await obter_id_dono(user_id)  # Fallback antigo
       if not dono_id:
           dono_id = str(user_id)  # Último recurso (apenas Telegram/legado)
   ```

**Impacto:** 
- ✅ Preserva fluxo legado (Telegram)
- ✅ Fixa fluxo WhatsApp moderno
- ✅ Mínimo de alterações

---

## CONCLUSÃO

✅ **AUDITORIA CONCLUÍDA**

O bug foi mapeado completamente:
1. Webhook resolve corretamente (7394370553)
2. Roteador não recebe esse valor
3. Tenta resolver novamente, falha
4. Cai em fallback que usa wa_id como tenant_id
5. Carrega contexto, onboarding do tenant errado

**Bloqueador:** main.py não passa `tenant_id` para roteador

**Solução:** 3 pontos críticos conforme descrito acima.

