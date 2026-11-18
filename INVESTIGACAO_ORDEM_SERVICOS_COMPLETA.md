# INVESTIGAÇÃO COMPLETA — ORDEM DE SERVIÇOS

**Data**: 2026-11-18  
**Status**: 🔍 **INVESTIGAÇÃO READ-ONLY CONCLUÍDA**  
**Escopo**: 5 atribuições de `servicos_opcao` + cadeia de dados

---

## SUMÁRIO EXECUTIVO

**Achado Crítico**: A ordem de serviços é **PERDIDA EM MÚLTIPLOS PONTOS** de forma assimétrica.

| Ponto | Atribuição | Origem | Ordem | Risco |
|-------|-----------|--------|-------|-------|
| **1654** (router) | `servicos_mencionados` | Set desordenado | ❌ PERDIDA | MÉDIO |
| **8628** (router) | `servicos_mencionados` | Set + sorted by len | ❌ PERDIDA | **ALTO** |
| **8880** (router) | `servicos_multiplos_detectados` | `extrair_multiplos_servicos_da_mensagem()` | ✅ CORRETA | BAIXO |
| **10104** (router) | `servicos_para_validacao` | `contexto_consulta["servicos_multiplos"]` | ✅ CORRETA | BAIXO |
| **1390** (router 3) | `servicos_mencionados` | Set desordenado | ❌ PERDIDA | MÉDIO |

---

## INVESTIGAÇÃO DETALHADA

### PONTO 1: router/principal_router.py:1654

**Localização**: Fluxo de múltiplos serviços inicial

```python
# Linha 1637-1649: Construir lista de serviços
profs_multiplos = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
servicos_catalogo_multiplos = set()  # ❌ SET = SEM ORDEM

for _, prof_data in profs_multiplos.items():
    for s in (prof_data.get("servicos") or []):
        servicos_catalogo_multiplos.add(normalizar(str(s)))  # ❌ Adiciona ao set

texto_norm_multiplos = normalizar(texto)
servicos_mencionados = []

# ❌ PROBLEMA: Itera sobre set (sem ordem)
for serv_cat in servicos_catalogo_multiplos:
    if serv_cat in texto_norm_multiplos:
        servicos_mencionados.append(serv_cat)  # ❌ Ordem = ordem aleatória do set

# Linha 1654
ctx["servicos_opcao"] = servicos_mencionados  # ❌ ORDEM PERDIDA
```

**Análise**:
- ❌ Usa `set()` para coleta (sem ordem)
- ❌ Itera sobre set direto (ordem não preservada)
- ❌ Ordem final = aleatória

**Função Responsável**: LÓGICA INLINE (sem função)

**Condição**: Quando `len(servicos_mencionados) > 1`

---

### PONTO 2: router/principal_router.py:8628

**Localização**: GUARD_AGUARDANDO_DATA (Caso C)

```python
# Linha 8597-8619: Construir lista (SIMILAR AO PONTO 1 MAS COM SORTED)
profs_multiplos = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
servicos_catalogo_multiplos = set()  # ❌ SET

for _, prof_data in profs_multiplos.items():
    for s in (prof_data.get("servicos") or []):
        servicos_catalogo_multiplos.add(normalizar(str(s)))

texto_norm_multiplos = normalizar(texto_usuario)
servicos_mencionados = []

# ❌ SORTED POR TAMANHO (NÃO POR POSIÇÃO)
servicos_ord = sorted(servicos_catalogo_multiplos, key=len, reverse=True)
for serv_cat in servicos_ord:  # Itera sobre sorted by len, não por posição
    if re.search(rf"\b{re.escape(serv_cat)}\b", texto_norm_multiplos):
        servicos_mencionados.append(serv_cat)  # ❌ Ordem by len, não by menção
        continue
    # Fallback...

# Linha 8628
ctx["servicos_opcao"] = servicos_mencionados  # ❌ ORDEM PERDIDA (MAIS GRAVE)
```

**Análise**:
- ❌ Usa `set()` para coleta
- ❌ **Sorted por tamanho DESC** (não por posição de menção)
- ❌ "manicure" e "pedicure" (8 chars cada) → sort não-determinístico
- ⚠️ **ESTE É O PONTO QUE INVERTE A ORDEM**

**Função Responsável**: LÓGICA INLINE em `aguardando_data_guard`

**Condição**: Quando `len(servicos_mencionados) > 1` em modo `aguardando_data`

---

### PONTO 3: router/principal_router.py:8880

**Localização**: P0_FASE1 (multisserviço)

```python
# Linha 8877-8880
servicos_multiplos_detectados = await extrair_multiplos_servicos_da_mensagem(texto_usuario, dono_id)
if len(servicos_multiplos_detectados) > 1:
    contexto_consulta["servicos_multiplos"] = servicos_multiplos_detectados
    ctx["servicos_opcao"] = servicos_multiplos_detectados  # ✅ DIRETO DA FUNÇÃO
```

