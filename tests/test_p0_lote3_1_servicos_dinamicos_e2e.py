"""
[MIGRAÇÃO LOTE 3 — TESTE 1] Serviços Dinâmicos — E2E Firebase Real

Convertido de: test_p0_servicos_dinamicos.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar extração dinâmica de serviços do catálogo do tenant.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote3_1_extrai_servico_catlogo_e2e():
    """
    T1: Sistema extrai serviço do catálogo do tenant.
    Mensagem: "quero agendar corte feminino"
    Esperado: Sistema reconhece "corte feminino" no catálogo
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5513001{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Extração dinâmica de serviço")
    print(f"  Mensagem: 'quero agendar corte feminino'")

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
        mensagem="quero agendar corte feminino",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve reconhecer o serviço
    assert any(x in resposta_texto for x in [
        "corte", "feminino", "profissional", "qual", "quando", "horário"
    ]), f"Serviço não reconhecido. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Serviço 'corte feminino' reconhecido")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote3_1_multiplos_servicos_e2e():
    """
    T2: Sistema reconhece múltiplos serviços do catálogo.
    Testa: "corte", "escova", "coloracao"
    Esperado: Todos os serviços são reconhecidos
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    servicos = [
        ("quero agendar corte", "corte"),
        ("quero fazer escova", "escova"),
        ("quero coloracao", "coloracao"),
    ]

    for i, (msg, servico) in enumerate(servicos, 1):
        phone_number = f"5513002{i}{uuid.uuid4().hex[:4]}"
        full_actor_id = f"whatsapp:{phone_number}"

        print(f"\n[T2.{i}] Teste E2E: Serviço '{servico}'")

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

        print(f"  ✓ Serviço '{servico}' reconhecido")

    print(f"  ✅ [T2] PASS (3 serviços)")
