# 📢 ANÁLISE: COMO AVISAR O DONO SOBRE O DASHBOARD

**Data:** 2026-07-01  
**Fase:** P1.1 Dashboard do Dono  
**Questão Central:** Como, quando e com que frequência informar o dono sobre as métricas

---

## 🔍 SITUAÇÃO ATUAL (BASELINE)

### Existe padrão de relatórios?

✅ **Sim, há precedente:**

```python
# handlers/report_handler.py

Comandos existentes:
├─ /relatorio_diario      → Relatório do dia
├─ /relatorio_semanal     → Relatório da semana
└─ /enviar_relatorio_email → Enviar por email

Como funciona:
1. Dono digita comando
2. Bot busca dados
3. Responde com resumo formatado
```

### E para avisos automáticos?

✅ **Sim, há scheduler:**

```python
# scheduler/daily_summary.py
# scheduler/followup_scheduler.py
# scheduler/notificacoes_scheduler.py

Padrão:
└─ Job rodando em background
   ├─ Checa condição (ex: hora X)
   └─ Envia notificação ao usuário
```

---

## 🎯 TRÊS FORMAS DE AVISAR O DONO

### 1️⃣ **SOB DEMANDA** (Comando)

**Modelo:** `/dashboard`

```python
# handlers/bot.py — adicionar novo comando

async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando: /dashboard
    Uso: Dono digita /dashboard
    Resposta: Dashboard completo agora
    """
    user_id = str(update.message.from_user.id)
    tenant_id = await obter_id_dono(user_id)
    
    dashboard = await obter_dashboard_completo(tenant_id)
    
    msg = f"""
📊 DASHBOARD DO DONO — {dashboard.timestamp}

HOJE:
├─ Ocupação: {dashboard.resumo_hoje.taxa_ocupacao:.0f}%
├─ Agendamentos: {dashboard.resumo_hoje.agendamentos_total}
├─ Cancelamentos: {dashboard.resumo_hoje.taxa_cancelamento:.0f}%
└─ Fila: {dashboard.resumo_hoje.fila_espera_ativa}

SEMANA:
├─ Total: {dashboard.resumo_semana.agendamentos_total}
├─ Ocupação: {dashboard.resumo_semana.taxa_ocupacao:.0f}%
└─ Encaixes: {dashboard.resumo_semana.encaixes_convertidos}

ALERTAS: {len(dashboard.alertas)}
{chr(10).join([f"  🔴 {a.descricao}" for a in dashboard.alertas[:3]])}
"""
    
    await update.message.reply_text(msg)
```

**Vantagens:**
- ✅ Dono controla quando ver
- ✅ Sob demanda (não incomoda)
- ✅ Fácil de implementar

**Desvantagens:**
- ❌ Dono pode esquecer de checar
- ❌ Não alerta proativamente

---

### 2️⃣ **AUTOMÁTICO DIÁRIO** (Scheduler)

**Modelo:** Avisar todo dia em horário fixo (ex: 8h da manhã)

```python
# scheduler/dashboard_scheduler.py (NOVO)

async def avisar_dashboard_diario(application: Application):
    """
    Roda todo dia às 8h
    Envia dashboard do dia anterior
    """
    from services.dashboard_service import obter_dashboard_completo
    
    # Buscar todos os donos (tenants)
    todos_tenants = await _buscar_todos_tenants()
    
    for tenant_id in todos_tenants:
        try:
            dashboard = await obter_dashboard_completo(tenant_id)
            
            # Avisar dono (por chat_id)
            chat_id = await _obter_chat_id_dono(tenant_id)
            
            msg = f"""
📊 RELATÓRIO DIÁRIO — {dashboard.timestamp}
Ocupação: {dashboard.resumo_hoje.taxa_ocupacao:.0f}%
Agendamentos: {dashboard.resumo_hoje.agendamentos_total}
Alertas: {len(dashboard.alertas)}
            """
            
            await application.bot.send_message(
                chat_id=chat_id,
                text=msg
            )
        except Exception as e:
            logger.error(f"Erro avisar dono {tenant_id}: {e}")
```

**Scheduling (usar APScheduler):**

```python
# main.py ou bot_runner.py

scheduler = BackgroundScheduler()

# Todo dia às 8:00 AM
scheduler.add_job(
    avisar_dashboard_diario,
    trigger="cron",
    hour=8,
    minute=0,
    timezone="America/Sao_Paulo"
)

scheduler.start()
```

