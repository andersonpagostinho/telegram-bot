# PLANO P0: REAGENDAMENTO CONVERSACIONAL — VERSÃO REVISADA
**Data:** 2026-08-11  
**Versão:** 2.0 (com requisitos arquiteturais corrigidos)  
**Status:** 🔴 REPLANEJAR (modelo anterior inadequado)  
**Timeline revisada:** 8-12 horas (não 4-6)

---

## MUDANÇA CRÍTICA DE ABORDAGEM

**Versão 1.0 (INVÁLIDA):** Palavras-chave rígidas → detecção direta  
**Versão 2.0 (CORRETA):** GPT interpreta → motor executa → separação clara

**Impacto:** Arquitetura mudou, timeline aumentou, mas resultado será robusto.

---

## PRINCÍPIOS ARQUITETURAIS (INVIOLÁVEIS)

### 1. Separação de Responsabilidades

```
CAMADA 1 — INTERPRETAÇÃO (GPT)
├─ Entrada: texto livre do usuário
├─ Processamento: GPT interpreta intenção
├─ Saída: estrutura de intenção JSON
└─ NÃO EXECUTA: permissão, conflito, duração

CAMADA 2 — ORQUESTRAÇÃO (Router/Bot)
├─ Entrada: intenção estruturada
├─ Processamento: identifica ator, valida permissão
├─ Saída: chamada ao motor determinístico
└─ NÃO EXECUTA: GPT, lógica de agenda

CAMADA 3 — EXECUÇÃO (Motor Determinístico)
├─ Entrada: contexto completo (tenant, actor, evento, novo horário)
├─ Processamento: validação de conflito, duração, disponibilidade
├─ Saída: alteração atômica
└─ NUNCA delegado ao GPT
```

### 2. Intenção Estruturada (Saída do GPT)

```json
{
  "intenção": "REAGENDAR",
  "ator_tipo": "cliente|dono|profissional",
  "cliente_mencionado": "Carla|null",
  "nova_data_mencionada": "amanhã|sexta|2026-08-15|null",
  "nova_hora_mencionada": "15h|17:30|null",
  "confidence": 0.9
}
```

O GPT **apenas estrutura**, não executa.

### 3. Permissão é Determinística

```python
# Determinar quem é o actor
actor_id = user_id  # Quem está falando
dono_id = obter_id_dono(actor_id)  # Tenant desse ator
role = obter_role(actor_id)  # cliente|dono|profissional

# Validar permissão (NUNCA delegado ao GPT)
if role == "cliente":
    if evento["cliente_id"] != actor_id:
        ERRO("Cliente só pode alterar seus próprios eventos")

elif role == "dono":
    if evento["tenant_id"] != dono_id:
        ERRO("Dono só pode alterar eventos do seu tenant")

elif role == "profissional":
    if evento["profissional"] != actor_id:
        ERRO("Profissional só pode alterar seus atendimentos")
```

### 4. Motor Determinístico (Reutilizar)

**NÃO ALTERAR:**
- `alterar_agendamento()`
- `verificar_conflito_e_sugestoes_profissional()`

**REUTILIZAR:**
- Tenant resolution corrigido
- Ownership validation
- Conflito detection
- Duração variável
- Alteração atômica
- Event_id preservation
- Histórico com actor_id

---

## ATORES SUPORTADOS NO P0

### ATOR 1 — CLIENTE

**Pode:** Alterar apenas seus próprios agendamentos

**Fluxo:**
```
Cliente: "Quero mudar meu horário"
         ↓
GPT: intenção="REAGENDAR", ator_tipo="cliente"
         ↓
Bot: validar actor_id == evento.cliente_id
         ↓
Motor: verificar disponibilidade
         ↓
Resultado: alterar ou oferecer alternativas
```

**Exemplo conversacional:**
```
Cliente: "Quero remarcar minha manicure"
Bot: "Qual manicure você quer mudar?"
     "1. Quinta 14h com Carla"
     "2. Sexta 10h com Bruna"
Cliente: "A de quinta"
Bot: "Para qual horário?"
Cliente: "Sexta às 15h"
Bot: [valida motor]
Bot: "Confirma sexta às 15h?"
Cliente: "Sim"
Bot: "Pronto! Alterado."
```

### ATOR 2 — DONO

**Pode:** Alterar agendamentos de clientes dentro do próprio tenant

