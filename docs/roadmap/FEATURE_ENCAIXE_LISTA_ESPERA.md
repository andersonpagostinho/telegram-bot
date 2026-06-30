# FEATURE: ENCAIXE / LISTA DE ESPERA ATIVA

**Status:** 📋 Roadmap (Documentação Futura)  
**Data Criação:** 2026-06-28  
**Prioridade:** P1 Alto  
**Fase Proposta:** F8 (pós-F5 WhatsApp Adapter ou P1.5)  
**Impacto Comercial:** Alto (reduz perda de vendas em salão cheio)  

---

## 1. STATUS ATUAL

### O que Existe Hoje

✅ **Detecção de Conflito**
- Motor detecta slot ocupado quando cliente solicita horário indisponível
- Localização: `services/agenda_service.py`, `services/event_service_async.py`

✅ **Sugestão de Alternativas**
- Sistema sugere horários alternativos para mesma profissional
- Sistema sugere profissional alternativa para mesmo horário
- Localização: `utils/formatters.py:gerar_sugestoes_de_horario()`

✅ **Cancelamento**
- Evento pode ser marcado como cancelado (soft delete)
- Função: `event_service_async.py:257:cancelar_evento()`
- Dados persistidos com status="cancelado"

### O que NÃO Existe

❌ **Registro Persistente de Interesse**
- Não há forma de cliente dizer "me avisa quando vagar"
- Não há coleção `ListaEspera`
- Cliente rejeita sugestão → interesse é perdido

❌ **Busca de Interessados ao Cancelar**
- Quando evento é cancelado, ninguém verifica quem queria aquele slot
- Slot libera mas cliente nunca fica sabendo
- Oportunidade de venda é perdida

❌ **Notificação Automática**
- Nenhum sistema dispara mensagem "Vagou o seu horário desejado"
- Cliente não tem mecanismo para entrar em fila de espera

❌ **Confirmação Rápida**
- Não há fluxo para cliente aceitar encaixe sem passar por fluxo completo
- Cada confirmação de encaixe seria interpretação GPT + motor completo

---

## 2. DEFINIÇÃO DA FEATURE

### Objetivo
Implementar sistema de **lista de espera ativa** que:
1. Oferece ao cliente opção de entrar em fila quando horário está ocupado
2. Monitora cancelamentos compatíveis
3. Notifica cliente em tempo real quando vaga abre
4. Permite confirmação rápida do encaixe

### Fluxo do Usuário (Visão)

**Cenário: Cliente quer corte com Bruna amanhã às 10h (ocupado)**

```
Cliente: "Quero corte com Bruna amanhã às 10h"
    ↓
NeoEve: "Desculpa, Bruna já tem agendamento nesse horário.
         Tenho outras opções:
         • Carla (profissional apta) às 10h
         • Bruna às 11h
         
         Ou quer que eu te aviso se esse horário vagar?"
    ↓
Cliente: "Avisa sim"
    ↓
NeoEve: "Certo! Qualquer coisa te mando mensagem. 
         [Registra interesse]"
    ↓
[Tempo passa]
    ↓
Outro cliente cancela:
"Oi, quero cancelar meu corte com Bruna amanhã às 10h"
    ↓
NeoEve: "Cancelado! Sua vaga foi liberada."
    ↓
[Sistema identifica waitlist]
    ↓
NeoEve envia para Cliente 1:
"Boa notícia! Vagou o horário de corte com Bruna amanhã às 10h.
 Quer confirmar?"
    ↓
Cliente 1: "Confirma"
    ↓
NeoEve: "Pronto! Seu horário está confirmado para amanhã às 10h com Bruna."
    ↓
Evento criado em Firestore
Lista de Espera marcada como "convertido"
```

---

## 3. ESTRUTURA PROPOSTA FIRESTORE

### Coleção: `ListaEspera`

**Caminho:** `Clientes/{tenant_id}/ListaEspera/{waitlist_id}`

```
Clientes/
├── {tenant_id}/
│   ├── Eventos/
│   │   ├── evt_001
│   │   ├── evt_002
│   │   └── ...
│   ├── Sessoes/
│   │   └── ...
│   ├── ListaEspera/          ← NOVA COLEÇÃO
│   │   ├── wait_001
│   │   ├── wait_002
│   │   └── ...
```

