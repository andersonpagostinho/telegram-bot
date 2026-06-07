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

def _tem_indicio_temporal(texto: str) -> bool:
    """
    Só permite interpretar data/hora quando houver pista explícita no texto.
    Evita casos como 'quero corte' virar 'agora'.
    """
    if not texto:
        return False

    t = _normalizar_texto_hora(texto.strip().lower().replace("às", "as"))

    # hora explícita: 10, 10:30, as 10, 15h, 15h20
    if re.search(r"\b(?:as\s*)?([01]?\d|2[0-3])(?::([0-5]\d))?\b", t):
        return True

    pistas = [
        "hoje", "amanha", "amanhã",
        "segunda", "terca", "terça", "quarta", "quinta", "sexta",
        "sabado", "sábado", "domingo",
        "dia ",
        "semana",
        "mes", "mês",
        "janeiro", "fevereiro", "marco", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]

    return any(p in t for p in pistas)


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

def extrair_trecho_temporal(texto: str) -> str:
    """
    Tenta reduzir uma frase longa ao pedaço temporal relevante.
    Exemplos:
    - 'Nossa, amanhã tenho reunião...' -> 'amanhã'
    - 'na quinta às 10 eu consigo' -> 'quinta às 10'
    - 'dia 06 de maio de manhã' -> 'dia 06 de maio'
    """
    if not texto:
        return ""

    t = texto.strip().lower()

    padroes = [
        r"\b(depois de amanhã(?:\s+(?:às|as)?\s*\d{1,2}(?::\d{2})?(?:\s*ou\s*\d{1,2}(?::\d{2})?)*)?)\b",

        r"\b(amanhã(?:\s+(?:às|as)?\s*\d{1,2}(?::\d{2})?(?:\s*ou\s*\d{1,2}(?::\d{2})?)*)?)\b",

        r"\b(amanha(?:\s+(?:às|as)?\s*\d{1,2}(?::\d{2})?(?:\s*ou\s*\d{1,2}(?::\d{2})?)*)?)\b",

        r"\b(hoje(?:\s+(?:às|as)?\s*\d{1,2}(?::\d{2})?(?:\s*ou\s*\d{1,2}(?::\d{2})?)*)?)\b",
        r"\b(segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)(?:\s*(?:às|as)?\s*\d{1,2}(?::\d{2})?)?\b",
        r"\b(dia\s+\d{1,2}(?:\s+de\s+\w+)?(?:\s+(?:às|as)\s+\d{1,2}(?::\d{2})?)?)\b",
        r"\b((?:às|as)\s+\d{1,2}(?::\d{2})?)\b",
    ]

    for padrao in padroes:
        m = re.search(padrao, t, re.IGNORECASE)
        if m:
            return m.group(1)

    return t

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

        # 🧪 PATCH MÍNIMO: preservar texto completo para GPT
        # Heurísticas usam texto_norm, fallback usa dateparser
        texto_norm = texto_original.strip().lower().replace("às", "as")
        texto_norm = _normalizar_texto_hora(texto_norm)

        # ✅ Se não houver qualquer pista temporal explícita, não interpreta nada
        if not _tem_indicio_temporal(texto_norm):
            return None

        # ✅ Se tiver "hoje" ou "amanhã" e tiver hora, monta a data manualmente
        if ("hoje" in texto_norm or "amanh" in texto_norm) and re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm):
            base = agora_br_aware()
            if "amanh" in texto_norm:
                base = base + timedelta(days=1)

            m = re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm)
            hora = int(m.group(1))
            minuto = int(m.group(2) or 0)

            dt_aware = FUSO_BR.localize(datetime(base.year, base.month, base.day, hora, minuto, 0, 0))
            result = dt_aware.astimezone(FUSO_BR).replace(tzinfo=None)
            print(f"🧪 [PARSER] fonte_parse=manual_hoje_amanha | resultado={result}", flush=True)
            return result

        # ✅ Detecta dia da semana isolado ou com hora, ex:
        # "quinta", "quinta feira", "na quinta", "quinta às 10"
        dias_semana = {
            "segunda": 0,
            "terca": 1,
            "terça": 1,
            "quarta": 2,
            "quinta": 3,
            "sexta": 4,
            "sabado": 5,
            "sábado": 5,
            "domingo": 6,
        }

        dia_semana_detectado = None
        for nome, idx in dias_semana.items():
            if re.search(rf"\b{nome}\b", texto_norm):
                dia_semana_detectado = idx
                break

        if dia_semana_detectado is not None:
            base = agora_br_aware()

            dias_ate = (dia_semana_detectado - base.weekday()) % 7
            if dias_ate == 0:
                dias_ate = 7  # sempre próxima ocorrência

            alvo = base + timedelta(days=dias_ate)

            m_hora = re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm)
            hora = int(m_hora.group(1)) if m_hora else 9
            minuto = int(m_hora.group(2) or 0) if m_hora else 0

            dt_aware = FUSO_BR.localize(
                datetime(alvo.year, alvo.month, alvo.day, hora, minuto, 0, 0)
            )
            result = dt_aware.astimezone(FUSO_BR).replace(tzinfo=None)
            print(f"🧪 [PARSER] fonte_parse=manual_dia_semana | resultado={result}", flush=True)
            return result

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
            result = dt_aware.astimezone(FUSO_BR).replace(tzinfo=None)
            print(f"🧪 [PARSER] fonte_parse=manual_dia_mes | resultado={result}", flush=True)
            return result

        # ✅ Caso geral: dateparser com base BR
        # 🧪 PATCH MÍNIMO: tentar texto completo primeiro

        settings_parse = {
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": base_aware,  # ponto crítico (evita UTC)
            "TIMEZONE": "America/Sao_Paulo",
            "RETURN_AS_TIMEZONE_AWARE": False,
            "DATE_ORDER": "DMY",
        }

        # Tentar com texto_original primeiro (preserva slots para GPT)
        parsed_original = dateparser.parse(
            texto_original,
            languages=["pt"],
            settings=settings_parse,
        )

        parsed = parsed_original
        fonte_parse = "original"

        # Fallback: se falhar, tentar com texto_reduzido
        if parsed is None:
            texto_reduzido = extrair_trecho_temporal(texto_original)

            # 🔒 P0: Se é só hora (ex: "às 10"), não tentar dateparser (evita interpretar como dia)
            if _so_hora(texto_reduzido):
                parsed_reduzido = None
                fonte_parse = "reduzido_so_hora_bloqueado"
            else:
                parsed_reduzido = dateparser.parse(
                    texto_reduzido,
                    languages=["pt"],
                    settings=settings_parse,
                )
                fonte_parse = "reduzido" if parsed_reduzido else None

            parsed = parsed_reduzido
        else:
            texto_reduzido = extrair_trecho_temporal(texto_original)
            parsed_reduzido = None

        # 🧪 Logs comparativos
        print(f"🧪 [PARSER] texto_original={texto_original!r}", flush=True)
        print(f"🧪 [PARSER] texto_reduzido={texto_reduzido!r}", flush=True)
        print(f"🧪 [PARSER] parsed_original={parsed_original}", flush=True)
        print(f"🧪 [PARSER] parsed_reduzido={parsed_reduzido}", flush=True)
        print(f"🧪 [PARSER] fonte_parse={fonte_parse}", flush=True)

        if isinstance(parsed, datetime):
            return parsed

        return parsed

    except Exception as e:
        print(f"[interpretar_data_e_hora] Erro: {e}")
        return None

