# FASE 3 — GATES EXPLÍCITOS E FLUXO TRANSACIONAL

**Data:** 2026-07-27  
**Decisão:** Caminhos escolhidos; Fluxo transacional formalizado; Gates definidos  
**Status:** Planejamento → Implementação governada por gates  

---

## 🎯 DECISÃO FORMAL: PATHS FIRESTORE

**Baseado em:** ADR_001_COMMERCIAL_PATHS_STRATEGY.md

**Decisão:** ✅ **OPÇÃO A** — `Clientes/{tenant_id}/Comercial`

**Justificativa:**
- Reutiliza raiz já operacionalizada
- Menor risco de duplicação de identidade
- Compatibilidade zero-ruptura
- Índices simples em subcoleção
- Backups já integrados

**Estrutura Firestore Definitiva:**

```
Clientes/{tenant_id}/
├─ [Tenant document: id_negocio, nome, estado]
├─ Comercial/{aggregate_id}            ← Novo
│  └─ [Snapshot: trial_state, assinatura_state, version, ...]
├─ ProcessedWebhookEvents/{id}         ← Novo
│  └─ [Dedup: provider, provider_event_id, status, ...]
├─ CommercialAudit/{audit_id}          ← Novo
│  └─ [Append-only: transitions, states_before/after, ...]
├─ CommercialOutbox/{outbox_id}        ← Novo
│  └─ [Pending outbox: event_type, status=PENDING, ...]
├─ Tarefas/{tarefa_id}                 ← Existente
├─ Contatos/{contato_id}               ← Existente
└─ NotificacoesAgendadas/{notif_id}    ← Existente
```

**Índices Requeridos:**

| Collection | Índice | Tipo |
|-----------|--------|------|
| Comercial | `(updated_at)` | Simples |
| Comercial | `(version)` | Simples |
| ProcessedWebhookEvents | `(provider, provider_event_id)` | Composto |
| ProcessedWebhookEvents | `(status)` | Simples |
| CommercialAudit | `(occurred_at)` | Simples |
| CommercialOutbox | `(publication_status)` | Simples |

**Gap Pré-Tenant:** Bloqueado para Fase 3 (definição contratual pendente)

---

## ⚡ FLUXO TRANSACIONAL OBRIGATÓRIO

### Invariante Fundamental

> **IDEMPOTÊNCIA E PERSISTÊNCIA DEVEM SER ATÔMICAS**
> 
> Check de duplicidade + decisão de domínio + persistência = MESMA TRANSAÇÃO
> 
> Não permitir: check fora da transação → persistência em transação separada

### Fluxo Completo (Ordem Obrigatória)

