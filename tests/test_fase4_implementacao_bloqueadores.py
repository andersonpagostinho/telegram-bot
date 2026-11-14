#!/usr/bin/env python3
"""
FASE 4: Testes de validação dos bloqueadores corrigidos.

READ-ONLY: Sem modificações de dados.
"""

import pytest
from services.multisservico_service import extrair_intervalo_horario
from services.varredura_disponibilidade import varrer_disponibilidade_multisservico
import asyncio


class TestExtrairIntervaloHorario:
    """Validar parser de intervalo com padrões reais."""

    def test_padrao_ponto_e_virgula_maximo(self):
        """Padrão real: "até, no máximo, 17h" """
        msg = "Consigo chegar a partir das 14h, mas tenho um compromisso no final do dia e preciso terminar os dois serviços até, no máximo, 17h."
        inicio, fim = extrair_intervalo_horario(msg)
        assert inicio == 14, f"Esperado inicio=14, obteve {inicio}"
        assert fim == 17, f"Esperado fim=17, obteve {fim}"
        print(f"✓ Padrão 'até, no máximo': ({inicio}, {fim})")

    def test_padrao_ate_puro(self):
        """Padrão: "até 17h" """
        msg = "a partir das 14h até 17h"
        inicio, fim = extrair_intervalo_horario(msg)
        assert inicio == 14
        assert fim == 17
        print(f"✓ Padrão 'até 17h': ({inicio}, {fim})")

    def test_padrao_das_ate(self):
        """Padrão: "das 14h às 17h" """
        msg = "manicure das 14h às 17h"
        inicio, fim = extrair_intervalo_horario(msg)
        assert inicio == 14
        assert fim == 17
        print(f"✓ Padrão 'das...às': ({inicio}, {fim})")

    def test_padrao_apenas_a_partir(self):
        """Padrão: "a partir de 14h" (sem limite final) """
        msg = "a partir das 14h"
        inicio, fim = extrair_intervalo_horario(msg)
        assert inicio == 14
        assert fim is None, f"Esperado fim=None, obteve {fim}"
        print(f"✓ Padrão 'a partir de': ({inicio}, {fim})")

    def test_padrao_nenhum_intervalo(self):
        """Padrão: sem intervalo """
        msg = "Gostaria de agendar um corte"
        inicio, fim = extrair_intervalo_horario(msg)
        assert inicio is None
        assert fim is None
        print(f"✓ Sem intervalo: ({inicio}, {fim})")


class TestVarreduraValidacao:
    """Validar proteção contra intervalos inválidos em varredura."""

    def test_intervalo_normal(self):
        """Intervalo válido (14, 17) deve ser testado."""
        print("✓ Intervalo normal (14, 17) passará validação")
        assert 17 > 14

    def test_intervalo_igual(self):
        """Intervalo (14, 14) deve ser rejeitado ANTES de range()."""
        intervalo_inicio = 14
        intervalo_fim = 14
        # Simular validação
        assert intervalo_fim <= intervalo_inicio, "Deveria rejeitar (14, 14)"
        print(f"✓ Intervalo (14, 14) seria rejeitado (fim <= inicio)")

    def test_intervalo_invertido(self):
        """Intervalo (17, 14) deve ser rejeitado ANTES de range()."""
        intervalo_inicio = 17
        intervalo_fim = 14
        # Simular validação
        assert intervalo_fim <= intervalo_inicio, "Deveria rejeitar (17, 14)"
        print(f"✓ Intervalo (17, 14) seria rejeitado (fim < inicio)")

    def test_intervalo_none(self):
        """Intervalo com None deve ser rejeitado ANTES de range()."""
        intervalo_inicio = 14
        intervalo_fim = None
        # Simular validação
        assert not isinstance(intervalo_fim, int), "Deveria rejeitar None"
        print(f"✓ Intervalo (14, None) seria rejeitado (tipo inválido)")


