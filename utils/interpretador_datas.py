import dateparser
import re
from datetime import datetime, timedelta
import pytz

# Fuso padrão do usuário/sistema
FUSO_BR = pytz.timezone("America/Sao_Paulo")


def agora_br_aware() -> datetime:
    """Datetime timezone-aware no fuso do Brasil."""
    return datetime.now(FUSO_BR)


def agora_br_naive() -> datetime:
    """Datetime naive, porém representando o horário do Brasil."""
    return agora_br_aware().replace(tzinfo=None)


def _normalizar_texto_hora(texto: str) -> str:
    """
    Normaliza formatos comuns:
      - "15h20" -> "15:20"
      - "15h"   -> "15:00"
      - "15 hrs" / "15 horas" -> "15h"
    Sem quebrar "15:20".
    """
    if not texto:
        return texto

    t = texto.lower()

    # normaliza palavras
    t = t.replace("hrs", "h").replace("horas", "h")

    # "15h20" -> "15:20"
    t = re.sub(r"\b(\d{1,2})h(\d{2})\b", r"\1:\2", t)

    # "15 h" ou "15h" -> "15:00" (somente quando NÃO tem minutos)
    t = re.sub(r"\b(\d{1,2})\s*h\b", r"\1:00", t)

    return t


def _so_hora(texto: str) -> bool:
    """
    Detecta se o texto é "só hora", ex:
      - "15"
      - "15:20"
      - "às 15"
      - "as 15:20"
      - "15h" / "15h20"
    """
    if not texto:
        return False
    t = _normalizar_texto_hora(texto.strip().lower().replace("às", "as"))
    return bool(re.match(r"^(?:as\s*)?\d{1,2}(?::\d{2})?$", t))


def interpretar_intervalo_de_datas(texto):
    texto = (texto or "").lower()
    hoje = agora_br_aware().date()

    # Semana que vem
    if "semana que vem" in texto or "próxima semana" in texto or "proxima semana" in texto:
        # próxima segunda
        inicio = hoje + timedelta(days=(7 - hoje.weekday()))
        fim = inicio + timedelta(days=6)
        return inicio, fim

    # Essa semana
    if "essa semana" in texto or "esta semana" in texto:
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
        return inicio, fim

    # Intervalo do tipo "entre os dias 12 e 17 de maio"
    match_intervalo = re.search(r"entre os dias (\d{1,2}) e (\d{1,2})(?: de (\w+))?", texto)
    if match_intervalo:
        dia1 = int(match_intervalo.group(1))
        dia2 = int(match_intervalo.group(2))
        mes_nome = match_intervalo.group(3)

        ano = hoje.year
        mes = hoje.month

        if mes_nome:
            dt = dateparser.parse(f"1 {mes_nome}", languages=["pt"])
            if dt:
                mes = dt.month

        try:
            inicio = datetime(ano, mes, dia1).date()
            fim = datetime(ano, mes, dia2).date()
            return inicio, fim
        except Exception:
            pass

    # "semana do dia 12"
    match_semana_do_dia = re.search(r"semana do dia (\d{1,2})", texto)
    if match_semana_do_dia:
        dia = int(match_semana_do_dia.group(1))
        try:
            ref_data = hoje.replace(day=dia)
            inicio = ref_data - timedelta(days=ref_data.weekday())
            fim = inicio + timedelta(days=6)
            return inicio, fim
        except Exception:
            pass

    # Último recurso: retorna semana atual
    inicio = hoje - timedelta(days=hoje.weekday())
    fim = inicio + timedelta(days=6)
    return inicio, fim


