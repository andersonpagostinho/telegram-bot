"""Implementações em memória de repositórios para Gate A."""

import uuid
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from copy import deepcopy


# ==============================================================================
# ESTRATÉGIA DE IDs DETERMINÍSTICOS
# ==============================================================================

# Namespace do domínio comercial (constante de domínio, não protocolo)
# Derivado uma única vez como: uuid5(NAMESPACE_DNS, "neoeve.commercial")
# Após derivação, tratado como namespace próprio do domínio comercial
COMMERCIAL_NAMESPACE = uuid.UUID("4415d802-c13a-506d-9721-97d028f6c541")

# Versão do esquema de chaves
AUDIT_KEY_VERSION = "1.0"
OUTBOX_KEY_VERSION = "1.0"


def compute_audit_id(
    tenant_id: str,
    aggregate_id: str,
    source_event_id: str,
    decision_code: str,
    aggregate_version_after: int,
) -> str:
    """
    Computar ID estável para auditoria.

    Composição da chave:
    commercial-audit:v1|tenant={tenant_id}|aggregate={aggregate_id}|
    source_event={source_event_id}|decision={decision_code}|
    version={aggregate_version_after}

    Mesma decisão → Mesmo ID
    """
    canonical_key = (
        f"commercial-audit:{AUDIT_KEY_VERSION}|"
        f"tenant={tenant_id}|"
        f"aggregate={aggregate_id}|"
        f"source_event={source_event_id}|"
        f"decision={decision_code}|"
        f"version={aggregate_version_after}"
    )
    return str(uuid.uuid5(COMMERCIAL_NAMESPACE, canonical_key))


def compute_outbox_id(
    tenant_id: str,
    aggregate_id: str,
    source_event_id: str,
    aggregate_version_after: int,
    event_index: int,
    event_type: str,
) -> str:
    """
    Computar ID estável para outbox.

    Composição da chave:
    commercial-outbox:v1|tenant={tenant_id}|aggregate={aggregate_id}|
    source_event={source_event_id}|version={aggregate_version_after}|
    index={event_index}|type={event_type}

    Mesmo evento em mesma posição → Mesmo ID
    Evento em posição diferente → ID diferente
    Tipo diferente → ID diferente
    """
    canonical_key = (
        f"commercial-outbox:{OUTBOX_KEY_VERSION}|"
        f"tenant={tenant_id}|"
        f"aggregate={aggregate_id}|"
        f"source_event={source_event_id}|"
        f"version={aggregate_version_after}|"
        f"index={event_index}|"
        f"type={event_type}"
    )
    return str(uuid.uuid5(COMMERCIAL_NAMESPACE, canonical_key))

from repositories.commercial_aggregate_repository import CommercialAggregateRepository
from repositories.processed_event_repository import (
    ProcessedEventRepository,
    ProcessedEvent,
    ProcessedEventStatus
)
from repositories.commercial_audit_repository import CommercialAuditRepository, AuditRecord
from repositories.commercial_outbox_repository import CommercialOutboxRepository, OutboxItem, OutboxStatus
from repositories.commercial_unit_of_work import CommercialUnitOfWork
from services.billing_domain_service import CommercialAggregate, AggregateSnapshot


class ConflictError(Exception):
    """Erro de conflito de versão ou duplicação."""
    pass


class CrossTenantError(Exception):
    """Erro de tentativa de acesso cross-tenant."""
    pass


