# CONTRATO_TRIAL_NEOEVE

---

## 🔒 REFERENCIA OBRIGATÓRIA

**Versão:** 1.2 (Operacional + Trial Value Reinforcement, Revisto)  
**Status:** ⚠️ RASCUNHO REVISTO — Requer Aprovação Jurídica + Produto  
**Data de Criação:** 2026-07-27  
**Última Atualização:** 2026-07-27 (Seção 6 evoluída para V1.2)  

**Evolução V1.0 → V1.1 → V1.2:**

V1.1 Adições:
- ✅ Seção 6 "Acompanhamento Inteligente do Trial" adicionada
- ✅ Estratégia de Trial Value Reinforcement documentada

V1.2 Correções (Revisão Crítica):
- ✅ Timeline refatorada: conceitos relativos (Início, Primeira metade, Penúltimo dia, etc) ao invés de dias fixos
- ✅ Perfis refatorados: 5 situações operacionais (Onboarding incompleto → Uso intenso) ao invés de números fixos
- ✅ Permissões refinadas: Derivações determinísticas permitidas; estimativas/projeções/interpretações IA proibidas
- ✅ Relatório final: "Comportamento de clientes" genérico removido; apenas métricas observáveis
- ✅ Resultado pretendido clarificado: não garante satisfação/churn, apenas decisão baseada em fatos  

**Este contrato define ESTADOS, REGRAS e TRANSIÇÕES.**

**Não define termos jurídicos** — veja Apêndice Jurídico ou TERMOS_DE_USO_NEOEVE.md

**Documentos que este contrato referencia (nunca duplica):**

| Item | Encontre Em | Não Copie Para |
|------|---|---|
| Duração do trial | Catálogo Comercial V1.2, Seção 6.2 | Este contrato (use "conforme Catálogo") |
| Preços | Catálogo Comercial V1.2, Seção 6.1 | Este contrato (não pertence aqui) |
| Retenção de dados | Política de Privacidade (TBD) | Este contrato (use "conforme Política") |
| Direitos LGPD | Política de Privacidade (TBD) | Este contrato (use "conforme Política") |
| Limites de indenização | Termos de Uso (TBD) | Este contrato (jurídico, não operacional) |
| Força maior | Termos de Uso (TBD) | Este contrato (jurídico, não operacional) |

---

## 📋 ÍNDICE

1. **Estados e Transições**
2. **Definição de Trial**
3. **Acesso e Features**
4. **Regras Operacionais**
5. **Encaminhamento Automático**
6. **Acompanhamento Inteligente do Trial** (Trial Value Reinforcement)
7. **Validação de Conformidade**
8. **Apêndice Jurídico** (questões legais)

---

## 1. ESTADOS E TRANSIÇÕES DO TRIAL

Visão geral de todos os estados possíveis e como passar de um para outro.

```
LEAD CRIA CONTA
    ↓
    [ONBOARDING_PENDENTE]
    ├─ Lead forneceu dados básicos (email, WhatsApp, serviço)
    ├─ Eve está validando configuração
    ├─ Timeout: 24h sem interação → Lead frio
    └─ Transição: Lead completa pré-requisitos → TRIAL_INICIADO
    
    ↓
    [TRIAL_ATIVO] ← AQUI começa a contagem de dias
    ├─ Duração: Conforme Catálogo Comercial V1.2, seção 6.2
    ├─ Acesso: Todas as features do plano selecionado
    ├─ Dados: Reais (não demo)
    ├─ Cancelamento: Lead pode sair a qualquer momento
    └─ Transições possíveis:
       ├─ Lead cancela → CANCELADO (dados preservados 30d)
       ├─ Lead paga → CLIENTE_ATIVO
       └─ Trial expira sem pagamento → TRIAL_EXPIRADO
    
    ↓
    [TRIAL_EXPIRADO]
    ├─ Lead não pagou até fim do período
    ├─ Tenant muda para read-only
    ├─ Eve para de responder
    ├─ Reativação disponível: Conforme Política de Privacidade
    ├─ Transições:
    │  ├─ Lead paga → CLIENTE_ATIVO
    │  ├─ Lead cancela → CANCELADO
    │  └─ Timeout de reativação → DELETADO
    └─ Transição automática caso reativação não ocorra
    
    ↓
    [CLIENTE_ATIVO]
    ├─ Lead pagou e tem assinatura ativa
    ├─ Acesso completo ao plano contratado
    ├─ Renovação: Conforme Contrato de Billing (TBD)
    └─ Transições:
       ├─ Lead cancela → CANCELADO (preservação conforme Política)
       └─ Lead não renova → SUSPENSO → [reativação possível]
    
    ↓
    [CANCELADO]
    ├─ Tenant é suspenso
    ├─ Dados preservados: Conforme Política de Privacidade
    └─ Transição: Reativação possível conforme Política
    
    ↓
    [DELETADO]
    ├─ Todos os dados permanentemente removidos
    ├─ Não é reversível
    ├─ Condições: Timeout conforme Política de Privacidade
    └─ Novo signup = nova conta
```

---

## 2. DEFINIÇÃO DE TRIAL

### 1.1 O Que É o Trial

Trial é um período de **7 dias corridos** de acesso grátis e completo às features e funcionalidades do plano selecionado pelo lead, sem cobrança ou cartão de crédito exigido.

**Características:**
- ✅ Período: 7 dias a partir da conclusão do onboarding mínimo
- ✅ Acesso: Completo (todas as features do plano)
- ✅ Custo: Grátis
- ✅ Cartão: Não exigido durante trial
- ✅ Dados: Reais (não são dados de demo ou teste)
- ✅ Cancelamento: Lead pode cancelar a qualquer momento durante trial

### 2.1 Quando Começa o Trial

Trial inicia no **Dia seguinte à conclusão do onboarding mínimo**, não no dia de signup.

**Onboarding mínimo valida:**
```
☐ Validar WhatsApp (pessoal ou Business)
☐ Cadastrar pelo menos 1 serviço
☐ Definir horários de funcionamento
☐ Configurar pelo menos 1 profissional/agenda
☐ Aceitar termos de trial
```

**Comportamento:**
- Se lead completa onboarding: Trial começa no próximo ciclo de sincronização
- Se lead não completa onboarding: Transição para ONBOARDING_PENDENTE (timeout definido em Política de Produto)

**Exemplo (ilustrativo):**
```
T0:    Lead clica "Começar trial"
T0-T1: Eve guia onboarding
T1:    Onboarding completado → Trial estado muda para TRIAL_ATIVO
T1+X: Trial expira (X = duração conforme Catálogo V1.2)
       → Transição para TRIAL_EXPIRADO
       → Notificação de pagamento enviada
```

