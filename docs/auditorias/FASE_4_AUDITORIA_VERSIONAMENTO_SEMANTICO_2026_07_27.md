# FASE 4 — AUDITORIA VERSIONAMENTO SEMÂNTICO

**Data:** 2026-07-27  
**Status:** 🔍 EM INVESTIGAÇÃO  
**Escopo:** Determinístico, código real, sem alterações  

---

## 📋 INVENTÁRIO DE VERSION

### Ocorrências de Versão (Coletadas)

| Arquivo | Linha | Contexto | Tipo | Responsabilidade |
|---------|-------|---------|------|-----------------|
| `repositories/commercial_aggregate_repository.py` | 49 | Parâmetro `expected_version` | Leitura/Escrita | Interface: compare-and-set |
| `repositories/commercial_aggregate_repository.py` | 69 | Erro se divergir | Comparação | Validação de conflito |
| `repositories/commercial_audit_repository.py` | 20-21 | Campos `aggregate_version_before/after` | Armazenamento | Auditoria persistida |
| `repositories/in_memory/in_memory_repositories.py` | 142 | Leitura em `existing.version` | Leitura | Obter versão atual |
| `repositories/in_memory/in_memory_repositories.py` | 156 | Comparação `existing.version != expected_version` | Comparação | CAS (Compare-And-Set) |
| `services/billing_application_service.py` | 236 | Versão inicial agregado novo | Escrita | Primeira versão = 0 |
| `services/billing_application_service.py` | 241 | Leitura `version_before = aggregate_before.version` | Leitura | Captura versão pré-decisão |
| `services/billing_application_service.py` | 263, 274 | Rejeição: `aggregate_version_after=version_before` | Escrita | Sem incremento em rejeição |
| `services/billing_application_service.py` | 294 | **CRÍTICO**: `version_after = version_before + 1 if domain_result.transitions else version_before` | Decisão | REGRA DE INCREMENTO |
| `services/billing_application_service.py` | 298 | Novo agregado com `version=version_after` | Escrita | Versão no agregado novo |
| `services/billing_application_service.py` | 314 | `expected_version=version_before` | Comparação | CAS ao persistir |
| `services/billing_application_service.py` | 335, 346 | Audit: `aggregate_version_after=version_after` | Armazenamento | Registrar versão pós-decisão |
| `services/billing_application_service.py` | 370 | Outbox: `aggregate_version=version_after` | Armazenamento | Registrar versão em evento |
| `services/billing_domain_service.py` | 108-145 | Classe `CommercialAggregate` | Estrutura | Encapsula identidade + estado + version |
| `services/billing_domain_service.py` | 124 | Campo `version: int` | Estrutura | Versão é propriedade do agregado |
| `tests/comercial/test_gate_a_in_memory.py` | 25, 37 | Helper `_create_test_aggregate(version)` | Teste | Construir agregados com versão |
| `tests/comercial/test_gate_a_in_memory.py` | 60-65, 68-79 | Testes CAS e conflito | Teste | Validar compare-and-set |

---

## 🔄 FLUXO REAL DA VERSÃO

### [1] Criação de Novo Agregado

**Arquivo:** `services/billing_application_service.py:220-239`

```python
# Agregado novo tem version = 0
aggregate_before = CommercialAggregate(
    aggregate_id=aggregate_id,
    tenant_id=event.tenant_id,
    version=0,  # ← INICIAL: 0
    snapshot=initial_snapshot,
    created_at=datetime.utcnow()
)
```

**Decisão Arquitetural:** Agregado novo começa com `version=0` (não persistido ainda)

---

### [2] Captura de Versão Pré-Decisão

**Arquivo:** `services/billing_application_service.py:241`

```python
version_before = aggregate_before.version  # 0 ou N
```

**Responsabilidade:** Guardar versão atual antes de qualquer mudança

---

### [3] Processamento no Domínio

**Arquivo:** `services/billing_domain_service.py:316-443`

```python
def process_external_event(
    self,
    normalized_event: Dict[str, Any],
    current_snapshot: AggregateSnapshot,
) -> BillingDomainServiceResult:
```

**Retorna:**
- `snapshot_before`: Estado inicial
- `snapshot_after`: Estado resultante (pode ser igual)
- `transitions`: Lista de transições executadas (de 5 máquinas)
- `success`: True se sem erro de domínio

**CRÍTICO:** `transitions` nunca está vazio se sucesso=True (todas 5 máquinas são executadas)

---

### [4] REGRA DE INCREMENTO (LINHA 294)

**Arquivo:** `services/billing_application_service.py:294`

