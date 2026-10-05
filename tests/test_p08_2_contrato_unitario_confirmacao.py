#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0.8.2 — FASE 1: Contrato Unitário da Confirmação

Objetivo: Validar o template exato da mensagem de confirmação
sem depender de integração, Firestore, WhatsApp ou Telegram.

Contrato oficial:
"Pronto! Seu horário de {servico} com {profissional} está confirmado para {quando} às {hora}."

Fallback (quando data_hora inválida):
"Pronto! Seu agendamento está confirmado."
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.mensagens_agendamento import montar_mensagem_confirmacao_sucesso


class TestContratoUnitarioConfirmacao:
    """
    P0.8.2 — Testes unitários do contrato textual de confirmação.

    Cobertura:
    - Template principal (data/hora válidas)
    - Fallback (data/hora inválidas)
    - Proteção contra regressão de template
    """

    def test_u1_template_exato_hoje(self):
        """
        U1: Template principal com data de hoje

        Validação: Assert ==IGUALDADE EXATA==

        Regressão detectada se:
        - "Pronto!" for "Pronto,"
        - "Seu horário de" for "sua"
        - "está confirmado" for "ficou agendada"
        """
        print("\n" + "="*80)
        print("[P0.8.2-U1] Template Exato — Hoje")
        print("="*80)

        # Input controlado
        servico = "corte"
        profissional = "Bruna"
        data_hora = "2026-10-05T10:00:00"  # assumir que hoje é 2026-10-05

        print(f"\n[INPUT]")
        print(f"  servico: {servico}")
        print(f"  profissional: {profissional}")
        print(f"  data_hora: {data_hora}")

        # Chamar função
        msg = montar_mensagem_confirmacao_sucesso(servico, profissional, data_hora)

        print(f"\n[RESULTADO]")
        print(f"  {repr(msg)}")

        # Validação: IGUALDADE EXATA
        # Formato esperado: "Pronto! Seu horário de corte com Bruna está confirmado para hoje às 10h."
        expected_pattern = "Pronto! Seu horário de corte com Bruna está confirmado para hoje às 10h."

        print(f"\n[ESPERADO]")
        print(f"  {repr(expected_pattern)}")

        # Assert: Padrão oficial é respeitado
        assert "Pronto!" in msg, f"Deve começar com 'Pronto!' (com exclamação). Recebido: {repr(msg)}"
        assert "Seu horário de" in msg, f"Deve ter 'Seu horário de'. Recebido: {repr(msg)}"
        assert "corte" in msg.lower(), f"Deve conter 'corte'. Recebido: {repr(msg)}"
        assert "Bruna" in msg, f"Deve conter 'Bruna'. Recebido: {repr(msg)}"
        assert "está confirmado" in msg, f"Deve ter 'está confirmado' (não 'ficou agendada'). Recebido: {repr(msg)}"
        assert "hoje" in msg, f"Deve conter 'hoje'. Recebido: {repr(msg)}"
        assert "10h" in msg, f"Deve conter '10h'. Recebido: {repr(msg)}"
        assert msg == expected_pattern, f"CONTRATO EXATO VIOLADO.\nEsperado: {repr(expected_pattern)}\nRecebido: {repr(msg)}"

        print(f"\n[VALIDAÇÃO]")
        print(f"   Contrato exato respeitado")
        print(f"   Pontuação: 'Pronto!'")
        print(f"   Estrutura: 'Seu horário de {servico} com {profissional}'")
        print(f"   Afirmação: 'está confirmado para'")
        print(f"   Tempo: 'hoje'")
        print(f"   Horário: '10h'")
        print(f"\n[RESULTADO]")
        print(f"   PASSOU — Contrato oficial protegido")
        print("="*80)

    def test_u1_template_exato_amanha(self):
        """
        U1b: Template principal com data de amanhã

        Mesmo contrato, apenas tempo relativo diferente.
        """
        print("\n" + "="*80)
        print("[P0.8.2-U1b] Template Exato — Amanhã")
        print("="*80)

        # Simular amanhã (2026-10-06, assumindo hoje=2026-10-05)
        servico = "escova"
        profissional = "Maria"
        data_hora = "2026-10-06T14:30:00"

        print(f"\n[INPUT]")
        print(f"  servico: {servico}")
        print(f"  profissional: {profissional}")
        print(f"  data_hora: {data_hora}")

        msg = montar_mensagem_confirmacao_sucesso(servico, profissional, data_hora)

        print(f"\n[RESULTADO]")
        print(f"  {repr(msg)}")

        # Validações críticas
        assert "Pronto!" in msg, f"Deve começar com 'Pronto!'. Recebido: {repr(msg)}"
        assert "Seu horário de" in msg, f"Deve ter 'Seu horário de'. Recebido: {repr(msg)}"
        assert "escova" in msg.lower(), f"Deve conter 'escova'. Recebido: {repr(msg)}"
        assert "Maria" in msg, f"Deve conter 'Maria'. Recebido: {repr(msg)}"
        assert "está confirmado" in msg, f"Deve ter 'está confirmado'. Recebido: {repr(msg)}"
        assert "amanhã" in msg, f"Deve conter 'amanhã'. Recebido: {repr(msg)}"
        assert "14h30" in msg, f"Deve conter '14h30'. Recebido: {repr(msg)}"

        print(f"\n[RESULTADO]")
        print(f"   PASSOU — Tempo relativo funcionando")
        print("="*80)

    def test_u1_template_exato_data_futura(self):
        """
        U1c: Template principal com data futura (formato DD/MM)

        Para datas não-hoje e não-amanhã, usa formato "em DD/MM"
        """
        print("\n" + "="*80)
        print("[P0.8.2-U1c] Template Exato — Data Futura")
        print("="*80)

        servico = "manicure"
        profissional = "Ana"
        data_hora = "2026-10-15T09:15:00"  # 10 dias no futuro

        print(f"\n[INPUT]")
        print(f"  servico: {servico}")
        print(f"  profissional: {profissional}")
        print(f"  data_hora: {data_hora}")

        msg = montar_mensagem_confirmacao_sucesso(servico, profissional, data_hora)

        print(f"\n[RESULTADO]")
        print(f"  {repr(msg)}")

        # Validações
        assert "Pronto!" in msg, f"Deve começar com 'Pronto!'. Recebido: {repr(msg)}"
        assert "Seu horário de" in msg, f"Deve ter 'Seu horário de'. Recebido: {repr(msg)}"
        assert "manicure" in msg.lower(), f"Deve conter 'manicure'. Recebido: {repr(msg)}"
        assert "Ana" in msg, f"Deve conter 'Ana'. Recebido: {repr(msg)}"
        assert "está confirmado" in msg, f"Deve ter 'está confirmado'. Recebido: {repr(msg)}"
        assert "em 15/10" in msg, f"Deve conter 'em 15/10'. Recebido: {repr(msg)}"
        assert "9h15" in msg, f"Deve conter '9h15'. Recebido: {repr(msg)}"

        print(f"\n[RESULTADO]")
        print(f"   PASSOU — Formato data futura OK")
        print("="*80)

    def test_u2_fallback_data_invalida(self):
        """
        U2: Fallback quando data_hora é inválida

        Contrato de fallback:
        "Pronto! Seu agendamento está confirmado."

        Cenários:
        - data_hora="" (vazia)
        - data_hora="invalid" (string inválida)
        - data_hora=None (None será convertido para string)
        """
        print("\n" + "="*80)
        print("[P0.8.2-U2] Fallback — Data Inválida")
        print("="*80)

        # Cenário 1: data_hora vazia
        print(f"\n[CENÁRIO 1: data_hora vazia]")
        msg1 = montar_mensagem_confirmacao_sucesso("corte", "Bruna", "")
        print(f"  Resultado: {repr(msg1)}")
        assert msg1 == "Pronto! Seu agendamento está confirmado.", \
            f"Fallback violado com data vazia. Recebido: {repr(msg1)}"
        print(f"   OK")

        # Cenário 2: data_hora inválida
        print(f"\n[CENÁRIO 2: data_hora inválida]")
        msg2 = montar_mensagem_confirmacao_sucesso("escova", "Maria", "not-a-date")
        print(f"  Resultado: {repr(msg2)}")
        assert msg2 == "Pronto! Seu agendamento está confirmado.", \
            f"Fallback violado com data inválida. Recebido: {repr(msg2)}"
        print(f"   OK")

        # Cenário 3: data_hora malformada
        print(f"\n[CENÁRIO 3: data_hora malformada]")
        msg3 = montar_mensagem_confirmacao_sucesso("manicure", "Ana", "2026-13-45T25:99:99")
        print(f"  Resultado: {repr(msg3)}")
        assert msg3 == "Pronto! Seu agendamento está confirmado.", \
            f"Fallback violado com data malformada. Recebido: {repr(msg3)}"
        print(f"   OK")

        print(f"\n[RESULTADO]")
        print(f"   PASSOU — Fallback protegido em todas cenários")
        print("="*80)

    def test_regressao_pronto_com_virgula(self):
        """
        Regressão: Alguém muda "Pronto!" para "Pronto,"

        Esse teste FALHA se o template for alterado para o padrão antigo.
        """
        print("\n" + "="*80)
        print("[P0.8.2-REGRESSÃO] Detectar Mudança para 'Pronto,'")
        print("="*80)

        msg = montar_mensagem_confirmacao_sucesso("corte", "Bruna", "2026-10-05T10:00:00")

        print(f"\n[RESULTADO]")
        print(f"  {repr(msg)}")

        # DEVE falhar se alguém mudar para "Pronto, sua..."
        assert msg.startswith("Pronto!"), \
            f"REGRESSÃO: Template não começa com 'Pronto!'. Recebido: {repr(msg)}"
        assert not msg.startswith("Pronto,"), \
            f"REGRESSÃO: Template contém 'Pronto,' (com vírgula). Recebido: {repr(msg)}"

        print(f"\n[PROTEÇÃO]")
        print(f"   Regressão 'Pronto,' seria detectada")
        print("="*80)

    def test_regressao_ficou_agendada(self):
        """
        Regressão: Alguém muda "está confirmado" para "ficou agendada"

        Esse teste FALHA se o verbo for alterado.
        """
        print("\n" + "="*80)
        print("[P0.8.2-REGRESSÃO] Detectar Mudança para 'ficou agendada'")
        print("="*80)

        msg = montar_mensagem_confirmacao_sucesso("corte", "Bruna", "2026-10-05T10:00:00")

        print(f"\n[RESULTADO]")
        print(f"  {repr(msg)}")

        # DEVE falhar se alguém mudar o verbo
        assert "está confirmado" in msg, \
            f"REGRESSÃO: Falta 'está confirmado'. Recebido: {repr(msg)}"
        assert "ficou agendada" not in msg.lower(), \
            f"REGRESSÃO: Contém 'ficou agendada' (forma antiga). Recebido: {repr(msg)}"

        print(f"\n[PROTEÇÃO]")
        print(f"   Regressão 'ficou agendada' seria detectada")
        print("="*80)


if __name__ == "__main__":
    # Executar testes com pytest
    pytest.main([__file__, "-v", "-s"])
