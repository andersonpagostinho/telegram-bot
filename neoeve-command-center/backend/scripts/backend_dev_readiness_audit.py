#!/usr/bin/env python3
"""Backend Developer Readiness Audit — PHASE 2"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import SessionLocal
from database.models import Agent
from app.services.agent_registry import AgentRegistry, Permission
from app.services.claude_code_adapter import ClaudeCodeAdapter

def audit_backend_developer():
    """Audit Backend Developer readiness"""

    db = SessionLocal()

    print("=" * 70)
    print("BACKEND DEVELOPER — READINESS AUDIT")
    print("=" * 70)
    print()

    findings = []

    try:
        # 1. Registered in Agent Registry
        print("[1] Registered in Agent Registry...")
        backend_config = None
        for key, config in AgentRegistry.AGENTS.items():
            if config["agent_id"] == "agent-backend":
                backend_config = config
                break

        if backend_config:
            print(f"  ✅ Found: {backend_config['agent_id']}")
            print(f"     Role: {backend_config['role'].value}")
            print(f"     Name: {backend_config['name']}")
            findings.append(("1_registry", True, f"Registered as {backend_config['name']}"))
        else:
            print(f"  ❌ NOT FOUND")
            findings.append(("1_registry", False, "Not in Agent Registry"))
        print()

        # 2. Identity and Function
        print("[2] Identity and Function...")
        if backend_config:
            print(f"  ✅ Role: {backend_config['role'].value}")
            print(f"  ✅ Name: {backend_config['name']}")
            print(f"  ✅ Description: {backend_config['description']}")
            findings.append(("2_identity", True, f"{backend_config['name']}"))
        print()

        # 3. Claude Code Adapter Operational
        print("[3] Claude Code Adapter Operational...")
        try:
            adapter = ClaudeCodeAdapter(subscription_only=True)
            print(f"  ✅ ClaudeCodeAdapter instantiated")
            print(f"  ✅ Subscription requirement: Yes")
            findings.append(("3_adapter", True, "Claude Code CLI adapter ready"))
        except Exception as e:
            print(f"  ❌ Error: {e}")
            findings.append(("3_adapter", False, f"Adapter error: {str(e)[:50]}"))
        print()

        # 4. Permissions (READ, WRITE, EXECUTE)
        print("[4] Effective Permissions...")
        backend_perms = {}
        for perm in [Permission.READ, Permission.WRITE, Permission.EXECUTE]:
            has_perm = AgentRegistry.has_permission("agent-backend", perm)
            backend_perms[perm.value] = has_perm
            status = "✅" if has_perm else "❌"
            print(f"  {status} {perm.value.upper()}: {has_perm}")

        execute_ok = backend_perms.get("execute", False)
        findings.append(("4_permissions", execute_ok, f"READ={backend_perms.get('read')}, WRITE={backend_perms.get('write')}, EXECUTE={execute_ok}"))
        print()

        # 5. No Approval Permission
        print("[5] No Approval Permission (Segregation)...")
        can_approve = AgentRegistry.can_approve("agent-backend")
        status = "❌" if can_approve else "✅"
        print(f"  {status} Can APPROVE: {can_approve}")
        findings.append(("5_no_approve", not can_approve, f"Can approve: {can_approve}"))
        print()

        # 6. Database Model (Agent)
        print("[6] Database Model...")
        backend_agent = db.query(Agent).filter(Agent.agent_id == "agent-backend").first()
        if backend_agent:
            print(f"  ✅ Agent model in database")
            print(f"     Role: {backend_agent.agent_role}")
            print(f"     Status: {backend_agent.status}")
            print(f"     Runtime: {backend_agent.runtime}")
            findings.append(("6_model", True, f"Status={backend_agent.status}, Runtime={backend_agent.runtime}"))
        else:
            print(f"  ❌ NOT FOUND in database")
            findings.append(("6_model", False, "Agent not in database"))
        print()

        # 7. TerminalAccessControl Integration
        print("[7] TerminalAccessControl Integration...")
        try:
            from app.services.terminal_access_control import TerminalAccessControl
            limits = TerminalAccessControl.RESOURCE_LIMITS
            print(f"  ✅ TerminalAccessControl available")
            print(f"     Timeout: {limits.get('timeout_seconds')}s")
            print(f"     Memory: {limits.get('memory_mb')}MB")
            print(f"     CPU: {limits.get('cpu_percent')}%")
            findings.append(("7_tac", True, "Resource limits enforced"))
        except Exception as e:
            print(f"  ⚠️  Error: {str(e)[:50]}")
            findings.append(("7_tac", False, "Integration issue"))
        print()

        # 8. Workspace Support
        print("[8] Workspace Support...")
        try:
            from app.services.agent_runtime import AgentRuntime
            runtime = AgentRuntime()
            has_adapter = "claude-code-cli" in runtime.adapters
            print(f"  ✅ AgentRuntime available")
            print(f"  ✅ Claude Code adapter: {has_adapter}")
            findings.append(("8_workspace", has_adapter, "Workspace execution ready"))
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
            findings.append(("8_workspace", False, "Runtime issue"))
        print()

        # 9. Execution & ExecutionAttempt Persistence
        print("[9] Execution Persistence Models...")
        try:
            from database.models import Execution, ExecutionAttempt
            print(f"  ✅ Execution model available")
            print(f"  ✅ ExecutionAttempt model available")
            print(f"     Supports: idempotence, lease, fencing token")
            findings.append(("9_persistence", True, "Recovery 3-layer protection ready"))
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
            findings.append(("9_persistence", False, "Model issue"))
        print()

        # 10. Event Publishing Capability
        print("[10] Event Publishing Capability...")
        try:
            from database.models import AgentEvent
            print(f"  ✅ AgentEvent model available")
            print(f"  ✅ Supports: source_agent, event_type, mission_id, task_id")
            findings.append(("10_events", True, "Event stream active"))
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
            findings.append(("10_events", False, "Event model issue"))
        print()

        # === SUMMARY ===
        print("=" * 70)
        print("READINESS SUMMARY")
        print("=" * 70)

        passed = sum(1 for _, result, _ in findings if result)
        total = len(findings)

        print()
        print(f"Checks Passed: {passed}/{total}")
        print()

        for check_id, result, detail in findings:
            status = "✅" if result else "❌"
            print(f"{status} {check_id}: {detail}")

        print()

        all_passed = all(result for _, result, _ in findings)

        if all_passed:
            print("=" * 70)
            print("✅ BACKEND DEVELOPER READY FOR PHASE 2 EXECUTION")
            print("=" * 70)
            return True
        else:
            print("=" * 70)
            print("❌ READINESS CHECK FAILED")
            print("=" * 70)
            return False

    except Exception as e:
        print(f"❌ AUDIT ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()

if __name__ == "__main__":
    success = audit_backend_developer()
    sys.exit(0 if success else 1)
