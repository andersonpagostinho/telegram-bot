# H1-P1 — RECONCILIAÇÃO FINAL DOS CALLSITES

**Data:** 2026-09-28  
**Modo:** Auditoria apenas (nenhuma alteração)  
**Objetivo:** Resolver divergências e definir Lote 3 definitivo

---

## RESUMO EXECUTIVO

| Métrica | Resultado |
|---------|-----------|
| **Total de callsites encontrados** | 18 |
| **LOTE 1 (Leitura)** | 5 |
| **LOTE 2 (Escrita)** | 3 ✅ Implementado |
| **LOTE 3 (Validação)** | 10 (não 9) |
| **Divergência anterior** | 5+3+9=17 vs 18 encontrados |
| **Explicação** | Callsite 18 (session_service.py) já estava fora da lista anterior |

**Descobertas críticas:**
- ⚠️ 3 callsites com **fallback proibido user_id**
- ⚠️ 1 callsite (event_service_async.py:980) com **None implicit**
- ⚠️ session_service.py:50 **BLOQUEADOR** (fallback persistente, não pode alterar)

---

## TABELA DE RECONCILIAÇÃO — 18 CALLSITES

| # | Arquivo | Linha | Função | Uso | Classificação | Já Corrigido? | Status | Risco |
|----|---------|-------|--------|-----|----------------|---------------|--------|------|
| 1 | event_service.py | 7 | buscar_eventos_por_intervalo() | LEITURA (busca eventos do tenant) | LOTE 1 | ✅ Sim | ✅ Seguro | Baixo |
| 2 | firebase_service_async.py | 450 | obter_id_dono_com_fallback() | LEITURA + fallback proposital | LOTE 1 | ✅ Sim | ✅ Seguro | Nenhum |
| 3 | gpt_service.py | 135 | ??? (debug print) | LEITURA (print apenas) | LOTE 1 | ✅ Sim | ✅ Seguro | Nenhum |
| 4 | gpt_service.py | 805 | ??? (limpeza) | LEITURA (passa para limpar_contexto) | LOTE 1 | ✅ Sim | ✅ Seguro | Baixo |
| 5 | gpt_service.py | 1309 | ??? (limpeza) | LEITURA (passa para limpar_contexto) | LOTE 1 | ✅ Sim | ✅ Seguro | Baixo |
| 6 | encaixe_service.py | 137 | solicitar_encaixe() | ESCRITA (criar encaixe) | LOTE 2 | ✅ Sim | ✅ Validado | Nenhum |
| 7 | event_service_async.py | 1650 | alterar_agendamento() | ESCRITA (alterar evento) | LOTE 2 | ✅ Sim | ✅ Validado | Nenhum |
| 8 | gpt_executor.py | 455 | ??? (salvar contexto) | ESCRITA (salvar contexto temp) | LOTE 2 | ✅ Sim | ✅ Validado | Nenhum |
| 9 | event_service_async.py | 304 | cancelar_evento() | VALIDAÇÃO (decide autorização) | LOTE 3 | ❌ Não | ⚠️ Risco | MÉDIO |
| 10 | event_service_async.py | 980 | ??? (buscar_disponibilidade?) | VALIDAÇÃO (resolve identidade) | LOTE 3 | ❌ Não | 🔴 Bloqueio | CRÍTICO |
| 11 | excel_service.py | 39 | ??? (export/report) | VALIDAÇÃO (decide pasta) | LOTE 3 | ❌ Não | ⚠️ Risco | ALTO |
| 12 | gpt_executor.py | 224 | ??? (verificar função) | ??? (precisa contexto) | ? | ❌ Não | ? | ? |
| 13 | gpt_executor.py | 264 | ??? (validação expediente?) | VALIDAÇÃO (expediente) | LOTE 3 | ❌ Não | ⚠️ Risco | ALTO |
| 14 | gpt_executor.py | 611 | ??? (WhatsApp?) | VALIDAÇÃO (fallback?) | LOTE 3 | ❌ Não | ⚠️ Risco | CRÍTICO |
| 15 | admin_command_service.py | 86 | ??? (verificar função) | ??? (precisa contexto) | ? | ❌ Não | ? | ? |
| 16 | informacao_service.py | 76 | responder_consulta_informativa() | VALIDAÇÃO (fallback user_id) | LOTE 3 | ❌ Não | 🔴 Bloqueio | CRÍTICO |
| 17 | normalizacao_service.py | 14 | ??? (normalizar serviços?) | VALIDAÇÃO (fallback user_id) | LOTE 3 | ❌ Não | 🔴 Bloqueio | CRÍTICO |
| 18 | session_service.py | 50 | sincronizar_contexto() | VALIDAÇÃO (fallback user_id) | LOTE 3 | ❌ Não | 🔴 BLOQUEADOR | CRÍTICO |

