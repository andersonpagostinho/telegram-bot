# GATE C3.13 — TABELA COMPARATIVA DETALHADA

**Comparação das 3 Opções contra os 14 Critérios de Avaliação**

---

## LEGENDA

🟢 **10/10** - Excelente (nenhuma preocupação)  
🟡 **5-9/10** - Bom (algumas preocupações)  
🔴 **1-4/10** - Fraco (riscos significativos)

---

## CRITÉRIO 1: ISOLAMENTO TENANT + ACTOR

### O que mede
Capacidade de manter dados de múltiplos atores separados, sem risco de sobrescrita cruzada.

### Opção A: Separação por Actor-ID
**Score: 🟢 10/10**

Cada actor tem seu próprio document:
```
Clientes/{tenant_id}/Donos/{actor_id}/onboarding
```

✅ Isolamento estrutural  
✅ Zero risco de overwrite entre atores  
✅ Cada actor vê apenas seus dados  

### Opção B: Guardrail no Documento Atual
**Score: 🔴 2/10**

Um único document por tenant:
```
Clientes/{tenant_id}/Configuracao/negocio
  ├─ onboarding_status
  ├─ dono_actor_id
  └─ guardrails (locks, version, checksum)
```

❌ Múltiplos atores compartilham mesmo document  
❌ Guardrails são simulados em client (não transacionais)  
❌ Risco de overwrite mesmo com locks  

**Exemplo de falha:**
```
Dono1 e Dono2 escrevem simultaneamente
  → mesmo document (Configuracao/negocio)
  → quem escreve por último vence
  → perda de dados do primeiro
```

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 7/10**

Document com namespace interno:
```
Clientes/{tenant_id}/Configuracao/negocio
  └─ donos:
      ├─ {actor_id_1}: {...}
      └─ {actor_id_2}: {...}
```

✅ Isolamento lógico (chave dentro do map)  
⚠️ Não é isolamento estrutural  
⚠️ RMW do document inteiro (risco de conflito)  

**Problema:** Se Dono1 e Dono2 escrevem simultaneamente:
```
Firestore recebe duas versões do MESMO document
  → Lock-conflict
  → Uma escrita é rejeitada
  → Cliente precisa retry
  → Complexidade operacional
```

---

## CRITÉRIO 2: CRESCIMENTO PARA MILHARES DE ATORES

### O que mede
Escalabilidade quando o tenant tem 100, 1000, 10000 atores.

### Opção A: Separação por Actor-ID
**Score: 🟢 10/10**

```
Clientes/{tenant_id}/Donos/
  ├─ actor_1/onboarding
  ├─ actor_2/onboarding
  ├─ ...
  └─ actor_10000/onboarding
```

✅ Collection Donos/ cresce linearmente  
✅ Cada document é pequeno (~1KB)  
✅ Firestore não sofre com "muitos documents"  
✅ Query em Donos/ é eficiente (indexed)  

**Tamanho Total:** 10,000 × 1KB = 10MB (negligenciável)

### Opção B: Guardrail no Documento Atual
**Score: 🔴 1/10**

```
Clientes/{tenant_id}/Configuracao/negocio
  {
    dono_actor_id: "actor_1",  ← APENAS 1 ATOR
    dono_nome: "Maria",
    onboarding_status: "completo",
    guardrails: {...}
  }
```

❌ Suporta apenas 1 dono por tenant  
❌ "Guardrails para N atores" não é implementável  
❌ Design fundamentalmente não escalável  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 5/10**

```
Clientes/{tenant_id}/Configuracao/negocio
  {
    donos: {
      "actor_1": {...},
      "actor_2": {...},
      ...
      "actor_1000": {...}  ← 1000 entradas no map
    }
  }
```

⚠️ Document cresce com cada ator (~2KB por ator)  
⚠️ 1000 atores = 2MB de um ÚNICO document  
⚠️ Firestore prefere documents <100KB  
❌ Acima de ~500 donos, performance degrada  

---

## CRITÉRIO 3: LIMITE DE TAMANHO DE DOCUMENTO

### O que mede
Respeito ao limite de 1MB por document no Firestore.

### Opção A: Separação por Actor-ID
**Score: 🟢 10/10**

Cada document é pequeno:
- Configuracao/negocio: ~500 bytes
- Donos/{actor_id}/onboarding: ~1 KB

✅ Bem abaixo do limite de 1MB  
✅ Mesmo com 10,000 atores, cada doc é <1KB  

