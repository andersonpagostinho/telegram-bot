# 🧪 Plano de Testes de Regressão — Fluxo de Agendamento

**Data:** 2026-06-02  
**Objetivo:** Validar fluxo completo sem criar novos fluxos paralelos  
**Metodologia:** Testes manuais (Telegram) + análise de logs Firestore  
**Risco P0:** Testar concorrência (cenário 12)

---

## 📋 Setup Inicial

### Dados de Teste
```
Tenant: TEST_NEOEVE_20260602
Cliente: TEST_USER_001, TEST_USER_002
Profissional: Bruna (TEST_BRUNA), Carla (TEST_CARLA)
Serviço: escova, coloração
```

### Verificações em Cada Teste
```
✓ Entrada do usuário (simulada via Telegram)
✓ Evento criado? (Firestore → Clientes/{dono}/Eventos)
✓ Contexto temporário (Redis: contexto_temporario:{user_id})
✓ Mensagem enviada (log do bot)
✓ Estado final esperado
✓ Sem duplicação de evento
✓ Sem vazar contexto entre usuários
```

---

## 🧪 Cenário 1: Cliente Pergunta Serviço → Data/Hora → Confirmação

### Entrada Simulada
```
TEST_USER_001:
  "vocês fazem escova?"
  "amanhã às 14"
  "sim"
```

### Fluxo Esperado
1. Pergunta "fazem escova?" → sistema lista profissionais que fazem escova
2. Usuário diz "amanhã às 14" → sistema procura horários
3. Sistema envia pré-confirmação: "Perfeito! Encontrei um horário com {prof} amanhã às 14h para sua escova. Posso confirmar?"
4. Usuário confirma "sim" → evento criado
5. Sistema envia: "Pronto, sua escova com {prof} ficou agendada para amanhã às 14h."
6. Contexto limpado

### Verificações
- [ ] `estado_fluxo` == "agendando" durante confirmação pendente
- [ ] `dados_confirmacao_agendamento` preenchido
- [ ] Evento criado em Firestore com `confirmado: true`
- [ ] Mensagem de sucesso enviada
- [ ] `aguardando_confirmacao_agendamento` == false após sucesso
- [ ] Contexto agendamento limpado

### Arquivo/Função
- `principal_router.py` — fluxo principal
- `handlers/event_handler.py::add_evento_por_gpt()` — criação
- `utils/mensagens_agendamento.py::montar_mensagem_preconfirmacao()` — pré-confirmação
- `utils/mensagens_agendamento.py::montar_mensagem_confirmacao_sucesso()` — sucesso

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 2: Confirmações Variadas

### Entrada Simulada (6 tentativas paralelas com diferentes confirmações)
```
TEST_USER_002: quero escova amanhã às 14 → confirmar
TEST_USER_003: quero escova amanhã às 14 → pode sim
TEST_USER_004: quero escova amanhã às 14 → ok
TEST_USER_005: quero escova amanhã às 14 → pode ser
TEST_USER_006: quero escova amanhã às 14 → fecha
TEST_USER_007: quero escova amanhã às 14 → agendar
TEST_USER_008: quero escova amanhã às 14 → perfeito
```

### Validações
- [ ] `eh_confirmacao()` detecta TODOS os 7 gatilhos (principal_router.py:885)
- [ ] Nenhum cria evento duplicado mesmo que confirmações chegarem próximas
- [ ] Ordem de recepção respeitada (sem race condition)

### Arquivo/Função
- `principal_router.py::eh_confirmacao()` — validador

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 3: Serviço + Horário Direto

### Entrada Simulada
```
TEST_USER_009:
  "quero escova amanhã às 14"
  "sim"
```

### Fluxo Esperado
- Detecta serviço + data/hora em uma mensagem
- Pergunta profissional se múltiplos disponíveis
- OU confirma direto se um profissional
- Cria evento sem pedir confirmação dupla

### Verificações
- [ ] Não passa por fluxo de pergunta dupla
- [ ] Pré-confirmação é enviada (não salta para evento)
- [ ] Evento criado apenas após "sim"

### Arquivo/Função
- `principal_router.py` — detecção de intent

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 4: Cliente com Profissional Específico

### Entrada Simulada
```
TEST_USER_010:
  "quero escova com a Bruna amanhã às 14"
  "pode confirmar"
```

### Validações
- [ ] Sistema identifica "com a Bruna"
- [ ] Não pergunta qual profissional
- [ ] Envia pré-confirmação com Bruna específica
- [ ] Confirmação criação evento

### Arquivo/Função
- `principal_router.py` — extração de profissional

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 5: Troca de Profissional

### Entrada Simulada
```
TEST_USER_011:
  "quero escova com a Bruna amanhã às 14"
  "na verdade quero com a Carla"
  "sim"
```

### Fluxo Esperado
- Sistema detecta alteração "com a Carla"
- Valida se Carla faz escova e tem horário disponível
- Atualiza `profissional_escolhido` em contexto
- Envia nova pré-confirmação com Carla
- Cria evento com Carla (não Bruna)

### Verificações
- [ ] Contexto atualiza profissional
- [ ] Evento final tem Carla, não Bruna
- [ ] Não cria evento intermediário para Bruna

### Arquivo/Função
- `principal_router.py::detectar_alteracao_draft_agendamento()` — detecção
- `handlers/event_handler.py` — criação com profissional certo

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 6: Horário Ocupado

### Entrada Simulada (pré-condition: Bruna ocupada às 14h amanhã)
```
TEST_USER_012:
  "escova com a Bruna amanhã às 14"
  (seleciona alternativa sugerida, ex: "15h")
  "sim"
```

