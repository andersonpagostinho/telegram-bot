"""Interface para repositório de agregado comercial."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from services.billing_domain_service import CommercialAggregate


@dataclass(frozen=True)
class CommercialAggregateRepository(ABC):
    """
    Interface para persistência e leitura de snapshot do agregado comercial.

    Responsabilidades:
    - Carregar snapshot atual (com versionamento)
    - Salvar novo snapshot (com compare-and-set)
    - Validar tenant_id
    - Implementar isolamento multi-tenant
    """

    @abstractmethod
    async def load(
        self,
        tenant_id: str,
        aggregate_id: str
    ) -> Optional[CommercialAggregate]:
        """
        Carregar snapshot do agregado comercial.

        Args:
            tenant_id: Identificador do tenant (obrigatório)
            aggregate_id: Identificador do agregado

        Returns:
            AggregateSnapshot se existe, None se não existe

        Raises:
            ValueError: Se tenant_id vazio ou inválido
            CrossTenantError: Se tentativa de acesso cross-tenant
        """
        pass

    @abstractmethod
    async def save(
        self,
        tenant_id: str,
        aggregate_id: str,
        aggregate: CommercialAggregate,
        expected_version: int
    ) -> bool:
        """
        Salvar agregado com comparação de versão (compare-and-set).

        Atomicidade: Esta escrita deve fazer parte de uma transação maior
        que inclui: dedup + audit + outbox.

        Args:
            tenant_id: Identificador do tenant (obrigatório)
            aggregate_id: Identificador do agregado
            aggregate: Novo agregado comercial com versão incrementada
            expected_version: Versão esperada (check)

        Returns:
            True se salvo (versão coincidiu)
            False não deve ser retornado em transação (ConflictError levantado)

        Raises:
            ValueError: Se tenant_id vazio ou inválido
            ConflictError: Se aggregate.version divergir de expected_version
            CrossTenantError: Se tenant_id divergir do aggregate.tenant_id
        """
        pass

    @abstractmethod
    async def delete_for_testing(self, tenant_id: str, aggregate_id: str) -> None:
        """
        Deletar agregado para limpeza de testes.

        NÃO usar em produção.
        """
        pass
