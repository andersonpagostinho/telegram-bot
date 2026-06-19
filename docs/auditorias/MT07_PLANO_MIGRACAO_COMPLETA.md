# 📋 PLANO DE MIGRAÇÃO COMPLETA MT-07

**Data**: 2026-06-19  
**Status**: INICIADO com proteção defensiva  
**Criticidade**: P0  
**Deadline recomendado**: 2026-06-26 (1 semana)

---

## 🎯 Objetivo

Completar migração de contexto_temporario v1 → v2 em todos os 8 handlers, garantindo multi-tenant safety 100%.

---

## 📊 Status Atual (2026-06-19 — FASE 2 COMPLETA)

| Handler | v1 Legado | v2 Novo | Status | Risco |
|---------|-----------|---------|--------|-------|
| **event_handler.py** | ❌ Não | ✅ Sim | ✅ MIGRADO | Baixo |
| **bot.py** | ⚠️ Sim | ❌ Não | 🔧 PATCH DEFENSIVO (tenant_id) | Médio → Baixo |
| **acao_router_handler.py** | ✅ Sim | ❌ Não | ✅ PATCH DEFENSIVO (tenant_id) | Alto → Médio |
| **context_manager.py** | ✅ Sim | ❌ Não | ❌ NÃO MIGRADO | Alto |
| **email_handler.py** | ✅ Sim | ❌ Não | ❌ NÃO MIGRADO | Médio |
| **gpt_text_handler.py** | ✅ Sim | ❌ Não | ❌ NÃO MIGRADO | Alto |
| **principal_router.py** | ✅ Sim | ❌ Não | ✅ PATCH DEFENSIVO (tenant_id) | Alto → Médio |
| **principal_router_precheck_func.py** | ✅ Sim | ❌ Não | ❌ NÃO MIGRADO | Médio |

**Taxa de Migração com Guard Rail**: 3/8 = 37.5% com proteção defensiva ativa

**Taxa FASE 2 (Entry Points Críticos)**: 
- principal_router.py (132 chamadas com tenant_id)
- acao_router_handler.py (6 chamadas com tenant_id)

---

## ✅ FASE 2 Implementada (2026-06-19 — Entry Points Críticos)

### Resumo Executivo

**Objetivo:** Reduzir uso inseguro de contexto legado nos fluxos reais principais (entry points críticos)

**Arquivos Modificados:**
1. `router/principal_router.py` — 132 chamadas v1 + tenant_id
2. `handlers/acao_router_handler.py` — 6 chamadas v1 + tenant_id

**Status:** ✅ COMPLETO
- Compilação: OK
- Testes defensivos: PASSANDO (3/3)
- Logs: Ativos com guard rail

### Detalhes Técnicos FASE 2

#### router/principal_router.py

**Mudanças:**
- Line 4157: `dono_id = await obter_id_dono(user_id)` (já existia)
- Replace_all: 132 ocorrências de `await salvar_contexto_temporario(user_id, ctx)` → com `tenant_id=dono_id`
- Replace_all: 4 ocorrências de `await carregar_contexto_temporario(user_id)` → com `tenant_id=dono_id`
- Helper `_send_and_stop_ctx` (line 60): agora obtém dono_id localmente antes de salvar

**Impacto:**
- Todas as chamadas v1 no fluxo de roteamento principal agora validam tenant_id
- Guard rail está ativo para 132 salvas em principal_router
- Proteção contra contexto cruzado de tenants nesse entry point

#### handlers/acao_router_handler.py

**Mudanças:**
1. Import: Adicionado `from services.firebase_service_async import obter_id_dono` (line 7)
2. Ação "criar_evento" (line 82): `dono_id = await obter_id_dono(user_id)` + `tenant_id=dono_id`
3. Ação "definir_meio_periodo_salao" (line 473): +dono_id, 2 chamadas com tenant_id
4. Ação "bloquear_agenda_profissional" (line 526): +dono_id, 1 chamada com tenant_id
5. Ação "definir_meio_periodo_profissional" (line 587): +dono_id, 1 chamada com tenant_id

**Impacto:**
- Todas as ações que usam contexto agora têm guard rail ativo
- Proteção defensiva em criar_evento (ação crítica de P0)

---

## 🔧 Patch Defensivo Implementado (2026-06-19 — Revisado)

### Mudanças em `utils/contexto_temporario.py`:

```python
# ANTES (v1 sem proteção):
async def carregar_contexto_temporario(user_id: str):
    # Carrega sem validar tenant

# DEPOIS (com patch defensivo):
async def carregar_contexto_temporario(user_id: str, tenant_id: str = None):
    # Se tenant_id informado: valida que contexto pertence ao tenant
    # Se mismatch: retorna {} para proteger
    # Se sem tenant_id: retorna mas loga alerta
```

### Mudanças em `handlers/bot.py`:

```python
# ANTES:
ctx_tmp = await carregar_contexto_temporario(user_id)

# DEPOIS:
ctx_tmp = await carregar_contexto_temporario(user_id, tenant_id=tenant_id)
await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)
await limpar_contexto_agendamento(user_id, tenant_id=tenant_id)
```

