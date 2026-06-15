# 🔐 POLÍTICA DE CODE REVIEW — ClienteProfile

**Data:** 2026-06-14  
**Status:** ✅ ATIVA  
**Escopo:** OBRIGATÓRIA para todos os PRs envolvendo ClienteProfile  
**Validade:** Permanente  

---

## 📌 CLIENTEPROFILE SAFETY RULE

```
Hierarquia Inviolável:

Mensagem atual > Histórico > Defaults

ClienteProfile INFLUENCIA.
ClienteProfile NÃO DECIDE.
```

---

## 🎯 Objetivo

Garantir que nenhuma funcionalidade futura baseada em ClienteProfile viole a regra central:

> **"ClienteProfile influencia sugestões, mas nunca decide criação de evento."**

---

## 🚫 PRs Que Devem Ser BLOQUEADOS

Qualquer PR que implemente:

- ❌ Criar evento usando ClienteProfile
- ❌ Confirmar evento usando ClienteProfile
- ❌ Sobrescrever escolha explícita do cliente com histórico
- ❌ Ignorar conflito baseado em histórico
- ❌ Ignorar disponibilidade baseado em histórico
- ❌ Auto-agendar recorrência sem autorização explícita
- ❌ Pular confirmação baseado em histórico
- ❌ GPT tomar decisão usando profile

**Ação:** REJECT + Cite SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md

---

## ✅ PRs Que São PERMITIDOS

PRs podem ser aprovados se implementarem:

- ✅ Sugestão baseada em ClienteProfile (requer confirmação)
- ✅ Preenchimento de draft com valores do perfil (cliente pode alterar)
- ✅ Personalização de linguagem baseada em histórico
- ✅ Contexto informado ao motor determinístico
- ✅ Redução de perguntas se dados disponíveis

**Condição:** Todos os itens do checklist abaixo devem estar marcados

---

## 📋 CHECKLIST OBRIGATÓRIO

**TODO PR relacionado a ClienteProfile DEVE incluir:**

```
CLIENTEPROFILE SAFETY VALIDATION

[ ] Li e entendi SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md
[ ] Pedido explícito do cliente continua vencendo histórico
[ ] Nenhum evento é criado automaticamente
[ ] Nenhuma confirmação é pulada
[ ] Nenhum conflito é ignorado
[ ] Nenhuma disponibilidade é ignorada
[ ] Histórico apenas influencia sugestões, não decide
[ ] Sugestões exigem confirmação explícita do cliente
[ ] Fluxo obrigatório continua: serviço → duração → disponibilidade → conflito → sugestão → confirmação → criação
[ ] GPT não toma decisões usando profile
[ ] Nenhum teste de "sugestão automática" foi adicionado

Assinado: _____________  Data: _______
```

---

## 🎯 Triggers para Code Review Obrigatória

PR DEVE passar por revisor especializado em ClienteProfile se contiver:

### 1. Leitura de ClienteProfile

```python
from services.clienteprofile_service import obter_profile
```

**Validação:** Verificar que dados são APENAS CONSULTADOS, não USADOS para decidir

### 2. Consulta de profissional_mais_frequente

```python
profile.get("tendencias", {}).get("profissional_mais_frequente")
```

**Validação:** Verificar que é SUGESTÃO, não DECISÃO

### 3. Consulta de servico_mais_frequente

```python
profile.get("tendencias", {}).get("servico_mais_frequente")
```

**Validação:** Verificar que é SUGESTÃO, não DECISÃO

### 4. Leitura de histórico do cliente

```python
profile.get("historico", {})
```

**Validação:** Verificar que dados são CONTEXTO, não AUTORIDADE

### 5. Uso de preferências ou perfil comportamental

```python
profile.get("preferencias")
profile.get("comportamento")
```

**Validação:** Verificar que influencia fluxo, não pula passos

---

## 📝 Critério de Aprovação

**APROVAR se:**

✅ Checklist está 100% marcado  
✅ Nenhum passo obrigatório é pulado  
✅ Dados do profile são apenas consultados (não decisivos)  
✅ Sugestões exigem confirmação explícita  
✅ Testes validam que profile NÃO cria evento automaticamente  
✅ Testes validam que cliente pode rejeitar sugestão  
✅ Testes validam que dado atual sobrescreve histórico  

**REJEITAR se:**

❌ Checklist está incompleto  
❌ Qualquer passo obrigatório é pulado  
❌ Evento pode ser criado sem confirmação  
❌ Histórico sobrescreve pedido explícito  
❌ Conflito é ignorado baseado em histórico  
❌ Disponibilidade é ignorada baseado em histórico  
❌ Sugestão é convertida em decisão  
❌ Auto-agendamento por recorrência aprendida  

---

## 🔍 Exemplos de Validação

