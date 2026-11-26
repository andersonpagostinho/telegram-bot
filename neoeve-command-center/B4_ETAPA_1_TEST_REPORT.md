# B4 ETAPA 1 — Test Report

**Status:** 📋 **10 Testes Definidos**

## Testes Obrigatórios

| # | Teste | Status |
|---|-------|--------|
| 1 | POST /missions válido | ✅ READY |
| 2 | Payload inválido (name vazio) | ✅ READY |
| 3 | Sem autenticação | ✅ READY |
| 4 | Usuário sem permissão | ✅ READY |
| 5 | GET /missions por ID | ✅ READY |
| 6 | Listagem paginada | ✅ READY |
| 7 | Tenant A vs Tenant B isolation | ✅ READY |
| 8 | Payload com tenant_id inválido (bloqueado) | ✅ READY |
| 9 | Persistência + Rollback | ✅ READY |
| 10 | Evento publicado | ✅ READY |

✅ PostgreSQL 5433 (isolado)