**Fluxo:**
```
Dono: "Remarque o agendamento da Maria para amanhã"
      ↓
GPT: intenção="REAGENDAR"
     cliente_mencionado="Maria"
     nova_data_mencionada="amanhã"
      ↓
Bot: validar actor_id é dono
     resolver tenant_id = dono_id
     buscar cliente "Maria" no tenant
     ↓
Motor: localizar evento de Maria
       validar conflito
       oferecer alternativas se necessário
      ↓
Resultado: alterar + registrar actor=dono
```

**Exemplo conversacional:**
```
Dono: "Marca a consulta da Carla para quinta"
Bot: "Qual consulta da Carla?"
     "1. Manicure — Terça 14h"
     "2. Corte — Quarta 10h"
Dono: "1"
Bot: "Quinta em qual horário?"
Dono: "15h"
Bot: [valida motor]
Bot: "Confirma mudar para quinta às 15h?"
Dono: "Sim"
Bot: "Pronto! Consulta da Carla foi movida para quinta às 15h."
```

### ATOR 3 — PROFISSIONAL

**Pode:** Alterar agendamentos dentro de seu escopo permitido

**Fluxo:**
```
Profissional: "Conserta meu agendamento com João para sexta"
              ↓
GPT: intenção="REAGENDAR"
     cliente_mencionado="João"
     nova_data_mencionada="sexta"
      ↓
Bot: validar actor_id é profissional
     buscar evento onde:
       profissional == actor_id
       cliente == "João"
      ↓
Motor: validar disponibilidade
       oferecer alternativas se necessário
      ↓
Resultado: alterar + registrar actor=profissional
```

**Exemplo conversacional:**
```
Profissional: "Não consigo atender o João amanhã, marca para sexta"
Bot: "Qual horário da sexta?"
Profissional: "10h"
Bot: [valida motor]
Bot: "Confirma atender João sexta às 10h?"
Profissional: "Sim"
Bot: "Pronto! Agendamento do João movido para sexta às 10h."
```

---

## DETECÇÃO DE INTENÇÃO (SEM PALAVRAS-CHAVE RÍGIDAS)

### Heurística Rápida (Opcional)

Se mensagem contém termos comuns (reagendar, remarcar, mudar), classificar direto.  
**Custo:** 0 (sem GPT)  
**Cobertura:** ~70% dos casos

### Fallback GPT (Robusto)

Se heurística não reconhece, chamar GPT com contexto:

```python
async def detectar_intenao_reagendamento(mensagem: str, contexto: dict) -> dict | None:
    """
    Detectar se mensagem é reagendamento.
    
    1. Tenta heurística rápida
    2. Se falha, consulta GPT
    3. Retorna: intenção estruturada ou None
    """
    
    # ETAPA 1: Heurística (rápida)
    if eh_heuristica_reagendamento(mensagem):
        return {
            "intenção": "REAGENDAR",
            "confianca": "alta",
            "origem": "heuristica"
        }
    
    # ETAPA 2: GPT (se heurística não reconheceu)
    prompt = f"""
    Mensagem: "{mensagem}"
    Contexto: O usuário tem agendamentos pendentes.
    
    Essa mensagem é sobre REAGENDAR (mudar horário) de um agendamento?
    
    Responda APENAS JSON:
    {{
        "eh_reagendamento": true|false,
        "confianca": 0.0-1.0,
        "cliente_mencionado": "nome|null",
        "data_mencionada": "data ou "null",
        "hora_mencionada": "hora ou null"
    }}
    """
    
    resultado_gpt = await chamar_gpt(prompt)
    
    if resultado_gpt.get("eh_reagendamento") and resultado_gpt.get("confianca", 0) >= 0.7:
        return {
            "intenção": "REAGENDAR",
            "confianca": resultado_gpt["confianca"],
            "origem": "gpt",
            "cliente_mencionado": resultado_gpt.get("cliente_mencionado"),
            "data_mencionada": resultado_gpt.get("data_mencionada"),
            "hora_mencionada": resultado_gpt.get("hora_mencionada")
        }
    
    return None  # Não é reagendamento
```

**Exemplos reconhecidos por GPT:**
```
✅ "Quero remarcar minha manicure"
✅ "Preciso adiar minha manicure"
✅ "Não consigo ir amanhã, pode ser sexta?"
✅ "Tem como jogar minha consulta mais para o fim do dia?"
✅ "Queria passar meu horário para sexta"
✅ "Será que dá para mudar o horário da Carla?"
✅ "Pode colocar a consulta da Maria para amanhã?"
✅ "Descala meu agendamento de quinta"
✅ "Muda a consulta do João"
```

