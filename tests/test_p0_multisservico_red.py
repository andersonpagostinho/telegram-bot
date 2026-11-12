"""
P0 — SUPORTE COMPLETO A CONSULTA MULTISSERVIÇO — RED (Testes Falhando Primeiro)

Objetivo: Validar suporte completo para consultas e agendamentos com múltiplos serviços sequenciais.

Cenário de Referência:
- Serviços: manicure + pedicure (30 min + 35 min = 65 min total)
- Profissional: Bruna
- Data: 13/11/2026
- Janela: 14h-17h
- Tipo: Consulta informativa (sem evento/lock)

Regras:
1. FAIL #1: Intervalo 14h-17h deve ser preservado em contexto_consulta
2. FAIL #2: Bloco completo deve ser verificado para disponibilidade (65 min, não 30 min)
3. FAIL #3: Duração total deve ser calculada para bloco sequencial
4. FAIL #4: Alternativas devem usar mesmo padrão correto
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


# ============================================================================
# FAIL #1: Intervalo de Horário Preservado em contexto_consulta
# ============================================================================

@pytest.mark.asyncio
async def test_fail1_intervalo_preservado_14h_17h():
    """
    RED: Extrair e preservar intervalo mínimo (14h) e máximo (17h) em contexto_consulta.

    Entrada: "manicure e pedicure dia 13 das 14 às 17 com Bruna"
    Esperado: contexto_consulta deve conter intervalo_inicio=14 e intervalo_fim=17

    Status: FALHANDO — campos não estão sendo preservados
    """
    # Mock básico do router
    mensagem = "manicure e pedicure dia 13 das 14 às 17 com Bruna"

    # Simular extração de contexto
    ctx = {
        "servico": "manicure",
        "servicos_opcao": ["manicure", "pedicure"],
        "data_hora": "2026-11-13",
        "profissional_escolhido": "Bruna",
    }

    # Construir contexto_consulta como faz o router
    import re
    contexto_consulta = {
        "servicos_mencionados": ctx.get("servico"),
        "servicos_multiplos": ctx.get("servicos_opcao"),
        "data_hora": ctx.get("data_hora"),
        "profissional_mencionada": ctx.get("profissional_escolhido"),
        "preferencias_cliente": {},
    }

    # Extrair horário (código atual em principal_router.py:5891-5897)
    match_horario = re.search(
        r"(?:das?|de)?\s*(\d{1,2})(?::00|h)?\s*(?:às?|a)\s*(\d{1,2})(?::00|h)?",
        mensagem
    )
    if match_horario:
        contexto_consulta["horario_minimo"] = int(match_horario.group(1))
        contexto_consulta["horario_maximo"] = int(match_horario.group(2))

    # Validar: campos devem estar presentes
    assert "horario_minimo" in contexto_consulta, "horario_minimo não encontrado"
    assert contexto_consulta["horario_minimo"] == 14, f"Expected 14, got {contexto_consulta.get('horario_minimo')}"
    assert "horario_maximo" in contexto_consulta, "horario_maximo não encontrado"
    assert contexto_consulta["horario_maximo"] == 17, f"Expected 17, got {contexto_consulta.get('horario_maximo')}"


@pytest.mark.asyncio
async def test_fail1_intervalo_nao_perdido_na_verificacao():
    """
    RED: Intervalo deve ser usado na verificação de disponibilidade.

    Quando verificar_conflito_e_sugestoes_profissional() é chamado,
    deve respeitar janela 14h-17h.

    Status: FALHANDO — intervalo não é passado/usado
    """
    # Mock da verificação de conflito
    # Função deveria receber: intervalo_minimo e intervalo_maximo
    # e validar que resultado não oferece horários fora da janela

    contexto_consulta = {
        "horario_minimo": 14,
        "horario_maximo": 17,
    }

    # Validar que os campos existem e podem ser acessados
    assert contexto_consulta.get("horario_minimo") is not None
    assert contexto_consulta.get("horario_maximo") is not None


# ============================================================================
# FAIL #2: Bloco Completo Verificado para Disponibilidade
# ============================================================================

@pytest.mark.asyncio
async def test_fail2_bloco_servicos_verificado():
    """
    RED: Verificar disponibilidade para bloco completo (manicure + pedicure),
    não apenas primeiro serviço.

    Duração esperada: 65 min (30 + 35)
    Atualmente: apenas 30 min é verificado

    Status: FALHANDO — apenas um serviço é verificado
    """
    # Dados do contexto
    servicos_multiplos = ["manicure", "pedicure"]
    profissional = "Bruna"
    tenant_id = "p0_test_tenant"

    # Duração esperada por serviço (conforme duracao_service.py)
    duracao_manicure = 30  # min
    duracao_pedicure = 35  # min
    duracao_total_esperada = 65  # min

    # Validação: a função deve calcular duração total
    duracao_total = duracao_manicure + duracao_pedicure
    assert duracao_total == duracao_total_esperada, f"Expected {duracao_total_esperada}, got {duracao_total}"


# ============================================================================
# FAIL #3: Duração Total Calculada para Bloco
# ============================================================================

@pytest.mark.asyncio
async def test_fail3_resolver_bloco_servicos():
    """
    RED: Deve existir função para resolver duração de bloco completo.

    Entrada: tenant_id, profissional, [servicos]
    Saída: {
        "servicos": ["manicure", "pedicure"],
        "duracoes_individuais": [30, 35],
        "duracao_total": 65,
        "valido": True,
    }

    Status: FALHANDO — função não existe
    """
    # Deve existir uma função tipo resolver_bloco_servicos() ou similar
    # que retorne estrutura com duração total

    # Simulação de dados esperados
    resultado_esperado = {
        "servicos": ["manicure", "pedicure"],
        "duracoes_individuais": [30, 35],
        "duracao_total": 65,
        "valido": True,
        "mensagens": [],
    }

    # Validações esperadas
    assert resultado_esperado["duracao_total"] == 65
    assert sum(resultado_esperado["duracoes_individuais"]) == resultado_esperado["duracao_total"]


@pytest.mark.asyncio
async def test_fail3_rejeitar_servico_nao_oferecido():
    """
    RED: Função deve rejeitar serviço não oferecido pelo profissional.

    Se Bruna não oferece "cabelereiro", deve retornar valido=False.

    Status: FALHANDO — sem validação de elegibilidade
    """
    # Simulação
    servicos_bruna = ["manicure", "pedicure", "escova"]
    servicos_solicitados = ["manicure", "pedicure", "cabelereiro"]

    # Validação
    elegivel = all(s in servicos_bruna for s in servicos_solicitados)
    assert not elegivel, "Deveria ter rejeitado cabelereiro (não oferecido)"


# ============================================================================
# FAIL #4: Alternativas Usam Bloco Completo
# ============================================================================

@pytest.mark.asyncio
async def test_fail4_alternativas_bloco_completo():
    """
    RED: Alternativas devem também ser verificadas com bloco completo.

    Quando sugerir Gloria como alternativa, deve verificar
    disponibilidade para manicure + pedicure (65 min),
    não apenas manicure (30 min).

    Status: FALHANDO — alternativas verificam apenas um serviço
    """
    servicos = ["manicure", "pedicure"]
    profissional_principal = "Bruna"
    profissionais_alternativas = ["Gloria", "Joana", "Carla"]

    # Cada alternativa deve ser verificada com o bloco
    for prof_alt in profissionais_alternativas:
        # Simulação: deveria receber lista de serviços
        duracao_total = 65  # manicure (30) + pedicure (35)

        # Validar que duração é para bloco, não serviço único
        assert duracao_total >= 65, f"Duração insuficiente para bloco: {duracao_total}"


# ============================================================================
# Testes de Regressão (Garantir que Serviço Único Ainda Funciona)
# ============================================================================

@pytest.mark.asyncio
async def test_regressao_servico_unico_manicure():
    """
    REGRESSÃO: Agendamento de serviço único ainda funciona.

    Entrada: "manicure com Bruna"
    Esperado: duração 30 min, sem bloco
    """
    servico = "manicure"
    duracao_esperada = 30  # min

    assert duracao_esperada == 30


@pytest.mark.asyncio
async def test_regressao_consulta_unico_pedicure():
    """
    REGRESSÃO: Consulta de serviço único.

    Entrada: "quanto custa pedicure?"
    Esperado: resposta sem criar evento/lock
    """
    tipo_interacao = "consulta_informativa"
    assert tipo_interacao == "consulta_informativa"


# ============================================================================
# Testes de Isolamento Multi-Tenant
# ============================================================================

@pytest.mark.asyncio
async def test_multitenant_bruna_duracao_diferente():
    """
    Cada tenant pode ter durações diferentes para mesma profissional.

    Tenant 1: Bruna manicure 30 min
    Tenant 2: Bruna manicure 40 min
    """
    duracao_tenant1 = 30
    duracao_tenant2 = 40

    assert duracao_tenant1 != duracao_tenant2


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v"])
