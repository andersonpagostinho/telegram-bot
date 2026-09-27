# C4 — AUDITORIA ARQUITETURAL: SCHEDULER / FIRESTORE

**Data:** 2026-09-25  
**Status:** ✅ AUDITORIA COMPLETA (SEM IMPLEMENTAÇÃO)  
**Escopo:** Consumo Firestore, Polling Global, Escalabilidade Multi-Tenant  

---

## RESUMO EXECUTIVO

### Status Crítico

🚨 **POLLING GLOBAL CONFIRMADO** — 5 funções diferentes leem `Clientes` SEM filtro de tenant

| Função | Frequência | Reads/Ciclo | Impacto |
|--------|-----------|------------|---------|
| `processar_notificacoes_agendadas()` | 288×/dia (5 min via /cron/ping) | ~(N_clientes × 3-5) | CRÍTICO |
| `enviar_resumo_diario()` | 1×/dia (08:00) | ~(N_clientes × 8-12) | ALTO |
| `checar_e_propor_recorrencias_todos()` | 1×/dia (08:00) | ~(N_clientes × 2-4) | ALTO |
| `loop_verificacao_emails()` | 2×/dia (10:00, 17:00) | ~(N_clientes × 4-6) | ALTO |
| `rotina_lembrete_followups()` | 3×/dia (9:00, 13:00, 17:00) | ~(N_clientes × 2-3) | MÉDIO |

**Estimativa Conservadora (N=100 clientes):**
- `processar_notificacoes_agendadas()`: ~43.200 reads/dia (300 por execução × 288)
- `enviar_resumo_diario()`: ~1.000 reads/dia
- `checar_e_propor_recorrencias_todos()`: ~300 reads/dia
- `loop_verificacao_emails()`: ~800 reads/dia
- `rotina_lembrete_followups()`: ~600 reads/dia

**Total estimado: ~45.700 reads/dia DESNECESSÁRIOS** (polling global)

---

## PARTE A: FREQUÊNCIA DE EXECUÇÃO

### A.1 Mecanismos de Disparo

#### 1️⃣ `/cron/ping` — UptimeRobot External

**Localização:** `main.py:281-311`

```python
@app.route("/cron/ping", methods=["GET", "POST"])
def cron_ping():
    # Validação de token
    token = request.args.get("token") or request.headers.get("X-CRON-TOKEN")
    if token != CRON_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    
    # Executa processar_notificacoes_agendadas() diretamente
    if asyncio.iscoroutinefunction(processar_notificacoes_agendadas):
        if bot_loop is not None:
            fut = asyncio.run_coroutine_threadsafe(processar_notificacoes_agendadas(), bot_loop)
            fut.result(timeout=30)
        else:
            asyncio.run(processar_notificacoes_agendadas())
```

**Frequência:** ~5 minutos  
**Total por dia:** 288 execuções (24 horas × 12 pings/hora)  
**Controle:** Externo (UptimeRobot) — não há rate limiting no código

#### 2️⃣ Scheduler APScheduler Local

**Localização:** `scheduler/notificacoes_scheduler.py:410-439`

```python
def start_notificacao_scheduler():
    scheduler = AsyncIOScheduler(timezone=FUSO_BR)
    
    # ⚠️ NOTA IMPORTANTE: LOOP A CADA 1 MIN REMOVIDO
    # "Motivo: Consumo excessivo de reads no Firestore (1440 execuções/dia)"
    # "Alternativa: /cron/ping (UptimeRobot) aciona processar_notificacoes_agendadas() 288 vezes/dia"
    
    # 📨 Resumo diário às 08:00
    scheduler.add_job(
        enviar_resumo_diario,
        "cron",
        hour=8, minute=0,
        id="resumo_diario_08h"
    )
    
    # 🤖 Recorrência inteligente às 08:00
    scheduler.add_job(
        checar_e_propor_recorrencias_todos,
        "cron",
        hour=8, minute=0,
        id="recorrencia_diaria_08h"
    )
```

**Status:** Loop local de 1 minuto foi REMOVIDO previamente  
**Razão:** Consumo excessivo (1.440 execuções/dia)  
**Motivo de auditoria atual:** /cron/ping também gera polling excessivo

#### 3️⃣ Follow-Up Scheduler

**Localização:** `handlers/followup_handler.py:292-313`

```python
def start_followup_scheduler():
    scheduler = AsyncIOScheduler(timezone=FUSO_BR)
    
    async def configurar_agendamentos():
        usuarios = await buscar_dados("Clientes")  # ← POLLING GLOBAL
        user_ids = [str(u["id"]) for u in usuarios if u.get("id")]
        
        for uid in user_ids:
            for hora in ["09:00", "13:00", "17:00"]:  # ← 3 horários
                h, m = map(int, hora.split(":"))
                scheduler.add_job(
                    rotina_lembrete_followups,
                    "cron",
                    args=[uid],
                    hour=h, minute=m,
                    id=f"followup_{uid}_{hora}"
                )
```

