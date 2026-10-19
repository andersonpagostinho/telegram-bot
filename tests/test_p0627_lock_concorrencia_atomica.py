"""
TESTES DE CONCORRÊNCIA P0.6.2.7 — Lock Atomicamente Seguro

Validar que o mecanismo de lock em criar_evento_com_lock() é atomicamente
seguro contra race conditions. Duas requisições simultâneas para o mesmo
profissional/horário devem resultar em apenas 1 evento criado.

Requisitos:
- Usar Firebase real (não mock)
- Sincronização real entre tarefas (asyncio.gather com timing)
- Verificar estado final no Firestore, não apenas retornos
- Testar múltiplos cenários de concorrência
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from pytz import timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Firebase
import firebase_admin
from firebase_admin import credentials, firestore

# Services
from services.agenda_lock_service import criar_evento_com_lock, gerar_buckets_tempo
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    buscar_subcolecao,
    deletar_dado_em_path,
    atualizar_dado_em_path,
)
from services.firestore_client import get_db

FUSO_BR = timezone("America/Sao_Paulo")

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="function")
def e2e_tenant_id():
    """ID único do tenant para este teste."""
    return f"test_p0627_lock_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def e2e_dono_id(e2e_tenant_id):
    """ID do dono (coincide com tenant_id para isolamento)."""
    return e2e_tenant_id  # MESMO ID que tenant!


@pytest.fixture(scope="function")
async def e2e_setup_agendamento(e2e_tenant_id, e2e_dono_id):
    """
    Setup: Cria profissionais, serviços e configuração.

    Limpa automaticamente ao fim.
    """
    db = firestore.client()

    # Criar configuração do tenant
    config_doc = {
        "nome": "Salão Teste Concorrência",
        "email": f"teste_concorrencia_{uuid.uuid4().hex[:4]}@test.local",
        "telefone": "11999999999",
        "fuso": "America/Sao_Paulo",
        "expediente": {
            "segunda": {"abertura": "09:00", "fechamento": "18:00"},
            "terca": {"abertura": "09:00", "fechamento": "18:00"},
            "quarta": {"abertura": "09:00", "fechamento": "18:00"},
            "quinta": {"abertura": "09:00", "fechamento": "18:00"},
            "sexta": {"abertura": "09:00", "fechamento": "18:00"},
            "sabado": {"abertura": "09:00", "fechamento": "14:00"},
            "domingo": {"abertura": None, "fechamento": None}
        }
    }
    await salvar_dado_em_path(f"Clientes/{e2e_tenant_id}/Configuracao", config_doc)

    # Criar profissionais
    prof_bruna = {
        "nome": "Bruna",
        "ativo": True,
        "servicos": ["manicure", "pedicure"]
    }
    prof_gloria = {
        "nome": "Glória",
        "ativo": True,
        "servicos": ["corte", "coloracao"]
    }
    await salvar_dado_em_path(f"Clientes/{e2e_tenant_id}/Profissionais/Bruna", prof_bruna)
    await salvar_dado_em_path(f"Clientes/{e2e_tenant_id}/Profissionais/Gloria", prof_gloria)

    yield {
        "tenant_id": e2e_tenant_id,
        "dono_id": e2e_dono_id,
        "profissionais": ["Bruna", "Gloria"],
        "servicos": ["manicure", "pedicure", "corte", "coloracao"]
    }

    # CLEANUP
    try:
        # Deletar todos os eventos
        eventos_ref = db.collection("Clientes").document(e2e_tenant_id).collection("Eventos")
        for doc in eventos_ref.stream():
            doc.reference.delete()

        # Deletar todos os locks
        locks_ref = db.collection("Clientes").document(e2e_tenant_id).collection("AgendaLocks")
        for doc in locks_ref.stream():
            doc.reference.delete()

        # Deletar profissionais
        profs_ref = db.collection("Clientes").document(e2e_tenant_id).collection("Profissionais")
        for doc in profs_ref.stream():
            doc.reference.delete()

        # Deletar config
        db.collection("Clientes").document(e2e_tenant_id).collection("Configuracao").document("default").delete() if \
            db.collection("Clientes").document(e2e_tenant_id).collection("Configuracao").document("default").get().exists else None
        db.collection("Clientes").document(e2e_tenant_id).delete()

        print(f"✅ Cleanup completo para tenant {e2e_tenant_id}")
    except Exception as e:
        print(f"⚠️ Erro durante cleanup: {e}")


# ============================================================
# TESTE 1: Duas requisições simultâneas, mesmo slot
# Resultado esperado: Apenas 1 evento criado
# ============================================================

@pytest.mark.asyncio
async def test_concorrencia_duas_requisicoes_mesmo_slot(e2e_setup_agendamento):
    """
    TESTE: Disputar o mesmo slot simultaneamente.

    1. Dispara 2 requisições assíncronas para criar evento em 14:00-15:00
    2. Ambas tentam criar com profissional="Bruna"
    3. Verifica no Firestore: apenas 1 evento deve existir
    4. A outra requisição deve ter falhado com tipo_erro="lock_existente"
    """
    setup = e2e_setup_agendamento
    tenant_id = setup["tenant_id"]
    dono_id = setup["dono_id"]

    # Dados do agendamento
    data_evento = datetime.now(FUSO_BR).date().isoformat()
    hora_inicio = "14:00"
    hora_fim = "15:00"

    evento_base = {
        "cliente_id": "cliente_teste_001",
        "profissional": "Bruna",
        "data": data_evento,
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "servico": "manicure",
        "duracao_minutos": 60,
        "confirmado": True,
        "status": "confirmado"
    }

    # Criar dois eventos com IDs diferentes mas mesmo slot
    evento_1 = {**evento_base, "id": f"evento_1_{uuid.uuid4().hex[:4]}"}
    evento_2 = {**evento_base, "id": f"evento_2_{uuid.uuid4().hex[:4]}"}

    # 🔥 DISPARA AMBAS SIMULTANEAMENTE
    resultado_1, resultado_2 = await asyncio.gather(
        criar_evento_com_lock(dono_id, evento_1, evento_1["id"]),
        criar_evento_com_lock(dono_id, evento_2, evento_2["id"]),
        return_exceptions=False
    )

    # ✅ VALIDAÇÃO 1: Exatamente uma deve ter sucesso
    um_sucesso = (resultado_1.get("ok") and not resultado_2.get("ok")) or \
                 (not resultado_1.get("ok") and resultado_2.get("ok"))

    assert um_sucesso, f"Esperado: 1 sucesso + 1 falha. Recebido: R1.ok={resultado_1.get('ok')}, R2.ok={resultado_2.get('ok')}"

    # ✅ VALIDAÇÃO 2: Falha deve ser de lock/conflito
    resultado_falha = resultado_2 if resultado_1.get("ok") else resultado_1
    tipo_erro = resultado_falha.get("tipo_erro")
    assert tipo_erro in ["lock_existente", "conflito"], \
        f"Tipo de erro esperado: lock_existente ou conflito. Recebido: {tipo_erro}"

    # ✅ VALIDAÇÃO 3: Verificar no Firestore que apenas 1 evento foi criado
    db = firestore.client()
    eventos = list(db.collection("Clientes").document(tenant_id).collection("Eventos").stream())

    # Contar eventos do nosso slot
    eventos_no_slot = [
        e for e in eventos
        if e.to_dict().get("profissional", "").lower() == "bruna" and
           e.to_dict().get("data") == data_evento
    ]

    assert len(eventos_no_slot) == 1, \
        f"Esperado: 1 evento no Firestore. Encontrado: {len(eventos_no_slot)}"

    print(f"✅ TEST_CONCORRENCIA_DUAS_REQUISICOES_MESMO_SLOT PASS")
    print(f"   - Um sucesso, um bloqueado com tipo_erro={tipo_erro}")
    print(f"   - Firestore contém exatamente 1 evento para o slot")


# ============================================================
# TESTE 2: Profissionais diferentes, sem bloqueio mútuo
# Resultado esperado: 2 eventos criados (um para cada prof)
# ============================================================

@pytest.mark.asyncio
async def test_concorrencia_profissionais_diferentes_sem_bloqueio(e2e_setup_agendamento):
    """
    TESTE: Dois profissionais DIFERENTES no mesmo horário.

    1. Dispara 2 requisições para 14:00-15:00
    2. Uma com Bruna, outra com Glória
    3. Ambas devem ter sucesso (sem bloqueio cruzado)
    4. Firestore deve ter 2 eventos
    """
    setup = e2e_setup_agendamento
    tenant_id = setup["tenant_id"]
    dono_id = setup["dono_id"]

    data_evento = datetime.now(FUSO_BR).date().isoformat()

    evento_bruna = {
        "cliente_id": "cliente_001",
        "profissional": "Bruna",
        "data": data_evento,
        "hora_inicio": "14:00",
        "hora_fim": "15:00",
        "servico": "manicure",
        "duracao_minutos": 60,
        "confirmado": True,
        "status": "confirmado",
        "id": f"evento_bruna_{uuid.uuid4().hex[:4]}"
    }

    evento_gloria = {
        "cliente_id": "cliente_002",
        "profissional": "Gloria",
        "data": data_evento,
        "hora_inicio": "14:00",
        "hora_fim": "15:00",
        "servico": "corte",
        "duracao_minutos": 60,
        "confirmado": True,
        "status": "confirmado",
        "id": f"evento_gloria_{uuid.uuid4().hex[:4]}"
    }

    # Dispara ambas simultaneamente
    resultado_bruna, resultado_gloria = await asyncio.gather(
        criar_evento_com_lock(dono_id, evento_bruna, evento_bruna["id"]),
        criar_evento_com_lock(dono_id, evento_gloria, evento_gloria["id"]),
        return_exceptions=False
    )

    # ✅ VALIDAÇÃO: Ambas devem ter sucesso
    assert resultado_bruna.get("ok"), f"Bruna falhou: {resultado_bruna.get('motivo')}"
    assert resultado_gloria.get("ok"), f"Glória falhou: {resultado_gloria.get('motivo')}"

    # ✅ Verificar no Firestore
    db = firestore.client()
    eventos = list(db.collection("Clientes").document(tenant_id).collection("Eventos").stream())

    eventos_no_slot = [
        e for e in eventos
        if e.to_dict().get("data") == data_evento and \
           e.to_dict().get("hora_inicio") == "14:00"
    ]

    assert len(eventos_no_slot) == 2, \
        f"Esperado: 2 eventos (Bruna + Glória). Encontrado: {len(eventos_no_slot)}"

    print(f"✅ TEST_CONCORRENCIA_PROFISSIONAIS_DIFERENTES_SEM_BLOQUEIO PASS")
    print(f"   - Ambas requisições tiveram sucesso")
    print(f"   - Firestore contém 2 eventos (sem bloqueio cruzado)")


# ============================================================
# TESTE 3: Três requisições, mesmo slot
# Resultado esperado: 1 sucesso, 2 bloqueados
# ============================================================

@pytest.mark.asyncio
async def test_concorrencia_tres_requisicoes_mesmo_slot(e2e_setup_agendamento):
    """
    TESTE: Escalação de concorrência.

    1. Dispara 3 requisições simultâneas para mesmo slot
    2. Exatamente 1 deve ter sucesso
    3. 2 devem ser bloqueadas
    4. Firestore deve ter 1 evento
    """
    setup = e2e_setup_agendamento
    tenant_id = setup["tenant_id"]
    dono_id = setup["dono_id"]

    data_evento = datetime.now(FUSO_BR).date().isoformat()

    eventos = [
        {
            "cliente_id": f"cliente_{i}",
            "profissional": "Bruna",
            "data": data_evento,
            "hora_inicio": "16:00",
            "hora_fim": "17:00",
            "servico": "pedicure",
            "duracao_minutos": 60,
            "confirmado": True,
            "status": "confirmado",
            "id": f"evento_{i}_{uuid.uuid4().hex[:4]}"
        }
        for i in range(3)
    ]

    resultados = await asyncio.gather(
        *[criar_evento_com_lock(dono_id, e, e["id"]) for e in eventos],
        return_exceptions=False
    )

    # ✅ Exatamente 1 sucesso
    sucessos = sum(1 for r in resultados if r.get("ok"))
    assert sucessos == 1, f"Esperado: 1 sucesso. Encontrado: {sucessos}"

    # ✅ Exatamente 2 falhas
    falhas = sum(1 for r in resultados if not r.get("ok"))
    assert falhas == 2, f"Esperado: 2 falhas. Encontrado: {falhas}"

    # ✅ Firestore
    db = firestore.client()
    eventos_db = list(db.collection("Clientes").document(tenant_id).collection("Eventos").stream())
    assert len(eventos_db) == 1, f"Esperado: 1 evento. Encontrado: {len(eventos_db)}"

    print(f"✅ TEST_CONCORRENCIA_TRES_REQUISICOES_MESMO_SLOT PASS")


# ============================================================
# TESTE 4: Reenvio sem duplicação (idempotência)
# ============================================================

@pytest.mark.asyncio
async def test_concorrencia_idempotencia_reenvio(e2e_setup_agendamento):
    """
    TESTE: Reenvio da mesma requisição.

    1. Cria evento (sucesso)
    2. Reenvia o MESMO evento (deve retornar duplicado, sem erro)
    3. Firestore tem 1 evento
    """
    setup = e2e_setup_agendamento
    tenant_id = setup["tenant_id"]
    dono_id = setup["dono_id"]

    data_evento = datetime.now(FUSO_BR).date().isoformat()
    event_id = f"evento_idempotente_{uuid.uuid4().hex[:4]}"

    evento = {
        "cliente_id": "cliente_test",
        "profissional": "Bruna",
        "data": data_evento,
        "hora_inicio": "10:00",
        "hora_fim": "11:00",
        "servico": "manicure",
        "duracao_minutos": 60,
        "confirmado": True,
        "status": "confirmado",
        "id": event_id
    }

    # Primeira vez
    resultado_1 = await criar_evento_com_lock(dono_id, evento, event_id)
    assert resultado_1.get("ok"), f"Primeira criação falhou: {resultado_1.get('motivo')}"

    # Segunda vez (mesma requisição)
    resultado_2 = await criar_evento_com_lock(dono_id, evento, event_id)
    assert resultado_2.get("ok"), f"Reenvio falhou: {resultado_2.get('motivo')}"
    assert resultado_2.get("duplicado"), "Reenvio deveria indicar duplicado"

    # Firestore
    db = firestore.client()
    eventos = list(db.collection("Clientes").document(tenant_id).collection("Eventos").stream())
    assert len(eventos) == 1, f"Esperado: 1 evento. Encontrado: {len(eventos)}"

    print(f"✅ TEST_CONCORRENCIA_IDEMPOTENCIA_REENVIO PASS")


# ============================================================
# TESTE 5: Isolamento por tenant
# ============================================================

@pytest.mark.asyncio
async def test_concorrencia_isolamento_tenants():
    """
    TESTE: Dois tenants diferentes.

    1. Cria dois tenants diferentes
    2. Tenta criar evento SIMULTANEAMENTE com mesmo slot em cada tenant
    3. Ambos devem ter sucesso (isolamento)
    """
    tenant_1 = f"test_p0627_tenant1_{uuid.uuid4().hex[:4]}"
    tenant_2 = f"test_p0627_tenant2_{uuid.uuid4().hex[:4]}"

    data_evento = datetime.now(FUSO_BR).date().isoformat()

    evento_1 = {
        "cliente_id": "cliente_1",
        "profissional": "Bruna",
        "data": data_evento,
        "hora_inicio": "12:00",
        "hora_fim": "13:00",
        "servico": "manicure",
        "duracao_minutos": 60,
        "confirmado": True,
        "status": "confirmado",
        "id": f"evento_tenant1_{uuid.uuid4().hex[:4]}"
    }

    evento_2 = {
        "cliente_id": "cliente_2",
        "profissional": "Bruna",
        "data": data_evento,
        "hora_inicio": "12:00",
        "hora_fim": "13:00",
        "servico": "pedicure",
        "duracao_minutos": 60,
        "confirmado": True,
        "status": "confirmado",
        "id": f"evento_tenant2_{uuid.uuid4().hex[:4]}"
    }

    resultado_1, resultado_2 = await asyncio.gather(
        criar_evento_com_lock(tenant_1, evento_1, evento_1["id"]),
        criar_evento_com_lock(tenant_2, evento_2, evento_2["id"]),
        return_exceptions=False
    )

    # ✅ Ambos devem ter sucesso (sem bloqueio cruzado)
    assert resultado_1.get("ok"), f"Tenant 1 falhou: {resultado_1.get('motivo')}"
    assert resultado_2.get("ok"), f"Tenant 2 falhou: {resultado_2.get('motivo')}"

    # Cleanup
    try:
        db = firestore.client()
        db.collection("Clientes").document(tenant_1).delete()
        db.collection("Clientes").document(tenant_2).delete()
    except:
        pass

    print(f"✅ TEST_CONCORRENCIA_ISOLAMENTO_TENANTS PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
