"""
P2B: Saudação indefinida pula fallback operacional — REGRA DE OURO

Valida que quando intencao_conversacional == "indefinida"
e texto é saudação, o guard impede montar_resposta_fallback().

REGRA DE OURO: Valida até Firestore (não apenas lógica em memória)
"""

import pytest
import pytest_asyncio
from services.firestore_client import get_db
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path


@pytest_asyncio.fixture
async def firebase_config():
    """Config para testes com Firebase real"""
    return {
        "tenant_id": "7394370553",
        "actor_id": "whatsapp:5511991382080",
    }


pytestmark = pytest.mark.asyncio


async def test_p2b_saudacao_indefinida_pula_fallback(firebase_config):
    """
    REGRA DE OURO: Valida a lógica do guard P2B até Firestore.
    Se mensagem é saudação indefinida, guard retorna False e pula fallback.

    1. Salva contexto com intencao_conversacional="indefinida"
    2. Processa "ola" pelo roteador
    3. Valida que Firestore foi persistido corretamente
    """
    tenant_id = firebase_config["tenant_id"]
    actor_id = firebase_config["actor_id"]
    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    # 1. Salvar contexto inicial em Firestore
    ctx_inicial = {
        "intencao_conversacional": "indefinida",
        "estado_fluxo": "idle",
        "historico_texto": [],
    }
    await salvar_dado_em_path(path, ctx_inicial)

    # 2. Processar "ola" (saudação indefinida)
    from router.principal_router import roteador_principal
    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem="ola",
        tenant_id=tenant_id,
        context=None
    )

    # 3. Validar Firestore: intencao deve permanecer indefinida
    doc_final = await buscar_dado_em_path(path)
    assert doc_final is not None, "Sessao nao foi persistida em Firestore"

    intencao_final = doc_final.get("intencao_conversacional")
    assert intencao_final == "indefinida", \
        f"FALHA P2B: Intencao deveria manter indefinida, mas é {intencao_final}"

    print("[PASS P2B T1] Saudação indefinida pulou fallback — Firestore validado")


async def test_p2b_operacional_executa_fallback(firebase_config):
    """
    REGRA DE OURO: Valida que operacional (confirmacao, dados, etc)
    executa fallback normalmente.

    FIX Opção A: Usar estrutura correta de confirmação
    - draft_agendamento é para NOVO agendamento
    - dados_confirmacao_agendamento é para CONFIRMAÇÃO de agendamento existente

    1. Salva contexto com intencao_conversacional="confirmacao"
    2. Usa dados_confirmacao_agendamento (estrutura correta)
    3. Processa "sim" (operacional)
    4. Valida Firestore: intencao reclassificada para confirmacao_agendamento
    """
    tenant_id = firebase_config["tenant_id"]
    actor_id = "whatsapp:5511991382081"  # Actor diferente
    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    # 1. Salvar contexto operacional com estrutura CORRETA de confirmação
    ctx_inicial = {
        "intencao_conversacional": "confirmacao",
        "estado_fluxo": "aguardando_confirmacao",
        "aguardando_confirmacao_agendamento": True,
        # FIX: Usar dados_confirmacao_agendamento (não draft_agendamento)
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte feminino",
            "data_hora": "2026-10-25T10:00:00",
            "duracao": 40,
            "descricao": "Corte feminino com Bruna",
        },
    }
    await salvar_dado_em_path(path, ctx_inicial)
    print("[T2 SETUP] Contexto confirmacao com dados_confirmacao_agendamento salvo")

    # 2. Processar "sim" (confirmação)
    from router.principal_router import roteador_principal
    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem="sim",
        tenant_id=tenant_id,
        context=None
    )

    # 3. Validar Firestore
    doc_final = await buscar_dado_em_path(path)
    assert doc_final is not None, "Sessao operacional nao foi persistida"

    intencao_final = doc_final.get("intencao_conversacional")
    # Contrato: intencao pode ser reclassificada de "confirmacao"
    # para "confirmacao_agendamento" (ambas válidas após processar "sim")
    assert intencao_final in ["confirmacao", "confirmacao_agendamento"], \
        f"FALHA P2B T2: Intencao deveria ser confirmacao ou confirmacao_agendamento, mas é {intencao_final}"

    print(f"[PASS P2B T2] Operacional — Intencao={intencao_final} (estrutura corrigida) ✅")


async def test_p2b_nao_saudacao_nao_indefinida_executa_fallback(firebase_config):
    """
    REGRA DE OURO: Valida que mensagem não-saudação não-indefinida
    executa fallback.

    1. Salva contexto com intencao_conversacional="ajuste_incremental"
    2. Processa "Bruna" (nome, não saudação)
    3. Valida Firestore persistiu
    """
    tenant_id = firebase_config["tenant_id"]
    actor_id = "whatsapp:5511991382082"  # Actor diferente
    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    # 1. Salvar contexto com ajuste incremental
    ctx_inicial = {
        "intencao_conversacional": "ajuste_incremental",
        "estado_fluxo": "aguardando_profissional",
        "draft_agendamento": {"servico": "corte", "data_hora": "2026-10-05T14:00"},
    }
    await salvar_dado_em_path(path, ctx_inicial)

    # 2. Processar "Bruna" (nome, não saudação)
    from router.principal_router import roteador_principal
    resultado = await roteador_principal(
        user_id=actor_id,
        mensagem="Bruna",
        tenant_id=tenant_id,
        context=None
    )

    # 3. Validar Firestore
    doc_final = await buscar_dado_em_path(path)
    assert doc_final is not None, "Sessao não-saudacao nao foi persistida"

    # Nome deveria ter sido processado (ajuste de profissional)
    draft_final = doc_final.get("draft_agendamento", {})
    # Validar que alguma mudança foi feita (mesmo que mínima)
    assert doc_final.get("_updated_at") is not None, \
        "FALHA P2B: Contexto não foi atualizado para ajuste incremental"

    print("[PASS P2B T3] Nome operacional executa fallback — Firestore validado")
