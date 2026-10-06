#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 — Testes Unitários: classificar_confirmacao_cancelamento()

Objetivo: Validar classificação de confirmação/negação/ambiguidade
em contexto de confirmação de cancelamento de evento.

Status: 18 testes obrigatórios conforme especificação
ESPECIFICACAO_CLASSIFICAR_CONFIRMACAO_CANCELAMENTO_2026_10_06.md
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.classificador_conversa import classificar_confirmacao_cancelamento


class TestConfirmacaoCancelamento:
    """Testes da função classificar_confirmacao_cancelamento()"""

    # =====================================================
    # CONFIRMAÇÕES (4 testes)
    # =====================================================

    def test_t1_confirmacao_sim(self):
        """T1: 'sim' deve retornar confirmacao"""
        resultado = classificar_confirmacao_cancelamento("sim")
        assert resultado == "confirmacao", f"Esperado: confirmacao, Obtido: {resultado}"
        print("[OK] T1: 'sim' → confirmacao")

    def test_t2_confirmacao_abreviacoes(self):
        """T2: Abreviações (s, ok, claro) devem retornar confirmacao"""
        casos = ["s", "ok", "claro"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "confirmacao", f"'{caso}' esperado confirmacao, obtido {resultado}"
        print("[OK] T2: Abreviações (s, ok, claro) → confirmacao")

    def test_t3_confirmacao_com_contexto(self):
        """T3: 'pode cancelar', 'sim, pode cancelar' devem retornar confirmacao"""
        casos = ["pode cancelar", "sim, pode cancelar", "pode desmarcar"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "confirmacao", f"'{caso}' esperado confirmacao, obtido {resultado}"
        print("[OK] T3: Confirmações com contexto → confirmacao")

    def test_t4_confirmacao_deitica(self):
        """T4: 'isso', 'isso mesmo' devem retornar confirmacao"""
        casos = ["isso", "isso mesmo"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "confirmacao", f"'{caso}' esperado confirmacao, obtido {resultado}"
        print("[OK] T4: Confirmação dêitica → confirmacao")

    # =====================================================
    # NEGAÇÕES (5 testes)
    # =====================================================

    def test_t5_negacao_simples(self):
        """T5: 'não', 'nao' devem retornar negacao"""
        casos = ["não", "nao"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "negacao", f"'{caso}' esperado negacao, obtido {resultado}"
        print("[OK] T5: Negação simples → negacao")

    def test_t6_negacao_com_razao(self):
        """T6: 'não quero', 'não quero cancelar', 'não precisa' devem retornar negacao"""
        casos = ["não quero", "não quero cancelar", "não precisa"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "negacao", f"'{caso}' esperado negacao, obtido {resultado}"
        print("[OK] T6: Negação com razão → negacao")

    def test_t7_negacao_implicita(self):
        """T7: 'deixa como está', 'esquece' devem retornar negacao"""
        casos = ["deixa como está", "esquece"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "negacao", f"'{caso}' esperado negacao, obtido {resultado}"
        print("[OK] T7: Negação implícita → negacao")

    def test_t8_negacao_contexto(self):
        """T8: 'não cancele', 'melhor não' devem retornar negacao"""
        casos = ["não cancele", "melhor não"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "negacao", f"'{caso}' esperado negacao, obtido {resultado}"
        print("[OK] T8: Negação com contexto → negacao")

    def test_t9_nao_confundir_impossibilidade_com_negacao(self):
        """T9: CRÍTICO — 'não consigo ir', 'não vou conseguir' devem retornar AMBÍGUO"""
        casos = ["não consigo ir", "não vou conseguir nesse horário"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "ambiguo", f"'{caso}' esperado ambiguo (não negacao!), obtido {resultado}"
        print("[OK] T9: Impossibilidade ≠ negação → ambiguo")

    # =====================================================
    # AMBÍGUAS (5 testes)
    # =====================================================

    def test_t10_ambiguo_incerteza(self):
        """T10: 'talvez', 'não sei' devem retornar ambiguo"""
        casos = ["talvez", "não sei"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "ambiguo", f"'{caso}' esperado ambiguo, obtido {resultado}"
        print("[OK] T10: Incerteza → ambiguo")

    def test_t11_ambiguo_adiamento(self):
        """T11: CRÍTICO — 'deixa para depois', 'depois eu vejo' devem retornar AMBÍGUO (não negacao!)"""
        casos = ["deixa para depois", "depois eu vejo", "vou pensar"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "ambiguo", f"'{caso}' esperado ambiguo (não negacao!), obtido {resultado}"
        print("[OK] T11: Adiamento → ambiguo")

    def test_t12_ambiguo_baixa_confianca(self):
        """T12: 'acho que sim', 'acho que não', 'pode ser' devem retornar ambiguo"""
        casos = ["acho que sim", "acho que não", "pode ser"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "ambiguo", f"'{caso}' esperado ambiguo, obtido {resultado}"
        print("[OK] T12: Baixa confiança → ambiguo")

    def test_t13_ambiguo_pode_sozinho(self):
        """T13: CRÍTICO — 'pode' SOZINHO deve retornar AMBÍGUO (não confirmacao!)"""
        resultado = classificar_confirmacao_cancelamento("pode")
        assert resultado == "ambiguo", f"'pode' esperado ambiguo (não confirmacao!), obtido {resultado}"
        print("[OK] T13: 'pode' sozinho → ambiguo")

    def test_t14_ambiguo_complexo(self):
        """T14: CRÍTICO — Frase complexa deve retornar AMBÍGUO"""
        caso = "que pena, então deixa para outra hora, obrigada"
        resultado = classificar_confirmacao_cancelamento(caso)
        assert resultado == "ambiguo", f"Frase complexa esperado ambiguo, obtido {resultado}"
        print("[OK] T14: Frase complexa → ambiguo")

    # =====================================================
    # PERIGOSAS (3 testes)
    # =====================================================

    def test_t15_perigo_remarcacao(self):
        """T15: Pedidos de remarcação devem retornar ambiguo"""
        casos = ["pode cancelar e marcar outro", "cancela e coloca para amanhã"]
        for caso in casos:
            resultado = classificar_confirmacao_cancelamento(caso)
            assert resultado == "ambiguo", f"'{caso}' esperado ambiguo, obtido {resultado}"
        print("[OK] T15: Remarcação → ambiguo")

    def test_t16_perigo_impossibilidade_nao_vou(self):
        """T16: 'não vou' é ambíguo (dupla interpretação)"""
        resultado = classificar_confirmacao_cancelamento("não vou")
        assert resultado == "ambiguo", f"'não vou' esperado ambiguo, obtido {resultado}"
        print("[OK] T16: 'não vou' → ambiguo")

    def test_t17_perigo_double_negation(self):
        """T17: 'não conseguir' é ambiguo (mudança de circunstância)"""
        resultado = classificar_confirmacao_cancelamento("não consigo")
        assert resultado == "ambiguo", f"'não consigo' esperado ambiguo, obtido {resultado}"
        print("[OK] T17: 'não consigo' → ambiguo")

    # =====================================================
    # REGRESSÃO (1 teste)
    # =====================================================

    def test_t18_regressao_isolamento(self):
        """T18: Função é específica para cancelamento, não afeta agendamento"""
        # Apenas validar que função existe e retorna sempre um de 3 valores
        resultado = classificar_confirmacao_cancelamento("qualquer coisa")
        assert resultado in ["confirmacao", "negacao", "ambiguo"], \
            f"Resultado inválido: {resultado}"
        print("[OK] T18: Isolamento funcional")

    # =====================================================
    # CASOS CRÍTICOS OBRIGATÓRIOS (Inversão Semântica)
    # =====================================================

    def test_critico_cancela_e_confirmacao(self):
        """CRÍTICO: 'cancela' deve ser CONFIRMAÇÃO (não negação!)"""
        resultado = classificar_confirmacao_cancelamento("cancela")
        assert resultado == "confirmacao", \
            f"'cancela' DEVE ser confirmacao (inversão semântica!), obtido {resultado}"
        print("[OK] CRÍTICO: 'cancela' → confirmacao")

    def test_critico_pode_cancelar_e_confirmacao(self):
        """CRÍTICO: 'pode cancelar' deve ser CONFIRMAÇÃO (não negacao!)"""
        resultado = classificar_confirmacao_cancelamento("pode cancelar")
        assert resultado == "confirmacao", \
            f"'pode cancelar' DEVE ser confirmacao (inversão semântica!), obtido {resultado}"
        print("[OK] CRÍTICO: 'pode cancelar' → confirmacao")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
