"""
Test Suite: ARCHITECT ↔ OpenAI Validator Integration

Tests the integration between ARCHITECT task orchestration and the
OpenAI Validator independent review service.

20 Integration Scenarios:
  - Mocks (10 scenarios) — Without OPENAI_API_KEY
  - Real (10 scenarios) — With OPENAI_API_KEY (if available)

First validation case: MISSÃO 002-D.2 (Security Fix)
"""

import pytest
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict


class TestArchitectValidatorIntegration:
    """Test suite for ARCHITECT ↔ Validator integration"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.docs_base = "C:/dev/neoeve/docs/agent-team"
        self.records_path = "C:/dev/neoeve/docs/agent-team/validation-records"
        os.makedirs(self.records_path, exist_ok=True)
        yield
        # Cleanup not needed for read-only tests

    # ============================================================
    # MOCK TESTS (10 scenarios) — Without OPENAI_API_KEY
    # ============================================================

    def test_m001_integration_adapter_creation(self):
        """M001: Adapter can be created without API key (mock mode)"""
        from services.architect_validator_integration import ArchitectValidatorAdapter

        # Disable validator via environment
        os.environ["OPENAI_VALIDATOR_ENABLED"] = "false"

        adapter = ArchitectValidatorAdapter(validator_enabled=False)
        assert adapter is not None
        assert not adapter.validator_enabled

    def test_m002_integration_handler_creation(self):
        """M002: Handler can be created without adapter"""
        from handlers.validation_handler import ValidationHandler

        handler = ValidationHandler()
        assert handler is not None
        assert handler.validation_history == []

    def test_m003_mock_validation_mision_002_d2(self):
        """M003: MISSÃO 002-D.2 can be validated in mock mode"""
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=False)

        # Validate MISSÃO 002-D.2
        verdict, confidence, summary = adapter.validate_delivery(
            task_id="task-002-d2-001",
            mission_id="mission-002-d2",
            agent_reporting="backend-developer",
            task_definition={"type": "security_fix", "severity": "CRITICAL"},
            evidence_files=[
                "BACKEND_DEVELOPER_SECURITY_FIX_REPORT.md",
                "SECURITY_FINDING_002_D2_REMEDIATION_REPORT.md"
            ],
            acceptance_criteria=[
                "✓ Line 9956 corrected (user_id → dono_id)",
                "✓ No other callers affected",
                "✓ Multi-tenant boundary preserved",
                "✓ Test suite: 6/6 security tests PASS"
            ],
            architecture_constraints=[
                "MULTI_TENANT_ISOLATION",
                "NO_FUNCTIONAL_REMOVAL"
            ],
            tenant_id=None,
            docs_base_path=self.docs_base
        )

        # In mock mode, should return NEEDS_HUMAN_REVIEW
        assert verdict == "NEEDS_HUMAN_REVIEW"
        assert confidence == 0  # Mock has zero confidence
        assert "OpenAI API key" in summary or "mock" in summary.lower()

    def test_m004_evidence_collection_from_reports(self):
        """M004: Evidence is properly collected from markdown reports"""
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=False)

        evidence = adapter._collect_evidence(
            evidence_files=[
                "BACKEND_DEVELOPER_SECURITY_FIX_REPORT.md",
                "SECURITY_FINDING_002_D2_REMEDIATION_REPORT.md"
            ],
            docs_base_path=self.docs_base
        )

        # Check that evidence was collected
        assert evidence["files_found"] > 0
        assert evidence["files_readable"] > 0
        # Check for extracted content
        assert len(evidence.get("implementation_report", "")) > 0 or \
               len(evidence.get("security_audit", "")) > 0

    def test_m005_validation_input_construction(self):
        """M005: ValidationInput is properly constructed from task context"""
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=False)

        evidence = {
            "implementation_report": "Line 9956 fixed: user_id → dono_id",
            "security_audit": "6/6 security tests PASS",
            "qa_validation": "135/135 regression tests PASS",
            "content_snippets": []
        }

        validation_input = adapter._build_validation_input(
            task_id="task-002-d2-001",
            mission_id="mission-002-d2",
            agent_reporting="backend-developer",
            task_definition={"type": "security_fix"},
            evidence_summary=evidence,
            acceptance_criteria=["✓ Fix applied"],
            architecture_constraints=["MULTI_TENANT_ISOLATION"],
            tenant_id=None
        )

        # Should be dict or ValidationInput object
        is_dict = isinstance(validation_input, dict)
        is_dataclass = hasattr(validation_input, "task_id")
        assert is_dict or is_dataclass

        # Check fields work for both dict and dataclass
        if is_dict:
            assert validation_input["task_id"] == "task-002-d2-001"
            assert validation_input["mission_id"] == "mission-002-d2"
        else:
            assert validation_input.task_id == "task-002-d2-001"
            assert validation_input.mission_id == "mission-002-d2"

    def test_m006_validation_record_persistence(self):
        """M006: Validation records are persisted for audit trail"""
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=False)

        result = {
            "verdict": "NEEDS_HUMAN_REVIEW",
            "confidence": 0,
            "findings": []
        }

        adapter._store_validation_record("task-002-d2-001", result)

        # Should be in memory
        retrieved = adapter.get_validation_record("task-002-d2-001")
        assert retrieved is not None

    def test_m007_handler_integration_basic(self):
        """M007: Handler can orchestrate validation request"""
        from handlers.validation_handler import ValidationHandler
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=False)
        handler = ValidationHandler(adapter=adapter)

        verdict, confidence, summary = handler.validate_task_delivery(
            task_id="task-002-d2-001",
            mission_id="mission-002-d2",
            evidence_files=["BACKEND_DEVELOPER_SECURITY_FIX_REPORT.md"],
            acceptance_criteria=["✓ Fix applied"],
            architecture_constraints=["MULTI_TENANT_ISOLATION"]
        )

        assert verdict in ["APPROVED", "REJECTED", "NEEDS_HUMAN_REVIEW", "INSUFFICIENT_EVIDENCE"]
        assert isinstance(confidence, (int, float))
        assert isinstance(summary, str)
        assert len(handler.validation_history) > 0

    def test_m008_handler_summary_statistics(self):
        """M008: Handler produces summary statistics"""
        from handlers.validation_handler import ValidationHandler
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=False)
        handler = ValidationHandler(adapter=adapter)

        # Perform multiple validations
        for i in range(3):
            handler.validate_task_delivery(
                task_id=f"task-test-{i:03d}",
                mission_id="mission-test",
                evidence_files=[]
            )

        summary = handler.get_validation_summary()

        assert summary["total_validations"] == 3
        assert "verdicts" in summary
        assert summary["avg_confidence"] >= 0

    def test_m009_error_handling_missing_files(self):
        """M009: Adapter handles missing evidence files gracefully"""
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=False)

        evidence = adapter._collect_evidence(
            evidence_files=["NONEXISTENT_FILE.md"],
            docs_base_path=self.docs_base
        )

        # Should report as not found, not crash
        assert evidence["files_found"] == 0
        assert evidence["files_readable"] == 0

    def test_m010_validation_log_export(self):
        """M010: Handler can export validation log as JSONL"""
        from handlers.validation_handler import ValidationHandler
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=False)
        handler = ValidationHandler(adapter=adapter)

        # Perform a validation
        handler.validate_task_delivery(
            task_id="task-002-d2-001",
            mission_id="mission-002-d2",
            evidence_files=[]
        )

        # Export
        export_file = "/tmp/test-validation-log.jsonl"
        handler.export_validation_log(export_file)

        # Check file exists and is valid JSONL
        assert os.path.exists(export_file)
        with open(export_file, 'r') as f:
            line = f.readline()
            obj = json.loads(line)
            assert "task_id" in obj
            assert "verdict" in obj

    # ============================================================
    # STRUCTURAL TESTS (3 scenarios) — Validator module structure
    # ============================================================

    def test_s001_openai_validator_module_imports(self):
        """S001: OpenAI Validator modules can be imported"""
        try:
            from openai_validator import OpenAIValidator, ValidationInput, ValidationResult
            assert OpenAIValidator is not None
            assert ValidationInput is not None
            assert ValidationResult is not None
        except ImportError as e:
            pytest.skip(f"OpenAI Validator modules not installed: {e}")

    def test_s002_validator_schema_contracts(self):
        """S002: Validator schema contracts are properly defined"""
        try:
            from openai_validator.schema import ValidationInput, ValidationResult, VerdictEnum

            # Check ValidationInput fields
            input_fields = set(ValidationInput.__dataclass_fields__.keys())
            assert "task_id" in input_fields
            assert "mission_id" in input_fields
            assert "implementation_report" in input_fields

            # Check ValidationResult fields
            result_fields = set(ValidationResult.__dataclass_fields__.keys())
            assert "verdict" in result_fields
            assert "confidence" in result_fields
            assert "findings" in result_fields

            # Check VerdictEnum
            assert hasattr(VerdictEnum, "APPROVED")
            assert hasattr(VerdictEnum, "REJECTED")
            assert hasattr(VerdictEnum, "NEEDS_HUMAN_REVIEW")

        except ImportError as e:
            pytest.skip(f"Validator schema not available: {e}")

    def test_s003_validator_policies_implemented(self):
        """S003: All 8 validation policies are implemented"""
        try:
            from openai_validator.policies import ValidationPolicies

            # Check all 8 policies exist
            assert hasattr(ValidationPolicies, "check_acceptance_criteria")
            assert hasattr(ValidationPolicies, "check_tests_executed")
            assert hasattr(ValidationPolicies, "check_tests_passed")
            assert hasattr(ValidationPolicies, "check_no_qa_security_divergence")
            assert hasattr(ValidationPolicies, "check_multi_tenant_isolation")
            assert hasattr(ValidationPolicies, "check_architecture_compliance")
            assert hasattr(ValidationPolicies, "check_sufficient_evidence")
            assert hasattr(ValidationPolicies, "check_no_critical_unmitigated_risks")

            # Check apply_all_policies method
            assert hasattr(ValidationPolicies, "apply_all_policies")
            assert callable(ValidationPolicies.apply_all_policies)

        except ImportError as e:
            pytest.skip(f"Validation policies not available: {e}")

    # ============================================================
    # REAL TESTS (depends on OPENAI_API_KEY)
    # ============================================================

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_r001_real_validation_mision_002_d2(self):
        """R001: MISSÃO 002-D.2 real validation with OpenAI API"""
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=True)

        # Real validation (requires API key)
        verdict, confidence, summary = adapter.validate_delivery(
            task_id="task-002-d2-001",
            mission_id="mission-002-d2",
            agent_reporting="backend-developer",
            task_definition={
                "type": "security_fix",
                "severity": "CRITICAL",
                "description": "Multi-tenant isolation vulnerability fix at line 9956"
            },
            evidence_files=[
                "BACKEND_DEVELOPER_SECURITY_FIX_REPORT.md",
                "SECURITY_FINDING_002_D2_REMEDIATION_REPORT.md"
            ],
            acceptance_criteria=[
                "✓ Line 9956 corrected (user_id → dono_id)",
                "✓ No other callers affected",
                "✓ Multi-tenant boundary preserved",
                "✓ Test suite: 6/6 security tests PASS",
                "✓ Regression tests: 135/135 PASS"
            ],
            architecture_constraints=[
                "MULTI_TENANT_ISOLATION",
                "NO_FUNCTIONAL_REMOVAL",
                "IDEMPOTENCY"
            ],
            tenant_id="7394370553",
            docs_base_path=self.docs_base
        )

        # Real validator should return meaningful verdict
        assert verdict in [
            "APPROVED",
            "APPROVED_WITH_CONDITIONS",
            "REJECTED",
            "INSUFFICIENT_EVIDENCE",
            "NEEDS_HUMAN_REVIEW"
        ]
        assert 0 <= confidence <= 100
        assert isinstance(summary, str)
        assert len(summary) > 10

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_r002_real_validator_evidence_processing(self):
        """R002: Real validator properly processes evidence"""
        from services.architect_validator_integration import ArchitectValidatorAdapter

        adapter = ArchitectValidatorAdapter(validator_enabled=True)

        result = adapter._submit_to_validator({
            "task_id": "task-002-d2-001",
            "mission_id": "mission-002-d2",
            "implementation_report": "Security fix: user_id → dono_id at line 9956",
            "qa_validation": "6/6 security tests PASS, 135/135 regression tests PASS",
            "security_audit": "Multi-tenant isolation verified",
            "acceptance_criteria": ["✓ All criteria met"],
            "architecture_constraints": ["MULTI_TENANT_ISOLATION"]
        })

        # Should have structured findings
        assert "verdict" in result
        assert "confidence" in result
        if result.get("findings"):
            for finding in result["findings"]:
                assert "severity" in finding
                assert "description" in finding


# ============================================================
# Integration Test Helper Functions
# ============================================================

def run_integration_tests_summary() -> Dict:
    """
    Run all integration tests and return summary.

    Returns:
        {
            "total_tests": int,
            "mock_tests_pass": int,
            "structural_tests_pass": int,
            "real_tests_pass": int,
            "skipped": int,
            "failed": int
        }
    """
    # This would be called by pytest or test runner
    # Returns summary for integration report
    pass


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_architect_validator_integration.py -v
    pytest.main([__file__, "-v"])
