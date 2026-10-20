from services.classificador_conversa import normalizar_txt, extrair_servico_do_catalogo

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

    # [FIX P0.3.1] Detecta consulta de disponibilidade com padrão determinístico
    if _parece_consulta_disponibilidade(t):
        servico_extraido = extrair_servico_do_catalogo(texto, servicos_catalogo)
        return {
            "intencao": "consulta_disponibilidade_servico",
            "objetivo": "consultar_disponibilidade_por_servico",
            "tipo_ajuste": None,
            "entidades": {"servico": servico_extraido} if servico_extraido else {},
            "confianca": 85,
            "motivo": "padrão_consulta_determinístico",
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

def _parece_consulta_disponibilidade(t: str) -> bool:
    """
    [FIX P0.3.1] Detecta padrões de consulta de disponibilidade.

    Exemplos:
      "você tem agenda para corte amanhã?"
      "tem horário para pedicure?"
      "tem disponibilidade amanhã às 10h?"
      "vocês fazem coloração?"

    Não confunde com confirmação ("sim", "ok") ou ajuste ("muda para 8h").
    """
    # Padrões que indicam consulta de disponibilidade/agenda
    padroes_consulta = [
        "voce tem agenda",
        "tem agenda",
        "tem horario",
        "tem disponibilidade",
        "tem vaga",
        "voces fazem",
        "voce faz",
        "faz o ",
        "oferec",  # oferece, oferecem
    ]

    return any(p in t for p in padroes_consulta)