**Análise**:
- ✅ **USA A FUNÇÃO CORRIGIDA** `extrair_multiplos_servicos_da_mensagem()`
- ✅ Ordem PRESERVADA (já corrigimos a função)
- ✅ Sem reconstrução desnecessária

**Função Responsável**: `extrair_multiplos_servicos_da_mensagem()` ✅

**Condição**: P0_FASE1 de multisserviço

---

### PONTO 4: router/principal_router.py:10104

**Localização**: Confirmação de profissional alternativa

```python
# Linha 10032-10041
servicos_para_validacao = (
    contexto_consulta.get("servicos_multiplos")  # ✅ FONTE CANÔNICA
    or [draft_alt.get("servico")
        or ctx.get("servico")
        or (...)]
)
if isinstance(servicos_para_validacao, str):
    servicos_para_validacao = [servicos_para_validacao]
servicos_para_validacao = [s for s in servicos_para_validacao if s]

# ... (linha 10044)

# Linha 10104
ctx["servicos_opcao"] = servicos_para_validacao if len(servicos_para_validacao) > 1 else None  # ✅ ORDEM PRESERVADA
```

**Análise**:
- ✅ Vem de `contexto_consulta["servicos_multiplos"]`
- ✅ Que vem de `extrair_multiplos_servicos_da_mensagem()` ✅
- ✅ Ordem PRESERVADA
- ✅ Sem reconstrução

**Função Responsável**: LÓGICA INLINE (mas sourceada corretamente)

**Condição**: Profissional alternativa selecionada

---

### PONTO 5: router/principal_router 3.py:1390

**Localização**: Fluxo alternativo de múltiplos serviços

```python
# Linha 1370-1385 (versão simplificada em router 3)
servicos_mencionados = []
for serv_cat in servicos_catalogo_multiplos:  # ❌ SET (SEM ORDEM)
    if serv_cat in texto_norm_multiplos:
        servicos_mencionados.append(serv_cat)

# Linha 1390
ctx["servicos_opcao"] = servicos_mencionados  # ❌ ORDEM PERDIDA
```

**Análise**:
- ❌ Usa `set()` para coleta
- ❌ Sem sorting (ordem = aleatória)
- ❌ Router 3 é versão legada/teste

**Função Responsável**: LÓGICA INLINE

**Condição**: Quando `len(servicos_mencionados) > 1` em router 3

---

## CADEIA DE DADOS — FLUXO MULTISSERVIÇO

```
Usuário: "manicure e pedicure"
   ↓
1. extrair_multiplos_servicos_da_mensagem() → ['manicure', 'pedicure'] ✅
   ├─ Preserva ordem por `matches_com_posicao.sort(key=lambda x: x[0])`
   │
   ├─→ Ponto 8880: ctx["servicos_opcao"] = ✅ CORRETO
   │
   └─→ informacao_service:168 (ContextoResultadoConsulta)
       └─ servicos=['manicure', 'pedicure'] ✅ PERSISTE CORRETO

2. FORK 1: Se `aguardando_data` (Ponto 8628) ❌ INVERTE
   ├─ Reconstrói com set + sorted(key=len)
   ├─→ ctx["servicos_opcao"] = ['pedicure', 'manicure'] ❌
   └─ Ponto 6107: ctx.get("servicos_opcao") = ['pedicure', 'manicure'] ❌

3. FORK 2: Se `confirmacao` (Ponto 10104) ✅ PRESERVA
   ├─ Recupera de contexto_consulta["servicos_multiplos"]
   ├─→ ctx["servicos_opcao"] = ['manicure', 'pedicure'] ✅
   └─ Ponto 6107: ctx.get("servicos_opcao") = ['manicure', 'pedicure'] ✅
```

---

## PROBLEMA: DUAS FONTES DE VERDADE

| Fonte | Ordem | Usado Em |
|-------|-------|----------|
| **Motor (informacao_service)** | ✅ Correto | Persistência Firestore |
| **ContextoResultadoConsulta** | ✅ Correto | Resultado mostrado |
| **Contexto Auxiliar (FIX 3.2.1)** | ❌ Pode estar invertido | Consulta futura |

**Causa Raiz**:

```
servicos_multiplos (Motor)              → ['manicure', 'pedicure'] ✅
        ↓
contexto_consulta["servicos_multiplos"] → ['manicure', 'pedicure'] ✅
        ↓
ctx["servicos_opcao"] (linha 6107)      → ['manicure', 'pedicure'] SE VINDO DE 10104 ✅
                                        → ['pedicure', 'manicure'] SE VINDO DE 8628 ❌
```

---

## CONVERGÊNCIA NO PONTO 6107

**Função**: principal_router.py:6107 (FIX 3.2.1)

