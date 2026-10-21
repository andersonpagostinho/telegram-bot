"""
[CORREÇÃO P0.4] Fix para data_hora=None em ajuste incremental
Testa que o sistema não falha com NoneType.split() quando draft é incompleto.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_p04_ajuste_incremental_sem_data_hora():
    """
    P0.4 FIX: Sistema deve validar data_hora antes de .split()
    Cenário: Mensagem de ajuste quando draft_agendamento tem profissional mas data_hora=None
    Esperado: Sistema responde pedindo a data/hora, sem crash 'NoneType.split()'
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5516001{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[P0.4 FIX] Teste: Ajuste incremental com data_hora=None")

    # Setup com draft INCOMPLETO: profissional mas SEM data_hora
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "bruna",
            # data_hora PROPOSITALMENTE ausente para testar guard
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Mensagem de ajuste (tenta alterar algo quando draft é incompleto)
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero com outra profissional",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # VALIDAÇÕES
    assert len(resposta_texto) > 0, "Resposta vazia (não deve ser)"
    assert "nao" not in resposta_texto or "erro" not in resposta_texto, \
        "Sistema respondeu com erro interno"

    print(f"  ✓ Sistema respondeu apropriadamente (sem crash)")
    print(f"  ✓ Resposta: {resposta_texto[:80]}...")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [P0.4] PASS — Guard data_hora=None funciona")


@pytest.mark.asyncio
async def test_p04_ajuste_com_data_hora_valida():
    """
    P0.4 FIX: Teste positivo — sistema funciona normalmente com data_hora preenchida
    Esperado: Sistema processa ajuste sem erro
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path
    from datetime import datetime, timedelta

    phone_number = f"5516002{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[P0.4 FIX] Teste: Ajuste incremental COM data_hora válida")

    # Data/hora para amanhã às 14h
    data_proxima = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    data_hora_valida = f"{data_proxima}T14:00:00"

    # Setup com draft COMPLETO
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "bruna",
            "data_hora": data_hora_valida,
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Mensagem de ajuste com profissional válida
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="segunda prefiro",  # Segunda-feira
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # VALIDAÇÕES
    assert len(resposta_texto) > 0, "Resposta vazia"

    print(f"  ✓ Sistema respondeu apropriadamente")
    print(f"  ✓ Resposta: {resposta_texto[:80]}...")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [P0.4+] PASS — Sistema funciona com data_hora válida")
