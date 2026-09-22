# Revisão — Contrato do Domínio Comercial V1.0 → V1.1

**Data:** 2026-07-22  
**Tipo de Revisão:** Arquitetural  
**Motivo:** Corrigir erros conceituais sobre identidade, isolamento, idempotência e domínios múltiplos  
**Impacto:** Alto — redefine modelo de dados comercial

---

## SUMÁRIO EXECUTIVO

A V1.0 assumia modelo simplista ("um ator, um papel"). A V1.1 corrige para modelo realista ("múltiplos vínculos, contexto singular") compatível com a arquitetura operacional existente da NeoEve e com cenários reais de negócio.

Todas as 13 correções obrigatórias foram implementadas. Nenhum código foi modificado. O documento é 100% arquitetural.

---

## PROBLEMAS ENCONTRADOS NA V1.0 E CORREÇÕES APLICADAS

### 1. Princípio "Um Ator, Um Papel" ← **CRÍTICO**

**Problema:** V1.0 assumia que cada ator tem um único papel_atual que muda exclusivamente (LEAD_COMERCIAL → DONO_TENANT).

**Realidade:** Um ator pode simultaneamente ser:
- Lead comercial de novo negócio
- Dono de um tenant existente
- Profissional de outro tenant
- Cliente final de terceiro tenant
- Admin interno

**Correção Aplicada:**
```
V1.0: papel_atual (um único valor por ator)
      ↓
V1.1: Atores/{actor_id} + VinculosTenant/{vinculo_id} (múltiplos papéis por contexto)
```

**Impacto Arquitetural:** Roteador agora resolve baseado em contexto, não em papel único.

---

### 2. Separação de lead_id vs actor_id ← **CRÍTICO**

**Problema:** V1.0 usava `Leads/{actor_id}`, assumindo uma jornada comercial por ator.

**Realidade:** Um ator pode retornar meses depois com novo negócio, nova campanha, múltiplas unidades.

**Correção Aplicada:**
```
V1.0: Leads/{actor_id}
      ↓
V1.1: Leads/{lead_id} (chave única)
      Leads/{lead_id}.actor_id (indexado, pode haver múltiplas por ator)
      Regra: máximo uma jornada ATIVA por ator
```

**Impacto Arquitetural:**
- Múltiplas jornadas permitidas
- Histórico preservado por negócio candidato
- Analytics pode rastrear por campanha

---

### 3. Conversão Não é Destrutiva ← **CRÍTICO**

**Problema:** V1.0 definia transição como `LEAD_COMERCIAL → DONO_TENANT` (substituição).

**Realidade:** Conversão deve preservar histórico comercial para auditoria, compliance, métricas.

**Correção Aplicada:**
```
V1.0: papel_atual muda de LEAD para DONO (histórico perdido)
      ↓
V1.1: 
  - Leads/{lead_id}.status_comercial = CONVERTIDO (persiste)
  - VinculosTenant criado com papel=DONO (novo vínculo)
  - Histórico comercial consultável sempre
```

**Impacto Arquitetural:**
- Auditoria completa de jornadas
- Possibilidade de re-ativar leads históricos
- Análise de padrão conversão

---

### 4. Modelo de Conversão — Híbrido (Núcleo Atômico + Etapas Recuperáveis) ← **CRÍTICO**

**Problema:** V1.0 misturava transação atômica com saga recuperável de forma ambígua.

**Realidade:** Precisamos de:
- Garantia de atomicidade no núcleo (tenant, vínculo, conversão)
- Recuperabilidade em etapas posteriores (mensagem, analytics)

**Correção Aplicada:**
```
NÚCLEO ATÔMICO (Firestore Transaction):
  - Cria Tenants/{tenant_id}
  - Cria VinculosTenant/{vinculo_id}
  - Atualiza Leads/{lead_id}
  - OU tudo, OU nada (rollback completo)

ETAPAS RECUPERÁVEIS:
  - Envio de mensagem (pode falhar, retry seguro)
  - Eventos para analytics (pode falhar, retry seguro)
  - Scheduler (pode faliar, retry seguro)
```

**Impacto Arquitetural:**
- Zero tenant duplicado mesmo com falhas
- Etapas recuperáveis sem risco
- Estados intermediários auditáveis

---

