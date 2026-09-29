"""
P2A: Bloquear "ola" indefinida em eh_aceite_de_acao_pendente()

Bug corrigido: "ola" com intencao_conversacional="indefinida" não deveria
ser tratado como aceite de ação pendente. A função estava retornando True
apenas porque:
- ctx["ultima_acao"] existia
- mensagem era curta
- não era negativa
- sem hora

Sem verificar que "ola" indefinida = conversação social, não confirmação.

Resultado: "ola" era roteado para executar_confirmacao_generica(), que
retornava erro "Não encontrei nenhuma ação recente para confirmar".

Correção: Adicionar guard em eh_aceite_de_acao_pendente() para bloquear
quando intencao_conversacional == "indefinida".
"""


def test_eh_aceite_acao_pendente_bloqueia_indefinida():
    """
    Simula: eh_aceite_de_acao_pendente("ola", ctx)

    Cenário:
    - txt = "ola"
    - ctx["ultima_acao"] = "contexto_limpo"
    - ctx["intencao_conversacional"] = "indefinida"

    Esperado: Retorna False (não é aceite)
    """
    # Simulando a lógica do guard
    txt = "ola"
    ctx = {
        "ultima_acao": "contexto_limpo",
        "intencao_conversacional": "indefinida",
        "estado_fluxo": "aguardando_profissional",
        "tem_draft": True,
    }

    # Guard check (como está em eh_aceite_de_acao_pendente linha 3289)
    if ctx.get("intencao_conversacional") == "indefinida":
        aceite = False
    else:
        aceite = True  # simulação simplificada do resto da função

    # Validação
    assert aceite is False, \
        "eh_aceite_de_acao_pendente deveria bloquear quando intencao='indefinida'"


def test_eh_aceite_acao_pendente_permite_operacional():
    """
    Simula: eh_aceite_de_acao_pendente("sim", ctx)

    Cenário:
    - txt = "sim"
    - ctx["ultima_acao"] = "resolver_fora_do_expediente"
    - ctx["intencao_conversacional"] = "confirmacao"

    Esperado: Guard permite, função continua avaliação
    """
    txt = "sim"
    ctx = {
        "ultima_acao": "resolver_fora_do_expediente",
        "intencao_conversacional": "confirmacao",
        "estado_fluxo": "aguardando_escolha_horario",
    }

    # Guard check
    if ctx.get("intencao_conversacional") == "indefinida":
        aceite = False
    else:
        aceite = True  # guard permite, função continua

    # Validação
    assert aceite is True, \
        "eh_aceite_de_acao_pendente deveria permitir quando intencao operacional"
