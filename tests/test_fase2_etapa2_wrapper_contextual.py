"""
TESTES — FASE 2 ETAPA 2: WRAPPER CONTEXTUAL DO CLASSIFICADOR

8 testes obrigatórios + testes de compatibilidade
Sem Firestore, apenas classificação e contexto
"""

import pytest
from services.classificador_conversa import (
    classificar_intencao_com_contexto,
    classificar_intencao_conversacional,
)


# =========================================================
# 8 TESTES OBRIGATÓRIOS
# =========================================================

def test_1_consulta_durante_agendamento():
    """Cenário A: Aguardando profissional + 'Quanto custa escova?'"""
    contexto = {
        "draft_agendamento": {"servico": "escova"},
        "estado_fluxo": "aguardando_profissional"
    }

    resultado = classificar_intencao_com_contexto(
        "Quanto custa escova?",
        contexto
    )

    assert resultado["é_mudanca_assunto"] == True
    assert resultado["recomendacao_acao"] == "responder_mudanca_preservar_draft"
    assert resultado["contexto_ativo"]["proxima_acao_esperada"] == "aguardando_profissional"
    assert resultado["contexto_ativo"]["draft_agendamento"]["servico"] == "escova"


def test_2_consulta_em_confirmacao_pendente():
    """Cenário B: Confirmação pendente + 'Qual o preço da manicure?'"""
    contexto = {
        "draft_agendamento": {"servico": "manicure", "profissional": "Bruna", "data_hora": "2026-11-05T14:00:00"},
        "estado_fluxo": "aguardando_confirmacao_agendamento",
        "aguardando_confirmacao_agendamento": True
    }

    resultado = classificar_intencao_com_contexto(
        "Qual o preço da manicure?",
        contexto
    )

    assert resultado["é_mudanca_assunto"] == True
    assert resultado["recomendacao_acao"] == "responder_mudanca_em_confirmacao"
    assert resultado["contexto_ativo"]["confirmacao_pendente"] == True
    assert resultado["contexto_ativo"]["proxima_acao_esperada"] == "aguardando_confirmacao"


def test_3_continuacao_normal_agendamento():
    """Cenário C: Aguardando profissional + 'Bruna'"""
    contexto = {
        "draft_agendamento": {"servico": "escova"},
        "estado_fluxo": "aguardando_profissional"
    }

    resultado = classificar_intencao_com_contexto(
        "Bruna",
        contexto
    )

    assert resultado["é_mudanca_assunto"] == False
    assert resultado["recomendacao_acao"] == "continuar_agendamento"
    assert resultado["intencao_conversacional"] == "ajuste_incremental"


def test_4_novo_agendamento_draft_anterior():
    """Cenário D: Draft anterior + novo pedido diferente"""
    contexto = {
        "draft_agendamento": {"servico": "corte"},  # Draft antigo
        "estado_fluxo": "idle"
    }

    resultado = classificar_intencao_com_contexto(
        "Quero manicure terça às 14h",
        contexto
    )

    # Novo agendamento com serviço diferente = novo agendamento, não mudança
    assert resultado["é_mudanca_assunto"] == False
    assert resultado["intencao_conversacional"] == "agendamento_direto"


def test_5_alteracao_profissional():
    """Cenário E: Alteração de profissional durante agendamento"""
    contexto = {
        "draft_agendamento": {"servico": "corte", "profissional": "Joana"},
        "estado_fluxo": "aguardando_data_hora"
    }

    resultado = classificar_intencao_com_contexto(
        "Na verdade prefiro a Bruna",
        contexto
    )

    assert resultado["é_mudanca_assunto"] == False  # Ajuste esperado
    assert resultado["intencao_conversacional"] == "ajuste_incremental"
    assert resultado["contexto_ativo"]["proxima_acao_esperada"] == "aguardando_data_hora"


def test_6_alteracao_servico():
    """Cenário F: Alteração de serviço durante agendamento"""
    contexto = {
        "draft_agendamento": {"servico": "corte"},
        "estado_fluxo": "aguardando_profissional"
    }

    resultado = classificar_intencao_com_contexto(
        "Na verdade prefiro escova",
        contexto
    )

    assert resultado["é_mudanca_assunto"] == False  # Ajuste esperado
    assert resultado["intencao_conversacional"] == "ajuste_incremental"
    assert resultado["contexto_ativo"]["proxima_acao_esperada"] == "aguardando_profissional"


def test_7_mensagem_ambigua():
    """Cenário G: Mensagem ambígua sem classificação clara"""
    resultado = classificar_intencao_com_contexto(
        "xyz abc 123"
    )

    assert resultado["necessita_esclarecimento"] == True
    assert resultado["intencao_conversacional"] == "indefinida"
    assert resultado["recomendacao_acao"] == "pedir_esclarecimento"


def test_8_pergunta_sem_sessao_ativa():
    """Cenário H: Pergunta independente sem sessão ativa"""
    contexto = {}  # Sem draft, sem estado

    resultado = classificar_intencao_com_contexto(
        "Qual é o horário de funcionamento?",
        contexto
    )

    assert resultado["é_mudanca_assunto"] == False  # Sem fluxo ativo = não é mudança
    assert resultado["contexto_ativo"]["draft_agendamento"] is None
    assert resultado["contexto_ativo"]["estado_fluxo"] is None


