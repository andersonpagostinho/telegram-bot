# P0: REAGENDAMENTO CONVERSACIONAL — GATES + E2E
**Data:** 2026-08-11  
**Criticidade:** P0  
**Definição de Pronto:** 13 cenários E2E + 1 cenário crítico (máquina de estados)

---

## GATES (6)

### Gate 1 — Detecção
**O quê:** Mensagens são interpretadas como intenção de reagendamento  
**Quem:** GPT + Router  
**Não faz:** Escolhe horário, verifica conflito

**Mensagens reconhecidas:**
```
"quero mudar meu horário"
"preciso remarcar"
"posso trocar meu horário?"
"quero passar para amanhã"
"tem como mudar minha manicure?"
"reagendar"
"alterar"
"trocar de dia"
```

**Saída:** Intenção estruturada
```
intenção: "reagendamento"
estado_fluxo: "aguardando_identificacao_evento"
```

---

### Gate 2 — Identificação do Evento
**O quê:** Sistema identifica qual evento alterar  
**Quem:** Motor (busca agendamentos do cliente)  
**Lógica:**

```
Se 1 agendamento:
  └─ Identificar automaticamente
  └─ Perguntar novo horário

Se N agendamentos:
  └─ Listar opcoes
     1. Manicure — quinta às 14h
     2. Corte — sexta às 10h
  └─ Cliente escolhe
  └─ Guardar evento_id
```

**Estado após gate 2:**
```
evento_id: "EVT123"
agendamento_anterior: {
  data: "2026-08-14",
  hora: "14:30",
  profissional: "Carla",
  servico: "Manicure",
  duracao: 30
}
estado_fluxo: "aguardando_novo_horario"
```

---

### Gate 3 — Novo Horário
**O quê:** Cliente fornece novo horário; GPT interpreta; motor calcula  
**Quem:** GPT (interpretação) → Motor (cálculo)  
**Entrada cliente:**

```
"amanhã às 15"
"sexta"
"às 17h"
"segunda-feira 16:30"
```

**Processamento:**
```
GPT interpreta:
  ↓
data: "2026-08-15"
hora: "15:00"
  ↓
Motor calcula:
  - data (absoluta)
  - hora (normalizada)
  - duração (do evento original: 30 min)
  - profissional (do evento original: Carla)
  - servico (do evento original: Manicure)
```

**Estado após gate 3:**
```
novo_horario: {
  data: "2026-08-15",
  hora: "15:00",
  duracao: 30,
  profissional: "Carla"
}
estado_fluxo: "validando_conflito"
```

---

### Gate 4 — Conflito
**O quê:** Motor valida se novo horário está disponível  
**Quem:** verificar_conflito_e_sugestoes_profissional()  
**Lógica:**

```
Motor chama:
  verificar_conflito_e_sugestoes_profissional(
    novo_horario,
    event_id=EVT123  ← ignora evento sendo alterado
  )

Resultado:
  ├─ Sem conflito
  │   └─ estado_fluxo = "aguardando_confirmacao"
  │
  └─ Com conflito
      └─ sugestoes = ["16:00", "17:00", "18:00"]
      └─ estado_fluxo = "oferecendo_alternativas"
```

**Resposta ao cliente:**

```
Se LIVRE:
  "Perfeito! Vou mudar para sexta às 15h."
  "Confirma?"

Se OCUPADO:
  "Esse horário está ocupado."
  "Posso oferecer:"
  1. 16h
  2. 17h
  3. 18h
```

---

### Gate 5 — Confirmação
**O quê:** Antes de mutar, cliente confirma explicitamente  
**Quem:** Bot (aguarda confirmação inequívoca)  
**Importante:** Alteração é operação mutável

```
Bot pergunta:
  "Confirma a mudança para sexta às 17h?"

Cliente responde:
  ├─ "Sim" → proceed
  ├─ "Confirmo" → proceed
  ├─ "Pronto" → proceed
  └─ "Não" / "Cancela" → não altera
```

**Estado após confirmação:**
```
confirmado: true
estado_fluxo: "alterando_evento"
```

---

### Gate 6 — Persistência
**O quê:** Evento é alterado atomicamente  
**Quem:** alterar_agendamento()  
**Saída:**

```
✅ Mesmo event_id (EVT123)
✅ Novo horário (2026-08-15 17:00)
✅ Histórico registrado ({timestamp, anterior, novo, motivo})
✅ Status permanece "confirmado"
❌ NÃO cancelar + criar
❌ NÃO trocar event_id
```

