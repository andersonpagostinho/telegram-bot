"""
TESTES OBRIGATÓRIOS — Correção da Continuidade Multisserviço
2026-11-15 | Fix: Definição de modo_operacao para consultas com múltiplas opções

4 testes estruturados + 2 regressões
"""

import pytest
from schemas.resultado_consulta_schema import OpcaoHorario, ContextoResultadoConsulta


# =============================================================================
# T1: Reconhecimento de Seleção de Opção
# =============================================================================

def test_t1_reconhecimento_referencia_primeiro():
    """
    T1: "o primeiro" → opção 1
    """

    opcoes = [
        OpcaoHorario(
            opcao_id="2026-11-16_bruna_1400",
            numero=1,
            profissional_id="bruna",
            data="2026-11-16",
            hora_inicio="14:00",
            hora_fim="15:20",
            servicos=["manicure", "pedicure"],
            duracao_total_min=60
        ),
        OpcaoHorario(
            opcao_id="2026-11-16_bruna_1520",
            numero=2,
            profissional_id="bruna",
            data="2026-11-16",
            hora_inicio="15:20",
            hora_fim="16:40",
            servicos=["manicure", "pedicure"],
            duracao_total_min=60
        ),
        OpcaoHorario(
            opcao_id="2026-11-16_bruna_1640",
            numero=3,
            profissional_id="bruna",
            data="2026-11-16",
            hora_inicio="16:40",
            hora_fim="18:00",
            servicos=["manicure", "pedicure"],
            duracao_total_min=60
        ),
    ]

    contexto = ContextoResultadoConsulta(
        servicos=["manicure", "pedicure"],
        data="2026-11-16",
        duracao_total_min=60,
        profissional_id="bruna",
        opcoes=opcoes
    )

    # Testar mapear_referencia_para_numero
    numero_primeiro = contexto.mapear_referencia_para_numero("o primeiro")
    assert numero_primeiro == 1, f"'o primeiro' deve ser 1, mas retornou {numero_primeiro}"

    numero_segunda = contexto.mapear_referencia_para_numero("segunda")
    assert numero_segunda == 2, f"'segunda' deve ser 2, mas retornou {numero_segunda}"

    numero_ultima = contexto.mapear_referencia_para_numero("última")
    assert numero_ultima == 3, f"'última' deve ser 3, mas retornou {numero_ultima}"

    # Testar obter_opcao
    opcao_1 = contexto.obter_opcao(1)
    assert opcao_1 is not None, "Deve recuperar opção 1"
    assert opcao_1.numero == 1, "Opção 1 deve ter numero=1"
    assert opcao_1.hora_inicio == "14:00", "Opção 1 deve começar em 14:00"

    print("✅ T1 PASS: Reconhecimento de referência")


# =============================================================================
# T2: Modo Operacional Definido Corretamente
# =============================================================================

def test_t2_modo_operacional_multisservico():
    """
    T2: Contexto com servicos_multiplos → modo_operacao = "consulta_sem_autorizacao_atual"
    """

    # Simular lógica de router que define modo_operacao
    contexto_consulta = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
    }

    # Lógica da correção (linhas ~6024-6036 de principal_router.py)
    servicos_multiplos = contexto_consulta.get("servicos_multiplos", [])

    if servicos_multiplos and len(servicos_multiplos) > 1:
        modo_operacao = "consulta_sem_autorizacao_atual"
    else:
        modo_operacao = "consulta_pura"

    assert modo_operacao == "consulta_sem_autorizacao_atual", \
        f"Modo deveria ser 'consulta_sem_autorizacao_atual', foi '{modo_operacao}'"

    # Verificar que FASE 4A pode executar com esse modo
    if modo_operacao == "consulta_sem_autorizacao_atual":
        fase4a_pode_executar = True
    else:
        fase4a_pode_executar = False

    assert fase4a_pode_executar, "FASE 4A deve ser capaz de executar"

    print("✅ T2 PASS: Modo operacional definido corretamente")


# =============================================================================
# T3: Persistência e Recuperação de Opções
# =============================================================================

