# LOTE-4: VALIDAÇÃO DE ESCOPO

**Data:** 2026-06-21  
**Status:** 🔍 INVESTIGAÇÃO COMPLETA  
**Arquivo:** services/onboarding_service.py  
**Ocorrências Reportadas:** 2  

---

## 🚨 CONCLUSÃO IMEDIATA

**RECOMENDAÇÃO:** ✅ **LOTE-4 APROVADO PARA MIGRAÇÃO**

Ambas as ocorrências são **REAIS**, não falsos positivos, e **precisam de migração urgente**.

---

## 📋 ANÁLISE DETALHADA DAS 2 OCORRÊNCIAS

### Ocorrência #1: onboarding_service.py:88

**Status:** ❌ SEM tenant_id — NECESSITA MIGRAÇÃO

**Função Contendo:** `processar_onboarding_endereco_dono(user_id, dono_id, texto_usuario, ctx, context)`  
**Função Definida:** Linha 16  
**Linha da Chamada:** 88  
**Tipo:** ESCRITA (salvar_contexto_temporario)  

**Código Atual (Linhas 84-88):**
```python
# Limpar estado — volta ao fluxo normal (agendamento)
ctx.pop("estado_fluxo", None)
ctx.pop("aguardando_endereco_negocio", None)
ctx["estado_fluxo"] = "agendando"  # Retorna ao estado normal
await salvar_contexto_temporario(user_id, ctx)
```

**Contexto Completo (Linhas 67-95):**
```python
# Temos rua e número, salvar em Firestore
endereco = {
    "rua": endereco_parsed["rua"],
    "numero": endereco_parsed["numero"],
    "completo": endereco_parsed["completo"]
}

sucesso = await salvar_endereco_negocio(dono_id, endereco)

if not sucesso:
    resposta = "Erro ao salvar endereço. Tente novamente."
    return {
        "handled": True,
        "acao": "send_stop",
        "resposta": resposta
    }

# Limpar estado — volta ao fluxo normal (agendamento)
ctx.pop("estado_fluxo", None)
ctx.pop("aguardando_endereco_negocio", None)
ctx["estado_fluxo"] = "agendando"  # Retorna ao estado normal
await salvar_contexto_temporario(user_id, ctx)  # ← LINHA 88: FALTA tenant_id

resposta = f"Perfeito. Endereço salvo: {endereco['completo']}."
return {
    "handled": True,
    "acao": "send_stop",
    "resposta": resposta
}
```

**Fluxo de Entrada:**
1. Dono respondeu à pergunta de endereço
2. Sistema extraiu rua e número
3. Sistema salvou endereço em Firestore (`salvar_endereco_negocio`)
4. Sistema limpa estado de "aguardando_endereco" e volta a "agendando"
5. Sistema salva contexto temporário (linha 88)

**Fluxo de Saída:**
- Próxima mensagem carrega este contexto
- Sistema sabe que já perguntou endereço
- Continua fluxo normal de agendamento

**Tipo de Dado Persistido:**
- estado_fluxo = "agendando" (retorna ao fluxo normal)
- Limpeza de flags temporárias (aguardando_endereco_negocio)
- Impacto: SESSÃO (estado conversacional temporário)

**Rastreamento de tenant_id:**

✅ **Existe no escopo?** SIM
- Parâmetro: `dono_id: str` (linha 18)
- Função recebe `dono_id` explicitamente
- Sem callbacks, sem async yield

✅ **Vem de qual origem?**
- Direto: `dono_id` é parâmetro da função
- Tipo: Resolvido pelo chamador (router/identidade)
- Garantia: Sempre presente (parâmetro obrigatório)

**Path Utilizado:**
- Legado: Clientes/{user_id}/MemoriaTemporaria/contexto
- v2: Clientes/{dono_id}/Sessoes/{actor_id}
- Atualmente: **LEGADO** (sem tenant_id)

**Classificação:** ✅ **APROVADA PARA MIGRAÇÃO**

**Patch Mínimo:**
```python
await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)
```

---

### Ocorrência #2: onboarding_service.py:100

**Status:** ❌ SEM tenant_id — NECESSITA MIGRAÇÃO

**Função Contendo:** `processar_onboarding_endereco_dono(user_id, dono_id, texto_usuario, ctx, context)`  
**Função Definida:** Linha 16  
**Linha da Chamada:** 100  
**Tipo:** ESCRITA (salvar_contexto_temporario)  

**Código Atual (Linhas 97-100):**
```python
# Primeira vez: não tem endereço, não perguntamos ainda → perguntar agora
ctx["estado_fluxo"] = "aguardando_endereco_negocio"
ctx["aguardando_endereco_negocio"] = True
await salvar_contexto_temporario(user_id, ctx)
```

