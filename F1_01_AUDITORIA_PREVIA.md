# F1-01 — Auditoria Prévia: Estado do Lead

**Data:** 2026-06-28  
**Escopo:** Implementar lead_status em Clientes/{tenant_id}/Clientes/{cliente_actor_id}

---

## 📍 Ponto 1: Onde Cliente é Criado/Atualizado

### Funções Encontradas

1. **services/firebase_service.py:54** — `salvar_cliente(user_id, dados)`
   - Função síncrona (antiga)
   - Salva em Firestore Clientes/{user_id}
   - Potencial legado

2. **services/firebase_service_async.py:274** — `async salvar_cliente(user_id: str, dados: dict)`
   - Função assíncrona (atual)
   - Salva em Firestore Clientes/{user_id}
   - **PONTO CRÍTICO**: Aqui é onde novo lead é criado

3. **services/identidade_service.py:128** — `async criar_ator_cliente_automatico()`
   - Criar cliente automaticamente na primeira interação
   - Detecta linguagem, extrai nome
   - **PONTO CRÍTICO**: Primeira mensagem → criar lead_status=novo

4. **services/notificacao_service.py:94** — `criar_notificacoes_evento_cliente_e_profissional()`
   - Notificações pós-evento
   - Não cria cliente

### Impacto & Riscos

✅ **O que fazer:**
- Interceptar em `criar_ator_cliente_automatico()` (identidade_service.py:128)
- Quando cliente novo é criado → salvar lead_status=novo + primeira_interacao=agora
- Usar função nova `lead_status_service.atualizar_lead_status()`

⚠️ **Risco:**
- Se salvar_cliente() é chamado antes de criar_ator_cliente_automatico(), lead_status será None
- Verificar se há path onde cliente é criado sem passar por criar_ator_cliente_automatico()

---

## 📍 Ponto 2: Onde Evento é Criado/Confirmado

### Funções Encontradas

1. **handlers/event_handler.py** (múltiplas linhas)
   - Cria eventos em Clientes/{dono_id}/Eventos/{event_id}
   - Salva dados do evento (cliente, profissional, horário, etc)
   - **PONTO CRÍTICO**: event_status=confirmado significa lead_status=agendado

2. **handlers/acao_handler.py:589**
   - Cria evento após ação
   - Também salva em Clientes/{user_id}/Eventos/{evento_id}

### Fluxo de Confirmação

```
1. Evento é criado → event_status="criado"
2. Cliente envia /sim (A-01 confirmação)
3. Evento passa para event_status="confirmado"
4. **AQUI**: lead_status deve virar "agendado"
```

### Impacto & Riscos

✅ **O que fazer:**
- Em handlers/event_handler.py, quando event_status → "confirmado"
- Chamar `lead_status_service.atualizar_lead_status(cliente_id, "agendado", tenant_id)`
- Também atualizar cliente_actor_id em Clientes/{tenant_id}/Clientes/{cliente_actor_id}

⚠️ **Risco:**
- Confirmação pode vir de múltiplos lugares
- Verificar se há múltiplas funções que mudam event_status para confirmado
- Garantir que lead_status só mude UMA VEZ (idempotente)

---

## 📍 Ponto 3: Onde Evento é Marcado Concluído

### Investigação Necessária

Não encontrado ainda em buscas iniciais. Verificar:
- Se evento tem campo `event_status="concluido"`
- Se há scheduler que marca evento como concluído
- Se há interface admin para marcar concluído

### Impacto & Riscos

⚠️ **Risco Alto:**
- Se não há ponto onde evento é marcado concluído, não há transição para "atendido"
- Pode exigir nova funcionalidade (escopo?)
- Deve ser **DETERMINÍSTICO**, não manual

---

## 📍 Ponto 4: Onde Mensagens Entram (Antes/Depois GPT)

### Fluxo Atual

```
1. handlers/bot.py → Recebe mensagem
2. handlers/bot.py → Resolve tenant_id, carrega contexto
3. router/principal_router.py → Roteamento determinístico
4. services/gpt_executor.py → Chama GPT (se necessário)
5. handlers/task_handler.py → Executa ações pós-GPT
```

### Pontos de Intercepção para lead_status

**ANTES DE GPT:**
- handlers/bot.py (linhas ~100-200) — Após resolver tenant_id
- Aqui é determinístico: primeira mensagem → novo
- Aqui é determinístico: mensagem com palavras-chave → interessado

