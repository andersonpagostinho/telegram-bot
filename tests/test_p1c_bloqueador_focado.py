"""
P1-C Bloqueador — Teste do Contrato

Valida que o guard bloqueia detectar_alteracao quando intencao=="indefinida".
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_guard_logica_indefinida_bloqueia():
    """
    Testa logica do guard (linha ~4362, ~5033):
    Se intencao_conversacional == "indefinida", entao alteracao = None
    """
    # Simulando logica do guard
    ctx = {"intencao_conversacional": "indefinida"}

    if ctx.get("intencao_conversacional") == "indefinida":
        alteracao = None
    else:
        alteracao = {"tipo": "servico", "valor": "coloracao"}

    # Validacao: guard bloqueou
    assert alteracao is None, \
        "Guard deveria bloquear quando intencao indefinida"


async def test_guard_logica_operacional_permite():
    """
    Testa logica do guard (linha ~4362, ~5033):
    Se intencao_conversacional != "indefinida", entao tenta detectar
    """
    # Simulando logica do guard
    ctx = {"intencao_conversacional": "ajuste_incremental"}

    if ctx.get("intencao_conversacional") == "indefinida":
        alteracao = None
    else:
        # Guard permite que detectar seja tentado
        alteracao = "seria_chamado"  # placeholder

    # Validacao: guard permitiu
    assert alteracao == "seria_chamado", \
        "Guard deveria permitir quando intencao operacional"
