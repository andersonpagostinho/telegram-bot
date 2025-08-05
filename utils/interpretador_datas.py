import dateparser
import re
from datetime import datetime, timedelta

def interpretar_intervalo_de_datas(texto):
    texto = texto.lower()
    hoje = datetime.now().date()

    # Semana que vem
    if "semana que vem" in texto or "próxima semana" in texto or "proxima semana" in texto:
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
        except:
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
        except:
            pass

    # Último recurso: retorna semana atual
    inicio = hoje - timedelta(days=hoje.weekday())
    fim = inicio + timedelta(days=6)
    return inicio, fim

def interpretar_e_salvar_data_hora(texto: str) -> datetime | None:
    """
    Interpreta expressões de data e hora a partir de um texto natural.
    Retorna um datetime completo se possível, ou None se não conseguiu interpretar.
    """

    # 🧠 Usa o dateparser para entender expressões como "amanhã às 10h"
    settings = {
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': datetime.now(),
        'RETURN_AS_TIMEZONE_AWARE': False,
        'DATE_ORDER': 'DMY',
        'PARSERS': ['relative-time', 'custom-formats'],
        'TIMEZONE': 'America/Sao_Paulo'
    }

    texto_formatado = texto.strip().lower().replace("às", "as")  # normaliza "às"
    data_hora_interpretada = dateparser.parse(texto_formatado, settings=settings)

    if isinstance(data_hora_interpretada, datetime):
        # ✅ Certifica que tem hora válida
        if data_hora_interpretada.hour != 0 or data_hora_interpretada.minute != 0:
            return data_hora_interpretada

    return None

def interpretar_data_e_hora(texto: str) -> datetime | None:
    if not texto:
        return None

    try:
        texto_original = texto
        texto = texto.lower()
        hoje = datetime.now()

        # 🧠 Substitui padrões ambíguos antes da análise
        texto = texto.replace("hrs", "h").replace("horas", "h")
        texto = re.sub(r"(\d{1,2}) ?h", r"\1:00", texto)

        # 🧠 Detecta "dia 5 às 10" e completa a data
        match = re.search(r"dia (\d{1,2})(?: de (\w+))?(?: (?:às|as) (\d{1,2})(?::(\d{2}))?)?", texto)
        if match:
            dia = int(match.group(1))
            mes_nome = match.group(2)
            hora = int(match.group(3)) if match.group(3) else 9
            minuto = int(match.group(4)) if match.group(4) else 0

            mes = hoje.month
            ano = hoje.year

            if mes_nome:
                mes_parse = dateparser.parse(f"1 {mes_nome}", languages=["pt"])
                if mes_parse:
                    mes = mes_parse.month

            if dia < hoje.day and mes == hoje.month:
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1

            from pytz import timezone
            fuso = timezone("America/Sao_Paulo")
            data_localizada = fuso.localize(datetime(ano, mes, dia, hora, minuto))
            data_local_naive = data_localizada.astimezone(fuso).replace(tzinfo=None)
            return data_local_naive

        # Se não caiu em nenhuma lógica especial, usa o dateparser normal
        return dateparser.parse(
            texto_original,
            languages=["pt"],
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": hoje,
                "TIMEZONE": "America/Sao_Paulo",
                "RETURN_AS_TIMEZONE_AWARE": False
            }
        )

    except Exception as e:
        print(f"[interpretar_data_e_hora] Erro: {e}")
        return None