(Duração exata: ver Catálogo Comercial V1.2, Seção 6.2)

### 1.3 Lead Qualificado para Trial

Trial está disponível apenas para leads que:

✅ Têm WhatsApp pessoal ou WhatsApp Business  
✅ Executam um negócio com agenda/agendamentos  
✅ Estão dispostos a testar com clientes reais (não apenas demo)  
✅ Completam onboarding mínimo  
✅ Aceitam estes termos de trial  

❌ Não estão disponíveis para:
- Empresas de educação/corporativo (roadmap futuro)
- Negócios puramente de venda de produtos
- Usuários sem qualquer cliente ou interesse em agendar

---

## 2. DIREITOS E RESPONSABILIDADES DA NEOEVE

### 2.1 Responsabilidades da NeoEve Durante Trial

NeoEve compromete-se a:

✅ **Disponibilidade:** Manter plataforma operacional >99% do tempo  
✅ **Features:** Disponibilizar todas as features do plano selecionado por 7 dias completos  
✅ **Suporte:** Responder dúvidas de onboarding em <24h (Email + WhatsApp)  
✅ **Segurança:** Proteger dados do lead com criptografia e backup automático (Firestore + Google Cloud)  
✅ **Notificações:** Enviar avisos sobre expiração (days 3, 6, 8)  
✅ **Reativação:** Permitir reativar durante janela 30 dias se lead não pagar no day-7  
✅ **Dados:** Preservar todos os dados até day-37 (90 dias após trial iniciado)  

### 2.2 Direitos da NeoEve

A NeoEve tem direito a:

✅ **Terminar Trial:** No day-8 se lead não iniciar pagamento  
✅ **Monitorar Uso:** Coletar dados sobre como lead usa plataforma (apenas para analytics e melhoria de produto)  
✅ **Determinar Reativação:** Avaliar elegibilidade para reativar tenant suspenso  
✅ **Deletar Dados:** Após day-37, deletar tenant e todos os dados permanentemente  
✅ **Bloquear Abuso:** Se lead usar plataforma para atividade ilegal ou contra TOS  

### 2.3 NÃO É RESPONSABILIDADE DA NEOEVE

NeoEve não é responsável por:

❌ **Marcações que o lead faz durante trial:** Se lead erra ao agendar um cliente, lead é responsável por corrigir  
❌ **Comunicação com clientes do lead:** Eve é um assistente automatizado; lead é responsável pelo relacionamento  
❌ **Lucro do lead:** Trial é chance de testar; não há garantia de resultado de vendas  
❌ **Perda de dados por desuso:** Se lead não entra na plataforma por 30+ dias, dados podem ser deletados  
❌ **Incompatibilidade com sistema legacy:** NeoEve é cloud-first; não integra com sistemas antigos  
❌ **Backup/restore de dados apagados:** Após day-37, deleção é permanente e irrecuperável  

---

## 3. DIREITOS E RESPONSABILIDADES DO LEAD

### 3.1 Direitos do Lead Durante Trial

Durante trial, lead tem direito a:

✅ **Teste Completo:** Usar todas as features do plano sem restrição  
✅ **Dados Reais:** Fazer agendamentos reais com clientes (não é demo)  
✅ **Suporte:** Receber suporte padrão do plano (resposta em <24h)  
✅ **Lembretes:** Receber lembretes automáticos sem custo  
✅ **Fila:** Usar fila de espera e encaixe automático  
✅ **Cancelamento:** Cancelar trial a qualquer momento sem penalidade  
✅ **Dados Preservados:** Manter todos os dados após trial se converter em pagamento  
✅ **Reativação:** Reativar tenant suspenso dentro de 30 dias  

### 3.2 Responsabilidades do Lead

Lead compromete-se a:

✅ **Usar Corretamente:** Usar plataforma apenas para fins legais (agendamentos)  
✅ **Aceitar Termos:** Aceitar automaticamente estes termos ao iniciar trial  
✅ **Dados Precisos:** Fornecer informações precisas no onboarding (nome, WhatsApp, serviços)  
✅ **Aviso de Problemas:** Reportar qualquer bug ou erro durante trial  
✅ **Decisão de Continuação:** Decidir até day-7 se quer pagar para continuar  
✅ **Pagamento:** Se quiser continuar após day-7, fornecer cartão válido via Hotmart  
✅ **Cancelamento Proativo:** Se não quer continuar, comunicar ao invés de deixar suspender  

### 3.3 Conformidade LGPD

Lead garante que:

✅ Os dados dos seus clientes foram coletados com consentimento (para fins de agendamento)  
✅ O lead tem direito de compartilhar dados com NeoEve (processadora)  
✅ O lead informou clientes que Eve é uma IA que gerencia agenda  
✅ O lead responde por violação de LGPD (não é responsabilidade de NeoEve)  

---

## 4. ACESSO E FEATURES

### 4.1 Features Disponíveis Durante Trial

Lead tem acesso a **todas as features** do plano selecionado:

| Feature | SOLO87 | SOLOPRO117 | STUDIO157 | SALAO247 | PRO347 |
|---------|--------|-----------|-----------|----------|---------|
| Link da Eve | ✅ | ✅ | ✅ | ✅ | ✅ |
| Agendamento automático | ✅ | ✅ | ✅ | ✅ | ✅ |
| Confirmação WhatsApp | ✅ | ✅ | ✅ | ✅ | ✅ |
| Lembretes (8am + 30min) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fila de espera | ✅ | ✅ | ✅ | ✅ | ✅ |
| Encaixe automático | ✅ | ✅ | ✅ | ✅ | ✅ |
| Aprende ritmo do cliente | ❌ | ✅ | ✅ | ✅ | ✅ |
| Número dedicado | ❌ | ❌ | ✅ | ✅ | ✅ |
| Agendas separadas | ❌ | ❌ | 3 | 6 | 10 |
| Dashboard | ❌ | ❌ | Básico | Monthly | Monthly |
| Suporte prioritário | ❌ | ✅ | ✅ | ✅ | ✅ (Dedicado) |

---

### 4.2 Restrições Durante Trial

Lead não pode:

❌ Exceder limite de profissionais do plano  
❌ Adicionar mais agendas que o plano permite  
❌ Usar API (não disponível em trial)  
❌ Exportar dados em massa (backup via UI apenas)  
❌ Integrar com sistemas terceiros (roadmap futuro)  

---

## 5. DADOS PESSOAIS (LGPD)

### 5.1 O Que NeoEve Coleta e Armazena

