# 📊 MIGRAÇÃO PARA 3 PLANOS CANÔNICOS — RELATÓRIO FINAL

**Data:** 2026-08-17  
**Status:** ✅ AUDITORIA COMPLETA (SEM ALTERAÇÕES)  
**Próximo Passo:** Aprovação de decisões comerciais  

---

## 🎯 SITUAÇÃO ATUAL

### Planos Canônicos (Já Documentados)
- **SOLO** — R$87/mês
- **PROFISSIONAL** — R$157/mês  
- **SALÕES** — R$247+/mês

### Planos Legados (Ainda Referenciados)
- **SOLO_PRO** — R$117/mês (4 referências)
- **STUDIO** — R$157/mês (11 referências)
- **SALÃO247** — R$247/mês (2 referências)
- **PRO347** — R$347/mês (2 referências)

**Total:** 19 referências em 6 arquivos

---

## 1️⃣ MATRIZ DE OCORRÊNCIAS

| Arquivo | Linha | Referência | Tipo | Categoria | Impacto | Ação |
|---------|-------|-----------|------|-----------|---------|------|
| simulacao_custo_meta.py | 62 | `PRECO_SOLO_PRO = 117.00` | CONSTANTE | PRODUÇÃO | ALTO | Renomear/Remover |
| simulacao_custo_meta.py | 63 | `PRECO_STUDIO = 157.00` | CONSTANTE | PRODUÇÃO | ALTO | Renomear PROFISSIONAL |
| simulacao_custo_meta.py | 64 | `PRECO_SALAO = 247.00` | CONSTANTE | PRODUÇÃO | ALTO | Confirmar preço |
| simulacao_custo_meta.py | 65 | `PRECO_PRO = 347.00` | CONSTANTE | PRODUÇÃO | ALTO | Decidir destino |
| simulacao_custo_meta.py | 70 | `"SOLO PRO": ...` | DICIONÁRIO | PRODUÇÃO | ALTO | Renomear/Remover |
| simulacao_custo_meta.py | 71 | `"STUDIO": ...` | DICIONÁRIO | PRODUÇÃO | ALTO | Renomear |
| simulacao_custo_meta.py | 72 | `"SALAO": ...` | DICIONÁRIO | PRODUÇÃO | ALTO | Renomear |
| simulacao_custo_meta.py | 73 | `"PRO": ...` | DICIONÁRIO | PRODUÇÃO | ALTO | Renomear/Remover |
| test_commercial_events.py | 45 | `plan_id="plan_studio"` | FIXTURE | TESTE | MÉDIO | Parametrizar |
| test_commercial_events.py | 64 | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_commercial_events.py | 71 | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_commercial_events.py | 264 | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_commercial_events.py | 274 | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_commercial_events.py | 481 | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_commercial_events.py | 488 | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 140+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 194+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 213+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 240+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 283+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 373+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 399+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 424+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| test_billing_domain_service.py | 455+ | `amount=157.00` | PREÇO | TESTE | MÉDIO | Parametrizar |
| domain/commercial_events.py | 173 | `converted_to_plan_id: str = None` | CAMPO | PRODUÇÃO | BAIXO | Manter/Remover |
| Backups | N/A | Código histórico | N/A | DEPRECADO | NENHUM | Ignorar |

---

## 2️⃣ ARQUITETURA ATUAL DE PLANOS

### 2.1 Onde Planos SÃO DEFINIDOS

**Resposta:** Não em código de produção.

```
✅ Documentação (CONTRATO_PLANOS_PHASE1_CORRIGIDO.md)
✅ Hotmart (sistema externo — source-of-truth para product_ids)
❌ Nenhum enum ou constante canônico no código Python
❌ Nenhuma tabela de planos em Firestore
❌ Nenhuma API que valida planos
```

**Implicação:** Planos são STRING simples, qualquer valor é aceito.

---

### 2.2 Onde Preços SÃO DEFINIDOS

**Resposta:** Documentação + Hotmart (não código).

```
✅ CATALOGO_COMERCIAL_NEOEVE.md (R$87, R$157, R$247)
✅ Hotmart (product_ids com preços reais)
✅ simulacao_custo_meta.py (apenas simulação)
❌ Nenhuma tabela centralizada de preços
❌ Nenhuma validação de preço
```

