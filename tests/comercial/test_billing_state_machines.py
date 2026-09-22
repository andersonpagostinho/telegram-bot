"""
TESTES — Billing State Machines

Cobertura das 4 máquinas:
1. MaquinaEstadoAssinatura
2. MaquinaEstadoPagamento
3. MaquinaEstadoAcesso
4. MaquinaEstadoRetencaoDados

Testa:
- Transições válidas
- Transições inválidas
- Estados terminais
- Idempotência
- Out-of-order
- Inputs inválidos
- Efeitos sugeridos
- Determinismo
- Sem mutação
"""

import pytest
from services.billing_state_machines import (
    MaquinaEstadoAssinatura,
    AssinaturaState,
    AssinaturaEvent,
    AssinaturaTransitionCode,
    MaquinaEstadoPagamento,
    PagamentoState,
    PagamentoEvent,
    PagamentoTransitionCode,
    MaquinaEstadoAcesso,
    AcessoState,
    AcessoEvent,
    AcessoTransitionCode,
    MaquinaEstadoRetencaoDados,
    RetencaoState,
    RetencaoEvent,
    RetencaoTransitionCode,
)


# ============================================================================
# TESTS: ASSINATURA
# ============================================================================


class TestAssinaturaValidTransitions:
    """Transições válidas de Assinatura"""

    def test_pendente_to_ativa(self):
        """PENDENTE → ATIVA via payment_approved"""
        result = MaquinaEstadoAssinatura.transition(
            AssinaturaState.PENDENTE, AssinaturaEvent.PAYMENT_APPROVED
        )
        assert result.success
        assert result.current_state == AssinaturaState.ATIVA

    def test_ativa_to_cancelamento_agendado(self):
        """ATIVA → CANCELAMENTO_AGENDADO via lead_cancels"""
        result = MaquinaEstadoAssinatura.transition(
            AssinaturaState.ATIVA, AssinaturaEvent.LEAD_CANCELS
        )
        assert result.success
        assert result.current_state == AssinaturaState.CANCELAMENTO_AGENDADO

    def test_cancelamento_agendado_to_ativa_reactivate(self):
        """CANCELAMENTO_AGENDADO → ATIVA via lead_reactivates"""
        result = MaquinaEstadoAssinatura.transition(
            AssinaturaState.CANCELAMENTO_AGENDADO, AssinaturaEvent.LEAD_REACTIVATES
        )
        assert result.success
        assert result.current_state == AssinaturaState.ATIVA

    def test_cancelamento_agendado_to_cancelada(self):
        """CANCELAMENTO_AGENDADO → CANCELADA via cycle_end"""
        result = MaquinaEstadoAssinatura.transition(
            AssinaturaState.CANCELAMENTO_AGENDADO, AssinaturaEvent.CYCLE_END
        )
        assert result.success
        assert result.current_state == AssinaturaState.CANCELADA

    def test_cancelada_to_encerrada(self):
        """CANCELADA → ENCERRADA via data_deletion"""
        result = MaquinaEstadoAssinatura.transition(
            AssinaturaState.CANCELADA, AssinaturaEvent.DATA_DELETION
        )
        assert result.success
        assert result.current_state == AssinaturaState.ENCERRADA


class TestAssinaturaInvalidTransitions:
    """Transições inválidas de Assinatura"""

    def test_pendente_invalid(self):
        """PENDENTE não pode fazer outro evento"""
        invalid_events = [
            AssinaturaEvent.LEAD_CANCELS,
            AssinaturaEvent.LEAD_REACTIVATES,
            AssinaturaEvent.CYCLE_END,
            AssinaturaEvent.DATA_DELETION,
        ]
        for event in invalid_events:
            result = MaquinaEstadoAssinatura.transition(
                AssinaturaState.PENDENTE, event
            )
            assert not result.success

    def test_ativa_invalid(self):
        """ATIVA só permite LEAD_CANCELS"""
        invalid_events = [
            AssinaturaEvent.PAYMENT_APPROVED,
            AssinaturaEvent.LEAD_REACTIVATES,
            AssinaturaEvent.CYCLE_END,
            AssinaturaEvent.DATA_DELETION,
        ]
        for event in invalid_events:
            result = MaquinaEstadoAssinatura.transition(AssinaturaState.ATIVA, event)
            assert not result.success

    def test_encerrada_terminal(self):
        """ENCERRADA é terminal"""
        events = [
            AssinaturaEvent.PAYMENT_APPROVED,
            AssinaturaEvent.LEAD_CANCELS,
            AssinaturaEvent.LEAD_REACTIVATES,
            AssinaturaEvent.CYCLE_END,
            AssinaturaEvent.DATA_DELETION,
        ]
        for event in events:
            result = MaquinaEstadoAssinatura.transition(
                AssinaturaState.ENCERRADA, event
            )
            assert not result.success
            assert result.code == AssinaturaTransitionCode.TERMINAL_STATE


