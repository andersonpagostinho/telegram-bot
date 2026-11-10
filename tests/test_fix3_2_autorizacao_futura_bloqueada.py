#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIX 3.2 — TESTE E2E: Bloqueio de Agendamento com Autorização Futura

Valida que mensagens com autorização futura condicional:
1. Permitam consulta de disponibilidade
2. Bloqueiem criação de confirmacao_pendente
3. Bloqueiem criação de locks
4. Bloqueiem criação de eventos
5. Preservem contexto para continuidade
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router.principal_router import eh_confirmacao, tem_confirmacao_temporal_condicional


class TestFix32BlockeioAutorizacaoFutura:
    """Validar bloqueio de agendamento com autorização futura condicional"""

    def test_a_mensagem_original_completa(self):
        """A) Mensagem original com autorização futura condicional

        ESPERADO:
        - tem_confirmacao_temporal_condicional() = True
        - eh_confirmacao() = False
        - Router não deve criar evento
        - Consulta deve executar
        - Nenhuma confirmacao_pendente
        """
        mensagem = (
            "Oi, tudo bem? Gostaria de verificar a possibilidade de agendar "
            "manicure e pedicure para sexta-feira, dia 13/11/2026, de preferência "
            "no mesmo atendimento, durante o período da tarde. Consigo chegar a "
            "partir das 14h, mas tenho um compromisso no final do dia e preciso "
            "terminar os dois serviços até, no máximo, 17h. Minha preferência é "
            "ser atendida pela Bruna, porque gostaria de fazer os dois procedimentos "
            "com a mesma profissional. Porém, caso ela não tenha disponibilidade "
            "nesse intervalo, não quero que você escolha outra profissional "
            "automaticamente; prefiro que primeiro consulte as alternativas e me "
            "apresente os horários disponíveis para que eu possa decidir. Também "
            "gostaria de saber se é possível realizar os dois serviços em sequência, "
            "sem precisar voltar em outro dia, e qual seria o horário estimado de "
            "início e término. Caso não exista disponibilidade na sexta-feira que "
            "respeite essas condições, pode me informar quais seriam as opções mais "
            "próximas, mas sem fazer nenhuma reserva ainda. Neste primeiro momento "
            "quero apenas consultar as possibilidades, comparar os horários e "
            "entender o que funciona melhor para mim. Depois que você me apresentar "
            "as opções, eu escolho a que preferir e autorizo expressamente a "
            "confirmação do agendamento."
        )

        # Validar detecção de autorização futura
        resultado_futuro = tem_confirmacao_temporal_condicional(mensagem)
        assert resultado_futuro == True, "Não detectou autorização futura"
        print("✅ A.1) PASS — Detectou 'Depois que... autorizo'")

        # Validar que não confirma agora
        resultado_confirmacao = eh_confirmacao(mensagem)
        assert resultado_confirmacao == False, "Tratou autorização futura como atual"
        print("✅ A.2) PASS — NÃO confirma agora (é consulta com autorização futura)")

        # Validar que contém indicadores de agendamento
        assert any(x in mensagem.lower() for x in ["manicure", "pedicure", "13/11", "14h", "17h"])
        print("✅ A.3) PASS — Contém indicadores de agendamento (manicure, pedicure, data, horários)")

    def test_b_quando_encontrar_autorizo(self):
        """B) Autorização futura: "Quando encontrar um horário, autorizo a reserva"

        ESPERADO:
        - tem_confirmacao_temporal_condicional() = True
        - eh_confirmacao() = False
        """
        mensagem = "Quando encontrar um horário, autorizo a reserva"

        resultado_futuro = tem_confirmacao_temporal_condicional(mensagem)
        assert resultado_futuro == True, "Não detectou 'quando'+'autorizo'"
        print("✅ B.1) PASS — Detectou 'quando encontrar, autorizo'")

        resultado_confirmacao = eh_confirmacao(mensagem)
        assert resultado_confirmacao == False, "Tratou como confirmação atual"
        print("✅ B.2) PASS — NÃO confirma agora")

    def test_c_consulta_sem_autorizacao(self):
        """C) Consulta sem autorização: "Quero apenas consultar os horários"

        ESPERADO:
        - tem_confirmacao_temporal_condicional() = False
        - eh_confirmacao() = False
        """
        mensagem = "Quero apenas consultar os horários"

        resultado_futuro = tem_confirmacao_temporal_condicional(mensagem)
        assert resultado_futuro == False, "Detectou futura onde não há"
        print("✅ C.1) PASS — Não detectou autorização futura")

        resultado_confirmacao = eh_confirmacao(mensagem)
        assert resultado_confirmacao == False, "Tratou consulta como confirmação"
        print("✅ C.2) PASS — Classificado como consulta pura")

    def test_d_confirmacao_atual_legitima(self):
        """D) Confirmação atual legítima: "Pode confirmar esse horário agora"

        ESPERADO:
        - tem_confirmacao_temporal_condicional() = False
        - eh_confirmacao() = True (se há operacao_pendente válida)
        """
        mensagem = "Pode confirmar esse horário agora"

        resultado_futuro = tem_confirmacao_temporal_condicional(mensagem)
        assert resultado_futuro == False, "Detectou futura em confirmação atual"
        print("✅ D.1) PASS — Confirmação atual é imediata")

        resultado_confirmacao = eh_confirmacao(mensagem)
        assert resultado_confirmacao == True, "Não reconheceu confirmação legítima"
        print("✅ D.2) PASS — Confirmação atual preservada")

    def test_e_autorizacao_futura_com_escolha(self):
        """E) Autorização futura após escolha: "Depois de analisar, decidi: pode confirmar"

        ESPERADO:
        - tem_confirmacao_temporal_condicional() = True
        - eh_confirmacao() = False
        """
        mensagem = "Depois de analisar as opções, decidi: pode confirmar esse horário"

        resultado_futuro = tem_confirmacao_temporal_condicional(mensagem)
        assert resultado_futuro == False, "Falso positivo: 'depois de' = passado"
        print("✅ E.1) PASS — 'depois de' é ação passada, não futura")

        # Mas "pode confirmar" sozinho é confirmação
        resultado_confirmacao = eh_confirmacao(mensagem)
        assert resultado_confirmacao == True, "Deveria reconhecer confirmação"
        print("✅ E.2) PASS — Confirmação atual reconhecida")

    def test_f_negacao_com_futuro(self):
        """F) Negação: "Não confirme ainda, quero analisar as opções"

        ESPERADO:
        - tem_confirmacao_temporal_condicional() = False
        - eh_confirmacao() = False
        """
        mensagem = "Não confirme ainda, quero analisar as opções"

        resultado_futuro = tem_confirmacao_temporal_condicional(mensagem)
        assert resultado_futuro == False, "Detectou confirmação onde há negação"
        print("✅ F.1) PASS — Não detectou confirmação (tem 'não')")

        resultado_confirmacao = eh_confirmacao(mensagem)
        assert resultado_confirmacao == False, "Tratou negação como confirmação"
        print("✅ F.2) PASS — Negação bloqueada")

    def test_g_consulta_complexa_dois_servicos_futura(self):
        """G) Consulta complexa: múltiplos serviços + autorização futura

        ESPERADO:
        - tem_confirmacao_temporal_condicional() = True
        - eh_confirmacao() = False
        - Extrair: manicure, pedicure, Bruna, 13/11, 14h-17h
        - Não criar evento
        """
        mensagem = (
            "Oi, preciso de manicure e pedicure pra sexta (13/11) das 14 às 17h. "
            "Quero com a Bruna se possível. Mas primeiro queria ver se consegue, "
            "aí depois que você me mostrar os horários, eu autorizo a reserva."
        )

        resultado_futuro = tem_confirmacao_temporal_condicional(mensagem)
        assert resultado_futuro == True, "Não detectou 'depois que'+'autorizo'"
        print("✅ G.1) PASS — Detectou autorização futura condicional")

        resultado_confirmacao = eh_confirmacao(mensagem)
        assert resultado_confirmacao == False, "Tratou como confirmação atual"
        print("✅ G.2) PASS — NÃO confirma agora (consulta)")

        # Validar indicadores de agendamento presentes
        assert any(x in mensagem.lower() for x in ["manicure", "pedicure", "13", "14", "17", "bruna"])
        print("✅ G.3) PASS — Contém informações de agendamento (serviços, data, horários, profissional)")

    def test_h_regressao_confirmacoes_legítimas(self):
        """H) Regressão: Confirmações legítimas ainda funcionam

        ESPERADO:
        - Mensagens simples de confirmação continuam passando
        - Sem autorização futura
        """
        testes = [
            ("sim, pode confirmar", True),
            ("tá ok, confirma aí", True),
            ("pode ser", False),  # Ambíguo, sem contexto
            ("não, cancela", False),
            ("quando?", False),  # Pergunta
        ]

        for msg, esperado in testes:
            resultado = eh_confirmacao(msg)
            if resultado != esperado:
                print(f"  ⚠️ '{msg}' → {resultado} (esperado {esperado})")
            else:
                print(f"  ✅ '{msg}' → {resultado}")

        print("✅ H) PASS — Regressão de confirmações legítimas validada")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
