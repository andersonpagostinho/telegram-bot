# 🚀 ROADMAP OFICIAL DE INTELIGÊNCIA — NEOEVE

**Status Base:** P0 concluído, F3-F8 validados  
**Data de Criação:** 2026-07-01  
**Última Atualização:** 2026-07-01  
**Próxima Revisão:** Semanal (toda segunda-feira)

---

## 📊 STATUS ATUAL (BASELINE 54/54)

```
✅ P0: Concluído e validado
✅ F3: 39/39 PASS
✅ F4: 8/8 PASS
✅ F8 (Encaixe MVP): Implementado e validado
✅ Firestore real: Validado
✅ Fronteira GPT → Motor determinístico: Validada
```

---

## 🧠 PRINCÍPIO CENTRAL (IMUTÁVEL)

```
GPT: Interpreta linguagem natural
Motor Determinístico: Executa TUDO
  ├─ Regras de negócio
  ├─ Cálculos
  ├─ Detecção de conflitos
  ├─ Sugestões
  ├─ Criação de eventos
  └─ Persistência

🚫 NENHUMA funcionalidade abaixo pode violar essa regra.
```

---

## 🎯 PRIORIDADE P1 — VALOR IMEDIATO

### **P1.1 — Dashboard do Dono (INICIAR AGORA) 🔴**

**Objetivo:** Gerar valor diário percebido pelo proprietário.

**Status:** ⏳ PLANEJADO

| Componente | Status | Progresso |
|---|---|---|
| Dados de operação | ⏳ Planejado | 0% |
| Dados de clientes | ⏳ Planejado | 0% |
| Dados de profissionais | ⏳ Planejado | 0% |
| Dados de serviços | ⏳ Planejado | 0% |
| Alertas operacionais | ⏳ Planejado | 0% |
| API/Endpoints | ⏳ Planejado | 0% |
| Testes F9 | ⏳ Planejado | 0% |

**Dados Mínimos:**

*Operação:*
- agendamentos do dia
- agendamentos da semana
- taxa de ocupação (%)
- horários mais procurados
- horários ociosos
- cancelamentos da semana
- encaixes convertidos
- lista de espera ativa (count)

*Clientes:*
- clientes novos (últimos 7 dias)
- clientes recorrentes (4+ agendamentos)
- clientes sem retorno (30/60/90 dias)
- top 5 clientes por frequência

*Profissionais:*
- atendimentos por profissional
- ocupação individual (%)
- faturamento estimado por profissional
- cancelamentos recebidos
- serviços mais realizados

*Serviços:*
- ranking de serviços (top 10)
- ticket médio
- duração média real vs estimada
- serviços complementares mais frequentes

*Alertas:*
- ⚠️ Ocupação abaixo de 50%
- 🔴 Cancelamentos acima de 15%
- 🔴 Profissional sem atendimentos por >7 dias
- 📈 Crescimento/queda anormal de demanda (>20%)

**Arquitetura:**

```
services/dashboard_service.py
├── obter_resumo_hoje(tenant_id) → Dict
├── obter_resumo_semana(tenant_id) → Dict
├── obter_metricas_profissionais(tenant_id) → List[Dict]
├── obter_metricas_clientes(tenant_id) → List[Dict]
├── obter_metricas_servicos(tenant_id) → List[Dict]
└── obter_alertas_operacionais(tenant_id) → List[Dict]
```

**Regras Obrigatórias:**
- ✅ Consultas sempre com `tenant_id` explícito
- ✅ Sem GPT para cálculos
- ✅ Agregações determinísticas
- ✅ Cache futuro permitido
- ✅ Firestore como fonte de verdade

**Testes Obrigatórios (F9):**
- [ ] F9-1: Métricas diárias corretas
- [ ] F9-2: Ocupação semanal correta
- [ ] F9-3: Faturamento por profissional
- [ ] F9-4: Clientes recorrentes identificados
- [ ] F9-5: Alertas operacionais disparam
- [ ] F9-6: Isolamento multi-tenant mantido
- [ ] F9-7: Dados vazios não quebram dashboard
- [ ] F9-8: Regressão P0/F3/F4/F8 intacta

**Estimativa:** 8-10 dias

---

### **P1.2 — Retorno Automático (REBOOK) 🟠**

**Objetivo:** Trazer clientes de volta automaticamente.

**Status:** ⏳ PLANEJADO

