# ETAPA 4 — PHASE D MIGRATION GUIDE
## Before/After Code for 4 Uses

**Status**: Planning phase - No changes applied yet
**Date**: 2026-11-11
**Authorization**: Phase D Migration

---

## USO 1: PRE-CHECK (validar_profissional_para_servico)

**Location**: router/principal_router.py:1337

### Current Implementation
```python
async def validar_profissional_para_servico(dono_id: str, profissional: str | None, servico: str | None):
    """Valida se o profissional executa o serviço."""
    if not profissional or not servico:
        return {"ok": False, "validos": []}
    
    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    
    # ... service compatibility check ...
    
    if any(normalizar(servico) == normalizar(s) for s in servicos_prof):
        return {"ok": True, "validos": []}  # ← No duration
    
    return {"ok": False, "validos": validos}
```

### Proposed Migration
```python
async def validar_profissional_para_servico(dono_id: str, profissional: str | None, servico: str | None):
    """Valida se o profissional executa o serviço. Retorna duração se válido."""
    if not profissional or not servico:
        return {"ok": False, "validos": [], "duracao": None}
    
    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    
    # ... existing service compatibility check ...
    
    if any(normalizar(servico) == normalizar(s) for s in servicos_prof):
        # NEW: Get duration using bridge
        from services.duracao_service import obter_duracao_por_profissional_bridge
        
        duracao = await obter_duracao_por_profissional_bridge(dono_id, profissional, servico)
        
        if duracao is None:
            # Duration not configured - don't allow booking
            return {"ok": False, "validos": validos, "duracao": None}
        
        return {"ok": True, "validos": [], "duracao": duracao}  # ← Return duration
    
    return {"ok": False, "validos": validos, "duracao": None}
```