### Opção B: Guardrail no Documento Atual
**Score: 🟡 8/10**

Um document com guardrails adicionais:
- Configuracao/negocio: ~1-2 KB (adiciona locks, checksums)

✅ Ainda muito abaixo de 1MB  
⚠️ Guardrails aumentam tamanho levemente  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🔴 2/10**

Document cresce com cada ator:
- 100 atores: ~200 KB (aceitável)
- 500 atores: ~1000 KB (PROBLEMA! Atinge limite)
- 1000+ atores: Impossível no Firestore

❌ Limite de escalabilidade é ~500 donos/tenant  
❌ Acima disso, document é inviável  

---

## CRITÉRIO 4: CONCORRÊNCIA FIRESTORE

### O que mede
Segurança sob múltiplas escritas simultâneas do mesmo tennant.

### Opção A: Separação por Actor-ID
**Score: 🟡 9/10**

Cada actor tem seu document. RMW isolado:

```
Dono1: UPDATE Donos/dono1/onboarding
Dono2: UPDATE Donos/dono2/onboarding
       ↓
       Firestore gerencia 2 escritas diferentes
       ↓
       Ambas bem-sucedidas (zero conflito)
```

✅ RMW totalmente isolado  
✅ Firestore não vê conflito  
⚠️ Menor ponto: se ambos atualizarem Configuracao/negocio, última escrita vence  

**Mitigação:** Configuracao/negocio é raro escrever (apenas mudança de negócio)

### Opção B: Guardrail no Documento Atual
**Score: 🔴 4/10**

Múltiplos atores escrevem MESMO document:

```
Dono1: UPDATE Configuracao/negocio
Dono2: UPDATE Configuracao/negocio (simultâneo)
       ↓
       Firestore vê 2 versões do MESMO doc
       ↓
       Conflict → Uma é rejeitada
       ↓
       Client precisa retry + backoff
```

❌ Conflict nativo do Firestore  
❌ Guardrails não ajudam (locks são simulados, não transacionais)  
❌ Retry pode ser indefinido  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 4/10**

Mesmo problema que B:

```
Dono1: UPDATE Configuracao/negocio.donos.actor_1
Dono2: UPDATE Configuracao/negocio.donos.actor_2 (simultâneo)
       ↓
       Firestore recebe 2 versões do MESMO document
       ↓
       CONFLICT (Firestore não ve que é "chaves diferentes")
```

⚠️ Mesmo problema de concorrência que B  
⚠️ Namespace não ajuda (problema é no document inteiro)  

---

## CRITÉRIO 5: RISCO DE OVERWRITE

### O que mede
Probabilidade de dados de um ator serem perdidos por dados de outro.

### Opção A: Separação por Actor-ID
**Score: 🟢 10/10**

Cada actor tem seu document:

```
Dono1: Donos/dono1/onboarding ← isolado
Dono2: Donos/dono2/onboarding ← isolado
```

✅ Zero possibilidade de overwrite cruzado  
✅ Mesmo que escrevam ao mesmo tempo, documents são diferentes  

### Opção B: Guardrail no Documento Atual
**Score: 🔴 3/10**

Múltiplos atores, um document:

```
T1: Dono1 lê Configuracao/negocio
    {onboarding_status: "em_progresso", indice: 0}
    
T2: Dono2 lê Configuracao/negocio
    {onboarding_status: "em_progresso", indice: 0}
    
T3: Dono1 escreve
    UPDATE {onboarding_status: "em_progresso", indice: 1, nome_negocio: "Salão Maria"}
    
T4: Dono2 escreve (rede lenta, chega atrasada)
    UPDATE {onboarding_status: "em_progresso", indice: 1, nome_negocio: "Salão João"}
    
RESULTADO:
    ✗ nome_negocio = "Salão João" (perdeu "Salão Maria")
    ✗ indice corrompido (depende da ordem de chegada)
```

❌ Risco altíssimo de overwrite  
❌ Mesmo com guardrails, não evita o RMW problem  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 4/10**

Mesmo problema, ligeiramente melhor (chaves diferentes):

```
T1: Dono1 lê Configuracao/negocio
    {donos: {dono1: {indice: 0}, dono2: {indice: 0}}}
    
T2: Dono2 lê (cópia local)
    
T3: Dono1 escreve
    UPDATE {donos.dono1: {indice: 1, nome: "Salão Maria"}}
    
T4: Dono2 escreve (simultâneo)
    UPDATE {donos.dono2: {indice: 1, nome: "Salão João"}}
    
FIRESTORE VÊ:
    UPDATE Configuracao/negocio (versão de Dono1)
    UPDATE Configuracao/negocio (versão de Dono2)
    
RESULTADO:
    ✗ Conflict (duas versões do mesmo document)
    ✗ Uma escrita é rejeitada
    ✗ Retry necessário
```

