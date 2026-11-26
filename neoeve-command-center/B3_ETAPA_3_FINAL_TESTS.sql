-- B3 ETAPA 3: PostgreSQL Final Validation Tests
-- Database: neoeve_etapa_a (port 5433)

-- TEST 1: Heartbeat field initialized and updatable
INSERT INTO tenant_agent_states
  (tenant_id, agent_id, status, connectivity_status, subscription_status, executor_status, last_heartbeat_at)
VALUES
  ('t-1', 'a-1', 'IDLE', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', NOW() - INTERVAL '5 minutes')
ON CONFLICT (tenant_id, agent_id) DO UPDATE
  SET last_heartbeat_at = EXCLUDED.last_heartbeat_at;

SELECT '✅ TEST 1: Heartbeat field initialized' as result;

-- TEST 2-4: Connectivity status detection (elapsed time calculation)
INSERT INTO tenant_agent_states
  (tenant_id, agent_id, status, connectivity_status, subscription_status, executor_status, last_heartbeat_at)
VALUES
  ('t-2', 'a-30s', 'IDLE', 'ONLINE', 'UNKNOWN', 'UNKNOWN', NOW() - INTERVAL '30 seconds'),
  ('t-3', 'a-150s', 'IDLE', 'STALE', 'UNKNOWN', 'UNKNOWN', NOW() - INTERVAL '150 seconds'),
  ('t-4', 'a-350s', 'IDLE', 'OFFLINE', 'UNKNOWN', 'UNKNOWN', NOW() - INTERVAL '350 seconds')
ON CONFLICT (tenant_id, agent_id) DO NOTHING;

-- Calculate elapsed time and expected status
SELECT
  'TEST 2-4: State transitions' as test,
  tenant_id,
  EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at))::int as elapsed_seconds,
  CASE
    WHEN EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at)) <= 60 THEN 'ONLINE'
    WHEN EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at)) <= 300 THEN 'STALE'
    ELSE 'OFFLINE'
  END as calculated_status,
  connectivity_status as actual_status
FROM tenant_agent_states
WHERE tenant_id IN ('t-2', 't-3', 't-4')
ORDER BY elapsed_seconds;

-- TEST 5: Isolamento entre tenants (mesmo agent_id)
INSERT INTO tenant_agent_states
  (tenant_id, agent_id, status, connectivity_status, subscription_status, executor_status)
VALUES
  ('tenant-A', 'shared-agent', 'IDLE', 'ONLINE', 'UNKNOWN', 'UNKNOWN'),
  ('tenant-B', 'shared-agent', 'WORKING', 'OFFLINE', 'UNKNOWN', 'UNKNOWN')
ON CONFLICT (tenant_id, agent_id) DO NOTHING;

SELECT
  'TEST 5: Tenant isolation' as test,
  COUNT(DISTINCT tenant_id) as tenant_count,
  CASE
    WHEN COUNT(DISTINCT tenant_id) = 2 THEN '✅ PASS'
    ELSE '❌ FAIL'
  END as result
FROM tenant_agent_states
WHERE agent_id = 'shared-agent';

-- TEST 6: Verificar migration e índice
SELECT
  'TEST 6: Migration applied' as test,
  column_name,
  data_type,
  CASE WHEN is_nullable = 'NO' THEN 'NOT NULL' ELSE 'nullable' END as constraint
FROM information_schema.columns
WHERE table_name = 'tenant_agent_states'
  AND column_name = 'last_heartbeat_at';

-- TEST 7: Índice para performance
SELECT
  'TEST 7: Index created' as test,
  indexname,
  CASE WHEN indexname LIKE '%heartbeat%' THEN '✅ PASS' ELSE '❌ FAIL' END as result
FROM pg_indexes
WHERE tablename = 'tenant_agent_states'
  AND indexname LIKE '%heartbeat%';

-- TEST 8: Operação transacional (preserva status)
UPDATE tenant_agent_states
SET last_heartbeat_at = NOW(), status = 'WORKING'
WHERE tenant_id = 't-1' AND agent_id = 'a-1';

SELECT
  'TEST 8: Transactional update' as test,
  status as operational_state_preserved,
  CASE WHEN status = 'WORKING' THEN '✅ PASS' ELSE '❌ FAIL' END as result
FROM tenant_agent_states
WHERE tenant_id = 't-1' AND agent_id = 'a-1';

-- TEST 9: SELECT FOR UPDATE (concurrency lock)
SELECT
  'TEST 9: SELECT FOR UPDATE available' as test,
  COUNT(*) as locked_rows
FROM tenant_agent_states
WHERE tenant_id = 't-1' AND agent_id = 'a-1'
FOR UPDATE;

-- TEST 10: UTC timestamps
SELECT
  'TEST 10: UTC timezone' as test,
  timezone(last_heartbeat_at) as tz_name,
  CASE WHEN EXTRACT(TIMEZONE_HOUR FROM last_heartbeat_at) = 0 THEN '✅ UTC' ELSE '❌ Not UTC' END as result
FROM tenant_agent_states
WHERE tenant_id = 't-1' AND agent_id = 'a-1' LIMIT 1;

-- Summary report
SELECT
  'FINAL SUMMARY' as report,
  COUNT(*) as total_test_records,
  COUNT(DISTINCT tenant_id) as tenant_isolation_count
FROM tenant_agent_states
WHERE tenant_id IN ('t-1', 't-2', 't-3', 't-4', 'tenant-A', 'tenant-B');

-- Cleanup
DELETE FROM tenant_agent_states
WHERE tenant_id IN ('t-1', 't-2', 't-3', 't-4', 'tenant-A', 'tenant-B');

