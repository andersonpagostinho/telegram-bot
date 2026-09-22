# 🧠 NeoEve - Análise de Gaps de Inteligência de Agenda

**Data:** 2026-07-01 | **Versão:** v1.0

---

## 📊 RESUMO EXECUTIVO

O NeoEve já possui **inteligência OPERACIONAL** sólida (agendamento, confirmação, cancelamento, fila de espera, detecção de recorrência). 

**Faltam:**
1. **Inteligência PREDITIVA** (prever demanda, no-shows, cancelamentos)
2. **Inteligência ANALÍTICA** (padrões, tendências, insights para dono)
3. **Inteligência RECOMENDATIVA** (sugerir horários ótimos, profissionais, blocos especiais)
4. **Inteligência OTIMIZADORA** (maximizar faturamento, ocupação, eficiência)
5. **Inteligência DE RISCO** (alertar sobre crises de agenda, queda de demanda)

---

## ✅ O QUE JÁ EXISTE (IMPLEMENTADO)

### 1. **Gestão de Agenda Base**
- ✅ Agendamento direto (com validação de conflito)
- ✅ Detecção de bloqueios (agenda salão, profissional)
- ✅ Validação de expediente (9-18h, configurável)
- ✅ Cálculo de duração estimada por serviço
- ✅ Sugestão de 3 horários livres quando conflito

### 2. **Cancelamento Inteligente**
- ✅ Detecção de intenção de cancelar
- ✅ Oferecimento de fila de espera automaticamente
- ✅ Rastreio de cancelamentos pendentes (não duplicados)
- ✅ Reagendamento automático de clientes em fila

### 3. **Fila de Espera Ativa**
- ✅ Criar entrada em lista de espera
- ✅ Notificação automática quando slot libera
- ✅ Conversão automática (fila → agendamento)
- ✅ Expiração automática (2 dias)
- ✅ Encaixe inteligente (gera 3 opções para cliente em fila)

### 4. **Detecção de Recorrência**
- ✅ Identifica padrão de atendimento (ex: cada 14 dias)
- ✅ Calcula mediana de intervalo entre serviços
- ✅ Sugere próxima data com profissional preferida
- ✅ Valida disponibilidade antes de oferecer
- ✅ Mínimo 3 atendimentos para detectar padrão

### 5. **Contexto do Cliente**
- ✅ Profissional preferido (mais frequente)
- ✅ Serviço preferido (mais frequente)
- ✅ Histórico de agendamentos
- ✅ Dependentes (filhos, cônjuges)
- ✅ Contexto motor (influencia sugestões, não decide)

### 6. **Multi-tenant & Isolamento**
- ✅ Suporte a múltiplos salões/negócios
- ✅ Isolamento completo de dados por tenant
- ✅ Contexto por canal (WhatsApp/Telegram)

---

## ❌ O QUE FALTA (GAPS CRÍTICOS)

### **NÍVEL 1: INTELIGÊNCIA PREDITIVA** ⭐⭐⭐⭐⭐

#### 1.1 **Previsão de No-Shows & Cancelamentos** (Prioridade 🔴 CRÍTICA)

**Por que falta:** Sem previsão, não há proteção contra perda de receita.

**Dados disponíveis:**
- Taxa histórica de cancelamento por cliente
- Taxa por hora do dia (ex: 18h mais cancelada que 10h)
- Taxa por dia da semana (ex: sexta mais cancelada)
- Taxa por profissional (tem profissional que choca mais?)
- Histórico de no-shows (não apareceu)

**Sugestões inteligentes possíveis:**
- ✅ Confirmar 24h antes (clientes com >30% no-show)
- ✅ Agendar buffer antes/depois (proteção contra cancelamento)
- ✅ Oferecer "meia-hora antes" para confirmação
- ✅ Double-booking inteligente (aceitar 2 clientes em fila se risco alto)
- ✅ Alertar: "Essa hora tem 40% de cancelamento"

