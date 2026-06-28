# SEG-05B MEC-03 — Verificações Críticas de Arquitetura

**Data:** 2026-06-27  
**Propósito:** Validar que SEG-05B respeita a separação entre **governança persistente** e **estado conversacional efêmero**

---

## 🎯 Problema Que Essas Verificações Resolvem

A implementação de MEC-03 cria uma distinção crítica:

```
responder_automaticamente = flag de GOVERNANÇA
  ├─ Persistida em Firestore
  ├─ Sobrevive a reinícios
  ├─ Isolada por tenant_id
  └─ NÃO é estado de sessão

vs

estado conversacional = dados de SESSÃO
  ├─ Em MemoriaTemporaria / context.user_data
  ├─ Perdida em reinício
  ├─ NÃO deve conter responder_automaticamente
  └─ Deve ser ignorado quando pausado
```

Se essa separação falhar:
- ❌ Reinício do bot "esqueceria" que contato está pausado
- ❌ Bloqueio não funcionaria após reinício
- ❌ Governança se misturaria com sessão

Essas verificações **garantem** que essa separação existe.

---

## ✅ Verificação 1: Persistência Após Reinício

### O Que Testa

**Governança é persistida em Firestore, não em sessão**

Cenário:
```
1. /pausar → responder_automaticamente=false salvo em Firestore
2. Aplicação reinicia (conexões fecham, sessão perdida)
3. Contato envia mensagem
4. Bot carrega governança do Firestore
5. Bloqueio funciona como antes
```

### Por Que É Crítico

Se a verificação **FALHAR**:
```
Problema 1: Persistência em Sessão
  /pausar → apenas em context.user_data
  Reinício → context.user_data perdido
  Resultado: contato desbloqueado inadvertidamente ❌

Problema 2: Falta de Carregamento de Firestore
  Mesmo que salvo em Firestore, bot não carrega
  Resultado: bloqueio não funciona após reinício ❌

Problema 3: Isolamento Multi-tenant Quebrado
  Salvo em sessão local, não em Firestore
  Resultado: pausar em tenant A afeta B ❌
```

### Como Testar

**Passo 1: Preparar estado pausado**
```bash
# Contato A-06 envia /pausar
/pausar

# Verificar Firestore
Clientes/{tenant_id}/Governanca/{actor_id}
└─ responder_automaticamente: false ✓
```

**Passo 2: Simular reinício**
```bash
# Parar aplicação/bot
# Aguardar 5 segundos
# Iniciar aplicação/bot novamente

# Contexto de sessão foi perdido, mas Firestore preserva dados
```

**Passo 3: Validar persistência**
```bash
# Mesmo contato envia mensagem normal
"Oi, tudo bem?"

# Bot responde com bloqueio (carregado do Firestore)
"⏸️ Você pausou as respostas automáticas..."

# Não é resposta do GPT!
```

**Passo 4: Verificar logs**
```
[MEC-03-BLOQUEIO] user_id=... | responder_automaticamente=False
  └─ Carregado do Firestore (não da sessão)
```

### Checklist de Validação

- [ ] **Antes do reinício:**
  - [ ] `/pausar` enviado
  - [ ] Firestore atualizado: `responder_automaticamente=false`
  - [ ] Log: `[MEC-03] /pausar executado: sucesso=True`

- [ ] **Durante reinício:**
  - [ ] Aplicação parada completamente
  - [ ] Sessão/context perdido
  - [ ] Aguardar 5+ segundos

- [ ] **Após reinício:**
  - [ ] Aplicação iniciada novamente
  - [ ] Contato envia mensagem
  - [ ] Bot carrega governança do Firestore
  - [ ] Bloqueio funciona
  - [ ] Log: `[MEC-03-BLOQUEIO] user_id=... | responder_automaticamente=False`

- [ ] **Firestore confirmado:**
  - [ ] `Clientes/{tenant_id}/Governanca/{actor_id}.responder_automaticamente` = false
  - [ ] Campo `atualizado_em` mostra timestamp anterior ao reinício
  - [ ] Campo `auditoria` contém registro de `/pausar`

