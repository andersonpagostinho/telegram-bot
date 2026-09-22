"""
Testes de versionamento semântico (FASE 4).

Validam que versão incrementa APENAS quando snapshot tem mudança semântica.
"""

import pytest
from datetime import datetime
from services.billing_domain_service import (
    AggregateSnapshot,
    TrialSnapshot,
    AssinaturaSnapshot,
    PagamentoSnapshot,
    AcessoSnapshot,
    RetencaoSnapshot,
)
from services.trial_state_machine import TrialState
from services.billing_state_machines import (
    AssinaturaState,
    PagamentoState,
    AcessoState,
    RetencaoState,
)
from services.semantic_snapshot import (
    semantic_snapshot_projection,
    has_semantic_snapshot_change,
    extract_semantic_metadata,
)


class TestSemanticMetadataExtraction:
    """Testes de filtragem de metadata semântica."""

    def test_inclui_campo_semantico_permitido(self):
        """Campo na allowlist é incluído."""
        metadata = {
            "trial_expires": "2026-08-27",
            "trial_days_remaining": 30,
        }
        result = extract_semantic_metadata(metadata)
        assert result == metadata

    def test_exclui_campo_tecnico(self):
        """Campo técnico é excluído."""
        metadata = {
            "trial_expires": "2026-08-27",
            "timestamp": "2026-07-27T12:00:00",  # Técnico
            "trace_id": "xyz",  # Técnico
        }
        result = extract_semantic_metadata(metadata)
        assert result == {"trial_expires": "2026-08-27"}
        assert "timestamp" not in result
        assert "trace_id" not in result

    def test_exclui_campo_desconhecido(self):
        """Campo desconhecido (não na allowlist) é excluído por segurança."""
        metadata = {
            "trial_expires": "2026-08-27",
            "unknown_field": "should_not_include",
        }
        result = extract_semantic_metadata(metadata)
        assert result == {"trial_expires": "2026-08-27"}
        assert "unknown_field" not in result

    def test_metadata_vazio(self):
        """Metadata vazio retorna dicionário vazio."""
        assert extract_semantic_metadata({}) == {}
        assert extract_semantic_metadata(None) == {}


class TestSemanticSnapshotProjection:
    """Testes de projeção semântica de snapshot."""

    @pytest.fixture
    def snapshot_inicial(self):
        """Snapshot em estado inicial."""
        return AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.PREPARADO, metadata={}),
            assinatura=AssinaturaSnapshot(state=AssinaturaState.PENDENTE, metadata={}),
            pagamento=PagamentoSnapshot(state=PagamentoState.PENDENTE, metadata={}),
            acesso=AcessoSnapshot(state=AcessoState.LIBERADO, metadata={}),
            retencao=RetencaoSnapshot(state=RetencaoState.ATIVO, metadata={}),
            timestamp=datetime.utcnow(),
        )

    def test_projecao_nao_inclui_timestamp(self, snapshot_inicial):
        """Projeção não inclui timestamp técnico."""
        proj = semantic_snapshot_projection(snapshot_inicial)
        # Não há campo timestamp na projeção
        assert not hasattr(proj, "timestamp")

    def test_projecao_inclui_estados(self, snapshot_inicial):
        """Projeção inclui valores de state."""
        proj = semantic_snapshot_projection(snapshot_inicial)
        assert proj.trial_state == "PREPARADO"
        assert proj.assinatura_state == "PENDENTE"
        assert proj.pagamento_state == "PENDENTE"
        assert proj.acesso_state == "LIBERADO"
        assert proj.retencao_state == "ATIVO"

    def test_projecao_congelada(self, snapshot_inicial):
        """Projeção é imutável (frozen)."""
        proj = semantic_snapshot_projection(snapshot_inicial)
        with pytest.raises(AttributeError):
            proj.trial_state = "ALTERADO"


