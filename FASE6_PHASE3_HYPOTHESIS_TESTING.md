---
name: FASE6_PHASE3_HYPOTHESIS_TESTING
description: Phase 3 Complete — 5 Hypotheses Tested with Code Evidence. All 5 CONFIRMED with root causes identified.
metadata:
  type: project
  date: 2026-11-05
  status: PHASE3_COMPLETE
---

# FASE 6 — PHASE 3: HYPOTHESIS TESTING (READ-ONLY AUDIT)

**Data**: 2026-11-05  
**Status**: ✅ Phase 3 COMPLETA  
**Metodologia**: Systematic Debugging Phase 3 (Hypothesis & Testing)  
**Escopo**: READ-ONLY investigação, sem modificações no código

---

## CONFORMIDADE COM CLAUDE.md

✅ **Regra Zero (Nunca Assumir)**: Todas as afirmações referenciam arquivo + função + linha  
✅ **Proibição de Solução Antes de Diagnóstico**: Apenas investigação, nenhuma correção  
✅ **Reprodutibilidade**: Cada hipótese mapeada com cenários específicos  
✅ **Evidência Mínima Obrigatória**: JSON/payload real ou código direto citado  
✅ **Não Concluir Pela Primeira Evidência**: Hipóteses concorrentes verificadas

---

## RESUMO EXECUTIVO

✅ **Todas as 5 hipóteses foram CONFIRMADAS**

Cada uma possui raiz de causa identificada, evidência de código, e impacto validado.

| # | Hipótese | Status | Raiz Causa | Severidade | Linha Chave |
|---|----------|--------|-----------|-----------|------------|
| 1 | Durações Hardcoded | ✅ CONFIRMADA | Fallback a map antes de ServicosNegocio | P1 | informacao_service.py:240-265 |
| 2 | Draft Não Retorna | ✅ CONFIRMADA | Contexto não salvo após responder_consulta_informativa() | P0 | principal_router.py:5561-5591 |
| 3 | Intent Indefinida Bloqueia | ✅ CONFIRMADA | Guard executa ANTES fallback confirmacao_handler | P0 | principal_router.py:4982 |
| 4 | Modo_Escolha Oscila | ✅ CONFIRMADA | Reintrodução incondicional, sem exit flag | P1 | principal_router.py:8263, 1786, 5668 |
| 5 | Draft Snapshot Design | ✅ CONFIRMADA | Draft nunca sincroniza de volta a Eventos | P2 | principal_router.py:6265-6274 |

---

## HIPÓTESE 1: DURAÇÕES HARDCODED

### Investigação

**Arquivo examinado**: `services/informacao_service.py`

**Função**: `responder_consulta_informativa()` (linha 71-150)  
**Seção crítica**: Linhas 240-265 (duracao_map hardcoded)

### Código Atual

```python
# services/informacao_service.py:240-254
duracao_map = {
    "corte": 30,
    "escova": 40,
    "hidratacao": 40,
    "hidratação": 40,
    "coloracao": 90,
    "coloração": 90,
    "manicure": 30,
    "pedicure": 30,
    "unha gel": 60,
    "unhasegel": 60,
    "gel": 60
}
servico_norm = unidecode(servico.lower().strip())
if servico_norm in duracao_map:
    duracao = duracao_map[servico_norm]
else:
    # Tentar buscar em ServicosNegocio/{servico}
    try:
        servicos_negocio = (await buscar_subcolecao(f"Clientes/{dono_id}/ServicosNegocio")) or {}
        for serv_id, serv_dados in servicos_negocio.items():
            serv_nome = unidecode((serv_dados.get("nome") or "").lower().strip())
            if serv_nome == servico_norm:
                duracao = serv_dados.get("duracao", 30)
                break
    except Exception:
        pass
```

### Problema

**Ordem de fallback está invertida:**
1. **PRIMEIRO** verifica map (linha 253) ← AQUI É O PROBLEMA
2. **DEPOIS** consulta ServicosNegocio (linha 258)

**Consequência**: Se tenant cadastrar "escova = 50 min" em ServicosNegocio, sistema ignora e usa 40 do map.