### 5. Chave de Idempotência Explícita ← **IMPORTANTE**

**Problema:** V1.0 não definia como prevenir duplicação se mesma conversão fosse retentada.

**Correção Aplicada:**
```
idempotency_key = actor_id + "_" + lead_id + "_conversao_v1"

Comportamento:
  - Mesma chave = mesma conversão (sem novo tenant)
  - Requisição duplicada converge para um resultado
  - Retry automático é seguro
```

**Impacto Arquitetural:**
- Retry automático seguro
- Sem duplicação de tenant
- Decisões comerciais versionadas

---

### 6. Trial Separado de Conversão ← **IMPORTANTE**

**Problema:** V1.0 iniciava trial automaticamente quando lead aceitava ("TRIAL_ACEITO").

**Realidade:** Trial deve ter estados separados:
- TRIAL_ACEITO (comercial aceita)
- TRIAL_PREPARADO (configuração mínima pronta)
- TRIAL_INICIADO (relógio começa)

**Correção Aplicada:**
```
V1.0: trial_started_at preenchido na conversão
      ↓
V1.1: Conversoes/{conversion_id}.trial.estado em [ACEITO, PREPARADO, INICIADO]
      Detalhamento em futuro Contrato de Trial
```

**Impacto Arquitetural:**
- Trial não passa de 14 dias se configuração mínima não completar
- Decisão de início é do motor operacional, não do comercial

---

### 7. Roteamento Contextual (Múltiplos Domínios) ← **CRÍTICO**

**Problema:** V1.0 prometia "Nenhuma conversa comercial chega a um dono" (absolutamente falso).

**Realidade:** Um dono pode querer:
- Upgrade de plano (DOMÍNIO COMERCIAL)
- Mudança de horário (DOMÍNIO OPERACIONAL)
- Problema de pagamento (DOMÍNIO BILLING)
- Relato técnico (DOMÍNIO SUPORTE)

**Correção Aplicada:**
```
V1.0: Roteamento binário (COMERCIAL vs OPERACIONAL)
      ↓
V1.1: Roteamento contextual (COMERCIAL, ONBOARDING, OPERACIONAL, BILLING, SUPORTE)
      Determinado por intenção detectada + vínculos disponíveis
```

**Impacto Arquitetural:**
- Uma pessoa, múltiplos domínios
- Mesmo actor_id pode estar em múltiplos domínios simultaneamente
- Garante isolamento de estado por domínio

---

### 8. Compatibilidade com Papéis Operacionais Reais ← **IMPORTANTE**

**Problema:** V1.0 inventava papéis (LEAD_COMERCIAL, DONO_TENANT) que não existiam no código operacional.

**Realidade:** Arquitetura existente usa DONO, PROFISSIONAL, CLIENTE_FINAL (sem lead).

**Correção Aplicada:**
```
V1.0: LEAD_COMERCIAL → DONO_TENANT (novo modelo)
      ↓
V1.1: Leads/{lead_id} (jornada comercial)
      +
      VinculosTenant com papel_no_tenant ∈ {DONO, PROFISSIONAL, CLIENTE_FINAL, ADMIN_INTERNO}
      (modelo operacional existente)
```

**Impacto Arquitetural:**
- Sem conflito com código operacional existente
- Lead é entidade comercial, não operacional
- Papel operacional surge apenas após conversão

---

### 9. Política de Comunicação Inbound vs. Outbound ← **IMPORTANTE**

**Problema:** V1.0 não definia regras de retorno, pressão, opt-out.

**Correção Aplicada:**
```
Seção 7 adicionada: POLÍTICA DE COMUNICAÇÃO COMERCIAL

INBOUND:
  - Lead iniciou
  - Sem limite de tentativas
  - Sem timeout

OUTBOUND:
  - NeoEve iniciou
  - Requer autorização
  - Máximo 1 tentativa por dia
  - Respeit opt-out
  - Cada tentativa registrada
```

**Impacto Arquitetural:**
- Custo de WhatsApp controlado
- Conformidade com política de canal
- Métricas de retenção claras

---

### 10. Fallback Explícito para Informação Não Autorizada ← **IMPORTANTE**

**Problema:** V1.0 dizia "Eve não responde sem autorização" sem detalhar fluxo.