**Implementação sugerida:**
```python
# services/previsao_service.py
async def prever_risco_cancelamento(
    tenant_id: str,
    cliente_id: str,
    data: str,
    hora: str,
    profissional: str
) -> Dict[str, Any]:
    """
    Retorna:
    {
        "risco_cancelamento": 0.35,  # 35% de risco
        "risco_no_show": 0.12,       # 12% de risco
        "recomendacoes": [
            "Enviar lembrete 24h antes",
            "Considerar buffer de 30min"
        ]
    }
    """
```

**Valor de negócio:** Reduzir perda de receita por cancelamento.

---

#### 1.2 **Previsão de Demanda por Período** (Prioridade 🟠 ALTA)

**Por que falta:** Sem previsão, não há preparação para picos/vales.

**Padrões a detectar:**
- Dias com mais demanda (segunda é +40% que quarta?)
- Horas de pico (12-13h mais procurado?)
- Sazonalidade (verão vs inverno, férias)
- Efeito "feriado" (demanda antes de feriado)
- Trends (cresce 5% ao mês?)

**Uso prático:**
- Abrir blocos especiais (estender até 20h) quando prevê pico
- Bloquear horários para descanso quando prevê vale
- Sugerir ao dono: "Sexta às 17h = pico, quer adicionar horário?"
- Contratação de profissional temporário (alerta ao dono)

**Implementação sugerida:**
```python
# services/demanda_service.py
async def prever_demanda_proxima_semana(
    tenant_id: str
) -> Dict[str, Any]:
    """
    Retorna padrão histórico de demanda:
    {
        "segunda": {"ocupacao_prevista": "80%", "pico_hora": "14-15h"},
        "terca": {"ocupacao_prevista": "55%", "vale": "11-12h"},
        ...
        "alertas": [
            "Sexta em alta (82%), considerar profissional extra"
        ]
    }
    """
```

**Valor de negócio:** Otimizar recursos, evitar overbooking, sugerir expansão.

---

### **NÍVEL 2: INTELIGÊNCIA ANALÍTICA** ⭐⭐⭐⭐

#### 2.1 **Dashboard de Saúde da Agenda** (Prioridade 🟠 ALTA)

**Métricas a rastrear:**
- Taxa de ocupação (% de slots preenchidos)
- Taxa de cancelamento (% de agendamentos cancelados)
- Taxa de no-show (% que não apareceu)
- Tempo médio de slot (quantos minutos reais, vs estimado)
- Fila de espera (quantos aguardando, tempo médio)
- Profissional com mais demanda
- Serviço com mais demanda
- Cliente mais frequente
- Receita estimada vs potencial

**Relatório possível:**
```
📊 SAÚDE DA AGENDA - SEMANA 27/06 a 03/07

Ocupação: 72% (📈 +5% vs semana passada)
Cancelamentos: 8% (📉 -2% vs semana passada)
No-Shows: 2% (✅ Normal)
Fila Espera: 4 clientes (esperando média 3 dias)

🔴 ALERTAS:
- Profissional "Carla": Fora 5 dias (27-31 de junho)
  → Rebote: 22 clientes tentarão outros horários
  
- Serviço "Escova": +40% demanda vs mês anterior
  → Sugestão: Adicionar profissional especializando em escova
  
- Segunda-feira: 95% ocupação
  → Risco de overbooking, considerar desdobramento
```

**Valor de negócio:** Visibilidade para decisões (contratação, expansão de horário).

---

#### 2.2 **Análise de Profitabilidade por Serviço** (Prioridade 🟠 ALTA)

**Métricas:**
- Receita por serviço (total e média)
- Receita por profissional (total e média)
- Margem por serviço (se tiver custo)
- Eficiência (receita/tempo investido)
- Crescimento mês a mês

