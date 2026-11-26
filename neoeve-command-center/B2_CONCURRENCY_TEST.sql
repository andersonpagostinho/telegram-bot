-- B2 CONCURRENCY TESTS — PostgreSQL 5433
-- Testes 1-10+ com isolamento e transações

\set ON_ERROR_STOP on

-- Setup: Limpeza
DELETE FROM tenant_agent_states WHERE tenant_id IN ('test_A', 'test_B', 'test_C');
DELETE FROM executions WHERE tenant_id IN ('test_A', 'test_B', 'test_C');
DELETE FROM tenants WHERE tenant_id IN ('test_A', 'test_B', 'test_C');

-- Dados de teste
INSERT INTO tenants (tenant_id, name, is_active, created_at, updated_at)
VALUES ('test_A', 'Test Tenant A', true, NOW(), NOW()),
       ('test_B', 'Test Tenant B', true, NOW(), NOW()),
       ('test_C', 'Test Tenant C', true, NOW(), NOW());

INSERT INTO agents (agent_id, agent_role, runtime, status, connectivity_status)
VALUES ('agent-test', 'architect', 'claude-code-cli', 'IDLE', 'UNKNOWN')
ON CONFLICT (agent_id) DO NOTHING;

-- TEST 1: Isolamento básico
\echo '=== TEST 1: Isolamento básico ==='
INSERT INTO tenant_agent_states (tenant_id, agent_id, status, connectivity_status, subscription_status, executor_status, created_at, updated_at)
VALUES ('test_A', 'agent-test', 'WORKING', 'ONLINE', 'VALID', 'AVAILABLE', NOW(), NOW()),
       ('test_B', 'agent-test', 'IDLE', 'OFFLINE', 'VALID', 'AVAILABLE', NOW(), NOW());

SELECT tenant_id, agent_id, status FROM tenant_agent_states
WHERE agent_id='agent-test' ORDER BY tenant_id;

-- TEST 2: Atualização isolada (A não afeta B)
\echo '=== TEST 2: Atualização isolada ==='
UPDATE tenant_agent_states
SET status='ERROR', updated_at=NOW()
WHERE tenant_id='test_A' AND agent_id='agent-test';

SELECT tenant_id, status FROM tenant_agent_states
WHERE agent_id='agent-test' ORDER BY tenant_id;

-- TEST 3: SELECT FOR UPDATE (simular lock)
\echo '=== TEST 3: SELECT FOR UPDATE lock ==='
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
  SELECT * FROM tenant_agent_states
  WHERE tenant_id='test_A' AND agent_id='agent-test'
  FOR UPDATE;
  -- Lock adquirido — atualizar
  UPDATE tenant_agent_states SET status='BLOCKED'
  WHERE tenant_id='test_A' AND agent_id='agent-test';
COMMIT;

SELECT status FROM tenant_agent_states
WHERE tenant_id='test_A' AND agent_id='agent-test';

-- TEST 4: Isolamento entre tenants (C independente)
\echo '=== TEST 4: Isolamento C ==='
INSERT INTO tenant_agent_states (tenant_id, agent_id, status, connectivity_status, subscription_status, executor_status, created_at, updated_at)
VALUES ('test_C', 'agent-test', 'IDLE', 'STALE', 'VALID', 'AVAILABLE', NOW(), NOW());

SELECT tenant_id, status, connectivity_status FROM tenant_agent_states
WHERE agent_id='agent-test' ORDER BY tenant_id;

-- TEST 5: Falha em A, B e C intactos
\echo '=== TEST 5: Falha localizada ==='
BEGIN TRANSACTION;
  UPDATE tenant_agent_states SET status='ERROR', updated_at=NOW()
  WHERE tenant_id='test_A' AND agent_id='agent-test';
  -- Simular erro: ROLLBACK
  ROLLBACK;
END;

SELECT tenant_id, status FROM tenant_agent_states
WHERE agent_id='agent-test' ORDER BY tenant_id;

-- TEST 6: Execuções ativas (simulação)
\echo '=== TEST 6: Execuções ativas ==='
INSERT INTO executions
(execution_id, mission_id, agent_id, tenant_id, project_id, runtime, status, queued_at)
VALUES
  ('exec_1', 'mission_1', 'agent-test', 'test_A', 'proj_1', 'claude', 'RUNNING', NOW()),
  ('exec_2', 'mission_2', 'agent-test', 'test_A', 'proj_1', 'claude', 'RUNNING', NOW()),
  ('exec_3', 'mission_3', 'agent-test', 'test_B', 'proj_1', 'claude', 'COMPLETED', NOW());

SELECT COUNT(*) as active_in_A
FROM executions
WHERE tenant_id='test_A' AND agent_id='agent-test' AND status IN ('RUNNING', 'RESERVED');

-- TEST 7: Finalizar exec_1, manter exec_2 ativo
\echo '=== TEST 7: Finalizar execução (outra ativa) ==='
UPDATE executions SET status='COMPLETED' WHERE execution_id='exec_1';

SELECT COUNT(*) as remaining_active
FROM executions
WHERE tenant_id='test_A' AND agent_id='agent-test' AND status IN ('RUNNING', 'RESERVED');

-- TEST 8: Finalizar exc_2, colocar em IDLE
\echo '=== TEST 8: Última execução finaliza ==='
UPDATE executions SET status='COMPLETED' WHERE execution_id='exec_2';

-- Agent deve ir para IDLE (nenhuma ativa)
SELECT COUNT(*) as active_count
FROM executions
WHERE tenant_id='test_A' AND agent_id='agent-test' AND status IN ('RUNNING', 'RESERVED');

UPDATE tenant_agent_states
SET status='IDLE', updated_at=NOW()
WHERE tenant_id='test_A' AND agent_id='agent-test' AND (
  SELECT COUNT(*) = 0 FROM executions
  WHERE tenant_id='test_A' AND agent_id='agent-test' AND status IN ('RUNNING', 'RESERVED')
);

SELECT tenant_id, status FROM tenant_agent_states
WHERE tenant_id IN ('test_A', 'test_B') AND agent_id='agent-test' ORDER BY tenant_id;

-- TEST 9: Sem tenant_id (deve retornar vazio ou erro controlado)
\echo '=== TEST 9: Query sem tenant_id (perigosa) ==='
SELECT tenant_id, status FROM tenant_agent_states
WHERE agent_id='agent-test' AND status='IDLE' ORDER BY tenant_id;
-- Resultado: 2 linhas (B e A, ambas podem estar em IDLE)

-- TEST 10: Isolamento PK (duplicata rejeitada)
\echo '=== TEST 10: Duplicata PK ==='
-- Esta query deve falhar (violação de constraint)
INSERT INTO tenant_agent_states (tenant_id, agent_id, status, connectivity_status, subscription_status, executor_status, created_at, updated_at)
VALUES ('test_A', 'agent-test', 'IDLE', 'UNKNOWN', 'VALID', 'AVAILABLE', NOW(), NOW());
-- Esperado: ERROR - duplicate key

-- Limpeza
DELETE FROM executions WHERE tenant_id IN ('test_A', 'test_B', 'test_C');
DELETE FROM tenant_agent_states WHERE tenant_id IN ('test_A', 'test_B', 'test_C');
DELETE FROM tenants WHERE tenant_id IN ('test_A', 'test_B', 'test_C');

\echo '=== TESTES COMPLETOS ==='