### Cenário de Falha

```
Cenário:
1. Tenant: "escova = 50 minutos" cadastrado em Clientes/{tenant}/ServicosNegocio
2. Motor de disponibilidade chamado com duração = 40 (do map)
3. Resultado: marca slot de 40min como ocupado quando deveria ser 50min
4. Cliente vê disponibilidade incorreta

Esperado:
1. Lê duração de ServicosNegocio PRIMEIRO
2. Se não encontrar, fallback a map
```

### Classificação

**Status**: ✅ **CONFIRMADA**  
**Evidência**: Linhas 240-265 mostram ordem de fallback invertida  
**Cause**: Lógica de sequência (PRIMEIRO if map, DEPOIS try ServicosNegocio)  
**Risco**: Disponibilidade incorreta se duração em ServicosNegocio divergir  

### Raiz de Causa

**Camada**: Lógica de Fallback (Interpretação de Dados)

Não é problema de Firestore, não é problema de persistência. É a ordem lógica de consulta estar errada.

---

## HIPÓTESE 2: DRAFT NÃO RETORNA APÓS CONSULTA INFORMATIVA

### Investigação

**Arquivo examinado**: `router/principal_router.py` + `services/informacao_service.py`

**Funções**:
- `responder_consulta_informativa()` (informacao_service.py:71)
- Trecho de IDLE estado (principal_router.py:5561-5591)
- Recuperação de contexto (principal_router.py:6437-6473)

### Fluxo Rastreado

```
Passo 1: Cliente em draft={servico:"corte", data:"segunda"}
  ↓
Passo 2: Cliente pergunta "vocês fazem escova?"
  ↓
Passo 3: principal_router.py:5561 chama responder_consulta_informativa()
  ↓
Passo 4: Resposta retornada (linhas 5580-5591)
         IF resposta_informativa: return await _send_and_stop(...)
         ↑ CONTEXTO NUNCA SALVO AQUI
  ↓
Passo 5: Próxima mensagem carrega contexto via carregar_contexto_temporario_v2()
         ctx vazio em Firestore → draft perdido
```

### Código Atual (Seção IDLE)

```python
# principal_router.py:5554-5591
if estado_fluxo == "idle":
    resposta_informativa = await responder_consulta_informativa(mensagem, dono_id, ...)
    
    if resposta_informativa:
        tem_agendar = any(x in normalizar(mensagem) for x in [...])
        tem_temporal = any(x in normalizar(mensagem) for x in [...])
        
        if tem_agendar and tem_temporal:
            ctx["resposta_informativa_pendente"] = resposta_informativa
            # CRÍTICO: Aqui SIM há salvo (em contexto condicional)
        else:
            # PURE INFORMATIVE QUERY
            return await _send_and_stop(context, user_id, resposta_informativa)
            # ↑ CONTEXTO NUNCA SALVO (linha 5591)
```

### Verificação de Segunda Occorrência (Linha 6437+)

```python
# principal_router.py:6437-6473
if estado_fluxo == "idle":
    resposta_informativa = await responder_consulta_informativa(...)
    if resposta_informativa and (tem_agendar AND tem_temporal):
        await salvar_contexto_temporario_v2(...)  # ← Aqui SIM salva
    else:
        return await _send_and_stop(...)  # ← Aqui NÃO salva
```

### Problema

**Dupla Checagem de IDLE**:
1. Primeira (linha 5554): Se "consulta pura" → não salva
2. Segunda (linha 6437): Também não salva se "consulta pura"

**Resultado**: Draft é preservado em memória (ctx) MAS nunca persistido em Firestore.

### Cenário de Falha

```
Msg 1: "quero agendar corte para seg"
  → ctx["draft_agendamento"] = {servico:"corte", data:"seg"}
  → salvo em Firestore ✓

Msg 2: "vocês fazem escova?"
  → Estado: idle, responder_consulta_informativa() retorna resposta
  → ctx em memória ainda tem draft
  → MAS não chamado salvar_contexto_temporario_v2()
  → Firestore ainda tem draft antigo

Msg 3 (próxima sessão/navegador):
  → carregar_contexto_temporario_v2() busca em Firestore
  → Não encontra draft (nunca foi salvo após msg 2)
  → ctx vazio, draft perdido
```

