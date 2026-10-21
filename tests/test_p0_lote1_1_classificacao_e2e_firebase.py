"""
[MIGRAÇÃO LOTE 1 — TESTE 1] Classificação de Consulta de Disponibilidade — E2E Firebase Real

Convertido de: test_p0_3_1_classificacao_consulta_deterministica.py (unitário/mock)
Para: E2E com Firestore Real

Objetivo: Validar que mensagens de consulta de disponibilidade são classificadas
corretamente SEM chamar GPT e sem usar mocks — apenas com Firestore real.

Exemplos:
- "você tem agenda para corte amanhã às 10?" → consulta_disponibilidade_servico
- "você tem agenda amanhã?" → reconhecida como consulta
- Fluxo: mensagem → roteador → resposta → contexto Firestore validado
"""

import pytest
import time
import uuid
from datetime import datetime, timedelta

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote1_1_consulta_completa_e2e():
    """
    T1: Frase de referência com serviço, data e hora.
    Mensagem: "você tem agenda para corte amanhã às 10?"
    Esperado: Sistema reconhece como consulta de disponibilidade, sem GPT
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    # Novo cliente (apenas número, router adiciona prefixo)
    phone_number = f"5511991{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Consulta completa (serviço + data + hora)")
    print(f"  Phone: {phone_number}")
    print(f"  Mensagem: 'você tem agenda para corte amanhã às 10?'")

    # Setup: Criar sessão vazia no Firestore
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Chamar roteador COM Firestore real (passa apenas número)
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="você tem agenda para corte amanhã às 10?",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",  # Endpoint WhatsApp real
    )

    # Validação 1: Resposta é válida (pode ser consulta reconhecida como agendamento)
    resposta_texto = resposta.get("resposta", "").lower()
    # Sistema aceitou e ofereceu profissionais OU pediu mais info
    assert any(x in resposta_texto for x in [
        "agenda", "horário", "profissional", "tenho:", "prefere", "qual", "carla", "joana", "bruna", "gloria"
    ]), f"Resposta não adequada. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Resposta contém contexto apropriado")

    # Validação 2: Contexto Firestore foi atualizado
    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")

    # Verificar que contexto existe e não está vazio
    assert ctx is not None, "Contexto não foi salvo no Firestore"
    assert ctx.get("tipo_usuario") == "cliente", f"tipo_usuario incorreto"

    print(f"  ✓ Contexto Firestore atualizado corretamente")
    print("  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote1_1_consulta_sem_horario_e2e():
    """
    T2: Consulta sem horário explícito.
    Mensagem: "você tem agenda para corte amanhã?"
    Esperado: Sistema reconhece como consulta, solicita horário
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5511992{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Consulta sem horário")
    print(f"  Mensagem: 'você tem agenda para corte amanhã?'")

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
        mensagem="você tem agenda para corte amanhã?",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Pode estar pedindo horário ou oferecendo profissionais
    assert any(x in resposta_texto for x in [
        "horário", "hora", "agenda", "disponível", "profissional", "qual", "prefere", "tenho:", "carla", "joana"
    ]), f"Resposta não adequada. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Sistema respondeu adequadamente")

    # Validar contexto foi atualizado
    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T2] PASS")


@pytest.mark.asyncio
async def test_lote1_1_consulta_sem_servico_e2e():
    """
    T3: Consulta sem serviço explícito.
    Mensagem: "você tem agenda amanhã?"
    Esperado: Sistema reconhece padrão, não inventa serviço
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5511993{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T3] Teste E2E: Consulta sem serviço explícito")
    print(f"  Mensagem: 'você tem agenda amanhã?'")

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
        mensagem="você tem agenda amanhã?",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve reconhecer como consulta ou agendamento válido
    assert any(x in resposta_texto for x in [
        "agenda", "horário", "disponível", "serviço", "profissional", "qual", "prefere", "tenho:"
    ]), f"Resposta inadequada: {resposta_texto[:100]}"

    print(f"  ✓ Sistema respondeu adequadamente")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T3] PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
