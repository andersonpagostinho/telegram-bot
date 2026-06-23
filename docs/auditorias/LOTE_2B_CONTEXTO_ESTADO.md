# LOTE 2B — Auditoria: Contexto e Estado

**Data:** 2026-06-22 00:30  
**Cenários:** 04 (Ambiguidade + contexto), 08 (Msg curta + contexto), 10 (Rajada)  
**Status:** Diagnóstico forense (SEM correções)  

---

## 🚨 DESCOBERTA CRÍTICA — RAIZ COMUM A TODOS 3 CENÁRIOS

```
Path SALVO (moderno):     Clientes/{tenant_id}/Sessoes/{actor_id}
Path LIDO (legado):       Clientes/{actor_id}/MemoriaTemporaria/contexto
                          └─ COMPLETAMENTE DIFERENTE! 
```

**Problema:** Sistema tenta ler de path LEGADO (não-multitenant) quando deveria ler de path MODERNO.

---

## 📊 MATRIZ DE AUDITORIA

### CENÁRIO 04 — Ambiguidade com Contexto

| Aspecto | Salvo | Lido | Match | Status |
|---------|-------|------|-------|--------|
| **Path salvo** | `Clientes/teste_fluxo_p1_70c3583e/Sessoes/whatsapp:55119999004` | ✓ OK | - | ✅ |
| **Path lido** | - | `Clientes/whatsapp:55119999004/MemoriaTemporaria/contexto` | - | ❌ LEGADO |
| **tenant_id salvo** | `teste_fluxo_p1_70c3583e` | - | - | ✅ |
| **tenant_id lido** | - | `whatsapp:55119999004` (do path) | ❌ MISMATCH | ❌ |
| **Guard validação** | - | `guard_tenant=teste_fluxo_p1_5de52944 ≠ esperado=teste_fluxo_p1_70c3583e` | ❌ False | ❌ DESCARTADO |
| **estado_fluxo salvo** | (em Sessões) | - | - | ✅ |
| **estado_fluxo lido** | - | `onboarding_dono` (LEGADO) | ❌ ERRADO | ❌ |
| **classificador_contexto** | - | `todas as features = False` | ❌ VAZIO | ❌ |

**Causa Raiz:** Path mismatch + guard validation descarta contexto legado por tenant divergência

---

### CENÁRIO 08 — Mensagem Curta com Contexto

| Aspecto | Salvo | Lido | Match | Status |
|---------|-------|------|-------|--------|
| **Path salvo** | `Clientes/teste_fluxo_p1_cf71d24c/Sessoes/whatsapp:55119999008` | ✓ OK | - | ✅ |
| **Path lido** | - | `Clientes/whatsapp:55119999008/MemoriaTemporaria/contexto` | - | ❌ LEGADO |
| **tenant_id salvo** | `teste_fluxo_p1_cf71d24c` | - | - | ✅ |
| **tenant_id lido** | - | `whatsapp:55119999008` (do path) | ❌ MISMATCH | ❌ |
| **Guard validação** | - | `guard_tenant=teste_fluxo_p1_836fab88 ≠ esperado=teste_fluxo_p1_cf71d24c` | ❌ False | ❌ DESCARTADO |
| **estado_fluxo salvo** | (em Sessões) | - | - | ✅ |
| **estado_fluxo lido** | - | `onboarding_dono` (LEGADO) | ❌ ERRADO | ❌ |
| **classificador_contexto** | - | `todas as features = False` | ❌ VAZIO | ❌ |

**Causa Raiz:** Idêntica ao cenário 04

---

### CENÁRIO 10 — Rajada Contraditória

| Aspecto | Salvo | Lido | Match | Status |
|---------|-------|------|-------|--------|
| **Path salvo (msg1)** | `Clientes/teste_fluxo_p1_cda15efe/Atores/whatsapp:55119999009` | ✓ OK | - | ✅ |
| **Path lido (msg1)** | - | `Clientes/whatsapp:55119999009/MemoriaTemporaria/contexto` | - | ❌ LEGADO |
| **tenant_id salvo (msg1)** | `teste_fluxo_p1_cda15efe` | - | - | ✅ |
| **tenant_id lido (msg1)** | - | `whatsapp:55119999009` | ❌ MISMATCH | ❌ |
| **Guard validação (msg1)** | - | `guard_tenant=teste_fluxo_p1_dac634c9 ≠ esperado=teste_fluxo_p1_cda15efe` | ❌ False | ❌ DESCARTADO |
| **estado_fluxo salvo (msg1)** | `None` (novo) | - | - | ✅ |
| **estado_fluxo lido (msg1)** | - | `onboarding_dono` (LEGADO) | ❌ ERRADO | ❌ |
| **Após msg1: novo contexto** | - | `aguardando_horario` (criar novo em tenant vazio) | ⚠️ | ⚠️ |
| **classificador_contexto (msg2)** | - | `todas as features = False` | ❌ VAZIO | ❌ |