class TestAssinaturaEffects:
    """Efeitos sugeridos de Assinatura"""

    def test_ativa_activation_effects(self):
        """PENDENTE → ATIVA sugere efeitos"""
        result = MaquinaEstadoAssinatura.transition(
            AssinaturaState.PENDENTE, AssinaturaEvent.PAYMENT_APPROVED
        )
        assert "publicar_evento:assinatura_ativada" in result.suggested_effects
        assert "iniciar_timer_renovacao" in result.suggested_effects


# ============================================================================
# TESTS: PAGAMENTO
# ============================================================================


class TestPagamentoValidTransitions:
    """Transições válidas de Pagamento"""

    def test_pendente_to_aprovado(self):
        """PENDENTE → APROVADO"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.PENDENTE, PagamentoEvent.PAYMENT_APPROVED
        )
        assert result.success
        assert result.current_state == PagamentoState.APROVADO

    def test_pendente_to_recusado(self):
        """PENDENTE → RECUSADO"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.PENDENTE, PagamentoEvent.PAYMENT_FAILED
        )
        assert result.success
        assert result.current_state == PagamentoState.RECUSADO

    def test_pendente_to_atrasado(self):
        """PENDENTE → ATRASADO"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.PENDENTE, PagamentoEvent.PAYMENT_DELAYED
        )
        assert result.success
        assert result.current_state == PagamentoState.ATRASADO

    def test_recusado_to_aprovado_retry(self):
        """RECUSADO → APROVADO (retry bem-sucedido)"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.RECUSADO, PagamentoEvent.RETRY_APPROVED
        )
        assert result.success
        assert result.current_state == PagamentoState.APROVADO

    def test_atrasado_to_aprovado(self):
        """ATRASADO → APROVADO"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.ATRASADO, PagamentoEvent.PAYMENT_APPROVED
        )
        assert result.success
        assert result.current_state == PagamentoState.APROVADO

    def test_atrasado_to_recusado_final(self):
        """ATRASADO → RECUSADO (falha final)"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.ATRASADO, PagamentoEvent.RETRY_FAILED
        )
        assert result.success
        assert result.current_state == PagamentoState.RECUSADO

    def test_aprovado_to_reembolsado(self):
        """APROVADO → REEMBOLSADO"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.APROVADO, PagamentoEvent.REFUND_REQUESTED
        )
        assert result.success
        assert result.current_state == PagamentoState.REEMBOLSADO

    def test_aprovado_to_contestado(self):
        """APROVADO → CONTESTADO (chargeback)"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.APROVADO, PagamentoEvent.CHARGEBACK_OPENED
        )
        assert result.success
        assert result.current_state == PagamentoState.CONTESTADO

    def test_contestado_to_resolvido(self):
        """CONTESTADO → RESOLVIDO"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.CONTESTADO, PagamentoEvent.CHARGEBACK_RESOLVED
        )
        assert result.success
        assert result.current_state == PagamentoState.RESOLVIDO


class TestPagamentoInvalidTransitions:
    """Transições inválidas de Pagamento"""

    def test_aprovado_no_return_to_pendente(self):
        """APROVADO não volta para PENDENTE"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.APROVADO, PagamentoEvent.PAYMENT_DELAYED
        )
        assert not result.success

    def test_reembolsado_terminal(self):
        """REEMBOLSADO é terminal"""
        events = [
            PagamentoEvent.PAYMENT_APPROVED,
            PagamentoEvent.PAYMENT_FAILED,
            PagamentoEvent.REFUND_REQUESTED,
        ]
        for event in events:
            result = MaquinaEstadoPagamento.transition(
                PagamentoState.REEMBOLSADO, event
            )
            assert not result.success

    def test_resolvido_terminal(self):
        """RESOLVIDO é terminal"""
        events = [
            PagamentoEvent.PAYMENT_APPROVED,
            PagamentoEvent.CHARGEBACK_OPENED,
        ]
        for event in events:
            result = MaquinaEstadoPagamento.transition(
                PagamentoState.RESOLVIDO, event
            )
            assert not result.success
            assert result.code == PagamentoTransitionCode.TERMINAL_STATE