```
webhook_payload (entrada)
    ↓
[1] BillingApplicationService.process_event()
    ↓
[2] Abrir transação Firestore
    ├─ TRANSAÇÃO COMEÇA AQUI
    ├─ Sem modificações fora deste escopo
    └─ Todo rollback descarta TUDO atomicamente
    ↓
[3] Validar envelope (sem estado)
    ├─ Verificar campos obrigatórios: correlation_id, event_type, received_at, tenant_id
    ├─ Verificar tipos de dados
    └─ Falha → DESCARTAR (erro 400)
    ↓
[4] ProcessedEventRepository.check_and_load()
    ├─ Buscar: (tenant_id, provider, provider_event_id)
    ├─ Se existe com status PROCESSED
    │  └─ Retornar resultado armazenado + commit (idempotência pura)
    ├─ Se existe com status PROCESSING
    │  └─ Falha transiente (conflict/retry)
    └─ Se novo → marcar como RECEIVED e continuar
    ↓
[5] CommercialAggregateRepository.load()
    ├─ Buscar snapshot por aggregate_id
    ├─ Carregar version atual (ex: 41)
    ├─ Falha (não existe) → criar novo com version=1
    └─ Validar tenant_id matches
    ↓
[6] Validar tenant_id
    ├─ webhook.tenant_id == snapshot.tenant_id?
    ├─ Se não match → erro (cross-tenant rejection)
    └─ Continuar
    ↓
[7] BillingDomainService.process() (PURO)
    ├─ Passar snapshot APENAS (sem acesso a repos)
    ├─ Retorna decisão estruturada
    ├─ Nenhuma persistência ocorre
    ├─ Nenhum side effect
    └─ Saída: BillingDomainServiceResult
    ↓
[8] CommercialAggregateRepository.save()
    ├─ Compare-and-set: version_before=41, version_after=42
    ├─ Firestore.transaction().set(
    │    path,
    │    new_snapshot_with_version_42,
    │    merge=False
    │  )
    ├─ Falha se version≠41 (ConflictError)
    └─ Sucesso: novo snapshot persistido
    ↓
[9] ProcessedEventRepository.mark_processed()
    ├─ Atualizar status: PROCESSING → PROCESSED
    ├─ Adicionar processed_at (server timestamp)
    ├─ Adicionar aggregate_version_after=42
    ├─ Transação garante atomicidade
    └─ Falha → rollback automático
    ↓
[10] CommercialAuditRepository.record()
    ├─ Criar novo documento append-only
    ├─ Incluir: states_before, states_after, transitions, decision_code
    ├─ Incluir: version_before, version_after
    ├─ Nunca update/delete (append-only)
    ├─ Transação garante atomicidade
    └─ Falha → rollback automático
    ↓
[11] CommercialOutboxRepository.save()
    ├─ Para cada evento interno gerado:
    │  ├─ Criar documento outbox com status=PENDING
    │  ├─ Incluir: event_payload (JSON completo)
    │  ├─ Incluir: correlation_id (rastreabilidade)
    │  ├─ Incluir: created_at (server timestamp)
    │  ├─ Incluir: publication_attempts=0
    │  └─ Incluir: publication_status=PENDING (nunca publicar em Fase 3)
    ├─ Máximo de eventos por saída: 5-10 (configurável)
    ├─ Transação garante atomicidade
    └─ Falha → rollback automático
    ↓
[12] UnityOfWork.commit()
    ├─ Validar que todas escritas staged estão prontas (snapshot, dedup, audit, N outbox)
    ├─ Executar transação
    ├─ OU sucesso: retornar resultado (todos documentos persistidos atomicamente)
    ├─ OU falha: rollback automático (nenhum documento é persistido, incluindo nenhum item de outbox)
    └─ Retornar código estável (200 OK ou 409 Conflict ou 503 Unavailable)
    ↓
resultado estruturado (ao chamador)
```

### Propriedades Garantidas

✅ **Atomicidade:** Todos os documentos produzidos pela decisão (1 snapshot + 1 dedup + 1 audit + N outbox) escrevem juntos ou nenhum é escrito

✅ **Idempotência:** Mesmo webhook recebido 2x retorna mesmo resultado sem duplicar outbox ou qualquer outro documento

✅ **Isolamento:** Outro webhook para outro tenant não interfere; contexto de tenant é validado em todas as operações

✅ **Durabilidade:** Commit = dados persistidos imediatamente

✅ **Determinismo:** Mesmo estado + mesma decisão = mesma persistência sempre

### Tratamento de Falhas Dentro da Transação

```
CENÁRIO A: Validação falha (envelope inválido)
    └─ Antes de transação abrir
    └─ Retornar erro 400 sem rollback

CENÁRIO B: ProcessedEvent check falha
    └─ ConflictError (status PROCESSING de outra requisição)
    └─ Transação rollback automático
    └─ Retornar code=409 (conflict), retryable=true

CENÁRIO C: Snapshot load falha (não existe)
    └─ Criar novo com version=1, continuar
    └─ Transação prossegue

CENÁRIO D: Version conflict (version_before≠41)
    └─ ConflictError no save()
    └─ Transação rollback automático
    └─ Retornar code=409 (conflict), retryable=true

CENÁRIO E: Audit falha (Firestore indisponível)
    └─ TransactionError
    └─ Rollback automático (snapshot, dedup, outbox também descartados)
    └─ Retornar code=503 (unavailable), retryable=true

CENÁRIO F: Outbox falha (25 writes limit excedido)
    └─ Paginação: máx 10 eventos por transação
    └─ Segundo lote em transação separada (pós-sucesso)
    └─ Registrar em audit: "outbox paginado"
```

### Código Pseudocódigo

