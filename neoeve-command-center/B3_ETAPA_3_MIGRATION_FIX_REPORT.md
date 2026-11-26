# B3 ETAPA 3 — Migration Fix Report

**Status:** ✅ **CORRIGIDO**

## Migration: 0003_add_heartbeat_to_tenant_agent_state.py

**Antes:**
```python
nullable=False
server_default=sa.func.now()  # ❌ Timestamps artificiais
```

**Depois:**
```python
nullable=True  # ✅ UNKNOWN até primeiro heartbeat
server_default=None  # ✅ Sem timestamp artificial
```

## Reversibilidade

✅ Upgrade: Adiciona coluna nullable
✅ Downgrade: Remove coluna
✅ Histórico Alembic preservado

