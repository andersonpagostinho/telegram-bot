# Contrato do Domínio Comercial — NeoEve

**Data de Criação:** 2026-07-22  
**Versão:** 1.1  
**Status:** Revisado — Aguardando Aprovação Arquitetural  
**Baseado em:** Auditoria Oficial V2.1 (AUDITORIA_PROMESSA_VS_CAPACIDADE_NEOEVE.md)  
**Revisão:** Correções arquiteturais de identidade múltipla, isolamento de domínios, idempotência e modelo híbrido

---

## 0. PRINCÍPIOS FUNDAMENTAIS

### 0.1 Identidade Múltipla, Contexto Singular

**Princípio Corrigido:**

Um ator pode possuir múltiplos vínculos e papéis contextuais. Cada mensagem, porém, deve ser processada por um único domínio responsável e dentro de um único contexto resolvido.

**Exemplos de Vínculos Simultâneos:**
- Alice: lead comercial de novo negócio + dono de tenant_1 + profissional de tenant_2 + cliente de tenant_3
- Bob: lead comercial + admin interno da NeoEve
- Carol: lead comercial + dono + cliente final (múltiplas unidades)

**Garantia:** Nenhum conflito entre papéis. O rotoador determina qual domínio processa cada mensagem.

### 0.2 Estrutura de Identidade Global

```
Atores/{actor_id}
    identidade_global
    criado_em
    atualizado_em

VinculosTenant/{vinculo_id}
    actor_id
    tenant_id
    papel_no_tenant (DONO | PROFISSIONAL | CLIENTE_FINAL | ADMIN_INTERNO)
    criado_em
    atualizado_em

Jornada Comercial (Leads/{lead_id})
    actor_id (indexado, pode haver múltiplas por ator)
    tenant_id_resultante (após conversão, nulo enquanto comercial)
    status_comercial
    criado_em
    atualizado_em
```

**Justificativa da Separação:**
- Mesmo ator pode retornar meses depois com nova jornada
- Pode contratar múltiplos negócios
- Pode vir de campanhas diferentes
- Pode evoluir de lead para cliente e depois para novo lead

### 0.3 Um Único Canal, Múltiplos Domínios

```
WhatsApp (um número NeoEve)
    ↓
    Resolução de contexto
    ↓
    ├─ DOMÍNIO COMERCIAL
    │   └─ Venda, qualificação, trial, conversão
    │
    ├─ DOMÍNIO ONBOARDING
    │   └─ Configuração pós-conversão
    │
    ├─ DOMÍNIO OPERACIONAL
    │   └─ Agendamento, cancelamento, confirmação
    │
    ├─ DOMÍNIO BILLING
    │   └─ Cobrança, upgrade, downgrade, pagamento
    │
    └─ DOMÍNIO SUPORTE
        └─ Problemas técnicos, questões operacionais
```

**Regra de Ouro:** Uma mensagem é processada por um único domínio. Se ambiguidade, solicitar desambiguação.

### 0.4 Transições São Aditivas, Não Destrutivas

Conversão não substitui jornada comercial. Ela:
1. Encerra jornada comercial
2. Cria tenant
3. Cria vínculo DONO
4. Inicializa onboarding
5. **Preserva histórico comercial para auditoria**

**Resultado:**
```
Lead.status = CONVERTIDO
Lead.tenant_id_resultante = tenant_abc123
VinculoTenant:
  actor_id = 5511987654321
  tenant_id = tenant_abc123
  papel = DONO
Sessao:
  dominio_ativo = ONBOARDING
```

**Garantia:** Histórico do lead permanece consultável. Conversão não é destrutiva.

---

## 1. IDENTIDADE GLOBAL E VÍNCULOS CONTEXTUAIS

### 1.1 Ator — Definição

Um ator é uma entidade no WhatsApp identificada por `actor_id` (número de telefone ou ID Telegram). Possui identidade global única, mas pode ter múltiplos papéis em múltiplos tenants.

**Documento Firestore:** `Atores/{actor_id}`

