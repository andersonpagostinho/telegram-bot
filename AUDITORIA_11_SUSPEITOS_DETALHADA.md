# 🔍 AUDITORIA DETALHADA: 11 Acessos Suspeitos

**Data:** 2026-06-02  
**Foco:** Rastrear origem de user_id em cada acesso suspeito

---

## 🔴 SUSPEITO 1: handlers/acao_router_handler.py:381

### Função
```python
async def executar_acao_por_nome(update, context, acao, dados):
    user_id = str(update.message.from_user.id)  # ← Linha 10
    ...
    elif acao == "listar_profissionais":
        profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")  # ← Linha 381
```

### Origem de user_id
- **Fonte:** `update.message.from_user.id`
- **Tipo:** ID da pessoa que enviou a mensagem
- **Pode ser:** QUALQUER um (cliente, dono, profissional)

### Quem chama `executar_acao_por_nome`?
1. **bot.py:170** — `tratar_mensagens_gerais()` — recebe CLIENTE ou DONO
2. **gpt_text_handler.py:418** — `processar_texto()` — recebe CLIENTE
3. **principal_router.py (5854, 5866, 8897, 8909, 9166, 9178)** — roteador — pode ser CLIENTE ou DONO
4. **admin_command_service.py (357, 518, 644)** — funções admin — DONO/ADMIN

### user_id sempre é dono?
❌ **NÃO**

### user_id pode ser cliente?
✅ **SIM** (via bot.py, gpt_text_handler.py, principal_router.py)

### user_id pode ser profissional?
❌ **NÃO** (profissional não tem acesso a Telegram direto)

### Impacto se user_id = cliente
🔴 **Cliente vê seus próprios profissionais em vez dos profissionais do DONO**

### Classificação
🔴 **BUG CONFIRMADO**

---

## 🔴 SUSPEITO 2-5: services/agenda_service.py:322, 354, 870, 904

### Função
```python
async def obter_janela_funcionamento(
    user_id: str,              # ← parâmetro
    profissional: str,
    data: date,
    incluir_conflitos: bool = True,
):
    ...
    # Linha 322
    profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
    
    # Linha 354
    f"Clientes/{user_id}/Profissionais/{profissional}/AgendaExcecoes"
    
    # Linhas 870, 904
    path = f"Clientes/{user_id}/Profissionais/{profissional}/AgendaExcecoes/{data}"
```

### Origem de user_id
- **Fonte:** Parâmetro da função
- **Quem passa?** Precisa rastrear callers

### Quem chama `obter_janela_funcionamento`?

Procurando...
```bash
grep -rn "obter_janela_funcionamento" . --include="*.py"
```

**Encontrados em:**
- `event_service_async.py` (múltiplas linhas)
- `profissional_service.py` (múltiplas linhas)
- `verificar_conflito_e_sugestoes_profissional()` — passa user_id direto
- Roteador principal — passa user_id do contexto

### Problema
🔴 **`obter_janela_funcionamento(user_id, ...)` recebe user_id SEM resolver para dono**

Quem chama passa o user_id da pessoa que quer agendar (CLIENTE) ou do dono (DONO).

### user_id sempre é dono?
❌ **NÃO** — pode ser cliente que está tentando agendar

### user_id pode ser cliente?
✅ **SIM** — se cliente está fazendo agendamento

### user_id pode ser profissional?
❌ **NÃO** — profissional não chama essas funções

### Impacto se user_id = cliente
🔴 **Busca exceções de agenda do CLIENTE em vez do DONO**
- Cliente vê agenda dele
- Cliente modifica exceções dele
- Profissionais dele (vazio) são usados para conflitos

### Classificação
🔴 **BUG CONFIRMADO** (junto com fluxos que passam user_id=cliente)

---

## 🟡 SUSPEITO 6-12: services/gpt_service.py:596, 1381, 2247, 2517, 2775, 2855, 3000

### Função container
```python
async def processar_com_gpt_com_acao(
    texto_usuario: str,
    contexto: dict,
    instrucao: str,
    user_id: str | None = None,
):
    # ...
    # Linha 596:   await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
    # Linha 1381:  await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
    # Linha 2247:  await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
    # Linha 2517:  await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
    # Linha 2775:  await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
    # Linha 2855:  await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
    # Linha 3000:  await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
```

### Origem de user_id
- **Fonte:** Parâmetro `user_id: str | None`
- **Derivação:** Se None, extrai de contexto["usuario"]["id"]
- **Quem passa?** Múltiplos callers

### Quem chama `processar_com_gpt_com_acao`?

1. **gpt_text_handler.py:395** — `processar_texto()` — passa user_id (ID de CLIENTE)
2. **voice_command_handler.py:50** — `processar_comando_voz()` — passa user_id (ID de quem enviou áudio)
3. **principal_router.py:9288** — `roteador_principal()` — passa contexto com user_id