### Schema de Documento

```json
{
  "waitlist_id": "wait_20260628_001",
  
  "tenant_id": "dono_123",
  
  "cliente": {
    "actor_id": "whatsapp:1234567890",
    "cliente_id": "cliente_456",
    "cliente_nome": "João"
  },
  
  "servico_desejado": {
    "servico": "corte",
    "profissional_preferido": "Bruna",
    "data_desejada": "2026-06-29",
    "hora_desejada": "10:00",
    "duracao_minutos": 30
  },
  
  "status": "ativo",
  "status_enums": ["ativo", "notificado", "confirmado", "expirado", "cancelado"],
  
  "auditoria": {
    "criado_em": "2026-06-28T15:30:00-03:00",
    "expira_em": "2026-06-30T23:59:59-03:00",
    "ultima_notificacao_em": null,
    "tentativas_notificacao": 0,
    "confirmado_em": null
  },
  
  "referencia": {
    "origem_evento_conflitante_id": "evt_bruna_20260629_100000",
    "evento_criado_apos_encaixe": null
  },
  
  "notificacao": {
    "canal": "whatsapp",
    "enviada": false
  }
}
```

### Índices Necessários

```
ListaEspera (composite):
  - tenant_id (Ascending)
  - status (Ascending)
  - servico_desejado.data_desejada (Ascending)
  - criado_em (Ascending)

Motivo: Buscar "próximo cliente na fila" rapidamente
Query: WHERE tenant_id=X AND servico=Y AND data=Z AND status='ativo' 
       ORDER BY criado_em ASC LIMIT 1
```

---

## 4. FLUXO PROPOSTO

### Fase A: Conflito Detectado

```python
# services/agenda_service.py (modificação futura)

def verificar_conflito_agenda(tenant_id, prof, data, hora_inicio):
    conflito = buscar_conflito_firestore()
    
    if conflito:
        # 1. Buscar sugestões (já existe)
        sugestoes = gerar_sugestoes_de_horario(prof, data, duracao)
        
        # 2. NOVO: Oferecer entrada em lista de espera
        ofercer_waitlist(
            cliente_id=cliente_id,
            servico=servico,
            profissional=prof,
            data=data,
            hora=hora_inicio,
            duracao=duracao
        )
        
        return {
            "conflito": True,
            "sugestoes": sugestoes,
            "pode_entrar_waitlist": True
        }
```

### Fase B: Cliente Aceita Entrar na Lista

```python
# handlers/event_handler.py (novo handler)

async def aceitar_lista_espera(
    user_id: str,
    servico: str,
    profissional: str,
    data: str,
    hora: str,
    duracao: int
):
    """
    Cliente aceitou "me avisa quando vagar"
    """
    
    waitlist_id = gerar_uuid_waitlist()
    
    documento = {
        "waitlist_id": waitlist_id,
        "tenant_id": obter_id_dono(user_id),
        "cliente": {
            "actor_id": f"whatsapp:{user_id}",
            "cliente_id": user_id,
            "cliente_nome": contexto.get("cliente_nome")
        },
        "servico_desejado": {
            "servico": servico,
            "profissional_preferido": profissional,
            "data_desejada": data,
            "hora_desejada": hora,
            "duracao_minutos": duracao
        },
        "status": "ativo",
        "criado_em": datetime.now(tz).isoformat(),
        "expira_em": (datetime.now(tz) + timedelta(days=2)).isoformat()
    }
    
    # Salvar em Firestore
    path = f"Clientes/{tenant_id}/ListaEspera/{waitlist_id}"
    await salvar_dado_em_path(path, documento)
    
    # Log
    logger.info(f"[WAITLIST] cliente={user_id} entrou na espera para {profissional} {data} {hora}")
    
    # Mensagem
    return "Certo! Te aviso assim que esse horário vagar."
```

### Fase C: Evento é Cancelado

