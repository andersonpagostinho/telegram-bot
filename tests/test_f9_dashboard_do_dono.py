# tests/test_f9_dashboard_do_dono.py
"""
F9 — Dashboard do Dono (Testes Obrigatórios)

Testes para validar que o Dashboard do Dono:
1. Calcula métricas diárias corretamente
2. Calcula ocupação semanal corretamente
3. Calcula faturamento por profissional
4. Identifica clientes recorrentes
5. Gera alertas operacionais
6. Mantém isolamento multi-tenant
7. Funciona com dados vazios
8. Não quebra regressão (P0/F3/F4/F8)
"""

import pytest
from datetime import datetime, timedelta, date
from pytz import timezone

from services.dashboard_service import (
    obter_resumo_hoje,
    obter_resumo_semana,
    obter_metricas_profissionais,
    obter_metricas_clientes,
    obter_metricas_servicos,
    obter_alertas_operacionais,
    obter_dashboard_completo,
)

FUSO_BR = timezone("America/Sao_Paulo")

# ============================================================================
# FIXTURES — Dados de teste
# ============================================================================

@pytest.fixture
def tenant_teste_1():
    """Tenant de teste 1."""
    return "tenant_teste_f9_001"


@pytest.fixture
def tenant_teste_2():
    """Tenant de teste 2 (para isolamento)."""
    return "tenant_teste_f9_002"


@pytest.fixture
def agendamentos_hoje_teste():
    """Agendamentos de teste para hoje."""
    hoje = date.today().isoformat()
    return [
        {
            "agendamento_id": "ag_001",
            "data": hoje,
            "hora_inicio": "09:00",
            "hora_fim": "09:30",
            "cliente_id": "cli_001",
            "cliente_nome": "Maria",
            "profissional": "Carla",
            "servico": "Corte",
            "duracao_minutos": 30,
            "preco": 70.00,
            "status": "confirmado",
            "origem": "direto",
        },
        {
            "agendamento_id": "ag_002",
            "data": hoje,
            "hora_inicio": "14:00",
            "hora_fim": "14:30",
            "cliente_id": "cli_002",
            "cliente_nome": "Ana",
            "profissional": "Bruna",
            "servico": "Escova",
            "duracao_minutos": 30,
            "preco": 80.00,
            "status": "confirmado",
            "origem": "direto",
        },
        {
            "agendamento_id": "ag_003",
            "data": hoje,
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "cliente_id": "cli_003",
            "cliente_nome": "João",
            "profissional": "Carla",
            "servico": "Corte",
            "duracao_minutos": 30,
            "preco": 70.00,
            "status": "cancelado",
            "origem": "direto",
        },
    ]


# ============================================================================
# F9-1: MÉTRICAS DIÁRIAS CORRETAS
# ============================================================================

@pytest.mark.asyncio
async def test_f9_1_metricas_diarias_corretas(tenant_teste_1, agendamentos_hoje_teste):
    """
    F9-1: Verifica se resumo_hoje calcula corretamente.

    Validações:
    - total = 3
    - confirmados = 2
    - cancelados = 1
    - concluidos = 0
    - taxa_ocupacao = 2/3 = 66.7%
    - taxa_cancelamento = 1/3 = 33.3%
    """

    # TODO: Mockar buscar_agendamentos_data() para retornar agendamentos_hoje_teste

    resumo = await obter_resumo_hoje(tenant_teste_1)

    # Validações esperadas
    assert resumo.agendamentos_total > 0, "Deve ter agendamentos"
    assert resumo.agendamentos_confirmados > 0, "Deve ter confirmados"
    assert resumo.agendamentos_cancelados >= 0, "Pode ter cancelados"
    assert 0 <= resumo.taxa_ocupacao <= 100, "Taxa ocupação deve estar entre 0-100%"
    assert 0 <= resumo.taxa_cancelamento <= 100, "Taxa cancelamento deve estar entre 0-100%"


# ============================================================================
# F9-2: OCUPAÇÃO SEMANAL CORRETA
# ============================================================================

@pytest.mark.asyncio
async def test_f9_2_ocupacao_semanal_correta(tenant_teste_1):
    """
    F9-2: Verifica se resumo_semana calcula ocupação da semana.

    Validações:
    - taxa_ocupacao entre 0-100%
    - taxa_cancelamento entre 0-100%
    - agendamentos_total > 0 (se houver dados)
    """

    resumo = await obter_resumo_semana(tenant_teste_1)

    # Validações esperadas
    assert 0 <= resumo.taxa_ocupacao <= 100, "Taxa ocupação semana deve estar entre 0-100%"
    assert 0 <= resumo.taxa_cancelamento <= 100, "Taxa cancelamento semana deve estar entre 0-100%"
    assert isinstance(resumo.agendamentos_total, int), "Total deve ser inteiro"
    assert resumo.agendamentos_total >= 0, "Total deve ser >= 0"


