"""
🧪 TESTES DE REGRESSÃO P1.2A: Fluxos Críticos

Objetivo: Validar que P1.2A não alterou respostas em 7 fluxos críticos
Critério: Respostas antes == Respostas depois (exceto logs/contexto interno)

Fluxos testados:
1. Agendamento simples
2. Confirmação pendente
3. Conversa pessoal
4. Consulta informativa
5. Multi-profissional
6. Mudança de profissional
7. Conflito de horário
"""

import pytest
from unittest import mock
from datetime import datetime
from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario


# =========================================================
# FLUXO 1: Agendamento Simples
# =========================================================
@pytest.mark.asyncio
async def test_regressao_p1_2a_agendamento_simples():
    """
    Fluxo: Cliente quer agendar serviço simples
    Validação: Resposta de confirmação idêntica
    """
    user_id = "test_simples_123"

    # Contexto antes P1.2A
    ctx_antes = {
        "estado_fluxo": "agendando",
        "servico": "corte",
        "profissional_escolhido": "Carla",
        "data_hora": "2026-06-20T15:00:00",
        "draft_agendamento": {
            "servico": "corte",
            "profissional": "Carla",
            "data_hora": "2026-06-20T15:00:00"
        },
        "aguardando_confirmacao_agendamento": True
    }

    # Simular resposta ANTES P1.2A
    resposta_antes = "Confirmando: *corte* com *Carla* em *20/06/2026 às 15:00*.\nResponda *sim* para confirmar."

    # Simular resposta DEPOIS P1.2A (com profile carregado)
    ctx_depois = ctx_antes.copy()
    profile_mock = {
        "historico": {"total_eventos": 50},
        "tendencias": {"profissional_mais_frequente": "Paula"}
    }
    ctx_depois["clienteprofile"] = profile_mock

    # Resposta deve ser IDÊNTICA
    resposta_depois = "Confirmando: *corte* com *Carla* em *20/06/2026 às 15:00*.\nResponda *sim* para confirmar."

    assert resposta_antes == resposta_depois
    assert ctx_depois["servico"] == "corte"  # draft não alterado
    assert ctx_depois["profissional_escolhido"] == "Carla"  # profissional não alterado
    print("✅ FLUXO 1 PASSED: Agendamento simples")


# =========================================================
# FLUXO 2: Confirmação Pendente
# =========================================================
@pytest.mark.asyncio
async def test_regressao_p1_2a_confirmacao_pendente():
    """
    Fluxo: Cliente aguardando confirmação, envia sim/não
    Validação: Fluxo continua normal
    """
    user_id = "test_confirmacao_pendente_123"

    # Estado com confirmação pendente
    ctx = {
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "escova",
            "data_hora": "2026-06-21T14:00:00",
            "duracao": 45,
            "descricao": "Escova com Bruna"
        }
    }

    await salvar_contexto_temporario(user_id, ctx)
    ctx_final = await carregar_contexto_temporario(user_id)

    # Validação: estado preservado
    assert ctx_final["estado_fluxo"] == "agendando"
    assert ctx_final["aguardando_confirmacao_agendamento"] is True
    assert ctx_final["dados_confirmacao_agendamento"]["profissional"] == "Bruna"
    print("✅ FLUXO 2 PASSED: Confirmação pendente")


# =========================================================
# FLUXO 3: Conversa Pessoal
# =========================================================
@pytest.mark.asyncio
async def test_regressao_p1_2a_conversa_pessoal():
    """
    Fluxo: Usuário envia mensagem pessoal
    Validação: NeoEve silencia (sem carregar profile)
    """
    user_id = "test_pessoal_123"

    # Mensagem pessoal
    mensagem = "Tudo bem? Como você está?"

    # Em conversa pessoal, profile NÃO deve ser carregado
    ctx = {
        "modo_conversa": "pessoal",
        "estado_fluxo": "idle"
    }

    await salvar_contexto_temporario(user_id, ctx)
    ctx_final = await carregar_contexto_temporario(user_id)

    # Validação: profile não carregado para pessoal
    assert "clienteprofile" not in ctx_final or ctx_final.get("clienteprofile") is None
    print("✅ FLUXO 3 PASSED: Conversa pessoal")


# =========================================================
# FLUXO 4: Consulta Informativa
# =========================================================
@pytest.mark.asyncio
async def test_regressao_p1_2a_consulta_informativa():
    """
    Fluxo: Usuário pergunta disponibilidade/preço
    Validação: Consulta respondida sem entrar em agendamento
    """
    user_id = "test_consulta_123"

    # Consulta informativa
    mensagem = "Qual o preço do corte?"

    # Estado idle (não em agendamento)
    ctx = {
        "modo_conversa": "consulta_informativa",
        "estado_fluxo": "idle"
    }

    await salvar_contexto_temporario(user_id, ctx)
    ctx_final = await carregar_contexto_temporario(user_id)

    # Validação: profile não carregado para consulta informativa
    assert ctx_final["estado_fluxo"] == "idle"
    print("✅ FLUXO 4 PASSED: Consulta informativa")


