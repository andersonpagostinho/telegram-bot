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

