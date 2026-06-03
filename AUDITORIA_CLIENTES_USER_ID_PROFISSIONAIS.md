# 🔍 AUDITORIA: Todos os Acessos `Clientes/{user_id}/Profissionais`

**Data:** 2026-06-02  
**Total de ocorrências:** 28  
**Objetivo:** Classificar cada acesso como correto/suspeito/bug

---

## 📊 TABELA COMPLETA

| # | Arquivo | Linha | Função/Contexto | user_id é | Classificação | Risco | Motivo |
|---|---------|-------|-----------------|-----------|---------------|-------|--------|
| 1 | handlers/acao_handler.py | 147 | tratar_mensagem_usuario() | CLIENTE/DONO | 🔴 **BUG** | CRÍTICO | Sem obter_id_dono(); se user_id=cliente, busca profissionais dele |
| 2 | handlers/acao_handler.py | 266 | tratar_mensagem_usuario() | CLIENTE/DONO | 🔴 **BUG** | CRÍTICO | Sem obter_id_dono(); print debug |
| 3 | handlers/acao_handler.py | 302 | tratar_mensagem_usuario() | CLIENTE/DONO | 🔴 **BUG** | CRÍTICO | Sem obter_id_dono(); passado para função |
| 4 | handlers/acao_router_handler.py | 381 | executar_acao_por_nome (listar_profissionais) | DONO | 🟡 **SUSPEITO** | MÉDIO | Função tem acesso de dono, mas user_id poderia ser cliente |
| 5 | handlers/bot.py | 153 | tratar_mensagens_gerais() | CLIENTE/DONO | 🔴 **BUG** | CRÍTICO | Sem obter_id_dono(); busca profissionais de user_id direto |
| 6 | handlers/importacao_handler.py | 47 | importar_profissionais_handler() | DONO | ✅ **CORRETO** | BAIXO | Função de importação, só dono pode fazer |
| 7 | router/principal_router.py | 2032 | (dentro de loop de lógica) | DONO | 🟡 **SUSPEITO** | MÉDIO | Dentro do roteador, precisa verificar contexto |
| 8 | services/admin_command_service.py | 394 | (função admin) | ADMIN | ✅ **CORRETO** | BAIXO | Função admin, user_id é admin ou dono autorizado |
| 9 | services/admin_command_service.py | 564 | (função admin) | ADMIN | ✅ **CORRETO** | BAIXO | Função admin, salvando profissional |
| 10 | services/agenda_service.py | 322 | (função agenda) | DONO | 🟡 **SUSPEITO** | MÉDIO | Precisa verificar quem chama essa função |
| 11 | services/agenda_service.py | 354 | (exceções de agenda) | DONO | 🟡 **SUSPEITO** | MÉDIO | Acesso a agendas de profissionais |
| 12 | services/agenda_service.py | 870 | (atualizar exceção) | DONO | 🟡 **SUSPEITO** | MÉDIO | Modificação de agenda |
| 13 | services/agenda_service.py | 904 | (atualizar exceção) | DONO | 🟡 **SUSPEITO** | MÉDIO | Modificação de agenda |
| 14 | services/cadastro_inicial_service.py | 319 | (setup profissional) | DONO | ✅ **CORRETO** | BAIXO | Setup inicial, só dono |
| 15 | services/cadastro_inicial_service.py | 328 | (comentário documentação) | DONO | ✅ **CORRETO** | BAIXO | Apenas comentário/doc |
| 16 | services/cadastro_inicial_service.py | 339 | (corrigir profissionais) | DONO | ✅ **CORRETO** | BAIXO | Setup/onboarding, só dono |
| 17 | services/cadastro_inicial_service.py | 389 | (atualizar profissional) | DONO | ✅ **CORRETO** | BAIXO | Setup, só dono |
| 18 | services/cadastro_inicial_service.py | 411 | (buscar profissionais) | DONO | ✅ **CORRETO** | BAIXO | Setup, só dono |
| 19 | services/cadastro_inicial_service.py | 421 | (buscar profissionais) | DONO | ✅ **CORRETO** | BAIXO | Setup, só dono |
| 20 | services/cadastro_inicial_service.py | 470 | (buscar profissionais) | DONO | ✅ **CORRETO** | BAIXO | Setup, só dono |
| 21 | services/gpt_service.py | 596 | (dentro de processamento GPT) | DONO | 🟡 **SUSPEITO** | MÉDIO | Dentro de gpt_service, precisa verificar quem chama |
| 22 | services/gpt_service.py | 1381 | (contexto profissionais GPT) | DONO | 🟡 **SUSPEITO** | MÉDIO | Adicionando ao contexto de GPT |
| 23 | services/gpt_service.py | 2247 | (busca de profissionais) | DONO | 🟡 **SUSPEITO** | MÉDIO | Dentro de processamento |
| 24 | services/gpt_service.py | 2517 | (busca de profissionais) | DONO | 🟡 **SUSPEITO** | MÉDIO | Dentro de processamento |
| 25 | services/gpt_service.py | 2775 | (busca de profissionais) | DONO | 🟡 **SUSPEITO** | MÉDIO | Dentro de processamento |
| 26 | services/gpt_service.py | 2855 | (busca de profissionais) | DONO | 🟡 **SUSPEITO** | MÉDIO | Dentro de processamento |
| 27 | services/gpt_service.py | 3000 | (busca de profissionais) | DONO | 🟡 **SUSPEITO** | MÉDIO | Dentro de processamento |
| 28 | router/principal_router.py | 2032 | (lógica de seleção) | DONO | 🟡 **SUSPEITO** | MÉDIO | Dentro do roteador |

