"""
TESTES — Trial State Machine

Cobertura:
- Todas as transições válidas
- Todas as transições inválidas
- Estados terminais
- Idempotência
- Out-of-order
- Estados desconhecidos
- Eventos desconhecidos
- Efeitos sugeridos
- Sem efeitos colaterais
- Determinismo
"""

import pytest
from services.trial_state_machine import (
    TrialStateMachine,
    TrialState,
    TrialEvent,
    TrialTransitionCode,
)


class TestTrialStateMachineValidTransitions:
    """Testa transições válidas"""

    def test_preparado_to_ativo(self):
        """PREPARADO → ATIVO via trial_start"""
        result = TrialStateMachine.transition(
            TrialState.PREPARADO, TrialEvent.TRIAL_START
        )
        assert result.success
        assert result.current_state == TrialState.ATIVO
        assert result.previous_state == TrialState.PREPARADO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_ativo_to_expirado(self):
        """ATIVO → EXPIRADO via trial_expires"""
        result = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.TRIAL_EXPIRES
        )
        assert result.success
        assert result.current_state == TrialState.EXPIRADO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_ativo_to_cancelado(self):
        """ATIVO → CANCELADO via lead_cancels"""
        result = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.LEAD_CANCELS
        )
        assert result.success
        assert result.current_state == TrialState.CANCELADO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_ativo_to_convertido(self):
        """ATIVO → CONVERTIDO via lead_pays"""
        result = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.LEAD_PAYS
        )
        assert result.success
        assert result.current_state == TrialState.CONVERTIDO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_expirado_to_convertido(self):
        """EXPIRADO → CONVERTIDO via lead_pays"""
        result = TrialStateMachine.transition(
            TrialState.EXPIRADO, TrialEvent.LEAD_PAYS
        )
        assert result.success
        assert result.current_state == TrialState.CONVERTIDO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_expirado_to_cancelado(self):
        """EXPIRADO → CANCELADO via lead_cancels"""
        result = TrialStateMachine.transition(
            TrialState.EXPIRADO, TrialEvent.LEAD_CANCELS
        )
        assert result.success
        assert result.current_state == TrialState.CANCELADO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_expirado_to_deletado(self):
        """EXPIRADO → DELETADO via timeout_reactivation"""
        result = TrialStateMachine.transition(
            TrialState.EXPIRADO, TrialEvent.TIMEOUT_REACTIVATION
        )
        assert result.success
        assert result.current_state == TrialState.DELETADO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_expirado_to_ativo_reactivate(self):
        """EXPIRADO → ATIVO via reactivate (janela de reativação)"""
        result = TrialStateMachine.transition(
            TrialState.EXPIRADO, TrialEvent.REACTIVATE
        )
        assert result.success
        assert result.current_state == TrialState.ATIVO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_cancelado_to_deletado(self):
        """CANCELADO → DELETADO via timeout_reactivation"""
        result = TrialStateMachine.transition(
            TrialState.CANCELADO, TrialEvent.TIMEOUT_REACTIVATION
        )
        assert result.success
        assert result.current_state == TrialState.DELETADO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_cancelado_to_ativo_reactivate(self):
        """CANCELADO → ATIVO via reactivate"""
        result = TrialStateMachine.transition(
            TrialState.CANCELADO, TrialEvent.REACTIVATE
        )
        assert result.success
        assert result.current_state == TrialState.ATIVO
        assert result.code == TrialTransitionCode.SUCCESS

    def test_cancelado_to_convertido(self):
        """CANCELADO → CONVERTIDO via lead_pays"""
        result = TrialStateMachine.transition(
            TrialState.CANCELADO, TrialEvent.LEAD_PAYS
        )
        assert result.success
        assert result.current_state == TrialState.CONVERTIDO
        assert result.code == TrialTransitionCode.SUCCESS


