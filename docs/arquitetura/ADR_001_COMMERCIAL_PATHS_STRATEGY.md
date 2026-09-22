# ADR 001 — Estratégia de Paths para Agregado Comercial

**Data:** 2026-07-27  
**Decisor:** Produto + Arquitetura  
**Status:** ANÁLISE (não implementado)  
**Impacto:** P0 — Define raiz de todas collections comerciais  

---

## 🎯 QUESTÃO

Qual estrutura Firestore usar para armazenar estado comercial (Trial, Assinatura, Pagamento, Acesso, Retenção)?

1. Estender `Clientes/{tenant_id}` com subcoleção `Comercial`
2. Criar nova raiz `Tenants/{tenant_id}`
3. Híbrido ou alternativa

---

## 📊 ANÁLISE COMPARATIVA

### Opção A: `Clientes/{tenant_id}/Comercial/{aggregate_id}`

**✅ Vantagens**
- Reutiliza raiz já mapeada no código existente
- Coerente com estrutura atual: `Clientes/{tenant_id}/Tarefas`, `Clientes/{tenant_id}/Contatos`
- Firestore é hierárquico por design
- Menor risco de duplicação de identidade
- Queries existentes no `firebase_service_async.py` continuam ativas
- Admin SDK e backups já operacionalizam este padrão
- Índices compostos seguem convenção `Clientes_{tenant_id}_Comercial`

**❌ Riscos**
- `Clientes/{tenant_id}` historicamente foi user_id, novo significado como tenant_id pode confundir
- Migração retroativa de dados pré-tenant requer ler/reescrever
- Diferencia "cliente" (usuário) de "tenant" (organização) apenas por semântica

**📝 Uso Atual**
```
Clientes/{user_id} → id_negocio (tenant_id)
├─ Tarefas/{tarefa_id}
├─ Contatos/{contato_id}
├─ NotificacoesAgendadas/{notif_id}
```

Novo:
```
Clientes/{tenant_id} → id_negocio (mesmo)
├─ Comercial/{aggregate_id}
├─ Tarefas/{tarefa_id}
├─ Contatos/{contato_id}
```

**Compatibilidade:** ✅ Serviços lendo `Clientes/{tenant_id}` continuam válidos

---

### Opção B: `Tenants/{tenant_id}/CommercialAggregates/{aggregate_id}`

**✅ Vantagens**
- Explícito: "Tenants" deixa claro que tenant_id é chave primária
- Segregação semântica clara: `Clientes` = usuários, `Tenants` = organizações
- Preparado para crescimento futuro (multi-tenant governance, SSO, delegação)
- Reduz confusão histórica user_id vs tenant_id

**❌ Riscos**
- **Cria nova raiz** — duplica identidade (Clientes/{tenant_id} E Tenants/{tenant_id})
- Índices compostos precisam ser criados do zero
- Consultas espalhadas entre duas raízes
- Migração: copiar dados ou aceitar histórico quebrado?
- Admin SDK precisa de novo path
- Backups precisam de novo prefixo
- 50% maior overhead de manutenção durante transição

**Índices Requeridos:** Novos (`Tenants` raiz não indexada)
```
- Tenants/{tenant_id}/CommercialAggregates (compound: tenant_id, version)
- Tenants/{tenant_id}/ProcessedEvents (compound: tenant_id, provider_event_id)
- Tenants/{tenant_id}/CommercialAudit (compound: tenant_id, occurred_at)
- Tenants/{tenant_id}/CommercialOutbox (compound: tenant_id, status)
```

**Compatibilidade:** ❌ Serviços históricos lendo Clientes/{tenant_id} precisam de fork

---

### Opção C: Híbrido — `Clientes/{tenant_id}/Comercial` + `ProcessedEvents` global

**Padrão:** Agregado em subcoleção, eventos de auditoria compartilhados