**Contexto Completo (Linhas 97-107):**
```python
# Primeira vez: não tem endereço, não perguntamos ainda → perguntar agora
ctx["estado_fluxo"] = "aguardando_endereco_negocio"
ctx["aguardando_endereco_negocio"] = True
await salvar_contexto_temporario(user_id, ctx)  # ← LINHA 100: FALTA tenant_id

resposta = "Qual é o endereço do negócio? Pode me mandar rua e número."
return {
    "handled": True,
    "acao": "send_stop",
    "resposta": resposta
}
```

**Fluxo de Entrada:**
1. Dono no primeiro acesso, sem endereço salvo ainda
2. Sistema detecta: não tem endereço em Firestore (linha 37)
3. Sistema detecta: não está aguardando resposta ainda (linha 44 é falso)
4. Sistema define estado temporário: aguardando_endereco_negocio
5. Sistema salva contexto temporário (linha 100)

**Fluxo de Saída:**
- Próxima mensagem carrega este contexto
- Sistema sabe que está aguardando endereço
- Próxima mensagem entra no branch de linha 44 (estado == "aguardando_endereco_negocio")

**Tipo de Dado Persistido:**
- estado_fluxo = "aguardando_endereco_negocio" (conversacional)
- aguardando_endereco_negocio = True (flag temporária)
- Impacto: SESSÃO (estado conversacional temporário)

**Rastreamento de tenant_id:**

✅ **Existe no escopo?** SIM
- Parâmetro: `dono_id: str` (linha 18)
- Função recebe `dono_id` explicitamente
- Sem callbacks, sem async yield

✅ **Vem de qual origem?**
- Direto: `dono_id` é parâmetro da função
- Tipo: Resolvido pelo chamador (router/identidade)
- Garantia: Sempre presente (parâmetro obrigatório)

**Path Utilizado:**
- Legado: Clientes/{user_id}/MemoriaTemporaria/contexto
- v2: Clientes/{dono_id}/Sessoes/{actor_id}
- Atualmente: **LEGADO** (sem tenant_id)

**Classificação:** ✅ **APROVADA PARA MIGRAÇÃO**

**Patch Mínimo:**
```python
await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)
```

---

## 📊 MATRIZ CONSOLIDADA

| # | Arquivo | Linha | Função | tenant_id Origem | Risco | Status | Ação |
|---|---------|-------|--------|------------------|-------|--------|------|
| 1 | onboarding_service.py | 88 | processar_onboarding_endereco_dono | dono_id (param) | 🟠 ALTO | ❌ SEM tenant_id | ✅ MIGRAR |
| 2 | onboarding_service.py | 100 | processar_onboarding_endereco_dono | dono_id (param) | 🟠 ALTO | ❌ SEM tenant_id | ✅ MIGRAR |

---

## 🔍 RASTREABILIDADE VALIDADA

### Ocorrência #1: Linha 88

**Função:** `processar_onboarding_endereco_dono()`
```
Assinatura (linhas 16-22):
  async def processar_onboarding_endereco_dono(
      user_id: str,
      dono_id: str,  ← PARÂMETRO OBRIGATÓRIO
      texto_usuario: str,
      ctx: dict,
      context
  ):

Origem de dono_id:
  └─ Parâmetro recebido pelo chamador
  └─ Garantidamente presente (erro se None)
  └─ Sem callbacks

Uso (linhas 84-88):
  └─ Chamada salvar_contexto_temporario(user_id, ctx)
  └─ Patch: adicionar tenant_id=dono_id
```

---

### Ocorrência #2: Linha 100

**Função:** `processar_onboarding_endereco_dono()`
```
Assinatura (linhas 16-22):
  async def processar_onboarding_endereco_dono(
      user_id: str,
      dono_id: str,  ← PARÂMETRO OBRIGATÓRIO
      texto_usuario: str,
      ctx: dict,
      context
  ):

Origem de dono_id:
  └─ Parâmetro recebido pelo chamador
  └─ Garantidamente presente (erro se None)
  └─ Sem callbacks

Uso (linhas 97-100):
  └─ Chamada salvar_contexto_temporario(user_id, ctx)
  └─ Patch: adicionar tenant_id=dono_id
```

---

## 🎯 ANÁLISE DE IMPACTO

### Sessão vs Dado Permanente

**Classificação:** SESSÃO (estado conversacional)

```
Dados Persistidos:
  - estado_fluxo = "aguardando_endereco_negocio" | "agendando"
  - aguardando_endereco_negocio = True (flag)

Característica:
  - Tempor ário (limpo ao fim da sessão)
  - Conversacional (guia diálogo)
  - NÃO catálogo, NÃO configuração permanente

Confirmação:
  - Linha 3-4 comentário: "Sem salvar catálogo/agenda na sessão"
  - Dados permanentes em: Clientes/{tenant_id}/Configuracao/dados_negocio
  - Dados sessionais em: Clientes/{dono_id}/Sessoes/{actor_id}
```