```json
{
  "actor_id": "5511987654321",
  "identidade_global": {
    "nome": "Maria Silva",
    "email": "maria@example.com",
    "criado_em": "2026-07-22T10:30:00Z",
    "atualizado_em": "2026-07-22T10:30:00Z"
  }
}
```

### 1.2 Vínculos com Tenants

Um ator pode ter múltiplos vínculos, cada um conferindo um papel específico em um tenant específico.

**Documento Firestore:** `VinculosTenant/{vinculo_id}`

```json
{
  "vinculo_id": "vinc_xyz789",
  "actor_id": "5511987654321",
  "tenant_id": "tenant_abc123",
  "papel_no_tenant": "DONO",
  "criado_em": "2026-07-22T11:05:00Z",
  "atualizado_em": "2026-07-22T11:05:00Z"
}
```

### 1.3 Papéis Operacionais Contextuais

| Papel | Domínio | Responsabilidades |
|-------|---------|------------------|
| **DONO** | Operacional / Billing | Administra tenant, profissionais, serviços, agendamentos, faturamento |
| **PROFISSIONAL** | Operacional | Visualiza agenda própria, responde disponibilidade, cancela horários |
| **CLIENTE_FINAL** | Operacional | Consulta agenda pública, faz agendamentos, recebe lembretes |
| **ADMIN_INTERNO** | Suporte / Billing | Intervém em problemas, altera configurações administrativas |

### 1.4 Jornada Comercial (Separada de Vínculos Operacionais)

Um ator pode estar em jornada comercial sem ter vínculos operacionais. Após conversão, ganha vínculo DONO mas mantém histórico comercial.

**Documento Firestore:** `Leads/{lead_id}`

```json
{
  "lead_id": "lead_12345",
  "actor_id": "5511987654321",
  "negocio_candidato": "Salão da Maria",
  "status_comercial": "CONVERTIDO",
  "tenant_id_resultante": "tenant_abc123",
  "etapa_funil": "onboarding",
  "origem": "landing_page",
  "criado_em": "2026-07-22T10:30:00Z",
  "atualizado_em": "2026-07-22T11:05:00Z"
}
```

### 1.5 Múltiplas Jornadas Comerciais Por Ator

Um mesmo ator pode:
- Ser lead para negócio_A (jornada_1, ATIVA)
- Ter lead histórico para negócio_B (jornada_2, CONVERTIDA)
- Ter lead histórico para negócio_C (jornada_3, PERDIDA)

**Regra:** Máximo uma jornada comercial ATIVA por ator, exceto se explicitamente autorizado.

---

## 2. ESTRUTURA DE DADOS — O MODELO COMERCIAL

### 2.1 Coleção Leads/{lead_id}

Representa a jornada comercial. Lead_id é chave única, permitindo múltiplas jornadas por ator.

```json
{
  "lead_id": "lead_12345",
  "actor_id": "5511987654321",
  "negocio_candidato": "Salão da Maria",
  "status_comercial": "EM_CONVERSACAO",
  "etapa_funil": "avaliando_plano",
  
  "qualificacao": {
    "tamanho_negocio": "pequeno",
    "profissionais": 3,
    "segmento": "salao_beleza",
    "usa_agenda": false,
    "levantado_em": "2026-07-22T10:45:00Z"
  },
  
  "plano_recomendado": "SOLO87",
  "plano_escolhido": null,
  
  "objecoes": [
    {
      "tipo": "preco",
      "texto": "Muito caro pra começar",
      "resposta_dada": "Você paga só pelo que usar...",
      "timestamp": "2026-07-22T10:45:00Z"
    }
  ],
  
  "origem": "landing_page",
  "utm_source": "google_ads",
  "utm_campaign": "hair_salons_q3",
  
  "conversacao": {
    "mensagens_trocadas": 7,
    "duracao_minutos": 12,
    "ultima_mensagem_usuario": "2026-07-22T11:00:00Z"
  },
  
  "tenant_id_resultante": null,
  "resultado_comercial": "INDEFINIDO",
  
  "criado_em": "2026-07-22T10:30:00Z",
  "ultima_interacao": "2026-07-22T11:00:00Z",
  "retomada_em": null,
  "atualizado_em": "2026-07-22T11:00:00Z"
}
```

