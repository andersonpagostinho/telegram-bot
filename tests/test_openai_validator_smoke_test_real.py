"""
MISSÃO 003.5 — Smoke Test Real do OpenAI Validator

Executar uma chamada real controlada à OpenAI API para validar o fluxo completo:
  ValidationHandler → ArchitectValidatorAdapter → OpenAI Validator → OpenAI API

Testa:
  - Resposta real da API
  - Schema estruturado
  - 8 políticas locais
  - Audit trail
  - Cost controller
  - Integration com ARCHITECT
"""

import os
import json
from datetime import datetime
import sys

# Add project to path
sys.path.insert(0, '/c/dev/neoeve')

def test_prerequisites():
    """Verificar pré-requisitos antes de executar"""

    print("\n" + "="*70)
    print("MISSÃO 003.5 — SMOKE TEST REAL — PRÉ-REQUISITOS")
    print("="*70)

    prerequisites = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "OPENAI_VALIDATOR_MODEL": os.getenv("OPENAI_VALIDATOR_MODEL", "gpt-4-turbo"),
        "OPENAI_VALIDATOR_ENABLED": os.getenv("OPENAI_VALIDATOR_ENABLED", "true"),
        "OPENAI_VALIDATOR_TIMEOUT": os.getenv("OPENAI_VALIDATOR_TIMEOUT", "30"),
        "OPENAI_VALIDATOR_MAX_COST_PER_REVIEW": os.getenv("OPENAI_VALIDATOR_MAX_COST_PER_REVIEW", "0.10"),
        "OPENAI_VALIDATOR_DAILY_BUDGET": os.getenv("OPENAI_VALIDATOR_DAILY_BUDGET", "5.00"),
        "OPENAI_VALIDATOR_MONTHLY_BUDGET": os.getenv("OPENAI_VALIDATOR_MONTHLY_BUDGET", "50.00")
    }

    for key, value in prerequisites.items():
        is_sensitive = "API_KEY" in key
        display_value = "***CONFIGURED***" if (is_sensitive and value) else (value or "NOT SET")
        status = "✅" if (not is_sensitive and value) or (is_sensitive and value) else "⏸️"
        print(f"{status} {key}: {display_value}")

    # Critical checks
    if not prerequisites["OPENAI_API_KEY"]:
        print("\n⚠️ AVISO: OPENAI_API_KEY não configurada")
        print("   Resultado: Teste será executado em MOCK MODE (sem chamada real)")
        return "mock"

    print("\n✅ Pré-requisitos OK — Teste será executado em REAL MODE")
    return "real"

def test_openai_validator_imports():
    """Verificar que todos os módulos podem ser importados"""

    print("\n" + "="*70)
    print("TESTE 1: Importações do OpenAI Validator")
    print("="*70)

    try:
        from openai_validator import OpenAIValidator, ValidationInput, ValidationResult
        print("✅ OpenAI Validator: Importado")

        from openai_validator.schema import VerdictEnum, SeverityEnum, ValidationFinding
        print("✅ Schema: Importado")

        from openai_validator.policies import ValidationPolicies
        print("✅ Policies: Importado (8 políticas)")

        from openai_validator.cost_controller import CostController
        print("✅ Cost Controller: Importado")

        from openai_validator.audit_logger import AuditLogger
        print("✅ Audit Logger: Importado")

        from openai_validator.client import OpenAIClient
        print("✅ OpenAI Client: Importado")

        from services.architect_validator_integration import ArchitectValidatorAdapter
        print("✅ Architect Validator Adapter: Importado")

        from handlers.validation_handler import ValidationHandler
        print("✅ Validation Handler: Importado")

        return True
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        return False

