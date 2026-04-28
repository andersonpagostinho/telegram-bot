import re
import unicodedata


def normalizar_texto(txt: str) -> str:
    txt = (txt or "").lower().strip()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt


def tem_indicio_data_ou_hora(texto: str) -> bool:
    t = normalizar_texto(texto)

    return bool(
        re.search(r"\b\d{1,2}:\d{2}\b", t)
        or re.search(r"\b\d{1,2}h(\d{2})?\b", t)
        or any(x in t for x in [
            "hoje", "amanha", "amanhã", "depois de amanha", "segunda",
            "terca", "terça", "quarta", "quinta", "sexta", "sabado",
            "sábado", "domingo", "cedo", "manha", "manhã", "tarde",
            "noite", "horario", "horário"
        ])
    )


def detectar_consulta_disponibilidade(texto: str) -> bool:
    t = normalizar_texto(texto)

    sinais = [
        "tem horario", "tem horário",
        "que horas", "quais horarios", "quais horários",
        "tem vaga", "tem algum horario", "tem algum horário",
        "horario disponivel", "horário disponível",
        "voce tem cedo", "você tem cedo",
        "tem cedo", "tem de manha", "tem de manhã",
        "algum horario", "algum horário",
    ]

    return any(s in t for s in sinais)


def detectar_mensagem_pessoal(texto: str) -> bool:
    t = normalizar_texto(texto)

    sinais_pessoais = [
        "vamos almocar", "vamos almoçar",
        "vamos sair", "saudades",
        "oi amiga", "oi amigo",
        "tudo bem com voce", "tudo bem com você",
        "como voce esta", "como você está",
        "bom dia amiga", "boa noite amiga",
    ]

    return any(s in t for s in sinais_pessoais)


async def classificar_contexto_conversa(
    texto_usuario: str,
    ctx: dict,
    dono_id: str,
    servicos_catalogo: list[str] | None = None,
    profissionais_catalogo: list[str] | None = None,
    actor_tipo: str | None = None,
) -> dict:
    """
    Camada conversacional v1.

    Não executa lógica de agenda.
    Não calcula disponibilidade.
    Não cria evento.
    Só classifica se a mensagem deve entrar no motor operacional.
    """

    t = normalizar_texto(texto_usuario)

    servicos_catalogo = servicos_catalogo or []
    profissionais_catalogo = profissionais_catalogo or []

    nivel_negocio = 0
    nivel_pessoal = 0
    nivel_comando_interno = 0

    servico_detectado = None
    profissional_detectado = None

    for s in servicos_catalogo:
        if normalizar_texto(s) in t:
            servico_detectado = s
            nivel_negocio += 3
            break

    for p in profissionais_catalogo:
        if normalizar_texto(p) in t:
            profissional_detectado = p
            nivel_negocio += 2
            break

    if tem_indicio_data_ou_hora(t):
        nivel_negocio += 1

    if detectar_consulta_disponibilidade(t):
        nivel_negocio += 3

    if any(x in t for x in ["agendar", "marcar", "reservar", "atendimento", "consulta"]):
        nivel_negocio += 2

    if detectar_mensagem_pessoal(t):
        nivel_pessoal += 4

    if actor_tipo in ("dono", "profissional"):
        if any(x in t for x in ["bloquear agenda", "fechar agenda", "nao vou atender", "não vou atender"]):
            nivel_comando_interno += 4

    if nivel_comando_interno >= 4:
        return {
            "tipo": "comando_interno_dono",
            "nivel_negocio": nivel_negocio,
            "nivel_pessoal": nivel_pessoal,
            "nivel_comando_interno": nivel_comando_interno,
            "servico_detectado": servico_detectado,
            "profissional_detectado": profissional_detectado,
            "motivo": "sinais de comando interno"
        }

    if nivel_pessoal >= 4 and nivel_negocio < 3:
        return {
            "tipo": "mensagem_pessoal",
            "nivel_negocio": nivel_negocio,
            "nivel_pessoal": nivel_pessoal,
            "nivel_comando_interno": nivel_comando_interno,
            "servico_detectado": servico_detectado,
            "profissional_detectado": profissional_detectado,
            "motivo": "sinais pessoais sem intenção operacional"
        }

    if detectar_consulta_disponibilidade(t) and nivel_negocio >= 3:
        return {
            "tipo": "consulta_disponibilidade",
            "nivel_negocio": nivel_negocio,
            "nivel_pessoal": nivel_pessoal,
            "nivel_comando_interno": nivel_comando_interno,
            "servico_detectado": servico_detectado,
            "profissional_detectado": profissional_detectado,
            "motivo": "pedido de horários/disponibilidade"
        }

    if nivel_negocio >= 3:
        return {
            "tipo": "agendamento_cliente",
            "nivel_negocio": nivel_negocio,
            "nivel_pessoal": nivel_pessoal,
            "nivel_comando_interno": nivel_comando_interno,
            "servico_detectado": servico_detectado,
            "profissional_detectado": profissional_detectado,
            "motivo": "sinais suficientes de atendimento"
        }

    return {
        "tipo": "indefinido",
        "nivel_negocio": nivel_negocio,
        "nivel_pessoal": nivel_pessoal,
        "nivel_comando_interno": nivel_comando_interno,
        "servico_detectado": servico_detectado,
        "profissional_detectado": profissional_detectado,
        "motivo": "sem sinais suficientes"
    }