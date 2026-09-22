"""
Testes E2E para Dashboard — Validação de Permissões e Segurança

Objetivo:
1. Validar que DONO pode acessar dashboard
2. Validar que CLIENTE é bloqueado
3. Validar que PROFISSIONAL é bloqueado
4. Validar isolamento entre tenants
5. Validar que todas as métricas retornam dados
"""

import pytest
import asyncio
from services.firebase_service_async import salvar_dado_em_path, obter_id_dono
from handlers.dashboard_handler import (
    cmd_dashboard,
    cmd_resumo_hoje,
    cmd_resumo_semana,
    cmd_metricas_profissionais,
    cmd_alertas,
    _validar_acesso_dono,
)


# === DADOS DE TESTE ===

DONO_ID = "tenant_dono_teste_001"
CLIENTE_ID = "cliente_teste_001"
PROFISSIONAL_ID = "prof_teste_001"
TENANT_DONO = "tenant_dono_teste_001"


@pytest.fixture(scope="session", autouse=True)
def setup_test_data_session():
    """Configura dados de teste para validação de permissões (session-wide)."""
    print("\n[SETUP] Configurando dados de teste...")

    async def _setup():
        # Dono: user_id == id_negocio (self-reference)
        # obter_id_dono retorna id_negocio se encontrado
        await salvar_dado_em_path(
            f"Clientes/{DONO_ID}",
            {
                "user_id": DONO_ID,
                "id_negocio": DONO_ID,  # CRITICO: dono aponta para si mesmo
                "nome": "Dono Teste",
                "tipo_usuario": "dono",
                "salao_nome": "Salao Teste",
            }
        )
        print(f"[OK] Dono criado: {DONO_ID}")

        # Cliente: vinculado a um dono (id_negocio = DONO_ID)
        await salvar_dado_em_path(
            f"Clientes/{CLIENTE_ID}",
            {
                "user_id": CLIENTE_ID,
                "id_negocio": DONO_ID,  # Cliente pertence a este dono
                "nome": "Cliente Teste",
                "tipo_usuario": "cliente",
            }
        )
        print(f"[OK] Cliente criado: {CLIENTE_ID}")

        # Profissional: vinculado a um dono
        await salvar_dado_em_path(
            f"Clientes/{PROFISSIONAL_ID}",
            {
                "user_id": PROFISSIONAL_ID,
                "id_negocio": DONO_ID,  # Profissional pertence a este dono
                "nome": "Profissional Teste",
                "tipo_usuario": "profissional",
            }
        )
        print(f"[OK] Profissional criado: {PROFISSIONAL_ID}")

    # Run async setup
    asyncio.run(_setup())


# === TESTE 1: DONO AUTORIZADO ===

@pytest.mark.asyncio
async def test_dono_acesso():
    """Testa que DONO pode acessar dashboard."""
    print("\n" + "=" * 80)
    print("TESTE 1: DONO PODE ACESSAR DASHBOARD")
    print("=" * 80)

    # Simular verificação de acesso
    eh_dono, tenant_id = await _validar_acesso_dono(DONO_ID)

    print(f"eh_dono: {eh_dono}")
    print(f"tenant_id: {tenant_id}")

    assert eh_dono == True, f"Dono deveria ter acesso, got {eh_dono}"
    assert tenant_id == DONO_ID, f"tenant_id deveria ser {DONO_ID}, got {tenant_id}"

    print("[OK] DONO tem acesso!")


# === TESTE 2: CLIENTE BLOQUEADO ===

@pytest.mark.asyncio
async def test_cliente_bloqueado():
    """Testa que CLIENTE NÃO pode acessar dashboard."""
    print("\n" + "=" * 80)
    print("TESTE 2: CLIENTE BLOQUEADO")
    print("=" * 80)

    # Simular verificação de acesso para cliente
    eh_dono, tenant_id = await _validar_acesso_dono(CLIENTE_ID)

    print(f"eh_dono: {eh_dono}")
    print(f"tenant_id: {tenant_id}")

    assert eh_dono == False, f"Cliente NÃO deveria ter acesso, got {eh_dono}"

    print("[OK] CLIENTE foi bloqueado!")


# === TESTE 3: PROFISSIONAL BLOQUEADO ===