---

## ANÁLISE DETALHADA DE CALLSITES CRÍTICOS

### event_service_async.py:304 — cancelar_evento()

```python
elif tipo_usuario == "dono":
    tenant_evento = await obter_id_dono(cliente_id_evento)
    if tenant_evento != user_id_efetivo:  # ← Sem validação explícita de None
        logger.warning(...)
        return False
```

**Análise:**
- Se `obter_id_dono()` retorna None: comparação `None != user_id_efetivo` é True
- Resultado: função bloqueia o cancelamento (seguro por acaso)
- **Problema:** Lógica não é clara; semanticamente deveria ser `if tenant_evento is None or tenant_evento != user_id_efetivo:`

**Classificação:** LOTE 3 (VALIDAÇÃO) — Risco MÉDIO

---

### event_service_async.py:980 — ??? (buscar_disponibilidade?)

```python
dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
user_id_efetivo = await obter_id_dono(user_id) if dados_usuario else user_id
# ← Se obter_id_dono retorna None: user_id_efetivo = None
eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
# ← Busca em "Clientes/None/Eventos" → vazio ou erro
```

**Análise:**
- Se `dados_usuario` existe mas `obter_id_dono()` retorna None: `user_id_efetivo = None`
- Depois busca em path `Clientes/None/Eventos` (inválido)
- **Problema:** Implicitamente usa fallback None, que causa busca inválida

**Classificação:** LOTE 3 (VALIDAÇÃO) — Risco CRÍTICO (implicit None)

---

### informacao_service.py:76 — responder_consulta_informativa()

```python
try:
    dono_id = await obter_id_dono(user_id)
except Exception:
    dono_id = user_id  # ← FALLBACK PROIBIDO!
```

**Análise:**
- Se exception (Firestore timeout, etc.): usa `user_id` direto
- Depois usa `dono_id` em queries: `Clientes/{dono_id}/...`
- **Problema:** Cross-tenant risk — se Firestore falha, pode acessar dados de outro tenant

**Classificação:** LOTE 3 (VALIDAÇÃO) — Risco CRÍTICO (fallback em exception)

---

### normalizacao_service.py:14 — ???

```python
try:
    dono_id = await obter_id_dono(user_id)
except Exception:
    dono_id = user_id  # ← FALLBACK PROIBIDO!
profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
```

**Análise:**
- Idêntico problema que informacao_service.py:76
- **Problema:** Cross-tenant risk em exception handling

**Classificação:** LOTE 3 (VALIDAÇÃO) — Risco CRÍTICO (fallback em exception)

---

### session_service.py:50 — sincronizar_contexto() — ⚠️ BLOQUEADOR

```python
tenant_id = await obter_id_dono(user_id)
if not tenant_id:
    tenant_id = str(user_id)  # ← FALLBACK PROIBIDO!
    print(f"[TENANT_FALLBACK] sincronizar_contexto: ... using user_id as fallback")
```

**Análise:**
- Explícito fallback `user_id` quando None
- Comentário "[P2-MIGRACAO-LOTE1-OC2]" — de fase anterior
- **Problema:** PROIBIDO ALTERAR session_service.py conforme instruções
- **Bloqueador:** Não posso implementar Lote 3 deixando fallback aqui

**Classificação:** ⚠️ BLOQUEADOR — Não pode ser alterado, mas tem fallback proibido

---

## CONTAGEM CORRIGIDA

✅ **18 callsites confirmados:**