**Exemplo:**
```
💰 PROFITABILIDADE:

Corte:      R$ 2.100/mês (30 sessões) = R$ 70/sessão, 35min
Escova:     R$ 1.850/mês (25 sessões) = R$ 74/sessão, 50min
Progressiva: R$ 800/mês  (4 sessões)  = R$200/sessão, 180min

🚀 INSIGHT: Progressiva é +170% rentável/minuto vs Corte
   → Sugestão: Promover progressiva em fins de semana

📉 ALERTA: Escova caiu 15% vs junho
   → Razão? Profissional saiu? Sazonalidade? Ação?
```

**Valor de negócio:** Identificar serviços mais lucrativos, otimizar portfólio.

---

### **NÍVEL 3: INTELIGÊNCIA RECOMENDATIVA** ⭐⭐⭐⭐⭐

#### 3.1 **Recomendação Inteligente de Horários** (Prioridade 🔴 CRÍTICA)

**O que fazer:** Em vez de apenas 3 horários livres, recomendar os MELHORES 3.

**Critérios:**
- Horário com menos risco de cancelamento
- Horário com menos choque de profissionais
- Horário que corresponde ao padrão do cliente (ex: cliente só vem 14h, não 9h)
- Horário que balanceia agenda (spread dos agendamentos)
- Horário que garante profissional preferida

**Código possível:**
```python
async def recomendar_horarios_otimizados(
    tenant_id: str,
    cliente_id: str,
    servico: str,
    profissional_preferida: str,
    max_opcoes: int = 3
) -> List[Dict[str, Any]]:
    """
    Retorna horários em ordem de qualidade:
    [
        {
            "data": "2026-07-05",
            "hora": "14:00",
            "score": 0.95,  # 95% aderência
            "razoes": [
                "Cliente agendou 14h em 80% das vezes",
                "Profissional 'Carla' tem 2h antes (manutenção de fluxo)",
                "Horário com 15% menos cancelamento"
            ]
        },
        {
            "data": "2026-07-05",
            "hora": "10:00",
            "score": 0.65,  # 65% aderência
            "razoes": ["Profissional disponível", "Menos conflito"]
        },
        ...
    ]
    """
```

**Valor de negócio:** Aumentar confirmação (menos "agendar e depois cancelar").

---

#### 3.2 **Sugestão de Profissional Alternativa** (Prioridade 🟠 ALTA)

**Cenário:** Cliente quer serviço mas profissional preferida não tem horário.

**Inteligência atual:** Oferece 3 horários livres, mas com qual profissional?

**Inteligência faltante:** Sugerir alternativa baseada em:
- Rating/avaliação (se houver)
- Similaridade de estilo (ex: mesma idade, experiência)
- Clientes similares que já usaram (ex: "3 clientes como você amam a Bruna")
- Taxa de satisfação histórica
- Disponibilidade (próxima data disponível)

**Código possível:**
```python
async def recomendar_profissional_alternativa(
    tenant_id: str,
    cliente_id: str,
    profissional_preferida: str,
    servico: str
) -> Dict[str, Any]:
    """
    Retorna alternativas ordenadas por compatibilidade:
    {
        "profissional_preferida": "Carla",
        "disponibilidade": "Próximo slot: 10 de julho",
        "alternativas": [
            {
                "nome": "Bruna",
                "compatibilidade": 0.92,
                "razoes": [
                    "5 clientes com perfil similar já agendaram com ela",
                    "Média 4.8/5 avaliação em 'Escova'",
                    "Disponível amanhã 14h"
                ]
            },
            ...
        ]
    }
    """
```

**Valor de negócio:** Aumentar agendamento, ocupar profissionais alternativos.

---

#### 3.3 **Sugestão de Serviços Complementares** (Prioridade 🟠 ALTA)

**Cenário:** Cliente já tem corte agendado para sexta.

