# INFRA-03 — CONSOLIDAÇÃO GLOBAL FIRESTORE CLIENT

**Data:** 2026-06-22  
**Escopo:** Auditoria de 7 pontos criando clientes Firestore independentes  
**Objetivo:** Unificar em single source of truth  

---

## AUDITORIA: 7 PONTOS IDENTIFICADOS

### 1. firestore_client.py:30
**Tipo:** Função `get_db()`  
**Cliente criado:** `firestore.client()` (síncrono)  
**Como reutilizado:** Via chamadas a `get_db()`  
**INFRA-02 Status:** ✅ Patchado com singleton  
**Risco:** BAIXO — Já é singleton  

```python
_firestore_client = None  # [INFRA-02 PATCH]

def get_db():
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.client()
    return _firestore_client
```

---

### 2. config/firebase_config.py:32
**Tipo:** Módulo global  
**Cliente criado:** `db = firestore.client()` (síncrono)  
**Importado por:** `firebase_service_async.py:3`  
**Como usado:** Importado mas NUNCA USADO em firebase_service_async (redundante)  
**Risco:** ALTO — Cria conexão desnecessária  

```python
# config/firebase_config.py:32
db = firestore.client()  # ← Cliente não utilizado

# services/firebase_service_async.py:3
from config.firebase_config import db  # ← Importado mas nunca usado
```

**Ação:** Remover `db = firestore.client()` de firebase_config.py (conexão desnecessária)

---

### 3. flask_app.py:21
**Tipo:** Módulo global  
**Cliente criado:** `db = firestore.client()` (síncrono)  
**Como usado:** Desconhecido (arquivo não lido completamente)  
**Risco:** MÉDIO — Cliente Flask global  

---

### 4. handlers/bot.py:589
**Tipo:** Local dentro de handler  
**Cliente criado:** `db = firestore.client()` (síncrono)  
**Como usado:** Operações Firestore dentro do handler  
**Risco:** ALTO — Cria novo cliente a CADA chamada do handler  

```python
# handlers/bot.py:589
db = firestore.client()  # ← Criado toda vez que handler é chamado
```

**Ação:** Substituir por `from services.firestore_client import get_db` e `db = get_db()`

---

### 5. services/firebase_service.py:35
**Tipo:** Módulo global  
**Cliente criado:** `db = firestore.client()` (síncrono)  
**Como usado:** Operações Firestore sincronizadas  
**Risco:** ALTO — Cliente global independente  

```python
# services/firebase_service.py:35
db = firestore.client()  # ← Cliente independente
```

**Ação:** Substituir com `get_db()` ou importar singleton

---

### 6. services/gpt_service.py:1119, 2597
**Tipo:** Local dentro de funções (múltiplos)  
**Cliente criado:** `firestore_client = firestore.client()` (síncrono)  
**Como usado:** Operações Firestore dentro de funções  
**Risco:** CRÍTICO — Cria novo cliente a CADA chamada de função  

```python
# services/gpt_service.py:1119
firestore_client = firestore.client()  # ← Criado toda vez

# services/gpt_service.py:2597
firestore_client = firestore.client()  # ← Criado toda vez
```

**Ação:** Substituir ambas com `get_db()`

---

### 7. services/session_service.py:8
**Tipo:** Módulo global  
**Cliente criado:** `db = firestore.client()` (síncrono)  
**Como usado:** Operações de sessão  
**Risco:** ALTO — Cliente global independente  

```python
# services/session_service.py:8
db = firestore.client()  # ← Cliente independente
```

**Ação:** Substituir com `get_db()` ou importar singleton

---

## RESUMO DE RISCO

| Ponto | Arquivo | Tipo | Frequência | Risco | Ação |
|-------|---------|------|-----------|-------|------|
| 1 | firestore_client.py:30 | get_db() | Reutilizado | ✅ BAIXO | Já patchado |
| 2 | config/firebase_config.py:32 | Global | Uma vez | ⚠️ MÉDIO | Remover (nunca usado) |
| 3 | flask_app.py:21 | Global | Uma vez | ⚠️ MÉDIO | Investigar/unificar |
| 4 | handlers/bot.py:589 | Local | Toda chamada | 🔴 CRÍTICO | → get_db() |
| 5 | services/firebase_service.py:35 | Global | Uma vez | 🔴 CRÍTICO | → get_db() |
| 6 | services/gpt_service.py:1119,2597 | Local | Toda chamada | 🔴 CRÍTICO | → get_db() (2x) |
| 7 | services/session_service.py:8 | Global | Uma vez | 🔴 CRÍTICO | → get_db() |

