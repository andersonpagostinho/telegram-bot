"""
COMMERCIAL EVENTS — Tipos de Eventos Internos e Externos para Domínio Comercial

Definições de eventos puros, tipados, imutáveis, sem efeitos colaterais.

Referências:
- CONTRATO_TRIAL_NEOEVE.md V1.2
- CONTRATO_BILLING_NEOEVE.md V1.1
- CONTRATO_CONVERSAO_LEAD_TENANT.md V1.0
- FASE2_ANALISE_EVENTOS_ORQUESTRACAO.md
"""

from abc import ABC
from dataclasses import dataclass, field, FrozenInstanceError
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4


# ==============================================================================
# TIPOS FUNDAMENTAIS
# ==============================================================================


class EventCategory(str, Enum):
    """Categorias de eventos para roteamento e audit."""
    TRIAL = "trial"
    SUBSCRIPTION = "subscription"
    PAYMENT = "payment"
    ACCESS = "access"
    DATA_RETENTION = "data_retention"
    CONVERSION = "conversion"
    AUDIT = "audit"
    RECONCILIATION = "reconciliation"


class EventSource(str, Enum):
    """Origem do evento."""
    HOTMART_WEBHOOK = "hotmart_webhook"
    INTERNAL_COMMAND = "internal_command"
    SYSTEM = "system"
    MANUAL = "manual"


class EventSchemaVersion(str, Enum):
    """Versioning do esquema de evento."""
    V1_0 = "1.0"


# ==============================================================================
# BASE EVENT CLASS (IMUTÁVEL)
# ==============================================================================


