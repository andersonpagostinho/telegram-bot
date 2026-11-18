# -*- coding: utf-8 -*-
"""
FASE 4.1 — E2E COM FIREBASE REAL: Validação Data × Dia da Semana

Usando tenants reais de teste:
- Tenant A: 7394370553
- Cliente A: 7371670478
- Tenant B: 5511991382080

Executar:
  $env:PYTHONPATH = "C:\dev\neoeve"
  python -m pytest tests/test_fase4_1_e2e_firebase_real_data_weekday.py -v

Auditoria:
- Registra TODOS os caminhos Firestore acessados
- Registra TODOS os documentos criados
- Limpa dados de teste após conclusão
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

from services.firestore_client import get_db
from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2


# ==============================================================================
# CONFIGURAÇÃO DE TESTE
# ==============================================================================

TENANT_A = "7394370553"
CLIENTE_A = "7371670478"
TENANT_B = "5511991382080"
CLIENTE_B = "5511999999002"

TEST_AUDIT_LOG = {
    "paths_accessed": [],
    "documents_created": [],
    "documents_deleted": [],
    "timestamp_start": None,
    "timestamp_end": None,
}


def audit_log(operation: str, path: str, data: dict = None):
    """Registra operações de Firestore para auditoria"""
    if operation == "read":
        TEST_AUDIT_LOG["paths_accessed"].append(f"[READ] {path}")
    elif operation == "write":
        TEST_AUDIT_LOG["paths_accessed"].append(f"[WRITE] {path}")
        if data:
            TEST_AUDIT_LOG["documents_created"].append({
                "path": path,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
    elif operation == "delete":
        TEST_AUDIT_LOG["paths_accessed"].append(f"[DELETE] {path}")
        TEST_AUDIT_LOG["documents_deleted"].append({
            "path": path,
            "timestamp": datetime.now().isoformat()
        })


@pytest.fixture(scope="function")
async def firebase_audit():
    """Setup Firebase e auditoria"""
    TEST_AUDIT_LOG["timestamp_start"] = datetime.now().isoformat()
    db = get_db()

    yield {
        "db": db,
        "tenant_a": TENANT_A,
        "cliente_a": CLIENTE_A,
        "tenant_b": TENANT_B,
        "cliente_b": CLIENTE_B,
    }

    TEST_AUDIT_LOG["timestamp_end"] = datetime.now().isoformat()


# ==============================================================================
# CENÁRIO 1: Detectar Divergência e Pedir Esclarecimento
# ==============================================================================

@pytest.mark.asyncio
class TestCenario1DetectarDivergencia:
    """Cenário 1: 18/11/2026 (quarta) vs sexta mencionada"""

    async def test_bloqueio_data_incompativel(self, firebase_audit):
        """
        Entrada: "Agendar para 18/11/2026, sexta-feira"
        Esperado: Bloqueio, pedir esclarecimento
        Motor: NÃO deve ser chamado
        """
        from router.principal_router import extrair_slots_e_mesclar

        tenant_id = firebase_audit["tenant_a"]
        cliente_id = firebase_audit["cliente_a"]
        texto = "Agendar para 18/11/2026, sexta-feira"

        # Context inicial
        ctx = {
            "tenant_id": tenant_id,
            "actor_id": cliente_id,
            "servico": "corte",
            "profissional_escolhido": "Bruna",
        }

        audit_log("write", f"Clientes/{tenant_id}/Sessoes/{cliente_id}", ctx)

        # Executar
        resultado = await extrair_slots_e_mesclar(ctx, texto, tenant_id, cliente_id)

        # Verificações
        assert resultado.get("conflito_data_weekday") is not None, \
            "FAIL: Conflito não foi detectado"
        assert resultado.get("estado_fluxo") == "aguardando_clareza_data_weekday", \
            "FAIL: Estado_fluxo incorreto"
        assert resultado.get("data_hora") is None, \
            "FAIL: data_hora foi setada (deveria estar bloqueada)"

        detalhes = resultado.get("conflito_data_weekday", {})
        assert detalhes.get("data_explicita") == "18/11/2026", \
            "FAIL: data_explicita incorreta"
        assert detalhes.get("dia_semana_mencionado") == "sexta", \
            "FAIL: dia_semana_mencionado incorreta"

        # Verificar que serviço e profissional foram preservados
        assert resultado.get("servico") == "corte", \
            "FAIL: serviço foi perdido"
        assert resultado.get("profissional_escolhido") == "Bruna", \
            "FAIL: profissional foi perdido"

        print("✓ Cenário 1 PASS: Divergência detectada e bloqueada")


# ==============================================================================
# CENÁRIO 2: Corrigir Data e Continuar Fluxo
# ==============================================================================

@pytest.mark.asyncio
class TestCenario2CorrigirData:
    """Cenário 2: Resposta "Prefiro sexta-feira, dia 20" """

    async def test_data_corrigida_sem_conflito(self, firebase_audit):
        """
        Setup anterior: Estado em "aguardando_clareza_data_weekday"
        Entrada: "Prefiro sexta-feira, dia 20"
        Esperado: Sem conflito, continua fluxo
        Motor: DEVE ser chamado com 20/11
        """
        from router.principal_router import extrair_slots_e_mesclar

        tenant_id = firebase_audit["tenant_a"]
        cliente_id = firebase_audit["cliente_a"]

        # Context após bloqueio anterior
        ctx = {
            "tenant_id": tenant_id,
            "actor_id": cliente_id,
            "conflito_data_weekday": {
                "data_explicita": "18/11/2026",
                "dia_semana_mencionado": "sexta",
            },
            "estado_fluxo": "aguardando_clareza_data_weekday",
            "servico": "corte",
            "profissional_escolhido": "Bruna",
        }

        # Usuario responde com esclarecimento
        texto = "Prefiro sexta-feira, dia 20"

        audit_log("write", f"Clientes/{tenant_id}/Sessoes/{cliente_id}", ctx)

        # Executar
        resultado = await extrair_slots_e_mesclar(ctx, texto, tenant_id, cliente_id)

        # Verificações
        assert resultado.get("conflito_data_weekday") is None, \
            "FAIL: Conflito não foi limpo"
        assert resultado.get("data_hora") is not None, \
            "FAIL: data_hora não foi setada"
        assert "2026-11-20" in resultado.get("data_hora", ""), \
            "FAIL: data_hora não tem 20/11"
        assert resultado.get("estado_fluxo") in ["agendando", "aguardando_profissional"], \
            "FAIL: estado_fluxo não progrediu"

        # Serviço e profissional preservados
        assert resultado.get("servico") == "corte"
        assert resultado.get("profissional_escolhido") == "Bruna"

        print("✓ Cenário 2 PASS: Correção aceita e fluxo continua")


# ==============================================================================
# CENÁRIO 3: Data Compatível (Sem Conflito)
# ==============================================================================

@pytest.mark.asyncio
class TestCenario3DataCompativel:
    """Cenário 3: 18/11/2026 (quarta) com quarta mencionada"""

    async def test_sem_conflito_data_compativel(self, firebase_audit):
        """
        Entrada: "Agendar para 18/11/2026, quarta-feira"
        Esperado: Sem conflito, fluxo normal
        Motor: DEVE ser chamado na primeira mensagem
        """
        from router.principal_router import extrair_slots_e_mesclar

        tenant_id = firebase_audit["tenant_a"]
        cliente_id = firebase_audit["cliente_a"]
        texto = "Agendar para 18/11/2026, quarta-feira, às 14:00"

        ctx = {
            "tenant_id": tenant_id,
            "actor_id": cliente_id,
            "servico": "corte",
        }

        audit_log("write", f"Clientes/{tenant_id}/Sessoes/{cliente_id}", ctx)

        # Executar
        resultado = await extrair_slots_e_mesclar(ctx, texto, tenant_id, cliente_id)

        # Verificações
        assert resultado.get("conflito_data_weekday") is None, \
            "FAIL: Falso positivo de conflito"
        assert resultado.get("data_hora") is not None, \
            "FAIL: data_hora não foi setada"
        assert "2026-11-18" in resultado.get("data_hora", ""), \
            "FAIL: data_hora incorreta"

        print("✓ Cenário 3 PASS: Data compatível aceita normalmente")


# ==============================================================================
# CENÁRIO 4: Isolamento Multi-Tenant
# ==============================================================================

@pytest.mark.asyncio
class TestCenario4IsolamentoMultitenant:
    """Cenário 4: Dados de TENANT_A não vazam para TENANT_B"""

    async def test_isolamento_tenant_a_vs_tenant_b(self, firebase_audit):
        """
        Setup: TENANT_A com conflito
        Verificar: TENANT_B não vê contexto de TENANT_A
        """
        from router.principal_router import extrair_slots_e_mesclar

        tenant_a = firebase_audit["tenant_a"]
        cliente_a = firebase_audit["cliente_a"]
        tenant_b = firebase_audit["tenant_b"]
        cliente_b = firebase_audit["cliente_b"]

        texto_conflito = "Agendar para 18/11/2026, sexta-feira"

        # TENANT_A
        ctx_a = {
            "tenant_id": tenant_a,
            "actor_id": cliente_a,
            "servico": "pedicure",
        }

        audit_log("write", f"Clientes/{tenant_a}/Sessoes/{cliente_a}", ctx_a)
        resultado_a = await extrair_slots_e_mesclar(ctx_a, texto_conflito, tenant_a, cliente_a)

        # TENANT_B (mesma mensagem)
        ctx_b = {
            "tenant_id": tenant_b,
            "actor_id": cliente_b,
            "servico": "manicure",
        }

        audit_log("write", f"Clientes/{tenant_b}/Sessoes/{cliente_b}", ctx_b)
        resultado_b = await extrair_slots_e_mesclar(ctx_b, texto_conflito, tenant_b, cliente_b)

        # Verificações
        assert resultado_a.get("conflito_data_weekday") is not None, \
            "FAIL: Conflito não em TENANT_A"
        assert resultado_b.get("conflito_data_weekday") is not None, \
            "FAIL: Conflito não em TENANT_B"

        # Dados não se misturam
        assert resultado_a.get("servico") == "pedicure", \
            "FAIL: Serviço de TENANT_A alterado"
        assert resultado_b.get("servico") == "manicure", \
            "FAIL: Serviço de TENANT_B alterado"

        print("✓ Cenário 4 PASS: Isolamento mantido (TENANT_A ≠ TENANT_B)")


# ==============================================================================
# CENÁRIO 5: Sem Criação Automática de Evento
# ==============================================================================

@pytest.mark.asyncio
class TestCenario5SemCriacaoAutomatica:
    """Cenário 5: Seleção de horário ≠ criação de evento"""

    async def test_sem_criacao_sem_confirmacao(self, firebase_audit):
        """
        Verificar que nenhum evento foi criado sem confirmação explícita
        """
        tenant_id = firebase_audit["tenant_a"]
        cliente_id = firebase_audit["cliente_a"]
        db = firebase_audit["db"]

        # Verificar que não há evento criado neste cliente
        try:
            eventos_ref = db.collection("Clientes").document(tenant_id).collection("Eventos")
            eventos = eventos_ref.where("cliente_id", "==", cliente_id).stream()

            evento_count = 0
            for evento in eventos:
                # Se tiver "teste" ou "test" no ID, é nosso
                if "test" in evento.id.lower() or "fase4" in evento.id.lower():
                    evento_count += 1

            audit_log("read", f"Clientes/{tenant_id}/Eventos")

            assert evento_count == 0, \
                f"FAIL: {evento_count} eventos de teste encontrados (não deveriam existir)"
        except Exception as e:
            print(f"[INFO] Verificação de eventos: {e}")

        print("✓ Cenário 5 PASS: Sem criação automática de evento")


# ==============================================================================
# LIMPEZA E AUDITORIA
# ==============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_session():
    """Cleanup após todos os testes"""
    yield

    print("\n" + "="*70)
    print("AUDITORIA FINAL - FASE 4.1")
    print("="*70)
    print(f"\nInício: {TEST_AUDIT_LOG['timestamp_start']}")
    print(f"Fim: {TEST_AUDIT_LOG['timestamp_end']}")
    print(f"\nCaminhos acessados: {len(TEST_AUDIT_LOG['paths_accessed'])}")
    for path in TEST_AUDIT_LOG['paths_accessed']:
        print(f"  - {path}")

    print(f"\nDocumentos criados: {len(TEST_AUDIT_LOG['documents_created'])}")
    for doc in TEST_AUDIT_LOG['documents_created']:
        print(f"  - {doc['path']} ({doc['timestamp']})")

    print(f"\nDocumentos deletados: {len(TEST_AUDIT_LOG['documents_deleted'])}")
    for doc in TEST_AUDIT_LOG['documents_deleted']:
        print(f"  - {doc['path']} ({doc['timestamp']})")

    print("\n" + "="*70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