**Estados Válidos de Status Comercial:**
- `EM_CONVERSACAO` — conversa ativa em domínio comercial
- `AGUARDANDO_RESPOSTA` — Eve esperando resposta do lead
- `EM_ANALISE` — lead analisando proposta
- `ACEITE_PENDENTE` — lead pronto para aceitar, aguardando confirmação final
- `ACEITE_REGISTRADO` — lead aceitou, conversão iniciada
- `CONVERTIDO` — tenant criado, vínculo de dono estabelecido
- `ABANDONADO` — sem mensagem >7 dias, sem opt-out explícito
- `RECUSADO` — lead disse explicitamente "não"
- `ADIADO` — lead pediu para retomar depois

---

### 2.2 Coleção Conversoes/{conversion_id}

Rastreia a transição de lead → dono com modelo híbrido: núcleo atômico + etapas recuperáveis.

```json
{
  "conversion_id": "conv_550e8400_e29b_41d4_a716_446655440000",
  "idempotency_key": "actor_5511987654321_lead_12345_conversao_v1",
  
  "actor_id": "5511987654321",
  "lead_id": "lead_12345",
  "plano": "SOLO87",
  
  "estado_conversao": "CONCLUIDA",
  
  "nucleo_atomico": {
    "status": "CRIADO",
    "timestamp": "2026-07-22T11:05:10Z",
    "componentes_criados": [
      "tenant_abcd1234",
      "vinculo_dono_established",
      "conversao_registered",
      "onboarding_inicializado"
    ]
  },
  
  "etapas_recuperaveis": [
    {
      "etapa": "INICIADA",
      "timestamp": "2026-07-22T11:05:00Z",
      "descricao": "Conversão recebida, validações passadas"
    },
    {
      "etapa": "NUCLEO_CRIADO",
      "timestamp": "2026-07-22T11:05:10Z",
      "descricao": "Tenant e vínculo criados atomicamente"
    },
    {
      "etapa": "ONBOARDING_INICIALIZADO",
      "timestamp": "2026-07-22T11:05:15Z",
      "descricao": "Sessão de onboarding ativada"
    },
    {
      "etapa": "CONCLUIDA",
      "timestamp": "2026-07-22T11:05:20Z",
      "descricao": "Mensagem de sucesso enviada ao lead"
    }
  ],
  
  "tenant_id": "tenant_abcd1234",
  "tenant_nome_temporario": "Salao da Maria",
  
  "trial": {
    "estado": "ACEITO",
    "aceito_em": "2026-07-22T11:00:00Z",
    "preparado_em": null,
    "iniciado_em": null
  },
  
  "criado_em": "2026-07-22T11:05:00Z",
  "concluido_em": "2026-07-22T11:05:20Z"
}
```

### 2.3 Modelo Híbrido: Núcleo Atômico + Etapas Recuperáveis

**Núcleo Atômico (Firestore Transaction):**

Executa atomicamente ou falha por completo:
- Criação de Tenants/{tenant_id}
- Criação de VinculosTenant/{vinculo_id} com papel=DONO
- Registro de Conversoes/{conversion_id}
- Atualização de Leads/{lead_id}.status_comercial = CONVERTIDO
- Inicialização de estado de onboarding

**Garantia:** Ou tudo é gravado, ou nada. Nenhum estado parcial.

**Etapas Recuperáveis (Posterior ao Núcleo):**

Podem ser retomadas sem risco de duplicação:
- Envio de mensagem de sucesso ao lead
- Ativação de scheduler para trial
- Disparo de evento para analytics
- Inicialização de integração externa

**Idempotency Key:**
```
actor_id + lead_id + tipo_conversao + versao_decisao
```

**Comportamento:**
- Mesma chave = mesma conversão, sem novo tenant
- Requisição duplicada converge para resultado único
- Retry automático após falha recuperável é seguro