**Vantagens:**
- ✅ Pró-ativo (dono recebe info)
- ✅ Rotina estabelecida
- ✅ Dono sabe quando esperar

**Desvantagens:**
- ❌ Pode ser incomodo (avisos demais)
- ❌ Complexo de configurar timezone
- ❌ Precisa armazenar chat_id do dono

---

### 3️⃣ **INTELIGENTE — ALERTAS CRÍTICOS** (Evento)

**Modelo:** Avisar APENAS quando há problema

```python
# scheduler/alertas_criticos_scheduler.py (NOVO)

async def alertar_critico(application: Application):
    """
    Roda a cada 30 minutos
    Verifica se há alertas CRÍTICOS
    Se houver: avisa AGORA
    """
    todos_tenants = await _buscar_todos_tenants()
    
    for tenant_id in todos_tenants:
        try:
            alertas = await obter_alertas_operacionais(tenant_id)
            
            # Filtrar APENAS críticos
            criticos = [a for a in alertas if a.severidade == "critical"]
            
            if criticos:  # ← Só avisa se houver críticos!
                chat_id = await _obter_chat_id_dono(tenant_id)
                
                msg = "🚨 ALERTA CRÍTICO NA AGENDA\n\n"
                for alerta in criticos:
                    msg += f"⚠️ {alerta.descricao}\n"
                    msg += f"   Ação: {alerta.acoes_sugeridas[0]}\n\n"
                
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=msg
                )
        except Exception as e:
            logger.error(f"Erro alerta crítico {tenant_id}: {e}")
```

**Vantagens:**
- ✅ Avisa quando importa (problema)
- ✅ Não incomoda com triviais
- ✅ Dono toma ação quando alerta

**Desvantagens:**
- ❌ Dono pode não ver relatório diário normal
- ❌ Precisa de threshold bem calibrado

---

## 🤖 O GPT ENTRA AQUI?

### Cenário 1: Dono pedindo dashboard

**Entrada:** "Quero ver os dados do salão"  
**Variações naturais:**
- "Mostra a agenda"
- "Qual foi a ocupação hoje?"
- "Quantos agendamentos?"
- "Está lotado?"
- "Tem fila de espera?"
- "Quanto faturamos?"
- "Como foi o dia?"

### Decisão: GPT OU NÃO?

#### ❌ **NÃO use GPT** (Determinístico é melhor)

```python
# Padrão MOTOR DETERMINÍSTICO:

router/principal_router.py → _classificar_pedido_dashboard()

Regras:
└─ Se texto contém: "dados", "agenda", "ocupação", "agendamento", etc
   └─ Tipo: "pedido_dashboard"
   └─ Ação: executar obter_dashboard_completo()

Sem GPT envolvido.
Rápido, determinístico, previsível.
```

#### ✅ **POR QUÊ NÃO usar GPT?**

1. **Rápido:** Motor determinístico é 50x+ rápido que GPT
2. **Confiável:** Regex não erra como GPT pode errar
3. **Barato:** Sem custo de API
4. **Simples:** Dono não precisa aprender linguagem natural
5. **Transparente:** Não há "caixa preta"

**Exemplo de padrão determinístico:**

```python
async def classificar_pedido_info(msg: str) -> Optional[str]:
    """
    Classifica se é pedido por dashboard/relatório.
    Sem GPT.
    """
    keywords = [
        r"(dados|métricas|dashboard|relatório|resumo)",
        r"(agenda|agendamentos|ocupação|ocupada)",
        r"(faturamento|receita|ganho)",
        r"(cliente|profissional)",
        r"(hoje|semana|mês)"
    ]
    
    texto_norm = msg.lower()
    
    # Se tem 2+ keywords, é pedido de dashboard
    matches = sum(1 for k in keywords if re.search(k, texto_norm))
    
    if matches >= 2:
        return "pedido_dashboard"  # ← Motor trata
    
    return None
```

---

## 🗓️ QUAL É A PERIODICIDADE CERTA?

### Análise de contexto

**NeoEve é um sistema de agendamento de salão/beleza.**

Padrão de uso:
- Manhã: Dono checa agenda do dia
- Noite: Dono revisa resultados do dia
- Semana: Dono faz planejamento

### Recomendação de Frequência

