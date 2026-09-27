# C3.15.4 — FASE B: DESENHO DA CONSOLIDAÇÃO

**Status:** DESENHO SOMENTE (Sem Implementação)  
**Data:** 2026-09-26  
**Escopo:** Projetar consolidação de onboarding isolado para Configuracao/negocio  

---

## 1. CONTRATO EXATO: `validar_onboarding_minimo()`

### Estado Atual (Legacy)

**Localização:** `services/onboarding_dono_service.py:403-457`

**Comportamento:** Lê de `Clientes/{tenant_id}/Configuracao/negocio` e valida 8 campos obrigatórios:
```
nome_negocio
segmento
endereco
agenda_padrao
primeiro_profissional
canal_primeiro_profissional
primeiro_servico
duracao_primeiro_servico
```

**Retorna:**
```python
{
    "valido": bool,
    "motivo": str,
    "faltando": [list of missing fields]
}
```

**Consumidor Único Identificado:**
- `processar_resposta_onboarding_dono()` em onboarding_service.py:305
- Usa resultado para decidir se marca onboarding como completo

### Semântica Clarificada

**O que está sendo validado:**
- ✅ **ACTOR STATE:** Os 8 campos de coleta do onboarding individual completou?
- ❌ **NOT:** Configuração consolidada do tenant
- ❌ **NOT:** Dados comerciais adicionais

**Mapeamento Semântico dos 8 Campos:**
```
Nome do Negócio          → nome_negocio
Tipo/Segmento           → segmento
Localização              → endereco
Horário Padrão           → agenda_padrao
1º Profissional          → primeiro_profissional
Canal de Contato (Prof)  → canal_primeiro_profissional
1º Serviço Oferecido     → primeiro_servico
Duração do Serviço       → duracao_primeiro_servico
```

**Conclusão:** Estes 8 campos representam o **estado mínimo necessário** para que um ator complete seu onboarding individual.

### Fonte de Verdade Pós-Consolidação

**Opção Escolhida: HYBRID (Leitura Sequencial)**

```python
async def validar_onboarding_minimo_v2(tenant_id: str, actor_id: str) -> dict:
    """
    Validar se onboarding mínimo está completo.
    
    Busca sequencialmente:
    1. Novo path: Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
       (estado atual do ator)
    2. Legacy: Clientes/{tenant_id}/Configuracao/negocio
       (fallback apenas se ownership válido)
    
    Valida os 8 campos em ambos os casos.
    """
```

**Justificativa:** Mantém compatibilidade com legacy enquanto prioriza novo path.

---

## 2. CONTRATO DE CONSOLIDAÇÃO

### Nova Função: `consolidar_onboarding_completo()`

```python
async def consolidar_onboarding_completo(
    tenant_id: str,
    actor_id: str
) -> dict:
    """
    Consolida onboarding completo do actor em Configuracao/negocio.
    
    Regras:
    - Operação ATÔMICA (Firestore Transaction)
    - Primeiro actor a completar → define dono_principal_actor_id
    - Segundo+ actors → preservam dono_principal_actor_id
    - Retry da mesma requisição → idempotente
    - Webhook duplicado → idempotente
    
    Returns:
    {
        "sucesso": bool,
        "consolidado": bool (True se foi primeiro, False se preservou)
        "dono_principal_actor_id": str (novo ou existente)
        "campos_consolidados": dict
        "timestamp_consolidacao": str
    }
    """
```

### Campos Consolidados

| Campo | Origem | Destino | Imutável | Notas |
|-------|--------|---------|----------|-------|
| nome_negocio | ator | negócio | NÃO | Pode ser atualizado depois |
| segmento | ator | negócio | NÃO | Pode ser atualizado depois |
| endereco | ator | negócio | NÃO | Pode ser atualizado depois |
| agenda_padrao | ator | negócio | NÃO | Pode ser atualizado depois |
| primeiro_profissional | ator | negócio | NÃO | Informativo apenas |
| canal_primeiro_profissional | ator | negócio | NÃO | Informativo apenas |
| primeiro_servico | ator | negócio | NÃO | Informativo apenas |
| duracao_primeiro_servico | ator | negócio | NÃO | Informativo apenas |
| dono_principal_actor_id | ator | negócio | **SIM** | **IMUTÁVEL** |
| dono_nome | ator | negócio | NÃO | Do primeiro ator |
| dono_email | ator | negócio | NÃO | Do primeiro ator |