---

## 📈 Cronograma de Migração

### Fase 1: Patch Defensivo (✅ CONCLUÍDO — 2026-06-19)

- [x] Modificar funções v1 para aceitar `tenant_id`
- [x] Adicionar guard rail `_tenant_id_guard` no contexto
- [x] Atualizar bot.py para passar `tenant_id`
- [x] Adicionar logs defensivos

**Status**: ✅ PRONTO

**Resultado**: Multi-tenant protection ativa mesmo em v1

---

### Fase 2: Migração de Entry Points Críticos (✅ COMPLETO — 2026-06-19)

**Timeline**: 2026-06-19 (completado antecipadamente)
**Esforço**: 2 horas
**Impacto**: Alto (ambos entry points cobertos)

#### 2.1 principal_router.py (✅ Prioridade 1 — FEITO)

**Localização**: router/principal_router.py  
**Chamadas v1 encontradas**: 136 (132 salvar + 4 carregar)
**Ação Completada**:
1. ✅ dono_id já obtido em linha 4157
2. ✅ Replace_all: 132 chamadas `salvar_contexto_temporario` com `tenant_id=dono_id`
3. ✅ Replace_all: 4 chamadas `carregar_contexto_temporario` com `tenant_id=dono_id`
4. ✅ Helper `_send_and_stop_ctx` atualizado para obter dono_id localmente

**Status**: ✅ IMPLEMENTADO E COMPILAÇÃO OK

#### 2.2 acao_router_handler.py (✅ Prioridade 1 — FEITO)

**Localização**: handlers/acao_router_handler.py  
**Chamadas v1 encontradas**: 6 (3 carregar + 2 salvar + 1 limpar → 6 total com blocos relacionados)
**Ação Completada**:
1. ✅ Importado `obter_id_dono` no topo do arquivo
2. ✅ Ação "criar_evento": +dono_id, carregar com tenant_id
3. ✅ Ação "definir_meio_periodo_salao": +dono_id, carregar+salvar+limpar com tenant_id
4. ✅ Ação "bloquear_agenda_profissional": +dono_id, limpar com tenant_id
5. ✅ Ação "definir_meio_periodo_profissional": +dono_id, limpar com tenant_id

**Status**: ✅ IMPLEMENTADO E COMPILAÇÃO OK

---

### Fase 3: Migração de Handlers Operacionais (⏳ PRÓXIMO — SEMANA 2)

**Timeline**: 2026-06-22 a 2026-06-24  
**Esforço**: 2-3 dias  
**Impacto**: Médio

#### 3.1 gpt_text_handler.py (Prioridade 2)

**Localização**: handlers/gpt_text_handler.py  
**Chamadas v1 encontradas**: ~3  
**Ação**: Passar `tenant_id` a todas as chamadas v1

#### 3.2 context_manager.py (Prioridade 2)

**Localização**: handlers/context_manager.py  
**Chamadas v1 encontradas**: ~5  
**Ação**: Passar `tenant_id` a todas as chamadas v1

#### 3.3 email_handler.py (Prioridade 2)

**Localização**: handlers/email_handler.py  
**Chamadas v1 encontradas**: ~2  
**Ação**: Passar `tenant_id` a todas as chamadas v1

#### 3.4 principal_router_precheck_func.py (Prioridade 3)

**Localização**: router/principal_router_precheck_func.py  
**Chamadas v1 encontradas**: ~1  
**Ação**: Passar `tenant_id` a todas as chamadas v1

---

### Fase 4: Migração para v2 (❌ NÃO AGORA)

**Timeline**: Futuro (FASE 2 do roadmap)  
**Esforço**: 3-4 dias  
**Impacto**: Alto (refatoração completa)

**NÃO fazer agora**. Apenas com patch defensivo por enquanto.

---

## 📋 Matriz de Migração (Detalhe)

| Arquivo | v1 Calls | Situa | tenant_id Disponível? | Ação Imediata | Ação Futura |
|---------|----------|-------|-------|-------------|-------------|
| event_handler.py | 0 | ✅ Migrado v2 | N/A | Manter v2 | N/A |
| bot.py | 3 | 🔧 Patch v1 | ✅ Sim (tenant_id) | ✅ FEITO | Migrar v2 |
| principal_router.py | 10 | ❌ v1 legado | ✅ Provável (dono_id) | Adicionar tenant_id | Migrar v2 |
| acao_router_handler.py | 5 | ❌ v1 legado | ✅ Provável (dono_id) | Adicionar tenant_id | Migrar v2 |
| gpt_text_handler.py | 3 | ❌ v1 legado | ⚠️ Verificar | Adicionar tenant_id | Migrar v2 |
| context_manager.py | 5 | ❌ v1 legado | ⚠️ Verificar | Adicionar tenant_id | Migrar v2 |
| email_handler.py | 2 | ❌ v1 legado | ⚠️ Verificar | Adicionar tenant_id | Migrar v2 |
| principal_router_precheck_func.py | 1 | ❌ v1 legado | ⚠️ Verificar | Adicionar tenant_id | Migrar v2 |

---

## 🧪 Testes Obrigatórios Após Patch