### Fluxo Esperado
- Sistema detecta conflito
- Envia: "Bruna ocupada às 14h. Alternativas: 15h, 16h, ..."
- Sistema NÃO cria evento automaticamente
- Usuário escolhe alternativa
- Cria evento no horário escolhido

### Verificações
- [ ] `verificar_conflito_e_sugestoes_profissional()` acionado
- [ ] Nenhum evento criado em 14h
- [ ] Evento criado apenas no horário escolhido
- [ ] Mensagem de conflito enviada (não silenciosa)

### Arquivo/Função
- `services/event_service_async.py::verificar_conflito_e_sugestoes_profissional()` — validação
- `handlers/event_handler.py` — sugestões

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 7: Profissional Ocupado, Outro Disponível

### Entrada Simulada (pré-condition: Bruna ocupada, Carla livre)
```
TEST_USER_013:
  "escova com a Bruna amanhã às 14"
```

### Fluxo Esperado
- Sistema detecta Bruna ocupada
- Sugere Carla como alternativa no mesmo horário
- Mensagem: "Bruna ocupada. Tenho Carla disponível às 14h. Quer agendar com Carla?"
- Sistema NÃO agenda automaticamente
- Usuário escolhe: "sim com Carla" ou "outro horário com Bruna"

### Verificações
- [ ] Sistema oferece alternativa, não força
- [ ] Sem criação de evento até confirmação explícita

### Arquivo/Função
- `services/profissional_service.py::buscar_profissionais_disponiveis_no_horario()` — busca

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 8: Serviço Sem Profissional, Múltiplos Disponíveis

### Entrada Simulada
```
TEST_USER_014:
  "quero escova amanhã às 14"
```

### Fluxo Esperado
- Sistema detecta múltiplos profissionais (Bruna, Carla)
- Pergunta: "Qual profissional prefere? Bruna ou Carla?"
- Usuário escolhe: "Bruna"
- Sistema envia pré-confirmação com Bruna
- Usuário confirma

### Verificações
- [ ] Não pula pergunta de profissional
- [ ] Contexto salva múltiplas opções
- [ ] Apenas profissional escolhido é usado

### Arquivo/Função
- `principal_router.py` — lógica de escolha

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 9: Mensagens Sociais No Meio

### Entrada Simulada
```
TEST_USER_015:
  "quero escova amanhã às 14"
  "oi"
  "tá aí?"
  "bom dia"
  "sim"
```

### Fluxo Esperado
- Mensagens sociais ("oi", "bom dia", etc.) não reiniciam fluxo
- Sistema mantém contexto de agendamento
- Responde a social, mas continua aguardando confirmação
- "sim" final cria evento

### Verificações
- [ ] `tem_contexto_agendamento_ativo()` retorna true durante sociais
- [ ] Fluxo NÃO reinicia
- [ ] Contexto preservado
- [ ] Evento criado com sucesso após "sim"

### Arquivo/Função
- `principal_router.py::tem_contexto_agendamento_ativo()` — proteção
- `router/conversation_classifier.py` — classificação social

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 10: Multi-Cliente — Sem Vazar Contexto

### Entrada Simulada (simultânea)
```
TEST_USER_001:
  "escova amanhã às 14"
  "sim"

TEST_USER_002:
  "coloração com Carla em 03/06 às 15"
  "sim"
```

### Fluxo Esperado
- Cada usuário tem seu próprio contexto
- Eventos criados independentemente
- Sem mistura de dados

### Verificações
- [ ] `carregar_contexto_temporario(TEST_USER_001)` retorna apenas dados de TEST_USER_001
- [ ] `salvar_contexto_temporario(TEST_USER_001, ...)` não sobrescreve TEST_USER_002
- [ ] Firestore eventos separados por cliente
- [ ] Nenhum contexto vaza entre user_ids

### Arquivo/Função
- `utils/contexto_temporario.py` — isolamento por user_id

### Risco: ⚠️ **Race condition se Redis falhar**

### Status
**[ ] NÃO TESTADO**

---

## 🧪 Cenário 11: Confirmação Duplicada (MESMO USUÁRIO, 2 CONFIRMAÇÕES SEQUENCIAIS)

### 1️⃣ Condição Exata Simulada
```
TEST_USER_016:
  Msg 1: "escova amanhã às 14"
         → Sistema entra em estado agendando
         → Salva: aguardando_confirmacao_agendamento = True
  
  Msg 2: "sim" (primeira confirmação)
         → Executa fluxo completo
         → Salva evento em Firestore
         → Limpa contexto
  
  Msg 3: "sim" (segunda confirmação — DUPLICADA)
         → Deve REJEITAR
```

### 2️⃣ Trecho Real do Código Exercitado

**Primeira confirmação ("sim"):**
- principal_router.py:3366-3368 — valida `aguardando_confirmacao_agendamento == True`
- principal_router.py:3372-3391 — lê `dados_confirmacao_agendamento`
- principal_router.py:3409-3412 — **MARCA COMO FALSO + SALVA**
  ```python
  ctx["aguardando_confirmacao_agendamento"] = False  # ← ESTADO MUDA
  ctx.pop("dados_confirmacao_agendamento", None)     # ← DADOS APAGADOS
  await salvar_contexto_temporario(user_id, ctx)     # ← PERSISTE EM FIRESTORE
  ```
- event_handler.py:929 — `await salvar_evento(user_id, evento_data)`
- event_handler.py:992 — `await limpar_contexto_agendamento(user_id)`
  ```python
  # contexto_temporario.py:39-40
  "aguardando_confirmacao_agendamento": firestore.DELETE_FIELD,
  "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
  ```

