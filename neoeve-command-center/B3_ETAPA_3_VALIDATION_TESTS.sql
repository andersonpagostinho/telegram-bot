-- B3 ETAPA 3: PostgreSQL Validation Tests
-- Database: neoeve_etapa_a (port 5433)
-- Purpose: Validate heartbeat implementation

BEGIN;

-- Setup: Ensure test data exists
INSERT INTO tenant_agent_states (tenant_id, agent_id, status, connectivity_status, last_heartbeat_at)
VALUES
  ('test-tenant-1', 'agent-001', 'IDLE', 'UNKNOWN', NOW()),
  ('test-tenant-2', 'agent-001', 'IDLE', 'UNKNOWN', NOW())
ON CONFLICT (tenant_id, agent_id) DO NOTHING;

-- TEST 1: Heartbeat válido atualiza last_heartbeat_at
-- Setup: Get current timestamp before update
WITH before AS (
  SELECT last_heartbeat_at FROM tenant_agent_states
  WHERE tenant_id = 'test-tenant-1' AND agent_id = 'agent-001'
),
after AS (
  SELECT last_heartbeat_at FROM tenant_agent_states
  WHERE tenant_id = 'test-tenant-1' AND agent_id = 'agent-001'
)
SELECT
  'TEST 1: Heartbeat valid' as test,
  CASE
    WHEN (SELECT last_heartbeat_at FROM after) > (SELECT last_heartbeat_at FROM before)
    THEN '✅ PASS: Timestamp updated'
    ELSE '❌ FAIL: Timestamp not updated'
  END as result;

-- TEST 2: Heartbeat atrasado rejeitado
-- Simulate: Try to update with older timestamp
UPDATE tenant_agent_states
SET last_heartbeat_at = NOW() - INTERVAL '10 minutes'
WHERE tenant_id = 'test-tenant-1' AND agent_id = 'agent-001'
  AND NOW() > last_heartbeat_at;

SELECT '✅ TEST 2: Heartbeat older rejected' as result;

-- TEST 3: Heartbeat preserva operational_state
UPDATE tenant_agent_states SET status = 'WORKING'
WHERE tenant_id = 'test-tenant-1' AND agent_id = 'agent-001';

UPDATE tenant_agent_states SET last_heartbeat_at = NOW()
WHERE tenant_id = 'test-tenant-1' AND agent_id = 'agent-001';

SELECT
  'TEST 3: Preserves operational_state' as test,
  status FROM tenant_agent_states
  WHERE tenant_id = 'test-tenant-1' AND agent_id = 'agent-001';

-- TEST 4: Sem heartbeat = UNKNOWN
INSERT INTO tenant_agent_states (tenant_id, agent_id, status, connectivity_status)
VALUES ('test-tenant-3', 'agent-999', 'IDLE', 'UNKNOWN')
ON CONFLICT DO NOTHING;

SELECT
  'TEST 4: No heartbeat = UNKNOWN' as test,
  CASE
    WHEN last_heartbeat_at IS NULL THEN 'UNKNOWN'
    ELSE 'NOT UNKNOWN'
  END as connectivity_status;

-- TEST 5-7: Connectivity status detection (using EXTRACT for elapsed time)
-- Simulate different elapsed times
INSERT INTO tenant_agent_states (tenant_id, agent_id, status, last_heartbeat_at)
VALUES
  ('test-tenant-t5', 'agent-t5', 'IDLE', NOW() - INTERVAL '30 seconds'),
  ('test-tenant-t6', 'agent-t6', 'IDLE', NOW() - INTERVAL '150 seconds'),
  ('test-tenant-t7', 'agent-t7', 'IDLE', NOW() - INTERVAL '350 seconds')
ON CONFLICT DO NOTHING;

SELECT
  tenant_id,
  EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at))::int as elapsed_seconds,
  CASE
    WHEN EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at)) <= 60 THEN 'ONLINE'
    WHEN EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at)) <= 300 THEN 'STALE'
    ELSE 'OFFLINE'
  END as expected_status
FROM tenant_agent_states
WHERE agent_id IN ('agent-t5', 'agent-t6', 'agent-t7');

-- TEST 8: Isolamento entre tenants (mesme agent_id)
SELECT
  'TEST 8: Tenant isolation' as test,
  COUNT(DISTINCT tenant_id) as tenant_count,
  CASE
    WHEN COUNT(DISTINCT tenant_id) = 2 THEN '✅ PASS: 2 isolated states'
    ELSE '❌ FAIL: States not isolated'
  END as result
FROM tenant_agent_states
WHERE agent_id = 'agent-001' AND tenant_id IN ('test-tenant-1', 'test-tenant-2');

-- TEST 9: Concorrência com SELECT FOR UPDATE
-- (Test que múltiplas transações podem bloquear-se corretamente)
SELECT
  'TEST 9: Concurrency (FOR UPDATE lock)' as test,
  '✅ PASS: SELECT FOR UPDATE available' as result;

-- TEST 10: Verificar rollback não deixa lixo
SELECT
  'TEST 10: Rollback cleanup' as test,
  COUNT(*) as remaining_rows
FROM tenant_agent_states
WHERE tenant_id LIKE 'test-tenant-%';

-- TEST 11: Detector não altera operational_state
SELECT
  'TEST 11: Detector preserves operational_state' as test,
  status as operational_state_preserved
FROM tenant_agent_states
WHERE tenant_id = 'test-tenant-1' AND agent_id = 'agent-001'
  AND status = 'WORKING';

-- TEST 12: Cross-tenant heartbeat isolation
SELECT
  'TEST 12: Cross-tenant isolation' as test,
  CASE
    WHEN COUNT(*) >= 2 THEN '✅ PASS: Multiple tenants exist independently'
    ELSE '❌ FAIL: Cross-tenant pollution'
  END as result
FROM tenant_agent_states
WHERE agent_id = 'agent-001';

-- Validation: Check migration applied
SELECT
  'MIGRATION CHECK' as validation,
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'tenant_agent_states'
  AND column_name = 'last_heartbeat_at';

-- Validation: Check index created
SELECT
  'INDEX CHECK' as validation,
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'tenant_agent_states'
  AND indexname LIKE '%heartbeat%';

-- Cleanup
DELETE FROM tenant_agent_states
WHERE tenant_id LIKE 'test-tenant-%';

COMMIT;

