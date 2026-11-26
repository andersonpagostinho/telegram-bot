# ETAPA 3.4 — ROLLOUT PLAN
## Plano de Lançamento Gradual do Recovery Service

**Data:** 2026-11-24  
**Status:** Pronto para Autorização  
**Critério:** Recovery Worker DESABILITADO até aprovação explícita

---

## 🎯 OBJETIVO

Lançar o Recovery Service em produção **sem ativar o Recovery Worker** até validação operacional completa.

---

## FASE 1 — DEPLOY DO CÓDIGO

### Pré-requisitos
```
✅ ETAPA 3.3.3 aprovada (169/169 testes)
✅ ETAPA 3.4 auditoria completa (bloqueadores: ZERO)
✅ Autorização do usuário (aguardando)
```

### Ações
```
1. ✅ Código aprovado está em main
2. ✅ Migrations 006 e 007 prontas
3. ✅ Testes passando (61/61 PostgreSQL, 54+54 SQLite)
4. ✅ Zero credenciais no código
```

### Restrições
```
❌ Não alterar Recovery Worker (self.enabled = False)
❌ Não executar migrations em produção (ainda não autorizado)
❌ Não ativar Worker
```

### Validação Pós-Deploy
```
1. Verificar DATABASE_URL em produção
2. Confirmar migrations não aplicadas (yet)
3. Validar health check endpoint (desativado por enquanto)
4. Confirmar Recovery Worker desabilitado (logs)
```

---

## FASE 2 — VALIDAÇÃO EM PRODUÇÃO

### Checklist Operacional

#### 2.1 — Health Check
```
[ ] GET /health → 200 OK (sem Recovery Worker)
[ ] Logs mostram: "Recovery worker is DISABLED"
[ ] Dashboard health check endpoint: 200 (sem dados)
[ ] Métricas zeradas (esperado, Worker desativado)
```

#### 2.2 — Conectividade
```
[ ] DATABASE_URL válida
[ ] Conexão PostgreSQL estabelecida
[ ] Pool de conexões estável
[ ] Sem timeout de banco
```

#### 2.3 — Isolamento
```
[ ] Multi-tenant isolado (verificar logs)
[ ] Sem cross-tenant data visible
[ ] Tenant_id propagado em contexto
[ ] Sem vazamento de dados
```

#### 2.4 — Segurança
```
[ ] Logs não contêm credenciais
[ ] Sem hard-coded secrets
[ ] Environment variables carregadas corretamente
[ ] Acesso a banco via DATABASE_URL (ORM)
```

---

## FASE 3 — TESTES CONTROLADOS (Homologação)

### Teste 1: Idempotência
```bash
# Executar em homologação com banco de teste
pytest tests/test_recovery_service_postgresql.py::TestPostgresqlConcurrency::test_f_duplicate_events_idempotent -v

Esperado:
- Evento processado uma vez
- Segunda tentativa retorna False (idempotente)
- Zero duplicação em execution_attempts
```

### Teste 2: Isolamento Multi-Tenant
```bash
pytest tests/test_recovery_service_postgresql.py::TestPostgresqlConcurrency::test_e_tenant_isolation -v

Esperado:
- Tenant A eventos isolados
- Tenant B eventos isolados
- Sem cross-tenant data
```

### Teste 3: Concorrência
```bash
pytest tests/test_recovery_service_postgresql.py::TestPostgresqlConcurrency::test_a_two_workers_dispute_lease -v
pytest tests/test_recovery_service_postgresql.py::TestPostgresqlConcurrency::test_b_concurrent_fencing_token_increment -v

Esperado:
- 1 worker adquire lease
- Outro bloqueado
- Sem "prepared state" error
- Fencing tokens monotônicos
```

### Teste 4: Health Check
```bash
# Executar em homologação
curl http://localhost:8000/tenant/{tenant}/recovery/worker-health

Esperado:
- 200 OK
- Status: healthy/unhealthy (desabilitado = OK)
- Métricas: empty (Workers desativados)
```

---

## FASE 4 — ATIVAÇÃO GRADUAL (Requer Aprovação)

### Pré-ativação
```
⚠️ BLOQUEADO ATÉ APROVAÇÃO EXPLÍCITA ⚠️

Critério de aprovação:
✅ Fases 1-3 validadas
✅ Sem incidentes em produção
✅ Health check verde
✅ Logs estáveis
✅ Performance aceitável
✅ Autorização do usuário recebida
```