def interpretar_e_salvar_data_hora(texto: str) -> datetime | None:
    """
    Interpreta expressões de data e hora a partir de um texto natural.
    Retorna um datetime completo se possível, ou None se não conseguiu interpretar.

    Observação importante:
    - Se o usuário mandar apenas uma hora ("15:20"), esta função NÃO deve inventar a data.
      (A data deve vir da sessão/contexto do seu fluxo.)
    """
    if not texto:
        return None

    texto_formatado = (texto or "").strip().lower().replace("às", "as")
    texto_formatado = _normalizar_texto_hora(texto_formatado)

    # ✅ Evita inferir data quando for "só hora"
    if _so_hora(texto_formatado):
        return None

    # Base correta (Brasil), evitando UTC no Render
    base = agora_br_aware()

    settings = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": base,
        "RETURN_AS_TIMEZONE_AWARE": False,
        "DATE_ORDER": "DMY",
        "PARSERS": ["relative-time", "custom-formats"],
        "TIMEZONE": "America/Sao_Paulo",
    }

    data_hora_interpretada = dateparser.parse(texto_formatado, settings=settings)

    if isinstance(data_hora_interpretada, datetime):
        # ✅ Certifica que tem hora válida
        if data_hora_interpretada.hour != 0 or data_hora_interpretada.minute != 0:
            return data_hora_interpretada

    return None


def interpretar_data_e_hora(texto: str) -> datetime | None:
    """
    Interpreta data+hora.
    - Se vier apenas hora ("15:20"), retorna None (porque não deve assumir o dia).
    - Se vier "dia X ..." monta manualmente.
    - Caso geral: usa dateparser com RELATIVE_BASE no fuso BR.
    """
    if not texto:
        return None

    try:
        texto_original = texto
        texto_norm = (texto or "").strip().lower().replace("às", "as")
        texto_norm = _normalizar_texto_hora(texto_norm)

        # ✅ Se tiver "hoje" ou "amanhã" e tiver hora, monta a data manualmente
        if ("hoje" in texto_norm or "amanh" in texto_norm) and re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm):
            base = agora_br_aware()
            if "amanh" in texto_norm:
                base = base + timedelta(days=1)

            m = re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm)
            hora = int(m.group(1))
            minuto = int(m.group(2) or 0)

            dt_aware = FUSO_BR.localize(datetime(base.year, base.month, base.day, hora, minuto, 0, 0))
            return dt_aware.astimezone(FUSO_BR).replace(tzinfo=None)

        # ✅ Se for só hora, não decide data aqui (isso é do fluxo/sessão)
        if _so_hora(texto_norm):
            return None

        # Base correta (Brasil), evitando UTC no Render
        base_aware = agora_br_aware()

        # ✅ Detecta "dia 5 (de março) as 10:30" e monta manualmente
        # Obs: aceita também sem hora (default 09:00)
        match = re.search(
            r"dia\s+(\d{1,2})(?:\s+de\s+(\w+))?(?:\s+(?:as)\s+(\d{1,2})(?::(\d{2}))?)?",
            texto_norm,
        )
        if match:
            dia = int(match.group(1))
            mes_nome = match.group(2)
            hora = int(match.group(3)) if match.group(3) else 9
            minuto = int(match.group(4)) if match.group(4) else 0

            mes = base_aware.month
            ano = base_aware.year

            if mes_nome:
                mes_parse = dateparser.parse(f"1 {mes_nome}", languages=["pt"])
                if mes_parse:
                    mes = mes_parse.month

            # Se a data "dia X" já passou no mês atual, joga pro próximo mês
            if mes == base_aware.month and dia < base_aware.day:
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1

            dt_aware = FUSO_BR.localize(datetime(ano, mes, dia, hora, minuto, 0, 0))
            return dt_aware.astimezone(FUSO_BR).replace(tzinfo=None)

        # ✅ Caso geral: dateparser com base BR
        parsed = dateparser.parse(
            texto_original,
            languages=["pt"],
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": base_aware,  # ponto crítico (evita UTC)
                "TIMEZONE": "America/Sao_Paulo",
                "RETURN_AS_TIMEZONE_AWARE": False,
                "DATE_ORDER": "DMY",
            },
        )

        if isinstance(parsed, datetime):
            return parsed

        return parsed

    except Exception as e:
        print(f"[interpretar_data_e_hora] Erro: {e}")
        return None