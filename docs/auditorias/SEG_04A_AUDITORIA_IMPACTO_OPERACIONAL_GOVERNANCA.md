# SEG-04A — AUDITORIA DE IMPACTO OPERACIONAL
## Matriz de Fluxos e Mecanismos de Governança

**Status:** Auditoria Completa (Sem Implementação)  
**Data:** 2026-06-23  
**Baseline:** 216/216 PASS (Congelado)  
**Escopo:** 20 fluxos operacionais + 7 casos limite  

---

## RESUMO EXECUTIVO

### Achados Críticos

⚠️ **Conflito 1: Pausado vs Ação Importante**
- Contato pausado não pode confirmar agendamento existente
- Risco: Agendamento fica pendente indefinidamente
- **Recomendação:** Whitelist confirmação de ações próprias

⚠️ **Conflito 2: Dono Silencioso vs Legítima Operação**
- Dono em silencioso não pode consultar própria agenda
- Risco: Dono sem acesso a informações do próprio negócio
- **Recomendação:** Diferenciação entre consulta (permitir) e resposta (bloquear)

⚠️ **Conflito 3: Lembretes e Notificações**
- Pausado não recebe lembretes/notificações
- Risco: Cliente perde confirmação, dono perde alertas
- **Recomendação:** Separar automação de mensagem (respeita pausa) de sistemas (ignora pausa)

✅ **Consenso: Onboarding, Cancelamento, Profissional**
- Sem conflitos óbvios
- Pronto para implementação

---

## 1. MATRIZ DE FLUXOS

### Legenda

| Sigla | Significado |
|-------|-------------|
| **A** | Ignora governança (sempre executa) |
| **B** | Respeita governança (pode ser bloqueado) |
| **C** | Respeita parcialmente governança |
| **D** | Requer decisão arquitetural |

---

### 1.1 Agendamento Novo

**Fluxo:** Cliente envia "Agende corte com Bruna amanhã 15h"

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **B** — Respeita governança |
| **Bloqueia?** | SIM (se pausado) |
| **Deve bloquear?** | SIM, é ação ativa |
| **Quem bloqueia?** | MEC-03 (contato pausado) |
| **Mecanismo** | responder_automaticamente = false |
| **Consequência** | Retorna "Estou pausado" |
| **Risco** | ✅ BAIXO (pausado quer pausar) |
| **Recomendação** | ✅ Bloquear, comportamento esperado |

---

### 1.2 Ajuste Incremental

**Fluxo:** Cliente responde "Mas prefiro 16h" durante agendamento

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **C** — Respeita parcialmente |
| **Bloqueia?** | SIM (se pausado no meio do fluxo) |
| **Deve bloquear?** | ⚠️ PARCIAL — interrompe fluxo existente |
| **Quem bloqueia?** | MEC-03 (contato pausado) |
| **Mecanismo** | responder_automaticamente = false |
| **Consequência** | Ajuste não é processado, volta a "Estou pausado" |
| **Risco** | ⚠️ MÉDIO (cliente quer mudar, mas é pausado) |
| **Recomendação** | ⚠️ Permitir continuidade de fluxo ativo (DECISÃO ARQUITETURAL) |

**Nota:** Pausado durante fluxo = diferente de pausado em mensagem nova.

---

### 1.3 Confirmação Pendente

**Fluxo:** Sistema aguarda "sim/não" para confirmar agendamento

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **D** — Requer decisão |
| **Bloqueia?** | SIM (se pausado) |
| **Deve bloquear?** | ❓ DEPENDE |
| **Quem bloqueia?** | MEC-03 (contato pausado) |
| **Mecanismo** | responder_automaticamente = false |
| **Consequência** | "sim/não" não é processado, fica pendente |
| **Risco** | 🔴 CRÍTICO (agendamento fica travado) |
| **Recomendação** | 🔴 **WHITELIST:** Permitir sim/não em confirmação pendente |

**Justificativa:**
- Pausado NÃO deve evitar NOVAS ações ("Agende")
- Pausado PODE continuar ações EXISTENTES ("sim" para agenda proposta)
- Diferença: Ação ativa vs resposta passiva

---

### 1.4 Cancelamento

**Fluxo:** Cliente envia "Cancelar meu agendamento de amanhã"

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **A** — Ignora governança |
| **Bloqueia?** | NÃO |
| **Deve bloquear?** | NÃO, é direito do cliente |
| **Quem bloqueia?** | Nenhum |
| **Mecanismo** | Nenhum |
| **Consequência** | Cancelamento é processado normalmente |
| **Risco** | ✅ BAIXO |
| **Recomendação** | ✅ **PRIORIDADE 1:** Nunca bloquear cancelamento |