```python
# services/event_service_async.py (modificação futura)

async def cancelar_evento(user_id, event_id):
    
    # 1. Executar cancelamento (já existe)
    evento = await buscar_dado_em_path(f"Clientes/{tenant_id}/Eventos/{event_id}")
    await atualizar_dado_em_path(path, {"status": "cancelado", ...})
    
    # 2. NOVO: Buscar clientes interessados
    tenant_id = obter_id_dono(user_id)
    profissional = evento.get("profissional")
    data = evento.get("data")
    hora = evento.get("hora_inicio")
    servico = evento.get("servico")
    
    waitlist_ativos = await buscar_subcolecao(
        f"Clientes/{tenant_id}/ListaEspera",
        filters=[
            ("status", "==", "ativo"),
            ("servico_desejado.profissional_preferido", "==", profissional),
            ("servico_desejado.data_desejada", "==", data),
            ("servico_desejado.hora_desejada", "==", hora)
        ]
    )
    
    # 3. Chamar sistema de notificação
    if waitlist_ativos:
        for waitlist_doc in waitlist_ativos:
            await notificar_vaga_aberta(waitlist_doc)
```

### Fase D: Notificação

```python
# services/notificacao_service.py (modificação futura)

async def notificar_vaga_aberta(waitlist_doc):
    
    cliente_id = waitlist_doc["cliente"]["cliente_id"]
    actor_id = waitlist_doc["cliente"]["actor_id"]
    
    # 1. Validar pré-requisitos
    # - cliente não tem outro evento em conflito?
    # - waitlist ainda ativo?
    
    cliente_eventos = await buscar_eventos_cliente(cliente_id)
    if cliente_eventos_conflita_com(cliente_eventos, waitlist_doc):
        logger.info(f"[WAITLIST] cliente já tem agendamento conflitante, não notificando")
        return False
    
    # 2. Enviar mensagem
    mensagem = f"""Boa notícia! 🎉

Vagou o horário de {waitlist_doc["servico_desejado"]["servico"]} 
com {waitlist_doc["servico_desejado"]["profissional_preferido"]} 
em {waitlist_doc["servico_desejado"]["data_desejada"]} às {waitlist_doc["servico_desejado"]["hora_desejada"]}.

Quer confirmar esse horário?"""
    
    await enviar_mensagem(actor_id, mensagem)
    
    # 3. Marcar como notificado
    waitlist_id = waitlist_doc["waitlist_id"]
    path = f"Clientes/{waitlist_doc['tenant_id']}/ListaEspera/{waitlist_id}"
    
    await atualizar_dado_em_path(path, {
        "status": "notificado",
        "ultima_notificacao_em": datetime.now(tz).isoformat(),
        "tentativas_notificacao": waitlist_doc.get("tentativas_notificacao", 0) + 1
    })
    
    logger.info(f"[WAITLIST] cliente {cliente_id} notificado sobre vaga")
    
    # 4. Definir timeout para expiração
    # Se cliente não responder em 30 min, marcar como expirado
    # (future: usar Cloud Tasks ou scheduler)
```

### Fase E: Cliente Confirma Encaixe

```python
# handlers/event_handler.py (novo handler)

async def confirmar_encaixe_lista_espera(
    user_id: str,
    waitlist_id: str
):
    """
    Cliente respondeu "confirma" após receber notificação de vaga
    """
    
    tenant_id = obter_id_dono(user_id)
    path_waitlist = f"Clientes/{tenant_id}/ListaEspera/{waitlist_id}"
    
    # 1. Buscar documento de waitlist
    waitlist_doc = await buscar_dado_em_path(path_waitlist)
    
    if not waitlist_doc or waitlist_doc.get("status") != "notificado":
        return "Desculpa, essa vaga expirou. Tenta novamente?"
    
    # 2. Revalidar disponibilidade dentro do lock
    # (CRÍTICO: verificar novamente antes de criar)
    
    prof = waitlist_doc["servico_desejado"]["profissional_preferido"]
    data = waitlist_doc["servico_desejado"]["data_desejada"]
    hora = waitlist_doc["servico_desejado"]["hora_desejada"]
    duracao = waitlist_doc["servico_desejado"]["duracao_minutos"]
    
    # Usar transaction para garantir atomicidade
    conflito_agora = await verificar_conflito_com_lock(
        tenant_id, prof, data, hora, duracao
    )
    
    if conflito_agora:
        await atualizar_dado_em_path(path_waitlist, {"status": "expirado"})
        return "Desculpa, alguém confirmou esse horário nesse meio tempo. Quer outra sugestão?"
    
    # 3. Criar evento (motor determinístico)
    evento_id = gerar_uuid_evento()
    evento = {
        "id": evento_id,
        "cliente_id": user_id,
        "cliente_nome": waitlist_doc["cliente"]["cliente_nome"],
        "servico": waitlist_doc["servico_desejado"]["servico"],
        "profissional": prof,
        "data": data,
        "hora_inicio": hora,
        "hora_fim": calcular_hora_fim(hora, duracao),
        "duracao": duracao,
        "confirmado": True,
        "status": "confirmado",
        "origem": "encaixe_lista_espera",
        "waitlist_id_origem": waitlist_id,
        "criado_em": datetime.now(tz).isoformat()
    }
    
    path_evento = f"Clientes/{tenant_id}/Eventos/{evento_id}"
    await salvar_evento(user_id, evento)
    
    # 4. Marcar waitlist como convertido
    await atualizar_dado_em_path(path_waitlist, {
        "status": "confirmado",
        "confirmado_em": datetime.now(tz).isoformat(),
        "evento_criado_apos_encaixe": evento_id
    })
    
    # 5. Resposta ao cliente
    return f"Pronto! Seu horário de {evento['servico']} com {prof} está confirmado para {data} às {hora}."
```