| Componente | Status | Progresso |
|---|---|---|
| Cálculo de intervalo médio | ⏳ Planejado | 0% |
| Sugestão de horários compatíveis | ⏳ Planejado | 0% |
| Reuso de profissional preferida | ⏳ Planejado | 0% |
| Validação de disponibilidade | ⏳ Planejado | 0% |
| Mensagem ao cliente | ⏳ Planejado | 0% |

**Exemplos:**
```
Manicure:    agendou a cada 28 dias  → próximo em 28 dias
Corte:       agendou a cada 30 dias  → próximo em 30 dias
Luzes:       agendou a cada 60 dias  → próximo em 60 dias
Coloração:   agendou a cada 45 dias  → próximo em 45 dias
```

**Fluxo:**
1. Calcular intervalo médio histórico do cliente
2. Identificar próxima data ideal
3. Sugerir 3 horários compatíveis (usando recomendação inteligente)
4. Oferecer profissional preferida (se disponível)
5. Respeitar disponibilidade real
6. Enviar mensagem ao cliente

**GPT:**
- Apenas redige mensagem (se necessário)

**Motor:**
- Decide TUDO

**Estimativa:** 6-8 dias

---

### **P1.3 — Evolução da Lista de Espera (F8+) 🟡**

**Objetivo:** Expandir F8 com funcionalidades reais.

**Status:** ⏳ PLANEJADO

**Adicionar:**
- [ ] Múltiplos clientes por vaga (priorização)
- [ ] Expiração automática (configurável)
- [ ] Chamada sequencial (ordem de entrada)
- [ ] Prioridades configuráveis (cliente VIP, urgência)
- [ ] Estatísticas de conversão (quantos foram agendados?)
- [ ] Relatório de lista de espera

**Estimativa:** 5-7 dias

---

### **P1.4 — Recomendação Inteligente de Horários 🟡**

**Objetivo:** Ordenar horários por qualidade, não aleatoriamente.

**Status:** ⏳ PLANEJADO

**Score Determinístico:**
```
score = 
    preferência_histórica(cliente, hora) * 0.35 +
    encaixe_operacional(profissional, hora) * 0.25 +
    ocupacao_ideal(hora) * 0.20 +
    risco_heurístico(cliente, hora) * 0.15 +
    janelas_improdutivas(hora) * 0.05
```

**Sem GPT tomando decisões.**

**Estimativa:** 7-9 dias

---

### **P1.5 — Serviços Complementares 🟡**

**Objetivo:** Oferecer complementos inteligentes.

**Status:** ⏳ PLANEJADO

**Exemplo:**
```
Cliente: "Vou fazer coloração"
Bot: "Deseja adicionar hidratação? Leva apenas 45 minutos extras. 
      Clientes que colorem adoram hidratar depois."
```

**Baseado em:**
- Histórico real (cliente já fez combo?)
- Frequência de combinação (quantos fazem?)
- Duração disponível (cabe no slot?)

**Estimativa:** 5-6 dias

---

## 🔍 PRIORIDADE P2 — INTELIGÊNCIA ANALÍTICA

### **P2.1 — Cancelamento Preditivo (HEURÍSTICO)**

**Objetivo:** Identificar clientes com risco de cancelamento.

**Status:** ⏳ PLANEJADO

**Variáveis (sem ML):**
- Histórico de faltas
- Cancelamentos anteriores
- Antecedência do agendamento
- Tempo de resposta
- Confirmações tardias

**Saída:** `"baixo" | "medio" | "alto"`

**Uso:** Confirmar 24h antes se risco alto

**Estimativa:** 5-7 dias

---

### **P2.2 — Detecção de Churn**

**Objetivo:** Identificar clientes que podem sair.

**Status:** ⏳ PLANEJADO

**Regras:**
- Cliente sem retorno há X dias
- Frequência caiu
- Profissional preferida saiu
- Serviços deixaram de ser utilizados

**Ação:** Enviar reengajamento proativo

**Estimativa:** 4-5 dias

---

### **P2.3 — Alertas Operacionais**

**Objetivo:** Notificar dono sobre problemas.

**Status:** ⏳ PLANEJADO

**Exemplos:**
- Ocupação caiu 30%
- Cancelamentos acima de 15%
- Profissional sem agenda
- Lista de espera crescendo rapidamente

**Estimativa:** 3-4 dias

