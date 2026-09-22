# CONTRATO DO MOTOR — REAGENDAMENTO
**Data:** 2026-08-11  
**Versão:** 1.0  
**Status:** INVIOLÁVEL — Motor já validado (7/7 testes passaram)

---

## PRINCÍPIO

O motor de agenda **NÃO foi alterado** para P0 de reagendamento.

Esse documento **garante** que o router/bot.py:
1. Chama o motor corretamente
2. Respeita as garantias do motor
3. Não tenta duplicar lógica do motor

---

## FUNÇÃO 1: `alterar_agendamento()`

**Arquivo:** `services/event_service_async.py`  
**Status:** ✅ TESTADO (TESTE_ALTERAR_SIMPLES_2026_08_11.py: 7/7 PASS)  
**Data de Validação:** 2026-08-11

### Assinatura

```python
async def alterar_agendamento(
    user_id: str,                    # Cliente ou ator fazendo a alteração
    event_id: str,                   # ID do evento (será PRESERVADO)
    nova_data: str,                  # "2026-08-15" (ISO format)
    nova_hora_inicio: str,           # "15:00" (HH:MM format)
    nova_duracao_minutos: int = None,  # Se None, usa duração original
    tenant_id: str = None            # Tenant (resolvido se None via user_id)
) -> dict
```

### Contrato de Saída

```python
{
    "ok": True,                      # Sucesso da alteração
    "evento_id": "EVT123",           # MESMO ID (não novo!)
    "detalhes": {
        "data": "2026-08-15",
        "hora_inicio": "15:00",
        "duracao_minutos": 30,
        "profissional": "Carla",
        "status": "confirmado"
    },
    "alteracao": {
        "timestamp": "2026-08-11T18:30:00Z",
        "anterior": {
            "data": "2026-08-14",
            "hora": "14:30"
        },
        "novo": {
            "data": "2026-08-15",
            "hora": "15:00"
        },
        "actor_id": "cliente_001"
    }
}
```

### Garantias Invioláveis

#### ✅ Preservação de event_id

```
ANTES:   evento_id = "EVT123"
FUNÇÃO:  alterar_agendamento(..., event_id="EVT123", ...)
DEPOIS:  evento_id = "EVT123"  ← MESMA ID, não novo

NÃO fazer: cancelar "EVT123" + criar "EVT456"
```

**Validação em teste:**
```python
evento_antes = await buscar_evento("EVT123")
assert evento_antes is not None

resultado = await alterar_agendamento(event_id="EVT123", ...)
assert resultado["evento_id"] == "EVT123"

evento_depois = await buscar_evento("EVT123")
assert evento_depois is not None
assert evento_depois["hora_inicio"] == "15:00"  # Alterado
```

#### ✅ Histórico Registrado Atomicamente

```python
evento_alterado["historico_alteracoes"] = [{
    "timestamp": "2026-08-11T18:30:00Z",
    "anterior": {"data": "2026-08-14", "hora": "14:30"},
    "novo": {"data": "2026-08-15", "hora": "15:00"},
    "actor_id": "cliente_001",
    "motivo": "Reagendamento do cliente"
}]
```

**Garantia:** Histórico usa `ArrayUnion` (não sobrescreve, acumula).

**Validação em teste:**
```python
evento = await buscar_evento("EVT123")
assert len(evento.get("historico_alteracoes", [])) >= 1
assert evento["historico_alteracoes"][0]["actor_id"] == "cliente_001"
```

#### ✅ Status Permanece "confirmado"

```
ANTES:   status = "confirmado"
DEPOIS:  status = "confirmado"  ← NÃO muda

NÃO fazer: status = "pendente" ou "rascunho"
```

**Validação em teste:**
```python
evento = await buscar_evento("EVT123")
assert evento["status"] == "confirmado"
```

#### ✅ Tenant Isolation Validado

```python
# Dentro de alterar_agendamento():
# 1. Resolve tenant_id se não fornecido
# 2. Busca evento em: Clientes/{tenant_id}/Eventos/{event_id}
# 3. Valida que evento pertence ao tenant
# 4. Não permite acesso cross-tenant

if evento["tenant_id"] != tenant_id:
    return {"ok": False, "motivo": "Evento não pertence a esse tenant"}
```

**Validação em teste:**
```python
# Tenant A não consegue alterar evento de Tenant B
resultado = await alterar_agendamento(
    event_id="EVT_TENANT_B",
    tenant_id="TENANT_A"
)
assert resultado["ok"] == False
```

#### ✅ Duração Variável Suportada

```python
# Duração pode mudar (ex: manicure 30min → manicure 60min)

resultado = await alterar_agendamento(
    event_id="EVT123",
    nova_data="2026-08-15",
    nova_hora_inicio="15:00",
    nova_duracao_minutos=60  # Alterado de 30 para 60
)

evento = await buscar_evento("EVT123")
assert evento["duracao_minutos"] == 60
assert evento["hora_fim"] == "16:00"  # Calculado automaticamente
```

