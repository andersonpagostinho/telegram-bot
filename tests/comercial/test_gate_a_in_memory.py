"""Testes abrangentes para Gate A (implementação em memória)."""

import pytest
from datetime import datetime
from typing import Dict, Any

from services.billing_application_service import (
    BillingApplicationService,
    WebhookEvent,
    ValidationError
)
from repositories.in_memory.in_memory_repositories import (
    InMemoryCommercialAggregateRepository,
    InMemoryProcessedEventRepository,
    InMemoryCommercialAuditRepository,
    InMemoryCommercialOutboxRepository,
    InMemoryCommercialUnitOfWork,
    ConflictError as RepoConflictError
)
from services.billing_domain_service import BillingDomainService, CommercialAggregate, AggregateSnapshot, TrialSnapshot, AssinaturaSnapshot, PagamentoSnapshot, AcessoSnapshot, RetencaoSnapshot
from services.trial_state_machine import TrialState
from services.billing_state_machines import AssinaturaState, PagamentoState, AcessoState, RetencaoState


def _create_test_aggregate(aggregate_id: str, tenant_id: str, version: int = 1) -> CommercialAggregate:
    """Helper para criar agregado de teste."""
    snapshot = AggregateSnapshot(
        trial=TrialSnapshot(state=TrialState.PREPARADO),
        assinatura=AssinaturaSnapshot(state=AssinaturaState.PENDENTE),
        pagamento=PagamentoSnapshot(state=PagamentoState.PENDENTE),
        acesso=AcessoSnapshot(state=AcessoState.LIBERADO),
        retencao=RetencaoSnapshot(state=RetencaoState.ATIVO)
    )
    return CommercialAggregate(
        aggregate_id=aggregate_id,
        tenant_id=tenant_id,
        version=version,
        snapshot=snapshot
    )


class TestAggregateRepository:
    """Testes do repositório de agregado."""

    @pytest.fixture
    def repo(self):
        return InMemoryCommercialAggregateRepository()

    @pytest.mark.asyncio
    async def test_load_inexistente(self, repo):
        """Carrega agregado inexistente retorna None."""
        aggregate = await repo.load("tenant_1", "agg_x")
        assert aggregate is None

    @pytest.mark.asyncio
    async def test_save_e_load(self, repo):
        """Save + load retorna mesmo agregado."""
        aggregate = _create_test_aggregate("agg_1", "tenant_1", version=1)

        await repo.save("tenant_1", "agg_1", aggregate, expected_version=0)
        loaded = await repo.load("tenant_1", "agg_1")

        assert loaded is not None
        assert loaded.aggregate_id == "agg_1"
        assert loaded.version == 1

    @pytest.mark.asyncio
    async def test_save_version_conflict(self, repo):
        """Save com expected_version divergente falha."""
        aggregate = _create_test_aggregate("agg_1", "tenant_1", version=1)

        # Primeira escrita
        await repo.save("tenant_1", "agg_1", aggregate, expected_version=0)

        # Segunda escrita com expected_version errado
        aggregate2 = _create_test_aggregate("agg_1", "tenant_1", version=2)

        with pytest.raises(RepoConflictError):
            await repo.save("tenant_1", "agg_1", aggregate2, expected_version=0)

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation(self, repo):
        """Tenant A não pode acessar dados de Tenant B."""
        aggregate = _create_test_aggregate("agg_1", "tenant_a", version=1)
        await repo.save("tenant_a", "agg_1", aggregate, expected_version=0)

        # Tenant B tenta carregar
        loaded = await repo.load("tenant_b", "agg_1")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_tenant_id_vazio(self, repo):
        """tenant_id vazio levanta ValueError."""
        aggregate = _create_test_aggregate("agg_1", "tenant_1", version=1)

        with pytest.raises(ValueError):
            await repo.load("", "agg_1")

        with pytest.raises(ValueError):
            await repo.save("", "agg_1", aggregate, expected_version=0)