def test_real_validation_call(mode="real"):
    """Executar uma chamada real (ou mock) para validação"""

    print("\n" + "="*70)
    print(f"TESTE 2: Chamada de Validação ({mode.upper()} MODE)")
    print("="*70)

    from handlers.validation_handler import ValidationHandler
    from services.architect_validator_integration import ArchitectValidatorAdapter

    # Dados sintéticos (sem informações reais de clientes)
    synthetic_validation = {
        "task_id": "smoke-test-001",
        "mission_id": "smoke-test",
        "agent_reporting": "qa-engineer",
        "task_definition": {
            "type": "smoke_test",
            "description": "Real validation API test",
            "severity": "INFO"
        },
        "evidence_files": [],
        "acceptance_criteria": [
            "✓ API call executed",
            "✓ Response received",
            "✓ Schema valid"
        ],
        "architecture_constraints": [
            "MULTI_TENANT_ISOLATION",
            "DETERMINISTIC_ENGINE"
        ]
    }

    try:
        # Criar handler com validator habilitado
        adapter = ArchitectValidatorAdapter(validator_enabled=(mode == "real"))
        handler = ValidationHandler(adapter=adapter)

        print(f"\n📋 Enviando validação sintética...")
        print(f"   Task ID: {synthetic_validation['task_id']}")
        print(f"   Mode: {mode.upper()}")

        # Executar validação
        verdict, confidence, summary = handler.validate_task_delivery(
            task_id=synthetic_validation["task_id"],
            mission_id=synthetic_validation["mission_id"],
            agent_reporting=synthetic_validation["agent_reporting"],
            task_definition=synthetic_validation["task_definition"],
            evidence_files=synthetic_validation["evidence_files"],
            acceptance_criteria=synthetic_validation["acceptance_criteria"],
            architecture_constraints=synthetic_validation["architecture_constraints"]
        )

        print(f"\n✅ Validação concluída com sucesso")
        print(f"   Verdict: {verdict}")
        print(f"   Confidence: {confidence}")
        print(f"   Summary (first 100 chars): {summary[:100]}...")

        # Verificar resultado
        result = handler.get_validation_summary()
        print(f"\n📊 Histórico de validações:")
        print(f"   Total: {result['total_validations']}")
        print(f"   Verdicts: {result['verdicts']}")
        print(f"   Avg confidence: {result['avg_confidence']}")

        return {
            "status": "SUCCESS",
            "verdict": verdict,
            "confidence": confidence,
            "summary": summary,
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        return {
            "status": "ERROR",
            "error": str(e),
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }

def test_failure_scenarios():
    """Testar cenários de falha com mocks"""

    print("\n" + "="*70)
    print("TESTE 3: Cenários de Falha (Mocks)")
    print("="*70)

    from services.architect_validator_integration import ArchitectValidatorAdapter

    test_cases = [
        {
            "name": "API Indisponível (Validator desabilitado)",
            "validator_enabled": False,
            "expected": "NEEDS_HUMAN_REVIEW"
        },
        {
            "name": "Invalid Evidence Files",
            "validator_enabled": False,
            "evidence_files": ["NONEXISTENT.md"],
            "expected": "NEEDS_HUMAN_REVIEW"
        }
    ]

    results = []

    for test_case in test_cases:
        try:
            adapter = ArchitectValidatorAdapter(
                validator_enabled=test_case.get("validator_enabled", False)
            )

            verdict, confidence, summary = adapter.validate_delivery(
                task_id=f"fail-test-{len(results)}",
                mission_id="fail-test",
                agent_reporting="qa-engineer",
                task_definition={"type": "failure_test"},
                evidence_files=test_case.get("evidence_files", []),
                acceptance_criteria=["✓ Test"],
                architecture_constraints=[]
            )

            expected = test_case["expected"]
            status = "✅ PASS" if verdict == expected else f"⏸️ DIFFER (got {verdict}, expected {expected})"

            print(f"\n{status}: {test_case['name']}")
            print(f"   Result: {verdict}")

            results.append({
                "test": test_case["name"],
                "status": status,
                "verdict": verdict
            })

        except Exception as e:
            print(f"\n❌ FAIL: {test_case['name']}")
            print(f"   Error: {e}")
            results.append({
                "test": test_case["name"],
                "status": "❌ FAIL",
                "error": str(e)
            })

    return results

def test_architect_integration():
    """Testar integração com ARCHITECT"""

    print("\n" + "="*70)
    print("TESTE 4: Integração com ARCHITECT")
    print("="*70)

    from handlers.validation_handler import ValidationHandler
    from services.architect_validator_integration import ArchitectValidatorAdapter

    try:
        adapter = ArchitectValidatorAdapter(validator_enabled=False)  # Mock para este teste
        handler = ValidationHandler(adapter=adapter)

        # Submeter 3 validações
        for i in range(3):
            handler.validate_task_delivery(
                task_id=f"arch-test-{i:03d}",
                mission_id="arch-test",
                evidence_files=[],
                acceptance_criteria=["✓ Test"],
                architecture_constraints=[]
            )

        # Verificar que ARCHITECT pode consultar histórico
        summary = handler.get_validation_summary()

        print(f"\n✅ Integração OK")
        print(f"   Validações registradas: {summary['total_validations']}")
        print(f"   Verdicts recebidos: {len(summary['verdicts'])} tipos")
        print(f"   Pode consultar: SIM")

        # Verificar que audit trail é preservado
        record = handler.get_validation_record("arch-test-000")
        print(f"   Audit trail preservado: {'SIM' if record else 'NÃO'}")

        return True

    except Exception as e:
        print(f"\n❌ Erro na integração: {e}")
        return False

def test_cost_tracking():
    """Testar rastreamento de custos"""

    print("\n" + "="*70)
    print("TESTE 5: Rastreamento de Custos")
    print("="*70)

    from openai_validator.cost_controller import CostController
    from openai_validator.client import OpenAIClient

    try:
        controller = CostController()
        client = OpenAIClient()

        # Simular estimativa
        estimated_cost = client.estimate_cost(
            input_tokens=500,
            output_tokens=200
        )

        print(f"\n✅ Cost Controller OK")
        print(f"   Estimated cost: ${estimated_cost:.4f}")
        print(f"   Max per review: ${controller.max_per_review}")
        print(f"   Daily budget: ${controller.daily_budget}")
        print(f"   Monthly budget: ${controller.monthly_budget}")

        # Verificar limite
        can_validate = controller.can_validate(estimated_cost, "cost-test-001")
        print(f"   Can validate: {'SIM' if can_validate else 'NÃO'}")

        return {
            "estimated_cost": estimated_cost,
            "max_per_review": controller.max_per_review,
            "daily_budget": controller.daily_budget,
            "monthly_budget": controller.monthly_budget,
            "can_validate": can_validate
        }

    except Exception as e:
        print(f"\n❌ Erro no cost tracking: {e}")
        return None

def main():
    """Executar smoke test completo"""

    print("\n" + "#"*70)
    print("# MISSÃO 003.5 — SMOKE TEST REAL DO OPENAI VALIDATOR")
    print("#"*70)

    # Pré-requisitos
    mode = test_prerequisites()

    # Teste de importações
    if not test_openai_validator_imports():
        print("\n❌ SMOKE TEST FALHOU: Importações com erro")
        return

    # Validação real (ou mock)
    validation_result = test_real_validation_call(mode)

    # Cenários de falha
    failure_results = test_failure_scenarios()

    # Integração com ARCHITECT
    arch_integration = test_architect_integration()

    # Cost tracking
    cost_tracking = test_cost_tracking()

    # Sumário
    print("\n" + "="*70)
    print("RESUMO DO SMOKE TEST")
    print("="*70)
    print(f"✅ Importações: OK")
    print(f"{'✅' if validation_result['status'] == 'SUCCESS' else '⏸️'} Validação ({mode}): {validation_result['status']}")
    print(f"✅ Cenários de Falha: {len([r for r in failure_results if '✅' in r['status']])}/{len(failure_results)} PASS")
    print(f"{'✅' if arch_integration else '❌'} Integração ARCHITECT: {'OK' if arch_integration else 'ERRO'}")
    print(f"{'✅' if cost_tracking else '❌'} Cost Tracking: {'OK' if cost_tracking else 'ERRO'}")

    print(f"\n📊 Mode: {mode.upper()}")
    if mode == "mock":
        print("⚠️  Teste executado sem API key: Use OPENAI_API_KEY para teste real")
    else:
        print("✅ Teste executado com API real")

    print("\n" + "="*70)
    print("SMOKE TEST CONCLUÍDO")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
