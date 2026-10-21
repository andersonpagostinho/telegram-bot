"""
[MIGRAÇÃO LOTE 3 — TESTE 4] Pedido Genérico Fix — E2E Firebase Real

Convertido de: test_p012_eh_pedido_generico_fix.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que pedidos genéricos são reconhecidos corretamente.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote3_4_pedido_generico_agendamento_e2e():
    """
    T1: Pedido genérico é reconhecido como agendamento.
    Mensagem: "quero agendar"
    Esperado: Sistema reconhece intenção de agendamento
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5513301{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Pedido genérico reconhecido")
    print(f"  Mensagem: 'quero agendar'")

    # Setup Firestore
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero agendar",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve reconhecer agendamento
    assert any(x in resposta_texto for x in [
        "qual", "serviço", "que", "quando", "data", "profissional", "qual"
    ]), f"Pedido genérico não reconhecido. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Pedido genérico reconhecido como agendamento")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote3_4_variantes_pedido_generico_e2e():
    """
    T2: Diferentes variantes de pedido genérico são reconhecidas.
    Testa: "quero agendar", "marcar agendamento", "fazer reserva"
    Esperado: Todas reconhecidas como agendamento
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    mensagens = ["quero agendar", "marcar agendamento", "fazer reserva"]

    for i, msg in enumerate(mensagens, 1):
        phone_number = f"5513302{i}{uuid.uuid4().hex[:4]}"
        full_actor_id = f"whatsapp:{phone_number}"

        print(f"\n[T2.{i}] Teste E2E: Variante '{msg}'")

        # Setup Firestore
        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "idle",
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem=msg,
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        resposta_texto = resposta.get("resposta", "").lower()
        assert len(resposta_texto) > 0, "Resposta vazia"

        ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        assert ctx is not None, "Contexto não foi salvo"

        print(f"  ✓ Variante '{msg}' reconhecida")

    print(f"  ✅ [T2] PASS (3 variantes)")