**Correção Aplicada:**
```
Seção 4.2 adicionada: Fallback detalhado

Quando Eve não tem resposta:
  1. NÃO INVENTAR
  2. RECONHECER necessidade
  3. REGISTRAR dúvida em Leads/{lead_id}
  4. PRESERVAR etapa do funil
  5. ENCAMINHAR humano
  6. PERMITIR atualizar catálogo

Classificação de ausência:
  - NAO_ENCONTRADO_NO_CATALOGO
  - INFORMACAO_AMBIGUA
  - REGRAS_EM_CONFLITO
  - QUESTAO_PROIBIDA
  - Etc.
```

**Impacto Arquitetural:**
- Eve nunca fica em silêncio
- Dúvidas são rastreáveis
- Catálogo pode evoluir

---

### 11. Separação de Estados Conceituais por Domínio ← **IMPORTANTE**

**Problema:** V1.0 sugeria um único `estado_fluxo` para tudo.

**Correção Aplicada:**
```
V1.0: estado_fluxo (global, combinatório)
      ↓
V1.1:
  - estado_comercial (QUALIFICANDO, EM_ANALISE, ACEITE_PENDENTE)
  - estado_onboarding (DADOS_PESSOAIS, PROFISSIONAIS, SERVICOS)
  - estado_operacional (AGENDA, CONFIRMACAO, CANCELAMENTO)
  - estado_billing (REVISION, AWAITING_PAYMENT, CHARGED)
  - estado_suporte (ABERTO, EM_PROGRESSO, RESOLVIDO)
```

**Impacto Arquitetural:**
- Objeção de preço nunca confunde ajuste de horário
- Estados são independentes
- Máquinas de estado por domínio

---

### 12. Retomada e Interrupção Explícitas ← **IMPORTANTE**

**Problema:** V1.0 mencionava interrupção mas não definia mecânica completa.

**Correção Aplicada:**
```
Seção 3.2 reescrita: INTERRUPÇÕES E RETOMADAS

Suportadas:
  - Pergunta lateral (responder, preservar contexto, retomar)
  - Mudança de assunto (mesmo ciclo, volta depois)
  - Hesitação (sem pressão outbound, reconhecimento se voltar)
  - Nova jornada (mesmo ator, novo lead_id)
```

**Impacto Arquitetural:**
- Conversação natural, não linear
- Contexto preservado entre interruções
- Analytics de padrão de retorno

---

### 13. Origem e Métricas Mapeadas ← **IMPORTANTE**

**Problema:** V1.0 não definia eventos de rastreamento.

**Correção Aplicada:**
```
Seção 9 adicionada: ORIGEM E MÉTRICAS DO FUNIL

13 eventos conceituais mapeados:
  - landing_view
  - commercial_message_received
  - price_presented
  - trial_accepted
  - conversion_started
  - ... (até subscription_active)

Identificadores de correlação:
  - source_token
  - campaign_id
  - actor_id
  - lead_id
  - conversion_id
  - tenant_id
```

**Impacto Arquitetural:**
- Rastreamento completo de jornada
- Analytics de ROI possível
- Sem confusão entre eventos (trial_accepted ≠ payment_approved)

---

## DECISÕES ARQUITETURAIS CONSOLIDADAS

✅ **Confirmadas (não mudam):**
1. Um único canal (WhatsApp)
2. Roteamento anterior ao motor operacional
3. Eve interpreta, motor executa
4. Trial é separado de onboarding
5. Lead é entidade comercial (não operacional)
6. Firestore transação no núcleo

⚠️ **Decisões Ainda Abertas (próximos documentos):**
1. Qual é a configuração mínima que triggers TRIAL_INICIADO?
2. Como validar plano em real-time? (regras de negócio)
3. Quem decide quando lead é ABANDONADO? (timeout, sem mensagem)
4. Qual é o máximo de outbound automático?
5. Como priorizar fallback (humano vs. fila de revisão)?

---

## ITENS QUE PERTENCEM AO FUTURO