**Sugestão inteligente:**
- "Escova combinada com corte? Resultado ainda melhor"
- "Hidratação + escova = combo R$XX" (10% desconto)
- "Cliente que cortaram semana passada gostaram de progressiva"

**Dados a usar:**
- Histórico do cliente (já fez combo antes?)
- Histórico de clientes similares (o que encaixam?)
- Disponibilidade de profissional (consegue fazer combo no tempo?)
- Complementaridade de serviços (qual vai bem junto?)

**Código possível:**
```python
async def sugerir_servicos_complementares(
    tenant_id: str,
    cliente_id: str,
    servico_principal: str,
    data_agendada: str,
    hora_agendada: str
) -> List[Dict[str, Any]]:
    """
    Retorna sugestões de serviços que encaixam:
    [
        {
            "servico": "Escova",
            "duracao_adicional_minutos": 30,
            "preco": 45.00,
            "compatibilidade": 0.88,
            "razoes": [
                "Cliente fez 'Corte + Escova' 3 vezes antes",
                "Profissional 'Carla' faz combo em 80min total"
            ]
        },
        ...
    ]
    """
```

**Valor de negócio:** Aumentar ticket médio, otimizar tempo do profissional.

---

### **NÍVEL 4: INTELIGÊNCIA OTIMIZADORA** ⭐⭐⭐

#### 4.1 **Otimização de Blocos de Tempo** (Prioridade 🟠 ALTA)

**Problema:** Agenda tem gaps (ex: 11-12h vazio em 60% dos dias de quarta).

**Solução inteligente:**
- Identificar blocos históricos com baixa ocupação
- Sugerir ao dono: "Feche 11-12h de quarta para manutenção"
- Ou: "Abra promoção: 'Desconto 20% se agendar 11-12h quinta'"
- Ou: "Bloqueie 11-12h terça para atendimento administrativo"

**Código possível:**
```python
async def analisar_blocos_subocupados(
    tenant_id: str
) -> Dict[str, Any]:
    """
    Identifica padrões de gaps:
    {
        "blocos_subocupados": [
            {
                "dia_semana": "quarta",
                "horario": "11:00-12:00",
                "ocupacao_media": "15%",
                "ocorrencias": "8/8 quartas (100% consistente)",
                "oportunidade": "R$ 400/mês potencial",
                "sugestoes": [
                    "Bloqueie para descanso/almoço",
                    "Faça promoção: desconto nesse horário",
                    "Coloque profissional em atendimento administrativo"
                ]
            }
        ]
    }
    """
```

**Valor de negócio:** Aumentar ocupação, otimizar tempo do profissional.

---

#### 4.2 **Sugestão de Preços Dinâmicos** (Prioridade 🟡 MÉDIA)

**Problema:** Preço fixo não reflete demanda.

**Inteligência:**
- Sexta às 17h = pico? Aumentar preço 15%
- Terça 11h = vale? Descontar 20%
- Profissional novo = validar com desconto?
- Serviço em demanda = aumentar?

**Código possível:**
```python
async def sugerir_preco_dinamico(
    tenant_id: str,
    servico: str,
    profissional: str,
    data: str,
    hora: str
) -> Dict[str, Any]:
    """
    Retorna recomendação de preço:
    {
        "preco_base": 70.00,
        "multiplicador_demanda": 1.20,  # +20% por alta demanda
        "multiplicador_horario": 0.85,  # -15% por baixa demanda
        "preco_sugerido": 71.40,
        "justificativa": "Sexta 17h tem 90% ocupação historicamente"
    }
    """
```

**Valor de negócio:** Aumentar receita, balancear demanda.

---

### **NÍVEL 5: INTELIGÊNCIA DE RISCO** ⭐⭐⭐

#### 5.1 **Detecção de Crises de Agenda** (Prioridade 🔴 CRÍTICA)

**Cenários de risco:**