**DEPOIS DE EVENTO CRIADO:**
- handlers/event_handler.py — Quando evento é salvo com status "confirmado"

**DETERMINÍSTICO (não no GPT):**
- Não deixar GPT decidir lead_status
- Usar regras determinísticas: palavras-chave, estado do evento, etc

### Impacto & Riscos

✅ **O que fazer:**
- Adicionar chamada a `lead_status_service.avaliar_transicao_deterministica()`
- Logo após handlers/bot.py resolver tenant_id
- ANTES de chamar principal_router

⚠️ **Risco:**
- Se chamar após GPT, pode estar contaminado por interpretação de IA
- Deve ser ANTES ou paralelo, não depois

---

## 📍 Ponto 5: Transições de Estado — Onde Ocorrem

### Estados & Gatilhos Determinísticos

| Estado | Gatilho | Onde |
|--------|---------|------|
| novo | 1ª mensagem do cliente | handlers/bot.py / criar_ator_cliente_automatico() |
| interessado | Palavras: preço, horário, serviço, disponibilidade | handlers/bot.py (análise antes GPT) |
| negociacao | Ajuste, troca, mudança de data/hora/prof/serviço | event_handler.py (quando evento é alterado) |
| agendado | evento.status = "confirmado" | event_handler.py (confirmação de evento) |
| atendido | evento.status = "concluido" | ???  (não encontrado ainda) |
| retorno_pendente | X dias após atendimento sem novo agendamento | scheduler (novo?) |
| inativo | 30+ dias sem interação | scheduler (novo?) |

### Impacto & Riscos

⚠️ **Risco Alto em Temporais:**
- retorno_pendente e inativo exigem scheduler ou batch job
- Pode exigir nova funcionalidade: followup_scheduler?
- Escopo diz "não recriar followup_scheduler"
- Solução: verificar se existe scheduler que pode ser reutilizado

---

## 📊 Sumário de Impacto

### Arquivos a Modificar

1. **services/lead_status_service.py** (NOVO)
   - Lógica determinística de transições
   - Funções: atualizar_lead_status(), avaliar_transicao(), registrar_auditoria()

2. **services/identidade_service.py**
   - Em criar_ator_cliente_automatico() (linha ~128)
   - Adicionar: atualizar_lead_status(..., "novo", ...)

3. **handlers/bot.py**
   - Logo após resolver tenant_id (~linha 150)
   - Adicionar: avaliar_transicao_deterministica() ANTES principal_router

4. **handlers/event_handler.py**
   - Quando event_status → "confirmado"
   - Adicionar: atualizar_lead_status(..., "agendado", ...)
   - Quando evento é alterado (ajuste/mudança)
   - Adicionar: atualizar_lead_status(..., "negociacao", ...)

5. **handlers/task_handler.py** (possível)
   - Verificar se há transições pós-evento

### Arquivos NÃO a Modificar

✅ Não alterar:
- agenda/conflito/disponibilidade/sugestão/criação (escopo explícito)
- gpt_executor.py (GPT não decide lead_status)
- followup_scheduler (não recriar)
- cliente_profile (apenas influencia relatórios)

### Regras de Ouro

✅ **O que é Obrigatório:**
- lead_status é DETERMINÍSTICO (não usa GPT)
- lead_status é PERSISTIDO (Firestore, não sessão)
- lead_status é ISOLADO (multi-tenant)
- lead_status muda em pontos EXISTENTES (não cria novos fluxos)
- lead_status tem AUDITORIA (registra transições)

---

## 🚨 Pendências de Investigação

1. **Evento concluído** — Procurar onde evento é marcado como "concluido"
   - Em `event_handler.py`?
   - Em `task_handler.py`?
   - Ou não existe ainda?

2. **Scheduler para temporal** — Verificar se existe scheduler que pode ser reutilizado
   - Para retorno_pendente (X dias pós-atendimento)
   - Para inativo (30+ dias sem interação)

3. **Multi-tenant em identidade_service** — Verificar se criar_ator_cliente_automatico() já passa tenant_id
   - Se não, será preciso adicionar

4. **Path de cliente novo** — Verificar se há outros paths onde cliente é criado além de criar_ator_cliente_automatico()

---

**Próximo passo:** Investigar pendências + criar lead_status_service.py