| Item | Pertence a | Status |
|------|-----------|--------|
| **Planos, preços, features** | CATALOGO_COMERCIAL_NEOEVE.md | ▶️ Próximo |
| **Garantias de transação atômica** | CONTRATO_CONVERSAO_LEAD_TENANT.md | ▶️ Próximo |
| **Configuração mínima de trial** | CONTRATO_TRIAL_NEOEVE.md | ▶️ Futuro |
| **Billing e cobrança** | CONTRATO_BILLING_NEOEVE.md | ▶️ Futuro |
| **Roteamento detalhado** | CONTRATO_ROTEAMENTO_DOMINIO.md | ▶️ Futuro |
| **Testes E2E comerciais** | TESTES_E2E_COMERCIAL_NEOEVE.md | ▶️ Futuro |
| **Implementação** | IMPLEMENTACAO_DOMINIO_COMERCIAL.md | ▶️ Futuro |

---

## CRITÉRIOS PARA APROVAÇÃO DA V1.1

**✅ Critério 1: Modelo Não Contradiz Código Operacional Existente**

V1.1 é compatível com:
- VinculosTenant/{vinculo_id} (papel_no_tenant)
- Atores/{actor_id} (identidade)
- Leads/{lead_id} (novo, comercial)

**Verificação:** Nenhuma alteração exigida no código operacional existente.

---

**✅ Critério 2: Identidade Múltipla é Suportada**

Mesmo ator pode ter:
- Lead ATIVA (novo negócio)
- Vínculo DONO (tenant_1)
- Vínculo PROFISSIONAL (tenant_2)
- Vínculo CLIENTE (tenant_3)

**Verificação:** Arquitetura suporta sem conflito. Roteamento escolhe domínio.

---

**✅ Critério 3: Idempotência é Garantida**

Requisição duplicada com mesma chave:
- Não cria tenant novo
- Retorna conversão anterior
- Retry seguro

**Verificação:** idempotency_key é composto e único.

---

**✅ Critério 4: Histórico é Preservado**

Após conversão:
- Leads/{lead_id}.status_comercial = CONVERTIDO (persiste)
- Leads/{lead_id} é consultável sempre
- Jornada é auditável

**Verificação:** Lead não é deletado, apenas status muda.

---

**✅ Critério 5: Isolamento de Domínio é Explícito**

Estado comercial ≠ estado operacional:
- estado_comercial (qualificação)
- estado_operacional (agenda)
- Nunca podem ser confundidos

**Verificação:** Seção 5.3 mapeia isolamento por domínio.

---

## RISCOS SE NÃO IMPLEMENTAR V1.1

🔴 **RISCO CRÍTICO:** Conflito de papéis

Se manter V1.0 (um ator, um papel):
- Dono que quer fazer upgrade fica confuso
- Lead retornando meses depois cria novo ator (duplicação)
- Impossível rastrear jornada de mesmo cliente em dois negócios

🔴 **RISCO CRÍTICO:** Duplicação de Tenant

Sem idempotência explícita:
- Retry de mesma conversão = novo tenant
- Dados inconsistentes
- Impossível recuperar de falhas

🔴 **RISCO IMPORTANTE:** Perda de Histórico

Sem lead persistente:
- Conversão destrutiva (não há como auditar jornada)
- Impossível analisar padrão conversão
- Dúvidas comerciais não são rastreáveis

---

## RECOMENDAÇÃO OBJETIVA

✅ **APROVAR V1.1**

Motivos:
1. Corrige 13 erros conceituais da V1.0
2. Compatível com código existente (sem alterações necessárias)
3. Realista (suporta múltiplos papéis por ator)
4. Seguro (idempotência explícita, núcleo atômico)
5. Auditável (histórico preservado)

⚠️ **Bloqueadores:** Nenhum encontrado

❌ **NÃO REJEITAR**

---

## INDICAÇÃO: PRÓXIMO DOCUMENTO

Após aprovação de V1.1, começar imediatamente:

**▶️ CATALOGO_COMERCIAL_NEOEVE.md**

Definirá:
- Planos (SOLO87, SOLOPRO117, ...)
- Preços
- Features por plano
- Limites por plano
- Roadmap (o que NÃO oferecer)

**Razão:** Eve precisa consultar esse documento (será a "fonte de verdade" que Eve usa para responder perguntas).

---

**Revisão Concluída:** 2026-07-22  
**Recomendação:** APROVAR V1.1  
**Próximo Passo:** Criar CATALOGO_COMERCIAL_NEOEVE.md