**Justificativa:** Cliente tem direito de se desagendar mesmo pausado.

---

### 1.5 Consulta de Agenda

**Fluxo:** Cliente/Dono envia "Qual é meu horário?"

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **C** — Respeita parcialmente |
| **Bloqueia?** | SIM (se pausado/silencioso) |
| **Deve bloquear?** | ⚠️ DEPENDE DO ATOR |
| **Quem bloqueia?** | MEC-03 (pausado) + MEC-04 (dono silencioso) |
| **Mecanismo** | responder_automaticamente = false OU modo_dono = silencioso |
| **Consequência** | "Estou pausado" / "Modo silencioso" |
| **Risco** | ⚠️ MÉDIO (dono sem acesso a informação própria) |
| **Recomendação** | ⚠️ **DECISÃO ARQUITETURAL:** Diferenciação |

**Análise por Ator:**
- **Cliente pausado:** Bloquear ✅ (coerente com pausa)
- **Dono silencioso:** Permitir ❓ (informação do próprio negócio)

---

### 1.6 Consulta de Disponibilidade

**Fluxo:** Cliente/Dono envia "Quando tem horário disponível?"

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **B** — Respeita governança |
| **Bloqueia?** | SIM (se pausado/silencioso) |
| **Deve bloquear?** | SIM, é ação ativa (procura por agendamento) |
| **Quem bloqueia?** | MEC-03 (pausado) + MEC-04 (dono silencioso) |
| **Mecanismo** | responder_automaticamente = false OU modo_dono = silencioso |
| **Consequência** | "Estou pausado" / "Modo silencioso" |
| **Risco** | ✅ BAIXO |
| **Recomendação** | ✅ Bloquear, é ação ativa |

---

### 1.7 Conflito + Sugestões

**Fluxo:** Sistema detecta conflito de horário e oferece alternativas

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **C** — Respeita parcialmente |
| **Bloqueia?** | SIM (se pausado) |
| **Deve bloquear?** | ⚠️ PARCIAL |
| **Quem bloqueia?** | MEC-03 (pausado) |
| **Mecanismo** | responder_automaticamente = false |
| **Consequência** | Sugestões não são enviadas |
| **Risco** | ⚠️ MÉDIO (está meio fluxo) |
| **Recomendação** | ⚠️ Permitir sugestões de alternativa (continuidade) |

---

### 1.8 Fluxo Onboarding

**Fluxo:** Dono novo entra, sistema ativa onboarding

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **A** — Ignora governança |
| **Bloqueia?** | NÃO |
| **Deve bloquear?** | NÃO |
| **Quem bloqueia?** | Nenhum |
| **Mecanismo** | Nenhum |
| **Consequência** | Onboarding executa normalmente |
| **Risco** | ✅ BAIXO |
| **Recomendação** | ✅ **PRIORIDADE 1:** Nunca bloquear onboarding |

**Justificativa:** Onboarding é pré-requisito. Dono precisa ativar governança.

---

### 1.9 Cadastro Administrativo

**Fluxo:** Admin/Dono cadastra novo profissional ou cliente

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **C** — Respeita parcialmente |
| **Bloqueia?** | SIM (se dono silencioso) |
| **Deve bloquear?** | ⚠️ DEPENDE DO CONTEXTO |
| **Quem bloqueia?** | MEC-04 (dono silencioso = sem IA) |
| **Mecanismo** | modo_dono = silencioso |
| **Consequência** | Cadastro não processa (precisa humano?) |
| **Risco** | ⚠️ MÉDIO (operação administrativa) |
| **Recomendação** | ⚠️ **DECISÃO:** Silencioso = sem IA, mas cadastro direto (manual) funciona? |

---

### 1.10 Comandos Administrativos

**Fluxo:** Dono executa /pausar, /retomar, /silencioso, /admin, /normal

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **A** — Ignora governança |
| **Bloqueia?** | NÃO |
| **Deve bloquear?** | NÃO |
| **Quem bloqueia?** | Nenhum (comandos são meta-operações) |
| **Mecanismo** | Nenhum |
| **Consequência** | Comandos executam mesmo que pausado/silencioso |
| **Risco** | ✅ BAIXO |
| **Recomendação** | ✅ **PRIORIDADE 1:** Comandos sempre funcionam |

**Justificativa:** Se pausado, precisa de /retomar. Se silencioso, precisa de /normal.

---

### 1.11 Lembretes Automáticos

