from pytz import timezone
from datetime import datetime, time, timedelta

def formatar_horario_atual(date_utc):
    fuso_br = timezone("America/Sao_Paulo")
    data_local = date_utc.astimezone(fuso_br)
    data_str = data_local.strftime("%d/%m/%Y")
    hora_str = data_local.strftime("%H:%M")
    return f"No momento são {data_str} e o horário é {hora_str}."

def adaptar_genero(nome: str | None, radical: str) -> str:
    """
    Retorna o radical flexionado por gênero com base no nome.
    Se nome terminar com 'a' -> feminino (ex.: 'ocupada'), senão -> masculino ('ocupado').
    Suporta None, string vazia e espaços sem quebrar.
    """
    try:
        if not nome:
            # neutro/seguro quando não há nome
            return radical + "o"
        n = nome.strip().lower()
        return radical + ("a" if n.endswith("a") else "o")
    except Exception:
        # fallback ultra-seguro
        return radical + "o"

def gerar_sugestoes_de_horario(inicio_base: datetime, ocupados: list, duracao_evento_minutos: int = 60, max_sugestoes: int = 3) -> list:
    """
    Gera sugestões de horários disponíveis com base na hora solicitada (inicio_base),
    evitando blocos que entram em conflito com a lista de horários ocupados.
    """
    duracao = timedelta(minutes=duracao_evento_minutos)
    sugestoes = []

    # Blocos candidatos: anterior, posterior, e mais ao redor
    candidatos = [
        inicio_base - duracao,
        inicio_base + duracao,
        inicio_base + 2 * duracao,
        inicio_base - 2 * duracao,
    ]

    for atual in candidatos:
        if len(sugestoes) >= max_sugestoes:
            break

        fim_dia = datetime.combine(atual.date(), time(18, 0))
        if atual + duracao > fim_dia:
            continue

        # Verifica se há conflito com eventos existentes
        conflito = any(not (atual + duracao <= inicio or atual >= fim) for inicio, fim in ocupados)

        if not conflito:
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