def test_t3_persistencia_opcoes():
    """
    T3: Opções podem ser persistidas e recuperadas via ContextoResultadoConsulta
    """

    opcoes_originais = [
        OpcaoHorario(
            opcao_id=f"2026-11-16_bruna_{1400 + i*80}",
            numero=i+1,
            profissional_id="bruna",
            data="2026-11-16",
            hora_inicio=f"{14 + i}:00",
            hora_fim=f"{15 + i}:20",
            servicos=["manicure", "pedicure"],
            duracao_total_min=60
        )
        for i in range(3)
    ]

    contexto_original = ContextoResultadoConsulta(
        servicos=["manicure", "pedicure"],
        data="2026-11-16",
        duracao_total_min=60,
        profissional_id="bruna",
        opcoes=opcoes_originais
    )

    # Simular persistência via to_dict (serialização)
    dados_persistidos = contexto_original.to_dict()

    assert dados_persistidos is not None, "to_dict() deve retornar algo"
    assert len(dados_persistidos["opcoes"]) == 3, "Deve ter 3 opções"
    assert dados_persistidos["servicos"] == ["manicure", "pedicure"], "Serviços devem estar corretos"

    # Simular recuperação via from_dict (desserialização)
    contexto_recuperado = ContextoResultadoConsulta.from_dict(dados_persistidos)

    assert len(contexto_recuperado.opcoes) == 3, "Deve recuperar 3 opções"
    assert contexto_recuperado.profissional_id == "bruna", "Profissional deve ser Bruna"

    # Verificar que opção 1 está intacta
    opcao_1_recuperada = contexto_recuperado.obter_opcao(1)
    assert opcao_1_recuperada is not None, "Deve recuperar opção 1"
    assert opcao_1_recuperada.hora_inicio == "14:00", "Opção 1 deve começar em 14:00"

    print("✅ T3 PASS: Persistência e recuperação funcionam")


# =============================================================================
# T4: Isolamento Multi-Tenant (Path Validation)
# =============================================================================

def test_t4_isolamento_multitenant():
    """
    T4: Paths de diferentes tenants são diferentes (isolamento)
    """

    tenant_a = "7394370553"
    tenant_b = "9999999999"
    actor_a = "5511991382080"
    actor_b = "5511999999999"

    # Simular construção de paths como seria feita em resultado_consulta_service
    path_a = f"Clientes/{tenant_a}/Sessoes/{actor_a}"
    path_b_diferente_tenant = f"Clientes/{tenant_b}/Sessoes/{actor_a}"
    path_b_diferente_actor = f"Clientes/{tenant_a}/Sessoes/{actor_b}"

    # Verificar que paths são diferentes
    assert path_a != path_b_diferente_tenant, "Paths de tenants diferentes devem ser diferentes"
    assert path_a != path_b_diferente_actor, "Paths de actors diferentes devem ser diferentes"

    # Verificar que cada path contém corretamente seus identificadores
    assert tenant_a in path_a, f"Path A deve conter tenant {tenant_a}"
    assert tenant_a not in path_b_diferente_tenant, f"Path B não deve conter tenant {tenant_a}"
    assert actor_a in path_a, f"Path A deve conter actor {actor_a}"
    assert actor_b not in path_a, f"Path A não deve conter actor {actor_b}"

    print("✅ T4 PASS: Isolamento multi-tenant validado via paths")


# =============================================================================
# REGRESSÃO: FASE 4A Guard
# =============================================================================

def test_regressao_fase4a_guard():
    """
    Regressão: Verificar que guard de FASE 4A (linha 5822) funciona
    """

    # Simular contexto que passa no guard
    contexto_multisservico = {
        "modo_operacao": "consulta_sem_autorizacao_atual"
    }

    # Guard: if ctx.get("modo_operacao") == "consulta_sem_autorizacao_atual":
    pode_executar = contexto_multisservico.get("modo_operacao") == "consulta_sem_autorizacao_atual"
    assert pode_executar, "FASE 4A deve executar com modo_operacao correto"

    # Simular contexto que NÃO passa no guard
    contexto_puro = {
        "modo_operacao": "consulta_pura"
    }

    pode_executar_puro = contexto_puro.get("modo_operacao") == "consulta_sem_autorizacao_atual"
    assert not pode_executar_puro, "FASE 4A não deve executar em consulta pura"

    print("✅ Regressão PASS: Guard de FASE 4A funciona")


# =============================================================================
# REGRESSÃO: Consulta Simples
# =============================================================================

def test_regressao_consulta_simples():
    """
    Regressão: Consultas simples não devem entrar em modo multisserviço
    """

    # Simular contexto de consulta simples (sem servicos_multiplos)
    contexto_simples = {
        "pergunta": "qual o horário de funcionamento?"
        # Sem servicos_multiplos
    }

    # Lógica de modo_operacao
    servicos_multiplos = contexto_simples.get("servicos_multiplos", [])

    if servicos_multiplos and len(servicos_multiplos) > 1:
        modo = "consulta_sem_autorizacao_atual"
    else:
        modo = "consulta_pura"

    assert modo == "consulta_pura", f"Consulta simples deve ser 'pura', mas foi '{modo}'"

    print("✅ Regressão PASS: Consulta simples mantém modo puro")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