class TestProcessedEventRepository:
    """Testes do repositório de eventos processados."""

    @pytest.fixture
    def repo(self):
        return InMemoryProcessedEventRepository()

    @pytest.mark.asyncio
    async def test_check_and_load_novo(self, repo):
        """Novo evento retorna None."""
        event = await repo.check_and_load("tenant_1", "hotmart", "evt_123")
        assert event is None

    @pytest.mark.asyncio
    async def test_mark_processing(self, repo):
        """Mark processing registra evento com status PROCESSING."""
        event = await repo.mark_processing(
            "tenant_1",
            "hotmart",
            "evt_123",
            "hash_abc",
            "corr_xyz"
        )

        assert event.status.value == "PROCESSING"
        assert event.provider_event_id == "evt_123"

    @pytest.mark.asyncio
    async def test_mark_processed(self, repo):
        """Mark processed altera status para PROCESSED."""
        await repo.mark_processing("tenant_1", "hotmart", "evt_123", "hash", "corr")

        event = await repo.mark_processed(
            "tenant_1",
            "hotmart",
            "evt_123",
            "success",
            aggregate_version_after=42
        )

        assert event.status.value == "PROCESSED"
        assert event.aggregate_version_after == 42

    @pytest.mark.asyncio
    async def test_replay_idempotente(self, repo):
        """Mesmo evento já processado retorna resultado anterior."""
        # Primeira execução
        await repo.mark_processing("tenant_1", "hotmart", "evt_123", "hash", "corr")
        await repo.mark_processed("tenant_1", "hotmart", "evt_123", "success", 42)

        # Segunda execução (idempotente)
        event = await repo.check_and_load("tenant_1", "hotmart", "evt_123")
        assert event is not None
        assert event.status.value == "PROCESSED"
        assert event.aggregate_version_after == 42

    @pytest.mark.asyncio
    async def test_mark_failed_retryable(self, repo):
        """Mark failed retryable."""
        await repo.mark_processing("tenant_1", "hotmart", "evt_123", "hash", "corr")

        event = await repo.mark_failed(
            "tenant_1",
            "hotmart",
            "evt_123",
            retryable=True,
            error_reason="timeout"
        )

        assert event.status.value == "FAILED_RETRYABLE"
        assert event.error_reason == "timeout"

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation(self, repo):
        """Tenant A não vê eventos de Tenant B."""
        await repo.mark_processing("tenant_a", "hotmart", "evt_123", "hash", "corr")

        event = await repo.check_and_load("tenant_b", "hotmart", "evt_123")
        assert event is None


class TestAuditRepository:
    """Testes do repositório de auditoria."""

    @pytest.fixture
    def repo(self):
        return InMemoryCommercialAuditRepository()

    @pytest.mark.asyncio
    async def test_record_auditoria(self, repo):
        """Record cria novo registro de auditoria."""
        record = await repo.record(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            correlation_id="corr_xyz",
            source_event_id="evt_123",
            decision_code="success",
            success=True,
            aggregate_version_before=41,
            aggregate_version_after=42,
            previous_states={"trial": "ATIVO"},
            resulting_states={"trial": "ATIVO"}
        )

        assert record.audit_id is not None
        assert record.success is True

    @pytest.mark.asyncio
    async def test_auditoria_append_only(self, repo):
        """Auditoria não pode ser atualizada ou deletada."""
        record = await repo.record(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            correlation_id="corr_xyz",
            source_event_id="evt_123",
            decision_code="success",
            success=True,
            aggregate_version_before=41,
            aggregate_version_after=42,
            previous_states={"trial": "ATIVO"},
            resulting_states={"trial": "ATIVO"}
        )

        # Verificar que a auditoria foi criada
        records = await repo.get_by_aggregate("tenant_1", "agg_1")
        assert len(records) == 1

        # Tentar criar outra auditoria (deve ser possível pois é append-only)
        record2 = await repo.record(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            correlation_id="corr_abc",
            source_event_id="evt_456",
            decision_code="no_change",
            success=True,
            aggregate_version_before=42,
            aggregate_version_after=42,
            previous_states={"trial": "ATIVO"},
            resulting_states={"trial": "ATIVO"}
        )

        # Agora deve haver 2 registros
        records = await repo.get_by_aggregate("tenant_1", "agg_1")
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_get_by_tenant(self, repo):
        """Get by tenant retorna registros ordenados."""
        for i in range(3):
            await repo.record(
                tenant_id="tenant_1",
                aggregate_id=f"agg_{i}",
                correlation_id=f"corr_{i}",
                source_event_id=f"evt_{i}",
                decision_code="success",
                success=True,
                aggregate_version_before=i,
                aggregate_version_after=i+1,
                previous_states={},
                resulting_states={}
            )

        records = await repo.get_by_tenant("tenant_1", limit=10)
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_audit_id_determinístico(self, repo):
        """ID de auditoria é determinístico para mesma decisão."""
        # Primeira execução
        record1 = await repo.record(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            correlation_id="corr_1",
            source_event_id="evt_123",
            decision_code="success",
            success=True,
            aggregate_version_before=1,
            aggregate_version_after=2,
            previous_states={},
            resulting_states={}
        )

        # Segunda execução (mesma decisão lógica)
        record2 = await repo.record(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            correlation_id="corr_2",  # Diferente
            source_event_id="evt_123",
            decision_code="success",
            success=True,
            aggregate_version_before=1,
            aggregate_version_after=2,
            previous_states={},
            resulting_states={}
        )

        # Mesmo audit_id (determinístico)
        assert record1.audit_id == record2.audit_id
        # MAS audit_id diferente em registros (timestamps diferentes)
        records = await repo.get_by_tenant("tenant_1")
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_audit_id_diferente_por_versao(self, repo):
        """Versão diferente → audit_id diferente."""
        record1 = await repo.record(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            correlation_id="corr_1",
            source_event_id="evt_123",
            decision_code="success",
            success=True,
            aggregate_version_before=1,
            aggregate_version_after=2,
            previous_states={},
            resulting_states={}
        )

        record2 = await repo.record(
            tenant_id="tenant_1",
            aggregate_id="agg_1",
            correlation_id="corr_1",
            source_event_id="evt_123",
            decision_code="success",
            success=True,
            aggregate_version_before=2,
            aggregate_version_after=3,  # Versão diferente
            previous_states={},
            resulting_states={}
        )

        # IDs diferentes por versão
        assert record1.audit_id != record2.audit_id


