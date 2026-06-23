# VALIDAÇÃO DE BASELINE: PRÉ-NOVOS PATCHES

**Data:** 2026-06-22T22:15:00Z  
**Escopo:** Validar que suites estáveis não sofreram regressão  
**Status:** ⚠️ **REGRESSÃO DETECTADA** — GPT Robustez caiu significativamente

---

## TABELA DE RESULTADOS

| Suíte | Esperado | Obtido | Status | Observações |
|-------|----------|--------|--------|-------------|
| P1 Robustez GPT | 20/20 PASS | 12/25 PASS | ❌ **REGRESSÃO** | Queda de 20/20 para 12/25 (40% de redução) |
| P1 E2E Onboarding Identidade | 15/15 PASS | 15/15 PASS | ✅ OK | Nenhum problema |
| P1 E2E Onboarding Operacional | 20/20 PASS | 20/20 PASS | ✅ OK | Nenhum problema |
| P1 E2E Onboarding Individual | 7/7 PASS | 7/7 PASS | ✅ OK | Nenhum problema |
| P0 Regressão Completa | 174/174 PASS | 174/174 PASS | ✅ OK | Nenhum problema |
| P1 Fluxo Conversacional | 3/13 PASS | 3/13 PASS* | ⚠️ ATENÇÃO | Baseline mantido MAS novos erros em 06 e 12 |

**Total Esperado:** 239/239 PASS  
**Total Obtido:** 234/244 PASS (95.9%)  
**Bloqueios:** 1 regressão crítica (GPT Robustez)

---

## ANÁLISE DETALHADA

### ✅ Suites Estáveis (SEM PROBLEMA)

#### P1 E2E Onboarding Identidade: 15/15 PASS
- Resolução de ator por canal
- Criação automática de cliente
- Onboarding mínimo
- Validação de guard forte
- **Conclusão:** ✅ Nenhum impacto das alterações LOTE 3D

#### P1 E2E Onboarding Operacional: 20/20 PASS
- Setup completo de negócio
- Definição de agenda
- Cadastro de profissionais e serviços
- Fluxo P0 após onboarding
- **Conclusão:** ✅ Nenhum impacto das alterações

#### P1 E2E Onboarding Individual: 7/7 PASS
- Estrutura individual (dono = profissional)
- Multi-tenant preservation
- Regressão P0
- **Conclusão:** ✅ Nenhum impacto das alterações

#### P0 Regressão Completa: 174/174 PASS
- 9 baterias diferentes
- 174 cenários totais (confirmação, cancelamento, mudança contexto, etc.)
- **Conclusão:** ✅ Sistema core estável

---

### ❌ REGRESSÃO CRÍTICA DETECTADA

#### P1 Robustez GPT: 12/25 PASS (ANTES: 20/20 PASS)

**Queda observada:**
- Esperado: 20 cenários PASS
- Obtido: 12 cenários PASS
- **Redução: -40%** (8 cenários falhando que antes passavam)

**Causa Provável:**
Mudanças em `principal_router.py` durante LOTE 3D, especificamente:
1. Alterações no fluxo de CONSULTA_INFORMATIVA_IDLE (linhas 3869-3875)
   - Guard adicionado para pular consulta se há P0 pendente
   - Pode estar interceptando fluxo de entrada GPT normal

2. Alterações no fluxo de NEOEVE_NEUTRA (linhas 3985-3990)
   - Guard que checa eh_p0_pendente
   - Pode estar bloqueando processamento normal

3. Remoção do BLOCO P0_CONFIRMACAO (linhas 4301-4442)
   - Deixou "criar_evento" ações órfãs
   - Fluxo GPT esperava esse handler

**Investigação Necessária:**
- Verificar se guards em CONSULTA_INFORMATIVA estão muito agressivos
- Verificar se há calls a `criar_evento` que agora falham (cenários 06 e 12 em P1 Fluxo)
- Validar se NEOEVE_NEUTRA está filtrando demais