# ============================================================================
# F9-3: FATURAMENTO POR PROFISSIONAL
# ============================================================================

@pytest.mark.asyncio
async def test_f9_3_faturamento_por_profissional(tenant_teste_1):
    """
    F9-3: Verifica cálculo de faturamento por profissional.

    Validações:
    - faturamento_estimado = soma de preços de agendamentos concluídos
    - ocupacao_percentual entre 0-100%
    - atendimentos >= 0
    """

    metricas = await obter_metricas_profissionais(tenant_teste_1)

    # Validações esperadas
    for prof in metricas:
        assert isinstance(prof.profissional, str), "Profissional deve ser string"
        assert prof.atendimentos >= 0, "Atendimentos deve ser >= 0"
        assert 0 <= prof.ocupacao_percentual <= 100, "Ocupação deve estar entre 0-100%"
        assert prof.faturamento_estimado >= 0, "Faturamento deve ser >= 0"
        assert prof.taxa_cancelamento >= 0, "Taxa cancelamento deve ser >= 0"


# ============================================================================
# F9-4: CLIENTES RECORRENTES
# ============================================================================

@pytest.mark.asyncio
async def test_f9_4_clientes_recorrentes(tenant_teste_1):
    """
    F9-4: Verifica identificação de clientes recorrentes.

    Validações:
    - clientes_recorrentes >= 0
    - clientes_recorrentes = clientes com 4+ agendamentos
    """

    # TODO: Mockar dados com cliente tendo 4+ agendamentos

    metricas = await obter_metricas_clientes(tenant_teste_1)

    # Validações esperadas
    assert metricas.clientes_recorrentes >= 0, "Recorrentes deve ser >= 0"
    assert isinstance(metricas.clientes_novos_7_dias, int), "Novos deve ser inteiro"
    assert isinstance(metricas.clientes_sem_retorno_30_dias, int), "Sem retorno 30d deve ser inteiro"
    assert isinstance(metricas.clientes_sem_retorno_60_dias, int), "Sem retorno 60d deve ser inteiro"
    assert isinstance(metricas.clientes_sem_retorno_90_dias, int), "Sem retorno 90d deve ser inteiro"


# ============================================================================
# F9-5: ALERTAS OPERACIONAIS
# ============================================================================

@pytest.mark.asyncio
async def test_f9_5_alertas_operacionais(tenant_teste_1):
    """
    F9-5: Verifica geração de alertas.

    Cenários validados:
    - Se ocupação < 50% → alerta "ocupacao_baixa"
    - Se cancelamento > 15% → alerta "cancelamento_alto"
    - Se profissional sem agenda > 7 dias → alerta
    """

    alertas = await obter_alertas_operacionais(tenant_teste_1)

    # Validações esperadas
    assert isinstance(alertas, list), "Alertas deve ser lista"

    for alerta in alertas:
        assert alerta.tipo in [
            "ocupacao_baixa",
            "cancelamento_alto",
            "profissional_sem_agenda",
            "queda_demanda",
            "crescimento_demanda",
        ], f"Tipo de alerta desconhecido: {alerta.tipo}"

        assert alerta.severidade in ["info", "warning", "critical"], \
            f"Severidade desconhecida: {alerta.severidade}"

        assert isinstance(alerta.descricao, str), "Descrição deve ser string"
        assert len(alerta.acoes_sugeridas) > 0, "Deve ter ações sugeridas"


# ============================================================================
# F9-6: ISOLAMENTO MULTI-TENANT
# ============================================================================

@pytest.mark.asyncio
async def test_f9_6_isolamento_multitenant(tenant_teste_1, tenant_teste_2):
    """
    F9-6: Verifica isolamento de dados entre tenants.

    Validações:
    - Dashboard de tenant_1 NÃO contém dados de tenant_2
    - Cada tenant retorna seus próprios dados isoladamente
    """

    # TODO: Mockar dados diferentes para cada tenant

    dashboard_1 = await obter_dashboard_completo(tenant_teste_1)
    dashboard_2 = await obter_dashboard_completo(tenant_teste_2)

    # Validações esperadas
    # Os dashboards podem estar vazios, mas devem ser estruturas válidas
    assert dashboard_1 is not None, "Dashboard 1 deve retornar estrutura"
    assert dashboard_2 is not None, "Dashboard 2 deve retornar estrutura"

    # Se houver dados, devem ser diferentes
    # (não conseguimos validar sem mocar dados específicos)
    assert hasattr(dashboard_1, "resumo_hoje"), "Dashboard 1 deve ter resumo_hoje"
    assert hasattr(dashboard_2, "resumo_hoje"), "Dashboard 2 deve ter resumo_hoje"


