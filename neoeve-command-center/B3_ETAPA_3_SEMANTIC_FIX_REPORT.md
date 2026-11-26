# B3 ETAPA 3 — Semantic Fix Report

**Status:** ✅ **CORRIGIDO**

## Correção Aplicada

**Modelo:** `database/models.py`
- De: `nullable=False, default=utc_now`
- Para: `nullable=True`

**Resultado:**
- ✅ NULL = UNKNOWN (sem heartbeat real)
- ✅ Apenas record_heartbeat() atualiza timestamp
- ✅ Contrato restaurado

## Dados

✅ 5 registros artificiais limpados (NULL)
✅ Nenhum heartbeat real perdido
✅ Semântica corrigida

## Status: PRONTO