**Estado final:**
```
evento = {
  id: "EVT123",  ← MESMO
  data: "2026-08-15",
  hora_inicio: "17:00",
  duracao: 30,
  profissional: "Carla",
  status: "confirmado",
  historico_alteracoes: [{
    timestamp: "2026-08-11T18:30:00",
    anterior: {data: "2026-08-14", hora: "14:30"},
    novo: {data: "2026-08-15", hora: "17:00"},
    motivo: "Reagendamento do cliente",
    usuario: "cliente_001"
  }]
}
estado_fluxo: "idle"
```

---

## E2E — 13 Cenários

### Cenário 1: Detecção
```
Cliente: "Quero remarcar"
       ↓
Bot: Intenção detectada
Bot: Lista agendamentos ou pergunta
```
**Gate validado:** 1 (Detecção)  
**Esperado:** estado_fluxo = "aguardando_identificacao_evento"

---

### Cenário 2: Identificação automática (1 evento)
```
Cliente: "Quero remarcar" (só tem 1 agendamento)
       ↓
Bot: "Para qual horário?"
```
**Gate validado:** 2 (Identificação)  
**Esperado:** evento_id identificado, evento_fluxo = "aguardando_novo_horario"

---

### Cenário 3: Identificação por lista (N eventos)
```
Cliente: "Quero remarcar" (tem 2+ agendamentos)
       ↓
Bot: "Qual você quer alterar?"
     "1. Manicure — quinta às 14h"
     "2. Corte — sexta às 10h"

Cliente: "1"
       ↓
Bot: "Para qual horário?"
```
**Gate validado:** 2 (Identificação)  
**Esperado:** evento_id selecionado, estado_fluxo = "aguardando_novo_horario"

---

### Cenário 4: Novo horário simples
```
Cliente: "Quero remarcar"
Bot: "Para qual horário?"

Cliente: "amanhã às 15h"
       ↓
Motor: Interpreta e valida
```
**Gate validado:** 3 (Novo Horário)  
**Esperado:** data e hora calculadas corretamente

---

### Cenário 5: Novo horário — formato flexível
```
Cliente: "sexta-feira"
Cliente: "às 5 da tarde"
Cliente: "segunda 16:30"
       ↓
Todos devem ser interpretados corretamente
```
**Gate validado:** 3 (Novo Horário)  
**Esperado:** data/hora normalizadas independente do formato

---

### Cenário 6: Horário livre (sem conflito)
```
Cliente: "Quero remarcar"
Bot: "Para qual horário?"

Cliente: "segunda às 17h"
Motor: Sem conflito
       ↓
Bot: "Perfeito! Vou mudar para segunda às 17h."
     "Confirma?"
```
**Gate validado:** 4 (Conflito — LIVRE)  
**Esperado:** estado_fluxo = "aguardando_confirmacao"

---

### Cenário 7: Horário ocupado (conflito)
```
Cliente: "Quero remarcar"
Bot: "Para qual horário?"

Cliente: "terça às 15h" (está ocupado)
Motor: Conflito detectado
       ↓
Bot: "Esse horário está ocupado."
     "Posso oferecer:"
     "1. 15:30"
     "2. 16:00"
     "3. 17:00"
```
**Gate validado:** 4 (Conflito — OCUPADO)  
**Esperado:** Motor oferece alternativas

---

### Cenário 8: Cliente escolhe alternativa
```
Bot: [oferece 3 alternativas]

Cliente: "2"
Motor: Revalida a opção 2 (16:00)
       ↓
Bot: "Perfeito! Segunda às 16h."
     "Confirma?"
```
**Gate validado:** 4 (Conflito — REVALIDAÇÃO)  
**Esperado:** Alternativa validada, pede confirmação

---

### Cenário 9: Confirmação positiva
```
Bot: "Confirma a mudança para segunda às 16h?"

Cliente: "Sim"
       ↓
Motor: alterar_agendamento()
Bot: "Pronto! Alterado."
```
**Gate validado:** 5 (Confirmação — SIM)  
**Esperado:** Evento alterado, histórico registrado

---

### Cenário 10: Rejeição (não altera)
```
Bot: "Confirma a mudança para segunda às 16h?"

Cliente: "Não"
       ↓
Bot: "Certo, não altero nada."
Motor: NÃO chama alterar_agendamento()
```
**Gate validado:** 5 (Confirmação — NÃO)  
**Esperado:** Evento NÃO alterado

---

