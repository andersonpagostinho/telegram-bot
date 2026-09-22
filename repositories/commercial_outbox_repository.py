"""Interface para repositório de outbox (eventos pendentes de publicação)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class OutboxStatus(str, Enum):
    """Status de um item de outbox."""

    PENDING = "PENDING"  # Aguardando publicação
    PROCESSING = "PROCESSING"  # Sendo publicado
    PUBLISHED = "PUBLISHED"  # Publicado com sucesso
    FAILED_RETRYABLE = "FAILED_RETRYABLE"  # Falha de publicação retentável
    FAILED_PERMANENT = "FAILED_PERMANENT"  # Falha permanente


@dataclass(frozen=True)
class OutboxItem:
    """Item de outbox (evento pendente de publicação)."""

    outbox_id: str
    tenant_id: str
    event_type: str
    schema_version: str
    payload: Dict[str, Any]
    correlation_id: str
    source_event_id: str
    aggregate_version: int
    status: OutboxStatus
    created_at: str
    publication_attempts: int = 0
    published_at: Optional[str] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializar outbox para persistência."""
        return {
            "outbox_id": self.outbox_id,
            "tenant_id": self.tenant_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "source_event_id": self.source_event_id,
            "aggregate_version": self.aggregate_version,
            "status": self.status.value,
            "created_at": self.created_at,
            "publication_attempts": self.publication_attempts,
            "published_at": self.published_at,
            "last_error": self.last_error,
        }


@dataclass(frozen=True)
class CommercialOutboxRepository(ABC):
    """
    Interface para outbox de eventos (padrão Transactional Outbox).

    Responsabilidades:
    - Gravar eventos pendentes de publicação
    - Manter status PENDING até publicação (Fase 5)
    - Implementar isolamento multi-tenant
    - NÃO publicar em Fase 3 (apenas persistir como PENDING)

    Padrão: Para cada decisão do domínio, gerar 0 a N eventos de outbox.
    Todos os N eventos são persistidos atomicamente com o agregado.
    """

    @abstractmethod
    async def save(
        self,
        tenant_id: str,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: str,
        source_event_id: str,
        aggregate_version: int
    ) -> OutboxItem:
        """
        Persistir novo item de outbox com status=PENDING.

        Deve ser chamado DENTRO da mesma transação que altera o agregado.

        Args:
            tenant_id: Identificador do tenant (obrigatório)
            event_type: Tipo de evento (ex: "SubscriptionActivated", "PaymentApproved")
            payload: Payload do evento (JSON-serializable)
            correlation_id: ID de correlação para rastreamento
            source_event_id: ID do evento original que disparou outbox
            aggregate_version: Versão do agregado no momento do outbox

        Returns:
            OutboxItem com status=PENDING

        Raises:
            ValueError: Se tenant_id vazio ou payload inválido
        """
        pass

    @abstractmethod
    async def save_batch(
        self,
        tenant_id: str,
        items: List[Dict[str, Any]]
    ) -> List[OutboxItem]:
        """
        Persistir múltiplos itens de outbox atomicamente.

        Útil quando uma decisão gera múltiplos eventos.

        Args:
            tenant_id: Identificador do tenant
            items: Lista de dicts com chaves:
                - event_type (obrigatório)
                - payload (obrigatório)
                - correlation_id (obrigatório)
                - source_event_id (obrigatório)
                - aggregate_version (obrigatório)

        Returns:
            Lista de OutboxItem salvos

        Raises:
            ValueError: Se tenant_id vazio ou items inválido
        """
        pass

    @abstractmethod
    async def get_pending(
        self,
        tenant_id: str,
        limit: int = 100
    ) -> List[OutboxItem]:
        """
        Recuperar itens pendentes de publicação.

        Usado pelo worker de publicação (Fase 5).

        Args:
            tenant_id: Identificador do tenant
            limit: Quantidade máxima de itens

        Returns:
            Lista de OutboxItem com status=PENDING
        """
        pass

    @abstractmethod
    async def get_by_correlation(
        self,
        tenant_id: str,
        correlation_id: str
    ) -> List[OutboxItem]:
        """
        Recuperar todos os itens de outbox gerados por um evento.

        Args:
            tenant_id: Identificador do tenant
            correlation_id: ID de correlação

        Returns:
            Lista de OutboxItem (tipicamente 0-5 itens)
        """
        pass

    @abstractmethod
    async def mark_published(
        self,
        tenant_id: str,
        outbox_id: str
    ) -> OutboxItem:
        """
        Marcar item como PUBLISHED (chamado pelo worker em Fase 5).

        NÃO será chamado em Fase 3.

        Args:
            tenant_id: Identificador do tenant
            outbox_id: ID do item de outbox

        Returns:
            OutboxItem com status=PUBLISHED
        """
        pass

    @abstractmethod
    async def mark_failed(
        self,
        tenant_id: str,
        outbox_id: str,
        retryable: bool,
        error_reason: str
    ) -> OutboxItem:
        """
        Marcar item como FAILED (retryable ou permanent).

        NÃO será chamado em Fase 3.

        Args:
            tenant_id: Identificador do tenant
            outbox_id: ID do item de outbox
            retryable: True se FAILED_RETRYABLE, False se FAILED_PERMANENT
            error_reason: Descrição do erro

        Returns:
            OutboxItem com status apropriado
        """
        pass

    @abstractmethod
    async def delete_for_testing(
        self,
        tenant_id: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Deletar items para limpeza de testes. NÃO usar em produção."""
        pass
