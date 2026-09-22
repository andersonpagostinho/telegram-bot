# services/dashboard_service.py
"""
Dashboard do Dono — Métricas operacionais da agenda

F9 — Dashboard do Dono
Objetivo: Gerar valor diário percebido pelo proprietário do negócio.

Dados:
- Operação (agendamentos, ocupação, cancelamentos)
- Clientes (novos, recorrentes, sem retorno)
- Profissionais (atendimentos, ocupação, faturamento)
- Serviços (ranking, ticket médio)
- Alertas (ocupação baixa, cancelamentos altos, profissional ausente)

Motor determinístico — Sem GPT para cálculos.
Firestore como fonte de verdade.
"""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from pytz import timezone

from services.firebase_service_async import (
    buscar_subcolecao,
    buscar_dado_em_path,
    obter_id_dono,
)

logger = logging.getLogger(__name__)
FUSO_BR = timezone("America/Sao_Paulo")


# ============================================================================
# DATACLASSES — Estruturas de retorno
# ============================================================================

@dataclass
class ResumoOperacional:
    """Resumo das operações do dia/semana."""
    agendamentos_total: int
    agendamentos_confirmados: int
    agendamentos_cancelados: int
    agendamentos_concluidos: int
    taxa_ocupacao: float  # 0-100
    taxa_cancelamento: float  # 0-100
    encaixes_convertidos: int
    fila_espera_ativa: int


@dataclass
class MetricasCliente:
    """Métricas de clientes."""
    clientes_novos_7_dias: int
    clientes_recorrentes: int  # 4+ agendamentos
    clientes_sem_retorno_30_dias: int
    clientes_sem_retorno_60_dias: int
    clientes_sem_retorno_90_dias: int
    top_clientes: List[Dict[str, Any]]  # [{nome, frequencia, ultima_visita}, ...]


@dataclass
class MetricasProfissional:
    """Métricas por profissional."""
    profissional: str
    atendimentos: int
    ocupacao_percentual: float
    faturamento_estimado: float
    cancelamentos_recebidos: int
    taxa_cancelamento: float
    servicos_mais_realizados: List[Tuple[str, int]]  # [(servico, count), ...]
    dias_sem_agendamento: int


@dataclass
class MetricasServico:
    """Métricas por serviço."""
    servico: str
    quantidade: int
    ticket_medio: float
    duracao_media_estimada: int  # minutos
    duracao_media_real: int  # minutos
    taxa_complementares: float  # % que fez combo com outro


@dataclass
class AlertaOperacional:
    """Alerta para o dono."""
    tipo: str  # "ocupacao_baixa", "cancelamento_alto", etc
    severidade: str  # "info", "warning", "critical"
    descricao: str
    acoes_sugeridas: List[str]


@dataclass
class DashboardCompleto:
    """Dashboard completo do dono."""
    timestamp: str  # ISO format
    resumo_hoje: ResumoOperacional
    resumo_semana: ResumoOperacional
    metricas_clientes: MetricasCliente
    metricas_profissionais: List[MetricasProfissional]
    metricas_servicos: List[MetricasServico]
    alertas: List[AlertaOperacional]


# ============================================================================
# FUNÇÕES PÚBLICAS — API do Dashboard
# ============================================================================