**1. Queda de Demanda**
```
🚨 ALERTA RISCO: 
Demanda caiu 35% vs mês anterior
Causas possíveis:
  - Profissional saiu? (Carla não agendada desde 25/jun)
  - Sazonalidade? (Junho costuma ser vale)
  - Competição? (Novo salão abriu na região?)
Ações:
  - Revisar preços?
  - Promoção de retenção?
  - Agendar entrevista com cliente "perdido"?
```

**2. Profissional Sobrecarregado**
```
🚨 ALERTA RISCO:
Bruna tem 92% ocupação nas próximas 2 semanas
Risco: Burnout, queda de qualidade, cancelamento
Ações:
  - Oferecer colega com 60% ocupação
  - Adicionar quebra de 1h para descanso?
  - Contratar profissional temporária?
```

**3. Taxa Anormal de Cancelamento**
```
🚨 ALERTA RISCO:
Cancelamento subiu de 8% para 18% em uma semana
Culpados: Profissional "Bruna" tem 35% de cancelamento (vs 5% em outros)
Ações:
  - Entrevistar Bruna (saúde? conflito?)
  - Auditar comentários (clientes insatisfeitos?)
  - Transferir clientes para colega?
```

**Código possível:**
```python
async def detectar_crises_agenda(
    tenant_id: str
) -> List[Dict[str, Any]]:
    """
    Analisa sinais de risco:
    [
        {
            "tipo_risco": "queda_demanda",
            "severidade": "crítica",
            "descricao": "Demanda caiu 35% vs junho",
            "causas_suspeitas": ["Profissional Carla ausente", "Sazonalidade"],
            "impacto_estimado": "R$ 3.500 perda de faturamento",
            "acoes_sugeridas": ["Revisar preços", "Promoção de retenção"]
        },
        {
            "tipo_risco": "profissional_sobrecarregado",
            "severidade": "alta",
            "profissional": "Bruna",
            "ocupacao": "92%",
            "proximas_2_semanas": 16,
            "acoes_sugeridas": ["Adicionar profissional", "Transferir clientes"]
        }
    ]
    """
```

**Valor de negócio:** Antecipar problemas, evitar crises.

---

#### 5.2 **Monitoramento de Satisfação Implícita** (Prioridade 🟡 MÉDIA)

**Sem feedback explícito, usar comportamento:**
- Cliente marca para próxima semana = satisfeito
- Cliente deixa 1 semana passar sem reagendar = insatisfeito?
- Cliente sempre pede mesma profissional = satisfeito com ela
- Cliente pede troca de profissional após 1 sessão = insatisfeito

**Alertas possíveis:**
```
⚠️ Cliente "Maria" não reagenda há 3 meses
Última sessão: 20/maio com Bruna
Padrão histórico: Agendava a cada 30 dias
Ação: Enviar "Sentir falta de você, agende agora!"

⚠️ Cliente "João" mudou de profissional 3 vezes em 4 meses
Primeira com Carla, depois Bruna, depois Ana
Padrão: Primeiro cliente sempre pede troca
Ação: Entrevista de feedback? Problema de comunicação?
```

**Código possível:**
```python
async def monitorar_satisfacao_implicita(
    tenant_id: str,
    cliente_id: str
) -> Dict[str, Any]:
    """
    Analisa comportamento para inferir satisfação:
    {
        "cliente_nome": "Maria",
        "satisfacao_estimada": "média",
        "sinais": [
            "Agendava a cada 30 dias, agora 90 dias",
            "Sempre pedia Bruna, agora não especifica"
        ],
        "alerta": "Cliente pode estar migrando",
        "acao": "Entrar em contato, confirmar satisfação"
    }
    """
```

**Valor de negócio:** Retenção de clientes, reduzir churn.

---

## 📊 MATRIZ DE PRIORIZAÇÃO

