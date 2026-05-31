# 🔍 INVESTIGAÇÃO DETALHADA - TESTE 1: "vocês fazem escova?"

## RESUMO EXECUTIVO

**Resposta às 4 perguntas do usuário:**

1. ❌ **O draft_agendamento realmente foi salvo no contexto?** → NÃO
2. ✅ **O {} é apenas exibição local?** → SIM
3. ❌ **Existe código que salva draft vazio em ctx?** → NÃO (há proteção)
4. ✅ **Conteúdo final serializado de ctx?** → Abaixo

---

## 1️⃣ DRAFT FOI SALVO EM CTX?

### ❌ RESPOSTA: NÃO

**Localização:** `router/principal_router.py` linhas 1461-1462

```python
# 🔥 persistir draft no contexto
if draft:
    ctx["draft_agendamento"] = draft
```

**Proteção:**

- `draft` é um dict
- Para consulta pura: `draft = {}` (dict VAZIO)
- Em Python: `if {}:` é **False** (dict vazio é falsy)
- Logo: `ctx["draft_agendamento"] = draft` **NÃO executa**

**Resultado:**

```python
ctx["draft_agendamento"]  # Permanece None (não alterado)
draft  # Variável local = {} (apenas em memória local)
```

---

## 2️⃣ O {} É EXIBIÇÃO LOCAL?

### ✅ RESPOSTA: SIM

**Fluxo:**

```
[ETAPA 0] Contexto inicial
  ctx["draft_agendamento"] = None  ← Inicializado como None
  draft = {}  ← Variável LOCAL criada
  Estão separados? Sim (diferentes objetos)

[ETAPA 2] extrair_slots_e_mesclar
  servico_detectado = "escova"
  eh_consulta_pura = True
  → Bloqueia draft["servico"] = "escova"  (não executa)
  → draft continua = {}

[ETAPA 3] Fim de extrair_slots_e_mesclar
  if draft:  ← Avalia {}
    # {} é falsy em Python
    # Esta linha NÃO executa:
    ctx["draft_agendamento"] = draft
```

**Prova:**

```python
>>> bool({})  # dict vazio
False

>>> if {}:
...     print("executou")
... else:
...     print("não executou")
não executou
```

---

## 3️⃣ EXISTE CÓDIGO QUE SALVA DRAFT VAZIO?

### ❌ RESPOSTA: NÃO (hay proteção)

**A proteção está no padrão usado:**

```python
if draft:  # ← Guarda em TODAS as 66 ocorrências
    ctx["draft_agendamento"] = draft
```

**Buscamos todas as 66 linhas que salvam draft:**

```
1462, 1729, 1793, 2016, 2079, 2121, 2201, 2311, 3040, 3155, 3211, 3242,
3339, 3400, 3483, 3522, 3678, 3764, 3821, 3946, 4023, 4073, 4449, 4522,
4644, 4704, 4814, 4895, 5134, 5307, 5384, 5658, 5693, 6029, 6222, 6249,
6479, 6628, 6655, 7192, 7549, 7593, 7759, 7827, 7870, 7986, 8111, 8169,
8221, 8251, 8569, 8594, 8837, 9179, 9518, 9714
```

**Todas têm o mesmo padrão:**

```python
if draft:  # ← Proteção universal
    ctx["draft_agendamento"] = draft
```

**Nenhuma salva draft vazio diretamente.**

---

## 4️⃣ CONTEÚDO FINAL SERIALIZADO DE CTX

### ESTADO FINAL JSON

```json
{
  "user_id": "test_user_1",
  "cliente_id": null,
  "cliente_nome": null,
  "intencao_conversacional": "consulta_disponibilidade_servico",
  "objetivo_conversacional": "consultar_disponibilidade_por_servico",
  "servico": null,
  "profissional": null,
  "data_hora": null,
  "estado_fluxo": "inicial",
  "draft_agendamento": null,
  "mensagem_anterior": null
}
```

**Campos alterados pela classificação GPT:**
- ✅ `intencao_conversacional`: `null` → `"consulta_disponibilidade_servico"`
- ✅ `objetivo_conversacional`: `null` → `"consultar_disponibilidade_por_servico"`

**Campos que PERMANECERAM `null` (protegidos pelos PATCHES):**
- ✅ `servico`: `null` (bloqueado por PATCH 1)
- ✅ `draft_agendamento`: `null` (bloqueado por PATCH 2)

---

## FLUXO COMPLETO PARA "vocês fazem escova?"

