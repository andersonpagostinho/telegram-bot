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
    Gera sugestões de horários disponíveis no mesmo dia do início_base,
    com blocos e intervalos baseados na duração configurada pelo usuário.
    """
    duracao = timedelta(minutes=duracao_evento_minutos)
    sugestoes = []
    atual = datetime.combine(inicio_base.date(), time(8, 0))
    fim_dia = datetime.combine(inicio_base.date(), time(18, 0))

    while atual + duracao <= fim_dia:
        livre = all(not (atual < fim and atual + duracao > inicio) for inicio, fim in ocupados)

        if livre:
            sugestoes.append(f"{atual.strftime('%H:%M')} - {(atual + duracao).strftime('%H:%M')}")
            if len(sugestoes) >= max_sugestoes:
                break

        atual += timedelta(minutes=duracao_evento_minutos)  # 🧠 respeita a duração como passo

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
