# GATE C3.15 — PLANO DE IMPLEMENTAÇÃO CONTROLADA DO ONBOARDING ISOLADO

**Data:** 2026-09-26  
**Escopo:** Planejamento completo para implementar Opção A (isolamento por actor_id)  
**Status:** Plano detalhado, zero implementação  
**Precedência:** C3.13 ✅, C3.14 ✅, C3.14-R1 ✅  

---

## FASE 1: DIAGNÓSTICO DO CÓDIGO ATUAL

### 1.1 Estado Atual Mapeado

**Path Atual:**
```
Clientes/{tenant_id}/Configuracao/negocio (1 documento por tenant)
```

**Conteúdo Atual (onboarding_dono_service.py:50-61):**
```python
config_data = {
    "tenant_id": tenant_id,                      # A — Negócio
    "onboarding_status": "em_progresso",         # B — Estado ator
    "onboarding_etapa_atual": "nome_negocio",    # B — Estado ator
    "onboarding_indice": 0,                      # B — Estado ator
    "criado_em": now,                            # C — Metadado
    "criado_por": actor_id,                      # C — Rastreabilidade
    "atualizado_em": now,                        # C — Metadado
    "dono_actor_id": actor_id,                   # C — Identidade
    "dono_nome": dono_nome,                      # A — Negócio
    "dono_email": dono_email                     # A — Negócio
}
```

**Problema Crítico:** Um documento compartilhado (tenant-wide) para estado que deveria ser isolado (actor-specific).

---

### 1.2 Funções Afetadas Hoje

#### A. services/onboarding_dono_service.py

| Função | Linhas | Operação | Path Lido | Path Escrito |
|--------|--------|----------|-----------|--------------|
| `iniciar_onboarding_dono()` | 30-80 | CREATE | — | `Configuracao/negocio` (`.set()`) |
| `pegar_etapa_onboarding()` | 83-114 | READ | `Configuracao/negocio` | — |
| `avancar_etapa_onboarding()` | 117-188 | UPDATE | `Configuracao/negocio` | `Configuracao/negocio` (.update()) |
| `marcar_onboarding_completo()` | 252-279 | UPDATE | — | `Configuracao/negocio` (.update()) |
| `validar_onboarding_minimo()` | 282-343 | READ | `Configuracao/negocio` | — |

#### B. router/integracao_identidade_onboarding.py

| Função | Linhas | Callsite |
|--------|--------|----------|
| `resolver_ator_e_validar_guard()` | 107 | `pegar_etapa_onboarding(tenant_id)` |
| (mesmo) | 221 | `iniciar_onboarding_dono(tenant_id, actor_id, ...)` |
| `processar_fluxo_identidade_onboarding()` | 298-355 | Chamada a `resolver_ator_e_validar_guard()` |

#### C. services/onboarding_service.py

| Função | Linhas | Callsite |
|--------|--------|----------|
| `processar_resposta_onboarding_dono()` | 227-333 | `pegar_etapa_onboarding(tenant_id)` (linha 256) |
| (mesmo) | (mesmo) | `avancar_etapa_onboarding(...)` (linha 282) |

---

### 1.3 Callsites de obter_id_dono()

**Total:** 139 callsites  
**Impactado por C3.15:** 0 (obter_id_dono resolve apenas tenant_id, não afeta onboarding diretamente)  
**Críticos para C3.15:** ~4 que leem/escrevem onboarding

---

## FASE 2: CONTRATO FINAL

### 2.1 Função: iniciar_onboarding_dono()

**Assinatura:**
```python
async def iniciar_onboarding_dono(
    tenant_id: str,
    actor_id: str,
    dono_nome: str,
    dono_email: str
) -> dict
```

**Responsabilidade:**
Inicia onboarding isolado por actor. Idempotente. Não sobrescreve onboarding completo.

**Entrada:**
| Parâmetro | Tipo | Validação | Origem |
|-----------|------|-----------|--------|
| `tenant_id` | str | Não vazio, 10 dígitos | `resolverit_ator_por_canal()` |
| `actor_id` | str | Normalizado, phone | `criar_ator_dono()` |
| `dono_nome` | str | Não vazio, < 100 chars | usuário |
| `dono_email` | str | Email válido (basic), < 100 chars | usuário |

**Saída (Sucesso):**
```python
{
    "status": "iniciado" | "resuming",
    "etapa_atual": str,  # "nome_negocio" ou última etapa
    "actor_id": str,
    "tenant_id": str,
    "proximo_passo": str  # Pergunta conversacional
}
```

**Saída (Erro):**
```python
{
    "status": "erro",
    "motivo": str,  # Específico
    "actor_id": str,
    "tenant_id": str
}
```

**Firestore Path:**
```
Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
```

**Transaction Boundary:**
```
T1: READ Donos/{actor_id}/onboarding/ativo (exist?)
T2: If exists and completo → ERROR
T2: If exists and em_progresso → RETURN resuming
T3: If not exists → CREATE new document
```

**Idempotência:**
- ✅ Chamar 2x com mesmo (tenant_id, actor_id): retorna `resuming`
- ✅ Chamar 2x com webhook duplicado: transação garante only-once creation

**Concorrência:**
- ✅ Webhook1 e Webhook2 simultâneos: Firestore .set() garante atomicidade
- ✅ Risco 0 de sobrescrita

