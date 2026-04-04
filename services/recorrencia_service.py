# services/recorrencia_service.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, time, date
from typing import Dict, List, Tuple, Optional

import unidecode

from services.firebase_service_async import (
    buscar_subcolecao,
    salvar_dado_em_path,
)
from services.event_service_async import (
    buscar_eventos_por_intervalo,
    verificar_conflito_e_sugestoes_profissional,
)
from utils.gpt_utils import estimar_duracao

logger = logging.getLogger(__name__)

# ----- Parâmetros de negócio -----
_CADENCIA_MIN = 10          # mínimo de dias aceitável pra considerar recorrência
_CADENCIA_MAX = 35          # máximo de dias aceitável
_MIN_OCORRENCIAS = 3        # precisa de pelo menos 3 atendimentos desse serviço
_DIAS_APOS_ULTIMO_PARA_AVISAR = 5  # envia proposta 5 dias após o último
_HORARIOS_PADRAO = [time(10, 0), time(14, 0), time(16, 0)]
_JANELA_BUSCA_INICIO = time(9, 0)
_JANELA_BUSCA_FIM = time(18, 0)
_PASSO_MINUTOS = 30

# ------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------

def _parse_dt(data_str: str, hora_str: str) -> Optional[datetime]:
    """Converte 'YYYY-MM-DD' + 'HH:MM' em datetime naive (local)."""
    try:
        return datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M")
    except Exception:
        return None

def _intervalos_em_dias(ordenadas: List[datetime]) -> List[int]:
    dias = []
    for i in range(1, len(ordenadas)):
        delta = (ordenadas[i] - ordenadas[i-1]).days
        dias.append(delta)
    return dias

def _mediana(valores: List[int]) -> Optional[float]:
    if not valores:
        return None
    s = sorted(valores)
    n = len(s)
    m = n // 2
    if n % 2 == 1:
        return float(s[m])
    return (s[m-1] + s[m]) / 2.0

def _normalizar_servico(descricao: str) -> str:
    """Tenta extrair um 'serviço' da descrição livre, de maneira simples."""
    d = unidecode.unidecode((descricao or "").lower()).strip()
    # heurística simples: pega primeira palavra/frase curta
    # (você pode adaptar para mapear com seus serviços cadastrados)
    return d

async def _tem_conflito_profissional(
    user_id: str,
    data_alvo_str: str,      # "YYYY-MM-DD"
    hora_inicio_str: str,    # "HH:MM"
    duracao_min: int,
    profissional: Optional[str],
    servico: Optional[str],
) -> bool:
    """
    Usa seu verificador oficial p/ checar conflito do profissional.
    Se não houver profissional, considera que não há conflito específico de profissional.
    """
    if not profissional:
        return False  # sem profissional específico, não bloqueia por aqui

    try:
        info = await verificar_conflito_e_sugestoes_profissional(
            user_id=user_id,
            data=data_alvo_str,
            hora_inicio=hora_inicio_str,
            duracao_min=duracao_min,
            profissional=profissional,
            servico=servico or ""
        )
        return bool(info.get("conflito"))
    except Exception as e:
        logger.error(f"[recorrencia] erro ao checar conflito do profissional: {e}")
        # conservador: considera conflito em caso de erro
        return True

# ------------------------------------------------------------
# Núcleo: gerar 3 horários realmente livres
# ------------------------------------------------------------

