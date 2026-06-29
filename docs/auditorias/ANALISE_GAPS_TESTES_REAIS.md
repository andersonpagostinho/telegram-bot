# ANÁLISE DE GAPS — TESTES FALTANTES EM NEOEVE

**Data:** 2026-06-28  
**Status:** 🔴 CRÍTICO — 40 testes faltantes identificados  
**Objetivo:** Encontrar cenários reais não cobertos que podem causar falhas em produção

---

## O QUE É NEOEVE?

**Bot conversacional de agenda (WhatsApp):**
- Clientes agendarem consultas/serviços
- Profissionais gerenciarem disponibilidade
- Donos administrarem business
- Multi-tenant com isolamento
- IA (GPT) interpreta → Motor determinístico executa

---

## TESTES EXISTENTES (238 PASS)

```
P0 Regressão:   174/174 (fluxo, cancelamento, contexto, etc)
P1 E2E:          42/42  (onboarding, identidade)
F2 Confiabilidade: 22/22 (ordem, múltiplos, reconexão)
────────────────────────────
TOTAL:          238/238 PASS
```

---

## GAPS CRÍTICOS IDENTIFICADOS

### 🔴 **Categoria A: Input Validation** (5 gaps)

#### A1: Mensagens malformadas/injectadas
```
Cenário: User envia "/agenda\x00\x01" ou "'; DROP TABLE eventos; --"
Status: NÃO TESTADO
Risco: Crash, SQL injection, RCE
Impacto: 🔴 CRÍTICO
```

#### A2: Mensagens muito longas
```
Cenário: User envia 10KB+ de texto
Status: NÃO TESTADO
Risco: Timeout, truncamento silencioso
Impacto: 🟠 ALTO
```

#### A3: Unicode/emojis/idiomas
```
Cenário: "Quero 📅 corte com ñ à côté"
Status: NÃO TESTADO
Risco: GPT interpreta errado, contexto corrompido
Impacto: 🟠 ALTO
```

#### A4: Entrada vazia
```
Cenário: User envia "", "   ", "\n"
Status: NÃO TESTADO
Risco: Pode ser interpretado como confirmação/negação
Impacto: 🟡 MÉDIO
```

---

### 🔴 **Categoria B: Fluxo Conversacional** (5 gaps)

#### B1: Interrupção de fluxo por comando
```
Cenário: Em "aguardando_profissional", user envia "/sair"
Status: NÃO TESTADO
Risco: Estado inconsistente, draft solto
Impacto: 🟠 ALTO
```

#### B2: Confirmação com typo
```
Cenário: Em confirmação, user envia "simm" ao invés de "sim"
Status: NÃO TESTADO
Risco: Sistema não entende, loop infinito
Impacto: 🟡 MÉDIO
```

#### B3: Draft expirado (> 24h)
```
Cenário: Draft existe há 2 dias, user responde
Status: NÃO TESTADO
Risco: Recria evento antigo ou estado inconsistente
Impacto: 🟡 MÉDIO
```

#### B4: Fluxos paralelos simultâneos
```
Cenário: User abre 2 abas, envia mensagens em paralelo
Status: NÃO TESTADO
Risco: Race condition, 2 eventos, estado corrupto
Impacto: 🔴 CRÍTICO
```

#### B5: Volta para fluxo anterior
```
Cenário: Estava em fluxo A, começou B, quer voltar
Status: NÃO TESTADO
Risco: Contexto A perdido, sistema sem "undo"
Impacto: 🟡 MÉDIO
```

---

### 🔴 **Categoria C: Interpretação GPT** (4 gaps)

#### C1: GPT alucinando (hallucination)
```
Cenário: "Quero corte com João" → João não existe
Status: NÃO TESTADO
Risco: Motor bloqueia, mensagem confusa ao user
Impacto: 🟠 ALTO
```

#### C2: Ambiguidade não detectada
```
Cenário: "Corte" pode ser serviço OU descrição
Status: NÃO TESTADO
Risco: Erro genérico, user confuso
Impacto: 🟠 ALTO
```