### Resultado Esperado

✅ **PASS:** Contato continua pausado após reinício (governança persistente)  
❌ **FAIL:** Contato fica desbloqueado após reinício (governança era apenas sessão)

---

## ✅ Verificação 2: Bloqueio Sem Processamento

### O Que Testa

**Bloqueio é no ponto de entrada, ANTES de qualquer processamento**

Cenário:
```
1. Contato pausado envia mensagens
2. Cada mensagem é RECEBIDA pelo bot
3. Cada mensagem é BLOQUEADA antes do GPT
4. Nenhuma ação colateral ocorre
   - GPT não é chamado
   - Contexto não é atualizado
   - Agenda não é consultada
   - Eventos não são criados
   - Notificações não são agendadas
```

### Por Que É Crítico

Se a verificação **FALHAR**, surgem side-effects:

```
Problema 1: Processamento Parcial
  Mensagem bloqueada, mas contexto foi atualizado
  Resultado: estado corrompido ❌

Problema 2: Chamadas ao GPT
  Mensagem bloqueada, mas GPT foi chamado
  Resultado: tokens gastos inutilmente ❌
  Resultado: latência aumenta ❌

Problema 3: Agenda Consultada
  Mensagem bloqueada, mas agenda foi lida
  Resultado: I/O desnecessário ❌
  Resultado: cargas em Firestore desnecessárias ❌

Problema 4: Contexto Contaminado
  Mensagem bloqueada, mas MemoriaTemporaria foi atualizada
  Resultado: próximas mensagens têm contexto inválido ❌

Problema 5: Efeitos Colaterais
  Mensagem bloqueada, mas eventos/notificações foram criados
  Resultado: dados órfãos no Firestore ❌
```

### Como Testar

**Passo 1: Preparar estado pausado**
```bash
/pausar
# responder_automaticamente=false salvos
```

**Passo 2: Enviar série de mensagens DIFERENTES**
```bash
Mensagem 1: "Oi"
Mensagem 2: "Como você funciona?"
Mensagem 3: "Agende corte de cabelo para amanhã"
Mensagem 4: "Quais profissionais estão livres?"
```

**Passo 3: Para CADA mensagem, validar**

```bash
### Mensagem 1: "Oi"

Bot responde:
"⏸️ Você pausou as respostas automáticas..."

Não responde com:
❌ "Oi! Tudo bem?" (resposta do GPT)
❌ Sugestão de agendamento (agenda consultada)
❌ Lista de profissionais (serviço chamado)

Log esperado:
[MEC-03-BLOQUEIO-ATIVO] user_id=... | motivo=responder_automaticamente=False...
[Nenhuma outra linha de processamento]

Firestore após mensagem:
✓ MemoriaTemporaria/{user_id} — NÃO mudou
✓ Clientes/{tenant_id}/Eventos — nenhum evento criado
✓ Clientes/{tenant_id}/Profissionais — não consultado
✓ Clientes/{tenant_id}/Tarefas — não consultado
```

**Passo 4: Validar isolamento entre mensagens**

```bash
# Mensagem 1 foi bloqueada, não criou contexto
# Mensagem 2 chega com MemoriaTemporaria limpo (não contaminado)

Mensagem 2: "Como você funciona?"

Bot responde:
"⏸️ Você pausou as respostas automáticas..."

# Mesma resposta genérica (não usa contexto da msg 1)
# Se contexto tivesse sido atualizado, poderia haver divergência
```

### Checklist de Validação

- [ ] **Setup:**
  - [ ] Contato pausado (`responder_automaticamente=false`)
  - [ ] MemoriaTemporaria está limpa antes dos testes

- [ ] **Para CADA mensagem enviada:**
  - [ ] Mensagem é recebida (HTTP 200, sem erro)
  - [ ] Resposta é bloqueio (`responder_automaticamente=false`)
  - [ ] GPT NÃO foi chamado (sem latência anormal)
  - [ ] MemoriaTemporaria NÃO foi atualizada
  - [ ] Agenda NÃO foi consultada
  - [ ] Nenhum evento foi criado
  - [ ] Nenhuma notificação foi agendada
  - [ ] Log mostra: `[MEC-03-BLOQUEIO-ATIVO]`
  - [ ] Nenhum outro log de processamento aparece