**Segunda confirmação ("sim"):**
- principal_router.py:3366 — **FALHA AQUI**
  ```python
  if eh_confirmacao_pendente_ativa(ctx) and ...  # ← ctx.get("aguardando_confirmacao_agendamento") == False
  ```
  Condition é FALSE → bloco não executa → "sim" é ignorado

### 3️⃣ Proteção Existente Hoje

✅ **Proteção de Leitura:**
- principal_router.py:3366 — valida `eh_confirmacao_pendente_ativa(ctx)`
  - Lê: `return bool(ctx.get("aguardando_confirmacao_agendamento"))` (principal_router.py:1578)

✅ **Proteção de Escrita:**
- principal_router.py:3409 — define `= False` ANTES de executar ação
- principal_router.py:3412 — salva contexto EM FIRESTORE
- contexto_temporario.py:39-40 — limpa com `DELETE_FIELD` (atômico no Firestore)

✅ **Proteção de Duplicação (Evento):**
- event_service_async.py:131-135 — ID idempotente por slot
  ```python
  base_id = f"{cliente_id}_{profissional}_{data}_{hora_inicio}"
  existente = await buscar_dado_em_path(path)
  if existente:
      return "duplicado"
  ```

### 4️⃣ Risco Identificado

⚠️ **Race Condition em MemoriaTemporaria:**

Se duas requisições chegarem **SIMULTANEAMENTE** (antes de principal_router.py:3412 completar):

```
T1: Msg "sim" lê ctx.get("aguardando_confirmacao_agendamento") = True  ✅ Passa
T2: Msg "sim" lê ctx.get("aguardando_confirmacao_agendamento") = True  ✅ Passa
│
T1: Define ctx["aguardando_confirmacao_agendamento"] = False
T1: Salva em Firestore
│
T2: Define ctx["aguardando_confirmacao_agendamento"] = False  ← REDUNDANTE
T2: Salva em Firestore (overwrite)
│
T1: Chama event_handler.py:929 → salvar_evento()
T2: Chama event_handler.py:929 → salvar_evento()  ← SIMULTÂNEA
```

**Proteção NO Firestore (evento):**
- event_service_async.py:131-135 previne 2 eventos com MESMO ID
- Mas CONTEXTO pode ser lido/escrito simultaneamente sem lock

**Risco Específico:** Leitura sem exclusão (read-modify-write) em MemoriaTemporaria
- Firestore NÃO bloqueia leituras paralelas
- Sem transação ou CAS, ambas as requisições veem `True`

### 5️⃣ Evidência no Log/Firestore

**Se PASSOU (sequencial):**
```
Log 1:
  [AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto
  ✅ Evento salvo para {dono} com ID {event_id}

Log 2:
  ⚠️ Sem log (principal_router.py:3366 falha silenciosamente)
  Msg "sim" é ignorado

Firestore:
  Clientes/{dono}/Eventos/{event_id} — 1 documento
  Clientes/{user_id}/MemoriaTemporaria/contexto:
    - aguardando_confirmacao_agendamento: <não existe (DELETE_FIELD)>
    - dados_confirmacao_agendamento: <não existe (DELETE_FIELD)>
```

**Se FALHOU (simultânea):**
```
Log:
  [AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto  (T1)
  [AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto  (T2)  ← DOIS LOGS
  ✅ Evento salvo para {dono} com ID {event_id}
  ♻️ Evento já existe (idempotente). Não criando duplicado.  ← T2 DETECTADO

Firestore:
  Clientes/{dono}/Eventos/{event_id} — 1 documento (ID salva idempotência)
  Clientes/{user_id}/MemoriaTemporaria/contexto: — pode estar inconsistente
    - aguardando_confirmacao_agendamento: pode estar TRUE ou FALSE
    - dados_confirmacao_agendamento: pode estar lá ou não
```

### 6️⃣ Classificação se Falhar

**Se sequencial (msg 2 entra APÓS msg 1 ser processada):**
- ✅ **PASSOU** — Proteção funciona

**Se simultânea (msg 2 entra ANTES de msg 1 completar salvar):**
- 🔴 **P0 BLOQUEANTE** — Race condition em RMW sem lock/transação
  - Motivo: MemoriaTemporaria não usa transação
  - Risco: Contexto fica inconsistente
  - Impacto: Fluxo pode ficar preso em estado agendando

### 7️⃣ Proteção vs Risco

| Camada | Proteção | Risco |
|--------|----------|-------|
| **Lógica (principal_router.py:3366)** | ✅ Valida `aguardando_confirmacao_agendamento` | ⚠️ Sem lock entre leitura/escrita |
| **Contexto (MemoriaTemporaria)** | ⚠️ `DELETE_FIELD` é atômico | ⚠️ RMW não é atômico |
| **Evento (Firestore)** | ✅ ID idempotente | ✅ Detecta duplicado |

**Conclusão:** Cenário 11 com **requisições sequenciais PASSA**. Com **simultâneas, é P0 bloqueante**.

---

## 🧪 Cenário 12: Dois Usuários Simultâneos, Mesmo Horário

### 1️⃣ Condição Exata Simulada
```
TEST_USER_017 e TEST_USER_018 SIMULTANEAMENTE:
  
Msg 1 (USER_017): "quero escova com Bruna 2026-06-03 14:00"
  → principal_router.py:1720 — ctx["estado_fluxo"] = "agendando"
  → principal_router.py:1729 — ctx["aguardando_confirmacao_agendamento"] = True
  → principal_router.py:1732 — ctx["dados_confirmacao_agendamento"] = {...}

Msg 2 (USER_018): "quero escova com Bruna 2026-06-03 14:00"
  → Mesmo setup, contexto separado (user_id diferente)

Msg 3 (USER_017): "sim"
  → Fluxo de confirmação inicia

Msg 4 (USER_018): "sim"  (SIMULTÂNEA com MSG 3)
  → Fluxo de confirmação inicia
```