- **LOTE 1 (Leitura):** 5 callsites ✅ Seguro
- **LOTE 2 (Escrita):** 3 callsites ✅ Implementado
- **LOTE 3 (Validação):** 10 callsites ❌ Pendente
  - 3 com fallback explícito (informacao, normalizacao, session)
  - 1 com None implicit (event_service_async:980)
  - 1 com comparison frágil (event_service_async:304)
  - 2 sem contexto verificado (gpt_executor:224, admin_command:86)
  - Vários outros a verificar

---

## LOTE 3 DEFINITIVO

**Callsites pendentes que PRECISAM de implementação:**

| # | Arquivo | Linha | Função | Tipo | Status |
|----|---------|-------|--------|------|--------|
| 1 | event_service_async.py | 304 | cancelar_evento() | VALIDAÇÃO | PENDENTE |
| 2 | event_service_async.py | 980 | ??? | VALIDAÇÃO | PENDENTE |
| 3 | excel_service.py | 39 | ??? | VALIDAÇÃO | PENDENTE |
| 4 | gpt_executor.py | 224 | ??? | ??? | PENDENTE (contexto incompleto) |
| 5 | gpt_executor.py | 264 | ??? | VALIDAÇÃO | PENDENTE |
| 6 | gpt_executor.py | 611 | ??? | VALIDAÇÃO | PENDENTE |
| 7 | admin_command_service.py | 86 | ??? | ??? | PENDENTE (contexto incompleto) |
| 8 | informacao_service.py | 76 | responder_consulta_informativa() | VALIDAÇÃO | ⚠️ FALLBACK PROIBIDO |
| 9 | normalizacao_service.py | 14 | ??? | VALIDAÇÃO | ⚠️ FALLBACK PROIBIDO |
| 10 | session_service.py | 50 | sincronizar_contexto() | VALIDAÇÃO | 🔴 BLOQUEADOR |

---

## BLOQUEADORES IDENTIFICADOS

### Bloqueador #1: session_service.py:50

**Situação:**
- Tem fallback `user_id` proibido
- Instrução diz "NÃO ALTERAR session_service.py"
- Não posso implementar Lote 3 corretamente deixando isso

**Opções:**
1. ✅ Alterar session_service.py (viola instrução original, mas necessário)
2. ❌ Deixar como está (viola integridade de Lote 3)
3. ⚠️ Implementar Lote 3 parcialmente (sem session_service)

**Necessário:** Confirmação do usuário se session_service.py pode ser incluído em Lote 3

---

### Bloqueador #2: Callsites sem contexto completo

**Callsites:**
- gpt_executor.py:224 — não consegui verificar função
- admin_command_service.py:86 — não consegui verificar função

**Necessário:** Verificar contexto completo de cada um antes de implementar

---

## CONCLUSÕES

### ✅ Confirmado:

1. **18 callsites existem** (5 + 3 + 10 = 18)
2. **LOTE 1 (5 callsites)** está seguro
3. **LOTE 2 (3 callsites)** foi implementado
4. **LOTE 3 tem 10 callsites**, não 9

### ⚠️ Riscos Identificados:

1. **3 callsites com fallback `user_id` proibido**
   - informacao_service.py:76
   - normalizacao_service.py:14
   - session_service.py:50

2. **1 callsite com None implícito**
   - event_service_async.py:980

3. **session_service.py é BLOQUEADOR**
   - Tem fallback que viola Lote 3
   - Não pode ser alterado conforme instrução
   - Precisa decisão executiva

### ❓ Itens Pendentes:

1. Verificar contexto completo de 2 callsites
2. Confirmar se session_service.py pode ser incluído em Lote 3
3. Decidir sobre implementação parcial vs. completa

---

## PRÓXIMAS AÇÕES

**Aguardando confirmação do usuário:**

1. ✅ Pode alterar session_service.py:50?
2. ✅ Continuar com Lote 3 com todos os 10 callsites?
3. ✅ Ou implementar apenas os 9 que não incluem session_service?

---

**Status:** ⏸️ AUDITORIA CONCLUÍDA, AGUARDANDO DECISÃO