# =========================================================
# TESTES DE COMPATIBILIDADE (12 tipos existentes)
# =========================================================

def test_compat_confirmacao_agendamento():
    """Verificar que confirmacao_agendamento continua funcionando"""
    contexto = {
        "draft_agendamento": {"servico": "corte", "profissional": "Bruna", "data_hora": "2026-11-05T14:00:00"},
        "aguardando_confirmacao_agendamento": True,
        "estado_fluxo": "aguardando_confirmacao_agendamento"
    }

    resultado = classificar_intencao_com_contexto("sim", contexto)
    resultado_base = classificar_intencao_conversacional("sim", contexto)

    assert resultado["intencao_conversacional"] == resultado_base["intencao_conversacional"]
    assert resultado["confianca"] == resultado_base["confianca"]


def test_compat_cancelamento():
    """Verificar que cancelamento continua funcionando"""
    contexto = {"draft_agendamento": {"servico": "corte"}}

    resultado = classificar_intencao_com_contexto("cancela", contexto)
    resultado_base = classificar_intencao_conversacional("cancela", contexto)

    assert resultado["intencao_conversacional"] == "cancelamento"
    assert resultado["intencao_conversacional"] == resultado_base["intencao_conversacional"]


def test_compat_agendamento_direto():
    """Verificar que agendamento_direto continua funcionando"""
    contexto = {}

    resultado = classificar_intencao_com_contexto("Quero corte terça às 14h", contexto)
    resultado_base = classificar_intencao_conversacional("Quero corte terça às 14h", contexto)

    assert resultado["intencao_conversacional"] == "agendamento_direto"
    assert resultado["intencao_conversacional"] == resultado_base["intencao_conversacional"]


def test_compat_ajuste_incremental():
    """Verificar que ajuste_incremental continua funcionando"""
    contexto = {
        "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
        "estado_fluxo": "aguardando_data_hora"
    }

    resultado = classificar_intencao_com_contexto("Preferir mais tarde", contexto)
    resultado_base = classificar_intencao_conversacional("Preferir mais tarde", contexto)

    assert resultado["intencao_conversacional"] == "ajuste_incremental"
    assert resultado["tipo_ajuste_incremental"] == resultado_base["tipo_ajuste_incremental"]


def test_compat_consulta_disponibilidade_servico():
    """Verificar que consulta_disponibilidade_servico continua funcionando"""
    contexto = {"draft_agendamento": {"servico": "corte"}}

    resultado = classificar_intencao_com_contexto("Qual o preço?", contexto)
    resultado_base = classificar_intencao_conversacional("Qual o preço?", contexto)

    assert resultado["intencao_conversacional"] == resultado_base["intencao_conversacional"]
    assert resultado["confianca"] == resultado_base["confianca"]


# =========================================================
# TESTES DE PROTEÇÃO (Cenários Críticos)
# =========================================================

def test_protecao_a_consulta_durante_agendamento():
    """Proteção A: Aguardando profissional + 'Quanto custa escova?'"""
    contexto = {
        "draft_agendamento": {"servico": "escova"},
        "estado_fluxo": "aguardando_profissional"
    }

    resultado = classificar_intencao_com_contexto("Quanto custa escova?", contexto)

    # Deve preservar draft
    assert resultado["contexto_ativo"]["draft_agendamento"]["servico"] == "escova"
    # Deve detectar como mudança
    assert resultado["é_mudanca_assunto"] == True
    # Mas não deve ser confirmacao_agendamento
    assert resultado["intencao_conversacional"] != "confirmacao_agendamento"


def test_protecao_b_confirmacao_com_pergunta():
    """Proteção B: Confirmação pendente + pergunta sobre preço"""
    contexto = {
        "draft_agendamento": {"servico": "manicure", "profissional": "Bruna"},
        "aguardando_confirmacao_agendamento": True,
        "estado_fluxo": "aguardando_confirmacao_agendamento"
    }

    resultado = classificar_intencao_com_contexto("Quanto custa mesmo?", contexto)

    # Deve ser mudança de assunto em confirmação
    assert resultado["é_mudanca_assunto"] == True
    assert resultado["recomendacao_acao"] == "responder_mudanca_em_confirmacao"


def test_protecao_c_continuacao_sem_mudanca():
    """Proteção C: Aguardando profissional + nome do catálogo"""
    contexto = {
        "draft_agendamento": {"servico": "escova"},
        "estado_fluxo": "aguardando_profissional"
    }

    resultado = classificar_intencao_com_contexto("Bruna", contexto)

    # NÃO deve ser mudança de assunto
    assert resultado["é_mudanca_assunto"] == False
    # Deve ser continuação do agendamento
    assert resultado["intencao_conversacional"] == "ajuste_incremental"


def test_protecao_e_novo_agendamento():
    """Proteção E: Novo agendamento com serviço diferente"""
    contexto = {
        "draft_agendamento": {"servico": "corte"},  # Anterior
        "estado_fluxo": "idle"
    }

    resultado = classificar_intencao_com_contexto("Quero manicure agora", contexto)

    # Não deve ser mudança, deve ser novo agendamento
    assert resultado["é_mudanca_assunto"] == False
    assert resultado["intencao_conversacional"] == "agendamento_direto"


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v"])