### Fase F: Cliente Recusa ou Expira

```python
# handlers/event_handler.py (novo handler)

async def rejeitar_encaixe_lista_espera(
    user_id: str,
    waitlist_id: str
):
    """
    Cliente respondeu "não" ou expirou o tempo
    """
    
    tenant_id = obter_id_dono(user_id)
    path_waitlist = f"Clientes/{tenant_id}/ListaEspera/{waitlist_id}"
    
    await atualizar_dado_em_path(path_waitlist, {
        "status": "cancelado",
        "cancelado_em": datetime.now(tz).isoformat()
    })
    
    logger.info(f"[WAITLIST] cliente rejeitou encaixe {waitlist_id}")
    
    # Opcionalmente: chamar próximo cliente da fila
    # (future: sistema de fila em cascata)
```

---

## 5. REGRAS CRÍTICAS

### 5.1 Nunca Reservar Slot por Estar na Lista

❌ **PROIBIDO:**
```python
# Não fazer isso
if cliente in waitlist:
    marcar_slot_reservado()  # NUNCA!
```

✅ **CORRETO:**
```python
# Waitlist é apenas "interesse", não reserva nada
# Slot só é reservado quando evento é CRIADO
if cliente_confirma_encaixe:
    criar_evento_com_lock()  # Cria com lock dentro de transação
```

**Razão:** Outro cliente pode agendar normalmente enquanto primeiro está considerando.

### 5.2 Sempre Revalidar Dentro do Lock

❌ **ERRADO:**
```
1. Buscar waitlist (disponível)
2. Enviar notificação
3. Cliente confirma após 30 min
4. Criar evento sem verificar novamente
↓
Pode ter sido ocupado nesse meio tempo!
```

✅ **CORRETO:**
```
1. Buscar waitlist
2. Enviar notificação
3. Cliente confirma
4. Verificar NOVAMENTE disponibilidade
5. Criar evento com lock ATÔMICO
6. Confirmar sucesso
```

### 5.3 Não Notificar Se Já Tem Agendamento Conflitante

❌ **ERRADO:**
```
Cliente tem: corte com Bruna amanhã às 11h
Waitlist: corte com Bruna amanhã às 10h
Vaga abre: enviar notificação
↓
Cliente fica confuso ou precisa cancelar outro
```

✅ **CORRETO:**
```
Antes de enviar notificação:
  IF cliente_tem_evento_conflitante(data, duracao):
    marcar_waitlist_como_expirado()
    NOT enviar notificação
```

### 5.4 Nunca Misturar Tenants

✅ **SEMPRE:**
```
WHERE tenant_id = obter_id_dono(user_id)
AND servico = X
AND profissional = Y
```

Razão: Multi-tenant isolation crítico.

### 5.5 Não Chamar GPT para Prioridade

❌ **PROIBIDO:**
```python
# Não faça isso
gpt_service.choose_priority_from_waitlist(clientes)
```

✅ **CORRETO:**
```python
# Determinístico: ordem de chegada
next_cliente = waitlist_collection.order_by("criado_em", "asc").first()
```

**Razão:** Consistência, auditoria, previsibilidade.