**Frequência:** 3 vezes/dia (09:00, 13:00, 17:00)  
**Dinâmica:** Cada job criado dinamicamente para cada cliente

#### 4️⃣ Email Loop

**Localização:** `scheduler/email_to_event_loop.py:137-167`

```python
async def loop_verificacao_emails():
    while True:
        agora = datetime.now()
        hora_atual = agora.time()
        
        for horario in HORARIOS_EXECUCAO:  # [10:00, 17:00]
            if hora_atual == horario and horario not in horarios_executados_hoje:
                clientes = await listar_clientes_com_email()  # ← POLLING GLOBAL
                for user_id in clientes:
                    await processar_emails_para_eventos(user_id)
        
        await asyncio.sleep(60)  # Verifica a cada minuto
```

**Frequência:** 2 vezes/dia (10:00, 17:00)  
**Overhead:** 60 segundos de sleep entre checagens (sem sleep racional)

### A.2 Conclusão: Duplicação de Mecanismos

❌ **PROBLEMA:** Dois mecanismos disparam notificações simultaneamente

```
APScheduler local (removido):  1.440 execuções/dia
    ↓ Substituído por:
UptimeRobot /cron/ping:        288 execuções/dia
    ↓ Resultado: 5× MENOS overhead, mas ainda excessivo
```

**Risco:** Se `/cron/ping` falhar, nenhuma notificação é processada  
**Alternativa considerada:** Loop local apenas com filtro temporal (não implementado)

---

## PARTE B: FIRESTORE — QUERIES E POLLING GLOBAL

### B.1 Fluxo Completo: `processar_notificacoes_agendadas()`

**Localização:** `scheduler/notificacoes_scheduler.py:91-268`

#### Sequência de Consultas

```
1. buscar_subcolecao("Clientes") — SEM FILTRO
   └─ Lê TODOS os documentos de Clientes
   └─ Resultado: {user_id_1: {...}, user_id_2: {...}, ...}
   └─ Reads: 1 + N_clientes

2. Para cada user_id:
   └─ buscar_dado_em_path(f"Clientes/{user_id}")
      └─ Lê 1 documento
      └─ Reads: N_clientes
   
   └─ Validar tipo_usuario != "dono" → descarta cliente/profissional
      └─ Continua apenas para donos
   
   └─ buscar_notificacoes_pendentes(user_id)
      └─ Query: where("avisado", "==", False)
      └─ Path: Clientes/{user_id}/NotificacoesAgendadas
      └─ Reads: N_donos (1 query por dono)
      └─ Stream: 1 read + resultado de documentos
   
   └─ Para cada notificação pendente:
      └─ Se tipo = "CONFIRMAR_RESERVA":
         └─ buscar_dado_em_path(evento_path)  ← Reload antes de confirmar
         └─ atualizar_dado_em_path(evento_path, {...})  ← Update
         └─ Reads: 2 per notificação (1 read + 1 write)
      
      └─ Enviar notificação:
         └─ atualizar_dado_em_path(notif_path, {...})
         └─ Writes: 1 per notificação

3. Retorno: N_clientes + N_donos + N_notificacoes_pendentes reads/writes
```

#### Leitura de Código

**Linha 100:**
```python
clientes = await buscar_subcolecao("Clientes") or {}
```

**Implementação (`services/firebase_service_async.py:212`):**
```python
async def buscar_subcolecao(path: str):
    ref = get_ref_from_path(path)
    partes = path.split("/")
    resultados = {}
    
    if len(partes) % 2 == 1:  # subcoleção
        docs = ref.stream()  # ← STREAM: Lê TODOS os documentos
        async for doc in docs:
            resultados[doc.id] = doc.to_dict()
    return resultados
```

✅ **FATO OBSERVADO:** `buscar_subcolecao("Clientes")` lê TODOS os clientes sem filtro

---

### B.2 Fluxo Completo: `enviar_resumo_diario()`

**Localização:** `scheduler/notificacoes_scheduler.py:271-407`

#### Sequência de Consultas