#### C3: Confiança muito baixa
```
Cenário: GPT retorna confianca=0.2
Status: NÃO TESTADO
Risco: Motor executa ação com confiança fraca
Impacto: 🟡 MÉDIO
```

#### C4: GPT retorna resposta diferente em retry
```
Cenário: Telegram reenvia MSG, GPT retorna tipo_resposta diferente
Status: NÃO TESTADO
Risco: Não idempotente, ação executada 2x
Impacto: 🔴 CRÍTICO
```

---

### 🔴 **Categoria D: Identidade/Papéis** (4 gaps)

#### D1: Cliente tenta ação admin
```
Cenário: Cliente envia "/cadastrar_profissional"
Status: NÃO TESTADO
Risco: Escalação de privilégio
Impacto: 🟡 MÉDIO
```

#### D2: Profissional acessa tenant diferente
```
Cenário: Profissional A tenta agendar em Tenant B
Status: NÃO TESTADO
Risco: Firestore rules falham, XSRF
Impacto: 🟠 ALTO
```

#### D3: Actor ID injection
```
Cenário: Webhook modificado: actor_id="outro_user"
Status: NÃO TESTADO
Risco: Age como outra pessoa
Impacto: 🔴 CRÍTICO
```

#### D4: Token de confirmação forjado
```
Cenário: User A modifica token de confirmação de User B
Status: NÃO TESTADO
Risco: Confirma evento alheio
Impacto: 🟡 MÉDIO
```

---

### 🔴 **Categoria E: Evento/Agenda** (5 gaps)

#### E1: Evento no passado
```
Cenário: "Quero agendar para ontem"
Status: NÃO TESTADO
Risco: Evento inválido criado
Impacto: 🟠 ALTO
```

#### E2: Evento muito longe (5 anos)
Status: NÃO TESTADO
Risco: Sem limite futuro validado
Impacto: 🟡 MÉDIO

#### E3: Horário inválido (25:00, -1:00)
Status: NÃO TESTADO
Risco: GPT extrai, motor bloqueia com erro genérico
Impacto: 🟠 ALTO

#### E4: Conflito horário (race condition)
```
Cenário: Dois users agendando no mesmo slot simultaneamente
Status: NÃO TESTADO
Risco: 2 eventos no mesmo slot, agenda quebrada
Impacto: 🔴 CRÍTICO
```

#### E5: Serviço de duração 0/-30 minutos
Status: NÃO TESTADO
Risco: Validação falha, agenda inconsistente
Impacto: 🟡 MÉDIO

---

### 🔴 **Categoria F: Estado/Contexto** (4 gaps)

#### F1: Draft corrupto (campo ausente)
```
Cenário: Firestore salva draft sem "servico"
Status: NÃO TESTADO
Risco: Motor quebra ao acessar
Impacto: 🟠 ALTO
```

#### F2: Sessão V2 parcialmente salva
```
Cenário: Crash durante save → dados incompletos
Status: NÃO TESTADO
Risco: Contexto incoerente, próxima mensagem quebra
Impacto: 🟡 MÉDIO
```

#### F3: Campo extra não esperado
```
Cenário: Admin adiciona "debug_flag" em Firestore
Status: NÃO TESTADO
Risco: Lógica inesperada
Impacto: 🟡 MÉDIO
```

#### F4: Timestamp inválido
```
Cenário: timestamp_fluxo="data_invalida" ou futuro
Status: NÃO TESTADO
Risco: Comparações quebram
Impacto: 🟠 ALTO
```

---

### 🔴 **Categoria G: Operações Críticas** (4 gaps)

#### G1: Cancelar evento inexistente
Status: NÃO TESTADO
Risco: Erro confuso ou silencio
Impacto: 🟡 MÉDIO

#### G2: Confirmação duplicada (clique rápido)
```
Cenário: User clica "Confirmar" 2x rápido
Status: NÃO TESTADO
Risco: 2 eventos criados se não idempotente
Impacto: 🔴 CRÍTICO
```

