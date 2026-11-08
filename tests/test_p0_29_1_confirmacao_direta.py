"""
Testes para P0.29.1 — Confirmação no agendamento direto

Validar que agendamento direto cria confirmacao_pendente
e permite confirmação via "sim"
"""

import pytest
from utils.confirmacao_pendente_manager import (
    gerar_operacao_id,
    criar_confirmacao_pendente,
    validar_confirmacao_pendente,
)


class TestConfirmacaoPendenteDireta:
    """Validar criação e validação de confirmacao_pendente em agendamento direto"""

    def test_gerar_operacao_id_deterministica(self):
        """operacao_id deve ser determinístico"""
        cliente_id = "5511991382080"
        dados = {
            "profissional": "Bruna",
            "data": "2026-11-09",
            "hora": "10:00"
        }

        op1 = gerar_operacao_id(cliente_id, "agendamento", dados)
        op2 = gerar_operacao_id(cliente_id, "agendamento", dados)

        assert op1 == op2, "operacao_id deve ser determinístico"
        assert "agendamento" in op1
        assert "bruna" in op1.lower()
        assert "20261109" in op1
        assert "1000" in op1

    def test_criar_confirmacao_pendente_schema(self):
        """confirmacao_pendente deve ter schema correto"""
        operacao_id = "agendamento_5511991382080_bruna_20261109_1000"
        conf = criar_confirmacao_pendente(operacao_id, "agendamento")

        assert conf["operacao_id"] == operacao_id
        assert conf["tipo"] == "agendamento"
        assert conf["status"] == "pendente"
        assert "apresentada_em" in conf
        assert conf["tentativas"] == 1
        assert conf["max_tentativas"] == 3
        assert "expira_em" in conf

    def test_validar_confirmacao_pendente_existe(self):
        """Validar confirmacao_pendente que existe"""
        operacao_id = "agendamento_5511991382080_bruna_20261109_1000"
        conf = criar_confirmacao_pendente(operacao_id, "agendamento")
        ctx = {"confirmacao_pendente": conf}

        validacao = validar_confirmacao_pendente(ctx, operacao_id)

        assert validacao["valida"] is True, f"Deve validar. Motivo: {validacao.get('motivo')}"
        assert validacao.get("confirmacao_pendente") is not None

    def test_validar_confirmacao_pendente_nao_existe(self):
        """Validar falha quando confirmacao_pendente não existe"""
        operacao_id = "agendamento_5511991382080_bruna_20261109_1000"
        ctx = {}  # Sem confirmacao_pendente

        validacao = validar_confirmacao_pendente(ctx, operacao_id)

        assert validacao["valida"] is False
        assert validacao["motivo"] == "sem_confirmacao_pendente"

    def test_validar_confirmacao_pendente_operacao_id_mismatch(self):
        """Validar falha com operacao_id diferente"""
        operacao_id1 = "agendamento_5511991382080_bruna_20261109_1000"
        operacao_id2 = "agendamento_5511991382080_gloria_20261109_1400"

        conf = criar_confirmacao_pendente(operacao_id1, "agendamento")
        ctx = {"confirmacao_pendente": conf}

        validacao = validar_confirmacao_pendente(ctx, operacao_id2)

        assert validacao["valida"] is False
        assert "operacao_id" in validacao["motivo"].lower()

    def test_confirmacao_pendente_schema_matches_slots_pattern(self):
        """Confirmar que schema de confirmacao_pendente é consistente"""
        # Via slots (linha 7367)
        operacao_id_slots = "agendamento_5511991382080_bruna_20261109_1000"
        conf_slots = criar_confirmacao_pendente(operacao_id_slots, "agendamento")

        # Via direto (linha 2603 + P0.29.1)
        operacao_id_direto = gerar_operacao_id(
            "5511991382080",
            "agendamento",
            {"profissional": "Bruna", "data": "2026-11-09", "hora": "10:00"}
        )
        conf_direto = criar_confirmacao_pendente(operacao_id_direto, "agendamento")

        # Ambas devem ter mesmo schema
        assert set(conf_slots.keys()) == set(conf_direto.keys())
        assert conf_slots["tipo"] == conf_direto["tipo"]
        assert conf_slots["status"] == conf_direto["status"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
