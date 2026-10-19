"""
TESTES P0.6.1 — Corrigir reclassificação de intenção

Validar que P0.6.1 diferencia pergunta genuína vs agendamento com cortesia
"""

import pytest
from services.classificador_conversa import classificar_intencao_conversacional


class TestP061IntencaoFix:
    """Testes de P0.6.1 com casos críticos"""

    def test_t1_pergunta_genuina(self):
        """Pergunta genuína → consulta"""
        resultado = classificar_intencao_conversacional(
            "Tem manicure amanhã?",
            {"draft_agendamento": {"servico": "corte feminino"}},
            ["manicure", "corte feminino"]
        )
        assert resultado["intencao_conversacional"] == "consulta_disponibilidade_servico"
        print("✅ T1: Pergunta genuína = consulta", flush=True)

    def test_t2_agendamento_com_cortesia(self):
        """Agendamento com '?' de cortesia → agendamento_direto"""
        resultado = classificar_intencao_conversacional(
            "Quero agendar manicure para amanhã, teria?",
            {"draft_agendamento": {"servico": "corte feminino"}},
            ["manicure", "corte feminino"]
        )
        assert resultado["intencao_conversacional"] == "agendamento_direto"
        print(f"✅ T2: Agendamento com cortesia = agendamento_direto (motivo={resultado.get('motivo')})", flush=True)

    def test_t3_sequencial_mesmo_servico(self):
        """Sequencial: mesmo serviço com '?' → agendamento_direto"""
        resultado = classificar_intencao_conversacional(
            "Quero corte para terça, teria?",
            {"draft_agendamento": {"servico": "corte feminino"}},
            ["manicure", "corte feminino"]
        )
        assert resultado["intencao_conversacional"] == "agendamento_direto"
        print(f"✅ T3: Sequencial mesmo serviço = agendamento_direto (motivo={resultado.get('motivo')})", flush=True)

    def test_t4_consulta_pura(self):
        """Consulta pura sem draft → consulta ou indefinida"""
        resultado = classificar_intencao_conversacional(
            "Vocês têm manicure?",
            {},
            ["manicure", "corte feminino"]
        )
        # Sem draft, pode ser consulta ou indefinida
        assert resultado["intencao_conversacional"] in ["consulta_disponibilidade_servico", "indefinida"]
        print(f"✅ T4: Consulta pura sem draft = {resultado['intencao_conversacional']}", flush=True)