**Causa Raiz:** Path mismatch causando estado perdido entre msg1 e msg2

---

## 🔍 Responder Perguntas Obrigatórias

### Q1: O contexto existe no Firestore?
✅ **SIM** — Logs confirmam salvamento em `Clientes/{tenant_id}/Sessoes/{actor_id}`

### Q2: O router lê o mesmo path onde o teste salvou?
❌ **NÃO** — Router lê `Clientes/{actor_id}/MemoriaTemporaria/contexto` (LEGADO)

### Q3: O guard multi-tenant descarta o contexto?
✅ **SIM** — `guard_validacao: match=False` → contexto descartado com `[CTX_LEGADO_TENANT_MISMATCH]`

### Q4: O campo está salvo com nome diferente?
Não aplicável — todo path está divergindo

### Q5: O campo está salvo dentro de draft, mas lido na raiz?
❌ **Não** — Draft está em Sessões, router procura em MemoriaTemporaria

### Q6: O contexto é carregado depois da classificação?
✅ **SIM** — Log mostra: `[DIAG_CARREGAR]` DEPOIS `[CLASSIFICADOR CONTEXTO]` (ordem errada!)

### Q7: Existe duplicidade entre Sessao, Sessoes, MemoriaTemporaria?
✅ **SIM CRÍTICO:**
- `Clientes/{tenant_id}/Sessoes/{actor_id}` (MODERNO - onde teste salva)
- `Clientes/{actor_id}/MemoriaTemporaria/contexto` (LEGADO - onde router lê)

---

## 🎯 Tabela Final Consolidada

| Cenário | Path Salvo | Path Lido | Campo Perdido | Ponto da Perda | Causa Raiz | Patch Recomendado |
|---------|---|---|---|---|---|---|
| **04** | `Clientes/70c3583e/Sessoes/55119999004` | `Clientes/55119999004/MemoriaTemporaria/contexto` | ALL | Guard validação | Migração incompleta para MT: lê legado, salva moderno | Usar path moderno em leitura também |
| **08** | `Clientes/cf71d24c/Sessoes/55119999008` | `Clientes/55119999008/MemoriaTemporaria/contexto` | ALL | Guard validação | Migração incompleta para MT | Usar path moderno em leitura também |
| **10** | `Clientes/cda15efe/Atores/55119999009` | `Clientes/55119999009/MemoriaTemporaria/contexto` | estado_fluxo (msg2) | Guard validação + ordem carregamento | Migração incompleta + carregamento late | Usar path moderno + carregar ANTES classificador |

---

## 📍 Funções Responsáveis

### Carregamento de Contexto
```
carregar_contexto_temporario()
└─ Lê de: Clientes/{actor_id}/MemoriaTemporaria/contexto  ← LEGADO
   Deveria ler: Clientes/{tenant_id}/Sessoes/{actor_id}  ← MODERNO
```

### Guard Validação
```
_verificar_tenant_contexto_legado()  ou equivalente
└─ Valida: guard_tenant vs esperado
└─ Falha quando: tenant_id_legado ≠ tenant_id_moderno
└─ Descarta contexto quando falha
```

### Classificador
```
classificador_contexto()
└─ Chamado DEPOIS de carregar (quando contexto já foi descartado!)
└─ Recebe: features vazias (all False)
└─ Output: modo_conversa='neutro', confianca=0
```

---

## 🧠 Conclusão

**Todos 3 cenários falham pela MESMA CAUSA:**

```
1. Teste salva em path MODERNO (multitenant)
2. Router tenta ler de path LEGADO (monoten tenant)
3. Path mismatch → guard descarta
4. classificador recebe contexto vazio
5. Sistema entra em "modo neutro" e ignora contexto
```

**Não é problema de campos específicos** (como no LOTE 2A).

**É problema de arquitetura:** Sistema foi parcialmente migrado para multitenant mas ainda tenta ler do caminho legado.

---

## ⚠️ Observação Crítica

Isto NÃO é "contexto não carregado" (LOTE 2A).

Isto é **"contexto carregado ERRADO de outro path, validado, descartado por mismatch de tenant"**.

A diferença:
- LOTE 2A: Arquivo não lê dados salvos no mesmo path
- LOTE 2B: Sistema lê dados SALVOS, mas de path LEGADO, e descarta por guard

---

## 📌 Próximo Passo

Consolidar com LOTE 2C para criar patch unificado que:
1. Conserte carregamento de contexto (LOTE 2B)
2. Conserte detecção de confirmação (LOTE 2A)
3. Conserte extração semântica (LOTE 2C - pendente)

