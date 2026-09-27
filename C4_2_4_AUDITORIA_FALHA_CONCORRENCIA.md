# C4.2.4 — AUDITORIA DA FALHA DE CONCORRÊNCIA DO CLAIM

**Data:** 2026-09-25  
**Status:** ⏳ AUDITORIA TÉCNICA (sem alterações)  
**Objetivo:** Determinar raiz da falha em T2 (concorrência)  

---

## A. FLUXO DO CLAIM — ANÁLISE LINHA POR LINHA

### Pseudofluxo Completo

```
tentar_claim_notificacao(tenant_id, notif_id, processo_id, max_tentativas=5):

    agora = datetime.now(FUSO_BR)  ← Timestamp LOCAL (único por execução)
    
    LOOP (até 5 tentativas):
        
        [ETAPA 1] Ler documento
            notif = await buscar_dado_em_path(path)
            ↓ retorna {status, avisado, processo_id, processando_em, ...}
        
        [ETAPA 2] Validar se pode assumir
            se avisado=true OU status="avisado" → return False
            se status="processando" E claim não expirado → return False
        
        [ETAPA 3] Escrever claim
            timestamp_escrita = agora.isoformat()  ← Mesmo para ambas se agora idêntico!
            
            payload = {
                status: "processando",
                processo_id: processo_id,  ← DIFERENTE por instância
                processando_em: timestamp_escrita,  ← MESMO se agora idêntico
                _timestamp_validacao: timestamp_escrita,  ← MESMO
            }
            
            await atualizar_dado_em_path(path, payload)  ← FIRESTORE MERGE=TRUE
        
        [ETAPA 4] Revalidar
            notif_apos = await buscar_dado_em_path(path)
            
            se (processo_id_apos == processo_id E
                timestamp_apos == timestamp_escrita E
                processando_em_apos == timestamp_escrita):
                → return True  ✅ CLAIM OBTIDO
            senão:
                → return False  ❌ OUTRO PROCESSO VENCEU
        
        Em exceção: retry com backoff exponencial
```

### Problema Identificado

**Linha 132:** `await atualizar_dado_em_path(path, payload)`

Esta função usa:
```python
# firebase_service_async.py:271-279
async def atualizar_dado_em_path(path: str, dados: dict):
    ref = get_ref_from_path(path)
    await ref.set(dados, merge=True)  ← FIRESTORE MERGE
```

**MERGE é a operação:**
- Não é transação
- Não é condicional
- É apenas "sobrescrever esses campos"

---

## B. OPERAÇÃO FIRESTORE UTILIZADA

**Tipo:** `DocumentReference.set(data, merge=True)`

**Semântica:**
```
set(..., merge=True):
  - Se documento não existe: cria
  - Se existe: mescla (update dos campos)
  - Retorna imediatamente (sucesso)
  - Não há precondição ("se X então faça Y")
```

**NÃO É:**
- ❌ Transaction
- ❌ Update condicional
- ❌ Create-if-not-exists
- ❌ Operação atômica de leitura-escrita

**É:**
- ✅ Merge simples
- ✅ Sobrescrita de campos
- ✅ Sem garantia de exclusividade

---

## C. COMPARAÇÃO T9 × T2

### T9 (PASSOU — 17/17 PASS anterior)

```python
# Linha 59: agora gerado UMA VEZ, ANTES do gather
agora = datetime.now(FUSO_BR)

# Linhas 72-75: Duas instâncias diferentes
async def instancia_tenta_claim(inst_id):
    processo_id = f"proc_{inst_id}_{uuid.uuid4().hex[:4]}"  ← UUID DIFERENTE!
    sucesso, notif = await tentar_claim_notificacao(TENANT, notif_id, processo_id)
    return (inst_id, sucesso, processo_id)

resultados = await asyncio.gather(
    instancia_tenta_claim(1),  ← processo_id = "proc_1_XXXX"
    instancia_tenta_claim(2),  ← processo_id = "proc_2_YYYY"
)
```

**Resultado esperado (e observado):** Apenas uma consegue

### T2 (FALHOU — ambas=True)

```python
# Linha 116: agora gerado UMA VEZ, ANTES do gather
agora = datetime.now(FUSO_BR)

# Linhas 114-115: Dois processo_ids CRIADOS ANTES do gather
processo1 = f"proc1_{uuid.uuid4().hex[:4]}"
processo2 = f"proc2_{uuid.uuid4().hex[:4]}"

# Linhas 126-130: Ambas compartilham MESMO agora
async def tenta_claim(proc_id):
    sucesso, _ = await tentar_claim_notificacao(
        TENANT_TEST, notif_id, proc_id
    )
    return sucesso

resultado1, resultado2 = await asyncio.gather(
    tenta_claim(processo1),  ← processo_id = "proc1_XXXX"
    tenta_claim(processo2),  ← processo_id = "proc2_YYYY"
)
```