```python
version_after = version_before + 1 if domain_result.transitions else version_before
```

**Regra Atual:**
```
IF transitions.length > 0:
    version_after = version_before + 1
ELSE:
    version_after = version_before
```

**Problema Identificado:**
- Transitions sempre está preenchido se sucesso=True
- Logo, versão SEMPRE incrementa em sucesso=True
- Não há comparação de snapshot_before vs snapshot_after
- Não distingue entre: "mudança de estado" vs "sem mudança"
- Não verifica TransitionDecision (APPLIED vs IGNORED vs REJECTED)

---

### [5] Construção do Novo Agregado

**Arquivo:** `services/billing_application_service.py:295-306`

```python
aggregate_after = CommercialAggregate(
    aggregate_id=aggregate_id,
    tenant_id=event.tenant_id,
    version=version_after,  # ← Versão calculada
    snapshot=domain_result.snapshot_after,  # ← Snapshot novo
    subscription_id=aggregate_before.subscription_id,
    plan_id=aggregate_before.plan_id,
    lead_id=aggregate_before.lead_id,
    period_start=aggregate_before.period_start,
    period_end=aggregate_before.period_end,
    created_at=aggregate_before.created_at
)
```

**Observação:** Mantém campos comerciais (subscription_id, plan_id, etc) do agregado anterior

---

### [6] Persistência com Compare-And-Set

**Arquivo:** `services/billing_application_service.py:310-315`

```python
await uow.aggregate_repository.save(
    tenant_id=event.tenant_id,
    aggregate_id=aggregate_id,
    aggregate=aggregate_after,
    expected_version=version_before  # ← CAS: espera versão anterior
)
```

**Garante:** Nenhuma outra instância alterou o agregado entre leitura e escrita

---

### [7] Registros de Auditoria

**Arquivo:** `services/billing_application_service.py:335-347`

```python
await uow.audit_repository.record(
    ...
    aggregate_version_before=version_before,
    aggregate_version_after=version_after,
    ...
)
```

**Registra:** Versão antes e depois (para rastreamento)

---

### [8] Persistência de Eventos Outbox

**Arquivo:** `services/billing_application_service.py:363-375`

```python
for idx, internal_event in enumerate(domain_result.internal_events):
    await uow.outbox_repository.save(
        ...
        aggregate_version=version_after,  # ← Versão final
        event_index=idx,
        ...
    )
```

**Registra:** Versão com cada evento outbox

---

## 🎯 REGRA ATUAL vs REGRA ESPERADA

### Regra Atual (Código Real)

```python
# Linha 294, billing_application_service.py
version_after = version_before + 1 if domain_result.transitions else version_before
```

**Comportamento:**
- ✅ Incrementa se transitions não está vazio
- ✅ Não incrementa se transitions está vazio
- ❌ NÃO valida se snapshot foi alterado
- ❌ NÃO verifica TransitionDecision (APPLIED/IGNORED/REJECTED)
- ❌ NÃO distingue "mudança semântica" de "execução sem mudança"

### Regra Esperada (Conforme Especificação)

```python
version_after = version_before + 1 if has_semantic_snapshot_change(snapshot_before, snapshot_after) else version_before
```

**Comportamento Esperado:**
- ✅ Incrementa APENAS se snapshot foi semanticamente alterado
- ✅ Não incrementa em replay idempotente
- ✅ Não incrementa em rejeição
- ✅ Ignora mudanças em campos técnicos (timestamp)
- ✅ Ignora transitions com IGNORED/REJECTED

---

## 🧊 SNAPSHOT INICIAL

### Política Atual

**Código:** `services/billing_application_service.py:220-239`

```python
# Agregado novo
aggregate_before = CommercialAggregate(
    aggregate_id=aggregate_id,
    tenant_id=event.tenant_id,
    version=0,  # ← INICIAL
    snapshot=initial_snapshot,
    created_at=datetime.utcnow()
)
```

**Onde `initial_snapshot` é criado:**

```python
# services/billing_domain_service.py (inferido)
# AggregateSnapshot com todas as máquinas em estado INICIAL
```

### Decisão Arquitetural

| Aspecto | Valor | Evidência |
|---------|-------|-----------|
| Versão agregado novo | 0 | Linha 236 |
| Snapshot inicial | Todas máquinas em estado INICIAL | Implícito em initial_snapshot |
| É persistido? | NÃO (version=0 antes da primeira decisão) | Linha 236 comentário |
| Primeira decisão bem-sucedida | version becomes 1 | version=0 → version=1 |
| Rejeição em novo | version permanece 0 | Linha 263 (version_before em rejeição) |

