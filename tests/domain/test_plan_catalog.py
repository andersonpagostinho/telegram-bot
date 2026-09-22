"""
TESTES — Plan Catalog

Valida que apenas os 3 planos canônicos são aceitos.
Rejeita planos antigos e inválidos.
"""

import pytest

from domain.plan_catalog import (
    PlanId,
    PlanDef,
    PLAN_CATALOG,
    KNOWN_PLAN_IDS,
    validate_plan_id,
    get_plan_def,
    get_plan_price,
    get_plan_name,
    get_all_plans,
    plan_id_to_enum,
)


class TestPlanCatalogStructure:
    """Testa estrutura do catálogo de planos."""

    def test_catalog_has_three_plans(self):
        """Catálogo deve ter exatamente 3 planos."""
        assert len(PLAN_CATALOG) == 3

    def test_known_plan_ids_count(self):
        """KNOWN_PLAN_IDS deve ter 3 elementos."""
        assert len(KNOWN_PLAN_IDS) == 3

    def test_catalog_has_solo(self):
        """Catálogo deve incluir SOLO."""
        assert "plan_solo" in PLAN_CATALOG
        plan = PLAN_CATALOG["plan_solo"]
        assert plan.plan_id == "plan_solo"
        assert plan.name == "SOLO"
        assert plan.price_brl == 87.00
        assert plan.max_professionals == 1

    def test_catalog_has_profissional(self):
        """Catálogo deve incluir PROFISSIONAL."""
        assert "plan_profissional" in PLAN_CATALOG
        plan = PLAN_CATALOG["plan_profissional"]
        assert plan.plan_id == "plan_profissional"
        assert plan.name == "PROFISSIONAL"
        assert plan.price_brl == 157.00
        assert plan.max_professionals == 3

    def test_catalog_has_saloes(self):
        """Catálogo deve incluir SALÕES."""
        assert "plan_saloes" in PLAN_CATALOG
        plan = PLAN_CATALOG["plan_saloes"]
        assert plan.plan_id == "plan_saloes"
        assert plan.name == "SALÕES"
        assert plan.price_brl == 247.00
        assert plan.max_professionals == 6


class TestValidatePlanId:
    """Testa validação de plan_ids."""

    def test_accept_plan_solo(self):
        """Deve aceitar plan_solo."""
        assert validate_plan_id("plan_solo") is True

    def test_accept_plan_profissional(self):
        """Deve aceitar plan_profissional."""
        assert validate_plan_id("plan_profissional") is True

    def test_accept_plan_saloes(self):
        """Deve aceitar plan_saloes."""
        assert validate_plan_id("plan_saloes") is True

    def test_reject_plan_studio(self):
        """Deve rejeitar plan_studio (plano antigo)."""
        assert validate_plan_id("plan_studio") is False

    def test_reject_plan_solo_pro(self):
        """Deve rejeitar plan_solo_pro (plano antigo)."""
        assert validate_plan_id("plan_solo_pro") is False

    def test_reject_plan_salao247(self):
        """Deve rejeitar plan_salao247 (plano antigo)."""
        assert validate_plan_id("plan_salao247") is False

    def test_reject_plan_pro347(self):
        """Deve rejeitar plan_pro347 (plano antigo)."""
        assert validate_plan_id("plan_pro347") is False

    def test_reject_empty_string(self):
        """Deve rejeitar string vazia."""
        assert validate_plan_id("") is False

    def test_reject_none(self):
        """Deve rejeitar None."""
        assert validate_plan_id(None) is False

    def test_reject_unknown_plan(self):
        """Deve rejeitar plan_id desconhecido."""
        assert validate_plan_id("plan_unknown") is False

    def test_reject_malformed(self):
        """Deve rejeitar plan_ids malformados."""
        assert validate_plan_id("SOLO") is False  # deve ser plan_solo
        assert validate_plan_id("profissional") is False  # sem prefixo plan_
        assert validate_plan_id("plan_") is False  # incompleto