### 5.6 Prioridade da Fila

**Padrão:** FIFO (First In, First Out)

```sql
WHERE status='ativo'
  AND servico=X
  AND profissional=Y
  AND data=Z
ORDER BY criado_em ASC
LIMIT 1
```

**Alternativa futura:** Regra configurável por tenant
- Idade do cliente
- Frequência histórica
- Valor do serviço
- (Mas sempre determinística, não aleatória)

---

## 6. TESTES FUTUROS SUGERIDOS

### F8 — ENCAIXE / LISTA DE ESPERA ATIVA

**Fase:** Após F5 WhatsApp ou P1.5 (retenção)  
**Suites:** 8 cenários + regressão

---

### F8-1: Cliente Entra em Lista Após Conflito

**Cenário:** Cliente solicita horário ocupado, aceita entrar em lista

**Setup:**
```
Profissional: Bruna (disponível)
Data: 2026-06-29
Hora: 10:00
Serviço: corte (30 min)
Evento existente: outro cliente já tem 09:00-10:30
```

**Fluxo:**
1. Cliente 1: "Quero corte com Bruna em 29/06 às 10h"
2. Motor: Detecta conflito (overlap 09:00-10:30)
3. NeoEve: "Esse horário está ocupado. Tenho Carla às 10h ou Bruna às 11h. Quer entrar em lista de espera?"
4. Cliente 1: "Entra na lista"
5. NeoEve: "Certo, te aviso."

**Validações:**
- ✅ Documento criado em `ListaEspera`
- ✅ Status = "ativo"
- ✅ Campo `servico_desejado` preenchido corretamente
- ✅ Campo `criado_em` = hoje
- ✅ Campo `expira_em` = hoje + 2 dias
- ✅ Session de cliente não foi alterada (volta a idle ou mantém leve)

**Resultado esperado:** PASS (1 waitlist criado)

---

### F8-2: Cancelamento Abre Vaga e Notifica Cliente Correto

**Cenário:** Outro cliente cancela → waitlist é notificado

**Setup:**
- Estado anterior: Cliente 1 em lista de espera para Bruna 29/06 10h
- Evento existente de Cliente 2: Bruna 29/06 09:00-10:30

**Fluxo:**
1. Cliente 2: "Cancela meu agendamento com Bruna"
2. Motor: Cancela evento, marca status="cancelado"
3. Motor: Busca `ListaEspera` WHERE profissional=Bruna AND data=29/06 AND status=ativo
4. Encontra Cliente 1
5. NeoEve (para Cliente 1): "Boa notícia! Vagou seu horário de corte com Bruna em 29/06 às 10h. Quer confirmar?"

**Validações:**
- ✅ Evento de Cliente 2 marcado como cancelado
- ✅ Waitlist de Cliente 1 encontrado
- ✅ Status muda para "notificado"
- ✅ Campo `ultima_notificacao_em` é preenchido
- ✅ Campo `tentativas_notificacao` = 1
- ✅ Mensagem enviada para Cliente 1
- ✅ Nenhum outro cliente notificado (tenant isolation)

**Resultado esperado:** PASS (notificação correta)

---

### F8-3: Cliente Confirma Encaixe e Evento é Criado

**Cenário:** Cliente responde "confirma" após notificação

**Setup:**
- Estado anterior: Waitlist de Cliente 1 com status="notificado"
- Vaga está disponível (não foi ocupada por outro)

**Fluxo:**
1. Cliente 1: "Confirma"
2. Motor: Revalida disponibilidade (double-check)
3. Motor: Cria evento com lock
4. Motor: Atualiza waitlist com status="confirmado"
5. NeoEve: "Pronto! Seu horário está confirmado."

**Validações:**
- ✅ Evento criado com todos os campos
- ✅ Evento tem `origem="encaixe_lista_espera"`
- ✅ Evento tem `waitlist_id_origem=wait_xxx`
- ✅ Evento tem status="confirmado"
- ✅ Firestore mostra evento persistido
- ✅ Waitlist status="confirmado"
- ✅ Waitlist campo `evento_criado_apos_encaixe` = evento_id
- ✅ AgendaLock criado para Bruna 29/06 10:00

**Resultado esperado:** PASS (evento criado atomicamente)

---

### F8-4: Dois Clientes em Espera, Apenas Primeiro Recebe Prioridade

