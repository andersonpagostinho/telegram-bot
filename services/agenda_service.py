# services/agenda_service.py

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any

from services.firebase_service_async import buscar_dado_em_path

def _normalizar_data_iso(data_iso: str) -> str:
    """
    Garante YYYY-MM-DD.
    Aceita:
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    """
    if not data_iso:
        raise ValueError("data_iso vazio")

    if "T" in data_iso:
        return datetime.fromisoformat(data_iso).strftime("%Y-%m-%d")

    return datetime.fromisoformat(f"{data_iso}T00:00:00").strftime("%Y-%m-%d")


def _to_date(data_iso: str) -> date:
    return datetime.fromisoformat(f"{_normalizar_data_iso(data_iso)}T00:00:00").date()


def _hora_para_minutos(hora_str: str | None) -> int | None:
    if not hora_str:
        return None

    try:
        hh, mm = map(int, str(hora_str).split(":"))
        return hh * 60 + mm
    except Exception:
        return None


def horario_dentro_do_expediente(hora: str, inicio: str | None, fim: str | None) -> bool:
    """
    Retorna True se a hora estiver dentro do expediente.
    Considera faixa [inicio, fim), isto é:
    - 08:00 entra
    - 18:00 não entra se fim=18:00
    """
    h = _hora_para_minutos(hora)
    hi = _hora_para_minutos(inicio)
    hf = _hora_para_minutos(fim)

    if h is None or hi is None or hf is None:
        return False

    return hi <= h < hf


def intervalo_dentro_do_expediente(
    hora_inicio: str,
    duracao_min: int,
    inicio: str | None,
    fim: str | None
) -> bool:
    """
    Valida o intervalo inteiro, não só o horário inicial.
    """
    hi = _hora_para_minutos(hora_inicio)
    exp_ini = _hora_para_minutos(inicio)
    exp_fim = _hora_para_minutos(fim)

    if hi is None or exp_ini is None or exp_fim is None:
        return False

    hora_fim = hi + int(duracao_min or 0)

    return exp_ini <= hi and hora_fim <= exp_fim


async def obter_config_agenda(user_id: str) -> dict[str, Any]:
    """
    Busca configuração de agenda do tenant no caminho real do Firestore:
    Clientes/{user_id} -> configuracao -> agenda_funcionamento
    """
    path = f"Clientes/{user_id}"
    doc = await buscar_dado_em_path(path) or {}

    configuracao = doc.get("configuracao") or {}
    agenda_cfg = configuracao.get("agenda_funcionamento") or {}

    agenda_padrao = agenda_cfg.get("agenda_padrao") or {}
    excecoes_data = agenda_cfg.get("excecoes_data") or {}

    return {
        "agenda_padrao": agenda_padrao,
        "excecoes_data": excecoes_data,
    }

async def obter_regra_agenda_da_data(user_id: str, data_iso: str) -> dict[str, Any]:
    """
    Resolve a regra final da agenda para uma data específica.

    Prioridade:
    1. excecao por data
    2. agenda semanal padrao

    Retorno:
    {
      "aberto": bool,
      "inicio": "HH:MM" | None,
      "fim": "HH:MM" | None,
      "origem": "excecao" | "padrao" | "fallback" | "erro",
      "data": "YYYY-MM-DD",
      "weekday": 0..6
    }
    """
    try:
        cfg = await obter_config_agenda(user_id)
        agenda_padrao = cfg["agenda_padrao"]
        excecoes_data = cfg["excecoes_data"]

        data_str = _normalizar_data_iso(data_iso)
        dt = _to_date(data_str)
        weekday_str = str(dt.weekday())

        # 1) excecao da data tem prioridade maxima
        if data_str in excecoes_data:
            reg = excecoes_data.get(data_str) or {}
            return {
                "aberto": bool(reg.get("aberto", False)),
                "inicio": reg.get("inicio"),
                "fim": reg.get("fim"),
                "origem": "excecao",
                "data": data_str,
                "weekday": dt.weekday(),
            }

        # 2) agenda padrao semanal
        if weekday_str in agenda_padrao:
            reg = agenda_padrao.get(weekday_str) or {}
            return {
                "aberto": bool(reg.get("aberto", False)),
                "inicio": reg.get("inicio"),
                "fim": reg.get("fim"),
                "origem": "padrao",
                "data": data_str,
                "weekday": dt.weekday(),
            }

        # 3) fallback conservador
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "fallback",
            "data": data_str,
            "weekday": dt.weekday(),
        }

    except Exception as e:
        print(f"❌ [agenda_service] erro em obter_regra_agenda_da_data: {e}", flush=True)
        return {
            "aberto": False,
            "inicio": None,
            "fim": None,
            "origem": "erro",
            "data": None,
            "weekday": None,
        }