def _compute_hash(payload: Dict[str, Any]) -> str:
    """Computar hash canônico de payload."""
    # Ordenar chaves para garantir determinismo
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class InMemoryCommercialAggregateRepository(CommercialAggregateRepository):
    """Implementação em memória do repositório de agregado."""

    def __init__(self):
        # Estrutura: {tenant_id: {aggregate_id: aggregate}}
        self.store: Dict[str, Dict[str, CommercialAggregate]] = {}

    async def load(
        self,
        tenant_id: str,
        aggregate_id: str
    ) -> Optional[CommercialAggregate]:
        """Carregar agregado comercial."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        tenant_store = self.store.get(tenant_id, {})
        aggregate = tenant_store.get(aggregate_id)

        if aggregate and aggregate.tenant_id != tenant_id:
            raise CrossTenantError(f"Agregado {aggregate_id} não pertence ao tenant {tenant_id}")

        return deepcopy(aggregate) if aggregate else None

    async def save(
        self,
        tenant_id: str,
        aggregate_id: str,
        aggregate: CommercialAggregate,
        expected_version: int
    ) -> bool:
        """Salvar agregado com compare-and-set."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        if aggregate.tenant_id != tenant_id:
            raise CrossTenantError(f"Agregado tenant_id diverge do contexto")

        # Verificar versão
        tenant_store = self.store.get(tenant_id, {})
        existing = tenant_store.get(aggregate_id)

        if existing:
            if existing.version != expected_version:
                raise ConflictError(
                    f"Version conflict: expected {expected_version}, got {existing.version}"
                )

        # Criar tenant se não existe
        if tenant_id not in self.store:
            self.store[tenant_id] = {}

        # Salvar cópia
        self.store[tenant_id][aggregate_id] = deepcopy(aggregate)
        return True

    async def delete_for_testing(self, tenant_id: str, aggregate_id: str) -> None:
        """Deletar para testes."""
        if tenant_id in self.store and aggregate_id in self.store[tenant_id]:
            del self.store[tenant_id][aggregate_id]


class InMemoryProcessedEventRepository(ProcessedEventRepository):
    """Implementação em memória do repositório de eventos processados."""

    def __init__(self):
        # Estrutura: {tenant_id: {(provider, provider_event_id): processed_event}}
        self.store: Dict[str, Dict[tuple, ProcessedEvent]] = {}

    def _make_key(self, provider: str, provider_event_id: str) -> tuple:
        """Criar chave primária conceitual."""
        return (provider, provider_event_id)

    async def check_and_load(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str
    ) -> Optional[ProcessedEvent]:
        """Verificar se evento foi processado."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        tenant_store = self.store.get(tenant_id, {})
        key = self._make_key(provider, provider_event_id)
        event = tenant_store.get(key)

        return deepcopy(event) if event else None

    async def mark_processing(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str,
        payload_hash: str,
        correlation_id: str
    ) -> ProcessedEvent:
        """Registrar como PROCESSING."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        if tenant_id not in self.store:
            self.store[tenant_id] = {}

        key = self._make_key(provider, provider_event_id)
        existing = self.store[tenant_id].get(key)

        if existing:
            raise ConflictError(
                f"Event already exists with status {existing.status.value}"
            )

        event = ProcessedEvent(
            tenant_id=tenant_id,
            provider=provider,
            provider_event_id=provider_event_id,
            status=ProcessedEventStatus.PROCESSING,
            payload_hash=payload_hash,
            received_at=datetime.utcnow().isoformat(),
            correlation_id=correlation_id
        )

        self.store[tenant_id][key] = event
        return deepcopy(event)

    async def mark_processed(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str,
        decision_code: str,
        aggregate_version_after: Optional[int] = None
    ) -> ProcessedEvent:
        """Marcar como PROCESSED."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        tenant_store = self.store.get(tenant_id, {})
        key = self._make_key(provider, provider_event_id)
        existing = tenant_store.get(key)

        if not existing:
            raise ValueError(f"Event {key} not found in PROCESSING")

        event = ProcessedEvent(
            tenant_id=existing.tenant_id,
            provider=existing.provider,
            provider_event_id=existing.provider_event_id,
            status=ProcessedEventStatus.PROCESSED,
            payload_hash=existing.payload_hash,
            received_at=existing.received_at,
            processed_at=datetime.utcnow().isoformat(),
            correlation_id=existing.correlation_id,
            aggregate_version_after=aggregate_version_after,
            decision_code=decision_code
        )

        self.store[tenant_id][key] = event
        return deepcopy(event)

    async def mark_failed(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str,
        retryable: bool,
        error_reason: str
    ) -> ProcessedEvent:
        """Marcar como FAILED."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        tenant_store = self.store.get(tenant_id, {})
        key = self._make_key(provider, provider_event_id)
        existing = tenant_store.get(key)

        if not existing:
            raise ValueError(f"Event {key} not found")

        status = (
            ProcessedEventStatus.FAILED_RETRYABLE
            if retryable
            else ProcessedEventStatus.FAILED_PERMANENT
        )

        event = ProcessedEvent(
            tenant_id=existing.tenant_id,
            provider=existing.provider,
            provider_event_id=existing.provider_event_id,
            status=status,
            payload_hash=existing.payload_hash,
            received_at=existing.received_at,
            processed_at=datetime.utcnow().isoformat(),
            correlation_id=existing.correlation_id,
            error_reason=error_reason
        )

        self.store[tenant_id][key] = event
        return deepcopy(event)

    async def delete_for_testing(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str
    ) -> None:
        """Deletar para testes."""
        if tenant_id in self.store:
            key = self._make_key(provider, provider_event_id)
            if key in self.store[tenant_id]:
                del self.store[tenant_id][key]