| Funcionalidade | Impacto | Complexidade | Esforço (dias) | Prioridade |
|---|---|---|---|---|
| Previsão No-Show/Cancelamento | 🔴 Alto | 🔴 Alto | 10-15 | 🔴 P0 |
| Dashboard Saúde Agenda | 🟠 Médio | 🟡 Médio | 5-7 | 🟠 P1 |
| Recomendação Horários Otimizados | 🟠 Médio | 🟠 Médio | 8-10 | 🟠 P1 |
| Previsão Demanda | 🟠 Médio | 🔴 Alto | 12-18 | 🟡 P2 |
| Sugestão Profissional Alternativa | 🟡 Baixo | 🟡 Médio | 5-7 | 🟡 P2 |
| Preços Dinâmicos | 🟡 Baixo | 🟡 Médio | 6-8 | 🟡 P2 |
| Análise Profitabilidade | 🟠 Médio | 🟡 Médio | 5-6 | 🟡 P2 |
| Detecção Crises | 🟠 Médio | 🟠 Médio | 7-9 | 🟡 P2 |
| Sugestão Serviços Complementares | 🟡 Baixo | 🟡 Médio | 6-8 | 🟡 P3 |
| Otimização Blocos | 🟡 Baixo | 🟡 Médio | 4-5 | 🟡 P3 |
| Monitoramento Satisfação Implícita | 🟡 Baixo | 🟠 Médio | 6-7 | 🟡 P3 |

---

## 🚀 ROADMAP SUGERIDO

### **FASE 1: FUNDAÇÃO PREDITIVA (4-6 semanas)**
```
Semana 1-2: Previsão No-Show/Cancelamento
├─ Coletar histórico de cancelamentos
├─ Treinar modelo simples (árvore de decisão)
└─ Integrar alertas ao fluxo

Semana 3-4: Dashboard Saúde da Agenda
├─ Crear aggregation funções (ocupação, cancelamento, no-show)
├─ Criar endpoint `/dashboard/saude`
└─ Integrar ao bot como comando `/saude`

Semana 5-6: Recomendação de Horários
├─ Implementar scoring de qualidade de horário
├─ Sortear por score ao invés de aleatório
└─ A/B test: sorteo vs score
```

### **FASE 2: INTELIGÊNCIA RECOMENDATIVA (6-8 semanas)**
```
Semana 7-8: Sugestão Profissional Alternativa
├─ Implementar matchmaking de profissionais
└─ Testar com amostra de clientes

Semana 9-10: Sugestão Serviços Complementares
├─ Implementar collinearity analysis (serviços que vão bem juntos)
└─ Testar com amostra

Semana 11-12: Preços Dinâmicos
├─ Implementar multiplicadores de demanda
└─ Testar em período de baixo risco
```

### **FASE 3: ANÁLISE E RISCO (6-8 semanas)**
```
Semana 13-16: Previsão de Demanda + Análise Profitabilidade
├─ Série temporal (ARIMA, Prophet)
├─ Profitability reports
└─ Alertas de queda de demanda

Semana 17-20: Detecção de Crises
├─ Monitorar padrões anormais
├─ Alertas multi-critério
└─ Sugestões de ação
```

---

## 💡 RECOMENDAÇÕES TÉCNICAS

### **1. Não Começar com ML Complexo**
❌ Evitar: Redes neurais, deep learning, modelos complexos
✅ Começar com: Heurísticas, árvores de decisão, regressão linear

**Por quê:** NeoEve precisa de **explicabilidade**. "Por que cancelou?" é tão importante quanto prever.

### **2. Coletar Dados Primeiro**
Antes de qualquer modelo, rastrear:
- Data/hora do agendamento → Data/hora do cancelamento
- Motivo do cancelamento (quando informado)
- Cliente → Profissional → Serviço
- Feedback (ratings, comentários)

### **3. A/B Testing Obrigatório**
Para cada recomendação, comparar:
- Horários recomendados vs aleatórios
- Profissional recomendada vs aleatória
- Preço dinâmico vs fixo

