# 🔧 PATCH MT-07 — Regressão NameError:dono_id is not defined

**Data**: 2026-06-19  
**Criticidade**: P0 — Regressão em produção  
**Status**: ✅ **CORRIGIDO E TESTADO**

---

## 📋 Regressão Encontrada

**Erro**: `NameError: dono_id is not defined`  
**Localização**: `handlers/event_handler.py:add_evento_por_gpt()` linhas 519, 560, 595

**Contexto**: MT-07 (patch de contexto v2 multi-tenant) foi integrado em 2026-06-17, mas a função `add_evento_por_gpt()` **não estava obtendo `dono_id`** necessário para chamar `carregar_contexto_temporario_v2()`.

---

## 🔍 Causa Raiz

### Código ANTES do Patch (❌ ERRO)

```python
# handlers/event_handler.py:473-520
async def add_evento_por_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, dados: dict):
    # ...
    duracao_minutos = dados.get("duracao", 60)
    user_id = str(update.message.from_user.id)
    
    # ❌ ERRO: dono_id nunca foi definido!
    contexto = await carregar_contexto_temporario_v2(dono_id, user_id) or {}
    #                                                  ↑↑↑↑↑↑
    # NameError: name 'dono_id' is not defined
```

### Por que aconteceu?

1. **MT-07** adicionou funções v2 que EXIGEM `dono_id` + `cliente_id` para isolamento multi-tenant
2. **`add_evento_por_gpt()`** foi atualizada para chamar `carregar_contexto_temporario_v2()`
3. **MAS** esqueceram de adicionar a linha que obtém `dono_id`:
   ```python
   dono_id = await obter_id_dono(user_id)  # ← FALTAVA ESTA LINHA
   ```

---

## ✅ PATCH APLICADO

### Mudanças em `handlers/event_handler.py`

**Linha 516-519** (ANTES):
```python
        duracao_minutos = dados.get("duracao", 60)
        user_id = str(update.message.from_user.id)

        # ✅ Carrega contexto UMA vez no início (evita UnboundLocalError)
        contexto = await carregar_contexto_temporario_v2(dono_id, user_id) or {}
```

**Linha 516-522** (DEPOIS):
```python
        duracao_minutos = dados.get("duracao", 60)
        user_id = str(update.message.from_user.id)

        # 🔧 PATCH MT-07: Obter dono_id para carregar contexto v2 (multi-tenant)
        dono_id = await obter_id_dono(user_id)

        # ✅ Carrega contexto UMA vez no início (evita UnboundLocalError)
        contexto = await carregar_contexto_temporario_v2(dono_id, user_id) or {}
```

**Linha 595** (ANTES):
```python
                await salvar_contexto_temporario_v2(id_dono, user_id, contexto_confirmacao)
#                                                    ↑↑↑↑↑↑ (typo)
```

**Linha 595** (DEPOIS):
```python
                await salvar_contexto_temporario_v2(dono_id, user_id, contexto_confirmacao)
#                                                    ↑↑↑↑↑↑↑ (corrigido)
```

---

## 🧪 Teste de Regressão

**Arquivo**: `tests/test_mt07_regressao_dono_id.py`

**Fluxo Testado**:
```
1️⃣  Telegram simulado: cliente envia "quero agendar"
2️⃣  GPT retorna: serviço + profissional + data/hora
3️⃣  Sistema pede confirmação
4️⃣  Cliente responde "Pode sim" (confirmação)
5️⃣  add_evento_por_gpt() é chamado
6️⃣  ✅ DEPOIS do patch: evento é criado + notificações geradas
```

### Resultado do Teste

```
======================================================================
TEST: MT-07 Regressão — dono_id is not defined
======================================================================

1️⃣ SETUP
   user_id: 123456789
   dono_id: dono_mt07_20260619181516
   cliente_id: 123456789

2️⃣ TELEGRAM SIMULADO
   Cliente: 'Quero agendar corte com Bruna amanhã às 15h'

3️⃣ GPT EXTRAÇÃO
   Dados extraídos: {'servico': 'corte', 'profissional': 'Bruna', ...}

4️⃣ CONTEXTO SALVO (aguardando confirmação)
   ✅ SALVO em Firestore: Clientes/dono_mt07_20260619181516/Sessoes/123456789

5️⃣ SISTEMA PEDE CONFIRMAÇÃO
   ✨ Corte com Bruna
   📆 2026-06-20 às 15:00
   Posso confirmar esse horário pra você?

6️⃣ CLIENTE CONFIRMAÇÃO
   Cliente: 'Pode sim!'

7️⃣ CALL add_evento_por_gpt()
   → Iniciando add_evento_por_gpt()
   → 🔧 PATCH: obter_id_dono(123456789)
      ✅ dono_id obtido: dono_mt07_20260619181516
   → carregar_contexto_temporario_v2(dono_mt07_20260619181516, 123456789)
      ✅ contexto carregado: ['aguardando_confirmacao_agendamento', ...]
   → salvar_evento() em Clientes/dono_mt07_20260619181516/Eventos/evt_mt07_20260619181516
      ✅ Evento criado: evt_mt07_20260619181516
   → criar_notificacao() para cliente, dono, profissional
      ✅ 3 Notificações criadas

8️⃣ VALIDAÇÃO

   ✅ Evento existe em Firestore:
      id: evt_mt07_20260619181516
      cliente: João
      profissional: Bruna
      data: 2026-06-20 às 15:00
      confirmado: True

   ✅ 3 Notificações criadas:
      1. Cliente notificado (agendamento_confirmado)
      2. Dono notificado (novo_agendamento)
      3. Profissional notificado (novo_cliente_profissional)

======================================================================
✅ TEST PASSOU: MT-07 patch funcionando
   • dono_id obtido corretamente
   • Contexto v2 carregado
   • Evento criado em Firestore
   • Notificações geradas (cliente + dono + profissional)
======================================================================
```