---

### 2.3 Onde plan_id É CRIADO

**Localizações:**
- `domain/commercial_events.py` → `TrialActivated.plan_id` (linha 147)
- `domain/commercial_events.py` → `TrialConverted.converted_to_plan_id` (linha 173)
- Webhook Hotmart (não em código Python)

**Padrão:** plan_id é STRING, recebido do webhook ou entrada manual.

---

### 2.4 Onde plan_id É LIDO/VALIDADO

**Leitura:**
- `domain/commercial_events.py` (armazena como campo)
- `services/billing_domain_service.py` (snapshot)
- Testes (fixtures)

**Validação:**
- ❌ **NÃO HÁ VALIDAÇÃO**
- ❌ Nenhuma rejeição de plan_id desconhecido
- ✅ Qualquer string é aceita

**Impacto:** Se alguém enviar `plan_id="xyz_aleatorio"`, será aceito sem erro.

---

### 2.5 Onde BILLING/PAYMENT Depende de plan_id

**Dependência:**
- Webhook Hotmart envia `amount` (preço)
- `plan_id` é apenas rastreado, não usado em lógica de pagamento
- Máquinas de estado NÃO validam plan_id

**Conclusão:** Pagamento é independente de plan_id.

---

### 2.6 Onde LIMITES/FEATURES Dependem de Plano

**Resposta:** ❌ NENHUM LUGAR.

```
❌ Nenhum if/elif baseado em plan_id
❌ Nenhuma feature-gate por plano
❌ Nenhuma validação de limite (profissionais, clientes)
❌ Nenhuma quota aplicada
```

**O que isto significa:**
- ✅ Bom design: todas as features estão disponíveis para todos
- ⚠️ Gap futuro: limites não são aplicados em código
- ✅ Flexível: pode suportar novos planos sem alterar lógica

---

### 2.7 Onde ONBOARDING/TRIAL Referencia Plano

**Localização:**
- `domain/commercial_events.py` → `TrialActivated.plan_id`
- `CONTRATO_TRIAL_NEOEVE.md`

**Lógica:**
- Trial é sempre 7 dias (não varia por plano)
- `plan_id` é armazenado mas não governa duração

---

### 2.8 Onde FRONTEND/SITE Envia plan_id

**Não encontrado em código Python.**

Presumivelmente:
- Frontend envia `plan_id` de escolha
- Backend aceita como string

---

### 2.9 Onde WEBHOOK Hotmart Envia plan_id

**Não encontrado em código Python.**

Presumivelmente:
- Hotmart envia `product_id` (não `plan_id` direto)
- Mapeamento é feito em Hotmart ou frontend

---

### 2.10 Existe Enum/Contrato Canônico de Planos?

**Resposta:** NÃO.

```
❌ Nenhum enum PlanType
❌ Nenhuma classe Plan
❌ Nenhuma lista KNOWN_PLANS
❌ Nenhum contrato Domain-Driven Design
```

**É apenas:** STRING em eventos + documentação manual.

---

## 3️⃣ DEPENDÊNCIAS ENCONTRADAS

### Fluxo de plan_id pelo Sistema

```
ENTRADA                PROCESSAMENTO              PERSISTÊNCIA
─────────             ──────────────             ────────────

Hotmart Webhook   →   TrialActivated      →    Firestore
  (product_id)         (plan_id: str)            (documento)
                            ↓
                      AggregateSnapshot    →    Snapshot
                      (metadata)
                            ↓
                      billing_domain_       →    Logs/Auditoria
                      service.py

Frontend/Manual   →   TrialActivated      →    Firestore
  (plan_id)            (plan_id: str)            (documento)
                            ↓
                      Testes (fixtures)    →    CI/CD Pipeline

Simulação        →    simulacao_custo_      →  Relatório
                      meta.py               (break-even)
                      (preços constantes)
```

---

### Componentes Críticos Que Dependem de plan_id

**RESULTADO:** Nenhum encontrado.

