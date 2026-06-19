# 🔔 MATRIZ DE NOTIFICAÇÕES POR EVENTO

**Data:** 2026-06-19  
**Status:** CRÍTICA — Achado real de falha em produção  
**Criticidade:** P0 — Cliente/Dono não notificado = agendamento invisível

---

## 📋 Contexto do Achado

**Observação em Teste Real (2026-06-19):**
- Cliente agendou corte com Bruna
- **Evento foi criado com sucesso** ✅
- **Dono NÃO recebeu aviso** ❌
- **Profissional (Bruna) NÃO recebeu aviso** ❌
- Apenas cliente recebeu (talvez)

**Impacto:**
- Dono não sabe que tem novo agendamento
- Profissional não sabe que tem cliente chegando
- Risco: Agendamento não confirmado, cliente fica esperando

---

## 🎯 Objetivo RO-13

Validar que **toda ação de agendamento** dispara notificações corretas para:
1. ✅ **Cliente** — Confirmação do agendamento
2. ✅ **Dono** — Novo agendamento na agenda
3. ✅ **Profissional** — Novo cliente no horário

---

## 📊 Matriz de Notificações × Ações

### 6 Ações Críticas

| Ação | Quem Dispara | Descrição |
|------|--------------|-----------|
| **Agendamento Criado (Cliente)** | Cliente manda mensagem | Cliente quer agendar serviço |
| **Agendamento Criado (Dono)** | Dono cria agendamento | Dono cria evento para cliente |
| **Cancelamento (Cliente)** | Cliente cancela | Cliente desiste do agendamento |
| **Cancelamento (Dono)** | Dono cancela | Dono cancela evento |
| **Alteração de Horário** | Cliente/Dono altera | Mudar data ou hora |
| **Lembrete Pré-Agendamento** | Scheduler automático | 30min ou 1h antes |

---

## 📬 Matriz Notificações Esperadas

### 1️⃣ Agendamento Criado pelo Cliente

```
AÇÃO: Cliente envia "quero agendar escova com Bruna amanhã 15h"
EVENT: evento.confirmado = True, cliente_id = X, profissional = Bruna

NOTIFICAÇÕES OBRIGATÓRIAS:
┌─────────────────────────────────────────────────────────┐
│ CLIENTE → Cliente (user_id)                             │
├─────────────────────────────────────────────────────────┤
│ Tipo: "agendamento_confirmado"                          │
│ Canal: Telegram (ou WhatsApp)                           │
│ Conteúdo:                                               │
│   - "Seu agendamento foi confirmado!"                   │
│   - Serviço: Escova                                     │
│   - Profissional: Bruna                                 │
│   - Data: Amanhã (2026-06-20)                           │
│   - Hora: 15:00                                         │
│   - Evento ID: {evento_id}                              │
│ Obrigatório: SIM                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ DONO → Dono (user_id)                                   │
├─────────────────────────────────────────────────────────┤
│ Tipo: "novo_agendamento"                                │
│ Canal: Telegram (ou WhatsApp)                           │
│ Conteúdo:                                               │
│   - "Novo agendamento!"                                 │
│   - Cliente: X                                          │
│   - Serviço: Escova                                     │
│   - Profissional: Bruna                                 │
│   - Data: Amanhã (2026-06-20)                           │
│   - Hora: 15:00                                         │
│   - Evento ID: {evento_id}                              │
│ Obrigatório: SIM                                        │
│ Status: ❌ FALHA DETECTADA — Dono não recebe            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ PROFISSIONAL → Bruna (contato_profissional_id)         │
├─────────────────────────────────────────────────────────┤
│ Tipo: "novo_cliente_profissional"                       │
│ Canal: Telegram (ou WhatsApp)                           │
│ Conteúdo:                                               │
│   - "Novo cliente agendado!"                            │
│   - Cliente: X                                          │
│   - Serviço: Escova                                     │
│   - Data: Amanhã (2026-06-20)                           │
│   - Hora: 15:00                                         │
│   - Evento ID: {evento_id}                              │
│ Obrigatório: SIM                                        │
│ Status: ❌ FALHA DETECTADA — Profissional não recebe    │
└─────────────────────────────────────────────────────────┘
```

### 2️⃣ Agendamento Criado pelo Dono