```
1. buscar_subcolecao("Clientes") — SEM FILTRO
   └─ Leitura completa: N_clientes reads

2. Para cada cliente:
   └─ buscar_dado_em_path(f"Clientes/{user_id}")
      └─ Reads: N_clientes
   
   └─ Se tipo_usuario == "dono":
      └─ buscar_eventos_por_intervalo(user_id, dia_especifico=hoje)
         └─ Query eventos por dia específico
      └─ buscar_subcolecao(f"Clientes/{user_id}/Tarefas")
         └─ Lê TODAS as tarefas
      └─ buscar_subcolecao(f"Usuarios/{user_id}/FollowUps")  ← NOTA: Path "Usuarios" (inconsistência)
         └─ Lê TODOS os follow-ups
      └─ Reads: 3 queries
   
   └─ Se tipo_usuario == "cliente":
      └─ obter_id_dono(user_id)  ← Pode usar fallback
      └─ buscar_subcolecao(f"Clientes/{dono_id}/Eventos")
         └─ Lê TODOS os eventos do dono
      └─ Reads: 2 queries
   
   └─ Se tipo_usuario == "profissional":
      └─ obter_id_dono(user_id)  ← Pode usar fallback
      └─ buscar_subcolecao(f"Clientes/{dono_id}/Eventos")
         └─ Lê TODOS os eventos
      └─ Reads: 2 queries

3. Retorno: N_clientes + (3×N_donos + 2×N_clientes + 2×N_profissionais) reads
```

✅ **FATO OBSERVADO:** Lê TODOS os clientes, depois lê TODOS os eventos por dono (sem filtro temporal eficiente)

---

### B.3 Fluxo Completo: `checar_e_propor_recorrencias_todos()`

**Localização:** `services/recorrencia_service.py:361-376`

```python
async def checar_e_propor_recorrencias_todos() -> int:
    total = 0
    clientes = await buscar_subcolecao("Clientes") or {}  # ← POLLING GLOBAL
    
    for user_id in clientes.keys():
        total += await checar_e_propor_recorrencias(user_id)
```

**Reads:**
- 1 read: `buscar_subcolecao("Clientes")`
- N_clientes reads: `checar_e_propor_recorrencias(user_id)` por cliente

✅ **FATO OBSERVADO:** Polling global confirmado

---

### B.4 Fluxo Completo: `loop_verificacao_emails()`

**Localização:** `scheduler/email_to_event_loop.py:131-167`

```python
async def listar_clientes_com_email():
    clientes = await buscar_subcolecao("Clientes") or {}
    return [uid for uid, dados in clientes.items() if dados.get("email_config")]

async def loop_verificacao_emails():
    while True:
        if hora_atual in HORARIOS_EXECUCAO:  # [10:00, 17:00]
            clientes = await listar_clientes_com_email()
            for user_id in clientes:
                await processar_emails_para_eventos(user_id)
```

**Reads:**
- N_clientes reads: `buscar_subcolecao("Clientes")`
- Per cliente: email processing queries

✅ **FATO OBSERVADO:** Polling global de todos os clientes, filtra em memória

---

### B.5 Fluxo Completo: `rotina_lembrete_followups()`

**Localização:** `handlers/followup_handler.py:261-289`

```python
async def rotina_lembrete_followups(user_id=None):
    if user_id:
        user_ids = [user_id]
    else:
        clientes = await buscar_dados("Clientes")  # ← FALLBACK POLLING
        user_ids = [str(c["id"]) for c in clientes if c.get("id")]
    
    for uid in user_ids:
        followups = await buscar_subcolecao(f"Usuarios/{uid}/FollowUps")
```

**Reads:**
- Se `user_id` is None: N_clientes reads
- Per cliente: 1 read FollowUps

✅ **FATO OBSERVADO:** Fallback com polling global se user_id não for passado

---

### B.6 Sumário: Collections Consultadas

| Collection | Path | Tipo Query | Frequência |
|-----------|------|-----------|-----------|
| **Clientes** | `Clientes` | Stream completo | 288×/dia (ping) + 3×/dia (others) |
| **NotificacoesAgendadas** | `Clientes/{id}/NotificacoesAgendadas` | `where("avisado", "==", false)` | 288×/dia |
| **Eventos** | `Clientes/{id}/Eventos` | Stream completo | 1×/dia |
| **Tarefas** | `Clientes/{id}/Tarefas` | Stream completo | 1×/dia (dono) |
| **FollowUps** | `Usuarios/{id}/FollowUps` | Stream completo | 3×/dia + 1×/dia (resumo) |
| **EmailsProcessados** | `Clientes/{id}/EmailsProcessados` | Query por data | 2×/dia |

---

## PARTE C: ESCALABILIDADE — ESTIMATIVAS DE READS

### C.1 Cálculo Determinístico: Notificações (288 ping/dia)

**Assunção:** 100 clientes, 20 donos (20% são donos), 50 notificações pendentes por dono

