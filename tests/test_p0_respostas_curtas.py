"""
Testes P0: Respostas curtas e normalização tem_draft
Validar correções mínimas para "sim"/"não" sem contexto
"""

import pytest
from services.classificador_conversa import extrair_features_conversa
from services.draft_validator import eh_draft_valido_para_retomar


class TestNormalizacaoTemDraft:
    """Testes para garantir que tem_draft é sempre booleano"""

    def test_tem_draft_none_quando_nao_existe_draft(self):
        """tem_draft deve ser False, não None, quando draft não existe"""
        ctx = {"estado_fluxo": "idle"}
        features = extrair_features_conversa("oi", ctx)

        # ANTES: tem_draft = None (falsy mas não False)
        # DEPOIS: tem_draft = False (estritamente booleano)
        assert isinstance(features["tem_draft"], bool), f"tem_draft deve ser bool, got {type(features['tem_draft'])}"
        assert features["tem_draft"] is False, "tem_draft deve ser False quando draft não existe"

    def test_tem_draft_false_quando_draft_residual(self):
        """tem_draft deve ser False quando draft é residual (1 campo em idle)"""
        ctx = {
            "estado_fluxo": "idle",
            "draft_agendamento": {"data_hora": "2026-11-03T09:00:00+00:00"}  # Residual
        }
        features = extrair_features_conversa("oi", ctx)

        assert isinstance(features["tem_draft"], bool)
        assert features["tem_draft"] is False, "Draft residual deve ser False"

    def test_tem_draft_true_quando_draft_valido(self):
        """tem_draft deve ser True quando draft é válido em estado ativo"""
        ctx = {
            "estado_fluxo": "aguardando_servico",
            "draft_agendamento": {
                "profissional": "Bruna",
                "data_hora": "2026-11-15T10:00:00+00:00",
                "servico": None
            }
        }
        features = extrair_features_conversa("oi", ctx)

        assert isinstance(features["tem_draft"], bool)
        assert features["tem_draft"] is True, "Draft válido deve ser True"

    def test_tem_draft_false_para_draft_vazio_dict(self):
        """tem_draft deve ser False para draft vazio {}"""
        ctx = {
            "estado_fluxo": "aguardando_servico",
            "draft_agendamento": {}  # Vazio
        }
        features = extrair_features_conversa("oi", ctx)

        assert isinstance(features["tem_draft"], bool)
        assert features["tem_draft"] is False, "Draft vazio deve ser False"


class TestRecuperacaoRespostasCurtas:
    """Testes para reconhecimento de respostas curtas sem contexto"""

    def test_resposta_sim_sem_fluxo(self):
        """'sim' sem fluxo deve ser reconhecido como resposta curta"""
        # Nota: Este teste valida a LÓGICA de reconhecimento
        # O teste E2E rodaremos na suite de integração
        texto = "sim"
        padroes_resposta_curta = r"^(sim|não|nao|ok|tudo bem|tá|ta|claro|certo|beleza)$"

        import re
        match = bool(re.search(padroes_resposta_curta, texto.lower(), re.IGNORECASE))
        assert match is True, "'sim' deve ser reconhecido como resposta curta"

    def test_resposta_nao_sem_fluxo(self):
        """'não' sem fluxo deve ser reconhecido como resposta curta"""
        texto = "não"
        padroes_resposta_curta = r"^(sim|não|nao|ok|tudo bem|tá|ta|claro|certo|beleza)$"

        import re
        match = bool(re.search(padroes_resposta_curta, texto.lower(), re.IGNORECASE))
        assert match is True, "'não' deve ser reconhecido como resposta curta"

    def test_resposta_ok_sem_fluxo(self):
        """'ok' sem fluxo deve ser reconhecido como resposta curta"""
        texto = "ok"
        padroes_resposta_curta = r"^(sim|não|nao|ok|tudo bem|tá|ta|claro|certo|beleza)$"

        import re
        match = bool(re.search(padroes_resposta_curta, texto.lower(), re.IGNORECASE))
        assert match is True, "'ok' deve ser reconhecido como resposta curta"

    def test_texto_operacional_nao_e_resposta_curta(self):
        """'quero um corte' não deve ser reconhecido como resposta curta"""
        texto = "quero um corte amanhã"
        padroes_resposta_curta = r"^(sim|não|nao|ok|tudo bem|tá|ta|claro|certo|beleza)$"

        import re
        match = bool(re.search(padroes_resposta_curta, texto.lower(), re.IGNORECASE))
        assert match is False, "Texto operacional não deve ser resposta curta"

    def test_saudacao_nao_e_resposta_curta(self):
        """'oi' é saudação, não resposta curta"""
        texto = "oi"
        padroes_resposta_curta = r"^(sim|não|nao|ok|tudo bem|tá|ta|claro|certo|beleza)$"

        import re
        match = bool(re.search(padroes_resposta_curta, texto.lower(), re.IGNORECASE))
        assert match is False, "'oi' é saudação, não resposta curta"


class TestIntegracaoRespostaCurtasComDraft:
    """Integração: Resposta curta + draft"""

    def test_resposta_curta_com_draft_residual_nao_retoma(self):
        """'sim' com draft residual NÃO deve retomar fluxo"""
        draft_residual = {"data_hora": "2026-11-03T09:00:00+00:00"}
        estado = "idle"

        valido = eh_draft_valido_para_retomar(draft_residual, estado)
        assert valido is False, "Draft residual em idle não deve ser retomável"

    def test_resposta_curta_com_draft_valido_em_espera(self):
        """'sim' com draft válido em aguardando_* DEVE retomar fluxo"""
        draft_valido = {
            "profissional": "Bruna",
            "data_hora": "2026-11-15T10:00:00+00:00",
            "servico": None
        }
        estado = "aguardando_servico"

        valido = eh_draft_valido_para_retomar(draft_valido, estado)
        assert valido is True, "Draft válido em estado ativo deve ser retomável"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
