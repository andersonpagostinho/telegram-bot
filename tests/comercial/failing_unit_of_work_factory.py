"""
Factory para criar Unit of Work com decorators de failure injection (FASE 5).

Contrato: Compartilha estado principal (stores) entre transações,
mas cria nova UnitOfWork + novo staging + novos decorators por transação.
"""

from typing import Optional
from repositories.in_memory.in_memory_repositories import (
    InMemoryCommercialAggregateRepository,
    InMemoryProcessedEventRepository,
    InMemoryCommercialAuditRepository,
    InMemoryCommercialOutboxRepository,
    InMemoryCommercialUnitOfWork,
    CommercialAggregateRepository,
    ProcessedEventRepository,
    CommercialAuditRepository,
    CommercialOutboxRepository,
)
from tests.comercial.failing_repositories import (
    FailingAggregateRepository,
    FailingProcessedEventRepository,
    FailingAuditRepository,
    FailingOutboxRepository,
)


class DecoratingUnitOfWork(InMemoryCommercialUnitOfWork):
    """
    Subclasse que decora repositórios com failure injection.

    Override das properties para retornar decorators.
    Decoração ocorre no contexto da transação (quando _in_transaction=True).
    """

    def __init__(self, *args, **kwargs):
        """Inicializar com mesmos args que pai."""
        super().__init__(*args, **kwargs)
        # Cache de decorators para evitar recriação
        self._decorated_aggregate_repo: Optional[FailingAggregateRepository] = None
        self._decorated_processed_repo: Optional[FailingProcessedEventRepository] = None
        self._decorated_audit_repo: Optional[FailingAuditRepository] = None
        self._decorated_outbox_repo: Optional[FailingOutboxRepository] = None

    @property
    def aggregate_repository(self) -> CommercialAggregateRepository:
        """Retornar agregado decorado (ou real se fora de transação)."""
        if not self._in_transaction:
            raise RuntimeError("Repositório só acessível dentro de transação")

        if self._decorated_aggregate_repo is None:
            self._decorated_aggregate_repo = FailingAggregateRepository(
                self._txn_aggregate_repo
            )

        return self._decorated_aggregate_repo

    @property
    def processed_event_repository(self) -> ProcessedEventRepository:
        """Retornar processado decorado."""
        if not self._in_transaction:
            raise RuntimeError("Repositório só acessível dentro de transação")

        if self._decorated_processed_repo is None:
            self._decorated_processed_repo = FailingProcessedEventRepository(
                self._txn_processed_repo
            )

        return self._decorated_processed_repo

    @property
    def audit_repository(self) -> CommercialAuditRepository:
        """Retornar auditoria decorada."""
        if not self._in_transaction:
            raise RuntimeError("Repositório só acessível dentro de transação")

        if self._decorated_audit_repo is None:
            self._decorated_audit_repo = FailingAuditRepository(
                self._txn_audit_repo
            )

        return self._decorated_audit_repo

    @property
    def outbox_repository(self) -> CommercialOutboxRepository:
        """Retornar outbox decorado."""
        if not self._in_transaction:
            raise RuntimeError("Repositório só acessível dentro de transação")

        if self._decorated_outbox_repo is None:
            self._decorated_outbox_repo = FailingOutboxRepository(
                self._txn_outbox_repo
            )

        return self._decorated_outbox_repo


class FailingInMemoryUnitOfWorkFactory:
    """
    Factory que cria UnitOfWork com repositórios decorados para failure injection.

    Padrão:
    - Stores (estado principal): COMPARTILHADOS entre transações
    - UnitOfWork: NOVA por transação
    - Staging: NOVO por transação
    - Decorators: NOVOS por transação
    - FailureInjector: GLOBAL (mesmo para todas as transações)
    """

    def __init__(
        self,
        aggregate_repo: InMemoryCommercialAggregateRepository,
        processed_repo: InMemoryProcessedEventRepository,
        audit_repo: InMemoryCommercialAuditRepository,
        outbox_repo: InMemoryCommercialOutboxRepository,
    ):
        """
        Inicializar factory com stores compartilhados.

        Args:
            aggregate_repo: Store real de agregados (compartilhado)
            processed_repo: Store real de eventos processados (compartilhado)
            audit_repo: Store real de auditoria (compartilhado)
            outbox_repo: Store real de outbox (compartilhado)
        """
        self.aggregate_repo = aggregate_repo
        self.processed_repo = processed_repo
        self.audit_repo = audit_repo
        self.outbox_repo = outbox_repo

    def __call__(self) -> DecoratingUnitOfWork:
        """
        Criar nova UnitOfWork com repositórios decorados.

        Cada chamada:
        1. Cria novo DecoratingUnitOfWork (novo staging)
        2. DecoratingUnitOfWork decora repositórios quando entrado em transação
        3. Retorna UnitOfWork com repositórios decorados

        O staging será novo, mas os stores principais serão compartilhados
        entre todas as transações.

        Returns:
            DecoratingUnitOfWork com repositórios decorados
        """
        return DecoratingUnitOfWork(
            aggregate_repo=self.aggregate_repo,
            processed_repo=self.processed_repo,
            audit_repo=self.audit_repo,
            outbox_repo=self.outbox_repo,
        )
