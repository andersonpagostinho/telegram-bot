"""
FASE 7: Testes adicionais de retomada (isolamento + casos extremos)
"""

import pytest
from datetime import datetime, timedelta
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from utils.contexto_temporario import salvar_sessao_temporaria, carregar_sessao_temporaria


@pytest.mark.asyncio
async def test_retomada_tenant_diferente():
    """Isolamento: Não recuperar contexto de outro tenant"""
    tenant_a = "7394370553"
    tenant_b = "9999999999"
    actor_id = "test_isolamento_tenant"

    # Salvar em tenant A
    contexto_a = {
        "profissional_escolhido": "Bruna",
        "draft_agendamento": {"profissional": "Bruna", "serviço": "manicure"},
        "_tenant_id_guard": tenant_a
    }

    await salvar_sessao_temporaria(actor_id, contexto_a, tenant_a)

    # Tentar carregar com tenant B (deve falhar ou retornar vazio)
    contexto_b = await carregar_sessao_temporaria(actor_id, tenant_b)

    # Validar isolamento
    assert contexto_b is None or contexto_b == {}, \
        f"Contexto de tenant A não deve ser acessível em tenant B"

    print("✅ Test: Isolamento tenant PASS")


@pytest.mark.asyncio
async def test_retomada_actor_diferente():
    """Isolamento: Não recuperar contexto de outro actor"""
    tenant_id = "7394370553"
    actor_a = "test_actor_a"
    actor_b = "test_actor_b"

    # Salvar com actor A
    contexto_a = {
        "profissional_escolhido": "Bruna",
        "draft_agendamento": {"profissional": "Bruna"},
        "_actor_id": actor_a
    }

    await salvar_sessao_temporaria(actor_a, contexto_a, tenant_id)

    # Tentar carregar com actor B (deve retornar vazio)
    contexto_b = await carregar_sessao_temporaria(actor_b, tenant_id)

    # Validar isolamento
    assert not contexto_b or not contexto_b.get("draft_agendamento"), \
        f"Contexto de actor A não deve ser acessível em actor B"

    print("✅ Test: Isolamento actor PASS")


@pytest.mark.asyncio
async def test_retomada_draft_incompleto():
    """Casos extremos: Draft com campos faltantes"""
    tenant_id = "7394370553"
    actor_id = "test_draft_incompleto"

    # Draft sem profissional (incompleto)
    contexto = {
        "draft_agendamento": {
            "serviço": "manicure",
            # Falta: profissional, data_hora
        }
    }

    await salvar_sessao_temporaria(actor_id, contexto, tenant_id)

    # Recuperar
    contexto_recuperado = await carregar_sessao_temporaria(actor_id, tenant_id)

    # Validar que existe mas está incompleto
    assert contexto_recuperado is not None
    assert contexto_recuperado["draft_agendamento"]["serviço"] == "manicure"
    assert "profissional" not in contexto_recuperado["draft_agendamento"]

    print("✅ Test: Draft incompleto PASS")


@pytest.mark.asyncio
async def test_retomada_horario_futuro_valido():
    """Validação: Horário futuro é válido para retomada"""
    tenant_id = "7394370553"
    actor_id = "test_horario_futuro"

    # Draft com horário futuro (válido)
    futuro = (datetime.now() + timedelta(days=2)).isoformat()
    contexto = {
        "draft_agendamento": {
            "profissional": "Bruna",
            "serviço": "manicure",
            "data_hora": futuro
        }
    }

    await salvar_sessao_temporaria(actor_id, contexto, tenant_id)

    # Recuperar
    contexto_recuperado = await carregar_sessao_temporaria(actor_id, tenant_id)

    # Validar que foi recuperado e data está correta
    assert contexto_recuperado is not None
    assert contexto_recuperado["draft_agendamento"]["data_hora"] == futuro

    print("✅ Test: Horário futuro válido PASS")


@pytest.mark.asyncio
async def test_retomada_preservacao_campos_validos():
    """Validação: Campos válidos são preservados mesmo com alguns inválidos"""
    tenant_id = "7394370553"
    actor_id = "test_campos_validos"

    # Context com alguns campos válidos
    contexto = {
        "profissional_escolhido": "Bruna",  # Válido
        "draft_agendamento": {
            "profissional": "Bruna",  # Válido
            "serviço": "manicure",  # Válido
            "data_hora": (datetime.now() + timedelta(days=1)).isoformat(),  # Válido
            "estado_fluxo": "aguardando_confirmacao"  # Válido
        },
        "estado_fluxo": "aguardando_confirmacao",
        "_tenant_id_guard": tenant_id
    }

    await salvar_sessao_temporaria(actor_id, contexto, tenant_id)

    # Recuperar
    contexto_recuperado = await carregar_sessao_temporaria(actor_id, tenant_id)

    # Validar que todos os campos foram preservados
    assert contexto_recuperado is not None
    assert contexto_recuperado["profissional_escolhido"] == "Bruna"
    assert contexto_recuperado["draft_agendamento"]["profissional"] == "Bruna"
    assert contexto_recuperado["_tenant_id_guard"] == tenant_id

    print("✅ Test: Preservação de campos válidos PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
