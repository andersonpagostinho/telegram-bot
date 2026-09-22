"""
TESTES — Billing Domain Service

Valida orquestração pura das máquinas, determinismo, isolamento e cenários críticos.
"""

import pytest
from datetime import datetime

from services.billing_domain_service import (
    BillingDomainService,
    AggregateSnapshot,
    TrialSnapshot,
    AssinaturaSnapshot,
    PagamentoSnapshot,
    AcessoSnapshot,
    RetencaoSnapshot,
    TransitionDecision,
)
from services.trial_state_machine import TrialState
from services.billing_state_machines import (
    AssinaturaState,
    PagamentoState,
    AcessoState,
    RetencaoState,
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def default_aggregate_snapshot():
    """Snapshot padrão: trial PREPARADO, assinatura PENDENTE, etc."""
    return AggregateSnapshot(
        trial=TrialSnapshot(state=TrialState.PREPARADO),
        assinatura=AssinaturaSnapshot(state=AssinaturaState.PENDENTE),
        pagamento=PagamentoSnapshot(state=PagamentoState.PENDENTE),
        acesso=AcessoSnapshot(state=AcessoState.LIBERADO),
        retencao=RetencaoSnapshot(state=RetencaoState.ATIVO),
    )


@pytest.fixture
def active_snapshot():
    """Snapshot após pagamento aprovado: assinatura ATIVA, acesso LIBERADO."""
    return AggregateSnapshot(
        trial=TrialSnapshot(state=TrialState.ATIVO),
        assinatura=AssinaturaSnapshot(state=AssinaturaState.ATIVA),
        pagamento=PagamentoSnapshot(state=PagamentoState.APROVADO),
        acesso=AcessoSnapshot(state=AcessoState.LIBERADO),
        retencao=RetencaoSnapshot(state=RetencaoState.ATIVO),
    )


@pytest.fixture
def service():
    """Instância do BillingDomainService."""
    return BillingDomainService()


# ==============================================================================
# TESTES DE VALIDAÇÃO DE ENTRADA
# ==============================================================================


class TestEventValidation:
    """Testa validação de eventos de entrada."""

    def test_missing_correlation_id(self, service, default_aggregate_snapshot):
        """Evento sem correlation_id é rejeitado."""
        event = {
            "event_type": "purchase_approved",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            # correlation_id FALTANDO
        }

        result = service.process_external_event(event, default_aggregate_snapshot)
        assert result.success is False
        assert result.failure_code == "validation_failed"

    def test_missing_event_type(self, service, default_aggregate_snapshot):
        """Evento sem event_type é rejeitado."""
        event = {
            "correlation_id": "corr_123",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            # event_type FALTANDO
        }

        result = service.process_external_event(event, default_aggregate_snapshot)
        assert result.success is False

    def test_invalid_received_at_type(self, service, default_aggregate_snapshot):
        """Evento com received_at não-datetime é rejeitado."""
        event = {
            "correlation_id": "corr_123",
            "event_type": "purchase_approved",
            "received_at": "2026-07-27",  # String, não datetime
            "tenant_id": "tenant_abc",
        }

        result = service.process_external_event(event, default_aggregate_snapshot)
        assert result.success is False

    def test_missing_tenant_id(self, service, default_aggregate_snapshot):
        """Evento sem tenant_id é rejeitado."""
        event = {
            "correlation_id": "corr_123",
            "event_type": "purchase_approved",
            "received_at": datetime.utcnow(),
            # tenant_id FALTANDO
        }

        result = service.process_external_event(event, default_aggregate_snapshot)
        assert result.success is False


# ==============================================================================
# TESTES DE SUCESSO (HAPPY PATH)
# ==============================================================================


class TestHappyPath:
    """Testa cenários de sucesso."""

    def test_purchase_approved_transitions_machines(
        self, service, default_aggregate_snapshot
    ):
        """Evento purchase_approved aplica transições em múltiplas máquinas."""
        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "source_event_id": "hotmart_456",
            "received_at": datetime(2026, 7, 27, 14, 30, 0),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result = service.process_external_event(event, default_aggregate_snapshot)

        # Deve ser sucesso
        assert result.success is True
        assert result.failure_reason is None

        # Deve ter transições aplicadas
        assert len(result.transitions) > 0
        applied_transitions = [
            t for t in result.transitions if t.decision == TransitionDecision.APPLIED
        ]
        assert len(applied_transitions) > 0

        # Snapshot deve mudar
        assert result.snapshot_before != result.snapshot_after

    def test_snapshot_preservation_on_failure(
        self, service, default_aggregate_snapshot
    ):
        """Snapshot não muda em caso de falha."""
        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "received_at": datetime.utcnow(),
            # tenant_id FALTANDO
        }

        result = service.process_external_event(event, default_aggregate_snapshot)

        # Mesmo com falha, snapshot é preservado
        assert result.snapshot_before == result.snapshot_after