### 2️⃣ Trecho Real do Código Exercitado

**USER_017 — confirmação:**
- principal_router.py:3366-3415 — processa confirmação
- event_handler.py:929 — `await salvar_evento(user_id=TEST_USER_017, ...)`
- event_service_async.py:87-98 — verifica conflito
- event_service_async.py:131-135 — cria ID idempotente:
  ```python
  base_id = f"{cliente_id}_{profissional}_{data}_{hora_inicio}"
  # BASE_ID = "TEST_USER_017_Bruna_2026-06-03_14:00"
  event_id = "test_user_017_bruna_2026-06-03_14:00"
  ```
- event_service_async.py:137 — `await salvar_dado_em_path(path, evento)`
  ```python
  path = f"Clientes/{dono_id}/Eventos/{event_id}"
  ```

**USER_018 — confirmação (SIMULTÂNEA):**
- event_service_async.py:87-98 — verifica conflito
- event_service_async.py:131-135 — cria ID idempotente:
  ```python
  base_id = f"{cliente_id}_{profissional}_{data}_{hora_inicio}"
  # BASE_ID = "TEST_USER_018_Bruna_2026-06-03_14:00"  ← DIFERENTE!
  event_id = "test_user_018_bruna_2026-06-03_14:00"  ← PATH DIFERENTE
  ```
- event_service_async.py:131-135 — **BUSCA DOCUMENTO COM ID DIFERENTE**
  ```python
  path = f"Clientes/{dono_id}/Eventos/test_user_018_bruna_2026-06-03_14:00"
  # NÃO ENCONTRA (porque é outro usuário)
  ```

### 3️⃣ Proteção Existente Hoje

✅ **Isolamento por user_id:**
- contexto_temporario.py:31 — `path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"`
- Cada usuário tem SEU PRÓPRIO documento em Firestore

✅ **ID idempotente inclui cliente_id:**
- event_service_async.py:102 — `base_id = f"{cliente_id}_{profissional}_{data}_{hora_inicio}"`
- Dois usuários = dois IDs diferentes

✅ **Verificação de conflito por profissional:**
- event_service_async.py:87-98 — consulta Firestore para profissional + horário
  ```python
  conflitos = await verificar_conflito(
      profissional=profissional,  ← Procura por PROFISSIONAL
      data=data,
      hora_inicio=hora_inicio
  )
  ```

### 4️⃣ Risco Identificado

🔴 **P0 CRÍTICO — Race Condition em verificar_conflito():**

```
T1 (USER_017): event_service_async.py:88 — consulta "conflitos com Bruna em 14:00"
               Resultado: VAZIO (sem conflito)

T2 (USER_018): event_service_async.py:88 — consulta "conflitos com Bruna em 14:00"
               Resultado: VAZIO (sem conflito)

T1: event_service_async.py:137 — salva evento de USER_017 com Bruna em 14:00
    Path: Clientes/{dono}/Eventos/test_user_017_bruna_2026-06-03_14:00

T2: event_service_async.py:137 — salva evento de USER_018 com Bruna em 14:00
    Path: Clientes/{dono}/Eventos/test_user_018_bruna_2026-06-03_14:00
    ✅ Salva SEM CONFLITO (ID diferente)
```

**Resultado:**
- 2 eventos em Firestore (AMBOS COM BRUNA, MESMO HORÁRIO)
- Profissional DUPLO AGENDADA

**Por quê não foi detectado:**
- event_service_async.py:131-135 (ID idempotente) protege DENTRO do MESMO usuário
- Mas verificar_conflito() é consultado ANTES do save (read-modify-write)
- Sem transação, interval entre consulta e save permite race

### 5️⃣ Evidência no Log/Firestore

**Se PASSOU (sem conflito — esperado):**
```
Log 1 (USER_017):
  ✅ Evento salvo para {dono} com ID test_user_017_bruna_2026-06-03_14:00

Log 2 (USER_018):
  ✅ Evento salvo para {dono} com ID test_user_018_bruna_2026-06-03_14:00  ← ERRO!

Firestore:
  Clientes/{dono}/Eventos/test_user_017_bruna_2026-06-03_14:00 — 1 doc
  Clientes/{dono}/Eventos/test_user_018_bruna_2026-06-03_14:00 — 1 doc  ← 2 DOCS!
  
  Ambos têm:
    "profissional": "Bruna"
    "data": "2026-06-03"
    "hora_inicio": "14:00"  ← MESMO HORÁRIO, MESMA PROFISSIONAL
```

**Se evento_deve_entrar_na_agenda() filtrar duplicados:**
```
Firestore terá 2 documentos, mas um pode ser marcado como inativo/ignorado
Depende de: handlers/event_handler.py:716-725
```

### 6️⃣ Classificação

🔴 **P0 BLOQUEANTE — Race Condition em RMW (verificar_conflito + salvar)**

Motivo:
- `verificar_conflito()` é leitura
- `salvar_evento()` é escrita
- Entre as duas, outro usuário pode criar conflito
- Sem transação ou lock, conflito não é detectado

Impacto:
- Profissional fica duplo agendada
- Sistema de agenda fica inconsistente
- Dados corrompidos no Firestore

### 7️⃣ Proteção vs Risco