```
Clientes/{tenant_id}/Comercial/{aggregate_id}
ProcessedWebhookEvents/{tenant_id}_{provider}_{event_id}  ← global, não aninhado
CommercialAudit/{tenant_id}_{audit_id}                    ← global, particionado por prefixo
CommercialOutbox/{tenant_id}_{outbox_id}                  ← global, particionado por prefixo
```

**Vantagens:**
- Agregado reutiliza estrutura existente
- Eventos críticos (auditoria, outbox) em raiz para query rápida
- Facilita worker global de outbox (Fase 5)
- Menos índices compostos aninhados

**Desvantagens:**
- Particionamento por prefixo não é idempotência garantida
- Queries requerem OR-logic ou COLLECTION GROUP
- Mais código para validar isolamento multi-tenant

---

## 🔍 VERIFICAÇÃO SISTEMÁTICA

### 1. Caminhos Atuais Críticos

**Grep em repositórios existentes:**
- `firebase_service_async.py`: usa `Clientes/{user_id}`
- `firestore_client.py`: singleton não-opinado
- Sem queries globais (todas scoped por Clientes/{user_id})

**Conclusão:** ✅ Código atual é agnóstico, mudança é possível

### 2. Serviços que Usam `Clientes/{tenant_id}`

```
firebase_service_async.py:
├─ buscar_cliente(user_id)
├─ atualizar_cliente(user_id, dados)
├─ obter_id_dono(user_id)  ← Crítico para tenant_id resolution
├─ buscar_tarefa(user_id, tarefa_id)
├─ atualizar_tarefa(user_id, tarefa_id, dados)
└─ ... (mais operações Tarefas, Contatos, etc)
```

**Impacto de Opção B:** Todas essas chamadas continuam válidas (usam `Clientes/{tenant_id}`)

**Impacto de Opção A:** Apenas adiciona `Comercial` subcoleção

### 3. Scripts de Migração

**Existem?** Não encontrado em `scripts/`

**Necessário?** Sim, se Opção B for escolhida (copiar histórico para Tenants/)

### 4. Testes Existentes

**Location:** `tests/test_firestore_*.py`, `tests/runner_*.py`

**Padrão:** Lêem/escrevem em Clientes/{user_id}

**Impacto:** Nenhum se usar Opção A; testes de comercial usam novo path de forma isolada

### 5. Consultas e Índices

**Índices atuais:** Firestore Admin console

**Novos índices necessários:**
- Opção A: `Clientes/{tenant_id}/Comercial (version)`, `(updated_at)`
- Opção B: Novos 4+ índices compostos sob Tenants/
- Opção C: Híbrido (2 índices novos em raiz)

### 6. Backups

**Padrão:** Cloud Firestore Backup (prefixo ou coleção)

