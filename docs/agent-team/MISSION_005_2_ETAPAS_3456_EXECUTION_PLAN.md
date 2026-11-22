# MISSÃO 005.2 — ETAPAS 3-6 EXECUTION PLAN

**Checkpoint**: 393da70  
**Estado**: POC validada (4/4 testes PASS)  
**Próximas Etapas**: Governança → Agentes → Testes → Relatório

---

## ETAPA 3 — GOVERNANÇA (8 REGRAS)

### Implementação Necessária

Arquivo: `event_bus/governance.py` (NEW)

```python
class GovernanceRules:
    """Deterministic governance enforcement"""
    
    # Rule 1: No self-approval
    def validate_no_self_approval(event, target_agent):
        if event.agent_id == target_agent and event.event_type == REVIEW_REQUESTED:
            return False, "Agent cannot approve own work"
        return True, None
    
    # Rule 2: QA Independence
    def validate_qa_independence(qa_rejection, backend_event):
        if qa_rejection:
            block_all_downstream_events(backend_event.mission_id)
        return True
    
    # Rule 3: Security Blocking
    def validate_security_blocking(security_rejection):
        if security_rejection.severity == CRITICAL:
            publish(DEPLOYMENT_BLOCKED)
            return False, "Critical vulnerability found"
        return True, None
    
    # Rule 4: Release Manager Gates
    def validate_release_manager_gate(qa_approved, security_approved):
        if not (qa_approved and security_approved):
            return False, "Prerequisites not met"
        return True, None
    
    # Rule 5: Evidenced Approval
    def validate_evidenced_approval(event):
        if not event.payload.get("evidence"):
            return False, "No evidence provided"
        return True, None
    
    # Rule 6: No Auto-Approval on Failure
    def validate_no_auto_approval_on_failure(validator_result):
        if validator_result == FAILED:
            return False, "Validation failed"
        if validator_result == TIMEOUT:
            move_to_dead_letter()
            alert_human()
        return True, None
    
    # Rule 7: Audit Trail
    def validate_audit_trail(event):
        # All decisions logged in Event Bus
        log_decision(event)
        return True, None
    
    # Rule 8: Preserve Audit Chain
    def validate_audit_chain(event):
        # correlation_id + causation_id chain intact
        verify_correlation_chain(event)
        return True, None
```

### Testes de Governança

Arquivo: `tests/test_governance_rules.py` (NEW)

```python
def test_no_self_approval():
    """Backend cannot approve Backend"""

def test_qa_blocks_bad_code():
    """QA rejection blocks deployment"""

def test_security_blocks_critical():
    """Security can block critical vulnerabilities"""

def test_release_manager_requires_all_approvals():
    """Release Manager cannot deploy without QA + Security"""

def test_no_auto_approval_on_validator_timeout():
    """OpenAI timeout doesn't auto-approve"""

def test_audit_trail_complete():
    """All decisions logged to Event Bus"""

def test_correlation_chain_preserved():
    """causation_id chain intact through approvals"""
```

---

## ETAPA 4 — INTEGRAÇÃO DE 5 AGENTES

### Handlers a Criar

Arquivo: `event_bus/agent_handlers.py` (EXTEND)

```python
class DebuggerHandler:
    """Debugger Agent Handler"""
    def handle_bug_detected(event) → ROOT_CAUSE_IDENTIFIED
    def handle_investigation_task(event) → INVESTIGATION_COMPLETED

class QAEngineerHandler:
    """QA Engineer Agent Handler"""
    def handle_test_task(event) → TEST_STARTED, TEST_COMPLETED
    def handle_code_diff(event) → QA_APPROVED or QA_REJECTED

class SecurityAuditorHandler:
    """Security Auditor Agent Handler"""
    def handle_audit_task(event) → AUDIT_COMPLETED
    def handle_fix_review(event) → SECURITY_APPROVED or SECURITY_REJECTED

class ReleaseManagerHandler:
    """Release Manager Agent Handler"""
    def handle_all_approvals(event) → RELEASE_PROPOSED
    def handle_deployment_request(event) → DEPLOYMENT_AUTHORIZED or DEPLOYMENT_BLOCKED

class OpenAIValidatorHandler:
    """OpenAI Validator Agent Handler"""
    def handle_validation_request(event) → VALIDATION_COMPLETED
    # External API call, read-only, fail-safe
```

### Verificação de Invocação Real

