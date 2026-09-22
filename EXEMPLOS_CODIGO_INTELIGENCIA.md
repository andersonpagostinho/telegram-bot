# 💻 NeoEve - Exemplos de Código para Implementação

**Arquivo de Referência:** Protótipos de código para os 5 principais features

---

## 1️⃣ PREVISÃO DE CANCELAMENTO

### `services/previsao_cancelamento_service.py`

```python
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from services.firebase_service_async import buscar_subcolecao

logger = logging.getLogger(__name__)

@dataclass
class RiscoPrevisao:
    risco_percentual: float  # 0-100
    nivel: str  # "baixo", "medio", "alto"
    razoes: List[str]
    acoes_recomendadas: List[str]

async def prever_risco_cancelamento(
    tenant_id: str,
    cliente_id: str,
    data_agendamento: str,
    hora_agendamento: str,
    profissional: str
) -> RiscoPrevisao:
    """
    Retorna previsão de risco de cancelamento baseado em:
    1. Histórico de cancelamentos do cliente
    2. Padrão de hora/dia da semana
    3. Profissional específico
    4. Distância do agendamento (dias)
    """
    
    # 1. Buscar histórico de cancelamentos do cliente
    historico = await _buscar_historico_cancelamentos(tenant_id, cliente_id)
    taxa_cancelamento_cliente = historico["taxa_cancelamento"]  # ex: 0.35
    vezes_cancelou = historico["quantidade"]  # ex: 5
    
    # 2. Análise de hora/dia
    dias_ate_agendamento = _calcular_dias(data_agendamento)
    hora_int = int(hora_agendamento.split(":")[0])
    dia_semana = _obter_dia_semana(data_agendamento)  # "segunda", "terça", etc
    
    # 3. Fatores de risco
    score = 0.0
    razoes = []
    
    # Fator 1: Histórico do cliente
    if taxa_cancelamento_cliente > 0.30:
        score += 35  # +35 pontos
        razoes.append(f"Cliente cancelou {vezes_cancelou}x antes (35% taxa)")
    elif taxa_cancelamento_cliente > 0.15:
        score += 15
        razoes.append(f"Cliente tem histórico moderado de cancelamento")
    
    # Fator 2: Horário (clientes cancelam mais tarde à noite?)
    if hora_int >= 17:  # 17h+
        score += 20
        razoes.append("Agendamento às 17h+ (hora pico de cancelamento)")
    elif hora_int < 10:  # antes de 10am
        score += 10
        razoes.append("Agendamento cedo (madrugadores cancelam mais?)")
    
    # Fator 3: Dia da semana
    if dia_semana == "sexta":
        score += 15
        razoes.append("Sexta tem 40% mais cancelamento historicamente")
    elif dia_semana == "segunda":
        score -= 10  # -10 (segunda é mais segura)
        razoes.append("Segunda tem menos cancelamento (padrão estável)")
    
    # Fator 4: Proximidade do agendamento (últimamente cancelam <24h?)
    if dias_ate_agendamento < 1:
        score += 40  # ALTÍSSIMO RISCO
        razoes.append("Agendamento hoje/amanhã (urgência = cancelamento?)")
    elif dias_ate_agendamento < 3:
        score += 20
        razoes.append("Agendamento em 2-3 dias (risco aumentado)")
    elif dias_ate_agendamento > 14:
        score += 10  # Cliente esquece?
        razoes.append("Agendamento muito distante (fácil esquecer)")
    
    # Fator 5: Profissional específico
    taxa_prof = await _buscar_taxa_cancelamento_profissional(tenant_id, profissional)
    if taxa_prof > 0.25:
        score += 15
        razoes.append(f"Profissional '{profissional}' tem 25%+ cancelamento")
    
    # Nivelar score (0-100)
    score = min(100, max(0, score))
    
    # Classificar nível de risco
    if score >= 70:
        nivel = "alto"
        acoes = [
            "❌ Não fazer double-booking",
            "✅ Enviar CONFIRMAÇÃO 24h antes",
            "✅ Enviar LEMBRETE 2h antes",
            "✅ Considerar cancelar com adiantamento"
        ]
    elif score >= 40:
        nivel = "medio"
        acoes = [
            "✅ Enviar lembrete 24h antes (padrão)",
            "⚠️  Manter +1 slot de backup nesse horário"
        ]
    else:
        nivel = "baixo"
        acoes = [
            "✅ Nenhuma ação adicional necessária",
            "📊 Padrão estável"
        ]
    
    return RiscoPrevisao(
        risco_percentual=int(score),
        nivel=nivel,
        razoes=razoes,
        acoes_recomendadas=acoes
    )

async def _buscar_historico_cancelamentos(
    tenant_id: str,
    cliente_id: str
) -> Dict[str, Any]:
    """Busca histórico de cancelamentos do cliente."""
    try:
        # Buscar últimos 50 agendamentos
        agendamentos = await buscar_subcolecao(
            f"Clientes/{tenant_id}/agendamentos",
            limit=50
        ) or []
        
        cancelados = sum(1 for ag in agendamentos if ag.get("status") == "cancelado")
        total = len(agendamentos)
        taxa = cancelados / total if total > 0 else 0
        
        return {
            "taxa_cancelamento": taxa,
            "quantidade": cancelados,
            "total_agendamentos": total
        }
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        return {"taxa_cancelamento": 0.15, "quantidade": 0, "total_agendamentos": 0}

async def _buscar_taxa_cancelamento_profissional(
    tenant_id: str,
    profissional: str
) -> float:
    """Calcula taxa de cancelamento específica de uma profissional."""
    try:
        # Em produção, isso viria de agregação no Firestore
        # Por enquanto, retorna valor hardcoded como placeholder
        taxas_por_prof = {
            "Carla": 0.08,
            "Bruna": 0.12,
            "Ana": 0.25,  # Alta taxa de cancelamento
        }
        return taxas_por_prof.get(profissional, 0.10)  # Default 10%
    except Exception:
        return 0.10

def _calcular_dias(data_agendamento: str) -> int:
    """Calcula dias entre hoje e agendamento (ex: '2026-07-05')."""
    try:
        agendado = datetime.strptime(data_agendamento, "%Y-%m-%d").date()
        hoje = datetime.now().date()
        return (agendado - hoje).days
    except Exception:
        return 0

def _obter_dia_semana(data_str: str) -> str:
    """Retorna dia da semana ('segunda', 'terca', etc)."""
    try:
        data = datetime.strptime(data_str, "%Y-%m-%d")
        dias = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
        return dias[data.weekday()]
    except Exception:
        return "desconhecido"

# INTEGRAÇÃO NO BOT
# handlers/bot.py
async def confirmar_agendamento(update, context):
    # ... código existente ...
    
    # NOVO: Verificar risco de cancelamento
    risco = await prever_risco_cancelamento(
        tenant_id=context.user_data["tenant_id"],
        cliente_id=context.user_data["cliente_id"],
        data_agendamento=context.user_data["data"],
        hora_agendamento=context.user_data["hora"],
        profissional=context.user_data["profissional"]
    )
    
    # Se risco alto, avisar e oferecer confirmação extra
    if risco.nivel == "alto":
        msg_aviso = f"""
🔴 AVISO: Taxa alta de cancelamento para esse horário
Razões: {', '.join(risco.razoes[:2])}

Você tem certeza que confirma?
"""
        await update.message.reply_text(msg_aviso)
        # Adicionar botões de confirmação extra
        # ...
```