| Camada | Proteção | Risco |
|--------|----------|-------|
| **Contexto (user_id)** | ✅ Isolado | ✅ OK |
| **ID evento** | ✅ Idempotente POR user_id | ✅ OK |
| **Conflito (evento-evento)** | ⚠️ Consulta antes de save | 🔴 RMW sem lock |
| **Firestore transação** | ❌ Não usa | 🔴 Race condition |

**Conclusão:** Cenário 12 **FALHA EM SIMULTÂNEA — P0 BLOQUEANTE**.

---

## 🧪 Cenário 12B: Mesmo Usuário, Duas Confirmações Simultâneas (MAIS CRÍTICO)

### 1️⃣ Condição Exata Simulada
```
TEST_USER_019 ÚNICO:

Msg 1: "escova com Bruna 2026-06-03 14:00"
  → principal_router.py:1729 — ctx["aguardando_confirmacao_agendamento"] = True
  → Contexto salvo EM FIRESTORE

Msg 2 e 3 SIMULTÂNEAS: "sim" e "sim"
  T1: Lê ctx.get("aguardando_confirmacao_agendamento")
  T2: Lê ctx.get("aguardando_confirmacao_agendamento")  (ANTES de T1 escrever False)
  
  Ambas veem: True → Ambas entram no bloco
```

### 2️⃣ Trecho Real do Código Exercitado

**T1 (primeira confirmação):**
- principal_router.py:3366 — valida `aguardando_confirmacao_agendamento == True` ✅
- principal_router.py:3372-3391 — lê `dados_confirmacao_agendamento` ✅
- principal_router.py:3409 — `ctx["aguardando_confirmacao_agendamento"] = False` ← ESCRITA
- principal_router.py:3412 — `await salvar_contexto_temporario(user_id, ctx)` ← PERSISTE
- event_handler.py:929 — `await salvar_evento()` ← CRIA EVENTO

**T2 (segunda confirmação, SIMULTÂNEA):**
- principal_router.py:3366 — valida `aguardando_confirmacao_agendamento == True` ✅ (LEITURA STALE!)
  - T2 leu ANTES de T1 escrever False
  - Firestore retornou: True
- principal_router.py:3372-3391 — lê `dados_confirmacao_agendamento` ✅ (AINDA EXISTE!)
  - T2 leu ANTES de T1 deletar
  - Firestore retornou: dados completos
- event_handler.py:929 — `await salvar_evento()` ← CRIA OUTRO EVENTO!

### 3️⃣ Proteção Existente Hoje

✅ **Antiduplicidade por ID de evento:**
- event_service_async.py:102-103 — ID idempotente:
  ```python
  base_id = f"{cliente_id}_{profissional}_{data}_{hora_inicio}"
  event_id = base_id.replace(" ", "_").lower()
  # MESMO ID para ambas as confirmações!
  ```
- event_service_async.py:131-135 — detecta se existe:
  ```python
  existente = await buscar_dado_em_path(path)
  if existente:
      return "duplicado"
  ```

**PROTEÇÃO REAL:** Se T1 salvar primeiro, T2 encontra documento já existe.

⚠️ **MAS:** Sem transação em MemoriaTemporaria, CONTEXTO pode ficar inconsistente.

### 4️⃣ Risco Identificado

🔴 **P0 CRÍTICO — RMW em MemoriaTemporaria SEM Transação:**

```
T1: Lê MemoriaTemporaria/contexto — aguardando_confirmacao_agendamento = True
    Faz lógica (1ms)
    Escreve: aguardando_confirmacao_agendamento = False
    Persiste em Firestore

T2: Lê MemoriaTemporaria/contexto — aguardando_confirmacao_agendamento = True
    (ANTES de T1 escrever — read view stale)
    Faz lógica (1ms)
    Escreve: aguardando_confirmacao_agendamento = False
    Persiste em Firestore (overwrite com MESMO valor)
    Chama salvar_evento()
```

**Resultado do Evento:**
- event_service_async.py:131-135 protege (ID idempotente)
- T2 recebe `return "duplicado"` ← evento NOT criado

**Resultado do Contexto:**
- MemoriaTemporaria fica inconsistente se T1 e T2 tentam limpar simultaneamente
- Se T2 tenta deletar `dados_confirmacao_agendamento` ENQUANTO T1 limpa

**Risco Específico:**
- contexto_temporario.py:30-54 usa `DELETE_FIELD`
- Firestore DELETE_FIELD é atômico POR campo
- MAS se múltiplas requisições executam limpeza, podem sofrer race

### 5️⃣ Evidência no Log/Firestore

**Se PASSOU (evento protegido por ID):**
```
Log:
  [AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto  (T1)
  [AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto  (T2)  ← 2 LOGS
  ✅ Evento salvo para {dono} com ID test_user_019_bruna_2026-06-03_14:00
  ♻️ Evento já existe (idempotente). Não criando duplicado.  ← T2 DETECTADO

Firestore:
  Clientes/{dono}/Eventos/test_user_019_bruna_2026-06-03_14:00 — 1 doc (T1 salvou)
  
  MemoriaTemporaria/contexto:
    - aguardando_confirmacao_agendamento: <DELETE_FIELD ou FALSE?>
    - dados_confirmacao_agendamento: <DELETE_FIELD ou NULL?>
    (Pode estar inconsistente, depende de timing)
```

**Cenário crítico:**
```
Se T2 conseguir deletar ANTES de T1 completar limpeza:
  - MemoriaTemporaria fica VAZIO
  - Próximo acesso não encontra contexto (estado perdido)
  
Se T1 e T2 tentam DELETE_FIELD no MESMO campo:
  - Firestore permite (DELETE_FIELD é idempotente)
  - MAS contexto em T2 pode refletir view STALE
```

