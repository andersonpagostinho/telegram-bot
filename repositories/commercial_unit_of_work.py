"""Interface para Unit of Work (coordenação de transações)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncContextManager

from repositories.commercial_aggregate_repository import CommercialAggregateRepository
from repositories.processed_event_repository import ProcessedEventRepository
from repositories.commercial_audit_repository import CommercialAuditRepository
from repositories.commercial_outbox_repository import CommercialOutboxRepository


@dataclass(frozen=True)
class CommercialUnitOfWork(ABC):
    """
    Interface de Unit of Work para coordenar múltiplos repositórios em uma transação.

    Responsabilidades:
    - Coordenar leitura/escrita de múltiplos repositórios
    - Garantir atomicidade de todas operações
    - Implementar commit/rollback
    - Isolar cada transação de outras concorrentes
    """

    @property
    @abstractmethod
    def aggregate_repository(self) -> CommercialAggregateRepository:
        """Repositório de agregado."""
        pass

    @property
    @abstractmethod
    def processed_event_repository(self) -> ProcessedEventRepository:
        """Repositório de eventos processados."""
        pass

    @property
    @abstractmethod
    def audit_repository(self) -> CommercialAuditRepository:
        """Repositório de auditoria."""
        pass

    @property
    @abstractmethod
    def outbox_repository(self) -> CommercialOutboxRepository:
        """Repositório de outbox."""
        pass

    @abstractmethod
    async def begin(self) -> None:
        """
        Iniciar transação.

        Chamado automaticamente ao entrar no context manager.
        """
        pass

    @abstractmethod
    async def commit(self) -> None:
        """
        Confirmar transação.

        Atomicamente:
        - Persiste o agregado
        - Marca evento como PROCESSED
        - Registra auditoria
        - Grava items de outbox

        Se alguma operação falhar: rollback automático de tudo.

        Raises:
            ConflictError: Se version conflict (retry é permitido)
            TransactionError: Se falha de transação (retry é permitido)
            PermanentError: Se falha não recuperável (não retry)
        """
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """
        Descartar transação.

        Todos os dados staged são descartados:
        - Agregado não é atualizado
        - Evento permanece com status anterior (ou FAILED)
        - Auditoria não é registrada
        - Outbox não é criado

        Deve ser chamado em caso de erro ou exceção.
        """
        pass

    @abstractmethod
    async def __aenter__(self) -> "CommercialUnitOfWork":
        """Context manager entry."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit.

        Se exc_type is None: commit
        Caso contrário: rollback
        """
        pass