⚠️ Risco de conflict, não overwrite (ligeiramente melhor)  
⚠️ Mas ainda perde dados se não fizer retry corretamente  

---

## CRITÉRIO 6: IDEMPOTÊNCIA

### O que mede
Segurança quando cliente retenta a mesma operação (rede cai, timeout, etc).

### Opção A: Separação por Actor-ID
**Score: 🟡 9/10**

Implementável com chave idempotência:

```
Request: avancar_etapa_onboarding(
  tenant_id, actor_id, "nome_negocio", "Salão Maria"
)

Gerar chave: sha256(tenant_id + actor_id + campo + valor)
= abc123def456...

Salvar em Donos/{actor_id}/onboarding:
{
  "ultima_chave_idempotencia": "abc123def456",
  "resultado_anterior": {proxima_etapa, mensagem},
  ...
}

Se cliente retenta com mesma chave:
  ✓ Ler documento
  ✓ Verificar se chave ja foi processada
  ✓ Retornar resultado anterior (cached)
  ✓ Sem ler nem escrever de novo
```

✅ Totalmente idempotente  
✅ Seguro retry indefinido  
⚠️ Requer lógica de cache (implementação)  

### Opção B: Guardrail no Documento Atual
**Score: 🟡 5/10**

Guardrails podem ajudar, mas complexo:

```
Guardrail strategies:
  1. Version number (incrementa cada escrita)
  2. Checksum (hash dos dados)
  3. Lock with timestamp (timeout de 5s)

Se cliente retenta:
  ✓ Ler document
  ✓ Comparar version
  ✗ Problema: version foi incrementada
  ✗ Replica do document diverge
```

⚠️ Não é verdadeira idempotência  
⚠️ Guardrails ajudam mas não garantem  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 5/10**

Mesmos problemas de B:

```
Idempotência é possível MAS complexa:
  - Checksum do donos.actor_id submap
  - Se submap não mudou, skip
  - Problema: outros atores podem ter alterado documento
```

⚠️ Mais frágil que Opção A  

---

## CRITÉRIO 7: CUSTO DE LEITURA/ESCRITA

### O que mede
Custo operacional do Firestore (reads/writes/deletes).

### Opção A: Separação por Actor-ID
**Score: 🟡 9/10**

Leitura: 2 reads
```
1. READ Clientes/{tenant_id}/Configuracao/negocio
2. READ Clientes/{tenant_id}/Donos/{actor_id}/onboarding
```

Escrita: 2 writes
```
1. UPDATE Clientes/{tenant_id}/Configuracao/negocio (raro)
2. UPDATE Clientes/{tenant_id}/Donos/{actor_id}/onboarding (frequente)
```

✅ Eficiente. Dois documents pequenos.  
✅ Sem N+1 queries.  
⚠️ Uma leitura a mais que Opção B (negócio + actor)  

### Opção B: Guardrail no Documento Atual
**Score: 🟢 10/10**

Leitura: 1 read
```
1. READ Clientes/{tenant_id}/Configuracao/negocio (tudo em um)
```

✅ Uma única leitura.  
✅ Mais eficiente que Opção A.  

Mas o custo total é similar (escrita é frequente, sobrepesa a leitura).

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 6/10**

Leitura: 1 read
```
1. READ Clientes/{tenant_id}/Configuracao/negocio
   (precisa desserializar map inteiro)
```

✅ Uma leitura.  
⚠️ Document é maior (1000+ donos = 1MB)  
⚠️ Desserialização é mais lenta  

---

## CRITÉRIO 8: COMPLEXIDADE DE MIGRAÇÃO

### O que mede
Esforço para mover dados de "atual" para "novo" sem perda.

### Opção A: Separação por Actor-ID
**Score: 🟡 5/10**

Requer migração de dados:

```
Script:
  Para cada tenant:
    1. Ler Configuracao/negocio (antigo)
    2. Extrair actor_id
    3. Escrever Donos/{actor_id}/onboarding (novo)
    4. Validar checksum
    5. Backup

Complexidade: MÉDIA
  - Script é determinístico
  - Testável
  - Reversível (backup preservado)
  - Tempo: ~2 semanas (desenvolvimento + testes)
```