class InMemoryCommercialAuditRepository(CommercialAuditRepository):
    """Implementação em memória do repositório de auditoria."""

    def __init__(self):
        # Estrutura: {tenant_id: [audit_records]}
        self.store: Dict[str, List[AuditRecord]] = {}

    async def record(
        self,
        tenant_id: str,
        aggregate_id: str,
        correlation_id: str,
        source_event_id: str,
        decision_code: str,
        success: bool,
        aggregate_version_before: int,
        aggregate_version_after: int,
        previous_states: Dict[str, Any],
        resulting_states: Dict[str, Any],
        transitions_applied: List[Dict[str, Any]] = None,
        transitions_ignored: List[Dict[str, Any]] = None,
        effects_suggested: List[str] = None,
        internal_events_generated: List[str] = None,
        reconciliation_required: bool = False,
        error_reason: Optional[str] = None
    ) -> AuditRecord:
        """Registrar auditoria (append-only) com ID determinístico."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        if tenant_id not in self.store:
            self.store[tenant_id] = []

        # Computar ID determinístico para mesma decisão → mesmo audit_id
        audit_id = compute_audit_id(
            tenant_id=tenant_id,
            aggregate_id=aggregate_id,
            source_event_id=source_event_id,
            decision_code=decision_code,
            aggregate_version_after=aggregate_version_after,
        )

        audit = AuditRecord(
            audit_id=audit_id,
            tenant_id=tenant_id,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            source_event_id=source_event_id,
            decision_code=decision_code,
            success=success,
            aggregate_version_before=aggregate_version_before,
            aggregate_version_after=aggregate_version_after,
            previous_states=previous_states,
            resulting_states=resulting_states,
            transitions_applied=transitions_applied or [],
            transitions_ignored=transitions_ignored or [],
            effects_suggested=effects_suggested or [],
            internal_events_generated=internal_events_generated or [],
            reconciliation_required=reconciliation_required,
            error_reason=error_reason,
            occurred_at=datetime.utcnow()
        )

        self.store[tenant_id].append(audit)
        return deepcopy(audit)

    async def get_by_tenant(
        self,
        tenant_id: str,
        limit: int = 100
    ) -> List[AuditRecord]:
        """Recuperar auditoria por tenant."""
        records = self.store.get(tenant_id, [])
        # Retornar mais recentes primeiro
        return [deepcopy(r) for r in sorted(
            records,
            key=lambda r: r.occurred_at or datetime.min,
            reverse=True
        )[:limit]]

    async def get_by_aggregate(
        self,
        tenant_id: str,
        aggregate_id: str,
        limit: int = 50
    ) -> List[AuditRecord]:
        """Recuperar auditoria por agregado."""
        records = self.store.get(tenant_id, [])
        filtered = [r for r in records if r.aggregate_id == aggregate_id]
        # Retornar mais recentes primeiro
        return [deepcopy(r) for r in sorted(
            filtered,
            key=lambda r: r.occurred_at or datetime.min,
            reverse=True
        )[:limit]]

    async def delete_for_testing(self, tenant_id: str, aggregate_id: Optional[str] = None) -> None:
        """Deletar para testes."""
        if tenant_id in self.store:
            if aggregate_id:
                self.store[tenant_id] = [r for r in self.store[tenant_id] if r.aggregate_id != aggregate_id]
            else:
                self.store[tenant_id] = []


class InMemoryCommercialOutboxRepository(CommercialOutboxRepository):
    """Implementação em memória do repositório de outbox."""

    def __init__(self):
        # Estrutura: {tenant_id: {outbox_id: outbox_item}}
        self.store: Dict[str, Dict[str, OutboxItem]] = {}

    async def save(
        self,
        tenant_id: str,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: str,
        source_event_id: str,
        aggregate_version: int,
        aggregate_id: Optional[str] = None,
        event_index: int = 0,
    ) -> OutboxItem:
        """Salvar item de outbox com ID determinístico."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        if tenant_id not in self.store:
            self.store[tenant_id] = {}

        # Computar ID determinístico para mesmo evento em mesma posição → mesmo outbox_id
        outbox_id = compute_outbox_id(
            tenant_id=tenant_id,
            aggregate_id=aggregate_id or "unknown",
            source_event_id=source_event_id,
            aggregate_version_after=aggregate_version,
            event_index=event_index,
            event_type=event_type,
        )

        item = OutboxItem(
            outbox_id=outbox_id,
            tenant_id=tenant_id,
            event_type=event_type,
            schema_version="1.0",
            payload=deepcopy(payload),
            correlation_id=correlation_id,
            source_event_id=source_event_id,
            aggregate_version=aggregate_version,
            status=OutboxStatus.PENDING,
            created_at=datetime.utcnow().isoformat()
        )

        self.store[tenant_id][item.outbox_id] = item
        return deepcopy(item)

    async def save_batch(
        self,
        tenant_id: str,
        items: List[Dict[str, Any]],
        aggregate_id: Optional[str] = None,
    ) -> List[OutboxItem]:
        """Salvar múltiplos items com índices para distinguir duplicatos."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id obrigatório e não vazio")

        results = []
        for idx, item_data in enumerate(items):
            result = await self.save(
                tenant_id=tenant_id,
                event_type=item_data["event_type"],
                payload=item_data["payload"],
                correlation_id=item_data["correlation_id"],
                source_event_id=item_data["source_event_id"],
                aggregate_version=item_data["aggregate_version"],
                aggregate_id=aggregate_id or item_data.get("aggregate_id"),
                event_index=idx,  # Índice para distinguir múltiplos eventos
            )
            results.append(result)

        return results

    async def get_pending(
        self,
        tenant_id: str,
        limit: int = 100
    ) -> List[OutboxItem]:
        """Recuperar items pendentes."""
        tenant_store = self.store.get(tenant_id, {})
        pending = [item for item in tenant_store.values() if item.status == OutboxStatus.PENDING]
        return [deepcopy(item) for item in pending[:limit]]

    async def get_by_correlation(
        self,
        tenant_id: str,
        correlation_id: str
    ) -> List[OutboxItem]:
        """Recuperar items por correlation_id."""
        tenant_store = self.store.get(tenant_id, {})
        items = [item for item in tenant_store.values() if item.correlation_id == correlation_id]
        return [deepcopy(item) for item in items]

    async def mark_published(
        self,
        tenant_id: str,
        outbox_id: str
    ) -> OutboxItem:
        """Marcar como PUBLISHED."""
        tenant_store = self.store.get(tenant_id, {})
        existing = tenant_store.get(outbox_id)

        if not existing:
            raise ValueError(f"Outbox {outbox_id} not found")

        item = OutboxItem(
            outbox_id=existing.outbox_id,
            tenant_id=existing.tenant_id,
            event_type=existing.event_type,
            schema_version=existing.schema_version,
            payload=existing.payload,
            correlation_id=existing.correlation_id,
            source_event_id=existing.source_event_id,
            aggregate_version=existing.aggregate_version,
            status=OutboxStatus.PUBLISHED,
            created_at=existing.created_at,
            published_at=datetime.utcnow().isoformat()
        )

        self.store[tenant_id][outbox_id] = item
        return deepcopy(item)

    async def mark_failed(
        self,
        tenant_id: str,
        outbox_id: str,
        retryable: bool,
        error_reason: str
    ) -> OutboxItem:
        """Marcar como FAILED."""
        tenant_store = self.store.get(tenant_id, {})
        existing = tenant_store.get(outbox_id)

        if not existing:
            raise ValueError(f"Outbox {outbox_id} not found")

        status = OutboxStatus.FAILED_RETRYABLE if retryable else OutboxStatus.FAILED_PERMANENT

        item = OutboxItem(
            outbox_id=existing.outbox_id,
            tenant_id=existing.tenant_id,
            event_type=existing.event_type,
            schema_version=existing.schema_version,
            payload=existing.payload,
            correlation_id=existing.correlation_id,
            source_event_id=existing.source_event_id,
            aggregate_version=existing.aggregate_version,
            status=status,
            created_at=existing.created_at,
            publication_attempts=existing.publication_attempts + 1,
            last_error=error_reason
        )

        self.store[tenant_id][outbox_id] = item
        return deepcopy(item)

    async def delete_for_testing(
        self,
        tenant_id: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Deletar para testes."""
        if tenant_id in self.store:
            if correlation_id:
                self.store[tenant_id] = {
                    k: v for k, v in self.store[tenant_id].items()
                    if v.correlation_id != correlation_id
                }
            else:
                self.store[tenant_id] = {}