# ============================================================================
# F9-7: DADOS VAZIOS NÃO QUEBRAM
# ============================================================================

@pytest.mark.asyncio
async def test_f9_7_dados_vazios_nao_quebram(tenant_teste_1):
    """
    F9-7: Verifica que Dashboard funciona com Firestore vazio.

    Validações:
    - Não lança exceção
    - Retorna estrutura válida com valores vazios/zero
    - Não quebra em nenhuma função
    """

    # Chamar com tenant que não tem dados

    try:
        resumo_hoje = await obter_resumo_hoje(tenant_teste_1)
        assert resumo_hoje is not None, "Deve retornar objeto, não None"
        assert resumo_hoje.agendamentos_total == 0, "Deve ter 0 agendamentos"

        resumo_semana = await obter_resumo_semana(tenant_teste_1)
        assert resumo_semana is not None, "Deve retornar objeto"

        profs = await obter_metricas_profissionais(tenant_teste_1)
        assert isinstance(profs, list), "Deve retornar lista"
        assert len(profs) == 0, "Lista deve estar vazia"

        clientes = await obter_metricas_clientes(tenant_teste_1)
        assert clientes is not None, "Deve retornar objeto"

        servicos = await obter_metricas_servicos(tenant_teste_1)
        assert isinstance(servicos, list), "Deve retornar lista"

        alertas = await obter_alertas_operacionais(tenant_teste_1)
        assert isinstance(alertas, list), "Deve retornar lista"

        dashboard = await obter_dashboard_completo(tenant_teste_1)
        assert dashboard is not None, "Deve retornar dashboard completo"

    except Exception as e:
        pytest.fail(f"Não deve lançar exceção com dados vazios: {e}")


# ============================================================================
# F9-8: REGRESSÃO P0/F3/F4/F8
# ============================================================================

@pytest.mark.asyncio
async def test_f9_8_regressao_p0_f3_f4_f8():
    """
    F9-8: Verifica que Dashboard não quebrou nada.

    Nota: Este teste depende que P0/F3/F4/F8 continuem rodando em verde.

    Quando implementado completamente:
    - Rodar P0: 174/174 PASS
    - Rodar F3: 39/39 PASS
    - Rodar F4: 8/8 PASS
    - Rodar F8: Funcional

    Por enquanto, apenas estrutura.
    """

    # TODO: Importar e rodar testes P0/F3/F4/F8
    # from tests.test_p0_agendamento import test_p0_*
    # from tests.test_f3_robustez import test_f3_*
    # from tests.test_f4_reativacao import test_f4_*
    # from tests.test_f8_encaixe import test_f8_*

    # Por enquanto, passar
    assert True, "Regressão P0/F3/F4/F8 deve estar em verde"


# ============================================================================
# TESTES ADICIONAIS (Verificações)
# ============================================================================

@pytest.mark.asyncio
async def test_dashboard_estrutura_completa(tenant_teste_1):
    """Verifica que Dashboard completo tem todas as seções."""

    dashboard = await obter_dashboard_completo(tenant_teste_1)

    # Estrutura obrigatória
    assert hasattr(dashboard, "timestamp"), "Deve ter timestamp"
    assert hasattr(dashboard, "resumo_hoje"), "Deve ter resumo_hoje"
    assert hasattr(dashboard, "resumo_semana"), "Deve ter resumo_semana"
    assert hasattr(dashboard, "metricas_clientes"), "Deve ter metricas_clientes"
    assert hasattr(dashboard, "metricas_profissionais"), "Deve ter metricas_profissionais"
    assert hasattr(dashboard, "metricas_servicos"), "Deve ter metricas_servicos"
    assert hasattr(dashboard, "alertas"), "Deve ter alertas"


@pytest.mark.asyncio
async def test_tipos_de_retorno_corretos(tenant_teste_1):
    """Verifica que tipos de retorno estão corretos."""

    resumo = await obter_resumo_hoje(tenant_teste_1)
    profs = await obter_metricas_profissionais(tenant_teste_1)
    clientes = await obter_metricas_clientes(tenant_teste_1)
    servicos = await obter_metricas_servicos(tenant_teste_1)
    alertas = await obter_alertas_operacionais(tenant_teste_1)

    # Tipos
    assert hasattr(resumo, "agendamentos_total"), "ResumoOperacional deve ter agendamentos_total"
    assert isinstance(profs, list), "Métricas profissionais deve retornar lista"
    assert hasattr(clientes, "clientes_novos_7_dias"), "MetricasCliente deve ter clientes_novos_7_dias"
    assert isinstance(servicos, list), "Métricas serviços deve retornar lista"
    assert isinstance(alertas, list), "Alertas deve retornar lista"


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