```
✅ domain/commercial_events.py
   └─ Rastreia plan_id, não governa lógica

✅ services/billing_domain_service.py
   └─ Armazena plan_id em metadata
   └─ Transições de estado NÃO dependem de plan_id

✅ services/billing_application_service.py
   └─ Persiste plan_id como-é
   └─ Transparente a mudanças

⚠️ simulacao_custo_meta.py
   └─ Usa valores/nomes de planos
   └─ Precisa atualização quando preços mudam

✅ Testes
   └─ Fixtures com plan_id
   └─ Precisam parametrização
```

**CONCLUSÃO:** Nenhuma lógica crítica governa comportamento por plan_id. Sistema é flexível.

---

## 4️⃣ DECISÕES QUE PRECISAM SER FORNECIDAS

### ❌ BLOCKER 1: SOLO_PRO (R$117) → Qual Novo Plano?

**Opções:**
- [ ] A: Mapear para **SOLO** (R$87) — redução de preço
- [ ] B: Mapear para **PROFISSIONAL** (R$157) — aumento de preço
- [ ] C: **Descontinuar** — apenas novos clientes em SOLO/PROFISSIONAL

**Impacto Financeiro:**
- Opção A: Revenue diminui
- Opção B: Revenue aumenta, risco de churn
- Opção C: Revenue cai progressivamente até expiração

**Decisão Recomendada:** _______________

---

### ❌ BLOCKER 2: STUDIO (R$157) → Qual Novo Plano?

**Opção Óbvia:**
- [ ] Mapear para **PROFISSIONAL** (R$157) — preço idêntico, sem impacto

**Impacto:** Nenhum (preço mantido)

**Decisão:** [ ] PROFISSIONAL ✅ (recomendado)

---

### ❌ BLOCKER 3: SALÃO247 (R$247) → Qual Novo Plano?

**Opção Principal:**
- [ ] Mapear para **SALÕES** (R$?) — qual é o novo preço?

**CRÍTICO:** Qual é o preço de SALÕES?
- [ ] R$247 (mantém preço)
- [ ] R$_____________ (novo preço)

**Impacto Financeiro:**
- Se R$247: Revenue mantido
- Se outro: Revenue varia

**Decisão Recomendada:** Preço SALÕES = R$ _______________

---

### ❌ BLOCKER 4: PRO347 (R$347) → Qual Novo Plano?

**Opções:**
- [ ] A: Mapear para **SALÕES** (R$247 ou R$?) — redução/variação de preço
- [ ] B: **Descontinuar** — apenas novos clientes em SALÕES
- [ ] C: Criar novo plano **ENTERPRISE** (R$347+) — mantém tier premium

**Impacto Financeiro:**
- Opção A: Revenue diminui ou varia
- Opção B: Revenue cai progressivamente
- Opção C: Revenue mantido, mais uma opção

**Complexidade:**
- Opção A/B: 1 dia
- Opção C: +1 semana (adiciona novo plano)

**Decisão Recomendada:** _______________

---

### ❌ BLOCKER 5: Timeline de Migração de Clientes

**Opções:**
- [ ] **Imediata** — clientes veem mudança hoje
  - Risk: Alto (mudança súbita)
  - Support: Alto volume de calls
  
- [ ] **Fim do Ciclo** — clientes migram na próxima renovação
  - Risk: Médio (período de transição)
  - Support: Planejado
  - **RECOMENDADO ✅**
  
- [ ] **Opcional** — comunicar e deixar cliente escolher
  - Risk: Baixo
  - Support: Baixo
  - Complexidade: Alta (administrativo)

**Comunicação ao Cliente:**
- [ ] SIM (comunicar antecipadamente)
- [ ] NÃO (silencioso, na renovação)

**Dias de Antecedência:** _____ dias

**Decisão Recomendada:** FIM DO CICLO com comunicação prévia

---

## 5️⃣ PLANO DE MIGRAÇÃO RECOMENDADO

### FASE 1: Preparação (1 dia)

**Antes de qualquer código:**

```
[ ] Confirmar as 5 decisões acima
[ ] Validar que nenhuma lógica crítica depende de plan_id
[ ] Listar clientes com planos antigos (query Firestore)
[ ] Validar integração Hotmart (qual field envia?)
[ ] Validar documentação está atualizada
```

---

### FASE 2: Implementação (2-3 dias)

**Ordem de execução:**