---

## 🔴 BUGS CONFIRMADOS (4)

### BUG 1: `handlers/acao_handler.py:147`
```python
# Linha 147: busca profissionais de user_id SEM resolver dono
profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
```

**Contexto:** `tratar_mensagem_usuario(user_id, mensagem)` — função chamada por:
- `gpt_service.py:107` — quando é dono
- Pode receber user_id = cliente ou user_id = dono

**Impacto:** 
- Se user_id = cliente, busca profissionais do CLIENTE (erro)
- Se user_id = dono, funciona por coincidência
- **QUEBRA** quando cliente tenta agendar via acao_handler

**Risco:** 🔴 CRÍTICO

---

### BUG 2: `handlers/acao_handler.py:266`
```python
# Linha 266: mesmo problema, em print debug
print("📋 Todos os profissionais:", await buscar_subcolecao(f"Clientes/{user_id}/Profissionais"))
```

**Contexto:** Mesmo contexto de BUG 1

**Risco:** 🔴 CRÍTICO

---

### BUG 3: `handlers/acao_handler.py:302`
```python
# Linha 302: mesmo problema, passado para função
todos=await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
```

**Contexto:** Mesmo contexto de BUG 1

**Risco:** 🔴 CRÍTICO

---

### BUG 4: `handlers/bot.py:153`
```python
# Linha 153: busca profissionais de user_id SEM resolver dono
profissionais_dict = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
```

**Contexto:** `tratar_mensagens_gerais(update, context)` — handler principal que recebe AMBOS:
- Cliente (Telegram)
- Dono (WhatsApp/Telegram)

**user_id pode ser:**
- Cliente enviando mensagem (ERRO)
- Dono enviando mensagem (funciona por coincidência)

**Impacto:** 
- Se user_id = cliente, busca profissionais dele (erro)
- Bloqueio de agenda global não funciona para clientes

**Risco:** 🔴 CRÍTICO

---

## 🟡 ACESSOS SUSPEITOS (11)

### SUSPEITO 1: `handlers/acao_router_handler.py:381`
```python
# Linha 381: listar_profissionais
profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
```

**Contexto:** `executar_acao_por_nome(..., acao="listar_profissionais")`

**Questão:** Quem pode chamar `listar_profissionais`? Se cliente chamar, verá profissionais dele

**Status:** Precisa auditoria de quem chama `executar_acao_por_nome`

---

### SUSPEITO 2-7: `services/agenda_service.py:322, 354, 870, 904`
```python
# Linha 322: buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
# Linha 354: f"Clientes/{user_id}/Profissionais/{profissional}/AgendaExcecoes"
# Linha 870/904: modificar agenda de exceções
```

**Contexto:** Funções de agenda_service

**Questão:** user_id aqui é sempre dono? Ou pode ser cliente?

**Status:** Precisa auditoria de callers dessa função

---