### Cenário 11: Evento preserva ID
```
Antes:  evento_id = "EVT123"

Cliente: [fluxo completo]

Depois: evento_id = "EVT123"  ← MESMO
        NOT "EVT456" (novo)
```
**Gate validado:** 6 (Persistência — ID)  
**Esperado:** event_id preservado

---

### Cenário 12: Histórico registrado
```
Após alteração:

evento.historico_alteracoes = [{
  timestamp: "...",
  anterior: {data: "2026-08-14", hora: "14:30"},
  novo: {data: "2026-08-15", hora: "17:00"},
  motivo: "Reagendamento do cliente"
}]
```
**Gate validado:** 6 (Persistência — Histórico)  
**Esperado:** Array com registro da alteração

---

### Cenário 13: Tenant isolado
```
Cliente A (tenant A): Altera evento
Cliente B (tenant B): NÃO vê evento de A

Motor valida:
  ├─ alteração de A em tenant A ✅
  ├─ consulta de B em tenant B ✅
  └─ isolamento mantido ✅
```
**Gate validado:** Todos (multi-tenant preservado)  
**Esperado:** Dados isolados por tenant

---

## CENÁRIO CRÍTICO — Máquina de Estados Completa

Este é o teste que PROVA que toda a máquina de estados funciona:

```
Cliente: "Quero mudar meu horário"
↓
Estado 1: "aguardando_identificacao_evento"

Bot: "Qual agendamento?"
"1. Manicure — quinta às 14h"
"2. Corte — sexta às 10h"

Cliente: "o de amanhã"
↓
[Motor resolve ambiguidade]

Bot: "Para qual horário?"
↓
Estado 2: "aguardando_novo_horario"

Cliente: "15h"
↓
Motor: Valida conflito

[Conflito detectado]
↓
Estado 3: "oferecendo_alternativas"

Bot: "15h está ocupado. Tenho 16h ou 17h."

Cliente: "16h"
↓
Motor: Revalida 16h

[Sem conflito]
↓
Estado 4: "aguardando_confirmacao"

Bot: "Confirmar para amanhã às 16h?"

Cliente: "sim"
↓
Motor: alterar_agendamento(
  evento_id="EVT123",
  nova_data="2026-08-15",
  nova_hora="16:00"
)
↓
Estado 5: "idle"

Bot: "Pronto! Seu agendamento foi alterado."

✅ Evento alterado
✅ evento_id = "EVT123" (mesmo)
✅ Histórico registrado
✅ Status confirmado
✅ Contexto limpo
```

**Este é o teste que prova tudo funciona.**

---

## Definição de Pronto

P0 está **PRONTO quando:**

```
✅ Gate 1: Detecção funciona (13 mensagens reconhecidas)
✅ Gate 2: Identificação funciona (1 evento auto, N eventos por lista)
✅ Gate 3: Novo horário funciona (5 formatos diferentes)
✅ Gate 4: Conflito funciona (livre e ocupado, revalidação)
✅ Gate 5: Confirmação funciona (sim/não)
✅ Gate 6: Persistência funciona (evento_id preservado, histórico)
✅ E2E 13 cenários: TODOS PASSAM
✅ Cenário crítico: Máquina de estados completa funciona
✅ Regressão: P0 174/174 continuam PASS
✅ Regressão: P1 42/42 continuam PASS
```

---

## Depois do P0

Quando este E2E estiver verde:

```
AUDITORIA v1 (2026-08-11): 229/242
    ├─ Classificações POSSIVELMENTE incorretas
    ├─ Motor não validado
    └─ Fluxos não testados

AUDITORIA v2 (depois do P0): CANÔNICA
    ├─ Domínio + fluxos VALIDADOS
    ├─ Testes REAIS rodando
    └─ Inventário CONFIÁVEL

Com essa base, podemos responder:
  - Retorno automático: lacuna ou já existe?
  - Ranking inteligente: roadmap ou tech debt?
  - Dashboard: novo ou extensão?
  - Alertas: feature ou infra?
  - Churn: produto ou vendas?
  - Serviços complementares: inovação ou pilar existente?
  - Evolução lista de espera: prioridade ou detalhe?
```

---

## Timeline Estimada

| Fase | Tempo | Gate |
|------|-------|------|
| Implementação P0 | ~4-6h | Router + bot.py + motor |
| E2E 13 cenários | ~2-3h | Testes conversacionais |
| Regressão | ~1-2h | P0/P1 suites |
| **TOTAL P0** | **~7-11h** | **PRONTO** |
| Auditoria v2 | ~2-4h | Inventário canônico |

---

**Status:** P0 Especificação completa, pronto para implementação

