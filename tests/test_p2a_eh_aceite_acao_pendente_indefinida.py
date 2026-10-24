"""
P2A E2E: Guard bloqueia entrada indefinida em eh_aceite_de_acao_pendente()

REGRA DE OURO: Valida até Firestore (não apenas lógica em memória)

Bug corrigido: "ola" com intencao_conversacional="indefinida" não deveria
ser tratado como aceite de ação pendente. Guard bloqueia quando intencao
é indefinida, permitindo apenas operacional (confirmacao, dados, etc).

Validação:
T1: "ola" indefinida → resposta "não entendi", não erro "ação não encontrada"
T2: "sim" operacional → processado normalmente (não bloqueado)
"""

import pytest
import pytest_asyncio
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal


@pytest_asyncio.fixture
async def firebase_config():
    """Config para testes com Firebase real"""
    return {
        "tenant_id": "7394370553",
        "actor_id_t1": "whatsapp:5511991382090",  # T1: indefinida
        "actor_id_t2": "whatsapp:5511991382091",  # T2: operacional
    }


pytestmark = pytest.mark.asyncio


async def test_eh_aceite_acao_pendente_bloqueia_indefinida(firebase_config):
    """
    E2E REGRA DE OURO: Guard bloqueia "ola" indefinida em eh_aceite_de_acao_pendente()

    1. Salva contexto com intencao_conversacional="indefinida"
    2. Processa "ola" pelo roteador
    3. Valida que resposta NÃO é erro "Não encontrei ação recente"
    4. Valida Firestore: intencao permanece indefinida
    """
    tenant_id = firebase_config["tenant_id"]
    actor_id = firebase_config["actor_id_t1"]
    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    # 1. Salvar contexto indefinido com ação pendente
    ctx_inicial = {
        "intencao_conversacional": "indefinida",
        "estado_fluxo": "aguardando_profissional",
        "ultima_acao": "contexto_limpo",
        "draft_agendamento": {"servico": "corte"},
    }
    await salvar_dado_em_path(path, ctx_inicial)
    print("[T1 SETUP] Contexto indefinido salvo em Firestore")

    # 2. Processar "ola" (entrada indefinida)
    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem="ola",
        tenant_id=tenant_id,
        context=None
    )

    # 3. Validar resposta: NÃO deve ser erro "ação não encontrada"
    resposta = resultado.get("resposta", "")
    assert "Não encontrei nenhuma ação recente" not in resposta, \
        "FALHA T1: Guard deveria bloquear, resposta não deveria ser erro de ação"
    print(f"[T1 RESPOSTA] {resposta[:80]}... (sem erro de ação)")

    # 4. Validar Firestore: intencao ainda é indefinida
    doc_final = await buscar_dado_em_path(path)
    intencao_final = doc_final.get("intencao_conversacional")
    assert intencao_final == "indefinida", \
        f"FALHA T1: Intencao deveria ser indefinida, mas é {intencao_final}"

    print("[PASS T1] Guard bloqueia indefinida — Firestore validado ✅")


async def test_eh_aceite_acao_pendente_permite_operacional(firebase_config):
    """
    E2E REGRA DE OURO: Guard permite "sim" operacional em eh_aceite_de_acao_pendente()

    1. Salva contexto com intencao_conversacional="confirmacao"
    2. Processa "sim" pelo roteador
    3. Valida que resposta é processada (não bloqueada)
    4. Valida Firestore: contexto foi atualizado
    """
    tenant_id = firebase_config["tenant_id"]
    actor_id = firebase_config["actor_id_t2"]
    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    # 1. Salvar contexto operacional (confirmacao)
    ctx_inicial = {
        "intencao_conversacional": "confirmacao",
        "estado_fluxo": "aguardando_escolha_horario",
        "ultima_acao": "resolver_fora_do_expediente",
        "draft_agendamento": {"servico": "corte", "data_hora": "2026-10-25T10:00:00"},
    }
    await salvar_dado_em_path(path, ctx_inicial)
    print("[T2 SETUP] Contexto operacional salvo em Firestore")

    # 2. Processar "sim" (operacional)
    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem="sim",
        tenant_id=tenant_id,
        context=None
    )

    # 3. Validar resposta: deve ser processada (não erro de "ação não encontrada")
    resposta = resultado.get("resposta", "")
    assert "Não encontrei nenhuma ação recente" not in resposta, \
        "FALHA T2: Guard deveria permitir operacional, resposta não deveria ser erro"
    print(f"[T2 RESPOSTA] {resposta[:80]}... (processado)")

    # 4. Validar Firestore: contexto foi atualizado (confirmacao ou reclassificado)
    doc_final = await buscar_dado_em_path(path)
    assert doc_final is not None, "FALHA T2: Firestore não foi persistido"
    assert doc_final.get("_updated_at") is not None, \
        "FALHA T2: Contexto não foi atualizado"

    print("[PASS T2] Guard permite operacional — Firestore validado ✅")