| Tipo | Frequência | Quando | Por Quê |
|---|---|---|---|
| **Dashboard sob demanda** | Qualquer hora | Quando dono pedir | Sempre disponível |
| **Alerta crítico** | A cada 30 min | Quando problema | Urgente |
| **Resumo diário** | 1x/dia (8h) | Manhã para ver dia | Rotina |
| **Resumo semanal** | 1x/semana (seg) | Segunda-feira | Planejamento |
| **Relatório completo** | 1x/semana (sex) | Sexta-feira | Análise de resultados |

**NÃO fazer:**
- ❌ Avisar a cada agendamento (spam)
- ❌ Avisar a cada cancelamento (spam)
- ❌ Avisar a cada 10 min (incomodo)

---

## 🏗️ IMPLEMENTAÇÃO RECOMENDADA

### **Fase 1: Comando sob demanda (Semana 1)**

```python
# handlers/bot.py
application.add_handler(CommandHandler(
    ["dashboard", "dados", "relatorio"],
    cmd_dashboard
))

# handlers/dashboard_handler.py (NOVO)
async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    tenant_id = await obter_id_dono(user_id)
    
    dashboard = await obter_dashboard_completo(tenant_id)
    msg = _formatar_dashboard(dashboard)
    
    await update.message.reply_text(msg)
```

**Esforço:** 1-2 dias

---

### **Fase 2: Avisos críticos automáticos (Semana 2)**

```python
# scheduler/alertas_scheduler.py (NOVO)
async def check_alertas_criticos(application: Application):
    # Roda a cada 30 min
    # Avisa APENAS se houver críticos

# main.py
scheduler.add_job(
    check_alertas_criticos,
    trigger="interval",
    minutes=30
)
```

**Esforço:** 2-3 dias

---

### **Fase 3: Resumo diário automático (Semana 3)**

```python
# scheduler/dashboard_diario_scheduler.py (NOVO)
async def enviar_dashboard_diario(application: Application):
    # Roda todo dia às 8h

# main.py
scheduler.add_job(
    enviar_dashboard_diario,
    trigger="cron",
    hour=8,
    minute=0,
    timezone="America/Sao_Paulo"
)
```

**Esforço:** 2-3 dias

---

## 🔄 FLUXO COMPLETO (COM GPT ROLE CLARO)

```
DONO PEDINDO DASHBOARD:

Mensagem: "Quero ver os dados do salão"
    ↓
[Motor Determinístico]
├─ Classificar: É pedido de dashboard?
├─ Resultado: SIM → tipo="pedido_dashboard"
└─ Sem GPT aqui! (rápido, confiável)
    ↓
[Dashboard Service]
├─ obter_dashboard_completo(tenant_id)
├─ Buscar: resumo, métricas, alertas
└─ Retornar dataclass estruturado
    ↓
[Formatação]
├─ _formatar_dashboard(dashboard)
└─ Gerar mensagem legível
    ↓
[Envio]
└─ await update.message.reply_text(msg)


QUANDO GPT ENTRA (se entra):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SITUAÇÃO: Dono faz pergunta mais complexa
Mensagem: "Por que minha ocupação caiu essa semana?"

Aqui SIM usamos GPT:
├─ Análise de causa
├─ Sugestão de ação
└─ Texto humanizado

Mas NUNCA para:
❌ Decidir se é pedido de dashboard
❌ Calcular ocupação
❌ Buscar dados
❌ Gerar alertas
```

---

## 📋 RECOMENDAÇÃO FINAL

### **Próximos Passos P1.1**

1. ✅ **Semana 1:** Comando `/dashboard` (sob demanda)
   - Não avisar automaticamente ainda
   - Apenas quando dono pedir
   - Implementar determinístico

2. ✅ **Semana 2-3:** Alertas críticos automáticos
   - Avisma APENAS se houver problema
   - A cada 30 minutos de verificação
   - Dono quer saber de crises

3. ✅ **Semana 4+:** Resumo diário (depois do P1.1 validado)
   - Só depois de validar se comando funciona

### **Sobre GPT**

- ✅ Use GPT: Para análise/insight ("por quê caiu?")
- ❌ NÃO use GPT: Para interpretar pedido de dashboard
- ✅ Motor determinístico: Mais rápido e confiável

---

## 🎯 CHECKLIST

```
[ ] Implementar comando /dashboard (determinístico)
[ ] Testar com pedidos variados
[ ] Não usar GPT para classificar (motor basta)
[ ] Avisos críticos: Depois, separado
[ ] Documentar no ROADMAP_OFICIAL
[ ] Adicionar testes F9
```

---

**Análise:** 2026-07-01  
**Status:** Pronto para implementar  
**Foco:** Comando sob demanda primeiro, automação depois