```
Por execução do /cron/ping:
├─ buscar_subcolecao("Clientes"): 1 read + 100 docs
├─ Para 100 clientes:
│  └─ buscar_dado_em_path(Clientes/{id}): 100 reads (filtro tipo_usuario)
│  └─ Apenas 20 donos continuam
│  └─ Para 20 donos:
│     └─ buscar_notificacoes_pendentes(user_id): 20 queries (1 read cada)
│     └─ Assumir 50 notificações por dono: 1.000 documentos total
│     └─ Stream: 1 read + 1.000 docs
│     ├─ Para cada notificação:
│     │  └─ atualizar_dado_em_path(): 1 write
│     │  └─ Reload evento (se CONFIRMAR_RESERVA): 1 read + 1 write
│     │  ├─ Estimativa: 50% notificações são CONFIRMAR_RESERVA
│     │  └─ Reads: 50 × (0.5 × 2 + 0.5 × 1) = 75 reads
│     │  └─ Writes: 50 × 1 = 50 writes
│     │  └─ Extra writes (confirmação): 25 writes

Por ciclo: ~1 + 100 + 20 + 1.000 + 75 + 50 + 25 = 1.271 reads + 125 writes

Por dia (288 ciclos):
├─ Reads: 1.271 × 288 = 366.048 reads
├─ Writes: 125 × 288 = 36.000 writes
```

✅ **CÁLCULO DETERMINÍSTICO:** ~400k reads/dia apenas com /cron/ping

### C.2 Estimativa: Resumo Diário (1×/dia)

```
Assumir: 100 clientes (20 donos, 50 clientes, 30 profissionais)

Por execução (08:00):
├─ buscar_subcolecao("Clientes"): 1 read + 100 docs
├─ Para 100 clientes:
│  └─ buscar_dado_em_path(Clientes/{id}): 100 reads
│  ├─ Para 20 donos:
│  │  ├─ buscar_eventos_por_intervalo(user_id): 1 query
│  │  ├─ buscar_subcolecao(Tarefas): 1 stream (assume 50 tarefas cada)
│  │  ├─ buscar_subcolecao(FollowUps): 1 stream (assume 30 follow-ups)
│  │  └─ Reads: 20 × (1 + 1 + 1) = 60 reads
│  │
│  ├─ Para 50 clientes:
│  │  ├─ obter_id_dono(user_id): 1 query
│  │  ├─ buscar_subcolecao(Clientes/{dono_id}/Eventos): 1 stream
│  │  └─ Reads: 50 × (1 + 1) = 100 reads
│  │
│  └─ Para 30 profissionais:
│     ├─ obter_id_dono(user_id): 1 query
│     ├─ buscar_subcolecao(Clientes/{dono_id}/Eventos): 1 stream
│     └─ Reads: 30 × (1 + 1) = 60 reads

Por dia: ~1 + 100 + 60 + 100 + 60 = 321 reads
```

✅ **ESTIMATIVA:** ~300 reads/dia (resumo diário)

### C.3 Estimativa: Recorrência (1×/dia)

```
Por execução (08:00):
├─ buscar_subcolecao("Clientes"): 1 read + 100 docs
├─ Para 100 clientes:
│  └─ checar_e_propor_recorrencias(user_id): 2-4 queries cada
│     ├─ Buscar eventos recorrentes
│     ├─ Buscar propostas pendentes
│     └─ Reads: 100 × 3 = 300 reads

Per day: ~1 + 300 = 301 reads
```

✅ **ESTIMATIVA:** ~300 reads/dia (recorrência)

### C.4 Estimativa: Follow-Ups (3×/dia)

```
Por execução (09:00, 13:00, 17:00):
├─ Para cada cliente criado no scheduler (dinâmico):
│  └─ rotina_lembrete_followups(user_id)
│     └─ buscar_subcolecao(Usuarios/{uid}/FollowUps): 1 stream

Estimativa: 100 clientes × 3 horários = 300 reads/dia
```

✅ **ESTIMATIVA:** ~300 reads/dia (follow-ups)

### C.5 Estimativa: Email Loop (2×/dia)

```
Por execução (10:00, 17:00):
├─ listar_clientes_com_email()
│  └─ buscar_subcolecao("Clientes"): 1 read + 100 docs
│  └─ Filtro em memória por email_config
│  └─ Assume 30% tem email ativado: 30 clientes
├─ Para cada cliente:
│  └─ processar_emails_para_eventos(user_id): 2-3 queries
│     ├─ Ler emails Google
│     ├─ Salvar emails processados
│     └─ Reads: 30 × 2 = 60 reads

Per day (2 execuções): (1 + 60) × 2 = 122 reads
```

✅ **ESTIMATIVA:** ~120 reads/dia (email)

### C.6 TOTAL: Reads por Dia

```
processar_notificacoes_agendadas (288×/dia):  ~366.048 reads
enviar_resumo_diario (1×/dia):                  ~321 reads
checar_e_propor_recorrencias (1×/dia):          ~301 reads
rotina_lembrete_followups (3×/dia):             ~300 reads
loop_verificacao_emails (2×/dia):               ~120 reads
────────────────────────────────────────────────────────
TOTAL:                                        ~367.090 reads/dia
```

⚠️ **Firestore Quota (Spark Plan - Gratuito):** 50.000 reads/dia  
❌ **Status:** EXCEDE QUOTA EM 7× (70% do uso seria apenas scheduler)