**Vantagem:** Não há lista infinita de sinônimos. GPT interpreta liberdade.

---

## MÁQUINA DE ESTADOS (7 ESTADOS)

```
IDLE (início)
  ↓ (intenção REAGENDAR detectada)

REAGENDAMENTO_INICIADO
  └─ Estado: Confirmado que é reagendamento
  └─ Próximo: Identificar qual evento alterar
  └─ Armazenar: intenção, actor_id, tenant_id

IDENTIFICANDO_EVENTO
  └─ Estado: Aguardando cliente/dono escolher qual evento
  └─ Lógica:
     - Se cliente: listar eventos do cliente
     - Se dono: listar eventos do tenant
     - Se profissional: listar eventos onde é profissional
  └─ Próximo: AGUARDANDO_NOVO_HORARIO
  └─ Armazenar: evento_id, agendamento_anterior

AGUARDANDO_NOVO_HORARIO
  └─ Estado: Cliente forneceu novo horário (ou dono forneceu junto com cliente)
  └─ Processamento:
     - GPT interpreta data/hora
     - Calcular duração (usar duração do evento original)
     - Guardar em draft
  └─ Próximo: VALIDANDO_DISPONIBILIDADE
  └─ Armazenar: draft_reagendamento {data, hora, duracao, profissional}

VALIDANDO_DISPONIBILIDADE (transição automática, não aguarda input)
  └─ Estado: Motor valida se novo horário está livre
  └─ Processamento:
     - Chamar verificar_conflito_e_sugestoes_profissional()
     - Passar event_id para ignorar evento sendo alterado
  └─ Próximo:
     - Se SEM conflito: AGUARDANDO_CONFIRMACAO
     - Se COM conflito: AGUARDANDO_ESCOLHA_ALTERNATIVA
  └─ Armazenar: resultado_conflito, sugestoes

AGUARDANDO_ESCOLHA_ALTERNATIVA (se houve conflito)
  └─ Estado: Cliente/dono escolhe entre alternativas
  └─ Lógica: Revalidar alternativa escolhida
  └─ Próximo: AGUARDANDO_CONFIRMACAO
  └─ Armazenar: draft_reagendamento atualizado com alternativa

AGUARDANDO_CONFIRMACAO
  └─ Estado: Confirmação explícita antes de mutar
  └─ Processamento:
     - Se "Sim/Confirmo": AGENDAMENTO_REAGENDANDO
     - Se "Não/Cancela": IDLE (sem alterar)
  └─ Armazenar: confirmacao=true|false

AGENDAMENTO_REAGENDANDO (transição automática)
  └─ Estado: Chamando motor para alterar
  └─ Processamento:
     - alterar_agendamento(
         event_id, nova_data, nova_hora, tenant_id, actor_id
       )
     - Validações defensivas de tenant/ownership
  └─ Próximo: CONCLUIDO
  └─ Armazenar: resultado_alteracao

CONCLUIDO
  └─ Responder ao usuário: "Pronto! Alterado."
  └─ Limpar contexto_temporario
  └─ VOLTA: IDLE
```

---

## CONTEXTO TEMPORÁRIO (Minimalista)

```python
contexto = {
    # Estado da máquina
    "estado_fluxo": "AGUARDANDO_NOVO_HORARIO",
    
    # Atores e tenant
    "actor_id": user_id,
    "tenant_id": dono_id,
    "role": "cliente|dono|profissional",
    
    # Evento sendo alterado
    "evento_id": "EVT123",
    "agendamento_anterior": {
        "data": "2026-08-14",
        "hora": "14:30",
        "profissional": "Carla",
        "servico": "Manicure",
        "duracao_minutos": 30
    },
    
    # Draft em construção
    "draft_reagendamento": {
        "data": "2026-08-15",
        "hora": "17:00",
        "profissional": "Carla",
        "duracao_minutos": 30
    },
    
    # Conflito (se houver)
    "conflito": True,
    "sugestoes": ["16:00-16:30", "17:30-18:00"],
    
    # Última ação
    "ultima_acao": "usuario_escolheu_novo_horario"
}
```

**NÃO ARMAZENAR:** Catálogo, lista de eventos, agenda, dados persistentes.

---

## CONTRATO DO MOTOR (INVIOLÁVEL)

### Função: `alterar_agendamento()`

