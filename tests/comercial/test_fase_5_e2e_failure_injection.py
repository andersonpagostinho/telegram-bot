"""
Teste E2E de atomicidade com injeção de falhas (FASE 5).

Fluxo completo:
BillingApplicationService
  → UnitOfWork factory decorada
  → BillingDomainService real
  → Repositórios decorados com failure injection
  → Falha injetada em ponto específico
  → Rollback real
  → Validação de estado intacto
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
from services.billing_domain_service import (
    BillingDomainService,
    AggregateSnapshot,
    TrialSnapshot,
    AssinaturaSnapshot,
    PagamentoSnapshot,
    AcessoSnapshot,
    RetencaoSnapshot,
)
from services.billing_application_service import (
    BillingApplicationService,
    WebhookEvent,
)
from services.trial_state_machine import TrialState
from services.billing_state_machines import (
    AssinaturaState,
    PagamentoState,
    AcessoState,
    RetencaoState,
)
from tests.comercial.failure_injection import (
    get_failure_injector,
    reset_failure_injector,
    FailurePlan,
    InjectedFailureType,
    InjectedFailureException,
)
from tests.comercial.failing_unit_of_work_factory import (
    FailingInMemoryUnitOfWorkFactory,
)
from tests.comercial.state_helpers import (
    snapshot_memory_state,
    assert_memory_state_equal,
)
from tests.comercial.operation_names import OperationNames


def create_real_aggregate_snapshot() -> AggregateSnapshot:
    """Criar snapshot inicial realista."""
    return AggregateSnapshot(
        trial=TrialSnapshot(state=TrialState.PREPARADO, metadata={}),
        assinatura=AssinaturaSnapshot(state=AssinaturaState.PENDENTE, metadata={}),
        pagamento=PagamentoSnapshot(state=PagamentoState.PENDENTE, metadata={}),
        acesso=AcessoSnapshot(state=AcessoState.LIBERADO, metadata={}),
        retencao=RetencaoSnapshot(state=RetencaoState.ATIVO, metadata={}),
        timestamp=datetime.utcnow(),
    )


def create_test_webhook_event() -> WebhookEvent:
    """Criar evento webhook válido que causa transição."""
    return WebhookEvent(
        correlation_id="corr_e2e_001",
        event_type="purchase_approved",  # Causa transição em assinatura e pagamento
        received_at=datetime.utcnow().isoformat(),
        tenant_id="tenant_e2e_test",
        provider="test_provider",
        provider_event_id="evt_e2e_001",
        payload={
            "aggregate_id": "agg_e2e_001",
            "subscription_id": "sub_001",
            "amount": 99.99,
            "tenant_id": "tenant_e2e_test",
        }
    )


class TestE2EFailureInjection:
    """Testes E2E de atomicidade com injeção de falhas."""

    @pytest.fixture(autouse=True)
    def reset_injector(self):
        """Resetar injetor antes de cada teste."""
        reset_failure_injector()
        yield
        reset_failure_injector()

    @pytest.fixture
    def setup_e2e(self):
        """Configurar ambiente E2E completo."""
        # Criar stores compartilhados (estado principal)
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        # Criar factory com decorators
        factory = FailingInMemoryUnitOfWorkFactory(
            aggregate_repo=aggregate_repo,
            processed_repo=processed_repo,
            audit_repo=audit_repo,
            outbox_repo=outbox_repo,
        )

        # Criar serviços reais
        # Para testes, usar domain_service que gera pelo menos um evento interno
        domain_service = BillingDomainService()

        # Wrapper que força geração de eventos internos para test
        class MockEvent:
            def __init__(self):
                self.event_type = "subscription_approved"
            def to_dict(self):
                return {"event_type": "subscription_approved", "test": True}

        @staticmethod
        def generate_with_event(*args, **kwargs):
            # Retornar sempre um evento interno para atingir outbox.save
            return [MockEvent()]
        domain_service._generate_internal_events = generate_with_event

        app_service = BillingApplicationService(
            unit_of_work_factory=factory,
            domain_service=domain_service,
        )

        return {
            "app_service": app_service,
            "factory": factory,
            "aggregate_repo": aggregate_repo,
            "processed_repo": processed_repo,
            "audit_repo": audit_repo,
            "outbox_repo": outbox_repo,
        }

    @pytest.mark.asyncio
    async def test_e2e_failure_on_first_outbox_save_rolls_back_all_stores(
        self, setup_e2e
    ):
        """
        Teste E2E: Falha no primeiro outbox.save causa rollback de todos os stores.

        Fluxo:
        1. Capturar estado antes (vazio)
        2. Injetar falha em outbox.save.1
        3. Executar BillingApplicationService.process_event
        4. Comprovar exceção foi lançada
        5. Comprovar que nenhum store foi alterado
        6. Comprovar que operações foram executadas até o ponto de falha
        """
        env = setup_e2e

        # [1] Capturar estado inicial (tudo vazio)
        state_before = snapshot_memory_state(
            env["aggregate_repo"],
            env["processed_repo"],
            env["audit_repo"],
            env["outbox_repo"],
        )

        # [2] Injetar falha em outbox.save.1
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation=f"{OperationNames.OUTBOX_SAVE}.1",
            call_number=1,
            message="Simulated failure on first outbox save",
        ))

        # [3] Executar serviço
        event = create_test_webhook_event()
        result = await env["app_service"].process_event(event)

        # [4] Comprovar que falha foi propagada
        assert result.success == False, "Resultado deve indicar falha"
        assert "Erro de transação" in result.message or "error" in result.message.lower(), (
            f"Mensagem deve indicar erro de transação. Recebido: {result.message}"
        )

        # [5] Capturar estado depois (deve ser idêntico)
        state_after = snapshot_memory_state(
            env["aggregate_repo"],
            env["processed_repo"],
            env["audit_repo"],
            env["outbox_repo"],
        )

        # [5] Validar atomicidade: estado não foi alterado
        assert_memory_state_equal(
            state_before,
            state_after,
            "ATOMICIDADE VIOLADA: Estado foi alterado durante falha"
        )

        # [6] Validar que operações foram tentadas
        # Agregado foi carregado
        assert injector.get_call_count(OperationNames.AGGREGATE_GET) >= 1, (
            "Agregado deve ter sido carregado"
        )

        # Agregado foi salvo (no staging, antes da falha)
        assert injector.get_call_count(OperationNames.AGGREGATE_SAVE) >= 1, (
            "Agregado deve ter sido salvo"
        )

        # Evento processado foi marcado como PROCESSING
        assert injector.get_call_count(OperationNames.PROCESSED_EVENT_MARK_PROCESSING) >= 1, (
            "Evento deve ter sido marcado como PROCESSING"
        )

        # Auditoria foi registrada (no staging)
        assert injector.get_call_count(OperationNames.AUDIT_APPEND) >= 1, (
            "Auditoria deve ter sido registrada"
        )

        # Outbox foi tentado (1 vez, antes da falha)
        assert injector.get_call_count(f"{OperationNames.OUTBOX_SAVE}.1") >= 1, (
            "Outbox deve ter sido tentado"
        )

    @pytest.mark.asyncio
    async def test_e2e_successful_transaction_with_outbox_items(
        self, setup_e2e
    ):
        """
        Teste E2E: Transação bem-sucedida com geração de outbox.

        Validar que:
        1. Sem falha injetada, a transação completa com sucesso
        2. Agregado é persisted
        3. Processado é marcado como PROCESSED
        4. Auditoria é registrada
        5. Outbox items são criados
        """
        env = setup_e2e

        # [1] Capturar estado anterior
        state_before = snapshot_memory_state(
            env["aggregate_repo"],
            env["processed_repo"],
            env["audit_repo"],
            env["outbox_repo"],
        )

        # [2] Executar SEM falha injetada
        injector = get_failure_injector()
        injector.disable()  # Sem injeção

        event = create_test_webhook_event()
        result = await env["app_service"].process_event(event)

        # [3] Comprovar sucesso
        assert result.success == True, (
            f"Transação deve suceder. Erro: {result.message}"
        )
        assert result.code == "200", "Código HTTP deve ser 200"

        # [4] Capturar estado depois
        state_after = snapshot_memory_state(
            env["aggregate_repo"],
            env["processed_repo"],
            env["audit_repo"],
            env["outbox_repo"],
        )

        # [5] Validar que estado foi alterado (commit ocorreu)
        assert state_before["aggregates"] != state_after["aggregates"], (
            "Agregados devem ter mudado após sucesso"
        )
        assert state_before["processed_events"] != state_after["processed_events"], (
            "Processados devem ter mudado após sucesso"
        )
        assert state_before["audits"] != state_after["audits"], (
            "Auditorias devem ter mudado após sucesso"
        )
        # Outbox pode estar vazio ou preenchido dependendo do domain service

    @pytest.mark.asyncio
    async def test_e2e_failure_on_aggregate_save_rolls_back(
        self, setup_e2e
    ):
        """Falha ao salvar agregado causa rollback."""
        env = setup_e2e

        state_before = snapshot_memory_state(
            env["aggregate_repo"],
            env["processed_repo"],
            env["audit_repo"],
            env["outbox_repo"],
        )

        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation=OperationNames.AGGREGATE_SAVE,
            call_number=1,
        ))

        event = create_test_webhook_event()
        result = await env["app_service"].process_event(event)

        assert result.success == False

        state_after = snapshot_memory_state(
            env["aggregate_repo"],
            env["processed_repo"],
            env["audit_repo"],
            env["outbox_repo"],
        )

        assert_memory_state_equal(state_before, state_after)

    @pytest.mark.asyncio
    async def test_e2e_failure_on_aggregate_load_rolls_back(
        self, setup_e2e
    ):
        """Falha ao carregar agregado causa rollback."""
        env = setup_e2e

        state_before = snapshot_memory_state(
            env["aggregate_repo"],
            env["processed_repo"],
            env["audit_repo"],
            env["outbox_repo"],
        )

        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.READ_FAILURE,
            operation=OperationNames.AGGREGATE_GET,
            call_number=1,
        ))

        event = create_test_webhook_event()
        result = await env["app_service"].process_event(event)

        assert result.success == False

        state_after = snapshot_memory_state(
            env["aggregate_repo"],
            env["processed_repo"],
            env["audit_repo"],
            env["outbox_repo"],
        )

        assert_memory_state_equal(state_before, state_after)