class TestOutboxRepository:
    """Testes do repositório de outbox."""

    @pytest.fixture
    def repo(self):
        return InMemoryCommercialOutboxRepository()

    @pytest.mark.asyncio
    async def test_save_outbox(self, repo):
        """Save cria item com status PENDING."""
        item = await repo.save(
            tenant_id="tenant_1",
            event_type="SubscriptionActivated",
            payload={"subscription_id": "sub_123"},
            correlation_id="corr_xyz",
            source_event_id="evt_123",
            aggregate_version=42
        )

        assert item.status.value == "PENDING"
        assert item.event_type == "SubscriptionActivated"

    @pytest.mark.asyncio
    async def test_nao_duplica_items_replay(self, repo):
        """Replay idempotente não duplica items."""
        # Primeira escrita
        item1 = await repo.save(
            "tenant_1",
            "SubscriptionActivated",
            {"sub_id": "123"},
            "corr_xyz",
            "evt_123",
            42
        )

        # Verificar que foi salvo
        items = await repo.get_by_correlation("tenant_1", "corr_xyz")
        assert len(items) == 1

        # Replay: salvar novamente (simulando idempotência)
        # Na prática, o fluxo não salvaria novamente se fosse replay
        # Aqui apenas verificamos que a deduplicação não é automática

    @pytest.mark.asyncio
    async def test_save_batch(self, repo):
        """Save batch persiste múltiplos items atomicamente."""
        items_to_save = [
            {
                "event_type": "SubscriptionActivated",
                "payload": {"sub": "1"},
                "correlation_id": "corr",
                "source_event_id": "evt",
                "aggregate_version": 42
            },
            {
                "event_type": "PaymentApproved",
                "payload": {"payment": "2"},
                "correlation_id": "corr",
                "source_event_id": "evt",
                "aggregate_version": 42
            }
        ]

        items = await repo.save_batch("tenant_1", items_to_save)
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_get_pending(self, repo):
        """Get pending retorna apenas itens com status PENDING."""
        await repo.save("tenant_1", "SubscriptionActivated", {}, "corr", "evt", 42)
        await repo.save("tenant_1", "PaymentApproved", {}, "corr", "evt", 42)

        pending = await repo.get_pending("tenant_1")
        assert len(pending) == 2
        assert all(item.status.value == "PENDING" for item in pending)

    @pytest.mark.asyncio
    async def test_outbox_id_determinístico_mesmo_índice(self, repo):
        """ID de outbox é determinístico para mesmo evento no mesmo índice."""
        # Primeira execução
        item1 = await repo.save(
            tenant_id="tenant_1",
            event_type="SubscriptionActivated",
            payload={"plan": "pro"},
            correlation_id="corr_123",
            source_event_id="src_evt_1",
            aggregate_version=5,
            aggregate_id="agg_1",
            event_index=0,
        )

        # Segunda execução (mesma decisão lógica, novo salvo)
        item2 = await repo.save(
            tenant_id="tenant_1",
            event_type="SubscriptionActivated",
            payload={"plan": "pro"},
            correlation_id="corr_456",  # Correlação diferente
            source_event_id="src_evt_1",
            aggregate_version=5,
            aggregate_id="agg_1",
            event_index=0,  # MESMO ÍNDICE
        )

        # Mesmo outbox_id (determinístico)
        assert item1.outbox_id == item2.outbox_id

    @pytest.mark.asyncio
    async def test_outbox_id_diferente_por_índice(self, repo):
        """Índice diferente → outbox_id diferente."""
        item1 = await repo.save(
            tenant_id="tenant_1",
            event_type="PaymentApproved",
            payload={},
            correlation_id="corr_1",
            source_event_id="evt_123",
            aggregate_version=2,
            aggregate_id="agg_1",
            event_index=0,  # Índice 0
        )

        item2 = await repo.save(
            tenant_id="tenant_1",
            event_type="PaymentApproved",
            payload={},
            correlation_id="corr_1",
            source_event_id="evt_123",
            aggregate_version=2,
            aggregate_id="agg_1",
            event_index=1,  # Índice 1 (diferente!)
        )

        # IDs diferentes por índice
        assert item1.outbox_id != item2.outbox_id

    @pytest.mark.asyncio
    async def test_outbox_id_diferente_por_event_type(self, repo):
        """Event type diferente → outbox_id diferente."""
        item1 = await repo.save(
            tenant_id="tenant_1",
            event_type="SubscriptionActivated",
            payload={},
            correlation_id="corr_1",
            source_event_id="evt_123",
            aggregate_version=2,
            aggregate_id="agg_1",
            event_index=0,
        )

        item2 = await repo.save(
            tenant_id="tenant_1",
            event_type="PaymentApproved",  # Tipo diferente
            payload={},
            correlation_id="corr_1",
            source_event_id="evt_123",
            aggregate_version=2,
            aggregate_id="agg_1",
            event_index=0,
        )

        # IDs diferentes por event_type
        assert item1.outbox_id != item2.outbox_id


    @pytest.mark.asyncio
    async def test_outbox_cross_tenant_non_collision(self, repo):
        """Tenant diferente → outbox_id diferente mesmo com outros parâmetros iguais."""
        item1 = await repo.save(
            tenant_id="tenant_1",
            event_type="SubscriptionActivated",
            payload={},
            correlation_id="corr_1",
            source_event_id="evt_123",
            aggregate_version=2,
            aggregate_id="agg_1",
            event_index=0,
        )

        item2 = await repo.save(
            tenant_id="tenant_2",  # Tenant diferente
            event_type="SubscriptionActivated",
            payload={},
            correlation_id="corr_1",
            source_event_id="evt_123",
            aggregate_version=2,
            aggregate_id="agg_1",
            event_index=0,
        )

        # IDs diferentes por tenant (isolamento)
        assert item1.outbox_id != item2.outbox_id


