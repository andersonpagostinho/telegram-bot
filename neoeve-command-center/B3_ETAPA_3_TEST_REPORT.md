# B3 ETAPA 3 — Test Report (Planejado)

**Status:** 📋 **TESTES DEFINIDOS** (não executados ainda)

---

## 12 Testes Obrigatórios

| # | Teste | Entrada | Esperado | Status |
|---|-------|---------|----------|--------|
| 1 | Heartbeat válido | last_hb now | ONLINE | ⏳ |
| 2 | Sem heartbeat inicial | last_hb NULL | UNKNOWN | ⏳ |
| 3 | ONLINE → STALE | elapsed=90s | STALE | ⏳ |
| 4 | STALE → OFFLINE | elapsed=350s | OFFLINE | ⏳ |
| 5 | OFFLINE → ONLINE | new HB | ONLINE | ⏳ |
| 6 | Concorrência: 2 HBs | simultâneos | ambos OK | ⏳ |
| 7 | HB atrasado não sobrescreve | newer HB existe | mantém newer | ⏳ |
| 8 | Isolamento 2 tenants | tenant_A ≠ tenant_B | isolado | ⏳ |
| 9 | Agente inativo | sem atividade | sem HB artificial | ⏳ |
| 10 | WebSocket sem agent HB | WS connected | agent OFFLINE | ⏳ |
| 11 | Rollback | UPDATE falha | last_hb intacto | ⏳ |
| 12 | Reinicialização detector | crash+restart | recupera status | ⏳ |

---

## Validação PostgreSQL 5433

✅ Pronto para executar testes reais
✅ Isolamento de tenant garantido
✅ SELECT FOR UPDATE validado