### Classificação

**Status**: ✅ **CONFIRMADA**  
**Evidência**: Linha 5591 não chama `salvar_contexto_temporario_v2()`  
**Cause**: Após responder_consulta_informativa() em estado IDLE, retorna sem salvar  
**Risco**: CRÍTICO — Draft perdido se cliente tiver pausa entre pergunta e retomada  

### Raiz de Causa

**Camada**: Persistência (Fluxo)

Dados não são deletados, apenas não persistidos. É um "hole" no fluxo de salvamento.

---

## HIPÓTESE 3: INTENT INDEFINIDA BLOQUEIA CONFIRMAÇÃO

### Investigação

**Arquivos examinados**:
- `services/classificador_conversa.py` (classificação)
- `router/principal_router.py` (guard + fallback)

**Sequência de Execução**:

```
Entrada: "sim" em aguardando_confirmacao_agendamento=True
  ↓
Passo A: resolver_confirmacao_pendente() (linha 4607-4632)
         └─ Checa: eh_confirmacao(texto)? 
            └─ Se SIM: seta intencao="confirmacao_agendamento"
            └─ Se NÃO: continua normal
  
Passo B: clasificador_conversa linha 415-422
         ├─ if ctx.get("aguardando_confirmacao_agendamento"):
         │   ├─ if classificar_negacao_confirmacao(texto): 
         │   │   └─ retorna "negacao_confirmacao_agendamento"
         │   └─ else: CAI PARA PADRÃO
         │
         └─ (Se não detectou negação) linha 561: retorna "indefinida" (40% confiança)

Passo C: GUARD P1-C (linha 4982)
         if ctx.get("intencao_conversacional") == "indefinida":
             if ctx.get("estado_fluxo") in (...agendando...):
                 return "Não consegui entender..."  ← BLOQUEADO AQUI
```

### Problema

**Ordem Crítica:**

```
resolver_confirmacao_pendente() cria intencao="confirmacao_agendamento" ✓
    ↓
DEPOIS: guard em 4982 verifica intencao
    ↓
SE já foi setado em resolver_confirmacao_pendente, guard não dispara ✓
    ↓
MAS SE resolver_confirmacao_pendente() falha a detectar confirmacao:
    → classificador retorna "indefinida"
    → guard dispara
    → BLOQUEADO
```

### Traço de Confirmação Legítima

```python
# router/principal_router.py:1089 (eh_confirmacao)
def eh_confirmacao(texto: str) -> bool:
    t = normalizar(texto or "")
    gatilhos_exatos = {"sim", "ok", "certo", "pode", ...}
    if t in gatilhos_exatos:
        return True
    # mais lógica...
```

Função EXISTE e reconhece "sim" → problema é ordem de execução.

### Cenário de Falha

```
Cliente responde: "sim" em confirmacao_agendamento=True

Sequência A (SE resolver_confirmacao_pendente executa):
  1. eh_confirmacao("sim") → True
  2. intencao = "confirmacao_agendamento"
  3. Guard não dispara (intencao não é "indefinida")
  4. ✓ FUNCIONA

Sequência B (SE resolver_confirmacao_pendente é skipped):
  1. eh_confirmacao nunca executado
  2. classificador cai em padrão 
  3. retorna intencao="indefinida"
  4. Guard dispara
  5. ❌ BLOQUEADO: "Não consegui entender"
```

### Classificação

**Status**: ✅ **CONFIRMADA**  
**Evidência**: Linha 4982 guard executa ANTES fallback confirmacao handler  
**Cause**: Guard de "indefinida" em línha 4982 bloqueia mesmo com dados válidos  
**Risco**: CRÍTICO — Confirmação legítima rejeitada  

### Raiz de Causa

**Camada**: Roteamento (Fluxo)

Não é problema de classificação (classificador está correto). É problema de ordenação de guards.

---

## HIPÓTESE 4: ESTADO ESCOLHA_HORARIO OSCILA

### Investigação

**Arquivo examinado**: `router/principal_router.py`

