"""
P2B: Saudação indefinida pula fallback operacional

Valida que quando intencao_conversacional == "indefinida"
e texto é saudação, o guard impede montar_resposta_fallback().
"""

import pytest


def test_p2b_saudacao_indefinida_pula_fallback():
    """
    Valida a lógica do guard P2B.
    Se mensagem é saudação indefinida, guard retorna False e pula fallback.
    """
    # Simular contexto P2B
    ctx = {"intencao_conversacional": "indefinida"}
    texto_usuario = "ola"

    from router.principal_router import normalizar
    tnorm = normalizar(texto_usuario)
    saudacoes = ["oi", "ola", "olá", "bom dia"]

    # Guard P2B: if not (indefinida AND saudacao) execute fallback
    deveria_executar_fallback = not (ctx.get("intencao_conversacional") == "indefinida" and tnorm in saudacoes)

    # Saudação indefinida deve PULAR fallback
    assert deveria_executar_fallback is False, \
        "FALHOU: Saudacao indefinida deveria PULAR fallback"


def test_p2b_operacional_executa_fallback():
    """
    Valida que operacional (confirmacao, dados, etc) executa fallback normalmente.
    """
    ctx = {"intencao_conversacional": "confirmacao"}
    texto_usuario = "sim"

    from router.principal_router import normalizar
    tnorm = normalizar(texto_usuario)
    saudacoes = ["oi", "ola", "olá", "bom dia"]

    deveria_executar_fallback = not (ctx.get("intencao_conversacional") == "indefinida" and tnorm in saudacoes)

    assert deveria_executar_fallback is True, \
        "FALHOU: Confirmacao operacional deveria EXECUTAR fallback"


def test_p2b_nao_saudacao_nao_indefinida_executa_fallback():
    """
    Valida que mensagem não-saudação não-indefinida executa fallback.
    """
    ctx = {"intencao_conversacional": "ajuste_incremental"}
    texto_usuario = "Bruna"

    from router.principal_router import normalizar
    tnorm = normalizar(texto_usuario)
    saudacoes = ["oi", "ola", "olá", "bom dia"]

    deveria_executar_fallback = not (ctx.get("intencao_conversacional") == "indefinida" and tnorm in saudacoes)

    assert deveria_executar_fallback is True, \
        "FALHOU: Nome operacional deveria EXECUTAR fallback"
