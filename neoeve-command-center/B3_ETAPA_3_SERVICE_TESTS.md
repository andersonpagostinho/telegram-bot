# B3 ETAPA 3 — Service Tests

**Status:** 📋 **TESTES DEFINIDOS** (ready for PostgreSQL 5433)

---

## 8 Testes Obrigatórios

| # | Teste | Entrada | Esperado | Localização |
|---|-------|---------|----------|-------------|
| 1 | HB válido → record | now | True | postgresql |
| 2 | HB atrasado → record | past | False | postgresql |
| 3 | Atualizações simultâneas | 2 threads | 1 sucesso | postgresql |
| 4 | Isolamento 2 tenants | tenant_A/B | isolado | postgresql |
| 5 | Sem HB → detect | None | UNKNOWN | python |
| 6 | 30s → detect | 30s | ONLINE | python |
| 7 | 150s → detect | 150s | STALE | python |
| 8 | 350s → detect | 350s | OFFLINE | python |

---

## Validações

✅ operational_state preservado  
✅ Nenhuma cross-tenant pollution  
✅ Rollback em erro  
✅ UTC timestamps  
✅ SELECT FOR UPDATE bloqueio correto  

---

## Pronto para Execução

🟢 PostgreSQL 5433 (isolado)  
🟢 Sessões independentes  
🟢 Sem agentes reais executados  

