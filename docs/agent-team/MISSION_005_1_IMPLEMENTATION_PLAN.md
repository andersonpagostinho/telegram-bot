# MISSÃO 005.1 — Core Event Bus Implementation Plan

**Data Início**: 2026-11-22  
**Fase**: 1 de 3  
**Estimativa**: 35 horas  
**Status**: 🟢 **AUTHORIZED FOR IMPLEMENTATION**

---

## Escopo da FASE 1

### Arquivos a Criar

```
event_bus/
├── __init__.py                    — Package init
├── event.py                       — Event schema + validation (200 linhas)
├── event_store.py                 — SQLite persistence (300 linhas)
├── event_publisher.py             — Publishing interface (150 linhas)
├── event_consumer.py              — Consuming interface (150 linhas)
├── idempotency.py                 — Deduplication (120 linhas)
├── audit_logger.py                — JSONL audit trail (150 linhas)
├── event_bus.py                   — Facade principal (200 linhas)
└── exceptions.py                  — Tipos de erro (80 linhas)

tests/
├── test_event_schema.py           — Validação de eventos (200 linhas)
├── test_event_store.py            — Persistência SQLite (300 linhas)
├── test_idempotency.py            — Deduplicação (150 linhas)
├── test_concurrency.py            — Concorrência (200 linhas)
├── test_recovery.py               — Recuperação (150 linhas)
└── test_integration.py            — End-to-end (200 linhas)

docs/
├── EVENT_BUS_SCHEMA.md            — Especificação de eventos
└── EVENT_BUS_OPERATIONS.md        — Manual de operação
```

**Total estimado**: ~2,100 linhas de código + testes

---

## Sequência de Implementação

### STEP 1: Fundações (6h)

**Backend Developer**:
1. Criar diretório `event_bus/`
2. Implementar `exceptions.py` (tipos de erro)
3. Implementar `event.py` (schema + validação)
4. Criar testes `test_event_schema.py`

**Arquitetura**:
```python
class Event:
    event_id: str
    event_type: str
    mission_id: str
    task_id: Optional[str]
    execution_id: Optional[str]
    agent_id: str
    agent_role: str
    timestamp: datetime
    correlation_id: str
    causation_id: Optional[str]
    payload: Dict
    schema_version: str
    metadata: Dict
```

**QA Engineer**: Verifica schema completude

---

### STEP 2: Persistência (8h)

**Backend Developer**:
1. Implementar `event_store.py` (SQLite)
2. Criar tabelas: events, event_states, processing_log
3. Implementar CRUD operations
4. Implementar estado de processamento
5. Criar testes `test_event_store.py`

**Schema SQLite**:
```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    mission_id TEXT NOT NULL,
    task_id TEXT,
    execution_id TEXT,
    agent_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    causation_id TEXT,
    payload TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    state TEXT DEFAULT 'PENDING'
);

CREATE TABLE processing_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    state TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    consumer_id TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);
```

**QA Engineer**: Testa CRUD, durabilidade, transações

**Security Auditor**: Verifica SQL injection, locking

---

### STEP 3: Deduplicação (5h)

**Backend Developer**:
1. Implementar `idempotency.py`
2. Cache em memória com timeout
3. Integrar com EventStore
4. Criar testes `test_idempotency.py`

**Estratégia**:
```python
class IdempotencyManager:
    def is_duplicate(self, idempotency_key: str) -> bool
    def mark_processed(self, idempotency_key: str, result: Any) -> None
    def get_result(self, idempotency_key: str) -> Optional[Any]
```

**QA Engineer**: Testa casos edge (timeout, cache miss)

---

### STEP 4: Publisher & Consumer (7h)

**Backend Developer**:
1. Implementar `event_publisher.py`
2. Implementar `event_consumer.py`
3. Integrar com EventStore
4. Criar testes `test_publisher_consumer.py`

**Pub/Sub Pattern**:
```python
# Publisher
bus.publish(event)

# Consumer
pending_events = bus.consume_pending(mission_id, limit=10)
for event in pending_events:
    try:
        process(event)
        bus.mark_completed(event.event_id)
    except Exception as e:
        bus.mark_failed(event.event_id, str(e))
```

**QA Engineer**: Testa ordering, delivery guarantees

---

### STEP 5: Auditoria (4h)

**Backend Developer**:
1. Implementar `audit_logger.py`
2. Escrever JSONL complementar
3. Integrar com EventStore
4. Criar testes `test_audit.py`