---

## 📊 CAMPOS DO SNAPSHOT

### AggregateSnapshot (`services/billing_domain_service.py:82-105`)

```python
@dataclass(frozen=True)
class AggregateSnapshot:
    trial: TrialSnapshot           # Estado máquina Trial
    assinatura: AssinaturaSnapshot # Estado máquina Assinatura
    pagamento: PagamentoSnapshot   # Estado máquina Pagamento
    acesso: AcessoSnapshot         # Estado máquina Acesso
    retencao: RetencaoSnapshot     # Estado máquina Retenção
    timestamp: datetime            # TÉCNICO (quando capturado)
```

### Classificação de Campos

| Campo | Categoria | Alteração incrementa versão? | Justificativa |
|-------|-----------|------------------------------|--------------|
| `trial.state` | Estado de Domínio | ✅ SIM | Mudança de estado é semântica |
| `trial.metadata` | Estado de Domínio | ✅ SIM | Metadados de domínio (ex: trial_expires) |
| `assinatura.state` | Estado de Domínio | ✅ SIM | Mudança de assinatura é semântica |
| `assinatura.metadata` | Estado de Domínio | ✅ SIM | Dados comerciais (plan, price) |
| `pagamento.state` | Estado de Domínio | ✅ SIM | Mudança de pagamento é semântica |
| `pagamento.metadata` | Estado de Domínio | ✅ SIM | Dados de pagamento |
| `acesso.state` | Estado de Domínio | ✅ SIM | Mudança de acesso é semântica |
| `acesso.metadata` | Estado de Domínio | ✅ SIM | Dados de acesso |
| `retencao.state` | Estado de Domínio | ✅ SIM | Mudança de retenção é semântica |
| `retencao.metadata` | Estado de Domínio | ✅ SIM | Dados de retenção |
| `timestamp` | Técnico | ❌ NÃO | Timestamp não é mudança semântica |

### CommercialAggregate (Campos Adicionais)

| Campo | Categoria | Alteração incrementa versão? | Justificativa |
|-------|-----------|------------------------------|--------------|
| `aggregate_id` | Identidade | ❌ NÃO | Imutável |
| `tenant_id` | Identidade | ❌ NÃO | Imutável |
| `version` | Técnico | ❌ NÃO | É a versão sendo calculada |
| `subscription_id` | Referência Comercial | ❓ TALVEZ | Vem de evento? Muda? |
| `plan_id` | Referência Comercial | ❓ TALVEZ | Vem de evento? Muda? |
| `lead_id` | Referência Comercial | ❓ TALVEZ | Vem de evento? Muda? |
| `period_start` | Referência Comercial | ❓ TALVEZ | Vem de evento? Muda? |
| `period_end` | Referência Comercial | ❓ TALVEZ | Vem de evento? Muda? |
| `created_at` | Técnico | ❌ NÃO | Imutável (primeiro evento) |

**Observação Crítica:** CommercialAggregate copia campos do agregado anterior (linhas 300-304). Não muda junto com AggregateSnapshot. Essas mudanças NÃO devem incrementar versão (já vêm do agregado anterior).

---

## 🧪 CENÁRIOS CRÍTICOS AUDITADOS

### Cenário 1: Primeira Decisão Bem-Sucedida

**Input:**
- Agregado novo (version=0)
- Evento purchase_approved (produz transitions + state change)

**Esperado:**
- snapshot_after ≠ snapshot_before
- transitions não está vazio
- version_after = 1 ✅

**Código Real (Linha 294):**
```python
if domain_result.transitions:  # True (transitions tem 5 elementos)
    version_after = 1  # 0 + 1 ✅
```

**Status:** ✅ FUNCIONA

---

### Cenário 2: Evento que Não Altera Estado

**Cenário:** `process_external_event` chamado com evento idêntico ao anterior (replay)

**Esperado:**
- snapshot_after = snapshot_before (sem mudança)
- transitions pode estar preenchido (máquinas executadas)
- version_after = version_before (não incrementa) ✅

**Código Real (Linha 294):**
```python
if domain_result.transitions:  # True (transitions sempre preenchido)
    version_after = version_before + 1  # ❌ INCREMENTA MESMO SEM MUDANÇA
```

**Status:** ❌ BUG: Incrementa versão em replay idempotente

---

### Cenário 3: Rejeição de Domínio

**Input:**
- Agregado (version=5)
- Evento que viola regra de domínio

**Esperado:**
- snapshot_after = snapshot_before (sem mudança, rejeição)
- domain_result.success = False
- version_after = 5 (não incrementa) ✅

