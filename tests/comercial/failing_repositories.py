"""
Repositórios decorados que injetam falhas determinísticas.

Usados apenas em testes de atomicidade. Envolvem repositórios reais
com lógica de falha sem modificar código de produção.
"""

from typing import Optional, Dict, Any, List
from repositories.commercial_aggregate_repository import CommercialAggregateRepository
from repositories.processed_event_repository import ProcessedEventRepository, ProcessedEvent, ProcessedEventStatus
from repositories.commercial_audit_repository import CommercialAuditRepository, AuditRecord
from repositories.commercial_outbox_repository import CommercialOutboxRepository, OutboxItem, OutboxStatus
from services.billing_domain_service import CommercialAggregate
from tests.comercial.failure_injection import (
    get_failure_injector,
    InjectedFailureType,
)
from tests.comercial.operation_names import OperationNames


class FailingAggregateRepository(CommercialAggregateRepository):
    """Agregado com injeção de falhas."""

    def __init__(self, wrapped: CommercialAggregateRepository):
        self.wrapped = wrapped

    async def load(self, tenant_id: str, aggregate_id: str) -> Optional[CommercialAggregate]:
        """Carregar com possível falha injetada."""
        get_failure_injector().check_and_increment(OperationNames.AGGREGATE_GET)
        return await self.wrapped.load(tenant_id, aggregate_id)

    async def save(
        self,
        tenant_id: str,
        aggregate_id: str,
        aggregate: CommercialAggregate,
        expected_version: int,
    ) -> bool:
        """Salvar com possível falha injetada."""
        get_failure_injector().check_and_increment(OperationNames.AGGREGATE_SAVE)
        return await self.wrapped.save(tenant_id, aggregate_id, aggregate, expected_version)

    async def delete_for_testing(self, tenant_id: str, aggregate_id: str) -> None:
        """Deletar para testes."""
        return await self.wrapped.delete_for_testing(tenant_id, aggregate_id)


class FailingProcessedEventRepository(ProcessedEventRepository):
    """Processed events com injeção de falhas."""

    def __init__(self, wrapped: ProcessedEventRepository):
        self.wrapped = wrapped

    async def check_and_load(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str,
    ) -> Optional[ProcessedEvent]:
        """Carregar com possível falha injetada."""
        get_failure_injector().check_and_increment(OperationNames.PROCESSED_EVENT_GET)
        return await self.wrapped.check_and_load(tenant_id, provider, provider_event_id)

    async def mark_processing(self, **kwargs) -> None:
        """Marcar como processando com possível falha."""
        get_failure_injector().check_and_increment(OperationNames.PROCESSED_EVENT_MARK_PROCESSING)
        return await self.wrapped.mark_processing(**kwargs)

    async def mark_processed(self, **kwargs) -> None:
        """Marcar como processado com possível falha."""
        get_failure_injector().check_and_increment(OperationNames.PROCESSED_EVENT_SAVE)
        return await self.wrapped.mark_processed(**kwargs)

    async def mark_failed(self, **kwargs) -> None:
        """Marcar como falho."""
        return await self.wrapped.mark_failed(**kwargs)

    async def delete_for_testing(self, **kwargs) -> None:
        """Deletar para testes."""
        return await self.wrapped.delete_for_testing(**kwargs)


class FailingAuditRepository(CommercialAuditRepository):
    """Auditoria com injeção de falhas."""

    def __init__(self, wrapped: CommercialAuditRepository):
        self.wrapped = wrapped

    async def record(self, **kwargs) -> AuditRecord:
        """Registrar com possível falha injetada."""
        get_failure_injector().check_and_increment(OperationNames.AUDIT_APPEND)
        return await self.wrapped.record(**kwargs)

    async def get_by_tenant(self, tenant_id: str, **kwargs) -> List[AuditRecord]:
        """Obter por tenant."""
        return await self.wrapped.get_by_tenant(tenant_id, **kwargs)

    async def get_by_aggregate(self, tenant_id: str, aggregate_id: str, **kwargs) -> List[AuditRecord]:
        """Obter por agregado."""
        return await self.wrapped.get_by_aggregate(tenant_id, aggregate_id, **kwargs)

    async def delete_for_testing(self, **kwargs) -> None:
        """Deletar para testes."""
        return await self.wrapped.delete_for_testing(**kwargs)


class FailingOutboxRepository(CommercialOutboxRepository):
    """Outbox com injeção de falhas."""

    def __init__(self, wrapped: CommercialOutboxRepository):
        self.wrapped = wrapped
        self._item_count = 0

    async def save(self, **kwargs) -> OutboxItem:
        """Salvar com possível falha injetada."""
        self._item_count += 1
        # Usar número do item para falhas em posições específicas
        operation = f"{OperationNames.OUTBOX_SAVE}.{self._item_count}"
        get_failure_injector().check_and_increment(operation)
        return await self.wrapped.save(**kwargs)

    async def save_batch(self, **kwargs) -> List[OutboxItem]:
        """Salvar lote."""
        return await self.wrapped.save_batch(**kwargs)

    async def get_pending(self, tenant_id: str, **kwargs) -> List[OutboxItem]:
        """Obter pendentes."""
        return await self.wrapped.get_pending(tenant_id, **kwargs)

    async def get_by_correlation(self, correlation_id: str, **kwargs) -> List[OutboxItem]:
        """Obter por correlation."""
        return await self.wrapped.get_by_correlation(correlation_id, **kwargs)

    async def mark_published(self, **kwargs) -> None:
        """Marcar como publicado."""
        return await self.wrapped.mark_published(**kwargs)

    async def mark_failed(self, **kwargs) -> None:
        """Marcar como falho."""
        return await self.wrapped.mark_failed(**kwargs)

    async def delete_for_testing(self, **kwargs) -> None:
        """Deletar para testes."""
        return await self.wrapped.delete_for_testing(**kwargs)

    def reset_item_count(self) -> None:
        """Resetar contador de itens (chamar antes de cada teste)."""
        self._item_count = 0
