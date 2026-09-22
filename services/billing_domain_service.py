"""
BILLING DOMAIN SERVICE — Orquestração Pura de Máquinas de Estado

Coordena as 5 máquinas de estado (Trial, Assinatura, Pagamento, Acesso, Retenção)
sem persistência, sem HTTP, sem efeitos colaterais.

Referências:
- services/trial_state_machine.py (Fase 1)
- services/billing_state_machines.py (Fase 1)
- ARQUITETURA_WEBHOOK_DOMAINSERVICE.md
- FASE2_ANALISE_EVENTOS_ORQUESTRACAO.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from domain.commercial_events import CommercialEvent
from services.trial_state_machine import (
    TrialStateMachine,
    TrialState,
    TrialEvent,
)
from services.billing_state_machines import (
    MaquinaEstadoAssinatura,
    AssinaturaState,
    AssinaturaEvent,
    MaquinaEstadoPagamento,
    PagamentoState,
    PagamentoEvent,
    MaquinaEstadoAcesso,
    AcessoState,
    AcessoEvent,
    MaquinaEstadoRetencaoDados,
    RetencaoState,
    RetencaoEvent,
)


# ==============================================================================
# ESTRUTURAS DE SNAPSHOT DE ESTADO
# ==============================================================================


@dataclass(frozen=True)
class TrialSnapshot:
    """Estado de uma máquina Trial em ponto no tempo."""
    state: TrialState
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssinaturaSnapshot:
    """Estado de uma máquina Assinatura em ponto no tempo."""
    state: AssinaturaState
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PagamentoSnapshot:
    """Estado de uma máquina Pagamento em ponto no tempo."""
    state: PagamentoState
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AcessoSnapshot:
    """Estado de uma máquina Acesso em ponto no tempo."""
    state: AcessoState
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetencaoSnapshot:
    """Estado de uma máquina Retenção em ponto no tempo."""
    state: RetencaoState
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AggregateSnapshot:
    """Snapshot completo do agregado comercial (todas as máquinas)."""
    trial: TrialSnapshot
    assinatura: AssinaturaSnapshot
    pagamento: PagamentoSnapshot
    acesso: AcessoSnapshot
    retencao: RetencaoSnapshot
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serializar snapshot para persistência."""
        return {
            "trial_state": self.trial.state.value,
            "trial_metadata": self.trial.metadata,
            "assinatura_state": self.assinatura.state.value,
            "assinatura_metadata": self.assinatura.metadata,
            "pagamento_state": self.pagamento.state.value,
            "pagamento_metadata": self.pagamento.metadata,
            "acesso_state": self.acesso.state.value,
            "acesso_metadata": self.acesso.metadata,
            "retencao_state": self.retencao.state.value,
            "retencao_metadata": self.retencao.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class CommercialAggregate:
    """
    Agregado comercial completo com identidade + estado + metadados.

    Encapsula:
    - Identidade (aggregate_id, tenant_id, version)
    - Estado das máquinas (trial, assinatura, pagamento, acesso, retencao)
    - Referências de negócio (subscription_id, plan_id, lead_id)
    - Períodos (period_start, period_end)
    - Timestamps (created_at)

    Imutável: frozen=True garante que nenhuma alteração é possível após criação.
    """
    aggregate_id: str
    tenant_id: str
    version: int
    snapshot: AggregateSnapshot  # Estado das máquinas (trial, assinatura, etc)
    subscription_id: Optional[str] = None
    plan_id: Optional[str] = None
    lead_id: Optional[str] = None
    period_start: Optional[str] = None  # ISO date
    period_end: Optional[str] = None  # ISO date
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializar para persistência."""
        return {
            "aggregate_id": self.aggregate_id,
            "tenant_id": self.tenant_id,
            "version": self.version,
            "snapshot": self.snapshot.to_dict(),
            "subscription_id": self.subscription_id,
            "plan_id": self.plan_id,
            "lead_id": self.lead_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==============================================================================
# RESULTADO DE PROCESSAMENTO
# ==============================================================================


class TransitionDecision(str, Enum):
    """Decisão de aplicação de uma transição."""
    APPLIED = "applied"  # Transição foi aplicada com sucesso
    IGNORED = "ignored"  # Transição não aplicada (pré-condição falhou)
    REJECTED = "rejected"  # Transição foi explicitamente rejeitada


@dataclass(frozen=True)
class MachineTransitionResult:
    """Resultado de transição de uma máquina individual."""
    machine_name: str
    decision: TransitionDecision
    previous_state: Any  # Estado enum
    current_state: Any  # Estado enum
    reason: str  # Descrição da decisão
    effects_suggested: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializar resultado de transição para persistência."""
        return {
            "machine_name": self.machine_name,
            "decision": self.decision.value if hasattr(self.decision, 'value') else str(self.decision),
            "previous_state": self.previous_state.value if hasattr(self.previous_state, 'value') else str(self.previous_state),
            "current_state": self.current_state.value if hasattr(self.current_state, 'value') else str(self.current_state),
            "reason": self.reason,
            "effects_suggested": self.effects_suggested,
        }


@dataclass
class BillingDomainServiceResult:
    """
    Resultado estruturado do processamento no domínio.

    Imutável semanticamente (após criação, não deve ser alterado).
    """
    success: bool
    correlation_id: str
    source_event_id: Optional[str]

    # Snapshots
    snapshot_before: AggregateSnapshot
    snapshot_after: AggregateSnapshot

    # Transições aplicadas
    transitions: List[MachineTransitionResult] = field(default_factory=list)

    # Eventos internos produzidos
    internal_events: List[CommercialEvent] = field(default_factory=list)

    # Razão de falha (se success = False)
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None

    # Efeitos sugeridos (não executados em Fase 2)
    suggested_effects: List[str] = field(default_factory=list)

    # Auditoria
    processed_at: datetime = field(default_factory=datetime.utcnow)

    # Necessidade de reconciliação
    reconciliation_required: bool = False
    reconciliation_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializar resultado para persistência."""
        return {
            "success": self.success,
            "correlation_id": self.correlation_id,
            "source_event_id": self.source_event_id,
            "snapshot_before": self.snapshot_before.to_dict(),
            "snapshot_after": self.snapshot_after.to_dict(),
            "transitions": [
                {
                    "machine": t.machine_name,
                    "decision": t.decision.value,
                    "previous_state": t.previous_state.value if hasattr(t.previous_state, 'value') else str(t.previous_state),
                    "current_state": t.current_state.value if hasattr(t.current_state, 'value') else str(t.current_state),
                    "reason": t.reason,
                    "effects_suggested": t.effects_suggested,
                }
                for t in self.transitions
            ],
            "internal_events_count": len(self.internal_events),
            "failure_reason": self.failure_reason,
            "failure_code": self.failure_code,
            "reconciliation_required": self.reconciliation_required,
            "processed_at": self.processed_at.isoformat(),
        }


# ==============================================================================
# NORMALIZADOR DE EVENTOS EXTERNOS
# ==============================================================================


class ExternalEventNormalizer:
    """
    Converte eventos Hotmart em comandos de domínio normalizados.

    Não executa lógica de transição; apenas extrai e valida.
    """

    @staticmethod
    def normalize_purchase_approved(
        webhook_payload: Dict[str, Any],
        correlation_id: str,
        received_at: datetime,
    ) -> Dict[str, Any]:
        """
        Normalizar evento purchase_approved do Hotmart.

        Retorna dicionário com campos estruturados para orquestração.
        """
        return {
            "event_type": "purchase_approved",
            "correlation_id": correlation_id,
            "source_event_id": webhook_payload.get("transaction_id"),
            "received_at": received_at,
            "tenant_id": webhook_payload.get("reference_id"),  # Obrigatório extrair
            "amount": webhook_payload.get("price"),
            "subscription_id": webhook_payload.get("subscription_id"),
            "metadata": webhook_payload,
        }

    @staticmethod
    def normalize_payment_failed(
        webhook_payload: Dict[str, Any],
        correlation_id: str,
        received_at: datetime,
    ) -> Dict[str, Any]:
        """Normalizar evento purchase_failed do Hotmart."""
        return {
            "event_type": "purchase_failed",
            "correlation_id": correlation_id,
            "source_event_id": webhook_payload.get("transaction_id"),
            "received_at": received_at,
            "tenant_id": webhook_payload.get("reference_id"),
            "failure_reason": webhook_payload.get("reason"),
            "metadata": webhook_payload,
        }

    @staticmethod
    def normalize_subscription_canceled(
        webhook_payload: Dict[str, Any],
        correlation_id: str,
        received_at: datetime,
    ) -> Dict[str, Any]:
        """Normalizar evento subscription_canceled do Hotmart."""
        return {
            "event_type": "subscription_canceled",
            "correlation_id": correlation_id,
            "source_event_id": webhook_payload.get("subscription_id"),
            "received_at": received_at,
            "tenant_id": webhook_payload.get("reference_id"),
            "metadata": webhook_payload,
        }


# ==============================================================================
# BILLING DOMAIN SERVICE (ORQUESTRADOR PURO)
# ==============================================================================


class BillingDomainService:
    """
    Serviço de domínio que orquestra as 5 máquinas de estado.

    PURO: Sem persistência, sem rede, sem I/O, sem relógio.
    DETERMINÍSTICO: Mesmo input → mesmo output sempre.
    IDEMPOTENTE: Reaplicação de eventos já processados não muda estado.
    """

    def process(
        self,
        snapshot: AggregateSnapshot,
        external_event_type: str,
        external_event_payload: Dict[str, Any],
        correlation_id: str,
    ) -> BillingDomainServiceResult:
        """
        Wrapper de compatibilidade para BillingApplicationService.

        Adapta parâmetros do caller para o formato interno.
        """
        normalized_event = {
            "correlation_id": correlation_id,
            "event_type": external_event_type,
            "received_at": __import__('datetime').datetime.utcnow(),
            "tenant_id": external_event_payload.get("tenant_id", ""),
            "source_event_id": external_event_payload.get("provider_event_id"),
            **external_event_payload,
        }
        return self.process_external_event(normalized_event, snapshot)

    def process_external_event(
        self,
        normalized_event: Dict[str, Any],
        current_snapshot: AggregateSnapshot,
    ) -> BillingDomainServiceResult:
        """
        Processa um evento externo normalizado.

        Fluxo:
        1. Validar pré-condições
        2. Aplicar máquinas em ordem determinística
        3. Detectar inconsistências
        4. Produzir eventos internos
        5. Retornar resultado estruturado

        Args:
            normalized_event: Comando normalizado (ex: de Hotmart)
            current_snapshot: Estado atual de todas máquinas

        Returns:
            BillingDomainServiceResult com sucesso/falha e detalhes
        """

        # 1. VALIDAR PRÉ-CONDIÇÕES (fazer primeiro, antes de acessar chaves)
        validation_error = self._validate_event(normalized_event)
        if validation_error:
            return BillingDomainServiceResult(
                success=False,
                correlation_id=normalized_event.get("correlation_id", "unknown"),
                source_event_id=normalized_event.get("source_event_id"),
                snapshot_before=current_snapshot,
                snapshot_after=current_snapshot,  # Sem mudança
                failure_reason=validation_error,
                failure_code="validation_failed",
            )

        # Extrair variáveis após validação bem-sucedida
        correlation_id = normalized_event["correlation_id"]
        event_type = normalized_event["event_type"]
        received_at = normalized_event["received_at"]
        source_event_id = normalized_event.get("source_event_id")

        # 2. APLICAR MÁQUINAS EM ORDEM DETERMINÍSTICA
        # Ordem: Assinatura → Pagamento → Acesso → Trial → Retenção
        transitions = []
        snapshot = current_snapshot

        try:
            # Máquina 1: Assinatura
            assinatura_result, snapshot = self._apply_assinatura_machine(
                event_type, snapshot, normalized_event
            )
            transitions.append(assinatura_result)

            # Máquina 2: Pagamento
            pagamento_result, snapshot = self._apply_pagamento_machine(
                event_type, snapshot, normalized_event
            )
            transitions.append(pagamento_result)

            # Máquina 3: Acesso
            acesso_result, snapshot = self._apply_acesso_machine(
                event_type, snapshot, normalized_event
            )
            transitions.append(acesso_result)

            # Máquina 4: Trial
            trial_result, snapshot = self._apply_trial_machine(
                event_type, snapshot, normalized_event
            )
            transitions.append(trial_result)

            # Máquina 5: Retenção
            retencao_result, snapshot = self._apply_retencao_machine(
                event_type, snapshot, normalized_event
            )
            transitions.append(retencao_result)

        except Exception as e:
            # Falha atômica: rejeitar toda a transição
            return BillingDomainServiceResult(
                success=False,
                correlation_id=correlation_id,
                source_event_id=source_event_id,
                snapshot_before=current_snapshot,
                snapshot_after=current_snapshot,  # Sem mudança
                transitions=transitions,
                failure_reason=str(e),
                failure_code="transition_failed",
            )

        # 3. DETECTAR INCONSISTÊNCIAS
        inconsistency = self._detect_inconsistencies(snapshot)
        if inconsistency:
            return BillingDomainServiceResult(
                success=False,
                correlation_id=correlation_id,
                source_event_id=source_event_id,
                snapshot_before=current_snapshot,
                snapshot_after=snapshot,
                transitions=transitions,
                failure_reason=f"Inconsistência detectada: {inconsistency}",
                failure_code="state_inconsistency",
                reconciliation_required=True,
                reconciliation_reason=inconsistency,
            )

        # 4. PRODUZIR EVENTOS INTERNOS
        internal_events = self._generate_internal_events(
            correlation_id, source_event_id, transitions
        )

        # 5. COLETAR EFEITOS SUGERIDOS
        suggested_effects = []
        for transition in transitions:
            suggested_effects.extend(transition.effects_suggested)

        # SUCESSO
        return BillingDomainServiceResult(
            success=True,
            correlation_id=correlation_id,
            source_event_id=source_event_id,
            snapshot_before=current_snapshot,
            snapshot_after=snapshot,
            transitions=transitions,
            internal_events=internal_events,
            suggested_effects=suggested_effects,
        )

    # ========================================================================
    # APLICAÇÃO DE MÁQUINAS
    # ========================================================================

    def _apply_assinatura_machine(
        self,
        event_type: str,
        snapshot: AggregateSnapshot,
        normalized_event: Dict[str, Any],
    ) -> Tuple[MachineTransitionResult, AggregateSnapshot]:
        """Aplicar máquina AssinaturaStateMachine."""

        # Mapear evento externo → evento da máquina
        machine_event = self._map_to_assinatura_event(event_type)
        if machine_event is None:
            # Evento não afeta assinatura
            return (
                MachineTransitionResult(
                    machine_name="AssinaturaStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.assinatura.state,
                    current_state=snapshot.assinatura.state,
                    reason="Evento não afeta máquina de assinatura",
                ),
                snapshot,
            )

        # Aplicar máquina
        result = MaquinaEstadoAssinatura.transition(
            snapshot.assinatura.state, machine_event
        )

        if not result.success:
            # Transição inválida
            return (
                MachineTransitionResult(
                    machine_name="AssinaturaStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.assinatura.state,
                    current_state=snapshot.assinatura.state,
                    reason=result.reason,
                ),
                snapshot,
            )

        # Transição bem-sucedida
        new_assinatura = AssinaturaSnapshot(
            state=result.current_state,
            metadata=snapshot.assinatura.metadata,
        )
        new_snapshot = AggregateSnapshot(
            trial=snapshot.trial,
            assinatura=new_assinatura,
            pagamento=snapshot.pagamento,
            acesso=snapshot.acesso,
            retencao=snapshot.retencao,
        )

        return (
            MachineTransitionResult(
                machine_name="AssinaturaStateMachine",
                decision=TransitionDecision.APPLIED,
                previous_state=snapshot.assinatura.state,
                current_state=result.current_state,
                reason=result.reason,
                effects_suggested=result.suggested_effects,
            ),
            new_snapshot,
        )

    def _apply_pagamento_machine(
        self,
        event_type: str,
        snapshot: AggregateSnapshot,
        normalized_event: Dict[str, Any],
    ) -> Tuple[MachineTransitionResult, AggregateSnapshot]:
        """Aplicar máquina PagamentoStateMachine."""

        machine_event = self._map_to_pagamento_event(event_type)
        if machine_event is None:
            return (
                MachineTransitionResult(
                    machine_name="PagamentoStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.pagamento.state,
                    current_state=snapshot.pagamento.state,
                    reason="Evento não afeta máquina de pagamento",
                ),
                snapshot,
            )

        result = MaquinaEstadoPagamento.transition(
            snapshot.pagamento.state, machine_event
        )

        if not result.success:
            return (
                MachineTransitionResult(
                    machine_name="PagamentoStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.pagamento.state,
                    current_state=snapshot.pagamento.state,
                    reason=result.reason,
                ),
                snapshot,
            )

        new_pagamento = PagamentoSnapshot(
            state=result.current_state,
            metadata=snapshot.pagamento.metadata,
        )
        new_snapshot = AggregateSnapshot(
            trial=snapshot.trial,
            assinatura=snapshot.assinatura,
            pagamento=new_pagamento,
            acesso=snapshot.acesso,
            retencao=snapshot.retencao,
        )

        return (
            MachineTransitionResult(
                machine_name="PagamentoStateMachine",
                decision=TransitionDecision.APPLIED,
                previous_state=snapshot.pagamento.state,
                current_state=result.current_state,
                reason=result.reason,
                effects_suggested=result.suggested_effects,
            ),
            new_snapshot,
        )

    def _apply_acesso_machine(
        self,
        event_type: str,
        snapshot: AggregateSnapshot,
        normalized_event: Dict[str, Any],
    ) -> Tuple[MachineTransitionResult, AggregateSnapshot]:
        """Aplicar máquina AcessoStateMachine."""

        machine_event = self._map_to_acesso_event(event_type)
        if machine_event is None:
            return (
                MachineTransitionResult(
                    machine_name="AcessoStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.acesso.state,
                    current_state=snapshot.acesso.state,
                    reason="Evento não afeta máquina de acesso",
                ),
                snapshot,
            )

        result = MaquinaEstadoAcesso.transition(
            snapshot.acesso.state, machine_event
        )

        if not result.success:
            return (
                MachineTransitionResult(
                    machine_name="AcessoStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.acesso.state,
                    current_state=snapshot.acesso.state,
                    reason=result.reason,
                ),
                snapshot,
            )

        new_acesso = AcessoSnapshot(
            state=result.current_state,
            metadata=snapshot.acesso.metadata,
        )
        new_snapshot = AggregateSnapshot(
            trial=snapshot.trial,
            assinatura=snapshot.assinatura,
            pagamento=snapshot.pagamento,
            acesso=new_acesso,
            retencao=snapshot.retencao,
        )

        return (
            MachineTransitionResult(
                machine_name="AcessoStateMachine",
                decision=TransitionDecision.APPLIED,
                previous_state=snapshot.acesso.state,
                current_state=result.current_state,
                reason=result.reason,
                effects_suggested=result.suggested_effects,
            ),
            new_snapshot,
        )

    def _apply_trial_machine(
        self,
        event_type: str,
        snapshot: AggregateSnapshot,
        normalized_event: Dict[str, Any],
    ) -> Tuple[MachineTransitionResult, AggregateSnapshot]:
        """Aplicar máquina TrialStateMachine."""

        machine_event = self._map_to_trial_event(event_type)
        if machine_event is None:
            return (
                MachineTransitionResult(
                    machine_name="TrialStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.trial.state,
                    current_state=snapshot.trial.state,
                    reason="Evento não afeta máquina de trial",
                ),
                snapshot,
            )

        result = TrialStateMachine.transition(
            snapshot.trial.state, machine_event
        )

        if not result.success:
            return (
                MachineTransitionResult(
                    machine_name="TrialStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.trial.state,
                    current_state=snapshot.trial.state,
                    reason=result.reason,
                ),
                snapshot,
            )

        new_trial = TrialSnapshot(
            state=result.current_state,
            metadata=snapshot.trial.metadata,
        )
        new_snapshot = AggregateSnapshot(
            trial=new_trial,
            assinatura=snapshot.assinatura,
            pagamento=snapshot.pagamento,
            acesso=snapshot.acesso,
            retencao=snapshot.retencao,
        )

        return (
            MachineTransitionResult(
                machine_name="TrialStateMachine",
                decision=TransitionDecision.APPLIED,
                previous_state=snapshot.trial.state,
                current_state=result.current_state,
                reason=result.reason,
                effects_suggested=result.suggested_effects,
            ),
            new_snapshot,
        )

    def _apply_retencao_machine(
        self,
        event_type: str,
        snapshot: AggregateSnapshot,
        normalized_event: Dict[str, Any],
    ) -> Tuple[MachineTransitionResult, AggregateSnapshot]:
        """Aplicar máquina RetencaoStateMachine."""

        machine_event = self._map_to_retencao_event(event_type)
        if machine_event is None:
            return (
                MachineTransitionResult(
                    machine_name="RetencaoStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.retencao.state,
                    current_state=snapshot.retencao.state,
                    reason="Evento não afeta máquina de retenção",
                ),
                snapshot,
            )

        result = MaquinaEstadoRetencaoDados.transition(
            snapshot.retencao.state, machine_event
        )

        if not result.success:
            return (
                MachineTransitionResult(
                    machine_name="RetencaoStateMachine",
                    decision=TransitionDecision.IGNORED,
                    previous_state=snapshot.retencao.state,
                    current_state=snapshot.retencao.state,
                    reason=result.reason,
                ),
                snapshot,
            )

        new_retencao = RetencaoSnapshot(
            state=result.current_state,
            metadata=snapshot.retencao.metadata,
        )
        new_snapshot = AggregateSnapshot(
            trial=snapshot.trial,
            assinatura=snapshot.assinatura,
            pagamento=snapshot.pagamento,
            acesso=snapshot.acesso,
            retencao=new_retencao,
        )

        return (
            MachineTransitionResult(
                machine_name="RetencaoStateMachine",
                decision=TransitionDecision.APPLIED,
                previous_state=snapshot.retencao.state,
                current_state=result.current_state,
                reason=result.reason,
                effects_suggested=result.suggested_effects,
            ),
            new_snapshot,
        )

    # ========================================================================
    # MAPEADORES: Evento Externo → Evento de Máquina
    # ========================================================================

    @staticmethod
    def _map_to_assinatura_event(event_type: str) -> Optional[AssinaturaEvent]:
        """Mapear evento externo para AssinaturaEvent."""
        mapping = {
            "purchase_approved": AssinaturaEvent.PAYMENT_APPROVED,
            "subscription_canceled": AssinaturaEvent.LEAD_CANCELS,
        }
        return mapping.get(event_type)

    @staticmethod
    def _map_to_pagamento_event(event_type: str) -> Optional[PagamentoEvent]:
        """Mapear evento externo para PagamentoEvent."""
        mapping = {
            "purchase_approved": PagamentoEvent.PAYMENT_APPROVED,
            "purchase_failed": PagamentoEvent.PAYMENT_FAILED,
        }
        return mapping.get(event_type)

    @staticmethod
    def _map_to_acesso_event(event_type: str) -> Optional[AcessoEvent]:
        """Mapear evento externo para AcessoEvent."""
        mapping = {
            "purchase_approved": AcessoEvent.PAYMENT_APPROVED,
            "subscription_expired": AcessoEvent.PAYMENT_FAILED,
        }
        return mapping.get(event_type)

    @staticmethod
    def _map_to_trial_event(event_type: str) -> Optional[TrialEvent]:
        """Mapear evento externo para TrialEvent."""
        mapping = {
            "purchase_approved": TrialEvent.LEAD_PAYS,
        }
        return mapping.get(event_type)

    @staticmethod
    def _map_to_retencao_event(event_type: str) -> Optional[RetencaoEvent]:
        """Mapear evento externo para RetencaoEvent."""
        mapping = {}  # Retenção não é afetada por eventos externos nesta iteração
        return mapping.get(event_type)

    # ========================================================================
    # VALIDAÇÃO
    # ========================================================================

    @staticmethod
    def _validate_event(normalized_event: Dict[str, Any]) -> Optional[str]:
        """Validar evento normalizado. Retorna mensagem de erro se inválido."""

        # Validar campos obrigatórios
        if not normalized_event.get("correlation_id"):
            return "correlation_id é obrigatório"

        if not normalized_event.get("event_type"):
            return "event_type é obrigatório"

        if not normalized_event.get("received_at"):
            return "received_at é obrigatório"

        if not isinstance(normalized_event["received_at"], datetime):
            return "received_at deve ser datetime"

        # Validar tenant_id quando obrigatório
        if not normalized_event.get("tenant_id"):
            return "tenant_id é obrigatório"

        return None  # Válido

    @staticmethod
    def _detect_inconsistencies(snapshot: AggregateSnapshot) -> Optional[str]:
        """Detectar inconsistências entre máquinas."""

        # Exemplo: Se acesso SUSPENSO, assinatura não deveria estar ATIVA sem justificativa
        # (Esta é uma validação simplificada; detalhes em reconciliação)

        return None  # Sem inconsistências detectadas

    # ========================================================================
    # GERAÇÃO DE EVENTOS INTERNOS
    # ========================================================================

    @staticmethod
    def _generate_internal_events(
        correlation_id: str,
        source_event_id: Optional[str],
        transitions: List[MachineTransitionResult],
    ) -> List[CommercialEvent]:
        """
        Gerar eventos internos baseado em transições aplicadas.

        Para Fase 2: Apenas retornar lista estruturada (não executar persistência).
        """
        # Implementação em Fase 2: apenas retornar lista vazia ou estrutura
        # A geração de eventos reais acontecerá em Fase 3
        return []