**Assinatura:**
```python
async def alterar_agendamento(
    user_id: str,           # Cliente ou ator
    event_id: str,          # Evento a alterar (PRESERVADO)
    nova_data: str,         # 2026-08-15
    nova_hora_inicio: str,  # 17:00
    nova_duracao_minutos: int,  # Pode variar
    tenant_id: str = None,  # Tenant (resolvido se None)
    actor_id: str = None    # Quem alterou (resolvido se None)
) -> dict:
```

**Garantias (NUNCA quebrar):**
- ✅ event_id é PRESERVADO (não cria novo evento)
- ✅ Histórico é registrado atomicamente com actor_id
- ✅ Status permanece "confirmado"
- ✅ Tenant isolation validado
- ✅ Ownership validado
- ✅ Retorna: {ok: bool, evento_id: str, detalhes: {...}, alteracao: {...}}

### Função: `verificar_conflito_e_sugestoes_profissional()`

**Assinatura:**
```python
async def verificar_conflito_e_sugestoes_profissional(
    user_id: str,
    data: str,
    hora_inicio: str,
    duracao_min: int,
    profissional: str,
    servico: str,
    event_id: str = None  # Ignora esse evento na busca
) -> dict:
```

**Garantias:**
- ✅ Ignora o evento sendo alterado (event_id)
- ✅ Retorna conflito: bool
- ✅ Retorna sugestoes: list (até 3)
- ✅ Sugestões respeitam duração variável

---

## FLUXO CONVERSACIONAL COMPLETO

### Cenário A — Cliente altera seu evento (horário livre)

```
[IDLE]

Cliente: "Quero mudar meu horário de manicure"

[Bot → GPT] Detectar intenção
GPT: intenção=REAGENDAR, ator_tipo=cliente, confianca=0.95

[Bot] Validar permissão: actor_id=cliente ✓

[Bot → Estado] REAGENDAMENTO_INICIADO → IDENTIFICANDO_EVENTO
Bot: "Qual manicure você quer alterar?"
     "1. Terça 14h com Carla"
     "2. Sexta 10h com Bruna"

[Estado → IDENTIFICANDO_EVENTO] Armazenar agendamentos

Cliente: "1"

[Bot → Estado] evento_id=EVT123, AGUARDANDO_NOVO_HORARIO
Bot: "Para qual horário você quer mudar?"

Cliente: "Sexta às 15h"

[Bot → GPT] Interpretar data/hora
GPT: data=sexta→2026-08-15, hora=15:00

[Bot → Estado] draft_reagendamento={data: 2026-08-15, hora: 15:00}

[Bot → Estado] VALIDANDO_DISPONIBILIDADE (automático)

[Bot → Motor] verificar_conflito_e_sugestoes_profissional(
    user_id=cliente, data=2026-08-15, hora_inicio=15:00,
    profissional=Carla, duracao_min=30, event_id=EVT123
)

Motor: SEM CONFLITO

[Bot → Estado] AGUARDANDO_CONFIRMACAO
Bot: "Confirmo alterar sua manicure para sexta às 15h?"

Cliente: "Sim"

[Bot → Estado] AGENDAMENTO_REAGENDANDO (automático)

[Bot → Motor] alterar_agendamento(
    event_id=EVT123, nova_data=2026-08-15, nova_hora_inicio=15:00,
    tenant_id=tenant, actor_id=cliente
)

Motor: ✅ Evento alterado
       evento_id=EVT123 (PRESERVADO)
       historico_alteracoes=[{
           timestamp=...,
           anterior={data: 2026-08-14, hora: 14:30},
           novo={data: 2026-08-15, hora: 15:00},
           actor_id=cliente
       }]

[Bot → Estado] CONCLUIDO
Bot: "Pronto! Sua manicure foi movida para sexta às 15h."

[Bot] Limpar contexto_temporario

[IDLE]
```

### Cenário B — Cliente altera seu evento (com conflito)

```
[Mesmos passos até VALIDANDO_DISPONIBILIDADE]

Motor: COM CONFLITO
       sugestoes=["16:00-16:30", "17:30-18:00"]

[Bot → Estado] AGUARDANDO_ESCOLHA_ALTERNATIVA
Bot: "15h está ocupado. Posso oferecer:"
     "1. 16h"
     "2. 17:30h"

Cliente: "2"

[Bot → Motor] Revalidar 17:30
Motor: SEM CONFLITO

[Bot → Estado] draft_reagendamento atualizado

[Bot → Estado] AGUARDANDO_CONFIRMACAO
Bot: "Confirmo alterar para sexta às 17:30h?"

[Resto igual cenário A]
```

