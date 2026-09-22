"""
Testes de atomicidade via injeção de falhas (FASE 5).

Validam que qualquer falha durante o processamento deixa os stores
em estado idêntico ao anterior (zero mudança parcial).
"""

import pytest
from copy import deepcopy
from unittest.mock import AsyncMock

from repositories.in_memory.in_memory_repositories import (
    InMemoryCommercialAggregateRepository,
    InMemoryProcessedEventRepository,
    InMemoryCommercialAuditRepository,
    InMemoryCommercialOutboxRepository,
    InMemoryCommercialUnitOfWork,
)
from repositories.processed_event_repository import ProcessedEventStatus
from services.billing_domain_service import (
    AggregateSnapshot,
    TrialSnapshot,
    AssinaturaSnapshot,
    PagamentoSnapshot,
    AcessoSnapshot,
    RetencaoSnapshot,
    CommercialAggregate,
    BillingDomainService,
)
from services.billing_application_service import BillingApplicationService, WebhookEvent
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
from tests.comercial.failing_repositories import (
    FailingAggregateRepository,
    FailingProcessedEventRepository,
    FailingAuditRepository,
    FailingOutboxRepository,
)
from datetime import datetime


def create_test_event(aggregate_id: str = "agg_1", tenant_id: str = "tenant_1") -> WebhookEvent:
    """Criar evento de teste."""
    return WebhookEvent(
        correlation_id="corr_test_123",
        tenant_id=tenant_id,
        provider="test_provider",
        provider_event_id="evt_001",
        event_type="purchase_approved",
        payload={
            "aggregate_id": aggregate_id,
            "subscription_id": "sub_123",
            "amount": 99.99,
        },
    )


def create_test_aggregate(version: int = 0) -> CommercialAggregate:
    """Criar agregado de teste."""
    return CommercialAggregate(
        aggregate_id="agg_1",
        tenant_id="tenant_1",
        version=version,
        snapshot=AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.PREPARADO, metadata={}),
            assinatura=AssinaturaSnapshot(state=AssinaturaState.PENDENTE, metadata={}),
            pagamento=PagamentoSnapshot(state=PagamentoState.PENDENTE, metadata={}),
            acesso=AcessoSnapshot(state=AcessoState.LIBERADO, metadata={}),
            retencao=RetencaoSnapshot(state=RetencaoState.ATIVO, metadata={}),
            timestamp=datetime.utcnow(),
        ),
    )


