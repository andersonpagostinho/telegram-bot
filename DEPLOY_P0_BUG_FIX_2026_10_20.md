# 🚀 DEPLOY — P0 Nova Fix Preservação de Contexto (2026-10-20)

## Resumo da Mudança
**FIX:** Serviço sendo trocado quando usuário escolhe profissional

**Commit:** `591f870` - [P0 NOVO BUG FIX] Preservar serviço quando usuário escolhe profissional

## Problema Descoberto
- Fluxo: MSG1 "corte feminino" → MSG2 "gloria" 
- ❌ Bug: Serviço trocado de "corte feminino" → "coloracao"
- Root cause: `extrair_slots_e_mesclar()` sobrescrevia serviço anterior

## Mudanças Implementadas
**Arquivo:** `router/principal_router.py` (1 linha adicionada)

```python
# ANTES (linhas 1415-1423):
if (
    not servico_detectado
    and not eh_rejeicao_alternativa
):
    servico_detectado = await encontrar_servico_mais_proximo(...)

# DEPOIS:
if (
    not servico_detectado
    and not eh_rejeicao_alternativa
    and not servico_anterior  # ← NOVO BLOQUEIO
):
    servico_detectado = await encontrar_servico_mais_proximo(...)
```

## Validação

### Testes Aprovados
✅ `test_p0_debug_servico_gloria.py` — Preservação de contexto MSG1→MSG2  
✅ `test_p0_12_e2e_evento_real.py` — E2E completo com evento no Firestore

### Comportamento Pós-Fix
- ✅ MSG1: "voce tem agenda para corte feminino amanha as 10?" → servico='corte feminino'
- ✅ MSG2: "gloria" → profissional_escolhido='Gloria', servico PRESERVADO='corte feminino'
- ✅ MSG3: evento criado em Firestore com profissional='Gloria', servico='corte feminino'

## Deploy Instructions
1. Verificar que commit `591f870` está em `origin/main`
2. Fazer deploy do branch `main`
3. Validar em produção: Fluxo 3 mensagens com "corte feminino" → escolher "gloria"

## Risk Assessment
🟢 **LOW RISK**
- Mudança minimal (1 linha)
- Apenas adiciona bloqueio existente (já validado em outras funções)
- Não afeta APIs externas
- Testes E2E com Firebase real validam completo

## Rollback
Se necessário, revert para commit anterior (27c037e) — mudança é facilmente reversível.

---
**Status:** ✅ READY FOR PRODUCTION DEPLOYMENT
**Date:** 2026-10-20 18:40 UTC
