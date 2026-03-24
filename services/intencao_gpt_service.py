import re

INTENCOES_VALIDAS = [
    "start", "help", "meusdados", "meuestilo", "adicionar_tarefa",
    "listar_tarefas", "listar_prioridade", "limpar_tarefas",
    "adicionar_evento", "listar_eventos", "confirmar_reuniao",
    "confirmar_presenca", "debug_eventos", "conectar_email",
    "authcallback", "ler_emails", "emails_prioritarios", "enviar_email",
    "meu_email", "relatorio_diario", "relatorio_semanal",
    "enviar_relatorio_email", "definir_tipo_negocio", "definir_estilo",
    "definir_nome_negocio", "criar_followup", "concluir_followup",
    "meusfollowups", "configurar_avisos", "organizar_semana"
]

# Heurística simples e determinística para evitar uma porta GPT paralela.
# Retorne None para deixar o fluxo principal decidir com contexto e regras.
def _norm(txt: str) -> str:
    return re.sub(r"\s+", " ", (txt or "").strip().lower())

async def identificar_intencao_com_gpt(texto_usuario: str) -> str | None:
    t = _norm(texto_usuario)

    # comandos curtos
    if t in ("/start", "start", "iniciar", "começar", "comecar"):
        return "start"
    if t in ("/help", "help", "ajuda", "socorro"):
        return "help"

    # organizar semana
    if any(k in t for k in ["organizar semana", "planejar semana", "minha semana", "me ajuda com meu dia", "planejar meu dia"]):
        return "organizar_semana"

    # email
    if any(k in t for k in ["ler email", "ler e-mails", "ver emails", "meus emails", "emails prioritarios", "e-mails prioritários"]):
        return "ler_emails"

    if any(k in t for k in ["enviar email", "mandar email", "enviar e-mail", "mandar e-mail"]):
        return "enviar_email"

    # tarefas (cuidado com falso positivo)
    if any(k in t for k in ["adicionar tarefa", "criar tarefa", "nova tarefa"]):
        return "adicionar_tarefa"
    if any(k in t for k in ["listar tarefas", "minhas tarefas", "ver tarefas"]):
        return "listar_tarefas"
    if "limpar tarefas" in t or "apagar tarefas" in t:
        return "limpar_tarefas"

    # eventos
    if any(k in t for k in ["adicionar evento", "criar evento", "marcar reunião", "agendar reunião", "agendar evento"]):
        return "adicionar_evento"
    if any(k in t for k in ["listar eventos", "meus eventos", "agenda de hoje", "agenda amanhã", "agenda amanha"]):
        return "listar_eventos"

    # confirmações simples
    if any(k in t for k in ["confirmar reunião", "confirmar reuniao"]):
        return "confirmar_reuniao"
    if any(k in t for k in ["confirmar presença", "confirmar presenca"]):
        return "confirmar_presenca"

    # followup
    if "criar followup" in t or "criar follow-up" in t:
        return "criar_followup"
    if "concluir followup" in t or "concluir follow-up" in t:
        return "concluir_followup"
    if "meus followups" in t or "meus follow-ups" in t:
        return "meusfollowups"

    # se não casar, deixa o fluxo principal decidir
    return None