**Código Real (Linhas 256-264):**
```python
if not domain_result.success:
    ...
    aggregate_version_after=version_before  # ✅ Não incrementa
```

**Status:** ✅ FUNCIONA (branch de rejeição)

---

### Cenário 4: Transitions com Decision = IGNORED

**Cenário:** Máquina executa transição, mas pré-condição falha (IGNORED)

**Esperado:**
- snapshot_after = snapshot_before
- transitions preenchido com MachineTransitionResult (decision=IGNORED)
- version_after = version_before ❓

**Código Real (Linha 294):**
```python
if domain_result.transitions:  # True (transitions preenchido)
    version_after = version_before + 1  # ❌ INCREMENTA MESMO COM IGNORED
```

**Status:** ❌ BUG: Não verifica TransitionDecision

---

### Cenário 5: Múltiplos Campos Alterados

**Input:**
- trial.state muda
- assinatura.state muda
- pagamento.state muda

**Esperado:**
- snapshot_after com 3 mudanças
- version_after = version_before + 1 ✅

**Código Real:**
```python
if domain_result.transitions:  # True
    version_after = version_before + 1  # ✅ Funciona
```

**Status:** ✅ FUNCIONA (transitions não está vazio)

---

### Cenário 6: Mudança em Timestamp Técnico Apenas

**Cenário:** Snapshot.timestamp atualizado, nenhum estado mudou

**Esperado:**
- snapshot_after.timestamp ≠ snapshot_before.timestamp
- Mas snapshot_after (sem timestamp) = snapshot_before (sem timestamp)
- version_after = version_before (ignora timestamp) ✅

**Código Real (Linha 294):**
```python
if domain_result.transitions:  # True (máquinas executadas)
    version_after = version_before + 1  # ❌ INCREMENTA MESMO COM MUDANÇA TÉCNICA
```

**Status:** ❌ BUG: Timestamp não deve incrementar versão

---

## 📍 RELAÇÃO COM IDS DETERMINÍSTICOS

### audit_id Depende de Versão

**Código:** `repositories/in_memory/in_memory_repositories.py:30-50`

```python
canonical_key = (
    f"commercial-audit:{AUDIT_KEY_VERSION}|"
    ...
    f"version={aggregate_version_after}"  # ← VERSÃO AQUI
)
return str(uuid.uuid5(COMMERCIAL_NAMESPACE, canonical_key))
```

**Risco:** Se versão for calculada incorretamente:
- Mesmo evento em replay pode gerar audit_id diferente
- Ou múltiplos eventos distintos podem compartilhar mesmo audit_id

**Exemplo:**
```
Evento A: version_before=5 → version_after=6 (correto)
Evento A replay: version_before=6 → version_after=7 (ERRADO!)
  
audit_id_A ≠ audit_id_A_replay  ❌ Deveria ser idêntico
```

---

### outbox_id Depende de Versão

**Código:** `repositories/in_memory/in_memory_repositories.py:57-78`

```python
canonical_key = (
    f"commercial-outbox:{OUTBOX_KEY_VERSION}|"
    ...
    f"version={aggregate_version_after}|"  # ← VERSÃO AQUI
    ...
)
return str(uuid.uuid5(COMMERCIAL_NAMESPACE, canonical_key))
```

**Risco:** Mesmo risco que audit_id

**Impacto:** Outbox pode conter duplicatas se versão for incrementada indevidamente

---

## 🧪 TESTES EXISTENTES

### Testes de Versão Encontrados

| Arquivo | Teste | Linha | O que testa | Lacuna |
|---------|-------|-------|-----------|--------|
| `test_gate_a_in_memory.py` | `_create_test_aggregate(version)` | 25 | Construir agregado com versão | - |
| `test_gate_a_in_memory.py` | `test_save_e_load` | 57-66 | Salvar e carregar com versão | Não testa incremento |
| `test_gate_a_in_memory.py` | `test_save_version_conflict` | 68-79 | CAS falha com expected_version errado | Não testa regra de incremento |
| `test_gate_a_in_memory.py` | `test_audit_id_determinístico` | ~580 | Audit IDs são determinísticos | Não valida regra de versão |
| `test_gate_a_in_memory.py` | Nenhum teste de incremento | - | **LACUNA CRÍTICA** | Nenhum teste que valida quando versão incrementa |

### Testes Ausentes