### Ativação (Apenas com Autorização)
```
1. Modificar app/services/recovery_worker.py:
   self.enabled = False  →  self.enabled = True

2. Validar restart:
   - Worker inicia
   - Logs mostram: "Recovery worker starting..."
   - Health check: worker status online

3. Monitorar primeiras 24h:
   - CPU/Memory
   - Database load
   - Error rate
   - Duplicate execution rate (deve ser ZERO)

4. Se problemas:
   - Executar rollback (vide FASE 5)
```

---

## FASE 5 — ROLLBACK PLAN

### Cenário 1: Antes da Ativação do Worker

**Se problemas na Fase 1-3:**
```
1. Revert código (git checkout HEAD~1)
2. Remover migrations 006 e 007 (via rollback alembic)
3. Restaurar banco (snapshot anterior)
4. Validar sistema
5. Investigar root cause
6. Aguardar novo deploy após correções
```

**Tempo de Reversão:** ~15 minutos

---

### Cenário 2: Após Ativação do Worker

**Se problemas após ativar Worker:**
```
1. IMEDIATAMENTE desabilitar Worker:
   - Modificar self.enabled = True → False
   - Restart aplicação
   - Verificar que Worker parou (logs)

2. Monitorar executions:
   - Leases expirados serão recuperados
   - Nenhum retry duplicado (proteção idempotência)
   - Histórico preservado

3. Verificar banco:
   - executions tabela intacta
   - execution_attempts não deletados
   - recovery_metrics preservados

4. Dados NÃO serão perdidos:
   - Tabelas permanecerão
   - Histórico completo disponível
   - Reativação futura possível

5. Investigar problema
6. Deploy novo após correção
```

**Tempo de Reversão:** ~5 minutos (parar Worker)

---

### Cenário 3: Disaster Recovery

**Se banco corrompido ou inacessível:**
```
1. Health check falhará (esperado)
2. Worker parará automaticamente
3. Manutenção manual do banco (DBA)
4. Sistema continua rodando (sem Recovery)
5. Historicamente executado sem Recovery Worker
```

---

## MONITORAMENTO PÓS-DEPLOY

### Métricas Críticas

#### CPU/Memory
```
Target: < 20% CPU, < 500MB RAM (Worker)
Alert: > 30% CPU ou > 750MB RAM
Ação: Verificar backlog, parar Worker
```

#### Database Connections
```
Target: 2-5 conexões ativas (Recovery)
Alert: > 10 conexões não esperadas
Ação: Verificar for leaks, restart
```

#### Error Rate
```
Target: 0% erros de Recovery
Alert: > 1% (5 falhas em 500 tentativas)
Ação: Investigar, considerar rollback
```

#### Duplicate Execution Rate
```
Target: 0% (idempotência garantida)
Alert: > 0 (qualquer duplicação)
Ação: IMEDIATO rollback + investigação
```

---

## COMUNICAÇÃO

### Pré-Deploy
```
[ ] Notificar time operacional
[ ] Validar janela de manutenção
[ ] Confirmar rollback plan com DBA
[ ] Preparar escalação
```

### Pós-Deploy
```
[ ] Comunicar status ao time
[ ] Compartilhar health check URL
[ ] Disponibilizar runbook de rollback
[ ] Escalonar problemas conforme protocolo
```

---

## TIMELINE

```
Fase 1 (Deploy): 30-60 minutos
Fase 2 (Validação Produção): 30 minutos
Fase 3 (Testes Homologação): 1-2 horas
Fase 4 (Ativação Gradual): Aguardando aprovação
─────────────────────────────
Total (até Ativação): 2-3 horas
```

---

## CRITÉRIO DE SUCESSO

✅ **Deploy Bem-Sucedido se:**
```
1. Código e migrations em produção
2. Health check verde (Worker desabilitado)
3. Sem incidentes em 24h
4. Logs estáveis
5. Isolamento validado
6. Performance estável
7. Autorização recebida para ativar Worker
```

❌ **Rollback Obrigatório se:**
```
1. Health check falhar
2. Erros não-recuperáveis em logs
3. Database inacessível
4. Duplicate executions detectados
5. Isolamento multi-tenant quebrado
6. Vazamento de credenciais
7. Incidente crítico não mitigável
```

---

## PRÓXIMOS PASSOS

1. ✅ Auditoria pré-deploy completa (ETAPA_3_4_PRE_DEPLOY_AUDIT.md)
2. ✅ Plano de rollout pronto (este documento)
3. ⏳ **Aguardando autorização para:**
   - Deploy do código em produção
   - Aplicação de migrations 006 e 007
   - Testes em ambiente de produção
   - Autorização para ativar Recovery Worker

---

**Plano Finalizado:** 2026-11-24  
**Status:** Aguardando Autorização do Usuário  
**Recomendação:** Prosseguir com deploy conforme Fase 1

