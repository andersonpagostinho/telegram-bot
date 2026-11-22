"""Governance Rules Tests — Validates deterministic rule enforcement"""

import pytest
import tempfile
import os

from event_bus.event_bus import EventBus
from event_bus.governance import GovernanceEngine, GovernanceViolation
from event_bus.event import Event, EventType


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path


@pytest.fixture
def engine(temp_db):
    """Create GovernanceEngine for testing"""
    bus = EventBus(temp_db, use_wal=False)
    return GovernanceEngine(bus), bus


def test_rule_1_no_self_approval(engine):
    """Rule 1: No agent can approve its own work"""
    governance, bus = engine

    # Backend tries to approve Backend's own work
    event = Event(
        event_type=EventType.REVIEW_APPROVED,
        mission_id="test",
        agent_id="backend",  # Backend is publishing
        agent_role="backend",
        correlation_id="test-1",
        payload={"evidence": "test passed"}
    )

    result = governance.evaluate(event, target_agent="backend", action="approve_or_reject")

    assert not result.allowed, "Backend should not be able to approve own work"
    assert "cannot approve own work" in result.reason
    print("✅ RULE 1 PASS: Self-approval blocked")


def test_rule_2_qa_independence(engine):
    """Rule 2: QA independence is required"""
    governance, bus = engine

    # QA receives code from Backend
    event = Event(
        event_type=EventType.TASK_COMPLETED,
        mission_id="test",
        agent_id="backend",
        agent_role="backend",
        correlation_id="test-2",
        payload={"code_diff": "some code"}
    )

    result = governance.evaluate(event, target_agent="qa", action="execute_tests")

    assert result.allowed, "QA should be allowed to test Backend's code"
    print("✅ RULE 2 PASS: QA can test independently")


def test_rule_3_security_veto(engine):
    """Rule 3: Security can block"""
    governance, bus = engine

    # Event marked as rejected by Security
    event = Event(
        event_type=EventType.REVIEW_APPROVED,
        mission_id="test",
        agent_id="architect",
        agent_role="architect",
        correlation_id="test-3",
        payload={"security_rejected": True, "evidence": "security found issue"}
    )

    result = governance.evaluate(event, target_agent="release", action="verify_readiness")

    assert not result.allowed, "Release should be blocked if Security rejected"
    assert "Security Auditor blocked" in result.reason
    print("✅ RULE 3 PASS: Security veto enforced")


def test_rule_4_release_authorization_gate(engine):
    """Rule 4: Release needs all approvals"""
    governance, bus = engine

    # Event without QA approval
    event = Event(
        event_type=EventType.DEPLOYMENT_REQUESTED,
        mission_id="test",
        agent_id="architect",
        agent_role="architect",
        correlation_id="test-4",
        payload={"qa_approved": False, "security_approved": True}  # QA missing
    )

    result = governance.evaluate(event, target_agent="release", action="verify_readiness")

    assert not result.allowed, "Release should require all approvals"
    assert "Missing required approvals" in result.reason
    print("✅ RULE 4 PASS: Release gate enforced")


def test_rule_5_evidence_required(engine):
    """Rule 5: Approvals need evidence"""
    governance, bus = engine

    # Approval without evidence
    event = Event(
        event_type=EventType.REVIEW_APPROVED,
        mission_id="test",
        agent_id="qa",
        agent_role="qa",
        correlation_id="test-5",
        payload={}  # No evidence
    )

    result = governance.evaluate(event, target_agent="qa", action="approve_or_reject")

    assert not result.allowed, "Approval without evidence should be rejected"
    assert "requires evidence" in result.reason
    print("✅ RULE 5 PASS: Evidence required")


def test_rule_6_fail_closed_on_validator_failure(engine):
    """Rule 6: Validator failure means no approval"""
    governance, bus = engine

    # Event with validator failure
    event = Event(
        event_type=EventType.REVIEW_APPROVED,
        mission_id="test",
        agent_id="validator",
        agent_role="validator",
        correlation_id="test-6",
        payload={"validator_failed": True}
    )

    result = governance.evaluate(event, target_agent="release", action="propose_release")

    assert not result.allowed, "Validator failure should block approval"
    assert "failed" in result.reason or "timeout" in result.reason
    print("✅ RULE 6 PASS: Fail-closed on validator failure")


def test_rule_7_permission_enforcement(engine):
    """Rule 7: Agents only execute authorized actions"""
    governance, bus = engine

    event = Event(
        event_type=EventType.TASK_ASSIGNED,
        mission_id="test",
        agent_id="architect",
        agent_role="architect",
        correlation_id="test-7",
        payload={}
    )

    # Backend trying to publish_task (unauthorized)
    result = governance.evaluate(event, target_agent="backend", action="publish_task")

    assert not result.allowed, "Backend not authorized for publish_task"
    assert "not authorized" in result.reason
    print("✅ RULE 7 PASS: Permission enforcement works")


def test_rule_8_audit_trail(engine):
    """Rule 8: Audit trail recorded"""
    governance, bus = engine

    event = Event(
        event_type=EventType.TASK_ASSIGNED,
        mission_id="test",
        agent_id="architect",
        agent_role="architect",
        correlation_id="test-8",
        payload={}
    )

    # This action should be allowed
    result = governance.evaluate(event, target_agent="backend", action="execute_task")

    assert result.allowed, "Backend should be authorized to execute tasks"
    assert len(governance.audit_log) > 0, "Audit log should record decision"

    last_entry = governance.audit_log[-1]
    assert last_entry["allowed"] == True
    assert last_entry["target_agent"] == "backend"

    print("✅ RULE 8 PASS: Audit trail recorded")


def test_all_rules_consolidated(engine):
    """Test full governance pipeline"""
    governance, bus = engine

    # Valid Backend execution
    event = Event(
        event_type=EventType.TASK_ASSIGNED,
        mission_id="test",
        agent_id="architect",
        agent_role="architect",
        correlation_id="full-test",
        payload={}
    )

    result = governance.evaluate(event, target_agent="backend", action="execute_task")
    assert result.allowed, "Valid execution should pass"

    print("✅ ALL RULES PASS: Governance engine working")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        bus = EventBus(db, use_wal=False)
        gov = GovernanceEngine(bus)
        engine_tuple = (gov, bus)

        print("\n🧪 Running Governance Tests...\n")

        test_rule_1_no_self_approval(engine_tuple)
        test_rule_2_qa_independence(engine_tuple)
        test_rule_3_security_veto(engine_tuple)
        test_rule_4_release_authorization_gate(engine_tuple)
        test_rule_5_evidence_required(engine_tuple)
        test_rule_6_fail_closed_on_validator_failure(engine_tuple)
        test_rule_7_permission_enforcement(engine_tuple)
        test_rule_8_audit_trail(engine_tuple)
        test_all_rules_consolidated(engine_tuple)

        print("\n✅ All governance tests passed!")