### Campos NÃO Consolidados (Permanecem Isolados)

```
❌ onboarding_etapa_atual     (estado individual)
❌ onboarding_indice           (estado individual)
❌ onboarding_status           (estado individual do novo path)
❌ _ultimo_campo_idempotencia  (C3.15.3 internal)
❌ criado_por                  (rastreabilidade do ator específico)
❌ ator_id                     (contexto do ator específico)
```

---

## 3. DONO PRINCIPAL (IMUTÁVEL)

### Regra Formal

```
dono_principal_actor_id := PRIMEIRO actor_id cujo onboarding foi
                           validado como completo e consolidado
                           atomicamente em Configuracao/negocio
```

### Propriedades

- **Definição:** Atômica via Firestore Transaction
- **Imutabilidade:** Uma vez definido, NUNCA é sobrescrito
- **Determinismo:** Não depende de timestamp, ordem de chegada ou webhook
- **Concorrência:** Transaction garante que apenas um actor o define
- **Idempotência:** Retry do mesmo actor não altera o valor

### Semanticamente

**Significa:** "Este é o ator que iniciou e completou o onboarding para este tenant."

**NÃO significa:** "Este é o único dono" (pode haver múltiplos atores, mas um é o "principal")

---

## 4. CONCORRÊNCIA: TRANSACTION BOUNDARY

### Cenário Crítico

```
Timeline:
T1: Actor A completa onboarding
T2: Actor B completa onboarding (SIMULTÂNEAMENTE ou dentro de ms)

Esperado:
- Exatamente UM define dono_principal_actor_id
- Outro preserva o valor já definido
- Ambos consolidam seus dados de negócio
```

### Pseudocódigo de Transaction

```python
def transaction_consolidar(transaction, tenant_id, actor_id):
    # 1. Ler documento consolidado
    negocio_ref = db.collection("Clientes").document(tenant_id)\
                     .collection("Configuracao").document("negocio")
    
    negocio_doc = transaction.get(negocio_ref)
    
    # 2. Verificar se dono_principal já foi definido
    if negocio_doc.exists and negocio_doc.get("dono_principal_actor_id"):
        # Dono já foi definido (outro ator completou primeiro)
        # Ação: consolidar dados deste ator, preservar dono_principal_actor_id
        dono_principal = negocio_doc.get("dono_principal_actor_id")
        consolidado = False
    else:
        # Dono não foi definido (este é o primeiro)
        # Ação: definir dono_principal_actor_id, consolidar dados
        dono_principal = actor_id
        consolidado = True
    
    # 3. Preparar dados consolidados
    dados_consolidados = {
        # Campos de negócio (sempre consolidar)
        "nome_negocio": ator_doc.get("nome_negocio"),
        "segmento": ator_doc.get("segmento"),
        "endereco": ator_doc.get("endereco"),
        "agenda_padrao": ator_doc.get("agenda_padrao"),
        
        # Campos informativos do primeiro profissional
        "primeiro_profissional": ator_doc.get("primeiro_profissional"),
        "canal_primeiro_profissional": ator_doc.get("canal_primeiro_profissional"),
        "primeiro_servico": ator_doc.get("primeiro_servico"),
        "duracao_primeiro_servico": ator_doc.get("duracao_primeiro_servico"),
        
        # Dono principal (só definir uma vez)
        "dono_principal_actor_id": dono_principal,
        
        # Metadados
        "consolidado_em": now,
        "consolidado_por_actor_id": actor_id,
        "dono_nome": ator_doc.get("dono_nome"),
        "dono_email": ator_doc.get("dono_email"),
    }
    
    # 4. Merge (não sobrescrever campos existentes)
    transaction.update(negocio_ref, {
        **dados_consolidados,
        "atualizado_em": now
    })
    
    # 5. Retornar resultado
    return {
        "sucesso": True,
        "consolidado": consolidado,
        "dono_principal_actor_id": dono_principal
    }

# Chamar a transaction
resultado = db.transaction(transaction_consolidar)(tenant_id, actor_id)
```