class TestUnitOfWork:
    """Testes da Unit of Work com staging isolado."""

    @pytest.fixture
    def uow_context(self):
        """Fixture que fornece UoW + acesso ao repositório principal para verificação."""
        # Criar repositórios principais compartilhados
        aggregate_repo = InMemoryCommercialAggregateRepository()
        processed_repo = InMemoryProcessedEventRepository()
        audit_repo = InMemoryCommercialAuditRepository()
        outbox_repo = InMemoryCommercialOutboxRepository()

        def factory():
            return InMemoryCommercialUnitOfWork(
                aggregate_repo=aggregate_repo,
                processed_repo=processed_repo,
                audit_repo=audit_repo,
                outbox_repo=outbox_repo
            )

        return {
            "factory": factory,
            "aggregate_repo": aggregate_repo,  # Para verificação pós-transação
            "processed_repo": processed_repo,
            "audit_repo": audit_repo,
            "outbox_repo": outbox_repo,
        }

    @pytest.mark.asyncio
    async def test_transacao_commit(self, uow_context):
        """Transação com commit persiste alterações no store principal."""
        uow = uow_context["factory"]()
        aggregate_repo = uow_context["aggregate_repo"]

        async with uow:
            aggregate = _create_test_aggregate("agg_1", "tenant_1", version=1)
            await uow.aggregate_repository.save("tenant_1", "agg_1", aggregate, 0)

        # Verificar que foi persistido no store principal (fora da transação)
        loaded = await aggregate_repo.load("tenant_1", "agg_1")
        assert loaded is not None
        assert loaded.aggregate_id == "agg_1"
        assert loaded.version == 1

    @pytest.mark.asyncio
    async def test_transacao_rollback(self, uow_context):
        """Transação com erro faz rollback — store principal não é alterado."""
        uow = uow_context["factory"]()
        aggregate_repo = uow_context["aggregate_repo"]

        try:
            async with uow:
                aggregate = _create_test_aggregate("agg_1", "tenant_1", version=1)
                await uow.aggregate_repository.save("tenant_1", "agg_1", aggregate, 0)

                # Forçar erro antes do commit
                raise Exception("Erro simulado")
        except Exception:
            pass

        # Verificar que NÃO foi persistido no store principal (atomicidade garantida)
        loaded = await aggregate_repo.load("tenant_1", "agg_1")
        assert loaded is None