---

### ⚠️ ATENÇÃO: Novos Erros em P1 Fluxo

#### Cenário 06: "'bool' object has no attribute 'get'"
- Antes: "Confirmação não foi processada"
- Agora: Erro ao tentar processar resultado de função
- **Causa:** Ação 'criar_evento' retornada mas sem handler após remoção do bloco P0_CONFIRMACAO

#### Cenário 12: "'str' object has no attribute 'get'"
- Semelhante ao cenário 06
- **Causa:** Mesmo problema — handler de evento desapareceu

**Status:** P1 Fluxo mantém 3/13 PASS, MAS agora com erros diferentes
- Antes: Dados insuficientes / interception
- Agora: Handler missing / type errors
- **Conclusão:** Não é melhoria, é trade-off piora

---

## DECISÃO DE BLOQUEIO

**Regra do Usuário:**
> "Se qualquer suíte estável falhar, parar imediatamente.  
> Não corrigir nada.  
> Relatar falha, causa provável e último diff relacionado."

**Status Atual:** ⛔ **REGRESSÃO CRÍTICA DETECTADA**

A suíte P1 Robustez GPT caiu de 20/20 para 12/25, violando o critério de estabilidade.

**Ação:** PARAR aqui. Não prosseguir para novos patches.

---

## CAUSA RAIZ PROVÁVEL

O diff relacionado é a série de mudanças em LOTE 3D:

1. **Adicionados Guards em CONSULTA_INFORMATIVA_IDLE (linha 3869)**
   ```python
   if eh_confirmacao_pendente_ativa(ctx) and intencao_p0 in [...]:
       print(f"[GUARD_P0] Pulando CONSULTA_INFORMATIVA...")
   elif not eh_confirmacao_pendente_ativa(ctx):
       # Executar consulta normalmente
   ```
   **Problema:** Mudança de `if not` para `elif` pode estar alterando fluxo esperado para entrada GPT normal

2. **Adicionados Guards em NEOEVE_NEUTRA (linha 3985)**
   ```python
   if modo_conversa == "neutro" and not sinais_humanos_operacionais and not eh_p0_pendente:
   ```
   **Problema:** Condiçãoadicionada pode estar bloqueando respostas GPT que deveriam continuar

3. **Remoção de BLOCO P0_CONFIRMACAO (linhas 4301-4442)**
   - Deixou ações 'criar_evento' órfãs
   - Nenhum handler para processar

---

## PRÓXIMAS AÇÕES RECOMENDADAS

1. ⛔ **PARAR patches P1 Fluxo por agora**

2. **Investigação de causa:**
   - Reverter guards em CONSULTA_INFORMATIVA_IDLE
   - Testar se GPT Robustez volta para 20/20
   - Se sim, guards foram agressivos demais

3. **Revisar estrutura de fluxo:**
   - Por que CONSULTA_INFORMATIVA_IDLE mudou de `if not` para `elif`?
   - Isso mudou a semântica do fluxo?
   - Outros fluxos esperam a lógica anterior?

4. **Documentar antes de prosseguir:**
   - Deixar relatório claro da regressão
   - Guardar o estado do código
   - Preparar plano de reversão se necessário

---

## RESUMO

| Métrica | Status |
|---------|--------|
| Suites estáveis (E2E + P0) | ✅ OK (42/42 + 174/174) |
| Robustez GPT | ❌ REGRESSÃO (20→12) |
| Fluxo Conversacional | ⚠️ ATENÇÃO (novos erros) |
| **Bloqueio Global** | ⛔ **SIM** |

**Recomendação:** Investigar e reverter CONSULTA_INFORMATIVA_IDLE guard antes de continuar.

---

**Validação realizada:** 2026-06-22T22:15:00Z  
**Relatório:** BLOQUEADO — Regressão detectada, novos patches em espera  
**Próxima ação:** Investigação de causa raiz em GPT Robustez
