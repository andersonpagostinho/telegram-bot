"""
PLANO CATALOG — Fonte Canônica Única dos Planos

Define os 3 planos canônicos suportados pelo NeoEve.
Esta é a ÚNICA fonte de verdade para:
- IDs de planos
- Nomes de planos
- Preços oficiais

Baseado em: CATALOGO_COMERCIAL_NEOEVE.md (V1.2, 2026-07-27)
Validação: Preços conforme index_2.html (site em produção)

Histórico:
- Versão anterior (5 planos): SOLO87, SOLOPRO117, STUDIO157, SALAO247, PRO347
- Decisão (2026-08-17): Reduzir para 3 planos canônicos apenas
- Planos mantidos: SOLO, PROFISSIONAL, SALÕES
- Planos removidos: SOLO_PRO, PRO347 (sem clientes pagos)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional


class PlanId(str, Enum):
    """IDs de planos canônicos suportados."""
    SOLO = "plan_solo"
    PROFISSIONAL = "plan_profissional"
    SALOES = "plan_saloes"


@dataclass(frozen=True)
class PlanDef:
    """Definição imutável de um plano."""
    plan_id: str
    name: str
    price_brl: float
    max_professionals: int


# Fonte canônica única dos 3 planos
PLAN_CATALOG: Dict[str, PlanDef] = {
    PlanId.SOLO.value: PlanDef(
        plan_id="plan_solo",
        name="SOLO",
        price_brl=87.00,
        max_professionals=1,
    ),
    PlanId.PROFISSIONAL.value: PlanDef(
        plan_id="plan_profissional",
        name="PROFISSIONAL",
        price_brl=157.00,
        max_professionals=3,
    ),
    PlanId.SALOES.value: PlanDef(
        plan_id="plan_saloes",
        name="SALÕES",
        price_brl=247.00,
        max_professionals=6,
    ),
}

# Conjunto de IDs válidos para validação rápida
KNOWN_PLAN_IDS: set = set(PLAN_CATALOG.keys())

# Lista ordenada de planos (para iteração em UI)
PLAN_IDS_ORDERED = [
    PlanId.SOLO.value,
    PlanId.PROFISSIONAL.value,
    PlanId.SALOES.value,
]


def validate_plan_id(plan_id: str) -> bool:
    """
    Valida se um plan_id é conhecido e válido.

    Rejeita:
    - plan_studio, plan_solo_pro, plan_salao247, plan_pro347 (planos antigos)
    - String vazia ou None
    - IDs genéricos desconhecidos

    Aceita:
    - plan_solo
    - plan_profissional
    - plan_saloes

    Args:
        plan_id: String do ID do plano

    Returns:
        True se plan_id é válido, False caso contrário
    """
    if not plan_id or not isinstance(plan_id, str):
        return False
    return plan_id in KNOWN_PLAN_IDS


def get_plan_def(plan_id: str) -> PlanDef:
    """
    Obtém definição completa de um plano.

    Args:
        plan_id: ID do plano (ex: "plan_solo")

    Returns:
        PlanDef com preço, nome e limites

    Raises:
        ValueError: Se plan_id é inválido
    """
    if not validate_plan_id(plan_id):
        raise ValueError(
            f"Plan ID inválido: {plan_id}. "
            f"Planos conhecidos: {', '.join(sorted(KNOWN_PLAN_IDS))}"
        )
    return PLAN_CATALOG[plan_id]


def get_plan_price(plan_id: str) -> float:
    """
    Conveniência: obtém apenas o preço de um plano.

    Args:
        plan_id: ID do plano

    Returns:
        Preço em reais (float)

    Raises:
        ValueError: Se plan_id é inválido
    """
    return get_plan_def(plan_id).price_brl


def get_plan_name(plan_id: str) -> str:
    """
    Conveniência: obtém apenas o nome de um plano.

    Args:
        plan_id: ID do plano

    Returns:
        Nome exibível (str)

    Raises:
        ValueError: Se plan_id é inválido
    """
    return get_plan_def(plan_id).name


def get_all_plans() -> Dict[str, PlanDef]:
    """
    Retorna cópia imutável do catálogo completo.

    Returns:
        Dicionário {plan_id: PlanDef}
    """
    return dict(PLAN_CATALOG)


def plan_id_to_enum(plan_id: str) -> Optional[PlanId]:
    """
    Converte string plan_id para enum PlanId.

    Args:
        plan_id: String do ID

    Returns:
        PlanId enum ou None se inválido
    """
    try:
        return PlanId(plan_id)
    except ValueError:
        return None
