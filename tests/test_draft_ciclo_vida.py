"""
TESTES TDD — Draft Ciclo de Vida
Problema: Draft residual interfere em classificação conversacional
Solução: Validar que draft respeita estado atual (não apenas contar campos)
"""

import pytest
from datetime import datetime, timezone, timedelta
import dateutil.parser

# Função que será implementada em FASE 4
# Para agora, vamos importá-la e ela vai falhar (RED)
try:
    from services.draft_validator import eh_draft_valido_para_retomar
except ImportError:
    # Placeholder: função não existe ainda
    def eh_draft_valido_para_retomar(draft: dict, estado_fluxo: str) -> bool:
        """Placeholder que será implementado em FASE 4"""
        raise NotImplementedError("eh_draft_valido_para_retomar() não implementado ainda")


class TestEhDraftValidoParaRetomar:
    """Suite TDD — Testes UNIT para função eh_draft_valido_para_retomar()"""

    # ==================== DRAFT RESIDUAL + IDLE ====================

    def test_1_draft_residual_somente_data_em_idle(self):
        """RED: Draft com somente data_hora em estado idle = NÃO válido"""
        draft_residual = {"data_hora": "2026-11-03T09:00:00+00:00"}
        resultado = eh_draft_valido_para_retomar(draft_residual, "idle")
        assert resultado is False, "Draft residual em idle deve ser inválido"

    def test_2_draft_vazio_em_idle(self):
        """RED: Draft vazio em estado idle = NÃO válido"""
        resultado = eh_draft_valido_para_retomar({}, "idle")
        assert resultado is False, "Draft vazio em idle deve ser inválido"

    def test_3_draft_none_em_idle(self):
        """RED: Draft None em estado idle = NÃO válido"""
        resultado = eh_draft_valido_para_retomar(None, "idle")
        assert resultado is False, "Draft None deve ser inválido"

    # ==================== DRAFT VÁLIDO EM ESTADOS DE ESPERA ====================

    def test_4_draft_valido_aguardando_servico(self):
        """GREEN: Draft válido em aguardando_servico (2 campos preenchidos)"""
        draft = {
            "profissional": "Bruna",
            "data_hora": "2026-11-15T10:00:00+00:00",
            "servico": None  # Sendo coletado
        }
        resultado = eh_draft_valido_para_retomar(draft, "aguardando_servico")
        assert resultado is True, "Draft com 2 campos em aguardando_servico deve ser válido"

    def test_5_draft_valido_aguardando_profissional(self):
        """GREEN: Draft válido em aguardando_profissional (2 campos preenchidos)"""
        draft = {
            "profissional": None,  # Sendo coletado
            "data_hora": "2026-11-15T10:00:00+00:00",
            "servico": "corte feminino"
        }
        resultado = eh_draft_valido_para_retomar(draft, "aguardando_profissional")
        assert resultado is True, "Draft com 2 campos em aguardando_profissional deve ser válido"

    def test_6_draft_valido_aguardando_data(self):
        """GREEN: Draft válido em aguardando_data (2 campos preenchidos)"""
        draft = {
            "profissional": "Gloria",
            "data_hora": None,  # Sendo coletado
            "servico": "manicure"
        }
        resultado = eh_draft_valido_para_retomar(draft, "aguardando_data")
        assert resultado is True, "Draft com 2 campos em aguardando_data deve ser válido"

    def test_7_draft_completo_aguardando_confirmacao(self):
        """GREEN: Draft completo em aguardando_confirmacao (3 campos preenchidos)"""
        draft = {
            "profissional": "Joana",
            "data_hora": "2026-11-15T14:00:00+00:00",
            "servico": "escova"
        }
        resultado = eh_draft_valido_para_retomar(draft, "aguardando_confirmacao_agendamento")
        assert resultado is True, "Draft com 3 campos em aguardando_confirmacao deve ser válido"

    # ==================== DRAFT EXPIRADO ====================

    def test_8_draft_expirado_data_passada(self):
        """RED: Draft com data_hora expirada = NÃO válido"""
        data_expirada = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        draft = {
            "profissional": "Carla",
            "data_hora": data_expirada,
            "servico": "coloracao"
        }
        resultado = eh_draft_valido_para_retomar(draft, "aguardando_confirmacao_agendamento")
        assert resultado is False, "Draft com data expirada deve ser inválido"

    def test_9_draft_incompleto_1_campo(self):
        """RED: Draft com somente 1 campo preenchido = NÃO válido"""
        draft = {"profissional": "Bruna"}  # Faltam 2 campos
        resultado = eh_draft_valido_para_retomar(draft, "aguardando_servico")
        assert resultado is False, "Draft com somente 1 campo deve ser inválido"

    def test_10_draft_incompleto_em_aguardando_e_depois_idle(self):
        """RED: Draft criado em estado ativo + depois idle = NÃO válido em idle"""
        draft = {"profissional": "Bruna", "data_hora": "2026-11-15T10:00:00+00:00"}

        # Em estado ativo: seria válido
        resultado_ativo = eh_draft_valido_para_retomar(draft, "aguardando_servico")
        assert resultado_ativo is True, "Draft deve ser válido em aguardando_servico"

        # Depois estado vira idle: agora não é válido
        resultado_idle = eh_draft_valido_para_retomar(draft, "idle")
        assert resultado_idle is False, "Mesmo draft torna-se inválido em idle"

    def test_11_draft_data_hora_invalida(self):
        """RED: Draft com data_hora inválida (não é ISO) = NÃO válido"""
        draft = {
            "profissional": "Bruna",
            "data_hora": "não é data",  # Inválida
            "servico": "corte"
        }
        resultado = eh_draft_valido_para_retomar(draft, "aguardando_data")
        assert resultado is False, "Draft com data_hora inválida deve ser inválido"

    def test_12_draft_2_campos_em_idle(self):
        """RED: Draft com 2 campos preenchidos mas em idle = NÃO válido"""
        draft = {
            "profissional": "Bruna",
            "data_hora": "2026-11-15T10:00:00+00:00",
            "servico": None
        }
        resultado = eh_draft_valido_para_retomar(draft, "idle")
        assert resultado is False, "Draft mesmo com 2 campos em idle deve ser inválido"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
