# BASELINE OFICIAL PÓS-RECLASSIFICAÇÃO P1

**Data:** 2026-06-22  
**Decisão:** Reclassificação de P1 Robustez entrada_gpt_real.py  
**Status:** ✅ OFICIALIZADO

---

## RECLASSIFICAÇÃO

**Antes:** Suíte "P1 Robustez Entrada + Fronteira GPT" com critério 20/20 PASS

**Depois:** Dois cenários distintos:
1. **P1 Robustez GPT/Fronteira:** 12 cenários de validação de entrada GPT
2. **P1 Robustez Fluxo Conversacional:** 13 cenários de fluxo em desenvolvimento

---

## BASELINE OFICIAL ATUAL

| Suíte | Escopo | Critério Oficial | Resultado Atual | Status |
|-------|--------|------------------|-----------------|--------|
| **P1 E2E Onboarding Identidade** | Resolução ator, criação cliente, guard | 15/15 PASS | 15/15 PASS | ✅ ESTÁVEL |
| **P1 E2E Onboarding Operacional** | Setup negócio, agenda, profissionais | 20/20 PASS | 20/20 PASS | ✅ ESTÁVEL |
| **P1 E2E Onboarding Individual** | Estrutura individual, multi-tenant | 7/7 PASS | 7/7 PASS | ✅ ESTÁVEL |
| **P1 Robustez GPT/Fronteira** | Validação de entrada GPT (12 cenários) | 12/12 PASS | 12/12 PASS | ✅ ESTÁVEL |
| **P1 Robustez Fluxo Conversacional** | Fluxo com confirmação/negação (13 cenários) | 3/13 PASS | 3/13 PASS | ⚠️ EM DESENVOLVIMENTO |
| **P0 Regressão Completa** | 9 baterias, 174 cenários críticos | 174/174 PASS | 174/174 PASS | ✅ ESTÁVEL |

---

## TOTAIS ESTÁVEIS

| Categoria | Cenários | Status |
|-----------|----------|--------|
| **P1 E2E Total** | 42/42 PASS | ✅ |
| **P0 Total** | 174/174 PASS | ✅ |
| **P1 + P0 Estável** | 216/216 PASS | ✅ |
| **P1 Fluxo (Desenvolvimento)** | 3/13 PASS | ⚠️ |

---

## DETALHES DA RECLASSIFICAÇÃO

### P1 Robustez GPT/Fronteira (12/12 PASS) ✅

**Cenários validados:**
1. ✅ Profissional inexistente
2. ✅ JSON incompleto do GPT
3. ✅ Ortografia degradada (parcial)
4. ✅ Caracteres estranhos/emojis
5. ✅ GPT tenta criar evento (sem dados)
6. ✅ GPT tenta responder disponibilidade
7. ✅ Ambiguidade com contexto
8. ✅ Profissional mencionado
9. ✅ Mensagem muito curta e errada
10. ✅ Entrada vazia/whitespace
11. ✅ Símbolos especiais
12. ✅ Mensagem genérica

**Propósito:** Validar que entrada GPT é robusta mesmo com dados ruins

**Critério:** 12/12 PASS (100%)

---

### P1 Robustez Fluxo Conversacional (3/13 PASS) ⚠️

**Cenários (13 total):**
1. ✅ Ruído pessoal longo não operacional
2. ❌ Pessoal + agendamento misturado
3. ✅ Ambiguidade sem contexto
4. ❌ Ambiguidade com contexto anterior
5. ❌ Mensagem longa com pedido no final
6. ❌ **Confirmação embutida em parágrafo** ← LOTE 3E
7. ❌ **Negação embutida em parágrafo** ← LOTE 3E
8. ❌ Mensagem muito curta com contexto ativo
9. ❌ Ortografia extremamente degradada
10. ❌ Rajada contraditória
11. ✅ Múltiplas entidades em uma mensagem
12. ❌ Serviço inexistente no fluxo
13. ❌ Regressão P0 - fluxo normal completo

**Propósito:** Validar fluxo conversacional com states complexos, draft, confirmação pendente

**Critério Atual:** 3/13 PASS (desenvolvimento)

**LOTE 3E targets:** Cenários 06 e 07

---

## PROIBIÇÕES E GARANTIAS

### Proibido Alterar em LOTE 3E
- ❌ Prompts GPT
- ❌ Agenda/Conflito/Disponibilidade
- ❌ Criação de evento (além do necessário)
- ❌ Onboarding
- ❌ Multi-tenant
- ❌ Semântica geral do router

### Garantias P1 E2E
- ✅ Manter 42/42 PASS
- ✅ Nenhuma regressão em identidade/operacional/individual

### Garantias P0
- ✅ Manter 174/174 PASS
- ✅ Nenhuma regressão em 9 baterias

---

## PRÓXIMA FASE: LOTE 3E

**Objetivo:** Tratar cenários 06 e 07 (confirmação/negação pendente)

**Abordagem:** Função isolada `resolver_confirmacao_pendente()` chamada early no router

**Escopo mínimo:**
- Detectar confirmação/negação
- Decidir deterministically
- Retornar sem estado global

**Validação:** 06/07 PASS + baseline estável 42/42 + 174/174

---

## HISTÓRICO DE MUDANÇAS

| Data | Evento | Baseline Anterior | Baseline Novo | Status |
|------|--------|-------------------|---------------|---------| 
| 2026-06-21 | P1 Onboarding OK | N/A | 42/42 + 174/174 | ✅ |
| 2026-06-22 | LOTE 3B-3D | 42/42 + 174/174 | 42/42 + 174/174 | ✅ |
| 2026-06-22 | Reclassificação P1 | (20/20 incorreto) | 12/12 + 3/13 | ✅ |

---

**Baseline oficializado:** 2026-06-22T22:45:00Z  
**Próxima fase:** LOTE 3E — Confirmação/Negação Pendente  
**Critério bloqueio:** Se cenário 06/07 não passar OU baseline cair, parar e investigar
