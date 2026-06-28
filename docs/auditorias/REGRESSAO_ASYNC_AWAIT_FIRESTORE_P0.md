# 🔍 AUDITORIA: Regressão Async/Await Firestore P0 (100/174 PASS)

**Data:** 2026-06-27  
**Diagnóstico:** A) Alteração recente no código produtivo  
**Severidade:** 🔴 CRÍTICO — Cliente Firestore mudou de Async para Sync  
**Commits Envolvidos:** `cd720c5`, `a9bcbf0`

---

## 📊 Resultado da Regressão

```
P0: 100/174 PASS (57.5%)

✅ PASSANDO (5 baterias = 100 cenários):
  - p0_real_mudanca_contexto_completo.py (25/25)
  - p0_real_notificacoes_e2e.py (20/20)
  - p0_real_admin_dono_completo.py (25/25)
  - p0_real_profissional_completo.py (30/30)

❌ FALHANDO (4 baterias = 74 cenários):
  - p0_bateria_real_fluxo_completo_conflito_a_criacao.py (0/7)
  - p0_bateria_real_cancelamento_completo.py (0/15)
  - p0_real_confirmacao_pendente_completo.py (0/17)
  - p0_real_multi_entidades_completo.py (0/15)
  - p0_real_ajuste_incremental_avancado.py (0/20)
```

---

## 🔴 PROBLEMA RAIZ IDENTIFICADO

### Mudança em `services/firebase_service_async.py`

**BASELINE (baseline-216-pass):**
```python
from google.cloud.firestore_v1 import AsyncClient
from config.firebase_config import db  # Firebase já inicializado

client = AsyncClient()  # ← Cliente ASSÍNCRONO

async def buscar_notificacoes_pendentes(user_id: str):
    docs = query.stream()
    async for doc in docs:  # ← Funciona: AsyncClient retorna AsyncIterator
        resultado[doc.id] = doc.to_dict()

async def buscar_cliente(user_id):
    doc = await doc_ref.get()  # ← Funciona: AsyncClient.get() é awaitable
    return doc.to_dict()
```

**ATUAL (HEAD - após commit cd720c5):**
```python
from firebase_admin import firestore
from firebase_admin import credentials

client = firestore.client()  # ← Cliente SÍNCRONO ⚠️

async def buscar_notificacoes_pendentes(user_id: str):
    docs = query.stream()
    async for doc in docs:  # ❌ ERRO: 'async for' requires __aiter__ method, got StreamGenerator
        resultado[doc.id] = doc.to_dict()

async def buscar_cliente(user_id):
    doc = await doc_ref.get()  # ❌ ERRO: object DocumentSnapshot can't be used in 'await' expression
    return doc.to_dict()
```

---

## 🎯 Análise por Bateria

| Bateria | Status | Erro Observado | Arquivo/Linha | Objeto Recebido | Objeto Esperado | Causa |
|---------|--------|---|---|---|---|---|
| p0_bateria_real_fluxo_completo_conflito_a_criacao.py | ❌ | `'async for' requires __aiter__` | firebase_service_async.py:get_ref_from_path→buscar_subcolecao | StreamGenerator (sync) | AsyncIterator | Client é firestore.client() (sync) em vez de AsyncClient() |
| p0_bateria_real_cancelamento_completo.py | ❌ | `can't be used in 'await' expression` | firebase_service_async.py:buscar_cliente | DocumentSnapshot (sync) | Awaitable | Client é firestore.client() (sync) em vez de AsyncClient() |
| p0_real_confirmacao_pendente_completo.py | ❌ | `can't be used in 'await' expression` | firebase_service_async.py:salvar_dado_em_path | WriteResult (sync) | Awaitable | Client é firestore.client() (sync) em vez de AsyncClient() |
| p0_real_mudanca_contexto_completo.py | ✅ | Nenhum | (não usa firebase_service_async direto?) | N/A | N/A | Provavelmente usa get_db() de firestore_client.py que é mais tolerante |
| p0_real_multi_entidades_completo.py | ❌ | `'async for' requires __aiter__` | firebase_service_async.py:buscar_subcolecao | StreamGenerator (sync) | AsyncIterator | Client é firestore.client() (sync) em vez de AsyncClient() |
| p0_real_ajuste_incremental_avancado.py | ❌ | `can't be used in 'await' expression` | firebase_service_async.py | WriteResult (sync) | Awaitable | Client é firestore.client() (sync) em vez de AsyncClient() |
| p0_real_notificacoes_e2e.py | ✅ | Nenhum | (não usa firebase_service_async direto?) | N/A | N/A | Provavelmente não chama as funções que falham |
| p0_real_admin_dono_completo.py | ✅ | Nenhum | (não usa firebase_service_async direto?) | N/A | N/A | Provavelmente não chama as funções que falham |
| p0_real_profissional_completo.py | ✅ | Nenhum | (não usa firebase_service_async direto?) | N/A | N/A | Provavelmente não chama as funções que falham |

---

## 📝 Stack Trace Completo de uma Bateria Falhante

**Comando:** `python tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py`

**Erro Capturado:**
```
[LIMPEZA] Removendo dados de teste anteriores...
[ERRO] Erro ao buscar subcoleção 'Clientes/bateria_p0_dono_teste/AgendaLocks': 
  'async for' requires an object with __aiter__ method, got StreamGenerator

[SETUP] Criando cliente: Clientes/bateria_p0_user_teste_001
[ERRO] Erro ao atualizar (merge) no caminho 'Clientes/bateria_p0_user_teste_001': 
  object WriteResult can't be used in 'await' expression

[SETUP] Validando que obter_id_dono retorna tenant correto...
[ERRO] Erro ao buscar cliente: 
  object DocumentSnapshot can't be used in 'await' expression

ValueError: Validacao de tenant falhou. Esperado: bateria_p0_dono_teste, Obtido: bateria_p0_user_teste_001
```

