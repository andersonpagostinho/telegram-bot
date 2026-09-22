"""Interface para repositório de auditoria (append-only)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass(frozen=True)
class AuditRecord:
    """Registro imutável de auditoria."""

    audit_id: str
    tenant_id: str
    aggregate_id: str
    correlation_id: str
    source_event_id: str
    decision_code: str
    success: bool
    aggregate_version_before: int
    aggregate_version_after: int
    previous_states: Dict[str, Any]
    resulting_states: Dict[str, Any]
    transitions_applied: List[Dict[str, Any]] = field(default_factory=list)
    transitions_ignored: List[Dict[str, Any]] = field(default_factory=list)
    effects_suggested: List[str] = field(default_factory=list)
    internal_events_generated: List[str] = field(default_factory=list)
    reconciliation_required: bool = False
    error_reason: Optional[str] = None
    occurred_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializar auditoria para persistência."""
        return {
            "audit_id": self.audit_id,
            "tenant_id": self.tenant_id,
            "aggregate_id": self.aggregate_id,
            "correlation_id": self.correlation_id,
            "source_event_id": self.source_event_id,
            "decision_code": self.decision_code,
            "success": self.success,
            "aggregate_version_before": self.aggregate_version_before,
            "aggregate_version_after": self.aggregate_version_after,
            "previous_states": self.previous_states,
            "resulting_states": self.resulting_states,
            "transitions_applied": self.transitions_applied,
            "transitions_ignored": self.transitions_ignored,
            "effects_suggested": self.effects_suggested,
            "internal_events_generated": self.internal_events_generated,
            "reconciliation_required": self.reconciliation_required,
            "error_reason": self.error_reason,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "schema_version": "1.0"
        }


from typing import Optional


@dataclass(frozen=True)
class CommercialAuditRepository(ABC):
    """
    Interface para auditoria append-only.

    Responsabilidades:
    - Criar novo registro de auditoria
    - NUNCA atualizar ou deletar auditoria
    - Implementar isolamento multi-tenant
    - Preservar integridade histórica
    """

    @abstractmethod
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
        """
        Registrar novo evento de auditoria (append-only).

        Deve ser chamado DENTRO da mesma transação que altera o agregado.

        Args:
            tenant_id: Identificador do tenant (obrigatório)
            aggregate_id: Identificador do agregado
            correlation_id: ID de correlação
            source_event_id: ID do evento que disparou a auditoria
            decision_code: Código da decisão
            success: True se decisão resultou em sucesso
            aggregate_version_before: Versão antes da decisão
            aggregate_version_after: Versão após a decisão
            previous_states: Estado anterior (todos 5 máquinas)
            resulting_states: Estado resultante
            transitions_applied: Transições aplicadas (opcional)
            transitions_ignored: Transições não aplicáveis (opcional)
            effects_suggested: Efeitos sugeridos (opcional)
            internal_events_generated: Eventos internos gerados (opcional)
            reconciliation_required: True se inconsistência detectada
            error_reason: Descrição de erro se falha

        Returns:
            AuditRecord persistido

        Raises:
            ValueError: Se tenant_id vazio ou IDs inválidos
            AppendOnlyViolation: Se tentar atualizar/deletar (não deve acontecer)
        """
        pass

    @abstractmethod
    async def get_by_tenant(
        self,
        tenant_id: str,
        limit: int = 100
    ) -> List[AuditRecord]:
        """
        Recuperar registros de auditoria mais recentes para um tenant.

        Args:
            tenant_id: Identificador do tenant
            limit: Quantidade máxima de registros

        Returns:
            Lista de AuditRecord em ordem cronológica (mais recentes primeiro)
        """
        pass

    @abstractmethod
    async def get_by_aggregate(
        self,
        tenant_id: str,
        aggregate_id: str,
        limit: int = 50
    ) -> List[AuditRecord]:
        """
        Recuperar histórico de auditoria de um agregado específico.

        Args:
            tenant_id: Identificador do tenant
            aggregate_id: Identificador do agregado
            limit: Quantidade máxima de registros

        Returns:
            Lista de AuditRecord em ordem cronológica
        """
        pass

    @abstractmethod
    async def delete_for_testing(self, tenant_id: str, aggregate_id: Optional[str] = None) -> None:
        """Deletar auditoria para limpeza de testes. NÃO usar em produção."""
        pass