def detectar_bloqueio_agenda_salao(texto: str) -> dict | None:
    texto_lower = (texto or "").lower()

    # 🔥 gatilho simples e direto (P0)
    gatilhos = [
        "não abriremos",
        "nao abriremos",
        "vamos fechar",
        "ficaremos fechados",
        "fechar o salão",
        "fechar agenda",
        "bloquear agenda",
    ]

    if not any(g in texto_lower for g in gatilhos):
        return None

    datas = []

    # =========================================================
    # 1) tenta usar o parser que você JÁ TEM
    # =========================================================
    dt = interpretar_data_e_hora(texto)
    if dt:
        datas.append(dt.strftime("%Y-%m-%d"))

    # =========================================================
    # 2) múltiplos dias (ex: "20 e 21")
    # =========================================================
    matches = re.findall(r"\b(\d{1,2})\b", texto_lower)
    if len(matches) > 1:
        hoje = datetime.now()
        for d in matches:
            try:
                dia = int(d)
                data = datetime(hoje.year, hoje.month, dia)
                datas.append(data.strftime("%Y-%m-%d"))
            except:
                pass

    # =========================================================
    # 3) duração (ex: "por 2 dias")
    # =========================================================
    m = re.search(r"por\s+(\d+)\s+dia", texto_lower)
    if m:
        qtd = int(m.group(1))
        hoje = datetime.now()

        datas = [
            (hoje + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(qtd)
        ]

    # remove duplicadas
    datas = sorted(set(datas))

    if not datas:
        return None

    return {
        "acao": "bloquear_agenda_salao",
        "dados": {
            "datas": datas,
            "motivo": "fechado"
        }
    }