```
AÇÃO: Dono cria agendamento para cliente Y com Ana (cabeleireira)
EVENT: evento.confirmado = True, cliente_id = Y, profissional = Ana

NOTIFICAÇÕES OBRIGATÓRIAS:
┌─────────────────────────────────────────────────────────┐
│ CLIENTE → Cliente Y                                     │
├─────────────────────────────────────────────────────────┤
│ Tipo: "agendamento_criado_por_dono"                     │
│ Conteúdo: Informar que dono criou agendamento          │
│ Obrigatório: SIM                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ PROFISSIONAL → Ana                                      │
├─────────────────────────────────────────────────────────┤
│ Tipo: "novo_cliente_profissional"                       │
│ Conteúdo: Cliente Y agendado com Ana                    │
│ Obrigatório: SIM                                        │
└─────────────────────────────────────────────────────────┘
```

### 3️⃣ Cancelamento por Cliente

```
AÇÃO: Cliente cancela agendamento
EVENT: evento.status = "cancelado"

NOTIFICAÇÕES OBRIGATÓRIAS:
┌─────────────────────────────────────────────────────────┐
│ DONO → Dono                                             │
├─────────────────────────────────────────────────────────┤
│ Tipo: "agendamento_cancelado"                           │
│ Conteúdo: Cliente X cancelou agendamento               │
│ Obrigatório: SIM                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ PROFISSIONAL → Profissional responsável                 │
├─────────────────────────────────────────────────────────┤
│ Tipo: "cliente_cancelado"                               │
│ Conteúdo: Cliente X cancelou (horário fica livre)      │
│ Obrigatório: SIM                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ CLIENTE → Cliente (confirmação de cancelamento)         │
├─────────────────────────────────────────────────────────┤
│ Tipo: "cancelamento_confirmado"                         │
│ Conteúdo: Seu agendamento foi cancelado                 │
│ Obrigatório: NÃO (mas recomendado)                     │
└─────────────────────────────────────────────────────────┘
```

### 4️⃣ Cancelamento por Dono

```
Similar ao cancelamento por cliente, mas com mensagem diferente.
Dono e profissional precisam concordar com cancelamento.
```

### 5️⃣ Alteração de Horário

```
AÇÃO: Cliente ou dono altera data/hora do evento
EVENT: evento.data e/ou evento.hora_inicio alterados

NOTIFICAÇÕES OBRIGATÓRIAS:
┌─────────────────────────────────────────────────────────┐
│ CLIENTE → Cliente                                       │
├─────────────────────────────────────────────────────────┤
│ Tipo: "agendamento_alterado"                            │
│ Conteúdo: Seu agendamento foi alterado para nova data  │
│ Obrigatório: SIM                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ DONO → Dono                                             │
├─────────────────────────────────────────────────────────┤
│ Tipo: "agendamento_alterado"                            │
│ Conteúdo: Agendamento X foi alterado                   │
│ Obrigatório: SIM                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ PROFISSIONAL → Profissional responsável                 │
├─────────────────────────────────────────────────────────┤
│ Tipo: "horario_alterado"                                │
│ Conteúdo: Cliente X mudou para novo horário             │
│ Obrigatório: SIM                                        │
└─────────────────────────────────────────────────────────┘
```

### 6️⃣ Lembrete Pré-Agendamento (Scheduler)

```
AÇÃO: Scheduler roda 30 min antes do evento
EVENT: evento.data = hoje, evento.hora_inicio = daqui 30min

NOTIFICAÇÕES OBRIGATÓRIAS:
┌─────────────────────────────────────────────────────────┐
│ CLIENTE → Cliente                                       │
├─────────────────────────────────────────────────────────┤
│ Tipo: "lembrete_evento"                                 │
│ Conteúdo: Seu agendamento é em 30 minutos             │
│ Obrigatório: SIM                                        │
│ Timing: 30min antes (idealmente)                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ PROFISSIONAL → Profissional responsável                 │
├─────────────────────────────────────────────────────────┤
│ Tipo: "cliente_chegando"                                │
│ Conteúdo: Cliente X chega em 30 minutos                │
│ Obrigatório: SIM                                        │
│ Timing: 30min antes (idealmente)                        │
└─────────────────────────────────────────────────────────┘
```

---