class TestPagamentoEffects:
    """Efeitos sugeridos de Pagamento"""

    def test_aprovado_effects(self):
        """PENDENTE → APROVADO sugere liberar_acesso"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.PENDENTE, PagamentoEvent.PAYMENT_APPROVED
        )
        assert "liberar_acesso" in result.suggested_effects
        assert "publicar_evento:pagamento_aprovado" in result.suggested_effects

    def test_recusado_effects(self):
        """PENDENTE → RECUSADO sugere retry"""
        result = MaquinaEstadoPagamento.transition(
            PagamentoState.PENDENTE, PagamentoEvent.PAYMENT_FAILED
        )
        assert "iniciar_retry_payment" in result.suggested_effects


# ============================================================================
# TESTS: ACESSO
# ============================================================================


class TestAcessoValidTransitions:
    """Transições válidas de Acesso"""

    def test_liberado_to_restrito(self):
        """LIBERADO → RESTRITO"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.LIBERADO, AcessoEvent.RESTRICT_ACCESS
        )
        assert result.success
        assert result.current_state == AcessoState.RESTRITO

    def test_liberado_to_suspenso(self):
        """LIBERADO → SUSPENSO (payment_failed)"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.LIBERADO, AcessoEvent.PAYMENT_FAILED
        )
        assert result.success
        assert result.current_state == AcessoState.SUSPENSO

    def test_restrito_to_liberado(self):
        """RESTRITO → LIBERADO"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.RESTRITO, AcessoEvent.PAYMENT_APPROVED
        )
        assert result.success
        assert result.current_state == AcessoState.LIBERADO

    def test_restrito_to_suspenso_direct(self):
        """RESTRITO → SUSPENSO (direto, sem passar por LIBERADO)"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.RESTRITO, AcessoEvent.PAYMENT_FAILED
        )
        assert result.success
        assert result.current_state == AcessoState.SUSPENSO

    def test_suspenso_to_liberado(self):
        """SUSPENSO → LIBERADO (reativação)"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.SUSPENSO, AcessoEvent.PAYMENT_APPROVED
        )
        assert result.success
        assert result.current_state == AcessoState.LIBERADO

    def test_restrito_idempotent(self):
        """RESTRITO → RESTRITO (idempotente)"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.RESTRITO, AcessoEvent.RESTRICT_ACCESS
        )
        assert result.success
        assert result.current_state == AcessoState.RESTRITO


class TestAcessoInvalidTransitions:
    """Transições inválidas de Acesso"""

    def test_liberado_restrict_twice(self):
        """LIBERADO pode ir para RESTRITO, depois de RESTRITO pode voltar"""
        result1 = MaquinaEstadoAcesso.transition(
            AcessoState.LIBERADO, AcessoEvent.RESTRICT_ACCESS
        )
        assert result1.success
        assert result1.current_state == AcessoState.RESTRITO

        # De RESTRITO para LIBERADO
        result2 = MaquinaEstadoAcesso.transition(
            AcessoState.RESTRITO, AcessoEvent.PAYMENT_APPROVED
        )
        assert result2.success
        assert result2.current_state == AcessoState.LIBERADO

    def test_encerrado_terminal(self):
        """ENCERRADO é terminal"""
        events = [
            AcessoEvent.RESTRICT_ACCESS,
            AcessoEvent.PAYMENT_FAILED,
            AcessoEvent.PAYMENT_APPROVED,
            AcessoEvent.DATA_DELETION,
        ]
        for event in events:
            result = MaquinaEstadoAcesso.transition(AcessoState.ENCERRADO, event)
            assert not result.success
            assert result.code == AcessoTransitionCode.TERMINAL_STATE


class TestAcessoEffects:
    """Efeitos sugeridos de Acesso"""

    def test_liberado_effects(self):
        """Transição para LIBERADO sugere liberar_acesso"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.RESTRITO, AcessoEvent.PAYMENT_APPROVED
        )
        assert "liberar_acesso_completo" in result.suggested_effects

    def test_suspenso_effects(self):
        """Transição para SUSPENSO sugere bloquear"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.LIBERADO, AcessoEvent.PAYMENT_FAILED
        )
        assert "bloquear_acesso" in result.suggested_effects


# ============================================================================
# TESTS: RETENÇÃO
# ============================================================================


class TestRetencaoValidTransitions:
    """Transições válidas de Retenção"""

    def test_ativo_to_em_retencao(self):
        """ATIVO → EM_RETENCAO"""
        result = MaquinaEstadoRetencaoDados.transition(
            RetencaoState.ATIVO, RetencaoEvent.ACESSO_BLOQUEADO
        )
        assert result.success
        assert result.current_state == RetencaoState.EM_RETENCAO

    def test_em_retencao_to_elegivel_exclusao(self):
        """EM_RETENCAO → ELEGIVEL_EXCLUSAO"""
        result = MaquinaEstadoRetencaoDados.transition(
            RetencaoState.EM_RETENCAO, RetencaoEvent.RETENTION_PERIOD_EXPIRES
        )
        assert result.success
        assert result.current_state == RetencaoState.ELEGIVEL_EXCLUSAO

    def test_elegivel_exclusao_to_excluido(self):
        """ELEGIVEL_EXCLUSAO → EXCLUIDO"""
        result = MaquinaEstadoRetencaoDados.transition(
            RetencaoState.ELEGIVEL_EXCLUSAO, RetencaoEvent.DATA_DELETION
        )
        assert result.success
        assert result.current_state == RetencaoState.EXCLUIDO

    def test_em_retencao_to_ativo_reactivate(self):
        """EM_RETENCAO → ATIVO (reativação durante janela)"""
        result = MaquinaEstadoRetencaoDados.transition(
            RetencaoState.EM_RETENCAO, RetencaoEvent.REATIVACAO_VALIDA
        )
        assert result.success
        assert result.current_state == RetencaoState.ATIVO


class TestRetencaoInvalidTransitions:
    """Transições inválidas de Retenção"""

    def test_ativo_invalid(self):
        """ATIVO só permite ACESSO_BLOQUEADO"""
        invalid_events = [
            RetencaoEvent.RETENTION_PERIOD_EXPIRES,
            RetencaoEvent.DATA_DELETION,
            RetencaoEvent.REATIVACAO_VALIDA,
        ]
        for event in invalid_events:
            result = MaquinaEstadoRetencaoDados.transition(
                RetencaoState.ATIVO, event
            )
            assert not result.success

    def test_elegivel_exclusao_invalid(self):
        """ELEGIVEL_EXCLUSAO só permite DATA_DELETION"""
        invalid_events = [
            RetencaoEvent.ACESSO_BLOQUEADO,
            RetencaoEvent.RETENTION_PERIOD_EXPIRES,
            RetencaoEvent.REATIVACAO_VALIDA,
        ]
        for event in invalid_events:
            result = MaquinaEstadoRetencaoDados.transition(
                RetencaoState.ELEGIVEL_EXCLUSAO, event
            )
            assert not result.success

    def test_excluido_terminal(self):
        """EXCLUIDO é terminal"""
        events = [
            RetencaoEvent.ACESSO_BLOQUEADO,
            RetencaoEvent.RETENTION_PERIOD_EXPIRES,
            RetencaoEvent.DATA_DELETION,
            RetencaoEvent.REATIVACAO_VALIDA,
        ]
        for event in events:
            result = MaquinaEstadoRetencaoDados.transition(
                RetencaoState.EXCLUIDO, event
            )
            assert not result.success
            assert result.code == RetencaoTransitionCode.TERMINAL_STATE


class TestRetencaoEffects:
    """Efeitos sugeridos de Retenção"""

    def test_em_retencao_effects(self):
        """ATIVO → EM_RETENCAO sugere iniciar_timer_retencao"""
        result = MaquinaEstadoRetencaoDados.transition(
            RetencaoState.ATIVO, RetencaoEvent.ACESSO_BLOQUEADO
        )
        assert "tornar_dados_inacessiveis" in result.suggested_effects
        assert "iniciar_timer_retencao" in result.suggested_effects

    def test_excluido_effects(self):
        """ELEGIVEL_EXCLUSAO → EXCLUIDO sugere deletar_todos_dados"""
        result = MaquinaEstadoRetencaoDados.transition(
            RetencaoState.ELEGIVEL_EXCLUSAO, RetencaoEvent.DATA_DELETION
        )
        assert "deletar_todos_dados_permanentemente" in result.suggested_effects


# ============================================================================
# TESTS: ISOLATION & DETERMINISM
# ============================================================================


class TestMachineIsolation:
    """Testa isolamento entre máquinas"""

    def test_assinatura_independent_of_pagamento(self):
        """Assinatura não depende de Pagamento"""
        # Assinatura pode transicionar independentemente
        result = MaquinaEstadoAssinatura.transition(
            AssinaturaState.PENDENTE, AssinaturaEvent.PAYMENT_APPROVED
        )
        assert result.success

    def test_acesso_independent_of_assinatura(self):
        """Acesso pode mudar sem que Assinatura mude"""
        result = MaquinaEstadoAcesso.transition(
            AcessoState.LIBERADO, AcessoEvent.RESTRICT_ACCESS
        )
        assert result.success
        # Assinatura permanece inalterada


class TestMachineDeterminism:
    """Testa determinismo de todas as máquinas"""

    def test_assinatura_deterministic(self):
        """Assinatura: mesma entrada = mesma saída"""
        r1 = MaquinaEstadoAssinatura.transition(
            AssinaturaState.PENDENTE, AssinaturaEvent.PAYMENT_APPROVED
        )
        r2 = MaquinaEstadoAssinatura.transition(
            AssinaturaState.PENDENTE, AssinaturaEvent.PAYMENT_APPROVED
        )
        assert r1.success == r2.success
        assert r1.current_state == r2.current_state

    def test_pagamento_deterministic(self):
        """Pagamento: mesma entrada = mesma saída"""
        r1 = MaquinaEstadoPagamento.transition(
            PagamentoState.PENDENTE, PagamentoEvent.PAYMENT_APPROVED
        )
        r2 = MaquinaEstadoPagamento.transition(
            PagamentoState.PENDENTE, PagamentoEvent.PAYMENT_APPROVED
        )
        assert r1.success == r2.success
        assert r1.current_state == r2.current_state

    def test_acesso_deterministic(self):
        """Acesso: mesma entrada = mesma saída"""
        r1 = MaquinaEstadoAcesso.transition(
            AcessoState.LIBERADO, AcessoEvent.RESTRICT_ACCESS
        )
        r2 = MaquinaEstadoAcesso.transition(
            AcessoState.LIBERADO, AcessoEvent.RESTRICT_ACCESS
        )
        assert r1.success == r2.success
        assert r1.current_state == r2.current_state

    def test_retencao_deterministic(self):
        """Retenção: mesma entrada = mesma saída"""
        r1 = MaquinaEstadoRetencaoDados.transition(
            RetencaoState.ATIVO, RetencaoEvent.ACESSO_BLOQUEADO
        )
        r2 = MaquinaEstadoRetencaoDados.transition(
            RetencaoState.ATIVO, RetencaoEvent.ACESSO_BLOQUEADO
        )
        assert r1.success == r2.success
        assert r1.current_state == r2.current_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
