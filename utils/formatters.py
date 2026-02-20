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

def _formatar_data_br(data_str: str) -> str:
    """Converte '2025-11-04' para '04/11/2025' se der, senão devolve original."""
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return data_str or "-"

def _status_evento_humano(status: str | None) -> str:
    status = (status or "").lower()
    if status == "confirmado":
        return "✅ Confirmado"
    if status == "cancelado":
        return "❌ Cancelado"
    return "⏳ Pendente"

def formatar_eventos_telegram(eventos: list[dict]) -> str:
    """
    Formata lista de eventos vinda do Firestore para uma mensagem legível
    no Telegram e no WhatsApp.
    """
    if not eventos:
        return "📅 Você não tem eventos agendados."

    linhas = ["📅 *Seus eventos:*"]
    for i, ev in enumerate(eventos, start=1):
        # nomes possíveis porque às vezes vem com minúscula e às vezes não
        data = ev.get("data") or ev.get("Data")
        hora_inicio = ev.get("hora_inicio") or ev.get("horainicio") or ev.get("horaInicio") or "-"
        hora_fim = ev.get("hora_fim") or ev.get("horafim") or ev.get("horaFim") or "-"
        descricao = ev.get("descricao") or ev.get("titulo") or "Evento"
        profissional = ev.get("profissional") or ev.get("prof") or "-"
        status = ev.get("status")

        data_fmt = _formatar_data_br(data)
        status_fmt = _status_evento_humano(status)

        linhas.append(
            f"{i}. *{data_fmt}* ({hora_inicio}–{hora_fim})\n"
            f"   • {descricao}\n"
            f"   • Profissional: {profissional}\n"
            f"   • Status: {status_fmt}"
        )

    return "\n".join(linhas)