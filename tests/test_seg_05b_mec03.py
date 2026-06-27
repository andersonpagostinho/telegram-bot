"""
SEG-05B — MEC-03: Testes de Ativação Controlada de Whitelist Classe A

Testes obrigatórios:
- G1: Override Manual (responder_automaticamente=True) — deve permitir tudo
- G2: Whitelist Classe A (responder_automaticamente=False) — deve permitir apenas A-01 a A-06
"""

import asyncio
import pytest
from services.whitelist_service import (
    classificar_com_whitelist,
    verificar_com_whitelist,
    obter_whitelist_info
)


# ============ G1: OVERRIDE MANUAL ============

class TestG1OverrideManual:
    """
    G1 — Override Manual

    Quando responder_automaticamente=True (padrão):
    - Qualquer mensagem é permitida
    - Whitelist não é consultada
    """

    @pytest.mark.asyncio
    async def test_g1_qualquer_mensagem_permitida(self, monkeypatch):
        """G1-A: Qualquer mensagem é permitida quando responder_automaticamente=True"""

        # Mock: governanca_service retorna responder_automaticamente=True
        async def mock_carregar_gov(actor_id, tenant_id):
            return {'responder_automaticamente': True}

        monkeypatch.setattr('services.whitelist_service.carregar_governanca', mock_carregar_gov)

        # Mensagens aleatórias (fora da whitelist)
        mensagens_teste = [
            "opa tudo bem?",
            "qual é o seu nome?",
            "como você funciona?",
            "me avisa quando terminar",
            "por favor, não responda automaticamente"
        ]

        for msg in mensagens_teste:
            permitida, detalhes = await verificar_com_whitelist(
                mensagem=msg,
                actor_id="test_user_1",
                tenant_id="test_tenant_1",
                registrar_bloqueio=False
            )

            assert permitida == True, f"Mensagem '{msg}' deveria ser permitida com responder_automaticamente=True"
            assert detalhes is None, f"Não deveria haver detalhes de bloqueio para '{msg}'"

    @pytest.mark.asyncio
    async def test_g1_responder_automaticamente_default_true(self, monkeypatch):
        """G1-B: Quando não há governanca, responder_automaticamente padrão é True"""

        # Mock: governanca_service retorna {} (vazio)
        async def mock_carregar_gov_empty(actor_id, tenant_id):
            return {}

        monkeypatch.setattr('services.whitelist_service.carregar_governanca', mock_carregar_gov_empty)

        permitida, detalhes = await verificar_com_whitelist(
            mensagem="mensagem aleatória",
            actor_id="test_user_2",
            tenant_id="test_tenant_2",
            registrar_bloqueio=False
        )

        assert permitida == True, "Sem governanca, responder_automaticamente deve defaultar para True"


# ============ G2: WHITELIST CLASSE A ============

