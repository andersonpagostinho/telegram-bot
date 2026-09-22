"""
BILLING STATE MACHINES — 4 Máquinas de estado independentes para Billing

Fonte: CONTRATO_BILLING_NEOEVE.md V1.1 § 1.2

Máquinas:
1. MaquinaEstadoAssinatura (PENDENTE, ATIVA, CANCELAMENTO_AGENDADO, CANCELADA, ENCERRADA)
2. MaquinaEstadoPagamento (PENDENTE, APROVADO, RECUSADO, ATRASADO, REEMBOLSADO, CONTESTADO, RESOLVIDO)
3. MaquinaEstadoAcesso (LIBERADO, RESTRITO, SUSPENSO, ENCERRADO)
4. MaquinaEstadoRetencaoDados (ATIVO, EM_RETENCAO, ELEGIVEL_EXCLUSAO, EXCLUIDO)

Nota: Máquinas PURAS:
- Sem efeitos colaterais
- Sem persistência
- Sem chamadas de rede
- Sem mutação de entrada
- Determinísticas
- Isoladas entre si

Efeitos sugeridos, não executados. Será responsabilidade de BillingDomainService (Fase 3).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Set
from abc import ABC, abstractmethod


# ============================================================================
# MÁQUINA 1: ASSINATURA
# ============================================================================


class AssinaturaState(str, Enum):
    """Estados da Assinatura conforme contrato"""
    PENDENTE = "PENDENTE"
    ATIVA = "ATIVA"
    CANCELAMENTO_AGENDADO = "CANCELAMENTO_AGENDADO"
    CANCELADA = "CANCELADA"
    ENCERRADA = "ENCERRADA"


class AssinaturaEvent(str, Enum):
    """Eventos que causam transições"""
    PAYMENT_APPROVED = "payment_approved"  # Webhook: pagamento aprovado
    LEAD_CANCELS = "lead_cancels"  # Lead solicitou cancelamento
    LEAD_REACTIVATES = "lead_reactivates"  # Lead descancelou
    CYCLE_END = "cycle_end"  # Fim do ciclo pago
    DATA_DELETION = "data_deletion_executed"  # Dados deletados


class AssinaturaTransitionCode(str, Enum):
    """Códigos de resultado"""
    SUCCESS = "assinatura_transition_success"
    INVALID_TRANSITION = "assinatura_invalid_transition"
    INVALID_STATE = "assinatura_invalid_state"
    INVALID_EVENT = "assinatura_invalid_event"
    TERMINAL_STATE = "assinatura_terminal_state"
    UNKNOWN_STATE = "assinatura_unknown_state"


@dataclass
class AssinaturaTransitionResult:
    """Resultado de transição de Assinatura"""
    success: bool
    code: AssinaturaTransitionCode
    previous_state: AssinaturaState
    current_state: AssinaturaState
    event: AssinaturaEvent
    reason: str
    suggested_effects: List[str] = field(default_factory=list)


class MaquinaEstadoAssinatura:
    """Máquina de estado da Assinatura"""

    TRANSITIONS = {
        AssinaturaState.PENDENTE: {
            AssinaturaEvent.PAYMENT_APPROVED: AssinaturaState.ATIVA,
        },
        AssinaturaState.ATIVA: {
            AssinaturaEvent.LEAD_CANCELS: AssinaturaState.CANCELAMENTO_AGENDADO,
        },
        AssinaturaState.CANCELAMENTO_AGENDADO: {
            AssinaturaEvent.LEAD_REACTIVATES: AssinaturaState.ATIVA,
            AssinaturaEvent.CYCLE_END: AssinaturaState.CANCELADA,
        },
        AssinaturaState.CANCELADA: {
            AssinaturaEvent.DATA_DELETION: AssinaturaState.ENCERRADA,
        },
    }

    TERMINAL_STATES = {AssinaturaState.ENCERRADA}
    VALID_STATES = set(AssinaturaState)

    @staticmethod
    def transition(
        current_state: AssinaturaState,
        event: AssinaturaEvent,
    ) -> AssinaturaTransitionResult:
        """Processa transição de Assinatura"""
        if current_state not in MaquinaEstadoAssinatura.VALID_STATES:
            return AssinaturaTransitionResult(
                success=False,
                code=AssinaturaTransitionCode.UNKNOWN_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado desconhecido: {current_state}",
            )

        if current_state in MaquinaEstadoAssinatura.TERMINAL_STATES:
            return AssinaturaTransitionResult(
                success=False,
                code=AssinaturaTransitionCode.TERMINAL_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado {current_state.value} é terminal",
            )

        if current_state not in MaquinaEstadoAssinatura.TRANSITIONS:
            return AssinaturaTransitionResult(
                success=False,
                code=AssinaturaTransitionCode.INVALID_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Nenhuma transição definida para {current_state.value}",
            )

        valid_events = MaquinaEstadoAssinatura.TRANSITIONS[current_state]
        if event not in valid_events:
            valid_names = [e.value for e in valid_events.keys()]
            return AssinaturaTransitionResult(
                success=False,
                code=AssinaturaTransitionCode.INVALID_TRANSITION,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=(
                    f"Transição inválida: {current_state.value} "
                    f"--{event.value}-->. Válidos: {', '.join(valid_names)}"
                ),
            )

        next_state = valid_events[event]
        effects = MaquinaEstadoAssinatura._suggest_effects(
            current_state, next_state, event
        )

        return AssinaturaTransitionResult(
            success=True,
            code=AssinaturaTransitionCode.SUCCESS,
            previous_state=current_state,
            current_state=next_state,
            event=event,
            reason=f"{current_state.value} → {next_state.value}",
            suggested_effects=effects,
        )

    @staticmethod
    def _suggest_effects(
        previous: AssinaturaState, next_state: AssinaturaState, event: AssinaturaEvent
    ) -> List[str]:
        """Sugere efeitos de domínio"""
        effects = []

        if previous == AssinaturaState.PENDENTE and next_state == AssinaturaState.ATIVA:
            effects.append("publicar_evento:assinatura_ativada")
            effects.append("iniciar_timer_renovacao")

        elif previous == AssinaturaState.ATIVA and next_state == AssinaturaState.CANCELAMENTO_AGENDADO:
            effects.append("publicar_evento:cancelamento_agendado")
            effects.append("manter_acesso_ate_fim_ciclo")

        elif previous == AssinaturaState.CANCELAMENTO_AGENDADO and next_state == AssinaturaState.ATIVA:
            effects.append("publicar_evento:cancelamento_revertido")
            effects.append("manter_acesso")

        elif previous == AssinaturaState.CANCELAMENTO_AGENDADO and next_state == AssinaturaState.CANCELADA:
            effects.append("publicar_evento:assinatura_cancelada")
            effects.append("cancelar_timer_renovacao")

        elif previous == AssinaturaState.CANCELADA and next_state == AssinaturaState.ENCERRADA:
            effects.append("publicar_evento:assinatura_encerrada")
            effects.append("iniciar_retencao_dados")

        return effects

    @staticmethod
    def get_valid_next_events(current_state: AssinaturaState) -> List[AssinaturaEvent]:
        """Retorna eventos válidos para o estado"""
        if current_state in MaquinaEstadoAssinatura.TRANSITIONS:
            return list(MaquinaEstadoAssinatura.TRANSITIONS[current_state].keys())
        return []

    @staticmethod
    def is_terminal(state: AssinaturaState) -> bool:
        """Verifica se terminal"""
        return state in MaquinaEstadoAssinatura.TERMINAL_STATES


# ============================================================================
# MÁQUINA 2: PAGAMENTO
# ============================================================================


class PagamentoState(str, Enum):
    """Estados de Pagamento conforme contrato"""
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    ATRASADO = "ATRASADO"
    REEMBOLSADO = "REEMBOLSADO"
    CONTESTADO = "CONTESTADO"
    RESOLVIDO = "RESOLVIDO"


class PagamentoEvent(str, Enum):
    """Eventos de Pagamento"""
    PAYMENT_APPROVED = "payment_approved"  # Cartão aprovado
    PAYMENT_FAILED = "payment_failed"  # Cartão recusado
    PAYMENT_DELAYED = "payment_delayed"  # Atrasado (ex: boleto não compensou)
    RETRY_APPROVED = "retry_approved"  # Retry bem-sucedido
    RETRY_FAILED = "retry_failed"  # Retries exauridos
    REFUND_REQUESTED = "refund_requested"  # Reembolso solicitado
    CHARGEBACK_OPENED = "chargeback_opened"  # Chargeback iniciado
    CHARGEBACK_RESOLVED = "chargeback_resolved"  # Chargeback resolvido


class PagamentoTransitionCode(str, Enum):
    """Códigos de resultado"""
    SUCCESS = "pagamento_transition_success"
    INVALID_TRANSITION = "pagamento_invalid_transition"
    INVALID_STATE = "pagamento_invalid_state"
    INVALID_EVENT = "pagamento_invalid_event"
    TERMINAL_STATE = "pagamento_terminal_state"
    UNKNOWN_STATE = "pagamento_unknown_state"


@dataclass
class PagamentoTransitionResult:
    """Resultado de transição de Pagamento"""
    success: bool
    code: PagamentoTransitionCode
    previous_state: PagamentoState
    current_state: PagamentoState
    event: PagamentoEvent
    reason: str
    suggested_effects: List[str] = field(default_factory=list)


class MaquinaEstadoPagamento:
    """Máquina de estado de Pagamento"""

    TRANSITIONS = {
        PagamentoState.PENDENTE: {
            PagamentoEvent.PAYMENT_APPROVED: PagamentoState.APROVADO,
            PagamentoEvent.PAYMENT_FAILED: PagamentoState.RECUSADO,
            PagamentoEvent.PAYMENT_DELAYED: PagamentoState.ATRASADO,
        },
        PagamentoState.RECUSADO: {
            PagamentoEvent.RETRY_APPROVED: PagamentoState.APROVADO,
        },
        PagamentoState.ATRASADO: {
            PagamentoEvent.PAYMENT_APPROVED: PagamentoState.APROVADO,
            PagamentoEvent.RETRY_FAILED: PagamentoState.RECUSADO,
        },
        PagamentoState.APROVADO: {
            PagamentoEvent.REFUND_REQUESTED: PagamentoState.REEMBOLSADO,
            PagamentoEvent.CHARGEBACK_OPENED: PagamentoState.CONTESTADO,
        },
        PagamentoState.REEMBOLSADO: {
            PagamentoEvent.CHARGEBACK_OPENED: PagamentoState.CONTESTADO,
        },
        PagamentoState.CONTESTADO: {
            PagamentoEvent.CHARGEBACK_RESOLVED: PagamentoState.RESOLVIDO,
        },
    }

    TERMINAL_STATES = {PagamentoState.RESOLVIDO, PagamentoState.REEMBOLSADO}
    VALID_STATES = set(PagamentoState)

    @staticmethod
    def transition(
        current_state: PagamentoState,
        event: PagamentoEvent,
    ) -> PagamentoTransitionResult:
        """Processa transição de Pagamento"""
        if current_state not in MaquinaEstadoPagamento.VALID_STATES:
            return PagamentoTransitionResult(
                success=False,
                code=PagamentoTransitionCode.UNKNOWN_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado desconhecido: {current_state}",
            )

        if current_state in MaquinaEstadoPagamento.TERMINAL_STATES:
            return PagamentoTransitionResult(
                success=False,
                code=PagamentoTransitionCode.TERMINAL_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado {current_state.value} é terminal",
            )

        if current_state not in MaquinaEstadoPagamento.TRANSITIONS:
            return PagamentoTransitionResult(
                success=False,
                code=PagamentoTransitionCode.INVALID_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Nenhuma transição definida para {current_state.value}",
            )

        valid_events = MaquinaEstadoPagamento.TRANSITIONS[current_state]
        if event not in valid_events:
            valid_names = [e.value for e in valid_events.keys()]
            return PagamentoTransitionResult(
                success=False,
                code=PagamentoTransitionCode.INVALID_TRANSITION,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=(
                    f"Transição inválida: {current_state.value} "
                    f"--{event.value}-->. Válidos: {', '.join(valid_names)}"
                ),
            )

        next_state = valid_events[event]
        effects = MaquinaEstadoPagamento._suggest_effects(
            current_state, next_state, event
        )

        return PagamentoTransitionResult(
            success=True,
            code=PagamentoTransitionCode.SUCCESS,
            previous_state=current_state,
            current_state=next_state,
            event=event,
            reason=f"{current_state.value} → {next_state.value}",
            suggested_effects=effects,
        )

    @staticmethod
    def _suggest_effects(
        previous: PagamentoState, next_state: PagamentoState, event: PagamentoEvent
    ) -> List[str]:
        """Sugere efeitos de domínio"""
        effects = []

        if next_state == PagamentoState.APROVADO:
            effects.append("liberar_acesso")
            effects.append("publicar_evento:pagamento_aprovado")

        elif next_state == PagamentoState.RECUSADO:
            effects.append("publicar_evento:pagamento_recusado")
            effects.append("iniciar_retry_payment")

        elif next_state == PagamentoState.ATRASADO:
            effects.append("publicar_evento:pagamento_atrasado")

        elif next_state == PagamentoState.REEMBOLSADO:
            effects.append("publicar_evento:pagamento_reembolsado")
            effects.append("enviar_notificacao_reembolso")

        elif next_state == PagamentoState.CONTESTADO:
            effects.append("publicar_evento:chargeback_aberto")

        elif next_state == PagamentoState.RESOLVIDO:
            effects.append("publicar_evento:chargeback_resolvido")

        return effects

    @staticmethod
    def get_valid_next_events(current_state: PagamentoState) -> List[PagamentoEvent]:
        """Retorna eventos válidos"""
        if current_state in MaquinaEstadoPagamento.TRANSITIONS:
            return list(MaquinaEstadoPagamento.TRANSITIONS[current_state].keys())
        return []

    @staticmethod
    def is_terminal(state: PagamentoState) -> bool:
        """Verifica se terminal"""
        return state in MaquinaEstadoPagamento.TERMINAL_STATES


# ============================================================================
# MÁQUINA 3: ACESSO
# ============================================================================


class AcessoState(str, Enum):
    """Estados de Acesso conforme contrato"""
    LIBERADO = "LIBERADO"
    RESTRITO = "RESTRITO"
    SUSPENSO = "SUSPENSO"
    ENCERRADO = "ENCERRADO"


class AcessoEvent(str, Enum):
    """Eventos de Acesso"""
    RESTRICT_ACCESS = "restrict_access"  # Restringir funcionalidade
    PAYMENT_FAILED = "payment_failed"  # Falta de pagamento
    PAYMENT_APPROVED = "payment_approved"  # Pagamento aprovado
    DATA_DELETION = "data_deletion_executed"  # Dados deletados


class AcessoTransitionCode(str, Enum):
    """Códigos de resultado"""
    SUCCESS = "acesso_transition_success"
    INVALID_TRANSITION = "acesso_invalid_transition"
    INVALID_STATE = "acesso_invalid_state"
    INVALID_EVENT = "acesso_invalid_event"
    TERMINAL_STATE = "acesso_terminal_state"
    UNKNOWN_STATE = "acesso_unknown_state"


@dataclass
class AcessoTransitionResult:
    """Resultado de transição de Acesso"""
    success: bool
    code: AcessoTransitionCode
    previous_state: AcessoState
    current_state: AcessoState
    event: AcessoEvent
    reason: str
    suggested_effects: List[str] = field(default_factory=list)


class MaquinaEstadoAcesso:
    """Máquina de estado de Acesso"""

    TRANSITIONS = {
        AcessoState.LIBERADO: {
            AcessoEvent.RESTRICT_ACCESS: AcessoState.RESTRITO,
            AcessoEvent.PAYMENT_FAILED: AcessoState.SUSPENSO,
            AcessoEvent.DATA_DELETION: AcessoState.ENCERRADO,
        },
        AcessoState.RESTRITO: {
            AcessoEvent.PAYMENT_APPROVED: AcessoState.LIBERADO,
            AcessoEvent.RESTRICT_ACCESS: AcessoState.RESTRITO,  # Idempotente
            AcessoEvent.PAYMENT_FAILED: AcessoState.SUSPENSO,
            AcessoEvent.DATA_DELETION: AcessoState.ENCERRADO,
        },
        AcessoState.SUSPENSO: {
            AcessoEvent.PAYMENT_APPROVED: AcessoState.LIBERADO,
            AcessoEvent.DATA_DELETION: AcessoState.ENCERRADO,
        },
    }

    TERMINAL_STATES = {AcessoState.ENCERRADO}
    VALID_STATES = set(AcessoState)

    @staticmethod
    def transition(
        current_state: AcessoState,
        event: AcessoEvent,
    ) -> AcessoTransitionResult:
        """Processa transição de Acesso"""
        if current_state not in MaquinaEstadoAcesso.VALID_STATES:
            return AcessoTransitionResult(
                success=False,
                code=AcessoTransitionCode.UNKNOWN_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado desconhecido: {current_state}",
            )

        if current_state in MaquinaEstadoAcesso.TERMINAL_STATES:
            return AcessoTransitionResult(
                success=False,
                code=AcessoTransitionCode.TERMINAL_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado {current_state.value} é terminal",
            )

        if current_state not in MaquinaEstadoAcesso.TRANSITIONS:
            return AcessoTransitionResult(
                success=False,
                code=AcessoTransitionCode.INVALID_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Nenhuma transição definida para {current_state.value}",
            )

        valid_events = MaquinaEstadoAcesso.TRANSITIONS[current_state]
        if event not in valid_events:
            valid_names = [e.value for e in valid_events.keys()]
            return AcessoTransitionResult(
                success=False,
                code=AcessoTransitionCode.INVALID_TRANSITION,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=(
                    f"Transição inválida: {current_state.value} "
                    f"--{event.value}-->. Válidos: {', '.join(valid_names)}"
                ),
            )

        next_state = valid_events[event]
        effects = MaquinaEstadoAcesso._suggest_effects(
            current_state, next_state, event
        )

        return AcessoTransitionResult(
            success=True,
            code=AcessoTransitionCode.SUCCESS,
            previous_state=current_state,
            current_state=next_state,
            event=event,
            reason=f"{current_state.value} → {next_state.value}",
            suggested_effects=effects,
        )

    @staticmethod
    def _suggest_effects(
        previous: AcessoState, next_state: AcessoState, event: AcessoEvent
    ) -> List[str]:
        """Sugere efeitos de domínio"""
        effects = []

        if next_state == AcessoState.LIBERADO:
            effects.append("liberar_acesso_completo")

        elif next_state == AcessoState.RESTRITO:
            effects.append("restringir_funcionalidade")

        elif next_state == AcessoState.SUSPENSO:
            effects.append("bloquear_acesso")
            effects.append("publicar_evento:acesso_suspenso")

        elif next_state == AcessoState.ENCERRADO:
            effects.append("bloquear_acesso")
            effects.append("publicar_evento:acesso_encerrado")

        return effects

    @staticmethod
    def get_valid_next_events(current_state: AcessoState) -> List[AcessoEvent]:
        """Retorna eventos válidos"""
        if current_state in MaquinaEstadoAcesso.TRANSITIONS:
            return list(MaquinaEstadoAcesso.TRANSITIONS[current_state].keys())
        return []

    @staticmethod
    def is_terminal(state: AcessoState) -> bool:
        """Verifica se terminal"""
        return state in MaquinaEstadoAcesso.TERMINAL_STATES


# ============================================================================
# MÁQUINA 4: RETENÇÃO DE DADOS
# ============================================================================


class RetencaoState(str, Enum):
    """Estados de Retenção conforme contrato"""
    ATIVO = "ATIVO"
    EM_RETENCAO = "EM_RETENCAO"
    ELEGIVEL_EXCLUSAO = "ELEGIVEL_EXCLUSAO"
    EXCLUIDO = "EXCLUIDO"


class RetencaoEvent(str, Enum):
    """Eventos de Retenção"""
    ACESSO_BLOQUEADO = "acesso_bloqueado"  # Acesso passou para ENCERRADO
    RETENTION_PERIOD_EXPIRES = "retention_period_expires"  # Timeout
    DATA_DELETION = "data_deletion_executed"  # Deletar agora
    REATIVACAO_VALIDA = "reativacao_valida"  # Reativar durante retenção


class RetencaoTransitionCode(str, Enum):
    """Códigos de resultado"""
    SUCCESS = "retencao_transition_success"
    INVALID_TRANSITION = "retencao_invalid_transition"
    INVALID_STATE = "retencao_invalid_state"
    INVALID_EVENT = "retencao_invalid_event"
    TERMINAL_STATE = "retencao_terminal_state"
    UNKNOWN_STATE = "retencao_unknown_state"


@dataclass
class RetencaoTransitionResult:
    """Resultado de transição de Retenção"""
    success: bool
    code: RetencaoTransitionCode
    previous_state: RetencaoState
    current_state: RetencaoState
    event: RetencaoEvent
    reason: str
    suggested_effects: List[str] = field(default_factory=list)


class MaquinaEstadoRetencaoDados:
    """Máquina de estado de Retenção de Dados"""

    TRANSITIONS = {
        RetencaoState.ATIVO: {
            RetencaoEvent.ACESSO_BLOQUEADO: RetencaoState.EM_RETENCAO,
        },
        RetencaoState.EM_RETENCAO: {
            RetencaoEvent.RETENTION_PERIOD_EXPIRES: RetencaoState.ELEGIVEL_EXCLUSAO,
            RetencaoEvent.REATIVACAO_VALIDA: RetencaoState.ATIVO,
        },
        RetencaoState.ELEGIVEL_EXCLUSAO: {
            RetencaoEvent.DATA_DELETION: RetencaoState.EXCLUIDO,
        },
    }

    TERMINAL_STATES = {RetencaoState.EXCLUIDO}
    VALID_STATES = set(RetencaoState)

    @staticmethod
    def transition(
        current_state: RetencaoState,
        event: RetencaoEvent,
    ) -> RetencaoTransitionResult:
        """Processa transição de Retenção"""
        if current_state not in MaquinaEstadoRetencaoDados.VALID_STATES:
            return RetencaoTransitionResult(
                success=False,
                code=RetencaoTransitionCode.UNKNOWN_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado desconhecido: {current_state}",
            )

        if current_state in MaquinaEstadoRetencaoDados.TERMINAL_STATES:
            return RetencaoTransitionResult(
                success=False,
                code=RetencaoTransitionCode.TERMINAL_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Estado {current_state.value} é terminal",
            )

        if current_state not in MaquinaEstadoRetencaoDados.TRANSITIONS:
            return RetencaoTransitionResult(
                success=False,
                code=RetencaoTransitionCode.INVALID_STATE,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=f"Nenhuma transição definida para {current_state.value}",
            )

        valid_events = MaquinaEstadoRetencaoDados.TRANSITIONS[current_state]
        if event not in valid_events:
            valid_names = [e.value for e in valid_events.keys()]
            return RetencaoTransitionResult(
                success=False,
                code=RetencaoTransitionCode.INVALID_TRANSITION,
                previous_state=current_state,
                current_state=current_state,
                event=event,
                reason=(
                    f"Transição inválida: {current_state.value} "
                    f"--{event.value}-->. Válidos: {', '.join(valid_names)}"
                ),
            )

        next_state = valid_events[event]
        effects = MaquinaEstadoRetencaoDados._suggest_effects(
            current_state, next_state, event
        )

        return RetencaoTransitionResult(
            success=True,
            code=RetencaoTransitionCode.SUCCESS,
            previous_state=current_state,
            current_state=next_state,
            event=event,
            reason=f"{current_state.value} → {next_state.value}",
            suggested_effects=effects,
        )

    @staticmethod
    def _suggest_effects(
        previous: RetencaoState, next_state: RetencaoState, event: RetencaoEvent
    ) -> List[str]:
        """Sugere efeitos de domínio"""
        effects = []

        if next_state == RetencaoState.EM_RETENCAO:
            effects.append("tornar_dados_inacessiveis")
            effects.append("iniciar_timer_retencao")

        elif next_state == RetencaoState.ELEGIVEL_EXCLUSAO:
            effects.append("publicar_evento:dados_elegivel_exclusao")

        elif next_state == RetencaoState.EXCLUIDO:
            effects.append("deletar_todos_dados_permanentemente")
            effects.append("publicar_evento:dados_excluidos")

        elif next_state == RetencaoState.ATIVO:
            effects.append("restaurar_dados_acessiveis")
            effects.append("cancelar_timer_retencao")

        return effects

    @staticmethod
    def get_valid_next_events(current_state: RetencaoState) -> List[RetencaoEvent]:
        """Retorna eventos válidos"""
        if current_state in MaquinaEstadoRetencaoDados.TRANSITIONS:
            return list(MaquinaEstadoRetencaoDados.TRANSITIONS[current_state].keys())
        return []

    @staticmethod
    def is_terminal(state: RetencaoState) -> bool:
        """Verifica se terminal"""
        return state in MaquinaEstadoRetencaoDados.TERMINAL_STATES