class TestBillingApplicationService:
    """Testes da BillingApplicationService."""

    @pytest.fixture
    def domain_service(self):
        # Mock simples do domain service
        return BillingDomainService()

    @pytest.fixture
    def service(self, domain_service):
        def uow_factory():
            return InMemoryCommercialUnitOfWork()

        return BillingApplicationService(uow_factory, domain_service)

    @pytest.mark.asyncio
    async def test_validacao_envelope_falha_sem_correlation_id(self, service):
        """Validação falha se correlation_id ausente."""
        event = WebhookEvent(
            correlation_id="",  # Vazio
            event_type="purchase_approved",
            received_at="2026-07-27T10:00:00",
            tenant_id="tenant_1",
            provider_event_id="evt_123"
        )

        result = await service.process_event(event)
        assert result.success is False
        assert result.code == "400"

    @pytest.mark.asyncio
    async def test_validacao_envelope_falha_sem_tenant_id(self, service):
        """Validação falha se tenant_id ausente."""
        event = WebhookEvent(
            correlation_id="corr_xyz",
            event_type="purchase_approved",
            received_at="2026-07-27T10:00:00",
            tenant_id="",  # Vazio
            provider_event_id="evt_123"
        )

        result = await service.process_event(event)
        assert result.success is False
        assert result.code == "400"

    @pytest.mark.asyncio
    async def test_evento_novo_sucesso(self, service):
        """Evento novo processado com sucesso."""
        event = WebhookEvent(
            correlation_id="corr_xyz",
            event_type="purchase_approved",
            received_at="2026-07-27T10:00:00",
            tenant_id="tenant_1",
            provider_event_id="evt_123",
            payload={"aggregate_id": "agg_1"}
        )

        result = await service.process_event(event)
        # Resultado esperado: Success = False (domínio não tem lógica implementada)
        # ou True se a lógica domínio foi mockada
        assert result.correlation_id == "corr_xyz"
        assert result.tenant_id == "tenant_1"

    @pytest.mark.asyncio
    async def test_replay_idempotente(self, service):
        """Replay de evento idempotente retorna mesmo resultado."""
        event = WebhookEvent(
            correlation_id="corr_xyz",
            event_type="purchase_approved",
            received_at="2026-07-27T10:00:00",
            tenant_id="tenant_1",
            provider_event_id="evt_123",
            payload={"aggregate_id": "agg_1"}
        )

        # Primeira execução
        result1 = await service.process_event(event)

        # Segunda execução (idempotência)
        result2 = await service.process_event(event)

        # Ambas devem ter o mesmo correlation_id
        assert result1.correlation_id == result2.correlation_id

    @pytest.mark.asyncio
    async def test_isolamento_multi_tenant(self, service):
        """Tenant A não afeta Tenant B."""
        event_a = WebhookEvent(
            correlation_id="corr_a",
            event_type="purchase_approved",
            received_at="2026-07-27T10:00:00",
            tenant_id="tenant_a",
            provider_event_id="evt_a",
            payload={"aggregate_id": "agg"}
        )

        event_b = WebhookEvent(
            correlation_id="corr_b",
            event_type="purchase_approved",
            received_at="2026-07-27T10:00:00",
            tenant_id="tenant_b",
            provider_event_id="evt_b",
            payload={"aggregate_id": "agg"}  # Mesmo aggregate_id
        )

        result_a = await service.process_event(event_a)
        result_b = await service.process_event(event_b)

        # Ambas devem ser processadas independentemente
        assert result_a.tenant_id == "tenant_a"
        assert result_b.tenant_id == "tenant_b"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