**Métrica:** Taxa de confirmação do agendamento

### **4. Feedback Loop**
Cada recomendação precisa validar:
- Cliente aceitou? → Score +1
- Cliente cancelou? → Score -2
- Cliente perguntou alternativa? → Score 0

Usar isso para retreinar modelos a cada semana.

### **5. Gradação de Confiança**
Nem toda recomendação é igual:
- Score 0.95 (alta confiança): Destacar, oferecer como padrão
- Score 0.70 (média confiança): Mostrar mas deixar cliente escolher
- Score 0.50 (baixa confiança): Não mostrar

### **6. Fallback em Cascata**
Se modelo falha/não tem dados:
```python
# Tenta score de qualidade
if score > 0.7:
    return recomendacao_inteligente
# Senão, oferece padrão
elif agenda_disponivel:
    return horarios_aleatorios_disponíveis
# Senão, fila de espera
else:
    return lista_espera
```

---

## 🎯 PRÓXIMOS PASSOS

### **Semana Que Vem:**
1. ☐ Definir métricas-chave (KPIs) a rastrear
2. ☐ Criar agregação de dados históricos
3. ☐ Prototipar modelo simples de cancelamento
4. ☐ Desenharpagina de dashboard

### **Próximo Mês:**
1. ☐ Implementar previsão de cancelamento (v1)
2. ☐ Criar dashboard de saúde
3. ☐ Integrar recomendação de horários
4. ☐ Começar coleta de feedback

### **Próximos 3 Meses:**
1. ☐ Recomendação de profissional
2. ☐ Sugestão de serviços
3. ☐ Previsão de demanda
4. ☐ Análise de profitabilidade
5. ☐ Detecção de crises

---

## 📚 APÊNDICES

### **A. Dados Necessários**

Cada agendamento deve rastrear:
```json
{
  "agendamento_id": "evt_123",
  "tenant_id": "salao_456",
  "cliente_id": "cli_789",
  "servico": "corte",
  "profissional": "Carla",
  "data_agendada": "2026-07-05",
  "hora_agendada": "14:00",
  "duracao_minutos": 45,
  "status": "confirmado",
  "timestamps": {
    "criado_em": "2026-07-01T10:30:00Z",
    "cancelado_em": "2026-07-02T09:15:00Z",
    "nao_compareceu_em": null,
    "completado_em": "2026-07-05T14:45:00Z"
  },
  "cancelamento": {
    "motivo": "Saudade não",
    "horario": "2026-07-02T09:15:00Z",
    "dias_antes": 3
  },
  "feedback": {
    "rating": 4.5,
    "comentario": "Adorei o resultado"
  }
}
```

### **B. Modelos Simples para Começar**

**Modelo 1: Árvore de Decisão (Cancelamento)**
```
IF tempo_antes_cancelamento <= 6 horas THEN risco_alto
ELIF cliente_cancelou_antes >= 2 vezes THEN risco_médio
ELIF hora_agendamento >= 17:00 THEN risco_médio
ELSE risco_baixo
```

**Modelo 2: Regressão Linear (Demanda)**
```
demanda_proxima_semana = 
  base_historica * 
  fator_dia_semana * 
  fator_sazonalidade * 
  fator_tendencia
```

### **C. Alertas Prontos para Disparar**

```python
# Se taxa de cancelamento semanal > histórico + 2σ
if cancelamento_semana > media_mensal + 2*desvio_padrao:
    alert("Cancelamento anormalmente alto")

# Se profissional tem ocupação > 85% por 2 semanas
if ocupacao_profissional > 0.85 for 2 weeks:
    alert("Profissional sobrecarregado")

# Se cliente não reagenda há 90 dias
if dias_desde_ultimo_agendamento > 90:
    alert("Cliente pode estar churn")
```

---

**Documento criado:** 2026-07-01  
**Versão:** 1.0  
**Status:** Pronto para discussão com stakeholders

