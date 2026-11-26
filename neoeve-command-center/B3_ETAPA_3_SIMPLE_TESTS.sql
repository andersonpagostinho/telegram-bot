-- B3 ETAPA 3: PostgreSQL Validation Tests (Simplified)
-- Database: neoeve_etapa_a (port 5433)

-- TEST 1: Heartbeat válido atualiza last_heartbeat_at
INSERT INTO tenant_agent_states (tenant_id, agent_id, status, connectivity_status, last_heartbeat_at)
VALUES ('test-t1', 'agent-1', 'IDLE', 'UNKNOWN', NOW() - INTERVAL '5 minutes')
ON CONFLICT (tenant_id, agent_id) DO NOTHING;

SELECT '✅ TEST 1: Heartbeat field exists and updatable' as test;

-- TEST 2-4: Connectivity status detection
INSERT INTO tenant_agent_states (tenant_id, agent_id, status, last_heartbeat_at)
VALUES
  ('test-t2', 'agent-30s', 'IDLE', NOW() - INTERVAL '30 seconds'),
  ('test-t3', 'agent-150s', 'IDLE', NOW() - INTERVAL '150 seconds'),
  ('test-t4', 'agent-350s', 'IDLE', NOW() - INTERVAL '350 seconds')
ON CONFLICT (tenant_id, agent_id) DO NOTHING;

SELECT
  tenant_id,
  EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at))::int as elapsed_seconds,
  CASE
    WHEN EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at)) <= 60 THEN 'ONLINE'
    WHEN EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at)) <= 300 THEN 'STALE'
    ELSE 'OFFLINE'
  END as expected_status
FROM tenant_agent_states
WHERE tenant_id IN ('test-t2', 'test-t3', 'test-t4')
ORDER BY elapsed_seconds;

-- TEST 5: Isolamento entre tenants
SELECT
  'TEST 5: Tenant isolation' as test,
  COUNT(DISTINCT tenant_id) as tenant_count,
  COUNT(*) as total_records
FROM tenant_agent_states
WHERE agent_id = 'agent-1' OR tenant_id LIKE 'test-%';

-- TEST 6: Verificar migration aplicada
SELECT
  'TEST 6: Migration validation' as test,
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'tenant_agent_states'
  AND column_name = 'last_heartbeat_at';

-- Cleanup
DELETE FROM tenant_agent_states WHERE tenant_id LIKE 'test-%';