Durante trial, NeoEve coleta e armazena (no Firestore, Google Cloud):

✅ **Lead (profissional):**
- Nome
- Telefone WhatsApp
- Email
- Profissão/Nicho

✅ **Serviços do lead:**
- Nome do serviço
- Duração
- Preço (opcional)

✅ **Clientes do lead (durante agendamentos):**
- Nome do cliente
- Telefone
- Serviço agendado
- Data/Hora do agendamento
- Status (confirmado, cancelado, faltou)

✅ **Logs de conversação:**
- Mensagens trocadas com Eve
- Intenções detectadas (extraído por GPT)
- Contexto de agendamento

❌ **NeoEve NUNCA coleta:**
- Dados sensíveis (cartão, CPF, etc.) — Hotmart coleta pagamento
- Áudio/vídeo das chamadas
- Localização em tempo real
- Perfil comportamental detalhado (não fazemos profiling)

### 5.2 Retenção de Dados

**Conforme Política de Privacidade (TBD):**

- Durante estado TRIAL_ATIVO: Dados mantidos em Firestore
- Após estado TRIAL_EXPIRADO: Retenção conforme Política de Privacidade
- Estado DELETADO: Todos os dados são permanentemente removidos (irrecuperável)

**Condições de deleção:** Definidas em POLITICA_PRIVACIDADE_NEOEVE.md

(Não hardcode aqui. Retenção muda por razões legais, não de produto.)

### 5.3 Direito de Acesso e Portabilidade

Lead tem direito a:

✅ **Acessar dados próprios:** Solicitar cópia dos dados a qualquer momento  
✅ **Portabilidade:** Solicitar exportação de dados em formato aberto (JSON)  
✅ **Retificação:** Corrigir dados incorretos  
✅ **Esquecimento (dentro de 37 dias):** Solicitar deleção antes do limit automático  

**Como solicitar:** Enviar email para [contato-legal]@neoeve.com.br

### 5.4 Conformidade LGPD

NeoEve (Processadora de Dados):
- ✅ Cumpre LGPD
- ✅ Não vende dados
- ✅ Criptografa em trânsito (HTTPS) e em repouso (AES-256)
- ✅ Não compartilha com terceiros sem consentimento
- ✅ Realiza backup automático (recuperação de desastres)
- ✅ Audita acesso a dados (logs)

Lead (Responsável pelos Dados de Clientes):
- ✅ Responsável por obter consentimento dos clientes para compartilhar dados com NeoEve
- ✅ Responsável por informar clientes que Eve é uma IA
- ✅ Responsável por responder a direitos LGPD dos clientes

---

## 6. CONTINUAÇÃO APÓS TRIAL

### 6.1 O Que Acontece no Day-7

No **7º dia completo do trial** (dia da expiração):

```
Timeline:
Day 6 (quarta 14h):  Notificação "Amanhã seu trial termina"
                     Link para checkout
                     
Day 7 (quinta 14h):  Trial expira
                     Tenant continua ativo por mais 24h
                     Agenda fica acessível (read-write)
                     
Day 8 (sexta 8h):    Tenant é suspenso
                     Agenda fica read-only
                     Lead recebe: "Trial expirou. Reative em 30 dias"
                     Link para checkout Hotmart
```

### 6.2 Pagamento (Hotmart)

Para continuar após day-7, lead deve:

1. ✅ Clicar no link de checkout (enviado por Eve)
2. ✅ Escolher o plano (pode ser diferente do trial)
3. ✅ Fornecer cartão de crédito válido a Hotmart
4. ✅ Hotmart processa pagamento
5. ✅ Webhook de aprovação retorna à NeoEve
6. ✅ Tenant é reativado
7. ✅ Lead recebe confirmação: "Bem-vindo! Seu plano está ativo"

**Ciclo de faturamento:** Mensal a partir do primeiro pagamento

### 6.3 Upgrade Durante Trial

Se lead quer mudar de plano durante trial:

**Cenário:** Lead escolheu SOLO87 para trial, quer testar STUDIO157

```
Eve: "Ótimo! Vou aumentar seu acesso para STUDIO157 agora.
      Seu trial continua sendo 7 dias, só que com mais features."

No day-7:
→ Lead é cobrado pelo plano STUDIO157 completo (não ajuste proporcional)
→ Crédito de dias já pagos em SOLO87 é automático em Hotmart
```

---

## 7. TRANSIÇÕES: EXPIRAÇÃO E REATIVAÇÃO

### 7.1 Transição: TRIAL_ATIVO → TRIAL_EXPIRADO

**Condição:** Trial atingiu fim do período (duração conforme Catálogo Comercial V1.2, Seção 6.2)

**Ações:**
```
├─ Estado muda para TRIAL_EXPIRADO
├─ Agenda muda para read-only (lead pode ver, não pode alterar)
├─ Eve para de responder a novas interações
├─ Lembretes param
├─ Lead recebe notificação: "Trial expirou. Reative em X dias."
│  (X = período conforme Política de Privacidade)
└─ Transições possíveis:
   ├─ Lead paga → CLIENTE_ATIVO
   ├─ Lead cancela explicitamente → CANCELADO
   └─ Timeout de reativação → DELETADO
```

### 7.2 Janela de Reativação

Lead pode reativar durante o período definido em POLITICA_PRIVACIDADE_NEOEVE.md:

```
[TRIAL_EXPIRADO com reativação disponível]:
├─ Tenant em read-only
├─ Todos os dados preservados
├─ Lead pode pagar a qualquer momento
├─ Pagamento reativa imediatamente
└─ Sem penalidade por atraso

[Se lead não reativar até timeout]:
└─ Transição automática para DELETADO (conforme Política)
```

### 7.3 Transição: TRIAL_EXPIRADO/CANCELADO → DELETADO

**Condição:** Timeout de reativação atingido (conforme Política de Privacidade)

**Ações:**
```
├─ Todos os dados são permanentemente removidos:
│  ├─ Lead data
│  ├─ Tenant e configurações
│  ├─ Agendamentos
│  ├─ Clientes e profissionais
│  ├─ Contexto e sessões
│  ├─ Backups
│  └─ Logs associados
│
├─ Lead recebe aviso final (antes de DELETADO)
└─ Após DELETADO:
   ├─ Irrecuperável
   ├─ Lead pode fazer novo signup (nova conta)
   └─ Histórico prévio não é acessível
```

---

## 6. ACOMPANHAMENTO INTELIGENTE DO TRIAL (Trial Value Reinforcement)

### 6.1 Objetivo e Filosofia

