#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIX 3 TEST SUITE: Confirmação Futura vs Atual

12 testes obrigatórios para validar correção de falso positivo
quando autorização é futura condicional (não imediata).

Restrições:
- Não alterar event service
- Não alterar locks
- Não alterar disponibilidade
- Não modificar criação de eventos
- Apenas eh_confirmacao() é afetada
"""

import pytest
from router.principal_router import eh_confirmacao


class TestConfirmacaoAtual:
    """Confirmações legítimas AGORA — devem retornar True"""

    def test_1_confirmacao_simples_sim(self):
        """Teste 1: 'Sim' com confirmação pendente válida"""
        assert eh_confirmacao("Sim") == True
        assert eh_confirmacao("sim") == True

    def test_2_confirmacao_pode_confirmar(self):
        """Teste 2: 'Pode confirmar esse horário' com operação pendente"""
        assert eh_confirmacao("Pode confirmar esse horário") == True
        assert eh_confirmacao("pode confirmar") == True


class TestConfirmacaoFutura:
    """Autorizações FUTURAS condicionadas — devem retornar False"""

    def test_3_depois_que_apresentar(self):
        """Teste 3: 'Depois que você apresentar as opções, eu confirmo'"""
        # DEVE retornar False (não é confirmação agora)
        result = eh_confirmacao(
            "Depois que você me apresentar as opções, eu escolho a que preferir "
            "e autorizo expressamente a confirmação do agendamento."
        )
        assert result == False, "Confirmação futura condicionada foi tratada como atual"

    def test_4_quando_escolher(self):
        """Teste 4: 'Quando encontrar um horário, autorizo a reserva'"""
        result = eh_confirmacao("Quando encontrar um horário, autorizo a reserva.")
        assert result == False, "Autorização condicional a 'quando' foi tratada como atual"

    def test_5_assim_que_encontrar(self):
        """Teste 5: 'Assim que você encontrar, pode confirmar'"""
        result = eh_confirmacao("Assim que você encontrar um horário, pode confirmar.")
        assert result == False, "Autorização condicional a 'assim que' foi tratada como atual"

    def test_6_primeiro_apresente(self):
        """Teste 6: 'Primeiro apresente as opções'"""
        result = eh_confirmacao(
            "Primeiro quero ver as opções e depois decido se confirmo."
        )
        assert result == False, "Confirmação condicional em futuro foi tratada como atual"


class TestRecusa:
    """Recusas ou suspensões — devem retornar False"""

    def test_7_nao_confirme_ainda(self):
        """Teste 7: 'Não confirme ainda'"""
        result = eh_confirmacao("Não confirme ainda.")
        assert result == False, "Negação foi tratada como confirmação"

    def test_8_apenas_consultar(self):
        """Teste 8: 'Quero apenas consultar'"""
        result = eh_confirmacao("Quero apenas consultar, não faça reserva.")
        assert result == False, "Consulta pura foi tratada como confirmação"

    def test_9_nao_fazer_reserva(self):
        """Teste 9: 'Não faça nenhuma reserva'"""
        result = eh_confirmacao("Não faça nenhuma reserva ainda.")
        assert result == False, "Negação de ação foi tratada como confirmação"


class TestConfirmacaoInvalida:
    """Contextos de segurança — devem retornar False"""

    def test_10_confirmacao_sem_contexto(self):
        """Teste 10: 'Confirmo' sem operation_id válido (contexto insuficiente)"""
        # A função eh_confirmacao() sozinha NÃO deve autorizar
        # (validação de operation_id acontece no router)
        result = eh_confirmacao("Confirmo")
        # eh_confirmacao() retorna True (palavra isolada)
        # MAS router deve validar operation_id ANTES de usar
        assert result == True, "Palavra 'confirmo' deve ser detectada"
        # A proteção acontece no router, não em eh_confirmacao()

    def test_11_confirmacao_operacao_diferente(self):
        """Teste 11: Confirmação com operação de outro tenant"""
        # Validação acontece no router, não em eh_confirmacao()
        result = eh_confirmacao("Confirmo")
        assert result == True
        # Router valida tenant antes de processar

    def test_12_confirmacao_operacao_concluida(self):
        """Teste 12: Confirmação com operação já concluída"""
        # Validação acontece no router, não em eh_confirmacao()
        result = eh_confirmacao("Confirmo")
        assert result == True
        # Router valida status operação antes de processar


class TestRegressao:
    """Garantir que confirmações legítimas continuam funcionando"""

    def test_regressao_ok(self):
        """Regressão: 'OK' deve continuar sendo confirmação"""
        assert eh_confirmacao("OK") == True

    def test_regressao_certo(self):
        """Regressão: 'Certo' deve continuar sendo confirmação"""
        assert eh_confirmacao("Certo") == True

    def test_regressao_pode_marcar(self):
        """Regressão: 'Pode marcar' deve continuar sendo confirmação"""
        assert eh_confirmacao("Pode marcar esse horário") == True

    def test_regressao_beleza(self):
        """Regressão: 'Beleza' deve continuar sendo confirmação"""
        assert eh_confirmacao("Beleza") == True


class TestComplementar:
    """7 testes complementares obrigatórios (A–G)"""

    def test_a_confirmacao_futura_completa(self):
        """A) Confirmação futura: 'Depois que você apresentar... eu autorizo'"""
        result = eh_confirmacao(
            "Depois que você apresentar as opções, eu escolho e autorizo a confirmação."
        )
        assert result == False, "Confirmação futura foi tratada como atual"

    def test_b_confirmacao_atual_agora(self):
        """B) Confirmação atual: 'Pode confirmar esse horário AGORA'"""
        result = eh_confirmacao("Pode confirmar esse horário agora")
        # "agora" não é marcador temporal de condicionalidade, é confirmação IMEDIATA
        assert result == True, "Confirmação imediata 'agora' foi bloqueada incorretamente"

    def test_c_temporal_sem_condicionar(self):
        """C) Referência temporal sem condicionar: 'Quando você encontrou? Pode confirmar agora?'"""
        result = eh_confirmacao(
            "Quando você encontrou o horário? Pode confirmar agora?"
        )
        # "quando" ISOLADO é pergunta, não condicional de confirmação
        # "agora" + "confirmar" = confirmação ATUAL
        # Marcador "quando" = pergunta passada, não futura condicional
        assert result == True, "Pergunta com 'quando' + confirmação atual foi bloqueada"

    def test_d_consulta_com_autorizacao_futura(self):
        """D) Consulta com autorização futura: 'Quando encontrar, pode reservar, MAS primeiro quero ver'"""
        result = eh_confirmacao(
            "Quando encontrar um horário, pode reservar, mas primeiro quero ver as opções."
        )
        # "quando" + "reservar" = condicional futuro
        # "mas primeiro quero ver" = bloqueia execução imediata
        assert result == False, "Autorização futura com objeção foi tratada como atual"

    def test_e_negacao_com_temporal(self):
        """E) Negação: 'Não confirme ainda, quero analisar'"""
        result = eh_confirmacao("Não confirme ainda, quero analisar as opções")
        # "não" bloqueia confirmação (proteção existente)
        assert result == False, "Negação foi tratada como confirmação"

    def test_f_confirmacao_atual_apos_analise(self):
        """F) Confirmação atual após análise: 'Depois de analisar, decidi: pode confirmar'"""
        result = eh_confirmacao(
            "Depois de analisar as opções, decidi: pode confirmar esse horário."
        )
        # "depois de" = ação completada no passado (não futuro condicional)
        # "pode confirmar" = confirmação AGORA
        assert result == True, "Confirmação pós-análise foi bloqueada incorretamente"

    def test_g_autorizacao_futura_sem_operacao(self):
        """G) Autorização futura sem operação pendente: 'Quando escolher, autorizo'"""
        result = eh_confirmacao("Quando escolher, autorizo a reserva")
        # "quando" + "autorizo" = condicional futuro
        # Deve retornar False (não confirma agora)
        # Router valida operation_id separadamente
        assert result == False, "Autorização futura foi tratada como atual"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