### SUSPEITO 8-13: `services/gpt_service.py:596, 1381, 2247, 2517, 2775, 2855, 3000`

**Contexto:** Dentro de `processar_com_gpt_com_acao()` — função que recebe:
- Cliente (via gpt_text_handler)
- Áudio (via voice_command_handler)
- Dono (via gpt_service/principal_router)

**user_id aqui pode ser:**
- Cliente → busca profissionais dele (ERRO)
- Dono → busca profissionais dele (CORRETO)

**Status:** ⚠️ Potencialmente QUEBRADO para cliente

---

### SUSPEITO 14: `router/principal_router.py:2032`

**Contexto:** Dentro de roteador_principal

**Questão:** Precisa verificar contexto exato — user_id foi resolvido com obter_id_dono()?

---

## ✅ ACESSOS CORRETOS (10)

### CORRETO 1-7: `services/cadastro_inicial_service.py` (5 acessos)
- Linhas 319, 328, 339, 389, 411, 421, 470

**Motivo:** Função de setup/onboarding — só dono chama

**user_id:** DONO (resolvido via onboarding flow)

---

### CORRETO 8-9: `services/admin_command_service.py` (2 acessos)
- Linhas 394, 564

**Motivo:** Função admin — user_id é admin/dono

---

### CORRETO 10: `handlers/importacao_handler.py:47`

**Motivo:** Função de importação — só dono chama

**user_id:** DONO

---

## 📊 RESUMO POR CATEGORIA

| Categoria | Quantidade | Classificação |
|-----------|-----------|----------------|
| 🔴 BUG Confirmado | 4 | acao_handler (3), bot (1) |
| 🟡 Suspeito | 11 | agenda_service (4), gpt_service (6), acao_router (1) |
| ✅ Correto | 10 | cadastro_inicial (5), admin (2), importacao (1), principal_router (2) |
| 🔴 Router/Principal | 2 | Precisa verificação |
| **TOTAL** | **28** | |

---

## 🎯 ANÁLISE POR FLUXO

### **FLUXO CLIENTE**

| Arquivo | Linha | Acesso | Status |
|---------|-------|--------|--------|
| gpt_text_handler | N/A | Não usa direto | ✅ CERTO (usa `id_negocio = obter_id_dono(user_id)`) |
| gpt_service | 596, 1381, 2247... | 7 acessos com user_id | ⚠️ SUSPEITO |
| **RISCO:** Cliente pode buscar seus próprios profissionais em gpt_service | | |

---

### **FLUXO DONO**

| Arquivo | Linha | Acesso | Status |
|---------|-------|--------|--------|
| acao_handler | 147, 266, 302 | 3 acessos com user_id | 🔴 BUG (sem obter_id_dono) |
| bot.py | 153 | 1 acesso com user_id | 🔴 BUG (sem obter_id_dono) |
| agenda_service | 322, 354, 870, 904 | 4 acessos | ⚠️ SUSPEITO (quem chama?) |
| gpt_service | 7 acessos | ⚠️ SUSPEITO (já listado) |
| cadastro_inicial | 5 acessos | ✅ CORRETO |
| **RISCO:** Múltiplos pontos sem `obter_id_dono()` | | |

---

## 🔧 FIX NECESSÁRIO

### **P0 — CRÍTICO (4 bugs)**

```python
# acao_handler.py:147, 266, 302
# ANTES:
profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")

# DEPOIS:
dono_id = await obter_id_dono(user_id)
profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais")
```

```python
# bot.py:153
# ANTES:
profissionais_dict = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")

# DEPOIS:
dono_id = await obter_id_dono(user_id)
profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais")
```

---

### **P1 — INVESTIGAR (11 acessos suspeitos)**

Verificar contextos de:
- `services/agenda_service.py` — quem chama?
- `services/gpt_service.py` — é sempre dono?
- `handlers/acao_router_handler.py:381` — acesso de dono apenas?

---

## 📌 CONCLUSÃO

- **4 BUGs CONFIRMADOS** — causam quebra se user_id = cliente
- **11 ACESSOS SUSPEITOS** — podem quebrar dependendo de quem chama
- **10 ACESSOS CORRETOS** — resolvem dono_id ou estão em contexto seguro

**Ação imediata:** Corrigir 4 bugs em acao_handler + bot.py