**Ownership:**
- ✅ Documento pertence a `actor_id`
- ✅ Apenas `actor_id` pode ler/escrever seu onboarding

**Comportamento Legacy:**
- Se já existe em `Configuracao/negocio.onboarding_etapa_atual`:
  - Detectar e criar novo documento em `Donos/{actor_id}/onboarding/ativo`
  - Copiar campos de estado (etapa, indice, status)
  - Marcar como migrado

**Comportamento em Retry:**
- Idempotente via transaction
- Mesmo (tenant, actor) → mesmo resultado

**Documento Não Existe:**
- Criar novo com estado inicial

---

### 2.2 Função: pegar_etapa_onboarding()

**Assinatura:**
```python
async def pegar_etapa_onboarding(
    tenant_id: str,
    actor_id: str  # ← NOVO PARÂMETRO
) -> dict | None
```

**Responsabilidade:**
Obtém etapa atual do onboarding isolado para um ator.

**Entrada:**
| Parâmetro | Tipo | Validação |
|-----------|------|-----------|
| `tenant_id` | str | Não vazio |
| `actor_id` | str | Normalizado, phone |

**Saída (Sucesso):**
```python
{
    "etapa_atual": str,
    "indice": int,
    "status": str,  # "em_progresso" | "completo" | "parado"
    "dados": dict  # Todos os campos do documento
}
```

**Saída (Não Encontrado):**
```python
None
```

**Firestore Path:**
```
Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
```

**Transaction Boundary:**
```
T1: READ Donos/{actor_id}/onboarding/ativo
T2: Return dados ou None
```

**Idempotência:**
- ✅ Chamadas repetidas: mesmo resultado

**Concorrência:**
- ✅ Read-only, sem risco

**Ownership:**
- ✅ Verificar se `doc.actor_id == actor_id`
- ✅ Se diferente, retornar None (access denied)

**Comportamento Legacy:**
- Se não encontra em novo path, tentar `Configuracao/negocio`
- Se encontra legado: copiar para novo path, retornar novo
- Se legado `dono_actor_id != actor_id`: retornar None

**Documento Não Existe:**
- Retornar None

---

### 2.3 Função: avancar_etapa_onboarding()

**Assinatura:**
```python
async def avancar_etapa_onboarding(
    tenant_id: str,
    actor_id: str,  # ← NOVO PARÂMETRO
    campo: str,
    valor: str
) -> dict
```

**Responsabilidade:**
Avança para próxima etapa. Valida campo esperado. Usa transaction para atomicidade.

**Entrada:**
| Parâmetro | Tipo | Validação | Descrição |
|-----------|------|-----------|-----------|
| `tenant_id` | str | Não vazio | Tenant do onboarding |
| `actor_id` | str | Normalizado | Owner do onboarding |
| `campo` | str | Em ETAPAS_ONBOARDING | Qual campo responde |
| `valor` | str | Validado por tipo | Resposta do usuário |

**Saída (Sucesso):**
```python
{
    "etapa_anterior": str,
    "etapa_atual": str,
    "proximo_passo": str,
    "status": "processado" | "idempotente"
}
```

**Saída (Erro):**
```python
{
    "status": "erro",
    "motivo": str,  # E.g., "Acesso negado", "Campo inválido"
    "campo": str,
    "valor": str
}
```

**Firestore Path:**
```
Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
```

**Transaction Boundary:**
```
T1: READ Donos/{actor_id}/onboarding/ativo
T2: VALIDATE (actor_id, campo, etapa esperada)
T3: VALIDATE valor
T4: UPDATE (campo, proxima_etapa, indice, idempotencia_key, atualizado_em)
T5: RETURN resultado
```

**Idempotência:**
```
Chave: sha256(f"{actor_id}:{campo}:{valor}")[:16]
Mecanismo: 
  - Ler idempotencia_key do documento
  - Se igual ao novo: SKIP (já foi processado)
  - Se diferente: processar normalmente, salvar nova chave
```

**Concorrência:**
```
Cenário: webhook1 e webhook2 avançam simultaneamente

T0: webhook1 lê doc (indice=0, etapa="nome_negocio")
T0: webhook2 lê doc (indice=0, etapa="nome_negocio")

T1: webhook1 escreve update (indice=1, etapa="segmento")
T2: webhook2 escreve update (indice=1, etapa="segmento")

FIRESTORE:
  - T1 sucede (primeira escritor ganha)
  - T2 falha em VALIDATE (etapa_esperada != etapa_atual agora)
  - Cliente2 reenvia (retry)
  - T3: webhook2 lê novamente (indice=1, etapa="segmento")
  - T3: campo="nome_negocio" != etapa_atual ("segmento")
  - T3: ERROR "Campo não esperado"

RESULTADO: ✅ Atomicidade garantida
```

**Ownership:**
- ✅ Validar `doc.actor_id == actor_id`
- ✅ Se falhar, retornar erro

**Comportamento Legacy:**
- Se não encontra em novo path, migrar de legacy primeiro
- Depois prosseguir normalmente

**Comportamento em Retry:**
- Idempotente via idempotencia_key
- Mesmo (tenant, actor, campo, valor) → mesmo resultado

