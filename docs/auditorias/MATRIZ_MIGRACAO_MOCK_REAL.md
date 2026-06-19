# MATRIZ DE MIGRACAO MOCK → REAL para Testes NeoEve

**Data**: 2026-06-16  
**Status**: Análise Completa  
**Objetivo**: Classificar todos os testes por necessidade de realismo com Firestore/E2E Telegram

---

## Princípios Arquiteturais

1. **GPT** = interpreta linguagem apenas
2. **Motor** = executa lógica crítica (determinístico)
3. **Crítico** = deve usar dados reais/controlados
4. **Telegram** = apenas meio de entrada/saída
5. **Agenda** = CRÍTICA - conflito, disponibilidade, sugestão, criação, cancelamento, contexto
6. **Firestore dev** = sempre, nunca produção
7. **Multi-tenant** = isolamento obrigatório

---

## Resumo Executivo

| Métrica | Valor |
|---------|-------|
| **Total de testes analisados** | 56 arquivos (18 principais) |
| **Mock aceitável (Classificação A)** | 3 testes |
| **Deve virar real (Classificação B)** | 14 testes |
| **Já é real (Classificação C)** | 1 teste |
| **E2E Telegram candidato (Classificação D)** | 0 testes |
| **Testes críticos (P0_REAL_1)** | 8 testes |

---

## Classificações

### A = Mock Aceitável
✅ Pode continuar mockado porque não envolve estado crítico ou integração.

- `runner_dry_run.py` - Lógica determinística isolada
- `debug/teste_contexto_merge.py` - Debug local
- `runner_onboarding_endereco_dono.py` - Setup, não crítico para agendamento

### B = Deve Virar Real
⚠️ Critico demais para ficar mockado. Precisa Firestore dev + contexto persistido.

**P0_REAL_1 (CRÍTICO - Agenda):**
1. `runner_regressao_p0_agendamento_critico.py`
   - Risco: Mock não detecta conflitos reais, sobrescritas, contaminação multi-tenant
   - Ação: Migrar 16 testes para usar Firestore dev real

2. `runner_stress_negativos_agendamento_p0.py`
   - Risco: Validações podem não refletir restrições reais
   - Ação: Testar com serviços/profissionais reais do Firestore

3. `runner_stress_confirmacao_agendamento.py`
   - Risco: Não detecta race conditions
   - Ação: Testar com confirmações simultâneas em Firestore

4. `runner_stress_conflito_aceite_sugestao.py`
   - Risco: Conflito real depende de Firestore, mock não valida
   - Ação: Criar eventos reais, validar conflito, sugerir alternativa

5. `runner_stress_conflito_aceite_confirmacao_final.py`
   - Risco: Cascata de operações críticas com mock
   - Ação: Testar fluxo completo com eventos reais

6. `runner_stress_confirmacao_pendente.py`
   - Risco: Múltiplas transações sem Firestore real
   - Ação: Testar race conditions em contexto persistido

7. `runner_stress_multi_entidades.py`
   - Risco: CRÍTICO - Multi-tenant sem Firestore real pode contaminar
   - Ação: Validar isolamento de tenants com Firestore dev

8. `runner_stress_multientidades_agendamento.py`
   - Risco: CRÍTICO - Contaminação multi-tenant com mock
   - Ação: Testar agendamentos simultâneos em tenants diferentes

**P0_REAL_2 (Agenda - Segunda Onda):**
- `runner_stress_profissional_alternativo_completo.py` - Troca de profissional
- `runner_stress_rajada_agendamento.py` - Rajadas de agendamento

**P1_REAL (Contexto):**
- `runner_stress_interrupcao_informativa_completo.py` - Preservar draft durante pergunta
- `runner_stress_mudanca_contexto_fluxo_ativo.py` - Mudar contexto sem perder fluxo
- `test_clienteprofile_p1.py` - Leitura ClienteProfile real
- `test_p1_2a_leitura_clienteprofile.py` - Segunda leitura ClienteProfile

### C = Já É Real
✅ Já implementado com Firestore dev e contexto persistido. Manter + expandir.