Durante o trial, a NeoEve deve reforçar o valor percebido utilizando **EXCLUSIVAMENTE dados reais** coletados durante o uso do sistema.

**Filosofia Central:**
```
Mostrar o que aconteceu
    ↑
  (baseado em fatos observados)

Nunca

Prometer o que poderá acontecer
    ↑
  (especulação ou estimativa)
```

**Regra de Ouro:** 
Se não pode ser derivado da telemetria do próprio cliente, não deve ser comunicado.

---

### 6.2 Princípios Obrigatórios

#### 6.2.1 O Que é PROIBIDO

❌ **Nunca inventar métricas**
- Não criar dados que não foram coletados
- Não estimar atividades que não ocorreram

❌ **Nunca estimar faturamento, economia ou ganho**
- Frases como "Você economizou R$ X" são proibidas
- Frases como "Você poderia ganhar R$ X" são proibidas
- Qualquer extrapolação de receita é proibida

❌ **Nunca fazer projeções de resultado**
- Não afirmar "retorno em X meses"
- Não fazer prognósticos de lucro
- Não prometer "nos próximos 3 meses você..."

❌ **Nunca criar comparações com outros clientes**
- Comparações inter-clientes são proibidas (mesmo anonimizadas)
- Percentis ("você usa mais que 90% dos clientes") são proibidos
- Benchmarks sem aprovação estatística formal são proibidos

❌ **Nunca pressionar comercialmente durante o acompanhamento**
- Check-in não é oportunidade de venda
- Relatório não termina em CTA agressivo
- Decisão deve emergir naturalmente

❌ **Nunca usar interpretações produzidas exclusivamente por IA**
- Conclusões psicológicas ("cliente indeciso", "propenso a churn")
- Classificações subjetivas ("cliente de alto valor", "cliente arriscado")
- Predições sem modelo estatístico validado

---

#### 6.2.2 O Que é PERMITIDO: Dados Diretos e Derivações Determinísticas

**Princípio:** São permitidos dados diretamente registrados e métricas derivadas por regras determinísticas, documentadas, reproduzíveis e auditáveis.

✅ **Dados diretamente registrados:**
- Número de mensagens recebidas (campo na telemetria)
- Número de agendamentos criados (evento no Firestore)
- Timestamp de interações (registro de banco de dados)
- Status de confirmação/cancelamento (estado do documento)

✅ **Derivações determinísticas (cruzamento de dados com regra clara):**
- "Sete mensagens foram recebidas enquanto você estava atendendo"
  - Regra: Timestamp da mensagem ∈ [horário_início_atendimento, horário_fim_atendimento]
  - Derivação: Determinística, auditável, reproduzível
  - Documentação: Regra acima explica como foi calculado

- "Taxa de resposta automática: 85%"
  - Regra: (mensagens_respondidas_automaticamente / total_mensagens) × 100
  - Derivação: Determinística, verificável
  
- "Agendamentos marcados fora do horário comercial: 3"
  - Regra: Timestamp do agendamento não ∈ [horário_abertura, horário_fechamento]
  - Derivação: Determinística, auditável

**Requisitos para derivação ser permitida:**
```
☐ Regra é matemática ou lógica pura (não interpretativa)
☐ Regra é documentada explicitamente
☐ Regra é reproduzível (mesmo input → mesmo output)
☐ Regra é auditável (pode-se verificar o cálculo)
☐ Não há espaço para subjetividade
☐ Não há estimativa envolvida
```

❌ **Derivações que NÃO são permitidas:**
- "Você é um cliente de alto valor" (interpretação subjetiva)
- "O cliente provavelmente vai churn" (predição sem modelo validado)
- "Taxa esperada de conversão: 25%" (estimativa baseada em suposição)
- "Você está tendo sucesso" (conceito vago, sem métrica)

---

#### 6.2.3 O Que é PERMITIDO: Comparações

✅ **Comparações internas (antes/depois do mesmo cliente)**
- "Nos primeiros 3 dias chegaram 12 mensagens"
- "Na semana seguinte chegaram 18 mensagens"
- Isso mostra progressão real

✅ **Comparações com período do próprio trial**
- "Comparado com o 1º dia, sua agenda está..."
- Sempre referenciando dados do próprio cliente

✅ **Comparações entre dias do mesmo cliente**
- "Segunda chegaram 8 mensagens; quinta chegaram 12"
- Mostra variação real observada

✅ **Fatos baseados em telemetria observável**
- "Essas 6 mensagens chegaram enquanto você estava em atendimento"
- Desde que a timestamp o confirme

✅ **Apresentar exatamente o que foi registrado**
- Mensagens respondidas automaticamente
- Clientes atendidos
- Agendamentos realizados
- Remarcações e cancelamentos
- Atividades fora do horário comercial

---

### 6.3 Check-in do Meio do Trial

#### 6.3.1 Momento e Objetivo

**Quando:** Na primeira metade do período de trial (exatamente qual dia: conforme Catálogo Comercial V1.2, Seção 6.2)

**Objetivo:** Mostrar valor percebido sem vender. Reforçar que NeoEve trabalhou enquanto o cliente trabalhou.

#### 6.3.2 Estrutura do Check-in

```
1. Abertura personalizada
   ├─ Usar nome do cliente
   ├─ Exemplo de intenção: 
   │  "Maria, enquanto você trabalhava, a NeoEve também trabalhou."
   └─ (Não copiar literalmente - adaptar ao contexto real)

2. Apresentar dados reais
   ├─ Mensagens respondidas (número exato)
   ├─ Clientes atendidos (número exato)
   ├─ Agendamentos realizados (número exato)
   ├─ Remarcações (número exato)
   ├─ Cancelamentos (número exato)
   ├─ Conversas fora do horário (quando aplicável)
   └─ Outras métricas efetivamente registradas
   
3. Reforçar benefício observado
   ├─ Exemplo de intenção:
   │  "Você continuou atendendo suas clientes enquanto a NeoEve 
   │   cuidava das conversas automáticas."
   ├─ Conectar dados ao benefício prático
   └─ Nunca fazer promessa, sempre observação factual

4. Abrir diálogo (SEM CTA de venda)
   ├─ Perguntar: "Quer ver mais detalhes?"
   ├─ Oferecer: "Posso mostrar como isso funciona?"
   ├─ Sugerir: "Quer explorar outras funcionalidades?"
   └─ Objetivo: Conversação, não fechamento
```

#### 6.3.3 O Que NÃO Fazer no Check-in

❌ **Não oferecer assinatura**
- Check-in não termina em venda