**Estados de Conversão Válidos:**
- `INICIADA` — validações passadas, aguardando núcleo
- `NUCLEO_CRIADO` — tenant e vínculo criados atomicamente
- `ONBOARDING_INICIALIZADO` — sessão de onboarding ativada
- `CONCLUIDA` — todas as etapas sucedidas
- `FALHA_RECUPERAVEL` — falha em etapa recuperável, pode retry
- `FALHA_DEFINITIVA` — falha no núcleo, requer intervenção manual

### 2.4 Invariantes Estruturais

```
∀ lead_id ∈ Leads:
  1. status_comercial ∈ {EM_CONVERSACAO, ABANDONADO, CONVERTIDO, RECUSADO, ADIADO}
  2. Se status == CONVERTIDO, então tenant_id_resultante != null
  3. Se status == CONVERTIDO, existe Conversoes/{conversion_id} com estado == CONCLUIDA
  4. etapa_funil é consistente com status_comercial

∀ conversion_id ∈ Conversoes:
  1. estado_conversao ∈ {INICIADA, NUCLEO_CRIADO, ONBOARDING_INICIALIZADO, CONCLUIDA, FALHA_RECUPERAVEL, FALHA_DEFINITIVA}
  2. idempotency_key é único (não pode haver dois conversion_id com mesma chave)
  3. Se estado == CONCLUIDA, todos os componentes em nucleo_atomico foram criados
  4. tenant_id != null ∧ Tenants/{tenant_id} existe

∀ vinculo_id ∈ VinculosTenant:
  1. actor_id + tenant_id + papel_no_tenant é única
  2. papel_no_tenant ∈ {DONO, PROFISSIONAL, CLIENTE_FINAL, ADMIN_INTERNO}
  3. Não pode existir ator vinculado a tenant parcialmente criado
  4. Se papel_no_tenant == DONO, existe correspondência em Conversoes com estado == CONCLUIDA
```

---

## 3. FUNIL COMERCIAL — TRANSIÇÕES DE ESTADO

### 3.1 Fluxo Ideal (Happy Path)

```
Lead chega no WhatsApp
    ↓
Ator criado (se novo)
Jornada comercial criada (Leads/{lead_id})
    ↓
Eve qualifica (tamanho, segmento, agenda atual)
Leads/{lead_id}.status_comercial = EM_CONVERSACAO
    ↓
Eve recomenda plano (ex: SOLO87)
    ↓
Lead faz perguntas / objeções
Leads/{lead_id}.objecoes[] registrada
    ↓
Eve responde com fatos autorizados
    ↓
Lead aceita trial ("Quero começar!")
Leads/{lead_id}.plano_escolhido = SOLO87
    ↓
Backend inicia conversão (Conversoes/{conversion_id})
    ↓
NÚCLEO ATÔMICO:
  - Cria Tenants/{tenant_id}
  - Cria VinculosTenant/{vinculo_id} com papel=DONO
  - Atualiza Leads/{lead_id}.status_comercial = CONVERTIDO
  - Registra Conversoes/{conversion_id}.estado = NUCLEO_CRIADO
    ↓
Etapas Recuperáveis:
  - Ativa dominio_ativo = ONBOARDING
  - Envia mensagem: "Vamos começar! Primeiro, seus dados..."
  - Conversoes/{conversion_id}.estado = CONCLUIDA
    ↓
Dono entra no domínio de onboarding
```

### 3.2 Interrupções e Retomadas

**Interrupção 1: Lead desaparece, volta dias depois**

```
Lead: "Oi, ainda estou interessado"
    ↓
Buscar Leads/{lead_id} ← encontrado
status_comercial = EM_CONVERSACAO
etapa_funil = avaliando_plano
    ↓
Eve retoma: "Ótimo! Você estava considerando o SOLO87. Tudo bem para começar?"
    ↓
Contexto carregado, conversa continua
```

**Interrupção 2: Lead muda de assunto no meio**

```
Eve: "Você tem quantos profissionais?"
Lead: "E se eu tiver mais depois, consigo trocar de plano?"
    ↓
Intenção detectada: pergunta lateral sobre upgrade
Eve responde: "Sim! Você troca quando precisar. Voltando... quantos profissionais hoje?"
    ↓
Estado_da_conversa: RETOMANDO_PERGUNTA_ANTERIOR
etapa_funil continua = avaliando_plano
```

