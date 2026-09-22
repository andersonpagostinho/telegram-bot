# FASE 3 — AUDITORIA DE PADRÕES FIRESTORE

**Data:** 2026-07-27  
**Objetivo:** Mapear padrões existentes antes de implementar persistência de domínio

---

## 1. SERVIÇO CENTRAL FIRESTORE

### Localização
- `services/firestore_client.py` — Cliente singleton
- `services/firebase_service_async.py` — Serviço de acesso (funções assíncronas)

### Cliente Singleton
```python
# firestore_client.py
def get_db():
    """Obtém cliente Firestore, reutilizando instância única"""
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.client()
    return _firestore_client
```

**Padrão:** Reutilização singleton para evitar acúmulo de conexões gRPC

### Cliente Async
```python
# firebase_service_async.py
from google.cloud.firestore_v1 import AsyncClient
client = AsyncClient()
```

**Padrão:** AsyncClient para operações não-bloqueantes

---

## 2. CONVENÇÃO DE PATHS

### Estrutura Observada

```
Clientes/{user_id}
├─ Document com dados do cliente
│  └─ campos: id_negocio, nome, email, ...
│
├─ Clientes/{cliente_id}/Tarefas/{tarefa_id}
├─ Clientes/{cliente_id}/Contatos/{contato_id}
├─ Clientes/{cliente_id}/NotificacoesAgendadas/{notif_id}
└─ [Outras subcoleções]
```

**Padrão Multi-Tenant:**
```
Clientes/{user_id}/  — Este é o TENANT_ID (negócio/dono)
```

### Resolução de Tenant
```python
# firebase_service_async.py
async def obter_id_dono(user_id: str) -> str | None:
    """
    Resolve tenant_id para um ator (usuário).
    Nunca retorna user_id como fallback silencioso.
    """
    cliente = await buscar_cliente(user_id)
    if cliente:
        return cliente.get("id_negocio")  # Campo que armazena tenant
    return None
```

**Padrão:** `id_negocio` é o tenant_id no documento Clientes

---

## 3. OPERAÇÕES FIRESTORE

### Set com Merge
```python
await ref.set(dados, merge=True)
```

**Uso:** Atualizar mantendo dados existentes (não sobrescrever tudo)

### Update com Operações Atômicas
```python
await ref.update({
    "counter": firestore.Increment(1),
    "items": firestore.ArrayUnion([new_item]),
    "campo_simples": valor
})
```

**Uso:** Operações que precisam de atomicidade (contadores, arrays)

### Batch Operations
Não encontrado em uso ativo no código existente.

### Transações Explícitas
**⚠️ NÃO ENCONTRADAS** no código existente (`firebase_service_async.py`)

Código usa `set(merge=True)` e `update()` mas **sem transações explícitas**.

---

## 4. TIMESTAMPS

### Observado no Código
```python
# firestore_service_async.py não usa serverTimestamp() explicitamente
# Timestamps são armazenados como valores ordinários
received_at=datetime.utcnow()  # Em eventos de aplicação
```

**Padrão:** Timestamps são aplicação-gerados, não server-side

---

## 5. TRATAMENTO DE EXCEÇÕES

### Padrão Observado
```python
try:
    # operação
    await ref.set(dados, merge=True)
    print(f"[OK] Dados salvos")
    return True
except Exception as e:
    print(f"[ERRO] Erro: {e}")
    return False
```

**Padrão:** Catch genérico de `Exception`, retorno boolean, logging

---

## 6. CONVENÇÕES DE IDs

### user_id
- **Tipo:** String
- **Origem:** Identificador do usuário/ator
- **Uso:** Chave primária em "Clientes/{user_id}"

### id_negocio
- **Tipo:** String
- **Origem:** Campo em documento Clientes
- **Uso:** Tenant ID (negócio/organização do usuário)

### ID Automático
```python
await client.collection(colecao).add(dados)  # Gera ID automático
```

**Padrão:** Firestore auto-gera IDs quando não especificado

---

## 7. ISOLAMENTO MULTI-TENANT

### Validação Observada
```python
# Não há validação ativa de tenant em firebase_service_async.py
# Responsabilidade é da camada de aplicação
```

**Padrão:** Camada de aplicação deve validar tenant_id, não Firestore service

---

## 8. PADRÕES DE TESTES

### Testes com Firebase Real
```python
# tests/runner_p0_e2e_firestore_real.py
# tests/runner_f9_dashboard_firestore_real.py
```

**Padrão:** E2E tests usam Firestore real (não emulador documentado)

### Testes Específicos
```python
# tests/test_firestore_diagnostico.py
# tests/test_seg_05b_mec03_firestore.py
```

