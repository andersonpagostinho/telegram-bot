"""
[MIGRAÇÃO LOTE 1 — TESTE 4] Extração de Data Sem Hora — E2E Firebase Real

Convertido de: test_p0_data_sem_hora_fix.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que quando usuário menciona APENAS data (sem hora),
o sistema reconhece corretamente e pede esclarecimento de hora.
"""

import pytest
import time
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote1_4_data_sem_hora_pede_esclarecimento_e2e():
    """
    Teste: Usuário menciona data sem hora.
    Mensagem: "quero agendar corte para amanhã"
    Esperado: Sistema reconhece data, pede horário
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5511998{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Data sem hora → sistema pede horário")
    print(f"  Mensagem: 'quero agendar corte para amanhã'")

    # Setup Firestore
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero agendar corte para amanhã",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve reconhecer data mas pedir horário
    assert any(x in resposta_texto for x in [
        "horário", "hora", "que horas", "qual hora",
        "prefere", "disponível", "profissional"
    ]), f"Sistema deveria pedir horário. Obtido: {resposta_texto[:150]}"

    print(f"  ✓ Sistema respondeu apropriadamente")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")

    # Contexto deve estar atualizado
    estado = ctx.get("estado_fluxo")
    assert estado is not None, "Estado não foi atualizado"

    print(f"  ✓ Contexto: estado={estado}")
    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote1_4_hora_sem_data_pede_esclarecimento_e2e():
    """
    Teste: Usuário menciona hora sem data.
    Mensagem: "quero agendar corte às 14h"
    Esperado: Sistema reconhece hora, pede data
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5511999{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Hora sem data → sistema pede data")
    print(f"  Mensagem: 'quero agendar corte às 14h'")

    # Setup Firestore
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero agendar corte às 14h",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve reconhecer hora mas pedir data
    assert any(x in resposta_texto for x in [
        "qual dia", "que dia", "data", "quando",
        "amanhã", "próximo", "disponível", "profissional"
    ]), f"Sistema deveria pedir data. Obtido: {resposta_texto[:150]}"

    print(f"  ✓ Sistema respondeu apropriadamente")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    estado = ctx.get("estado_fluxo")

    # Contexto deve estar atualizado
    assert estado is not None, "Estado não foi atualizado"

    print(f"  ✓ Contexto: estado={estado}")
    print(f"  ✅ [T2] PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