### Changes Required
- Line ~1378: Add bridge lookup before returning success
- Return dict now includes "duracao" field
- Reject booking if duration is None (can't proceed without knowing duration)

### Test Case
```python
@pytest.mark.asyncio
async def test_uso_1_precheck_with_duration():
    """USO 1: PRE-CHECK returns duration for valid prof+service."""
    dono_id = "tenant_precheck_1"
    prof_name = "Bruna"
    service = "corte"
    
    result = await validar_profissional_para_servico(dono_id, prof_name, service)
    
    assert result["ok"] is True
    assert result["duracao"] == 60  # ← Duration returned
    assert result["duracao"] is not None  # ← Explicit None handling
```

---

## USO 2: ALTERNATIVAS (verificar_conflito_e_sugestoes_profissional)

**Location**: router/principal_router.py:8525

### Current Implementation
```python
resultado_disp = await verificar_conflito_e_sugestoes_profissional(
    user_id=dono_id,
    data=data_iso,
    hora_inicio=hora_preferida,
    duracao_min=duracao_ctx,  # ← Passed in
    profissional=prof_ctx,
    servico=servico_ctx
)

# Returns alternatives for primary professional
# Each alternative uses duracao_min from primary professional
```

### Proposed Migration
For each alternative professional suggested, get their specific duration:

```python
# Inside verificar_conflito_e_sugestoes_profissional or calling code:

from services.duracao_service import obter_duracao_por_profissional_bridge

# Get alternatives (existing code)
alternatives = await find_alternative_professionals(...)

# NEW: For each alternative, get their duration
alternatives_with_durations = []
for alt_prof in alternatives:
    alt_duracao = await obter_duracao_por_profissional_bridge(
        tenant_id=dono_id,
        nome_profissional=alt_prof,
        nome_servico=servico
    )
    
    if alt_duracao is not None:  # ← Only include if duration known
        alternatives_with_durations.append({
            "profissional": alt_prof,
            "duracao": alt_duracao
        })

# Return alternatives with their specific durations
# Don't assume all have same duration as primary
```

### Changes Required
- Don't use `duracao_min` from primary for alternatives
- Get each alternative's specific duration via bridge
- Only suggest alternatives where duration is known
- Return alternatives with their durations

### Test Case
```python
@pytest.mark.asyncio
async def test_uso_2_alternativas_different_durations():
    """USO 2: Each alternative has their own configured duration."""
    # Primary: Bruna (corte 60min, unavailable)
    # Alternative 1: Gloria (corte 60min, available)
    # Alternative 2: Joana (corte 50min, available)
    
    alternatives = await find_alternatives_with_durations(...)
    
    # Each alternative must have their correct duration
    assert alternatives[0]["profissional"] == "Gloria"
    assert alternatives[0]["duracao"] == 60  # ← Gloria's duration
    
    assert alternatives[1]["profissional"] == "Joana"
    assert alternatives[1]["duracao"] == 50  # ← Joana's duration (different!)
```

---

## USO 3: LOOP COM CACHE (Multiple service slot checks)

**Location**: router/principal_router.py:7351, 7519, 7780+

### Current Implementation
```python
# Loop through available time slots
for slot_time in available_slots:
    for service in requested_services:
        duracao = estimar_duracao(service)  # ← Called repeatedly!
        
        # Check availability with this duration
        disponivel = await check_availability(prof, slot_time, duracao)
```

### Proposed Migration
```python
# NEW: Operation-scoped cache
prof_duracao_cache = {}  # Exists only during this operation

# Loop through available time slots
for slot_time in available_slots:
    for service in requested_services:
        # NEW: Check cache first
        cache_key = f"{prof}:{service}"
        if cache_key not in prof_duracao_cache:
            # First time: get duration via bridge
            from services.duracao_service import obter_duracao_por_profissional_bridge
            
            duracao = await obter_duracao_por_profissional_bridge(
                tenant_id=tenant_id,
                nome_profissional=prof,
                nome_servico=service
            )
            
            # Cache it for this operation only
            prof_duracao_cache[cache_key] = duracao
        else:
            # Use cached value
            duracao = prof_duracao_cache[cache_key]
        
        if duracao is None:
            continue  # ← Skip if duration unknown
        
        # Check availability with this duration
        disponivel = await check_availability(prof, slot_time, duracao)

# After operation ends: cache is discarded (scope ends)
```

### Changes Required
- Add operation-scoped cache (dictionary)
- Use bridge for first lookup, cache for subsequent
- Cache key includes both prof and service
- Cache never persists after operation ends
- No global cache, no inter-request sharing

### Test Case
```python
@pytest.mark.asyncio
async def test_uso_3_loop_cache_avoids_repeated_lookups():
    """USO 3: Cache prevents repeated lookups within operation."""
    prof = "Bruna"
    services = ["corte", "escova", "manicure"]
    
    # Simulate loop with cache
    prof_cache = {}
    lookup_count = 0
    
    for service in services:
        cache_key = f"{prof}:{service}"
        if cache_key not in prof_cache:
            # Simulate bridge lookup
            duracao = await obter_duracao_por_profissional_bridge(tenant_id, prof, service)
            prof_cache[cache_key] = duracao
            lookup_count += 1
    
    # 3 services = 3 lookups (one per service, not per slot)
    assert lookup_count == 3
    
    # But if we looped through 10 time slots, still only 3 lookups
    # (not 10 * 3 = 30 lookups)
    
    # Cache discarded after operation (no persistence)
    assert len(prof_cache) == 0  # ← Cache scope ended
```

---

## USO 4: CONFIRMAÇÃO (dados_confirmacao_agendamento)

**Location**: router/principal_router.py:2770

### Current Implementation
```python
# Try to get duration from service catalog
duracao_catalogo = None
if servicos_catalogo and servico_norm:
    for nome_servico, servico_data in servicos_catalogo.items():
        if nome_servico.strip().lower() == servico_norm:
            duracao_catalogo = servico_data.get("duracao")
            break

# Fallback to estimate
duracao_confirmacao = duracao_catalogo or estimar_duracao(servico)

ctx["dados_confirmacao_agendamento"] = {
    "profissional": prof,
    "servico": servico,
    "data_hora": data_hora,
    "duracao": duracao_confirmacao,  # ← Could be estimate
    "descricao": formatar_descricao_evento(servico, prof),
}
```

### Proposed Migration
```python
# NEW: Try bridge BEFORE fallback to estimate
from services.duracao_service import obter_duracao_por_profissional_bridge

# Existing catalog lookup
duracao_catalogo = None
if servicos_catalogo and servico_norm:
    for nome_servico, servico_data in servicos_catalogo.items():
        if nome_servico.strip().lower() == servico_norm:
            duracao_catalogo = servico_data.get("duracao")
            break

# NEW: Try bridge if catalog didn't have it
duracao_bridge = None
if duracao_catalogo is None and prof:
    duracao_bridge = await obter_duracao_por_profissional_bridge(
        tenant_id=dono_id,
        nome_profissional=prof,
        nome_servico=servico
    )

# NEW: Explicit None handling
duracao_confirmacao = duracao_catalogo or duracao_bridge or estimar_duracao(servico)

# NEW: Don't confirm without known duration
if duracao_confirmacao is None:
    return await _send_and_stop(context, user_id, "Não consegui definir a duração do serviço")

ctx["dados_confirmacao_agendamento"] = {
    "profissional": prof,
    "servico": servico,
    "data_hora": data_hora,
    "duracao": duracao_confirmacao,  # ← Now definitely set
    "descricao": formatar_descricao_evento(servico, prof),
}
```

### Changes Required
- Line ~2770: Add bridge lookup before estimate fallback
- Explicit None check - don't confirm without duration
- Priority: catalog → bridge → estimate
- Message if duration can't be determined

### Test Case
```python
@pytest.mark.asyncio
async def test_uso_4_confirmacao_uses_bridge_before_estimate():
    """USO 4: Confirmation uses bridge duration before fallback estimate."""
    prof = "Carla"
    service = "pedicure"
    
    # Bridge returns 40min, but estimate would be 30min
    # Confirmation should use 40min (bridge value)
    
    dados_conf = await build_confirmation_data(tenant_id, prof, service)
    
    assert dados_conf["duracao"] == 40  # ← From bridge, not estimate
    assert dados_conf["duracao"] is not None
```

---

## Summary: Migration Points

| Use | Location | Current | Change | Priority |
|-----|----------|---------|--------|----------|
| USO 1 | 1337 | Validates service only | Add duration + reject if None | HIGH |
| USO 2 | 8525 | Uses primary duration for all | Get each alternative's duration | HIGH |
| USO 3 | 7351, 7519, 7780+ | Repeated estimate calls | Operation-scoped cache + bridge | MEDIUM |
| USO 4 | 2770 | Catalog → estimate | Catalog → bridge → estimate | MEDIUM |

---

## Testing Strategy

1. Unit tests: Each use case tested in isolation
2. Integration: All 4 uses together
3. Multi-tenant: Same prof name, different tenants
4. Regression: Full flow doesn't break
5. Real Firestore: Persistence tests

---

## Approval Criteria

- ✅ All 4 uses migrated
- ✅ 18+ tests passing (infrastructure + new integration)
- ✅ No breaking changes
- ✅ Multi-tenant isolation maintained
- ✅ None handling explicit throughout
- ✅ Diff documented for each use

---

**Next**: Implement migrations in order, test each before advancing.