#### G3: Confirmar evento de outro user
Status: NÃO TESTADO
Risco: Ação não autorizada
Impacto: 🟡 MÉDIO

#### G4: Editar evento após confirmação
```
Cenário: User muda serviço após "Confirmar"
Status: NÃO TESTADO
Risco: Draft limpo, mudança silenciosa
Impacto: 🟠 ALTO
```

---

### 🔴 **Categoria H: Performance** (3 gaps)

#### H1: 1000+ eventos históricos
Status: NÃO TESTADO
Risco: Query lenta, timeout
Impacto: 🟡 MÉDIO

#### H2: Processamento > 30 segundos
```
Cenário: GPT timeout, Firestore timeout, webhook timeout
Status: NÃO TESTADO
Risco: User nunca recebe resposta, estado inconsistente
Impacto: 🔴 CRÍTICO
```

#### H3: Firestore quota excedida
Status: NÃO TESTADO
Risco: Sistema quebra silenciosamente
Impacto: 🟡 MÉDIO

---

### 🔴 **Categoria I: Recuperação/Error Handling** (3 gaps)

#### I1: WhatsApp API rejeita mensagem
```
Cenário: 401, 429, erro ao enviar resposta
Status: NÃO TESTADO
Risco: User não recebe feedback, contexto continua
Impacto: 🔴 CRÍTICO
```

#### I2: Firestore indisponível
Status: NÃO TESTADO
Risco: Loop infinito de retry
Impacto: 🟡 MÉDIO

#### I3: GPT rate-limited (429)
Status: NÃO TESTADO
Risco: Retry sem backoff adequado
Impacto: 🟡 MÉDIO

---

### 🔴 **Categoria J: Segurança** (5 gaps)

#### J1: SQL Injection em draft
Status: NÃO TESTADO (Firestore menos vulnerável que SQL)
Impacto: 🟡 MÉDIO

#### J2: XXE (se houver XML)
Status: NÃO TESTADO
Impacto: 🟡 MÉDIO

#### J3: Path Traversal
Status: NÃO TESTADO
Impacto: 🟡 MÉDIO

#### J4: CSRF via webhook alterado
Status: NÃO TESTADO
Risco: Events criados em tenant errado
Impacto: 🟠 ALTO

#### J5: Privacy (PII nos logs)
```
Cenário: Logs contêm nome, telefone, endereço
Status: NÃO TESTADO
Risco: LGPD violation
Impacto: 🔴 CRÍTICO
```

---

## RESUMO POR SEVERIDADE

```
🔴 CRÍTICO (5 gaps):
   - B4: Fluxos paralelos
   - C4: GPT inconsistência
   - D3: Actor ID injection
   - E4: Conflito horário race
   - G2: Confirmação duplicada
   - H2: Timeout > 30s
   - I1: WhatsApp API error
   - J5: PII exposure

🟠 ALTO (14 gaps):
   - A1, A2, A3 (Input validation)
   - B1 (Interrupção fluxo)
   - C1, C2 (GPT quality)
   - D2 (Multi-tenant)
   - E1, E3 (Evento inválido)
   - F1, F4 (Estado corrupto)
   - G4 (Edição pós-confirmação)
   - J4 (CSRF)

🟡 MÉDIO (21 gaps):
   - Resto (validação, performance, erro handling)

════════════════════════════════════════
TOTAL: 40 GAPS | 238 TESTES EXISTENTES
════════════════════════════════════════
```

---

## TOP 5 RISCO IMEDIATO (Implementar Urgente)

1. **B4 — Fluxos paralelos** → Race condition no draft
2. **D3 — Actor ID injection** → Acesso não autorizado
3. **E4 — Conflito horário race** → Agenda quebrada
4. **H2 — Timeout prolongado** → Estado inconsistente
5. **J5 — PII logs** → Compliance violation

---

## PRÓXIMOS PASSOS

1. Criar F3 (Robustez) com 40 testes faltantes
2. Priorizar os 5 críticos
3. Validar regressão: 238 + 40 = **278/278 PASS**
4. Antes de ir para Fase 3, cobrir os gaps