### ✅ APROVADO: Sugestão com Confirmação

```python
# PR: P1.2 - Histórico Inteligente

# Código que sugerição, mas não decide
profile = await obter_profile(tenant_id, cliente_id)
if profile and profile.get("tendencias", {}).get("profissional_mais_frequente"):
    sugestao = profile["tendencias"]["profissional_mais_frequente"]
    # ✅ Pergunta, não agenda
    resposta = await pedir_confirmacao(f"Quer com {sugestao}?")
    if resposta == "sim":
        usar = sugestao
    else:
        # ✅ Respeitou recusa
        usar = None
```

**Checklist:** ✅ TODOS os itens marcados  
**Testes:** ✅ 5+ testes validando recusa e aceitação  
**Resultado:** APROVADO

---

### ❌ REJEITADO: Auto-agendamento

```python
# PR: P1.3 - Preferências (ERRADO)

profile = await obter_profile(tenant_id, cliente_id)
if profile and profile.get("tendencias", {}).get("profissional_mais_frequente"):
    # ❌ Cria evento automaticamente usando histórico
    criar_evento(
        profissional=profile["tendencias"]["profissional_mais_frequente"],
        cliente_id=cliente_id
    )
```

**Problema:** ❌ Evento criado SEM confirmação  
**Checklist:** ❌ "Nenhum evento é criado automaticamente" = NÃO marcado  
**Resultado:** REJEITADO + Cite SPEC_SEGURANCA

---

### ❌ REJEITADO: Sobrescrever Escolha

```python
# PR: P1.2 - Histórico (ERRADO)

cliente_escolheu = "com Bruna"
profile = await obter_profile(tenant_id, cliente_id)
if profile and profile.get("tendencias", {}).get("profissional_mais_frequente"):
    # ❌ Sobrescreve escolha explícita
    usar = profile["tendencias"]["profissional_mais_frequente"]
```

**Problema:** ❌ Histórico sobrescreve pedido  
**Checklist:** ❌ "Pedido explícito continua vencendo" = NÃO marcado  
**Resultado:** REJEITADO + Cite SPEC_SEGURANCA

---

## 🛡️ Proteções Implementadas

### 1. Checklist Obrigatório

Revisor não pode aprovar sem todos os itens marcados.

### 2. Referência Obrigatória à SPEC_SEGURANCA

Todo PR deve citar:  
`SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md`

### 3. Teste Obrigatório

Cada PR deve incluir teste que valida:
- ✅ Sugestão é oferecida e confirmação é solicitada
- ✅ Cliente pode recusar sugestão
- ✅ Recusa limpa draft/estado
- ✅ Histórico não sobrescreve escolha atual

### 4. Revisor Especializado

PRs envolvendo ClienteProfile devem ser aprovadas por:
- Alguém que leu SPEC_SEGURANCA
- Alguém que entende a hierarquia (atual > histórico > defaults)

---

## 📊 Fluxo de Code Review

```
PR submetido
    ↓
Checklist preenchido? → NÃO → REJECT
    ↓ SIM
Referencia SPEC_SEGURANCA? → NÃO → REJECT
    ↓ SIM
Lê ClienteProfile? → SIM → Atribuir a revisor especializado
                  → NÃO → Revisor padrão OK
    ↓
Revisor verifica:
├─ Nenhum evento criado automaticamente
├─ Nenhuma confirmação pulada
├─ Nenhum conflito ignorado
├─ Nenhuma disponibilidade ignorada
├─ Cliente pode rejeitar sugestão
├─ Histórico apenas influencia
└─ Testes cobrem segurança
    ↓
Tudo OK? → SIM → APPROVE
        → NÃO → REJECT + feedback específico
```

---

## 📌 Referência Rápida para Revisores

**Sempre pergunte:**

1. "Este PR cria um evento sem confirmação?" → ❌ Rejeitar
2. "Este PR pula um passo do fluxo obrigatório?" → ❌ Rejeitar
3. "Este PR pode sobrescrever escolha do cliente?" → ❌ Rejeitar
4. "Este PR ignora conflito baseado em histórico?" → ❌ Rejeitar
5. "Este PR ignora disponibilidade baseado em histórico?" → ❌ Rejeitar
6. "Este PR trata sugestão como decisão?" → ❌ Rejeitar
7. "Este PR exige confirmação antes de usar histórico?" → ✅ Continuar

---

## 🔐 Governança

**Política:** OBRIGATÓRIA  
**Aplicável a:** Todos os PRs com ClienteProfile  
**Revisores:** Mínimo 1 especializado em SPEC_SEGURANCA  
**Duração:** Permanente (até supersedida)  
**Violação:** PR é REJEITADO, não pode ser mergeado  

---

**Política criada:** 2026-06-14  
**Status:** ✅ ATIVA  
**Validade:** Permanente  
