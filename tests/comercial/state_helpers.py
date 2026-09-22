"""
Helpers para captura e comparação de estado em testes de atomicidade (FASE 5).

Usam deep copy para garantir que estado capturado não seja mutado.
"""

from copy import deepcopy
from typing import Dict, Any
from repositories.in_memory.in_memory_repositories import (
    InMemoryCommercialAggregateRepository,
    InMemoryProcessedEventRepository,
    InMemoryCommercialAuditRepository,
    InMemoryCommercialOutboxRepository,
)


def snapshot_memory_state(
    aggregate_repo: InMemoryCommercialAggregateRepository,
    processed_repo: InMemoryProcessedEventRepository,
    audit_repo: InMemoryCommercialAuditRepository,
    outbox_repo: InMemoryCommercialOutboxRepository,
) -> Dict[str, Any]:
    """
    Capturar snapshot profundo do estado de todos os stores.

    Usa deep copy para garantir que valor retornado não seja afetado
    por mutações futuras do estado compartilhado.

    Args:
        aggregate_repo: Repositório de agregados
        processed_repo: Repositório de eventos processados
        audit_repo: Repositório de auditoria
        outbox_repo: Repositório de outbox

    Returns:
        Dict contendo:
        - aggregates: deep copy do store de agregados
        - processed_events: deep copy do store de eventos processados
        - audits: deep copy do store de auditoria
        - outbox: deep copy do store de outbox
    """
    return {
        "aggregates": deepcopy(aggregate_repo.store),
        "processed_events": deepcopy(processed_repo.store),
        "audits": deepcopy(audit_repo.store),
        "outbox": deepcopy(outbox_repo.store),
    }


def assert_memory_state_equal(
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    message: str = "Estado deve ser idêntico",
) -> None:
    """
    Asserção profunda de igualdade de estado.

    Compara dois snapshots e valida que são completamente iguais.
    Útil para comprovar que transação não modificou estado ao falhar.

    Args:
        state_before: Snapshot anterior (antes da transação)
        state_after: Snapshot posterior (depois da transação)
        message: Mensagem de erro customizada

    Raises:
        AssertionError: Se estado foi alterado
    """
    # Comparar agregados
    assert state_before["aggregates"] == state_after["aggregates"], (
        f"{message} — agregados alterados:\n"
        f"Antes: {state_before['aggregates']}\n"
        f"Depois: {state_after['aggregates']}"
    )

    # Comparar eventos processados
    assert state_before["processed_events"] == state_after["processed_events"], (
        f"{message} — eventos processados alterados:\n"
        f"Antes: {state_before['processed_events']}\n"
        f"Depois: {state_after['processed_events']}"
    )

    # Comparar auditoria
    assert state_before["audits"] == state_after["audits"], (
        f"{message} — auditorias alteradas:\n"
        f"Antes: {state_before['audits']}\n"
        f"Depois: {state_after['audits']}"
    )

    # Comparar outbox
    assert state_before["outbox"] == state_after["outbox"], (
        f"{message} — outbox alterado:\n"
        f"Antes: {state_before['outbox']}\n"
        f"Depois: {state_after['outbox']}"
    )
