# REVISÃO DO PLANO P0 — STATUS FINAL
**Data:** 2026-08-11  
**Situação:** Especificação completamente restruturada para correção arquitetural  
**Timeline:** 4-6h → 8-12h (para fazer **certo**)

---

## O QUE MUDOU

### ❌ MODELO ANTIGO (v1.0 — INVÁLIDO)

**Problemas:**
```
1. Detecção por palavras-chave rígidas
   - Não reconhecia linguagem variada
   - Fallback inexistente
   - Rígido

2. Ator único (cliente)
   - Não suportava dono
   - Não suportava profissional
   - Cenários reais não cobertos

3. Detecção sem GPT
   - Router direto sem interpretação
   - GPT vinha depois
   - Arquitetura invertida

4. Implementação rápida
   - 4-6 horas
   - Arrumação futura provável
   - Débito técnico desde o início
```

### ✅ MODELO NOVO (v2.0 — CORRETO)

**Soluções:**
```
1. Detecção por GPT + heurística
   - Heurística rápida para 70% dos casos
   - GPT interpreta linguagem livre
   - Sem lista infinita de sinônimos

2. 3 atores suportados
   - Cliente altera seus eventos
   - Dono altera eventos do tenant
   - Profissional altera seu escopo
   - Validação determinística

3. Separação clara
   - GPT: apenas interpreta
   - Router: apenas orquestra
   - Motor: apenas executa lógica

4. Implementação certa
   - 8-12 horas
   - Arquitetura sólida
   - Sem débito técnico
```

---

## COMPARAÇÃO DE FLUXOS

### ANTES: Cliente Pede "Reagendar Meu Horário"

```
Cliente: "Reagendar meu horário"
  ↓
[Detector palavras-chave]
eh_gatilho_reagendamento() → True (detectou "reagendar")
  ↓
[Bot → Gateway direto para fluxo]
Lista agendamentos, pede novo horário
  ↓
[Sem validação de permissão]
Altera evento
```

**Problema:** Se cliente disser "Adiar minha manicure" (sem palavra "reagendar"), não funciona.

### DEPOIS: Cliente Pede Com Qualquer Linguagem

```
Cliente: "Adiar minha manicure"
  ↓
[Detector rápido]
eh_heuristica_reagendamento("Adiar minha manicure") → False
  ↓
[Fallback GPT]
GPT: "Isso é reagendamento?" → Sim (confidence 0.92)
  ↓
[Estrutura de intenção]
{intenção: "REAGENDAR", ator_tipo: "cliente", confianca: 0.92}
  ↓
[Validação determinística]
actor_id == evento.cliente_id ✓
  ↓
[Motor]
verificar_conflito + alterar_agendamento()
```

**Benefício:** Funciona com qualquer linguagem natural.

---

## DOCUMENTAÇÃO CRIADA

### 1. PLANO_P0_REAGENDAMENTO_CONVERSACIONAL_REVISADO_2026_08_11.md

**Escopo:** Arquitetura completa

**Seções:**
- Princípios arquiteturais (invioláveis)
- 3 atores (Cliente, Dono, Profissional)
- Detecção de intenção (heurística + GPT)
- 7 máquina de estados
- Contexto minimalista
- Fluxo conversacional (3 cenários)
- Validações determinísticas
- 15+ testes E2E obrigatórios
- Gates de validação final

### 2. CONTRATO_MOTOR_REAGENDAMENTO_2026_08_11.md

**Escopo:** Garantias invioláveis do motor

**Seções:**
- Função `alterar_agendamento()` (5 garantias)
- Função `verificar_conflito_e_sugestoes_profissional()` (4 garantias)
- Como router/bot usa motor (fluxo correto)
- Fluxos incorretos (erros a evitar)
- Testes que validam motor
- Checklist para bot.py

### 3. REVISAO_P0_STATUS_2026_08_11.md (este arquivo)

**Escopo:** Resumo executivo da revisão

---

## MUDANÇAS DE IMPLEMENTAÇÃO

### ANTES (v1.0)

**Archivos a criar/alterar:**
```
router/principal_router.py      +25 linhas (eh_gatilho_reagendamento)
handlers/bot.py                +160 linhas (Gates 2-5)
TESTE_P0_REAGENDAMENTO_E2E     570 linhas (14 cenários)
```

**Total de mudança:** ~755 linhas

**Timeline:** 4-6h

### DEPOIS (v2.0)

**Arquivos a criar/alterar:**
```
router/principal_router.py           +40 linhas (eh_heuristica + detectar_intencao_gpt)
handlers/bot.py                     +200 linhas (7 estados, validações)
services/gpt_service.py             +30 linhas (estrutura de intenção)
TESTE_P0_REAGENDAMENTO_E2E_v2       700+ linhas (15+ cenários)
PLANO_P0_REAGENDAMENTO_REVISADO     ✅ CRIADO
CONTRATO_MOTOR_REAGENDAMENTO        ✅ CRIADO
```

**Total de mudança:** ~1000 linhas + documentação

**Timeline:** 8-12h

---

## CRONOGRAMA REVISADO

| Fase | Descrição | Tempo | Bloqueador |
|------|-----------|-------|-----------|
| **1** | Reescrever E2E com 15+ cenários | 2h | — |
| **2** | Implementar detecção GPT | 2h | — |
| **3** | Implementar 7 estados em bot.py | 3h | Fase 1 |
| **4** | Testes unitários (15+ cenários) | 1h | Fase 3 |
| **5** | Regressão P0 174/174 + P1 42/42 | 1h | Fase 4 |
| **6** | Teste manual E2E conversacional | 1h | Fase 5 |
| **7** | Documentar o que foi feito | 1h | Fase 6 |
| **TOTAL** | | **11h** | |