```python
def process_event(event: WebhookEvent) -> BillingApplicationServiceResult:
    # [1-3] Validação envelope
    validate_envelope(event)
    
    # [2] Abrir transação
    with firestore.transaction() as txn:
        # [4] Check idempotência
        processed = processed_repo.check_and_load(
            txn,
            tenant_id=event.tenant_id,
            provider=event.provider,
            provider_event_id=event.provider_event_id
        )
        if processed and processed.status == "PROCESSED":
            return processed.result  # Replay idempotente
        
        # [5] Load agregado
        snapshot = aggregate_repo.load(txn, aggregate_id)
        version_before = snapshot.version
        
        # [6] Validar tenant
        assert snapshot.tenant_id == event.tenant_id
        
        # [7] Domínio (PURO)
        domain_result = billing_service.process(snapshot, event)
        
        # [8] Save com versionamento
        new_snapshot = snapshot.copy()
        new_snapshot.version = version_before + 1
        aggregate_repo.save(txn, new_snapshot, expected_version=version_before)
        
        # [9] Mark processed
        processed_repo.mark_processed(
            txn,
            provider=event.provider,
            provider_event_id=event.provider_event_id,
            status="PROCESSED",
            aggregate_version_after=new_snapshot.version
        )
        
        # [10] Audit
        audit_repo.record(txn, {
            "version_before": version_before,
            "version_after": new_snapshot.version,
            "states_before": snapshot.to_dict(),
            "states_after": new_snapshot.to_dict(),
            "transitions": domain_result.transitions,
            "decision_code": domain_result.success
        })
        
        # [11] Outbox
        for event_internal in domain_result.internal_events:
            outbox_repo.save(txn, {
                "event_type": event_internal.event_type,
                "payload": event_internal.to_dict(),
                "publication_status": "PENDING"
            })
        
        # [12] Commit (automático ao sair do contexto)
        # Se falhar aqui: rollback automático
    
    return BillingApplicationServiceResult(
        success=domain_result.success,
        correlation_id=event.correlation_id,
        snapshots=(snapshot, new_snapshot),
        result_code=200
    )
```

---

## 🚪 GATES EXPLÍCITOS

### Gate A — Implementação Em Memória (Sem Firestore)

**Objetivo:** Validar fluxo completo sem I/O, com rollback simulado

**Bloqueadores:** Implementação de Firestore NÃO comença até Gate A PASS

**Testes Obrigatórios:**
- ✅ Evento novo processado com sucesso
- ✅ Evento duplicado já processado (retorno armazenado)
- ✅ Evento em PROCESSING (race condition simulada)
- ✅ Falha de domínio sem alteração snapshot
- ✅ Versionamento incremental (41 → 42)
- ✅ Cross-tenant rejection (tenant_id mismatch)
- ✅ Snapshot imutável durante processamento
- ✅ Rollback simula descard de todas escritas

**Evidência de Passou:**
```
✅ 8+ testes unitários PASS (em memória)
✅ Fluxo completo rastreável
✅ Idempotência sem duplicação
✅ Rollback restaura estado anterior
✅ Nenhuma importação Firestore
```

**Aprovação:** Code review + testes unitários 100% PASS

---

### Gate B — Decisão Formal de Paths + Estratégia Pré-Tenant

**Objetivo:** Documentar formalmente caminho e justificar decisão

**Bloqueadores:** Firestore concreto NÃO é criado até Gate B PASS

**Documentação Obrigatória:**
- ✅ ADR_001 finalizado (caminho escolhido + justificativa)
- ✅ Compatibilidade verificada (serviços existentes não quebram)
- ✅ Índices Firestore listados e validados
- ✅ Estratégia pré-tenant documentada (bloqueada ou alternativa)
- ✅ Impacto em Fase 4+ (webhook, worker) avaliado

**Checklist:**

```
☐ Paths em ADR_001 finalizados?
☐ Opção A (Clientes/{tenant_id}/Comercial) confirmada?
☐ Impacto em firebase_service_async.py? (Nenhum, path só leitura)
☐ Índices mapeados em matriz?
☐ Pré-tenant estratégia documentada (bloqueado em Fase 3)?
☐ Compatibilidade com backups Admin SDK verificada?
```

**Aprovação:** Produto + Arquitetura + Code review

---

### Gate C — Firestore Isolado (Emulador ou Projeto Teste)

**Objetivo:** Implementação Firestore sem riscos de produção

**Bloqueadores:** Nenhuma credencial de produção; nenhuma collection real

**Requisitos:**
- ✅ Emulador Firestore OR projeto de teste dedicado
- ✅ Collections isoladas (prefixo TEST_)
- ✅ Tenant exclusivo para testes (ex: tenant_test_001)
- ✅ Dados limpáveis entre testes
- ✅ Nenhuma credencial real no código
- ✅ Rollback simulado em memória ANTES de Firestore real

