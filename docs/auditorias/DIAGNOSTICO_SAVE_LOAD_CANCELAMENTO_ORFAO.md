# DIAGNÓSTICO P0 — Divergência Save/Load Após Cancelamento

**Data:** 2026-06-19  
**Status:** 🟡 INSTRUMENTAÇÃO ADICIONADA — AGUARDANDO EXECUÇÃO  
**Objetivo:** Provar se contexto limpo está sendo salvo no path correto

---

## 📊 Instrumentação de Logs Adicionada

### Ponto 1: ANTES do Save (linha 3391 em router/principal_router.py)

```
[DIAG_SAVE_PRE] tenant_id={valor} | actor_id={user_id} | path=Clientes/{tenant_id}/Sessoes/{user_id}
[DIAG_SAVE_PRE] estado_fluxo={valor} | cancelamento_pendente={True/False} | draft_agendamento={True/False} | dados_confirmacao={True/False}
[DIAG_SAVE_PRE] ctx_keys=[lista de chaves]
```

**O que analisar:**
- ✅ tenant_id está preenchido?
- ✅ estado_fluxo = "idle"?
- ✅ cancelamento_pendente = False/vazio?
- ✅ draft_agendamento = False/vazio?
- ✅ dados_confirmacao_agendamento = False/vazio?

---

### Ponto 2: DENTRO do Save (salvar_contexto_temporario)

#### 2a. ENTRADA
```
[DIAG_SALVAR] path_legado={path_legado} | tenant_id={valor} | user_id={user_id}
[DIAG_SALVAR] antes_merge: estado_fluxo={valor_old} | cancelamento_pendente={True/False}
[DIAG_SALVAR] depois_merge: estado_fluxo={valor_novo} | cancelamento_pendente={True/False} | keys_atualizadas=[chaves]
```

**O que analisar:**
- ✅ Qual path foi salvo? (Path legado vs V2)
- ✅ Antes de merge vs depois de merge — mudou corretamente?
- ✅ estado_fluxo mudou para "idle"?

#### 2b. SAÍDA
```
[DIAG_SALVAR] resultado_save={True/False} | tipo={tipo_resultado}
```

**O que analisar:**
- ✅ Retornou True (sucesso) ou False (falha)?
- ✅ Se False, por que? Verificar logs anteriores

---

### Ponto 3: DENTRO do Load (carregar_contexto_temporario)

#### 3a. INÍCIO
```
[DIAG_CARREGAR] path_legado={path_legado} | tenant_id={valor} | user_id={user_id}
[DIAG_CARREGAR] lido_legado: existe={True/False} | estado_fluxo={valor} | cancelamento_pendente={True/False}
```

**O que analisar:**
- ✅ Qual path foi lido?
- ✅ contexto existe? (True/False)
- ✅ **CRÍTICO:** estado_fluxo ainda = "aguardando_confirmacao_cancelamento"? (SE SIM, DIVERGÊNCIA CONFIRMADA)

#### 3b. VALIDAÇÃO
```
[DIAG_CARREGAR] guard_validacao: guard_tenant={valor} | esperado={tenant_id} | match={True/False}
```

**O que analisar:**
- ✅ Guard validou?
- ✅ Guard bate com tenant esperado?

#### 3c. RETORNO
```
[DIAG_CARREGAR] retornando_legado: estado_fluxo={valor} | cancelamento_pendente={True/False}
```

**O que analisar:**
- ✅ Qual estado foi retornado?
- ✅ Se ainda contém cancelamento_pendente, contexto não foi limpo!

---

## 🔍 Cenários de Diagnóstico Esperados

### ✅ Cenário CORRETO

```
MENSAGEM 1: "Quero cancelar..."
[OK] Salva com estado_fluxo="aguardando_confirmacao_cancelamento"

MENSAGEM 2: "Sim"
[DIAG_SAVE_PRE] estado_fluxo=idle | cancelamento_pendente=False | draft_agendamento=False
[DIAG_SALVAR] resultado_save=True
[DIAG_SALVAR] path_legado salvo com estado_fluxo=idle

MENSAGEM 3: "Quero corte..."
[DIAG_CARREGAR] lido_legado: existe=True | estado_fluxo=idle | cancelamento_pendente=False
[DIAG_CARREGAR] retornando_legado: estado_fluxo=idle | cancelamento_pendente=False
[OK] Fluxo continua normalmente
```

---

### ❌ Cenário PROBLEMA #1: Contexto Não Foi Salvo

```
MENSAGEM 2: "Sim"
[DIAG_SAVE_PRE] estado_fluxo=idle | cancelamento_pendente=False
[DIAG_SALVAR] resultado_save=True  ← Diz que salvou

MENSAGEM 3: "Quero corte..."
[DIAG_CARREGAR] lido_legado: estado_fluxo=aguardando_confirmacao_cancelamento ← AINDA VELHO!
[DIAG_CARREGAR] cancelamento_pendente=True ← AINDA EXISTE!

CAUSA RAIZ: Salvar retornou True mas Firestore não foi atualizado
           Problema possível: merge=True não remove campos
           Solução: usar DELETE_FIELD ou salvar explicitamente como None/False
```

---

### ❌ Cenário PROBLEMA #2: Salvar Retornou False

```
MENSAGEM 2: "Sim"
[DIAG_SAVE_PRE] tenant_id=null | estado_fluxo=idle
[DIAG_SALVAR] resultado_save=False

CAUSA RAIZ: tenant_id ausente
            Bloqueio do Patch P0 acionado
            Contexto nunca foi salvo
```

---

### ❌ Cenário PROBLEMA #3: Salvar em Path Errado

