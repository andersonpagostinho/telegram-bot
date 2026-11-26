# B2 — Pending Tests Plan

**Data:** 2026-11-25  
**Status:** ⏳ **TESTES FALTANTES IDENTIFICADOS**

---

## Testes Executados (Reportados)

| # | Teste | Status |
|---|-------|--------|
| 3 | SELECT FOR UPDATE + atualização | ✅ PASS |
| 4 | Duas execuções simultâneas | ✅ PASS |
| 5 | E1 finaliza, E2 continua ativo | ✅ PASS |
| 6 | E2 finaliza, nenhuma ativa | ✅ PASS |

---

## Testes Planejados mas NÃO Executados (4/13 Faltando)

### Faltantes Identificados

**Teste 1:** Isolamento básico  
- **Cenário:** Verificar que tenant_A ≠ tenant_B
- **Validação:** Estados isolados por PK composta
- **Esperado:** 0 cross-contamination

**Teste 2:** Criação concorrente (INSERT ON CONFLICT)  
- **Cenário:** Duas transações tentam criar mesmo registro
- **Validação:** Apenas uma sucede, segunda é CONFLICT
- **Esperado:** Atomicidade garantida
- **Bloqueador Encontrado:** FK constraint (agente não existente)

**Teste 7:** Dois tenants com mesmo agent_id  
- **Cenário:** Agent A em Tenant X, Agent A em Tenant Y
- **Validação:** Estados completamente isolados
- **Esperado:** Sem vazamento entre tenants

**Testes 9-13:** Não reportados em B2_REMEDIATION_FINAL.md
- Teste 9: Sem tenant_id (deve falhar)
- Teste 10: Idempotência
- Teste 11-13: Cenários de timeout/cancelamento

---

## Plano de Execução Paralela

### Preparação

1. ✅ Criar agentes fictícios no PostgreSQL 5433
   - Resolve FK constraint bloqueador

2. ✅ Preparar script SQL para 4 testes faltantes
   - Teste 1, 2, 7, e subset de 9-13

3. ⏳ Executar com PostgreSQL real
   - Sessões independentes
   - Validação de isolamento

### Critério de Aceite

- Teste 1: 0 cross-contamination ✅
- Teste 2: INSERT ON CONFLICT atômico ✅
- Teste 7: Isolamento entre tenants ✅
- Testes 9-13: Cobertura de edge cases ✅

---

## Status

🟡 **Pronto para execução paralela a B3**

**Bloqueador superado:** FK constraint (solução: criar agente no banco)