---

## 2️⃣ RECOMENDAÇÃO INTELIGENTE DE HORÁRIOS

### `services/recomendacao_horarios_service.py`

```python
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class HorarioRecomendado:
    data: str  # "2026-07-05"
    hora: str  # "14:00"
    score: float  # 0-1.0
    razoes: List[str]
    profissional: str

async def recomendar_horarios_otimizados(
    tenant_id: str,
    cliente_id: str,
    servico: str,
    profissional_preferida: str,
    horarios_disponiveis: List[Tuple[str, str]],  # [(data, hora), ...]
    max_opcoes: int = 3
) -> List[HorarioRecomendado]:
    """
    Ordena horários disponíveis por qualidade/aderência.
    
    Args:
        horarios_disponiveis: Lista de (data, hora) livres
        profissional_preferida: Profissional preferida
    
    Returns:
        Lista de HorarioRecomendado ordenada por score (melhor primeiro)
    """
    
    # Buscar histórico do cliente
    historico = await _buscar_historico_cliente(tenant_id, cliente_id)
    padroes_cliente = {
        "hora_preferida": historico.get("hora_mais_frequente", "14:00"),  # cliente agenda 14h em 70% das vezes
        "dia_preferido": historico.get("dia_mais_frequente", "quarta"),
        "profissional_frequente": historico.get("profissional_mais_frequente"),
    }
    
    # Calcular score para cada horário disponível
    opcoes_com_score = []
    
    for data, hora in horarios_disponiveis:
        score = 0.0
        razoes = []
        
        # FATOR 1: Hora coincide com histórico do cliente?
        if hora == padroes_cliente["hora_preferida"]:
            score += 0.35
            razoes.append(f"Você agendou {hora} em 70% das vezes")
        else:
            # Quão perto está da hora preferida?
            diff = abs(int(hora.split(":")[0]) - int(padroes_cliente["hora_preferida"].split(":")[0]))
            if diff == 1:  # 1 hora de diferença
                score += 0.15
                razoes.append(f"Perto de sua hora habitual ({padroes_cliente['hora_preferida']})")
        
        # FATOR 2: Profissional preferida?
        if profissional_preferida == padroes_cliente["profissional_frequente"]:
            score += 0.25
            razoes.append(f"Sua profissional favorita '{profissional_preferida}'")
        
        # FATOR 3: Risco de cancelamento é baixo?
        risco_cancelamento = await _estimar_risco_cancelamento(
            tenant_id, cliente_id, data, hora, profissional_preferida
        )
        if risco_cancelamento < 0.30:  # <30% risco
            score += 0.20
            razoes.append(f"Baixo risco de cancelamento ({int(risco_cancelamento*100)}%)")
        
        # FATOR 4: Encaixe com profissional (não tem cliente antes/depois conflitando?)
        encaixe_prof = await _calcular_encaixe_profissional(
            tenant_id, profissional_preferida, data, hora
        )
        if encaixe_prof > 0.8:  # >80% encaixe
            score += 0.15
            razoes.append("Ótimo encaixe na agenda da profissional")
        
        # FATOR 5: Dia da semana (segunda é mais segura que sexta?)
        dia_semana = datetime.strptime(data, "%Y-%m-%d").strftime("%A")
        if dia_semana.lower() in ["monday", "tuesday"]:  # segunda, terça (mais seguras)
            score += 0.05
            razoes.append(f"Dia da semana estável ({dia_semana})")
        
        opcoes_com_score.append({
            "data": data,
            "hora": hora,
            "score": score,
            "razoes": razoes,
            "profissional": profissional_preferida,
            "risco_cancelamento": risco_cancelamento
        })
    
    # Ordenar por score (melhor primeiro) e retornar top N
    ordenados = sorted(opcoes_com_score, key=lambda x: x["score"], reverse=True)[:max_opcoes]
    
    return [
        HorarioRecomendado(
            data=op["data"],
            hora=op["hora"],
            score=op["score"],
            razoes=op["razoes"],
            profissional=op["profissional"]
        )
        for op in ordenados
    ]

async def _buscar_historico_cliente(
    tenant_id: str,
    cliente_id: str
) -> Dict[str, Any]:
    """Busca padrões históricos do cliente."""
    try:
        # Em produção: agregar dados do Firestore
        # Placeholder:
        return {
            "hora_mais_frequente": "14:00",  # cliente agendou nessa hora em 70% das vezes
            "dia_mais_frequente": "quarta",
            "profissional_mais_frequente": "Carla",
            "taxa_confirmacao": 0.92  # confirmou 92% dos agendamentos
        }
    except Exception:
        return {}

async def _estimar_risco_cancelamento(
    tenant_id: str,
    cliente_id: str,
    data: str,
    hora: str,
    profissional: str
) -> float:
    """Reutiliza o modelo de previsão de cancelamento."""
    from services.previsao_cancelamento_service import prever_risco_cancelamento
    
    risco = await prever_risco_cancelamento(
        tenant_id, cliente_id, data, hora, profissional
    )
    return risco.risco_percentual / 100  # Converter 35% → 0.35

async def _calcular_encaixe_profissional(
    tenant_id: str,
    profissional: str,
    data: str,
    hora: str
) -> float:
    """Quanto essa hora se encaixa bem na agenda da profissional?"""
    # Verificar se há outros agendamentos próximos (bom para fluxo)
    # Score = 1.0 se há espaço bem, 0.5 se é isolado
    return 0.85  # Placeholder

# INTEGRAÇÃO NO BOT
# handlers/bot.py
async def sugerir_horarios(update, context):
    """Quando sistema oferece horários, usar recomendação inteligente."""
    
    horarios_disponiveis = [
        ("2026-07-05", "09:00"),
        ("2026-07-05", "14:00"),
        ("2026-07-05", "17:00"),
    ]
    
    recomendacoes = await recomendar_horarios_otimizados(
        tenant_id=context.user_data["tenant_id"],
        cliente_id=context.user_data["cliente_id"],
        servico=context.user_data["servico"],
        profissional_preferida=context.user_data["profissional"],
        horarios_disponiveis=horarios_disponiveis,
        max_opcoes=3
    )
    
    # Enviar em ordem de qualidade
    msg = "📅 Melhores horários disponíveis:\n\n"
    for i, rec in enumerate(recomendacoes, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        msg += f"{emoji} {rec.data} às {rec.hora} (Qualidade: {int(rec.score*100)}%)\n"
        msg += f"   {rec.razoes[0]}\n\n"
    
    await update.message.reply_text(msg)
```

