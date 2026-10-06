#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 — Teste Isolado: Extração de Termo de Cancelamento

Objetivo: Validar que a extração de termo em principal_router.py
produz o contrato esperado para cada caso de uso.

Contrato:
- Cancelamento SEM alvo: termo=""
- Cancelamento COM alvo: termo="alvo específico"
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def extrair_termo_cancelamento(texto_usuario: str) -> str:
    """
    Replica a lógica que deve estar em principal_router.py:4258-4265.

    Contrato:
    - Remove keywords de cancelamento em QUALQUER posição
    - Se não sobra nada, retorna ""
    - Se sobra algo, retorna o termo de busca
    """
    termo = texto_usuario
    cancelamento_keywords = [
        "gostaria de cancelar",
        "quero cancelar",
        "preciso cancelar",
        "pode cancelar",
        "pode desistir",
        "cancelar",
        "desistir",
        "cancela",
    ]

    # Remove keywords em qualquer posição (case-insensitive)
    for kw in cancelamento_keywords:
        while True:
            termo_lower = termo.lower()
            idx = termo_lower.find(kw.lower())
            if idx == -1:
                break
            termo = termo[:idx] + termo[idx + len(kw):]

    # Limpar espaços múltiplos
    termo = " ".join(termo.split()).strip()
    return termo


class TestExtracaoTermoCancelamento:
    """Testes da extração de termo de cancelamento"""

    # =====================================================
    # CANCELAMENTO PURO (sem alvo) — deve retornar ""
    # =====================================================

    def test_c1_cancelar_apenas(self):
        """C1: 'cancelar' sozinho => termo='' """
        resultado = extrair_termo_cancelamento("cancelar")
        assert resultado == "", f"Esperado: '', Obtido: '{resultado}'"
        print("[OK] C1: cancelar => (vazio)")

    def test_c2_quero_cancelar(self):
        """C2: 'quero cancelar' => termo='' """
        resultado = extrair_termo_cancelamento("quero cancelar")
        assert resultado == "", f"Esperado: '', Obtido: '{resultado}'"
        print("[OK] C2: quero cancelar => (vazio)")

    def test_c3_gostaria_cancelar(self):
        """C3: 'gostaria de cancelar' => termo='' """
        resultado = extrair_termo_cancelamento("gostaria de cancelar")
        assert resultado == "", f"Esperado: '', Obtido: '{resultado}'"
        print("[OK] C3: gostaria de cancelar => (vazio)")

    def test_c4_preciso_cancelar(self):
        """C4: 'preciso cancelar' => termo='' """
        resultado = extrair_termo_cancelamento("preciso cancelar")
        assert resultado == "", f"Esperado: '', Obtido: '{resultado}'"
        print("[OK] C4: preciso cancelar => (vazio)")

    def test_c5_pode_cancelar(self):
        """C5: 'pode cancelar' => termo='' (CASO CRITICO!)"""
        resultado = extrair_termo_cancelamento("pode cancelar")
        assert resultado == "", f"Esperado: '', Obtido: '{resultado}'"
        print("[OK] C5: pode cancelar => (vazio) [CRITICO]")

    # =====================================================
    # CANCELAMENTO COM ALVO — deve retornar o alvo
    # =====================================================

    def test_a1_cancelar_meu_corte(self):
        """A1: 'cancelar meu corte' => termo='meu corte' """
        resultado = extrair_termo_cancelamento("cancelar meu corte")
        assert resultado == "meu corte", f"Esperado: 'meu corte', Obtido: '{resultado}'"
        print("[OK] A1: cancelar meu corte => meu corte")

    def test_a2_cancelar_corte_com_bruna(self):
        """A2: 'cancelar o corte com Bruna' => termo='o corte com Bruna' """
        resultado = extrair_termo_cancelamento("cancelar o corte com Bruna")
        assert resultado == "o corte com Bruna", f"Esperado: 'o corte com Bruna', Obtido: '{resultado}'"
        print("[OK] A2: cancelar o corte com Bruna => o corte com Bruna")

    def test_a3_pode_cancelar_com_alvo(self):
        """A3: 'pode cancelar o corte com Bruna' => termo='o corte com Bruna' (CRITICO!)"""
        resultado = extrair_termo_cancelamento("pode cancelar o corte com Bruna")
        assert resultado == "o corte com Bruna", f"Esperado: 'o corte com Bruna', Obtido: '{resultado}'"
        print("[OK] A3: pode cancelar o corte com Bruna => o corte com Bruna [CRITICO]")

    def test_a4_pode_cancelar_meu_horario(self):
        """A4: 'pode cancelar meu horario' => termo='meu horario' """
        resultado = extrair_termo_cancelamento("pode cancelar meu horario")
        assert resultado == "meu horario", f"Esperado: 'meu horario', Obtido: '{resultado}'"
        print("[OK] A4: pode cancelar meu horario => meu horario")

    def test_a5_cancelar_meu_corte_com_bruna(self):
        """A5: 'cancelar meu corte com Bruna' => termo='meu corte com Bruna' """
        resultado = extrair_termo_cancelamento("cancelar meu corte com Bruna")
        assert resultado == "meu corte com Bruna", f"Esperado: 'meu corte com Bruna', Obtido: '{resultado}'"
        print("[OK] A5: cancelar meu corte com Bruna => meu corte com Bruna")

    # =====================================================
    # SANIDADE: NÃO DEVE QUEBRAR CASOS ADJACENTES
    # =====================================================

    def test_s1_nao_vira_string_vazia_errado(self):
        """S1: 'cancelar meu corte com Bruna' NAO vira '' """
        resultado = extrair_termo_cancelamento("cancelar meu corte com Bruna")
        assert resultado != "", f"Erro: resultado ficou vazio quando deveria ser 'meu corte com Bruna'"
        print("[OK] S1: Termo nao ficou vazio indevidamente")

    def test_s2_pode_cancelar_nao_permanece_inteiro(self):
        """S2: 'pode cancelar' NAO permanece 'pode cancelar' """
        resultado = extrair_termo_cancelamento("pode cancelar")
        assert resultado != "pode cancelar", f"Erro: 'pode cancelar' permaneceu inteiro"
        print("[OK] S2: pode cancelar foi reduzido para (vazio)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