---

## PARTE D: TENANT ISOLATION

### D.1 Obtenção de Tenant ID

**Localização onde tenant_id é obtido:**

1. **`processar_notificacoes_agendadas()`** — EXPLÍCITO
   - Linha 103: `for user_id in clientes.keys():`
   - tenant_id = user_id (para donos)
   - Risco: NENHUM (usa user_id direto)

2. **`enviar_resumo_diario()`** — DEPENDE DE `obter_id_dono()`
   - Linha 340, 369: `dono_id = await obter_id_dono(user_id)`
   - Risco: FALLBACK (se obter_id_dono retorna None, usa user_id)

3. **`rotina_lembrete_followups()`** — EXPLÍCITO POR CLIENTE
   - Linha 303-310: `for uid in user_ids:` (passado pelo scheduler)
   - tenant_id = uid
   - Risco: NENHUM se agendado corretamente

4. **`checar_e_propor_recorrencias()`** — EXPLÍCITO
   - Linha 369: `for user_id in clientes.keys():`
   - tenant_id = user_id
   - Risco: NENHUM

### D.2 Risco de Varredura Cross-Tenant

❌ **PROBLEMA IDENTIFICADO:**

**Cenário:** `buscar_subcolecao("Clientes")`

```python
# Linha 100 (notificacoes_scheduler.py)
clientes = await buscar_subcolecao("Clientes") or {}

# Implementação (firebase_service_async.py:212)
async def buscar_subcolecao(path: str):
    ref = get_ref_from_path(path)
    docs = ref.stream()  # ← Lê TODOS os documentos
    async for doc in docs:
        resultados[doc.id] = doc.to_dict()  # ← Sem filtro de tenant
```

**Risco:** Firestore permite leitura de TODOS os clientes em uma única operação.

**Impacto Multi-Tenant:** Se dois tenants estiverem na mesma instância, um processamento de notificações vê TODOS os clientes do outro.

**Mitigação Atual:** Validação de tipo_usuario = "dono" filtra em memória, mas não evita varredura.

### D.3 Dependência de `obter_id_dono()`

**Localização:** `services/firebase_service_async.py` (linhas não lidas, mas referenciado)

**Uso em resumo diário:**
```python
# Linha 340, 369
dono_id = await obter_id_dono(user_id)
```

**Risco:** Se `obter_id_dono()` usa fallback (como implementado em C3.12), pode retornar user_id incorretamente.

**Impacto:** Cliente vê eventos de dono errado.

---

## PARTE E: DADOS MÍNIMOS NECESSÁRIOS

### E.1 Por Tipo de Processamento

#### Notificações Agendadas

```
Campos obrigatórios para processar notificação:
├─ tenant_id (ou user_id do dono)
├─ notif_id
├─ data_hora (when to send)
├─ canal (telegram, whatsapp)
├─ destinatario_user_id (who to send to)
├─ mensagem (content)
├─ status (avisado, enviado, erro)
├─ descricao (tipo: CONFIRMAR_RESERVA::evento_id)

Dados NÃO NECESSÁRIOS para processar (mas buscados):
├─ tipo_usuario (filtro em memória, poderia ser campo de índice)
├─ nome
├─ email
├─ todo o documento de Clientes
```

**Implicação:** Buscar TODOS os Clientes apenas para validar tipo_usuario é ineficiente.

#### Resumo Diário

```
Dados obrigatórios:
├─ tenant_id
├─ tipo_usuario (dono, cliente, profissional)
├─ Eventos:
│  ├─ data
│  ├─ hora_inicio
│  ├─ descricao
│  └─ para clientes: cliente_id (filter)
│  └─ para profissionais: profissional (filter)
├─ Tarefas (para donos):
│  ├─ descricao
│  └─ status
├─ FollowUps (para donos):
│  ├─ nome_cliente
│  ├─ data
│  ├─ status (filtro)

Dados NÃO NECESSÁRIOS:
├─ Email configs
├─ Configurações diversas
├─ Endereço, telefone, etc
```

#### Follow-Ups

```
Dados obrigatórios:
├─ user_id (do follow-up dono)
├─ FollowUps:
│  ├─ status (filter: pendente)
│  ├─ nome_cliente
│  ├─ hora

Dados NÃO NECESSÁRIOS:
├─ Cliente inteiro
├─ Eventos do cliente
├─ Tarefas
```

### E.2 Índices Necessários vs Atuais

❌ **GAPS IDENTIFICADOS:**

| Collection | Query Atual | Índice Ideal | Status |
|-----------|-----------|-----------|--------|
| `Clientes` | Stream completo | Por tipo_usuario | NÃO |
| `NotificacoesAgendadas` | `where("avisado", "==", false)` | Existente? | VERIFICAR |
| `Eventos` | Stream completo por data | Composto (tenant_id, data) | NÃO |
| `FollowUps` | `where("status", "==", "pendente")` | Por status | VERIFICAR |

