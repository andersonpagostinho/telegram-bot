"""
Nomes canônicos de operações para failure injection (FASE 5).

Centralizar aqui evita divergência textual entre:
- Nomes usados em decorators
- Nomes usados em injetor
- Nomes usados em testes
"""


class OperationNames:
    """Nomes canônicos invioláveis."""

    # Processed Event Repository
    PROCESSED_EVENT_GET = "processed_event.get"
    PROCESSED_EVENT_SAVE = "processed_event.save"
    PROCESSED_EVENT_MARK_PROCESSING = "processed_event.mark_processing"

    # Aggregate Repository
    AGGREGATE_GET = "aggregate.get"
    AGGREGATE_SAVE = "aggregate.save"

    # Audit Repository
    AUDIT_APPEND = "audit.append"

    # Outbox Repository
    OUTBOX_SAVE = "outbox.save"

    # Unit of Work
    UOW_COMMIT_PREPARE = "uow.commit.prepare"
    UOW_COMMIT_PUBLISH = "uow.commit.publish"
    UOW_EXIT = "uow.exit"
