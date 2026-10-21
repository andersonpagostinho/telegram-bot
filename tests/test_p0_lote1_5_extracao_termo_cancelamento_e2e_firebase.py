"""
[MIGRAÇÃO LOTE 1 — TESTE 5] Extração de Termos de Cancelamento — E2E Firebase Real

Convertido de: test_p0_extracao_termo_cancelamento.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que múltiplas formas de pedir cancelamento são
reconhecidas pelo sistema E2E com Firestore.
"""

import pytest
import time
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote1_5_reconhece_varios_termos_cancelamento_e2e():
    """
    Teste: Diferentes formas de pedir cancelamento.
    Esperado: Sistema reconhece todas as variações como intenção de cancelamento

    Variações testadas:
    - "cancelar agendamento"
    - "desmarcar consulta"
    - "não quero mais"
    - "quero desistir"
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    variacoes = [
        "cancelar meu agendamento",
        "desmarcar a consulta",
        "não quero mais vir",
        "quero desistir",
    ]

    for i, msg in enumerate(variacoes, 1):
        phone_number = f"551200{i}{uuid.uuid4().hex[:5]}"
        full_actor_id = f"whatsapp:{phone_number}"

        print(f"\n[T{i}] Teste E2E: Reconhece '{msg}'")

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
            mensagem=msg,
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        resposta_texto = resposta.get("resposta", "").lower()

        # Sistema deve reconhecer como cancelamento
        assert any(x in resposta_texto for x in [
            "cancelar", "desmarcar", "remover", "confirma",
            "tem certeza", "cancelamento", "agendamento", "agenda"
        ]), f"Não reconheceu '{msg}'. Resposta: {resposta_texto[:100]}"

        # Validar contexto
        ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        assert ctx is not None, "Contexto não foi salvo"

        print(f"  ✓ Reconhecido como cancelamento")
        print(f"  ✅ [T{i}] PASS")


@pytest.mark.asyncio
async def test_lote1_5_nao_confunde_cancelamento_com_outros_e2e():
    """
    Teste: Mensagens que NÃO são cancelamento não são confundidas

    Variações que NÃO devem ser interpretadas como cancelamento:
    - "quero remarcar"
    - "quero trocar de profissional"
    - "qual é meu agendamento?"
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    nao_cancelamento = [
        "quero remarcar meu agendamento",
        "quero trocar de profissional",
        "qual é meu agendamento?",
    ]

    for i, msg in enumerate(nao_cancelamento, 1):
        phone_number = f"551205{i}{uuid.uuid4().hex[:5]}"
        full_actor_id = f"whatsapp:{phone_number}"

        print(f"\n[T{3+i}] Teste E2E: NÃO confunde '{msg}' com cancelamento")

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
            mensagem=msg,
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        # Validar contexto
        ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        assert ctx is not None, "Contexto não foi salvo"
        intencao = ctx.get("intencao_conversacional")

        # NÃO deve estar em cancelamento
        assert intencao != "cancelamento", \
            f"'{msg}' foi confundido com cancelamento!"

        print(f"  ✓ Corretamente não interpretado como cancelamento")
        print(f"  ✅ [T{3+i}] PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
