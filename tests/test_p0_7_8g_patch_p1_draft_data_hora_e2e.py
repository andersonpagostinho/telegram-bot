"""
P0.7.8G — Testes E2E com Firestore Real

OBJETIVO: Validar que P0.7.8J.7 (Guard semântico mínimo) não causa UnboundLocalError
e que draft_agendamento.data_hora é preservado quando cliente faz pergunta informativa.

Regra de Ouro: Todos os testes validam até Firestore real.
"""

import pytest
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from datetime import datetime


@pytest.mark.asyncio
async def test_t1_sem_unboundlocalerror_draft_preservado():
    """
    T1 E2E: Validar que pergunta informativa não causa UnboundLocalError
    e que draft é preservado.

    Reprodução exata do incidente:
    - Mensagem: "tem outra que faz manicure?"
    - Setup: draft_agendamento.data_hora = "2026-10-28T10:00:00"
    - Esperado:
      1. Sem UnboundLocalError
      2. draft.data_hora preservado
      3. Roteador retorna resposta (sem crash)
    """
    tenant_id = "7394370553"
    wa_id = "5511999999999"
    actor_canonico = f"whatsapp:{wa_id}"

    # SETUP: Contexto com draft herdado
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "aguardando_profissional",
        "motivo_estado": "profissional_nao_atende_servico",
        "servico": "manicure",
        "data_hora": None,  # SEM data em contexto
        "aguardando_confirmacao_agendamento": False,
        "draft_agendamento": {
            "data_hora": "2026-10-28T10:00:00",  # Data no draft
            "servico": "manicure",
            "profissional": None
        }
    }

    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_canonico}",
        dados=ctx_inicial
    )
    await atualizar_dado_em_path(
        path=f"Clientes/{wa_id}/MemoriaTemporaria/contexto",
        dados=ctx_inicial
    )

    # EXECUTE: Pergunta informativa que causava UnboundLocalError
    try:
        resultado = await roteador_principal(
            user_id=wa_id,
            mensagem="tem outra que faz manicure?",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )
        resposta = resultado.get("resposta", "")
        print(f"\n[T1] Resposta recebida: {resposta[:150]}")
    except UnboundLocalError as e:
        pytest.fail(f"❌ FAIL: UnboundLocalError não deveria ocorrer! {e}")
    except Exception as e:
        pytest.fail(f"❌ FAIL: Exceção inesperada: {type(e).__name__}: {e}")

    # VALIDAR 1: Resposta não vazia (roteador completou sem crash)
    assert resposta, "Resposta não deveria ser vazia"
    assert "erro" not in resposta.lower() or "unboundlocal" not in resposta.lower(), \
        f"Resposta não deveria conter erro de UnboundLocalError. Recebeu: {resposta}"

    # VALIDAR 2: draft_agendamento.data_hora deve ser preservado
    sessao_pos = await buscar_dado_em_path(
        path=f"Clientes/{wa_id}/MemoriaTemporaria/contexto"
    )
    draft = sessao_pos.get("draft_agendamento") or {}
    assert draft.get("data_hora") == "2026-10-28T10:00:00", \
        f"draft.data_hora deveria ser preservado ('2026-10-28T10:00:00'), mas é: {draft.get('data_hora')}"

    # VALIDAR 3: servico preservado
    assert draft.get("servico") == "manicure", \
        f"draft.servico deveria ser preservado, mas é: {draft.get('servico')}"

    print("✅ T1 E2E PASS: Sem UnboundLocalError, draft preservado (Firestore real)")


@pytest.mark.asyncio
async def test_t2_variacao_pergunta_sem_crash():
    """
    T2 E2E: Testar variação de pergunta informativa (não crashes)

    Objetivo: Validar que guard semântico detecta múltiplas formas de pergunta
    """
    tenant_id = "7394370553"
    wa_id = "5511988888888"
    actor_canonico = f"whatsapp:{wa_id}"

    # SETUP
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "aguardando_profissional",
        "motivo_estado": "profissional_nao_atende_servico",
        "servico": "manicure",
        "data_hora": None,
        "aguardando_confirmacao_agendamento": False,
        "draft_agendamento": {
            "data_hora": "2026-10-28T14:00:00",
            "servico": "manicure",
            "profissional": None
        }
    }

    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_canonico}",
        dados=ctx_inicial
    )
    await atualizar_dado_em_path(
        path=f"Clientes/{wa_id}/MemoriaTemporaria/contexto",
        dados=ctx_inicial
    )

    # EXECUTE: Variação de pergunta
    try:
        resultado = await roteador_principal(
            user_id=wa_id,
            mensagem="qual outro profissional faz manicure?",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )
        resposta = resultado.get("resposta", "")
        print(f"\n[T2] Resposta recebida: {resposta[:150]}")
    except UnboundLocalError as e:
        pytest.fail(f"❌ FAIL: UnboundLocalError com variação de pergunta! {e}")
    except Exception as e:
        pytest.fail(f"❌ FAIL: Exceção inesperada: {type(e).__name__}: {e}")

    # VALIDAR: Resposta obtida, draft preservado
    assert resposta, "Resposta não deveria ser vazia"

    sessao_pos = await buscar_dado_em_path(
        path=f"Clientes/{wa_id}/MemoriaTemporaria/contexto"
    )
    draft = sessao_pos.get("draft_agendamento") or {}
    assert draft.get("data_hora") == "2026-10-28T14:00:00", \
        f"draft.data_hora deveria ser preservado, mas é: {draft.get('data_hora')}"

    print("✅ T2 E2E PASS: Variação de pergunta sem crash, draft preservado (Firestore real)")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
