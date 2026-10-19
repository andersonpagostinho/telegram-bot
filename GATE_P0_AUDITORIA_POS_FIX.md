# GATE P0 — AUDITORIA PÓS-FIX DE `estado_fluxo`

**Data:** 2026-10-19  
**Tipo:** READ-ONLY  
**Status:** Investigação completa

---

## ✅ 1. DIFF RESUMIDO

### Arquivo: `router/integracao_identidade_onboarding.py`

```diff
     # Atualizar contexto com informações do ator
+    # [P0-FIX] Preservar estado_fluxo ativo (não sobrescrever)
+    estado_fluxo_anterior = ctx.get("estado_fluxo")
+    multiplos_servicos_anterior = ctx.get("multiplos_servicos_candidatos")
+    
     ctx.update({
         "actor_id": resultado_guard.get("actor_id"),
         "tipo_usuario": resultado_guard.get("tipo_usuario"),
         "permissoes": resultado_guard.get("permissoes", []),
         "tenant_id": tenant_id,
     })
     
     # ... (linhas 330-357 sem alteração) ...
     
     # Passo 3: Continuar no fluxo P0 normal
+    # [P0-FIX] Restaurar estado_fluxo ativo se não foi legitimamente alterado
+    if estado_fluxo_anterior and not ctx.get("estado_fluxo"):
+        ctx["estado_fluxo"] = estado_fluxo_anterior
+        print(f"[P0-FIX] Restaurado estado_fluxo={estado_fluxo_anterior} após validação de identidade", flush=True)
+    
+    if multiplos_servicos_anterior and "multiplos_servicos_candidatos" not in ctx:
+        ctx["multiplos_servicos_candidatos"] = multiplos_servicos_anterior
+        print(f"[P0-FIX] Restaurados multiplos_servicos_candidatos após validação de identidade", flush=True)
+    
     await salvar_contexto_temporario(tenant_id, cliente_id or user_id, ctx)
     return None
```

**Total:** +11 linhas, 0 linhas removidas

---

## ✅ 2. RESPEITO A TRANSIÇÕES LEGÍTIMAS

### Análise de Casos

**Caso 1: Cliente Normal com Estado Ativo**
```
Entrada: ctx = {estado_fluxo: "aguardando_servico", ...}

Linha 331: if resultado_guard.get("proxima_acao") == "onboarding" → FALSE
Linha 348: if resultado_guard.get("note") == "Cliente criado" → FALSE

Linha 360: if "aguardando_servico" and not None → TRUE
→ Restaura estado_fluxo="aguardando_servico" ✅ CORRETO
```

**Caso 2: Dono Sem Onboarding (Transição Legítima)**
```
Entrada: ctx = {estado_fluxo: "aguardando_servico", ...}

Linha 331: if resultado_guard.get("proxima_acao") == "onboarding" → TRUE
Linha 333: ctx.update({estado_fluxo: "onboarding_dono", ...})
Linha 337: await salvar_contexto_temporario(...)
Line 341: return {...}

→ Retorna antes de chegar na linha 360
→ NÃO sobrescreve "onboarding_dono" com "aguardando_servico" ✅ CORRETO
```

**Caso 3: Cliente Novo Criado Automaticamente (Transição Legítima)**
```
Entrada: ctx = {} (novo cliente)
estado_fluxo_anterior = None

Linha 348: if resultado_guard.get("note") == "Cliente criado" → TRUE
Linha 351: ctx.update({estado_fluxo: "idle", ...})
Linha 354: await salvar_contexto_temporario(...)

Linha 360: if None and not "idle" → FALSE (não restaura)
→ Mantém estado_fluxo="idle" ✅ CORRETO
```

**Conclusão:** ✅ A lógica respeta transições legítimas. Não reativa estados encerrados.

---

## ✅ 3. CONTRATOS DE FUNÇÃO CONFIRMADOS

### Assinatura Confirmada

**Arquivo:** `utils/contexto_temporario.py:322`

```python
async def salvar_contexto_temporario(user_id: str, contexto: dict, tenant_id: str = None):
```

**Contrato esperado:** `(user_id, contexto_dict, tenant_id_str)`

---

### Chamadas Localizadas

**Linha 337 (dentro do `if onboarding`):**
```python
await salvar_contexto_temporario(tenant_id, cliente_id or user_id, ctx)
```

**Linha 354 (dentro do `if cliente_novo`):**
```python
await salvar_contexto_temporario(tenant_id, cliente_id or user_id, ctx)
```