---

## 📊 Evidências do Patch

### 1️⃣ Evento Criado em Firestore ✅

```json
{
  "id": "evt_mt07_20260619181516",
  "cliente_id": "123456789",
  "cliente_nome": "João",
  "profissional": "Bruna",
  "servico": "corte",
  "data": "2026-06-20",
  "hora_inicio": "15:00",
  "hora_fim": "16:00",
  "duracao": 60,
  "descricao": "Corte com Bruna",
  "confirmado": true,
  "criado_em": "2026-06-19T18:15:16.413640"
}
```

**Path**: `Clientes/dono_mt07_20260619181516/Eventos/evt_mt07_20260619181516`

### 2️⃣ Notificação do Cliente ✅

```json
{
  "id": "notif_cli_20260619181516",
  "user_id": "123456789",
  "tipo": "agendamento_confirmado",
  "evento_id": "evt_mt07_20260619181516",
  "conteudo": "Corte com Bruna - 2026-06-20 às 15:00",
  "criado_em": "2026-06-19T18:15:16.413640"
}
```

### 3️⃣ Notificação do Dono ✅

```json
{
  "id": "notif_dono_20260619181516",
  "user_id": "dono_mt07_20260619181516",
  "tipo": "novo_agendamento",
  "evento_id": "evt_mt07_20260619181516",
  "conteudo": "Novo agendamento - João com Bruna",
  "criado_em": "2026-06-19T18:15:16.413640"
}
```

### 4️⃣ Notificação do Profissional ✅

```json
{
  "id": "notif_prof_20260619181516",
  "user_id": "bruna_id",
  "tipo": "novo_cliente_profissional",
  "evento_id": "evt_mt07_20260619181516",
  "conteudo": "Novo cliente - João às 15:00",
  "criado_em": "2026-06-19T18:15:16.413640"
}
```

---

## 📋 Checklist de Validação

- [x] Causa raiz identificada: `dono_id` nunca foi obtido em `add_evento_por_gpt()`
- [x] Patch aplicado em `handlers/event_handler.py` (2 locais)
- [x] Teste de regressão criado: `tests/test_mt07_regressao_dono_id.py`
- [x] Teste PASSA com patch aplicado
- [x] Evento é criado em Firestore corretamente
- [x] 3 Notificações são geradas (cliente, dono, profissional)
- [x] Contexto v2 é carregado com `dono_id` correto

---

## 🚨 Impacto da Regressão (ANTES do Patch)

**Severidade**: 🔴 P0 — Bloqueador crítico

```
1. Cliente tenta agendar
2. Sistema pede confirmação
3. Cliente confirma ("Pode sim")
4. add_evento_por_gpt() é chamado
5. ❌ NameError: dono_id is not defined
6. Agendamento falha
7. Cliente não sabe o que aconteceu
8. Suporte recebe tickets em cascata
```

---

## ✅ Resultado Pós-Patch

Todos os mesmos passos acima agora funcionam:
- ✅ Cliente consegue agendar
- ✅ Confirmação funciona
- ✅ Evento é criado em Firestore (multi-tenant safe)
- ✅ 3 Notificações são enviadas
- ✅ Fluxo completo funciona

---

## 📝 Conclusão

**Patch Mínimo Aplicado**:
- 1 linha adicionada em `add_evento_por_gpt()` para obter `dono_id`
- 1 typo corrigido (`id_dono` → `dono_id`)

**Teste**: PASSOU ✅

**Regressão**: CORRIGIDA ✅

**Recomendação**: Deploy imediato em produção

---

**Patch criado**: 2026-06-19  
**Teste validado**: 2026-06-19  
**Status**: ✅ **PRONTO PARA PRODUÇÃO**

