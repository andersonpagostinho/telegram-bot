"""
Fake BillingDomainService para testes com controle determinístico de eventos internos.

Permite configurar:
- Número de eventos (0, 1, 3, N)
- Tipos de eventos
- Snapshot alterado semanticamente
- Transitions válidas
- Sem modificar máquinas de estado de produção
"""

from typing import Dict, Any, List
from copy import deepcopy
from datetime import datetime

from services.billing_domain_service import (
    BillingDomainService,
    BillingDomainServiceResult,
    AggregateSnapshot,
    TrialSnapshot,
    AssinaturaSnapshot,
    PagamentoSnapshot,
    AcessoSnapshot,
    RetencaoSnapshot,
    MachineTransitionResult,
    TransitionDecision,
)
from services.trial_state_machine import TrialState
from services.billing_state_machines import (
    AssinaturaState,
    PagamentoState,
    AcessoState,
    RetencaoState,
)


class MockInternalEvent:
    """Evento interno mock para testes."""

    def __init__(self, event_type: str, payload: Dict[str, Any]):
        self.event_type = event_type
        self.payload = payload
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at,
        }


class FakeBillingDomainService(BillingDomainService):
    """
    Fake determinístico que permite configurar eventos internos.

    Uso:
        fake = FakeBillingDomainService()
        fake.with_internal_events(3, [
            ("event_type_1", {"key": "value1"}),
            ("event_type_2", {"key": "value2"}),
            ("event_type_3", {"key": "value3"}),
        ])
        result = fake.process(snapshot, event_type, payload, correlation_id)
    """

    def __init__(self):
        super().__init__()
        self._internal_events_config: List[tuple] = []
        self._snapshot_modification_enabled: bool = True

    def with_internal_events(
        self,
        count: int,
        events: List[tuple] = None,
    ) -> "FakeBillingDomainService":
        """
        Configurar número de eventos internos a serem retornados.

        Args:
            count: Número de eventos (0, 1, 3, etc.)
            events: Lista de (event_type, payload) — se None, gera automaticamente
        """
        if events is None:
            events = [
                (f"internal_event_{i}", {"index": i})
                for i in range(count)
            ]
        self._internal_events_config = events
        return self

    def with_snapshot_modification(self, enabled: bool) -> "FakeBillingDomainService":
        """Habilitar/desabilitar modificação semântica do snapshot."""
        self._snapshot_modification_enabled = enabled
        return self

    def process(
        self,
        snapshot: AggregateSnapshot,
        external_event_type: str,
        external_event_payload: Dict[str, Any],
        correlation_id: str,
    ) -> BillingDomainServiceResult:
        """
        Process com controle de eventos internos.

        Se configurado, retorna snapshot_after alterado semanticamente.
        """
        # Chamar implementação real para validação de máquinas de estado
        result = super().process(
            snapshot=snapshot,
            external_event_type=external_event_type,
            external_event_payload=external_event_payload,
            correlation_id=correlation_id,
        )

        # Se falha, retornar sem modificações
        if not result.success:
            return result

        # Modificar snapshot semanticamente se habilitado
        if self._snapshot_modification_enabled and result.snapshot_after:
            new_assinatura = AssinaturaSnapshot(
                state=AssinaturaState.ATIVA,
                metadata={"fake_processed": True, "original_state": result.snapshot_after.assinatura.state},
            )
            modified_snapshot = AggregateSnapshot(
                trial=result.snapshot_after.trial,
                assinatura=new_assinatura,
                pagamento=result.snapshot_after.pagamento,
                acesso=result.snapshot_after.acesso,
                retencao=result.snapshot_after.retencao,
            )
        else:
            modified_snapshot = result.snapshot_after

        # Gerar eventos internos
        internal_events = []
        for event_type, payload in self._internal_events_config:
            internal_events.append(MockInternalEvent(event_type, payload))

        # Retornar resultado com eventos injetados
        return BillingDomainServiceResult(
            success=True,
            correlation_id=correlation_id,
            source_event_id=external_event_payload.get("provider_event_id"),
            snapshot_before=result.snapshot_before,
            snapshot_after=modified_snapshot or result.snapshot_after,
            transitions=result.transitions,
            internal_events=internal_events,  # ← Eventos configurados
            suggested_effects=result.suggested_effects,
        )


class FakeBillingDomainServiceBuilder:
    """Builder fluente para configurar o fake."""

    def __init__(self):
        self.fake = FakeBillingDomainService()

    def with_zero_events(self) -> "FakeBillingDomainServiceBuilder":
        """Sem eventos internos."""
        self.fake.with_internal_events(0, [])
        return self

    def with_one_event(self, event_type: str = "test_event") -> "FakeBillingDomainServiceBuilder":
        """Um evento interno."""
        self.fake.with_internal_events(1, [(event_type, {"index": 0})])
        return self

    def with_three_events(
        self,
        event_types: List[str] = None,
    ) -> "FakeBillingDomainServiceBuilder":
        """Três eventos internos."""
        if event_types is None:
            event_types = ["event_1", "event_2", "event_3"]
        events = [
            (event_types[i], {"index": i, "type": event_types[i]})
            for i in range(3)
        ]
        self.fake.with_internal_events(3, events)
        return self

    def with_three_same_type(self, event_type: str = "same_event") -> "FakeBillingDomainServiceBuilder":
        """Três eventos do mesmo tipo."""
        events = [
            (event_type, {"index": i})
            for i in range(3)
        ]
        self.fake.with_internal_events(3, events)
        return self

    def with_snapshot_modified(self) -> "FakeBillingDomainServiceBuilder":
        """Snapshot semanticamente alterado."""
        self.fake.with_snapshot_modification(True)
        return self

    def with_snapshot_unmodified(self) -> "FakeBillingDomainServiceBuilder":
        """Snapshot igual ao original."""
        self.fake.with_snapshot_modification(False)
        return self

    def build(self) -> FakeBillingDomainService:
        """Construir instância."""
        return self.fake