**Formato JSONL**:
```json
{"timestamp":"2026-11-22T...","event_id":"evt-...","state":"PUBLISHED","details":{}}
{"timestamp":"2026-11-22T...","event_id":"evt-...","state":"PROCESSED","consumer":"qae-001"}
```

**Security Auditor**: Verifica integridade trilha

---

### STEP 6: Facade & Integration (5h)

**Backend Developer**:
1. Implementar `event_bus.py` (Facade)
2. Integrar todos módulos
3. Criar testes `test_integration.py` (end-to-end)

**Interface**:
```python
class EventBus:
    def publish(self, event: Event) -> str
    def consume_pending(self, mission_id: str, agent_id: str) -> List[Event]
    def mark_completed(self, event_id: str) -> None
    def mark_failed(self, event_id: str, reason: str) -> None
    def get_history(self, mission_id: str) -> List[Event]
    def recover_from_failure() -> None
```

**QA Engineer**: Testa fluxo completo

---

## Validações Independentes (Paralelo)

### QA Engineer (8h total)

1. ✅ Testa schema
2. ✅ Testa persistência
3. ✅ Testa deduplicação
4. ✅ Testa ordering
5. ✅ Testa recuperação
6. ✅ Testa integração
7. ✅ Verifica cobertura de testes
8. ✅ Relatório QA

### Security Auditor (5h total)

1. ✅ SQL injection
2. ✅ Race conditions
3. ✅ Acesso não autorizado
4. ✅ Isolamento tenant_id
5. ✅ Trilha auditoria
6. ✅ Relatório Security

### Debugger (2h disponível)

1. ✅ Análise de issues se surgir
2. ✅ Diagnóstico de falhas

### Release Manager (3h total)

1. ✅ Verifica commits
2. ✅ Documenta rollback
3. ✅ Verifica integridade
4. ✅ Preparação FASE 2

---

## Testes Obrigatórios (18 tipos)

| # | Tipo | Arquivo | Status |
|---|------|---------|--------|
| 1 | Schema validação | test_event_schema.py | ✅ |
| 2 | Schema rejeição | test_event_schema.py | ✅ |
| 3 | Persistência SQLite | test_event_store.py | ✅ |
| 4 | Leitura eventos | test_event_store.py | ✅ |
| 5 | Duplicata evita dupla | test_idempotency.py | ✅ |
| 6 | Idempotência | test_idempotency.py | ✅ |
| 7 | Concorrência leitura | test_concurrency.py | ✅ |
| 8 | Concorrência escrita | test_concurrency.py | ✅ |
| 9 | Falha durante processo | test_recovery.py | ✅ |
| 10 | Recuperação pós-falha | test_recovery.py | ✅ |
| 11 | Evento preso processing | test_recovery.py | ✅ |
| 12 | Falha JSONL | test_audit.py | ✅ |
| 13 | Correlação ID | test_integration.py | ✅ |
| 14 | Causation ID | test_integration.py | ✅ |
| 15 | Isolamento tenant | test_integration.py | ✅ |
| 16 | Transições estado | test_event_store.py | ✅ |
| 17 | Limite tentativas | test_recovery.py | ✅ |
| 18 | Histórico completo | test_integration.py | ✅ |

---

## Critérios de Aceitação

✅ Todos 18 testes PASS  
✅ Cobertura >80%  
✅ SQLite persistência funciona  
✅ JSONL auditoria funciona  
✅ Idempotência garantida  
✅ Concorrência segura  
✅ Recuperação funciona  
✅ Zero secrets em eventos  
✅ Isolamento tenant garantido  
✅ Documentação completa  
✅ Rollback documentado  

---

## Cronograma

```
Dia 1 (8h):  STEP 1 + STEP 2 (Fundações + Persistência)
Dia 2 (8h):  STEP 3 + STEP 4 (Dedup + Pub/Sub)
Dia 3 (8h):  STEP 5 + STEP 6 (Auditoria + Facade)
Dia 4 (5h):  Validações QA + Security + Debug
Dia 5 (3h):  Release Manager + Relatório Final
```

**Total**: 32h (com 3h margem de ajustes)

---

## Próxima Fase

Após FASE 1 aprovada:
- FASE 2: Integração com agentes (30h)
- FASE 3: Resiliência + Command Center prep (30h)

---

**Plano Pronto**: 2026-11-22  
**Status**: 🟢 AUTORIZADO PARA IMPLEMENTAÇÃO

