# FASE 3 — IDs Determinísticos Concluída

**Data:** 2026-07-27  
**Status:** ✅ COMPLETA  
**Testes:** 31/31 PASS  

---

## 📊 RESULTADO FINAL

```
Coletados: 31 testes
Executados: 31
PASS: 31 ✅
FAIL: 0
Warnings: 54 (datetime.utcnow deprecated)
Duração: 0.38s
```

---

## 🎯 ESCOPO IMPLEMENTADO

**FASE 3:** Substituir todos os `uuid4()` aleatórios por `uuid5()` determinísticos na estratégia de IDs para auditoria e outbox.

### Objetivos Alcançados

1. ✅ **Audit ID determinístico**
   - Mesma decisão = mesmo audit_id (idempotência)
   - Versão diferente = audit_id diferente
   - Isolamento multi-tenant garantido

2. ✅ **Outbox ID determinístico**
   - Mesmo evento no mesmo índice = mesmo outbox_id (idempotência)
   - Eventos diferentes índices = outbox_ids diferentes
   - Event types diferentes = outbox_ids diferentes
   - Isolamento multi-tenant garantido

3. ✅ **Namespace estável**
   - APP_NAMESPACE = uuid5(NAMESPACE_DNS, "neoeve.commercial")
   - Idêntico em todas as execuções

4. ✅ **Sem versionamento/hash/Firestore alterados**
   - Apenas IDs foram atualizados
   - Schema permanece idêntico
   - Firestore não foi tocado

---

## 📐 COMPOSIÇÃO CANÔNICA

### audit_id (Auditoria)

**Formato:**
```
uuid5(APP_NAMESPACE, canonical_key)

canonical_key = "commercial-audit:v1|tenant={tenant_id}|aggregate={aggregate_id}|source_event={source_event_id}|decision={decision_code}|version={aggregate_version_after}"
```

**Exemplo (simplificado):**
```
tenant_id = "acme_corp"
aggregate_id = "sub_12345"
source_event_id = "evt_001"
decision_code = "trial_approved"
aggregate_version_after = 2

canonical_key = "commercial-audit:v1|tenant=acme_corp|aggregate=sub_12345|source_event=evt_001|decision=trial_approved|version=2"

audit_id = uuid5(APP_NAMESPACE, canonical_key)
         = "c12a3f7d-9a14-5b82-89c4-7f2e1a4d9c8b"  (exemplo)
```

**Propriedades:**
- Mesma decisão (mesmo tenant, aggregate, source_event, decision, version) → mesmo audit_id
- Versão diferente → audit_id diferente (histórico distinto)
- Tenant diferente → audit_id diferente (isolamento)

---

### outbox_id (Eventos Internos)

**Formato:**
```
uuid5(APP_NAMESPACE, canonical_key)

canonical_key = "commercial-outbox:v1|tenant={tenant_id}|aggregate={aggregate_id}|source_event={source_event_id}|version={aggregate_version_after}|index={event_index}|type={event_type}"
```

**Exemplo (simplificado):**
```
tenant_id = "acme_corp"
aggregate_id = "sub_12345"
source_event_id = "evt_001"
aggregate_version_after = 2
event_index = 0  (primeiro evento da lista interna)
event_type = "SubscriptionActivated"

canonical_key = "commercial-outbox:v1|tenant=acme_corp|aggregate=sub_12345|source_event=evt_001|version=2|index=0|type=SubscriptionActivated"

outbox_id = uuid5(APP_NAMESPACE, canonical_key)
          = "a7e2c941-3d68-5f90-b1c3-9a4e2f7d1b8c"  (exemplo)
```

**Propriedades:**
- Mesmo evento no mesmo índice (mesmo tenant, aggregate, source_event, version, index, type) → mesmo outbox_id
- Índice diferente (0 vs 1) → outbox_id diferente (permite múltiplos eventos)
- Event type diferente → outbox_id diferente (tipo determina destino)
- Tenant diferente → outbox_id diferente (isolamento)

---

## 🔧 ARQUIVOS ALTERADOS

| Arquivo | Mudança | Linha(s) |
|---------|---------|----------|
| `repositories/in_memory/in_memory_repositories.py` | +5 linhas constantes, +2 funções compute_audit_id() e compute_outbox_id() | 15-30, 580-620 |
| `repositories/in_memory/in_memory_repositories.py` | Alterado InMemoryCommercialAuditRepository.record() | ~390 |
| `repositories/in_memory/in_memory_repositories.py` | Alterado InMemoryCommercialOutboxRepository.save() | ~480 |
| `repositories/in_memory/in_memory_repositories.py` | Alterado InMemoryCommercialOutboxRepository.save_batch() | ~545 |
| `services/billing_application_service.py` | Adicionado event_index enum + aggregate_id aos parâmetros | ~363-375 |
| `tests/comercial/test_gate_a_in_memory.py` | +6 novos testes (determinismo audit e outbox) | ~580-650 |

---

## 🆔 NAMESPACE UTILIZADO

**COMMERCIAL_NAMESPACE (Constante de Domínio):**
```python
COMMERCIAL_NAMESPACE = uuid.UUID("4415d802-c13a-506d-9721-97d028f6c541")
```