- `runner_p0_persistencia_real.py` - 6 testes: agendamento, cancelamento, profissional, contexto
  - 100% com Firestore dev
  - Salva/recarrega contexto real
  - Cria/cancela eventos reais
  - Multi-tenant validado

### D = E2E Telegram Candidato
📱 Para validar webhook → handler → router → resposta → persistência ponta a ponta.

**Critério**: Apenas 10-20 fluxos máximo. Não duplicar testes internos em Telegram.

**Candidatos iniciais** (após virar B/C):
1. Agendamento completo: "Quero corte com Bruna amanhã às 10" → "Pode"
2. Profissional incompatível: "Quero botox capilar com Bruna" → escolher alternativa → confirmar
3. Conflito de horário: mesmo horário já agendado → sugerir alternativa → aceitar
4. Cancelamento: "Cancelar corte" → "Sim"
5. Interrupção: "Quero corte..." → "Qual horário?" → "Pode"

---

## Matriz Detalhada

### Coluna: Arquivo
Nome do arquivo de teste

### Coluna: Cenário
O que está sendo testado

### Coluna: Fluxo P0/P1
Qual fluxo crítico é coberto

### Coluna: Usa Mock?
- Sim = firebase_mock, contexto_mock, etc
- Não = Firestore dev real

### Coluna: Usa Firestore Real?
- Sim = busca/salva dados reais
- Não = simula Firestore

### Coluna: Cria Evento Real?
- Sim = evento persistido em Firestore
- Não = apenas simula

### Coluna: Salva Contexto Real?
- Sim = via salvar_contexto_temporario() real
- Não = dict em memória

### Coluna: Risco Se Continuar Mockado
- NENHUM = mock suficiente
- BAIXO = pode ficar, não crítico
- MÉDIO = pode esconder bugs
- ALTO = vai quebrar em produção
- CRÍTICO = data corruption / multi-tenant

### Coluna: Classificação
- A = Mock aceitável
- B = Deve virar real
- C = Já é real
- D = E2E Telegram

### Coluna: Prioridade
- P0_REAL_1 = Máxima (agenda crítica, multi-tenant)
- P0_REAL_2 = Alta (agenda, segunda onda)
- P1_REAL = Média (contexto, ClienteProfile)
- N/A = Pode aguardar

---

## TOP 10 Migrações Mais Críticas

### 1. `runner_regressao_p0_agendamento_critico.py`
**Prioridade**: P0_REAL_1  
**Risco**: ALTO  
**O que fazer**:
- Migrar 16 testes para usar Firestore dev
- Criar eventos teste reais
- Validar profissional incompatível com dados reais
- Salvar/recarregar contexto com salvar_contexto_temporario() real

**Estimativa**: 2-3 dias

### 2-3. Multi-tenant (crítico)
**Arquivos**:
- `runner_stress_multi_entidades.py`
- `runner_stress_multientidades_agendamento.py`

**Prioridade**: P0_REAL_1  
**Risco**: CRÍTICO  
**O que fazer**:
- Criar 2+ tenants de teste isolados
- Validar que cada tenant vê apenas seus dados
- Testar agendamentos simultâneos em tenants diferentes
- Verificar contaminação de contexto entre tenants

**Estimativa**: 2 dias

### 4-6. Conflito + Sugestão + Confirmação (cascata)
**Arquivos**:
- `runner_stress_conflito_aceite_sugestao.py`
- `runner_stress_conflito_aceite_confirmacao_final.py`
- `runner_stress_confirmacao_pendente.py`

**Prioridade**: P0_REAL_1  
**Risco**: ALTO  
**O que fazer**:
- Criar eventos reais para detectar conflito
- Testar sugestão de alternativas com horários reais
- Confirmar agendamento após aceitar sugestão
- Validar race conditions

**Estimativa**: 3 dias

### 7-8. Profissional + Rajada
**Arquivos**:
- `runner_stress_profissional_alternativo_completo.py`
- `runner_stress_rajada_agendamento.py`