**Interrupção 3: Lead hesita antes de aceitar**

```
Lead: "Deixa eu pensar..."
    ↓
Leads/{lead_id}.status_comercial = EM_ANALISE
Leads/{lead_id}.etapa_funil = aceite_pendente
    ↓
POLÍTICA DE RETORNO:
  - Sem mensagem outbound automática (não enviar immediately)
  - Se lead retorna em <7 dias, Eve reconhece contexto
  - Se não retorna em 7+ dias, status = ABANDONADO
  - Nenhuma pressão, apenas reconhecimento se voltar
```

**Interrupção 4: Novo lead, mesmo ator**

```
Ator (mesmo 5511987654321):
  Jornada 1: Negócio_A → CONVERTIDO (lead_1)
  Meses depois...
  Jornada 2: Negócio_B (novo lead_id)
    ↓
Criar novo Leads/{lead_id_novo}
Leads/{lead_id_novo}.actor_id = 5511987654321
Iniciar nova qualificação
    ↓
Eve: "Ótimo ver você de novo! Dessa vez qual é o negócio?"
```

**Garantia:** Lead é contexto isolado. Múltiplas jornadas por ator são permitidas e auditáveis.

---

## 4. DOMÍNIO COMERCIAL — RESPONSABILIDADES E LIMITES DE EVE

### 4.1 O Que Eve Interpreta (Não Executa)

✅ **Eve interpreta e recomenda:**
- Intenção (qualificação, objeção, pergunta, aceite)
- Extração de dados (tamanho do negócio, profissionais, segmento)
- Classificação de lead (qualificação alta/média/baixa, urgência)
- Detecção de objeção (preço, desconfiança, necessidade de teste)
- Respostas humanizadas com fatos autorizados

❌ **Eve NUNCA executa:**
- Aprovação de plano (motor valida)
- Oferta de desconto (motor executa, após aprovação humana)
- Criação de tenant (motor executa)
- Garantias sobre roadmap (encaminha para fundador)
- Respostas jurídicas/tributárias (encaminha)
- Dados sensíveis em MemoriaTemporaria (não persiste)

### 4.2 Fallback para Informação Não Autorizada

Quando Eve não tem resposta no catálogo:

```
1. NÃO INVENTAR
   ↓
2. RECONHECER: "Preciso confirmar essa informação"
   ↓
3. REGISTRAR DÚVIDA em Leads/{lead_id}.duvidas_nao_cobertas[]
   ↓
4. PRESERVAR ETAPA DO FUNIL (não regride)
   ↓
5. ENCAMINHAR PARA HUMANO OU FILA DE REVISÃO
   ↓
6. PERMITIR ATUALIZAÇÃO POSTERIOR DO CATÁLOGO
```

**Classificação de Ausência de Informação:**

| Tipo | Ação |
|------|------|
| `NAO_ENCONTRADO_NO_CATALOGO` | Registrar, encaminhar humano |
| `INFORMACAO_AMBIGUA` | Solicitar clarificação humana |
| `REGRAS_EM_CONFLITO` | Escalar para produto |
| `DADO_TEMPORARIAMENTE_INDISPONIVEL` | Tentar novamente, sem assumir |
| `QUESTAO_PROIBIDA` (jurídico, tributário, compliance) | Encaminhar especialista |
| `ENCAMINHAMENTO_HUMANO_OBRIGATORIO` | Fila de suporte |

---

## 5. ROTEAMENTO — MÚLTIPLOS DOMÍNIOS, CONTEXTO ÚNICO

### 5.1 Domínios Disponíveis

| Domínio | Responsabilidade | Acionado Quando |
|---------|-----------------|------------------|
| **COMERCIAL** | Venda, qualificação, objeções, trial | Actor é lead; ou dono pergunta sobre upgrade/novo negócio |
| **ONBOARDING** | Configuração pós-conversão | Lead convertido, primeiro acesso |
| **OPERACIONAL** | Agendamento, cancelamento, confirmação | Dono/profissional/cliente_final utiliza produto |
| **BILLING** | Cobrança, upgrade/downgrade, pagamento | Questão sobre faturamento |
| **SUPORTE** | Problemas técnicos, falhas operacionais | Relato de erro ou falha |

