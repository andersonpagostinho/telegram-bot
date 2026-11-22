# Autonomy Policy for NeoEve Multi-Tenant Agent System

**Date**: 2026-11-21  
**Configuration**: `.claude/settings.json`  
**Scope**: Project-wide agent autonomy  

---

## 1. Policy Overview

This policy enables autonomous operation of NeoEve agents (ARCHITECT, BACKEND-DEVELOPER, QA-ENGINEER, SECURITY-AUDITOR, RELEASE-MANAGER) without repetitive permission prompts for authorized operations.

**Goal**: Reduce manual approvals for normal development operations while maintaining security boundaries.

---

## 2. Automatic Operations (No Prompts)

The following operations execute automatically without permission requests:

### File & Code Search
- ✅ **Read**: Read any project file (all paths)
- ✅ **Glob**: Search files by pattern (e.g., `*.py`, `tests/**/*.js`)
- ✅ **Grep**: Search code for symbols, keywords, patterns

**Use Case**: Agents can search codebase independently to understand structure and find code sections.

### Git Operations (Safe)
- ✅ **git status**: Check repository state
- ✅ **git diff**: View changes between commits
- ✅ **git log**: Review commit history
- ✅ **git show**: Display commit details
- ✅ **git branch**: List branches

**Use Case**: Agents can audit git state, view changes, and understand branch history.

### Testing (Automated)
- ✅ **pytest**: Execute test suite (`pytest tests/...`, `pytest -v`, etc.)
- ✅ **python -m pytest**: Run tests via Python module

**Use Case**: QA-Engineer and Backend-Developer can execute tests independently.

