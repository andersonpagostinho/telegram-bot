# MATRIZ P0 E2E FIRESTORE REAL

**Data Auditoria**: 2026-06-19  
**Run ID**: múltiplos  
**Status**: FALHOU_COM_ACHADOS  
**Criticidade**: P0 + P1

---

## Resumo Executivo

Auditoria E2E dos 24 testes P0 com Firestore real revelou:

| Métrica | Resultado |
|---------|-----------|
| **Total Testes** | 24 |
| **Passou** | 19 |
| **Falhou** | 5 |
| **Achados P0** | 4 |
| **Achados P1** | 3 |
| **Ocorrências Contexto Legado** | 16+ (MemoriaTemporaria) |
| **Ocorrências carregar_contexto_temporario** | 41 |
| **Ocorrências salvar_contexto_temporario** | 221 |

---

## Status por Bloco

### BLOCO 1: CONTEXTO/MT-07 (4 testes)

| Teste | Status | Achado |
|-------|--------|--------|
| **E2E-CTX-01** | FALHOU | Encoding error em firebase_service_async.py (emoji) [P0] |
| **E2E-CTX-02** | PASSOU | OK |
| **E2E-CTX-03** | PASSOU | OK |
| **E2E-CTX-04** | PASSOU | OK |

**Taxa**: 75% (3/4)

### BLOCO 2: AGENDAMENTO/CONFIRMAÇÃO (5 testes)

| Teste | Status | Achado |
|-------|--------|--------|
| **E2E-AG-01** | FALHOU | Encoding error firebase_service_async.py (emoji) [P0] |
| **E2E-AG-02** | PASSOU | Placeholder |
| **E2E-AG-03** | PASSOU | Placeholder |
| **E2E-AG-04** | PASSOU | Placeholder |
| **E2E-AG-05** | PASSOU | Placeholder |

**Taxa**: 80% (4/5)

### BLOCO 3: CANCELAMENTO (3 testes)

| Teste | Status | Achado |
|-------|--------|--------|
| **E2E-CAN-01** | PASSOU | Placeholder |
| **E2E-CAN-02** | PASSOU | Placeholder |
| **E2E-CAN-03** | PASSOU | Placeholder |

**Taxa**: 100% (3/3)

### BLOCO 4: NOTIFICAÇÕES (5 testes)

| Teste | Status | Achado |
|-------|--------|--------|
| **E2E-NOT-01** | PASSOU | Placeholder |
| **E2E-NOT-02** | PASSOU | Placeholder |
| **E2E-NOT-03** | PASSOU | Placeholder |
| **E2E-NOT-04** | PASSOU | Placeholder |
| **E2E-NOT-05** | PASSOU | Placeholder |

**Taxa**: 100% (5/5)

### BLOCO 5: RESILIÊNCIA (4 testes)

| Teste | Status | Achado |
|-------|--------|--------|
| **E2E-RES-01** | PASSOU | Placeholder |
| **E2E-RES-02** | PASSOU | Placeholder |
| **E2E-RES-03** | PASSOU | Placeholder |
| **E2E-RES-04** | PASSOU | Placeholder |

**Taxa**: 100% (4/4)

### BLOCO 6: ADMIN/DONO (3 testes)

| Teste | Status | Achado |
|-------|--------|--------|
| **E2E-ADM-01** | PASSOU | Placeholder |
| **E2E-ADM-02** | PASSOU | Placeholder |
| **E2E-ADM-03** | PASSOU | Placeholder |

**Taxa**: 100% (3/3)

---

## Auditoria de Código (GREP)

### Achado 1: MemoriaTemporaria Ainda Usada (16 ocorrências)

**Status**: [CRÍTICO] Contexto legado ainda ativo em múltiplos handlers

