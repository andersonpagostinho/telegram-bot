"""
TESTE DE REGRESSÃO: Bloqueador A — Impedir gravações em Clientes/None

Objetivo: Garantir que criar_notificacoes_evento_cliente_e_profissional()
rejeita tenant_id=None e não tenta salvar no Firestore.
"""

import pytest
from services.notificacao_service import criar_notificacoes_evento_cliente_e_profissional


@pytest.mark.asyncio
async def test_notificacao_rejeita_tenant_none():
    """Função deve retornar falha se tenant_id é None"""
    resultado = await criar_notificacoes_evento_cliente_e_profissional(
        tenant_id=None,  # ← Forçar None
        evento_id="evt_test_123",
        cliente_id="cli_test_001",
        cliente_nome="Cliente Teste",
        profissional_nome="Prof Teste",
        profissional_user_id=None,
        data="2026-10-25",
        hora_inicio="10:00",
    )

    # Validar que ambas falham
    assert resultado["cliente"]["sucesso"] == False, "Cliente deve falhar com tenant_id=None"
    assert resultado["profissional"]["sucesso"] == False, "Prof deve falhar com tenant_id=None"

    # Validar motivo claro
    assert resultado["cliente"].get("motivo"), "Cliente deve ter motivo de falha"
    assert "tenant_id vazio" in resultado["cliente"]["motivo"].lower(), \
        f"Motivo deve mencionar tenant_id vazio. Recebido: {resultado['cliente']['motivo']}"

    # Validar que nenhum ID foi criado
    assert resultado["cliente"].get("notif_id") is None, "Não deve gerar notif_id com tenant_id=None"
    assert resultado["profissional"].get("notif_id") is None, "Não deve gerar notif_id com tenant_id=None"

    print("[✅] PASS: tenant_id=None bloqueado corretamente")


@pytest.mark.asyncio
async def test_notificacao_rejeita_tenant_vazio():
    """Função deve retornar falha se tenant_id é string vazia"""
    resultado = await criar_notificacoes_evento_cliente_e_profissional(
        tenant_id="",  # ← Vazio
        evento_id="evt_test_456",
        cliente_id="cli_test_002",
        cliente_nome="Cliente Teste",
        profissional_nome="Prof Teste",
        profissional_user_id=None,
        data="2026-10-25",
        hora_inicio="11:00",
    )

    assert resultado["cliente"]["sucesso"] == False, "Cliente deve falhar com tenant_id vazio"
    assert resultado["profissional"]["sucesso"] == False, "Prof deve falhar com tenant_id vazio"

    print("[✅] PASS: tenant_id vazio bloqueado corretamente")


@pytest.mark.asyncio
async def test_notificacao_aceita_tenant_valido():
    """Função deve iniciar processamento se tenant_id é válido"""
    # Nota: Este teste NÃO valida Firestore (usa tenant fictício)
    # Apenas verifica que a validação inicial passa
    resultado = await criar_notificacoes_evento_cliente_e_profissional(
        tenant_id="tenant_teste_valido_001",  # ← Válido
        evento_id="evt_test_789",
        cliente_id="cli_test_003",
        cliente_nome="Cliente Teste",
        profissional_nome="Prof Teste",
        profissional_user_id=None,
        data="2026-10-25",
        hora_inicio="12:00",
    )

    # Não deve retornar motivo de tenant_id inválido
    if resultado["cliente"].get("motivo"):
        assert "tenant_id" not in resultado["cliente"]["motivo"].lower(), \
            "Não deve ter erro de tenant_id com valor válido"

    print("[✅] PASS: tenant_id válido aceito (validação inicial passou)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