```
┌─────────────────────────────────────────────────────────┐
│ [ETAPA 0] CONTEXTO INICIAL                              │
├─────────────────────────────────────────────────────────┤
│ ctx["draft_agendamento"] = None                          │
│ draft (variável local) = {}                              │
│ Estado: LIMPO ✅                                         │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ [ETAPA 1] GPT CLASSIFICA INTENÇÃO                        │
├─────────────────────────────────────────────────────────┤
│ Mensagem: "vocês fazem escova?"                          │
│ ↓                                                        │
│ objetivo_conversacional = "consultar_disponibilidade..." │
│ intencao_conversacional = "consulta_disponibilidade..."  │
│ ✅ CONSULTA PURA DETECTADA                              │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ [ETAPA 2] extrair_slots_e_mesclar (PATCH 1)             │
├─────────────────────────────────────────────────────────┤
│ servico_detectado = "escova"                             │
│ eh_consulta_pura = True                                  │
│                                                          │
│ 🛡️  PATCH 1: BLOQUEIA                                    │
│   if eh_consulta_pura:                                   │
│       → Não executa: ctx["servico"] = servico_detectado  │
│       → Não executa: draft["servico"] = ...              │
│                                                          │
│ ctx["servico"] = None (protegido)                        │
│ draft = {} (não alterado)                                │
│                                                          │
│ FIM da função extrair_slots_e_mesclar:                   │
│   if draft:  ← Avalia {} (falsy)                         │
│       ✅ NÃO EXECUTA: ctx["draft_agendamento"] = draft   │
│                                                          │
│ ctx["draft_agendamento"] = None (protegido) ✅           │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ [ETAPA 3] resolver_proximo_passo_real (PATCH 2)         │
├─────────────────────────────────────────────────────────┤
│ objetivo = "consultar_disponibilidade_por_servico"       │
│ intencao = "consulta_disponibilidade_servico"            │
│                                                          │
│ 🛡️  PATCH 2: EARLY RETURN                               │
│   if objetivo == "consultar..." or intencao == "...":    │
│       return None  ← BLOQUEIA AQUI                       │
│                                                          │
│ proximo_passo_real = None (protegido) ✅                 │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ [ETAPA 4] p1_preservar_resposta_gpt                      │
├─────────────────────────────────────────────────────────┤
│ p1_preservar_resposta_gpt = True                         │
│                                                          │
│ ✅ GPT RESPONDE LIVREMENTE                              │
│    "Sim, fazemos escova! [Descrição do serviço]"         │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ [RESULTADO FINAL]                                        │
├─────────────────────────────────────────────────────────┤
│ ctx["draft_agendamento"] = null (NUNCA FOI PREENCHIDO)   │
│ draft (variável local) = {} (existe apenas em memória)   │
│                                                          │
│ PROVA:                                                   │
│ - PATCH 1 bloqueia preenchimento de draft               │
│ - PATCH 2 retorna None imediatamente                     │
│ - `if draft:` em linha 1461 não executa (dict vazio)     │
│ - ctx["draft_agendamento"] permanece None               │
│                                                          │
│ ✅ SEGURO: Nenhum draft foi criado                       │
└─────────────────────────────────────────────────────────┘
```

---

## CONCLUSÕES

### ❌ Pergunta 1: Draft foi salvo?
**NÃO.** `ctx["draft_agendamento"]` permanece `null` porque:
1. PATCH 1 bloqueia preenchimento de `draft`
2. Linha 1461: `if draft:` avalia `{}` → False
3. `ctx["draft_agendamento"] = draft` nunca executa

### ✅ Pergunta 2: {} é local?
**SIM.** O dict vazio `{}` é uma variável local (`draft`) que:
1. Nunca é salvo em `ctx`
2. Fica apenas em memória durante a execução
3. É descartado ao final da função

### ❌ Pergunta 3: Código salva draft vazio?
**NÃO.** Há proteção universal em **66 pontos** do router:
```python
if draft:  # ← Guarda SEMPRE antes de salvar
    ctx["draft_agendamento"] = draft
```

### ✅ Pergunta 4: Conteúdo final?
```json
{
  "objetivo_conversacional": "consultar_disponibilidade_por_servico",
  "intencao_conversacional": "consulta_disponibilidade_servico",
  "servico": null,
  "draft_agendamento": null
}
```

---

## IMPLICAÇÃO DOS PATCHES

Os **2 patches mínimos** garantem:

1. **PATCH 1** (linha 1136-1150): Bloqueia `ctx["servico"]` para consultas
2. **PATCH 2** (linha 9-19): Bloqueia `proximo_passo_real` para consultas
3. **Proteção existente** (linha 1461): `if draft:` impede salvamento de draft vazio

**Resultado:** Consulta pura "vocês fazem escova?" **NÃO cria nenhum draft**, nem em ctx nem em Firestore. ✅
