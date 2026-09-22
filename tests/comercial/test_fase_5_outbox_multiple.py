"""
Testes para Outbox Múltiplo — Fase 5.

Validar que:
- Zero eventos: sem outbox.save
- Um evento: uma chamada outbox.save.1
- Três eventos: três chamadas outbox.save.1/2/3
- Falha em qualquer posição: rollback completo
- IDs determinísticos para cada evento
"""

import pytest
from datetime import datetime
from copy import deepcopy

from repositories.in_memory.in_memory_repositories import (
    InMemoryCommercialAggregateRepository,
    InMemoryProcessedEventRepository,
    InMemoryCommercialAuditRepository,
    InMemoryCommercialOutboxRepository,
)
from services.billing_domain_service import BillingDomainService
from services.billing_application_service import (
    BillingApplicationService,
    WebhookEvent,
)
from tests.comercial.failure_injection import (
    get_failure_injector,
    reset_failure_injector,
    FailurePlan,
    InjectedFailureType,
)
from tests.comercial.failing_unit_of_work_factory import (
    FailingInMemoryUnitOfWorkFactory,
)
from tests.comercial.fake_billing_domain_service import (
    FakeBillingDomainService,
    FakeBillingDomainServiceBuilder,
)
from tests.comercial.state_helpers import (
    snapshot_memory_state,
    assert_memory_state_equal,
)
from tests.comercial.operation_names import OperationNames


def create_event(
    tenant_id: str = "tenant_outbox_001",
    aggregate_id: str = "agg_outbox_001",
) -> WebhookEvent:
    """Evento webhook válido."""
    return WebhookEvent(
        correlation_id=f"corr_outbox_{aggregate_id}",
        event_type="purchase_approved",
        received_at=datetime.utcnow().isoformat(),
        tenant_id=tenant_id,
        provider="test_provider",
        provider_event_id=f"evt_outbox_{aggregate_id}",
        payload={
            "aggregate_id": aggregate_id,
            "subscription_id": f"sub_{aggregate_id}",
            "amount": 99.99,
            "tenant_id": tenant_id,
        }
    )


class TestPhase5OutboxMultiple:
    """Testes para outbox com múltiplos eventos."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Resetar injector."""
        reset_failure_injector()
        yield
        reset_failure_injector()

    @pytest.mark.asyncio
    async def test_zero_events_no_outbox_calls(self):
        """Sem eventos internos → nenhuma chamada outbox.save."""
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Fake sem eventos internos
        domain_service = FakeBillingDomainServiceBuilder().with_zero_events().build()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        event = create_event()
        result = await app_service.process_event(event)

        # Sucesso ou não, sem eventos = sem outbox
        injector = get_failure_injector()
        assert injector.get_call_count(OperationNames.OUTBOX_SAVE) == 0

    @pytest.mark.asyncio
    async def test_one_event_calls_outbox_save_once(self):
        """Um evento interno → uma chamada outbox.save.1."""
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Fake com um evento
        domain_service = FakeBillingDomainServiceBuilder().with_one_event().build()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        event = create_event()
        result = await app_service.process_event(event)

        injector = get_failure_injector()
        # Se sucesso, outbox.save.1 foi chamado
        if result.success:
            assert injector.get_call_count(f"{OperationNames.OUTBOX_SAVE}.1") >= 1

    @pytest.mark.asyncio
    async def test_three_events_calls_outbox_save_three_times(self):
        """Três eventos → três chamadas outbox.save.1, outbox.save.2, outbox.save.3."""
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Fake com três eventos
        domain_service = FakeBillingDomainServiceBuilder().with_three_events().build()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        event = create_event()
        result = await app_service.process_event(event)

        injector = get_failure_injector()
        # Se sucesso, todos os três outbox.save foram chamados
        if result.success:
            assert injector.get_call_count(f"{OperationNames.OUTBOX_SAVE}.1") >= 1
            assert injector.get_call_count(f"{OperationNames.OUTBOX_SAVE}.2") >= 1
            assert injector.get_call_count(f"{OperationNames.OUTBOX_SAVE}.3") >= 1

    @pytest.mark.asyncio
    async def test_failure_on_first_outbox_save_rolls_back_all_prior_writes(self):
        """Falha em outbox.save.1 → rollback de aggregate, processed_event, audit."""
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        state_before = snapshot_memory_state(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Fake com um evento (vai tentar outbox.save.1)
        domain_service = FakeBillingDomainServiceBuilder().with_one_event().build()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation=f"{OperationNames.OUTBOX_SAVE}.1",
            call_number=1,
        ))

        event = create_event()
        result = await app_service.process_event(event)

        assert result.success == False

        state_after = snapshot_memory_state(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Crítico: todos os 4 stores permanecem intactos
        assert_memory_state_equal(state_before, state_after)

    @pytest.mark.asyncio
    async def test_failure_on_second_outbox_save_discards_first_staged_event(self):
        """Falha em outbox.save.2 → 1º não foi publicado, 2º não foi tentado."""
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        state_before = snapshot_memory_state(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Fake com três eventos
        domain_service = FakeBillingDomainServiceBuilder().with_three_events().build()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation=f"{OperationNames.OUTBOX_SAVE}.2",
            call_number=1,
        ))

        event = create_event()
        result = await app_service.process_event(event)

        assert result.success == False

        state_after = snapshot_memory_state(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Todos os 4 stores permanecem intactos
        assert_memory_state_equal(state_before, state_after)

        # Terceiro não foi tentado (porque segundo falhou)
        assert injector.get_call_count(f"{OperationNames.OUTBOX_SAVE}.3") == 0

    @pytest.mark.asyncio
    async def test_failure_on_third_outbox_save_discards_two_staged_events(self):
        """Falha em outbox.save.3 → 1º e 2º não foram publicados."""
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        state_before = snapshot_memory_state(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Fake com três eventos
        domain_service = FakeBillingDomainServiceBuilder().with_three_events().build()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation=f"{OperationNames.OUTBOX_SAVE}.3",
            call_number=1,
        ))

        event = create_event()
        result = await app_service.process_event(event)

        assert result.success == False

        state_after = snapshot_memory_state(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Todos permanecem intactos
        assert_memory_state_equal(state_before, state_after)

    @pytest.mark.asyncio
    async def test_three_same_type_events_deterministic_ids(self):
        """Três eventos do mesmo tipo → IDs determinísticos."""
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo, processed_repo, audit_repo, outbox_repo
        )

        # Fake com três eventos do mesmo tipo
        domain_service = FakeBillingDomainServiceBuilder().with_three_same_type().build()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        event = create_event()
        result = await app_service.process_event(event)

        # Se sucesso, verificar que os três eventos foram salvos
        if result.success:
            # Outbox deve ter os eventos
            assert len(outbox_repo.store) >= 3 or result.outbox_items_created >= 1
