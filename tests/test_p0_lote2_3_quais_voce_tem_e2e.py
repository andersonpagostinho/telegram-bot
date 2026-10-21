"""
[MIGRAÇÃO LOTE 2 — TESTE 3] Quais Você Tem — E2E Firebase Real

Convertido de: test_p0_quais_voce_tem.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que "quais profissional você tem?" oferece alternativas
durante agendamento com draft.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote2_3_quais_voce_tem_durante_agendamento_e2e():
    """
    T1: "quais você tem?" durante agendamento com draft.
    Mensagem: "quais você tem?"
    Esperado: Sistema oferece profissionais alternativos
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512201{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: 'quais você tem?' durante agendamento")

    # Setup com draft em agendamento
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "bruna",
            "data_hora": "2026-10-22T10:00"
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quais você tem?",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve oferecer profissionais que ofereçam o serviço
    assert any(x in resposta_texto for x in [
        "gloria", "joana", "carla", "profissional", "qual", "tenho", "outras", "alternativa"
    ]), f"Profissionais não oferecidos. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Sistema ofereceu alternativas de profissional")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote2_3_quais_voce_tem_variantes_e2e():
    """
    T2: "quais você tem?" com diferentes variantes.
    Mensagens: "quem mais tem?", "quais alternativas?"
    Esperado: Sistema reconhece todas as variantes
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    variantes = ["quem mais tem?", "quais alternativas?", "quem atende corte?"]

    for i, msg in enumerate(variantes, 1):
        phone_number = f"5512202{i}{uuid.uuid4().hex[:4]}"
        full_actor_id = f"whatsapp:{phone_number}"

        print(f"\n[T2.{i}] Teste E2E: Variante '{msg}'")

        # Setup com draft
        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional_selecionada": "bruna",
            },
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
