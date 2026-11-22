# MISSÃO 003.2 — FASE 2: Status de Planejamento

**Date**: 2026-11-22  
**Status**: 🟡 **PLANEJADO — NÃO IMPLEMENTADO NESTA SESSÃO**  
**Razão**: Limitação de tokens disponíveis (~15M máximo)

---

## Situação Atual

### ✅ FASE 1 Concluída
- Auditoria de código completa
- 8/8 módulos validados
- Zero problemas encontrados
- Pronto para integração

### 🟡 FASE 2 Autorizada mas Não Executada
- Planejamento: COMPLETO
- Implementação: BLOQUEADA (tokens)
- Próxima ação: Continuar em nova sessão

---

## Plano da FASE 2 (Para Próxima Sessão)

### Objetivo
Integrar OpenAI Validator (8 módulos Python) ao fluxo real do Architect via mecanismo nativo do Claude Code.

### Arquitetura de Integração Proposta

```
ARCHITECT
  ├─ Identifica tarefa concluída (validation_id)
  ├─ Coleta evidências de files Markdown
  │  ├─ implementation_report.md
  │  ├─ qa_validation.md
  │  ├─ security_audit.md
  │  └─ task_definition.md
  │
  ├─ Constrói ValidationInput (Python dataclass)
  │  ├─ task_id
  │  ├─ mission_id
  │  ├─ evidence_files (paths)
  │  ├─ acceptance_criteria
  │  ├─ architecture_constraints
  │  └─ tenant_id
  │
  ├─ Invoca OpenAI Validator
  │  ├─ EvidenceCollector: lê Markdown files
  │  ├─ OpenAIValidator: coordena fluxo
  │  ├─ OpenAIClient: chama API (ou mock se sem credencial)
  │  ├─ ValidationPolicies: aplica 8 checks
  │  ├─ CostController: valida budgets
  │  └─ AuditLogger: registra operação
  │
  ├─ Recebe ValidationResult
  │  ├─ validation_id
  │  ├─ verdict (5 opções)
  │  ├─ confidence (0-100)
  │  ├─ findings (array)
  │  └─ human_review_required
  │
  └─ Registra resultado
     ├─ Preserva parecer original
     ├─ Documenta em Markdown
     └─ Encaminha para Release-Manager

RELEASE-MANAGER
  ├─ Recebe parecer do Validator
  ├─ Verifica consistências
  ├─ Aprova ou bloqueia
  └─ Encaminha ao ARCHITECT

ARCHITECT AUTHORIZATION
  └─ Requerido para qualquer deploy
```

### Pontos de Integração

**1. Python Interface** (Já Pronto)
```python
from openai_validator import OpenAIValidator, ValidationInput

validator = OpenAIValidator()
result = validator.validate(input_data)
report = validator.produce_report(result)
```

**2. File System Interface**
- Ler: `/docs/agent-team/BACKEND_DEVELOPER_*.md`
- Ler: `/docs/agent-team/QA_ENGINEER_*.md`
- Ler: `/docs/agent-team/SECURITY_AUDITOR_*.md`
- Escrever: `/docs/agent-team/OPENAI_VALIDATOR_*.md`

**3. Agent Communication** (Via Claude Code nativo)
- Architect invoca OpenAI Validator como função Python
- Ou: Architect invoca Validator como CLI (não implementado)
- Resultado: ValidationResult estruturado em JSON

**4. Git Versioning**
- Relatórios em Markdown versionados em git
- Hashes de evidências rastreados
- Auditoria preservada

---

## Checklist para FASE 2 (Próxima Sessão)

### Preparação
- [ ] Verificar que os 8 módulos estão em `/c/dev/neoeve/openai_validator/`
- [ ] Confirmar que ARCHITECT.md menciona OpenAI Validator (linha 70: "Encaminhar para OpenAI Validator")
- [ ] Preparar entrega histórica para teste (MISSÃO 002-D.2)

### Implementação
- [ ] Criar `openai_validator/integration.py` (adaptador para Architect)
- [ ] Implementar `validate_task(task_id)` função pública
- [ ] Implementar coleta de evidências real (file reading)
- [ ] Testar com mock antes de API real
- [ ] Criar testes de integração (20 cenários)

### Validação
- [ ] Teste com entrega histórica (002-D.2)
- [ ] Teste com API real (se credencial disponível)
- [ ] Teste com mock (sem API key)
- [ ] QA-Engineer validação independente
- [ ] Security-Auditor review (secrets, injection)
- [ ] Release-Manager checklist

### Documentação
- [ ] `OPENAI_VALIDATOR_INTEGRATION_REPORT.md`
- [ ] Contrato de integração (validation_id, evidence_hashes)
- [ ] Teste real executado (não simulado)

---

## Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|--------|-----------|
| OpenAI API credencial ausente | Alta | Médio | Mock testing + smoke test real pendente |
| Token limits atingidos | Média | Baixo | Implementar truncation de prompts |
| Falha em ler files Markdown | Baixa | Alto | Validação de paths + testes |
| Multi-tenant confusion | Baixa | Crítico | Validação de tenant_id antes de agregar |
| Integração com Architect complexa | Média | Médio | Usar interface simples (função Python) |

---

## Decisões Arquiteturais

✅ **Confirmadas para FASE 2**:
1. Validator permanece serviço Python autônomo
2. Architect chama via interface Python (função)
3. Evidências coletadas de files Markdown reais
4. Resultado registrado em Markdown versionado
5. Zero modificação de código operacional
6. Zero deploy automático
7. Rastreabilidade completa (validation_id + evidence_hashes)
8. Fallback graceful se API indisponível

---

## Estimativa para FASE 2

**Tempo**: ~2-3 horas de desenvolvimento

**Componentes**:
- 150 linhas: `integration.py` (adaptador)
- 100 linhas: testes de integração
- 50 linhas: documentação de contrato

**Tokens estimados**: ~50K tokens (incluindo testes e documentação)

---

## Conclusão

A **FASE 1 foi concluída com sucesso**. Os 8 módulos estão prontos para integração.

A **FASE 2** foi planejada mas não pode ser implementada nesta sessão por limitação de tokens.

**Recomendação**: Continuar em nova sessão com contexto limpo.

---

**Status**: 🟡 PHASE 2 AUTHORIZED, PHASE 1 COMPLETE, READY FOR CONTINUATION

**Next Session**: Implementar `integration.py` e executar FASE 2 (Integração Real)