**Fluxo:** Sistema envia "Lembrança: seu agendamento é amanhã às 15h"

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **D** — Requer decisão |
| **Bloqueia?** | ⚠️ DEPENDE |
| **Deve bloquear?** | ❓ DEPENDE DA POLÍTICA |
| **Quem bloqueia?** | MEC-03 (pausado) |
| **Mecanismo** | responder_automaticamente = false |
| **Consequência** | Lembrete não é enviado |
| **Risco** | 🔴 CRÍTICO (cliente perde confirmação) |
| **Recomendação** | 🔴 **SEPARAR:** Automação (bloqueia) vs Sistemas (ignora) |

**Conceito:** 
- Automação IA: Responde conversas (pausado bloqueia) ✅
- Sistemas de negócio: Notificações (pausado IGNORA pausa) ❓

---

### 1.12 Notificações Automáticas

**Fluxo:** Sistema notifica "Seu profissional confirmou..." ou "Cancelado por..."

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **D** — Requer decisão |
| **Bloqueia?** | ⚠️ DEPENDE |
| **Deve bloquear?** | ❓ DEPENDE DA POLÍTICA |
| **Quem bloqueia?** | MEC-03 (pausado) |
| **Mecanismo** | responder_automaticamente = false |
| **Consequência** | Notificação não é enviada |
| **Risco** | 🔴 CRÍTICO (cliente não sabe status) |
| **Recomendação** | 🔴 **SEPARAR:** Automação (bloqueia) vs Notificação (permite) |

---

### 1.13 Histórico

**Fluxo:** Cliente/Dono pede "Quais foram meus agendamentos anteriores?"

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **B** — Respeita governança |
| **Bloqueia?** | SIM (se pausado/silencioso) |
| **Deve bloquear?** | ⚠️ PARCIAL (é consulta histórica, não ação) |
| **Quem bloqueia?** | MEC-03 + MEC-04 |
| **Mecanismo** | responder_automaticamente = false OU modo_dono = silencioso |
| **Consequência** | "Estou pausado" |
| **Risco** | ⚠️ MÉDIO (informação leitura) |
| **Recomendação** | ⚠️ Permitir leitura histórico (informação passada) |

---

### 1.14 ClienteProfile

**Fluxo:** Sistema acessa perfil do cliente (nome, telefone, preferências)

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **A** — Ignora governança |
| **Bloqueia?** | NÃO |
| **Deve bloquear?** | NÃO |
| **Quem bloqueia?** | Nenhum (é dado de sistema) |
| **Mecanismo** | Nenhum |
| **Consequência** | Perfil é carregado normalmente |
| **Risco** | ✅ BAIXO |
| **Recomendação** | ✅ Nunca bloquear acesso a perfil |

---

### 1.15 Follow-up Futuro

**Fluxo:** Sistema agenda follow-up automático "Você quer marcar próximo corte?"

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **B** — Respeita governança |
| **Bloqueia?** | SIM (se pausado) |
| **Deve bloquear?** | SIM, é ação ativa |
| **Quem bloqueia?** | MEC-03 (pausado) |
| **Mecanismo** | responder_automaticamente = false |
| **Consequência** | Follow-up não é enviado |
| **Risco** | ✅ BAIXO (coerente com pausa) |
| **Recomendação** | ✅ Bloquear, é ação ativa |

---

### 1.16 Retorno de Cliente

**Fluxo:** Cliente que foi cancelado volta após dias, sistema reconhece

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **A** — Ignora governança |
| **Bloqueia?** | NÃO |
| **Deve bloquear?** | NÃO |
| **Quem bloqueia?** | Nenhum (é novo fluxo) |
| **Mecanismo** | Nenhum |
| **Consequência** | Cliente volta ao fluxo normal |
| **Risco** | ✅ BAIXO |
| **Recomendação** | ✅ Permitir retorno |

**Nota:** Se cliente volta, pausa anterior não mais aplica (nova sessão).

---

### 1.17 Profissional (Fluxo)

**Fluxo:** Profissional envia mensagem operacional (ex: "Tenho conflito com Bruna")

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **D** — Requer decisão futura |
| **Bloqueia?** | NÃO (em Sprint 1) |
| **Deve bloquear?** | ❓ SIM (MEC-05, futuro) |
| **Quem bloqueia?** | Nenhum em Sprint 1; MEC-05 em Sprint 2 |
| **Mecanismo** | tipo_usuario = profissional (futuro) |
| **Consequência** | Resposta IA normal (será mudada) |
| **Risco** | ⚠️ MÉDIO (comportamento mudará) |
| **Recomendação** | ⚠️ Documentar para MEC-05 (Sprint 2) |

---

### 1.18 Dono (Fluxo)

