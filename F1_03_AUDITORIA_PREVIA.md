# F1-03 — Auditoria Prévia: Retorno Pendente

**Data:** 2026-06-28  
**Escopo:** Marcar cliente como retorno_pendente após 15 dias de atendimento

---

## 📍 Ponto 1: Onde Evento é Marcado Concluído

### Investigação Necessária

Procurar por:
- `event_status = "concluido"`
- `evento.status = "concluido"`
- Função que marca evento como finalizado

### Hipótese Inicial

Em `services/lead_status_service.py:286` existe `registrar_atendimento()` que:
- Marca `lead_status = "atendido"`
- Define `ultimo_atendimento = now`
- Chamado quando evento.status == "concluido"

**Status:** [CONFIRMADO] F1-01 já implementou essa integração

### Impacto & Riscos

✅ **O que fazer:**
- Reutilizar campo `ultimo_atendimento` já existente
- Usar `atendimento_service.verificar_retorno_pendente()` para verificar regra temporal
- Integrar em ponto que verifica lead_status regularmente

⚠️ **Risco:**
- Se `ultimo_atendimento` não for atualizado, regra não funciona
- Garantir que F1-01 sempre seta esse campo

---

## 📍 Ponto 2: Campos Disponíveis em Clientes

### Path
`Clientes/{tenant_id}/Clientes/{cliente_actor_id}`

### Campos F1-01 Criados
```
lead_status: "novo|interessado|negociacao|agendado|atendido|retorno_pendente|inativo"
lead_status_updated_at: ISO timestamp
primeira_interacao: ISO timestamp
ultima_interacao: ISO timestamp
ultimo_atendimento: ISO timestamp (pode ser null)
total_agendamentos: integer
```

### Campos F1-03 Utilizará
- `ultimo_atendimento` — quando cliente foi atendido
- `lead_status` — será atualizado para "retorno_pendente"
- `lead_status_updated_at` — timestamp da mudança

**Status:** [CONFIRMADO] Todos os campos já existem

---

## 📍 Ponto 3: Integração — Onde Verificar Retorno Pendente

### Opção A: Batch Job (DESCARTADO)
- Exige cron job novo (proibido no escopo)
- Não é determinístico (roda em horário específico)

### Opção B: Lazy Evaluation (RECOMENDADO)
```
Quando dono consulta backlog_comercial:
    ↓
Para cada cliente em status "atendido":
    ↓
    Se (hoje - ultimo_atendimento) >= 15 dias:
        ↓
        Atualizar lead_status para "retorno_pendente"
        ↓
    Se já é "retorno_pendente":
        ↓
        Incluir na lista de retorno pendente
```

**Vantagem:** Determinístico, sem scheduler novo, sem job agendado

**Implementação:** Integrar em `listar_clientes_retorno_pendente()` do backlog_comercial_service

### Opção C: Avaliação no Fluxo (COMPLEMENTAR)
```
Quando cliente envia mensagem:
    ↓
No bot.py após lead_status_service:
    ↓
Se lead_status == "atendido" E (agora - ultimo_atendimento) >= 15 dias:
    ↓
    Atualizar para "retorno_pendente"
```

**Status:** Ambas as opções serão implementadas (B = principal, C = complementar)

---

## 📍 Ponto 4: Impacto em F1-01 e F1-02

### F1-01 (lead_status_service.py)
- Nenhuma alteração necessária
- Continua registrando `ultimo_atendimento`
- F1-03 usa esse campo, não altera lógica

**Risco:** Baixo

### F1-02 (backlog_comercial_service.py)
- `listar_retorno_pendente()` já existe
- Será aprimorado para verificar regra temporal
- Clientes "atendidos" com 15+ dias serão convertidos a "retorno_pendente"

**Risco:** Baixo (apenas leitura e atualização, não afeta consultas de outros status)

### Sessões / MemoriaTemporaria
- Nenhuma referência necessária
- Retorno pendente é estado persistido, não temporário

**Risco:** Nenhum

---

## 📍 Ponto 5: Regras de Transição

### Transições Permitidas

```
atendido --(15+ dias sem novo agendamento)--> retorno_pendente
retorno_pendente --(novo agendamento)--> agendado
retorno_pendente --(nova consulta/mensagem)--> volta a lead_status normal
```

### Não Permitido (Escopo)
- ❌ FollowUps
- ❌ followup_scheduler
- ❌ mensagens automáticas
- ❌ WhatsApp automático
- ❌ notificações
- ❌ cron jobs

### Determinístico
- ✅ Apenas query de timestamp
- ✅ Sem GPT
- ✅ Sem IA

---

## 📊 Sumário de Impacto

### Arquivos a Criar

1. **services/retorno_pendente_service.py** (NOVO)
   - Lógica de verificação temporal
   - Atualização de status
   - Idempotência

2. **tests/test_f1_03_retorno_pendente_firestore.py** (NOVO)
   - 10 testes Firebase

### Arquivos a Modificar

1. **services/backlog_comercial_service.py**
   - `listar_retorno_pendente()` aprimorada
   - Verificação temporal integrada
   - **IMPACTO:** Mínimo (adiciona lógica, não altera interface)

2. **handlers/bot.py** (POSSÍVEL)
   - [OPCIONAL] Após lead_status_service
   - Verificar retorno_pendente também
   - **IMPACTO:** Mínimo (nova branch, não altera fluxo existente)

### Arquivos NÃO a Modificar

✅ Não alterar:
- lead_status_service (F1-01)
- agenda, conflito, disponibilidade
- gpt_service (GPT não decide)
- followup_scheduler (não recriar)
- Sessões

---

## 🚨 Pendências de Investigação

1. **Onde exatamente evento é marcado concluído?**
   - Em qual handler?
   - Em qual função?
   - Firestore path?

2. **Existe integração atual entre evento.status=="concluido" e lead_status?**
   - F1-01 está sendo chamado?
   - `registrar_atendimento()` está sendo acionado?

---

**Próximo passo:** Implementar retorno_pendente_service.py + testes