**Garantia:** Motor recalcula hora_fim baseado em nova duração.

#### ✅ Atomicidade Garantida

```python
# Se alterar_agendamento() retorna {"ok": True}:
# - Evento foi alterado NO FIRESTORE (não é rascunho)
# - Histórico foi registrado
# - Locks foram liberados
# - Operação é IRREVOGÁVEL

# Se retorna {"ok": False}:
# - NENHUMA alteração foi feita
# - NENHUM histórico foi registrado
# - Estado anterior está intacto
```

---

## FUNÇÃO 2: `verificar_conflito_e_sugestoes_profissional()`

**Arquivo:** `services/event_service_async.py`  
**Status:** ✅ VALIDADO (em uso há meses, bugs corrigidos)  
**Uso em P0:** Sempre usar ANTES de alterar

### Assinatura

```python
async def verificar_conflito_e_sugestoes_profissional(
    user_id: str,              # Tenant ou cliente
    data: str,                 # "2026-08-15"
    hora_inicio: str,          # "15:00"
    duracao_min: int,          # Duração do serviço
    profissional: str,         # "Carla"
    servico: str,              # "Manicure"
    event_id: str = None       # [CRÍTICO] Ignora esse evento na busca
) -> dict
```

### Contrato de Saída

#### Sem Conflito

```python
{
    "conflito": False,
    "sugestoes": []  # Vazio se sem conflito
}
```

#### Com Conflito

```python
{
    "conflito": True,
    "sugestoes": [
        "16:00-16:30",
        "17:00-17:30",
        "18:00-18:30"
    ]
}
```

### Garantias Invioláveis

#### ✅ Respeita event_id (Crítico para Reagendamento)

```python
# Se event_id é fornecido:
# Motor IGNORA esse evento na busca de conflitos

# Exemplo:
# - Evento EVT123 está em 2026-08-15 15:00-15:30
# - Cliente quer mudar para 2026-08-15 15:00 (mesmo horário)
# - Motor ignora EVT123 e retorna: conflito=False

validacao = await verificar_conflito_e_sugestoes_profissional(
    user_id=dono_id,
    data="2026-08-15",
    hora_inicio="15:00",
    duracao_min=30,
    profissional="Carla",
    servico="Manicure",
    event_id="EVT123"  # ← Crítico!
)

assert validacao["conflito"] == False  # Ignora EVT123
```

**Sem `event_id`, teria retornado `conflito=True` (ele mesmo!).**

#### ✅ Sugestões Respeitam Duração Variável

```python
# Se serviço tem duração 60min, sugestões respeitam:
# - 16:00-17:00 (não 16:00-16:30)

validacao = await verificar_conflito_e_sugestoes_profissional(
    data="2026-08-15",
    hora_inicio="15:00",
    duracao_min=60,  # Manicure + massagem
    profissional="Carla",
    servico="Manicure"
)

# Sugestões terão espaço de 60 minutos cada
assert all(len(s.split("-")) == 2 for s in validacao["sugestoes"])
```

#### ✅ Retorna até 3 Sugestões

```python
validacao = await verificar_conflito_e_sugestoes_profissional(...)

assert len(validacao.get("sugestoes", [])) <= 3
```

---

## COMO O ROUTER/BOT USA O MOTOR

### ✅ Fluxo Correto

```python
# ETAPA 1: Usuário forneceu novo horário
novo_horario = "15:00"
nova_data = "2026-08-15"

# ETAPA 2: Chamar motor ANTES de alterar
validacao = await verificar_conflito_e_sugestoes_profissional(
    user_id=dono_id,
    data=nova_data,
    hora_inicio=novo_horario,
    duracao_min=30,
    profissional="Carla",
    servico="Manicure",
    event_id="EVT123"  # ← CRÍTICO: Ignora evento sendo alterado
)

# ETAPA 3: Validar resultado
if validacao["conflito"]:
    # Oferecer alternativas
    sugestoes = validacao["sugestoes"]
    # Aguardar cliente escolher
else:
    # Pedir confirmação
    bot.reply("Confirma?")
    # Se cliente confirma, chamar alterar_agendamento()

# ETAPA 4: Só chamar alterar_agendamento() se sem conflito
resultado = await alterar_agendamento(
    event_id="EVT123",
    nova_data=nova_data,
    nova_hora_inicio=novo_horario,
    tenant_id=dono_id
)
```

### ❌ Fluxos INCORRETOS (Proibidos)

#### Erro 1: Não passar event_id

```python
# ❌ ERRADO
validacao = await verificar_conflito_e_sugestoes_profissional(
    user_id=dono_id,
    data=nova_data,
    hora_inicio=novo_horario,
    duracao_min=30,
    profissional="Carla",
    servico="Manicure"
    # FALTA: event_id="EVT123"
)
# Resultado: Motor detecta conflito consigo mesmo!
# conflito=True (falso positivo)
```