### Garantias da Transaction

- ✅ Leitura e escrita atômicas
- ✅ Apenas um actor define `dono_principal_actor_id`
- ✅ Retry automático do Firestore é seguro
- ✅ Nenhuma race condition
- ✅ Determinístico

---

## 5. IDEMPOTÊNCIA

### Definição Formal

**Mesma requisição enviada N vezes** → mesmo resultado sem efeito colateral

### Cenários Cobertos

1. **Webhook Duplicado**
   - Actor A completa → webhook enviado 2x
   - 2ª tentativa: detectar idempotência, retornar resultado da 1ª

2. **Retry de Network**
   - Requisição enviada, timeout na resposta
   - Cliente retenta → sem duplicar consolidação

3. **Timeout Pós-Commit**
   - Transaction commitou, servidor não respondeu
   - Cliente retenta → idempotência detecta já consolidado

4. **Retry de Transaction**
   - Firestore retenta automaticamente
   - Deve ser seguro retomar no mesmo ponto

### Mecanismo Determinístico

**Usar chave de idempotência armazenada no documento:**

```
consolidacao_idempotencia_key = SHA256(actor_id:tenant_id:timestamp_local)[:16]
```

Armazenar em `Configuracao/negocio`:
```
_consolidacao_por_actor[actor_id] = consolidacao_idempotencia_key
```

Verificação:
```python
if negocio_doc.get("_consolidacao_por_actor", {}).get(actor_id) == key:
    # Já consolidado por este ator
    return resultado_anterior()
```

---

## 6. MATRIZ LEGACY

| Situação | Ação | Resultado |
|----------|------|-----------|
| Legacy pertence ao mesmo actor | Fallback se novo não existe | OK |
| Legacy pertence a outro actor | BLOQUEAR (ownership check) | ERROR |
| Legacy sem `dono_actor_id` | Não assumir, usar novo path | Seguro |
| Novo path existe | Novo path é fonte de verdade | OK |
| Legacy existe, novo não existe | Fallback + ownership validation | OK se ownership OK |
| Ambos existem | Novo path prevalece | OK |
| Legacy completo | Preservar, não sobrescrever | OK |
| Legacy em progresso | Não interferir, deixar progresso | OK |
| Nenhum existe | Criar consolidação vazia | OK se ator já completou |

---

## 7. ESTRATÉGIA DE MIGRAÇÃO (Sem Executar)

### Elegibilidade

Documento legacy pode ser migrado se:
1. Possui `dono_actor_id` válido (normalizado)
2. Possui os 8 campos mínimos
3. Status é "completo"
4. Novo path não existe ainda

### Transformação

```python
legacy_doc = {
    "nome_negocio": "...",
    "segmento": "...",
    "dono_actor_id": "5521111111111",
    # ... 6 outros campos
}

novo_doc = {
    "tenant_id": tenant_id,
    "actor_id": legacy_doc["dono_actor_id"],
    "onboarding_status": "completo",
    "onboarding_etapa_atual": "completo",
    "onboarding_indice": 11,
    # ... copiar 8 campos
    "dono_principal_actor_id": legacy_doc["dono_actor_id"],  # Consolidado
}
```

### Validação Pós-Migração

1. Novo path criado
2. Campos não corrompidos
3. Ownership preservado
4. Legacy ainda intacto

### Rollback

Se validação falhar:
1. Deletar novo path criado
2. Legacy permanece
3. Log de erro registrado

### Idempotência de Migração

Usar idempotencia key:
```
migracao_key = SHA256(legacy_doc_id:actor_id)[:16]
```