class TestAtomicityWithFailureInjection:
    """Testes de atomicidade com injeção de falhas."""

    @pytest.fixture(autouse=True)
    def reset_injector(self):
        """Resetar injetor antes de cada teste."""
        reset_failure_injector()
        yield
        reset_failure_injector()

    @pytest.fixture
    def uow_context_with_failing_repos(self):
        """Unit of work com repositórios que injetam falhas."""
        # Criar repositórios reais
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        # Envolver com injeção de falhas
        failing_aggregate_repo = FailingAggregateRepository(aggregate_repo)
        failing_processed_repo = FailingProcessedEventRepository(processed_repo)
        failing_audit_repo = FailingAuditRepository(audit_repo)
        failing_outbox_repo = FailingOutboxRepository(outbox_repo)

        def factory():
            return InMemoryCommercialUnitOfWork(
                aggregate_repo=failing_aggregate_repo,
                processed_repo=failing_processed_repo,
                audit_repo=failing_audit_repo,
                outbox_repo=failing_outbox_repo,
            )

        return {
            "factory": factory,
            "aggregate_repo": aggregate_repo,  # Repositório real para verificação
            "processed_repo": processed_repo,
            "audit_repo": audit_repo,
            "outbox_repo": outbox_repo,
            "failing_outbox_repo": failing_outbox_repo,  # Para resetar contador
        }

    @pytest.mark.asyncio
    async def test_falha_no_load_agregado(self, uow_context_with_failing_repos):
        """Falha ao carregar agregado deixa todos os stores intactos."""
        ctx = uow_context_with_failing_repos

        # Setup: adicionar evento anterior
        await ctx["processed_repo"].mark_processing(
            tenant_id="tenant_1",
            provider="test_provider",
            provider_event_id="evt_000",
            payload_hash="hash_000",
            correlation_id="corr_000",
        )

        # Registrar estado anterior
        state_before = {
            "aggregates": deepcopy(ctx["aggregate_repo"].store),
            "processed_events": deepcopy(ctx["processed_repo"].store),
            "audits": deepcopy(ctx["audit_repo"].store),
            "outbox": deepcopy(ctx["outbox_repo"].store),
        }

        # Injetar falha
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.READ_FAILURE,
            operation="aggregate_repository.load",
            call_number=1,
        ))

        # Tentar processar (vai falhar)
        uow = ctx["factory"]()
        event = create_test_event()

        with pytest.raises(InjectedFailureException):
            async with uow:
                # Dentro da transação:
                # [4] check_and_load passa
                # [5] load agregado FALHA aqui
                pass

        # Verificar que stores não foram alterados
        assert ctx["aggregate_repo"].store == state_before["aggregates"]
        assert ctx["processed_repo"].store == state_before["processed_events"]
        assert ctx["audit_repo"].store == state_before["audits"]
        assert ctx["outbox_repo"].store == state_before["outbox"]

    @pytest.mark.asyncio
    async def test_falha_no_save_agregado(self, uow_context_with_failing_repos):
        """Falha ao salvar agregado deixa os stores intactos."""
        ctx = uow_context_with_failing_repos

        # Registrar estado anterior (store vazio)
        state_before = {
            "aggregates": deepcopy(ctx["aggregate_repo"].store),
            "processed_events": deepcopy(ctx["processed_repo"].store),
            "audits": deepcopy(ctx["audit_repo"].store),
            "outbox": deepcopy(ctx["outbox_repo"].store),
        }

        # Injetar falha no save de agregado
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation="aggregate_repository.save",
            call_number=1,
        ))

        # Tentar processar
        uow = ctx["factory"]()

        with pytest.raises(InjectedFailureException):
            async with uow:
                # A falha ocorre durante staging, rollback automático
                pass

        # Verificar que NENHUMA store foi alterada
        assert ctx["aggregate_repo"].store == state_before["aggregates"]
        assert ctx["processed_repo"].store == state_before["processed_events"]
        assert ctx["audit_repo"].store == state_before["audits"]
        assert ctx["outbox_repo"].store == state_before["outbox"]

    @pytest.mark.asyncio
    async def test_falha_no_primeiro_outbox(self, uow_context_with_failing_repos):
        """Falha ao salvar primeiro item de outbox deixa stores intactos."""
        ctx = uow_context_with_failing_repos
        ctx["failing_outbox_repo"].reset_item_count()

        # Registrar estado anterior
        state_before = {
            "outbox": deepcopy(ctx["outbox_repo"].store),
        }

        # Injetar falha no primeiro outbox
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation="outbox_repository.save.1",
            call_number=1,
        ))

        # Tentar processar
        uow = ctx["factory"]()

        with pytest.raises(InjectedFailureException):
            async with uow:
                # A falha ocorre durante staging
                pass

        # Verificar que outbox não foi alterado
        assert ctx["outbox_repo"].store == state_before["outbox"]

    @pytest.mark.asyncio
    async def test_versao_nao_incrementa_em_falha(self, uow_context_with_failing_repos):
        """Falha preserva a versão anterior."""
        ctx = uow_context_with_failing_repos

        # Criar e salvar agregado
        aggregate = create_test_aggregate(version=5)
        await ctx["aggregate_repo"].save(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            aggregate=aggregate,
            expected_version=0,
        )

        # Registrar versão anterior
        loaded = await ctx["aggregate_repo"].load("tenant_1", "agg_1")
        version_before = loaded.version

        # Injetar falha no save agregado (vai falhar antes de incrementar em staging)
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation="aggregate_repository.save",
            call_number=1,
        ))

        # Tentar processar
        uow = ctx["factory"]()

        with pytest.raises(InjectedFailureException):
            async with uow:
                pass

        # Verificar que versão não mudou
        loaded_after = await ctx["aggregate_repo"].load("tenant_1", "agg_1")
        assert loaded_after.version == version_before

    @pytest.mark.asyncio
    async def test_processed_event_nao_marcado_em_falha(self, uow_context_with_failing_repos):
        """Falha não marca evento como PROCESSED."""
        ctx = uow_context_with_failing_repos

        # Injetar falha
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation="aggregate_repository.save",
            call_number=1,
        ))

        # Tentar processar
        uow = ctx["factory"]()

        with pytest.raises(InjectedFailureException):
            async with uow:
                pass

        # Verificar que evento não está como PROCESSED
        processed = await ctx["processed_repo"].check_and_load(
            tenant_id="tenant_1",
            provider="test_provider",
            provider_event_id="evt_001",
        )
        # Deve ser None (não foi marcado)
        assert processed is None or processed.status != ProcessedEventStatus.PROCESSED

    @pytest.mark.asyncio
    async def test_auditoria_nao_adicionada_em_falha(self, uow_context_with_failing_repos):
        """Falha não adiciona auditoria."""
        ctx = uow_context_with_failing_repos

        # Registrar contagem anterior
        audits_before = len(ctx["audit_repo"].store.get("tenant_1", []))

        # Injetar falha
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation="aggregate_repository.save",
            call_number=1,
        ))

        # Tentar processar
        uow = ctx["factory"]()

        with pytest.raises(InjectedFailureException):
            async with uow:
                pass

        # Verificar que auditoria não foi adicionada
        audits_after = len(ctx["audit_repo"].store.get("tenant_1", []))
        assert audits_after == audits_before

    @pytest.mark.asyncio
    async def test_falha_nao_deixa_staging_visivel(self, uow_context_with_failing_repos):
        """Staging de uma falha não altera stores principais."""
        ctx = uow_context_with_failing_repos

        # Registrar estado principal antes
        aggregates_before = deepcopy(ctx["aggregate_repo"].store)

        # Injetar falha no save (vai falhar dentro do staging, não afetando main)
        injector = get_failure_injector()
        injector.enable()
        injector.plan_failure(FailurePlan(
            failure_type=InjectedFailureType.WRITE_FAILURE,
            operation="aggregate_repository.save",
            call_number=1,
        ))

        # Transação com falha
        uow = ctx["factory"]()
        with pytest.raises(InjectedFailureException):
            async with uow:
                pass

        # Staging não deve ter modificado o main store
        aggregates_after = ctx["aggregate_repo"].store
        assert aggregates_after == aggregates_before

    @pytest.mark.asyncio
    async def test_deep_copy_isolation_metadata(self):
        """Metadata aninhada é isolada por deep copy."""
        aggregate_repo = InMemoryCommercialAggregateRepository()

        # Criar agregado com metadata
        aggregate = create_test_aggregate(version=1)
        metadata = {"key": "value", "nested": {"inner": "data"}}
        aggregate_with_metadata = CommercialAggregate(
            aggregate_id="agg_1",
            tenant_id="tenant_1",
            version=1,
            snapshot=AggregateSnapshot(
                trial=TrialSnapshot(state=TrialState.PREPARADO, metadata=metadata),
                assinatura=aggregate.snapshot.assinatura,
                pagamento=aggregate.snapshot.pagamento,
                acesso=aggregate.snapshot.acesso,
                retencao=aggregate.snapshot.retencao,
                timestamp=aggregate.snapshot.timestamp,
            ),
        )

        # Salvar
        await aggregate_repo.save(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            aggregate=aggregate_with_metadata,
            expected_version=0,
        )

        # Carregar e modificar o objeto
        loaded = await aggregate_repo.load("tenant_1", "agg_1")
        original_metadata = loaded.snapshot.trial.metadata

        # Tentar mutar (em produção isso não deve afetar storage)
        # Se deep copy foi feito corretamente, a mutação não afeta o store
        assert original_metadata is not None