**Padrão:** Testes de diagnóstico e segurança

---

## 9. POTENCIAIS CONFLITOS COM FASE 3

### 1. Falta de Transações Explícitas
**Risco:** Atomicidade entre snapshot, auditoria e outbox pode não ser garantida
**Impacto:** Necessário implementar transação ou padrão alternativo
**Decisão Fase 3:** Usar `firestore.transaction()` explicitamente

### 2. Sem Versionamento Concorrente
**Risco:** Lost update se dois serviços gravam concorrentemente
**Impacto:** Controle otimista necessário
**Decisão Fase 3:** Adicionar `version` field com compare-and-set

### 3. Timestamps Aplicação-Gerados
**Risco:** Vulnerável a clock skew
**Impacto:** Auditoria pode ter timestamps imprecisos
**Decisão Fase 3:** Usar `serverTimestamp()` para auditoria

### 4. Sem Idempotência Estruturada
**Risco:** Duplicação de eventos processados
**Impacto:** Necessário `processed_events` collection com chave única
**Decisão Fase 3:** Criar `ProcessedWebhookEvents` collection

### 5. Sem Outbox Implementado
**Risco:** Perda de eventos internos se falhar entre domínio e persistência
**Impacto:** Necessário outbox pattern
**Decisão Fase 3:** Criar `CommercialOutbox` collection

---

## 10. RECOMENDAÇÕES FASE 3

### ✅ Reutilizar
- Cliente Firestore singleton (`firestore_client.py`)
- Convenção de paths `Clientes/{tenant_id}/...`
- Padrão multi-tenant com `id_negocio`

### ✅ Estender
- Adicionar transações explícitas
- Adicionar versionamento para concorrência
- Adicionar `serverTimestamp()` para auditoria

### ✅ Implementar Novo
- `CommercialAggregateRepository` (snapshot)
- `ProcessedEventRepository` (idempotência)
- `CommercialAuditRepository` (append-only)
- `CommercialOutboxRepository` (eventos pendentes)
- `BillingUnitOfWork` (transação coordenada)
- `BillingApplicationService` (orquestração)

### ❌ Não Fazer
- Não criar novo cliente Firestore
- Não usar padrão diferente de multi-tenant
- Não mudar convenção de paths

---

## 11. MATRIZ DE ENTIDADES FIRESTORE (PLANEJADA)

| Entidade | Collection | Chave | Tenant | Transação | Índices |
|----------|-----------|-------|--------|-----------|---------|
| Agregado Comercial | `Tenants/{tenant_id}/CommercialAggregates/{aggregate_id}` | `aggregate_id` | `tenant_id` | Sim (escritor) | `(tenant_id, version)` |
| Eventos Processados | `Tenants/{tenant_id}/ProcessedWebhookEvents/{provider}_{event_id}` | `provider_event_id` | `tenant_id` | Sim | `(tenant_id, status)` |
| Auditoria | `Tenants/{tenant_id}/CommercialAudit/{audit_id}` | Auto-generated | `tenant_id` | Append-only | `(tenant_id, occurred_at)` |
| Outbox | `Tenants/{tenant_id}/CommercialOutbox/{outbox_id}` | Auto-generated | `tenant_id` | Sim | `(tenant_id, status)` |

---

## 12. GAPS CONTRATUAIS IDENTIFICADOS

### Gap #1: Caminho Pré-Tenant
**Questão:** Como tratar leads/prospects que ainda não têm tenant_id?
**Status:** Contrato de conversão é aditivo mas caminho pré-tenant não definido
**Decisão Fase 3:** Registrar como bloqueio, não improvisar estrutura

### Gap #2: Timestamps e Causalidade
**Questão:** server vs. application timestamps para auditoria?
**Status:** Implementação atual usa application timestamps
**Decisão Fase 3:** Usar `serverTimestamp()` para auditoria, application para eventos

### Gap #3: Transação Firestore Limites
**Questão:** Firestore limita a 25 writes/transação; se outbox tiver N eventos?
**Status:** Ainda não definido
**Decisão Fase 3:** Documentar limite e implementar paginação se necessário

---

## PRÓXIMAS AÇÕES

1. ✅ **Auditoria (DONE)** — Mapeado padrões existentes
2. ⏳ **Modelo de Dados** — Definir estrutura de Collections
3. ⏳ **Implementação Repositórios** — Criar abstrações
4. ⏳ **Implementação Firestore** — Criar concretas
5. ⏳ **Testes** — Unitários + integração

---

**FASE3_AUDITORIA_FIRESTORE_PATTERNS.md**