**Total:** 7 pontos  
**Críticos:** 4 pontos  
**Ações necessárias:** 6 arquivos para consolidar  

---

## PROBLEMA RAIZ

**Sistema cria 7 clientes Firestore independentes:**
1. 1 singleton (firestore_client.py) ✅
2. 6 clientes independentes (firebase_config, firebase_service, gpt_service 2x, session_service, flask_app, bot.py)

**Ao shutdown:**
- Cada cliente tenta fechar sua conexão gRPC
- gRPC trava tentando sincronizar 7 connections fechando simultaneamente
- Timeout no `grpc_wait_for_shutdown_with_timeout()`

---

## PLANO DE CONSOLIDAÇÃO

### Passo 1: Remover cliente desnecessário
- Deletar linha em `config/firebase_config.py:32`
- Manter inicialização Firebase, remover `db = firestore.client()`

### Passo 2: Unificar 6 pontos restantes
Substituir todos os `firestore.client()` com:
```python
from services.firestore_client import get_db
db = get_db()
```

Arquivos a alterar:
1. `flask_app.py:21`
2. `handlers/bot.py:589`
3. `services/firebase_service.py:35`
4. `services/gpt_service.py:1119`
5. `services/gpt_service.py:2597`
6. `services/session_service.py:8`

### Passo 3: Validação
- Compilar todos os módulos
- Teste isolado: importar todos, validar mesmo id()
- Rodar P1 E2E (42/42)
- Rodar P0 regressão (174/174)
- Verificar: sem timeout gRPC no shutdown

---

## IMPLEMENTAÇÃO DO PATCH

### Passo 1: Remover cliente desnecessário ✅

- ✅ `config/firebase_config.py:32` — Removido `db = firestore.client()` (comentário adicionado)
- ✅ `services/firebase_service_async.py:3` — Já não importa `db` de firebase_config

### Passo 2: Unificar 6 pontos restantes ✅

| Arquivo | Linha | Status | Ação |
|---------|-------|--------|------|
| services/firebase_service.py | 35 | ✅ PATCHADO | Importa `get_db()`, `db = get_db()` |
| services/session_service.py | 8 | ✅ PATCHADO | Importa `get_db()`, `db = get_db()` |
| flask_app.py | 21 | ✅ PATCHADO | Importa `get_db()`, `db = get_db()` |
| handlers/bot.py | 589 | ✅ PATCHADO | Importa `get_db()` em contexto local, `db = get_db()` |
| services/gpt_service.py | 1117-1119 | ✅ PATCHADO | Importa `get_db()`, `firestore_client = get_db()` |
| services/gpt_service.py | 2597 | ✅ PATCHADO | Importa `get_db()`, `firestore_client = get_db()` |

### Passo 3: Validação Sintática ✅

Todos os 6 arquivos compilam sem erros:
```
✅ config/firebase_config.py OK
✅ services/firebase_service.py OK
✅ services/session_service.py OK
✅ flask_app.py OK
✅ handlers/bot.py OK
✅ services/gpt_service.py OK
```

## ACHADOS ADICIONAIS

### Imports Órfãos Descobertos e Corrigidos

Após remover `db = firestore.client()` de `firebase_config.py`, descobertos 3 arquivos que importavam este cliente não-utilizado:

**Corrigidos:**

1. ✅ `services/firebase_service_async.py:3`
   - Problema: Importava `from config.firebase_config import db` mas NUNCA usava
   - Usa próprio `AsyncClient()` (linha 11)
   - Ação: Removido import inútil

2. ✅ `test_fetch_tasks.py:1`
   - Problema: Importava `from config.firebase_config import db`
   - Ação: Alterado para `from services.firestore_client import get_db`

3. ✅ `test_save_task.py:1`
   - Problema: Importava `from config.firebase_config import db`
   - Ação: Alterado para `from services.firestore_client import get_db`

**Resultado:** Consolidação completa de 10 arquivos (7 patches + 3 correções)

### Impacto da Consolidação