class TestTrialStateMachineInvalidTransitions:
    """Testa transições inválidas"""

    def test_preparado_invalid_transitions(self):
        """PREPARADO não pode fazer transições não permitidas"""
        invalid_events = [
            TrialEvent.TRIAL_EXPIRES,
            TrialEvent.LEAD_CANCELS,
            TrialEvent.LEAD_PAYS,
            TrialEvent.TIMEOUT_REACTIVATION,
            TrialEvent.REACTIVATE,
        ]
        for event in invalid_events:
            result = TrialStateMachine.transition(TrialState.PREPARADO, event)
            assert not result.success, f"PREPARADO → {event} deveria falhar"
            assert (
                result.code == TrialTransitionCode.INVALID_TRANSITION
            ), f"Código errado para {event}"

    def test_ativo_invalid_transitions(self):
        """ATIVO não pode fazer transições não permitidas"""
        invalid_events = [
            TrialEvent.TIMEOUT_REACTIVATION,
            TrialEvent.REACTIVATE,
            TrialEvent.TRIAL_START,
        ]
        for event in invalid_events:
            result = TrialStateMachine.transition(TrialState.ATIVO, event)
            assert not result.success

    def test_convertido_terminal(self):
        """CONVERTIDO é terminal, nenhuma transição"""
        events = [
            TrialEvent.TRIAL_START,
            TrialEvent.TRIAL_EXPIRES,
            TrialEvent.LEAD_CANCELS,
            TrialEvent.LEAD_PAYS,
            TrialEvent.TIMEOUT_REACTIVATION,
            TrialEvent.REACTIVATE,
        ]
        for event in events:
            result = TrialStateMachine.transition(TrialState.CONVERTIDO, event)
            assert not result.success
            assert result.code == TrialTransitionCode.TERMINAL_STATE

    def test_deletado_terminal(self):
        """DELETADO é terminal"""
        events = [
            TrialEvent.TRIAL_START,
            TrialEvent.TRIAL_EXPIRES,
            TrialEvent.LEAD_CANCELS,
            TrialEvent.LEAD_PAYS,
            TrialEvent.TIMEOUT_REACTIVATION,
            TrialEvent.REACTIVATE,
        ]
        for event in events:
            result = TrialStateMachine.transition(TrialState.DELETADO, event)
            assert not result.success
            assert result.code == TrialTransitionCode.TERMINAL_STATE


class TestTrialStateMachineUnknownInputs:
    """Testa tratamento de entrada inválida"""

    def test_unknown_state(self):
        """Estado inválido é rejeitado"""
        invalid_state = "INVALID_STATE"  # type: ignore
        result = TrialStateMachine.transition(invalid_state, TrialEvent.TRIAL_START)
        assert not result.success
        assert result.code == TrialTransitionCode.UNKNOWN_STATE

    def test_unknown_event(self):
        """Evento inválido é rejeitado"""
        invalid_event = "invalid_event"  # type: ignore
        result = TrialStateMachine.transition(TrialState.PREPARADO, invalid_event)
        assert not result.success
        assert result.code == TrialTransitionCode.INVALID_EVENT


class TestTrialStateMachineIdempotency:
    """Testa idempotência e repetição de eventos"""

    def test_same_event_twice_in_ativo(self):
        """Repetir trial_expires duas vezes falha na segunda"""
        result1 = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.TRIAL_EXPIRES
        )
        assert result1.success
        assert result1.current_state == TrialState.EXPIRADO

        # Tentar de novo em EXPIRADO
        result2 = TrialStateMachine.transition(
            TrialState.EXPIRADO, TrialEvent.TRIAL_EXPIRES
        )
        assert not result2.success
        assert result2.code == TrialTransitionCode.INVALID_TRANSITION

    def test_repeat_trial_start_in_preparado(self):
        """Repetir trial_start em PREPARADO falha (já em ATIVO)"""
        result1 = TrialStateMachine.transition(
            TrialState.PREPARADO, TrialEvent.TRIAL_START
        )
        assert result1.success
        assert result1.current_state == TrialState.ATIVO

        # Evento inválido em ATIVO
        result2 = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.TRIAL_START
        )
        assert not result2.success


class TestTrialStateMachineSuggestedEffects:
    """Testa efeitos sugeridos"""

    def test_preparado_to_ativo_effects(self):
        """PREPARADO → ATIVO sugere efeitos"""
        result = TrialStateMachine.transition(
            TrialState.PREPARADO, TrialEvent.TRIAL_START
        )
        assert result.success
        assert "liberar_acesso" in result.suggested_effects
        assert "publicar_evento:trial_iniciado" in result.suggested_effects

    def test_ativo_to_expirado_effects(self):
        """ATIVO → EXPIRADO sugere efeitos"""
        result = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.TRIAL_EXPIRES
        )
        assert result.success
        assert "restringir_acesso" in result.suggested_effects
        assert "publicar_evento:trial_expirado" in result.suggested_effects
        assert "iniciar_timer_reativacao" in result.suggested_effects

    def test_ativo_to_convertido_effects(self):
        """ATIVO → CONVERTIDO sugere criar_assinatura"""
        result = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.LEAD_PAYS
        )
        assert result.success
        assert "criar_assinatura" in result.suggested_effects

    def test_expirado_to_deletado_effects(self):
        """EXPIRADO → DELETADO sugere cancelar timer"""
        result = TrialStateMachine.transition(
            TrialState.EXPIRADO, TrialEvent.TIMEOUT_REACTIVATION
        )
        assert result.success
        assert "cancelar_timer_reativacao" in result.suggested_effects