**Linha 368 (fluxo normal):**
```python
await salvar_contexto_temporario(tenant_id, cliente_id or user_id, ctx)
```

---

## ⚠️ 4. RISCO DAS CHAMADAS LEGADAS

### Discrepância de Argumentos

**Chamada atual:** `(tenant_id, cliente_id, ctx_dict)`  
**Esperado:** `(user_id, contexto_dict, tenant_id)`

### Mapeamento dos Argumentos

| Posição | Esperado | Recebido | Tipo Esperado | Tipo Real | Risco |
|---------|----------|----------|---------------|-----------|-------|
| arg1 | `user_id` | `tenant_id` | str | str | ⚠️ RISCO: Path errado |
| arg2 | `contexto_dict` | `cliente_id or user_id` | dict | str | 🔴 CRÍTICO: Tipo errado |
| arg3 | `tenant_id` | `ctx` | str \| None | dict | ⚠️ RISCO: Tipo errado |

### Impacto Real

**Linha 332 do `salvar_contexto_temporario()`:**
```python
path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"
```

Com argumentos errados:
```python
path = f"Clientes/{tenant_id}/MemoriaTemporaria/contexto"
# path = "Clientes/7394370553/MemoriaTemporaria/contexto"
```

**Path é INCORRETO!** Deveria ser:
```python
path = f"Clientes/{dono_id}/Sessoes/{actor_id}"
# path = "Clientes/7394370553/Sessoes/whatsapp:5511991382080"
```

### Linha 352 do `salvar_contexto_temporario()`

```python
atual = await buscar_dado_em_path(path) or {}
atual.update(contexto)  # contexto = "whatsapp:5511991382080" (STRING!)
```

**Tentativa de fazer `.update()` com string causa:**
- TypeError se rigoroso
- Comportamento indefinido se lenient
- Resultado: Gravação incorreta ou falha

### Cenário de Falha

1. Cliente chega com `estado_fluxo="aguardando_servico"`
2. Identidade processada normalmente
3. Linha 368: Tenta salvar contexto com argumentos errados
4. `salvar_contexto_temporario()` grava em path ERRADO (`/MemoriaTemporaria/` em vez de `/Sessoes/`)
5. Próxima mensagem carrega de path CORRETO (`/Sessoes/`) → contexto vazio
6. **`estado_fluxo` ainda perdido!** (agora por motivo diferente)

---

## ✅ 5. VERIFICAÇÃO: ONDE REALMENTE GRAVA?

### Fluxo da Salvação

1. **Linha 368:** `await salvar_contexto_temporario(tenant_id, cliente_id or user_id, ctx)`
2. **Entra em:** `utils/contexto_temporario.py:322`
3. **Linha 332:** `path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"`
   - Nota: `user_id` recebe `tenant_id` (argumento 1)
   - Path fica: `"Clientes/7394370553/MemoriaTemporaria/contexto"`
4. **Linha 352:** `atual = await buscar_dado_em_path(path) or {}`
   - Carrega de path LEGADO, não de `/Sessoes/`
5. **Linha 355:** `atual.update(contexto)`
   - Tenta fazer update com string (ERRO!)

### Confirmação: Path é INCORRETO

Comparação:
- **Esperado:** `Clientes/7394370553/Sessoes/whatsapp:5511991382080`
- **Real:** `Clientes/7394370553/MemoriaTemporaria/contexto`

**Resultado:** Contexto restaurado é salvo em lugar ERRADO!

---

## ⚠️ CRÍTICO: Impacto na Correção