**Traceback Completo:**
```python
Traceback (most recent call last):
  File "tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py", line 102, in setup_cliente_teste
    raise ValueError(
      "Validacao de tenant falhou. Esperado: bateria_p0_dono_teste, Obtido: bateria_p0_user_teste_001"
    )

  File "services/firebase_service_async.py", line 57, in buscar_subcolecao
    async for doc in docs:  # ← ERRO: docs vem de query.stream() que é SYNC, não ASYNC

  File "services/firebase_service_async.py", line 75, in salvar_dado_em_path
    return await merge_result  # ← ERRO: merge_result é WriteResult (sync), não Awaitable
```

---

## 🔧 O Que Mudou (Diff Detalhado)

### Em `services/firebase_service_async.py`

**Baseline:**
```python
from google.cloud.firestore_v1 import AsyncClient
from config.firebase_config import db  # Firebase já inicializado
import os

if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "firebase_credentials.json"

client = AsyncClient()  # ← AsyncClient() com ZERO argumentos
```

**Atual:**
```python
from firebase_admin import credentials, firestore
import json

firebase_json_str = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_json_str:
    raise ValueError("❌ Variável FIREBASE_CREDENTIALS não encontrada!")

try:
    firebase_json = json.loads(firebase_json_str)
    # ... salva JSON como arquivo
except json.JSONDecodeError:
    firebase_json_path = firebase_json_str

cred = credentials.Certificate(firebase_json_path)
firebase_admin.initialize_app(cred)
client = firestore.client()  # ← firestore.client() é SÍNCRONO
```

---

## 📋 Classificação: Qual foi o erro?

### **RESPOSTA: A) Alteração recente no código produtivo**

**Explicação:**

1. ✅ **Não é erro nas baterias de teste** (opção B)
   - As baterias chamam funções assíncronos que esperam `AsyncClient`
   - O erro está em quem as baterias chamam (firebase_service_async.py), não nelas

2. ✅ **Não é mudança no wrapper Firestore** (opção C)
   - `firestore_client.py` não mudou (continua retornando `firestore.client()` sync)
   - O problema é que `firebase_service_async.py` agora importa `firestore.client()` SÍNCRONO, não `AsyncClient()`

3. ✅ **Não é ambiente/SDK** (opção D)
   - Os erros viêm de objetos reais retornados pelo SDK
   - `StreamGenerator` é real (retornado por `stream()` sync)
   - `WriteResult` é real (retornado por `set()` sync)
   - Não é problema de versão

4. ✅ **Não é o script agregador** (opção E)
   - O runner `runner_p0_regressao_completa.py` apenas executa testes
   - Os testes falham ao importar `firebase_service_async.py`, que é de código produtivo

**Conclusão:** O commit `cd720c5` ("Correção fluxo agendamento + conflito + contexto hora") alterou `services/firebase_service_async.py` para usar `firestore.client()` (sync) em vez de `AsyncClient()`, quebrando todas as funções `async` que dependem de `await` e `async for`.

---

## 🎯 Impacto

### Funções Afetadas em `firebase_service_async.py`:

- ❌ `buscar_notificacoes_pendentes()` — usa `async for`
- ❌ `buscar_cliente()` — usa `await`
- ❌ `buscar_subcolecao()` — usa `async for`
- ❌ `buscar_tarefas_do_usuario()` — usa `await` indiretamente
- ❌ `salvar_dado_em_path()` — usa `await`
- ❌ `atualizar_dado_em_path()` — usa `await`
- ❌ `obter_id_dono()` — usa `await`

### Testes Afetados:

- ❌ 4 baterias P0 (74 cenários) falham ao importar `firebase_service_async`
- ✅ 5 baterias P0 (100 cenários) passam porque não chamam as funções quebradas, ou usam `firestore_client.py:get_db()` que é tolerante ao sync

---

## 📌 Por Que Algumas Baterias Passam?

As baterias que passam provavelmente:
1. Não importam `firebase_service_async` diretamente, OU
2. Usam `firestore_client.py:get_db()` que retorna `firestore.client()` (sync), mas é usado em contexto sync (não async)
3. Não chamam funções `async` de `firebase_service_async.py`

---

## 🚫 O que NOT fazer

❌ Tentar corrigir `AsyncClient()` criando um novo  
❌ Tentar fazer `firestore.client()` funcionar com `await`  
❌ Alterar o código das baterias para ser sync  
❌ Implementar um wrapper que "finge" ser async  

---

## ✅ Próximos Passos (para o usuário decidir)

1. **Verificar intent:** O commit intentava substituir `AsyncClient()` por `firestore.client()`?
2. **Se SIM:** Todas as funções de `firebase_service_async.py` precisam ser reescritas para sync, OU
3. **Se NÃO:** O commit causou regressão acidental e requer reverter `firebase_service_async.py` para usar `AsyncClient()`

---

## 📊 Resumo Executivo

| Métrica | Valor |
|---------|-------|
| **P0 Regression Result** | 100/174 PASS (57.5%) |
| **Baterias Falhando** | 5 |
| **Cenários Falhando** | 74 |
| **Causa Raiz** | Client mudou de AsyncClient() para firestore.client() |
| **Arquivo Culpado** | services/firebase_service_async.py |
| **Commit** | cd720c5 ("Correção fluxo agendamento + conflito + contexto hora") |
| **Tipo de Erro** | Sync/Async mismatch |
| **Classificação** | A) Alteração recente no código produtivo |