### File Editing (Restricted Paths)
- ✅ **Edit .claude/**: Modify agent configuration and documentation
- ✅ **Edit tests/**: Create and modify test files
- ✅ **Edit docs/**: Update documentation

**Use Case**: Agents can create tests, document findings, and update agent configs.

---

## 3. Restricted Operations (Always Ask for Approval)

The following operations always require explicit user approval:

### Git Operations (Dangerous)
- ❌ **git push**: Upload commits to remote (always ask)
- ❌ **git reset**: Discard commits (always ask)
- ❌ **git rebase**: Reorder commits (always ask)
- ❌ **git merge**: Merge branches (always ask)

**Reason**: These operations can lose work or corrupt history.

### File Deletion
- ❌ **rm**: Remove files (always ask)

**Reason**: Accidental file deletion is irreversible.

### Privileged Operations
- ❌ **sudo**: Root/privileged execution (always deny)
- ❌ **rm -rf**: Recursive deletion (always deny)

**Reason**: These are destructive and require explicit authorization.

---

## 4. Explicitly Denied Operations

The following operations are **permanently denied** and cannot be overridden:

```
❌ Bash(sudo *)           — Privileged execution forbidden
❌ Bash(rm -rf *)         — Recursive deletion forbidden
❌ PowerShell(Remove-Item -Recurse -Force)  — Dangerous deletion forbidden
```

**Reason**: These create unacceptable security risks.

---

## 5. Deploy Operations (Not Automated)

**Deploy is not part of this autonomy policy.**

Deploy operations:
- Require explicit ARCHITECT authorization
- Are encapsulated separately in Release-Manager workflow
- Never auto-execute even with autonomy policy enabled

---

## 6. Configuration (Technical Details)

### File Location
`.claude/settings.json` (project-scoped)

### Permission Rules Format
```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(git status)",
      "Bash(pytest *)",
      "Edit(tests/*)",
      "Edit(docs/*)"
    ],
    "ask": [
      "Bash(git push *)",
      "Bash(rm *)"
    ],
    "deny": [
      "Bash(sudo *)",
      "Bash(rm -rf *)"
    ],
    "defaultMode": "default"
  }
}
```

### Rule Matching
- **Exact**: `"Bash(git status)"` matches only `git status`
- **Prefix**: `"Bash(pytest *)"` matches `pytest tests/...`, `pytest -v`, etc.
- **Tool only**: `"Read"` matches all read operations
- **Deny**: `"Bash(sudo *)"` blocks all sudo invocations

---

## 7. Scope: Which Agents Are Covered

| Agent | Covered Operations |
|-------|-------------------|
| **ARCHITECT** | Read, Glob, Grep, Git (safe), Design documentation |
| **BACKEND-DEVELOPER** | Edit tests, Run pytest, Git (safe), Create reports |
| **QA-ENGINEER** | Run pytest, Grep tests, Edit test files, Git (safe) |
| **SECURITY-AUDITOR** | Read code, Grep patterns, Git (safe), Write audit reports |
| **RELEASE-MANAGER** | Read policies, Grep for configs, Git (safe), Create checklists |

Each agent inherits permissions from this policy. No agent receives elevated privileges.

---

## 8. Operational Boundaries

### What Agents CAN Do Autonomously
- Search and read code
- Create and modify tests
- Run test suites
- Review git history
- Write documentation
- Create checklists and reports
- Analyze logs and output

### What Agents CANNOT Do Without Asking
- Push to git
- Delete files
- Reset commits
- Use privileged commands

### What is NEVER Allowed
- Sudo/root execution
- Recursive mass deletion
- Unauthorized deploy
- Access to production secrets

---

## 9. Special Cases

### Case 1: Backend-Developer Creates a Test File
```
✅ ALLOWED (automatic)
- Read: Understand test pattern
- Edit: Create tests/test_fix.py
- Run: pytest tests/test_fix.py
Result: No prompts
```

### Case 2: QA-Engineer Needs to Review git diff
```
✅ ALLOWED (automatic)
- Bash(git diff): Compare changes
- Bash(git log): Review history
Result: No prompts
```

### Case 3: ARCHITECT Reviews Changes Before Push
```
❌ REQUIRES APPROVAL
- Bash(git push): Blocked
Prompt: "Push to remote? Allow once / Allow always / No"
```

### Case 4: Security-Auditor Writes Audit Report
```
✅ ALLOWED (automatic)
- Edit(docs/agent-team/AUDIT_REPORT.md): Create report
Result: No prompts
```

---

## 10. Testing the Policy

### Test 1: Read File
```bash
# Automatic — no prompt expected
claude read C:\dev\neoeve\router\principal_router.py
```
**Expected**: File content returned without permission prompt.

### Test 2: Run Tests
```bash
# Automatic — no prompt expected
cd C:\dev\neoeve
pytest tests/test_*.py -v
```
**Expected**: Tests run, results shown without permission prompt.

### Test 3: Git Diff
```bash
# Automatic — no prompt expected
cd C:\dev\neoeve
git diff HEAD~1
```
**Expected**: Diff displayed without permission prompt.

### Test 4: Git Push (Should Prompt)
```bash
# SHOULD REQUIRE APPROVAL
cd C:\dev\neoeve
git push origin main
```
**Expected**: Permission prompt appears.

### Test 5: Edit Test File
```bash
# Automatic — no prompt expected
# (Backend-Developer creates test)
edit tests/test_new_feature.py
```
**Expected**: File edited without permission prompt.

---

## 11. Limitations & Caveats

### Session Scope
This policy applies to:
- ✅ Interactive Claude Code sessions
- ✅ Agents spawned from main session
- ⚠️ **NEW SESSIONS**: Policy must be loaded in settings for each new session

### Configuration Reloading
- **New Session**: Policy loads automatically from `.claude/settings.json`
- **Mid-Session Change**: Reload required via `/hooks` menu or restart

### Git Hooks Interaction
If this project has git hooks (pre-commit, etc.):
- ✅ Hooks execute automatically with allowed Bash commands
- ⚠️ Hook failures block subsequent operations
- ✅ Agents can diagnose hook failures via git output

---

## 12. Summary Table

| Operation | Auto | Ask | Deny |
|-----------|------|-----|------|
| Read files | ✅ | — | — |
| Glob search | ✅ | — | — |
| Grep search | ✅ | — | — |
| git status | ✅ | — | — |
| git diff | ✅ | — | — |
| git log | ✅ | — | — |
| pytest | ✅ | — | — |
| Edit tests/* | ✅ | — | — |
| Edit docs/* | ✅ | — | — |
| git push | — | ✅ | — |
| git reset | — | ✅ | — |
| rm | — | ✅ | — |
| sudo | — | — | ❌ |
| rm -rf | — | — | ❌ |

---

**Policy Status**: 🟢 **ACTIVE**

**Last Updated**: 2026-11-21 23:55 UTC

**Applies To**: NeoEve multi-tenant agent system (ARCHITECT through RELEASE-MANAGER)

---

For configuration changes, see: `.claude/settings.json` (permissions section)