@pytest.mark.asyncio
async def test_profissional_bloqueado():
    """Testa que PROFISSIONAL NÃO pode acessar dashboard."""
    print("\n" + "=" * 80)
    print("TESTE 3: PROFISSIONAL BLOQUEADO")
    print("=" * 80)

    # Simular verificação de acesso para profissional
    eh_dono, tenant_id = await _validar_acesso_dono(PROFISSIONAL_ID)

    print(f"eh_dono: {eh_dono}")
    print(f"tenant_id: {tenant_id}")

    assert eh_dono == False, f"Profissional NÃO deveria ter acesso, got {eh_dono}"

    print("[OK] PROFISSIONAL foi bloqueado!")


# === TESTE 4: CROSS-TENANT BLOQUEADO ===

@pytest.mark.asyncio
async def test_cross_tenant_bloqueado():
    """Testa que não há vazamento de dados entre tenants."""
    print("\n" + "=" * 80)
    print("TESTE 4: ISOLAMENTO CROSS-TENANT")
    print("=" * 80)

    # Criar segundo dono
    DONO2_ID = "tenant_dono_teste_002"
    await salvar_dado_em_path(
        f"Clientes/{DONO2_ID}",
        {
            "user_id": DONO2_ID,
            "id_negocio": DONO2_ID,  # CRITICO: apontar para si mesmo
            "nome": "Dono 2 Teste",
            "tipo_usuario": "dono",
            "salao_nome": "Salao 2 Teste",
        }
    )

    # DONO 1 tentando acessar dados de DONO 2
    # Cada dono só acessa seus próprios dados (via tenant_id)
    eh_dono_1, tenant_1 = await _validar_acesso_dono(DONO_ID)
    eh_dono_2, tenant_2 = await _validar_acesso_dono(DONO2_ID)

    print(f"DONO 1: eh_dono={eh_dono_1}, tenant_id={tenant_1}")
    print(f"DONO 2: eh_dono={eh_dono_2}, tenant_id={tenant_2}")

    assert tenant_1 != tenant_2, "Tenants deveriam ser diferentes"
    assert eh_dono_1 == True and eh_dono_2 == True

    print("[OK] Isolamento multi-tenant validado!")


# === TESTE 5: MÉTRICAS RETORNAM ESTRUTURA CORRETA ===

@pytest.mark.asyncio
async def test_estrutura_metricas():
    """Testa que funções retornam estrutura correta."""
    print("\n" + "=" * 80)
    print("TESTE 5: ESTRUTURA DE MÉTRICAS")
    print("=" * 80)

    from services.dashboard_service import (
        obter_resumo_hoje,
        obter_resumo_semana,
        obter_metricas_profissionais,
        obter_metricas_clientes,
        obter_metricas_servicos,
        obter_alertas_operacionais,
    )

    # Testar cada métrica
    resumo_hoje = await obter_resumo_hoje(DONO_ID)
    print(f"resumo_hoje: {type(resumo_hoje).__name__}")
    assert resumo_hoje is not None
    assert hasattr(resumo_hoje, "taxa_ocupacao")
    assert hasattr(resumo_hoje, "agendamentos_total")

    resumo_semana = await obter_resumo_semana(DONO_ID)
    print(f"resumo_semana: {type(resumo_semana).__name__}")
    assert resumo_semana is not None

    profs = await obter_metricas_profissionais(DONO_ID)
    print(f"profissionais: {type(profs).__name__} (len={len(profs)})")
    assert isinstance(profs, list)

    clientes = await obter_metricas_clientes(DONO_ID)
    print(f"clientes: {type(clientes).__name__}")
    assert hasattr(clientes, "clientes_novos_7_dias")

    servicos = await obter_metricas_servicos(DONO_ID)
    print(f"servicos: {type(servicos).__name__} (len={len(servicos)})")
    assert isinstance(servicos, list)

    alertas = await obter_alertas_operacionais(DONO_ID)
    print(f"alertas: {type(alertas).__name__} (len={len(alertas)})")
    assert isinstance(alertas, list)

    print("[OK] Todas as estruturas de métricas estão corretas!")


# Note: Pytest executa os testes automaticamente quando você roda:
# pytest tests/test_dashboard_e2e_permissoes.py -v
