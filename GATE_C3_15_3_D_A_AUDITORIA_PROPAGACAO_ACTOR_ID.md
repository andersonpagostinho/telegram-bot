# GATE C3.15.3-D-A — AUDITORIA DE PROPAGAÇÃO actor_id → SESSÃO

**Data:** 2026-09-27  
**Status:** ✅ PASS — Causa raiz identificada com evidência  
**Objetivo:** Encontrar onde actor_id canônico é perdido no fluxo WhatsApp  

---

## 📋 DIVERGÊNCIA OBSERVADA

**Evidência de log:**
```
[TENANT_INGRESS] tenant_id explícito recebido do endpoint: 7394370553
[ACTOR_CANONICO] Resolvido para WhatsApp: actor_id=whatsapp:5511991382080

MAS depois:

[LOAD SESSAO v2]
path=Clientes/7394370553/Sessoes/5511991382080
actor=5511991382080

[SESSION_STORE]
write_path=Clientes/7394370553/Sessoes/5511991382080
read_path=Clientes/7394370553/Sessoes/5511991382080
```

**Problema:** Sessão usa `5511991382080` (sem `whatsapp:` prefix) em vez de `whatsapp:5511991382080`

---

## 🔍 RASTREAMENTO COMPLETO

### PONTO A: Entry Point — main.py:237-243

**Arquivo:** `main.py`  
**Linhas:** 237-243  
**Código:**
```python
future = asyncio.run_coroutine_threadsafe(
    roteador_principal(
        user_id=from_number,           # ← AQUI: apenas o número
        mensagem=text_body,
        tenant_id=tenant_id,
        update=None,
        context=None
    ),
    bot_loop
)
```

**Análise:**
- `from_number` vem de: `msg.get("from")` (linha 211)
- Formato: apenas número direto da WhatsApp API (ex: "5511991382080")
- ❌ NÃO está em formato canônico "whatsapp:5511991382080"

---

### PONTO B: Resolução de actor_id — router/principal_router.py:3400-3410

**Arquivo:** `router/principal_router.py`  
**Linhas:** 3400-3410  
**Código:**
```python
actor_id_whatsapp = None
if tenant_id:
    from services.identidade_service import resolver_ator_por_canal_canonico
    try:
        ator_canonico = await resolver_ator_por_canal_canonico(
            tenant_id=dono_id,
            canal="whatsapp",
            identificador=user_id              # ← Recebe "5511991382080" de main.py
        )
        if ator_canonico:
            actor_id_whatsapp = ator_canonico.get("actor_id") or ator_canonico.get("id")
            print(f"[ACTOR_CANONICO] Resolvido para WhatsApp: actor_id={actor_id_whatsapp}", flush=True)
            # ✅ AQUI: actor_id_whatsapp = "whatsapp:5511991382080"
```

**Análise:**
- ✅ Resolve corretamente para formato canônico: "whatsapp:5511991382080"
- ✅ Armazena em variável: `actor_id_whatsapp`
- ❌ MAS: nunca usa `actor_id_whatsapp` novamente
- ❌ Continua usando `user_id` (valor original) para sessão

---

### PONTO C: Carregamento de Sessão — router/principal_router.py:3425

**Arquivo:** `router/principal_router.py`  
**Linha:** 3425  
**Código:**
```python
else:
    # Carregar V2 se handler não carregou
    ctx = await carregar_contexto_temporario_v2(dono_id, user_id) or {}
                                                            ↑
                                                   ❌ USAR user_id
                                                   ✅ DEVERIA SER actor_id_whatsapp
```

**Análise:**
- ❌ Passa `user_id` ("5511991382080") em vez de `actor_id_whatsapp` ("whatsapp:5511991382080")
- ❌ Carrega path ERRADO: `Clientes/7394370553/Sessoes/5511991382080`
- ✅ DEVERIA carregar: `Clientes/7394370553/Sessoes/whatsapp:5511991382080`

---

### PONTO D: Salvamento de Sessão — router/principal_router.py (múltiplas linhas)

**Arquivo:** `router/principal_router.py`  
**Linhas:** 3443, 3511, e mais 139 ocorrências  

**Exemplos:**
```python
# Linha 3443
await salvar_contexto_temporario_v2(dono_id, user_id, ctx)
                                            ↑
                                 ❌ user_id novamente

# Linha 3511
await salvar_contexto_temporario_v2(dono_id, user_id, ctx)
                                            ↑
                                 ❌ user_id novamente

# ... (139 mais locais)
```

**Contagem:**
- **141 chamadas a `salvar_contexto_temporario_v2(dono_id, user_id, ...)`**
- Todas usando `user_id` em vez de `actor_id_whatsapp`