**Validação:**

```python
def test_firestore_isolated():
    # Verificar que estamos em emulador
    assert os.getenv("FIRESTORE_EMULATOR_HOST") == "localhost:8080"
    # OU verificar projeto de teste
    assert db.project == "test-project-xyz"
    # Tenant de teste exclusivo
    assert tenant_id.startswith("test_")
```

**Limpeza Entre Testes:**
```python
@pytest.fixture(autouse=True)
def cleanup_firestore():
    yield
    # Deletar todo conteúdo de Clientes/test_*
    # Deletar índices de teste
    # Verificar que produçnao não foi tocado
```

**Aprovação:** Testes isolados + verificação de ambiente

---

### Gate D — Atomicidade Verificada em Firestore Real

**Objetivo:** Demonstrar que transação garante atomicidade

**Bloqueadores:** Implementação de aplicação NÃO avança até Gate D PASS

**Testes Obrigatórios:**
- ✅ Snapshot + Dedup + Audit + Outbox persistem juntos
- ✅ Simulando falha no meio → nenhum write parcial permanece
- ✅ Versão atualiza corretamente (41 → 42)
- ✅ Processed event fica PROCESSED após commit
- ✅ Audit append-only sem updates/deletes
- ✅ Outbox criado com status=PENDING

**Evidência de Atomicidade:**

```
Cenário:
    1. Começar transação
    2. Escrever snapshot
    3. Escrever dedup
    4. Escrever audit
    5. Falhar intencionalmente antes outbox
    
Verificação:
    → Nenhum documento foi persistido
    → Snapshot versão não mudou
    → Dedup não foi criado
    → Audit vazio
    
PASS: Atomicidade confirmada
FAIL: Algum documento parcial permaneceu → Gate D falha
```

**Código de Teste:**

```python
def test_transaction_atomicity():
    with pytest.raises(Exception):
        with firestore.transaction() as txn:
            # Escrever snapshot
            snapshot_ref.set({"version": 42}, transaction=txn)
            
            # Escrever dedup
            dedup_ref.set({"status": "PROCESSED"}, transaction=txn)
            
            # Escrever audit
            audit_ref.set({"...": "..."}, transaction=txn)
            
            # FALHAR INTENCIONALMENTE
            raise RuntimeError("Simulando falha")
            
            # Outbox não é atingido
    
    # Verificar que nada foi salvo
    assert not snapshot_ref.get().exists
    assert not dedup_ref.get().exists
    assert not audit_ref.get().exists
```

**Aprovação:** Teste de atomicidade 100% PASS; verificação de zero writes parciais

---

### Gate E — Concorrência Testada em Firestore Real

**Objetivo:** Garantir isolamento e determinismo sob concorrência

**Bloqueadores:** Aplicação NÃO é considerada pronta até Gate E PASS

**Cenários de Concorrência:**
- ✅ Dois webhooks do mesmo tenant simultaneamente
- ✅ Dois webhooks para agregados diferentes do mesmo tenant
- ✅ Dois webhooks duplicados (mesmo provider_event_id) — deve gerar idempotência
- ✅ Webhook A para tenant A + Webhook B para tenant B (cross-tenant isolation)
- ✅ Version conflict (A lê version 41, B lê version 41, A escreve 42 primeiro, B falha com conflict)
- ✅ Retry automático de B (recarrega versão 42, continua)

**Testes Obrigatórios:**

```python
def test_concurrent_same_aggregate():
    """Dois webhooks para o mesmo agregado simultaneamente"""
    events = [
        webhook_event(aggregate_id="agg_1", event_id="evt_1"),
        webhook_event(aggregate_id="agg_1", event_id="evt_2")
    ]
    
    # Simular concorrência com threads
    results = concurrent_process(events)
    
    # Validar:
    # 1. Ambos completaram (não deadlock)
    assert len(results) == 2
    # 2. Snapshot persistido tem version final = 43 (ambos aplicados)
    snapshot = aggregate_repo.load(tenant_id, "agg_1")
    assert snapshot.version == 43
    # 3. Ambos events aparecem em dedup com PROCESSED
    assert dedup_repo.get(provider="webhooks", event_id="evt_1").status == "PROCESSED"
    assert dedup_repo.get(provider="webhooks", event_id="evt_2").status == "PROCESSED"
```

