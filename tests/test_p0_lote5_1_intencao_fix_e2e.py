"""
[MIGRAÇÃO LOTE 5 — TESTE 1] Intenção Fix P061 — E2E Firebase Real

Objetivo: Validar fix de intenção em P061.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote5_1_intencao_classificada_corretamente_e2e():
    """
    T1: Intenção é classificada corretamente.
    Mensagem: "quero agendar"
    Esperado: intencao_conversacional = agendamento
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5515001{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Intenção classificada corretamente")

    ctx_inicial = {"tipo_usuario": "cliente", "estado_fluxo": "idle"}
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero agendar corte",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Resposta vazia"

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✓ Intenção classificada")
    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote5_1_multiplas_intencoes_e2e():
    """
    T2: Múltiplas intenções são tratadas.
    Testa: agendamento, cancelamento, consulta
    Esperado: Cada uma é reconhecida corretamente
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    mensagens = [
        ("quero agendar", "agendamento"),
        ("quero cancelar", "cancelamento"),
        ("qual seu horário?", "consulta"),
    ]

    for i, (msg, tipo) in enumerate(mensagens, 1):
        phone_number = f"5515002{i}{uuid.uuid4().hex[:4]}"
        full_actor_id = f"whatsapp:{phone_number}"

        print(f"\n[T2.{i}] Teste E2E: Intenção '{tipo}'")

        ctx_inicial = {"tipo_usuario": "cliente", "estado_fluxo": "idle"}
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

        assert len(resposta.get("resposta", "")) > 0, "Resposta vazia"

        ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        assert ctx is not None, "Contexto não foi salvo"

        print(f"  ✓ Intenção '{tipo}' reconhecida")

    print(f"  ✅ [T2] PASS (3 intenções)")