## 🧪 Teste RO-13: Implementação

**Localização:** `tests/runner_p0_resiliencia_operacional_real.py` → `RO_13_matriz_notificacoes_por_evento()`

### Fluxo do Teste

```python
1. Setup:
   dono_id = "test_owner_{run_id}"
   cliente_id = "test_cliente_{run_id}"
   profissional = "Bruna"
   
2. Criar evento confirmado:
   evento.confirmado = True
   evento.cliente_id = cliente_id
   evento.profissional = "Bruna"
   
3. Criar 3 notificações:
   - Notificação para cliente
   - Notificação para dono
   - Notificação para profissional
   
4. Validar:
   - Existem exatamente 3 notificações?
   - Cada notificação foi para o user_id correto?
   - Cada notificação referencia evento_id correto?
   - Conteúdo tem todos campos obrigatórios?
   - Não há notificação para profissional ERRADO?
```

### Falhas Esperadas

❌ **Teste falha se:**
- Menos de 3 notificações criadas
- Cliente não recebe notificação
- Dono não recebe notificação
- Profissional não recebe notificação
- Notificação vai para user_id errado
- Conteúdo está vazio (falta evento_id, cliente, data, hora)
- Notificação referencia evento_id errado

---

## 🔧 Implementação Necessária

### Problema Identificado

```javascript
// HOJE:
salvar_evento(user_id, evento) {
  // Cria evento ✅
  // Mas NÃO cria notificação para dono ❌
  // E NÃO cria notificação para profissional ❌
}
```

### Solução Necessária

```javascript
// NECESSÁRIO:
salvar_evento(user_id, evento) {
  // 1. Criar evento ✅
  await salvar_evento_firestore(evento)
  
  // 2. Notificar cliente ✅
  await criar_notificacao({
    user_id: evento.cliente_id,
    tipo: "agendamento_confirmado",
    evento_id: evento.id
  })
  
  // 3. Notificar DONO ← FALTANDO
  await criar_notificacao({
    user_id: dono_id,
    tipo: "novo_agendamento",
    evento_id: evento.id
  })
  
  // 4. Notificar PROFISSIONAL ← FALTANDO
  await criar_notificacao({
    user_id: profissional_contato_id,
    tipo: "novo_cliente_profissional",
    evento_id: evento.id
  })
}
```

---

## 📊 Checklist Validação RO-13

### Antes de Executar

- [ ] Entender que dono e profissional NÃO estão recebendo notificações
- [ ] Verificar se notificação_service.py cria 3 notificações
- [ ] Verificar se evento_service_async.py chama criar_notificacao

### Durante Execução

- [ ] Teste RO-13 roda e cria 3 notificações?
- [ ] Ou falha porque faltam notificações?
- [ ] Logs mostram quais notificações foram criadas?

### Após Execução

- [ ] RO-13 passou ou falhou?
- [ ] Se falhou: qual notificação está faltando?
- [ ] Registrar em `bugs_encontrados`

---

## 🚨 Impacto P0

**Por quê é P0?**

```
Cliente agenda
    ↓
Evento é criado (confirmado=True) ✅
    ↓
Dono NÃO é notificado ❌
    ↓
Dono não sabe que tem novo agendamento
    ↓
Cliente chega na hora marcada
    ↓
Profissional/dono não sabe
    ↓
Agendamento não é honrado
    ↓
Reputação prejudicada 💔
```

**Solução:** Toda criação de evento DEVE dispara 3 notificações (cliente, dono, profissional).

---

## 📚 Referências

- **RO-13:** `tests/runner_p0_resiliencia_operacional_real.py`
- **Notificações:** `services/notificacao_service.py`
- **Eventos:** `services/event_service_async.py`
- **Firestore:** `services/firebase_service_async.py`

---

## 📅 Próximos Passos

1. ✅ Executar RO-13 (FASE 4)
2. ❌ Se falhar: Registrar bugs
3. 🔧 Criar patch mínimo (3 notificações)
4. ✅ Reexecutar RO-13 com patch
5. ✅ Validar 13/13 em 3 execuções

---

**Status:** Matriz documentada, teste implementado, pronto para execução.

**Crítica:** P0 — Impacta visibilidade de agendamentos para dono e profissional.

Documento criado: 2026-06-19
