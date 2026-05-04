from utils.text_utils import normalizar_txt


def interpretar_conversa_operacional(
    texto: str,
    ctx: dict | None = None,
    servicos_catalogo: list[str] | None = None,
    profissionais_catalogo: list[str] | None = None,
) -> dict:
    ctx = ctx or {}
    servicos_catalogo = servicos_catalogo or []
    profissionais_catalogo = profissionais_catalogo or []

    t = normalizar_txt(texto or "")

    if ctx.get("aguardando_confirmacao_agendamento") is True:
        if _parece_negacao_confirmacao(t):
            return {
                "intencao": "negacao_confirmacao_agendamento",
                "objetivo": "encerrar_fluxo_agendamento",
                "tipo_ajuste": None,
                "entidades": {},
                "confianca": 90,
                "motivo": "negacao_durante_confirmacao",
            }

    return {
        "intencao": "indefinida",
        "objetivo": None,
        "tipo_ajuste": None,
        "entidades": {},
        "confianca": 40,
        "motivo": "fallback_inicial",
    }

def _parece_negacao_confirmacao(t: str) -> bool:
    termos = [
        "nao quero",
        "nao precisa",
        "melhor nao",
        "deixa",
        "esquece",
        "cancela",
        "desisti",
        "agora nao",
        "vou ver depois",
    ]

    return any(x in t for x in termos)