### Cenário C — Dono altera evento de cliente

```
[IDLE]

Dono: "Remarque o agendamento da Maria para sexta"

[Bot → GPT] Detectar intenção
GPT: intenção=REAGENDAR, cliente_mencionado=Maria, data_mencionada=sexta

[Bot] Validar: actor_id é dono ✓

[Bot] Resolver tenant_id = dono_id ✓

[Bot → Estado] REAGENDAMENTO_INICIADO → IDENTIFICANDO_EVENTO
Bot: "Qual agendamento da Maria?"
     "1. Manicure — Terça 14h com Carla"
     "2. Corte — Quarta 10h com Bruna"

Dono: "1"

[Bot → Estado] evento_id=EVT456

[Bot → Estado] AGUARDANDO_NOVO_HORARIO
Bot: "Para qual horário na sexta?"

Dono: "15h"

[GPT] Interpretar: 2026-08-15, 15:00

[Motor] Validar: SEM CONFLITO

[Bot → Estado] AGUARDANDO_CONFIRMACAO
Bot: "Confirmo mover a manicure da Maria para sexta às 15h?"

Dono: "Sim"

[Motor] alterar_agendamento(event_id=EVT456, actor_id=dono)

[Bot] "Pronto! Manicure da Maria foi movida para sexta às 15h."

[Limpar, IDLE]
```

---

## VALIDAÇÕES DETERMINÍSTICAS (NUNCA GPT)

### 1. Tenant Isolation

```python
# SEMPRE validar tenant_id
if evento["tenant_id"] != actor_tenant_id:
    raise PermissionError("Evento não pertence a esse tenant")
```

### 2. Permissão por Role

```python
if role == "cliente":
    if evento["cliente_id"] != actor_id:
        raise PermissionError("Cliente não pode alterar evento de outro cliente")

elif role == "dono":
    # Dono pode alterar qualquer evento do tenant
    # Validação já feita por tenant_id
    pass

elif role == "profissional":
    if evento["profissional"] != actor_id:
        raise PermissionError("Profissional não pode alterar evento onde não trabalha")
```

### 3. Conflito e Sugestões

```python
# SEMPRE usar motor determinístico
validacao = await verificar_conflito_e_sugestoes_profissional(...)

if validacao["conflito"]:
    # NÃO alterar, oferecer alternativas
    sugestoes = validacao["sugestoes"]  # Até 3 sugestões
    # Aguardar cliente escolher
else:
    # Sem conflito, pedir confirmação e alterar
```

### 4. Confirmação Obrigatória

```python
# SEMPRE pedir confirmação antes de mutar
# Exceto se intenção estiver 100% explícita (raro)

# Exemplos de intenção explícita (ainda assim, pedir):
# "Muda meu agendamento de quinta 14h para sexta 15h" ← mesmo assim confirma
```

### 5. Operação Atômica

```python
# SEMPRE usar alterar_agendamento()
# NÃO fazer: cancelar + criar novo

# Garantias:
# - event_id preservado
# - histórico atômico
# - tenant isolation
# - ownership validado
```

---

## TESTES E2E OBRIGATÓRIOS (15+ Cenários)

### Grupo 1 — Cliente Altera (5 cenários)

- [ ] **C1** — Cliente com 1 agendamento, horário livre
- [ ] **C2** — Cliente com 1 agendamento, horário ocupado, escolhe alternativa
- [ ] **C3** — Cliente com N agendamentos, lista e escolhe qual
- [ ] **C4** — Cliente com linguagem fora das palavras-chave ("Preciso adiar...")
- [ ] **C5** — Cliente recusa confirmação (não altera)

### Grupo 2 — Dono Altera (4 cenários)

- [ ] **D1** — Dono altera evento de cliente dentro do tenant
- [ ] **D2** — Dono tenta acessar evento de cliente em outro tenant (falha)
- [ ] **D3** — Dono com N clientes, seleciona correto
- [ ] **D4** — Dono fornece cliente + novo horário tudo junto

### Grupo 3 — Profissional Altera (2 cenários)

- [ ] **P1** — Profissional altera seu próprio agendamento
- [ ] **P2** — Profissional tenta alterar evento onde não trabalha (falha)

### Grupo 4 — Motor/Persistência (4 cenários)

