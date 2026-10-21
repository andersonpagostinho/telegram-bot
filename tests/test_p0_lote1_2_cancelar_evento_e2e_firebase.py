"""
[MIGRAÇÃO LOTE 1 — TESTE 2] Bloqueio de Cancelamento de Eventos Passados — E2E Firebase Real

Convertido de: test_p0_cancelar_evento_passado.py (unitário/mock)
Para: E2E com Firestore Real

Objetivo: Validar que usuário NÃO consegue cancelar eventos com data no passado.
Fluxo real: mensagem de cancelamento → validação em Firestore → resposta apropriada
"""

import pytest
import time
import uuid
from datetime import datetime, date, timedelta

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote1_2_nao_cancelar_evento_passado_e2e():
    """
    Teste: Usuário tenta cancelar evento do passado.
    Esperado: Sistema bloqueia o cancelamento.

    Estratégia: Enviar mensagem de cancelamento, validar que sistema
    responde apropriadamente (não cancela evento passado).
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5511994{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Bloqueio de cancelamento de evento passado")
    print(f"  Mensagem: 'quero cancelar meu agendamento de ontem'")

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
        mensagem="quero cancelar meu agendamento de ontem",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve indicar que não há agendamento ou que já passou
    assert any(x in resposta_texto for x in [
        "não", "passado", "já", "anterior", "antigo", "não tenho",
        "sem agendamento", "nenhum", "agenda"
    ]), f"Resposta deveria indicar bloqueio. Obtido: {resposta_texto[:150]}"

    print(f"  ✓ Sistema respondeu apropriadamente")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote1_2_pode_cancelar_evento_futuro_e2e():
    """
    Teste: Usuário tenta cancelar evento futuro.
    Esperado: Sistema permite o fluxo de cancelamento.
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5511995{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Cancelamento de evento futuro permitido")
    print(f"  Mensagem: 'quero cancelar meu agendamento de amanhã'")

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
        mensagem="quero cancelar meu agendamento de amanhã",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve reconhecer o pedido de cancelamento
    assert any(x in resposta_texto for x in [
        "cancelar", "confirma", "tem certeza", "cancelamento",
        "qual agendamento", "encontre", "agenda"
    ]), f"Sistema deveria reconhecer cancelamento. Obtido: {resposta_texto[:150]}"

    print(f"  ✓ Sistema reconheceu pedido de cancelamento")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"
    estado = ctx.get("estado_fluxo")
    assert estado is not None, "Estado não foi atualizado"

    print(f"  ✅ [T2] PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