**Fluxo:** Dono envia mensagem pessoal (ex: "Como você está?")

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **B** — Respeita governança |
| **Bloqueia?** | DEPENDE do modo |
| **Deve bloquear?** | SIM (modo silencioso), NÃO (modo normal) |
| **Quem bloqueia?** | MEC-04 (modo_dono) |
| **Mecanismo** | modo_dono = silencioso OU admin |
| **Consequência** | Resposta bloqueada se silencioso/admin |
| **Risco** | ✅ BAIXO (esperado) |
| **Recomendação** | ✅ Bloquear conforme modo |

---

### 1.19 Cliente Identificado

**Fluxo:** Cliente com histórico entra, sistema carrega contexto

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **A** — Ignora governança |
| **Bloqueia?** | NÃO |
| **Deve bloquear?** | NÃO |
| **Quem bloqueia?** | Nenhum (é carregamento de contexto) |
| **Mecanismo** | Nenhum |
| **Consequência** | Contexto é carregado normalmente |
| **Risco** | ✅ BAIXO |
| **Recomendação** | ✅ Sempre carregar contexto, depois aplicar governança |

---

### 1.20 Contato Desconhecido

**Fluxo:** Número novo entra, sistema sem histórico

| Aspecto | Análise |
|---------|---------|
| **Categoria** | **A** — Ignora governança |
| **Bloqueia?** | NÃO |
| **Deve bloquear?** | NÃO |
| **Quem bloqueia?** | Nenhum (sem Governanca doc) |
| **Mecanismo** | Nenhum (default = responder_automaticamente = true) |
| **Consequência** | Fluxo normal |
| **Risco** | ✅ BAIXO |
| **Recomendação** | ✅ Primeira mensagem não é bloqueada |

---

## 2. RESUMO DA MATRIZ

### Por Categoria

| Categoria | Fluxos | Exemplo |
|-----------|--------|---------|
| **A** — Ignora | 7 | Onboarding, Cancelamento, Comandos |
| **B** — Respeita | 7 | Agendamento, Disponibilidade, Dono |
| **C** — Parcial | 4 | Ajuste incremental, Conflito, Cadastro |
| **D** — Decisão | 2 | Confirmação pendente, Lembretes |

---

### Resumo por Bloqueio

| Fluxo | Pausado (MEC-03) | Silencioso (MEC-04) | Recomendação |
|-------|-----------------|-------------------|--------------|
| Agendamento novo | ✅ Bloqueia | ✅ Bloqueia | Esperado |
| Confirmação pendente | ⚠️ Whitelist | — | DECISÃO |
| Cancelamento | ❌ Permite | ❌ Permite | PRIORIDADE 1 |
| Consulta agenda | ✅ Bloqueia | ⚠️ Whitelist | DECISÃO |
| Lembretes | ⚠️ SEPARA | ⚠️ SEPARA | DECISÃO |
| Notificações | ⚠️ SEPARA | ⚠️ SEPARA | DECISÃO |
| Comandos admin | ❌ Permite | ❌ Permite | PRIORIDADE 1 |
| Onboarding | ❌ Permite | ❌ Permite | PRIORIDADE 1 |

---

## 3. CASOS LIMITE

### CASO 01: Contato Pausado Cancela Horário

**Cenário:**
```
Contato pausado envia: "quero cancelar meu horário de amanhã"
```

**Análise:**

| Aspecto | Decisão |
|---------|---------|
| **Bloqueia?** | ❌ NÃO |
| **Permite?** | ✅ SIM |
| **Justificativa** | Cancelamento é direito do cliente, mesmo pausado |
| **Categoria** | **PRIORIDADE 1:** Nunca bloquear cancelamento |
| **Implementação** | Whitelist: comandos de CANCELAMENTO ≠ comandos de AGENDAMENTO |
| **Risco** | ✅ BAIXO |

**Recomendação:**
```
Se pausado AND mensagem é cancelamento:
    → Executar cancelamento
Else se pausado:
    → Bloquear com "Estou pausado"
```

---

### CASO 02: Contato Pausado Confirma Agendamento

**Cenário:**
```
Contato pausado durante fluxo de confirmação:
Sistema: "Confirma agendamento para amanhã 15h? Responda sim/não"
Contato: "sim"
```

**Análise:**

| Aspecto | Decisão |
|---------|---------|
| **Bloqueia?** | ⚠️ DEPENDE |
| **Permite?** | ⚠️ DEPENDE |
| **Justificativa** | Confirmação = continuidade de fluxo existente, NÃO ação nova |
| **Categoria** | **WHITELIST:** Confirmação pending respeitada mesmo pausado |
| **Implementação** | If estado_fluxo == "aguardando_confirmacao" → Permitir sim/não |
| **Risco** | 🔴 CRÍTICO se blocar (agendamento fica pendente) |