### 5.2 Algoritmo de Roteamento

```
mensagem_recebida(actor_id, texto, tenant_id_contexto=null):
    
    # Passo 1: Resolver identidade global
    ator = consultar Atores/{actor_id}
    if ator not found:
        criar Atores/{actor_id}
    
    # Passo 2: Detectar intenção
    intenção = gpt.classificar(texto)
    
    # Passo 3: Resolver vínculos relevantes
    vínculos = listar VinculosTenant/{actor_id/*}
    
    # Passo 4: Determinar domínio
    if intenção in [QUALIFICACAO, OBJECAO, RECOMENDACAO, ACEITE_TRIAL]:
        dominio = COMERCIAL
        contexto = Leads/{lead_id}
    
    elif intenção in [AGENDAMENTO, CANCELAMENTO, CONFIRMACAO]:
        if not tenant_id_contexto:
            tenant_id_contexto = inferir_de_mensagem(texto, vínculos)
        if len(vínculos) == 0:
            dominio = COMERCIAL (novo lead)
        else:
            dominio = OPERACIONAL
            contexto = Clientes/{tenant_id_contexto}
    
    elif intenção in [UPGRADE, DOWNGRADE, PAGAMENTO]:
        dominio = BILLING
        contexto = Subscricoes/{subscription_id}
    
    elif intenção in [ERRO, FALHA, PROBLEMA]:
        dominio = SUPORTE
        contexto = Tickets/{ticket_id}
    
    else:
        dominio = DESAMBIGUACAO_NECESSARIA
        solicitar clarificação ao usuário
    
    # Passo 5: Validar contexto multi-tenant
    if dominio != COMERCIAL and len(vínculos) > 1:
        if not tenant_id_contexto:
            solicitar qual tenant o usuário está referenciando
    
    processar_com(dominio, contexto)
```

**Garantia:** Uma mensagem é roteada para um único domínio decisório. Ambiguidade = solicita clarificação.

### 5.3 Sessão Isolada por Domínio

| Domínio | Estado | Contexto | Ações |
|---------|--------|---------|-------|
| **COMERCIAL** | `estado_comercial` (qualificando, avaliando, aceite_pendente) | `Leads/{lead_id}` | Sem alteração em Tenants/ ou Agendamentos/ |
| **ONBOARDING** | `estado_onboarding` (dados_pessoais, profissionais, serviços) | `Tenants/{tenant_id}` | Sem alteração em domínio comercial |
| **OPERACIONAL** | `estado_operacional` (agenda, confirmação, cancelamento) | `Clientes/{tenant_id}/{cliente_id}` | Agendamentos, cancelamento, confirmação |
| **BILLING** | `estado_billing` (revision, awaiting_payment, charged) | `Subscricoes/{subscription_id}` | Sem alteração em agendamentos |
| **SUPORTE** | `estado_suporte` (aberto, em_progresso, resolvido) | `Tickets/{ticket_id}` | Registro de problema, sem execução |

**Garantia:** Objeção de preço nunca confunde ajuste de horário.

---

## 6. TRANSIÇÃO LEAD → DONO (MODELO HÍBRIDO)

### 6.1 Quando Ocorre

Lead envia aceite explícito:
- "Quero começar"
- "Vamos lá"
- "Perfeito"

Eve classifica como `intenção=ACEITE_TRIAL`.

### 6.2 Fluxo Híbrido: Núcleo Atômico + Etapas Recuperáveis

**Passo 1: Eve detecta e classifica aceite**
```
eve.classificador("Quero começar!")
  → intenção = ACEITE_TRIAL
  → Leads/{lead_id}.plano_escolhido = SOLO87
  → envia sinal: conversao_iniciada(actor_id, lead_id, plano)
```