class TestGetPlanDef:
    """Testa obtenção de definição de plano."""

    def test_get_solo_definition(self):
        """Deve retornar definição completa de SOLO."""
        plan = get_plan_def("plan_solo")
        assert plan.plan_id == "plan_solo"
        assert plan.name == "SOLO"
        assert plan.price_brl == 87.00
        assert plan.max_professionals == 1

    def test_get_profissional_definition(self):
        """Deve retornar definição completa de PROFISSIONAL."""
        plan = get_plan_def("plan_profissional")
        assert plan.plan_id == "plan_profissional"
        assert plan.name == "PROFISSIONAL"
        assert plan.price_brl == 157.00
        assert plan.max_professionals == 3

    def test_get_saloes_definition(self):
        """Deve retornar definição completa de SALÕES."""
        plan = get_plan_def("plan_saloes")
        assert plan.plan_id == "plan_saloes"
        assert plan.name == "SALÕES"
        assert plan.price_brl == 247.00
        assert plan.max_professionals == 6

    def test_raise_on_invalid_plan(self):
        """Deve lançar ValueError para plan_id inválido."""
        with pytest.raises(ValueError):
            get_plan_def("plan_studio")

    def test_raise_on_unknown_plan(self):
        """Deve lançar ValueError para plan_id desconhecido."""
        with pytest.raises(ValueError):
            get_plan_def("plan_unknown")

    def test_error_message_lists_known_plans(self):
        """Mensagem de erro deve listar planos conhecidos."""
        with pytest.raises(ValueError) as exc_info:
            get_plan_def("plan_studio")
        error_msg = str(exc_info.value)
        assert "plan_solo" in error_msg
        assert "plan_profissional" in error_msg
        assert "plan_saloes" in error_msg


class TestGetPlanPrice:
    """Testa obtenção de preço."""

    def test_solo_price(self):
        """SOLO deve custar R$ 87.00."""
        assert get_plan_price("plan_solo") == 87.00

    def test_profissional_price(self):
        """PROFISSIONAL deve custar R$ 157.00."""
        assert get_plan_price("plan_profissional") == 157.00

    def test_saloes_price(self):
        """SALÕES deve custar R$ 247.00."""
        assert get_plan_price("plan_saloes") == 247.00

    def test_raise_on_invalid_plan(self):
        """Deve lançar ValueError para plan_id inválido."""
        with pytest.raises(ValueError):
            get_plan_price("plan_unknown")


class TestGetPlanName:
    """Testa obtenção de nome."""

    def test_solo_name(self):
        """Nome de SOLO."""
        assert get_plan_name("plan_solo") == "SOLO"

    def test_profissional_name(self):
        """Nome de PROFISSIONAL."""
        assert get_plan_name("plan_profissional") == "PROFISSIONAL"

    def test_saloes_name(self):
        """Nome de SALÕES."""
        assert get_plan_name("plan_saloes") == "SALÕES"


class TestGetAllPlans:
    """Testa obtenção de catálogo completo."""

    def test_returns_all_three_plans(self):
        """Deve retornar todos os 3 planos."""
        all_plans = get_all_plans()
        assert len(all_plans) == 3
        assert "plan_solo" in all_plans
        assert "plan_profissional" in all_plans
        assert "plan_saloes" in all_plans

    def test_returns_copy_not_reference(self):
        """Deve retornar cópia, não referência."""
        plans1 = get_all_plans()
        plans2 = get_all_plans()
        # Modificar plans1 não deve afetar plans2
        plans1["plan_novo"] = "valor"
        assert "plan_novo" not in plans2
        # Catálogo original não deve ser afetado
        assert "plan_novo" not in PLAN_CATALOG


class TestPlanIdEnum:
    """Testa enum PlanId."""

    def test_enum_values(self):
        """Enum deve ter 3 valores."""
        assert len(PlanId) == 3

    def test_enum_solo_value(self):
        """PlanId.SOLO deve valer 'plan_solo'."""
        assert PlanId.SOLO.value == "plan_solo"

    def test_enum_profissional_value(self):
        """PlanId.PROFISSIONAL deve valer 'plan_profissional'."""
        assert PlanId.PROFISSIONAL.value == "plan_profissional"

    def test_enum_saloes_value(self):
        """PlanId.SALOES deve valer 'plan_saloes'."""
        assert PlanId.SALOES.value == "plan_saloes"


class TestPlanIdToEnum:
    """Testa conversão string → enum."""

    def test_convert_solo(self):
        """Deve converter 'plan_solo' para PlanId.SOLO."""
        result = plan_id_to_enum("plan_solo")
        assert result == PlanId.SOLO

    def test_convert_profissional(self):
        """Deve converter 'plan_profissional' para PlanId.PROFISSIONAL."""
        result = plan_id_to_enum("plan_profissional")
        assert result == PlanId.PROFISSIONAL

    def test_convert_saloes(self):
        """Deve converter 'plan_saloes' para PlanId.SALOES."""
        result = plan_id_to_enum("plan_saloes")
        assert result == PlanId.SALOES

    def test_return_none_for_invalid(self):
        """Deve retornar None para plan_id inválido."""
        assert plan_id_to_enum("plan_unknown") is None
        assert plan_id_to_enum("plan_studio") is None


class TestPlanDefImmutability:
    """Testa que PlanDef é imutável."""

    def test_plan_def_frozen(self):
        """PlanDef deve ser imutável (frozen)."""
        plan = PLAN_CATALOG["plan_solo"]
        with pytest.raises(AttributeError):
            plan.price_brl = 99.00
