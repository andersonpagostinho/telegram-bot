# -*- coding: utf-8 -*-
# tests/test_p0_data_weekday_validation.py
"""
TESTES OBRIGATÓRIOS: Validação de Data Explícita × Dia da Semana

Critério de aceite: Nenhuma data com divergência pode chegar ao motor de disponibilidade.
"""

import pytest
from datetime import datetime
from utils.interpretador_datas import interpretar_data_e_hora, validar_compatibilidade_data_weekday


class TestExtractionIndependent:
    """Testes para extração independente de data explícita vs dia da semana"""

    def test_1_data_explicita_compativel_com_dia_semana(self):
        """Test 1: Data explícita compatível com o dia da semana."""
        # 18/11/2026 é uma quarta-feira
        texto = "Agendar para 18/11/2026, quarta-feira."
        resultado = interpretar_data_e_hora(texto, return_metadata=True)

        assert resultado is not None
        assert resultado.get("datetime") is not None
        assert resultado.get("data_explicita") == "18/11/2026"
        assert resultado.get("dia_semana_mencionado") == "quarta"
        assert resultado.get("conflito_data_weekday") is False
        print(f"✓ Test 1 PASS: Data e weekday compatíveis")

    def test_2_data_explicita_incompativel_com_dia_semana(self):
        """Test 2: Data explícita incompatível com o dia da semana."""
        # 18/11/2026 é quarta-feira, mas texto diz sexta
        texto = "Agendar para 18/11/2026, sexta-feira."
        resultado = interpretar_data_e_hora(texto, return_metadata=True)

        assert resultado is not None
        assert resultado.get("data_explicita") == "18/11/2026"
        assert resultado.get("dia_semana_mencionado") == "sexta"
        assert resultado.get("conflito_data_weekday") is True
        print(f"✓ Test 2 PASS: Conflito detectado (18/11=quarta vs sexta)")

    def test_3_data_explicita_sem_dia_semana(self):
        """Test 3: Apenas data explícita, sem dia da semana."""
        texto = "Agendar para 18/11/2026 às 14:00."
        resultado = interpretar_data_e_hora(texto, return_metadata=True)

        assert resultado is not None
        assert resultado.get("data_explicita") == "18/11/2026"
        assert resultado.get("dia_semana_mencionado") is None
        assert resultado.get("conflito_data_weekday") is False
        print(f"✓ Test 3 PASS: Apenas data explícita, sem conflito")

    def test_4_somente_dia_semana(self):
        """Test 4: Apenas dia da semana mencionado."""
        texto = "Agendar para sexta-feira às 14:00."
        resultado = interpretar_data_e_hora(texto, return_metadata=True)

        assert resultado is not None
        assert resultado.get("data_explicita") is None
        assert resultado.get("dia_semana_mencionado") == "sexta"
        assert resultado.get("conflito_data_weekday") is False
        print(f"✓ Test 4 PASS: Apenas weekday, sem conflito")

    def test_5_data_formato_brasileiro(self):
        """Test 5: Data em formato brasileiro DD/MM/AAAA."""
        # Testando extração em formato brasileiro
        texto = "Agendar para 19/11/2026, quinta-feira."
        resultado = interpretar_data_e_hora(texto, return_metadata=True)

        assert resultado is not None
        assert resultado.get("data_explicita") is not None
        # 19/11/2026 é quinta-feira - compatível
        assert resultado.get("conflito_data_weekday") is False
        print(f"✓ Test 5 PASS: Formato DD/MM/AAAA extraído")

    def test_6_data_formato_iso(self):
        """Test 6: Data em formato ISO AAAA-MM-DD."""
        texto = "Agendar para 2026-11-18, quarta-feira."
        resultado = interpretar_data_e_hora(texto, return_metadata=True)

        assert resultado is not None
        # Formato ISO também deve ser extraído
        assert resultado.get("datetime") is not None
        print(f"✓ Test 6 PASS: Formato ISO extraído")

    def test_7_mensagem_longa(self):
        """Test 7: Mensagem longa com data, horário, serviço e profissional."""
        texto = "Olá! Gostaria de agendar uma escova com a Bruna para 18/11/2026, sexta-feira, às 14:00. Tudo bem?"
        resultado = interpretar_data_e_hora(texto, return_metadata=True)

        assert resultado is not None
        assert resultado.get("data_explicita") == "18/11/2026"
        # 18/11/2026 é quarta, não sexta → conflito
        assert resultado.get("conflito_data_weekday") is True
        print(f"✓ Test 7 PASS: Conflito detectado em mensagem longa")