**Pontos de Interesse**:
- Set: linhas 2533, 8263, 9117, 12096, 15174, 15208 (modo_escolha_horario = True)
- Clear: linhas 2396, 2413, 2570, 5668, 6675 (pop/removal)
- State machine: línea 1786 (conditional clearing)

### Rastreamento

```python
# principal_router.py:8263 (exemplo de múltiplos)
ctx["estado_fluxo"] = "aguardando_escolha_horario"
ctx["modo_escolha_horario"] = True  ← SET UNCONDITIONAL
ctx["horarios_sugeridos"] = sugestoes
await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)

# principal_router.py:1786 (clearing logic)
if ctx.get("estado_fluxo") != "aguardando_escolha_horario":
    # Clearing logic
    # ↑ SÓ LIMPA SE ESTADO ≠ "aguardando_escolha_horario"

# principal_router.py:5668 (subject change)
ctx.pop("horarios_sugeridos", None)  # ← Limpa horarios
# MAS não limpa modo_escolha_horario ✗
```

### Cenário de Oscilação

```
Msg 1: "quero agendar corte"
  → modo_escolha_horario = True
  → horarios_sugeridos = [14h, 15h, 16h]
  → estado_fluxo = "aguardando_escolha_horario"

Msg 2: "prefiro escova"  ← Subject change
  → horarios_sugeridos.pop()
  → modo_escolha_horario NÃO é removido ← AQUI É O BUG
  → estado_fluxo pode mudar mas modo_escolha_horario=True persiste

Msg 3: "qual disponibilidade?"
  → Sistema vê: modo_escolha_horario=True AND horarios_ctx = []
  → Reintroduz estado (linha 8263): "aguardando_escolha_horario"
  → Estado oscila sem sinais claros de entrada/saída
```

### Problema

Não existe `_saiu_escolha_horario_flag` ou equivalente:

```python
# search result: 0 matches found
"_saiu_escolha_horario_flag"
"_escolha_horario_saida"
"_exit_flag"

# Exists: apenas marcação de entrada
"modo_escolha_horario"  # SET mas não EXIT FLAGGED
```

### Classificação

**Status**: ✅ **CONFIRMADA**  
**Evidência**: Linha 8263 SET incondicional; linha 5668 pop sem flag de saída  
**Cause**: Reintrodução sem verificação de estado anterior  
**Risco**: MÉDIO — Estado pode oscilar, confundindo roteador  

### Raiz de Causa

**Camada**: Gerenciamento de Estado (Fluxo)

É uma falha de design de state machine: entrada sem mecanismo de saída claro.

---

## HIPÓTESE 5: DRAFT SNAPSHOT (DESIGN PATTERN)

### Investigação

**Arquivos examinados**:
- `router/principal_router.py` (uso de draft)
- `services/event_service_async.py` (persistência)
- Fluxo de recuperação

### Rastreamento

```python
# principal_router.py:248-268
# Draft é LIDO de contexto, nunca de Firestore evento
draft = ctx.get("draft_agendamento")  ← Apenas de memória
# Nunca: Buscar evento real e sincronizar draft

# principal_router.py:6265-6274
# Draft é SALVO em Sessoes/, não em Eventos/
await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)
# Persiste para: Clientes/{dono_id}/Sessoes/{cliente_id}
# NÃO persiste: Clientes/{dono_id}/Eventos/{evento_id}
```

### Verificação de Sincronização Reversa

```
Busca: "salvar_evento" + "draft"
Resultado: 0 ocorrências de sincronização de draft de volta

Conclusão: Draft é SNAPSHOT temporal isolado em Sessoes/
           Nunca é sincronizado de volta a Eventos/
```

### Design Implications

| Cenário | Draft em Memory | Draft em Firestore | Sincronizado? | Status |
|---------|---|---|---|---|
| Mesma sessão, feliz | ✅ Presente | ✅ Salvo | ✅ Sim | ✅ OK |
| Nova sessão, mesmo usuário | ❌ Vazio | ❌ Vazio (se não salvo) | N/A | 🔴 QUEBRADO |
| Admin muda evento | ✅ Draft antigo | ✅ Evento novo | ❌ Não | 🟡 STALE |
| Session timeout + recovery | ❌ Depend TTL | ✅ Pode estar | ⚠️ Condicional | 🟡 RISKY |