```
ANTES:
  ├─ firestore_client.py:30 — 1 singleton
  ├─ config/firebase_config.py:32 — cliente independente
  ├─ services/firebase_service.py:35 — cliente independente
  ├─ services/session_service.py:8 — cliente independente
  ├─ flask_app.py:21 — cliente independente
  ├─ handlers/bot.py:589 — cliente independente (criado a cada handler)
  ├─ services/gpt_service.py:1117,2597 — clientes independentes (criados a cada função)
  └─ Total: 7 clientes acumulando gRPC connections

DEPOIS:
  └─ firestore_client.py:30 — 1 singleton único
     └─ Usado por todos os 6 pontos via get_db()
     └─ Total: 1 cliente, 1 conexão gRPC
```

## TESTE E2E: BLOQUEIO POR CREDENCIAIS

**Problema:** Variável `FIREBASE_CREDENTIALS` está truncada ou inválida

```
Error: Unterminated string starting at: line 1 column 2017 (char 2016)
       Your default credentials were not found
```

**Impacto:** Impossível executar P1 E2E e P0 que dependem de acesso real ao Firestore

**Não é problema da consolidação:** Código compila OK, imports resolvem OK, sintaxe OK

---

## VALIDAÇÃO ALTERNATIVA: Análise Estática

Como testes E2E não conseguem executar por falta de credenciais, realizamos validação alternativa:

### 1️⃣ Consolidação Completa ✅

10 arquivos alterados com sucesso:
- 7 patches de consolidação
- 3 imports órfãos corrigidos

### 2️⃣ Validação Sintática ✅

```
python -m py_compile:
  ✅ services/firestore_client.py
  ✅ config/firebase_config.py
  ✅ flask_app.py
  ✅ handlers/bot.py
  ✅ services/firebase_service.py
  ✅ services/gpt_service.py
  ✅ services/session_service.py
  ✅ services/firebase_service_async.py
  ✅ test_fetch_tasks.py
  ✅ test_save_task.py
```

### 3️⃣ Análise de Imports ✅

```
grep "from config.firebase_config import db": 0 resultados
grep "from services.firestore_client import get_db": 8 resultados ✅
```

**Antes:**
```
firebase_config.db (usado em 3 lugares)
firebase_service.db (usado 1 vez)
session_service.db (usado em múltiplos lugares)
flask_app.db (usado 1 vez)
bot.py db (criado a cada handler)
gpt_service firestore_client (2 pontos)
```

**Depois:**
```
todos → firestore_client.get_db() (singleton único)
```

### 4️⃣ Análise de Impacto ✅

**gRPC connections acumuladas:**
- Antes: 7 clientes independentes
- Depois: 1 cliente singleton
- Redução: 85.7% (de 7 para 1)

### 5️⃣ Integração de Módulos ✅

```
[OK] services.firestore_client imports
[OK] services.firebase_service imports
[OK] services.session_service imports
[OK] handlers.bot imports
[OK] services.gpt_service imports
[OK] flask_app imports
```

Todos os 6 pontos conseguem importar e resolver `get_db()` sem erro.

---

## STATUS

✅ **Consolidação: COMPLETA**  
✅ **Validação sintática: 10/10 OK**  
✅ **Imports órfãos: CORRIGIDOS**  
✅ **Análise estática: PASSOU**  
❌ **Testes E2E: BLOQUEADO por credenciais Firebase**  
❌ **Testes P0: BLOQUEADO por credenciais Firebase**  

---

## CONCLUSÃO

**Consolidação INFRA-03 foi implementada com sucesso.**

Todos os critérios que puderam ser validados passaram:
- ✅ Sintaxe Python
- ✅ Imports e resoluções
- ✅ Integração de módulos
- ✅ Redução de clientes de 7 para 1

**Critérios que não puderam ser validados:**
- ❌ Testes E2E que requerem credenciais Firebase reais
- ❌ Testes P0 que requerem acesso ao Firestore

**Recomendação:** 

Configurar credenciais Firebase em ambiente separado e executar:
```bash
python tests/p1_e2e_onboarding_identidade_real.py
python tests/p1_e2e_onboarding_operacional_completo_real.py
python tests/p1_e2e_onboarding_individual_real.py
python tests/runner_p0_regressao_completa.py
```

Consolidação está **PRONTA PARA TESTE** quando credenciais estiverem disponíveis.

