"""
Validation policies - 8 mandatory checks
"""

class ValidationPolicies:
    """Enforce NeoEve architecture and acceptance criteria"""

    @staticmethod
    def check_acceptance_criteria(criteria_met: int, criteria_total: int) -> bool:
        """✓ 1. All acceptance criteria must be met"""
        return criteria_met == criteria_total

    @staticmethod
    def check_tests_executed(tests_executed: int, tests_found: int) -> bool:
        """✓ 2. Tests must be executed (not just documented)"""
        return tests_executed >= tests_found and tests_found > 0

    @staticmethod
    def check_tests_passed(tests_passed: int, tests_executed: int) -> bool:
        """✓ 3. All executed tests must pass"""
        return tests_executed == 0 or tests_passed == tests_executed

    @staticmethod
    def check_no_qa_security_divergence(qa_evidence: str, security_evidence: str) -> bool:
        """✓ 4. QA and Security findings must not diverge"""
        qa_has_issues = "FAIL" in qa_evidence or "REJECT" in qa_evidence
        security_has_issues = "FAIL" in security_evidence or "REJECT" in security_evidence
        return qa_has_issues == security_has_issues

    @staticmethod
    def check_multi_tenant_isolation(implementation: str) -> bool:
        """✓ 5. Multi-tenant isolation must be preserved"""
        violations = ["cross-tenant", "tenant confusion", "isolation bypass"]
        return not any(v in implementation.lower() for v in violations)

    @staticmethod
    def check_architecture_compliance(constraints: list, evidence: str) -> bool:
        """✓ 6. Architecture contracts must be respected"""
        critical_constraints = [
            "MULTI_TENANT_ISOLATION",
            "NO_FUNCTIONAL_REMOVAL",
            "IDEMPOTENCY",
            "DETERMINISTIC_ENGINE"
        ]
        for constraint in critical_constraints:
            if constraint in constraints:
                if "violat" in evidence.lower():
                    return False
        return True

    @staticmethod
    def check_sufficient_evidence(evidence_count: int, min_required: int = 3) -> bool:
        """✓ 7. Sufficient evidence must be provided"""
        return evidence_count >= min_required

    @staticmethod
    def check_no_critical_unmitigated_risks(critical_issues: list, mitigations: list) -> bool:
        """✓ 8. No critical unmitigated risks"""
        return len(critical_issues) == 0 or len(mitigations) >= len(critical_issues)

    @staticmethod
    def apply_all_policies(validation_data: dict) -> tuple[bool, list]:
        """Apply all 8 policies and return verdict + violated rules"""

        policies = [
            ("acceptance_criteria", lambda: ValidationPolicies.check_acceptance_criteria(
                validation_data.get("acceptance_criteria_met", 0),
                validation_data.get("acceptance_criteria_total", 1)
            )),
            ("tests_executed", lambda: ValidationPolicies.check_tests_executed(
                validation_data.get("tests_executed", 0),
                validation_data.get("tests_found", 0)
            )),
            ("tests_passed", lambda: ValidationPolicies.check_tests_passed(
                validation_data.get("tests_passed", 0),
                validation_data.get("tests_executed", 0)
            )),
            ("qa_security_divergence", lambda: ValidationPolicies.check_no_qa_security_divergence(
                validation_data.get("qa_evidence", ""),
                validation_data.get("security_evidence", "")
            )),
            ("multi_tenant_isolation", lambda: ValidationPolicies.check_multi_tenant_isolation(
                validation_data.get("implementation", "")
            )),
            ("architecture_compliance", lambda: ValidationPolicies.check_architecture_compliance(
                validation_data.get("architecture_constraints", []),
                validation_data.get("implementation", "")
            )),
            ("sufficient_evidence", lambda: ValidationPolicies.check_sufficient_evidence(
                validation_data.get("evidence_count", 0)
            )),
            ("critical_risks", lambda: ValidationPolicies.check_no_critical_unmitigated_risks(
                validation_data.get("critical_issues", []),
                validation_data.get("mitigations", [])
            ))
        ]

        violated = [name for name, check in policies if not check()]
        all_pass = len(violated) == 0

        return all_pass, violated