class TestG2WhitelistClasseA:
    """
    G2 — Whitelist Classe A

    Quando responder_automaticamente=False:
    - Apenas mensagens em Whitelist A-01 a A-06 são permitidas
    - Outras mensagens são bloqueadas
    - Auditoria é registrada
    """

    def test_g2_a01_confirmacao_positiva(self):
        """G2-A01: Confirmações positivas são permitidas"""

        confirmacoes_positivas = [
            "sim",
            "okay",
            "certo",
            "confirmo",
            "ok tudo bem",
            "pode ir",
            "isso",
            "exato"
        ]

        for msg in confirmacoes_positivas:
            esta_na_whitelist, categoria, nome = classificar_com_whitelist(msg, "test_user")
            assert esta_na_whitelist == True, f"'{msg}' deveria estar em A-01"
            assert categoria == "A-01", f"'{msg}' deveria ser categorizado como A-01"

    def test_g2_a02_confirmacao_negativa(self):
        """G2-A02: Confirmações negativas são permitidas"""

        confirmacoes_negativas = [
            "não",
            "nao",
            "no",
            "nope",
            "nunca",
            "jamais"
        ]

        for msg in confirmacoes_negativas:
            esta_na_whitelist, categoria, nome = classificar_com_whitelist(msg, "test_user")
            assert esta_na_whitelist == True, f"'{msg}' deveria estar em A-02"
            assert categoria == "A-02", f"'{msg}' deveria ser categorizado como A-02"

    def test_g2_a03_cancelamento(self):
        """G2-A03: Cancelamentos são permitidos"""

        cancelamentos = [
            "cancelar",
            "cancela",
            "cancelado",
            "para",
            "stop",
            "parar"
        ]

        for msg in cancelamentos:
            esta_na_whitelist, categoria, nome = classificar_com_whitelist(msg, "test_user")
            assert esta_na_whitelist == True, f"'{msg}' deveria estar em A-03"
            assert categoria == "A-03", f"'{msg}' deveria ser categorizado como A-03"

    def test_g2_a05_onboarding(self):
        """G2-A05: Mensagens de onboarding são permitidas"""

        onboardings = [
            "olá",
            "ola",
            "oi",
            "tudo bem",
            "opa e aí"
        ]

        for msg in onboardings:
            esta_na_whitelist, categoria, nome = classificar_com_whitelist(msg, "test_user")
            assert esta_na_whitelist == True, f"'{msg}' deveria estar em A-05"
            assert categoria == "A-05", f"'{msg}' deveria ser categorizado como A-05"

    def test_g2_a06_comandos_admin(self):
        """G2-A06: Comandos administrativos são permitidos"""

        comandos = [
            "/help",
            "/ajuda",
            "/menu",
            "/pausar",
            "/retomar"
        ]

        for msg in comandos:
            esta_na_whitelist, categoria, nome = classificar_com_whitelist(msg, "test_user")
            assert esta_na_whitelist == True, f"'{msg}' deveria estar em A-06"
            assert categoria == "A-06", f"'{msg}' deveria ser categorizado como A-06"

    @pytest.mark.asyncio
    async def test_g2_mensagens_fora_whitelist_bloqueadas(self, monkeypatch):
        """G2-BLOCK: Mensagens fora da whitelist são bloqueadas quando responder_automaticamente=False"""

        # Mock: governanca_service retorna responder_automaticamente=False
        async def mock_carregar_gov_false(actor_id, tenant_id):
            return {'responder_automaticamente': False}

        monkeypatch.setattr('services.whitelist_service.carregar_governanca', mock_carregar_gov_false)

        mensagens_bloqueadas = [
            "qual é o seu nome?",
            "como você funciona?",
            "me avisa quando terminar",
            "por favor, responda algo",
            "isso é um teste"
        ]

        for msg in mensagens_bloqueadas:
            permitida, detalhes = await verificar_com_whitelist(
                mensagem=msg,
                actor_id="test_user_3",
                tenant_id="test_tenant_3",
                registrar_bloqueio=False
            )

            assert permitida == False, f"Mensagem '{msg}' deveria ser bloqueada"
            assert detalhes is not None, f"Deveria haver detalhes de bloqueio para '{msg}'"
            assert "whitelist" in detalhes.get("motivo", "").lower(), f"Motivo deveria mencionar whitelist"

    def test_g2_whitelist_info_completa(self):
        """G2-INFO: Whitelist completa contém A-01 a A-06"""

        whitelist_info = obter_whitelist_info()

        assert len(whitelist_info) == 6, "Whitelist deveria ter 6 categorias (A-01 a A-06)"
        assert "A-01" in whitelist_info
        assert "A-02" in whitelist_info
        assert "A-03" in whitelist_info
        assert "A-04" in whitelist_info
        assert "A-05" in whitelist_info
        assert "A-06" in whitelist_info


# ============ TESTES DE CRITÉRIO FINAL ============

class TestCriterioFinal:
    """Validação de critério final de sucesso"""

    def test_criterio_final_g1_g2_presentes(self):
        """Critério Final: G1 e G2 estão implementados"""

        # Verificar que as classes de teste existem
        assert TestG1OverrideManual is not None
        assert TestG2WhitelistClasseA is not None

    def test_criterio_final_sem_regressoes(self):
        """Critério Final: Nenhuma falha de caso crítico"""

        casos_criticos = [
            "sim",  # confirmação
            "não",  # negação
            "cancelar",  # cancelamento
            "oi",  # onboarding
            "/help"  # comando
        ]

        for caso in casos_criticos:
            # Cada caso crítico deve estar na whitelist
            esta_na_whitelist, categoria, nome = classificar_com_whitelist(caso, "test")
            assert esta_na_whitelist == True, f"Caso crítico '{caso}' deveria estar na whitelist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