---

## 3️⃣ DASHBOARD DE SAÚDE DA AGENDA

### `services/dashboard_saude_service.py`

```python
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass
import logging
from services.firebase_service_async import buscar_subcolecao

logger = logging.getLogger(__name__)

@dataclass
class DashboardSaude:
    ocupacao_percentual: float  # 0-100
    taxa_cancelamento: float  # 0-100
    taxa_no_show: float  # 0-100
    fila_espera_count: int
    profissionais_sobrecarregados: List[str]
    alertas: List[str]
    tendencia_semana: str  # "subindo", "estavel", "caindo"

async def gerar_dashboard_saude(tenant_id: str) -> DashboardSaude:
    """
    Gera um snapshot de saúde da agenda.
    Métricas da semana atual vs semana anterior.
    """
    
    # 1. Buscar agendamentos da semana
    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    
    agendamentos_semana = await _buscar_agendamentos_periodo(
        tenant_id, inicio_semana, fim_semana
    )
    
    # 2. Calcular OCUPAÇÃO
    total_slots = await _calcular_total_slots_disponiveis(tenant_id, inicio_semana, fim_semana)
    slots_preenchidos = len([a for a in agendamentos_semana if a["status"] in ["confirmado", "concluido"]])
    ocupacao = (slots_preenchidos / total_slots * 100) if total_slots > 0 else 0
    
    # 3. Calcular CANCELAMENTO
    cancelados = len([a for a in agendamentos_semana if a["status"] == "cancelado"])
    taxa_cancelamento = (cancelados / len(agendamentos_semana) * 100) if agendamentos_semana else 0
    
    # 4. Calcular NO-SHOW (não compareceu)
    no_shows = len([a for a in agendamentos_semana if a["status"] == "nao_compareceu"])
    taxa_no_show = (no_shows / len(agendamentos_semana) * 100) if agendamentos_semana else 0
    
    # 5. Fila de espera
    fila = await _buscar_fila_espera(tenant_id)
    fila_count = len(fila)
    
    # 6. Profissionais sobrecarregados
    profs_sobrecarregados = await _identificar_profissionais_sobrecarregados(
        tenant_id, inicio_semana, fim_semana
    )
    
    # 7. Alertas
    alertas = await _gerar_alertas(
        tenant_id, ocupacao, taxa_cancelamento, profs_sobrecarregados
    )
    
    # 8. Tendência (vs semana anterior)
    tendencia = await _calcular_tendencia_ocupacao(tenant_id, inicio_semana)
    
    return DashboardSaude(
        ocupacao_percentual=ocupacao,
        taxa_cancelamento=taxa_cancelamento,
        taxa_no_show=taxa_no_show,
        fila_espera_count=fila_count,
        profissionais_sobrecarregados=profs_sobrecarregados,
        alertas=alertas,
        tendencia_semana=tendencia
    )

async def _buscar_agendamentos_periodo(
    tenant_id: str,
    inicio: date,
    fim: date
) -> List[Dict[str, Any]]:
    """Busca todos os agendamentos do período."""
    try:
        # Em produção: query no Firestore com range de datas
        agendamentos = await buscar_subcolecao(
            f"Clientes/{tenant_id}/agendamentos"
        ) or []
        # Filtrar por data (simplificado)
        return [a for a in agendamentos if inicio <= a.get("data") <= fim]
    except Exception as e:
        logger.error(f"Erro ao buscar agendamentos: {e}")
        return []

async def _calcular_total_slots_disponiveis(
    tenant_id: str,
    inicio: date,
    fim: date
) -> int:
    """Total de slots disponíveis no período."""
    # Simplificado: 8 profissionais * 8h/dia * 2 slots/h * 6 dias = 768 slots
    dias = (fim - inicio).days + 1
    slots_por_dia = 16  # 2 slots/h * 8h
    profissionais = 8  # placeholder
    return dias * slots_por_dia * profissionais

async def _buscar_fila_espera(tenant_id: str) -> List[Dict]:
    """Busca cliente em fila de espera."""
    try:
        fila = await buscar_subcolecao(
            f"Clientes/{tenant_id}/listaEspera"
        ) or []
        return [f for f in fila if f.get("status") == "ativo"]
    except Exception:
        return []

async def _identificar_profissionais_sobrecarregados(
    tenant_id: str,
    inicio: date,
    fim: date
) -> List[str]:
    """Identifica profissionais com >85% ocupação."""
    agendamentos = await _buscar_agendamentos_periodo(tenant_id, inicio, fim)
    
    ocupacao_por_prof = {}
    for ag in agendamentos:
        prof = ag.get("profissional")
        if prof:
            ocupacao_por_prof[prof] = ocupacao_por_prof.get(prof, 0) + 1
    
    # Considerar sobrecarregado se tem >30 agendamentos em semana (>85% ocupação)
    return [prof for prof, count in ocupacao_por_prof.items() if count > 30]

async def _gerar_alertas(
    tenant_id: str,
    ocupacao: float,
    taxa_cancelamento: float,
    profs_sobrecarregados: List[str]
) -> List[str]:
    """Gera alertas baseado em métricas."""
    alertas = []
    
    # Alerta 1: Ocupação baixa
    if ocupacao < 50:
        alertas.append(f"⚠️  Ocupação baixa ({int(ocupacao)}%). Promoção?")
    
    # Alerta 2: Ocupação alta
    if ocupacao > 90:
        alertas.append(f"🔴 ALERTA: Agenda 90%+ cheia. Risco de overbooking!")
    
    # Alerta 3: Cancelamento alto
    if taxa_cancelamento > 12:
        alertas.append(f"⚠️  Taxa de cancelamento alta ({int(taxa_cancelamento)}%)")
    
    # Alerta 4: Profissional sobrecarregado
    if profs_sobrecarregados:
        nomes = ", ".join(profs_sobrecarregados)
        alertas.append(f"⚠️  Profissionais sobrecarregadas: {nomes}")
    
    return alertas

async def _calcular_tendencia_ocupacao(
    tenant_id: str,
    inicio_semana_atual: date
) -> str:
    """Compara ocupação com semana anterior."""
    # Simplificado
    # Em produção: buscar ocupação semana anterior
    ocupacao_anterior = 65
    ocupacao_atual = 72  # exemplo
    
    if ocupacao_atual > ocupacao_anterior + 5:
        return "subindo 📈"
    elif ocupacao_atual < ocupacao_anterior - 5:
        return "caindo 📉"
    else:
        return "estavel ➡️"

# INTEGRAÇÃO NO BOT
# handlers/bot.py
async def cmd_saude_agenda(update, context):
    """Comando: /saude"""
    
    dashboard = await gerar_dashboard_saude(
        tenant_id=context.user_data["tenant_id"]
    )
    
    msg = f"""
📊 SAÚDE DA AGENDA - SEMANA 27/06 a 03/07

📈 Ocupação: {int(dashboard.ocupacao_percentual)}%
❌ Cancelamentos: {int(dashboard.taxa_cancelamento)}%
⛔ No-Shows: {int(dashboard.taxa_no_show)}%
⏳ Fila de Espera: {dashboard.fila_espera_count} clientes

🔴 ALERTAS:
"""
    for alerta in dashboard.alertas:
        msg += f"  {alerta}\n"
    
    await update.message.reply_text(msg)
```