### 6️⃣ Classificação

🔴 **P0 BLOQUEANTE — RMW sem transação em MemoriaTemporaria**

Motivo:
- Firestore NÃO oferece lock entre leitura e escrita
- Sem transação, T2 lê dados STALE (que T1 está modificando)
- Ambas entram no fluxo de confirmação SIMULTANEAMENTE

Impacto (mesmo que evento seja protegido):
- Contexto pode ficar inconsistente
- Segunda requisição acredita ter sucesso mas evento já foi criado
- Estado de sessão corrompido

### 7️⃣ Proteção vs Risco

| Camada | Proteção | Risco |
|--------|----------|-------|
| **Evento (Firestore)** | ✅ ID idempotente | ✅ OK — T2 recebe "duplicado" |
| **Contexto (MemoriaTemporaria)** | ⚠️ DELETE_FIELD atômico POR campo | 🔴 RMW lê stale |
| **Lógica (principal_router.py:3366)** | ✅ Valida flag | ⚠️ Flag pode ser TRUE em ambas |
| **Firestore transação** | ❌ Não usa | 🔴 Race condition |

**Conclusão:** Cenário 12B **FALHA EM SIMULTÂNEA — P0 BLOQUEANTE — MAIS CRÍTICO QUE 12A**.

---

## 📊 Resumo: P0 Cenários 11, 12, 12B

| Cenário | Tipo | Proteção Evento | Proteção Contexto | Risco Crítico | Classificação |
|---------|------|-----------------|------------------|---------------|---------------|
| **11** | Seq duplicada (1 user) | ✅ ID idempotente | ✅ Flag FALSE | ⚠️ RMW se simultâneo | P0 IF simultâneo |
| **12** | Simultânea (2 users) | ✅ ID separado | ✅ Isolado | 🔴 verificar_conflito RMW | P0 BLOQUEANTE |
| **12B** | Simultânea (1 user) | ✅ ID idempotente | ⚠️ Leitura stale | 🔴 MemoriaTemporaria RMW | P0 BLOQUEANTE |

**Nenhum cenário P0 é "esperado". Todos são riscos reais no código.**


---

## 🧪 Cenário 12: Concorrência — Duplo Agendamento (P0 CRÍTICO ⚠️)

### Entrada Simulada
```
TEST_USER_017 e TEST_USER_018 SIMULTANEAMENTE:
  ambos: "escova com Bruna amanhã às 14"
  ambos: "sim"
```

### Fluxo Esperado (Ideal)
- Apenas UM evento criado em Firestore
- OU ambos rejeitados se código usa lock/transaction
- OU segundo encontra conflito e oferece alternativa

### Verificações Críticas
- [ ] Firestore contém EXATAMENTE 1 evento às 14h com Bruna
- [ ] Não há 2 eventos no mesmo horário
- [ ] Segundo usuário recebe mensagem de conflito (não silencioso)

### Se Falhar
- [ ] **MARCAR COMO P0**
- [ ] **Não tentar corrigir agora** (exige transaction ou lock)
- [ ] **Documentar em CLAUDE.md**

### Arquivo/Função
- `handlers/event_handler.py::add_evento_por_gpt()` — conflito
- `services/firebase_service_async.py::salvar_evento()` — persistência

### Estrutura de Teste
```python
# Pseudocódigo: executar paralelamente
async def test_concorrencia():
    user_17_task = enviar_confirmacao("TEST_USER_017", "sim")
    user_18_task = enviar_confirmacao("TEST_USER_018", "sim")
    
    await asyncio.gather(user_17_task, user_18_task)
    
    # Verificar Firestore
    eventos = buscar_eventos_firestore(
        dono_id="TEST_NEOEVE_20260602",
        data="2026-06-03",
        hora="14:00"
    )
    
    assert len(eventos) == 1, f"Esperado 1 evento, encontrados {len(eventos)}"
```

### Status
**[ ] NÃO TESTADO — CRÍTICO**

---

## 🧪 Cenário 12B: Confirmação Concorrente da Mesma Sessão (P0 CRÍTICO)

### Entrada Simulada
```
MESMO usuário.
MESMO draft.
Duas confirmações SIMULTÂNEAS.

TEST_USER_019:
  "escova com Bruna 2026-06-03 14:00"
  → contexto salvo (draft_agendamento, dados_confirmacao_agendamento)
  → SIMULTANEAMENTE: "sim" (msg 1) e "sim" (msg 2)
```

### Fluxo Esperado
- Primeira confirmação: cria evento, limpa contexto
- Segunda confirmação: encontra contexto vazio, não cria evento
- **Resultado final: 1 evento (não 2)**

### Por que é mais crítico que 12A
```
Cenário 12A (dois usuários):
- Contextos separados por user_id (mais fácil isolar)
- Race condition afeta apenas Firestore

Cenário 12B (mesmo usuário):
- Mesmo contexto em MemoriaTemporaria
- Race condition afeta leitura/escrita do MESMO documento
- Mais provável expor bugs de sincronização local
```

### Verificações Críticas
- [ ] MemoriaTemporaria aguardando_confirmacao_agendamento muda de true → false ATOMICAMENTE
- [ ] Segunda confirmação NÃO acessa dados_confirmacao_agendamento zerado
- [ ] Firestore contém EXATAMENTE 1 evento
- [ ] Nenhum evento parcial ou corrompido

