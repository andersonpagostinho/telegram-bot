import dateparser
import re
from datetime import datetime, timedelta

def interpretar_intervalo_de_datas(texto):
    texto = texto.lower()
    hoje = datetime.now().date()

    # Semana que vem
    if "semana que vem" in texto or "próxima semana" in texto or "proxima semana" in texto:
        inicio = hoje + timedelta(days=(7 - hoje.weekday()))  # próxima segunda
        fim = inicio + timedelta(days=6)
        return inicio, fim

    # Essa semana
    if "essa semana" in texto or "esta semana" in texto:
        inicio = hoje - timedelta(days=hoje.weekday())  # segunda desta semana
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

def interpretar_data_e_hora(texto: str) -> datetime | None:
    """
    Tenta extrair uma data e hora do texto do usuário.
    Ex: "amanhã às 10", "sexta 14h", "dia 25 às 15:30"
    """
    if not texto:
        return None

    try:
        texto_normalizado = texto.lower()

        data_hora = dateparser.parse(
            texto_normalizado,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.now(),
                "TIMEZONE": "America/Sao_Paulo",
                "RETURN_AS_TIMEZONE_AWARE": False
            }
        )

        return data_hora
    except Exception as e:
        print(f"[interpretador_datas] Erro ao interpretar data/hora: {e}")
        return None

