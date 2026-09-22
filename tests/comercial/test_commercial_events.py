"""
TESTES — Commercial Events

Valida estrutura, tipagem, imutabilidade e rastreabilidade de eventos.
"""

import pytest
from datetime import datetime
from dataclasses import FrozenInstanceError

from domain.commercial_events import (
    CommercialEvent,
    TrialActivated,
    PaymentApproved,
    SubscriptionActivated,
    AccessReleased,
    DataRetentionStarted,
    TenantCreated,
    EventProcessed,
    ReconciliationRequested,
    EventCategory,
    EventSource,
    EventSchemaVersion,
    EVENT_TYPE_REGISTRY,
    get_event_class,
    get_all_event_types,
)


# ==============================================================================
# TESTES DE ESTRUTURA BÁSICA
# ==============================================================================


class TestEventStructure:
    """Testa estrutura base de eventos."""

    def test_trial_activated_creation(self):
        """Criar evento TrialActivated válido."""
        event = TrialActivated(
            correlation_id="corr_123",
            received_at=datetime(2026, 7, 27, 14, 30, 0),
            tenant_id="tenant_abc",
            lead_id="lead_xyz",
            plan_id="plan_profissional",
            trial_duration_days=7,
            trial_start_date=datetime(2026, 7, 27),
        )

        assert event.event_type == "trial_activated"
        assert event.category == EventCategory.TRIAL
        assert event.correlation_id == "corr_123"
        assert event.tenant_id == "tenant_abc"
        assert event.event_id  # UUID gerado

    def test_payment_approved_creation(self):
        """Criar evento PaymentApproved válido."""
        event = PaymentApproved(
            correlation_id="corr_456",
            received_at=datetime(2026, 7, 27, 14, 30, 0),
            tenant_id="tenant_abc",
            source_event_id="hotmart_123456",
            source=EventSource.HOTMART_WEBHOOK,
            amount=157.00,
            currency="BRL",
            approval_date=datetime(2026, 7, 27, 14, 30, 0),
        )

        assert event.event_type == "payment_approved"
        assert event.category == EventCategory.PAYMENT
        assert event.amount == 157.00
        assert event.source == EventSource.HOTMART_WEBHOOK
        assert event.source_event_id == "hotmart_123456"

    def test_event_id_auto_generated(self):
        """Event ID é gerado automaticamente como UUID."""
        event1 = TrialActivated(
            correlation_id="corr_123",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
        )
        event2 = TrialActivated(
            correlation_id="corr_123",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
        )

        # Diferentes event IDs
        assert event1.event_id != event2.event_id


# ==============================================================================
# TESTES DE IMUTABILIDADE
# ==============================================================================


class TestEventImmutability:
    """Testa que eventos são imutáveis após criação."""

    def test_event_frozen_after_creation(self):
        """Tentar alterar atributo de evento congelado deve falhar."""
        event = TrialActivated(
            correlation_id="corr_123",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
        )

        with pytest.raises(FrozenInstanceError):
            event.tenant_id = "tenant_novo"

    def test_metadata_frozen(self):
        """Metadados não podem ser alterados."""
        event = PaymentApproved(
            correlation_id="corr_456",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
            amount=100.0,
            metadata={"initial": "value"},
        )

        # Tentar alterar metadata
        with pytest.raises(FrozenInstanceError):
            event.metadata = {"new": "value"}


# ==============================================================================
# TESTES DE VALIDAÇÃO
# ==============================================================================


class TestEventValidation:
    """Testa validação de eventos."""

    def test_correlation_id_required(self):
        """correlation_id é obrigatório."""
        with pytest.raises(ValueError, match="correlation_id é obrigatório"):
            TrialActivated(
                correlation_id="",  # Vazio
                received_at=datetime.utcnow(),
                tenant_id="tenant_abc",
            )

    def test_correlation_id_not_none_string(self):
        """correlation_id não pode ser None."""
        with pytest.raises(ValueError, match="correlation_id é obrigatório"):
            TrialActivated(
                correlation_id=None,
                received_at=datetime.utcnow(),
                tenant_id="tenant_abc",
            )

    def test_received_at_must_be_datetime(self):
        """received_at deve ser datetime."""
        with pytest.raises(TypeError, match="received_at deve ser datetime"):
            TrialActivated(
                correlation_id="corr_123",
                received_at="2026-07-27",  # String, não datetime
                tenant_id="tenant_abc",
            )

    def test_tenant_id_cannot_be_empty_string(self):
        """tenant_id não pode ser string vazia (None é permitido)."""
        with pytest.raises(ValueError, match="tenant_id não pode ser string vazia"):
            TrialActivated(
                correlation_id="corr_123",
                received_at=datetime.utcnow(),
                tenant_id="",  # String vazia proibida
            )

    def test_tenant_id_none_is_valid(self):
        """tenant_id como None é válido para alguns eventos."""
        event = EventProcessed(
            correlation_id="corr_123",
            received_at=datetime.utcnow(),
            tenant_id=None,  # None é permitido
            processing_status="success",
        )
        assert event.tenant_id is None

    def test_amount_validation(self):
        """Valores de amount podem ser negativos ou zero (validação em serviço)."""
        # Eventos puros não validam valores de negócio
        event = PaymentApproved(
            correlation_id="corr_456",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
            amount=-100.0,  # Permitido em estrutura; validação é em serviço
        )
        assert event.amount == -100.0