---

## 4️⃣ SUGESTÃO DE PROFISSIONAL ALTERNATIVA

### `services/recomendacao_profissional_service.py`

```python
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProfissionalAlternativa:
    nome: str
    compatibilidade: float  # 0-1.0
    razoes: List[str]
    proxima_disponibilidade: str  # data
    proxima_hora: str  # hora

async def recomendar_profissional_alternativa(
    tenant_id: str,
    cliente_id: str,
    profissional_preferida: str,
    servico: str
) -> List[ProfissionalAlternativa]:
    """
    Quando profissional preferida não tem horário, sugerir alternativas.
    
    Critérios:
    - Perfil semelhante (idade, experiência, avaliação)
    - Clientes similares a este já usaram?
    - Avaliação/rating
    - Disponibilidade próxima
    """
    
    # 1. Buscar todas as profissionais disponíveis
    todas_profs = await _buscar_profissionais_salao(tenant_id)
    
    # 2. Excluir a preferida (já não tem)
    alternativas = [p for p in todas_profs if p["nome"] != profissional_preferida]
    
    # 3. Calcular compatibilidade para cada uma
    alternativas_com_score = []
    
    for prof in alternativas:
        score = 0.0
        razoes = []
        
        # Fator 1: Rating/avaliação
        rating = prof.get("rating", 4.0)  # ex: 4.8
        score += (rating / 5.0) * 0.30  # Até 0.30 pontos
        razoes.append(f"Avaliação: {rating}⭐")
        
        # Fator 2: Clientes similares que já usaram
        clientes_similares_usando = await _contar_clientes_similares(
            tenant_id, cliente_id, prof["nome"], servico
        )
        if clientes_similares_usando >= 3:
            score += 0.35
            razoes.append(f"{clientes_similares_usando} clientes como você amam {prof['nome']}")
        elif clientes_similares_usando >= 1:
            score += 0.15
            razoes.append(f"Outros clientes já confiaram em {prof['nome']}")
        
        # Fator 3: Especialidade em serviço
        if servico.lower() in [s.lower() for s in prof.get("especialidades", [])]:
            score += 0.20
            razoes.append(f"{prof['nome']} é especialista em {servico}")
        
        # Fator 4: Disponibilidade próxima
        proxima_data, proxima_hora = await _buscar_proxima_disponibilidade(
            tenant_id, prof["nome"], servico
        )
        dias_ate = _calcular_dias(proxima_data)
        if dias_ate <= 2:
            score += 0.15
            razoes.append(f"Disponível amanhã ({proxima_data})")
        elif dias_ate <= 7:
            score += 0.10
            razoes.append(f"Disponível em {dias_ate} dias")
        
        alternativas_com_score.append({
            "nome": prof["nome"],
            "compatibilidade": score,
            "razoes": razoes,
            "proxima_data": proxima_data,
            "proxima_hora": proxima_hora
        })
    
    # 4. Ordenar por compatibilidade
    ordenadas = sorted(alternativas_com_score, key=lambda x: x["compatibilidade"], reverse=True)[:3]
    
    return [
        ProfissionalAlternativa(
            nome=op["nome"],
            compatibilidade=op["compatibilidade"],
            razoes=op["razoes"],
            proxima_disponibilidade=op["proxima_data"],
            proxima_hora=op["proxima_hora"]
        )
        for op in ordenadas
    ]

async def _buscar_profissionais_salao(tenant_id: str) -> List[Dict[str, Any]]:
    """Retorna lista de todas as profissionais."""
    # Placeholder
    return [
        {"nome": "Bruna", "rating": 4.8, "especialidades": ["Escova", "Hidratação"]},
        {"nome": "Ana", "rating": 4.5, "especialidades": ["Corte", "Penteado"]},
        {"nome": "Carla", "rating": 4.9, "especialidades": ["Progressiva", "Escova"]},
    ]

async def _contar_clientes_similares(
    tenant_id: str,
    cliente_id: str,
    profissional: str,
    servico: str
) -> int:
    """Quantos clientes com perfil similar já usaram essa profissional?"""
    # Placeholder
    return 4  # 4 clientes similares já usaram Bruna

async def _buscar_proxima_disponibilidade(
    tenant_id: str,
    profissional: str,
    servico: str
) -> tuple[str, str]:
    """Retorna próxima data/hora disponível."""
    # Placeholder
    return ("2026-07-06", "14:00")

def _calcular_dias(data: str) -> int:
    """Dias até a data."""
    from datetime import datetime
    data_obj = datetime.strptime(data, "%Y-%m-%d").date()
    return (data_obj - datetime.now().date()).days

# INTEGRAÇÃO NO BOT
# handlers/bot.py
async def oferecer_profissional_alternativa(update, context):
    """Quando profissional preferida não tem horário."""
    
    alternativas = await recomendar_profissional_alternativa(
        tenant_id=context.user_data["tenant_id"],
        cliente_id=context.user_data["cliente_id"],
        profissional_preferida="Carla",
        servico="Escova"
    )
    
    msg = "😊 Carla não tem horário disponível em breve.\n"
    msg += "Mas temos ótimas alternativas:\n\n"
    
    for alt in alternativas:
        msg += f"💇‍♀️ {alt.nome} (compatibilidade {int(alt.compatibilidade*100)}%)\n"
        msg += f"   {alt.razoes[0]}\n"
        msg += f"   Disponível: {alt.proxima_disponibilidade} às {alt.proxima_hora}\n\n"
    
    await update.message.reply_text(msg)
```

