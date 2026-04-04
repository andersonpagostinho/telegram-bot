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
            return radical + "o"
        n = nome.strip().lower()
        return radical + ("a" if n.endswith("a") else "o")
    except Exception:
        return radical + "o"


# =========================================================
# MOTOR DE AGENDA INTELIGENTE
# =========================================================

def _calcular_blocos_livres(data_ref: datetime, ocupados: list,
                           inicio_expediente=time(8, 0),
                           fim_expediente=time(18, 0)):
    """
    Recebe lista de intervalos ocupados [(inicio,fim)]
    e devolve blocos livres no expediente.
    """

    inicio_dia = datetime.combine(data_ref.date(), inicio_expediente)
    fim_dia = datetime.combine(data_ref.date(), fim_expediente)

    if not ocupados:
        return [(inicio_dia, fim_dia)]

    ocupados = sorted(ocupados, key=lambda x: x[0])

    livres = []
    cursor = inicio_dia

    for inicio, fim in ocupados:

        if inicio > cursor:
            livres.append((cursor, inicio))

        cursor = max(cursor, fim)

    if cursor < fim_dia:
        livres.append((cursor, fim_dia))

    return livres


def gerar_sugestoes_de_horario(
        inicio_base: datetime,
        ocupados: list,
        duracao_evento_minutos: int = 60,
        max_sugestoes: int = 3,
        passo_minutos: int = 10
) -> list:
    """
    Gera sugestões reais de horários disponíveis.
    Permite encaixes inteligentes na agenda.
    """

    duracao = timedelta(minutes=duracao_evento_minutos)
    passo = timedelta(minutes=passo_minutos)

    blocos_livres = _calcular_blocos_livres(inicio_base, ocupados)

    candidatos = []

    for livre_inicio, livre_fim in blocos_livres:

        cursor = livre_inicio

        while cursor + duracao <= livre_fim:

            candidatos.append(cursor)

            cursor += passo

    if not candidatos:
        return []

    # remove horário original exato
    candidatos = [c for c in candidatos if c != inicio_base]

    # ordena pela proximidade do horário solicitado
    candidatos.sort(key=lambda x: abs((x - inicio_base).total_seconds()))

    sugestoes = []

    for horario in candidatos[:max_sugestoes]:

        inicio = horario.strftime("%H:%M")
        fim = (horario + duracao).strftime("%H:%M")

        sugestoes.append(f"{inicio} - {fim}")

    return sugestoes


# =========================================================
# FORMATADORES DE MENSAGEM
# =========================================================

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

        data = ev.get("data") or ev.get("Data")

        hora_inicio = (
                ev.get("hora_inicio")
                or ev.get("horainicio")
                or ev.get("horaInicio")
                or "-"
        )

        hora_fim = (
                ev.get("hora_fim")
                or ev.get("horafim")
                or ev.get("horaFim")
                or "-"
        )

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