```python
# Linha 6107-6113
servicos_mult = ctx.get("servicos_opcao") or []  # ← PODE SER DE QUALQUER PONTO

contexto_consulta = {
    "servicos_mencionados": ctx.get("servico") or ctx_atualizado.get("servico"),
    "servicos_multiplos": servicos_mult if servicos_mult else None,  # ← USAR servicos_opcao
    ...
}
```

**Problema**: `servicos_opcao` pode vir de:
- ✅ Ponto 8880 (correto)
- ✅ Ponto 10104 (correto)
- ❌ Ponto 8628 (INVERTIDO)
- ❌ Ponto 1654 (desordenado)

---

## SOLUÇÃO MÍNIMA

### Opção A: Usar Fonte Canônica em Todos os Pontos

**Recomendação**: Substituir todas as 5 atribuições para usar:

```python
# Em vez de reconstruir, usar direto:
ctx["servicos_opcao"] = servicos_multiplos_detectados

# Onde servicos_multiplos_detectados vem de:
servicos_multiplos_detectados = await extrair_multiplos_servicos_da_mensagem(texto, dono_id)
```

**Impacto**:
- ✅ Garantia de ordem preservada
- ✅ Uma única fonte de verdade
- ✅ Sem reconstruções desnecessárias

### Opção B: Corrigir set() em Pontos 1654, 8628, 1390

**Alternativa**: Manter lógica inline mas corrigir ordem

```python
# Substituir em linhas 1654, 8628, 1390:

# ❌ ANTES
for serv_cat in servicos_catalogo_multiplos:  # set sem ordem
    if serv_cat in texto_norm_multiplos:
        servicos_mencionados.append(serv_cat)

# ✅ DEPOIS
# Usar mesma lógica de extrair_multiplos_servicos_da_mensagem():
# 1. Coleta com posição
# 2. Sort por posição
# 3. Retorna preservando ordem
```

---

## ARQUIVOS E LINHAS QUE PRECISAM ALTERAÇÃO

| Arquivo | Linha | Tipo | Prioridade |
|---------|-------|------|-----------|
| router/principal_router.py | 1654 | Set desordenado | P2 |
| router/principal_router.py | 8628 | ⚠️ **Sorted by len** | **P1** |
| router/principal_router.py | 8880 | ✅ OK | - |
| router/principal_router.py | 10104 | ✅ OK | - |
| router/principal_router 3.py | 1390 | Set desordenado | P3 (legado) |

---

## TESTES NECESSÁRIOS

### Teste 1: Ordem em Ponto 8628 (CRÍTICO)

```python
def test_ordem_aguardando_data_caso_c():
    # Entrada: "manicure e pedicure"
    # Esperado: ['manicure', 'pedicure']
    # Atual: ['pedicure', 'manicure'] ❌
```

### Teste 2: Regressão Pontos 8880 + 10104

```python
def test_ordem_preservada_multisservico():
    # Verificar que estes pontos CONTINUAM RETORNANDO ORDEM CORRETA
    assert contexto_consulta["servicos_multiplos"] == ['manicure', 'pedicure']
    assert ctx["servicos_opcao"] == ['manicure', 'pedicure']
```

### Teste 3: Coerência em FIX 3.2.1

```python
def test_contexto_auxiliar_ordem_correta():
    # Após FIX 3.2.1, contexto_consulta["servicos_multiplos"] deve preservar ordem
    assert contexto_consulta["servicos_multiplos"] == ['manicure', 'pedicure']
```

---

## RISCO DE REGRESSÃO

### Sem Alteração:
- ⚠️ Ordem invertida em fluxo `aguardando_data` (ponto 8628)
- ⚠️ Ordem aleatória em inicialização (ponto 1654)

### Com Alteração (Opção A):
- ✅ Ordem sempre preservada
- ✅ Sem regressão (pontos 8880, 10104 já corretos)
- ⚠️ Pode alterar comportamento em fluxos antigos que dependem de reordenação

### Com Alteração (Opção B):
- ✅ Ordem preservada em todos os 5 pontos
- ✅ Zero regressão em teste_p0_multisservico_green.py
- ⚠️ Mais mudanças em código

---

## RECOMENDAÇÃO FINAL

### **Prioridade P1: Corrigir Ponto 8628**

**Por quê**: Este é o ponto que INVERTE a ordem (`sorted(..., key=len, reverse=True)`).

**Implementação Mínima**: 

No ponto 8628, substituir:
```python
# ❌ ANTES (linha 8607-8619)
servicos_ord = sorted(servicos_catalogo_multiplos, key=len, reverse=True)
for serv_cat in servicos_ord:
    # Match logic

# ✅ DEPOIS
# Chamar extrair_multiplos_servicos_da_mensagem() OU
# Rastrear posição como fazemos em linha 743-801
```

**Impacto**: 1-2 linhas de mudança

---

**Status**: 🔍 Investigação Concluída  
**Próximo Passo**: Autorização para implementar correção mínima