**Documento Não Existe:**
- Retornar erro "Onboarding não iniciado"

---

### 2.4 Função: marcar_onboarding_completo()

**Assinatura:**
```python
async def marcar_onboarding_completo(
    tenant_id: str,
    actor_id: str  # ← NOVO PARÂMETRO
) -> bool
```

**Responsabilidade:**
Marca onboarding como completo. Copia dados para `Configuracao/negocio` se for o primeiro completo.

**Entrada:**
| Parâmetro | Tipo | Validação |
|-----------|------|-----------|
| `tenant_id` | str | Não vazio |
| `actor_id` | str | Normalizado |

**Saída (Sucesso):**
```python
True
```

**Saída (Erro):**
```python
False
```

**Firestore Paths:**
```
READ:  Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
WRITE: Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
WRITE: Clientes/{tenant_id}/Configuracao/negocio (se primeiro)
```

**Transaction Boundary:**
```
T1: READ Donos/{actor_id}/onboarding/ativo
T2: VALIDATE (onboarding_indice >= 8, todos campos preenchidos)
T3: UPDATE Donos/{actor_id}/onboarding/ativo
      {onboarding_status: "completo", concluido_em: now}
T4: READ Configuracao/negocio (dono_principal_actor_id exists?)
T5: If dono_principal_actor_id não existe:
      UPDATE Configuracao/negocio
        {dono_principal_actor_id: actor_id, dono_nome, ..., completado_em: now}
```

**Idempotência:**
- ✅ Se já marcado como completo: return True

**Ownership:**
- ✅ Validar `doc.actor_id == actor_id`

**Comportamento Legacy:**
- Se onboarding_status já era "completo": skip

**Documento Não Existe:**
- Retornar False

---

## FASE 3: INVARIANTES ARQUITETURAIS

### 3.1 Regras Imutáveis

1. **Isolamento Actor:**
   - Estado de onboarding pertence UNICAMENTE ao actor
   - Nunca compartilhar entre actors
   - Nunca permitir actor A ler/alterar onboarding de actor B

2. **Tenant Isolamento:**
   - Dados de tenant X não vazam para tenant Y
   - `tenant_id` no path garante isolamento estrutural

3. **Propriedade do Documento:**
   - Documento `Donos/{actor_id}/onboarding/ativo` pertence ao `actor_id`
   - Campo `doc.actor_id` deve ser igual ao path
   - Se divergir = corrupção, throw error

4. **Etapa Determinística:**
   - `onboarding_etapa_atual` determina qual campo responder
   - `onboarding_indice` é monotonicamente crescente
   - Nunca retroceder

5. **Primeiro Completo Vence:**
   - Apenas o primeiro actor a completar onboarding é registrado em `Configuracao/negocio.dono_principal_actor_id`
   - Campo é imutável após definido
   - Outros actors completam mas não sobrescrevem este campo

6. **Sem Query Global:**
   - Nunca buscar "onboarding do tenant" com query (query pode ser lenta, sem owner-check)
   - Sempre usar path determinístico: `Donos/{actor_id}/onboarding/ativo`

7. **Compatibilidade Legacy:**
   - Legacy path: `Configuracao/negocio`
   - Novo path: `Donos/{actor_id}/onboarding/ativo`
   - Nunca sobrescrever legacy com novo (versioned)
   - Migration é unidirecional (legacy → novo)

8. **Idempotência Baseada em Conteúdo:**
   - Chave: sha256(actor_id:campo:valor)
   - Mesmo conteúdo = mesma chave
   - Mesma chave = operação idempotente

9. **Atomicidade:**
   - Read-check-write deve ser transacional
   - Firestore `.transaction()` garante atomicidade

10. **Ownership Verificável:**
    - Cada operação verifica `doc.actor_id == actor_id`
    - Falha: throw access denied error

11. **Imutabilidade de Criador:**
    - Campo `criado_por` é definido uma vez, nunca alterado
    - Campo `dono_principal_actor_id` é definido uma vez, nunca alterado

12. **Sem Duas Fontes de Verdade Mutáveis:**
    - Estado de onboarding em `Donos/{actor_id}/` é a verdade
    - Legacy em `Configuracao/negocio` é SOMENTE referência/compatibilidade
    - Nunca sincronizar bidirecionalmente

---

## FASE 4: TRANSACTIONS

### 4.1 Padrão Firestore Transaction

**Sintaxe Padrão (Python SDK):**
```python
async def operacao_transacional(tenant_id, actor_id, ...):
    def transact(transaction):
        # 1. READ
        doc_ref = db.collection("Clientes").document(tenant_id)\
            .collection("Donos").document(actor_id)\
            .collection("onboarding").document("ativo")
        
        doc = transaction.get(doc_ref)
        
        # 2. VALIDATE
        if not doc.exists:
            raise ValueError("Document not found")
        
        data = doc.to_dict()
        if data.get("actor_id") != actor_id:
            raise ValueError("Access denied")
        
        # 3. WRITE
        transaction.update(doc_ref, {
            "campo": valor,
            "atualizado_em": now,
            ...
        })
        
        # 4. RETURN
        return resultado
    
    return await asyncio.to_thread(
        lambda: db.transaction()(transact)()
    )
```

### 4.2 Transações por Função

#### iniciar_onboarding_dono() - TRANSACTION