❌ **Não usar CTAs agressivos:**
- "Assine agora"
- "Escolha seu plano"
- "Últimos dias de trial"
- "Não perca essa oportunidade"
- Qualquer variação desses

❌ **Não criar urgência artificial**
- Fake scarcity ("apenas 2 vagas")
- Descontos temporários
- Pressão de tempo

---

### 6.4 Segmentação por Situação Operacional

A NeoEve deve categorizar o cliente baseado em sua situação operacional real, não apenas em números. 

**Nota Importante:** Os números abaixo são exemplos de parâmetros configuráveis. A situação operacional tem prioridade sobre volume.

#### 6.4.1 Situação 1: Onboarding Incompleto

**Definição:** Cliente iniciou trial mas não finalizou configuração mínima

**Indicadores:**
- Horários não configurados (ou configurados parcialmente)
- Nenhum serviço cadastrado
- Nenhum agendamento realizado
- Sem interação de clientes reais

**Abordagem:**
```
Foco: Completar configuração, não medir volume
├─ Oferecer guia passo-a-passo
├─ Validar cada etapa
├─ Exemplo de intenção:
│  "Vi que sua agenda ainda não está pronta. Vamos configurar 
│   seus horários e serviços em 5 minutos?"
└─ Objetivo: Primeira experiência funcional
```

**Sem métricas a apresentar:** Focar em suporte, não em relatório.

---

#### 6.4.2 Situação 2: Configurado, Sem Movimento Suficiente

**Definição:** Onboarding completo, mas volume de atividade é baixo

**Indicadores:**
- Configuração completa (horários, serviços, profissionais)
- Poucos ou nenhum cliente durante o período
- Sem atividade de mercado real (não é falha do sistema)

**Abordagem:**
```
Foco: Validar que configuração está correta
├─ Confirmar que período tem baixa demanda natural
├─ Não criticar números baixos
├─ Exemplo de intenção:
│  "Essa semana foi mais calma, mas sua agenda está pronta. 
│   Quando os clientes chegarem, Eve vai estar aqui."
└─ Objetivo: Confiança no sistema
```

**Validar antes de comunicar:** É sazonalidade, feriado, ou realmente ausência de demanda?

---

#### 6.4.3 Situação 3: Movimento Existente, Mas Fluxo Bloqueado

**Definição:** Cliente recebe mensagens, mas conversas não se convertem em agendamentos

**Indicadores:**
- Muitas mensagens recebidas
- Poucos agendamentos realizados
- Taxa de conversão anormalmente baixa
- Possíveis causas: resposta ineficaz, horários não disponíveis, serviço não reconhecido

**Abordagem:**
```
Foco: Diagnosticar e resolver o bloqueio
├─ Revisar configuração (horários estão realmente visíveis?)
├─ Revisar respostas (estão sendo claras?)
├─ Exemplo de intenção:
│  "Você recebeu 18 mensagens mas marcou apenas 1 agendamento. 
│   Quer revisar a configuração ou minhas respostas?"
└─ Objetivo: Desbloquear o fluxo
```

**Análise causal:** Investigar por quê antes de comunicar números.

---

#### 6.4.4 Situação 4: Uso Saudável com Valor Comprovado

**Definição:** Uso consistente, taxa de conversão normal, sistema funcionando como esperado

**Indicadores:**
- Mensagens recebidas e respondidas automaticamente
- Taxa de conversão em agendamentos é saudável
- Confirmações e cancelamentos sendo processados
- Uso sustentável (não picos artificiais)

**Abordagem:**
```
Foco: Mostrar resultados obtidos
├─ Destacar eficiência do sistema
├─ Ressaltar automação em ação
├─ Exemplo de intenção:
│  "Você recebeu 24 mensagens e marcou 6 agendamentos. 
│   A NeoEve organizou tudo enquanto você atendia."
└─ Abrir para: exploração de features adicionais
```

**Finalização:** Porta aberta natural, sem pressão.

---

#### 6.4.5 Situação 5: Uso Intenso com Valor Comprovado

**Definição:** Alto volume de atividade, sistema em capacidade plena, valor tangível

**Indicadores:**
- Alto volume de mensagens processadas
- Múltiplos agendamentos por período
- Taxa de cancelamento/remarcação dentro do esperado
- Uso diário ou quase diário

**Abordagem:**
```
Foco: Validar escalabilidade
├─ Confirmar que plano é adequado para volume
├─ Avaliar necessidade de upgrade futuro
├─ Exemplo de intenção:
│  "Você marcou 12 agendamentos esta semana. A NeoEve 
│   processou 52 mensagens enquanto você trabalhava."
└─ Abrir para: otimizações e features premium
```

**Finalização:** Conversa sobre sustainability e próximos passos.

---

#### 6.4.6 Nota sobre Números como Parâmetros

Os números mencionados acima (18 mensagens, 6 agendamentos, etc.) são exemplos de **parâmetros configuráveis**, não limites arquiteturais.

**Princípio:** Dois clientes com mesma métrica podem estar em situações diferentes:
- Cliente A: 12 mensagens, 0 agendamentos → Onboarding incompleto (Situação 1)
- Cliente B: 12 mensagens, 6 agendamentos → Uso saudável (Situação 4)

**A situação operacional** (configuração completa? fluxo funcionando? demanda real?) tem prioridade sobre volume.

---

### 6.5 Segmentação por Causa

Além do volume de uso, a NeoEve pode identificar **por quê** o lead está em cada perfil.

#### 6.5.1 Causas Identificáveis

```
Causa A: Agenda não configurada
├─ Sintoma: Poucos agendamentos apesar de muitas mensagens
├─ Ação: Oferecer ajuda de configuração
└─ Exemplo: "Você tem 20 mensagens mas nenhum agendamento? 
             Talvez os horários não estejam visíveis."

Causa B: Poucos clientes durante período
├─ Sintoma: Baixo volume geral
├─ Ação: Validar que não é falha do sistema
└─ Exemplo: "Essa é a semana que você marcou, não é esperado 
             ver muitas mensagens. É normal."

Causa C: Mensagens sem conversão em agendamento
├─ Sintoma: Muitas mensagens respondidas, poucos agendamentos
├─ Ação: Oferecer consultoria sobre qualidade de resposta
└─ Exemplo: "Você recebeu 30 mensagens mas marcou apenas 2 
             agendamentos. Quer revisar algumas respostas?"

Causa D: Utilização plena
├─ Sintoma: Uso balanceado e consistente
├─ Ação: Explorar features adicionais
└─ Exemplo: "Você está usando tudo como esperado. Quer conhecer 
             funcionalidades extras?"
```

#### 6.5.2 Investigação de Causa