**Validação Arquitetural:** ✅ CORRETA
- Não salva catálogo em sessão
- Não salva serviços em sessão
- Salva apenas estado conversacional

---

### Impacto em P0 Agendamento

**Análise de Riscos:**

- ✅ **Agendamento** — Não afetado
  - Linha 100: aguardando_endereco_negocio NÃO interfere com agendamento
  - Linha 88: retorna para "agendando" (estado normal)
  - Sem impacto na lógica de agenda

- ✅ **Confirmação Pendente** — Não afetado
  - Contexto de onboarding é separado
  - Flags de confirmação pendente em contexto diferente

- ✅ **Notificações** — Não afetado
  - Notificações usam evento, não contexto temporário
  - Sem dependência

- ✅ **Cancelamento** — Não afetado
  - Cancelamento usa evento, não contexto
  - Sem impacto

- ✅ **Contexto Geral** — Impactado POSITIVAMENTE
  - Isolamento multi-tenant garantido
  - Previne contaminação entre tenants

---

### Impacto em Fluxo de Onboarding

**Primer Acesso:**
```
1. Dono acessa pela primeira vez
2. Sistema: "Qual é o endereço do negócio?"
3. Contexto salvo COM tenant_id (depois da migração)
   └─ Path: Clientes/{dono_id}/Sessoes/{actor_id}
   └─ Dados: {"estado_fluxo": "aguardando_endereco_negocio", ...}
4. Dono responde: "Rua João Baroni, 550"
5. Contexto atualizado COM tenant_id (depois da migração)
   └─ Path: Clientes/{dono_id}/Sessoes/{actor_id}
   └─ Dados: {"estado_fluxo": "agendando", ...}
6. Continua fluxo normal
```

**Impacto:** ZERO (apenas caminho muda, lógica idêntica)

---

## 📋 CHECKLIST CRITÉRIO DE ACEITE

**Todos os critérios ✅ ATENDIDOS:**

- [x] tenant_id explícito ou resolvido de forma segura
  - ✅ Ambas: `dono_id` é parâmetro obrigatório
  - ✅ Sem callbacks, sem resolução adicional necessária

- [x] não salva catálogo em sessão
  - ✅ Ocorrência 1: salva apenas estado_fluxo
  - ✅ Ocorrência 2: salva apenas estado_fluxo + flag temporária
  - ✅ Confirma comentário linha 3: "Sem salvar catálogo/agenda na sessão"

- [x] patch mínimo identificado
  - ✅ OC1: `await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)`
  - ✅ OC2: `await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)`

- [x] sem risco de quebrar P0
  - ✅ Nenhuma mudança em lógica de agenda
  - ✅ Nenhuma mudança em lógica de conflito
  - ✅ Nenhuma mudança em lógica de notificação
  - ✅ Apenas caminho de persistência (Firestore path)

---

## 🚀 RECOMENDAÇÃO FINAL

**Decisão:** ✅ **LOTE-4 APROVADO PARA MIGRAÇÃO**

### Motivos:

1. **Ambas as ocorrências faltam tenant_id**
   - Não são falsos positivos
   - São escritas legadas reais

2. **tenant_id é facilmente acessível**
   - Parâmetro da função
   - Sem callbacks ou resolução adicional

3. **Impacto é ISOLADO e SEGURO**
   - Apenas sessão conversacional
   - Não afeta catálogo ou configuração permanente
   - Não afeta P0 agendamento

4. **Patch é MÍNIMO**
   - Uma linha: adicionar `tenant_id=dono_id`
   - Nenhuma refatoração necessária
   - Nenhuma mudança lógica

5. **CRÍTICO: Risco de Contaminação Multi-tenant**
   - SEM tenant_id, contexto de dono A pode ser lido por dono B
   - Violação séria de isolamento
   - **Deve ser migrado URGENTEMENTE**

---

## 📊 ESTADO FINAL — FASE 2 TIER 2

| Lote | Status | Ocorrências | Ação |
|------|--------|-------------|------|
| LOTE-1 | ✅ COMPLETO | 2/2 | Commitado |
| LOTE-2 | ✅ COMPLETO | 2/2 | Commitado |
| LOTE-3 | ❌ FALSO POSITIVO | 0/2 | Cancelado |
| LOTE-4 | ✅ APROVADO | 2/2 | **MIGRAR URGENTEMENTE** |

**Fase 2 Completo:** 6/8 após LOTE-4 (75%)  
**Status Crítico:** LOTE-4 deve ser executado IMEDIATAMENTE

---

**Validação Completada:** 2026-06-21  
**Status:** ✅ LOTE-4 APROVADO PARA MIGRAÇÃO IMEDIATA  
**Urgência:** 🔴 CRÍTICA (risco multi-tenant)