Para cada handler, documentar:
1. Se é handler Python local
2. Se invoca Claude Code Agent (via Agent tool)
3. Se é serviço externo (OpenAI API)
4. Mecanismo de comunicação
5. Evidência de execução real

---

## ETAPA 5 — TESTES E2E

### Pipeline Completo

```
Architect publishes TASK_ASSIGNED
  ↓
Backend Handler executes → publishes CODE_COMMITTED
  ↓
QA Handler tests → publishes QA_APPROVED or QA_REJECTED
  ↓ (if approved)
Security Handler audits → publishes SECURITY_APPROVED or SECURITY_REJECTED
  ↓ (if approved)
OpenAI Validator analyzes → publishes VALIDATION_COMPLETED or VALIDATION_FAILED
  ↓ (if approved)
Release Manager reviews → publishes RELEASE_PROPOSED
  ↓
Complete correlation_id chain + causation_id links
```

### Cenários de Teste

```python
def test_e2e_happy_path():
    """All approvals granted"""

def test_e2e_qa_rejection():
    """QA rejects, blocks downstream"""

def test_e2e_security_blocks():
    """Security blocks, stops pipeline"""

def test_e2e_validator_timeout():
    """OpenAI timeout, moves to dead-letter"""

def test_e2e_concurrent_missions():
    """Multiple missions don't interfere"""

def test_e2e_isolation_by_tenant():
    """Tenant A can't see Tenant B events"""

def test_e2e_idempotent_replay():
    """Replaying event doesn't duplicate effects"""

def test_e2e_correlation_chain():
    """correlation_id traces entire flow"""
```

---

## ETAPA 6 — RELATÓRIO FINAL

### Arquivo: `docs/agent-team/MISSION_005_2_FINAL_REPORT.md`

Seções obrigatórias:

1. **Arquitetura Final**
   - Componentes
   - Fluxo de eventos
   - Isolamento

2. **Participantes Integrados**
   - Architect (implementado ✅)
   - Backend (implementado ✅)
   - Debugger (status)
   - QA Engineer (status)
   - Security Auditor (status)
   - Release Manager (status)
   - OpenAI Validator (status)

3. **Mecanismo de Invocação**
   - Handlers Python: Y/N
   - Claude Code Agents: Y/N
   - APIs Externas: Y/N
   - Evidências

4. **Governança**
   - 8 regras implementadas
   - Testes para cada regra
   - Resultados

5. **Testes E2E**
   - 7 cenários executados
   - Resultados (PASS/FAIL)
   - Logs

6. **Auditoria**
   - Security review
   - OpenAI Validator feedback (se disponível)
   - Achados críticos

7. **Limitações**
   - O que não foi possível
   - Por quê
   - Workarounds

8. **Commits**
   - Todos os commits
   - Descrição breve

9. **Recomendações**
   - Próxima missão
   - Melhorias
   - Riscos

---

## 📋 CHECKLIST DE CONCLUSÃO

- [ ] ETAPA 3: Governança implementada (8 regras)
- [ ] ETAPA 3: Testes de governança (7 testes PASS)
- [ ] ETAPA 4: 5 handlers integrados
- [ ] ETAPA 4: Mecanismo de invocação documentado
- [ ] ETAPA 5: Pipeline E2E funcionando
- [ ] ETAPA 5: 7 cenários testados
- [ ] ETAPA 5: Isolamento verificado
- [ ] ETAPA 5: Correlação completa
- [ ] ETAPA 6: Relatório final criado
- [ ] ETAPA 6: Commits consolidados
- [ ] ETAPA 6: Recomendações para STEP 3

---

## 🎯 ESTIMATIVA

| Etapa | Horas | Complexidade |
|-------|-------|--------------|
| 3 - Governança | 2-3 | MÉDIO |
| 4 - 5 Agentes | 4-6 | ALTO |
| 5 - E2E Tests | 2-4 | MÉDIO |
| 6 - Relatório | 1-2 | BAIXO |
| **TOTAL** | **9-15 horas** | - |

---

## ✅ PRÓXIMA SESSÃO

**Começar com**: ETAPA 3 (Governança)

1. Criar `event_bus/governance.py`
2. Implementar 8 regras
3. Criar `tests/test_governance_rules.py`
4. Validar testes
5. Prosseguir para ETAPA 4

**Checkpoint**: 393da70  
**Preservar**: Todos os 31 commits

---

**Status**: 🟢 **PRONTO PARA ETAPA 3**