NeoEve deve usar telemetria para investigar antes de comunicar:

```
Se volume baixo, verificar:
├─ Horários foram configurados? (SIM/NÃO)
├─ Serviços foram cadastrados? (SIM/NÃO)
├─ Qual foi o período? (férias, fim de semana, dia útil?)
├─ Há conversas que não viraram agendamento? (SIM/NÃO)
└─ Reputação do cliente (primeira vez, já consolidado?)
```

**Cada causa deve gerar uma abordagem diferente:**
- Configuração incompleta → Suporte
- Período baixo → Validação
- Qual conversão baixa → Consultoria
- Tudo ótimo → Exploração de features

---

### 6.6 Relatório Final do Trial

#### 6.6.1 Momento e Estrutura

**Quando:** No penúltimo dia do período de trial (exatamente qual dia: conforme Catálogo Comercial V1.2, Seção 6.2)

**Objetivo:** Mostrar tudo o que a NeoEve realizou. Não criar urgência artificial.

#### 6.6.2 Conteúdo do Relatório

Estrutura do relatório focada em fatos observáveis:

```
[RELATÓRIO DE TRIAL — RESUMO DO PERÍODO]

1. Processamento de Mensagens
   ├─ Total de mensagens recebidas: X
   ├─ Respondidas automaticamente: Y
   ├─ Taxa de cobertura automática: Y/X = Z%
   └─ Tempo médio de resposta: N segundos

2. Agendamentos
   ├─ Novos agendamentos criados: X
   ├─ Agendamentos confirmados pelo cliente: Y
   ├─ Solicitações de remarcação: Z
   ├─ Solicitações de cancelamento: W
   └─ Clientes únicos atendidos: V

3. Padrão de Atividade
   ├─ Mensagens recebidas durante horário comercial: X
   ├─ Mensagens recebidas fora do horário: Y
   ├─ Horário com maior volume: [HH:MM]
   ├─ Dias com maior volume: [dias da semana]
   └─ Dias com menor volume: [dias da semana]

4. Disponibilidade e Confiabilidade
   ├─ Tempo de atividade do sistema: X%
   ├─ Erros registrados: Y
   ├─ Mensagens não processadas (rejeições): Z
   └─ Tempo médio de processamento: N ms

5. Resumo de Valor Entregue
   ├─ A NeoEve processou X mensagens
   ├─ Enquanto você atendia outras pessoas
   ├─ Seus agendamentos foram organizados automaticamente
   └─ Nenhuma mensagem foi perdida
```

**O que NUNCA aparece no relatório:**
```
❌ "Comportamento de clientes" (genérico e interpretativo)
❌ "Você é um cliente de alto valor"
❌ "Estimativa de economia"
❌ "Projeção de crescimento"
❌ "Comparação com outros clientes"
❌ Qualquer conclusão psicológica ou comercial
```

#### 6.6.3 Tom do Relatório

```
✅ Foco: Apresentar o que foi realizado
   Exemplo: "A NeoEve processou 47 mensagens enquanto você 
            continuava atendendo."

✅ Tom: Observacional, nunca laudatório
   Evitar: "Incrível!", "Fantástico!", "Você foi ótimo!"
   Usar: "Você recebeu X mensagens. Processamos Y automaticamente."

❌ Não criar narrativas artificiais
   Evitar: "Se continuasse assim, você faturaria R$ XXX"
   Usar: "Nos próximos dias espere padrão semelhante"

❌ Não comparar com expectativas não confirmadas
   Evitar: "Você poderia ter ganho mais"
   Usar: "Esse foi o padrão de mensagens da sua semana"
```

#### 6.6.4 Call-to-Action Discreta

**Apenas após apresentar o relatório completo:**

```
Exemplo de intenção (nunca literal):

"Durante esses 7 dias, você viu tudo funcionando. 
Se quer continuar, basta escolher um plano e pronto."

Características:
├─ Informativa (não urgente)
├─ Simples (não complexa)
├─ Opcional (não forçada)
├─ Pós-valor (não pré-venda)
└─ Link discreto para checkout (não botão destacado)
```

**O Que NÃO Fazer:**
```
❌ "Últimos 24 horas de trial!"
❌ "Assine agora e ganhe desconto"
❌ "Sua conta será deletada se não assinar"
❌ "Clique aqui URGENTE"
❌ "Risco: perder tudo"
```

---

### 6.7 Política de Transparência

A NeoEve deve ser transparente sobre a estratégia de acompanhamento:

#### 6.7.1 O Que Comunicar ao Lead

```
No início do trial, comunicar:

"Durante seu trial, vamos acompanhar como a NeoEve está 
funcionando. Usaremos apenas os dados reais do seu uso 
para mostrar o valor entregue. Sem comparações, sem 
promessas — apenas o que realmente aconteceu."
```

#### 6.7.2 O Que NÃO Comunicar

❌ Nunca comunicar que está sendo "rastreado"  
❌ Nunca usar linguagem invasiva ("monitoramento")  
❌ Nunca prometer que "vamos te ensinar a vender mais"  

---

### 6.8 Dados Permitidos vs Proibidos

#### 6.8.1 Dados Que PODEM ser Comunicados

| Dado | Permitido | Razão |
|------|-----------|-------|
| Total de mensagens | ✅ | Fato observado |
| Taxa de resposta automática | ✅ | Derivado de telemetria |
| Agendamentos realizados | ✅ | Fato observado |
| Cancelamentos processados | ✅ | Fato observado |
| Tempo fora do expediente | ✅ | Timestamp pode confirmar |
| Clientes atendidos | ✅ | Fato observado |
| Média de resposta (segundos) | ✅ | Métrica técnica real |

#### 6.8.2 Dados Que SÃO PROIBIDOS

| Dado | Proibido | Razão |
|------|----------|-------|
| "Você economizou R$ X" | ❌ | Estimativa, não fato |
| "Seu faturamento aumentou X%" | ❌ | Especulação |
| "Você vendeu X% mais" | ❌ | Não é controlado pela NeoEve |
| "Ranking vs outros clientes" | ❌ | Comparação proibida |
| "Você usa mais que 80% dos usuários" | ❌ | Percentil não validado |
| "Em 3 meses você vai recuperar o investimento" | ❌ | Promessa não verificável |
| "Você poderia atender 10x mais" | ❌ | Suposição |

---

### 6.9 Validação de Dados Antes de Comunicar

Antes de qualquer comunicação de acompanhamento:

```
Checklist de Validação:

☐ O dado vem de telemetria real? (não é estimativa)
☐ Pode ser derivado do comportamento do cliente? (não é inferência)
☐ É observável nos logs? (não é interpretação)
☐ Evita estimativas de economia/ganho? (não promete ROI)
☐ Evita comparações com outros? (não benchmarking)
☐ Evita prognósticos? (não promete futuro)
☐ É factual e verificável? (pode ser auditado)
☐ Contribui para mostrar valor? (não é ruído)

Se qualquer resposta for NÃO: 
→ Não comunicar esse dado
```

---

### 6.10 Exemplos de Comunicações Permitidas vs Proibidas

#### Permitido

```
✅ "Você recebeu 34 mensagens de clientes esta semana."
   (Fato, número exato, telemetria)

✅ "A NeoEve respondeu 28 delas automaticamente."
   (Fato, número exato, ação registrada)

✅ "Isso aconteceu enquanto você estava atendendo outras pessoas."
   (Fato, timestamps confirmam)

✅ "Segunda teve 5 mensagens. Quinta teve 8."
   (Comparação interna, mesmo cliente, dias reais)

✅ "8 agendamentos foram marcados durante o trial."
   (Fato, número exato)
```

#### Proibido

```
❌ "Você economizou 2 horas"
   (Especulação, não telemetria)

❌ "Você poderia ganhar mais R$ 500 por mês"
   (Estimativa, não fato)

❌ "90% dos seus concorrentes vendem menos que você"
   (Comparação com outros, benchmarking proibido)

❌ "Se continuar assim, em 3 meses sua renda dobrará"
   (Promessa de futuro, não verificável)

❌ "Você usa a NeoEve mais que 85% dos clientes"
   (Percentil sem aprovação estatística)

❌ "Ganhe R$ 1.000 a mais por mês — assine agora!"
   (Promessa de ganho + CTA agressivo)
```

---

### 6.11 Filosofia Final

**A NeoEve vende através do valor comprovado pelo uso real.**

```
Estratégia de Trial Value Reinforcement:

┌──────────────────────────────────────────────────────┐
│                                                      │
│  Início do Trial                                     │
│  ├─ Usuário configura, explora, começa a usar       │
│  │                                                   │
│  Primeira Metade do Período                         │
│  ├─ Check-in: Mostrar valor observado até aqui      │
│  ├─ Adaptar suporte ao perfil (A/B/C/D)             │
│  │                                                   │
│  Penúltimo Dia                                       │
│  ├─ Relatório: Resumo de tudo realizado              │
│  ├─ Apresentar valor total entregue                 │
│  │                                                   │
│  Término do Período                                  │
│  ├─ Informação objetiva sobre continuidade          │
│  ├─ Sem pressão ou urgência artificial              │
│  │                                                   │
│  Primeiro Dia Após Expiração                        │
│  ├─ Aplicar regras de suspensão/deletação           │
│  ├─ Oferecer reativação (período conforme Política) │
│  │                                                   │
│  Decisão Natural                                     │
│  ├─ Baseada em fatos observados, não em pressão     │
│  └─ Cliente escolhe continuar ou não                │
│                                                      │
└──────────────────────────────────────────────────────┘

(Duração exata de cada fase: Catálogo Comercial V1.2)
```

**Nunca:**
```
❌ Inventar dados
❌ Estimar resultados
❌ Prometer retorno
❌ Comparar com outros
❌ Pressionar comercialmente
❌ Criar urgência artificial
```

**Sempre:**
```
✅ Mostrar o que aconteceu
✅ Baseado em telemetria
✅ Adaptado à situação operacional real
✅ Abrir diálogo, não forçar venda
✅ Respeitar período de decisão
✅ Deixar conclusão natural emergir
```

---

### 6.12 Resultado Pretendido (Não Garantido)

**Esta política de acompanhamento inteligente pretende:**

✅ Favorecer uma decisão baseada no valor efetivamente observado  
✅ Reduzir o risco de conversões obtidas por pressão ou expectativas artificiais  
✅ Construir confiança através de transparência factual  
✅ Adaptar o suporte a cada situação operacional real  

**O que esta política NÃO garante:**

❌ Maior satisfação do cliente (será medida depois, se houver)  
❌ Menor taxa de churn (será medida depois, se houver)  
❌ Conversão de trial em assinatura (decisão do cliente, não da NeoEve)  
❌ Retenção a longo prazo (depende de satisfação com produto)  

**Por quê:** A satisfação e o churn são resultado de múltiplos fatores (produto, suporte, preço, necessidade real). 

Esta política garante apenas que a decisão inicial de continuar será baseada em fatos, não em pressão.

**Medições futuras:** Satisfação e churn deverão ser medidas separadamente através de pesquisas e análise de dados reais pós-conversão.

---

## 7. VALIDAÇÃO DE CONFORMIDADE

### 8.1 Cenários de Encaminhamento

Durante trial, se lead tem dúvida fora do escopo de Eve, encaminhamento automático acontece:

| Situação | Eve Diz | Encaminha Para | Tempo |
|----------|---------|-----------------|-------|
| **Pergunta jurídica** | "Isso precisa de um advogado. Deixa eu passar pro time legal." | Legal | <2h |
| **Dúvida sobre LGPD** | "Conformidade é sério. Vou passar pro time de compliance." | Compliance | <4h |
| **Desconto/Negociação** | "Deixa eu ver com meu gerente se é possível." | Comercial | <2h |
| **Bug ou erro** | "Que chato! Vou chamar o time técnico." | Suporte | <1h |
| **Nenhuma atividade até day-3** | "Vi que ainda não testou. Quer ajuda pra primeira agenda?" | Onboarding | Imediato |
| **Dúvida sobre trial policy** | "Isso a gente precisa detalhar com uma pessoa. Deixa chamar." | Customer Success | <2h |

### 8.2 SLA de Encaminhamento

| Tipo | SLA | Contato |
|------|-----|---------|
| Bug crítico | <1h | suporte@neoeve.com.br |
| Dúvida operacional | <4h | support@neoeve.com.br |
| Questão legal | <24h | legal@neoeve.com.br |
| Compliance/LGPD | <24h | compliance@neoeve.com.br |

---

## 9. REATIVAÇÃO DE TENANT SUSPENSO

### 9.1 Processo de Reativação

Se lead quer reativar durante janela 30 dias (days 8-37):

```
Lead clica em "Reativar" ou vai ao checkout
    ↓
Eve valida: tenant está suspenso?
    ├─ SIM → prosseguir
    └─ NÃO → erro (já está ativo)
    
    ↓
Hotmart processa pagamento (mesmo fluxo que trial)
    ↓
Lead fornece cartão
    ↓
Webhook de aprovação retorna
    ↓
NeoEve reativa tenant
    ├─ Tenant volta para "ATIVO"
    ├─ Eve começa a responder
    ├─ Lembretes são retomados
    ├─ Clientes podem agendar novamente
    └─ Lead recebe: "Bem-vindo de volta! Sua assinatura está ativa"
```