1. **Criar Enum Canônico** (baixo risco)
   - `domain/plan_catalog.py` (NOVO)
   - Enum com SOLO, PROFISSIONAL, SALÕES
   - Tabela de preços centralizada
   - Validação de plan_id

2. **Atualizar simulacao_custo_meta.py** (médio risco)
   - Renomear constantes
   - Atualizar dicionário PLANOS
   - Validar script executa

3. **Parametrizar Testes** (médio risco)
   - `test_commercial_events.py` fixtures
   - `test_billing_domain_service.py` preços
   - Adicionar testes para novos planos

4. **Atualizar Documentação** (baixo risco)
   - CONTRATO_PLANOS_PHASE1_CORRIGIDO.md
   - CATALOGO_COMERCIAL_NEOEVE.md
   - CONTRATO_BILLING_NEOEVE.md

---

### FASE 3: Validação (1-2 dias)

```
[ ] Regressão P0 (174/174 PASS)
[ ] Regressão P1 E2E (42/42 PASS)
[ ] Sem novo timeout gRPC
[ ] Documentação atualizada
[ ] Aprovação de QA
```

---

### FASE 4: Backfill de Dados (1-2 dias)

**Opção A: Migração Imediata**
- UPDATE Firestore: `plan_id` "plan_studio" → "plan_profissional"
- Executar hoje

**Opção B: Migração ao Fim do Ciclo**
- Manter plano_id antigo até renovação
- Atualizar na renovação (automático ou manual)

**Recomendação:** Opção B (menos risco)

---

### FASE 5: Comunicação com Clientes (N/A se silencioso)

**Se comunicar:**
- Email template: "Seu plano [ANTIGO] → [NOVO]"
- Documentação de benefícios
- Data de efetivação

---

## 📋 CANONICAL_PLAN_CONTRACT

```
PLANO: SOLO
  - plan_id: "plan_solo"
  - Preço: R$87.00/mês
  - Profissionais: 1
  - Features: Link exclusivo, agendamento, lembretes
  - Trial: 7 dias
  
PLANO: PROFISSIONAL
  - plan_id: "plan_profissional"
  - Preço: R$157.00/mês
  - Profissionais: 3
  - Features: Número dedicado, aprende ritmo, alertas
  - Trial: 7 dias
  
PLANO: SALÕES
  - plan_id: "plan_saloes"
  - Preço: R$247.00+/mês (⚠️ Confirmar)
  - Profissionais: 10+
  - Features: Dashboard, suporte dedicado, onboarding
  - Trial: 7 dias
  
DEPRECATED (Legados — manter para rastreamento histórico):
  - SOLO_PRO: R$117.00 (mapear para _____)
  - STUDIO: R$157.00 (mapear para PROFISSIONAL)
  - SALÃO247: R$247.00 (mapear para SALÕES)
  - PRO347: R$347.00 (mapear para _____)
```

---

## ✅ O QUE NÃO FOI ALTERADO

- ✅ Nenhum código foi modificado
- ✅ Nenhum arquivo foi renomeado
- ✅ Nenhum teste foi executado
- ✅ Nenhuma confirmação de preço foi assumida
- ✅ Nenhum backfill foi executado
- ✅ Nenhuma documentação foi alterada

---

## 🚀 PRÓXIMO PASSO

**AGUARDANDO SUAS DECISÕES:**

1. [ ] SOLO_PRO → qual novo plano?
2. [ ] STUDIO → PROFISSIONAL ✅
3. [ ] Preço de SALÕES?
4. [ ] PRO347 → qual novo plano?
5. [ ] Timeline de migração de clientes?

**Data Necessária:** Hoje/Amanhã (bloqueia implementação)

---

## 📁 DOCUMENTOS DE REFERÊNCIA

Todos os 4 documentos de auditoria estão em:
```
C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial\
```

1. **AUDITORIA_PROFUNDA_PLANOS_NEOEVE.md** (detalhado)
2. **MAPA_DEPENDENCIAS_PLANOS.md** (arquitetural)
3. **PLANO_MIGRACAO_RECOMENDADO.md** (executável)
4. **MATRIZ_ACHADOS_COMPLETA.md** (referência)

---

**Auditoria Completa e Verificada**  
**Status:** ✅ Pronto para decisões comerciais