**Cenário:** Dois clientes querem mesmo slot, primeiro criado tem prioridade

**Setup:**
```
Cliente 1: entra na lista em 2026-06-28 15:00
Cliente 2: entra na lista em 2026-06-28 15:05
(diferença 5 minutos)

Ambos: corte com Bruna em 29/06 às 10h
```

**Fluxo:**
1. Evento de Bruna é cancelado
2. Motor: Busca waitlist WHERE servico=corte AND profissional=Bruna AND data=29/06
3. Encontra 2 clientes
4. Motor: ORDER BY criado_em ASC → Cliente 1 é primeiro
5. Notifica apenas Cliente 1
6. Marcar Cliente 2 como "aguardando_fila" ou deixa em "ativo"

**Validações:**
- ✅ Cliente 1 recebe notificação
- ✅ Cliente 2 NÃO recebe notificação (ainda)
- ✅ Ordem de chegada respeitada

**Resultado esperado:** PASS (FIFO respeitado)

---

### F8-5: Primeiro Não Responde, Segundo é Chamado

**Cenário:** Cliente 1 não responde, timeout expira, chamar Cliente 2

**Setup:**
- Cliente 1 notificado há 45 minutos, sem resposta
- Cliente 2 aguardando em fila
- Timeout configurado: 30 minutos

**Fluxo:**
1. Cloud Task (ou scheduler): "Verificar waitlist expirados"
2. Encontra Cliente 1 com status="notificado" e criado_em > 30 min atrás
3. Marcar Cliente 1 como "expirado"
4. Buscar próximo: Cliente 2
5. Notificar Cliente 2

**Validações:**
- ✅ Cliente 1 marcado como "expirado"
- ✅ Cliente 2 recebe notificação
- ✅ Cliente 2 status muda para "notificado"

**Resultado esperado:** PASS (cascata de fila funciona)

---

### F8-6: Cliente em Espera Já Marcou Outro Horário, Não Notificar

**Cenário:** Depois de entrar na lista, cliente marca horário diferente → não notificar sobre encaixe

**Setup:**
- Cliente em espera: corte com Bruna 29/06 10h
- Cliente marca novo evento: hidratação com Amanda 29/06 10h (conflita com waitlist)

**Fluxo:**
1. Vaga de Bruna 29/06 10h abre
2. Motor: Busca cliente na waitlist
3. Antes de notificar: verifica eventos do cliente
4. Encontra evento de hidratação 29/06 10h com Amanda
5. NÃO envia notificação

**Validações:**
- ✅ Waitlist não é notificado
- ✅ Status permanece "ativo" (ou marcado como "conflito_posterior")
- ✅ Sem mensagem duplicada

**Resultado esperado:** PASS (detecção de conflito posterior)

---

### F8-7: Cancelamento em Outro Tenant Não Notifica Cliente Errado

**Cenário:** Tenant A cancela evento → não notifica cliente de Tenant B

**Setup:**
```
Tenant A: profissional Bruna, cliente espera por corte 29/06 10h
Tenant B: profissional Bruna (mesma pessoa, multi-tenant), cliente espera por corte 29/06 10h

Cancelamento em Tenant A
```

**Fluxo:**
1. Evento de Tenant A é cancelado
2. Motor busca: `ListaEspera WHERE tenant_id=Tenant_A AND ...`
3. Notifica apenas Tenant A
4. Tenant B não é tocado

**Validações:**
- ✅ Tenant A cliente notificado
- ✅ Tenant B cliente NÃO notificado
- ✅ Queries incluem WHERE tenant_id

**Resultado esperado:** PASS (isolamento multi-tenant)

---

### F8-8: Race Condition - Dois Clientes Confirmam Vaga ao Mesmo Tempo

**Cenário:** Dois clientes em fila confirmam encaixe simultaneamente

**Setup:**
- Cliente 1 e Cliente 2 ambos em status="notificado" para mesma vaga
- (Cenário edge: sistema notificou ambos por erro, ou Cliente 2 chegou depois)

**Fluxo:**
1. Cliente 1: "Confirma"
2. Cliente 2: "Confirma" (simultâneos)
3. Motor: Cria evento para Cliente 1 com lock
4. Motor: Tenta criar evento para Cliente 2 com lock
5. Lock falha para Cliente 2 (slot já ocupado)

