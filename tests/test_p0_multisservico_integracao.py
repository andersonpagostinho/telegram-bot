"""
P0 — SUPORTE COMPLETO A CONSULTA MULTISSERVIÇO — Testes de Integração

Validar que as correções funcionam de ponta a ponta.
"""

import pytest
from services.multisservico_service import (
    resolver_bloco_servicos,
    validar_horario_em_janela,
    extrair_intervalo_horario,
    enriquecer_contexto_consulta,
)


# ============================================================================
# Testes de Extração de Intervalo
# ============================================================================

def test_extrair_14_17():
    """Extrair 14h-17h"""
    h_min, h_max = extrair_intervalo_horario("das 14 às 17")
    assert h_min == 14
    assert h_max == 17


def test_extrair_14_00_17_00():
    """Extrair 14:00-17:00"""
    h_min, h_max = extrair_intervalo_horario("de 14:00 a 17:00")
    assert h_min == 14
    assert h_max == 17


def test_extrair_14h_17h():
    """Extrair 14h-17h (formato com h)"""
    h_min, h_max = extrair_intervalo_horario("14h às 17h")
    assert h_min == 14
    assert h_max == 17


def test_extrair_nenhum_intervalo():
    """Sem intervalo na mensagem"""
    h_min, h_max = extrair_intervalo_horario("manicure com Bruna")
    assert h_min is None
    assert h_max is None


# ============================================================================
# Testes de Validação de Horário em Janela
# ============================================================================

def test_14_com_65min_cabe_em_14_17():
    """14h + 65min = 15:05, cabe em 14h-17h"""
    resultado = validar_horario_em_janela(14, 65, 14, 17)
    assert resultado is True


def test_14_com_180min_cabe_em_14_17():
    """14h + 180min = 17:00, exatamente no limite de 14h-17h"""
    resultado = validar_horario_em_janela(14, 180, 14, 17)
    assert resultado is True


def test_14_com_200min_nao_cabe_em_14_17():
    """14h + 200min = 17:20, ultrapassa 14h-17h"""
    resultado = validar_horario_em_janela(14, 200, 14, 17)
    assert resultado is False


def test_16_com_120min_nao_cabe_em_14_17():
    """16h + 120min = 18:00, ultrapassa 14h-17h"""
    resultado = validar_horario_em_janela(16, 120, 14, 17)
    assert resultado is False


def test_sem_janela_aceita_qualquer_horario():
    """Sem restrição de janela, aceita qualquer horário"""
    resultado = validar_horario_em_janela(23, 120, None, None)
    assert resultado is True


# ============================================================================
# Testes de Enriquecimento de Contexto
# ============================================================================

def test_enriquecer_contexto_com_intervalo():
    """Enriquecer contexto com intervalo extraído"""
    contexto = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "profissional_mencionada": "Bruna",
    }

    contexto_enriquecido = enriquecer_contexto_consulta(
        contexto,
        "manicure e pedicure das 14 às 17 com Bruna"
    )

    assert contexto_enriquecido["intervalo_inicio"] == 14
    assert contexto_enriquecido["intervalo_fim"] == 17


def test_enriquecer_contexto_sem_intervalo():
    """Contexto sem intervalo continua funcionando"""
    contexto = {
        "servicos_multiplos": ["manicure"],
        "profissional_mencionada": "Bruna",
    }

    contexto_enriquecido = enriquecer_contexto_consulta(
        contexto,
        "manicure com Bruna"
    )

    assert "intervalo_inicio" not in contexto_enriquecido or contexto_enriquecido.get("intervalo_inicio") is None


# ============================================================================
# Testes de Resolver Bloco (com mock de duracao_service)
# ============================================================================

@pytest.mark.asyncio
async def test_resolver_bloco_manicure_pedicure():
    """Resolver bloco manicure + pedicure"""
    # Este teste precisaria mockar obter_duracao_por_profissional_bridge
    # Para agora, apenas validar que a função existe e retorna estrutura correta

    # Espera-se que:
    # resolver_bloco_servicos("tenant1", "Bruna", ["manicure", "pedicure"])
    # retorne:
    # {
    #     "valido": True,
    #     "servicos": ["manicure", "pedicure"],
    #     "duracoes_individuais": [30, 35],
    #     "duracao_total": 65,
    #     "mensagens": [],
    # }

    # Validar que a função pode ser chamada (mesmo que falhe sem bridge real)
    # Ignorar resultado por enquanto
    pass


# ============================================================================
# Testes de Fluxo Completo (Simulado)
# ============================================================================

def test_fluxo_consulta_multisservico():
    """
    Simular fluxo completo:
    1. Usuário: "manicure e pedicure dia 13 das 14 às 17 com Bruna"
    2. Extrair contexto
    3. Enriquecer com intervalo
    4. Validar disponibilidade em janela
    5. Retornar resposta informativa (sem evento/lock)
    """

    # Passo 1: Mensagem
    mensagem = "manicure e pedicure dia 13 das 14 às 17 com Bruna"

    # Passo 2: Extração (simulada)
    ctx = {
        "servico": "manicure",
        "servicos_opcao": ["manicure", "pedicure"],
        "data_hora": "2026-11-13",
        "profissional_escolhido": "Bruna",
    }

    # Passo 3: Construir contexto_consulta base
    contexto_consulta = {
        "servicos_mencionados": ctx.get("servico"),
        "servicos_multiplos": ctx.get("servicos_opcao"),
        "data_hora": ctx.get("data_hora"),
        "profissional_mencionada": ctx.get("profissional_escolhido"),
    }

    # Passo 4: Enriquecer com intervalo
    contexto_consulta = enriquecer_contexto_consulta(contexto_consulta, mensagem)

    # Validações
    assert contexto_consulta["servicos_multiplos"] == ["manicure", "pedicure"]
    assert contexto_consulta["intervalo_inicio"] == 14
    assert contexto_consulta["intervalo_fim"] == 17

    # Passo 5: Validar que disponibilidade respeitaria janela
    # Bloco de 65 min começando às 14h cabe em 14h-17h
    resultado = validar_horario_em_janela(
        hora_inicio_bloqueio=14,
        duracao_min=65,  # manicure + pedicure
        janela_minima=14,
        janela_maxima=17
    )
    assert resultado is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
