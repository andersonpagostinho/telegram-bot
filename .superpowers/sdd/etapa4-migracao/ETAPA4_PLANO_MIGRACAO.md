# ETAPA 4 — GO FINAL: Migração dos Usos 1–4
## Plan: buscar_profissional_por_nome com wrapper em duracao_service.py

**Spec Authority:** Pasted authorization 2026-11-11

### Global Constraints (PROTEÇÕES CRÍTICAS)
- Nenhum fallback silencioso de None para 60
- Nenhuma alteração na duração dos serviços
- Nenhuma alteração na disponibilidade
- Nenhuma alteração nos conflitos
- Nenhuma alteração nos locks
- Nenhuma alteração na criação de eventos
- Nenhuma alteração nos drafts ou sessões
- Se houver ambiguidade, não selecionar arbitrariamente outro profissional
- Cache apenas durante operação atual (nunca multi-tenant/requisições)

### Interfaces & Dependencies

**Existing Function:**
- `identidade_service.buscar_profissional_por_nome(tenant_id: str, nome: str) -> dict | None`
  - Async, Firestore-backed
  - Returns full ator document or None
  - Validates tenant_id isolation

**Helper (To Create):**
- `obter_duracao_servico_validada(prof_data: dict, nome_servico: str) -> int | None`
  - Pure function or async
  - Takes prof_data from buscar_profissional_por_nome result
  - Returns validated duration or None (no silent fallback to 60)

**New Service (To Create):**
- `duracao_service.obter_duracao_por_profissional_nome(tenant_id: str, nome_prof: str, nome_servico: str) -> int | None`
  - Wrapper combining lookup + duration extraction
  - Handles None prof_data gracefully
  - Preserves tenant isolation

### Tasks

**Task 1: Understand Current State (Discovery)**
- Read identidade_service.buscar_profissional_por_nome spec
- Search codebase for uses of this function
- Identify the 4 uses (USO 1–4) or equivalent current usage patterns
- Document current context in ledger

**Task 2: Create duracao_service.py with Wrapper**
- Implement obter_duracao_por_profissional_nome wrapper
- TDD: test for happy path, None prof, missing service, None duration
- Ensure no silent fallback to 60
- Verify tenant isolation preserved

**Task 3: Identify & Migrate USO 1 (Pre-Check)**
- Find PRE-CHECK usage
- Write failing test for migrated behavior
- Apply migration (use wrapper instead of direct calls)
- Verify all existing PRE-CHECK tests still pass

**Task 4: Identify & Migrate USO 2 (Alternativa)**
- Find Alternativa (Alternative) usage
- Write failing test
- Apply migration
- Verify tests pass

**Task 5: Identify & Migrate USO 3 (Loop com cache local)**
- Find loop-with-cache usage
- Write failing test for cache behavior during single operation
- Apply migration with local cache
- Verify cache never spans tenants/requests
- Verify single prof lookup per operation where possible

**Task 6: Identify & Migrate USO 4 (Confirmação)**
- Find Confirmation usage
- Write failing test
- Apply migration
- Verify tests pass

**Task 7: Regression Test Suite**
- Run 14 tests from ETAPA 2
- Run 7 tests from ETAPA 3
- Run individual use tests (4 + new wrapper tests)
- Run multi-service tests
- Run multi-tenant isolation tests
- Run edge cases: profissional inexistente, duração ausente
- Run fallback-allowed tests (if any)
- Run full agendamento flow tests

**Task 8: Final Verification & Report**
- All tests green
- Diffs per use documented
- Artifacts modified listed
- Isolation evidence collected
- Cache behavior validated
- No regressões
- Residual risks identified
- Checkpoint & implementation docs updated

### Review Focus (For Final Reviewer)
- Tenant isolation not broken by cache
- No silent None→60 fallbacks introduced
- All 4 uses migrated correctly
- No behavioral changes in scheduling/durations/availability

### Commit Strategy
- One commit per task (8 commits total)
- BASE: current HEAD before Task 1