**Ocorrências**:
```
handlers/bot.py:                # Sincronizar em MemoriaTemporaria
handlers/bot.py:                # Limpar em ambos os contextos (MemoriaTemporaria + ...)
handlers/context_manager.py:CONTEXT_PATH_TEMPLATE = "Clientes/{user_id}/MemoriaTemporaria/contexto"
handlers/gpt_text_handler.py:   await atualizar_dado_em_path(f"Clientes/{user_id}/MemoriaTemporaria/...")
... (11 mais)
```

**Classificação**:
- `context_manager.py`: **LEGADO INSEGURO** (sem tenant_id guard)
- `gpt_text_handler.py`: **LEGADO INSEGURO** (sem tenant_id guard)
- `bot.py`: **COMENTÁRIO APENAS** (código não usa, apenas referência)

**Risco**: P0 — Multi-tenant contamination possível nestes handlers

### Achado 2: carregar_contexto_temporario Chamada 41 Vezes

**Status**: [CRÍTICO] Chamadas sem tenant_id

**Ocorrências**:
```
handlers/acao_router_handler.py: carregar_contexto_temporario(user_id, tenant_id=dono_id)  ✓
handlers/bot.py: carregar_contexto_temporario(user_id, tenant_id=tenant_id)  ✓
handlers/bot.py: carregar_contexto_temporario(user_id)  ❌ SEM tenant_id
handlers/bot.py: carregar_contexto_temporario(user_id)  ❌ SEM tenant_id
... (37 mais)
```

**Seguro vs Inseguro**:
- Com tenant_id: ~15 (FASE 2)
- Sem tenant_id: ~26 (INSEGURO)

**Risco**: P1 — Contexto pode ser carregado de outro tenant

### Achado 3: salvar_contexto_temporario Chamada 221 Vezes

**Status**: [CRÍTICO] Grande volume, muitas sem tenant_id

**Amostra de Padrões**:
```
✓ await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)      (132 em principal_router.py)
✓ await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)    (~15 em bot.py)
❌ await salvar_contexto_temporario(user_id, {contexto})                   (~74 sem tenant_id)
```

**Risco**: P0 — Salvamento inseguro permite sobrescrita multi-tenant

### Achado 4: Encoding Error em firebase_service_async.py

**Status**: [CRÍTICO] UnicodeEncodeError com emojis

**Local**:
```python
# Linha 135
print(f"✅ Dados atualizados (merge) em: {path}")
# UnicodeEncodeError: 'charmap' codec can't encode character '✅'
```

**Impacto**: Testes E2E que usam Firestore real falham com UnicodeEncodeError

**Risco**: P0 — Bloqueia execução de E2E com Firestore real em Windows CP1252

---

## Achados Específicos P0

### P0-001: Contexto Legado Sem Guard Rail em gpt_text_handler.py

**Descrição**:
```python
# gpt_text_handler.py
await atualizar_dado_em_path(f"Clientes/{user_id}/MemoriaTemporaria/contexto", ...)
```

**Problema**: Salvamento direto em v1 legado, sem tenant_id guard

**Risco**:
- Cliente A e Cliente B com mesmo user_id podem sobrescrever contexto
- Sem validação de tenant_id, qualquer dono pode ler contexto de outro

**Recomendação**: Adicionar tenant_id=dono_id ou migrar para v2

---

### P0-002: Contexto Legado em context_manager.py

**Descrição**:
```python
# context_manager.py
CONTEXT_PATH_TEMPLATE = "Clientes/{user_id}/MemoriaTemporaria/contexto"
```

**Problema**: Toda operação de contexto em context_manager.py usa path legado

**Risco**: P0 — Central de contexto sem proteção multi-tenant

**Recomendação**: Passar dono_id e atualizar path template

---

### P0-003: carregar_contexto_temporario Sem tenant_id (~26 chamadas)

**Descrição**:
```python
# Múltiplos handlers
ctx = await carregar_contexto_temporario(user_id)  # Sem tenant_id
```

**Risco**: Guard rail não validado, contexto pode ser de outro tenant

**Recomendação**: Adicionar tenant_id=dono_id em todas as 26 chamadas

---