async def validar_data_funcionamento(user_id: str, data_iso: str) -> dict[str, Any]:
    """
    Valida se a data pode receber agendamento.
    """
    regra = await obter_regra_agenda_da_data(user_id, data_iso)

    if not regra.get("aberto"):
        return {
            "permitido": False,
            "motivo": "fechado_na_data",
            "regra": regra,
        }

    return {
        "permitido": True,
        "motivo": None,
        "regra": regra,
    }


async def validar_horario_funcionamento(
    user_id: str,
    data_iso: str,
    hora_inicio: str,
    duracao_min: int
) -> dict[str, Any]:
    """
    Valida se o horário e o intervalo cabem no expediente da data.
    """
    regra = await obter_regra_agenda_da_data(user_id, data_iso)

    print("🧪 AGENDA REGRA:", regra, flush=True)

    if not regra.get("aberto"):
        return {
            "permitido": False,
            "motivo": "fechado_na_data",
            "regra": regra,
        }

    inicio = regra.get("inicio")
    fim = regra.get("fim")

    if not intervalo_dentro_do_expediente(hora_inicio, duracao_min, inicio, fim):
        return {
            "permitido": False,
            "motivo": "fora_do_expediente",
            "regra": regra,
        }

    return {
        "permitido": True,
        "motivo": None,
        "regra": regra,
    }


async def proxima_data_permitida(
    user_id: str,
    data_iso: str,
    limite_dias: int = 30
) -> str | None:
    """
    Retorna a próxima data aberta, respeitando exceções e agenda semanal.
    """
    try:
        base = _to_date(data_iso)

        for i in range(1, limite_dias + 1):
            candidato = base + timedelta(days=i)
            data_str = candidato.strftime("%Y-%m-%d")

            validacao = await validar_data_funcionamento(user_id, data_str)
            if validacao.get("permitido"):
                return data_str

        return None

    except Exception as e:
        print(f"❌ [agenda_service] erro em proxima_data_permitida: {e}", flush=True)
        return None


async def proximo_horario_valido_no_dia(
    user_id: str,
    data_iso: str,
    duracao_min: int,
    grade_minutos: int = 10
) -> str | None:
    """
    Procura o primeiro horário válido dentro do expediente.
    Não verifica conflito com eventos; só expediente.
    """
    try:
        regra = await obter_regra_agenda_da_data(user_id, data_iso)
        if not regra.get("aberto"):
            return None

        inicio = regra.get("inicio")
        fim = regra.get("fim")

        min_ini = _hora_para_minutos(inicio)
        min_fim = _hora_para_minutos(fim)

        if min_ini is None or min_fim is None:
            return None

        atual = min_ini
        while atual + duracao_min <= min_fim:
            hh = atual // 60
            mm = atual % 60
            hora = f"{hh:02d}:{mm:02d}"

            if intervalo_dentro_do_expediente(hora, duracao_min, inicio, fim):
                return hora

            atual += grade_minutos

        return None

    except Exception as e:
        print(f"❌ [agenda_service] erro em proximo_horario_valido_no_dia: {e}", flush=True)
        return None