**Teste de Cross-Tenant:**

```python
def test_cross_tenant_isolation():
    """Dois webhooks para tenants diferentes"""
    event_tenant_a = webhook_event(tenant_id="tenant_a", aggregate_id="agg_x")
    event_tenant_b = webhook_event(tenant_id="tenant_b", aggregate_id="agg_x")
    
    # Mesma aggregate_id, tenants diferentes
    results = concurrent_process([event_tenant_a, event_tenant_b])
    
    # Validar:
    # Tenant A carrega seu documento, não o de B
    snapshot_a = aggregate_repo.load("tenant_a", "agg_x")
    # Tenant B carrega seu documento, não o de A
    snapshot_b = aggregate_repo.load("tenant_b", "agg_x")
    
    # Verificar isolamento em dedup também
    dedup_a = dedup_repo.load("tenant_a", ...)
    dedup_b = dedup_repo.load("tenant_b", ...)
```

**Teste de Duplicado Concorrente:**

```python
def test_duplicate_webhook_concurrent():
    """Mesmo webhook (duplicate) chega 2x simultaneamente"""
    webhook = webhook_event(provider_event_id="evt_12345")
    
    # Enviar 2x ao mesmo tempo
    results = concurrent_process([webhook, webhook])
    
    # Validar:
    # 1. Ambos retornaram sucesso (idempotência)
    assert all(r.success for r in results)
    # 2. Mesmo correlation_id retorna mesmo resultado
    assert results[0].result == results[1].result
    # 3. Dedup foi criado UMA VEZ, não DUAS
    dedup_count = dedup_repo.count(tenant_id, provider_event_id="evt_12345")
    assert dedup_count == 1
    # 4. Outbox foi criado UMA VEZ, não DUAS
    outbox_count = outbox_repo.count(tenant_id, source_event_id="evt_12345")
    # Múltiplos eventos sim, mas originários do MESMO webhook
```

**Teste de Version Conflict + Retry:**

```python
def test_version_conflict_with_retry():
    """Version conflict é retornado e cliente pode retrying"""
    # A lê version 41
    snapshot_a = aggregate_repo.load(tenant_id, aggregate_id)
    assert snapshot_a.version == 41
    
    # B lê version 41
    snapshot_b = aggregate_repo.load(tenant_id, aggregate_id)
    assert snapshot_b.version == 41
    
    # A processa e escreve (version 42)
    result_a = process_event(event_a, expected_version=41)
    assert result_a.success
    snapshot_final = aggregate_repo.load(tenant_id, aggregate_id)
    assert snapshot_final.version == 42
    
    # B tenta escrever (falha porque version é 42, não 41)
    result_b = process_event(event_b, expected_version=41)
    assert not result_b.success
    assert result_b.code == "409_CONFLICT"
    assert result_b.retryable == True
    
    # B retenta (recarrega version 42)
    result_b_retry = process_event(event_b, expected_version=42)
    assert result_b_retry.success
    snapshot_final = aggregate_repo.load(tenant_id, aggregate_id)
    assert snapshot_final.version == 43  # Ambos aplicados
```

**Aprovação:** Todos cenários de concorrência PASS; nenhuma race condition; isolamento validado

---

## 📋 CHECKLIST GATES

### Gate A — Em Memória
```
[ ] 8+ testes unitários PASS
[ ] Idempotência validada
[ ] Rollback funcionando
[ ] Nenhuma importação Firestore
[ ] Code review aprovado
```

### Gate B — Paths + Pré-Tenant
```
[ ] ADR_001 finalizado
[ ] Caminho Opção A escolhido
[ ] Compatibilidade verificada
[ ] Índices mapeados
[ ] Pré-tenant documentado (bloqueado)
[ ] Produto + Arquitetura aprovado
```

### Gate C — Firestore Isolado
```
[ ] Emulador OU projeto teste
[ ] Collections com prefixo TEST_
[ ] Tenant teste (test_001)
[ ] Limpeza entre testes
[ ] Nenhuma credencial real
[ ] Testes isolados rodam
```

### Gate D — Atomicidade Firestore
```
[ ] Snapshot + Dedup + Audit + Outbox atômicos
[ ] Simulação de falha → zero writes parciais
[ ] Version atualiza corretamente
[ ] Audit append-only confirmado
[ ] Teste de atomicidade 100% PASS
```