```
MENSAGEM 2: "Sim"
[DIAG_SALVAR] path_legado=Clientes/{user_id}/MemoriaTemporaria/contexto ← LEGADO!

MENSAGEM 3: "Quero corte..."
[DIAG_CARREGAR] path_legado lê o MESMO path
[OK] Funcionaria... MAS...

CAUSA RAIZ: V2 foi criado vazio antes, load tenta V2 primeiro (vazio)
            Depois fallback para legado (que tem dados antigos)
            V2 nunca é atualizado
            Legado continua tendo dados antigos

SOLUÇÃO: Salvar deve ir direto para V2: Clientes/{tenant_id}/Sessoes/{user_id}
```

---

### ❌ Cenário PROBLEMA #4: Pop não Remove do Firestore

```
MENSAGEM 2: "Sim"
[DIAG_SAVE_PRE] cancelamento_pendente=False ← LOCAL dict limpou
[DIAG_SALVAR] antes_merge: cancelamento_pendente=True  ← FIRESTORE tinha
[DIAG_SALVAR] depois_merge: cancelamento_pendente=False ← update removeu?

MENSAGEM 3: "Quero corte..."
[DIAG_CARREGAR] cancelamento_pendente=True ← VOLTA DO FIRESTORE!

CAUSA RAIZ: `ctx.pop()` remove da local dict
            `atual.update(ctx)` não remove campos não mencionados
            Firestore merge=True preserva campos não atualizados
            Resultado: campos removidos localmente mas persistidos no Firestore
```

---

## 🎯 Matriz de Diagnóstico

| Log esperado | Lido? | Significa |
|--------------|-------|-----------|
| `[DIAG_SAVE_PRE] estado_fluxo=idle` | ✅ | Limpeza local OK |
| `[DIAG_SALVAR] resultado_save=True` | ✅ | Salvar sucedeu |
| `[DIAG_CARREGAR] estado_fluxo=idle` | ✅ | Leitura correta |
| `[DIAG_CARREGAR] estado_fluxo=aguardando_...` | ❌ | **DIVERGÊNCIA ENCONTRADA** |
| `[DIAG_SAVE_PRE] tenant_id=null` | ❌ | Bloqueio P0 acionado |
| `[DIAG_SALVAR] resultado_save=False` | ❌ | Salvar falhou |

---

## 📋 Checklist de Análise

Após executar fluxo (cancelamento → "Sim" → novo agendamento):

### ✅ Verificações Críticas

- [ ] `[DIAG_SAVE_PRE]` aparece na mensagem 2?
- [ ] `[DIAG_SAVE_PRE]` mostra `estado_fluxo=idle`?
- [ ] `[DIAG_SAVE_PRE]` mostra `cancelamento_pendente=False`?
- [ ] `[DIAG_SALVAR]` mostra `resultado_save=True`?
- [ ] `[DIAG_CARREGAR]` aparece na mensagem 3?
- [ ] `[DIAG_CARREGAR] lido_legado` mostra `estado_fluxo=idle`?
- [ ] `[DIAG_CARREGAR] lido_legado` mostra `cancelamento_pendente=False`?
- [ ] `[DIAG_CARREGAR] retornando_legado` mostra `estado_fluxo=idle`?

---

## 🔍 Análise Por Cenário

### Se Cenário CORRETO:
```
→ Problema RESOLVIDO
→ Contexto está sendo salvo e carregado corretamente
→ Investigar linha 4171 ou cache
```

### Se Cenário PROBLEMA #1:
```
→ Merge não remove campos
→ Solução: Usar DELETE_FIELD ou salvar como None/False
→ Arquivo: utils/contexto_temporario.py:219
```

### Se Cenário PROBLEMA #2:
```
→ tenant_id ausente no handler de cancelamento
→ Solução: Garantir dono_id foi obtido (linha 3347)
→ Arquivo: router/principal_router.py:3391
```

### Se Cenário PROBLEMA #3:
```
→ Salvando em path legado ao invés de V2
→ Solução: Usar salvar_sessao_temporaria() ao invés de salvar_contexto_temporario()
→ Arquivo: router/principal_router.py:3391
```

### Se Cenário PROBLEMA #4:
```
→ ctx.pop() não remove de Firestore
→ Solução: Usar DELETE_FIELD explicitamente
→ Arquivo: utils/contexto_temporario.py
```

---

## 📊 Logs para Coletar

Para análise completa, coletar logs de um fluxo completo:

```
# Mensagem 1: "Quero cancelar com a Bruna"
[buscar: linhas com CANCELAMENTO]

# Mensagem 2: "Sim"
[buscar: linhas com DIAG_SAVE_PRE, DIAG_SALVAR, resultado_save]

# Mensagem 3: "Quero corte amanhã"
[buscar: linhas com DIAG_CARREGAR, lido_legado, retornando_legado]
```

---

## ✅ Como Usar Este Diagnóstico

1. **Executar fluxo normal:**
   - Usuario: "Cancelar corte com Bruna"
   - Sistema: oferece confirmação
   - Usuario: "Sim"
   - Sistema: cancela
   - Usuario: "Quero corte amanhã às 10"

2. **Coletar logs** com [DIAG_*] e [DIAG_CARREGAR]

3. **Comparar com cenários acima**

4. **Identificar qual PROBLEMA # ocorreu**

5. **Referência:** solução está indicada em cada cenário

---

## 📚 Referência

- **Salvar após cancelamento:** `router/principal_router.py:3386-3400`
- **Função salvar:** `utils/contexto_temporario.py:188-220`
- **Função carregar:** `utils/contexto_temporario.py:222-264`
- **Guard Rail:** `utils/contexto_temporario.py:205-207`

---

**Status:** 🟡 INSTRUMENTAÇÃO COMPLETA — Aguardando execução com logs para diagnóstico

