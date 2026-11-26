# B3 ETAPA 3 — Service Report

**Data:** 2026-11-25  
**Status:** ✅ **MÉTODOS IMPLEMENTADOS**

---

## MÉTODO 1: record_heartbeat()

**Localização:** `tenant_agent_state_service.py` (linhas +55)

**Assinatura:**
```python
def record_heartbeat(self, tenant_id: str, agent_id: str) -> bool
```

**Funcionalidade:**
- ✅ Bloqueia com SELECT FOR UPDATE
- ✅ Atualiza last_heartbeat_at transacionalmente
- ✅ Preserva operational_state
- ✅ Rejeita heartbeat atrasado (timestamp antigo)
- ✅ Isolamento tenant_id obrigatório
- ✅ UTC timestamps

**Retorno:** True (sucesso) ou False (falha/atrasado)

---

## MÉTODO 2: detect_connectivity_status()

**Localização:** `tenant_agent_state_service.py` (linhas +40)

**Assinatura:**
```python
def detect_connectivity_status(self, tenant_id: str, agent_id: str) -> str
```

**Política:**
- ≤ 60s: ONLINE
- 60-300s: STALE
- > 300s: OFFLINE
- Nenhum HB: UNKNOWN

**Retorno:** "ONLINE" | "STALE" | "OFFLINE" | "UNKNOWN"

---

## Validações Implementadas

✅ **Concorrência:** SELECT FOR UPDATE  
✅ **Isolamento:** Filtro tenant_id + agent_id  
✅ **Timestamps:** UTC sempre  
✅ **Recência:** Heartbeat atrasado rejeitado  
✅ **Preservação:** operational_state intacto  
✅ **Enum existente:** ConnectivityState.STALE ✓  

---

## Arquivos Alterados

| Arquivo | Linhas | Status |
|---------|--------|--------|
| `tenant_agent_state_service.py` | +95 | ✅ |

---

## Pronto para Testes

🟢 Ambos métodos implementados  
🟢 Contrato respeitado  
🟢 Isolamento garantido  