class InMemoryCommercialUnitOfWork(CommercialUnitOfWork):
    """
    Implementação em memória de Unit of Work com transação isolada e staging real.

    Garantias:
    - Nenhuma alteração é visível no store principal antes do commit
    - Commit é atômico (sucesso ou falha completa)
    - Rollback descarta integramente o staging
    """

    def __init__(
        self,
        aggregate_repo: InMemoryCommercialAggregateRepository = None,
        processed_repo: InMemoryProcessedEventRepository = None,
        audit_repo: InMemoryCommercialAuditRepository = None,
        outbox_repo: InMemoryCommercialOutboxRepository = None
    ):
        self._main_aggregate_repo = aggregate_repo or InMemoryCommercialAggregateRepository()
        self._main_processed_repo = processed_repo or InMemoryProcessedEventRepository()
        self._main_audit_repo = audit_repo or InMemoryCommercialAuditRepository()
        self._main_outbox_repo = outbox_repo or InMemoryCommercialOutboxRepository()

        # Transação em andamento?
        self._in_transaction = False
        self._committed = False
        self._rolled_back = False

        # Staging isolado: cópias profundas dos stores principais
        self._staging_aggregate_store: Dict[str, Dict[str, CommercialAggregate]] = {}
        self._staging_processed_store: Dict[str, Dict[tuple, ProcessedEvent]] = {}
        self._staging_audit_store: Dict[str, List[AuditRecord]] = {}
        self._staging_outbox_store: Dict[str, Dict[str, OutboxItem]] = {}

        # Repositórios transacionais (apontam ao staging)
        self._txn_aggregate_repo: Optional[InMemoryCommercialAggregateRepository] = None
        self._txn_processed_repo: Optional[InMemoryProcessedEventRepository] = None
        self._txn_audit_repo: Optional[InMemoryCommercialAuditRepository] = None
        self._txn_outbox_repo: Optional[InMemoryCommercialOutboxRepository] = None

    @property
    def aggregate_repository(self) -> CommercialAggregateRepository:
        if not self._in_transaction:
            raise RuntimeError("Repositório só acessível dentro de transação")
        return self._txn_aggregate_repo

    @property
    def processed_event_repository(self) -> ProcessedEventRepository:
        if not self._in_transaction:
            raise RuntimeError("Repositório só acessível dentro de transação")
        return self._txn_processed_repo

    @property
    def audit_repository(self) -> CommercialAuditRepository:
        if not self._in_transaction:
            raise RuntimeError("Repositório só acessível dentro de transação")
        return self._txn_audit_repo

    @property
    def outbox_repository(self) -> CommercialOutboxRepository:
        if not self._in_transaction:
            raise RuntimeError("Repositório só acessível dentro de transação")
        return self._txn_outbox_repo

    async def begin(self) -> None:
        """Iniciar transação com staging isolado."""
        if self._in_transaction:
            raise RuntimeError("Transação já em andamento")
        if self._committed or self._rolled_back:
            raise RuntimeError("Unit of Work já foi utilizada (committed/rolled back)")

        self._in_transaction = True

        # Criar cópias profundas dos stores principais para staging
        self._staging_aggregate_store = deepcopy(self._main_aggregate_repo.store)
        self._staging_processed_store = deepcopy(self._main_processed_repo.store)
        self._staging_audit_store = deepcopy(self._main_audit_repo.store)
        self._staging_outbox_store = deepcopy(self._main_outbox_repo.store)

        # Criar repositórios transacionais que apontam ao staging
        self._txn_aggregate_repo = InMemoryCommercialAggregateRepository()
        self._txn_aggregate_repo.store = self._staging_aggregate_store

        self._txn_processed_repo = InMemoryProcessedEventRepository()
        self._txn_processed_repo.store = self._staging_processed_store

        self._txn_audit_repo = InMemoryCommercialAuditRepository()
        self._txn_audit_repo.store = self._staging_audit_store

        self._txn_outbox_repo = InMemoryCommercialOutboxRepository()
        self._txn_outbox_repo.store = self._staging_outbox_store

    async def commit(self) -> None:
        """
        Confirmar transação atomicamente.

        Aplica integramente o staging ao store principal.
        Falha se não está em transação ou já foi committed/rolled back.
        """
        if not self._in_transaction:
            raise RuntimeError("Nenhuma transação em andamento")
        if self._committed:
            raise RuntimeError("Transação já foi committed")
        if self._rolled_back:
            raise RuntimeError("Transação já foi rolled back")

        try:
            # Aplicar staging ao principal (atomicamente)
            self._main_aggregate_repo.store = self._staging_aggregate_store
            self._main_processed_repo.store = self._staging_processed_store
            self._main_audit_repo.store = self._staging_audit_store
            self._main_outbox_repo.store = self._staging_outbox_store

            self._in_transaction = False
            self._committed = True
        except Exception as e:
            # Falha no commit: rollback automático
            await self.rollback()
            raise

    async def rollback(self) -> None:
        """
        Descartar transação completamente.

        O staging é descartado, os stores principais permanecem inalterados.
        """
        if self._rolled_back:
            # Idempotência: segundo rollback é no-op
            return

        self._in_transaction = False
        self._rolled_back = True

        # Descartar staging (não tocar no principal)
        self._staging_aggregate_store = {}
        self._staging_processed_store = {}
        self._staging_audit_store = {}
        self._staging_outbox_store = {}

        # Limpar repositórios transacionais
        self._txn_aggregate_repo = None
        self._txn_processed_repo = None
        self._txn_audit_repo = None
        self._txn_outbox_repo = None

    async def __aenter__(self) -> "CommercialUnitOfWork":
        """Context manager entry."""
        await self.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()
