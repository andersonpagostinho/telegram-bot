# B3 ETAPA 3 — PostgreSQL Revalidation

**Status:** ✅ **VALIDADO**

## Dados Limpados

```sql
UPDATE tenant_agent_states SET last_heartbeat_at = NULL;
```

✅ 5 registros artificiais convertidos para NULL
✅ Resultado: last_heartbeat_at IS NULL = 5 registros

## Semantic Validation

| Teste | Esperado | Resultado |
|-------|----------|-----------|
| NULL = UNKNOWN | ✅ | ✅ PASS |
| Sem artificial | ✅ | ✅ PASS |
| Isolamento | ✅ | ✅ PASS |

## Schema Status

✅ Constraint `NOT NULL` removida
✅ `nullable=True` ativo
✅ `server_default=None`

**Contrato restaurado:** Sem heartbeat real = UNKNOWN

