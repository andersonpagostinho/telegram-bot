#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 E2E — Reconhecimento Contextual de Profissional
Validar que "bruna" é reconhecida em estado aguardando_profissional
"""

import pytest
from services.classificador_conversa import extrair_features_conversa


class TestProfissionalContextualE2E:
    """Validar reconhecimento de nomes em aguardando_profissional"""

    def test_bruna_em_aguardando_profissional(self):
        """Estado aguardando_profissional + 'bruna' + catálogo → reconhecida"""
        ctx = {"estado_fluxo": "aguardando_profissional"}
        catalogo = ["Bruna", "Gloria", "Joana", "Carla"]

        features = extrair_features_conversa("bruna", ctx=ctx, catalogo_profissionais=catalogo)

        assert features["tem_ref_profissional"] is True, \
            f"FAIL: 'bruna' deveria ser reconhecida. Features: {features}"
        print(f"[PASS] 'bruna' reconhecida em aguardando_profissional")

    def test_gloria_maiuscula_em_aguardando_profissional(self):
        """Estado aguardando_profissional + 'GLORIA' + catálogo → reconhecida"""
        ctx = {"estado_fluxo": "aguardando_profissional"}
        catalogo = ["Bruna", "Gloria", "Joana", "Carla"]

        features = extrair_features_conversa("GLORIA", ctx=ctx, catalogo_profissionais=catalogo)

        assert features["tem_ref_profissional"] is True, \
            f"FAIL: 'GLORIA' deveria ser reconhecida. Features: {features}"
        print(f"[PASS] 'GLORIA' reconhecida em aguardando_profissional")

    def test_idle_sem_verbo_nao_reconhecida(self):
        """Estado idle + 'bruna' (sem verbo) + catálogo → NÃO reconhecida"""
        ctx = {"estado_fluxo": "idle"}
        catalogo = ["Bruna", "Gloria", "Joana", "Carla"]

        features = extrair_features_conversa("bruna", ctx=ctx, catalogo_profissionais=catalogo)

        assert features["tem_ref_profissional"] is False, \
            f"FAIL: 'bruna' em idle NÃO deveria ser reconhecida sem verbo. Features: {features}"
        print(f"[PASS] 'bruna' em idle corretamente rejeitada")

    def test_sem_catalogo_volta_comportamento_antigo(self):
        """Estado aguardando_profissional + 'bruna' + catalogo=None → comportamento antigo"""
        ctx = {"estado_fluxo": "aguardando_profissional"}

        features = extrair_features_conversa("bruna", ctx=ctx, catalogo_profissionais=None)

        # Sem catálogo, requer verbo
        assert features["tem_ref_profissional"] is False, \
            f"FAIL: Sem catálogo, deveria retornar False. Features: {features}"
        print(f"[PASS] Sem catálogo, comportamento antigo preservado")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