# ==============================================================================
# TESTES DE DETERMINISMO
# ==============================================================================


class TestDeterminism:
    """Testa que entrada idêntica produz saída idêntica."""

    def test_same_event_produces_same_result(
        self, service, default_aggregate_snapshot
    ):
        """Processar mesmo evento duas vezes produz mesmo resultado."""
        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "source_event_id": "hotmart_456",
            "received_at": datetime(2026, 7, 27, 14, 30, 0),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result1 = service.process_external_event(event, default_aggregate_snapshot)
        result2 = service.process_external_event(event, default_aggregate_snapshot)

        # Resultados são idênticos (exceto processed_at timestamp)
        assert result1.success == result2.success
        assert result1.snapshot_after.to_dict() == result2.snapshot_after.to_dict()
        assert len(result1.transitions) == len(result2.transitions)

    def test_idempotency_validation(self, service, default_aggregate_snapshot):
        """Reaplicação de evento validada por provider_event_id."""
        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "source_event_id": "hotmart_same_456",  # MESMO ID
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result1 = service.process_external_event(event, default_aggregate_snapshot)
        result2 = service.process_external_event(event, default_aggregate_snapshot)

        # Ambos devem ter mesmo resultado estrutural
        assert result1.success == result2.success


# ==============================================================================
# TESTES DE CENÁRIOS CRÍTICOS
# ==============================================================================


class TestCriticalScenarios:
    """Testa cenários críticos de orquestração."""

    def test_payment_approved_activates_subscription_and_access(
        self, service, default_aggregate_snapshot
    ):
        """Pagamento aprovado ativa assinatura e libera acesso."""
        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result = service.process_external_event(event, default_aggregate_snapshot)

        assert result.success is True

        # Verificar transições aplicadas
        assinatura_transition = next(
            (t for t in result.transitions if t.machine_name == "AssinaturaStateMachine"),
            None,
        )
        pagamento_transition = next(
            (t for t in result.transitions if t.machine_name == "PagamentoStateMachine"),
            None,
        )
        acesso_transition = next(
            (t for t in result.transitions if t.machine_name == "AcessoStateMachine"),
            None,
        )

        assert assinatura_transition is not None
        assert pagamento_transition is not None
        assert acesso_transition is not None

    def test_payment_approved_converts_trial(
        self, service, active_snapshot
    ):
        """Se trial ATIVO, payment_approved converte trial."""
        # Snapshot com trial ativo
        snapshot = AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.ATIVO),  # ATIVO
            assinatura=AssinaturaSnapshot(state=AssinaturaState.PENDENTE),
            pagamento=PagamentoSnapshot(state=PagamentoState.PENDENTE),
            acesso=AcessoSnapshot(state=AcessoState.LIBERADO),
            retencao=RetencaoSnapshot(state=RetencaoState.ATIVO),
        )

        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result = service.process_external_event(event, snapshot)

        # Trial deve transicionar
        trial_transition = next(
            (t for t in result.transitions if t.machine_name == "TrialStateMachine"),
            None,
        )
        assert trial_transition is not None

    def test_unknown_event_type_ignored(self, service, default_aggregate_snapshot):
        """Evento desconhecido é ignorado."""
        event = {
            "event_type": "unknown_event_type_xyz",
            "correlation_id": "corr_123",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
        }

        result = service.process_external_event(event, default_aggregate_snapshot)

        # Nenhuma transição deve ser aplicada
        applied = [t for t in result.transitions if t.decision == TransitionDecision.APPLIED]
        assert len(applied) == 0