### Implementação de Teste
```python
async def test_confirmacao_concorrente_mesmo_usuario():
    user_id = "TEST_USER_019"
    
    # Step 1: Enviar "escova com Bruna 2026-06-03 14:00"
    await telegram_send(user_id, "escova com Bruna 2026-06-03 14:00")
    
    # Aguardar pré-confirmação (bot responde)
    await asyncio.sleep(0.5)
    
    # Verificar contexto salvo
    ctx_antes = load_context(user_id)
    assert ctx_antes.get("aguardando_confirmacao_agendamento") == True
    assert ctx_antes.get("dados_confirmacao_agendamento") is not None
    
    # Step 2: Enviar "sim" DUAS VEZES SIMULTANEAMENTE
    task_sim_1 = telegram_send(user_id, "sim")
    task_sim_2 = telegram_send(user_id, "sim")
    
    await asyncio.gather(task_sim_1, task_sim_2)
    
    # Aguardar processamento
    await asyncio.sleep(1.0)
    
    # Step 3: Verificações
    # 3A: Contexto deve estar limpo
    ctx_depois = load_context(user_id)
    assert ctx_depois.get("aguardando_confirmacao_agendamento") == False, \
        "FALHA: aguardando_confirmacao_agendamento ainda True"
    assert ctx_depois.get("dados_confirmacao_agendamento") is None, \
        "FALHA: dados_confirmacao_agendamento não foi limpado"
    
    # 3B: Firestore deve ter EXATAMENTE 1 evento
    eventos = db.collection("Clientes").doc(TEST_DONO).collection("Eventos").where(
        "data", "==", "2026-06-03"
    ).where(
        "hora_inicio", "==", "14:00"
    ).where(
        "profissional", "==", "Bruna"
    ).get()
    
    assert len(eventos) == 1, \
        f"P0 CRÍTICO: {len(eventos)} eventos criados (esperado 1). " \
        f"Falha de sincronização em MemoriaTemporaria ou Firestore."
    
    # 3C: Evento deve estar completo (não parcial)
    evento = eventos[0]
    assert evento.get("confirmado") == True
    assert evento.get("status") == "confirmado"
    assert evento.get("profissional") == "Bruna"
```

### Arquivo/Função (onde falha provavelmente ocorre)
- `utils/contexto_temporario.py` — limpeza não-atômica
- `handlers/event_handler.py::add_evento_por_gpt()` — sem lock em salvar_evento()
- `principal_router.py` — sem validação de contexto zerado

### Se Falhar
- **BLOQUEIA PRODUÇÃO**
- Documenta em CLAUDE.md como P0 crítico
- Cria issue: "Concorrência em confirmação: duplo agendamento"
- Exige correção com transaction/lock ANTES de merge

### Status
**[ ] NÃO TESTADO — CRÍTICO (MAIS CRÍTICO QUE 12A)**

---

## 📊 Matriz de Testes

| Cenário | Status | Passou? | Falhas | Arquivo |
|---------|--------|---------|--------|---------|
| 1. Pergunta → Data → Confirmação | [ ] | [ ] | [ ] | |
| 2. Confirmações variadas | [ ] | [ ] | [ ] | |
| 3. Serviço + horário direto | [ ] | [ ] | [ ] | |
| 4. Com profissional específico | [ ] | [ ] | [ ] | |
| 5. Troca de profissional | [ ] | [ ] | [ ] | |
| 6. Horário ocupado | [ ] | [ ] | [ ] | |
| 7. Profissional ocupado | [ ] | [ ] | [ ] | |
| 8. Múltiplos profissionais | [ ] | [ ] | [ ] | |
| 9. Mensagens sociais | [ ] | [ ] | [ ] | |
| 10. Multi-cliente | [ ] | [ ] | [ ] | |
| 11. Confirmação duplicada | [ ] | [ ] | [ ] | |
| 12. **Concorrência 2 usuários (P0)** | [ ] | [ ] | [ ] | |
| 12B. **Concorrência mesmo usuário (P0+)** | [ ] | [ ] | [ ] | |

---

## 🔍 Verificações de Log em Cada Teste

### O que procurar em logs
```
✓ "[AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto" — evento sendo criado
✓ "✅ Evento salvo" — persistência bem-sucedida
✓ "aguardando_confirmacao_agendamento" transitions — rastreamento de estado
✓ Nenhum "UnboundLocalError" ou "NameError"
✓ Nenhuma duplicação de evento
```

### Firestore Checks
```
db.collection("Clientes")
  .doc("{dono_id}")
  .collection("Eventos")
  .where("data", "==", "2026-06-03")
  .where("hora_inicio", "==", "14:00")
  .where("profissional", "==", "Bruna")
  
→ Deve retornar EXATAMENTE 1 documento (não 0, não 2+)
```

---

## ⚠️ Riscos Identificados

| Risco | Severidade | Ação |
|-------|-----------|------|
| Cenário 12 — Concorrência sem lock | P0 | Testar, documentar, marcar como crítico |
| Vazamento de contexto entre users | P0 | Testar Cenário 10 |
| Duplicação de evento em confirmação dupla | P0 | Testar Cenário 11 |
| Race condition em limpeza de contexto | P1 | Monitorar logs |

---

## 🚀 Plano de Execução em 3 Fases

Executar testes em ordem para validar progressivamente o fluxo.

### Fase 1: Testes Básicos (Cenários 1-4)
**Duração:** 30-40 min | **Risco:** Baixo

**Objetivo:** Validar fluxo básico (pergunta → confirmação → evento)

#### Pré-Execução
- [ ] Ambiente de teste: Telegram + Firestore + Logs habilitados
- [ ] MemoriaTemporaria vazia para TEST_USER_*
- [ ] Nenhum evento em 2026-06-03