**Correção:**
```python
validacao = await verificar_conflito_e_sugestoes_profissional(
    ...,
    event_id="EVT123"  # ← Adicionar
)
```

#### Erro 2: Não respeitar conflito

```python
# ❌ ERRADO
validacao = await verificar_conflito_e_sugestoes_profissional(...)

# Ignorar resultado e alterar mesmo assim
if validacao["conflito"]:
    # ERRADO: Alterar mesmo com conflito!
    resultado = await alterar_agendamento(...)
```

**Correção:**
```python
if validacao["conflito"]:
    # Oferecer alternativas, NÃO alterar
    bot.reply(f"Ocupado. Tenho: {validacao['sugestoes']}")
    # Aguardar cliente escolher
else:
    # Só aqui alterar
    resultado = await alterar_agendamento(...)
```

#### Erro 3: Duplicar lógica de conflito

```python
# ❌ ERRADO
# Tentar implementar detecção de conflito no router/GPT
def meu_verificar_conflito(...):
    # Reimplementar lógica do motor
    # ...

validacao = meu_verificar_conflito(...)  # Versão errada!
```

**Correção:**
```python
# Chamar motor do domínio
validacao = await verificar_conflito_e_sugestoes_profissional(...)
```

---

## TESTES QUE VALIDAM O MOTOR

### Teste 1: Preservação de event_id

**Arquivo:** TESTE_ALTERAR_SIMPLES_2026_08_11.py (linha 63-119)  
**Status:** ✅ PASSA 7/7

```python
# Criar evento
resultado1 = await criar_evento(event_id="evt_001")

# Alterar
resultado2 = await alterar_agendamento(event_id="evt_001", ...)

# Validar
evento_alterado = await buscar_evento("evt_001")
assert evento_alterado is not None  # Ainda existe com MESMO ID
assert evento_alterado["hora_inicio"] == "10:00"  # Alterado
```

### Teste 2: Histórico Registrado

```python
evento = await buscar_evento("evt_001")
assert len(evento["historico_alteracoes"]) >= 1
assert evento["historico_alteracoes"][0]["anterior"]["data"] == "2026-08-11"
assert evento["historico_alteracoes"][0]["novo"]["data"] == "2026-08-12"
```

### Teste 3: event_id em verificar_conflito

```python
# Evento em 15:00-15:30
# Cliente quer mudar para 15:00 (mesmo horário)

validacao = await verificar_conflito_e_sugestoes_profissional(
    data="2026-08-15",
    hora_inicio="15:00",
    duracao_min=30,
    event_id="evt_001"  # Ignora esse evento
)

assert validacao["conflito"] == False  # Sem conflito (ignora ele mesmo)

# Sem event_id, teria retornado conflito=True (falso positivo)
```

---

## CHECKLIST PARA BOT.PY

Antes de chamar motor, validar:

- [ ] `event_id` está definido e é string válida
- [ ] `nova_data` está em formato ISO "YYYY-MM-DD"
- [ ] `nova_hora_inicio` está em formato "HH:MM"
- [ ] `duracao_minutos` é número > 0
- [ ] `tenant_id` está definido (resolvido via `obter_id_dono()`)
- [ ] `actor_id` está definido (user_id que está fazendo a alteração)
- [ ] Conflito foi validado ANTES de chamar alterar_agendamento()
- [ ] Cliente confirmou ANTES de chamar alterar_agendamento()

---

## FALHAS ESPERADAS (Tratá-las Graciosamente)

### Falha 1: Motor retorna "ok": False

```python
resultado = await alterar_agendamento(...)

if not resultado["ok"]:
    motivo = resultado.get("motivo", "Erro desconhecido")
    await bot.reply(f"Não consegui alterar: {motivo}")
    # Exemplos de motivo:
    # - "Evento não encontrado"
    # - "Tenant mismatch"
    # - "Ownership validation failed"
```

### Falha 2: Conflito que não foi oferecido

```python
# Se motor retorna conflito=True e não foi oferecido ao cliente:
if validacao["conflito"]:
    bot.reply("Ops, esse horário ficou ocupado enquanto conversávamos.")
    bot.reply("Deixa eu oferecer outras opções...")
    sugestoes = validacao["sugestoes"]
    bot.reply(f"Tenho: {sugestoes}")
```

---

## NENHUMA ALTERAÇÃO ESPERADA AO MOTOR

Este documento **descreve** o motor, não **altera** ele.

Se durante a implementação descobrir um bug no motor:

1. ✅ Documentar o bug
2. ✅ Criar teste que reproduz
3. ✅ Corrigir o bug no motor
4. ✅ Adicionar teste permanente
5. ✅ **NÃO** fazer workaround no router

---

**Próximo:** Implementar bot.py confiando nessas garantias.