async def _gerar_3_horarios_livres(
    user_id: str,
    data_sugerida: date,
    servico_chave: Optional[str] = None,
    profissional: Optional[str] = None,
    duracao_min: Optional[int] = None
) -> List[str]:
    """
    Retorna 3 horários realmente livres no dia (sem conflito com agenda global)
    e, se houver PROFISSIONAL, sem conflito do PROFISSIONAL também.

    Estratégia:
      - Tenta horários base: 10:00, 14:00, 16:00
      - Se não achar, varre 09:00→18:00 em passos de 30 min
    """
    # 1) duração do serviço (fallback 60)
    if duracao_min is None:
        try:
            duracao_min = estimar_duracao(servico_chave or "") or 60
        except Exception:
            duracao_min = 60

    # 2) eventos do dia para checar conflito geral (independente de profissional)
    eventos_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=data_sugerida) or []
    ocupados: List[Tuple[datetime, datetime]] = []
    for ev in eventos_dia:
        try:
            ini = _parse_dt(ev["data"], ev["hora_inicio"])
            fim = _parse_dt(ev["data"], ev["hora_fim"])
            if ini and fim and fim > ini:
                ocupados.append((ini, fim))
        except Exception:
            continue

    def _livre_global(dt_ini: datetime) -> bool:
        dt_fim = dt_ini + timedelta(minutes=duracao_min)
        for i, f in ocupados:
            if not (dt_fim <= i or dt_ini >= f):
                return False
        return True

    def _fmt(dt: datetime) -> Tuple[str, str]:
        return (dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"))

    livres: List[str] = []

    # 3) checa candidatos padrão primeiro
    for t in _HORARIOS_PADRAO:
        dt_ini = datetime.combine(data_sugerida, t)
        if not _livre_global(dt_ini):
            continue
        data_str, hora_str = _fmt(dt_ini)
        conflito_prof = await _tem_conflito_profissional(
            user_id, data_str, hora_str, duracao_min, profissional, servico_chave
        )
        if not conflito_prof:
            livres.append(hora_str)
        if len(livres) == 3:
            return livres

    # 4) fallback: varredura 09:00→18:00 de 30 em 30 min
    start_scan = datetime.combine(data_sugerida, _JANELA_BUSCA_INICIO)
    end_scan = datetime.combine(data_sugerida, _JANELA_BUSCA_FIM)
    cursor = start_scan
    seen = set(livres)

    while cursor <= end_scan and len(livres) < 3:
        h = cursor.strftime("%H:%M")
        if h not in seen:
            if _livre_global(cursor):
                data_str, hora_str = _fmt(cursor)
                conflito_prof = await _tem_conflito_profissional(
                    user_id, data_str, hora_str, duracao_min, profissional, servico_chave
                )
                if not conflito_prof:
                    livres.append(hora_str)
            seen.add(h)
        cursor += timedelta(minutes=_PASSO_MINUTOS)

    return livres[:3]

# ------------------------------------------------------------
# Descoberta de padrão (cadência)
# ------------------------------------------------------------

async def _descobrir_cadencia(
    user_id: str,
    cliente_id: str,
    chave_servico: str
) -> Optional[int]:
    """
    Lê o histórico do cliente + serviço, calcula intervalos em dias e retorna
    uma cadência (mediana) se estiver entre [_CADENCIA_MIN, _CADENCIA_MAX]
    e se houver ocorrências suficientes.
    """
    # Busca TODOS os eventos (você pode otimizar p/ 180 dias, etc.)
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
    # filtra por cliente_id e serviço
    ocorrencias: List[datetime] = []
    chave_norm = unidecode.unidecode(chave_servico.lower())

    for _id, ev in eventos.items():
        if not isinstance(ev, dict):
            continue
        if str(ev.get("cliente_id") or "").strip() != str(cliente_id).strip():
            continue
        desc = _normalizar_servico(ev.get("descricao", ""))
        if chave_norm not in desc:
            continue

        dt = _parse_dt(ev.get("data", ""), ev.get("hora_inicio", ""))
        if dt:
            ocorrencias.append(dt)

    if len(ocorrencias) < _MIN_OCORRENCIAS:
        return None

    ocorrencias.sort()
    deltas = _intervalos_em_dias(ocorrencias)
    if not deltas:
        return None

    med = _mediana(deltas)
    if med is None:
        return None

    if _CADENCIA_MIN <= med <= _CADENCIA_MAX:
        return int(round(med))
    return None

# ------------------------------------------------------------
# Orquestração: checar e propor recorrência
# ------------------------------------------------------------

async def checar_e_propor_recorrencias(user_id: str) -> int:
    """
    Para UM negócio (user_id do dono), identifica clientes com padrão de recorrência
    e envia proposta com 3 horários livres para a PRÓXIMA data (cadência),
    disparando 5 dias após o último atendimento.

    Retorna quantas propostas foram geradas.
    """
    propostas = 0

    # 1) pega todos os eventos do negócio para inferir (cliente, serviço, profissional)
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
    # index por (cliente_id, serviço_normalizado) -> lista de dt
    por_cliente_serv: Dict[Tuple[str, str], List[dict]] = {}

    for _id, ev in eventos.items():
        if not isinstance(ev, dict):
            continue
        cliente_id = str(ev.get("cliente_id") or "").strip()
        if not cliente_id:
            continue
        desc = _normalizar_servico(ev.get("descricao", ""))
        if not desc:
            continue

        chave = (cliente_id, desc)
        por_cliente_serv.setdefault(chave, []).append(ev)

    agora = datetime.now()
    # 2) para cada par (cliente, serviço), checa padrão e se precisa enviar agora
    for (cliente_id, servico_chave), lst in por_cliente_serv.items():
        # ordena por data
        ocorr: List[datetime] = []
        lst_ordenada = []
        for ev in lst:
            dt = _parse_dt(ev.get("data", ""), ev.get("hora_inicio", ""))
            if dt:
                ocorr.append(dt)
                lst_ordenada.append((dt, ev))

        if len(ocorr) < _MIN_OCORRENCIAS:
            continue

        ocorr.sort()
        lst_ordenada.sort(key=lambda x: x[0])
        ultimo_dt, ultimo_ev = lst_ordenada[-1]

        cadencia = await _descobrir_cadencia(user_id, cliente_id, servico_chave)
        if not cadencia:
            continue

        # só dispara se já passaram 5 dias do ÚLTIMO atendimento
        if (agora - ultimo_dt) < timedelta(days=_DIAS_APOS_ULTIMO_PARA_AVISAR):
            continue

        # data alvo = último + cadência
        data_alvo = (ultimo_dt + timedelta(days=cadencia)).date()
        profissional = (ultimo_ev.get("profissional") or "").strip() or None
        duracao = None
        try:
            duracao = estimar_duracao(servico_chave or "") or 60
        except Exception:
            duracao = 60

        horarios = await _gerar_3_horarios_livres(
            user_id=user_id,
            data_sugerida=data_alvo,
            servico_chave=servico_chave,
            profissional=profissional,
            duracao_min=duracao
        )

        if not horarios:
            logger.info(f"[recorrencia] Sem horários livres para {cliente_id} em {data_alvo}")
            continue

        # monta mensagem clara
        servico_txt = servico_chave or "seu atendimento"
        prof_txt = f" com *{profissional}*" if profissional else ""
        msg = (
            "Olá! 👋\n\n"
            f"Notei que você costuma fazer *{servico_txt}*{prof_txt} a cada ~{cadencia} dias. "
            "Que tal já deixar o próximo marcado?\n\n"
            f"📅 Sugestão: *{data_alvo.strftime('%d/%m/%Y')}*\n"
            f"⏰ Horários disponíveis: {', '.join(horarios)}\n\n"
            "Responda com o horário preferido que eu confirmo pra você. 🙂"
        )

        # cria notificação IMEDIATA para o CLIENTE (data_hora = agora)
        try:
            notif = {
                "descricao": f"Proposta de {servico_txt}",
                "mensagem": msg,
                "canal": "telegram",
                "data_hora": agora.isoformat(),     # envia já
                "avisado": False,
                "status": "pendente",
                "criado_em": agora.isoformat(),
                "alvo_evento": {
                    "data": data_alvo.isoformat(),
                    "hora_inicio": horarios[0],
                    "profissional": profissional
                },
                "minutos_antes": 0,
                "destinatario": str(cliente_id),
                "origem_user": str(user_id),
                "tipo": "proposta_recorrencia",
            }
            from uuid import uuid4
            notif_id = str(uuid4())
            await salvar_dado_em_path(
                f"Clientes/{cliente_id}/NotificacoesAgendadas/{notif_id}",
                notif
            )
            propostas += 1
            logger.info(f"[recorrencia] Proposta enviada para cliente {cliente_id} (notif {notif_id}).")
        except Exception as e:
            logger.error(f"[recorrencia] Erro ao salvar notificação de proposta: {e}")

    return propostas

# ------------------------------------------------------------
# Conveniência: rodar para TODOS os negócios
# (pode ser chamado por um scheduler diário)
# ------------------------------------------------------------

async def checar_e_propor_recorrencias_todos() -> int:
    """
    Itera por TODOS os clientes (negócios) e dispara checagem de recorrência.
    Retorna total de propostas geradas.
    """
    total = 0
    try:
        clientes = await buscar_subcolecao("Clientes") or {}
        for user_id in clientes.keys():
            try:
                total += await checar_e_propor_recorrencias(user_id)
            except Exception as e:
                logger.error(f"[recorrencia] Falha ao processar user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"[recorrencia] Erro ao listar Clientes: {e}")
    return total