---

## 5️⃣ DETECÇÃO DE CRISES

### `services/deteccao_crises_service.py`

```python
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CriseAlerta:
    tipo: str  # "queda_demanda", "profissional_sobrecarregado", etc
    severidade: str  # "critica", "alta", "media"
    descricao: str
    causas_suspeitas: List[str]
    impacto_estimado: str
    acoes_sugeridas: List[str]

async def detectar_crises_agenda(tenant_id: str) -> List[CriseAlerta]:
    """
    Analisa sinais de risco na agenda.
    Retorna lista de crises detectadas, ordenada por severidade.
    """
    
    crises = []
    
    # CRISE 1: Queda de demanda
    queda = await _detectar_queda_demanda(tenant_id)
    if queda:
        crises.append(queda)
    
    # CRISE 2: Profissional sobrecarregado
    profs_sobrecarregadas = await _detectar_profissionais_sobrecarregados(tenant_id)
    for prof_alerta in profs_sobrecarregadas:
        crises.append(prof_alerta)
    
    # CRISE 3: Taxa de cancelamento anormal
    cancelamento = await _detectar_cancelamento_anormal(tenant_id)
    if cancelamento:
        crises.append(cancelamento)
    
    # CRISE 4: Profissional ausente/saída
    ausencia = await _detectar_profissional_ausente(tenant_id)
    if ausencia:
        crises.append(ausencia)
    
    # Ordenar por severidade
    ordem_severidade = {"critica": 0, "alta": 1, "media": 2}
    crises.sort(key=lambda x: ordem_severidade.get(x.severidade, 3))
    
    return crises

async def _detectar_queda_demanda(tenant_id: str) -> CriseAlerta | None:
    """Detecta queda anormal de demanda."""
    
    # Comparar 2 semanas: semana passada vs semana anterior
    hoje = datetime.now().date()
    semana_atual = hoje - timedelta(days=7)
    semana_anterior = semana_atual - timedelta(days=7)
    
    agendamentos_atual = await _contar_agendamentos_periodo(
        tenant_id, semana_atual, hoje
    )
    agendamentos_anterior = await _contar_agendamentos_periodo(
        tenant_id, semana_anterior, semana_atual
    )
    
    # Calcular queda percentual
    if agendamentos_anterior > 0:
        queda_pct = (agendamentos_anterior - agendamentos_atual) / agendamentos_anterior * 100
    else:
        queda_pct = 0
    
    # Se caiu >20%, é crise
    if queda_pct > 20:
        causas = await _investigar_causas_queda(tenant_id)
        
        impacto_estimado = f"R$ {int(queda_pct/100 * 80 * 20 * 30)} de perda/mês"
        
        return CriseAlerta(
            tipo="queda_demanda",
            severidade="critica" if queda_pct > 40 else "alta",
            descricao=f"Demanda caiu {int(queda_pct)}% vs semana anterior",
            causas_suspeitas=causas,
            impacto_estimado=impacto_estimado,
            acoes_sugeridas=[
                "Revisar preços competitivos",
                "Lançar promoção de retenção",
                "Entrevistar clientes 'perdidos'",
                "Verificar avaliações (Google, redes sociais)"
            ]
        )
    
    return None

async def _detectar_profissionais_sobrecarregados(tenant_id: str) -> List[CriseAlerta]:
    """Detecta profissionais com ocupação >85%."""
    
    alertas = []
    profs_cargas = await _calcular_carga_professionais(tenant_id)
    
    for prof, ocupacao in profs_cargas.items():
        if ocupacao > 0.85:  # >85%
            agendamentos_proximas_2sem = await _contar_agendamentos_prof(
                tenant_id, prof, dias_afrente=14
            )
            
            alertas.append(CriseAlerta(
                tipo="profissional_sobrecarregado",
                severidade="alta",
                descricao=f"{prof} tem {int(ocupacao*100)}% ocupação nas próximas 2 semanas",
                causas_suspeitas=[
                    "Crescimento de demanda",
                    "Ausência de outra profissional"
                ],
                impacto_estimado=f"Risco de {prof} ficar sobrecarregada",
                acoes_sugeridas=[
                    f"Oferecer colega com menor carga para clientes",
                    f"Adicionar profissional temporária",
                    f"Aumentar preço de {prof} (demanda alta)"
                ]
            ))
    
    return alertas

async def _detectar_cancelamento_anormal(tenant_id: str) -> CriseAlerta | None:
    """Detecta se taxa de cancelamento aumentou anormalmente."""
    
    taxa_media_historica = 0.08  # 8% é normal
    taxa_atual = await _calcular_taxa_cancelamento_semana(tenant_id)
    
    if taxa_atual > taxa_media_historica * 2:  # >16%
        causas = await _investigar_cancelamentos_altos(tenant_id)
        
        return CriseAlerta(
            tipo="cancelamento_anormal",
            severidade="alta",
            descricao=f"Taxa de cancelamento {int(taxa_atual*100)}% (normal: 8%)",
            causas_suspeitas=causas,
            impacto_estimado=f"R$ {int((taxa_atual - taxa_media_historica) * 100 * 20)} perda/semana",
            acoes_sugeridas=[
                "Auditar comentários de clientes",
                "Verificar saúde/bem-estar de profissionais",
                "Oferecer confirmações extra para clientes com histórico"
            ]
        )
    
    return None

async def _detectar_profissional_ausente(tenant_id: str) -> CriseAlerta | None:
    """Detecta se profissional desapareceu sem avisar."""
    
    profs = await _buscar_profissionais_salao(tenant_id)
    
    for prof in profs:
        ultimos_agendamentos = await _buscar_ultimos_agendamentos_prof(
            tenant_id, prof["nome"], limit=5
        )
        
        if ultimos_agendamentos:
            ultimo_agendamento = ultimos_agendamentos[-1]
            dias_desde = (datetime.now().date() - ultimo_agendamento["data"]).days
            
            # Se não tem agendamento há >7 dias (sem aviso), suspeita
            if dias_desde > 7:
                # Contar quantos clientes eram dela
                clientes_afetados = await _contar_clientes_agendados_prof(
                    tenant_id, prof["nome"], proximas_2_semanas=True
                )
                
                if clientes_afetados > 0:
                    return CriseAlerta(
                        tipo="profissional_ausente",
                        severidade="critica",
                        descricao=f"{prof['nome']} não tem agendamentos há {dias_desde} dias",
                        causas_suspeitas=[
                            "Profissional saiu sem avisar",
                            "Problema de saúde",
                            "Conflito interno"
                        ],
                        impacto_estimado=f"{clientes_afetados} clientes sem profissional preferida",
                        acoes_sugeridas=[
                            f"Entrar em contato urgente com {prof['nome']}",
                            "Redistribuir clientes para colegas",
                            "Comunicar aos clientes sobre alternativas"
                        ]
                    )
    
    return None

async def _investigar_causas_queda(tenant_id: str) -> List[str]:
    """Investiga possíveis causas de queda de demanda."""
    causas = []
    
    # Checklist de causas possíveis
    
    # 1. Profissional saiu?
    profs_ausentes = await _detectar_profissional_ausente(tenant_id)
    if profs_ausentes:
        causas.append("Profissional-chave ausente")
    
    # 2. Sazonalidade? (é julho, férias?)
    if datetime.now().month in [7, 8, 12]:
        causas.append("Possível sazonalidade (férias/recesso)")
    
    # 3. Avaliações ruins? (placar baixa)
    rating_medio = await _buscar_rating_medio(tenant_id)
    if rating_medio < 4.0:
        causas.append("Avaliações caíram (clientes insatisfeitos?)")
    
    # 4. Concorrência nova na região?
    causas.append("Nova competição na região? (verificar)")
    
    # 5. Preços aumentaram muito?
    # Faria sentido verificar histórico de preços...
    
    return causas

# Helpers
async def _contar_agendamentos_periodo(tenant_id: str, inicio: date, fim: date) -> int:
    return 24  # Placeholder

async def _calcular_taxa_cancelamento_semana(tenant_id: str) -> float:
    return 0.12  # Placeholder (12% taxa)

async def _investigar_cancelamentos_altos(tenant_id: str) -> List[str]:
    return ["Profissional X tem alta taxa (35%)", "Hora pico (17h+)"]  # Placeholder

async def _calcular_carga_professionais(tenant_id: str) -> Dict[str, float]:
    return {"Carla": 0.92, "Bruna": 0.65, "Ana": 0.78}  # Placeholder

async def _buscar_profissionais_salao(tenant_id: str) -> List[Dict]:
    return [{"nome": "Carla"}, {"nome": "Bruna"}]  # Placeholder

async def _buscar_ultimos_agendamentos_prof(tenant_id: str, prof: str, limit: int = 5):
    return [{"data": date.today() - timedelta(days=8)}]  # Placeholder

async def _contar_clientes_agendados_prof(tenant_id: str, prof: str, proximas_2_semanas: bool) -> int:
    return 22  # Placeholder

async def _buscar_rating_medio(tenant_id: str) -> float:
    return 4.3  # Placeholder

# INTEGRAÇÃO NO BOT
# handlers/bot.py - Executar diariamente
async def verificar_crises_diariamente(application):
    """Task que roda diariamente para detectar crises."""
    
    todos_tenants = await _buscar_todos_tenants()
    
    for tenant_id in todos_tenants:
        crises = await detectar_crises_agenda(tenant_id)
        
        if crises:
            # Notificar dono
            dono_id = await _obter_id_dono(tenant_id)
            msg = "🚨 ALERTAS DE CRISE DA AGENDA:\n\n"
            
            for crise in crises:
                msg += f"🔴 {crise.tipo.upper()}\n"
                msg += f"   {crise.descricao}\n"
                msg += f"   Ações: {', '.join(crise.acoes_sugeridas[:2])}\n\n"
            
            await _enviar_notificacao(dono_id, msg)
```

---

## 📋 PRÓXIMOS PASSOS

1. **Escolher** qual das 5 funcionalidades implementar primeiro
2. **Adaptar** os exemplos para a arquitetura real do NeoEve
3. **Integrar** ao bot (handlers)
4. **Testar** com dados reais
5. **Medir** impacto (antes vs depois)

Documentos de referência:
- `ANALISE_GAPS_INTELIGENCIA_AGENDA.md` — Análise completa
- `RESUMO_EXECUTIVO_INTELIGENCIA.md` — Visão executiva