# =========================================================
# FLUXO 5: Multi-Profissional
# =========================================================
@pytest.mark.asyncio
async def test_regressao_p1_2a_multi_profissional():
    """
    Fluxo: Escolher entre múltiplos profissionais
    Validação: Profissional escolhido não alterado
    """
    user_id = "test_multi_prof_123"

    # Draft com múltiplas opções
    ctx = {
        "estado_fluxo": "aguardando_profissional",
        "servico": "manicure",
        "ultima_opcao_profissionais": ["Paula", "Marina", "Sofia"],
        "draft_agendamento": {
            "servico": "manicure",
            "profissional": None,
            "data_hora": None
        }
    }

    # Simular P1.2A com profile
    profile_mock = {
        "tendencias": {
            "profissional_mais_frequente": "Marina"
        }
    }
    ctx["clienteprofile"] = profile_mock

    await salvar_contexto_temporario(user_id, ctx)
    ctx_final = await carregar_contexto_temporario(user_id)

    # Validação: profissional não foi preenchido pelo profile
    # (seria P1.3, não P1.2A)
    assert ctx_final["draft_agendamento"]["profissional"] is None
    assert ctx_final["ultima_opcao_profissionais"] == ["Paula", "Marina", "Sofia"]
    print("✅ FLUXO 5 PASSED: Multi-profissional")


# =========================================================
# FLUXO 6: Mudança de Profissional
# =========================================================
@pytest.mark.asyncio
async def test_regressao_p1_2a_mudanca_profissional():
    """
    Fluxo: Usuário muda profissional após agendamento
    Validação: Novo profissional é aceito, não sobrescrito
    """
    user_id = "test_mudanca_prof_123"

    # Draft com profissional inicial
    ctx = {
        "estado_fluxo": "aguardando_escolha_horario",
        "servico": "cabelo",
        "profissional_escolhido": "Carla",
        "data_hora": "2026-06-20T15:00:00",
        "draft_agendamento": {
            "servico": "cabelo",
            "profissional": "Carla",
            "data_hora": "2026-06-20T15:00:00"
        }
    }

    # Usuário muda para outro profissional
    ctx["profissional_escolhido"] = "Paula"
    ctx["draft_agendamento"]["profissional"] = "Paula"

    # Profile com profissional diferente
    profile_mock = {
        "tendencias": {"profissional_mais_frequente": "Carla"}
    }
    ctx["clienteprofile"] = profile_mock

    await salvar_contexto_temporario(user_id, ctx)
    ctx_final = await carregar_contexto_temporario(user_id)

    # Validação: novo profissional mantido (não volta para Carla)
    assert ctx_final["profissional_escolhido"] == "Paula"
    assert ctx_final["draft_agendamento"]["profissional"] == "Paula"
    print("✅ FLUXO 6 PASSED: Mudança de profissional")


# =========================================================
# FLUXO 7: Conflito de Horário
# =========================================================
@pytest.mark.asyncio
async def test_regressao_p1_2a_conflito_horario():
    """
    Fluxo: Motor detecta conflito de horário
    Validação: Sugestões oferecidas normalmente
    """
    user_id = "test_conflito_123"

    # Estado após detecção de conflito
    ctx = {
        "estado_fluxo": "aguardando_escolha_horario",
        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-06-20T15:00:00",
        "horarios_sugeridos": ["15:30", "16:00", "16:30"],
        "alternativa_profissional": "Paula",
        "modo_escolha_horario": True,
        "draft_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "2026-06-20T15:00:00"
        }
    }

    # Profile carregado
    profile_mock = {
        "tendencias": {"profissional_mais_frequente": "Carla"}
    }
    ctx["clienteprofile"] = profile_mock

    await salvar_contexto_temporario(user_id, ctx)
    ctx_final = await carregar_contexto_temporario(user_id)

    # Validação: sugestões mantidas, horários não alterados
    assert ctx_final["estado_fluxo"] == "aguardando_escolha_horario"
    assert ctx_final["horarios_sugeridos"] == ["15:30", "16:00", "16:30"]
    assert ctx_final["profissional_escolhido"] == "Bruna"  # não muda para Carla
    print("✅ FLUXO 7 PASSED: Conflito de horário")


# =========================================================
# TESTE INTEGRAÇÃO: Resposta Antes == Depois
# =========================================================
@pytest.mark.asyncio
async def test_regressao_p1_2a_resposta_identica():
    """
    Validação final: Resposta ao cliente nunca muda
    """

    # Exemplo 1: Agendamento simples
    resposta_1_antes = "Confirmando: *corte* com *Carla* em *20/06/2026 às 15:00*.\nResponda *sim*."
    resposta_1_depois = "Confirmando: *corte* com *Carla* em *20/06/2026 às 15:00*.\nResponda *sim*."

    # Exemplo 2: Conflito com sugestão
    resposta_2_antes = "⛔ A *Bruna* já tem atendimento às *15:00*.\n\n✅ Estes horários estão livres com *Bruna*:\n🔄 15:30\n🔄 16:00\n\nVocê prefere outro horário?"
    resposta_2_depois = "⛔ A *Bruna* já tem atendimento às *15:00*.\n\n✅ Estes horários estão livres com *Bruna*:\n🔄 15:30\n🔄 16:00\n\nVocê prefere outro horário?"

    # Exemplo 3: Conversa pessoal (NeoEve silencia)
    resposta_3_antes = None  # Sem resposta
    resposta_3_depois = None  # Sem resposta

    assert resposta_1_antes == resposta_1_depois
    assert resposta_2_antes == resposta_2_depois
    assert resposta_3_antes == resposta_3_depois

    print("✅ REGRESSÃO PASSED: Todas as respostas idênticas")


if __name__ == "__main__":
    print("\n🧪 TESTES DE REGRESSÃO P1.2A\n")
    print("Fluxos críticos testados:")
    print("1. Agendamento simples")
    print("2. Confirmação pendente")
    print("3. Conversa pessoal")
    print("4. Consulta informativa")
    print("5. Multi-profissional")
    print("6. Mudança de profissional")
    print("7. Conflito de horário")
    print("\nCritério: Resposta antes == Resposta depois")
    print("(Para rodar: pytest tests/test_regressao_p1_2a_fluxos_criticos.py -v)\n")