**Recomendação:**
```
Se pausado AND estado_fluxo == "aguardando_confirmacao":
    → Processar "sim/não"
Else se pausado AND nova_acao:
    → Bloquear com "Estou pausado"
```

---

### CASO 03: Dono Silencioso Consulta Agenda

**Cenário:**
```
Dono em modo silencioso envia: "agenda de amanhã"
```

**Análise:**

| Aspecto | Decisão |
|---------|---------|
| **É comando?** | ❌ NÃO é /comando |
| **É mensagem comum?** | ✅ SIM |
| **Deve executar?** | ⚠️ DEPENDE DA ARQUITETURA |
| **Risco** | ⚠️ MÉDIO (dono sem acesso à própria agenda) |
| **Categoria** | **DECISÃO ARQUITETURAL** |

**Opções:**

**Opção A: Bloquear (silencioso = sem IA)**
```
Dono silencioso: "agenda de amanhã"
→ "Modo silencioso, não respondo"
```
✅ Simples  
❌ Dono fica sem acesso a informação própria

**Opção B: Permitir leitura, bloquear ação (recomendado)**
```
Dono silencioso: "agenda de amanhã"
→ Retorna agenda (informação)

Dono silencioso: "cancela horário de Bruna"
→ "Modo silencioso, não respondo" (ação)
```
✅ Respeita informação vs ação  
⚠️ Mais complexo

**Recomendação:**
```
modo_dono = silencioso → Diferenciar:
  - Consultas leitura (agenda, histórico) → PERMITIR
  - Ações (agendar, cancelar, alterar) → BLOQUEAR
```

---

### CASO 04: Dono Silencioso Quer Marcar Corte

**Cenário:**
```
Dono em modo silencioso envia: "quero marcar corte amanhã"
```

**Análise:**

| Aspecto | Decisão |
|---------|---------|
| **Deve responder?** | ❌ NÃO |
| **Deve ignorar?** | ✅ SIM |
| **Justificativa** | Silencioso = sem IA, sem resposta automática |
| **Categoria** | **ESPERADO** |
| **Implementação** | MEC-04: modo_dono = silencioso → Bloqueia resposta |
| **Risco** | ✅ BAIXO (é intenção) |

**Recomendação:**
```
Se dono AND modo_dono = "silencioso":
    → Retorna "Modo silencioso ativado"
Else se dono AND modo_dono = "normal":
    → Processa agendamento normal
```

---

### CASO 05: Profissional Bloqueia Agenda

**Cenário:**
```
Profissional envia: "bloqueia minha agenda amanhã"
```

**Análise:**

| Aspecto | Decisão |
|---------|---------|
| **Deve ser tratado?** | ⚠️ DEPENDE DE MEC-05 |
| **Deve ser ignorado?** | ⚠️ ATÉ QUE MEC-05 EXISTA |
| **Precisa de decisão futura?** | ✅ SIM, é escopo Sprint 2 |
| **Categoria** | **SPRINT 2** (MEC-05 — Profissional) |
| **Implementação** | Nenhuma em Sprint 1 |
| **Risco** | ⚠️ MÉDIO (será mudado) |

**Recomendação:**
```
Sprint 1: Sem mudança, profissional recebe resposta normal
Sprint 2: Implementar MEC-05, profissional fica silencioso por padrão
```

---

### CASO 06: Contato Pausado Recebe Lembrete

**Cenário:**
```
Contato pausado anteriormente.
Sistema automático: "Lembrança: seu agendamento é amanhã às 15h"
```

**Análise:**

| Aspecto | Decisão |
|---------|---------|
| **Lembrete continua?** | ⚠️ DEPENDE |
| **Lembrete para?** | ⚠️ DEPENDE |
| **Justificativa** | Separação: Automação IA (bloqueia) vs Sistemas (continua) |
| **Categoria** | **DECISÃO ARQUITETURAL CRÍTICA** |
| **Risco** | 🔴 CRÍTICO (cliente perde confirmação) |

**Opção A: Bloquear (responder_automaticamente = false bloqueia tudo)**
```
Pausado recebe: "Lembrança: seu agendamento é amanhã"
→ NÃO recebe (bloqueado)
```
❌ Risco crítico: Cliente perde confirmação

**Opção B: Separar canais (RECOMENDADO)**
```
responder_automaticamente = false:
  - Bloqueia: Respostas IA, agendamentos, consultas
  - Permite: Lembretes, notificações, alertas de status

Implementação: 
  - Automação conversacional → verifica governanca
  - Sistemas de negócio → ignora governanca
```
✅ Cliente recebe informações críticas  
✅ Resposta IA é pausada  
⚠️ Requer duplicação de lógica