### 9.2 Dados Após Reativação

- ✅ Todos os agendamentos históricos são preservados
- ✅ Todos os clientes já cadastrados são mantidos
- ✅ Preferências (horários, serviços) são mantidas
- ✅ Lembretes dos próximos dias são retomados

### 9.3 Impossibilidade de Reativação

Lead NÃO pode reativar se:

❌ Passou day-37 (39+ dias após trial) — deve fazer novo signup  
❌ Tenant foi deletado manualmente  
❌ Conta foi bloqueada por violação de TOS  
❌ Cartão recusado e lead não forneceu alternativa em 30 dias  

---

## 10. CANCELAMENTO E SAÍDA

### 10.1 Cancelamento Durante Trial

Lead pode cancelar a qualquer momento (days 1-7):

```
Lead diz: "Quero cancelar"
    ↓
Eve: "Que pena! Quer nos deixar uma sugestão?"
    ↓
Lead fornece feedback (opcional)
    ↓
Tenant é suspenso imediatamente
    ├─ Todos os dados são preservados
    ├─ Lead pode reativar dentro de 37 dias ainda
    └─ Lead recebe: "Sua conta foi cancelada. Pode reativar quando quiser nos próximos 30 dias"
```

### 10.2 Cancelamento Pós-Pagamento

Lead pode cancelar a qualquer momento (mesmo com assinatura ativa):

```
Lead solicita cancelamento
    ↓
Eve: "Que pena! Sua assinatura será cancelada no final deste ciclo."
    ↓
NeoEve marca tenant com flag: "cancelamento_pendente"
    ↓
No final do ciclo (30 dias após último pagamento):
    ├─ Cobranças futuras param
    ├─ Tenant é suspenso
    ├─ Lead entra em janela de 30 dias novamente
    └─ Se não reativar: deleção no day-38
```

### 10.3 Saída (Sem Reativação)

Se lead deixar passar 37 dias sem pagar:

```
Day 8-37:  Janela de reativação
Day 38:    Tenant deletado automaticamente
           Lead recebe: "Sua conta foi deletada. Para começar de novo, faça signup."
           
Lead pode fazer novo signup (nova tenant_id):
├─ Trial é 7 dias novamente
├─ Histórico anterior é perdido
└─ Novo lead ID é gerado
```

---

## 11. RESPONSABILIDADE LIMITADA

### 11.1 Isenção de Garantias

NeoEve funciona no "estado em que se encontra" (AS-IS). NeoEve não garante:

❌ Que Eve responda 100% corretamente em todas as situações  
❌ Que não haja atrasos ou downtime (mesmo com >99% uptime)  
❌ Que clientes do lead responderão às mensagens de Eve  
❌ Que você ganhará mais clientes (Eve organiza, não vende)  
❌ Que dados serão recuperáveis após deleção (day-38+)  

### 11.2 Limitação de Indenização

**Em nenhuma circunstância NeoEve é responsável por:**

❌ Lucro cessante  
❌ Perda de clientes/receita  
❌ Danos indiretos  
❌ Perda de reputação  

**Máximo que NeoEve pode ser responsabilizada:** Valor pago no trial (R$ 0 durante trial grátis, ou valor do plano após conversão)

### 11.3 Força Maior

NeoEve não é responsável por:

❌ Outages de Google Cloud / Firestore  
❌ Problemas de WhatsApp Business API  
❌ Problemas de conectividade do lead  
❌ Falhas de serviços terceiros (Hotmart, Meta, etc.)

---

## 12. TERMOS GERAIS

### 12.1 Modificação de Termos

NeoEve pode modificar estes termos a qualquer momento. Lead será notificado com **7 dias de antecedência**.

Se lead não concorda com a mudança:
- ✅ Lead pode cancelar antes da mudança entrar em vigor
- ❌ Continuação automática = aceitação da mudança

### 12.2 Lei Aplicável

Estes termos são governados por leis da República Federativa do Brasil.

Qualquer disputa será resolvida em:
- 1º lugar: Negociação direta
- 2º lugar: Arbitragem (se negociação falhar)
- 3º lugar: Jurisdição brasileira

### 12.3 Contato para Dúvidas

Para dúvidas sobre este contrato:

```
Email:    contrato@neoeve.com.br
WhatsApp: +55 [número]
Horário:  De segunda a sexta, 9h-18h
```

### 12.4 Vigência

Estes termos começam quando lead clica "Aceitar trial" e vigoram por:
- ✅ Toda a duração do trial (dias 1-7)
- ✅ Janela de reativação (days 8-37)
- ✅ Após pagamento (conversão em assinatura)
- ✅ Até cancelamento ou deleção

---

## 📋 CHECKLIST DE APROVAÇÃO LEGAL

Este contrato requer aprovação de:

- [ ] **Departamento Jurídico:** Conformidade com leis brasileiras
- [ ] **LGPD Compliance:** Revisão de seções 5.x
- [ ] **Hotmart/Billing:** Alinhamento de termos de pagamento
- [ ] **Engenharia:** Validação de processos técnicos (suspensão, deleção, reativação)
- [ ] **Comercial:** Alinhamento com política de trial (Catálogo V1.2)
- [ ] **Suporte:** Treinamento sobre políticas de SLA e encaminhamento
- [ ] **Eve (IA):** Respostas atualizadas com refs a este contrato

---

## 📞 VERSIONING

**Versão:** 1.0  
**Status:** ⚠️ RASCUNHO — Requer Aprovação Jurídica  
**Data:** 2026-07-27  
**Criado por:** Claude Code (assistente)  
**Próximo:** Submeter para legal@neoeve.com.br  

---

## ✅ PRÓXIMOS PASSOS

1. **Legal Review** — Submeter para jurídico revisar (LGPD compliance, responsabilidades)
2. **Engenharia Review** — Validar processos técnicos (suspensão, deleção, reativação)
3. **Comercial Alignment** — Garantir consistência com Catálogo V1.2
4. **Eve Training** — Atualizar respostas da IA com referências a este contrato
5. **Lead Acceptance** — Integrar aceitação deste contrato no fluxo de trial
6. **V1.1 Approval** — Após revisões, publicar versão final

---

**Contrato de Trial:** 2026-07-27  
**Status:** Aguardando Revisão Legal  
**Próxima Revisão:** Após aprovações acima

