"""
TESTE E2E: Bloqueio de Expediente no Fluxo Completo

Valida que quando usuário menciona dia fechado (domingo),
o sistema rejeita com mensagem de erro e NÃO continua processando.
"""

import pytest
import asyncio
from datetime import datetime
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path


@pytest.mark.asyncio
async def test_bloqueio_expediente_no_roteador():
    """
    E2E test: Usuário diz 'quero agendar para hoje' (domingo 18/10)
    Sistema deve rejeitar com "não abre" e NÃO continuar processando
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    # Setup: sessão vazia (estado_fluxo deve ser string)
    ctx = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }

    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx
    )

    # Chamar roteador_principal simule webhook
    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem="quero agendar um corte para hoje",  # 18/10/2026 = domingo
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    # Verificar resposta
    resposta_texto = resultado.get("resposta", "").lower()

    print(f"\n[TESTE E2E] Resposta: {resposta_texto[:100]}...")

    # Deve conter mensagem de rejeição
    assert "não abre" in resposta_texto or "fechado" in resposta_texto, \
        f"Resposta deveria mencionar que não abre. Recebeu: {resposta_texto[:200]}"

    # Verificar que estado ficou aguardando_data (não avançou)
    sessao_pos = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )

    assert sessao_pos.get("estado_fluxo") == "aguardando_data", \
        f"Estado deveria ser 'aguardando_data', mas é {sessao_pos.get('estado_fluxo')}"

    # Verificar que data_hora não foi atribuído
    assert sessao_pos.get("data_hora") is None, \
        f"data_hora não deveria ser atribuído, mas foi {sessao_pos.get('data_hora')}"

    print("✅ E2E test PASSOU: Expediente rejeitado no roteador completo")


@pytest.mark.asyncio
async def test_aceita_dia_valido_amanha():
    """
    E2E test: Usuário diz 'quero agendar para amanhã' (segunda 19/10)
    Sistema deve aceitar (segunda é dia de funcionamento)
    """
    import uuid
    tenant_id = "7394370553"
    actor_id = "whatsapp:" + uuid.uuid4().hex[:8]

    # Setup: sessão vazia (estado_fluxo deve ser string)
    ctx = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }

    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx
    )

    # Chamar roteador_principal
    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem="quero agendar um corte para amanhã",  # 19/10/2026 = segunda
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    # Verificar resposta NÃO tem erro de expediente
    resposta_texto = resultado.get("resposta", "").lower()

    print(f"\n[TESTE E2E] Resposta: {resposta_texto[:100]}...")

    # Não deve rejeitar por expediente
    assert "não abre" not in resposta_texto and "fechado" not in resposta_texto, \
        f"Deveria aceitar dia válido. Recebeu: {resposta_texto[:200]}"

    # Verificar sessão foi atualizada
    sessao_pos = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )

    # Não deve ter erro de validação
    assert sessao_pos.get("_erro_validacao") is None, \
        f"Não deveria ter erro para dia válido, mas tem: {sessao_pos.get('_erro_validacao')}"

    print("✅ E2E test PASSOU: Dia válido aceito")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
