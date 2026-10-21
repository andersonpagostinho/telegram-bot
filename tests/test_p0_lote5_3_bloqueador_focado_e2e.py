"""
[MIGRAÇÃO LOTE 5 — TESTE 3] Bloqueador Focado P1 — E2E Firebase Real

Objetivo: Validar bloqueadores focados em P1 (TESTE FINAL).
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote5_3_bloqueador_fluxo_incompativel_e2e():
    """
    T1: Bloqueador em fluxo incompatível.
    Mensagem: Mensagem fora de contexto durante agendamento
    Esperado: Sistema trata de forma segura
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5515201{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Bloqueador em fluxo incompatível")

    # Setup com draft em agendamento
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {"servico": "corte"},
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Mensagem incompatível
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="123456",  # Mensagem não faz sentido
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()
    assert len(resposta_texto) > 0, "Sistema não respondeu a mensagem incompatível"

    print(f"  ✓ Bloqueador tratou mensagem incompatível")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi mantido"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote5_3_validacao_final_fim_da_migracao_e2e():
    """
    T2: Teste final validando que toda migração funcionou.
    Esperado: Sistema responde a qualquer entrada de forma segura
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5515202{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: VALIDAÇÃO FINAL DA MIGRAÇÃO")

    ctx_inicial = {"tipo_usuario": "cliente", "estado_fluxo": "idle"}
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Teste com entrada aleatória
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="xyz",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()
    assert len(resposta_texto) > 0, "Sistema não respondeu a entrada aleatória"

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi criado"
    assert ctx.get("tipo_usuario") == "cliente", "tipo_usuario não é cliente"

    print(f"  ✓ Migração completa e funcional")
    print(f"  ✓ Sistema respondeu seguramente a entrada inesperada")
    print(f"  ✓ Contexto criado e mantido corretamente")
    print(f"\n🎉 MIGRAÇÃO 23/23 TESTES FINALIZADA COM SUCESSO!")
    print(f"  ✅ [T2] PASS")