async def obter_resumo_hoje(tenant_id: str) -> ResumoOperacional:
    """
    Retorna resumo operacional de hoje.

    Args:
        tenant_id: ID do dono/salão

    Returns:
        ResumoOperacional com métricas do dia
    """
    hoje = datetime.now(FUSO_BR).date()
    agendamentos = await _buscar_agendamentos_data(tenant_id, hoje)

    if not agendamentos:
        return ResumoOperacional(
            agendamentos_total=0,
            agendamentos_confirmados=0,
            agendamentos_cancelados=0,
            agendamentos_concluidos=0,
            taxa_ocupacao=0.0,
            taxa_cancelamento=0.0,
            encaixes_convertidos=0,
            fila_espera_ativa=0,
        )

    confirmados = sum(1 for a in agendamentos if a.get("status") == "confirmado")
    cancelados = sum(1 for a in agendamentos if a.get("status") == "cancelado")
    concluidos = sum(1 for a in agendamentos if a.get("status") == "concluido")

    ocupados = confirmados + concluidos
    taxa_ocupacao = (ocupados / len(agendamentos) * 100) if agendamentos else 0.0
    taxa_cancelamento = (cancelados / len(agendamentos) * 100) if agendamentos else 0.0

    encaixes = sum(1 for a in agendamentos if a.get("origem") == "encaixe")

    fila = await _buscar_fila_espera_ativa(tenant_id)
    fila_count = len(fila)

    return ResumoOperacional(
        agendamentos_total=len(agendamentos),
        agendamentos_confirmados=confirmados,
        agendamentos_cancelados=cancelados,
        agendamentos_concluidos=concluidos,
        taxa_ocupacao=taxa_ocupacao,
        taxa_cancelamento=taxa_cancelamento,
        encaixes_convertidos=encaixes,
        fila_espera_ativa=fila_count,
    )


async def obter_resumo_semana(tenant_id: str) -> ResumoOperacional:
    """
    Retorna resumo operacional da semana.

    Args:
        tenant_id: ID do dono/salão

    Returns:
        ResumoOperacional com métricas da semana (seg-dom)
    """
    hoje = datetime.now(FUSO_BR).date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())  # Segunda
    fim_semana = inicio_semana + timedelta(days=6)  # Domingo

    agendamentos = await _buscar_agendamentos_periodo(tenant_id, inicio_semana, fim_semana)

    if not agendamentos:
        return ResumoOperacional(
            agendamentos_total=0,
            agendamentos_confirmados=0,
            agendamentos_cancelados=0,
            agendamentos_concluidos=0,
            taxa_ocupacao=0.0,
            taxa_cancelamento=0.0,
            encaixes_convertidos=0,
            fila_espera_ativa=0,
        )

    confirmados = sum(1 for a in agendamentos if a.get("status") == "confirmado")
    cancelados = sum(1 for a in agendamentos if a.get("status") == "cancelado")
    concluidos = sum(1 for a in agendamentos if a.get("status") == "concluido")

    ocupados = confirmados + concluidos
    taxa_ocupacao = (ocupados / len(agendamentos) * 100) if agendamentos else 0.0
    taxa_cancelamento = (cancelados / len(agendamentos) * 100) if agendamentos else 0.0

    encaixes = sum(1 for a in agendamentos if a.get("origem") == "encaixe")

    fila = await _buscar_fila_espera_ativa(tenant_id)
    fila_count = len(fila)

    return ResumoOperacional(
        agendamentos_total=len(agendamentos),
        agendamentos_confirmados=confirmados,
        agendamentos_cancelados=cancelados,
        agendamentos_concluidos=concluidos,
        taxa_ocupacao=taxa_ocupacao,
        taxa_cancelamento=taxa_cancelamento,
        encaixes_convertidos=encaixes,
        fila_espera_ativa=fila_count,
    )