**Passo 2: Backend executa NÚCLEO ATÔMICO (Firestore Transaction)**
```
idempotency_key = actor_id + "_" + lead_id + "_conversao_v1"

transaction.begin()
  
  // Validação prévia
  plano = Catalogo/{plano}
  if not exists: transaction.abort()
  
  // Verificar idempotência
  conversao_existente = buscar Conversoes por idempotency_key
  if conversao_existente && estado_conversao==CONCLUIDA:
      return conversao_existente (sem novo tenant)
  
  // Criar núcleo atomicamente
  conversion_id = uuid.new()
  tenant_id = "tenant_" + random_id()
  vinculo_id = uuid.new()
  
  Conversoes/{conversion_id} = {
    idempotency_key,
    estado_conversao: "NUCLEO_CRIADO",
    actor_id, lead_id, plano,
    tenant_id,
    criado_em: now()
  }
  
  Tenants/{tenant_id} = {
    dono_id: actor_id,
    nome_temporario: negocio_candidato,
    plano,
    status: "ATIVO",
    criado_em: now(),
    trial: {estado: "ACEITO", aceito_em: now()}
  }
  
  VinculosTenant/{vinculo_id} = {
    actor_id,
    tenant_id,
    papel_no_tenant: "DONO",
    criado_em: now()
  }
  
  Leads/{lead_id} = {
    ...lead_anterior,
    status_comercial: "CONVERTIDO",
    tenant_id_resultante: tenant_id,
    resultado_comercial: "SUCESSO",
    atualizado_em: now()
  }

transaction.commit() // Ou falha e rollback completo
```

**Garantia:** Ou TUDO é criado, ou NADA. Nenhum estado parcial.

**Passo 3: Etapas Recuperáveis (Posterior)**
```
if conversao.estado_conversao == NUCLEO_CRIADO:
  
  // Ativar domínio de onboarding
  dominio_ativo = ONBOARDING
  estado_onboarding = DADOS_PESSOAIS_PENDENTES
  Conversoes/{conversion_id}.etapa = ONBOARDING_INICIALIZADO
  
  // Enviar mensagem de sucesso (pode falhar sem problema)
  Eve: "Ótimo! Bem-vindo ao seu trial 🎉
        Vamos começar configurando o básico:
        1. Qual é o nome do seu salão?"
  
  if mensagem_enviada:
    Conversoes/{conversion_id}.estado_conversao = "CONCLUIDA"
  else:
    Conversoes/{conversion_id}.estado_conversao = "FALHA_RECUPERAVEL"
    retry_agendado = true
```

### 6.3 Falhas e Recuperação

| Falha | Onde | Recuperação |
|-------|------|------------|
| Plano inválido | Passo 2, validação | Transação falha inteira, retry com plano válido |
| Tenant não criado | Passo 2, transaction | Rollback automático, retry cria novamente (idem key) |
| Vínculo falha | Passo 2, transaction | Rollback automático |
| Mensagem não envia | Passo 3, etapa recuperável | Retry agendado, não afeta conversão |

**Garantia:** Nunca há ator vinculado a tenant parcialmente criado.

---

## 7. POLÍTICA DE COMUNICAÇÃO COMERCIAL

### 7.1 Inbound vs. Outbound

**INBOUND:**
- Lead iniciou a conversa
- Responder com fatos e educação
- Sem limite de mensagens
- Sem timeout de resposta

**OUTBOUND:**
- NeoEve ou sistema iniciou nova mensagem
- Requer autorização explícita
- Deve respeitar limites de WhatsApp
- Deve ter opt-out claro

### 7.2 Regras de Outbound (Rascunho — Será Detalhado no Catálogo Comercial)

```
Máximo 1 tentativa de retorno por dia
Intervalo mínimo: 24 horas entre mensagens
Máximo 3 tentativas antes de marcar como ABANDONADO
Consentimento: opt-in explícito ou usuário iniciou
Encerramento: respeitar "não" ou "parar"
Registro: cada tentativa de outbound registrada em Leads/{lead_id}
```

---

## 8. DEFINIÇÃO DE TRIAL — SEPARAÇÃO DE ESTADOS