**Análise:**
- ❌ Salva path ERRADO: `Clientes/7394370553/Sessoes/5511991382080`
- ✅ DEVERIA salvar: `Clientes/7394370553/Sessoes/whatsapp:5511991382080`

---

## 📊 CONTRATO ESPERADO VS REAL

### Esperado (Correto)

**WhatsApp flow (tenant_id passado):**
```
main.py:238          from_number="5511991382080"
                     user_id="5511991382080"
                             ↓
router:3410          resolver_ator_por_canal_canonico()
                     actor_id_whatsapp="whatsapp:5511991382080"
                             ↓
router:3425          carregar_contexto_temporario_v2(
                        dono_id=7394370553,
                        cliente_id=whatsapp:5511991382080  ← ✅ CANÔNICO
                     )
                             ↓
utils/contexto:82    path = f"Clientes/7394370553/Sessoes/whatsapp:5511991382080"
                     [LOAD SESSAO v2] path=...Sessoes/whatsapp:5511991382080 ✅
```

### Real (Atualmente Errado)

**WhatsApp flow (tenant_id passado):**
```
main.py:238          from_number="5511991382080"
                     user_id="5511991382080"
                             ↓
router:3410          resolver_ator_por_canal_canonico()
                     actor_id_whatsapp="whatsapp:5511991382080"
                     [RESOLVIDO MAS NÃO USADO]
                             ↓
router:3425          carregar_contexto_temporario_v2(
                        dono_id=7394370553,
                        cliente_id=5511991382080  ← ❌ NÃO CANÔNICO
                     )
                             ↓
utils/contexto:82    path = f"Clientes/7394370553/Sessoes/5511991382080"
                     [LOAD SESSAO v2] path=...Sessoes/5511991382080 ❌
```

---

## 🎯 CAUSA RAIZ

**Padrão identificado:** `actor_id_whatsapp` é resolvido mas nunca propagado

```python
# Linha 3410
actor_id_whatsapp = ator_canonico.get("actor_id")  # ← Resolve "whatsapp:..."
print(f"[ACTOR_CANONICO] actor_id={actor_id_whatsapp}")  # ← Loga

# Mas depois...

# Linha 3425
ctx = await carregar_contexto_temporario_v2(dono_id, user_id)  # ← Usa user_id (nunca usa actor_id_whatsapp)

# E em todos os outros 141 locais...

await salvar_contexto_temporario_v2(dono_id, user_id, ctx)  # ← Usa user_id (nunca usa actor_id_whatsapp)
```

**Conclusão:** Variável `actor_id_whatsapp` é criada mas NÃO é utilizada para carregar/salvar sessão

---

## 🔧 CORREÇÃO MÍNIMA RECOMENDADA

### Estratégia A: Usar `actor_id_whatsapp` Quando Disponível (RECOMENDADO)

**Mudança mínima:**
1. Na linha 3425 (carregar): usar `actor_id_whatsapp` se disponível, fallback para `user_id`
2. Nas 141 linhas de save: usar `actor_id_whatsapp` se disponível, fallback para `user_id`

**Padrão:**
```python
# Linha 3425
cliente_id = actor_id_whatsapp or user_id
ctx = await carregar_contexto_temporario_v2(dono_id, cliente_id) or {}

# Linhas de save
cliente_id = actor_id_whatsapp or user_id
await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)
```

**Impacto:**
- WhatsApp: carrega/salva em path CORRETO com `whatsapp:...` prefix
- Telegram: continua usando `user_id` (como antes, se `actor_id_whatsapp` for None)
- Fallback: seguro se `actor_id_whatsapp` não for resolvido

---

### Estratégia B: Normalizar `user_id` em main.py (ALTERNATIVA)

**Mudança mínima:**
1. Em main.py:238, normalizar `from_number` para formato canônico
2. Passar `user_id="whatsapp:{from_number}"` para o roteador

**Padrão:**
```python
# main.py:238
user_id = f"whatsapp:{from_number}"  # ← Normalizar aqui
future = asyncio.run_coroutine_threadsafe(
    roteador_principal(
        user_id=user_id,  # ← Agora é "whatsapp:5511991382080"
        ...
    ),
    bot_loop
)
```

**Impacto:**
- WhatsApp: carrega/salva com prefix correto automaticamente
- Mudança simples em UMA linha
- Elimina necessidade de resolver `actor_id_whatsapp` separadamente

---

## 📊 DISTRIBUIÇÃO DE IMPACTO