- [ ] **Verificação Firestore:**
  - [ ] `Clientes/{tenant_id}/MemoriaTemporaria/{user_id}` — não foi criado/atualizado
  - [ ] `Clientes/{tenant_id}/Eventos` — nenhum novo evento
  - [ ] `Clientes/{tenant_id}/Notificacoes` — nenhuma notificação
  - [ ] `Clientes/{tenant_id}/Governanca/{actor_id}` — apenas `responder_automaticamente`

- [ ] **Verificação de Contexto:**
  - [ ] Mensagem A é bloqueada (não cria contexto)
  - [ ] Mensagem B é bloqueada (não usa contexto de A)
  - [ ] Mensagem C é bloqueada (não usa contexto de A/B)
  - [ ] Cada bloqueio é independente (sem efeito colateral)

- [ ] **Performance:**
  - [ ] Tempo de resposta < 500ms (bloqueio rápido, antes de processamento)
  - [ ] Nenhuma latência anormal (GPT não foi chamado)
  - [ ] Nenhuma I/O desnecessária (Firestore não consultado)

### Resultado Esperado

✅ **PASS:** Bloqueio é limpo, sem side-effects, antes de qualquer processamento  
❌ **FAIL:** Mensagens geram efeitos colaterais (GPT, contexto, agenda, eventos)

---

## 🏗️ Arquitetura Validada

Se **ambas as verificações PASSAREM**, a arquitetura é **correta**:

```
┌─────────────────────────────────────────┐
│  Mensagem Chega                         │
│  user_id = X, tenant_id = A             │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  bot.py:149                             │
│  Carregar governanca(X, A)              │
│  ← Firestore (PERSISTENTE)              │
└────────────┬────────────────────────────┘
             │
             ▼
    responder_automaticamente?
             │
     ┌───────┴───────┐
     │               │
    false          true
     │               │
     ▼               ▼
  BLOQUEIO        CONTINUAR
  ┌──────┐       ┌──────────┐
  │Nenhum│       │Whitelist?│
  │processo      │          │
  │              │ ┌─────┬──┘
  │              │ │     │
  │              no   sim
  │              │     │
  │              ▼     ▼
  │            BLOQUEIA CONTINUA
  │            GPT OK ✓
  └─────────────┬──────────┘
                │
                ▼
        MemoriaTemporaria ATUALIZADA
        Agenda CONSULTADA
        Eventos CRIADOS
```

---

## 📊 Resumo

### Verificação 1: Persistência Após Reinício

| Aspecto | Esperado | Validar |
|---------|----------|---------|
| Antes do reinício | `responder_automaticamente=false` em Firestore | ✓ |
| Durante reinício | Sessão perdida | ✓ |
| Após reinício | Firestore carregado, bloqueio funciona | ✓ |
| Cenário | Governança é PERSISTENTE | ✓ |

### Verificação 2: Bloqueio Sem Processamento

| Aspecto | Esperado | Validar |
|---------|----------|---------|
| Recebimento | Mensagem recebida (HTTP 200) | ✓ |
| Bloqueio | ANTES de qualquer processamento | ✓ |
| Side-effects | ZERO (GPT, contexto, agenda, eventos) | ✓ |
| Logs | `[MEC-03-BLOQUEIO-ATIVO]` apenas | ✓ |
| Performance | < 500ms (bloqueio, não processamento) | ✓ |

---

## 🎯 Conclusão

Essas **duas verificações** validam o coração da implementação:

✅ **Verificação 1** → Governança é persistente (não efêmera)  
✅ **Verificação 2** → Bloqueio é no ponto certo (não colateral)

Se ambas passarem: **Arquitetura está correta**

Se alguma falhar: **Há problema fundamental na implementação**
