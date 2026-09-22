"""Interface para repositório de eventos processados (idempotência)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ProcessedEventStatus(str, Enum):
    """Status de um evento processado."""

    RECEIVED = "RECEIVED"  # Recebido, ainda não processando
    PROCESSING = "PROCESSING"  # Processando agora
    PROCESSED = "PROCESSED"  # Processamento concluído com sucesso
    FAILED_RETRYABLE = "FAILED_RETRYABLE"  # Falha que pode ser retentada
    FAILED_PERMANENT = "FAILED_PERMANENT"  # Falha permanente, não retry
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"  # Conflito detectado


@dataclass(frozen=True)
class ProcessedEvent:
    """Registro de evento processado para idempotência."""

    tenant_id: str
    provider: str
    provider_event_id: str
    status: ProcessedEventStatus
    payload_hash: str
    received_at: str
    processed_at: Optional[str] = None
    correlation_id: Optional[str] = None
    aggregate_id: Optional[str] = None
    aggregate_version_before: Optional[int] = None
    aggregate_version_after: Optional[int] = None
    decision_code: Optional[str] = None
    error_reason: Optional[str] = None


@dataclass(frozen=True)
class ProcessedEventRepository(ABC):
    """
    Interface para rastreamento de idempotência de eventos.

    Responsabilidades:
    - Verificar se evento já foi processado
    - Registrar evento como PROCESSING
    - Marcar como PROCESSED após sucesso
    - Implementar chave primária (tenant_id, provider, provider_event_id)
    """

    @abstractmethod
    async def check_and_load(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str
    ) -> Optional[ProcessedEvent]:
        """
        Verificar se evento foi processado e carregar registro.

        Chave primária conceitual: (tenant_id, provider, provider_event_id)

        Args:
            tenant_id: Identificador do tenant (obrigatório)
            provider: Provedor do evento (ex: "hotmart", "internal", "manual")
            provider_event_id: ID único do evento no provedor

        Returns:
            ProcessedEvent se existe, None se novo

        Raises:
            ValueError: Se tenant_id vazio ou inválido
        """
        pass

    @abstractmethod
    async def mark_processing(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str,
        payload_hash: str,
        correlation_id: str
    ) -> ProcessedEvent:
        """
        Registrar evento como PROCESSING para detectar duplicatas simultâneas.

        Args:
            tenant_id: Identificador do tenant
            provider: Provedor do evento
            provider_event_id: ID único do evento
            payload_hash: Hash do payload (para detectar mutação)
            correlation_id: ID de correlação para rastreamento

        Returns:
            ProcessedEvent com status=PROCESSING

        Raises:
            ValueError: Se tenant_id vazio
            ConflictError: Se evento já existe com status diferente
        """
        pass

    @abstractmethod
    async def mark_processed(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str,
        decision_code: str,
        aggregate_version_after: Optional[int] = None
    ) -> ProcessedEvent:
        """
        Marcar evento como PROCESSED após sucesso da decisão.

        Deve ser chamado DENTRO da mesma transação que altera o agregado.

        Args:
            tenant_id: Identificador do tenant
            provider: Provedor do evento
            provider_event_id: ID único do evento
            decision_code: Código da decisão (ex: "success", "no_transition", "validation_failed")
            aggregate_version_after: Versão do agregado após processamento

        Returns:
            ProcessedEvent com status=PROCESSED

        Raises:
            ValueError: Se tenant_id vazio
        """
        pass

    @abstractmethod
    async def mark_failed(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str,
        retryable: bool,
        error_reason: str
    ) -> ProcessedEvent:
        """
        Marcar evento como FAILED (retryable ou permanent).

        Args:
            tenant_id: Identificador do tenant
            provider: Provedor do evento
            provider_event_id: ID único do evento
            retryable: True se FAILED_RETRYABLE, False se FAILED_PERMANENT
            error_reason: Descrição da falha

        Returns:
            ProcessedEvent com status apropriado
        """
        pass

    @abstractmethod
    async def delete_for_testing(
        self,
        tenant_id: str,
        provider: str,
        provider_event_id: str
    ) -> None:
        """Deletar para limpeza de testes. NÃO usar em produção."""
        pass
