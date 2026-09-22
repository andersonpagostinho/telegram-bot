# FASE 3 — PERSISTÊNCIA, AUDITORIA, IDEMPOTÊNCIA E OUTBOX

**Data:** 2026-07-27  
**Fase:** 3 (Persistência)  
**Status:** Planejamento Detalhado  

---

## 🎯 OBJETIVO

Criar camada de aplicação e infraestrutura que:
- Carrega snapshot comercial atual
- Valida idempotência ANTES de decisão de domínio
- Chama BillingDomainService puro (Fase 2)
- Persiste novo snapshot de forma consistente
- Registra auditoria append-only
- Grava eventos internos em outbox
- Retorna resultado estruturado
- Não executa integrações externas

---

## 📊 MODELO DE DADOS

### 1. Agregado Comercial (Snapshot)

**Collection:** `Tenants/{tenant_id}/CommercialAggregates/{aggregate_id}`

**Documento (JSON):**
```json
{
  "aggregate_id": "string (UUID)",
  "tenant_id": "string (obrigatório)",
  "lead_id": "string (quando pre-tenant)",
  "subscription_id": "string (quando convertido)",
  "plan_id": "string (STUDIO157, SALAO247, etc)",
  "version": 42,
  "created_at": "timestamp (server)",
  "updated_at": "timestamp (server)",
  "last_source_event_id": "string (hotmart_123456)",
  "trial_state": "PREPARADO|ATIVO|EXPIRADO|CONVERTIDO|CANCELADO|DELETADO",
  "assinatura_state": "PENDENTE|ATIVA|CANCELAMENTO_AGENDADO|CANCELADA|ENCERRADA",
  "pagamento_state": "PENDENTE|APROVADO|RECUSADO|ATRASADO|REEMBOLSADO|CONTESTADO|RESOLVIDO",
  "acesso_state": "LIBERADO|RESTRITO|SUSPENSO|ENCERRADO",
  "retencao_state": "ATIVO|EM_RETENCAO|ELEGIVEL_EXCLUSAO|EXCLUIDO",
  "period_start": "date",
  "period_end": "date",
  "metadata": {
    "last_trial_days": 7,
    "reactivation_deadline": "date",
    "cancellation_effective_date": "date"
  }
}
```

**Índices Requeridos:**
- `(tenant_id, updated_at)` para queries por tenant
- `(tenant_id, version)` para controle otimista

---

### 2. Eventos Processados (Idempotência)

**Collection:** `Tenants/{tenant_id}/ProcessedWebhookEvents/{id}`

**Documento (JSON):**
```json
{
  "provider": "hotmart|internal|manual",
  "provider_event_id": "string (unique per provider)",
  "event_type": "purchase_approved|payment_failed|subscription_canceled|...",
  "tenant_id": "string (obrigatório)",
  "payload_hash": "string (SHA256 do payload)",
  "received_at": "datetime (application-generated)",
  "processing_status": "RECEIVED|PROCESSING|PROCESSED|FAILED_RETRYABLE|FAILED_PERMANENT|RECONCILIATION_REQUIRED",
  "correlation_id": "string (rastreabilidade)",
  "processed_at": "timestamp (server)",
  "decision_code": "string (success|validation_failed|conflict|...)",
  "aggregate_version_before": 41,
  "aggregate_version_after": 42,
  "error_reason": "string (se falha)"
}
```

**Chave Primária Conceitual:** `provider + provider_event_id`

**Índices Requeridos:**
- `(tenant_id, provider_event_id)` para idempotência
- `(tenant_id, processing_status)` para reconciliação
- `(tenant_id, received_at)` para auditoria temporal

---

### 3. Auditoria (Append-Only)

**Collection:** `Tenants/{tenant_id}/CommercialAudit/{audit_id}`

