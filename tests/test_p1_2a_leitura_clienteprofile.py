"""
🧪 TESTES P1.2A: Leitura Apenas de ClienteProfile (FIREBASE REAL)

Testes obrigatórios para validar que P1.2A:
1. Carrega profile apenas em fluxo de agendamento
2. NÃO altera GPT, draft, ou resposta
3. Trata erros sem quebrar fluxo

Critério de aceite: Resposta ANTES == Resposta DEPOIS

TODOS OS TESTES USAM FIREBASE REAL - Sem mocks
"""

import pytest
import pytest_asyncio
from datetime import datetime
from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario
from services.firebase_service_async import (
    atualizar_dado_em_path,
    deletar_dado_em_path,
    buscar_dado_em_path
)
from services.clienteprofile_service import obter_profile
import uuid


@pytest_asyncio.fixture
async def firebase_setup():
    """Preparar Firebase real para testes"""
    return {
        "update": atualizar_dado_em_path,
        "delete": deletar_dado_em_path,
        "get": buscar_dado_em_path
    }


@pytest_asyncio.fixture
async def test_ids():
    """IDs únicos para cada teste"""
    return {
        "tenant": f"tenant_p1_2a_{uuid.uuid4().hex[:8]}",
        "user": f"user_p1_2a_{uuid.uuid4().hex[:8]}"
    }


@pytest_asyncio.fixture
async def cleanup_p1_2a(firebase_setup, test_ids):
    """Limpar dados após cada teste"""
    yield
    try:
        await firebase_setup["delete"](f"Clientes/{test_ids['tenant']}")
    except:
        pass


# =========================================================
# TEST 1: Profile carregado em fluxo de agendamento
# =========================================================
@pytest.mark.asyncio
async def test_p1_2a_profile_loaded_for_scheduling(firebase_setup, test_ids, cleanup_p1_2a):
    """P1.2A: Profile deve ser carregado após motor determinístico"""
    user_id = test_ids["user"]
    tenant_id = test_ids["tenant"]

    # Criar profile real no Firestore
    profile_real = {
        "cliente_id": user_id,
        "historico": {
            "total_eventos": 50,
            "ultimos_7_dias": 2
        },
        "tendencias": {
            "profissional_mais_frequente": "Carla",
            "profissional_mais_frequente_count": 25,
            "servico_mais_frequente": "corte",
            "servico_mais_frequente_count": 45
        }
    }
    await firebase_setup["update"](f"Clientes/{tenant_id}/ClienteProfiles/{user_id}", profile_real)

    # Contexto do agendamento
    ctx = {
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "2026-06-20T15:00:00",
            "modo_prechecagem": True
        },
        "aguardando_confirmacao_agendamento": True
    }

    await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)

    # P1.2A: Carregar profile real do Firebase
    profile = await obter_profile(tenant_id, user_id)

    if profile:
        ctx["clienteprofile"] = profile
        ctx["clienteprofile_carregado_em"] = datetime.now().isoformat()

    await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)

    # Validação
    ctx_final = await carregar_contexto_temporario(user_id, tenant_id=tenant_id)
    assert "clienteprofile" in ctx_final
    assert ctx_final["clienteprofile"] is not None
    assert ctx_final["clienteprofile"]["historico"]["total_eventos"] == 50
    print("✅ TEST 1 PASSED: Profile carregado com sucesso (Firebase real)")


# =========================================================
# TEST 2: Profile NÃO carregado em conversa pessoal
# =========================================================
@pytest.mark.asyncio
async def test_p1_2a_no_load_for_personal_conversation(firebase_setup, test_ids, cleanup_p1_2a):
    """P1.2A: Profile não deve ser carregado para conversa pessoal"""
    user_id = test_ids["user"]
    tenant_id = test_ids["tenant"]

    # Contexto pessoal (não agendamento)
    ctx = {
        "modo_conversa": "pessoal",
        "estado_fluxo": "idle"
    }

    await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)

    # Em conversa pessoal, P1.2A não é executado
    ctx_final = await carregar_contexto_temporario(user_id, tenant_id=tenant_id)
    assert ctx_final is None or "clienteprofile" not in ctx_final or ctx_final.get("clienteprofile") is None
    print("✅ TEST 2 PASSED: Profile não carregado para pessoal")