**TRIAL_ACEITO:**
O lead aceitou comercialmente iniciar o teste.

**TRIAL_PREPARADO:**
Tenant e estrutura mínima foram criados, mas o produto pode não estar utilizável.

**TRIAL_INICIADO:**
O relógio do trial começa apenas quando a configuração operacional mínima estiver concluída.

**Configuração Mínima Sugerida:**
- Tenant válido
- Responsável vinculado (vínculo DONO)
- Ao menos um profissional configurado
- Ao menos um serviço configurado
- Agenda mínima configurada
- Canal operacional validado (WhatsApp confirmado)
- Onboarding alcançou marco mínimo utilizável

**Nota:** A regra final de início será responsabilidade do futuro Contrato de Trial.

---

## 9. ORIGEM E MÉTRICAS DO FUNIL

Eventos conceituais mínimos:

```
landing_view
whatsapp_cta_clicked
commercial_message_received
commercial_chat_started
price_presented
plan_recommended
trial_accepted
conversion_started
tenant_created
onboarding_started
onboarding_completed
trial_started
checkout_created
payment_approved
subscription_active
```

Identificadores de correlação:

```
source_token
campaign_id
actor_id
lead_id
conversion_id
tenant_id
```

**Clarificações Importantes:**
- Clique no WhatsApp não equivale a conversa iniciada
- Abertura do aplicativo pode não ser diretamente mensurável
- Primeira mensagem recebida é o marco confiável de início
- Pagamento aprovado é diferente de trial aceito
- Onboarding concluído é diferente de tenant criado

---

## 10. GARANTIAS FINAIS OBRIGATÓRIAS

✅ **Identidade:** Um ator possui identidade global e pode ter múltiplos vínculos contextuais

✅ **Isolamento:** Cada mensagem é processada por um único domínio responsável

✅ **Multi-tenant:** Nenhuma resolução de papel ocorre sem considerar tenant e contexto

✅ **Persistência:** A jornada comercial permanece histórica após conversão

✅ **Idempotência:** A mesma conversão não cria duplicidade

✅ **Recuperação:** Falhas intermediárias podem ser retomadas com segurança

✅ **Trial:** Aceite comercial não inicia automaticamente o relógio do trial

✅ **Fonte de Verdade:** Preços, planos, limites, objeções e políticas virão do Catálogo Comercial

✅ **IA:** GPT interpreta linguagem, mas não executa decisões de negócio

✅ **Auditoria:** Toda transição importante registra origem, timestamp, estado anterior e estado posterior

---

## REGISTRO DE ALTERAÇÕES — VERSÃO 1.1

### Problemas Corrigidos

1. **Princípio "um ator, um papel"** ← Corrigido para "múltiplos vínculos, contexto singular"
2. **lead_id vs actor_id** ← Separados, permitindo múltiplas jornadas por ator
3. **Conversão destrutiva** ← Alterada para aditiva (histórico preservado)
4. **Modelo de conversão** ← Híbrido (núcleo atômico + etapas recuperáveis)
5. **Idempotência** ← Defina explicitamente com chave composta
6. **Trial automático** ← Separado em ACEITO → PREPARADO → INICIADO
7. **Roteamento** ← Múltiplos domínios (COMERCIAL, ONBOARDING, OPERACIONAL, BILLING, SUPORTE)
8. **Papéis operacionais** ← Compatível com arquitetura existente (DONO, PROFISSIONAL, CLIENTE, ADMIN)
9. **Outbound** ← Seção dedicada a política de comunicação
10. **Fallback** ← Fluxo claro quando Eve não tem resposta autorizada
11. **Estados conceituais** ← Separados por domínio (não combinatórios)
12. **Retomada e interrupção** ← Explicitamente suportadas
13. **Métricas** ← Mapeamento claro de eventos e identificadores

---

**Documento Finalizado:** 2026-07-22 (V1.1)  
**Status:** Revisado — Aguardando Aprovação Arquitetural  
**Próximo Passo:** Gerar documento de revisão (REVISAO_CONTRATO_DOMINIO_COMERCIAL_V1_1.md)
