# INVESTIGAÇÃO: MESMA MENSAGEM, ROTAS DIFERENTES

**Data**: 2026-11-18  
**Status**: 🔍 **INVESTIGAÇÃO READ-ONLY CONCLUÍDA**  
**Escopo**: Rastreamento de bifurcação de roteamento para mesma mensagem multisserviço

---

## MENSAGEM DE TESTE

```
"Gostaria de verificar a possibilidade de agendar manicure e pedicure 
para o dia 20/11/2026, de preferência no mesmo atendimento, durante o 
período da tarde. Consigo chegar a partir das 14h, mas tenho um compromisso 
no final do dia e preciso terminar os dois serviços até, no máximo, 17h. 
Minha preferência é ser atendida pela Bruna..."
```

**Extração Base**:
- Serviços: `['manicure', 'pedicure']` ✅
- Data: `20/11/2026` ✅
- Intervalo: `14h-17h` ✅
- Profissional: `Bruna` ✅

---

## BIFURCAÇÃO PRINCIPAL

### Ponto de Decisão: `estado_fluxo` (Carregado do Firestore)

```
Entrada: mensagem de consulta multisserviço
   ↓
Linha 4913: ctx = await carregar_contexto_temporario_v2()
   ↓
Verificar ctx.get("estado_fluxo")
   ├─→ ROTA 1: Se estado_fluxo != "aguardando_data" (ou None/idle)
   │        ↓ Linha 5984 (ANTES_CONSULTA_INFORMATIVA_IDLE)
   │        → Fluxo INFORMATIVO
   │
   └─→ ROTA 2: Se estado_fluxo == "aguardando_data"
            ↓ Linha 8569 (GUARD_AGUARDANDO_DATA)
            → Fluxo CONTINUIDADE
```

---

## ROTA 1: ANTES_CONSULTA_INFORMATIVA_IDLE

**Localização**: `router/principal_router.py:5984+`

**Pré-condições**:
```python
estado_fluxo = ctx.get("estado_fluxo")  # None, "idle", ou outro não "aguardando_data"
intencao_conv = ctx.get("intencao_conversacional")

if intencao_conv != "agendamento_direto" and not confirmacao_pendente:
    # → Entra em ANTES_CONSULTA_INFORMATIVA_IDLE
```

**Processamento da Mensagem**:

```
Passo 1: Extração de serviços (Linha 6010)
  servicos_multiplos_detectados = await extrair_multiplos_servicos_da_mensagem(texto_usuario, dono_id)
  → Resultado: ['manicure', 'pedicure'] ✅ (preserva ordem)

Passo 2: Enriquecimento de contexto (Linha 6017)
  contexto_consulta = enriquecer_contexto_consulta(contexto_consulta, texto_usuario)
  → Adiciona: intervalo_inicio=14, intervalo_fim=17

Passo 3: Extração de profissional (Linha 6022-6033)
  profissional_mencionada_features = class_intencao.get("features", {}).get("profissional_mencionada")
  → Bruna (se detectada pela IA)

Passo 4: Atribuição de servicos_opcao
  → NÃO ATRIBUÍDO em ROTA 1 (apenas contexto_consulta["servicos_multiplos"])

Passo 5: Chamada ao motor informativo (Linha 6054)
  resposta_informativa = await responder_consulta_informativa(
      texto_usuario=texto_usuario,
      dono_id=dono_id,
      actor_id=cliente_id,
      contexto_consulta=contexto_consulta
  )
```

**Fluxo de Entrada no Motor**:
```python
# Em informacao_service.py:168
contexto_resultado = ContextoResultadoConsulta(
    servicos=servicos_multiplos,  # ← VEM DE contexto_consulta["servicos_multiplos"]
    ...
)
```

**Resultado no Contexto**:
```python
# Linha 6128 (FIX 3.2.1)
contexto_consulta = {
    "servicos_mencionados": "manicure",  # Único serviço inicial
    "servicos_multiplos": ['manicure', 'pedicure'],  # ✅ ORDEM CORRETA
    "profissional_mencionada": "bruna"
}

# Linha 6113
ctx["contexto_consulta"] = contexto_consulta
ctx["servicos_opcao"] = None  # NÃO ATRIBUÍDO em ROTA 1
```