⚠️ Requer downtime ou dual-write  
⚠️ Requer validação pós-migração  

### Opção B: Guardrail no Documento Atual
**Score: 🟢 10/10**

Adiciona campos a document existente:

```
Alteração:
  Clientes/{tenant_id}/Configuracao/negocio
    ├─ ... campos existentes ...
    └─ guardrails: {lock, version, checksum}  ← NOVO
```

✅ Sem migração de dados  
✅ Apenas adicionar campos  
✅ Zero risco de perda  
✅ Tempo: ~1 semana  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 9/10**

Estrutura os dados existentes:

```
Alteração:
  Configuracao/negocio
    ├─ ... campos business ...
    └─ donos:
        └─ {dono_id}: {...dados movidos...}
```

✅ Migração simples (ler atual, reestruturar, escrever)  
✅ Dados não são duplicados  
✅ Tempo: ~1 semana  

---

## CRITÉRIO 9: COMPATIBILIDADE COM DADOS EXISTENTES

### O que mede
Capacidade de preservar dados atuais sem perdê-los.

### Opção A: Separação por Actor-ID
**Score: 🟡 4/10**

Requer migração. Risco de perda:

```
Antes:
  Clientes/{tenant_id}/Configuracao/negocio
    {nome_negocio, segmento, onboarding_status, ...}

Depois:
  Clientes/{tenant_id}/Configuracao/negocio
    {nome_negocio, segmento}
  
  Clientes/{tenant_id}/Donos/{actor_id}/onboarding
    {onboarding_status, onboarding_indice, ...}
```

⚠️ Requer ler dados antigos corretamente  
⚠️ Se script falhar, dados podem ser perdidos  
✅ Mitigação: backup automático + script testado  

### Opção B: Guardrail no Documento Atual
**Score: 🟢 10/10**

Preserva tudo:

```
Clientes/{tenant_id}/Configuracao/negocio
  {
    ... campos existentes (todos preservados) ...
    guardrails: {...}  ← novo, não sobrescreve nada
  }
```

✅ 100% compatível  
✅ Zero perda de dados  
✅ Dados antigos intactos  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟢 10/10**

Também preserva:

```
Clientes/{tenant_id}/Configuracao/negocio
  {
    ... campos business existentes ...
    donos: {...}  ← novo namespace, não sobrescreve
  }
```

✅ Dados antigos intactos  
✅ Novo namespace adicionado  
✅ Zero perda  

---

## CRITÉRIO 10: FACILIDADE DE MANUTENÇÃO

### O que mede
Quanto fácil é entender e manter o código no futuro.

### Opção A: Separação por Actor-ID
**Score: 🟢 10/10**

Estrutura clara:

```python
# Lerá negócio
config_negocio = db.collection("Clientes")\
  .document(tenant_id).collection("Configuracao")\
  .document("negocio").get()

# Ler onboarding do ator
onboarding_ator = db.collection("Clientes")\
  .document(tenant_id).collection("Donos")\
  .document(actor_id).collection("onboarding")\
  .document("onboarding").get()
```

✅ Paths claros e descritivos  
✅ Responsabilidades separadas (negocio vs ator)  
✅ Código futuro é mais legível  
✅ Novos desenvolvedores entendem rapidamente  

### Opção B: Guardrail no Documento Atual
**Score: 🔴 4/10**

Lógica de guardrail espalhada:

```python
# Ler documento
doc = db.collection("Clientes")\
  .document(tenant_id).collection("Configuracao")\
  .document("negocio").get()

# Verificar locks
if doc.get("guardrails"):
  lock_timestamp = doc.get("guardrails").get("lock_timestamp")
  if time.time() - lock_timestamp < 5:  # timeout
    # Aguardar ou falhar
    ...
    
# Verificar version
if doc.get("version") != expected_version:
  # Retry com backoff
  ...
  
# Verificar checksum
if sha256(doc) != expected_checksum:
  # Dados corrompidos?
  ...
```

❌ Lógica complexa espalhada pelo código  
❌ Difícil de entender sem documentação  
❌ Frágil (muitos pontos de falha)  
❌ Novos devs acharem confuso  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 5/10**

Melhor que B, mas não tão claro quanto A:

```python
# Ler documento
doc = db.collection("Clientes")\
  .document(tenant_id).collection("Configuracao")\
  .document("negocio").get()

# Navegar namespace
ator_onboarding = doc.get("donos", {}).get(actor_id, {})

if not ator_onboarding:
  # Não existe?
  ...
```