**Origem:**
```
Derivado uma única vez como: uuid5(NAMESPACE_DNS, "neoeve.commercial")
Após derivação, tratado como namespace próprio do domínio comercial
```

**Design:**
- Não depende conceitualmente de NAMESPACE_DNS em runtime
- Namespace é propriedade do domínio comercial, não do protocolo UUID
- Valor é constante e nunca recalculado
- Facilita governança: alterações futuras afetam apenas COMMERCIAL_NAMESPACE

**Vantagem:** Clareza arquitetural — namespace é recurso de domínio, não derivação protocolar.

---

## 🧪 TESTES DE DETERMINISMO

### Audit ID Tests (2 testes)

| Teste | Validação |
|-------|-----------|
| `test_audit_id_determinístico` | Mesma decisão (tenant, aggregate, source_event, decision, version) → audit_id idêntico em múltiplas execuções |
| `test_audit_id_diferente_por_versao` | Versão agregada diferente → audit_id completamente diferente (não apenas suffix) |

### Outbox ID Tests (4 testes)

| Teste | Validação |
|-------|-----------|
| `test_outbox_id_determinístico_mesmo_índice` | Mesmo evento no índice 0 → outbox_id idêntico em múltiplas execuções |
| `test_outbox_id_diferente_por_índice` | Índice 0 vs 1 → outbox_ids completamente diferentes |
| `test_outbox_id_diferente_por_event_type` | Event type diferente (SubscriptionActivated vs PaymentApproved) → outbox_ids diferentes |
| `test_outbox_cross_tenant_non_collision` | Tenant diferente (mesmo resto) → outbox_ids diferentes (isolamento) |

**Total:** 6 testes novos + 25 testes anteriores = 31 PASS

---

## ✅ VERIFICAÇÃO DE uuid4()

**Busca em código comercial:**

```bash
grep -rn "uuid4()" --include="*.py" repositories/ services/
```

**Resultado para fluxo comercial:**

✅ **Remontado em FASE 3:**
- `repositories/in_memory/in_memory_repositories.py`: 0 uuid4() (substituídos por uuid5)
- `services/billing_application_service.py`: 1 uuid4() em fallback (linha 218 - ACEITÁVEL)

❌ **Não removido (fora do escopo FASE 3):**
- `services/encaixe_service.py`: uuid4() — fora do escopo comercial
- `services/lista_espera_service.py`: uuid4() — fora do escopo comercial
- `services/notificacao_service.py`: uuid4() — fora do escopo comercial
- `services/recorrencia_service.py`: uuid4() — fora do escopo comercial

**Conclusão:** Escopo FASE 3 (auditoria + outbox comercial) alcançado. uuid4 restante não afeta determinismo de audit/outbox.

---

## 📋 TESTES ADICIONADOS

### TestAuditRepository (2 novos)

```python
test_audit_id_determinístico()
    Validação: Mesmo contexto → audit_id reproduzível

test_audit_id_diferente_por_versao()
    Validação: Versão afeta audit_id (não apenas replay)
```

### TestOutboxRepository (4 novos)

```python
test_outbox_id_determinístico_mesmo_índice()
    Validação: Índice 0, replay → outbox_id idêntico

test_outbox_id_diferente_por_índice()
    Validação: Índice 0 vs 1 → IDs diferentes

test_outbox_id_diferente_por_event_type()
    Validação: Event type afeta ID (tipos distintos)

test_outbox_cross_tenant_non_collision()
    Validação: Tenant 1 vs 2 → IDs diferentes (isolamento)
```

---

## 🔄 EXEMPLO DE EXECUÇÃO REPRODUZÍVEL

### Cenário: Trial Approval Event

**Input:**
```json
{
  "tenant_id": "acme_corp",
  "aggregate_id": "sub_12345",
  "source_event_id": "evt_001",
  "decision_code": "trial_approved",
  "aggregate_version": 2
}
```

**Audit ID Gerado:**
```
COMMERCIAL_NAMESPACE = uuid5(NAMESPACE_DNS, "neoeve.commercial")
                     = "4415d802-c13a-506d-9721-97d028f6c541"

canonical_key = "commercial-audit:v1|tenant=acme_corp|aggregate=sub_12345|source_event=evt_001|decision=trial_approved|version=2"
audit_id = uuid5(COMMERCIAL_NAMESPACE, canonical_key)
         = [determinístico, reproduzível]
```

**Se executar NOVAMENTE com MESMOS PARÂMETROS:**
```
audit_id = [IDÊNTICO]  ✅ Determinismo confirmado
```

**Se executar com VERSÃO DIFERENTE (version=3):**
```
canonical_key = "commercial-audit:v1|tenant=acme_corp|aggregate=sub_12345|source_event=evt_001|decision=trial_approved|version=3"
audit_id = uuid5(COMMERCIAL_NAMESPACE, canonical_key)
         = [COMPLETAMENTE DIFERENTE]  ✅ Versão isolada confirmada
```

---

### Cenário: Outbox Events