---

## GATES DE VALIDAÇÃO

### Antes de Iniciar Implementação

- [ ] Entendi que GP interpreta APENAS
- [ ] Entendi que motor executa APENAS
- [ ] Entendi que router orquestra APENAS
- [ ] Entendi 3 atores (cliente, dono, profissional)
- [ ] Entendi 7 máquina de estados
- [ ] Entendi que event_id é preservado (crítico)
- [ ] Entendi que conflito oferece alternativas (não altera)
- [ ] Entendi que confirmação é obrigatória

### Depois de Implementar

- [ ] Detecção reconhece linguagem livre (sem lista fixa)
- [ ] GPT estrutura intenção (não executa motor)
- [ ] Router orquestra (não contém lógica de motor)
- [ ] Motor valida (conflito, permissão, atomicidade)
- [ ] Cliente altera somente seus eventos
- [ ] Dono altera eventos do tenant
- [ ] Profissional respeita escopo
- [ ] Tenant isolation validado
- [ ] 15+ cenários E2E passam
- [ ] Regressão P0 174/174 + P1 42/42 continua PASS

---

## ARQUIVO DE REFERÊNCIA RÁPIDA

Quando implementar, consulte:

| Dúvida | Arquivo | Seção |
|--------|---------|-------|
| "Como GPT interpreta?" | PLANO_P0_REVISADO | Detecção de Intenção |
| "Quais são os 7 estados?" | PLANO_P0_REVISADO | Máquina de Estados |
| "Como chamar motor?" | CONTRATO_MOTOR | Como Router/Bot Usa Motor |
| "O que o motor garante?" | CONTRATO_MOTOR | Garantias Invioláveis |
| "Qual é o fluxo?" | PLANO_P0_REVISADO | Fluxo Conversacional |
| "Quais cenários testar?" | PLANO_P0_REVISADO | Testes E2E Obrigatórios |

---

## PRÓXIMAS AÇÕES (SEQUÊNCIA)

### 1. ✅ Revisar Documentação (Este passo)

- [x] Ler PLANO_P0_REAGENDAMENTO_CONVERSACIONAL_REVISADO_2026_08_11.md
- [x] Ler CONTRATO_MOTOR_REAGENDAMENTO_2026_08_11.md
- [x] Ler este documento (REVISAO_P0_STATUS_2026_08_11.md)

**Tempo:** 30 min

**Próximo:** Iniciar implementação

### 2. ⏭️ Reescrever E2E com 15+ Cenários

**Arquivo:** TESTE_P0_REAGENDAMENTO_E2E_v2.py (novo)

**Grupos de testes:**
- 5 cenários cliente
- 4 cenários dono
- 2 cenários profissional
- 4 cenários motor/persistência
- 3 cenários arquitetura
- 1 cenário regressão

**Tempo:** 2h

### 3. ⏭️ Implementar Detecção GPT

**Arquivo:** router/principal_router.py (novo código)

**Função:** `detectar_intencao_reagendamento(mensagem, contexto)`

**Lógica:**
1. Heurística rápida
2. Se falha, chamar GPT
3. Retornar estrutura de intenção

**Tempo:** 2h

### 4. ⏭️ Implementar 7 Estados em bot.py

**Arquivo:** handlers/bot.py (novo bloco)

**Estados:**
1. REAGENDAMENTO_INICIADO
2. IDENTIFICANDO_EVENTO
3. AGUARDANDO_NOVO_HORARIO
4. VALIDANDO_DISPONIBILIDADE
5. AGUARDANDO_ESCOLHA_ALTERNATIVA
6. AGUARDANDO_CONFIRMACAO
7. AGENDAMENTO_REAGENDANDO

**Tempo:** 3h

### 5. ⏭️ Testes + Regressão

**Tempo:** 2h

---

## IMPORTANTE: PRINCÍPIOS A MANTER

1. **Separação de Responsabilidades**
   - GPT não executa motor
   - Router não contém lógica de agenda
   - Motor não tenta interpretar linguagem

2. **Permissão é Determinística**
   - Nunca delegar ao GPT
   - Sempre validar tenant_id
   - Sempre validar ownership

3. **Motor é Inviolável**
   - Não alterar alterar_agendamento()
   - Não alterar verificar_conflito_e_sugestoes_profissional()
   - Reutilizar 100%

4. **event_id é Sagrado**
   - event_id PRESERVADO (não criar novo)
   - Passar event_id para motor (crítico!)
   - Validar em teste

5. **Confirmação é Obrigatória**
   - Sempre pedir antes de mutar
   - Nunca alterar sem "Sim"
   - Respeitar "Não"

---

## QUANDO IMPLEMENTAR, LEMBRAR

```
Arquitetura > Velocidade

Certo em 12h > Rápido em 4h que vai quebrar depois.

Se descobre um padrão que muda a arquitetura:
1. Pausar implementação
2. Atualizar plano
3. Prosseguir com novo padrão

Não tentar "corrigir depois".
```

---

## STATUS FINAL

**Documentação:** ✅ 100% (3 arquivos principais)  
**Código:** ❌ 0% (não começou, por design)  
**Testes:** ❌ 0% (E2E precisa ser reescrito com 15+ cenários)

**Bloqueador atual:** Nenhum (documentação está completa)

**Próximo:** Iniciar implementação seguindo plano revisado

---

**Validação:** Documentação revisada, aprovada pelo usuário, pronta para implementação.
