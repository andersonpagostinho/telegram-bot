# P0.4-INVESTIGAÇÃO 2 — Rastreamento Firestore → Context → Interpretação

**Data:** 2026-09-29  
**Status:** PROTOCOLO DE INVESTIGAÇÃO  
**Objetivo:** Descobrir por que nova mensagem "ola" recebe contexto antigo

---

## Fluxo a Investigar

```
Firestore (limpo após cleanup)
    ↓
carregar_sessao_temporaria()
    ↓
principal_router()
    ↓
classificar_contexto_mensagem()
    ↓
resolver_confirmacao_pendente()
    ↓
intencao_conversacional reconstruída?
```

---

## Pontos Críticos de Investigação

### PONTO 1: Leitura do Firestore

**Arquivo:** `utils/contexto_temporario.py:66-91`  
**Função:** `carregar_sessao_temporaria()`

**O que faz:**
```python
path_novo = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
data_novo = await buscar_dado_em_path(path_novo)
if data_novo:
    return data_novo  # Retorna EXATAMENTE como está em Firestore
```

**Pergunta:** Se Firestore está limpo (conforme P0.4 E2E validou), ctx carregado AQUI deveria estar limpo.

**VERIFICAR:** Conteúdo retornado por `buscar_dado_em_path()` imediatamente após cleanup.

---

### PONTO 2: Context do Handler (context.user_data)

**Arquivo:** `router/principal_router.py:3435-3441`

**O que faz:**
```python
ctx = {}
if context and hasattr(context, 'user_data') and context.user_data:
    ctx = context.user_data  # ⚠️ REUTILIZA CONTEXTO ANTIGO!
    print(f"[CTX_HANDLER] Usando contexto carregado pelo handler")
else:
    ctx = await carregar_contexto_temporario_v2(dono_id, cliente_id) or {}
```

**Pergunta:** `context.user_data` é limpado entre mensagens?

**VERIFICAR:** 
1. Quem popula `context.user_data`?
2. Quando é limpado?
3. Persiste após cleanup?

---

### PONTO 3: Decisão de Confirmação

**Arquivo:** `router/principal_router.py:3447-3466`  
**Função:** `resolver_confirmacao_pendente()`

**O que faz:**
```python
decisao_confirmacao = await resolver_confirmacao_pendente(
    ctx,
    texto_usuario.lower(),
    dono_id,
    user_id,
    funcoes={...}
)
```

**Pergunta:** `resolver_confirmacao_pendente()` pode reconstruir campos?

**VERIFICAR:** 
- Se ctx vazio entra, sai vazio?
- Se detecta "ola" como confirmação erroneamente?
- Se reutiliza `intencao_conversacional` de ctx anterior?

---

### PONTO 4: Normalização/Classificação

**Arquivo:** `services/classificador_conversa.py`  
**Funções:**
- `classificar_contexto_mensagem()`
- `classificar_intencao_conversacional()`

**Pergunta:** Essas funções criam campos?

**VERIFICAR:**
```python
# Exemplo do que pode estar acontecendo:
if ctx.get("intencao_conversacional"):  # ← Se houver no ctx
    reutilizar()  # ← Reutiliza valor antigo
elif texto_usuario == "ola":
    # Detectar como confirmação?
```

---

### PONTO 5: Intenção Antecipada

**Log observado contém:**
```
[INTENÇÃO_ANTECIPADA]
intencao_conversacional = confirmacao_agendamento
```

**Pergunta:** Onde essa "antecipação" ocorre?

**VERIFICAR:** Procurar por "INTENÇÃO_ANTECIPADA" no código.

---

## Checklist de Investigação

```
A. Firestore estava limpo? 
   [ ] Verificar Firestore ANTES de principal_router() ser chamado
   [ ] Validar que cleanup executou completamente
   
B. Context.user_data é o culpado?
   [ ] Verificar se context.user_data persiste entre mensagens
   [ ] Verificar se é limpo após cleanup
   [ ] Verificar se é limpado quando nova mensagem chega
   
C. Carregar_contexto_temporario_v2 retorna limpo?
   [ ] Instrumentar função com logging do conteúdo ANTES do return
   [ ] Comparar Firestore vs retorno
   
D. Resolver_confirmacao_pendente() reconstrói?
   [ ] Verificar se adiciona intencao_conversacional
   [ ] Verificar se cria draft_agendamento
   [ ] Verificar se altera estado_fluxo
   
E. Classificador reconstrui?
   [ ] Verificar se classificar_intencao_conversacional() cria campos
   [ ] Verificar se usa valores de ctx anterior
   
F. Cache/Memória intermediária?
   [ ] Redis?
   [ ] Dict global?
   [ ] Singleton?
   [ ] Cache de processo?
   
G. Múltiplas leituras do Firestore?
   [ ] Há multiple pontos que carregam contexto?
   [ ] Algum salva antes do principal_router?
```

---

## Hipóteses Principais

### Hipótese 1: context.user_data Persistente

**Problema:** `context.user_data` carrega contexto antigo e não é limpo.

**Evidência a procurar:** Handler que popula user_data sem cleanup.

**Próximo passo:** Rastrear todas as operações em `context.user_data`.

---

### Hipótese 2: Reutilização de Intenção

**Problema:** Se ctx tem `intencao_conversacional`, código reutiliza sem verificação.

**Evidência a procurar:** 
```python
if ctx.get("intencao_conversacional"):  # ← Problema aqui
    usar()
```

**Próximo passo:** Grep por "intencao_conversacional" com reutilização.

---

### Hipótese 3: Recontrução em Classificador

**Problema:** `classificar_intencao_conversacional()` cria campos que não existiam.

**Evidência a procurar:** Função que adiciona campos ao ctx.

**Próximo passo:** Verificar todos os `ctx["campo"] = valor` em classificador.

---

### Hipótese 4: Múltipla Leitura

**Problema:** Alguma função lê Firestore ANTES do cleanup, salva contexto em memória.

**Evidência a procurar:** Handlers que carregam contexto antes do principal_router.

**Próximo passo:** Rastrear ordem de execução.

---

## Investigação Obrigatória (Sem Código Alterado)

Para cada hipótese, produzir:

1. **Arquivo + Linha** — onde ocorre
2. **Conteúdo exato** — o que é atribuído
3. **Condição** — quando acontece
4. **Fonte** — de onde vem o valor

Exemplo de resultado esperado:

```
CAMPO: intencao_conversacional
STATUS: RECRIADO APÓS CLEANUP
ORIGEM 1: 
  Arquivo: router/principal_router.py:3447
  Função: resolver_confirmacao_pendente()
  Linha: if ctx.get("intencao_conversacional"):
  Problema: reutiliza valor antigo se existir em ctx
  
ORIGEM 2:
  Arquivo: services/classificador_conversa.py:87
  Função: classificar_intencao_conversacional()
  Linha: ctx["intencao_conversacional"] = extrair_intencao()
  Problema: cria novo valor sem validação de cleanup
```

---

## Resultado Esperado

Relatório com causa raiz:

```
CAMPO                          ORIGEM                    SOLUÇÃO
intencao_conversacional        [arquivo:linha]           [remover reutilização / validar cleanup]
estado_fluxo                   [arquivo:linha]           [...]
draft_agendamento              [arquivo:linha]           [...]
dados_confirmacao_agendamento  [arquivo:linha]           [...]
```

---

**Próximo:** Executar investigação rastreando cada ponto.