**Documento (JSON):**
```json
{
  "audit_id": "string (auto-generated)",
  "tenant_id": "string (obrigatório)",
  "aggregate_id": "string",
  "aggregate_version_before": 41,
  "aggregate_version_after": 42,
  "source_event_id": "string",
  "correlation_id": "string",
  "decision_code": "string",
  "success": true,
  "previous_states": {
    "trial_state": "ATIVO",
    "assinatura_state": "PENDENTE",
    "pagamento_state": "PENDENTE",
    "acesso_state": "LIBERADO",
    "retencao_state": "ATIVO"
  },
  "resulting_states": {
    "trial_state": "ATIVO",
    "assinatura_state": "ATIVA",
    "pagamento_state": "APROVADO",
    "acesso_state": "LIBERADO",
    "retencao_state": "ATIVO"
  },
  "transitions_applied": [
    {"machine": "AssinaturaStateMachine", "from": "PENDENTE", "to": "ATIVA"},
    {"machine": "PagamentoStateMachine", "from": "PENDENTE", "to": "APROVADO"},
    {"machine": "AcessoStateMachine", "from": "LIBERADO", "to": "LIBERADO"}
  ],
  "transitions_ignored": [],
  "effects_suggested": [
    "publicar_evento:assinatura_ativada",
    "liberar_acesso_completo"
  ],
  "internal_events_generated": [
    "SubscriptionActivated",
    "PaymentApproved",
    "AccessReleased"
  ],
  "occurred_at": "timestamp (server)",
  "schema_version": "1.0"
}
```

**Padrão:** Append-only. NUNCA update ou delete.

**Índices Requeridos:**
- `(tenant_id, occurred_at)` para timeline
- `(tenant_id, decision_code)` para análise de decisões

---

### 4. Outbox (Eventos Não Publicados)

**Collection:** `Tenants/{tenant_id}/CommercialOutbox/{outbox_id}`

**Documento (JSON):**
```json
{
  "outbox_id": "string (UUID)",
  "tenant_id": "string (obrigatório)",
  "event_type": "SubscriptionActivated|PaymentApproved|...",
  "schema_version": "1.0",
  "payload": {
    "event_id": "string",
    "correlation_id": "string",
    "tenant_id": "string",
    "received_at": "datetime",
    "...": "event-specific payload"
  },
  "correlation_id": "string",
  "source_event_id": "string (webhook que gerou)",
  "aggregate_version": 42,
  "created_at": "timestamp (server)",
  "publication_status": "PENDING|PROCESSING|PUBLISHED|FAILED_RETRYABLE|FAILED_PERMANENT",
  "publication_attempts": 0,
  "published_at": null,
  "last_error": null
}
```

**Padrão:** Nesta fase apenas criar (PENDING). Não publicar.

**Índices Requeridos:**
- `(tenant_id, publication_status)` para worker (Fase 5)
- `(tenant_id, created_at)` para auditoria

---

## 🏗️ ARQUITETURA

### Fluxo Completo

```
webhook_payload (entrada)
    ↓
BillingApplicationService.process_event()
    ↓
    1. Validar envelope
    2. Abrir UnityOfWork (transação)
    3. IdempotencyRepository.check()
       ↓
       ├─ Se já processado → retornar resultado armazenado
       └─ Se novo → continuar
    4. CommercialAggregateRepository.load()
    5. BillingDomainService.process() (puro)
    6. CommercialAggregateRepository.save() (com versionamento)
    7. ProcessedEventRepository.mark_processed()
    8. CommercialAuditRepository.record()
    9. CommercialOutboxRepository.save()
    10. UnityOfWork.commit() (transação Firestore)
    ↓
resultado estruturado
```

### Separação de Responsabilidades

#### BillingApplicationService
- Orquestração de fluxo
- Validação de envelope
- Gerenciamento de UnityOfWork
- Tratamento de erros

#### Repositórios (Interfaces)
- CommercialAggregateRepository: load/save snapshot
- ProcessedEventRepository: check/mark idempotência
- CommercialAuditRepository: record auditoria
- CommercialOutboxRepository: save eventos
- UnityOfWork: coordenar transação

#### Implementações Firestore
- Concrete implementations com Firestore SDK
- Transações explícitas
- Versionamento otimista

#### BillingDomainService (Fase 2)
- Lógica pura (não toca repositórios)
- Retorna decisão estruturada
- Já implementado e testado

---

## 🔐 CONCORRÊNCIA E VERSIONAMENTO

### Controle Otimista