**Impacto A:** Inclui automaticamente Clientes/* (já feito)
**Impacto B:** Precisa de novo prefixo Tenants/* ou EXCLUDE explícito
**Impacto C:** Hibrid (alguns em Clientes, alguns em raiz)

### 7. Compatibilidade Admin SDK

**Firestore Admin Python:** Agnóstico, qualquer path funciona

**Limitação:** Max 25 writes/transação, não foi limite para Opção A vs B

### 8. Risco de Duplicação de Identidade Tenant

**Cenário:** Mesmo tenant_id referenciado em dois caminhos

- Opção A: ✅ Impossível (raiz única)
- Opção B: ⚠️ Possível (se código ler Clientes E Tenants)
- Opção C: ⚠️ Possível (agregado em Clientes, eventos em Tenants)

**Mitigação:** Repositório abstrai read/write, validação obrigatória

### 9. Impacto Futuro

**Fase 4+: Webhook Hotmart**
- Requer roteamento por tenant_id
- Ambos paths funcionam

**Fase 5+: Worker de Outbox**
- Opção A: Query `CollectionGroup('Comercial')` + `CollectionGroup('ProcessedWebhookEvents')`
- Opção B: Query direto `Tenants/` + `ProcessedWebhookEvents/`
- Opção C: Híbrido (queries mistas)

**Recomendação:** Opção C realmente simplifica worker futuro

---

## 🎯 CONCLUSÃO E RECOMENDAÇÃO

### Decisão: **OPÇÃO A** (`Clientes/{tenant_id}/Comercial`)

**Justificativa:**
1. Menor risco de duplicação (raiz única)
2. Reutiliza estrutura já operacionalizada
3. Compatibilidade zero-ruptura com código existente
4. Índices simples (compostos em subcoleção)
5. Backups e Admin já integrados
6. Migração futura é sempre possível se necessário

### Comprometimentos Explícitos:
- Semântica confusa (Clientes historicamente = usuários)
- Índices aninhados podem escalar lentamente
- Worker futuro usa CollectionGroup (menos eficiente)

### Mitigações:
- Documentar explicitamente: Clientes/{tenant_id} = organização (negócio)
- Adicionar comentário em `obter_id_dono()`: "Clientes.doc() = Tenant ID em NeoEve"
- Repositório encapsula path completamente
- Revisar esta decisão em Fase 5 se performance degradar

---

## ✅ ESTRUTURA FIRESTORE DEFINITIVA (Opção A)

### Collections

```
Clientes/{tenant_id}/
├─ [Tenant document: id_negocio, nome, estado]
│
├─ Comercial/{aggregate_id}
│  └─ [Snapshot: trial_state, assinatura_state, version, ...]
│
├─ ProcessedWebhookEvents/{id}
│  └─ [Dedup: provider, provider_event_id, status, ...]
│
├─ CommercialAudit/{audit_id}
│  └─ [Append-only: transitions, states_before/after, ...]
│
├─ CommercialOutbox/{outbox_id}
│  └─ [Pending outbox: event_type, status=PENDING, ...]
│
├─ Tarefas/{tarefa_id}  ← Existente
├─ Contatos/{contato_id}  ← Existente
└─ NotificacoesAgendadas/{notif_id}  ← Existente
```

### Índices Requeridos

| Collection | Índice | Tipo |
|-----------|--------|------|
| Comercial | `(updated_at)` | Simples |
| Comercial | `(version)` | Simples |
| ProcessedWebhookEvents | `(provider, provider_event_id)` | Composto |
| ProcessedWebhookEvents | `(status)` | Simples |
| CommercialAudit | `(occurred_at)` | Simples |
| CommercialOutbox | `(publication_status)` | Simples |

### Validação Multi-Tenant

```python
def _validate_tenant_id(tenant_id: str) -> None:
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id obrigatório")
    # Não permitir caracteres especiais
    if not tenant_id.isalnum():
        raise ValueError("tenant_id deve conter apenas alphanumerics")
```

---

## 🚫 PRÉ-TENANT (Gap Bloqueado)

### Problema
Leads/prospects sem tenant_id antes de conversão. Onde armazenar?

### Soluções Candidatas
1. **Criar `Leads/` raiz** — nova raiz, mesma duplicação que Tenants/
2. **Clientes/{pseudo_tenant_id}** — usar lead_id como tenant, renomear na conversão
3. **Documento global Leads/{lead_id}** — single collection, queries por lead_id
4. **Postergar** — não implementar pré-tenant em Fase 3

### Decisão Atual
**Bloqueado para Fase 3.** Repositório define interface abstrata:
```python
async def load_by_lead_id(lead_id: str) -> Optional[CommercialAggregate]:
    raise NotImplementedError("Pré-tenant storage strategy undefined")
```

Fase 4/5 define armazenamento quando contrato pré-tenant for claro.

---

## 📋 Checklist de Implementação (Gate B)

- [ ] Verificar que nenhum código existente quebra
- [ ] Atualizar comentários em `firebase_service_async.py`
- [ ] Documenter em ADR que Clientes/{tenant_id} = tenant (não user)
- [ ] Criar teste que valida isolamento entre Clientes/{A} e Clientes/{B}
- [ ] Implementar paths em constantes centralizadas
- [ ] Definir estratégia pré-tenant (bloqueada ou alternativa)

---

**ADR_001_COMMERCIAL_PATHS_STRATEGY.md**