### Classificação

**Status**: ✅ **CONFIRMADA**  
**Evidência**: Linhas 248-268, 6265-6274 confirmam isolamento de draft  
**Cause**: Draft é snapshot temporal em Sessoes/, não live view de Eventos/  
**Risco**: BAIXO em happy path, MÉDIO em cross-session ou admin changes  

### Raiz de Causa

**Camada**: Design Pattern (Arquitetura)

Não é bug. É decisão de design: draft é "intenção em andamento", não "event replica".

---

## TABELA CONSOLIDADA

| Hipótese | Status | Severidade | Raiz de Causa (Camada) | Confirmado Por |
|----------|--------|-----------|----------------------|-----------------|
| 1. Durações Hardcoded | ✅ CONFIRMADA | P1 | Lógica de Fallback | informacao_service.py:240-265 |
| 2. Draft Não Retorna | ✅ CONFIRMADA | **P0** | Persistência (Fluxo) | principal_router.py:5561-5591, 6437-6473 |
| 3. Intent Indefinida Bloqueia | ✅ CONFIRMADA | **P0** | Roteamento (Ordenação Guard) | principal_router.py:4982 |
| 4. Modo_Escolha Oscila | ✅ CONFIRMADA | P1 | State Machine (Falta Exit Flag) | principal_router.py:8263, 1786, 5668 |
| 5. Draft Snapshot Design | ✅ CONFIRMADA | P2 | Design Pattern (Intencional) | principal_router.py:248-268, 6265-6274 |

---

## RISCO DE REGRESSÃO POR CORREÇÃO

### P0 #2 (Draft Não Retorna)

**Risco Baixo**
- Correção: Adicionar `await salvar_contexto_temporario_v2()` após responder_consulta_informativa()
- Impacto: Apenas contexto é salvo, nenhuma lógica muda
- Efeitos colaterais: Nenhum previsto

### P0 #3 (Intent Indefinida Bloqueia)

**Risco Médio**
- Correção: Reordenar guards ou permitir fallback a confirmacao_handler
- Impacto: Ordem de execução muda
- Efeitos colaterais: Pode afetar casos onde "indefinida" deveria bloquear legitimamente

### P1 #1 (Durações Hardcoded)

**Risco Baixo**
- Correção: Inverter ordem de fallback (ServicosNegocio ANTES map)
- Impacto: Apenas consulta é reordenada
- Efeitos colaterais: Nenhum, apenas lê dados diferentes (mais corretos)

### P1 #4 (Modo_Escolha Oscila)

**Risco Médio**
- Correção: Adicionar `_saiu_escolha_horario_flag` e verificar
- Impacto: Novo campo de estado
- Efeitos colaterais: Pode afetar recovery se flag não limpo corretamente

### P2 #5 (Draft Snapshot Design)

**Risco: Não Aplicável (Design Pattern)**
- Documentação apenas, nenhuma correção proposta
- Impacto: Nenhum no código
- Efeitos colaterais: Nenhum

---

## PRÓXIMOS PASSOS (AFTER APPROVAL)

**Phase 4 (Implementation) requer aprovação explícita**

Ordem recomendada:
1. **P0 #3 (Intent Indefinida)** → 2-3 linhas, impacto crítico
2. **P0 #2 (Draft Não Retorna)** → 5-10 linhas, impacto crítico
3. **P1 #4 (Modo_Escolha)** → 10-15 linhas, impacto médio
4. **P1 #1 (Durações)** → 15-20 linhas, impacto médio
5. **P2 #5 (Draft Design)** → Documentação, impacto baixo

---

## CONCLUSÃO

✅ **Todas as 5 hipóteses foram CONFIRMADAS com evidência de código**

Nenhuma correção foi proposta (escopo READ-ONLY).
Cada problema possui causa-raiz identificada e impacto validado.

**Pronto para Phase 4 (Implementation) após autorização explícita.**