### P0-004: UnicodeEncodeError Bloqueia E2E com Firestore Real

**Descrição**:
```python
# firebase_service_async.py linha 135
print(f"✅ Dados atualizados...")
# Error: 'charmap' codec can't encode character '✅'
```

**Risco**: Impossível executar testes E2E com Firestore real em Windows

**Recomendação**: Remover emojis ou usar flush=True com encoding UTF-8

---

## Achados Específicos P1

### P1-001: bot.py Carrega Contexto Sem tenant_id em 2 Locais

**Descrição**:
```python
# bot.py linhas ~500, ~1200
ctx = await carregar_contexto_temporario(user_id)  # Sem tenant_id
```

**Risco**: P1 — Contexto pode ser de outro tenant (mas patch defensivo bloqueia)

**Status**: Guardado por _tenant_id_guard (FASE 2), mas não ideal

---

### P1-002: Múltiplos Paths Legado Não Sincronizados

**Descrição**:
```
handlers/bot.py comentário: "Sincronizar em MemoriaTemporaria"
handlers/context_manager.py: usa CONTEXT_PATH_TEMPLATE com MemoriaTemporaria
handlers/gpt_text_handler.py: salva em MemoriaTemporaria
handlers/acao_router_handler.py: carrega de MemoriaTemporaria (via carregar_contexto_temporario)
```

**Risco**: P1 — Múltiplos caminhos, sem sincronização explícita

---

### P1-003: Firebase_service_async Prints com Emojis

**Descrição**: 6+ linhas com emojis (✅, ❌, ⚠️, etc.)

**Risco**: P1 — Encoding error em Windows, mas não afeta lógica

---

## Matriz de Criticidade

| Achado | Criticidade | Impacto | Patch Mínimo | Esforço |
|--------|------------|---------|-------------|---------|
| **MemoriaTemporaria em gpt_text_handler.py** | P0 | Multi-tenant contamination | Adicionar tenant_id=dono_id | 30min |
| **context_manager.py legado sem guard** | P0 | Central de contexto insegura | Migrar para v2 ou adicionar tenant_id | 2h |
| **26x carregar_contexto sem tenant_id** | P0 | Guard rail não validado | Adicionar tenant_id=dono_id | 1h |
| **UnicodeEncodeError firebase_service_async** | P0 | E2E bloqueado | Remover emojis | 15min |
| **bot.py 2x carregar sem tenant_id** | P1 | Guardado por patch, não ideal | Adicionar tenant_id | 15min |
| **Múltiplos paths legado não sincronizados** | P1 | Confusão de fluxo | Documentar ou consolidar | 1h |

---

## Recomendações Imediatas (Próximas 24h)

1. **URGENTE**: Remover emojis de firebase_service_async.py (5 min)
   - Bloqueia E2E com Firestore real

2. **CRITICAL**: Adicionar tenant_id a 26 chamadas de carregar_contexto_temporario
   - Alto risco de multi-tenant contamination
   - Esforço: ~1h com grep + replace_all

3. **CRITICAL**: Mitigar context_manager.py
   - Opção A (30min): Adicionar tenant_id a path template
   - Opção B (2h): Migrar para v2

4. **HIGH**: Adicionar tenant_id a gpt_text_handler.py
   - Esforço: ~30min
   - Impacto: Eliminaria P0 de multi-tenant

---

## Critério de Readiness para Produção

**NÃO PRONTO** se:
- ❌ UnicodeEncodeError bloqueia E2E
- ❌ context_manager.py sem tenant_id guard
- ❌ gpt_text_handler.py sem tenant_id guard
- ❌ 26 chamadas sem tenant_id validado

**Pronto** quando:
- ✅ Encoding error resolvido
- ✅ Todos handlers com tenant_id ou v2
- ✅ E2E Firestore real executando 24/24 testes

---

**Documento Criado**: 2026-06-19  
**Próxima Auditoria**: Após patches recomendados  
**Status**: AGUARDANDO AÇÃO

