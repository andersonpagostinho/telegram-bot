# CORREÇÃO: CONTRATO ÚNICO DE SESSÃO/CONTEXTO

**Data:** 2026-06-22  
**Escopo:** Unificar store de sessão usado por teste e router  
**Status:** Auditoria concluída, patch pendente

---

## ACHADO CRÍTICO

### Antes (Atual — Quebrado)

| Componente | Função | Path | Campo Salvo | Campo Esperado | Sincronizado? |
|-----------|--------|------|------------|-----------------|--------------|
| **Teste (Runner)** | `salvar_dado_em_path()` | `Clientes/{tenant}/Sessoes/{actor}` | `confirmacao_pendente` | N/A (apenas lê estado depois) | ❌ NÃO |
| **Router** | `carregar_contexto_temporario()` (LEGADO) | `Clientes/{actor}/MemoriaTemporaria/contexto` | N/A | `aguardando_confirmacao_agendamento` | ❌ NÃO |
| **Router** | `salvar_contexto_temporario()` (LEGADO) | `Clientes/{actor}/MemoriaTemporaria/contexto` | Diversos (multiplos) | N/A | ❌ NÃO |

### Depois (Desejado — Correto)

| Componente | Função | Path | Campo | Sincronizado? |
|-----------|--------|------|-------|--------------|
| **Teste + Router** | `salvar_sessao_temporaria()` (NOVO) | `Clientes/{tenant}/Sessoes/{actor}` | `*` (todos) | ✅ SIM |
| **Teste + Router** | `carregar_sessao_temporaria()` (NOVO) | `Clientes/{tenant}/Sessoes/{actor}` | `*` (todos) | ✅ SIM |

---

## PROBLEMA RAIZ

O router **ainda usa a função legada** que:

1. **Salva em:** `Clientes/{actor}/MemoriaTemporaria/contexto` (sem tenant no path)
2. **Carrega de:** `Clientes/{actor}/MemoriaTemporaria/contexto` (sem tenant no path)
3. **O teste salva em:** `Clientes/{tenant}/Sessoes/{actor}` (diferente!)
4. **Resultado:** Contexto nunca é carregado = confirmacao_pendente não encontrada

---

## CAMPOS MAPEAMENTO

### Novo Contrato (Desejado)

```
Clientes/{tenant_id}/Sessoes/{actor_id}
{
  // ESTRUTURAL (preservar)
  "estado_fluxo": "agendando|idle|confirmacao|...",
  "aguardando_confirmacao_agendamento": true|false,
  "aguardando_confirmacao_cancelamento": true|false,
  "ultima_acao": "criar_evento|ajuste_incremental|...",
  
  // FLUXO AGENDAMENTO (draft)
  "draft_agendamento": {
    "profissional": "Bruna",
    "servico": "corte",
    "data_hora": "2026-06-23T14:00:00",
    "modo_prechecagem": true
  },
  "dados_confirmacao_agendamento": {
    "profissional": "Bruna",
    "servico": "corte",
    "data_hora": "2026-06-23T14:00:00",
    "descricao": "Corte com Bruna"
  },
  
  // FLUXO CANCELAMENTO
  "cancelamento_pendente": {
    "evento_id": "...",
    "resumo_evento": {...}
  },
  
  // INTERPRETAÇÃO
  "interpretacao_conversacional": {
    "intencao": "negacao_confirmacao_agendamento|...",
    "entidades": {...}
  },
  "intencao_conversacional": "negacao_confirmacao_agendamento",
  
  // METADADOS
  "_tenant_id_guard": "{tenant_id}",
  "_actor_id": "{actor_id}",
  "_schema_version": 2,
  "_updated_at": "2026-06-22T20:30:00",
  "_migrado_em": "2026-06-22T20:00:00"  // se vem de legado
}
```

---

## ALTERAÇÕES NECESSÁRIAS

### 1. Router — Trocar funções

**Arquivo:** `router/principal_router.py`

**Mudança 1:** Linha ~3359 (carregamento inicial)

```python
# ANTES (LEGADO):
ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}

# DEPOIS (NOVO):
ctx = await carregar_sessao_temporaria(user_id, tenant_id=dono_id) or {}
```

**Mudança 2:** Todas as salvagens de contexto

```python
# ANTES (LEGADO):
await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)

# DEPOIS (NOVO):
await salvar_sessao_temporaria(user_id, ctx, tenant_id=dono_id)
```

### 2. Imports Router

**Arquivo:** `router/principal_router.py:6`

```python
# ANTES:
from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario

# DEPOIS:
from utils.contexto_temporario import (
    salvar_sessao_temporaria,
    carregar_sessao_temporaria,
    # Legado fallback apenas se necessário
    salvar_contexto_temporario,
    carregar_contexto_temporario
)
```

### 3. Validação de Logs

**Esperado após patch:**

```
[DIAG] [LOAD SESSAO v2] path=Clientes/{tenant}/Sessoes/{actor} | source=novo | tenant={tenant} | actor={actor}
[DIAG] [SAVE SESSAO v2] path=Clientes/{tenant}/Sessoes/{actor} | tenant={tenant} | actor={actor}
[SESSION_STORE] write_path=Clientes/{tenant}/Sessoes/{actor}
[SESSION_STORE] read_path=Clientes/{tenant}/Sessoes/{actor}
[SESSION_STORE] same_path=True
```

**NÃO esperado (fallback legado):**

```
[DIAG] [LOAD SESSAO v2 FALLBACK]  ← indicaria contexto vazio (erro)
[LOAD_CTX_LEGADO]  ← indicaria migração em progresso (aceitável)
```

---

## TESTE

**Novo setup (via utils.contexto_temporario):**

```python
await salvar_sessao_temporaria(
    actor_id="whatsapp:55119999007",
    contexto={
        "confirmacao_pendente": True,
        "draft_confirmacao": {...},
        "aguardando_confirmacao_agendamento": True,  # ← CAMPO CRÍTICO
        "dados_confirmacao_agendamento": {...}
    },
    tenant_id=tenant_id
)
```

---

## CONTRATO OFICIAL (APROVADO)

✅ **Único path para sessão:**
```
Clientes/{tenant_id}/Sessoes/{actor_id}
```

✅ **Funções para salvar:**
```
salvar_sessao_temporaria(actor_id, contexto, tenant_id)
```

✅ **Funções para carregar:**
```
carregar_sessao_temporaria(actor_id, tenant_id)
```

✅ **Legado (fallback SOMENTE se novo vazio):**
```
Clientes/{actor_id}/MemoriaTemporaria/contexto  ← com guard_tenant validation
```

---

## CHECKLIST PÓS-PATCH

- [ ] Router carrega via `carregar_sessao_temporaria()`
- [ ] Router salva via `salvar_sessao_temporaria()`
- [ ] Teste salva via `salvar_sessao_temporaria()` ou equivalente
- [ ] Logs mostram `[SESSION_STORE] same_path=True`
- [ ] Cenário 07 detecta negação (intenção_conversacional setada)
- [ ] Cenário 06 detecta confirmação (evento criado)
- [ ] Nenhuma referência a `MemoriaTemporaria/contexto` em novo código
- [ ] Fallback legado logado e rastrável

---

**Relatório auditoria:** 2026-06-22T20:35:00Z  
**Status:** Pronto para patch