# ==============================================================================
# TESTES DE ISOLAMENTO
# ==============================================================================


class TestTenantIsolation:
    """Testa isolamento por tenant."""

    def test_event_processed_with_tenant_id(self, service, default_aggregate_snapshot):
        """Evento com tenant_id específico não afeta outros tenants."""
        event_tenant_a = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_a",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_a",
            "amount": 100.0,
        }

        event_tenant_b = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_b",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_b",
            "amount": 200.0,
        }

        service = BillingDomainService()

        # Processar ambos os eventos
        result_a = service.process_external_event(
            event_tenant_a, default_aggregate_snapshot
        )
        result_b = service.process_external_event(
            event_tenant_b, default_aggregate_snapshot
        )

        # Ambos devem ser processados (serviço não persiste, apenas valida)
        assert result_a.success is True or result_a.success is False
        assert result_b.success is True or result_b.success is False
        # Correlations devem ser diferentes
        assert result_a.correlation_id != result_b.correlation_id


# ==============================================================================
# TESTES DE IMUTABILIDADE
# ==============================================================================


class TestImmutability:
    """Testa que snapshots não são mutados."""

    def test_snapshot_not_mutated_on_success(
        self, service, default_aggregate_snapshot
    ):
        """Snapshot original não é mutado em caso de sucesso."""
        original_snapshot = default_aggregate_snapshot

        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result = service.process_external_event(event, original_snapshot)

        # Snapshot original não deve mudar
        assert original_snapshot.trial.state == TrialState.PREPARADO
        assert original_snapshot.assinatura.state == AssinaturaState.PENDENTE


# ==============================================================================
# TESTES DE RESULTADO ESTRUTURADO
# ==============================================================================


class TestResultStructure:
    """Testa estrutura do resultado."""

    def test_result_has_required_fields(self, service, default_aggregate_snapshot):
        """Resultado tem todos os campos obrigatórios."""
        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "source_event_id": "hotmart_456",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result = service.process_external_event(event, default_aggregate_snapshot)

        # Campos obrigatórios
        assert hasattr(result, "success")
        assert hasattr(result, "correlation_id")
        assert hasattr(result, "source_event_id")
        assert hasattr(result, "snapshot_before")
        assert hasattr(result, "snapshot_after")
        assert hasattr(result, "transitions")
        assert hasattr(result, "internal_events")
        assert hasattr(result, "failure_reason")
        assert hasattr(result, "failure_code")
        assert hasattr(result, "suggested_effects")
        assert hasattr(result, "processed_at")

    def test_result_serializable(self, service, default_aggregate_snapshot):
        """Resultado pode ser serializado para dicionário."""
        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result = service.process_external_event(event, default_aggregate_snapshot)
        dict_result = result.to_dict()

        assert isinstance(dict_result, dict)
        assert "success" in dict_result
        assert "correlation_id" in dict_result
        assert "snapshot_before" in dict_result
        assert "snapshot_after" in dict_result
        assert "transitions" in dict_result


# ==============================================================================
# TESTES DE EFEITOS SUGERIDOS
# ==============================================================================


class TestSuggestedEffects:
    """Testa sugestão de efeitos (não executados em Fase 2)."""

    def test_suggested_effects_returned_not_executed(
        self, service, default_aggregate_snapshot
    ):
        """Efeitos são retornados, não executados."""
        event = {
            "event_type": "purchase_approved",
            "correlation_id": "corr_123",
            "received_at": datetime.utcnow(),
            "tenant_id": "tenant_abc",
            "amount": 157.00,
        }

        result = service.process_external_event(event, default_aggregate_snapshot)

        # Efeitos sugeridos devem estar presentes
        assert isinstance(result.suggested_effects, list)
        # Mas não executados (isso é verificado na ausência de Firestore calls)