```
T1: READ Donos/{actor_id}/onboarding/ativo
    → Se exists && status != "completo": RETURN resuming
    → Se exists && status == "completo": THROW erro
    → Se not exists: CREATE

T2: WRITE Donos/{actor_id}/onboarding/ativo (new document)

GARANTIA: Atomicidade de criação
```

#### pegar_etapa_onboarding() - READ-ONLY

```
T1: READ Donos/{actor_id}/onboarding/ativo

GARANTIA: Nenhuma (read-only, sem write conflict)
```

#### avancar_etapa_onboarding() - TRANSACTION

```
T1: READ Donos/{actor_id}/onboarding/ativo
T2: VALIDATE (actor_id, etapa, campo, valor)
T3: CALCULATE proxima_etapa
T4: WRITE Donos/{actor_id}/onboarding/ativo

GARANTIA: Atomicidade de avanço (prevent concurrent etapa override)
```

#### marcar_onboarding_completo() - TRANSACTION

```
T1: READ Donos/{actor_id}/onboarding/ativo
T2: VALIDATE (todos campos preenchidos)
T3: WRITE Donos/{actor_id}/onboarding/ativo (mark completo)
T4: READ Configuracao/negocio (check dono_principal_actor_id)
T5: If dono_principal_actor_id not set:
      WRITE Configuracao/negocio (set dono_principal_actor_id)

GARANTIA: 
  - Atomicidade de conclusão
  - Apenas primeiro completo registrado
```

---

## FASE 5: IDEMPOTÊNCIA

### 5.1 Chave de Idempotência

**Definição:**
```python
import hashlib

def gerar_chave_idempotencia(actor_id: str, campo: str, valor: str) -> str:
    """
    Gera chave determinística baseada em conteúdo da operação.
    
    Não muda com retry ou timestamp.
    """
    texto = f"{actor_id}:{campo}:{valor}"
    return hashlib.sha256(texto.encode()).hexdigest()[:16]
```

**Exemplo:**
```
actor_id = "5521987654321"
campo = "nome_negocio"
valor = "Salão da Maria"

chave = gerar_chave_idempotencia(actor_id, campo, valor)
      = "sha256(5521987654321:nome_negocio:Salão da Maria)"[:16]
      = "abc123def456..." (16 chars)
```

### 5.2 Mecanismo de Verificação

```python
async def avancar_etapa_onboarding_idempotente(
    tenant_id: str, actor_id: str, campo: str, valor: str
):
    doc_ref = db.collection("Clientes").document(tenant_id)\
        .collection("Donos").document(actor_id)\
        .collection("onboarding").document("ativo")
    
    chave_atual = gerar_chave_idempotencia(actor_id, campo, valor)
    
    def transact(transaction):
        doc = transaction.get(doc_ref)
        data = doc.to_dict()
        
        # VERIFICA: Já foi processado com EXATAMENTE este conteúdo?
        chave_anterior = data.get("idempotencia_key")
        
        if chave_anterior == chave_atual:
            # ✅ SIM. Retornar resultado anterior (cached).
            return {
                "status": "idempotente",
                "etapa_atual": data.get("onboarding_etapa_atual"),
                "razao": "Mesmo conteúdo já foi processado"
            }
        
        # ❌ NÃO. Processar normalmente.
        # ... validação, calculo proxima etapa, etc ...
        
        # Salvar chave da operação para próximo retry
        transaction.update(doc_ref, {
            campo: valor,
            "onboarding_etapa_atual": proxima_etapa,
            "onboarding_indice": proxima_indice,
            "idempotencia_key": chave_atual,  # ← SALVAR
            "atualizado_em": now,
            "tentativas": data.get("tentativas", 0) + 1
        })
        
        return {
            "status": "processado",
            "etapa_anterior": etapa_anterior,
            "etapa_atual": proxima_etapa
        }
    
    return await asyncio.to_thread(
        lambda: db.transaction()(transact)()
    )
```

### 5.3 Cenários Cobertos

| Cenário | Chave | Resultado |
|---------|-------|-----------|
| Webhook original | `sha256(...)` | Processado, chave salva |
| Webhook retry (rede falhou) | `sha256(...)` (MESMA) | Idempotente, retorna resultado anterior |
| Usuário reenvia mesma mensagem 1h depois | `sha256(...)` (MESMA) | Idempotente |
| Usuário envia valor diferente | `sha256(...novo...)` (DIFERENTE) | Novo processamento, nova chave |
| Webhook duplicado de Meta | `sha256(...)` (MESMA) | Idempotente |

---

## FASE 6: LEGACY E MIGRAÇÃO

### 6.1 Detecção de Legacy

**Legacy é identificado por:**
```python
def eh_legacy(tenant_id: str) -> bool:
    """
    Verifica se existe dados de onboarding em caminho legado.
    """
    doc_ref = db.collection("Clientes").document(tenant_id)\
        .collection("Configuracao").document("negocio")
    
    doc = doc_ref.get()
    if not doc.exists:
        return False
    
    data = doc.to_dict()
    
    # Legacy tem estes campos em Configuracao/negocio
    return (
        "onboarding_status" in data or
        "onboarding_etapa_atual" in data or
        "onboarding_indice" in data or
        "dono_actor_id" in data
    )

def eh_legacy_de_actor(
    tenant_id: str, 
    actor_id: str
) -> bool:
    """
    Verifica se legacy pertence a este ator.
    """
    doc_ref = db.collection("Clientes").document(tenant_id)\
        .collection("Configuracao").document("negocio")
    
    doc = doc_ref.get()
    if not doc.exists:
        return False
    
    data = doc.to_dict()
    
    # Legacy pertence ao ator se dono_actor_id == actor_id
    return data.get("dono_actor_id") == actor_id
```