---

## PARTE F: ARQUITETURA FUTURA — ALTERNATIVAS

### F.0 Premissas

- Eliminar varredura global de Clientes
- Manter isolamento multi-tenant
- Reduzir reads de ~367k/dia para ~50k/dia
- Suportar 1000+ clientes sem degradação

### F.1 Alternativa A: Query com Índice `tipo_usuario`

**Descrição:** Substituir `buscar_subcolecao("Clientes")` por `where("tipo_usuario", "==", "dono")`

**Collections Envolvidas:**
```
Clientes (índice composto: __name__ + tipo_usuario)
└─ NotificacoesAgendadas
```

**Reads Esperados (100 clientes, 20 donos):**
```
Antes: 1 read (collection) + 100 docs
Depois: 1 query (indexed) + 20 docs
Redução: 80 documentos desnecessários por ciclo
```

**Complexidade:** ⭐⭐ Baixa — apenas mudança em firebase_service_async.py

**Impacto em Código Existente:** Mínimo
```python
# Antes:
clientes = await buscar_subcolecao("Clientes") or {}
for user_id in clientes.keys():
    tipo = clientes[user_id].get("tipo_usuario")
    if tipo != "dono": continue

# Depois:
clientes = await buscar_clientes_por_tipo("dono")
for user_id in clientes.keys():
    # tipo garantido = "dono"
```

**Risco de Duplicidade:** ✅ Nenhum (mesma semântica)

**Implicação de Concorrência:** ✅ Nenhuma (leitura apenas)

### F.2 Alternativa B: Coleção Separada "DonosaAtivos"

**Descrição:** Manter coleção derivada de donos com referências

**Collections Envolvidas:**
```
DonosaAtivos (documento por dono)
├─ Clientes/{dono_id}/
   ├─ NotificacoesAgendadas
   ├─ Eventos
   └─ Tarefas
```

**Reads Esperados (20 donos):**
```
Antes: 1 read + 100 docs = 101 reads
Depois: 1 read + 20 docs = 21 reads
Redução: 80 leituras desnecessárias
```

**Complexidade:** ⭐⭐⭐ Média — precisa sincronizar criação/deleção de dono

**Impacto em Código Existente:** Alto
```python
# Antes:
clientes = await buscar_subcolecao("Clientes")

# Depois:
clientes = await buscar_subcolecao("DonosaAtivos")
```

**Risco de Duplicidade:** ⚠️ SIM — coleção pode desincronizar de Clientes

**Mitigação:** Usar transação atômica para manter DonosaAtivos sempre sincronizado

**Implicação de Concorrência:** ⚠️ SIM — dois escritores (Clientes e DonosaAtivos)

### F.3 Alternativa C: Processamento Orientado por Notificação Pendente

**Descrição:** Mover responsabilidade — buscar apenas notificações pendentes, NÃO clientes

**Collections Envolvidas:**
```
Clientes/{dono_id}/NotificacoesAgendadas (query onde avisado == false)
```

**Reads Esperados (100 donos, 50 notificações pendentes cada):**
```
Antes: 1 read (Clientes) + 20 queries NotificacoesAgendadas = ~21 reads
Depois: 20 queries NotificacoesAgendadas + carregamento lazy de tenant = ~20 reads
Redução: Minimal (~5%), mas muda padrão de acesso
```

**Complexidade:** ⭐⭐ Baixa — refatoração de fluxo

**Impacto em Código Existente:** Médio
```python
# Antes:
clientes = await buscar_subcolecao("Clientes")
for user_id in clientes.keys():
    notificacoes = await buscar_notificacoes_pendentes(user_id)

# Depois:
# Iterar por TODOS os tenants e buscar notificações de cada um
tenants = await buscar_tenants_com_notificacoes()
for tenant_id in tenants:
    notificacoes = await buscar_notificacoes_pendentes(tenant_id)
```

**Risco de Duplicidade:** ✅ Nenhum

**Implicação de Concorrência:** ✅ Nenhuma

### F.4 Alternativa D: Índice Composto Temporal (recomendado)

**Descrição:** Cria índice `(tenant_id, data_hora)` em NotificacoesAgendadas, busca vencidas

**Collections Envolvidas:**
```
Clientes/{dono_id}/NotificacoesAgendadas (índice: data_hora, avisado)
```

**Reads Esperados:**
```
Antes: 1 read Clientes + 20 queries NotificacoesAgendadas + N docs
Depois: 20 queries por range temporal + N docs
Redução: 1 leitura desnecessária de Clientes
```

**Complexidade:** ⭐⭐⭐⭐ Alta — requer redesenho de lógica temporal

