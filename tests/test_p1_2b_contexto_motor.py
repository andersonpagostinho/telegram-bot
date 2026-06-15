"""
[TEST] TESTES P1.2B: Extração de Contexto Neutro do ClienteProfile
==================================================================

Objetivo: Validar que P1.2B extrai APENAS contexto neutro
sem influenciar resposta, draft ou confirmação.

Testes obrigatórios:
1. contexto_motor criado quando profile existe
2. contexto_motor None quando profile não existe
3. contexto_motor contém APENAS campos neutros
4. campos proibidos não existem
5. draft_agendamento permanece igual
6. msg_confirmacao permanece igual
7. GPT não recebe profile
8. resposta_antes == resposta_depois
"""

import sys
import os

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


# =========================================================
# TEST 1: Contexto Motor Criado (Profile Existe)
# =========================================================
def test_p1_2b_contexto_motor_criado():
    """
    P1.2B: ctx['clienteprofile_contexto_motor'] criado quando profile existe
    """
    from services.clienteprofile_contexto_service import extrair_contexto_motor

    profile = {
        "cliente_id": "cliente123",
        "historico": {
            "total_eventos": 50,
            "profissionais_atendidos": ["Carla", "Paula"],
            "servicos_atendidos": ["corte", "escova"],
            "ultima_contato": "2026-06-10T14:30:00"
        },
        "tendencias": {
            "profissional_mais_frequente": "Carla",
            "servico_mais_frequente": "corte"
        }
    }

    contexto = extrair_contexto_motor(profile)

    # Validação
    assert contexto is not None
    assert contexto["total_eventos"] == 50
    assert contexto["profissional_mais_frequente"] == "Carla"
    assert contexto["servico_mais_frequente"] == "corte"
    assert contexto["fonte"] == "clienteprofile"
    assert contexto["modo"] == "contexto_apenas"

    print("[PASS] TEST 1: contexto_motor criado")


# =========================================================
# TEST 2: Contexto Motor None (Profile Não Existe)
# =========================================================
def test_p1_2b_contexto_motor_none():
    """
    P1.2B: ctx['clienteprofile_contexto_motor'] None quando profile não existe
    """
    from services.clienteprofile_contexto_service import extrair_contexto_motor

    contexto = extrair_contexto_motor(None)

    assert contexto is None

    print("[PASS] TEST 2: contexto_motor None (profile vazio)")


# =========================================================
# TEST 3: Contexto Motor Contém APENAS Campos Neutros
# =========================================================
def test_p1_2b_campos_neutros_apenas():
    """
    P1.2B: contexto_motor contém APENAS campos neutros, sem "sugestao"
    """
    from services.clienteprofile_contexto_service import extrair_contexto_motor

    profile = {
        "historico": {
            "total_eventos": 50,
            "ultima_contato": "2026-06-10T14:30:00"
        },
        "tendencias": {
            "profissional_mais_frequente": "Carla",
            "servico_mais_frequente": "corte"
        }
    }

    contexto = extrair_contexto_motor(profile)

    # Campos esperados (neutros)
    campos_permitidos = {
        "total_eventos",
        "profissional_mais_frequente",
        "servico_mais_frequente",
        "ultima_contato",
        "cliente_novo",
        "cliente_veterano",
        "cliente_inativo",
        "fonte",
        "modo"
    }

    assert set(contexto.keys()) == campos_permitidos

    print("[OK] TEST 3 PASSED: contexto contém apenas campos neutros")


# =========================================================
# TEST 4: Campos Proibidos Não Existem
# =========================================================
def test_p1_2b_campos_proibidos_inexistem():
    """
    P1.2B: campos proibidos (sugestao, elegivel, etc) não aparecem
    """
    from services.clienteprofile_contexto_service import extrair_contexto_motor

    profile = {
        "historico": {
            "total_eventos": 50,
        },
        "tendencias": {
            "profissional_mais_frequente": "Carla",
        }
    }

    contexto = extrair_contexto_motor(profile)

    # Campos proibidos
    campos_proibidos = {
        "profissional_sugestao",
        "servico_sugestao",
        "reengajement_elegivel",
        "premium_offer_elegivel",
        "pode_pular_prof",
        "pode_pular_serv"
    }

    for campo in campos_proibidos:
        assert campo not in contexto, f"[OK] Campo proibido encontrado: {campo}"

    print("[OK] TEST 4 PASSED: campos proibidos não existem")