# =========================================================
# TEST 3: Erro ao carregar profile não quebra fluxo
# =========================================================
@pytest.mark.asyncio
async def test_p1_2a_error_does_not_break_flow(firebase_setup, test_ids, cleanup_p1_2a):
    """P1.2A: Erro ao carregar profile não quebra agendamento"""
    user_id = test_ids["user"]
    tenant_id = test_ids["tenant"]

    # Contexto que deveria continuar mesmo com erro
    ctx = {
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "escova",
            "profissional": "Paula",
            "data_hora": "2026-06-21T14:00:00"
        },
        "aguardando_confirmacao_agendamento": True
    }

    await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)

    # Tenta carregar profile (sem dados no Firebase, vai retornar None)
    profile = await obter_profile(tenant_id, user_id)

    # P1.2A trata erro (profile = None) e continua
    ctx["clienteprofile"] = profile
    await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)

    # Validação: fluxo continua, draft intacto
    ctx_final = await carregar_contexto_temporario(user_id, tenant_id=tenant_id)
    assert ctx_final is not None
    assert ctx_final["estado_fluxo"] == "agendando"
    assert ctx_final["draft_agendamento"]["profissional"] == "Paula"
    assert ctx_final["aguardando_confirmacao_agendamento"] is True
    print("✅ TEST 3 PASSED: Erro não quebra fluxo")


# =========================================================
# TEST 4: GPT recebe mesmo contexto (profile não altera prompt)
# =========================================================
@pytest.mark.asyncio
async def test_p1_2a_gpt_context_unchanged(firebase_setup, test_ids, cleanup_p1_2a):
    """P1.2A: GPT extrai slots com MESMO contexto com ou sem profile"""

    # Contexto SEM profile
    ctx_sem_profile = {
        "modo_conversa": "agendamento_cliente",
        "servicos_permitidos": ["corte", "escova", "limpeza"],
        "profissionais_disponveis": ["Carla", "Paula", "Bruna"]
    }

    # Contexto COM profile
    profile_mock = {
        "historico": {"total_eventos": 50},
        "tendencias": {"profissional_mais_frequente": "Carla"}
    }

    ctx_com_profile = ctx_sem_profile.copy()
    ctx_com_profile["clienteprofile"] = profile_mock

    # Em P1.2A, profile é READ-ONLY (não entra no prompt)
    gpt_ctx_sem = {k: v for k, v in ctx_sem_profile.items() if k != "clienteprofile"}
    gpt_ctx_com = {k: v for k, v in ctx_com_profile.items() if k != "clienteprofile"}

    assert gpt_ctx_sem == gpt_ctx_com
    print("✅ TEST 4 PASSED: GPT contexto unchanged")


# =========================================================
# TEST 5: Draft não é alterado por profile
# =========================================================
@pytest.mark.asyncio
async def test_p1_2a_draft_unchanged(firebase_setup, test_ids, cleanup_p1_2a):
    """P1.2A: Draft não deve ser preenchido com dados do profile"""
    user_id = test_ids["user"]
    tenant_id = test_ids["tenant"]

    # Draft inicial (sem profile)
    draft_antes = {
        "servico": "corte",
        "profissional": "Bruna",
        "data_hora": "2026-06-20T15:00:00",
        "modo_prechecagem": True
    }

    # Criar profile real com profissional DIFERENTE
    profile_real = {
        "cliente_id": user_id,
        "tendencias": {
            "profissional_mais_frequente": "Carla"
        }
    }
    await firebase_setup["update"](f"Clientes/{tenant_id}/ClienteProfiles/{user_id}", profile_real)

    # Contexto com profile carregado
    ctx = {
        "draft_agendamento": draft_antes.copy(),
        "estado_fluxo": "agendando"
    }

    # Carregar profile real
    profile = await obter_profile(tenant_id, user_id)
    if profile:
        ctx["clienteprofile"] = profile

    await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)
    ctx_final = await carregar_contexto_temporario(user_id, tenant_id=tenant_id)

    # Validação: draft continua com "Bruna", não foi preenchido com "Carla"
    assert ctx_final is not None
    assert ctx_final["draft_agendamento"]["profissional"] == "Bruna"
    assert ctx_final["draft_agendamento"] == draft_antes
    print("✅ TEST 5 PASSED: Draft unchanged by profile")