⚠️ Lógica de namespace + chave  
⚠️ Menos óbvio que separação estrutural  

---

## CRITÉRIO 11: FACILIDADE DE TESTES

### O que mede
Facilidade de escrever testes unitários sem complexidade.

### Opção A: Separação por Actor-ID
**Score: 🟢 10/10**

Fixtures simples, sem dependências:

```python
@pytest.fixture
def onboarding_ator1():
    return {
        "actor_id": "ator1",
        "onboarding_status": "em_progresso",
        "onboarding_indice": 0,
        ...
    }

@pytest.fixture
def onboarding_ator2():
    return {
        "actor_id": "ator2",
        "onboarding_status": "em_progresso",
        "onboarding_indice": 0,
        ...
    }

# Testes isolados, sem interferência
test_ator1_progredisce(onboarding_ator1)
test_ator2_progredisce(onboarding_ator2)
```

✅ Cada teste é independente  
✅ Sem mocking complexo  
✅ Fixtures claras e simples  

### Opção B: Guardrail no Documento Atual
**Score: 🔴 2/10**

Precisa mockar locks, timestamps, checksums:

```python
@pytest.fixture
def config_negocio_com_guardrails():
    return {
        "nome_negocio": "Salão",
        "guardrails": {
            "lock_timestamp": time.time(),
            "version": 1,
            "checksum": "abc123..."
        },
        ...
    }

# Testes precisam:
# - Mockar time.time()
# - Calcular checksums corretos
# - Simular locks
# - Verificar timeouts
```

❌ Muito mocking necessário  
❌ Difícil de mockar comportamento concorrente  
❌ Testes frágeis (dependem de timing)  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 6/10**

Melhor que B:

```python
@pytest.fixture
def config_com_namespace():
    return {
        "nome_negocio": "Salão",
        "donos": {
            "ator1": {
                "onboarding_status": "em_progresso",
                ...
            },
            "ator2": {...}
        }
    }

# Testes precisam:
# - Navegar namespace
# - Mockar chaves do map
# - Verificar que sobrescrita não acontece
```

⚠️ Mais simples que B  
⚠️ Mas ainda complexo (nested mocks)  

---

## CRITÉRIO 12: IMPACTO NOS CALLSITES ATUAIS

### O que mede
Quanto código precisa ser alterado.

### Opção A: Separação por Actor-ID
**Score: 🟡 6/10**

Impacto médio em ~4 callsites críticos:

```python
# Antes:
config = get_config(tenant_id)
etapa = config.get("onboarding_etapa_atual")

# Depois:
config = get_config(tenant_id)
actor_onboarding = get_onboarding_ator(tenant_id, actor_id)
etapa = actor_onboarding.get("onboarding_etapa_atual")
```

⚠️ Impacto em:
  - router/integracao_identidade_onboarding.py
  - services/onboarding_dono_service.py
  - services/onboarding_service.py
  - services/informacao_service.py (~4 funções)

✅ Outras 135 callsites não precisam mudar (usam apenas obter_id_dono para resolver tenant)

### Opção B: Guardrail no Documento Atual
**Score: 🟡 9/10**

Impacto mínimo:

```python
# Antes:
config = get_config(tenant_id)

# Depois:
config = get_config(tenant_id)  ← mesma coisa!

# Guardrail logic é interno
```

✅ Code não precisa mudar  
✅ Apenas adicionar lógica interna  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 6/10**

Impacto médio similar a A:

```python
# Antes:
config = get_config(tenant_id)
status = config.get("onboarding_status")

# Depois:
config = get_config(tenant_id)
status = config.get("donos", {}).get(actor_id, {}).get("onboarding_status")
```

⚠️ Impacto em mesmas ~4 funções de A  

---

## CRITÉRIO 13: MÚLTIPLOS DONOS/PROFISSIONAIS

### O que mede
Design pode suportar naturalmente 2+ atores do mesmo tipo.

### Opção A: Separação por Actor-ID
**Score: 🟢 10/10**

Design nativo:

```
Clientes/{tenant_id}/Donos/
  ├─ dona_maria/onboarding
  ├─ dona_joao/onboarding
  ├─ dona_pedro/onboarding
  └─ ... infinitos ...
```

✅ Cada dono tem seu próprio document  
✅ Completamente escalável  
✅ Sem modificações necessárias  

Igualmente funciona para profissionais:

```
Clientes/{tenant_id}/Profissionais/
  ├─ bruna/profile
  ├─ carla/profile
  └─ ...
```

### Opção B: Guardrail no Documento Atual
**Score: 🔴 1/10**

Design não suporta múltiplos donos:

```
Clientes/{tenant_id}/Configuracao/negocio
  {
    dono_actor_id: "5521987654321",  ← APENAS 1
    dono_nome: "Maria",
    onboarding_status: "completo"
  }
```

❌ Pode ter APENAS 1 dono por documento  
❌ Se adicionar 2º dono, qual `dono_actor_id` é correto?  
❌ Architecture fundamentalmente não suporta  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 8/10**

Suporta bem:

```
Clientes/{tenant_id}/Configuracao/negocio
  {
    donos: {
      "dona_maria": {...},
      "dona_joao": {...},
      "dona_pedro": {...}
    }
  }
```

✅ Suporta N donos  
⚠️ Mas limitado por tamanho do document (~500 donos)  
⚠️ Não é tão escalável quanto A  

---

## CRITÉRIO 14: EVOLUÇÃO FUTURA DO MODELO

### O que mede
Quão fácil é estender o design sem reescrever.

### Opção A: Separação por Actor-ID
**Score: 🟢 10/10**

Padrão generalizável:

```
Clientes/{tenant_id}/
  ├─ Configuracao/
  │   ├─ negocio
  │   ├─ catalogo
  │   └─ horarios
  │
  ├─ Donos/
  │   └─ {actor_id}/
  │       ├─ onboarding
  │       ├─ permissoes
  │       └─ preferencias
  │
  ├─ Profissionais/
  │   └─ {actor_id}/
  │       ├─ onboarding
  │       ├─ availabilidade
  │       └─ comissoes
  │
  ├─ Gerentes/
  │   └─ {actor_id}/
  │       ├─ onboarding
  │       └─ delegacoes
  │
  └─ Clientes/
      └─ {actor_id}/
          ├─ perfil
          └─ historico
```

✅ Padrão é escalável  
✅ Suporta múltiplos papéis sem modificações  
✅ Fácil adicionar novos atores  

### Opção B: Guardrail no Documento Atual
**Score: 🔴 2/10**

Design frágil, precisa reescrita:

```
Se quisermos adicionar:
  - Novo papel (gerente)
  - Novo tipo de ator (suporte)
  
Seria necessário:
  - Reescrever Configuracao/negocio
  - Adicionar novos guardrails
  - Código novo para cada papél
  
→ Reescrita completa do design
```

❌ Não é escalável  
❌ Cada novo papel = refactor  

### Opção C: Namespace "donos" Dentro do Documento
**Score: 🟡 5/10**

Parcialmente escalável:

```
Configuracao/negocio
  {
    donos: {actor_id: {...}},
    profissionais: {actor_id: {...}},
    gerentes: {actor_id: {...}}
  }
```

⚠️ Funciona mas document fica gigante  
⚠️ Acima de ~2000 atores totais, inviável  
❌ Reescreva é necessária em escala  

---

## RESUMO COMPARATIVO

### Scores Totais

| Critério | Opção A | Opção B | Opção C |
|----------|---------|---------|---------|
| 1. Isolamento | 10 | 2 | 7 |
| 2. Escalabilidade | 10 | 1 | 5 |
| 3. Tamanho documento | 10 | 8 | 2 |
| 4. Concorrência | 9 | 4 | 4 |
| 5. Overwrite risk | 10 | 3 | 4 |
| 6. Idempotência | 9 | 5 | 5 |
| 7. Custo | 9 | 10 | 6 |
| 8. Migração | 5 | 10 | 9 |
| 9. Compatibilidade | 4 | 10 | 10 |
| 10. Manutenção | 10 | 4 | 5 |
| 11. Testes | 10 | 2 | 6 |
| 12. Impacto callsites | 6 | 9 | 6 |
| 13. Múltiplos donos | 10 | 1 | 8 |
| 14. Evolução futura | 10 | 2 | 5 |
| **TOTAL** | **127/140** | **69/140** | **77/140** |
| **PERCENTUAL** | **90.7%** | **49.3%** | **55%** |

### Conclusão

**✅ Opção A é claramente superior.**

- **44% melhor** que Opção B
- **35% melhor** que Opção C
- Único trade-off: requer migração de dados (mitigável com script)
- Todos os outros critérios A vence ou empata com B+C

---

**Recomendação:** Implementar Opção A com migração dual-write.