- [ ] **M1** — event_id é preservado (MESMO ID, não novo)
- [ ] **M2** — Histórico registra actor_id, anterior, novo, timestamp
- [ ] **M3** — Conflito não altera, oferece alternativas
- [ ] **M4** — Operação atômica (nenhuma alteração se conflito não resolvido)

### Grupo 5 — Arquitetura (3 cenários)

- [ ] **A1** — GPT apenas interpreta (não executa motor)
- [ ] **A2** — Router apenas orquestra (não executa lógica)
- [ ] **A3** — Tenant isolation: cliente A não vê eventos de cliente B

### Grupo 6 — Regressão (1 cenário)

- [ ] **R1** — P0 174/174 continua PASS + P1 42/42 continua PASS

---

## GATES DE VALIDAÇÃO FINAL

Antes de declarar P0 PRONTO:

```
[ ] Linguagem livre chega à intenção REAGENDAR
    Evidência: 5 variações de linguagem reconhecidas

[ ] GPT apenas interpreta
    Evidência: GPT retorna estrutura, não executa motor

[ ] Router apenas orquestra
    Evidência: Router não contém lógica de conflito/disponibilidade

[ ] Motor executa lógica
    Evidência: Motor valida conflito independente de entrada

[ ] Cliente altera somente seus eventos
    Evidência: Teste C1-C5 passam, tentativa de outro cliente falha

[ ] Dono altera eventos do tenant
    Evidência: Teste D1-D4 passam, acesso cross-tenant falha

[ ] Profissional respeita escopo
    Evidência: Teste P1-P2 passam, tentativa fora do escopo falha

[ ] Tenant isolation validado
    Evidência: Teste A2 passa, actor não vê dados de outro tenant

[ ] Conflito validado
    Evidência: Teste M3 passa, conflito não altera

[ ] Alternativas validadas
    Evidência: Sugestões são oferecidas e revalidadas

[ ] Confirmação validada
    Evidência: Teste C5 passa, não altera sem "Sim"

[ ] Mesmo event_id preservado
    Evidência: Teste M1 passa, evento_id antes == evento_id depois

[ ] Histórico preservado
    Evidência: Teste M2 passa, histórico contém actor_id + anterior + novo

[ ] Actor da alteração registrado
    Evidência: historico_alteracoes[0].actor_id == quem alterou

[ ] Operação atômica
    Evidência: Teste M4 passa, nenhuma alteração se conflito

[ ] E2E conversacional passando
    Evidência: Todos os 15 cenários executam e validam

[ ] Regressão P0 existente continua passando
    Evidência: Teste R1 passa, 174/174 + 42/42

[ ] Nenhuma alteração quando conflito permanece
    Evidência: Se cliente escolhe alternativa e há conflito, oferece novamente
```

---

## ARQUIVOS A ATUALIZAR/CRIAR

| Arquivo | Ação | Escopo |
|---------|------|--------|
| P0_REAGENDAMENTO_GATES_E2E_2026_08_11.md | Atualizar | 15+ cenários |
| TESTE_P0_REAGENDAMENTO_E2E_2026_08_11.py | Reescrever | 15+ testes |
| CONTRATO_MOTOR_REAGENDAMENTO.md | CRIAR | Garanta motor |
| handlers/bot.py | Implementar | Estados 2-7 |
| router/principal_router.py | Atualizar | Detecção GPT |
| P0_ARQUITETURA_REAGENDAMENTO.md | CRIAR | Diagrama completo |

---

## TIMELINE REVISADA

| Fase | Atividade | Tempo | Bloqueador |
|------|-----------|-------|-----------|
| **1** | Atualizar documentação arquitetural | 2h | Não |
| **2** | Reescrever E2E com 15 cenários | 2h | Fase 1 |
| **3** | Implementar detecção GPT | 2h | Fase 1 |
| **4** | Implementar 7 estados em bot.py | 3h | Fase 1 |
| **5** | Executar 15 testes E2E | 1h | Fase 4 |
| **6** | Validar regressão P0/P1 | 1h | Fase 5 |
| **TOTAL** | | **11h** | |

(Aumentou de 4-6h para ~11h, mas será correto.)

---

## PRINCÍPIO FUNDAMENTAL

> "Não implementar apenas a solução mais rápida se isso exigir criar arquitetura que posteriormente precise ser refeita."

Este plano **não é** a solução mais rápida.

Este plano **é** a solução **certa**.

---

**Próximo:** Atualizar P0_REAGENDAMENTO_GATES_E2E_2026_08_11.md com 15+ cenários específicos.