```python
# Ao carregar:
snapshot = repository.load(aggregate_id)
version = snapshot.version  # ex: 41

# BillingDomainService processa
result = service.process(snapshot, event)

# Ao salvar:
try:
    repository.save(
        new_snapshot_with_version_42,
        expected_version=41  # compare-and-set
    )
except ConflictError:
    # Retry ou fail gracefully
    return {"success": False, "code": "version_conflict", "retryable": True}
```

### Implementação Firestore
- Use `transaction()` com check de version
- Falha se `version_before != expected`
- Retorna código estável para retry

---

## ✅ ATOMICIDADE

### Transação Firestore Coordenada

```python
def commit_transaction(transaction_writes):
    """
    Atomicidade garantida:
    - Snapshot novo
    - Evento marcado como processado
    - Auditoria registrada
    - Outbox criado

    OU nada (rollback se falha)
    """
    with firestore.transaction() as txn:
        txn.set(aggregatePath, newSnapshot)
        txn.set(processedEventPath, processedEvent)
        txn.set(auditPath, auditRecord)
        txn.set(outboxPath, outboxEvent)
        # Commit automático ao sair do contexto
        # Ou falha com TransactionError se conflito
```

### Limitação Conhecida
- Firestore limita 25 writes por transação
- Outbox com N eventos = N writes
- **Decisão Fase 3:** 1 evento por outbox entry (padrão correto)

---

## 📋 IDEMPOTÊNCIA

### Antes de Decisão de Domínio

```
workflow:
    1. ProcessedEventRepository.check(provider, event_id)
       ↓
       ├─ Se existe com status PROCESSED
       │  └─ Retornar result armazenado (idempotente replay)
       └─ Se novo
          └─ Registrar como PROCESSING
    2. BillingDomainService.process()
    3. Atualizar status para PROCESSED
```

### Chave Primária
- `provider` (ex: "hotmart")
- `provider_event_id` (ex: "evt_123456")
- **Conceitual:** Unique constraint em (tenant_id, provider, provider_event_id)

### Payload Hash
- SHA256(JSON do payload)
- Detectar duplicados com payload_hash diferente
- → Reconciliação necessária (conflict)

---

## 🛡️ ISOLAMENTO MULTI-TENANT

### Requisitos Obrigatórios

✅ **tenant_id validado em toda leitura/escrita**
```python
def load(tenant_id: str, aggregate_id: str):
    # Validar tenant_id não vazio
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id obrigatório")
    
    # Carregar de path específico
    return db.collection(f"Tenants/{tenant_id}/CommercialAggregates/{aggregate_id}").get()
```