**Prioridade**: P0_REAL_2  
**Risco**: ALTO  
**O que fazer**:
- Testar troca de profissional com compatibilidade real
- Testar rajadas (10+) de agendamentos sequenciais
- Validar que não há race conditions

**Estimativa**: 2 dias

### 9-10. ClienteProfile + Contexto (P1)
**Arquivos**:
- `test_clienteprofile_p1.py`
- `runner_stress_interrupcao_informativa_completo.py`

**Prioridade**: P1_REAL  
**Risco**: MÉDIO  
**O que fazer**:
- Ler ClienteProfile real do Firestore
- Testar preservação de contexto durante interrupção
- Validar mudança de contexto em fluxo ativo

**Estimativa**: 2 dias

---

## Roadmap de Migração

### Fase 1 (Imediato - 1 semana)
✅ **Já feito**: `runner_p0_persistencia_real.py` (6 testes)

### Fase 2 (P0_REAL_1 - 2 semanas)
- [ ] `runner_regressao_p0_agendamento_critico.py` (16 testes)
- [ ] Multi-tenant: `runner_stress_multi_entidades.py`
- [ ] Conflito+Sugestão: `runner_stress_conflito_aceite_sugestao.py`
- [ ] Confirmação: `runner_stress_confirmacao_pendente.py`

**Total**: ~40 testes novos com Firestore dev

### Fase 3 (P0_REAL_2 - 1 semana)
- [ ] `runner_stress_profissional_alternativo_completo.py`
- [ ] `runner_stress_rajada_agendamento.py`
- [ ] `runner_stress_negativos_agendamento_p0.py`

**Total**: ~12 testes

### Fase 4 (P1_REAL - 1 semana)
- [ ] `test_clienteprofile_p1.py`
- [ ] `test_p1_2a_leitura_clienteprofile.py`
- [ ] `runner_stress_interrupcao_informativa_completo.py`
- [ ] `runner_stress_mudanca_contexto_fluxo_ativo.py`

**Total**: ~8 testes

### Fase 5 (E2E Telegram Canário - 1 semana)
- [ ] Selecionar 10-20 fluxos críticos
- [ ] Testar via Telegram com dados reais
- [ ] Validar webhook → handler → router → resposta → Firestore

**Total**: 10-20 fluxos

---

## Por Que Não Confiar em Mock

| Cenário | Mock Falha | Real Detecta |
|---------|-----------|-------------|
| Conflito de horário | ❌ Mock sempre permite | ✅ Firestore retorna erro |
| Profissional não atende | ❌ Mock nunca valida | ✅ Firestore valida compatibilidade |
| Race condition | ❌ Mock é single-thread | ✅ Firestore transaction atomicidade |
| Multi-tenant contamination | ❌ Mock tudo é global | ✅ Firestore isolamento por tenant |
| Contexto perdido | ❌ Dict em memória é robusto | ✅ Firestore reload detecta bugs |
| Rajada simultânea | ❌ Mock nunca bloqueia | ✅ Firestore locks/conflicts |

---

## Checklist de Migração para Cada Teste

Para migrar um teste de B (mock) para real:

- [ ] Usar `salvar_contexto_temporario()` real (não mock)
- [ ] Usar `carregar_contexto_temporario()` real
- [ ] Criar eventos com `salvar_evento()` real
- [ ] Cancelar com `cancelar_evento()` real
- [ ] Validar com `json.dumps(ctx)` antes de salvar
- [ ] Testar com 2+ tenants isolados
- [ ] Limpar fixtures após teste (criar com prefixo TEST_)
- [ ] Validar comportamento em Firestore dev (nunca prod)
- [ ] 100% testes passam com dados reais

---

## Referências

- **P0 Persistência Real**: `tests/runner_p0_persistencia_real.py` (já implementado)
- **Matriz JSON**: `tests/matriz_migracao_mock_real.json`
- **Documentação Arquitetura**: `docs/ARQUITETURA.md`

---

**Próximas Etapas:**

1. Migrar Fase 2 (P0_REAL_1) em paralelo
2. Manter Firestore dev isolado com dados de teste
3. Validar no Fase 5 com Telegram real
4. **Nunca testar em produção**