**Recomendação:**
```
Criar dois fluxos:
  1. Automacao(user_id, dono_id) → Respeita governanca
  2. Notificacao(user_id) → Ignora governanca

Lembretes usam Notificacao (ignora pausa)
Respostas IA usam Automacao (respeita pausa)
```

---

### CASO 07: Contato Pausado Recebe Notificação

**Cenário:**
```
Contato pausado anteriormente.
Sistema notifica: "Seu profissional confirmou para amanhã"
```

**Análise:**

| Aspecto | Decisão |
|---------|---------|
| **Continua?** | ✅ SIM |
| **Para quem?** | Contato pausado |
| **Justificativa** | Notificação ≠ Automação; cliente precisa saber status |
| **Categoria** | **PRIORIDADE IMPLÍCITA:** Notificações sempre chegam |
| **Risco** | 🔴 CRÍTICO se blocar (cliente não sabe status) |

**Recomendação:**
```
Notificação de status (confirmação, cancelamento, alteração):
  → Sempre enviado, ignora pausa
  
Resposta automática IA:
  → Bloqueia quando pausado
  
Diferença:
  - Notificação = Informação de sistema
  - Resposta = Automação conversacional
```

---

## 4. PRIORIDADES DE BLOQUEIO

### PRIORIDADE 1: Nunca Bloquear

❌ Nunca pausar ou bloquear estes fluxos, independente da governança:

```
□ Onboarding (pré-requisito)
□ Cancelamento (direito do cliente)
□ Comandos administrativos (/pausar, /retomar, /status, /silencioso, /admin, /normal)
□ Notificações de sistema (status de agendamento)
□ Lembretes de confirmação (cliente precisa lembrar)
□ ClienteProfile (acesso a perfil próprio)
□ Retorno de cliente (nova sessão, sem pausa anterior)
□ Confirmação de ação própria (sim/não em aguardando_confirmacao)
□ Cancelamento por requisição (mesmo que pausado)
```

**Critério:** Operações que removem agência do cliente ou causam bloqueio permanente.

---

### PRIORIDADE 2: Pode Bloquear

⚠️ Bloquear se governança ativa, mas não é crítico:

```
□ Agendamento novo (cliente quer pausar)
□ Consulta de disponibilidade (cliente quer pausar)
□ Consulta de agenda (DECISÃO: para cliente sim, para dono depende)
□ Follow-up futuro (ação ativa)
□ Ajuste incremental (continuidade de fluxo)
□ Conflito + sugestões (continuidade de fluxo)
```

**Critério:** Ações que cliente pode postergar, mas deixam fluxo limpo.

---

### PRIORIDADE 3: Bloquear Sempre

🔴 Bloquear se governança ativa, é intenção clara:

```
□ Dono modo silencioso recebe resposta IA (é silencioso)
□ Dono modo admin só executa admin (é admin)
```

**Critério:** Operações que são a intenção exata da governança.

---

## 5. CONFLITOS ARQUITETURAIS IDENTIFICADOS

### CONFLITO A: Pausa vs Ação Importante

**Problema:**
```
responder_automaticamente = false (MEC-03) bloqueia TUDO
Mas cliente pausado quer:
  - Confirmar agendamento existente
  - Cancelar horário
  - Retirar pausa
```

**Impacto:**
- 🔴 CRÍTICO: Agendamento fica pendente
- 🔴 CRÍTICO: Cliente sem forma de desfazer pausa
- ⚠️ MÉDIO: Cliente sem forma de cancelar

**Solução Recomendada:**
```
responder_automaticamente = false:
  ✅ Bloqueia: Novas ações (agendamento, consulta)
  ✅ Bloqueia: Automação IA (resposta conversacional)
  ✅ Permite: Ações de próprio cliente (sim/não, cancelar)
  ✅ Permite: Comandos (/pausar, /retomar)

Whitelist:
  - Confirmação pendente (sim/não)
  - Cancelamento (cancelar horário)
  - Comandos administrativos
```

**Implementação em Sprint 1:**
```python
if governanca.get("responder_automaticamente") == False:
    # Whitelists
    if estado_fluxo == "aguardando_confirmacao" and msg in ["sim", "não"]:
        → Processar confirmação
    elif eh_comando_cancelamento(msg):
        → Processar cancelamento
    elif eh_comando_admin(msg):
        → Processar comando
    else:
        → Bloquear com "Estou pausado"
```

---

### CONFLITO B: Dono Silencioso vs Negócio