class TestTrialStateMachineHelpers:
    """Testa funções auxiliares"""

    def test_get_valid_next_events_preparado(self):
        """Válidos de PREPARADO"""
        events = TrialStateMachine.get_valid_next_events(TrialState.PREPARADO)
        assert TrialEvent.TRIAL_START in events
        assert len(events) == 1

    def test_get_valid_next_events_ativo(self):
        """Válidos de ATIVO"""
        events = TrialStateMachine.get_valid_next_events(TrialState.ATIVO)
        assert TrialEvent.TRIAL_EXPIRES in events
        assert TrialEvent.LEAD_CANCELS in events
        assert TrialEvent.LEAD_PAYS in events
        assert len(events) == 3

    def test_get_valid_next_events_convertido(self):
        """CONVERTIDO terminal, sem eventos"""
        events = TrialStateMachine.get_valid_next_events(TrialState.CONVERTIDO)
        assert len(events) == 0

    def test_get_valid_next_events_deletado(self):
        """DELETADO terminal, sem eventos"""
        events = TrialStateMachine.get_valid_next_events(TrialState.DELETADO)
        assert len(events) == 0

    def test_is_terminal(self):
        """Verifica estados terminais"""
        assert TrialStateMachine.is_terminal(TrialState.CONVERTIDO)
        assert TrialStateMachine.is_terminal(TrialState.DELETADO)
        assert not TrialStateMachine.is_terminal(TrialState.ATIVO)
        assert not TrialStateMachine.is_terminal(TrialState.EXPIRADO)

    def test_validate_state(self):
        """Valida estados conhecidos"""
        assert TrialStateMachine.validate_state(TrialState.ATIVO)
        assert TrialStateMachine.validate_state(TrialState.PREPARADO)
        assert not TrialStateMachine.validate_state("INVALID")


class TestTrialStateMachineDeterminism:
    """Testa determinismo"""

    def test_same_input_same_output(self):
        """Mesma entrada = mesma saída"""
        result1 = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.TRIAL_EXPIRES
        )
        result2 = TrialStateMachine.transition(
            TrialState.ATIVO, TrialEvent.TRIAL_EXPIRES
        )

        assert result1.success == result2.success
        assert result1.current_state == result2.current_state
        assert result1.code == result2.code
        assert result1.suggested_effects == result2.suggested_effects

    def test_no_side_effects(self):
        """Transição não altera estado global"""
        state_before = TrialState.ATIVO
        result = TrialStateMachine.transition(state_before, TrialEvent.TRIAL_EXPIRES)
        assert state_before == TrialState.ATIVO  # state_before não mudou
        assert result.previous_state == TrialState.ATIVO
        assert result.current_state == TrialState.EXPIRADO


class TestTrialStateMachineOutOfOrder:
    """Testa cenários fora de ordem"""

    def test_expirado_without_ativo(self):
        """Não pode ir direto de PREPARADO para EXPIRADO"""
        result = TrialStateMachine.transition(
            TrialState.PREPARADO, TrialEvent.TRIAL_EXPIRES
        )
        assert not result.success
        assert result.code == TrialTransitionCode.INVALID_TRANSITION

    def test_convertido_without_ativo(self):
        """Não pode ir direto de PREPARADO para CONVERTIDO"""
        result = TrialStateMachine.transition(
            TrialState.PREPARADO, TrialEvent.LEAD_PAYS
        )
        assert not result.success
        assert result.code == TrialTransitionCode.INVALID_TRANSITION


class TestTrialStateMachinePreservesInput:
    """Testa que não há mutação de entrada"""

    def test_state_enum_not_mutated(self):
        """TrialState enum não é alterado"""
        state = TrialState.ATIVO
        original_value = state.value
        TrialStateMachine.transition(state, TrialEvent.TRIAL_EXPIRES)
        assert state.value == original_value
        assert state == TrialState.ATIVO


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
