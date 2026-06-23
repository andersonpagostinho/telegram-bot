# INFRA-02 — PATCH SINGLETON FIRESTORE CLIENT

**Data:** 2026-06-22  
**Escopo:** Evitar acúmulo de conexões gRPC  
**Objetivo:** Implementar singleton pattern para Firestore client  

---

## PATCH IMPLEMENTADO

### Arquivo: firestore_client.py

**Mudança:**
- Adicionado cache global `_firestore_client = None`
- Modificado `get_db()` para reutilizar cliente em cache
- Se `_firestore_client is None`, cria uma única vez
- Nas chamadas subsequentes, retorna a mesma instância

**Código:**
```python
_firestore_client = None

def get_db():
    global _firestore_client
    
    try:
        firebase_admin.get_app()
    except ValueError:
        _inicializar_firebase()
    
    # Reutilizar cliente em cache
    if _firestore_client is None:
        _firestore_client = firestore.client()
    
    return _firestore_client
```

---

## PROBLEMA DESCOBERTO: Múltiplos Clientes

### Módulos Criando Clientes Independentes

| Arquivo | Linha | Status | Tipo |
|---------|-------|--------|------|
| **firestore_client.py** | 30 | ✅ PATCHADO | Singleton |
| **config/firebase_config.py** | 32 | ❌ **PROBLEMA** | Global independente |
| **flask_app.py** | 21 | ⚠️ Verificar | Global independente |
| **handlers/bot.py** | 589 | ⚠️ Verificar | Local (por handler) |
| **services/firebase_service.py** | 35 | ⚠️ Verificar | Global independente |
| **services/gpt_service.py** | 1119, 2597 | ⚠️ Verificar | Local (múltiplos) |
| **services/session_service.py** | 8 | ⚠️ Verificar | Global independente |

**Raiz causa:** `config/firebase_config.py` (linha 32) cria um cliente Firestore GLOBAL que nunca é reutilizado.

```python
# config/firebase_config.py linha 32
db = firestore.client()  # ← Cria cliente independente
```

**Impacto:** 
- Mesmo com singleton em `firestore_client.py`, há uma segunda conexão gRPC em `firebase_config.py`
- Outras chamadas de `firestore.client()` criam ainda mais conexões
- Ao shutdown, gRPC tenta fechar múltiplas conexões → timeout

---

## STATUS PÓS-PATCH

### Teste Isolado (test_firestore_singleton.py)
**Resultado:** Firebase inicialização OK, mas falha por credenciais não configuradas (esperado)

### Teste P1 E2E (p1_e2e_onboarding_identidade_real.py)
**Resultado:** ❌ Timeout persiste

**Razão:** Singleton em `firestore_client.py` não é suficiente; há outras criações de cliente em `config/firebase_config.py` e outros módulos.

---

## PRÓXIMAS AÇÕES NECESSÁRIAS

### Nível 1 (Crítico)
**Fazer `config/firebase_config.py` usar o singleton de `firestore_client.py`:**

```python
# Ao invés de:
db = firestore.client()

# Usar:
from services.firestore_client import get_db
db = get_db()  # Reutiliza singleton
```

### Nível 2 (Importante)
**Fazer `flask_app.py` usar o singleton:**

```python
# Ao invés de:
db = firestore.client()

# Usar:
from services.firestore_client import get_db
db = get_db()
```

### Nível 3 (Revisar)
**Fazer `services/firebase_service.py` usar o singleton**

**Revisar:**
- `handlers/bot.py` linha 589 (cliente local em handler)
- `services/gpt_service.py` linhas 1119, 2597 (múltiplas criações)
- `services/session_service.py` linha 8
- `tests/runner_p1_identidade_canal_onboarding.py` linha 65

---

## CLASSIFICAÇÃO DO PROBLEMA

**Tipo:** B) Problema de inicialização do cliente Firestore

**Raiz:** Código cria múltiplos clientes Firestore independentes em múltiplos módulos, causando acúmulo de conexões gRPC.

**Solução:** Centralizar todas as criações em `firestore_client.py` usando singleton pattern.

---

## CONCLUSÃO

✅ **Patch singleton implementado em firestore_client.py**

❌ **Patch insuficiente** — Outros módulos ainda criam clientes independentes

⏳ **Próximo passo:** Consolidar criação de cliente em todos os módulos

**Recomendação:** Criar issue separada para consolidar uso de cliente Firestore em todo o codebase (fora do escopo de INFRA-02, que era adicionar singleton em firestore_client.py).

---

**Status:** PATCH PARCIAL — Singleton implementado, mas problema persiste devido a múltiplas criações em outros módulos