**Problema:**
```
modo_dono = "silencioso" (MEC-04) bloqueia resposta IA
Mas dono quer:
  - Consultar agenda de seu negócio
  - Saber histórico
  - Receber alertas importantes
```

**Impacto:**
- ⚠️ MÉDIO: Dono sem acesso a informação do negócio
- ⚠️ MÉDIO: Dono sem alertas críticos
- ✅ BAIXO: É intenção, mas operacional inadequado

**Solução Recomendada:**
```
modo_dono = "silencioso":
  ✅ Bloqueia: Respostas IA (conversação)
  ✅ Bloqueia: Agendamentos novos (ação)
  ⚠️ Permite (DECISÃO): Consultas de leitura (agenda)
  ⚠️ Permite (DECISÃO): Alertas críticos (cancelamento)

Diferenciar:
  - Leitura (agenda, histórico) → INFORMAÇÃO
  - Ação (agendar, cancelar) → OPERAÇÃO
  - Resposta IA → AUTOMAÇÃO
```

**Implementação em Sprint 1:**
```python
if user_id == dono_id and governanca.get("modo_dono") == "silencioso":
    if eh_consulta_leitura(msg):
        → Permitir (retorna informação)
    elif eh_acao(msg):
        → Bloquear (modo silencioso)
    elif eh_resposta_ia(msg):
        → Bloquear (modo silencioso)
    else:
        → Bloquear (padrão)
```

---

### CONFLITO C: Pausa vs Notificação

**Problema:**
```
responder_automaticamente = false (MEC-03) bloqueia tudo
Mas cliente pausado precisa de:
  - Lembretes de confirmação
  - Alertas de cancelamento
  - Status de agendamento
```

**Impacto:**
- 🔴 CRÍTICO: Cliente perde informação de negócio
- 🔴 CRÍTICO: Agendamento fica sem confirmação
- ⚠️ MÉDIO: Dono não sabe o que aconteceu

**Solução Recomendada:**
```
Separar dois canais:

Canal 1: Automacao (Resposta IA)
  - Respeita governanca
  - Bloqueia se pausado
  
Canal 2: Notificacao (Sistema de negócio)
  - Ignora governanca
  - Sempre envia (lembretes, alertas)

Classificação:
  - "Qual é sua disponibilidade?" → Automacao (pergunta)
  - "Lembrança: seu agendamento é amanhã" → Notificacao (alerta)
  - "Seu profissional confirmou" → Notificacao (alerta)
  - "Confirma agendamento?" → Automacao (pergunta)
```

**Implementação Futura (Sprint 3+):**
```python
# Função dispatcher
def enviar_mensagem(user_id, tipo_mensagem, corpo):
    if tipo_mensagem == "AUTOMACAO":
        governanca = carregar_governanca(user_id)
        if governanca.get("responder_automaticamente") == False:
            return  # Bloqueado
    # Ambos: Automacao e Notificacao chegam se não bloqueado
    
    send_whatsapp(user_id, corpo)
```

---

## 6. ANÁLISE DE RISCO POR FLUXO

### Riscos Críticos (Requerem Decisão antes de Implementar)

| Fluxo | Risco | Impacto | Decisão Necessária |
|-------|-------|--------|-------------------|
| Confirmação Pendente | Agendamento travado | 🔴 CRÍTICO | Whitelist sim/não |
| Lembretes | Sem confirmação | 🔴 CRÍTICO | Separar canais |
| Notificações | Sem status | 🔴 CRÍTICO | Separar canais |
| Dono Silencioso + Agenda | Sem acesso | ⚠️ MÉDIO | Diferenciar leitura/ação |
| Cancelamento | Sem opção | ⚠️ MÉDIO | Whitelist cancelar |

---

### Riscos Aceitáveis (Sem Decisão Necessária)

| Fluxo | Risco | Impacto | Motivo |
|-------|-------|--------|--------|
| Agendamento Novo | Pausado não agenda | ✅ BAIXO | É intenção |
| Consulta Disponibilidade | Pausado não consulta | ✅ BAIXO | É intenção |
| Follow-up | Sem follow-up | ✅ BAIXO | Coerente |
| Dono Normal | Comportamento atual | ✅ NENHUM | Default |

---

## 7. RECOMENDAÇÕES FINAIS

### Recomendação 1: WHITELIST de Confirmação

**Decisão Arquitetural Obrigatória**

```
Implementar em Sprint 1:

Se pausado:
  → Se aguardando_confirmacao e msg="sim"|"não":
      Permitir resposta
  → Senão:
      Bloquear
```

**Risco se não implementar:** 🔴 CRÍTICO (agendamento fica pendente)

---