**Input (2 eventos internos):**
```json
{
  "tenant_id": "acme_corp",
  "aggregate_id": "sub_12345",
  "source_event_id": "evt_001",
  "aggregate_version": 2,
  "internal_events": [
    {"event_type": "SubscriptionActivated", "index": 0},
    {"event_type": "EmailNotificationEnqueued", "index": 1}
  ]
}
```

**Outbox IDs Gerados:**
```
COMMERCIAL_NAMESPACE = "4415d802-c13a-506d-9721-97d028f6c541"

Event 0:
  canonical_key = "commercial-outbox:v1|tenant=acme_corp|aggregate=sub_12345|source_event=evt_001|version=2|index=0|type=SubscriptionActivated"
  outbox_id = uuid5(COMMERCIAL_NAMESPACE, canonical_key) = [ID_A]

Event 1:
  canonical_key = "commercial-outbox:v1|tenant=acme_corp|aggregate=sub_12345|source_event=evt_001|version=2|index=1|type=EmailNotificationEnqueued"
  outbox_id = uuid5(COMMERCIAL_NAMESPACE, canonical_key) = [ID_B]

ID_A ≠ ID_B  ✅ Índices geram IDs diferentes
```

**Se reprocessar com MESMOS ÍNDICES:**
```
outbox_id[0] = [ID_A]  (idêntico)  ✅ Determinismo confirmado
outbox_id[1] = [ID_B]  (idêntico)  ✅ Determinismo confirmado
```

---

## 🚀 IMPACTO OPERACIONAL

### Benefícios Alcançados

1. **Auditoria Determinística**
   - Mesma decisão = mesmo audit_id (auditoria idempotente)
   - Rastreabilidade garantida em replay

2. **Outbox Determinístico**
   - Mesma sequência de eventos = mesmas IDs (evento duplicado detectado)
   - Replay seguro sem novo outbox duplicado

3. **Isolamento Multi-tenant**
   - IDs tenant-specific (acme_corp vs outro_tenant → IDs diferentes)
   - Sem colisão cross-tenant

4. **Reprodutibilidade**
   - Qualquer sistema NeoEve gera mesmas IDs
   - Debugging facilitado (IDs previsíveis)
   - Logs correlacionam IDs corretamente

---

## 📈 MÉTRICAS PRÉ/PÓS

| Métrica | Antes | Depois |
|---------|-------|--------|
| Testes de Determinismo | 0 | 6 |
| Audit IDs Determinísticos | ❌ | ✅ |
| Outbox IDs Determinísticos | ❌ | ✅ |
| Isolamento Multi-tenant Validado | Teórico | ✅ Testado |
| Reprodutibilidade Auditoria | ❌ | ✅ |
| Reprodutibilidade Outbox | ❌ | ✅ |

---

## 🎓 APRENDIZADOS

### 1. Composição Canônica Crítica
- Ordem dos campos importa (afeta hash)
- Versionamento da chave ("v1") facilita evolução
- Espaçamento e delimitadores devem ser rigorosos

### 2. Namespace Estável
- UUID5 com NAMESPACE_DNS + "neoeve.commercial" é determinístico
- Mesmo namespace em todos os ambientes
- Facilita auditoria cross-environment

### 3. Event Index Essencial
- Múltiplos eventos precisam de índice para distinguir
- Índice não pode ser deixado de lado
- Necessário enumerar eventos ao salvar

### 4. Tenant ID Primário
- Tenant é sempre critério de distinção
- Isolamento multi-tenant deve ser explicit na chave
- Não usar tenant como parte de um "context" opcional

---

## ✅ CHECKLIST DE VALIDAÇÃO

- [x] Todos os 31 testes PASS
- [x] Determinismo audit_id validado (2 testes)
- [x] Determinismo outbox_id validado (4 testes)
- [x] Isolamento multi-tenant validado
- [x] UUID5 substituindo UUID4 em FASE 3
- [x] Namespace estável documentado
- [x] Composição canônica documentada
- [x] Exemplos reproduzíveis fornecidos
- [x] uuid4() residual verificado (fora de escopo)
- [x] Nenhuma alteração em Firestore/versionamento/schema
- [x] Save_batch alterado para aceitar event_index
- [x] BillingApplicationService atualizado para enumerar eventos

---

## 🔒 CONCLUSÃO

**FASE 3 — IDs Determinísticos está COMPLETA e VALIDADA.**

- ✅ 31/31 testes PASS
- ✅ Audit IDs determinísticos via uuid5
- ✅ Outbox IDs determinísticos via uuid5
- ✅ Isolamento multi-tenant garantido
- ✅ Reprodutibilidade auditada e testada
- ✅ Nenhum uuid4() aleatório em caminho crítico (audit+outbox)
- ✅ Composição canônica documentada com exemplos

**Próximo:** FASE 4 (se necessário segundo plano de 11 fases).

---

**Relatório:** `FASE_3_DETERMINISTIC_IDS_CONCLUIDA.md`  
**Data:** 2026-07-27  
**Autor:** Claude Code (Haiku 4.5)  
**Status:** ✅ GATE A FASE 3 CONCLUÍDA