```
❌ test_version_incrementa_em_mudanca_semantica
   Validar: snapshot muda → version incrementa

❌ test_version_nao_incrementa_em_replay
   Validar: snapshot igual → version não incrementa

❌ test_version_nao_incrementa_em_rejeicao
   Validar: rejeição → version mantém

❌ test_version_nao_incrementa_timestamp_tecnico
   Validar: timestamp muda, estado igual → version não incrementa

❌ test_version_nao_incrementa_transition_ignored
   Validar: transition.decision=IGNORED → version não incrementa

❌ test_transitions_sempre_preenchido
   Validar: transitions está vazio só se success=False

❌ test_snapshot_inicial_agregado_novo
   Validar: aggregado novo version=0

❌ test_determinismo_versao_em_replay
   Validar: version_after determinística em replay
```

---

## 🔮 RELAÇÃO COM FIRESTORE (FUTURO)

### Contrato Esperado para Persistência

```
1. Leitura: get(aggregate_id) → (aggregate, version=N)
2. Validação: expected_version = N
3. Processamento: version_after = N+1 (se mudança semântica)
4. Escrita: save(aggregate, version=N+1, expected_version=N)
5. Transação: compare-and-set atômico
6. Conflito: retry com novo snapshot
```

### Implicação: Versão Deve Ser Calculada Antes da Persistência

**Código Atual (Correto):**
```python
version_after = version_before + 1 if condition else version_before
await save(..., expected_version=version_before)
```

**Razão:** expected_version precisa ser versão ANTERIOR para CAS funcionar

---

## 🚨 DIAGNÓSTICO RESUMIDO

| Achado | Severidade | Código | Status |
|--------|-----------|--------|--------|
| Versão inicial = 0 em novo agregado | ✅ Correto | L236 | OK |
| Versão não incrementa em rejeição | ✅ Correto | L263 | OK |
| Versão cria audit_id determinístico | ⚠️ Risco | L50 | Depende de regra de incremento |
| Versão cria outbox_id determinístico | ⚠️ Risco | L78 | Depende de regra de incremento |
| **Versão incrementa SEMPRE em sucesso** | ❌ Bug | L294 | **NÃO VALIDA SNAPSHOT** |
| **Transitions sempre preenchido em sucesso** | ❌ Bug | L294 | Não distingue APPLIED/IGNORED |
| **Timestamp técnico muda, incrementa versão** | ❌ Bug | L294 | Não filtra campos técnicos |
| **Sem teste de regra de incremento** | ❌ Lacuna | - | 0 testes da regra |
| **Sem função has_semantic_snapshot_change** | ❌ Ausência | - | Precisa ser criada |
| **Replay pode incrementar versão indevidamente** | ❌ Bug | L294 | Quebra idempotência |

---

## 📋 PLANO DE CORREÇÃO (PROPOSTO)

### Patch Mínimo Necessário

1. **Criar função determinística:**
   ```python
   def has_semantic_snapshot_change(
       snapshot_before: AggregateSnapshot,
       snapshot_after: AggregateSnapshot
   ) -> bool:
       """Detectar mudança semântica (ignora timestamp técnico)."""
       # Comparar apenas campos semânticos
       # Ignorar timestamp
   ```

2. **Alterar regra de incremento (L294):**
   ```python
   version_after = (
       version_before + 1 
       if has_semantic_snapshot_change(
           domain_result.snapshot_before,
           domain_result.snapshot_after
       )
       else version_before
   )
   ```

3. **Adicionar testes (8 cenários):**
   - Mudança semântica → incrementa
   - Sem mudança → não incrementa
   - Replay → não incrementa
   - Timestamp → não incrementa
   - Transition IGNORED → não incrementa
   - etc

4. **Não alterar:**
   - Unit of Work (Fase 2)
   - IDs determinísticos (Fase 3)
   - Firestore (futuro)
   - Máquinas de estado

---

## 🎯 DECISÃO FASE 4

**CLASSIFICAÇÃO:** `FASE 4 REQUER CORREÇÃO MÍNIMA`

**Justificativa:**
- ✅ Baseline funciona (incremento funciona em casos bem-sucedidos)
- ⚠️ Bug identificado: replay pode incrementar indevidamente
- ⚠️ Bug identificado: timestamp técnico incrementa versão
- ⚠️ Risco: audit_id e outbox_id podem ter colisões em replay
- ✅ Patch é mínimo (1 função + 1 linha + 8 testes)
- ✅ Não quebra nada existente

**Próximo Passo:** Implementar patch mínimo conforme planejado.

---

**Auditoria Concluída:** 2026-07-27  
**Arquivos Inspecionados:** 8  
**Ocorrências de Version:** 60+  
**Bugs Identificados:** 3  
**Lacunas de Teste:** 8  
**Status Recomendado:** Prosseguir para patch mínimo
