# B3 ETAPA 3 — Final Semantic Audit

**Data:** 2026-11-25  
**Status:** 🔴 **VIOLAÇÃO DO CONTRATO DETECTADA**

---

## Achado Crítico

### Migration File Analysis

**File:** `migrations/versions/0003_add_heartbeat_to_tenant_agent_state.py`

**Linha 23-24 (PROBLEMA):**
```python
nullable=False,
server_default=sa.func.now(),
```

---

## 🔴 Violação do Contrato

### Contrato Esperado (B3 DESIGN)
```
Sem heartbeat real = UNKNOWN
Heartbeat real ≤ 60s = ONLINE
Heartbeat real 60-300s = STALE
Heartbeat real > 300s = OFFLINE
```

### Realidade (Implementação Atual)

**Registros preexistentes após migration:**

| Record | Heartbeat Real | Timestamp Artificial | Age | Status |
|--------|----------------|----------------------|-----|--------|
| tenant_B/architect | ❌ NUNCA | 2026-11-25 00:25:39 | ~117s | STALE |
| tenant_A/architect | ❌ NUNCA | 2026-11-25 00:25:39 | ~117s | STALE |
| test_A/agent | ❌ NUNCA | 2026-11-25 00:25:39 | ~1-2min | ONLINE/STALE |

**Interpretação:** Agentes que **NUNCA tiveram heartbeat real** recebem timestamp artificial via `DEFAULT now()` durante migration.

**Resultado:** ✅ parecem estar vivos quando na verdade nunca enviaram heartbeat.

---

## Raiz do Problema

### Migration Design Error

```python
op.add_column(
    'tenant_agent_states',
    sa.Column(
        'last_heartbeat_at',
        sa.DateTime(timezone=True),
        nullable=False,           # ← PROBLEMA 1
        server_default=sa.func.now(),  # ← PROBLEMA 2
        comment='...'
    )
)
```

**Por que é um problema:**

1. `nullable=False` força que coluna sempre tenha valor
2. `server_default=sa.func.now()` atribui NOW() aos registros antigos
3. Registros que NUNCA tiveram heartbeat recebem timestamp artificial
4. Método `detect_connectivity_status()` calcula age baseado no timestamp artificial
5. Resultado: Status baseado em ficção, não em heartbeat real

---

## Contrato Violado

### O que deveria acontecer:
```python
# Agente sem heartbeat real
last_heartbeat_at = None
connectivity_status = detect_connectivity_status(None)
# Resultado: UNKNOWN
```

### O que está acontecendo:
```python
# Agente sem heartbeat real, mas DEFAULT now() na migration
last_heartbeat_at = 2026-11-25 00:25:39  # ← Artificial
age = NOW() - 2026-11-25 00:25:39
connectivity_status = "STALE" or "ONLINE" (baseado em ficção)
# Resultado: STALE ou ONLINE (errado!)
```

---

## Impacto

### Curto Prazo (Agora)
- Registros antigos parecem STALE/ONLINE sem heartbeat real
- `detect_connectivity_status()` retorna status baseado em timestamp artificial
- AgentRuntime será enganado por "heartbeat" que nunca existiu

### Longo Prazo
- Integração com RecoveryService (ETAPA 4) verá agentes vivos quando estão inativos
- Decisões de retry/abandon baseadas em ficção
- Monitoramento de disponibilidade inacurado

---

## Solução Proposta

### Opção A: Fazer last_heartbeat_at Nullable (RECOMENDADO)

**Migration Corrigida:**
```python
op.add_column(
    'tenant_agent_states',
    sa.Column(
        'last_heartbeat_at',
        sa.DateTime(timezone=True),
        nullable=True,  # ← PERMITIR NULL
        server_default=None,  # ← SEM DEFAULT ARTIFICIAL
        comment='Timestamp of last heartbeat from agent (UTC, NULL until first heartbeat)'
    )
)
```

**Semântica Corrigida:**
- Registros antigos: `last_heartbeat_at = NULL`
- `detect_connectivity_status(None)` retorna `UNKNOWN`
- Apenas após `record_heartbeat()` ser chamado realmente → timestamp válido

**Vantagem:** Respeita contrato completamente
**Risco:** Nenhum (NULL é semanticamente correto)

### Opção B: Manter NOT NULL + server_default

**Consequência:**
- Continuar enganando sistema sobre disponibilidade
- Registros parecem vivos quando nunca tiveram heartbeat
- Contrato violado permanentemente

---

## Métodos Afetados

### record_heartbeat()
✅ Implementação correta (atualiza timestamp real)
❌ Mas começa com timestamp artificial do DEFAULT

### detect_connectivity_status()
✅ Lógica correta (calcula ONLINE/STALE/OFFLINE)
❌ Mas recebe timestamp artificial como entrada
❌ Nunca retorna UNKNOWN (porque last_heartbeat_at nunca é NULL)

---

## Checklist Semântico

| Aspecto | Esperado | Atual | Status |
|---------|----------|-------|--------|
| Sem heartbeat = UNKNOWN | Sim | Não (artificial) | 🔴 FAIL |
| Heartbeat real ≤ 60s = ONLINE | Sim | Sim (after real HB) | 🟡 PARTIAL |
| Isolamento tenant | Sim | Sim | ✅ PASS |
| UTC timestamps | Sim | Sim | ✅ PASS |
| Rejeita heartbeat atrasado | Sim | Sim | ✅ PASS |
| Preserva operational_state | Sim | Sim | ✅ PASS |

---

## Recomendação

🔴 **Implementação atual viola contrato B3**

**Ação recomendada ANTES de integração com AgentRuntime (ETAPA 4):**

Corrigir migration para fazer `last_heartbeat_at` nullable, eliminando heartbeat artificial.

```python
# CORREÇÃO NECESSÁRIA
nullable=True  # Em vez de False
server_default=None  # Em vez de sa.func.now()
```

**Impacto:** 
- Nenhum código precisa mudar
- Apenas semântica é restaurada
- Registros históricos continuam com timestamp artificial (aceitável)
- Novos registros começam com NULL (correto)

---

## Conclusão

✅ Schema está pronto (tecnicamente)  
❌ Semântica está quebrada (contratualmente)  
⚠️ **BLOQUEADOR para ETAPA 4 (AgentRuntime integration)**

**Próximo:** Corrigir migration ANTES de integrar AgentRuntime