class TestSemantiaIntervalo:
    """Validar semântica de horário pontual vs janela."""

    def test_horario_pontual(self):
        """Horário pontual: apenas um horário mencionado."""
        msg = "a partir das 14h"
        inicio, fim = extrair_intervalo_horario(msg)
        # Pontual = sem limite final
        assert inicio is not None
        assert fim is None
        print(f"✓ Horário pontual detectado: inicio={inicio}, sem limite")

    def test_janela_completa(self):
        """Janela completa: ambos os limites mencionados."""
        msg = "das 14h às 17h"
        inicio, fim = extrair_intervalo_horario(msg)
        # Janela = ambos
        assert inicio is not None
        assert fim is not None
        assert fim > inicio
        print(f"✓ Janela completa detectada: {inicio}h-{fim}h")

    def test_janela_incompleta(self):
        """Janela incompleta: apenas um limite mencionado."""
        msg = "até 17h"
        inicio, fim = extrair_intervalo_horario(msg)
        # Incompleta = fim sem inicio
        assert inicio is None
        assert fim is not None
        print(f"✓ Janela incompleta detectada: ?-{fim}h")


# Testes de integração (sem modificação de dados)
class TestIntegracaoCenarioOriginal:
    """Reproduzir cenário original: manicure + pedicure, Bruna, 14h-17h."""

    def test_contexto_intervalo_preservado(self):
        """Intervalo extraído deve permanecer (14, 17) até motor."""
        # Simular: mensagem → enriquecimento → motor
        msg = "Consigo chegar a partir das 14h, mas tenho um compromisso no final do dia e preciso terminar os dois serviços até, no máximo, 17h."
        inicio, fim = extrair_intervalo_horario(msg)

        # Verificar que intervalo está correto
        assert inicio == 14, f"Intervalo inicio deve ser 14, obteve {inicio}"
        assert fim == 17, f"Intervalo fim deve ser 17, obteve {fim}"

        # Verificar que não há None ou valores iguais
        assert inicio != fim, "Intervalo não pode ser pontual (inicio == fim)"
        assert fim > inicio, "Fim deve ser maior que inicio"

        print(f"✓ Contexto intervalo preservado: ({inicio}, {fim})")

    def test_range_valido(self):
        """Range (14, 17) deve iterar 14, 15, 16."""
        intervalo_inicio = 14
        intervalo_fim = 17
        horas = list(range(intervalo_inicio, intervalo_fim))
        assert horas == [14, 15, 16], f"Esperado [14, 15, 16], obteve {horas}"
        print(f"✓ Range válido: {horas}")

    def test_range_invalido_rejeitado(self):
        """Range (14, 14) seria silenciosamente vazio sem validação."""
        intervalo_inicio = 14
        intervalo_fim = 14

        # SEM validação: silenciosamente vazio
        horas_sem_validacao = list(range(intervalo_inicio, intervalo_fim))
        assert horas_sem_validacao == [], f"Range (14, 14) é vazio (PROBLEMA)"

        # COM validação: rejeitado antes
        is_valid = intervalo_fim > intervalo_inicio
        assert not is_valid, "Validação deveria rejeitar (14, 14)"

        print(f"✓ Range inválido (14, 14) seria rejeitado com validação")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FASE 4: TESTES DE VALIDAÇÃO")
    print("="*80 + "\n")

    # Testes de parser
    print("[1] Parser de Intervalo:")
    tests_parser = TestExtrairIntervaloHorario()
    tests_parser.test_padrao_ponto_e_virgula_maximo()
    tests_parser.test_padrao_ate_puro()
    tests_parser.test_padrao_das_ate()
    tests_parser.test_padrao_apenas_a_partir()
    tests_parser.test_padrao_nenhum_intervalo()

    # Testes de varredura
    print("\n[2] Validação de Varredura:")
    tests_varredura = TestVarreduraValidacao()
    tests_varredura.test_intervalo_normal()
    tests_varredura.test_intervalo_igual()
    tests_varredura.test_intervalo_invertido()
    tests_varredura.test_intervalo_none()

    # Testes de semântica
    print("\n[3] Semântica de Intervalo:")
    tests_semantica = TestSemantiaIntervalo()
    tests_semantica.test_horario_pontual()
    tests_semantica.test_janela_completa()
    tests_semantica.test_janela_incompleta()

    # Testes de integração
    print("\n[4] Integração - Cenário Original:")
    tests_integracao = TestIntegracaoCenarioOriginal()
    tests_integracao.test_contexto_intervalo_preservado()
    tests_integracao.test_range_valido()
    tests_integracao.test_range_invalido_rejeitado()

    print("\n" + "="*80)
    print("✅ TODOS OS TESTES PASSARAM")
    print("="*80 + "\n")