async def obter_metricas_profissionais(tenant_id: str) -> List[MetricasProfissional]:
    """
    Retorna métricas por profissional (últimos 30 dias).

    Args:
        tenant_id: ID do dono/salão

    Returns:
        Lista de MetricasProfissional ordenada por atendimentos DESC
    """
    hoje = datetime.now(FUSO_BR).date()
    inicio = hoje - timedelta(days=30)

    agendamentos = await _buscar_agendamentos_periodo(tenant_id, inicio, hoje)

    if not agendamentos:
        return []

    # Agrupar por profissional
    por_prof: Dict[str, List[Dict]] = {}
    for ag in agendamentos:
        prof = ag.get("profissional", "Sem profissional")
        if prof not in por_prof:
            por_prof[prof] = []
        por_prof[prof].append(ag)

    metricas = []

    for prof, agenda_prof in por_prof.items():
        atendimentos = len(agenda_prof)
        confirmados = sum(1 for a in agenda_prof if a.get("status") in ["confirmado", "concluido"])
        cancelados = sum(1 for a in agenda_prof if a.get("status") == "cancelado")

        # Ocupação: % de confirmados+concluidos
        ocupacao = (confirmados / atendimentos * 100) if atendimentos > 0 else 0

        # Faturamento estimado (simplificado: ticket médio * confirmados)
        ticket_medio = await _calcular_ticket_medio_profissional(tenant_id, prof)
        faturamento = ticket_medio * confirmados

        # Taxa de cancelamento
        taxa_cancel = (cancelados / atendimentos * 100) if atendimentos > 0 else 0

        # Serviços mais realizados (campo "servico" não está sempre preenchido)
        servicos_dict: Dict[str, int] = {}
        for ag in agenda_prof:
            servico = ag.get("descricao", "Agendamento")  # Usar descricao como proxy de servico
            if servico:
                servicos_dict[servico] = servicos_dict.get(servico, 0) + 1

        servicos_top = sorted(servicos_dict.items(), key=lambda x: x[1], reverse=True)[:5]

        # Dias sem agendamento
        dias_sem = await _contar_dias_sem_agendamento(tenant_id, prof, dias_atrás=30)

        metricas.append(MetricasProfissional(
            profissional=prof,
            atendimentos=atendimentos,
            ocupacao_percentual=ocupacao,
            faturamento_estimado=faturamento,
            cancelamentos_recebidos=cancelados,
            taxa_cancelamento=taxa_cancel,
            servicos_mais_realizados=servicos_top,
            dias_sem_agendamento=dias_sem,
        ))

    # Ordenar por atendimentos DESC
    metricas.sort(key=lambda x: x.atendimentos, reverse=True)

    return metricas


async def obter_metricas_clientes(tenant_id: str) -> MetricasCliente:
    """
    Retorna métricas sobre clientes.

    Args:
        tenant_id: ID do dono/salão

    Returns:
        MetricasCliente com análise de clientes
    """
    hoje = datetime.now(FUSO_BR).date()

    # Clientes novos (últimos 7 dias)
    inicio_7d = hoje - timedelta(days=7)
    agendamentos_7d = await _buscar_agendamentos_periodo(tenant_id, inicio_7d, hoje)
    clientes_novos = await _contar_clientes_novos(tenant_id, agendamentos_7d)

    # Clientes recorrentes (4+ agendamentos)
    clientes_recorrentes = await _contar_clientes_recorrentes(tenant_id, min_agendamentos=4)

    # Clientes sem retorno
    clientes_sem_retorno_30 = await _contar_clientes_inativos(tenant_id, dias=30)
    clientes_sem_retorno_60 = await _contar_clientes_inativos(tenant_id, dias=60)
    clientes_sem_retorno_90 = await _contar_clientes_inativos(tenant_id, dias=90)

    # Top clientes por frequência
    top_clientes = await _obter_top_clientes(tenant_id, limit=5)

    return MetricasCliente(
        clientes_novos_7_dias=clientes_novos,
        clientes_recorrentes=clientes_recorrentes,
        clientes_sem_retorno_30_dias=clientes_sem_retorno_30,
        clientes_sem_retorno_60_dias=clientes_sem_retorno_60,
        clientes_sem_retorno_90_dias=clientes_sem_retorno_90,
        top_clientes=top_clientes,
    )


