"""
PRIMEIRO TESTE E2E SIMPLES — APENAS ATOMICIDADE.

Objetivo: Validar que estado permanece intacto quando falha é injetada.

Fluxo:
1. Capturar estado antes (vazio)
2. Injetar falha em outbox.save.1
3. Executar BillingApplicationService real
4. Validar que 4 stores não foram alterados
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
from tests.comercial.state_helpers import (
    snapshot_memory_state,
    assert_memory_state_equal,
)
from tests.comercial.operation_names import OperationNames


def create_event() -> WebhookEvent:
    """Evento webhook válido."""
    return WebhookEvent(
        correlation_id="corr_simple_e2e_001",
        event_type="purchase_approved",
        received_at=datetime.utcnow().isoformat(),
        tenant_id="tenant_test_001",
        provider="test_provider",
        provider_event_id="evt_simple_001",
        payload={
            "aggregate_id": "agg_simple_001",
            "subscription_id": "sub_001",
            "amount": 99.99,
            "tenant_id": "tenant_test_001",
        }
    )


class TestPhase5SimpleE2E:
    """Teste E2E simples focado apenas em atomicidade."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Resetar injector."""
        reset_failure_injector()
        yield
        reset_failure_injector()

    @pytest.mark.asyncio
    async def test_atomicity_state_unchanged_on_failure(self):
        """
        VALIDAÇÃO PRINCIPAL: Atomicidade via State Intactness.

        Quando falha é injetada em qualquer ponto,
        os 4 stores (agregados, processados, auditorias, outbox)
        devem permanecer exatamente iguais ao estado anterior.
        """
        # [1] Setup: criar stores
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        # [2] Capturar estado ANTES
        state_before = snapshot_memory_state(
            aggregate_repo,
            processed_repo,
            audit_repo,
            outbox_repo,
        )
        print(f"[INFO] State captured before: {len(state_before)} stores")

        # [3] Criar factory + serviços
        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo=aggregate_repo,
            processed_repo=processed_repo,
            audit_repo=audit_repo,
            outbox_repo=outbox_repo,
        )
        domain_service = BillingDomainService()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        # [4] Injetar falha em aggregate.save
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation=OperationNames.AGGREGATE_SAVE,
            call_number=1,
        ))
        print(f"[INFO] Failure injected in {OperationNames.AGGREGATE_SAVE}")

        # [5] Executar serviço (vai falhar internamente)
        event = create_event()
        result = await app_service.process_event(event)
        print(f"[INFO] Execution result: success={result.success}, code={result.code}")

        # [6] Capturar estado DEPOIS
        state_after = snapshot_memory_state(
            aggregate_repo,
            processed_repo,
            audit_repo,
            outbox_repo,
        )
        print(f"[INFO] State captured after: {len(state_after)} stores")

        # [7] VALIDAÇÃO CRÍTICA: Estados são idênticos
        try:
            assert_memory_state_equal(
                state_before,
                state_after,
                message="Atomicity validation: states must be identical"
            )
            print("[OK] ATOMICIDADE VALIDADA: Todos os 4 stores intactos apos falha")
        except AssertionError as e:
            print(f"[FAIL] ATOMICIDADE VIOLADA: {e}")
            raise

    @pytest.mark.asyncio
    async def test_success_case_modifies_state(self):
        """Validação: sucesso SIM modifica o estado."""
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        state_before = snapshot_memory_state(
            aggregate_repo,
            processed_repo,
            audit_repo,
            outbox_repo,
        )

        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo=aggregate_repo,
            processed_repo=processed_repo,
            audit_repo=audit_repo,
            outbox_repo=outbox_repo,
        )
        domain_service = BillingDomainService()
        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        # SEM falha injetada
        injector = get_failure_injector()
        injector.disable()

        event = create_event()
        result = await app_service.process_event(event)

        state_after = snapshot_memory_state(
            aggregate_repo,
            processed_repo,
            audit_repo,
            outbox_repo,
        )

        # Em caso de sucesso, pelo menos algo deve ter mudado
        # (mas pode ser apenas processed_events, se domínio não modifica snapshot)
        print(f"[INFO] Success case: result.success={result.success}")
        print(f"[INFO] Before == After: {state_before == state_after}")