### Recomendação 2: SEPARAR Canais

**Decisão Arquitetural Futura**

```
Implementar em Sprint 3+ (Pós Sprint 1):

Criar dois fluxos:
  1. automacao_ia(user_id) → responder_automaticamente?
  2. notificacao_sistema(user_id) → sempre envia
  
Lembretes e alertas usam notificacao_sistema
Respostas IA usam automacao_ia
```

**Risco se não implementar:** 🔴 CRÍTICO (cliente perde informação)

---

### Recomendação 3: DIFERENCIAR Dono

**Decisão Arquitetural Para Sprint 1+**

```
Ao implementar modo_dono = "silencioso":

Diferenciação:
  - Consultas (leitura) → PERMITIR
  - Ações (alterar) → BLOQUEAR
  - IA (resposta) → BLOQUEAR

Exemplo:
  "Minha agenda?" → Retorna agenda (leitura)
  "Cancela corte?" → "Modo silencioso" (ação)
```

**Risco se não implementar:** ⚠️ MÉDIO (dono sem acesso)

---

## 8. MATRIZ DE DECISÕES NECESSÁRIAS

### Decisões Antes de Implementar Sprint 1

| Decisão | Status | Impacto | Quando |
|---------|--------|--------|--------|
| **Whitelist Confirmação** | ✅ RECOMENDADO | 🔴 CRÍTICO | Sprint 1 |
| **Separar Canais** | ⚠️ FUTURO | 🔴 CRÍTICO | Sprint 3+ |
| **Dono Leitura/Ação** | ⚠️ FUTURO | ⚠️ MÉDIO | Sprint 2+ |

---

## 9. CHECKLIST DE COMPATIBILIDADE

### ✅ Sem Conflito (Implementar Sprint 1)

- [x] Agendamento novo (pausado bloqueia)
- [x] Cancelamento (pausado permite)
- [x] Comandos admin (sempre funcionam)
- [x] Onboarding (ignora governanca)
- [x] Dono normal (sem mudança)
- [x] ClienteProfile (sempre carrega)
- [x] Contato novo (sem governanca)
- [x] Retorno de cliente (nova sessão)

### ⚠️ Requer Decisão (Sprint 1+)

- [ ] Confirmação pendente (WHITELIST necessária)
- [ ] Lembretes (SEPARAR necessário)
- [ ] Notificações (SEPARAR necessário)
- [ ] Dono silencioso + agenda (DIFERENCIAR necessário)

### 🔴 Bloqueado para Sprint 2+

- [ ] Profissional (MEC-05)
- [ ] Contato desconhecido específico (MEC-02 fase 2)

---

## 10. PARECER FINAL

### Recomendação: IMPLEMENTAR SPRINT 1 COM WHITELISTS

**Status:** ✅ APROVADO (Com Restrições)

**Condições:**

1. ✅ **Implementar Whitelist de Confirmação**
   - Pausado pode confirmar sim/não
   - Bloqueia outras ações

2. ✅ **Implementar Whitelist de Cancelamento**
   - Pausado pode cancelar
   - Bloqueia outras ações

3. ✅ **Implementar Whitelist de Comandos**
   - Pausado pode usar /retomar
   - Silencioso pode usar /normal

4. ⚠️ **Adiar Separação de Canais**
   - Lembretes/notificações para Sprint 3+
   - Documentar arquitetura em SEG-04A

5. ⚠️ **Adiar Diferenciação de Dono**
   - Dono silencioso bloqueia tudo
   - Refinamento em Sprint 2+

**Baseline Impact:** ✅ ZERO (whitelists garantem compatibilidade)

**Risco:** ✅ BAIXO (conservador, sem bloqueios inesperados)

---

## CONCLUSÃO

Sprint 1 é implementável com as seguintes restrições:

```
✅ MEC-03 (Override Manual)
   - responder_automaticamente = false
   - Whitelist: confirmação, cancelamento, comandos
   - Risco: BAIXO

✅ MEC-04 (Modo Dono)
   - 3 modos: normal, admin, silencioso
   - Silencioso bloqueia todas as ações
   - Risco: BAIXO

❌ Separação de Canais
   - ADIAR para Sprint 3+
   - Risco se não fizer: CRÍTICO

❌ Diferenciação de Dono
   - ADIAR para Sprint 2+
   - Risco se não fizer: MÉDIO
```

**Status Baseline:** Verde (216/216 PASS) ✅

---

**Auditoria:** SEG-04A  
**Data:** 2026-06-23  
**Status:** ✅ Completa (Sem Implementação)

**Próximo:** Implementação Sprint 1 com whitelists aplicadas ao PRD SEG-04