async def obter_metricas_servicos(tenant_id: str) -> List[MetricasServico]:
    """
    Retorna ranking de serviços (últimos 30 dias).

    Args:
        tenant_id: ID do dono/salão

    Returns:
        Lista de MetricasServico ordenada por quantidade DESC
    """
    hoje = datetime.now(FUSO_BR).date()
    inicio = hoje - timedelta(days=30)

    agendamentos = await _buscar_agendamentos_periodo(tenant_id, inicio, hoje)

    if not agendamentos:
        return []

    # Agrupar por descrição (que funciona como serviço)
    por_servico: Dict[str, List[Dict]] = {}
    for ag in agendamentos:
        # Usar descricao como tipo de serviço
        servico = ag.get("descricao", "Agendamento")
        if servico not in por_servico:
            por_servico[servico] = []
        por_servico[servico].append(ag)

    metricas = []

    for servico, agenda_servico in por_servico.items():
        quantidade = len(agenda_servico)

        # Ticket médio (estimado por enquanto - preco não existe)
        ticket_medio = 100.0  # Valor padrão até que preco seja adicionado aos eventos

        # Duração média (usando campo "duracao" que existe)
        duracao_total = sum(ag.get("duracao", 0) for ag in agenda_servico)
        duracao_media_est = duracao_total // quantidade if quantidade > 0 else 0

        # Duração real (não temos esse campo atualmente)
        duracao_media_real = duracao_media_est  # Mesma estimativa

        # Taxa de complementares (campo "servicos" como lista não existe)
        # Por enquanto, retorna 0% até ter estrutura de múltiplos serviços
        taxa_complementares = 0.0

        metricas.append(MetricasServico(
            servico=servico,
            quantidade=quantidade,
            ticket_medio=ticket_medio,
            duracao_media_estimada=duracao_media_est,
            duracao_media_real=duracao_media_real,
            taxa_complementares=taxa_complementares,
        ))

    # Ordenar por quantidade DESC
    metricas.sort(key=lambda x: x.quantidade, reverse=True)

    return metricas


async def obter_alertas_operacionais(tenant_id: str) -> List[AlertaOperacional]:
    """
    Gera alertas baseado em anomalias operacionais.

    Args:
        tenant_id: ID do dono/salão

    Returns:
        Lista de AlertaOperacional ordenada por severidade
    """
    alertas = []

    # Alerta 1: Ocupação baixa
    resumo_semana = await obter_resumo_semana(tenant_id)
    if resumo_semana.taxa_ocupacao < 50:
        alertas.append(AlertaOperacional(
            tipo="ocupacao_baixa",
            severidade="warning",
            descricao=f"Ocupação semanal baixa ({resumo_semana.taxa_ocupacao:.0f}%)",
            acoes_sugeridas=[
                "Considerar promoção especial",
                "Entrar em contato com clientes inativos",
                "Revisar preços"
            ]
        ))

    # Alerta 2: Cancelamentos altos
    if resumo_semana.taxa_cancelamento > 15:
        alertas.append(AlertaOperacional(
            tipo="cancelamento_alto",
            severidade="critical",
            descricao=f"Taxa de cancelamento elevada ({resumo_semana.taxa_cancelamento:.0f}%)",
            acoes_sugeridas=[
                "Revisar feedback de clientes",
                "Verificar saúde das profissionais",
                "Implementar confirmação 24h antes"
            ]
        ))

    # Alerta 3: Profissional sem agendamentos
    profs = await obter_metricas_profissionais(tenant_id)
    for prof in profs:
        if prof.dias_sem_agendamento > 7:
            alertas.append(AlertaOperacional(
                tipo="profissional_sem_agenda",
                severidade="critical",
                descricao=f"Profissional '{prof.profissional}' sem agendamentos há {prof.dias_sem_agendamento} dias",
                acoes_sugeridas=[
                    f"Entrar em contato com {prof.profissional}",
                    "Verificar disponibilidade",
                    "Considerar redistribuição de clientes"
                ]
            ))

    # Alerta 4: Crescimento/queda anormal
    mudanca_demanda = await _calcular_mudanca_demanda(tenant_id)
    if mudanca_demanda < -20:  # Queda >20%
        alertas.append(AlertaOperacional(
            tipo="queda_demanda",
            severidade="critical",
            descricao=f"Queda de demanda de {abs(mudanca_demanda):.0f}% vs semana anterior",
            acoes_sugeridas=[
                "Investigar causas (profissional saiu? sazonalidade?)",
                "Revisar preços da concorrência",
                "Lançar campaign de reengajamento"
            ]
        ))
    elif mudanca_demanda > 30:  # Crescimento >30%
        alertas.append(AlertaOperacional(
            tipo="crescimento_demanda",
            severidade="warning",
            descricao=f"Crescimento forte de demanda ({mudanca_demanda:.0f}%)",
            acoes_sugeridas=[
                "Considerar expandir horário de atendimento",
                "Avaliar contratação de profissional temporária",
                "Otimizar agenda para máxima ocupação"
            ]
        ))

    # Ordenar por severidade (critical > warning > info)
    ordem = {"critical": 0, "warning": 1, "info": 2}
    alertas.sort(key=lambda x: ordem.get(x.severidade, 3))

    return alertas


