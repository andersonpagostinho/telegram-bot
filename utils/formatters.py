from pytz import timezone
from datetime import datetime, time, timedelta

def formatar_horario_atual(date_utc):
    fuso_br = timezone("America/Sao_Paulo")
    data_local = date_utc.astimezone(fuso_br)
    data_str = data_local.strftime("%d/%m/%Y")
    hora_str = data_local.strftime("%H:%M")
    return f"No momento são {data_str} e o horário é {hora_str}."

def gerar_sugestoes_de_horario(inicio_base: datetime, ocupados: list, duracao_evento_minutos: int = 60, max_sugestoes: int = 3) -> list:
    """
    Gera sugestões de horários disponíveis com base na hora solicitada (inicio_base),
    buscando horários vizinhos (antes e depois) com base na duração.
    """
    duracao = timedelta(minutes=duracao_evento_minutos)
    sugestoes = []

    # Base: uma antes, a própria, e uma depois
    blocos = [
        inicio_base - duracao,
        inicio_base,
        inicio_base + duracao
    ]

    for atual in blocos:
        if len(sugestoes) >= max_sugestoes:
            break

        fim_dia = datetime.combine(atual.date(), time(18, 0))
        if atual + duracao > fim_dia:
            continue  # pula se passar do horário final

        livre = all(not (atual < fim and atual + duracao > inicio) for inicio, fim in ocupados)

        if livre:
            sugestoes.append(f"{atual.strftime('%H:%M')} - {(atual + duracao).strftime('%H:%M')}")

    return sugestoes

def formatar_lista_emails(emails):
    if not emails:
        return "Nenhum e-mail encontrado."

    return "\n\n".join(
        f"📩 *{e.get('remetente', 'Desconhecido')}*\n"
        f"✉️ {e.get('assunto', 'Sem assunto')}\n"
        f"⚡ Prioridade: {e.get('prioridade', 'baixa')}\n"
        f"🔗 {e.get('link', 'Sem link')}"
        for e in emails
    )