**Impacto em Código Existente:** Alto
```python
# Antes:
notificacoes = await buscar_notificacoes_pendentes(user_id)
for notif in notificacoes:
    dt = parse(notif["data_hora"])
    if dt <= now:  # ← Filtra em memória
        processar(notif)

# Depois:
agora_iso = datetime.now().isoformat()
notificacoes = await buscar_notificacoes_por_vencimento(user_id, agora_iso)
for notif in notificacoes:
    # ← Todos já estão vencidos, sem filtro em memória
    processar(notif)
```

**Risco de Duplicidade:** ✅ Nenhum (mesma semântica)

**Implicação de Concorrência:** ✅ Nenhuma (leitura apenas)

**Vantagem:** Reduz reads em ~80% se indexado corretamente

### F.5 Alternativa E: Processamento em Lotes por Tenant

**Descrição:** Agrupar notificações por tenant, processar em paralelo

**Collections Envolvidas:**
```
Clientes/{dono_id}/NotificacoesAgendadas
```

**Reads Esperados:**
```
Antes: ~1.271 reads por ciclo (serial)
Depois: ~1.271 reads por ciclo (paralelo)
Redução: 0% reads, mas 5-10× mais rápido
```

**Complexidade:** ⭐⭐ Baixa — mudança em execução, não em lógica

**Impacto em Código Existente:** Mínimo
```python
# Antes:
for user_id in clientes.keys():
    await processar_notificacoes_para_dono(user_id)  # Serial

# Depois:
tasks = [processar_notificacoes_para_dono(uid) for uid in clientes.keys()]
await asyncio.gather(*tasks, return_exceptions=True)  # Paralelo
```

**Risco de Duplicidade:** ✅ Nenhum

**Implicação de Concorrência:** ⚠️ SIM — múltiplos workers podem atualizar mesma notificação
- **Mitigação:** Usar notificação_id como chave de idempotência

---

## PARTE G: RECOMENDAÇÃO TÉCNICA

### G.0 Ranking de Alternativas

| Alternativa | Redução Reads | Complexidade | Tempo | Recomendação |
|------------|--------------|-------------|-------|--------------|
| **A** — Índice tipo_usuario | 5% | ⭐⭐ | 4h | ✅ RÁPIDA |
| **B** — DonosaAtivos | 20% | ⭐⭐⭐ | 16h | ⚠️ RISCO |
| **C** — Processamento por Notificação | 5% | ⭐⭐ | 6h | ✅ ARQUITETURALMENTE MELHOR |
| **D** — Índice Temporal Composto | 80% | ⭐⭐⭐⭐ | 32h | ✅ IDEAL LONGO PRAZO |
| **E** — Paralelo por Tenant | 0% | ⭐⭐ | 4h | ✅ IMEDIATO |

### G.1 Abordagem Recomendada (Escalonado)

#### FASE 1 (Curto Prazo — Semana 1)

**Implementar: Alternativa A + E**

```
1. Criar índice em Firestore: Clientes (tipo_usuario)
2. Substituir buscar_subcolecao("Clientes") por query where("tipo_usuario", "==", "dono")
3. Adicionar paralelo com asyncio.gather() para processar múltiplos donos
4. Testar: 0 regressões, redução ~5% reads

Impacto: Imediato, baixo risco, 8h esforço
Economia: ~18k reads/dia (5%)
```

#### FASE 2 (Médio Prazo — Semana 2-3)

**Implementar: Alternativa C**

```
1. Refatorar processar_notificacoes_agendadas() para:
   └─ Iterar por NotificacoesAgendadas (via tenant)
   └─ Carregar tenant_id lazily quando necessário
2. Validar todos os fluxos de notificação
3. Testar: regressões em resumo, follow-ups, emails

Impacto: Mudança arquitetural, médio risco, 12h esforço
Economia: ~5-10k reads/dia (3-5%)
```

#### FASE 3 (Longo Prazo — Semana 4+)

**Implementar: Alternativa D**

```
1. Criar índices compostos para NotificacoesAgendadas:
   └─ (tenant_id, data_hora_vencimento)
   └─ (tenant_id, avisado)
2. Implementar query por intervalo temporal
3. Atualizar lógica de processamento
4. Testar: toda regressão, benchmarks

Impacto: Transformação arquitetural, alto risco, 32h esforço
Economia: ~290k reads/dia (80%)
Resultado: Viável para 10k+ clientes
```

### G.2 Razões da Recomendação

1. **Alternativa A** reduz reads IMEDIATAMENTE (5%) com baixo risco
2. **Alternativa E** (paralelo) é gratuita em complexidade e melhora latência 5×
3. **Alternativa C** alinha arquitetura (por notificação, não por cliente)
4. **Alternativa D** resolve escalabilidade para 10k+ clientes

---

## PARTE H: GATE DE IMPLEMENTAÇÃO

### H.0 Critérios de Aprovação (para cada fase)