---

## 🚀 PRIORIDADE P3 — ESCALA

### **P3.1 — Modelos Estatísticos Reais**

**Status:** 📅 FUTURO (após milhares de eventos)

Somente após dados suficientes em produção.

---

### **P3.2 — Preço Dinâmico**

**Status:** 📅 FUTURO

Não prioritário para público inicial.

---

### **P3.3 — Otimização Automática de Agenda**

**Status:** 📅 FUTURO

Posterior à consolidação do produto.

---

## 📅 ROADMAP 90 DIAS

### **MÊS 1 (Semanas 1-4)**

```
Semana 1-2:
├─ [🔴] F5 WhatsApp Adapter (integração)
├─ [🔴] Dashboard do Dono (P1.1) — INICIAR
└─ [🔴] Testes F9 (validação)

Semana 3-4:
├─ [🟠] Piloto controlado (clientes reais)
└─ [🟠] Evolução F8 (múltiplos clientes/vaga)
```

**Métrica:** Dashboard em produção com 8/8 testes F9 passando

---

### **MÊS 2 (Semanas 5-8)**

```
Semana 5-6:
├─ [🟠] Retorno Automático (P1.2)
└─ [🟠] Recomendação de Horários (P1.4)

Semana 7-8:
├─ [🟡] Serviços Complementares (P1.5)
└─ [🟡] Regressão P0/F3/F4/F8/F9 completa
```

**Métrica:** +20% recorrência (Retorno Automático), +15% confirmação (Recomendação)

---

### **MÊS 3 (Semanas 9-12)**

```
Semana 9-10:
├─ [🟠] Cancelamento Preditivo (P2.1)
└─ [🟠] Detecção de Churn (P2.2)

Semana 11-12:
├─ [🟡] Alertas Operacionais (P2.3)
└─ [🟡] Regressão final + validação
```

**Métrica:** Reduzir cancelamento de 8% → 5%, churn detectado

---

## 🎯 DECISÃO OFICIAL — PRIORIDADES IMEDIATAS

**Começar com (ordem):**

1. **Dashboard do Dono (F9)** 🔴 AGORA
2. **WhatsApp Adapter (F5)** 🔴 PARALELO
3. **Retorno Automático** 🟠 Semana 5
4. **Evolução F8** 🟠 Paralelo a F9
5. **Recomendação de Horários** 🟠 Semana 5

---

## 🔐 PRINCÍPIO PERMANENTE (IMUTÁVEL)

```
EIXO PRINCIPAL DE EXECUÇÃO:

Serviço
  ↓
Duração (estimada)
  ↓
Disponibilidade (profissional preferida)
  ↓
Conflito (validação)
  ↓
Sugestão (3 horários, alternativas)
  ↓
Criação (evento em Firestore)
  ↓
Histórico (aprender padrão)
  ↓
Retorno (trazer cliente de volta)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⭐ TODA inteligência deve REFORÇAR esse eixo.
❌ NUNCA substituir decisões do motor.
❌ NUNCA deixar GPT decidir de novo.
❌ NUNCA pular passos de validação.
```

---

## 📋 TEMPLATE DE ATUALIZAÇÃO SEMANAL

**Toda segunda-feira, atualizar:**

```markdown
### SEMANA [N] (DD/MM a DD/MM)

**Progresso:**
- [X] P1.1: % pronto
- [ ] P1.2: % pronto
- [ ] P5: % pronto

**Bloqueadores:**
- (se houver)

**Próximos passos:**
- (semana que vem)

**Métrica da semana:**
- (KPI alcançado?)
```

---

## 📞 CONTATO E ESCALAÇÃO

Se houver bloqueador crítico:
1. Registrar em `BLOQUEADORES_SEMANA.md`
2. Indicar impacto na timeline
3. Sugerir solução alternativa
4. Reopriorizar se necessário

---

## 📊 TRACKER DE STATUS

**Legenda:**
- 🔴 Crítico (comece agora)
- 🟠 Alto (próximas 2 semanas)
- 🟡 Médio (próximo mês)
- ⏳ Planejado
- ⚙️ Em progresso
- ✅ Concluído
- 📅 Futuro
- ❌ Bloqueado

---

**Documento Oficial Criado:** 2026-07-01  
**Próxima Atualização:** 2026-07-08  
**Owner:** NeoEve Team  
**Status:** ATIVO