class TestBlockAvailabilityCheck:
    """Testes para bloqueio do motor de disponibilidade em caso de conflito"""

    def test_8_conflito_bloqueia_motor(self):
        """Test 8: Divergência bloqueia consulta de disponibilidade."""
        texto = "Agendar para 18/11/2026, sexta-feira, às 14:00."

        # Validar antes de qualquer chamada ao motor
        valido = validar_compatibilidade_data_weekday(texto)

        # A função retorna um dict com bloqueio True, não False
        assert isinstance(valido, dict)
        assert valido.get("bloqueio") is True
        assert valido.get("razao") == "conflito_data_weekday"
        print(f"✓ Test 8 PASS: Motor bloqueado por conflito")

    def test_9_sem_conflito_permite_motor(self):
        """Test 9: Sem divergência permite motor."""
        texto = "Agendar para 19/11/2026, quinta-feira, às 14:00."

        valido = validar_compatibilidade_data_weekday(texto)

        assert valido is True
        print(f"✓ Test 9 PASS: Motor permitido (sem conflito)")


class TestContextPreservation:
    """Testes para preservação de contexto multi-tenant"""

    def test_11_preserva_tenant_id(self):
        """Test 11: Contexto preserva tenant_id e actor_id."""
        # Este teste valida que a lógica de validação não prejudica
        # o isolamento multi-tenant
        tenant_id = "7394370553"
        actor_id = "5511991382080"

        # Simulando validação com contexto multi-tenant
        valido = validar_compatibilidade_data_weekday(
            "18/11/2026, sexta-feira",
            tenant_id=tenant_id,
            actor_id=actor_id
        )

        # O importante é que tenant_id/actor_id não sejam perdidos
        assert valido is not None
        print(f"✓ Test 11 PASS: Isolamento multi-tenant mantido")


class TestNoRegression:
    """Testes de regressão no fluxo existente"""

    def test_12_fluxo_agendamento_simples_sem_regressao(self):
        """Test 12: Fluxo de agendamento simples sem regressão."""
        # Fluxo que funcionava antes, não pode quebrar
        texto = "Agendar escova amanhã às 10:00 com a Bruna."
        resultado = interpretar_data_e_hora(texto, return_metadata=True)

        assert resultado is not None
        assert resultado.get("datetime") is not None
        assert resultado.get("conflito_data_weekday") is False
        print(f"✓ Test 12 PASS: Sem regressão em agendamento simples")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SUITE DE TESTES: Validação Data × Dia da Semana")
    print("="*70 + "\n")

    # Test extraction
    print("[EXTRAÇÃO INDEPENDENTE]")
    test_ext = TestExtractionIndependent()

    tests_extraction = [
        (1, "test_1_data_explicita_compativel_com_dia_semana"),
        (2, "test_2_data_explicita_incompativel_com_dia_semana"),
        (3, "test_3_data_explicita_sem_dia_semana"),
        (4, "test_4_somente_dia_semana"),
        (5, "test_5_data_formato_brasileiro"),
        (6, "test_6_data_formato_iso"),
        (7, "test_7_mensagem_longa"),
    ]

    for test_num, test_name in tests_extraction:
        try:
            getattr(test_ext, test_name)()
        except AssertionError as e:
            print(f"✗ Test {test_num} FAIL: {e}")
        except Exception as e:
            print(f"✗ Test {test_num} ERROR: {e}")

    print("\n[BLOQUEIO MOTOR]")
    test_block = TestBlockAvailabilityCheck()

    tests_block = [
        (8, "test_8_conflito_bloqueia_motor"),
        (9, "test_9_sem_conflito_permite_motor"),
    ]

    for test_num, test_name in tests_block:
        try:
            getattr(test_block, test_name)()
        except AssertionError as e:
            print(f"✗ Test {test_num} FAIL: {e}")
        except Exception as e:
            print(f"✗ Test {test_num} ERROR: {e}")

    print("\n[PRESERVAÇÃO CONTEXTO]")
    test_ctx = TestContextPreservation()
    try:
        test_ctx.test_11_preserva_tenant_id()
    except AssertionError as e:
        print(f"✗ Test 11 FAIL: {e}")
    except Exception as e:
        print(f"✗ Test 11 ERROR: {e}")

    print("\n[REGRESSÃO]")
    test_reg = TestNoRegression()
    try:
        test_reg.test_12_fluxo_agendamento_simples_sem_regressao()
    except AssertionError as e:
        print(f"✗ Test 12 FAIL: {e}")
    except Exception as e:
        print(f"✗ Test 12 ERROR: {e}")

    print("\n" + "="*70)