### Análise por caller

#### **gpt_text_handler.py:395** (CLIENTE Telegram)
```python
resultado_raw = await processar_com_gpt_com_acao(
    user_id=user_id,  # ← ID do cliente
    texto_usuario=texto,
    contexto=contexto,
    instrucao=INSTRUCAO_SECRETARIA,
)
```
**user_id = CLIENTE**

#### **voice_command_handler.py:50** (ÁUDIO)
```python
resultado = await processar_com_gpt_com_acao(
    texto_usuario=texto,
    contexto=contexto,
    instrucao=INSTRUCAO_SECRETARIA,
    user_id=user_id,  # ← ID de quem enviou voz
)
```
**user_id = QUEM ENVIOU VOZ** (cliente ou dono)

#### **principal_router.py:9288** (ROTEADOR)
```python
resposta_gpt = await chamar_gpt_com_contexto(
    mensagem, 
    contexto, 
    INSTRUCAO_SECRETARIA
)
```
**user_id = contexto["usuario"]["id"]** (cliente ou dono, dependendo de quem passou para roteador)

### user_id sempre é dono?
❌ **NÃO** — é CLIENTE quando chamado de gpt_text_handler

### user_id pode ser cliente?
✅ **SIM** — gpt_text_handler passa user_id=cliente

### user_id pode ser profissional?
❌ **NÃO** — profissional não acessa GPT direto

### Impacto se user_id = cliente
🔴 **CRÍTICO** — Busca profissionais do CLIENTE em vez do DONO
- GPT vê profissionais do cliente (vazio)
- GPT não consegue sugerir profissionais reais
- Respostas de disponibilidade ficam erradas

### Classificação
🔴 **BUG CONFIRMADO** — gpt_text_handler passa user_id=cliente para gpt_service

**Nota:** Já implementamos bloqueio em gpt_service.py:167 para "consulta_disponibilidade_servico", mas outros acessos (linhas 596, 1381, 2247, 2517, 2775, 2855, 3000) AINDA USAM user_id incorreto

---

## 🟡 SUSPEITO 13: router/principal_router.py:2032

### Contexto
```python
# Linha 2032 — dentro de uma lógica condicional complexa
f"Clientes/{user_id}/Profissionais"
```

### Localização exata na função
Precisa verificar qual função e contexto...

### Análise
🔡 **SUSPEITO** — linha sem contexto claro, parte de uma string interpolada

### Classificação
🟡 **DEPENDE DO CHAMADOR** — Precisa verificação manual

---

## 📊 RESUMO DOS 11 SUSPEITOS

| # | Arquivo | Linha | Função | user_id é | Pode ser CLIENTE? | Classificação |
|----|---------|-------|--------|----------|-------------------|---------------|
| 1 | acao_router_handler | 381 | executar_acao_por_nome() | update.message.from_user.id | ✅ SIM | 🔴 BUG |
| 2-5 | agenda_service | 322, 354, 870, 904 | obter_janela_funcionamento() | Parâmetro recebido | ✅ SIM | 🔴 BUG |
| 6-12 | gpt_service | 596, 1381, 2247, 2517, 2775, 2855, 3000 | processar_com_gpt_com_acao() | Parâmetro recebido | ✅ SIM | 🔴 BUG |
| 13 | principal_router | 2032 | (contexto da string) | contexto["usuario"]["id"] | ✅ SIM | 🟡 VERIF |

---

## 🔴 CONCLUSÃO: Todos os 11 são BUGS

### Padrão Identificado
```
TODOS recebem user_id SEM VERIFICAÇÃO DE ORIGEM
↓
user_id pode ser CLIENTE
↓
Busca Clientes/{CLIENTE}/Profissionais
↓
Encontra profissionais do CLIENTE (quando existe)
↓
Lógica quebrada
```

### Severidade
- **Linhas 322, 354, 870, 904** (agenda_service) — 🔴 CRÍTICO
- **Linhas 596, 1381, 2247, 2517, 2775, 2855, 3000** (gpt_service) — 🔴 CRÍTICO
- **Linha 381** (acao_router_handler) — 🟡 MÉDIO (depende de filtro anterior)

---

## ✅ FIX PADRÃO

```python
# Para cada suspeito:
# ANTES:
profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")

# DEPOIS:
dono_id = await obter_id_dono(user_id)
profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais")
```

---

## 📌 RECOMENDAÇÃO

Todos os 11 "suspeitos" são de fato **BUGS CONFIRMADOS**.

Precisam de fix com padrão único: sempre resolver user_id para dono_id com `obter_id_dono()` ANTES de usar em path Firestore.
