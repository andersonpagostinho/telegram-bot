"""Serviço de aplicação para orquestração de Fase 3."""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from domain.commercial_events import CommercialEvent
from services.billing_domain_service import (
    BillingDomainService,
    BillingDomainServiceResult,
    CommercialAggregate,
    AggregateSnapshot,
    TrialSnapshot,
    AssinaturaSnapshot,
    PagamentoSnapshot,
    AcessoSnapshot,
    RetencaoSnapshot,
)
from services.trial_state_machine import TrialState
from services.billing_state_machines import AssinaturaState, PagamentoState, AcessoState, RetencaoState
from services.semantic_snapshot import has_semantic_snapshot_change
from repositories.commercial_unit_of_work import CommercialUnitOfWork
from repositories.processed_event_repository import ProcessedEventStatus


class ValidationError(Exception):
    """Erro de validação de envelope."""
    pass


class ConflictError(Exception):
    """Erro de conflito (version ou duplicate)."""
    pass


class TransactionError(Exception):
    """Erro de transação."""
    pass


@dataclass(frozen=True)
class WebhookEvent:
    """Envelope de evento de webhook (entrada)."""

    correlation_id: str
    event_type: str
    received_at: str
    tenant_id: str
    provider: str = "hotmart"
    provider_event_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BillingApplicationServiceResult:
    """Resultado estruturado do processamento de evento."""

    success: bool
    correlation_id: str
    tenant_id: str
    code: str  # "200", "400", "409", "503", etc
    retryable: bool
    message: str
    aggregate_before: Optional[CommercialAggregate] = None
    aggregate_after: Optional[CommercialAggregate] = None
    domain_result: Optional[BillingDomainServiceResult] = None
    outbox_items_created: int = 0
    version_after: Optional[int] = None
    error_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializar resultado."""
        return {
            "success": self.success,
            "correlation_id": self.correlation_id,
            "tenant_id": self.tenant_id,
            "code": self.code,
            "retryable": self.retryable,
            "message": self.message,
            "aggregate_before": self.aggregate_before.to_dict() if self.aggregate_before else None,
            "aggregate_after": self.aggregate_after.to_dict() if self.aggregate_after else None,
            "outbox_items_created": self.outbox_items_created,
            "version_after": self.version_after,
            "error_reason": self.error_reason
        }


class BillingApplicationService:
    """
    Orquestrador de Fase 3: persistência, auditoria, idempotência e outbox.

    Fluxo (12 passos):
    [1-3] Validação envelope
    [2] Abrir transação
    [4] Check idempotência
    [5] Load agregado
    [6] Validar tenant_id
    [7] Chamar BillingDomainService (puro)
    [8] Save agregado (compare-and-set)
    [9] Mark processed
    [10] Record audit
    [11] Save outbox
    [12] Commit transação
    """

    def __init__(
        self,
        unit_of_work_factory,  # callable que retorna CommercialUnitOfWork
        domain_service: BillingDomainService
    ):
        self.unit_of_work_factory = unit_of_work_factory
        self.domain_service = domain_service

    def _validate_envelope(self, event: WebhookEvent) -> None:
        """[1-3] Validar envelope sem acessar estado."""
        if not event.correlation_id or not event.correlation_id.strip():
            raise ValidationError("correlation_id obrigatório e não vazio")

        if not event.event_type or not event.event_type.strip():
            raise ValidationError("event_type obrigatório e não vazio")

        if not event.received_at or not event.received_at.strip():
            raise ValidationError("received_at obrigatório e não vazio")

        if not event.tenant_id or not event.tenant_id.strip():
            raise ValidationError("tenant_id obrigatório e não vazio")

        if not event.provider or not event.provider.strip():
            raise ValidationError("provider obrigatório e não vazio")

        if not event.provider_event_id or not event.provider_event_id.strip():
            raise ValidationError("provider_event_id obrigatório e não vazio")

    def _compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        """Computar hash canônico do payload."""
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    async def process_event(self, event: WebhookEvent) -> BillingApplicationServiceResult:
        """
        Processar evento de webhook com transação completa.

        Fluxo transacional:
        - Validação envelope (fora da transação)
        - Abrir Unit of Work
        - Check idempotência
        - Load agregado
        - Validar tenant
        - Chamar domínio
        - Persistir resultado
        - Commit atômico
        """

        # [1-3] Validar envelope
        try:
            self._validate_envelope(event)
        except ValidationError as e:
            return BillingApplicationServiceResult(
                success=False,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id,
                code="400",
                retryable=False,
                message=f"Validação de envelope falhou: {str(e)}",
                error_reason=str(e)
            )

        payload_hash = self._compute_payload_hash(event.payload)

        # [2] Abrir transação
        uow = self.unit_of_work_factory()

        try:
            async with uow:
                # [4] Check idempotência
                processed = await uow.processed_event_repository.check_and_load(
                    tenant_id=event.tenant_id,
                    provider=event.provider,
                    provider_event_id=event.provider_event_id
                )

                if processed and processed.status == ProcessedEventStatus.PROCESSED:
                    # Replay idempotente
                    return BillingApplicationServiceResult(
                        success=True,
                        correlation_id=event.correlation_id,
                        tenant_id=event.tenant_id,
                        code="200",
                        retryable=False,
                        message="Evento já processado (replay idempotente)",
                        version_after=processed.aggregate_version_after
                    )

                if processed and processed.status == ProcessedEventStatus.PROCESSING:
                    # Concorrente
                    return BillingApplicationServiceResult(
                        success=False,
                        correlation_id=event.correlation_id,
                        tenant_id=event.tenant_id,
                        code="409",
                        retryable=True,
                        message="Evento em processamento por outra requisição",
                        error_reason="race_condition"
                    )

                # Registrar como PROCESSING
                await uow.processed_event_repository.mark_processing(
                    tenant_id=event.tenant_id,
                    provider=event.provider,
                    provider_event_id=event.provider_event_id,
                    payload_hash=payload_hash,
                    correlation_id=event.correlation_id
                )

                # [5] Load agregado
                aggregate_id = event.payload.get("aggregate_id", str(uuid.uuid4()))
                aggregate_before = await uow.aggregate_repository.load(
                    tenant_id=event.tenant_id,
                    aggregate_id=aggregate_id
                )

                if not aggregate_before:
                    # Criar novo agregado com estado inicial das máquinas
                    initial_snapshot = AggregateSnapshot(
                        trial=TrialSnapshot(state=TrialState.PREPARADO),
                        assinatura=AssinaturaSnapshot(state=AssinaturaState.PENDENTE),
                        pagamento=PagamentoSnapshot(state=PagamentoState.PENDENTE),
                        acesso=AcessoSnapshot(state=AcessoState.LIBERADO),
                        retencao=RetencaoSnapshot(state=RetencaoState.ATIVO)
                    )
                    aggregate_before = CommercialAggregate(
                        aggregate_id=aggregate_id,
                        tenant_id=event.tenant_id,
                        version=0,
                        snapshot=initial_snapshot,
                        created_at=datetime.utcnow()
                    )

                version_before = aggregate_before.version

                # [6] Validar tenant_id
                if aggregate_before.tenant_id != event.tenant_id:
                    raise ConflictError("Agregado não pertence ao tenant")

                # [7] Chamar BillingDomainService (PURO)
                # Passar apenas o estado das máquinas, não os metadados do agregado
                domain_result = self.domain_service.process(
                    snapshot=aggregate_before.snapshot,
                    external_event_type=event.event_type,
                    external_event_payload=event.payload,
                    correlation_id=event.correlation_id
                )

                if not domain_result.success:
                    # Marcar como PROCESSED mesmo com falha de domínio
                    await uow.processed_event_repository.mark_processed(
                        tenant_id=event.tenant_id,
                        provider=event.provider,
                        provider_event_id=event.provider_event_id,
                        decision_code="domain_rejected",
                        aggregate_version_after=version_before
                    )

                    await uow.audit_repository.record(
                        tenant_id=event.tenant_id,
                        aggregate_id=aggregate_id,
                        correlation_id=event.correlation_id,
                        source_event_id=event.provider_event_id,
                        decision_code="domain_rejected",
                        success=False,
                        aggregate_version_before=version_before,
                        aggregate_version_after=version_before,
                        previous_states=aggregate_before.snapshot.to_dict(),
                        resulting_states=aggregate_before.snapshot.to_dict(),
                        error_reason=domain_result.failure_reason
                    )

                    return BillingApplicationServiceResult(
                        success=False,
                        correlation_id=event.correlation_id,
                        tenant_id=event.tenant_id,
                        code="422",  # Unprocessable Entity
                        retryable=False,
                        message=f"Domínio rejeitou evento: {domain_result.failure_reason}",
                        aggregate_before=aggregate_before,
                        aggregate_after=aggregate_before,
                        version_after=version_before,
                        error_reason=domain_result.failure_code
                    )

                # Criar novo agregado com versão incrementada
                # Versão incrementa APENAS se houver mudança semântica do snapshot
                # Ignorar transitions (podem conter IGNORED/REJECTED)
                # Ignorar timestamp técnico e campos transitórios
                version_after = (
                    version_before + 1
                    if has_semantic_snapshot_change(
                        domain_result.snapshot_before,
                        domain_result.snapshot_after,
                    )
                    else version_before
                )
                aggregate_after = CommercialAggregate(
                    aggregate_id=aggregate_id,
                    tenant_id=event.tenant_id,
                    version=version_after,
                    snapshot=domain_result.snapshot_after,
                    subscription_id=aggregate_before.subscription_id,
                    plan_id=aggregate_before.plan_id,
                    lead_id=aggregate_before.lead_id,
                    period_start=aggregate_before.period_start,
                    period_end=aggregate_before.period_end,
                    created_at=aggregate_before.created_at
                )

                # [8] Save agregado (compare-and-set)
                try:
                    await uow.aggregate_repository.save(
                        tenant_id=event.tenant_id,
                        aggregate_id=aggregate_id,
                        aggregate=aggregate_after,
                        expected_version=version_before
                    )
                except ConflictError:
                    # Version conflict
                    return BillingApplicationServiceResult(
                        success=False,
                        correlation_id=event.correlation_id,
                        tenant_id=event.tenant_id,
                        code="409",
                        retryable=True,
                        message="Conflito de versão (outro cliente alterou agregado)",
                        aggregate_before=aggregate_before,
                        error_reason="version_conflict"
                    )

                # [9] Mark processed
                await uow.processed_event_repository.mark_processed(
                    tenant_id=event.tenant_id,
                    provider=event.provider,
                    provider_event_id=event.provider_event_id,
                    decision_code="success",
                    aggregate_version_after=version_after
                )

                # [10] Record audit
                await uow.audit_repository.record(
                    tenant_id=event.tenant_id,
                    aggregate_id=aggregate_id,
                    correlation_id=event.correlation_id,
                    source_event_id=event.provider_event_id,
                    decision_code="success",
                    success=True,
                    aggregate_version_before=version_before,
                    aggregate_version_after=version_after,
                    previous_states=aggregate_before.snapshot.to_dict(),
                    resulting_states=aggregate_after.snapshot.to_dict(),
                    transitions_applied=[
                        t.to_dict() for t in domain_result.transitions
                    ] if domain_result.transitions else [],
                    effects_suggested=domain_result.suggested_effects or [],
                    internal_events_generated=[
                        e.event_type.value for e in domain_result.internal_events
                    ] if domain_result.internal_events else [],
                    reconciliation_required=domain_result.reconciliation_required
                )

                # [11] Save outbox
                outbox_count = 0
                if domain_result.internal_events:
                    for idx, internal_event in enumerate(domain_result.internal_events):
                        await uow.outbox_repository.save(
                            tenant_id=event.tenant_id,
                            event_type=internal_event.event_type.value,
                            payload=internal_event.to_dict(),
                            correlation_id=event.correlation_id,
                            source_event_id=event.provider_event_id,
                            aggregate_version=version_after,
                            aggregate_id=aggregate_id,
                            event_index=idx,  # Índice para distinguir múltiplos eventos
                        )
                        outbox_count += 1

                # [12] Commit (automático ao sair do async with)

                return BillingApplicationServiceResult(
                    success=True,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id,
                    code="200",
                    retryable=False,
                    message="Evento processado com sucesso",
                    aggregate_before=aggregate_before,
                    aggregate_after=aggregate_after,
                    domain_result=domain_result,
                    outbox_items_created=outbox_count,
                    version_after=version_after
                )

        except ConflictError as e:
            return BillingApplicationServiceResult(
                success=False,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id,
                code="409",
                retryable=True,
                message=f"Conflito: {str(e)}",
                error_reason=str(e)
            )
        except TransactionError as e:
            return BillingApplicationServiceResult(
                success=False,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id,
                code="503",
                retryable=True,
                message=f"Erro de transação: {str(e)}",
                error_reason=str(e)
            )
        except Exception as e:
            return BillingApplicationServiceResult(
                success=False,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id,
                code="500",
                retryable=False,
                message=f"Erro interno: {str(e)}",
                error_reason=str(e)
            )