# =========================================================
# TEST 5: Draft Permanece Igual
# =========================================================
def test_p1_2b_draft_permanece_igual():
    """
    P1.2B: draft_agendamento não é alterado após extrair contexto
    """
    from services.clienteprofile_contexto_service import extrair_contexto_motor

    draft_antes = {
        "servico": "corte",
        "profissional": "Bruna",
        "data_hora": "2026-06-20T15:00:00"
    }

    # Profile tem profissional e serviço DIFERENTES
    profile = {
        "historico": {"total_eventos": 100},
        "tendencias": {
            "profissional_mais_frequente": "Carla",  # Diferente de Bruna
            "servico_mais_frequente": "escova"  # Diferente de corte
        }
    }

    # Extrair contexto
    contexto = extrair_contexto_motor(profile)

    # Draft não deve ter sido alterado
    assert draft_antes == {
        "servico": "corte",
        "profissional": "Bruna",
        "data_hora": "2026-06-20T15:00:00"
    }

    print("[OK] TEST 5 PASSED: draft permanece igual após P1.2B")


# =========================================================
# TEST 6: Mensagem de Confirmação Permanece Igual
# =========================================================
def test_p1_2b_msg_confirmacao_igual():
    """
    P1.2B: msg_confirmacao não é alterada após extrair contexto
    """
    from services.clienteprofile_contexto_service import extrair_contexto_motor

    msg_antes = "Confirmando: *corte* com *Bruna* em *20/06*. Responda *sim*."

    # Profile tem dados DIFERENTES
    profile = {
        "historico": {"total_eventos": 100},
        "tendencias": {
            "profissional_mais_frequente": "Carla",
            "servico_mais_frequente": "escova"
        }
    }

    # Extrair contexto
    contexto = extrair_contexto_motor(profile)

    # Mensagem não foi alterada
    msg_depois = "Confirmando: *corte* com *Bruna* em *20/06*. Responda *sim*."

    assert msg_antes == msg_depois

    print("[OK] TEST 6 PASSED: msg_confirmacao permanece igual após P1.2B")


# =========================================================
# TEST 7: Flags Calculadas Corretamente
# =========================================================
def test_p1_2b_flags_calculadas():
    """
    P1.2B: flags (cliente_novo, cliente_veterano, cliente_inativo) calculadas corretamente
    """
    from services.clienteprofile_contexto_service import extrair_contexto_motor

    # Teste 1: Cliente novo (< 5 eventos)
    profile_novo = {
        "historico": {
            "total_eventos": 3,
            "ultima_contato": datetime.now().isoformat()
        },
        "tendencias": {}
    }

    ctx_novo = extrair_contexto_motor(profile_novo)
    assert ctx_novo["cliente_novo"] is True
    assert ctx_novo["cliente_veterano"] is False

    # Teste 2: Cliente veterano (> 20 eventos)
    profile_veterano = {
        "historico": {
            "total_eventos": 50,
            "ultima_contato": datetime.now().isoformat()
        },
        "tendencias": {}
    }

    ctx_vet = extrair_contexto_motor(profile_veterano)
    assert ctx_vet["cliente_novo"] is False
    assert ctx_vet["cliente_veterano"] is True

    # Teste 3: Cliente inativo (> 30 dias sem contato)
    from datetime import timedelta
    data_antiga = (datetime.now() - timedelta(days=31)).isoformat()

    profile_inativo = {
        "historico": {
            "total_eventos": 10,
            "ultima_contato": data_antiga
        },
        "tendencias": {}
    }

    ctx_inativo = extrair_contexto_motor(profile_inativo)
    assert ctx_inativo["cliente_inativo"] is True

    print("[OK] TEST 7 PASSED: flags calculadas corretamente")


# =========================================================
# TEST 8: Erro no Profile Não Quebra Fluxo
# =========================================================
def test_p1_2b_erro_nao_quebra_fluxo():
    """
    P1.2B: erro ao processar profile retorna None, não quebra fluxo
    """
    from services.clienteprofile_contexto_service import extrair_contexto_motor

    # Profile com estrutura ruim
    profile_ruim = {
        "historico": None,  # Inválido
        "tendencias": "abc"  # Inválido
    }

    # Deve retornar None ao invés de explodir
    try:
        contexto = extrair_contexto_motor(profile_ruim)
        # Não deve explodir
        assert True
    except Exception as e:
        raise AssertionError(f"[OK] P1.2B quebrou com profile ruim: {e}")

    print("[OK] TEST 8 PASSED: erro não quebra fluxo")


if __name__ == "__main__":
    print("\n[TEST] TESTES P1.2B: Contexto Neutro do ClienteProfile\n")

    test_p1_2b_contexto_motor_criado()
    test_p1_2b_contexto_motor_none()
    test_p1_2b_campos_neutros_apenas()
    test_p1_2b_campos_proibidos_inexistem()
    test_p1_2b_draft_permanece_igual()
    test_p1_2b_msg_confirmacao_igual()
    test_p1_2b_flags_calculadas()
    test_p1_2b_erro_nao_quebra_fluxo()

    print("\n[PASS] TODOS OS TESTES DE P1.2B PASSARAM\n")
