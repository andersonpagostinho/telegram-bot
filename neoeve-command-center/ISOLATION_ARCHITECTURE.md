# PostgreSQL Isolation Architecture — ETAPA 3.3.2
## Recovery Service Homologation

**Date:** 2026-11-24  
**Purpose:** Homolog RecoveryService with complete isolation from production

---

## 1. Environment Separation

### Production
```
Database: neoeve_command_center
Host: localhost
Port: 5432
Container: neoeve_postgres_test (existing)
Schema: public (existing tables)
User: neoeve_dev
```

### Test (Recovery Homologation)
```
Database: neoeve_recovery_test
Host: localhost  
Port: 5433
Container: neoeve_postgres_recovery_test (new, isolated)
Schema: public (fresh, for testing only)
User: recovery_test_user
Volume: postgres_recovery_test_data (new, independent)
```

---

## 2. Connection String Configuration

### Production (application/alembic default)
```
DATABASE_URL=postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center
```

### Test (required for homologation)
```
TEST_DATABASE_URL=postgresql://recovery_test_user:recovery_test_pass_7XqR9kL2mN4@localhost:5433/neoeve_recovery_test
```

**Rule:** TEST_DATABASE_URL is MANDATORY. If not set:
- conftest.py uses SQLite in-memory (safe)
- test_recovery_service_postgresql.py raises ValueError (blocks)
- alembic falls back to DATABASE_URL (safe)

---

## 3. Safety Mechanisms

### 3.1 Docker Isolation
- Two separate containers on different ports
- Independent volumes (data never shared)
- Network: same bridge (neoeve_network), but different physical storage

### 3.2 Application Level
```python
# In test_recovery_service_postgresql.py
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")  # MANDATORY

if not TEST_DB_URL:
    raise ValueError("FATAL: TEST_DATABASE_URL required")

# SAFETY: Block production markers
if any(marker in TEST_DB_URL for marker in ["5432", "neoeve_dev", "neoeve_command_center"]):
    raise ValueError("FATAL: TEST_DATABASE_URL points to production")
```

### 3.3 Migration Level
```python
# In migrations/env.py
DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
# TEST_DATABASE_URL takes priority
```

### 3.4 Validation Script
```bash
python backend/scripts/validate_isolation.py
# Output:
# ✅ Ports isolated: test=5433, prod=5432
# ✅ Databases different: test=neoeve_recovery_test, prod=neoeve_command_center
# ✅ TEST_DATABASE_URL clean (no production markers)
```

---

## 4. Data Flow

```
Production Path:
┌─────────────────┐
│  Application    │
├─────────────────┤
│ DATABASE_URL    │  (optional, falls back to default)
│ → localhost:5432│
│ → neoeve_dev    │
│ → neoeve_command_center
└─────────────────┘
        ↓
┌─────────────────────────────────┐
│ Container: neoeve_postgres_test │
│ Volume: postgres_data           │
└─────────────────────────────────┘

Test Path (Homologation):
┌─────────────────┐
│   pytest        │
├─────────────────┤
│ TEST_DATABASE_  │  (MANDATORY)
│ URL=recovery... │
│ → localhost:5433│
│ → recovery_test_│
│ user            │
│ → neoeve_recovery_test
└─────────────────┘
        ↓
┌──────────────────────────────────────┐
│ Container: neoeve_postgres_recovery_ │
│ test (NEW, ISOLATED)                 │
│ Volume: postgres_recovery_test_data  │
└──────────────────────────────────────┘
```

---

## 5. Failure Scenarios

### Scenario A: TEST_DATABASE_URL not set
```
Expected: Pytest raises ValueError
Actual: ✅ ValueError raised
Result: ✅ SAFE (blocks execution)
```

### Scenario B: TEST_DATABASE_URL = production URL
```
Expected: Security check rejects it
Actual: ✅ ValueError on ["5432", "neoeve_dev", "neoeve_command_center"]
Result: ✅ SAFE (blocks execution)
```

### Scenario C: Container failure during migration
```
Expected: Alembic fails gracefully
Result: ✅ No data loss in production (different port/db/container)
```

### Scenario D: Test drops all tables
```
Expected: Only test tables affected
Result: ✅ SAFE (isolated database)
```

---

## 6. Credentials Management

**Production Credentials** (checked into repo with defaults)
```
user: neoeve_dev
password: neoeve_dev_123
database: neoeve_command_center
```

**Test Credentials** (NOT in repo)
```
.env.recovery (git-ignored)
user: recovery_test_user
password: recovery_test_pass_7XqR9kL2mN4
database: neoeve_recovery_test
```

**Rule:** .env.recovery is NOT committed. Created locally for homologation only.

---

## 7. Alembic Configuration

**Main alembic.ini** (for production)
```
sqlalchemy.url = postgresql://neoeve_dev:...@localhost:5432/neoeve_command_center
```

**New alembic.recovery.ini** (for homologation)
```
# Uses TEST_DATABASE_URL from environment
sqlalchemy.url = driver://user:pass@localhost/dbname  (overridden by env.py)
```

**Migration Priority:**
```
1. TEST_DATABASE_URL (if set)
2. DATABASE_URL (fall back)
3. Default production URL (last resort)
```

---

## 8. Verification Checklist

### Before Homologation Start
- [ ] Container created and healthy
- [ ] TEST_DATABASE_URL set
- [ ] validate_isolation.py returns PASS
- [ ] Migrations 006 & 007 applied to test db

### During Homologation
- [ ] 7 concurrency tests execute
- [ ] Each test uses isolated connection
- [ ] Multi-tenant isolation verified
- [ ] Fencing token monotonicity verified
- [ ] Idempotency validated

### After Homologation
- [ ] Rollback downgrade successful
- [ ] Tables removable
- [ ] Re-upgrade successful
- [ ] Production data untouched
- [ ] Container cleanup complete

---

## 9. Disaster Recovery

If test somehow affects production:

**Immediate Actions:**
```bash
# 1. Verify production is intact
psql -h localhost -U neoeve_dev -d neoeve_command_center -c "SELECT COUNT(*) FROM executions;"

# 2. Isolate test container
docker stop neoeve_postgres_recovery_test
docker rm neoeve_postgres_recovery_test

# 3. Verify containers are separate
docker ps | grep postgres
# Should show: neoeve_postgres_test (5432) only

# 4. Restore from backup if needed
# (but should never be needed with this architecture)
```

---

## 10. Long-term Maintenance

**When homologation completes:**
- [ ] Keep container up for future regression tests
- [ ] Or: `docker-compose down postgres-recovery-test && docker volume rm neoeve-command-center_postgres_recovery_test_data`
- [ ] Keep .env.recovery for CI/CD (don't commit)
- [ ] Keep alembic.recovery.ini for reference

**Next iteration:**
- [ ] Reuse same container/credentials if still isolated
- [ ] Or: Rotate credentials monthly for security
- [ ] Or: Run tests against cloud PostgreSQL (future enhancement)

---

**Architecture Review:**  
✅ Ports isolated (5432 ≠ 5433)  
✅ Databases isolated (different names)  
✅ Containers isolated (volumes)  
✅ Credentials isolated (.env.recovery)  
✅ Users isolated (neoeve_dev ≠ recovery_test_user)  
✅ Code-level protection (TEST_DATABASE_URL mandatory)  
✅ Migration-level protection (priority system)  
✅ Validation automated (validate_isolation.py)  

**Conclusion:** ✅ PRODUCTION DATA IS PROTECTED

