# SDD ledger — plan: ETAPA4_MIGRACAO_USOS_1_4

## Setup
- Plan: ETAPA4_PLANO_MIGRACAO.md created
- TDD skill loaded
- Workspace: .superpowers/sdd/etapa4-migracao

## Pre-Flight Scan
- Shared interfaces: Task 2 (duracao_service wrapper) → Tasks 3–6 (each migration)
- No conflicts detected; 1 dependency identified

### Task 1: Discovery [in_progress]
**Step 1: Read current state of buscar_profissional_por_nome**
- ✅ identidade_service.py:447–475 read
- Async function, takes tenant_id + nome
- Returns full ator document or None
- Uses Firestore query with type_usuario == "profissional"

**Step 2: Search for current uses**
- ✅ Found imports in scheduler/notificacoes_scheduler.py (imported but not yet used)
- ✅ Found test usage in tests/runner_p1_identidade_canal_onboarding.py
- ✅ Found existing duration lookup pattern in event_service_async.py:1315 (duracao_servico_min)

**Step 3: Understand Duration Storage**
- Professional data can have: {"duracoes": {servico → minutos}, "duracao_servicos": {...}, "duracao_por_servico": {...}}
- Fallback exists but SPEC says "no silent None→60 fallback" - return None if not found
- Pattern from duracao_servico_min in event_service_async lines 1315–1343 is reference implementation

**DISCOVERY COMPLETE**
- buscar_profissional_por_nome exists and is ready to use
- Duration lookup pattern identified in event_service_async
- Ready to create wrapper service

**BASE**: Getting current HEAD for commit reference...