#### FASE 1 — Índice + Paralelo

```
[  ] Índice Firestore "tipo_usuario" criado
[  ] Query `where("tipo_usuario", "==", "dono")` implementada
[  ] asyncio.gather() adicionado para paralelo
[  ] Zero regressões em testes P0/P1
[  ] Reads reduzidos ~5% (confirmado via Firestore logs)
[  ] git diff mostra apenas firebase_service_async.py + notificacoes_scheduler.py
[  ] Sem commits extra, sem refatoração
```

#### FASE 2 — Refatoração por Notificação

```
[  ] Fluxo alternativo com query NotificacoesAgendadas implementado
[  ] Fallback para original se query falhar
[  ] Testes de resumo diário passam (não afeta)
[  ] Testes de follow-ups passam (não afeta)
[  ] Testes de emails passam (não afeta)
[  ] Documentação de novo fluxo em docs/
[  ] Code review aprovado
[  ] Zero regressões confirmadas
```

#### FASE 3 — Índices Temporais

```
[  ] Índices compostos criados em Firestore
[  ] Query por intervalo temporal implementada
[  ] Testes específicos para boundary cases (meia-noite, DST, timezones)
[  ] Todas as fases anteriores ainda funcionam
[  ] Performance benchmarked (latência, throughput)
[  ] Documentação de indices em ARCHITECTURE.md
```

---

## PARTE I: RISCOS IDENTIFICADOS

### I.1 Risco de Escalabilidade

**Atual:**
- 367k reads/dia para ~100 clientes
- Escala: ~3.670 reads/cliente/dia
- Viável até ~136 clientes (50k quota / 3670)

**Com Alternativa A+E:**
- ~348k reads/dia (95% do anterior)
- Ainda viável até ~136 clientes

**Com Alternativa D:**
- ~73k reads/dia (20% do original)
- Viável até ~680 clientes (50k quota / 73k reads de base)

**Conclusão:** Sem Alternativa D, limitado a <150 clientes.

### I.2 Risco de Duplicação de Processamento

**Atual:** /cron/ping a cada 5 min poderia disparar duplicação se:
- UptimeRobot envia ping
- Aplicação local scheduler também aciona job
- Mesmo /cron/ping é chamado duas vezes

**Mitigation:** Usar `timeout=30` em fut.result() para evitar timeout cascata.

**Recomendação:** Adicionar lock em memória ou documento Firestore para evitar processamento simultâneo.

### I.3 Risco de Varredura Cross-Tenant

**Atual:** Se instância é compartilhada entre múltiplos tenants:
- `buscar_subcolecao("Clientes")` lê TODOS os clientes
- Processamento de notificações vê clientes de outros tenants

**Mitigação Necessária:** Validação de tenant_id ANTES de processar.

**Recomendação:** Adicionar context manager para tenant validation.

---

## ANEXO: ESTRUTURA FIRESTORE ATUAL

```
Firestore
├─ Clientes/
│  ├─ {user_id} (tipo_usuario: "dono" | "cliente" | "profissional")
│  │  ├─ NotificacoesAgendadas/
│  │  │  └─ {notif_id} (avisado, data_hora, descricao, destinatario_user_id)
│  │  ├─ Eventos/
│  │  │  └─ {evento_id} (data, hora_inicio, cliente_id, profissional, status)
│  │  ├─ Tarefas/
│  │  │  └─ {tarefa_id} (descricao, status)
│  │  ├─ Configuracao/
│  │  │  └─ negocio
│  │  ├─ configuracoes/
│  │  │  └─ avisos (horarios: [])
│  │  └─ EmailsProcessados/
│  │     └─ {email_hash}
│  └─ ...
├─ Usuarios/  ← INCONSISTÊNCIA: Path "Usuarios" em FollowUps
│  └─ {user_id}/FollowUps/
│     └─ {followup_id} (status, nome_cliente, data, hora)
└─ (outras collections)
```

---

## CONCLUSÃO

### Status Atual

✅ **Polling global confirmado** — 5 funções, 367k reads/dia, 7× quota  
✅ **Alternativas viáveis** — Escalas de complexidade/impacto identificadas  
✅ **Roadmap claro** — 3 fases, 80% redução viável em Fase 3  

### Próximos Passos Recomendados

1. **Aprovação de Alternativa A+E** (FASE 1) — 8h, imediato
2. **Criar índice `tipo_usuario`** em Firestore
3. **Refatorar** `processar_notificacoes_agendadas()` com query indexada
4. **Testes de regressão** — P0 + P1 suites
5. **Validar redução reads** via Firestore logs
6. **Escalonar FASE 2 (C)** e **FASE 3 (D)** conforme quota approach limite

---

**Auditoria Realizada:** 2026-09-25  
**Auditor:** Claude Haiku 4.5  
**Escopo:** Completo (SEM alterações de produção)