### Gate E — Concorrência Firestore
```
[ ] Dois webhooks mesmo agregado
[ ] Dois webhooks cross-tenant
[ ] Duplicado concorrente
[ ] Version conflict + retry
[ ] Isolamento multi-tenant confirmado
[ ] Nenhuma race condition
[ ] Testes de concorrência 100% PASS
```

---

## 📋 EVIDÊNCIAS FINAIS OBRIGATÓRIAS

Depois de Gate E, **Fase 3 requer evidências explícitas:**

### Decisão e Justificativa
- [ ] ADR_001 assinado (caminho escolhido)
- [ ] Compatibilidade com serviços existentes (verificada)
- [ ] Pré-tenant strategy (documentada como bloqueada ou alternativa)

### Atomicidade e Transação
- [ ] Fluxo transacional (passos 1-12 implementados)
- [ ] Teste de atomicidade (snapshot + dedup + audit + outbox)
- [ ] Simulação de falha (verificação de zero writes parciais)

### Concorrência e Isolamento
- [ ] Version conflict handling (compare-and-set)
- [ ] Cross-tenant isolation (testes de rejeição)
- [ ] Duplicate concurrent webhooks (idempotência validada)
- [ ] Retry logic (código estável para conflict)

### Idempotência Estruturada
- [ ] ProcessedEvent deduplication por (provider, provider_event_id)
- [ ] Check + Persistência MESMA transação
- [ ] Replay sem duplicação de outbox

### Persistência e Auditoria
- [ ] Snapshot com versionamento (41 → 42 → 43)
- [ ] Audit append-only (nenhum update/delete)
- [ ] Outbox status PENDING (nunca publicado em Fase 3)

### Isolamento Multi-Tenant
- [ ] Validação tenant_id em toda leitura/escrita
- [ ] Test que Tenant A não lê Tenant B
- [ ] Test que Tenant A não escreve Tenant B
- [ ] Auditoria e outbox isoladas por tenant

### Testes
- [ ] 80+ unitários (em memória): PASS
- [ ] 40+ integração (Firestore isolado): PASS
- [ ] 20+ segurança (multi-tenant): PASS
- [ ] Atomicidade real (Gate D): PASS
- [ ] Concorrência real (Gate E): PASS

### Código
- [ ] py_compile sem erros
- [ ] Nenhuma importação Firestore fora de `/infra`
- [ ] BillingDomainService permanece puro
- [ ] Repositórios abstraem Firestore completamente

### Documentação
- [ ] Fluxo transacional (este arquivo)
- [ ] ADR_001 (decisão de paths)
- [ ] Matriz de operações (read/write por transação)
- [ ] Limites conhecidos (25 writes, paginação outbox)
- [ ] Gaps pré-tenant (bloqueado até clareza contratual)

---

## 🚫 PROIBIÇÕES MANTIDAS

✅ Mantidas todas proibições de escopo:

```
❌ Não alterar Fase 1/2 sem defeito comprovado
❌ Não adicionar Firestore ao BillingDomainService
❌ Não implementar webhook HTTP
❌ Não integrar Hotmart
❌ Não publicar outbox (apenas PENDING)
❌ Não implementar worker de reconciliação
❌ Não criar raiz Tenants/ sem aprovação formal
❌ Não armazenar lead pré-tenant sem estratégia
```

---

## ⏭️ PRÓXIMAS AÇÕES (Governadas por Gates)

### Fase 3.1 — Implementação Em Memória (Gate A)
- [ ] Criar repositórios de interface
- [ ] Criar implementações em memória
- [ ] Criar BillingApplicationService
- [ ] Criar 80+ testes unitários
- [ ] Gate A review + aprovação

### Fase 3.2 — Decisão Formal (Gate B)
- [ ] ADR_001 assinado
- [ ] Índices mapeados
- [ ] Compatibilidade verificada
- [ ] Gate B review + aprovação Produto + Arquitetura

### Fase 3.3 — Implementação Firestore (Gates C, D, E)
- [ ] Setup emulador/projeto teste
- [ ] Implementações Firestore
- [ ] 40+ testes integração
- [ ] 20+ testes segurança
- [ ] Gate C, D, E review + aprovação

### Fase 3.4 — Integração Completa
- [ ] BillingApplicationService integrado
- [ ] Testes E2E
- [ ] Documentação
- [ ] Aprovação final

---

**FASE3_GATES_E_FLUXO_TRANSACIONAL.md**