**Validações:**
- ✅ Evento criado para Cliente 1
- ✅ Cliente 2 recebe: "Desculpa, alguém confirmou nesse meio tempo"
- ✅ Waitlist de Cliente 2 marcado como "expirado"
- ✅ Nenhuma corrupção de dados

**Resultado esperado:** PASS (transação protege integridade)

---

## 7. REGRESSÃO OBRIGATÓRIA

Ao implementar F8 no futuro:

- ✅ P0 Regressão: 174/174 PASS (sem alteração em código crítico)
- ✅ P1 E2E: 42/42 PASS (sem impacto em onboarding/identidade)
- ✅ F1 Baseline: 8/8 PASS (estado do lead)
- ✅ F2 Robustez: 39/39 PASS (sem quebra em input/session/agenda)
- ✅ F4 E2E Real: 8/8 PASS (sem impacto em fluxo de 7 clientes)
- ✅ F8 Específico: 8/8 PASS (novos cenários)

**Total esperado:** 254/254 PASS

---

## 8. CLASSIFICAÇÃO

### Prioridade
- **P1 Alto** — Valor comercial alto (salão cheio = perda de vendas)

### Fase
- **F8** (Proposto pós-F5 WhatsApp ou como P1.5 — Retenção)
- **Não bloqueia F5** (WhatsApp Adapter funciona sem waitlist)

### Impacto Comercial
- 🔴 **Alto:** Aumenta conversão quando salão está cheio
- 🔴 **Reduz:** "Não consegui agendar" → cliente volta depois
- 🔴 **Melhora:** Taxa de confirmação do agendamento

### Complexidade
- 🟡 **Média:** 
  - Nova coleção Firestore
  - Integração com cancelamento
  - Notificação automática
  - Double-check de disponibilidade (transação)

### Risco
- 🟡 **Médio:**
  - Race condition se não usar lock
  - Notificação duplicada se não sincronizado
  - Cliente recebe oferta expirada
  - Mitigação: regras críticas seção 5

### Timeframe
- **Estimado:** 2-3 sprints (após F5 estabilizar)

### Dependências
- ✅ F5 WhatsApp Adapter (para enviar mensagens reais)
- ✅ Cloud Tasks ou Scheduler (para timeout de expiração)
- ✅ Transações Firestore (para atomicidade)

---

## 9. PRÓXIMOS PASSOS

### Quando Implementar (Decisão Futura)

1. **Fase 1:** Validar que F5 WhatsApp está estável (sem regressões)
2. **Fase 2:** Feedback de vendas — confirmado que clientes querem isso?
3. **Fase 3:** Design detalhado (UX de mensagem, timeouts, fallbacks)
4. **Fase 4:** Implementação sprint-by-sprint (Fase A, B, C, D separados)
5. **Fase 5:** F8 completo com 8 cenários validados

### Documentação de Preparação

Não criar ainda. Apenas quando iniciar implementação:
- [ ] `DESIGN_ENCAIXE_LISTA_ESPERA.md` (arquitetura detalhada)
- [ ] `PLANO_IMPLEMENTACAO_F8.md` (timeline, tasks)
- [ ] `TESTES_F8_ENCAIXE.md` (specs de testes)

### Código de Preparação

Não criar ainda. O roadmap é suficiente para sinalizar direção técnica.

---

## 10. REFERÊNCIAS

**Documentos relacionados:**
- `docs/roadmap/` — Outras features roadmap
- `docs/auditorias/BASELINE_PRE_WHATSAPP_54_PASS.md` — Estado pré-WhatsApp
- `services/event_service_async.py:257` — Função `cancelar_evento()`
- `utils/formatters.py` — Função `gerar_sugestoes_de_horario()`

**Filas/Waitlist em sistemas similares:**
- WhatsApp Business: oferece notificação de espera
- Calendly: possui fila de cancelamento com push
- Uber: waitlist para motoristas indisponíveis
- Padrão: notificar em tempo real, timeout em 30-60 min

---

**Documento criado:** 2026-06-28  
**Status:** 📋 Roadmap (Não implementado)  
**Aprovado por:** Arquitetura NeoEve  
**Próxima revisão:** Pós-F5 WhatsApp Adapter (estabilização)