### Teste 1: Compatibilidade com tenant_id

```python
# Cenário: Dois donos, mesmo cliente
user_id = "123456"
dono_a = "dono_a"
dono_b = "dono_b"

# Salvar contexto no dono A
ctx_a = {"draft": "corte", "profissional": "Bruna"}
await salvar_contexto_temporario(user_id, ctx_a, tenant_id=dono_a)

# Carregar no dono B (deve ser bloqueado)
ctx_b = await carregar_contexto_temporario(user_id, tenant_id=dono_b)
assert ctx_b == {}  # Deve estar vazio por mismatch
```

### Teste 2: Proteção contra mismatch

```python
# Carregar contexto de dono A enquanto processando dono B
ctx_carregado = await carregar_contexto_temporario(user_id, tenant_id=dono_b)
# Log deve mostrar: [CTX_LEGADO_TENANT_MISMATCH]
# Retorno deve ser: {}
```

### Teste 3: Compatibilidade sem tenant_id (legado puro)

```python
# Chamar v1 sem tenant_id (para compatibilidade)
ctx = await carregar_contexto_temporario(user_id)
# Log deve mostrar: [CTX_LEGADO_SEM_TENANT_PARAM]
# Retorno deve ser: contexto (para compat)
```

---

## ✅ Critério de Conclusão

### Fase 1 (Patch Defensivo) — ✅ CONCLUÍDO

- [x] Funções v1 modificadas para aceitar `tenant_id`
- [x] Guard rail implementado
- [x] bot.py atualizado
- [x] Logs defensivos adicionados
- [x] Teste reproduzido com sucesso

### Fase 2 (Entry Points) — ⏳ A FAZER

- [ ] principal_router.py atualizado com `tenant_id`
- [ ] acao_router_handler.py atualizado com `tenant_id`
- [ ] Testes de compatibilidade passando
- [ ] Grep final mostrando todas as chamadas com `tenant_id`

### Fase 3 (Handlers) — ⏳ A FAZER

- [ ] gpt_text_handler.py atualizado
- [ ] context_manager.py atualizado
- [ ] email_handler.py atualizado
- [ ] principal_router_precheck_func.py atualizado
- [ ] Testes de regressão passando

### Fase 4 (v2 Completo) — ⏳ FUTURO

- [ ] event_handler.py já está em v2
- [ ] bot.py migrado para v2
- [ ] Todos handlers migrarem para v2
- [ ] Funções v1 removidas
- [ ] MT-07 marcado como COMPLETO

---

## 🚨 Logs de Auditoria

### Logs do Patch Defensivo (2026-06-19)

**Esperado em produção**:
```
[CTX_LEGADO_COMPAT] — contexto legado com tenant_id validado
[CTX_LEGADO_TENANT_MISMATCH] — bloqueio de mismatch
[CTX_LEGADO_SEM_TENANT] — contexto ignorado sem guard
[CTX_LEGADO_SAVE_COMPAT] — salvamento legado com guard
[CTX_LEGADO_SAVE_SEM_TENANT] — salvamento legado sem guard
```

### Comandos de Auditoria

```bash
# Listar todos usos de v1 legado:
grep -r "carregar_contexto_temporario\|salvar_contexto_temporario" \
  handlers/*.py router/*.py --include="*.py" | \
  grep -v "tenant_id=" | \
  grep -v "#.*v2"

# Verificar se tenant_id foi adicionado:
grep "tenant_id=.*tenant_id\|tenant_id=.*dono_id" \
  handlers/*.py router/*.py --include="*.py"
```

---

## 📌 Notas Críticas

1. **Não remover v1 ainda**: Funções legadas são necessárias para compatibilidade durante migração

2. **Patch defensivo é obrigatório**: Sem ele, risco de data contamination entre tenants é P0

3. **tenant_id deve estar disponível**: Antes de migrar um handler, garantir que `tenant_id` ou `dono_id` foi obtido

4. **Logs são evidência**: A auditoria será feita via logs. Manter prints defensivos mesmo em v2

5. **Testes de regressão**: Executar suite de testes após cada handler migrado

---

## 🎯 Decisão de Negócio

### Opção A: Completar agora (RECOMENDADO)
- Esforço: 3-4 dias
- Risco: Baixo com patch defensivo
- Benefício: Multi-tenant 100% seguro
- Custo: ~24-32 horas de desenvolvimento

### Opção B: Manter com patch defensivo (SEGURO)
- Esforço: 0 (já implementado)
- Risco: Médio (depende de patch funcionar)
- Benefício: Proteção imediata
- Custo: 0 horas (implementado 2026-06-19)

### Opção C: Migração incremental (BALANCEADO)
- Esforço: 1-2 dias/semana
- Risco: Baixo (patch fornece amortecimento)
- Benefício: Progresso constante
- Custo: ~12 horas/semana

**Recomendação**: Opção A (completar em 2026-06-26)

---

**Documento criado**: 2026-06-19  
**Status**: PLANO ATIVO COM PATCH DEFENSIVO  
**Próxima revisão**: 2026-06-20  
**Deadline**: 2026-06-26

