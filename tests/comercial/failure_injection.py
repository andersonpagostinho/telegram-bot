"""
Infraestrutura de injeção de falhas determinísticas para testes de atomicidade.

Permite provocar exceções em pontos específicos do processamento sem modificar
código de produção.
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class InjectedFailureType(str, Enum):
    """Tipos de falhas injetadas."""
    READ_FAILURE = "read_failure"
    WRITE_FAILURE = "write_failure"
    DOMAIN_FAILURE = "domain_failure"
    COMMIT_FAILURE = "commit_failure"
    ROLLBACK_FAILURE = "rollback_failure"


class InjectedFailureException(Exception):
    """Exceção base para falhas injetadas."""
    def __init__(self, failure_type: InjectedFailureType, operation: str, message: str = ""):
        self.failure_type = failure_type
        self.operation = operation
        super().__init__(f"[{failure_type.value}] {operation}: {message}")


@dataclass
class FailurePoint:
    """Ponto específico onde injetar falha."""
    operation: str  # Nome da operação (ex: "aggregate_repository.save")
    call_number: int = 1  # Qual chamada dentro da transação falha (1-based)
    enabled: bool = True  # Se deve injetar falha


@dataclass
class FailurePlan:
    """Plano de falha para uma transação de teste."""
    failure_type: InjectedFailureType
    operation: str
    call_number: int = 1
    message: str = ""

    def matches(self, operation: str, call_count: int) -> bool:
        """Verificar se essa falha deve ser injetada."""
        return (
            self.operation == operation and
            call_count == self.call_number
        )


class FailureInjector:
    """
    Injetor de falhas determinísticas para testes.

    Permite provocar exceções em operações específicas dentro de transações.
    Cada operação tem um contador interno que incrementa cada vez que é chamada.
    """

    def __init__(self):
        self.failure_plans: Dict[str, FailurePlan] = {}
        self.call_counts: Dict[str, int] = {}
        self.enabled = False

    def plan_failure(self, plan: FailurePlan) -> None:
        """Registrar um plano de falha."""
        self.failure_plans[plan.operation] = plan

    def enable(self) -> None:
        """Habilitar injeção de falhas."""
        self.enabled = True

    def disable(self) -> None:
        """Desabilitar injeção de falhas."""
        self.enabled = False

    def reset(self) -> None:
        """Resetar contadores de chamadas."""
        self.call_counts.clear()

    def check_and_increment(self, operation: str) -> None:
        """
        Incrementar contador de chamada e verificar se deve injetar falha.

        Args:
            operation: Nome da operação (ex: "aggregate_repository.save")

        Raises:
            InjectedFailureException: Se uma falha deve ser injetada
        """
        if not self.enabled:
            return

        # Incrementar contador
        current_call = self.call_counts.get(operation, 0) + 1
        self.call_counts[operation] = current_call

        # Verificar se deve falhar
        if operation in self.failure_plans:
            plan = self.failure_plans[operation]
            if plan.matches(operation, current_call):
                raise InjectedFailureException(
                    failure_type=plan.failure_type,
                    operation=operation,
                    message=plan.message,
                )

    def get_call_count(self, operation: str) -> int:
        """Obter número de chamadas para uma operação."""
        return self.call_counts.get(operation, 0)


# Instância global (apenas para testes)
_global_injector = FailureInjector()


def get_failure_injector() -> FailureInjector:
    """Obter instância global do injetor."""
    return _global_injector


def reset_failure_injector() -> None:
    """Resetar injetor (limpar planos e contadores)."""
    _global_injector.failure_plans.clear()
    _global_injector.call_counts.clear()
    _global_injector.disable()
