#!/usr/bin/env python3
"""
FASE 2 — Testes críticos para correção de preservar_continuidade_data.

Foco: Verificar se novo serviço é permitido quando em estado aguardando_data.
"""

import pytest
from services.classificador_conversa import (
    classificar_intencao_conversacional,
)


class TestFase2FixPreservarContinuidade:
    """Testes críticos: novo serviço desbloqueado em aguardando_data"""

    def test_01_novo_servico_diferente_desbloqueado(self):
        """CRITICO: Draft 'coloracao' + novo 'corte feminino'
        DEVE retornar agendamento_direto (nao bloqueado por continuidade)"""
        catalogo = ["coloracao", "corte feminino", "escova"]
        ctx = {
            "draft_agendamento": {"servico": "coloracao"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "quero marcar corte hoje",
            ctx,
            catalogo_servicos=catalogo
        )

        # ANTES FIX: bloqueado por preservar_continuidade_data
        # DEPOIS FIX: desbloqueado porque novo_servico_identificado
        assert resultado["intencao_conversacional"] == "agendamento_direto", \
            f"BLOQUEADO: esperado agendamento_direto, obtido {resultado['intencao_conversacional']}"

    def test_02_mesmo_servico_preservado(self):
        """Draft 'corte feminino' + mesmo 'corte feminino'
        DEVE retornar ajuste_incremental (continuidade preservada)"""
        catalogo = ["coloracao", "corte feminino", "escova"]
        ctx = {
            "draft_agendamento": {"servico": "corte feminino"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "quero outro horario para corte feminino",
            ctx,
            catalogo_servicos=catalogo
        )

        # Mesmo servico = ajuste incremental
        assert resultado["intencao_conversacional"] == "ajuste_incremental", \
            f"Esperado ajuste_incremental, obtido {resultado['intencao_conversacional']}"

    def test_03_sem_novo_servico_preservado(self):
        """Draft 'coloracao' + mensagem sem servico novo
        continuidade preservada (nao inventa novo servico)"""
        catalogo = ["coloracao", "corte feminino", "escova"]
        ctx = {
            "draft_agendamento": {"servico": "coloracao"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "qual o horario?",
            ctx,
            catalogo_servicos=catalogo
        )

        # Sem novo servico mencionado
        assert resultado["features"]["servico_mencionado"] is None, \
            f"Nao deveria inventar servico, obtido {resultado['features']['servico_mencionado']}"

    def test_04_novo_servico_com_tempo(self):
        """Draft 'coloracao' + 'quero escova hoje'
        DEVE retornar agendamento_direto"""
        catalogo = ["coloracao", "escova"]
        ctx = {
            "draft_agendamento": {"servico": "coloracao"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "prefiro escova hoje",
            ctx,
            catalogo_servicos=catalogo
        )

        assert resultado["intencao_conversacional"] == "agendamento_direto", \
            f"Novo servico bloqueado: {resultado['intencao_conversacional']}"
        assert resultado["features"]["servico_mencionado"] == "escova"

    def test_05_fora_aguardando_data_desbloqueado(self):
        """Fora de aguardando_data, novo servico sempre desbloqueado"""
        catalogo = ["coloracao", "corte feminino"]
        ctx = {
            "draft_agendamento": None,
            "estado_fluxo": "pendente"
        }

        resultado = classificar_intencao_conversacional(
            "quero marcar corte feminino hoje",
            ctx,
            catalogo_servicos=catalogo
        )

        assert resultado["intencao_conversacional"] == "agendamento_direto"
        assert resultado["features"]["servico_mencionado"] == "corte feminino"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