async def obter_dashboard_completo(tenant_id: str) -> DashboardCompleto:
    """
    Retorna dashboard completo com todas as métricas.

    Args:
        tenant_id: ID do dono/salão

    Returns:
        DashboardCompleto com todas as informações
    """
    timestamp = datetime.now(FUSO_BR).isoformat()

    resumo_hoje = await obter_resumo_hoje(tenant_id)
    resumo_semana = await obter_resumo_semana(tenant_id)
    metricas_clientes = await obter_metricas_clientes(tenant_id)
    metricas_profissionais = await obter_metricas_profissionais(tenant_id)
    metricas_servicos = await obter_metricas_servicos(tenant_id)
    alertas = await obter_alertas_operacionais(tenant_id)

    return DashboardCompleto(
        timestamp=timestamp,
        resumo_hoje=resumo_hoje,
        resumo_semana=resumo_semana,
        metricas_clientes=metricas_clientes,
        metricas_profissionais=metricas_profissionais,
        metricas_servicos=metricas_servicos,
        alertas=alertas,
    )


# ============================================================================
# FUNÇÕES AUXILIARES PRIVADAS
# ============================================================================

async def _buscar_agendamentos_data(tenant_id: str, data: date) -> List[Dict[str, Any]]:
    """Busca eventos (agendamentos) de uma data específica.

    🔴 CORREÇÃO: buscar_subcolecao retorna DICT, não lista
    Path correto: `Eventos` (não `agendamentos`)
    """
    try:
        # Buscar eventos de um tenant (retorna dict {doc_id: data})
        eventos_dict = await buscar_subcolecao(
            f"Clientes/{tenant_id}/Eventos"
        ) or {}

        # Converter dict para lista de valores
        eventos = list(eventos_dict.values()) if isinstance(eventos_dict, dict) else []

        # Filtrar por data (comparar ISO format)
        data_iso = data.isoformat()
        return [ev for ev in eventos if ev.get("data") == data_iso]
    except Exception as e:
        logger.error(f"Erro ao buscar eventos do dia {data}: {e}")
        return []