# ==============================================================================
# TESTES DE RASTREABILIDADE
# ==============================================================================


class TestEventTraceability:
    """Testa correlação e rastreamento de eventos."""

    def test_correlation_id_propagation(self):
        """correlation_id é propagado de entrada a saída."""
        correlation_id = "corr_abc123"
        event = PaymentApproved(
            correlation_id=correlation_id,
            received_at=datetime.utcnow(),
            tenant_id="tenant_xyz",
            source_event_id="hotmart_999",
        )

        assert event.correlation_id == correlation_id

    def test_source_event_id_optional(self):
        """source_event_id é opcional."""
        event1 = PaymentApproved(
            correlation_id="corr_123",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
            source_event_id=None,
        )
        assert event1.source_event_id is None

        event2 = PaymentApproved(
            correlation_id="corr_123",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
            source_event_id="hotmart_123",
        )
        assert event2.source_event_id == "hotmart_123"

    def test_source_tracking(self):
        """Origem do evento é rastreada."""
        event_webhook = PaymentApproved(
            correlation_id="corr_123",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
            source=EventSource.HOTMART_WEBHOOK,
        )
        assert event_webhook.source == EventSource.HOTMART_WEBHOOK

        event_internal = SubscriptionActivated(
            correlation_id="corr_456",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
            source=EventSource.INTERNAL_COMMAND,
        )
        assert event_internal.source == EventSource.INTERNAL_COMMAND


# ==============================================================================
# TESTES DE SERIALIZAÇÃO
# ==============================================================================


class TestEventSerialization:
    """Testa serialização de eventos para persistência."""

    def test_to_dict_complete(self):
        """Evento pode ser serializado para dicionário."""
        event = PaymentApproved(
            correlation_id="corr_123",
            received_at=datetime(2026, 7, 27, 14, 30, 0),
            tenant_id="tenant_abc",
            source_event_id="hotmart_999",
            amount=157.00,
            currency="BRL",
        )

        result = event.to_dict()

        assert result["event_type"] == "payment_approved"
        assert result["correlation_id"] == "corr_123"
        assert result["tenant_id"] == "tenant_abc"
        assert result["source_event_id"] == "hotmart_999"
        assert result["amount"] == 157.00
        assert "event_id" in result

    def test_serialization_preserves_metadata(self):
        """Metadados são preservados na serialização."""
        metadata = {"order_id": "ord_123", "custom_field": "value"}
        event = EventProcessed(
            correlation_id="corr_123",
            received_at=datetime.utcnow(),
            tenant_id="tenant_abc",
            metadata=metadata,
        )

        result = event.to_dict()
        assert result["metadata"] == metadata


# ==============================================================================
# TESTES DE REGISTRO DE EVENTOS
# ==============================================================================


class TestEventRegistry:
    """Testa reflexão e registro de tipos de eventos."""

    def test_event_type_in_registry(self):
        """Todos os tipos de evento estão registrados."""
        assert "trial_activated" in EVENT_TYPE_REGISTRY
        assert "payment_approved" in EVENT_TYPE_REGISTRY
        assert "subscription_activated" in EVENT_TYPE_REGISTRY
        assert "access_released" in EVENT_TYPE_REGISTRY
        assert "data_retention_started" in EVENT_TYPE_REGISTRY
        assert "conversion_completed" in EVENT_TYPE_REGISTRY
        assert "event_processed" in EVENT_TYPE_REGISTRY
        assert "reconciliation_requested" in EVENT_TYPE_REGISTRY

    def test_get_event_class_by_type(self):
        """Resolver classe de evento por tipo."""
        assert get_event_class("trial_activated") == TrialActivated
        assert get_event_class("payment_approved") == PaymentApproved
        assert get_event_class("subscription_activated") == SubscriptionActivated
        assert get_event_class("unknown_type") is None

    def test_get_all_event_types(self):
        """Listar todos os tipos de evento."""
        all_types = get_all_event_types()
        assert isinstance(all_types, list)
        assert len(all_types) > 0
        assert all(isinstance(t, str) for t in all_types)
        # Verificar que lista está ordenada
        assert all_types == sorted(all_types)

    def test_registry_completeness(self):
        """Registro contém múltiplos eventos de cada categoria."""
        trial_events = [t for t in get_all_event_types() if "trial" in t]
        payment_events = [t for t in get_all_event_types() if "payment" in t]
        access_events = [t for t in get_all_event_types() if "access" in t]

        assert len(trial_events) >= 3
        assert len(payment_events) >= 3
        assert len(access_events) >= 3


