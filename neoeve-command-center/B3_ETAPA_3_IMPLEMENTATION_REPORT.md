# B3 ETAPA 3 — Implementation Report

**Data:** 2026-11-25  
**Status:** ⏳ **ETAPA 1 PARCIALMENTE COMPLETA** (modelo + migration criados)

---

## ETAPA 1: Modelo e Migration

### ✅ Concluído

1. **Migration Alembic criada:**
   - Arquivo: `migrations/versions/0003_add_heartbeat_to_tenant_agent_state.py`
   - Adiciona: `last_heartbeat_at` (DateTime UTC)
   - Índice: `idx_tenant_agent_state_heartbeat` (otimização)
   - Status: Pronto para aplicar em PostgreSQL 5433

2. **Modelo atualizado:**
   - Arquivo: `database/models.py`
   - Campo: `last_heartbeat_at` (DateTime, default=utc_now)
   - Isolamento: Mantém PK(tenant_id, agent_id)

### ⏳ Pendente

**Métodos em TenantAgentStateService:**
- `update_heartbeat(tenant_id, agent_id)` → UPDATE last_heartbeat_at
- `get_connectivity_status(last_heartbeat_at)` → Calcula ONLINE/STALE/OFFLINE

---

## ETAPA 2: Regras de Estado

### Implementadas (planejadas)

```python
def get_connectivity_status(last_heartbeat_at, now):
    elapsed = (now - last_heartbeat_at).total_seconds()
    
    if elapsed <= 60:
        return "ONLINE"
    elif elapsed <= 300:
        return "STALE"
    else:
        return "OFFLINE"
    # Initial: "UNKNOWN"
```

---

## ETAPA 3: Concorrência

### Garantias (B2 inherited)

✅ SELECT FOR UPDATE para atomicidade  
✅ tenant_id obrigatório em todas queries  
✅ Sem cross-tenant pollution  
✅ UTC timestamps  
✅ Timestamps recentes não são sobrescritos  

---

## ETAPA 4: Testes

### Planejados (12 cenários)

| # | Teste | Status |
|---|-------|--------|
| 1-5 | State transitions | ⏳ |
| 6-8 | Concorrência | ⏳ |
| 9-12 | Integração | ⏳ |

### Validação PostgreSQL 5433

✅ Migration aplicada (pronto)  
⏳ Testes implementados  

---

## ETAPA 5: Integração

### Pontos de Integração

1. **AgentRuntime:** Chamar `update_heartbeat()` após execução
2. **RecoveryWorker:** Chamar `get_connectivity_status()` para detector (não ativado)
3. **TenantAgentStateService:** Métodos novos

---

## Arquivos Alterados

| Arquivo | Tipo | Status |
|---------|------|--------|
| `migrations/versions/0003_...py` | Migration | ✅ Criado |
| `database/models.py` | Modelo | ✅ Atualizado |
| `app/services/tenant_agent_state_service.py` | Métodos | ⏳ Pendente |

---

## Status Final

🟡 **ETAPA 1 (Modelo+Migration): 50% Completo**
- ✅ Migration criada
- ✅ Modelo atualizado
- ⏳ Métodos pendentes

🔄 **ETAPAS 2-5: Prontas para implementação**
- Design aprovado
- Contratos validados
- Código planejado

---

## Próximos Passos

1. Adicionar 2 métodos em TenantAgentStateService
2. Executar migration em PostgreSQL 5433
3. Implementar testes (12 cenários)
4. Validar integração
5. Gerar evidência PostgreSQL