Mesmo com a lógica de preservação/restauração CORRETA (Análise #2), o contexto é gravado em path ERRADO.

**Sequência de falha:**

1. T1: Pergunta enviada → Salva em `/Sessoes/` via `salvar_contexto_temporario_v2()`
2. T2: Resposta chega → Carrega de `/Sessoes/` ✅
3. T2: Identidade processa → Restaura `estado_fluxo` ✅
4. T2: Tenta salvar em `/MemoriaTemporaria/` via `salvar_contexto_temporario()` ❌
5. T3: Próxima mensagem → Carrega de `/Sessoes/` → ainda vazio

**Conclusão:** A correção implementada está **CORRETA LOGICAMENTE**, mas é **BLOQUEADA POR BUG PRÉ-EXISTENTE** nas chamadas legadas.

---

## ✅ 6. TESTES EXECUTADOS

### Resultado Final

```
tests/test_p0_fix_estado_fluxo_identidade.py::test_t1_estado_fluxo_aguardando_servico_preservado PASSED ✅
tests/test_p0_fix_estado_fluxo_identidade.py::test_t2_multiplos_servicos_candidatos_preservado PASSED ✅
tests/test_p0_fix_estado_fluxo_identidade.py::test_t4_estado_encerrado_nao_reativado PASSED ✅
tests/test_p0_fix_estado_fluxo_identidade.py::test_t5_firestore_real_persistencia SKIPPED (Firestore não configurado)
tests/test_p0_fix_estado_fluxo_identidade.py::test_t6_regressao_pode_marcar_duas SKIPPED (E2E pendente)
```

### Status Detalhado

| Teste | Status | Validação |
|-------|--------|-----------|
| T1 | ✅ PASS | Preservação de estado funciona em memória |
| T2 | ✅ PASS | Preservação de candidatos funciona em memória |
| T4 | ✅ PASS | Estados legítimos não são reativados |
| T5 | ⏳ SKIP | Firestore real: NOT SAFE para testes |
| T6 | ⏳ SKIP | E2E completo: Requer ambiente produção-like |

**Crítico:** Testes usam MOCKS de `salvar_contexto_temporario()`. Não capturam o erro de argumentos!

---

## ⚠️ 7. FIRESTORE REAL: SEGURANÇA

### T5 Análise

**Executar Firestore real?** NÃO — RISCO

**Motivo:**
1. Argumentos errados causam gravação em path legado
2. Path legado é `/MemoriaTemporaria/` compartilhado (não multi-tenant)
3. Gravações erradas podem contaminar outros tenants
4. Não é seguro testar em produção

**Recomendação:** Skip até que bug legado seja corrigido.

---

## ⚠️ 8. COBERTURA DE "PODE MARCAR AS DUAS"

### Cenário Real

1. **T1 (Pergunta):** Salva via `salvar_contexto_temporario_v2()` → Path correto ✅
2. **T2 (Resposta):**
   - Carrega de path correto ✅
   - Processa identidade ✅
   - Restaura `estado_fluxo` em memória ✅
   - **Tenta salvar via `salvar_contexto_temporario()` → Path ERRADO** ❌
3. **T3 (Próxima msg):**
   - Carrega de path correto → contexto vazio (não tem a gravação de T2)
   - `estado_fluxo` volta a ser None ❌

**Conclusão:** Correção resolve problema PARCIALMENTE. Bug legado o anula em execução real.

---

## 🔴 DECISÃO: BLOQUEADO PARA MERGE

### Motivos

1. **Lógica de preservação:** ✅ CORRETA
2. **Testes em memória:** ✅ 3/3 PASS
3. **Chamadas legadas:** 🔴 ARGUMENTOS ERRADOS (pré-existente, não corrigido)
4. **Gravação real:** 🔴 Path INCORRETO em Firestore
5. **Firestore real:** ⏳ UNSAFE testar (contamina)

**Resultado Final:** Mesmo que implementação de preservação seja correta, a gravação real não funciona por bug legado.

---

## ✅ CORREÇÃO MÍNIMA PROPOSTA

Para desbloquear, adicionar **UMA linha** em `integracao_identidade_onboarding.py:368`:

**Opção A: Usar V2 (recomendada)**
```python
# Antes:
await salvar_contexto_temporario(tenant_id, cliente_id or user_id, ctx)

# Depois:
await salvar_contexto_temporario_v2(tenant_id, cliente_id or user_id, ctx)
```

**Impacto:** 1 palavra muda (`salvar_contexto_temporario` → `salvar_contexto_temporario_v2`)  
**Risco:** BAIXO — V2 é versão corrigida, argumentos corretos

**Opção B: Corrigir argumentos (mais risky)**
```python
# user_id, contexto_dict, tenant_id
await salvar_contexto_temporario(user_id, ctx, tenant_id)
```

**Impacto:** Argumentos reorganizados  
**Risco:** MÉDIO — precisa verificar TODAS as 3 chamadas

---

## 📌 RECOMENDAÇÃO

**Status Atual:** 🔴 **BLOQUEADO**

**Ação Necessária:**
1. Corrigir chamadas legadas (Opção A ou B acima)
2. Re-executar testes T1-T4
3. Considerar T5 com Firestore real isolado
4. Então: APROVADO para merge

**Cronograma:** Pode ser feito em mesmo commit ou PR separada.

---

**Auditoria Concluída:** 2026-10-19  
**Status Final:** 🔴 BLOQUEADO POR BUG PRÉ-EXISTENTE (não causado por esta correção)