# ==============================================================================
# TESTES DE CATEGORIAS E VERSIONING
# ==============================================================================


class TestEventCategoriesAndVersioning:
    """Testa categorias e versionamento de eventos."""

    def test_event_categories(self):
        """Eventos têm categoria correta."""
        trial_event = TrialActivated(
            correlation_id="c1",
            received_at=datetime.utcnow(),
            tenant_id="t1",
        )
        assert trial_event.category == EventCategory.TRIAL

        payment_event = PaymentApproved(
            correlation_id="c2",
            received_at=datetime.utcnow(),
            tenant_id="t2",
            amount=100.0,
        )
        assert payment_event.category == EventCategory.PAYMENT

    def test_schema_version(self):
        """Eventos têm versão de schema."""
        event = PaymentApproved(
            correlation_id="c1",
            received_at=datetime.utcnow(),
            tenant_id="t1",
            amount=100.0,
            schema_version=EventSchemaVersion.V1_0,
        )
        assert event.schema_version == EventSchemaVersion.V1_0

    def test_schema_version_default(self):
        """Versão de schema tem valor padrão."""
        event = TrialActivated(
            correlation_id="c1",
            received_at=datetime.utcnow(),
            tenant_id="t1",
        )
        assert event.schema_version == EventSchemaVersion.V1_0


# ==============================================================================
# TESTES DE MÚLTIPLAS CATEGORIAS
# ==============================================================================


class TestAllEventCategories:
    """Valida que todas as categorias de eventos funcionam."""

    def test_trial_events_valid(self):
        """Todos os eventos de Trial são válidos."""
        event = TrialActivated(
            correlation_id="c1", received_at=datetime.utcnow(), tenant_id="t1"
        )
        assert event.category == EventCategory.TRIAL

    def test_subscription_events_valid(self):
        """Todos os eventos de Subscription são válidos."""
        event = SubscriptionActivated(
            correlation_id="c1", received_at=datetime.utcnow(), tenant_id="t1"
        )
        assert event.category == EventCategory.SUBSCRIPTION

    def test_payment_events_valid(self):
        """Todos os eventos de Payment são válidos."""
        event = PaymentApproved(
            correlation_id="c1",
            received_at=datetime.utcnow(),
            tenant_id="t1",
            amount=100.0,
        )
        assert event.category == EventCategory.PAYMENT

    def test_access_events_valid(self):
        """Todos os eventos de Access são válidos."""
        event = AccessReleased(
            correlation_id="c1", received_at=datetime.utcnow(), tenant_id="t1"
        )
        assert event.category == EventCategory.ACCESS

    def test_retention_events_valid(self):
        """Todos os eventos de Data Retention são válidos."""
        event = DataRetentionStarted(
            correlation_id="c1",
            received_at=datetime.utcnow(),
            tenant_id="t1",
            retention_period_days=30,
        )
        assert event.category == EventCategory.DATA_RETENTION

    def test_conversion_events_valid(self):
        """Todos os eventos de Conversion são válidos."""
        event = TenantCreated(
            correlation_id="c1",
            received_at=datetime.utcnow(),
            tenant_id="t1",
            lead_id="lead_123",
        )
        assert event.category == EventCategory.CONVERSION

    def test_audit_events_valid(self):
        """Todos os eventos de Audit são válidos."""
        event = EventProcessed(
            correlation_id="c1",
            received_at=datetime.utcnow(),
            tenant_id="t1",
            processing_status="success",
        )
        assert event.category == EventCategory.AUDIT

    def test_reconciliation_events_valid(self):
        """Todos os eventos de Reconciliation são válidos."""
        event = ReconciliationRequested(
            correlation_id="c1",
            received_at=datetime.utcnow(),
            tenant_id="t1",
            reason="estado_inconsistente",
        )
        assert event.category == EventCategory.RECONCILIATION


# ==============================================================================
# TESTES DE DETERMINISMO
# ==============================================================================


class TestEventDeterminism:
    """Testa que eventos são determinísticos."""

    def test_same_input_same_structure(self):
        """Mesmo input produz mesma estrutura (exceto event_id)."""
        correlation_id = "corr_123"
        received_at = datetime(2026, 7, 27, 14, 30, 0)
        tenant_id = "tenant_abc"

        event1 = PaymentApproved(
            correlation_id=correlation_id,
            received_at=received_at,
            tenant_id=tenant_id,
            amount=157.00,
        )

        event2 = PaymentApproved(
            correlation_id=correlation_id,
            received_at=received_at,
            tenant_id=tenant_id,
            amount=157.00,
        )

        # Estrutura idêntica (exceto event_id)
        assert event1.correlation_id == event2.correlation_id
        assert event1.received_at == event2.received_at
        assert event1.tenant_id == event2.tenant_id
        assert event1.amount == event2.amount
        # Mas event_id diferente
        assert event1.event_id != event2.event_id