@dataclass(frozen=True)
class CommercialEvent(ABC):
    """
    Base class para todos os eventos do domínio comercial.

    Garantias:
    - Imutável (frozen=True)
    - Tipado explicitamente
    - Correlação rastreável
    - Timestamp explícito (não gerado implicitamente)
    - Tenant_id obrigatório quando aplicável
    - Schema versionado
    """

    # Rastreabilidade (campos obrigatórios sem defaults)
    correlation_id: str  # OBRIGATÓRIO: agrupa eventos relacionados
    received_at: datetime  # Timestamp EXPLÍCITO, nunca gerado implicitamente

    # Identidade do evento (com defaults)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = field(init=False)  # Definido por subclass
    category: EventCategory = field(init=False)  # Definido por subclass
    schema_version: EventSchemaVersion = field(default=EventSchemaVersion.V1_0)

    # Rastreabilidade (opcionais)
    source_event_id: Optional[str] = None  # ID do evento de origem (ex: hotmart_123456)
    source: EventSource = EventSource.INTERNAL_COMMAND

    # Isolamento multi-tenant
    tenant_id: Optional[str] = None  # OBRIGATÓRIO para maioria dos eventos

    # Auditoria
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validações adicionais após criação (dataclass frozen permite)."""
        # Validar que correlation_id não está vazio
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("correlation_id é obrigatório e não pode ser vazio")

        # Validar timestamp
        if not isinstance(self.received_at, datetime):
            raise TypeError("received_at deve ser datetime")

        # Validar tenant_id se obrigatório
        if self.tenant_id is not None and not self.tenant_id.strip():
            raise ValueError("tenant_id não pode ser string vazia (use None)")

    def to_dict(self) -> Dict[str, Any]:
        """Serialização para persistência ou transmissão."""
        result = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "category": self.category.value,
            "schema_version": self.schema_version.value,
            "correlation_id": self.correlation_id,
            "source_event_id": self.source_event_id,
            "source": self.source.value,
            "received_at": self.received_at.isoformat(),
            "tenant_id": self.tenant_id,
            "metadata": self.metadata,
        }
        # Adicionar campos específicos da subclasse
        for key, value in self.__dict__.items():
            if key not in result and not key.startswith("_"):
                # Serializar enums e datetime
                if isinstance(value, Enum):
                    result[key] = value.value
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


# ==============================================================================
# TRIAL EVENTS
# ==============================================================================


@dataclass(frozen=True)
class TrialActivated(CommercialEvent):
    """
    Trial foi ativado (PREPARADO → ATIVO).
    Lead completou onboarding mínimo.
    """
    event_type: str = field(default="trial_activated", init=False)
    category: EventCategory = field(default=EventCategory.TRIAL, init=False)

    # Detalhes
    lead_id: str = None  # ID do lead que iniciou trial
    plan_id: str = None  # Plano selecionado
    trial_duration_days: int = 7  # Duração do trial
    trial_start_date: datetime = None  # Data/hora início


@dataclass(frozen=True)
class TrialExpired(CommercialEvent):
    """
    Trial expirou (ATIVO → EXPIRADO).
    Período de teste terminou sem pagamento.
    """
    event_type: str = field(default="trial_expired", init=False)
    category: EventCategory = field(default=EventCategory.TRIAL, init=False)

    trial_end_date: datetime = None


@dataclass(frozen=True)
class TrialConverted(CommercialEvent):
    """
    Trial foi convertido (EXPIRADO → CONVERTIDO).
    Lead pagou após trial.
    """
    event_type: str = field(default="trial_converted", init=False)
    category: EventCategory = field(default=EventCategory.TRIAL, init=False)

    converted_to_plan_id: str = None
    conversion_date: datetime = None


@dataclass(frozen=True)
class TrialCanceled(CommercialEvent):
    """
    Trial foi cancelado (ATIVO/EXPIRADO → CANCELADO).
    Lead solicitou cancelamento.
    """
    event_type: str = field(default="trial_canceled", init=False)
    category: EventCategory = field(default=EventCategory.TRIAL, init=False)

    cancellation_reason: str = None  # Motivo do cancelamento (opcional)


@dataclass(frozen=True)
class TrialDeleted(CommercialEvent):
    """
    Trial foi deletado (EXPIRADO/CANCELADO → DELETADO).
    Timeout de reativação expirou.
    """
    event_type: str = field(default="trial_deleted", init=False)
    category: EventCategory = field(default=EventCategory.TRIAL, init=False)


@dataclass(frozen=True)
class TrialReactivated(CommercialEvent):
    """
    Trial foi reativado (EXPIRADO/CANCELADO → ATIVO).
    Lead solicitou reativação dentro da janela.
    """
    event_type: str = field(default="trial_reactivated", init=False)
    category: EventCategory = field(default=EventCategory.TRIAL, init=False)


# ==============================================================================
# SUBSCRIPTION EVENTS
# ==============================================================================


@dataclass(frozen=True)
class SubscriptionActivated(CommercialEvent):
    """
    Assinatura foi ativada (PENDENTE → ATIVA).
    Payment foi aprovado.
    """
    event_type: str = field(default="subscription_activated", init=False)
    category: EventCategory = field(default=EventCategory.SUBSCRIPTION, init=False)

    plan_id: str = None
    activation_date: datetime = None


@dataclass(frozen=True)
class SubscriptionCancellationScheduled(CommercialEvent):
    """
    Cancelamento foi agendado (ATIVA → CANCELAMENTO_AGENDADO).
    Lead solicitou cancelamento; vigência até fim de ciclo.
    """
    event_type: str = field(default="subscription_cancellation_scheduled", init=False)
    category: EventCategory = field(default=EventCategory.SUBSCRIPTION, init=False)

    cancellation_effective_date: datetime = None


@dataclass(frozen=True)
class SubscriptionCanceled(CommercialEvent):
    """
    Assinatura foi cancelada (CANCELAMENTO_AGENDADO → CANCELADA).
    Fim de ciclo de pagamento atingido.
    """
    event_type: str = field(default="subscription_canceled", init=False)
    category: EventCategory = field(default=EventCategory.SUBSCRIPTION, init=False)

    cancellation_date: datetime = None


@dataclass(frozen=True)
class SubscriptionEnded(CommercialEvent):
    """
    Assinatura foi encerrada (qualquer → ENCERRADA).
    Dados foram deletados.
    """
    event_type: str = field(default="subscription_ended", init=False)
    category: EventCategory = field(default=EventCategory.SUBSCRIPTION, init=False)

    end_date: datetime = None


@dataclass(frozen=True)
class SubscriptionReactivated(CommercialEvent):
    """
    Assinatura foi reativada (CANCELAMENTO_AGENDADO → ATIVA).
    Lead reverteu cancelamento.
    """
    event_type: str = field(default="subscription_reactivated", init=False)
    category: EventCategory = field(default=EventCategory.SUBSCRIPTION, init=False)

    reactivation_date: datetime = None


# ==============================================================================
# PAYMENT EVENTS
# ==============================================================================


@dataclass(frozen=True)
class PaymentApproved(CommercialEvent):
    """
    Pagamento foi aprovado (PENDENTE → APROVADO).
    Cartão aceitou transação.
    """
    event_type: str = field(default="payment_approved", init=False)
    category: EventCategory = field(default=EventCategory.PAYMENT, init=False)

    amount: float = None  # Valor da transação
    currency: str = "BRL"
    provider_transaction_id: Optional[str] = None  # ID da transação (ex: Hotmart)
    approval_date: datetime = None


@dataclass(frozen=True)
class PaymentRejected(CommercialEvent):
    """
    Pagamento foi rejeitado (PENDENTE → RECUSADO).
    Cartão recusou transação.
    """
    event_type: str = field(default="payment_rejected", init=False)
    category: EventCategory = field(default=EventCategory.PAYMENT, init=False)

    rejection_reason: str = None  # Motivo (insufficient_funds, expired_card, etc)
    rejection_date: datetime = None


@dataclass(frozen=True)
class PaymentRefunded(CommercialEvent):
    """
    Pagamento foi reembolsado (APROVADO → REEMBOLSADO).
    Reembolso foi solicitado/processado.
    """
    event_type: str = field(default="payment_refunded", init=False)
    category: EventCategory = field(default=EventCategory.PAYMENT, init=False)

    refund_amount: float = None
    refund_reason: str = None
    refund_date: datetime = None


@dataclass(frozen=True)
class PaymentContested(CommercialEvent):
    """
    Pagamento foi contestado (APROVADO/REEMBOLSADO → CONTESTADO).
    Chargeback foi aberto.
    """
    event_type: str = field(default="payment_contested", init=False)
    category: EventCategory = field(default=EventCategory.PAYMENT, init=False)

    chargeback_id: str = None
    dispute_amount: float = None
    dispute_reason: str = None


@dataclass(frozen=True)
class PaymentDisputeResolved(CommercialEvent):
    """
    Disputa de pagamento foi resolvida (CONTESTADO → RESOLVIDO).
    Chargeback foi decidido.
    """
    event_type: str = field(default="payment_dispute_resolved", init=False)
    category: EventCategory = field(default=EventCategory.PAYMENT, init=False)

    dispute_outcome: str = None  # "won" ou "lost"
    resolution_date: datetime = None


# ==============================================================================
# ACCESS EVENTS
# ==============================================================================


@dataclass(frozen=True)
class AccessReleased(CommercialEvent):
    """
    Acesso foi liberado (qualquer → LIBERADO).
    Tenant tem acesso completo.
    """
    event_type: str = field(default="access_released", init=False)
    category: EventCategory = field(default=EventCategory.ACCESS, init=False)

    previous_state: str = None
    release_date: datetime = None


@dataclass(frozen=True)
class AccessRestricted(CommercialEvent):
    """
    Acesso foi restrito (LIBERADO → RESTRITO).
    Funcionalidade limitada (ex: pendência de confirmação).
    """
    event_type: str = field(default="access_restricted", init=False)
    category: EventCategory = field(default=EventCategory.ACCESS, init=False)

    restriction_reason: str = None
    restriction_date: datetime = None


@dataclass(frozen=True)
class AccessSuspended(CommercialEvent):
    """
    Acesso foi suspenso (qualquer → SUSPENSO).
    Tenant bloqueado (falta de pagamento, etc).
    """
    event_type: str = field(default="access_suspended", init=False)
    category: EventCategory = field(default=EventCategory.ACCESS, init=False)

    suspension_reason: str = None
    suspension_date: datetime = None


@dataclass(frozen=True)
class AccessEnded(CommercialEvent):
    """
    Acesso foi encerrado (qualquer → ENCERRADO).
    Dados foram deletados.
    """
    event_type: str = field(default="access_ended", init=False)
    category: EventCategory = field(default=EventCategory.ACCESS, init=False)

    end_date: datetime = None


# ==============================================================================
# DATA RETENTION EVENTS
# ==============================================================================


@dataclass(frozen=True)
class DataRetentionStarted(CommercialEvent):
    """
    Retenção de dados iniciada (ATIVO → EM_RETENCAO).
    Acesso foi bloqueado; dados aguardam período de retenção.
    """
    event_type: str = field(default="data_retention_started", init=False)
    category: EventCategory = field(default=EventCategory.DATA_RETENTION, init=False)

    retention_start_date: datetime = None
    retention_period_days: int = 30


@dataclass(frozen=True)
class DataEligibleForDeletion(CommercialEvent):
    """
    Dados elegíveis para deleção (EM_RETENCAO → ELEGIVEL_EXCLUSAO).
    Período de retenção expirou.
    """
    event_type: str = field(default="data_eligible_for_deletion", init=False)
    category: EventCategory = field(default=EventCategory.DATA_RETENTION, init=False)

    eligibility_date: datetime = None


@dataclass(frozen=True)
class DataDeleted(CommercialEvent):
    """
    Dados foram deletados (ELEGIVEL_EXCLUSAO → EXCLUIDO).
    Deleção permanente executada.
    """
    event_type: str = field(default="data_deleted", init=False)
    category: EventCategory = field(default=EventCategory.DATA_RETENTION, init=False)

    deletion_date: datetime = None
    deletion_reason: str = "retention_period_expired"


@dataclass(frozen=True)
class DataRetentionCanceled(CommercialEvent):
    """
    Retenção de dados foi cancelada (EM_RETENCAO → ATIVO).
    Lead reativou durante período de retenção.
    """
    event_type: str = field(default="data_retention_canceled", init=False)
    category: EventCategory = field(default=EventCategory.DATA_RETENTION, init=False)

    cancellation_date: datetime = None


# ==============================================================================
# CONVERSION EVENTS (Lead → Tenant)
# ==============================================================================


@dataclass(frozen=True)
class TenantCreationRequested(CommercialEvent):
    """
    Solicitação de criação de tenant.
    Lead quer começar um trial.
    """
    event_type: str = field(default="tenant_creation_requested", init=False)
    category: EventCategory = field(default=EventCategory.CONVERSION, init=False)

    lead_id: str = None
    plan_id: str = None
    request_date: datetime = None


@dataclass(frozen=True)
class TenantCreated(CommercialEvent):
    """
    Tenant foi criado.
    Lead pode agora acessar plataforma.
    """
    event_type: str = field(default="tenant_created", init=False)
    category: EventCategory = field(default=EventCategory.CONVERSION, init=False)

    lead_id: str = None
    creation_date: datetime = None


@dataclass(frozen=True)
class ConversionCompleted(CommercialEvent):
    """
    Conversão Lead → Tenant completada.
    Lead foi vinculado e primeiras máquinas criadas.
    """
    event_type: str = field(default="conversion_completed", init=False)
    category: EventCategory = field(default=EventCategory.CONVERSION, init=False)

    lead_id: str = None
    completion_date: datetime = None


# ==============================================================================
# AUDIT EVENTS
# ==============================================================================


@dataclass(frozen=True)
class EventProcessed(CommercialEvent):
    """
    Webhook foi recebido e processado com sucesso.
    Rastreabilidade de eventos externos.
    """
    event_type: str = field(default="event_processed", init=False)
    category: EventCategory = field(default=EventCategory.AUDIT, init=False)

    external_event_type: str = None  # Ex: "purchase_approved"
    processing_status: str = "success"  # success, failed, ignored
    processing_date: datetime = None


@dataclass(frozen=True)
class TransitionApplied(CommercialEvent):
    """
    Transição de máquina de estado foi aplicada.
    Auditoria de mudanças de estado.
    """
    event_type: str = field(default="transition_applied", init=False)
    category: EventCategory = field(default=EventCategory.AUDIT, init=False)

    machine_name: str = None  # Ex: "AssinaturaStateMachine"
    previous_state: str = None
    new_state: str = None
    applied_date: datetime = None


@dataclass(frozen=True)
class ValidationFailed(CommercialEvent):
    """
    Evento foi rejeitado por falha de validação/pré-condição.
    """
    event_type: str = field(default="validation_failed", init=False)
    category: EventCategory = field(default=EventCategory.AUDIT, init=False)

    validation_error: str = None  # Motivo detalhado
    external_event_type: str = None  # Qual evento foi rejeitado
    failure_date: datetime = None


# ==============================================================================
# RECONCILIATION EVENTS
# ==============================================================================


@dataclass(frozen=True)
class ReconciliationRequested(CommercialEvent):
    """
    Reconciliação foi solicitada.
    Estado inconsistente ou evento anômalo detectado.
    """
    event_type: str = field(default="reconciliation_requested", init=False)
    category: EventCategory = field(default=EventCategory.RECONCILIATION, init=False)

    reason: str = None  # Ex: "estado_inconsistente", "evento_retroativo"
    affected_machines: List[str] = field(default_factory=list)
    request_date: datetime = None


# ==============================================================================
# EVENT REGISTRY (Reflexão)
# ==============================================================================

# Mapa de tipos de evento para classes (para desserialização)
EVENT_TYPE_REGISTRY = {
    # Trial
    "trial_activated": TrialActivated,
    "trial_expired": TrialExpired,
    "trial_converted": TrialConverted,
    "trial_canceled": TrialCanceled,
    "trial_deleted": TrialDeleted,
    "trial_reactivated": TrialReactivated,

    # Subscription
    "subscription_activated": SubscriptionActivated,
    "subscription_cancellation_scheduled": SubscriptionCancellationScheduled,
    "subscription_canceled": SubscriptionCanceled,
    "subscription_ended": SubscriptionEnded,
    "subscription_reactivated": SubscriptionReactivated,

    # Payment
    "payment_approved": PaymentApproved,
    "payment_rejected": PaymentRejected,
    "payment_refunded": PaymentRefunded,
    "payment_contested": PaymentContested,
    "payment_dispute_resolved": PaymentDisputeResolved,

    # Access
    "access_released": AccessReleased,
    "access_restricted": AccessRestricted,
    "access_suspended": AccessSuspended,
    "access_ended": AccessEnded,

    # Data Retention
    "data_retention_started": DataRetentionStarted,
    "data_eligible_for_deletion": DataEligibleForDeletion,
    "data_deleted": DataDeleted,
    "data_retention_canceled": DataRetentionCanceled,

    # Conversion
    "tenant_creation_requested": TenantCreationRequested,
    "tenant_created": TenantCreated,
    "conversion_completed": ConversionCompleted,

    # Audit
    "event_processed": EventProcessed,
    "transition_applied": TransitionApplied,
    "validation_failed": ValidationFailed,

    # Reconciliation
    "reconciliation_requested": ReconciliationRequested,
}


def get_event_class(event_type: str) -> Optional[type]:
    """Resolve classe de evento por tipo."""
    return EVENT_TYPE_REGISTRY.get(event_type)


def get_all_event_types() -> List[str]:
    """Lista todos os tipos de evento registrados."""
    return sorted(EVENT_TYPE_REGISTRY.keys())
