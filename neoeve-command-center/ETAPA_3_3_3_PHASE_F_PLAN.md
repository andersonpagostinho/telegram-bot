# ETAPA 3.3.3 — FASE F: REGRESSÃO COMPLETA
## Plano de Execução

**Data:** 2026-11-24  
**Status:** Planejamento  
**Database:** neoeve_postgres_recovery_test (port 5433) EXCLUSIVAMENTE

---

## 1. PRÉ-REQUISITOS VALIDADOS

✅ **Conexão com banco teste confirmada**
- PostgreSQL 15.20 (Alpine)
- Database: neoeve_recovery_test
- Port: 5433 ✓ (isolado de produção 5432)

✅ **Sem processos em background**
- Nenhum pytest, alembic ou migração em execução

✅ **Warnings classificados (Fase E)**
- 7 warnings Pydantic: Severidade 🟡 BAIXA (deprecation, não bloqueia)

---

## 2. SUITES DE TESTE A EXECUTAR

### Suite 1: RecoveryService Core (20 testes)
```bash
pytest tests/test_recovery_service.py::TestRecoveryServiceCore -v
```
- Esperado: 20/20 PASS
- Duração: ~2-3 min
- Validação: Núcleo de retry, política, classificação

### Suite 2: AgentRuntime Integration (12 testes)
```bash
pytest tests/test_recovery_service.py::TestAgentRuntimeIntegration -v
```
- Esperado: 12/12 PASS
- Duração: ~1-2 min
- Validação: Integração com runtime de agentes

### Suite 3: Recovery Dashboard (17 testes)
```bash
pytest tests/test_recovery_service.py::TestRecoveryDashboard -v
```
- Esperado: 17/17 PASS
- Duração: ~2-3 min
- Validação: Métricas e histórico

### Suite 4: Persistence (5 testes)
```bash
pytest tests/test_recovery_service.py::TestPersistence -v
```
- Esperado: 5/5 PASS
- Duração: ~1 min
- Validação: Salvamento e recuperação

### Suite 5: PostgreSQL Concurrency (7 testes) ✨
```bash
pytest tests/test_recovery_service_postgresql.py::TestPostgresqlConcurrency -v
```
- Esperado: 7/7 PASS ✅ (já validado em Fase E)
- Duração: ~3 min
- Validação: Concorrência, deduplicação, isolamento

**Total: 61 testes**

---

## 3. REGRESSÃO SQLite (Verificação de Estabilidade)

Executar toda a suíte de 54 testes (Core+AgentRuntime+Dashboard+Persistence) **DUAS VEZES** consecutivas:

```bash
# RUN 1
pytest tests/test_recovery_service.py -v

# RUN 2
pytest tests/test_recovery_service.py -v
```

**Objetivo:** Verificar ausência de contaminação entre testes, vazamento de estado, ou instabilidade.

**Esperado:** 54/54 PASS em ambas as execuções

---

## 4. VERIFICAÇÕES ADICIONAIS (Checklist)

### Deduplicação (test_f)
- [ ] Primeiro processamento de evento retorna `True`
- [ ] Duplicata do mesmo evento retorna `False`
- [ ] Apenas UM registro em event_idempotency_keys (não dois)
- [ ] Sessão SQLAlchemy continua utilizável após tentativa duplicada
- [ ] Erros reais não são silenciosamente tratados como duplicação

### Concorrência
- [ ] Sem "InvalidRequestError: This session is in 'prepared' state"
- [ ] Sem "PytestUnhandledThreadExceptionWarning"
- [ ] Sessions isoladas por thread (não compartilhadas)
- [ ] test_a: 1 worker adquire lease (outro bloqueado)
- [ ] test_b: tokens monotônicos (1,2,3... sem gaps)

### Isolamento Multi-Tenant
- [ ] Dados de tenant A não vazam para tenant B
- [ ] Queries filtram por tenant_id obrigatoriamente
- [ ] test_e resultado: Isolamento validado

### Migrations
- [ ] `alembic current` = 007
- [ ] `alembic downgrade 006` funciona (sem "index not exist")
- [ ] `alembic upgrade 007` funciona (re-aplicação)
- [ ] Índices corrigidos (sem duplicação)

### Warnings
- [ ] Nenhum warning crítico (além dos Pydantic deprecation)
- [ ] Nenhum "unhandled exception in thread"
- [ ] Nenhum "prepared state" error

---

## 5. RESTRIÇÕES MANTIDAS

```
❌ Não ativar Recovery Worker
❌ Não executar agentes reais
❌ Não criar missões reais
❌ Não alterar projeto principal
❌ Não fazer commit, push, deploy
❌ Não modificar banco de produção
✅ Usar EXCLUSIVAMENTE neoeve_postgres_recovery_test (5433)
```

---

## 6. CRONOGRAMA ESPERADO

| Fase | Duração | Pontos |
|------|---------|--------|
| RecoveryService (20) | ~2-3 min | Núcleo |
| AgentRuntime (12) | ~1-2 min | Integração |
| Dashboard (17) | ~2-3 min | Métricas |
| Persistence (5) | ~1 min | Salvamento |
| PostgreSQL (7) | ~3 min | Concorrência ✨ |
| **Subtotal 61** | **~10-15 min** | - |
| SQLite Run 1 (54) | ~6-8 min | Estabilidade |
| SQLite Run 2 (54) | ~6-8 min | Contaminação |
| **Total** | **~30-40 min** | - |

---

## 7. CRITÉRIO DE APROVAÇÃO

✅ **Aprovado se:**
- 61/61 testes PostgreSQL + suites PASS (100%)
- 54/54 testes SQLite RUN 1 PASS (100%)
- 54/54 testes SQLite RUN 2 PASS (100%)
- Nenhuma regressão vs Fase E
- Nenhum warning crítico (Pydantic OK)
- Isolamento confirmado
- Migrations funcionando (up/down/up)

❌ **Rejeitado se:**
- Qualquer teste FAIL
- Warning de thread não tratado
- "prepared state" error
- Isolamento quebrado
- Migrations em erro

---

## 8. RELATÓRIO ESPERADO

Será gerado em: `ETAPA_3_3_3_PHASE_F_REPORT.md`

Conteúdo:
- Resultados por suíte (duração, testes, warnings)
- Warnings classificados
- Falhas e correções (se houver)
- Evidências de isolamento
- Confirmação do banco utilizado
- Resultado das 2 execuções SQLite
- Pendências e riscos
- Aprovação/Rejeição final

---

**Next:** Aguardar conclusão de migration 007, depois iniciar testes.