async def _buscar_agendamentos_periodo(
    tenant_id: str,
    inicio: date,
    fim: date
) -> List[Dict[str, Any]]:
    """Busca eventos (agendamentos) de um período.

    🔴 CORREÇÃO: buscar_subcolecao retorna DICT, não lista
    Path correto: `Eventos` (não `agendamentos`)
    """
    try:
        # Buscar eventos de um tenant (retorna dict {doc_id: data})
        eventos_dict = await buscar_subcolecao(
            f"Clientes/{tenant_id}/Eventos"
        ) or {}

        # Converter dict para lista de valores
        eventos = list(eventos_dict.values()) if isinstance(eventos_dict, dict) else []

        # Filtrar por período (comparar strings ISO)
        inicio_iso = inicio.isoformat()
        fim_iso = fim.isoformat()

        return [
            ev for ev in eventos
            if inicio_iso <= ev.get("data", "") <= fim_iso
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar eventos do período {inicio}-{fim}: {e}")
        return []


async def _buscar_fila_espera_ativa(tenant_id: str) -> List[Dict[str, Any]]:
    """Busca clientes na fila de espera ativa."""
    try:
        fila = await buscar_subcolecao(
            f"Clientes/{tenant_id}/listaEspera"
        ) or []
        return [f for f in fila if f.get("status") == "ativo"]
    except Exception as e:
        logger.error(f"Erro ao buscar fila de espera: {e}")
        return []


async def _calcular_ticket_medio_profissional(
    tenant_id: str,
    profissional: str
) -> float:
    """Calcula ticket médio de uma profissional (simplificado).

    🔴 NOTA: Campo "preco" não existe na estrutura atual de eventos.
    Retorna valor estimado baseado em número de eventos concluídos.
    Para implementação real, seria necessário adicionar preço aos eventos.
    """
    try:
        hoje = datetime.now(FUSO_BR).date()
        inicio = hoje - timedelta(days=30)

        agendamentos = await _buscar_agendamentos_periodo(tenant_id, inicio, hoje)

        da_prof = [
            a for a in agendamentos
            if a.get("profissional") == profissional and a.get("status") == "concluido"
        ]

        if not da_prof:
            return 0.0

        # Por enquanto, retorna estimativa (100 reais por agendamento)
        # Isso deve ser ajustado quando eventos tiverem campo "preco"
        ticket_estimado = 100.0
        return ticket_estimado
    except Exception as e:
        logger.error(f"Erro ao calcular ticket médio: {e}")
        return 0.0


async def _contar_dias_sem_agendamento(
    tenant_id: str,
    profissional: str,
    dias_atrás: int = 30
) -> int:
    """Conta quantos dias a profissional ficou sem agendamentos."""
    try:
        hoje = datetime.now(FUSO_BR).date()
        inicio = hoje - timedelta(days=dias_atrás)

        agendamentos = await _buscar_agendamentos_periodo(tenant_id, inicio, hoje)
        da_prof = [a for a in agendamentos if a.get("profissional") == profissional]

        if not da_prof:
            return dias_atrás

        # Encontrar a data mais recente (converter string para date)
        datas = []
        for a in da_prof:
            data_str = a.get("data")
            if data_str:
                try:
                    # data_str é ISO format (YYYY-MM-DD)
                    data_obj = datetime.fromisoformat(data_str).date()
                    datas.append(data_obj)
                except (ValueError, TypeError):
                    pass

        if not datas:
            return dias_atrás

        ultima_data = max(datas)
        dias_desde = (hoje - ultima_data).days

        return dias_desde
    except Exception as e:
        logger.error(f"Erro ao contar dias sem agendamento: {e}")
        return 0


async def _contar_clientes_novos(
    tenant_id: str,
    agendamentos_recentes: List[Dict[str, Any]]
) -> int:
    """Conta clientes novos (primeiro agendamento).

    🔴 CORREÇÃO: buscar_subcolecao retorna DICT
    """
    try:
        clientes_novos = set()

        for ag in agendamentos_recentes:
            cliente_id = ag.get("cliente_id")
            if not cliente_id:
                continue

            # Verificar se tem outro agendamento antes
            todos_ag_dict = await buscar_subcolecao(
                f"Clientes/{tenant_id}/Eventos"
            ) or {}
            todos_ag = list(todos_ag_dict.values()) if isinstance(todos_ag_dict, dict) else []

            ag_cliente = [a for a in todos_ag if a.get("cliente_id") == cliente_id]

            if len(ag_cliente) == 1:  # Apenas este agendamento
                clientes_novos.add(cliente_id)

        return len(clientes_novos)
    except Exception as e:
        logger.error(f"Erro ao contar clientes novos: {e}")
        return 0


async def _contar_clientes_recorrentes(
    tenant_id: str,
    min_agendamentos: int = 4
) -> int:
    """Conta clientes recorrentes (N+ agendamentos)."""
    try:
        eventos_dict = await buscar_subcolecao(
            f"Clientes/{tenant_id}/Eventos"
        ) or {}
        agendamentos = list(eventos_dict.values()) if isinstance(eventos_dict, dict) else []

        clientes_dict: Dict[str, int] = {}

        for ag in agendamentos:
            cliente_id = ag.get("cliente_id")
            if cliente_id:
                clientes_dict[cliente_id] = clientes_dict.get(cliente_id, 0) + 1

        recorrentes = sum(1 for count in clientes_dict.values() if count >= min_agendamentos)

        return recorrentes
    except Exception as e:
        logger.error(f"Erro ao contar clientes recorrentes: {e}")
        return 0


async def _contar_clientes_inativos(tenant_id: str, dias: int) -> int:
    """Conta clientes sem agendamento há X dias."""
    try:
        hoje = datetime.now(FUSO_BR).date()
        data_limite = hoje - timedelta(days=dias)

        eventos_dict = await buscar_subcolecao(
            f"Clientes/{tenant_id}/Eventos"
        ) or {}
        agendamentos = list(eventos_dict.values()) if isinstance(eventos_dict, dict) else []

        # Filtrar clientes ativos (data >= data_limite)
        clientes_ativos_recentes = set()
        for a in agendamentos:
            cliente_id = a.get("cliente_id")
            data_str = a.get("data")
            if cliente_id and data_str:
                try:
                    data_obj = datetime.fromisoformat(data_str).date()
                    if data_obj >= data_limite:
                        clientes_ativos_recentes.add(cliente_id)
                except (ValueError, TypeError):
                    pass

        # Todos clientes (aproximado: clientes que já tiveram agendamento)
        todos_clientes = set(a.get("cliente_id") for a in agendamentos if a.get("cliente_id"))

        inativos = len(todos_clientes - clientes_ativos_recentes)

        return inativos
    except Exception as e:
        logger.error(f"Erro ao contar clientes inativos: {e}")
        return 0


async def _obter_top_clientes(
    tenant_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Retorna top N clientes por frequência."""
    try:
        eventos_dict = await buscar_subcolecao(
            f"Clientes/{tenant_id}/Eventos"
        ) or {}
        agendamentos = list(eventos_dict.values()) if isinstance(eventos_dict, dict) else []

        clientes_dict: Dict[str, Dict[str, Any]] = {}

        for ag in agendamentos:
            cliente_id = ag.get("cliente_id")
            cliente_nome = ag.get("cliente_nome", "Desconhecido")
            data = ag.get("data")

            if cliente_id not in clientes_dict:
                clientes_dict[cliente_id] = {
                    "id": cliente_id,
                    "nome": cliente_nome,
                    "frequencia": 0,
                    "ultima_visita": None
                }

            clientes_dict[cliente_id]["frequencia"] += 1

            if data:
                if not clientes_dict[cliente_id]["ultima_visita"] or data > clientes_dict[cliente_id]["ultima_visita"]:
                    clientes_dict[cliente_id]["ultima_visita"] = data

        # Ordenar por frequência DESC e pegar top N
        top = sorted(
            clientes_dict.values(),
            key=lambda x: x["frequencia"],
            reverse=True
        )[:limit]

        return top
    except Exception as e:
        logger.error(f"Erro ao obter top clientes: {e}")
        return []


async def _calcular_mudanca_demanda(tenant_id: str) -> float:
    """Calcula % de mudança de demanda entre semanas."""
    try:
        hoje = datetime.now(FUSO_BR).date()

        # Semana atual
        inicio_atual = hoje - timedelta(days=hoje.weekday())
        agendamentos_atual = await _buscar_agendamentos_periodo(
            tenant_id, inicio_atual, hoje
        )

        # Semana anterior
        inicio_anterior = inicio_atual - timedelta(days=7)
        fim_anterior = inicio_anterior + timedelta(days=6)
        agendamentos_anterior = await _buscar_agendamentos_periodo(
            tenant_id, inicio_anterior, fim_anterior
        )

        if not agendamentos_anterior:
            return 0.0

        mudanca = (len(agendamentos_atual) - len(agendamentos_anterior)) / len(agendamentos_anterior) * 100

        return mudanca
    except Exception as e:
        logger.error(f"Erro ao calcular mudança de demanda: {e}")
        return 0.0


# ============================================================================
# HELPERS PARA CONVERSÃO
# ============================================================================

def to_dict(dataclass_obj) -> Dict[str, Any]:
    """Converte dataclass para dict."""
    return asdict(dataclass_obj)