**Saída da ROTA 1**:
- Motor recebe: `servicos_multiplos=['manicure', 'pedicure']` ✅
- Ordem no log: `['manicure', 'pedicure']` ✅

---

## ROTA 2: CONTINUIDADE FORÇADA (aguardando_data)

**Localização**: `router/principal_router.py:8569+`

**Pré-condição**:
```python
if ctx.get("estado_fluxo") == "aguardando_data":  # Sessão em estado de espera
    # → GUARD_AGUARDANDO_DATA ativa
```

**Processamento da Mesma Mensagem**:

```
Passo 1: Interpretação de data/hora (Linha 8575)
  resultado = interpretar_data_e_hora(texto_usuario, return_metadata=True)
  → Encontra: 20/11/2026
  → Encapsula em dt

Passo 2: Extração de serviços NO GUARD (Linha 8596-8631)
  # ⚠️ RECONSTRÓI do catálogo (não usa extrair_multiplos_servicos())
  
  profs_multiplos = await buscar_subcolecao(...)
  servicos_catalogo_multiplos = set()  # ❌ SET = SEM ORDEM
  
  for _, prof_data in profs_multiplos.items():
      for s in prof_data.get("servicos"):
          servicos_catalogo_multiplos.add(normalizar(str(s)))
  
  # 🔥 LÓGICA CORRIGIDA (após Ponto 8628)
  servicos_ord = sorted(servicos_catalogo_multiplos, key=len, reverse=True)
  matches_com_posicao = []
  
  for serv_cat in servicos_ord:
      match_exato = re.search(...)
      if match_exato:
          matches_com_posicao.append((match_exato.start(), serv_cat))
  
  # Ordenar por posição
  matches_com_posicao.sort(key=lambda x: x[0])
  servicos_mencionados = [serv for _, serv in matches_com_posicao]
  → Resultado: ['manicure', 'pedicure'] ✅ (após correção Ponto 8628)

Passo 3: Atribuição de servicos_opcao (Linha 8628 - ANTES DA CORREÇÃO)
  ctx["servicos_opcao"] = servicos_mencionados  # ❌ ORDEM PODE ESTAR INVERTIDA
  
  (APÓS CORREÇÃO): ✅ ORDEM PRESERVADA
```

**Diferença Crítica entre Rotas**:

| Aspecto | ROTA 1 (ANTES_CONSULTA) | ROTA 2 (aguardando_data) |
|---------|------------------------|-------------------------|
| **Função de Extração** | `extrair_multiplos_servicos_da_mensagem()` | Lógica inline no GUARD |
| **Ordem Inicial** | ✅ Preservada por posição | ❌ Por tamanho (antes fix) |
| **Atribuição servicos_opcao** | Não atribuído | Atribuído em linha 8628 |
| **Entrada no Motor** | Via contexto_consulta | Via ctx direto |

---

## CONVERGÊNCIA NO MOTOR

**Ponto**: services/informacao_service.py:168

```python
# ROTA 1 passa:
contexto_resultado = ContextoResultadoConsulta(
    servicos=contexto_consulta.get("servicos_multiplos"),  # ['manicure', 'pedicure'] ✅
)

# ROTA 2 passa:
contexto_resultado = ContextoResultadoConsulta(
    servicos=ctx.get("servicos_opcao"),  # Pode ser ['pedicure', 'manicure'] ❌ (antes fix)
)
```

**Problema Original** (antes Ponto 8628 fix):
- ROTA 1: Motor recebe ['manicure', 'pedicure'] ✅
- ROTA 2: Motor recebe ['pedicure', 'manicure'] ❌

**Após Correção Ponto 8628**:
- ROTA 1: Motor recebe ['manicure', 'pedicure'] ✅
- ROTA 2: Motor recebe ['manicure', 'pedicure'] ✅

