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
    Agenda inteligente P1 (NeoEve):
    - Fase 1: preenche manhã → tarde (até ~70%)
    - Fase 2: encaixe fino para otimizar ocupação
    """

    duracao = timedelta(minutes=duracao_evento_minutos)
    passo = timedelta(minutes=passo_minutos)

    blocos_livres = _calcular_blocos_livres(inicio_base, ocupados)

    # =========================
    # 📊 CALCULAR OCUPAÇÃO
    # =========================
    inicio_dia = datetime.combine(inicio_base.date(), time(8, 0))
    fim_dia = datetime.combine(inicio_base.date(), time(18, 0))

    total_dia = (fim_dia - inicio_dia).total_seconds()

    ocupado_total = 0
    for ini, fim in ocupados:
        if ini and fim:
            ocupado_total += (fim - ini).total_seconds()

    ocupacao_ratio = ocupado_total / total_dia if total_dia else 0

    # =========================
    # GERAR CANDIDATOS
    # =========================
    candidatos = []

    for livre_inicio, livre_fim in blocos_livres:
        cursor = livre_inicio

        while cursor + duracao <= livre_fim:
            if cursor != inicio_base:
                candidatos.append(cursor)
            cursor += passo

    if not candidatos:
        return []

    ocupados_ordenados = sorted(
        [(ini, fim) for ini, fim in ocupados if ini and fim and fim > ini],
        key=lambda x: x[0]
    )

    # =========================
    # SCORE INTELIGENTE
    # =========================
    def score_slot(horario: datetime):
        fim_slot = horario + duracao

        evento_anterior_fim = None
        proximo_evento_inicio = None

        for ev_ini, ev_fim in ocupados_ordenados:
            if ev_fim <= horario:
                evento_anterior_fim = ev_fim
            elif ev_ini >= fim_slot:
                proximo_evento_inicio = ev_ini
                break

        gap_antes = None
        gap_depois = None

        if evento_anterior_fim:
            gap_antes = int((horario - evento_anterior_fim).total_seconds() // 60)

        if proximo_evento_inicio:
            gap_depois = int((proximo_evento_inicio - fim_slot).total_seconds() // 60)

        desperdicio = 0
        if gap_antes is not None and gap_antes > 0:
            desperdicio += gap_antes
        if gap_depois is not None and gap_depois > 0:
            desperdicio += gap_depois

        distancia = abs(int((horario - inicio_base).total_seconds() // 60))

        # ✅ bônus para horários mais naturais
        minuto = horario.minute
        if minuto in (0, 30):
            penalidade_visual = 0
        elif minuto in (15, 45):
            penalidade_visual = 1
        else:
            penalidade_visual = 2

        # ✅ bônus para encaixe colado
        encosta = 0
        if gap_antes == 0:
            encosta += 1
        if gap_depois == 0:
            encosta += 1

        # =========================
        # 🔥 FASE 1 — BAIXA OCUPAÇÃO
        # prioriza proximidade do pedido
        # =========================
        if ocupacao_ratio < 0.7:
            return (
                distancia,           # 1) mais próximo do horário pedido
                penalidade_visual,   # 2) horário mais bonito
                desperdicio,         # 3) menor buraco
                -encosta,            # 4) se encosta em outro evento, melhor
                horario              # 5) desempate cronológico
            )

        # =========================
        # 🔥 FASE 2 — ALTA OCUPAÇÃO
        # encaixe mais agressivo, mas sem ignorar proximidade
        # =========================
        return (
            -encosta,               # 1) colar em eventos
            desperdicio,            # 2) minimizar buraco
            distancia,              # 3) respeitar horário pedido
            penalidade_visual,      # 4) evitar horários feios
            horario                 # 5) desempate cronológico
        )

    candidatos_ordenados = sorted(candidatos, key=score_slot)

    sugestoes = []

    janelas_ocupadas = []  # [(inicio, fim)]

    for horario in candidatos_ordenados:

        inicio_slot = horario
        fim_slot = horario + duracao

        # 🔥 verifica se esse horário conflita com alguma sugestão já escolhida
        conflita = False
        for ini_exist, fim_exist in janelas_ocupadas:
            if not (fim_slot <= ini_exist or inicio_slot >= fim_exist):
                conflita = True
                break

        if conflita:
            continue

        # ✅ adiciona como melhor daquela janela
        janelas_ocupadas.append((inicio_slot, fim_slot))

        inicio = inicio_slot.strftime("%H:%M")
        fim = fim_slot.strftime("%H:%M")
        faixa = f"{inicio} - {fim}"

        sugestoes.append(faixa)

        if len(sugestoes) >= max_sugestoes:
            break

    return sugestoes

# =========================================================
# FORMATADORES DE MENSAGEM
# =========================================================

def _formatar_data_br(data_str: str) -> str:
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