Se já migrado: skip, não duplicar.

---

## 8. `validar_onboarding_minimo()` PÓS-CONSOLIDAÇÃO

### Mudança de Comportamento

**Antes (C3.15.3):**
```python
validar_onboarding_minimo(tenant_id)
# → lê de Configuracao/negocio
```

**Depois (C3.15.4):**
```python
validar_onboarding_minimo(tenant_id, actor_id)
# → lê de Donos/{actor_id}/onboarding/ativo
# → fallback para Configuracao/negocio se ownership OK
```

### Separação: Actor State vs Business Configuration

```python
async def validar_actor_onboarding_completo(tenant_id, actor_id):
    """Valida se O ATOR completou seu onboarding."""
    # Lê de Donos/{actor_id}/onboarding/ativo
    # Verifica 8 campos preenchidos
    # Retorna estado do ator

async def validar_negocio_configuracao_minima(tenant_id):
    """Valida se O NEGÓCIO tem configuração mínima."""
    # Lê de Configuracao/negocio
    # Verifica 8 campos consolidados
    # Retorna estado do negócio
```

### Consumidor Único

`processar_resposta_onboarding_dono()` atualmente valida actor (não negócio), portanto:

**Novo Contrato:**
```python
validacao = await validar_actor_onboarding_completo(tenant_id, actor_id)
if validacao.get("valido"):
    consolidar_onboarding_completo(tenant_id, actor_id)
```

---

## 9. AUDITORIA DE CALLSITES

### Funções Afetadas

| Função | Arquivo | Linha | Ação | Risco |
|--------|---------|-------|------|-------|
| `validar_onboarding_minimo` | onboarding_dono_service.py | 403 | ADD actor_id param | BAIXO |
| `marcar_onboarding_completo` | onboarding_dono_service.py | 231 | ADD consolidar call | MÉDIO |
| `processar_resposta_onboarding_dono` | onboarding_service.py | 305 | UPDATE validação | BAIXO |

### Callsites Consumidores

1. **processar_resposta_onboarding_dono** (onboarding_service.py:305)
   - Chama: `validar_onboarding_minimo(tenant_id)`
   - Mudança necessária: passar `actor_id`
   - Impacto: BAIXO (actor_id já está em ctx)

---

## 10. MATRIZ DE TESTES (Plano Somente)

### Testes de Consolidação (Novos)

```
C1  — Primeiro ator completa → define dono_principal        [DESIGN]
C2  — Segundo ator completa → preserva dono_principal       [DESIGN]
C3  — Dois atores completam concorrentemente                 [DESIGN]
C4  — Retry da requisição → idempotente                      [DESIGN]
C5  — Webhook duplicado → idempotente                        [DESIGN]
C6  — Transaction retry seguro                               [DESIGN]
C7  — Actor inválido → bloqueado                             [DESIGN]
C8  — Tenant inválido → bloqueado                            [DESIGN]
C9  — Onboarding incompleto → não consolida                  [DESIGN]
C10 — Documento negócio inexistente → criar                  [DESIGN]
C11 — Documento negócio já existente → merge                 [DESIGN]
C12 — dono_principal_actor_id permanece imutável             [DESIGN]
C13 — Campos consolidados corretos                           [DESIGN]
C14 — Campos isolados NÃO contaminam negócio                 [DESIGN]
C15 — Legacy preservado                                      [DESIGN]
```

### Testes de Validação (Novos)

```
V1  — validar_actor com novo path                            [DESIGN]
V2  — validar_actor com legacy fallback                      [DESIGN]
V3  — validar_negocio com consolidação                       [DESIGN]
V4  — validar sem actor_id (erro)                            [DESIGN]
```

### Regressões (Verificar)

```
R1  — C3.15.1: 10/10 PASS                                    [TODO]
R2  — C3.15.2: 13/13 PASS                                    [TODO]
R3  — C3.15.3: 16/16 PASS                                    [TODO]
```

---

## 11. INVARIANTES