---

## DIAGRAMA DE FLUXO

```
┌─── ENTRADA: Mensagem Multisserviço ───────────┐
│ "manicure e pedicure para 20/11, 14-17h"      │
└─────────────────────────────────────────────┬──┘
                                              │
                    ┌─────────────────────────┴──────────────────┐
                    │  Carregar contexto do Firestore            │
                    │  ctx = await carregar_contexto_v2()        │
                    └────────┬────────────────┬──────────────────┘
                             │                │
                 ┌───────────┘                └────────────────┐
                 │                                             │
        ┌────────▼─────────┐                        ┌──────────▼────────┐
        │ ROTA 1           │                        │ ROTA 2            │
        │ (estado != "AD") │                        │ (estado == "AD")  │
        └────────┬─────────┘                        └──────────┬────────┘
                 │                                             │
        ┌────────▼────────────────┐           ┌────────────────▼─────────┐
        │ ANTES_CONSULTA_         │           │ GUARD_AGUARDANDO_DATA    │
        │ INFORMATIVA_IDLE        │           │ (Ponto 8569)             │
        │ (Linha 5984)            │           │                          │
        └────────┬────────────────┘           └────────────┬─────────────┘
                 │                                         │
        ┌────────▼────────────────┐           ┌────────────▼─────────────┐
        │ Extração:              │           │ CASO C: Extração         │
        │ extrair_multiplos_()    │           │ Inline (linhas 8596-31)  │
        │ → ['manicure', 'pedicure']          │ → ['manicure', 'pedicure'] 
        └────────┬────────────────┘           │   (após fix Ponto 8628) ✅
                 │                            └────────────┬──────────────┘
        ┌────────▼────────────────┐                        │
        │ Enriquecimento:         │           ┌────────────▼──────────┐
        │ intervalo, profissional │           │ Atribuição:          │
        │ → ctx["contexto_       │           │ ctx["servicos_opcao"]│
        │   consulta"]           │           │ = servicos_          │
        └────────┬────────────────┘           │   mencionados        │
                 │                            └────────────┬──────────┘
        ┌────────▼────────────────┐                        │
        │ Sem atribuição de       │           ┌────────────▼──────────┐
        │ servicos_opcao          │           │ Entrada no motor:    │
        │ (apenas contexto_       │           │ ctx["servicos_opcao"]│
        │ consulta)               │           │ = ['manicure',       │
        └────────┬────────────────┘           │   'pedicure'] ✅     │
                 │                            └────────────┬──────────┘
        ┌────────▼────────────────┐                        │
        │ Chamada ao motor:       │           ┌────────────▼──────────┐
        │ responder_             │           │ Entrada no motor:    │
        │ consulta_informativa()  │           │ Mesmo motor via      │
        │ com contexto_consulta   │           │ informacao_service   │
        └────────┬────────────────┘           └────────────┬──────────┘
                 │                                         │
        ┌────────▼─────────────────────────────────────────▼──────────┐
        │       MOTOR: informacao_service.py:168                      │
        │       ContextoResultadoConsulta(servicos=...)               │
        │       → Motor recebe ordem correta ✅                       │
        └───────────────────────────┬────────────────────────────────┘
                                    │
                        ┌───────────▼──────────┐
                        │ Resultado final:     │
                        │ ['manicure',         │
                        │  'pedicure'] ✅      │
                        └──────────────────────┘
```

---

## CONDIÇÕES EXATAS DE ENTRADA

### ROTA 1 (ANTES_CONSULTA_INFORMATIVA_IDLE)
```python
# Linha 5984+
# Entra se:
estado_fluxo in [None, "idle", "agendando", "aguardando_profissional", ...]
AND
intencao_conversacional != "agendamento_direto"
AND
NOT confirmacao_pendente
```

### ROTA 2 (GUARD_AGUARDANDO_DATA)
```python
# Linha 8569
# Entra SE:
estado_fluxo == "aguardando_data"
AND
interpretar_data_e_hora() encontra data válida
```