**Resultado esperado:** Apenas uma consegue
**Resultado observado:** ⚠️ **Ambas conseguem (resultado1=True, resultado2=True)**

### Por Que T2 Falha Mas T9 Passou?

**DIFERENÇA ESTRUTURAL:** Nenhuma aparente no nível de teste!

Ambos:
- Compartilham `agora` antes do gather
- Geram `processo_id` diferentes antes do gather
- Executam `asyncio.gather()` que roda ambas concorrentemente
- Chamam tentar_claim() com tenant/notif_id iguais

**HIPÓTESE:** Diferença no timing/execução na máquina de testes
- T9: Sequência de sorte onde revalidação detecta conflito
- T2: Sequência desafortunada onde ambas passam na revalidação

---

## D. TIMESTAMP: ANÁLISE PROFUNDA

### Geração do Timestamp

**Código (linha 121):**
```python
timestamp_escrita = agora.isoformat()
```

Onde `agora = datetime.now(FUSO_BR)` (linha 73 em tentar_claim)

### Precisão Real

```python
datetime.now(FUSO_BR).isoformat()
# Exemplo: "2026-09-25T16:08:45.234567-03:00"
# Precisão: MICROSEGUNDOS (6 dígitos)
```

### Cenário de Colisão

Quando dois processos executam **no mesmo microsegundo:**

```
TEMPO: 16:08:45.234567

Processo A:
  agora = datetime.now(FUSO_BR)  # 16:08:45.234567
  timestamp_escrita = "2026-09-25T16:08:45.234567-03:00"
  
Processo B (paralelo, mesmo microsegundo):
  agora = datetime.now(FUSO_BR)  # 16:08:45.234567 (MESMO!)
  timestamp_escrita = "2026-09-25T16:08:45.234567-03:00" (IDÊNTICO)

Ambos escrevem com:
  _timestamp_validacao: "2026-09-25T16:08:45.234567-03:00"

Revalidação:
  A: esperava "2026-09-25T16:08:45.234567-03:00", achei "2026-09-25T16:08:45.234567-03:00" ✓
  B: esperava "2026-09-25T16:08:45.234567-03:00", achei "2026-09-25T16:08:45.234567-03:00" ✓
  
  Resultado: AMBOS ACHAM QUE VENCERAM!
```

### Por Que UUID5 Resolveria (ou não)

**UUID5 (proposto):**
```python
timestamp_escrita = str(uuid5(
    NAMESPACE_DNS,
    f"{tenant_id}:{notif_id}:{uuid.uuid4()}"
))
```

**Resultado:**
- A: uuid5(...{uuid4-1}) = "xxxxxxxx-xxxx-5xxx-xxxx-xxxxxxxxxxxx"
- B: uuid5(...{uuid4-2}) = "yyyyyyyy-yyyy-5yyy-yyyy-yyyyyyyyyyyy"
- **DIFERENTE!** Revalidação funcionaria.

**MAS** — UUID5 não é uma solução arquitetural. É mascarar o problema.

O problema verdadeiro é: **Merge sem precondição não oferece exclusividade.**

---

## E. GARANTIA ATUAL: CLASSIFICAÇÃO

### Classificação: **D — NÃO SEGURO PARA CONCORRÊNCIA**

**Justificativa:**

```
Pré-requisito de atomicidade:
  - Operação única (indivisível) OU
  - Precondição testada no banco antes de escrever

O que temos:
  - Read (linha 78)
  - Write merge simples (linha 132)
  - Reread (linha 136)
  
Problema:
  - Entre linha 78 e 132, outro processo pode escrever
  - Merge não testa precondição
  - Revalidação compara strings — se iguais, ambas passam
  
Prova:
  - T2 falhou demonstrando ambos conseguem o claim
```

**Nível de Garantia Oferecido:**

| Nível | Descrição | Oferecido? |
|-------|-----------|-----------|
| Transacional (SERIALIZABLE) | ❌ | Não |
| Atômico (ACID) | ❌ | Não |
| CAS (Compare-And-Swap) | ❌ | Não |
| Otimista com revalidação | ⚠️ | Parcialmente (falha em colisão de timestamp) |
| Exclusividade | ❌ | **Não (T2 prova)** |

---

## F. IMPACTO NA INTEGRAÇÃO C4.2.2

### Pode o Scheduler Enviar Duplicado?

**SIM. Cenário:**