### 6.2 Migração de Legacy para Novo

**Fluxo:**
```
1. Detectar se legacy existe para (tenant_id, actor_id)
2. Se sim e pertence ao actor: migrar para novo path
3. Se sim mas não pertence: skip (outro ator é dono)
4. Se não: prosseguir normalmente

Migração = cópia estruturada + marca como migrado
```

**Pseudocódigo:**
```python
async def migrar_onboarding_legacy_se_necessario(
    tenant_id: str,
    actor_id: str
) -> bool:
    """
    Migra legacy para novo path se necessário.
    Retorna True se migrado, False se já novo ou sem legacy.
    """
    
    # 1. Verificar se legacy existe
    legacy_ref = db.collection("Clientes").document(tenant_id)\
        .collection("Configuracao").document("negocio")
    
    legacy_doc = legacy_ref.get()
    if not legacy_doc.exists:
        return False  # Sem legacy
    
    legacy_data = legacy_doc.to_dict()
    
    # 2. Verificar se pertence ao actor
    if legacy_data.get("dono_actor_id") != actor_id:
        return False  # Legacy pertence a outro actor
    
    # 3. Preparar novo documento
    novo_data = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "onboarding_status": legacy_data.get("onboarding_status", "em_progresso"),
        "onboarding_etapa_atual": legacy_data.get("onboarding_etapa_atual", "nome_negocio"),
        "onboarding_indice": legacy_data.get("onboarding_indice", 0),
        "criado_em": legacy_data.get("criado_em"),
        "criado_por": legacy_data.get("criado_por"),
        "atualizado_em": legacy_data.get("atualizado_em"),
        "dono_nome": legacy_data.get("dono_nome"),
        "dono_email": legacy_data.get("dono_email"),
        "nome_negocio": legacy_data.get("nome_negocio"),
        "segmento": legacy_data.get("segmento"),
        "endereco": legacy_data.get("endereco"),
        # ... copiar todos os campos ...
        "migrado_de_legacy": True,
        "migrado_em": now
    }
    
    # 4. Escrever no novo path
    novo_ref = db.collection("Clientes").document(tenant_id)\
        .collection("Donos").document(actor_id)\
        .collection("onboarding").document("ativo")
    
    novo_ref.set(novo_data)
    
    return True  # Migração completa
```

### 6.3 Garfo de Legacy

**Quando chamar pegar_etapa_onboarding(tenant_id, actor_id):**

```python
async def pegar_etapa_onboarding(tenant_id: str, actor_id: str) -> dict | None:
    # 1. Tentar novo path
    novo_ref = db.collection("Clientes").document(tenant_id)\
        .collection("Donos").document(actor_id)\
        .collection("onboarding").document("ativo")
    
    novo_doc = novo_ref.get()
    
    if novo_doc.exists:
        # ✅ Encontrou no novo path
        return {
            "etapa_atual": novo_doc.get("onboarding_etapa_atual"),
            "indice": novo_doc.get("onboarding_indice"),
            "status": novo_doc.get("onboarding_status"),
            "dados": novo_doc.to_dict()
        }
    
    # 2. Se não encontrou, tentar legacy (SOMENTE para compat)
    legacy_ref = db.collection("Clientes").document(tenant_id)\
        .collection("Configuracao").document("negocio")
    
    legacy_doc = legacy_ref.get()
    
    if legacy_doc.exists:
        legacy_data = legacy_doc.to_dict()
        
        # ✅ Legacy existe mas pertence a outro actor?
        if legacy_data.get("dono_actor_id") != actor_id:
            return None  # Não é seu onboarding
        
        # ✅ Legacy pertence ao ator. Migrar e retornar.
        await migrar_onboarding_legacy_se_necessario(tenant_id, actor_id)
        
        return {
            "etapa_atual": legacy_data.get("onboarding_etapa_atual"),
            "indice": legacy_data.get("onboarding_indice"),
            "status": legacy_data.get("onboarding_status"),
            "dados": legacy_data.to_dict(),
            "nota": "Migrado de legacy"
        }
    
    # 3. Nenhum encontrado
    return None
```

### 6.4 Preservação de Legacy

**Legacy é preservado:**
- ✅ Não deletar `Configuracao/negocio.onboarding_*` após migração
- ✅ Apenas marcar como migrado (campo `migrado_em`)
- ✅ Deixar campo legado para auditoria
- ✅ Versão nova é a fonte de verdade

**Rollback é possível:**
- Se novo path falhar: tentar ler legacy e retornar
- Se migração falhar: novo path não foi escrito, legacy intacto

---

## FASE 7: MATRIZ DE TESTES

### 7.1 Testes Firestore Real (Obrigatórios)