| Invariante | Verificação | Critério |
|-----------|------------|----------|
| `dono_principal_actor_id` imutável | Nunca sobrescrito | Uma vez definido, permanece |
| Ownership validado | Sempre | doc.actor_id == request.actor_id |
| Tenant validado | Sempre | doc.tenant_id == request.tenant_id |
| Legacy preservado | Nunca deletado | Legacy persiste |
| Isolamento mantido | Campos isolados | Sem contaminação entre atores |
| Transaction atômica | Sem race condition | Um vencedor por consolidação |
| Idempotência | Retry seguro | Mesma chave = mesmo resultado |
| Compatibilidade | Fallback ativo | Legacy ainda funciona |

---

## 12. ANÁLISE DE ESCALA

### Complexidade

- **O(1) por operação**
  - Acesso direto: `Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo`
  - Consolidação: `Clientes/{tenant_id}/Configuracao/negocio`

- **Nenhuma query global**
  - Sem varredura de tenants
  - Sem busca de todos os atores
  - Sem índices necessários

- **Transaction Size**
  - Leitura: 1 documento (negócio consolidado)
  - Escrita: 1 documento (negócio consolidado)
  - Máximo 2 operações Firestore por transação

### Custo Firestore

| Operação | Reads | Writes | Nota |
|----------|-------|--------|------|
| Consolidar (1º ator) | 1 | 1 | Define dono_principal |
| Consolidar (2º+ ator) | 1 | 1 | Preserva dono_principal |
| Validar ator | 1 | 0 | Leitura do novo path |
| Validar negócio | 1 | 0 | Leitura de consolidação |

---

## 13. RISCOS RESIDUAIS

| Risco | Probabilidade | Impacto | Mitigation |
|-------|---------------|--------|-----------|
| **Firestore transaction abort** | BAIXA | MÉDIO | Retry automático, idempotência |
| **Webhook timeout após commit** | MÉDIA | BAIXO | Idempotência detecta já consolidado |
| **Dois atores mesma timestamp** | MUITO BAIXA | ALTO | Transaction garante vencedor único |
| **Legacy corrompido acidentalmente** | BAIXA | ALTO | Preservar, não alterar |
| **validar_onboarding_minimo confuso** | MÉDIA | MÉDIO | Documentar semanticamente |

---

## 14. ARQUIVOS QUE SERÃO AFETADOS (Fase C)

```
SERÁ ALTERADO:
  ✏️ services/onboarding_dono_service.py
     - marcar_onboarding_completo() → adicionar consolidar
     - Nova função: consolidar_onboarding_completo()
     - validar_onboarding_minimo() → ADD actor_id param

  ✏️ services/onboarding_service.py
     - processar_resposta_onboarding_dono() → UPDATE validação

SERÁ CRIADO:
  ✨ tests/test_c315_4_consolidacao.py (16+ testes)

NÃO SERÁ ALTERADO:
  ✓ router/integracao_identidade_onboarding.py
  ✓ services/onboarding_isolado_schema.py
  ✓ services/firebase_service_async.py
```

---

## CRITÉRIOS OBJETIVOS DE APROVAÇÃO (Fase B)

- [x] Contrato exato de `validar_onboarding_minimo()` definido
- [x] Contrato de consolidação definido
- [x] Regra de dono principal formalizada (imutável)
- [x] Transaction boundary explícito
- [x] Idempotência determinística
- [x] Matriz legacy completa
- [x] Estratégia de migração documentada
- [x] Separação Actor State / Business Config clara
- [x] Callsites auditados
- [x] Matriz de testes planejada
- [x] Invariantes documentadas
- [x] Escala validada (O(1), sem queries globais)
- [x] Riscos identificados
- [x] Nenhuma implementação iniciada
- [x] Nenhuma alteração em Firestore
- [x] Nenhum commit
- [x] Nenhum push

---

**FASE B CONCLUÍDA:** Desenho pronto para aprovação  
**Próximo:** Fase C (Implementação) — aguarda aprovação explícita  