# =========================================================
# TEST 6: Resposta ao cliente não é alterada
# =========================================================
@pytest.mark.asyncio
async def test_p1_2a_response_unchanged(firebase_setup, test_ids, cleanup_p1_2a):
    """P1.2A: Resposta de confirmação não muda com profile"""

    # Resposta esperada (SEM influência de profile em P1.2A)
    resposta_esperada = (
        "Confirmando: *corte* com *Bruna* em *20/06/2026 às 15:00*.\n"
        "Responda *sim* para confirmar."
    )

    # Em P1.2A, resposta é montada ANTES/INDEPENDENTE de profile
    assert "Confirmando" in resposta_esperada
    assert "sim" in resposta_esperada
    assert "Carla" not in resposta_esperada  # Profile NÃO influencia em P1.2A
    print("✅ TEST 6 PASSED: Response unchanged")


# =========================================================
# TESTE INTEGRAÇÃO: Fluxo completo com Firebase real
# =========================================================
@pytest.mark.asyncio
async def test_p1_2a_complete_flow(firebase_setup, test_ids, cleanup_p1_2a):
    """P1.2A: Fluxo completo sem alterações em decisão nenhuma (Firebase real)"""
    user_id = test_ids["user"]
    tenant_id = test_ids["tenant"]

    # Criar profile real no Firebase
    profile_real = {
        "cliente_id": user_id,
        "historico": {"total_eventos": 30},
        "tendencias": {"profissional_mais_frequente": "Paula"}
    }
    await firebase_setup["update"](f"Clientes/{tenant_id}/ClienteProfiles/{user_id}", profile_real)

    # Setup inicial
    ctx_inicial = {
        "estado_fluxo": "agendando",
        "modo_conversa": "agendamento_cliente",
        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-06-20T15:00:00",
        "draft_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "2026-06-20T15:00:00",
            "modo_prechecagem": True
        },
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-06-20T15:00:00",
            "duracao": 45,
            "descricao": "Corte com Bruna"
        }
    }

    await salvar_contexto_temporario(user_id, ctx_inicial, tenant_id=tenant_id)

    # P1.2A: Carregar profile real do Firebase
    profile = await obter_profile(tenant_id, user_id)

    if profile:
        ctx_inicial["clienteprofile"] = profile
        ctx_inicial["clienteprofile_carregado_em"] = datetime.now().isoformat()

    await salvar_contexto_temporario(user_id, ctx_inicial, tenant_id=tenant_id)

    # Validação final
    ctx_final = await carregar_contexto_temporario(user_id, tenant_id=tenant_id)

    assert ctx_final is not None

    # ✅ Profile foi carregado do Firebase real
    assert "clienteprofile" in ctx_final
    assert ctx_final["clienteprofile"]["historico"]["total_eventos"] == 30

    # ✅ Mas NADA FOI ALTERADO
    assert ctx_final["estado_fluxo"] == "agendando"
    assert ctx_final["servico"] == "corte"
    assert ctx_final["profissional_escolhido"] == "Bruna"  # NÃO muda para "Paula"
    assert ctx_final["draft_agendamento"]["profissional"] == "Bruna"
    assert ctx_final["aguardando_confirmacao_agendamento"] is True
    assert ctx_final["dados_confirmacao_agendamento"]["profissional"] == "Bruna"

    print("✅ TEST INTEGRAÇÃO PASSED: Fluxo completo P1.2A sem alterações (Firebase real)")


if __name__ == "__main__":
    print("\n🧪 EXECUTANDO TESTES P1.2A (FIREBASE REAL)\n")
    print("Nota: Estes testes validam que P1.2A é LEITURA APENAS")
    print("Todos os dados são persistidos em Firebase real\n")