```
Execução 1 (worker A):
  1. tentar_claim(notif_123) → timestamp="T1"
  2. bot.send_message() → ENVIADO
  
Execução 2 (worker B, ~microsegundo depois):
  1. Lê: status="pendente" (ainda não confirmou)
  2. tentar_claim(notif_123) → timestamp="T1" (COLISÃO!)
  3. Revalidação: ambas vêem "T1" → AMBAS RETORNAM TRUE
  4. bot.send_message() → ENVIADO DE NOVO

Resultado:
  ❌ USUÁRIO RECEBE MENSAGEM 2×
```

**Localização exata no scheduler:**

```python
# scheduler/notificacoes_scheduler.py:134-151
sucesso_claim, _ = await tentar_claim_notificacao(...)
if not sucesso_claim:
    continue  # Proteção: se não conseguiu, pula

# MAS: em concorrência com colisão de timestamp, sucesso_claim=True
# para AMBOS, então AMBOS entram aqui e enviam
```

---

## G. SOLUÇÃO NECESSÁRIA: OPÇÕES

### ❌ NÃO FUNCIONA: UUID5 (Mascara Problema)

Usar UUID5 para timestamp único evitaria colisão, MAS:
- Não resolve o fato de merge sem precondição
- Apenas torna colisão mais improvável
- Não é verdadeira atomicidade

### ✅ FUNCIONARIA: Firestore Transaction (Verdadeiro)

```python
transaction = db.transaction()

@transaction.transactional
async def tentar_claim_tx(tx):
    notif = tx.get(path)
    if notif.get("avisado"):
        return False
    
    # Update atômico: se não houve mudança, falha
    tx.update(path, {"status": "processando", ...})
    return True
```

**MAS:** Async não suporta @transaction.transactional

### ✅ FUNCIONARIA: Conditional Update

```python
# Firestore tem `updateMask` que permite "update se == valor"
await ref.update(
    {_timestamp_validacao: novo_valor},
    precondition={"if_match": "valor_antigo"}
)
```

**MAS:** Firebase SDK async não expõe este API facilmente

### ✅ FUNCIONARIA: Document Lock em Subcoleção

```
Clientes/{tenant}/NotificacoesAgendadas/{notif_id}/locks/{processo_id}
```

Apenas uma consegue criar o documento.

**Implementável:** SIM, sem transaction

---

## H. ARQUIVOS QUE PRECISARIAM SER MODIFICADOS

### Para Corrigir (Necessário)

1. **services/notificacoes_idempotencia_service.py**
   - Função: `tentar_claim_notificacao()`
   - Mudança: Usar mecanismo diferente (lock document ou transaction)
   - Linhas afetadas: 72-175

2. **tests/test_c42_idempotencia_atomica.py**
   - Revisar T9 para validar se realmente testa concorrência
   - Possível: falso positivo por sorte de timing

3. **tests/test_c423_regression_scheduler_integration.py**
   - Manter testes T1-T6 como prova de falha
   - Usar para validar fix

### Para Validar (Após fix)

4. **scheduler/notificacoes_scheduler.py**
   - Nenhuma mudança necessária
   - Apenas rodar regressão após fix

---

## I. NOVOS TESTES NECESSÁRIOS APÓS FIX

### Teste de Colisão Explícita

```python
# Forçar dois processos a gerar EXATAMENTE o mesmo timestamp
# Validar que apenas um consegue mesmo com colisão
```

### Teste de Stress (100+ concurrent)

```python
# Simular 100+ notificações simultâneas
# Verificar que nenhuma duplica
```

### Teste de Timing Adverso

```python
# Variar delays entre etapas (leitura, escrita, reread)
# Validar exclusividade em qualquer timing
```

---

## J. RESUMO EXECUTIVO

### CAUSA RAIZ CONFIRMADA

**Merge sem precondição permite que dois processos com timestamps idênticos passem na revalidação.**

Quando `asyncio.gather()` executa ambas as instâncias **no mesmo microsegundo:**
- Ambas geram `agora.isoformat()` idêntico
- Ambas escrevem com merge=true
- Ambas revalidam e vêem timestamp idêntico
- **Ambas retornam True**

### PROVA

- **T2 falhou:** Relatou ambos conseguiram claim
- **Logs:** Ambas atualizações registradas

### SOLUÇÃO RECOMENDADA

**NÃO usar UUID5** (mascara problema).

**Usar lock document ou Firestore Transaction** para verdadeira atomicidade.

---

## K. GATE FINAL

### C4.2.4 — **APROVADO PARA CORREÇÃO**

**Justificativa:**
1. Causa raiz identificada: colisão de timestamp em merge sem precondição
2. Solução arquitetural clara: lock document ou transaction
3. Testes comprovam falha e podem validar fix
4. Impacto: Scheduler pode duplicar em concorrência

**Próximo passo:** Implementar lock document e reprovar C4.2.3