class TestHasSemanticSnapshotChange:
    """Testes de detecção de mudança semântica."""

    @pytest.fixture
    def snapshot_base(self):
        """Snapshot base para testes."""
        return AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.PREPARADO, metadata={}),
            assinatura=AssinaturaSnapshot(state=AssinaturaState.PENDENTE, metadata={}),
            pagamento=PagamentoSnapshot(state=PagamentoState.PENDENTE, metadata={}),
            acesso=AcessoSnapshot(state=AcessoState.LIBERADO, metadata={}),
            retencao=RetencaoSnapshot(state=RetencaoState.ATIVO, metadata={}),
            timestamp=datetime.utcnow(),
        )

    def test_mudanca_trial_state_detectada(self, snapshot_base):
        """Mudança de trial.state é detectada."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.ATIVO, metadata={}),  # Mudou
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is True

    def test_mudanca_assinatura_state_detectada(self, snapshot_base):
        """Mudança de assinatura.state é detectada."""
        snapshot_after = AggregateSnapshot(
            trial=snapshot_base.trial,
            assinatura=AssinaturaSnapshot(state=AssinaturaState.ATIVA, metadata={}),  # Mudou
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is True

    def test_mudanca_metadata_semantica_detectada(self, snapshot_base):
        """Mudança de metadata semântica é detectada."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(
                state=snapshot_base.trial.state,
                metadata={"trial_expires": "2026-08-27"},  # Metadado semântico adicionado
            ),
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is True

    def test_mudanca_timestamp_nao_detectada(self, snapshot_base):
        """Mudança de timestamp não é detectada (técnico)."""
        snapshot_after = AggregateSnapshot(
            trial=snapshot_base.trial,
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),  # Timestamp diferente
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is False

    def test_mudanca_campo_tecnico_nao_detectada(self, snapshot_base):
        """Mudança de campo técnico em metadata não é detectada."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(
                state=snapshot_base.trial.state,
                metadata={
                    "trace_id": "novo_trace",  # Campo técnico
                    "timestamp": "2026-07-27T13:00:00",  # Campo técnico
                },
            ),
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is False

    def test_snapshot_identico_retorna_false(self, snapshot_base):
        """Snapshots idênticos não têm mudança."""
        snapshot_after = AggregateSnapshot(
            trial=snapshot_base.trial,
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=snapshot_base.timestamp,
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is False

    def test_multiplos_campos_alterados_retorna_true(self, snapshot_base):
        """Múltiplos campos semânticos alterados retorna True."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.ATIVO, metadata={}),  # Mudou
            assinatura=AssinaturaSnapshot(state=AssinaturaState.ATIVA, metadata={}),  # Mudou
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is True

    def test_determinismo_mesmos_inputs_mesma_saida(self, snapshot_base):
        """Mesmo input sempre produz mesma saída (determinismo)."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.ATIVO, metadata={}),
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )
        result1 = has_semantic_snapshot_change(snapshot_base, snapshot_after)
        result2 = has_semantic_snapshot_change(snapshot_base, snapshot_after)
        assert result1 == result2

    def test_simetria_comparacao(self, snapshot_base):
        """A ordem de comparação é simétrica para snapshots diferentes."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.ATIVO, metadata={}),
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )
        result1 = has_semantic_snapshot_change(snapshot_base, snapshot_after)
        result2 = has_semantic_snapshot_change(snapshot_after, snapshot_base)
        assert result1 == result2

    def test_mudanca_campo_desconhecido_ignorado(self, snapshot_base):
        """Mudança em campo desconhecido é ignorada (não incrementa versão)."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(
                state=snapshot_base.trial.state,
                metadata={
                    "unknown_field": "novo_valor",  # Desconhecido
                },
            ),
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is False

    def test_todos_estados_alterados(self, snapshot_base):
        """Todos os estados alterados é mudança."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.ATIVO, metadata={}),
            assinatura=AssinaturaSnapshot(state=AssinaturaState.ATIVA, metadata={}),
            pagamento=PagamentoSnapshot(state=PagamentoState.APROVADO, metadata={}),
            acesso=AcessoSnapshot(state=AcessoState.RESTRITO, metadata={}),
            retencao=RetencaoSnapshot(state=RetencaoState.EM_RETENCAO, metadata={}),
            timestamp=datetime.utcnow(),
        )
        assert has_semantic_snapshot_change(snapshot_base, snapshot_after) is True

    def test_snapshot_nao_mutado(self, snapshot_base):
        """Snapshots originais não são mutados pela comparação."""
        snapshot_after = AggregateSnapshot(
            trial=TrialSnapshot(state=TrialState.ATIVO, metadata={}),
            assinatura=snapshot_base.assinatura,
            pagamento=snapshot_base.pagamento,
            acesso=snapshot_base.acesso,
            retencao=snapshot_base.retencao,
            timestamp=datetime.utcnow(),
        )

        # Guardar valores originais
        trial_state_before = snapshot_base.trial.state
        assinatura_state_before = snapshot_base.assinatura.state

        # Executar comparação
        has_semantic_snapshot_change(snapshot_base, snapshot_after)

        # Verificar que não foram mutados
        assert snapshot_base.trial.state == trial_state_before
        assert snapshot_base.assinatura.state == assinatura_state_before
