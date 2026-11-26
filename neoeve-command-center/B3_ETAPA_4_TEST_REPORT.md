# B3 ETAPA 4 — Test Report

**Status:** 📋 **10 Testes Definidos**

---

## Testes Obrigatórios

| # | Teste | Esperado |
|---|-------|----------|
| 1 | Agente inativo = sem HB artificial | UNKNOWN |
| 2 | Execução real = HB emitido | ONLINE |
| 3 | Execução longa = HB válido | ONLINE |
| 4 | HB falha ≠ interrompe tarefa | Tarefa continua |
| 5 | Isolamento 2 tenants | Isolado |
| 6 | 2 execuções concorrentes | Ambas OK |
| 7 | HB antigo ≠ sobrescreve novo | Novo preservado |
| 8 | WebSocket sem agent HB | Agent OFFLINE |
| 9 | Restart preserva timestamp | Timestamp intacto |
| 10 | UNKNOWN até HB real | UNKNOWN |

✅ PostgreSQL 5433 (real)

