"""
TRIAL STATE MACHINE — Máquina de estados pura para Trial

Fonte: CONTRATO_TRIAL_NEOEVE.md V1.2 § 1, CONTRATO_BILLING_NEOEVE.md V1.1 § 1.2

Estados: PREPARADO, ATIVO, EXPIRADO, CONVERTIDO, CANCELADO, DELETADO

Nota: Esta é uma máquina de estado PURA:
- Sem efeitos colaterais
- Sem persistência
- Sem chamadas de rede
- Sem mutação de entrada
- Determinística
- Isolada

Transições orquestradas por BillingDomainService (Fase 3)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class TrialState(str, Enum):
    """Estados do Trial conforme contrato"""
    PREPARADO = "PREPARADO"
    ATIVO = "ATIVO"
    EXPIRADO = "EXPIRADO"
    CONVERTIDO = "CONVERTIDO"
    CANCELADO = "CANCELADO"
    DELETADO = "DELETADO"


class TrialEvent(str, Enum):
    """Eventos que causam transições"""
    TRIAL_START = "trial_start"  # Onboarding completo
    TRIAL_EXPIRES = "trial_expires"  # Período expirou
    LEAD_CANCELS = "lead_cancels"  # Lead cancelou
    LEAD_PAYS = "lead_pays"  # Lead efetuou pagamento
    TIMEOUT_REACTIVATION = "timeout_reactivation"  # Expirou janela de reativação
    REACTIVATE = "reactivate"  # Lead reativou (voltar de EXPIRADO/CANCELADO)


class TrialTransitionCode(str, Enum):
    """Códigos de resultado de transição"""
    SUCCESS = "trial_transition_success"
    ALREADY_IN_STATE = "trial_already_in_state"
    INVALID_TRANSITION = "trial_invalid_transition"
    INVALID_STATE = "trial_invalid_state"
    INVALID_EVENT = "trial_invalid_event"
    UNKNOWN_STATE = "trial_unknown_state"
    TERMINAL_STATE = "trial_terminal_state"


@dataclass
class TrialTransitionResult:
    """Resultado de uma transição de estado no Trial"""
    success: bool
    code: TrialTransitionCode
    previous_state: TrialState
    current_state: TrialState
    event: TrialEvent
    reason: str
    suggested_effects: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"TrialTransitionResult("
            f"success={self.success}, "
            f"code={self.code.value}, "
            f"{self.previous_state.value} --{self.event.value}--> {self.current_state.value})"
        )


class TrialStateMachine:
    """
    Máquina de estados para Trial.

    Responsabilidades:
    - Validar transições permitidas
    - Retornar novo estado ou falha
    - Sugerir efeitos (não executar)
    - Ser determinística

    NÃO pode:
    - Mutar entrada
    - Chamar Firestore
    - Acessar relógio global
    - Criar side effects
    - Alterar outra máquina
    """

    # Transições permitidas: estado_atual -> {eventos: novo_estado}
    TRANSITIONS = {
        TrialState.PREPARADO: {
            TrialEvent.TRIAL_START: TrialState.ATIVO,
        },
        TrialState.ATIVO: {
            TrialEvent.TRIAL_EXPIRES: TrialState.EXPIRADO,
            TrialEvent.LEAD_CANCELS: TrialState.CANCELADO,
            TrialEvent.LEAD_PAYS: TrialState.CONVERTIDO,
        },
        TrialState.EXPIRADO: {
            TrialEvent.LEAD_PAYS: TrialState.CONVERTIDO,
            TrialEvent.LEAD_CANCELS: TrialState.CANCELADO,
            TrialEvent.TIMEOUT_REACTIVATION: TrialState.DELETADO,
            TrialEvent.REACTIVATE: TrialState.ATIVO,  # Reativar durante janela
        },
        TrialState.CANCELADO: {
            TrialEvent.TIMEOUT_REACTIVATION: TrialState.DELETADO,
            TrialEvent.REACTIVATE: TrialState.ATIVO,  # Reativar durante janela
            TrialEvent.LEAD_PAYS: TrialState.CONVERTIDO,  # Pagar mesmo cancelado
        },
        # CONVERTIDO é terminal
        # DELETADO é terminal
    }

    # Estados terminais (sem transições)
    TERMINAL_STATES = {TrialState.CONVERTIDO, TrialState.DELETADO}

    # Estados válidos
    VALID_STATES = set(TrialState)

    @staticmethod
    def transition(
        current_state: TrialState,
        event: TrialEvent,
        correlation_id: Optional[str] = None,
    ) -> TrialTransitionResult:
        """
        Processa uma transição de estado.

        Args:
            current_state: Estado atual do trial
            event: Evento que dispara a transição
            correlation_id: ID opcional para auditoria

        Returns:
            TrialTransitionResult com resultado da transição

        Nota: Não altera nenhum estado global, apenas retorna resultado.
        """
        # Validar estado atual
        if current_state not in TrialStateMachine.VALID_STATES:
            return TrialTransitionResult(
                success=False,
                code=TrialTransitionCode.UNKNOWN_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado desconhecido: {current_state}",
            )

        # Validar evento
        if event not in TrialEvent:
            return TrialTransitionResult(
                success=False,
                code=TrialTransitionCode.INVALID_EVENT,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Evento desconhecido: {event}",
            )

        # Verificar se estado é terminal
        if current_state in TrialStateMachine.TERMINAL_STATES:
            return TrialTransitionResult(
                success=False,
                code=TrialTransitionCode.TERMINAL_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado {current_state.value} é terminal",
            )

        # Procurar transição permitida
        if current_state not in TrialStateMachine.TRANSITIONS:
            return TrialTransitionResult(
                success=False,
                code=TrialTransitionCode.INVALID_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Nenhuma transição definida para estado {current_state.value}",
            )

        valid_events = TrialStateMachine.TRANSITIONS[current_state]
        if event not in valid_events:
            valid_event_names = [e.value for e in valid_events.keys()]
            return TrialTransitionResult(
                success=False,
                code=TrialTransitionCode.INVALID_TRANSITION,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=(
                    f"Transição não permitida: {current_state.value} "
                    f"--{event.value}--> (inválida). "
                    f"Eventos válidos: {', '.join(valid_event_names)}"
                ),
            )

        # Transição válida
        next_state = valid_events[event]

        # Determinar efeitos sugeridos
        suggested_effects = TrialStateMachine._suggest_effects(
            current_state, next_state, event
        )

        return TrialTransitionResult(
            success=True,
            code=TrialTransitionCode.SUCCESS,
            previous_state=current_state,
            current_state=next_state,
            event=event,
            reason=f"Transição permitida: {current_state.value} → {next_state.value}",
            suggested_effects=suggested_effects,
        )

    @staticmethod
    def _suggest_effects(
        previous_state: TrialState,
        next_state: TrialState,
        event: TrialEvent,
    ) -> List[str]:
        """
        Sugere efeitos de domínio para a transição.

        Efeitos são DADOS, não são EXECUTADOS.
        Será responsabilidade de BillingDomainService (Fase 3) executar.

        Efeitos sugeridos:
        - liberar_acesso: Lead pode usar plataforma
        - restringir_acesso: Lead não pode usar
        - iniciar_retencao: Dados em retenção
        - publicar_evento_trial: Publicar para event bus
        - iniciar_timer_reativacao: Timer para reativação
        """
        effects = []

        if previous_state == TrialState.PREPARADO and next_state == TrialState.ATIVO:
            effects.append("liberar_acesso")
            effects.append("publicar_evento:trial_iniciado")

        elif previous_state == TrialState.ATIVO and next_state == TrialState.EXPIRADO:
            effects.append("restringir_acesso")
            effects.append("publicar_evento:trial_expirado")
            effects.append("iniciar_timer_reativacao")
            effects.append("iniciar_retencao")

        elif previous_state == TrialState.ATIVO and next_state == TrialState.CONVERTIDO:
            effects.append("publicar_evento:trial_convertido")
            effects.append("criar_assinatura")

        elif previous_state == TrialState.ATIVO and next_state == TrialState.CANCELADO:
            effects.append("restringir_acesso")
            effects.append("publicar_evento:trial_cancelado")
            effects.append("iniciar_timer_reativacao")
            effects.append("iniciar_retencao")

        elif previous_state == TrialState.EXPIRADO and next_state == TrialState.CONVERTIDO:
            effects.append("publicar_evento:trial_reativado_e_convertido")
            effects.append("criar_assinatura")
            effects.append("liberar_acesso")

        elif previous_state == TrialState.EXPIRADO and next_state == TrialState.DELETADO:
            effects.append("publicar_evento:trial_dados_deletados")
            effects.append("cancelar_timer_reativacao")

        elif previous_state == TrialState.CANCELADO and next_state == TrialState.DELETADO:
            effects.append("publicar_evento:trial_dados_deletados")
            effects.append("cancelar_timer_reativacao")

        elif previous_state == TrialState.EXPIRADO and next_state == TrialState.ATIVO:
            effects.append("liberar_acesso")
            effects.append("publicar_evento:trial_reativado")
            effects.append("cancelar_timer_reativacao")

        elif previous_state == TrialState.CANCELADO and next_state == TrialState.ATIVO:
            effects.append("liberar_acesso")
            effects.append("publicar_evento:trial_reativado")
            effects.append("cancelar_timer_reativacao")

        elif previous_state == TrialState.CANCELADO and next_state == TrialState.CONVERTIDO:
            effects.append("publicar_evento:trial_cancelado_e_convertido")
            effects.append("criar_assinatura")
            effects.append("liberar_acesso")
            effects.append("cancelar_timer_reativacao")

        return effects

    @staticmethod
    def get_valid_next_events(current_state: TrialState) -> List[TrialEvent]:
        """
        Retorna lista de eventos válidos para o estado atual.

        Útil para validação de entrada em camadas superiores.
        """
        if current_state in TrialStateMachine.TRANSITIONS:
            return list(TrialStateMachine.TRANSITIONS[current_state].keys())
        return []

    @staticmethod
    def is_terminal(state: TrialState) -> bool:
        """Verifica se estado é terminal (sem transições possíveis)"""
        return state in TrialStateMachine.TERMINAL_STATES

    @staticmethod
    def validate_state(state: TrialState) -> bool:
        """Valida se estado é conhecido"""
        return state in TrialStateMachine.VALID_STATES