**Critério Decisivo**: O último `estado_fluxo` persistido em Firestore

---

## DIFERENÇAS DE ESTADO INICIAL

| Campo | ROTA 1 Típico | ROTA 2 Típico |
|-------|---------------|--------------|
| `estado_fluxo` | `None` ou `"idle"` | `"aguardando_data"` |
| `draft_agendamento` | Vazio ou legado | Pode ter dados anteriores |
| `contexto_consulta` | Vazio | Pode ter multisserviço anterior |
| `servicos_opcao` | Não atribuído | Pode ter valor anterior |
| `modo_operacao` | Não setado | Pode ser `"consulta_sem_autorizacao_atual"` |

---

## ORIGEM DE `servicos_opcao`

| Rota | Atribuição | Linha | Origem |
|-----|-----------|-------|--------|
| **ROTA 1** | Não atribuído | - | Via `contexto_consulta["servicos_multiplos"]` |
| **ROTA 2** | `ctx["servicos_opcao"] = servicos_mencionados` | 8628 | Reconstruído do catálogo (ANTES: pode inverter) |
| **ROTA 2 (AFTER FIX)** | Mesma | 8628 | Preserva ordem por posição ✅ |

---

## CONFIRMAÇÃO: ONDE OCORRE A INVERSÃO

**ANTES Ponto 8628 Fix**:
- ROTA 2, Linha 8607: `sorted(servicos_catalogo_multiplos, key=len, reverse=True)`
- Mesmo com aparência diferente, lógica é: "manicure" (8) == "pedicure" (8) → sort não-determinístico

**DEPOIS Ponto 8628 Fix**:
- ROTA 2, Linha 8631 (após linha 8628 fix): `matches_com_posicao.sort(key=lambda x: x[0])`
- Orderação preserva posição real: "manicure" aparece primeiro (posição menor)

---

## TESTE A/B REPRODUZÍVEL (Sem Alterar Produção)

### Setup Isolado

```python
# 1. Criar duas sessões simuladas

# Sessão A: estado_fluxo = None (vai para ROTA 1)
ctx_a = {
    "estado_fluxo": None,
    "intencao_conversacional": "consulta_multisservico",
    "confirmacao_pendente": None
}

# Sessão B: estado_fluxo = "aguardando_data" (vai para ROTA 2)
ctx_b = {
    "estado_fluxo": "aguardando_data",
    "contexto_consulta": {"servicos_multiplos": None},
    "servicos_opcao": None
}

# 2. Passar mesma mensagem para ambas as rotas

mensagem = "manicure e pedicure para 20/11, 14-17h"

# 3. Rastrear servicos em cada ponto:
# - Extração
# - Atribuição em ctx
# - Entrada no motor

# 4. Verificar ordem em cada etapa
```

### Pontos de Observação

```
ROTA 1:
  - Linha 6010: servicos_multiplos_detectados = ?
  - Linha 6012: contexto_consulta["servicos_multiplos"] = ?
  - Linha 6054: responder_consulta_informativa recebe ?

ROTA 2:
  - Linha 8603: texto_norm_multiplos = ?
  - Linha 8631: matches_com_posicao.sort() resultado = ?
  - Linha 8628: ctx["servicos_opcao"] = ?
```

---

## CONCLUSÃO

**Bifurcação é Determinística**:
- Fator decisivo: `estado_fluxo` (do Firestore)
- Se `None`/`idle`: ROTA 1 (ANTES_CONSULTA_INFORMATIVA_IDLE)
- Se `"aguardando_data"`: ROTA 2 (GUARD_AGUARDANDO_DATA)

**Inversão Detectada**:
- Ocorria em ROTA 2, linha 8607 (sorted by len)
- Corrigida em Ponto 8628 (preserva por posição)

**Ambas as Rotas Agora Preservam Ordem** ✅ (após fix)

---

**Status**: 🔍 Investigação Completa  
**Recomendação**: Teste A/B com sessões isoladas para validar ambos os caminhos

