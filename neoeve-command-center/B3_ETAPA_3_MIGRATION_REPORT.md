# B3 ETAPA 3 — Migration Report

**Status:** ✅ **MIGRATION CRIADA E VALIDADA**

---

## Migration Created

**Arquivo:** `migrations/versions/0003_add_heartbeat_to_tenant_agent_state.py`

```python
# Upgrade:
- ADD COLUMN last_heartbeat_at (DateTime UTC, default=NOW())
- CREATE INDEX idx_tenant_agent_state_heartbeat

# Downgrade:
- DROP INDEX
- DROP COLUMN
```

---

## Validation Checklist

✅ Adiciona campo necessário  
✅ Respeita PK (tenant_id, agent_id)  
✅ Timestamps em UTC  
✅ Índice para performance  
✅ Reversível (downgrade)  
✅ Sem breaking changes  

---

## Pronto para Aplicar (5433 isolado)

```bash
alembic upgrade head
```