| Componente | Linhas | Arquivo | Mudanças Necessárias |
|-----------|--------|---------|----------------------|
| Entry Point | 238 | main.py | 1 linha (se Estratégia B) |
| Resolução | 3410 | principal_router.py | 0 (info only) |
| Carregamento (linha específica) | 3425 | principal_router.py | 2 linhas (Estratégia A) |
| Carregamento (outras) | 3 | principal_router.py | 2 linhas × 3 (Estratégia A) |
| Salvamento (linhas-chave) | ~10-20 | principal_router.py | 2 linhas × 10-20 (Estratégia A) |
| Salvamento (outras) | ~120+ | principal_router.py | 2 linhas × 120+ (Estratégia A) |

---

## ✅ ARQUIVOS QUE SERÃO ALTERADOS (Próxima Etapa)

### Estratégia A (Recomendada):
- ✅ `router/principal_router.py` (múltiplas linhas de carregamento e salvamento)
- ❌ Nenhum outro arquivo

### Estratégia B (Alternativa):
- ✅ `main.py` (apenas linha 238)
- ❌ Nenhum outro arquivo

---

## ❌ ARQUIVOS QUE NÃO DEVEM SER ALTERADOS

- ❌ `utils/contexto_temporario.py` (funções estão corretas)
- ❌ `services/identidade_service.py` (resolução está correta)
- ❌ `handlers/bot.py` (Telegram segue padrão diferente)
- ❌ `services/whatsapp_service.py` (já funciona corretamente)
- ❌ `handlers/whatsapp_bridge_handler.py` (se existir)
- ❌ `handlers/context_manager.py` (wrapper deve permanecer)

---

## 📈 DIFF ESTIMADO (Estratégia A)

### Padrão de mudança:

```python
# Antes (linha 3425)
ctx = await carregar_contexto_temporario_v2(dono_id, user_id) or {}

# Depois
cliente_id = actor_id_whatsapp or user_id
ctx = await carregar_contexto_temporario_v2(dono_id, cliente_id) or {}

# Antes (linha 3443 e 139+ outras)
await salvar_contexto_temporario_v2(dono_id, user_id, ctx)

# Depois
cliente_id = actor_id_whatsapp or user_id
await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)
```

**Estimativa:**
- +142 linhas (1 linha de assignment × 141 callsites + 1 carregamento)
- Mudanças mecânicas (simples substituição)
- Risco muito baixo (fallback seguro)

---

## 🧪 VALIDAÇÃO APÓS CORREÇÃO

**Cenários a testar:**

1. **WhatsApp com endpoint registrado (Happy path)**
   - Input: "ola" via WhatsApp
   - Esperado: `path=Clientes/7394370553/Sessoes/whatsapp:5511991382080`
   - Log: `[LOAD SESSAO v2] path=...Sessoes/whatsapp:5511991382080` ✅

2. **Telegram (deve manter comportamento)**
   - Input: "/start" via Telegram
   - Esperado: `actor_id_whatsapp=None` (context ≠ None, não entra WhatsApp)
   - Comportamento: `user_id` é usado normalmente ✅

3. **WhatsApp sem actor resolvido (fallback)**
   - Esperado: `actor_id_whatsapp=None`
   - Comportamento: `cliente_id = None or user_id` = `user_id`
   - Resultado: fallback seguro para `user_id` ✅

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO (Próxima Etapa)

- [ ] Definir `cliente_id = actor_id_whatsapp or user_id` no início de roteador
- [ ] Ou: definir inline em cada ponto de uso
- [ ] Atualizar linha 3425 (carregamento inicial)
- [ ] Atualizar linha 3443 (primeira save)
- [ ] Atualizar todas as 139 outras saves
- [ ] Validar com teste específico
- [ ] Executar P1 E2E (42/42)
- [ ] Executar P0 Regressão (174/174)

---

## 🎯 RESUMO EXECUTIVO

| Item | Valor |
|------|-------|
| **Status Auditoria** | ✅ PASS |
| **Causa Raiz** | actor_id_whatsapp resolvido mas não propagado |
| **Localização Exata** | router/principal_router.py:3410 (resolve) vs 3425+ (não usa) |
| **Impacto** | Sessão carregada/salva em path ERRADO para WhatsApp |
| **Path Atual** | `Clientes/{tenant_id}/Sessoes/5511991382080` ❌ |
| **Path Esperado** | `Clientes/{tenant_id}/Sessoes/whatsapp:5511991382080` ✅ |
| **Mudanças Necessárias** | +2 linhas × ~141 = ~142 linhas |
| **Estratégia Recomendada** | Estratégia A (usar `actor_id_whatsapp` quando disponível) |
| **Risco** | Muito baixo (fallback seguro) |
| **Próximo Passo** | GATE C3.15.3-D-B — Implementação |

---

**Auditoria concluída: NENHUM ARQUIVO FOI ALTERADO.**  
**Pronto para fase de implementação.**