| ID | Categoria | Teste | Validação |
|----|-----------|-------|-----------|
| T1 | Isolamento A/B | Dois donos no mesmo tenant, etapas diferentes | Ambos têm seu próprio document, sem overwrite |
| T2 | Isolamento A/B | Dono A tenta ler onboarding de Dono B | Access denied |
| T3 | Isolamento A/B | Dono A tenta escrever onboarding de Dono B | Access denied |
| T4 | Tenant Isolation | Tenant X não vê dados de Tenant Y | Paths isolados por tenant_id |
| T5 | Idempotência | Webhook duplicado, mesmo payload | Processado 1x, resultado cacheado |
| T6 | Idempotência | Retry com mesmo campo/valor | Idempotencia_key match, skip |
| T7 | Idempotência | Mesmo valor reenvio 1h depois | Idempotencia_key match, retorna anterior |
| T8 | Criação | Dois webhooks iniciam simultaneamente | Somente 1 cria document |
| T9 | Avanço | Dois webhooks avançam mesma etapa | Apenas 1 sucede, outro retorna erro |
| T10 | Avanço | Etapa fora de ordem (campo !=etapa_esperada) | ERROR "Campo não esperado" |
| T11 | Webhook Duplicado | Meta reenvia 3x mesmo webhook_id | Processado 1x |
| T12 | Retry | Timeout, cliente retenta | Idempotente |
| T13 | Concorrência | Actor A e B completam simultaneamente | Apenas A registrado em dono_principal_actor_id |
| T14 | Ownership | actor_id no path != doc.actor_id | Lançar erro (corrupção) |
| T15 | Primeiro Completo | A completa, depois B completa | dono_principal_actor_id = A (imutável) |
| T16 | Deleção Ator | Deletar Donos/{actor_id}/* | Dados removidos, Configuracao/negocio intacto |
| T17 | Legacy Migração | Legacy existe, ator idêntico | Migra para novo path |
| T18 | Legacy Não Migra | Legacy de outro ator | Skip, sem migração |
| T19 | Legacy + Novo | Legacy e novo coexistem | Novo tem prioridade |
| T20 | Onboarding Completo Não Reinicia | Marcar completo 2x | Segunda vez retorna sucesso, sem alteração |
| T21 | Documento Inexistente | pegar_etapa_onboarding não existe | Retorna None |
| T22 | Documento Inexistente | avancar sem iniciar | ERROR "Onboarding não iniciado" |
| T23 | Imutabilidade Criador | Tentar alterar criado_por | Erro ou campo não altera |
| T24 | Imutabilidade dono_principal | Tentar alterar dono_principal_actor_id | Erro ou campo não altera |

---

## FASE 8: ARQUIVOS E CALLSITES AFETADOS

### 8.1 Arquivos Que Precisarão Mudanças

| Arquivo | Alteração | Tipo | Impacto |
|---------|-----------|------|--------|
| `services/onboarding_dono_service.py` | Redirecionar path + adicionar `actor_id` parâmetro | MAJOR | 5 funções |
| `router/integracao_identidade_onboarding.py` | Adicionar `actor_id` em callsites | MINOR | 2 linhas |
| `services/onboarding_service.py` | Adicionar `actor_id` em callsites | MINOR | 2-3 linhas |
| `services/informacao_service.py` | Referências a `buscar_endereco_negocio` | MINOR | ~1 função |
| (novo) `scripts/migrate_onboarding_legacy.py` | Script de migração | NEW | Migration apenas |
| (novo) `tests/test_c315_onboarding_isolado.py` | 24 testes Firestore real | NEW | Full test coverage |

### 8.2 Funções Principais Afetadas

```
services/onboarding_dono_service.py:
  ├─ iniciar_onboarding_dono(tenant_id, actor_id, ...)  [REWRITE]
  ├─ pegar_etapa_onboarding(tenant_id, actor_id)        [ADD param]
  ├─ avancar_etapa_onboarding(tenant_id, actor_id, ...)  [ADD param + TRANSACTION]
  ├─ marcar_onboarding_completo(tenant_id, actor_id)     [ADD param + TRANSACTION]
  └─ validar_onboarding_minimo(tenant_id, actor_id)      [ADD param]

router/integracao_identidade_onboarding.py:
  ├─ resolver_ator_e_validar_guard() [2 callsites]
  │   └─ pegar_etapa_onboarding(tenant_id, actor_id)
  │   └─ iniciar_onboarding_dono(tenant_id, actor_id, ...)
  └─ processar_fluxo_identidade_onboarding() [1 indirect]

services/onboarding_service.py:
  └─ processar_resposta_onboarding_dono() [2 callsites]
      ├─ pegar_etapa_onboarding(tenant_id, actor_id)
      └─ avancar_etapa_onboarding(tenant_id, actor_id, ...)
```

---

## FASE 9: PLANO C3.15.1 → C3.15.9

### C3.15.1: PREPARAÇÃO E SCHEMA

**Objetivo:** Definir schema final, validar paths, preparar estrutura.

**Tarefas:**
- [ ] Criar documento Firestore rule definition (simular no código)
- [ ] Validar path: `Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo`
- [ ] Criar fixtures de teste (sample documents)
- [ ] Documentar invariantes no código

**Testes:**
- Path é criável sem erro
- Document validation passa (campos corretos)

**Critério de Aprovação:**
- Schema validado
- Fixtures criadas
- Zero implementação de lógica

**Rollback:**
- N/A (apenas schema, sem dados)

---

### C3.15.2: LEITURA (pegar_etapa_onboarding)

**Objetivo:** Implementar função de leitura isolada.

**Alterações:**
```python
# ANTES:
async def pegar_etapa_onboarding(tenant_id: str) -> dict:
    doc = db.collection("Clientes").document(tenant_id)\
        .collection("Configuracao").document("negocio").get()

# DEPOIS:
async def pegar_etapa_onboarding(tenant_id: str, actor_id: str) -> dict:
    # 1. Tentar novo path
    doc = db.collection("Clientes").document(tenant_id)\
        .collection("Donos").document(actor_id)\
        .collection("onboarding").document("ativo").get()
    
    if doc.exists:
        return {...}
    
    # 2. Fallback legacy
    # ...
```

**Testes:**
- T5 (Idempotência)
- T21 (Documento inexistente)
- T19 (Legacy + novo)

**Critério de Aprovação:**
- Lê de novo path corretamente
- Fallback legacy funciona
- Testes T5, T21, T19 passam

**Rollback:**
- Revert a `pegar_etapa_onboarding()` anterior
- Legacy fallback garante compatibilidade

---

### C3.15.3: ESCRITA TRANSACIONAL (avancar_etapa_onboarding)

**Objetivo:** Implementar avanço com transaction e idempotência.

**Alterações:**
```python
# ANTES (sem transaction):
async def avancar_etapa_onboarding(tenant_id, campo, valor):
    doc_ref = db.collection("Clientes").document(tenant_id)..
    doc = doc_ref.get()
    # RMW problem aqui
    doc_ref.update({...})

# DEPOIS (com transaction):
async def avancar_etapa_onboarding(tenant_id, actor_id, campo, valor):
    def transact(transaction):
        doc = transaction.get(doc_ref)
        # VALIDATE ownership, etapa
        # IDEMPOTENCIA check
        # WRITE
        transaction.update(doc_ref, {...})
    
    return db.transaction()(transact)()
```

**Testes:**
- T9 (Avanço concorrente)
- T10 (Etapa fora de ordem)
- T6 (Idempotência webhook duplicado)
- T7 (Idempotência reenvio tardio)

**Critério de Aprovação:**
- Transaction implementada
- Ownership validado
- Idempotencia_key funciona
- Testes T9, T10, T6, T7 passam

**Rollback:**
- Revert transaction
- Fallback para código antigo (sem transação mas funcional)

---

### C3.15.4: CRIAÇÃO E INICIALIZAÇÃO (iniciar_onboarding_dono)

**Objetivo:** Implementar criação isolada por actor com transaction.

**Alterações:**
```python
# ANTES:
async def iniciar_onboarding_dono(tenant_id, actor_id, ...):
    config_data = {...}
    db.collection("Clientes").document(tenant_id)\
        .collection("Configuracao").document("negocio").set(config_data)

# DEPOIS:
async def iniciar_onboarding_dono(tenant_id, actor_id, ...):
    def transact(transaction):
        doc = transaction.get(doc_ref)
        if doc.exists and doc.get("onboarding_status") != "completo":
            return {"status": "resuming"}
        
        transaction.set(doc_ref, config_data, merge=False)
    
    return db.transaction()(transact)()
```

**Testes:**
- T8 (Dois webhooks simultaneamente)
- T1 (Isolamento A/B)
- T5 (Idempotência webhook duplicado)

**Critério de Aprovação:**
- Transaction implementada
- Idempotência de criação
- Testes T8, T1, T5 passam
- Resuming funciona

**Rollback:**
- Revert para `.set()` simples
- Compatível com C3.15.3

---

### C3.15.5: INTEGRAÇÃO DOS CALLSITES

**Objetivo:** Atualizar router e onboarding_service para passar `actor_id`.

**Alterações:**

router/integracao_identidade_onboarding.py:
```python
# ANTES:
etapa_info = await pegar_etapa_onboarding(tenant_id)

# DEPOIS:
etapa_info = await pegar_etapa_onboarding(tenant_id, actor_id)
```

services/onboarding_service.py:
```python
# ANTES:
resultado_avanço = await avancar_etapa_onboarding(tenant_id, campo, valor)

# DEPOIS:
resultado_avanço = await avancar_etapa_onboarding(tenant_id, actor_id, campo, valor)
```

**Testes:**
- Testes P0/P1 com fluxo completo
- Regression testes

**Critério de Aprovação:**
- Todos callsites atualizados
- Compilação passa
- Testes P0/P1 >= 90% pass rate

**Rollback:**
- Revert alterações em router/onboarding_service
- Functions still work se chamadas corretamente

---

### C3.15.6: COMPATIBILIDADE LEGACY

**Objetivo:** Implementar migração automática de legacy.

**Alterações:**
```python
# Adicionar em pegar_etapa_onboarding:
async def pegar_etapa_onboarding(tenant_id, actor_id):
    # Tentar novo
    novo = ...get novo path...
    if novo.exists:
        return novo
    
    # Fallback legacy
    legacy = ...get legacy path...
    if legacy.exists and legacy.get("dono_actor_id") == actor_id:
        # MIGRAR e retornar novo
        await migrar_onboarding_legacy_se_necessario(tenant_id, actor_id)
        return {...}
    
    return None
```

**Funções Novas:**
- `migrar_onboarding_legacy_se_necessario(tenant_id, actor_id)`
- `eh_legacy(tenant_id)`
- `eh_legacy_de_actor(tenant_id, actor_id)`

**Testes:**
- T17 (Legacy migração)
- T18 (Legacy não migra)
- T19 (Legacy + novo)
- T20 (Onboarding completo não reinicia)

**Critério de Aprovação:**
- Migração automática funciona
- Legacy não é deletado
- Testes T17-T20 passam
- Tenant 7394370553 compatível

**Rollback:**
- Remover migração
- Código volta a tentar legacy manualmente

---

### C3.15.7: TESTES FIRESTORE

**Objetivo:** Implementar 24 testes de matriz.

**Arquivo:** `tests/test_c315_onboarding_isolado_firebase_real.py`

**Testes:**
- T1-T24 (conforme matriz na Fase 7)

**Critério de Aprovação:**
- Todos 24 testes PASS
- Firestore real (não mocks)
- Cobertura > 95%

**Rollback:**
- N/A (testes são verificação)

---

### C3.15.8: VALIDAÇÃO FINAL

**Objetivo:** Validar completude e segurança.

**Checklist:**
- [ ] Todos os arquivos compilam
- [ ] Todos os testes passam (24/24)
- [ ] P0 regressão >= 174/174 PASS
- [ ] P1 regressão >= 42/42 PASS
- [ ] Tenant 7394370553 intacto
- [ ] Nenhum dado perdido
- [ ] Zero security violations
- [ ] Invariantes respeitados

**Critério de Aprovação:**
- Checklist 100% completo
- Segurança validada
- Escalabilidade testada (100 donos)

**Rollback:**
- Revert todos os commits de C3.15.1-C3.15.7
- Restaurar a partir de backup pré-C3.15

---

### C3.15.9: REMOÇÃO FUTURA DO LEGACY

**Objetivo:** Planejado para DEPOIS que C3.15 está estável (semanas).

**NÃO FAZER EM C3.15:**
- ❌ Não deletar campos legacy de Configuracao/negocio
- ❌ Não remover fallback de leitura
- ❌ Não forçar migração

**FAZER DEPOIS:**
- ✅ Monitorar uso de legacy em produção
- ✅ Quando zero, remover código de fallback
- ✅ Quando zero, deletar campos legacy
- ✅ Manter backup por 3 meses

---

## FASE 10: RISCOS REMANESCENTES

### 10.1 Riscos Durante Implementação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|--------|-----------|
| **Onboarding quebrado durante transição** | 3% | Alto | Dual-read (novo+legacy) |
| **Perda de dados em migração** | 2% | Crítico | Backup automático, script testado |
| **Query lenta de legacy** | 5% | Médio | Cache, índices automáticos |
| **Tenant A vê dados de Tenant B** | 1% | Crítico | Paths isolam tenant_id |
| **Actor A vê onboarding de Actor B** | 1% | Crítico | Ownership check em cada operação |
| **Idempotencia_key collision** | 0.1% | Baixo | SHA256 é resistente a colisão |
| **Transaction deadlock** | 2% | Médio | Timeout 30s, retry automático |
| **Regressão em P0 testes** | 5% | Alto | Testes rodados após cada gate |

---

### 10.2 Salvaguardas

**Antes de implementar C3.15.1:**
- [ ] Backup automático de produção
- [ ] Feature flag preparado
- [ ] Rollback script testado
- [ ] Oncall avisado

**Durante implementação:**
- [ ] Monitorar logs de erro
- [ ] Monitorar latência Firestore
- [ ] Alertas de data loss

**Pós-implementação:**
- [ ] 48h monitoring de produção
- [ ] Zero P0 incidents
- [ ] Tenant 7394370553 validado

---

## FASE 11: GATE DE APROVAÇÃO

### Checklist Final de C3.15

- [ ] Fase 1: Diagnóstico completo ✅
- [ ] Fase 2: Contrato final assinado ✅
- [ ] Fase 3: Invariantes arquiteturais documentadas ✅
- [ ] Fase 4: Transactions definidas ✅
- [ ] Fase 5: Idempotência projetada ✅
- [ ] Fase 6: Legacy/migração planejada ✅
- [ ] Fase 7: Matriz de testes (24 testes) ✅
- [ ] Fase 8: Callsites/arquivos mapeados ✅
- [ ] Fase 9: Plano C3.15.1-9 detalhado ✅
- [ ] Fase 10: Riscos identificados e mitigados ✅

### Aprovação

**Status:** ✅ **C3.15 — PLANEJAMENTO CONCLUÍDO**

**Nenhum código alterado**  
**Nenhum Firestore alterado**  
**Nenhuma migração executada**  
**Nenhum commit feito**  
**Nenhum push feito**

**Próximo passo:** Aprovação formal para começar C3.15.1 (Preparação e Schema)

---

**Assinatura:** Auditoria C3.15 Completa  
**Data:** 2026-09-26  
**Documentos de Entrada:** C3.13, C3.14, C3.14-R1  
**Documentos de Saída:** Este plano de 11 fases