✅ **Nenhum lookup global que permita colisão**
- Todas as queries incluem WHERE tenant_id
- Nenhuma leitura de Tenants/*/

✅ **Teste de cross-tenant obrigatório**
```python
def test_cross_tenant_isolation():
    # Tenant A carrega snapshot
    # Tenant B tenta carregar mesmo aggregate_id
    # Deve falhar com NOT_FOUND, não retornar Tenant A

✅ **Suportar pré-tenant (lead sem tenant_id)**
- lead_id presente antes de conversão
- Após conversão, criar vínculo lead_id → tenant_id
- Manter histórico do lead

---

## 🚫 PROIBIÇÕES DURANTE FASE 3

❌ **Não adicionar Firestore ao BillingDomainService**
- BillingDomainService permanece puro
- Não pode importar Firebase/Firestore

❌ **Não implementar worker de publicação**
- Outbox apenas persiste com status PENDING
- Worker será Fase 5

❌ **Não chamar serviços externos**
- Sem Hotmart
- Sem webhooks
- Sem email/SMS/WhatsApp

❌ **Não alterar Fase 1/2 sem defeito**
- Máquinas de estado congeladas
- Eventos de domínio congelados
- BillingDomainService congelado

---

## 📁 ESTRUTURA DE ARQUIVOS (Planejada)

```
services/
├─ billing_application_service.py          (450 linhas)
│  └─ BillingApplicationService (orquestração)

repositories/
├─ __init__.py
├─ commercial_aggregate_repository.py      (150 linhas, interface)
├─ processed_event_repository.py            (150 linhas, interface)
├─ commercial_audit_repository.py           (100 linhas, interface)
├─ commercial_outbox_repository.py          (100 linhas, interface)
├─ billing_unit_of_work.py                  (100 linhas, interface)
│
└─ infra/
   ├─ __init__.py
   ├─ firestore_commercial_aggregate_repo.py    (250 linhas)
   ├─ firestore_processed_event_repo.py         (250 linhas)
   ├─ firestore_commercial_audit_repo.py        (150 linhas)
   ├─ firestore_commercial_outbox_repo.py       (150 linhas)
   └─ firestore_billing_unit_of_work.py         (200 linhas)

tests/comercial/
├─ test_billing_application_service.py     (80 testes unitários)
├─ test_billing_application_firebase.py    (40 testes integração real)
└─ test_idempotency_cross_tenant.py         (20 testes segurança)
```

**Total Planejado:**
- ~1,800 linhas código implementação
- ~140 testes (80 unitários + 40 integração + 20 segurança)

---

## 🧪 TESTES OBRIGATÓRIOS

### Unitários (80 testes)
✅ Evento novo processado com sucesso
✅ Evento duplicado já processado
✅ Duplicado em PROCESSING (race condition)
✅ Duplicado com payload_hash diferente
✅ Falha de domínio sem alteração snapshot
✅ Persistência do snapshot
✅ Versionamento incremental
✅ Persistência de auditoria
✅ Persistência de outbox
✅ Rollback por falha na auditoria
✅ Rollback por falha na outbox
✅ Conflito de versão
✅ Retry após conflito
✅ Cross-tenant isolation
✅ Tenant ausente quando obrigatório
✅ Lead pré-tenant válido
✅ Conversão aditiva
✅ Snapshot não mutado
✅ Evento fora de ordem → reconciliação
✅ Idempotência sem duplicar outbox
... (40 mais)

### Integração Firebase Real (40 testes)
✅ E2E com Firestore real
✅ Transação concorrente
✅ Duplicidade simultânea
✅ Falha no meio de transação
✅ Isolamento entre tenants
✅ Leitura após restart
✅ Auditoria append-only (nenhuma update/delete)
✅ Outbox persistida com status PENDING
... (32 mais)

### Segurança Multi-Tenant (20 testes)
✅ Tenant A não lê Tenant B
✅ Tenant A não escreve Tenant B
✅ Cross-tenant event processing rejeitado
✅ Auditoria isolada por tenant
✅ Outbox isolada por tenant
... (15 mais)

---

## 📋 GAPS CONTRATUAIS REGISTRADOS

### Gap #1: Caminho Pré-Tenant
- **Status:** Bloqueio até clareza contratual
- **Ação Fase 3:** Registrar como `lead_id` field, NOT criar collection

### Gap #2: Timestamps Server vs Application
- **Status:** Será serverTimestamp() para auditoria
- **Ação Fase 3:** Decidir e documentar

### Gap #3: Limite de Transação Firestore (25 writes)
- **Status:** Documentado
- **Ação Fase 3:** 1 evento = 1 outbox entry (não agregado)

---

## ✅ EVIDÊNCIAS FINAIS ESPERADAS

✅ Arquivos criados e alterados (lista)
✅ Modelo de dados definitivo (Collections + fields)
✅ Caminhos Firestore (todos os paths)
✅ Testes: 80 unitários + 40 integração + 20 segurança
✅ Evidência de atomicidade (transação Firestore)
✅ Evidência de controle de concorrência (version conflict handling)
✅ Evidência de idempotência (processed_events query)
✅ Evidência de isolamento multi-tenant (cross-tenant test failure)
✅ Evidência de rollback (transaction abort on error)
✅ Nenhuma importação proibida (grep Firestore apenas em infra)
✅ py_compile sem erros
✅ Git diff do snapshot de código

---

## 🎯 DECISÃO FINAL

**Fase 3 será aprovada quando:**
- ✅ Todos 140 testes PASS
- ✅ Atomicidade garantida por transação Firestore
- ✅ Idempotência verificada por processed_events
- ✅ Isolamento multi-tenant testado
- ✅ Sem importações proibidas
- ✅ Gaps contratuais documentados

**Bloqueadores:**
- Se testes falharem: investigar e corrigir
- Se gaps reais encontrados: documentar e escalar para Produto

---

**FASE3_PERSISTENCIA_AUDITORIA_IDEMPOTENCIA.md**