#### Execução
1. Executar Cenários 1-4 em sequência
2. Após cada cenário: verificar Firestore (1 evento criado)
3. Verificar MemoriaTemporaria: contexto limpado

#### Critério de Sucesso
- ✅ 4/4 cenários passaram
- ✅ Nenhuma duplicação
- ✅ Mensagens naturais (pré-confirmação + sucesso)
- ✅ Contexto limpado

#### Se Falhar
- Registrar cenário + log de erro
- Manter dados de teste para debug
- Passar para Fase 2 mesmo assim

---

### Fase 2: Testes de Robustez (Cenários 5-9)
**Duração:** 40-50 min | **Risco:** Médio

**Objetivo:** Validar alternativas, conflitos, proteção contra reinício

#### Pré-Condições (Setup Firestore)
```
Cenários 6-7 — criar evento para simular ocupação:
- Profissional: Bruna
- Data: 2026-06-03
- Hora: 14:00-14:40
- Serviço: escova
- Status: confirmado

Resultado esperado:
- Bruna ocupada em 14:00
- Carla disponível em 14:00
```

#### Execução
1. Preencher pré-condições
2. Executar Cenários 5-9 em ordem
3. Verificar alternativas oferecidas (SEM criar evento automaticamente)

#### Critério de Sucesso
- ✅ 5/5 cenários passaram
- ✅ Eventos criados apenas quando confirmado
- ✅ Nenhum evento automático em conflito
- ✅ Fluxo não reinicia com mensagens sociais

#### Se Falhar
- Marcar como bloqueante se houver criação automática ou reinício indevido

---

### Fase 3: Testes P0 Críticos (Cenários 10-12)
**Duração:** 30-40 min | **Risco:** P0 CRÍTICO

**Objetivo:** Testar isolamento, duplicação e concorrência

#### ⚠️ Avisos
- **Cenário 10:** Falha = vazamento de dados entre usuários
- **Cenário 11:** Falha = duplicação de evento
- **Cenário 12:** Falha = ESPERADO (sem lock/transaction) — apenas DOCUMENTAR

#### Cenário 12: Teste de Concorrência
```python
# Simular dois usuários SIMULTANEAMENTE
async def test_concorrencia():
    # USER_017
    task_17 = telegram_send(TEST_USER_017, "quero escova com Bruna 2026-06-03 14:00")
    await asyncio.sleep(0.05)
    task_17_confirm = telegram_send(TEST_USER_017, "sim")
    
    # USER_018 (paralelo)
    task_18 = telegram_send(TEST_USER_018, "quero escova com Bruna 2026-06-03 14:00")
    await asyncio.sleep(0.05)
    task_18_confirm = telegram_send(TEST_USER_018, "sim")
    
    # Aguardar ambas
    await asyncio.gather(task_17, task_17_confirm, task_18, task_18_confirm)
    
    # Verificar Firestore
    eventos = db.collection("Clientes").doc(TEST_DONO).collection("Eventos").where(
        "data", "==", "2026-06-03"
    ).where(
        "hora_inicio", "==", "14:00"
    ).where(
        "profissional", "==", "Bruna"
    ).get()
    
    # Esperado: EXATAMENTE 1 evento
    assert len(eventos) == 1, f"P0 CRÍTICO: {len(eventos)} eventos (esperado 1)"
```

#### Critério de Sucesso
- ✅ **Cenário 10:** Nenhuma mistura de contexto
- ✅ **Cenário 11:** Segundo "sim" não cria evento
- ✅ **Cenário 12:** Apenas 1 evento criado (ou falha esperada)

#### Se Cenário 12 Falhar
- [ ] **ESPERADO** — sem transaction/lock ainda
- [ ] Copiar evidência (2 eventos em Firestore)
- [ ] Documentar como P0 crítico
- [ ] Marcar como bloqueante para produção

---

## 📊 Matriz de Execução

| Fase | Cenários | Duração | Risco | Bloqueante |
|------|----------|---------|-------|-----------|
| 1 | 1-4 | 30-40m | Baixo | NÃO |
| 2 | 5-9 | 40-50m | Médio | NÃO |
| 3 | 10-12 | 30-40m | P0 | SIM se 10-11 falhar |

---

## 📝 Relatório Final (A Preencher)

```markdown
# Relatório de Testes de Regressão — Fluxo Agendamento

**Data de Execução:** [data]
**Testador:** [nome]
**Ambiente:** [dev/staging/prod]
**Resultado Geral:** [ ] PASSOU [ ] FALHOU [ ] COM OBSERVAÇÕES

## Cenários Testados: X/12

### Falhas Encontradas
- [ ] Nenhuma
- [X] Cenário 12 (Concorrência) — duplo agendamento observado
  - Arquivo: handlers/event_handler.py
  - Função: add_evento_por_gpt()
  - Causa: Sem transaction/lock em salvar_evento()
  - Ação: Marcar P0, documentar em CLAUDE.md

### Recomendações
- Implementar transaction em cenário 12
- Adicionar log de concorrência
- Testar novamente após implementação
```

---

## 🚀 Como Executar

### Opção 1: Manual (Telegram)
1. Conectar a conta de teste ao bot
2. Seguir roteiro de cada cenário
3. Verificar logs em tempo real
4. Verificar Firestore após cada teste

### Opção 2: Script Python (Recomendado)
```bash
python test_agendamento_regressao.py --cenarios 1,2,3,4,5,6,7,8,9,10,11,12
```

### Opção 3: Mock/Stub (Mais Rápido)
```bash
pytest tests/test_agendamento_mock.py -v
```

---

**Próximo Passo:** Executar testes e preencher relatório.  
**Sem alterações de código até aprovação do plano de teste.**
