# C3.16-R1 — REVISÃO E CONTRATO FINAL DE IDENTIDADE DE ATORES

**Data:** 2026-09-26  
**Modo:** READ-ONLY (análise arquitetural)  
**Status:** Análise Profunda

---

## 🔍 PROBLEMA 1: PRIMEIRO ACESSO ≠ AUTOMATICAMENTE DONO

### Situação Atual

**ENCONTRADO EM CÓDIGO:**
- `onboarding_dono_service.py` — Lógica de atribuição automática ao primeiro acesso
- `integracao_identidade_onboarding.py` — Fluxo de onboarding sem validação de autorização

**PROBLEMAS IDENTIFICADOS:**

#### A) Tenant inexistente
```
Situação: Novo tenant + primeiro ator
Comportamento atual: ⚠️ Primeiro ator = automaticamente DONO
Status: FALHA DE SEGURANÇA
Razão: Sem autorização, qualquer pessoa pode virar dono
```

#### B) Tenant existente
```
Situação: Tenant já existe + novo ator acessa
Comportamento atual: ⚠️ Actor novo NÃO deve virar dono (parcialmente correto)
Status: PARCIAL (mas sem validação explícita)
Problema: Sem checkpoint claro que rejeita o acesso se não autorizado
```

#### C) Cliente desconhecido
```
Situação: Novo cliente entra por WhatsApp
Comportamento atual: ? Implícito em handlers
Status: NÃO CLARO
Problema: Sem critério de identificação/cadastro
```

#### D) Profissional desconhecido
```
Situação: Novo profissional tenta se registrar
Comportamento atual: ⚠️ NÃO ENCONTRADO no código
Status: LACUNA CRÍTICA
Problema: Sem fluxo de autorização de profissional
```

### Decisão Arquitetural (NOVA)

```
REGRA 1.A: TENANT NOVO + PRIMEIRO ATOR
├─ Requer AUTORIZAÇÃO EXPLÍCITA antes
├─ Não pode ser "qualquer pessoa"
├─ Opção A: Email de confirmação com código
├─ Opção B: Código administrativo pré-compartilhado
├─ Opção C: Apenas email/WhatsApp whitelisted
└─ Status: REQUER IMPLEMENTAÇÃO

REGRA 1.B: TENANT EXISTENTE + NOVO ATOR
├─ Automaticamente torna-se CLIENTE (tipo_usuario="cliente")
├─ Não altera papéis existentes
├─ Validar: tenant_id ≠ None
└─ Status: PARCIALMENTE EXISTENTE (precisa validação explícita)

REGRA 1.C: CLIENTE DESCONHECIDO
├─ Cadastro automático ao primeiro contato
├─ Informação mínima: phone_number + tenant_id
├─ tipo_usuario = "cliente"
├─ Pode solicitar nome/contexto depois
└─ Status: IMPLÍCITO (requer formalização)

REGRA 1.D: PROFISSIONAL DESCONHECIDO
├─ NÃO pode auto-registrar
├─ Requer aprovação do DONO
├─ Fluxo: DONO registra profissional via menu/API
├─ tipo_usuario = "profissional"
└─ Status: LACUNA CRÍTICA - NÃO IMPLEMENTADO
```

---

## 🔀 PROBLEMA 2: SEPARAR IDENTIDADES

### Identidades Encontradas no Código

```
1. tenant_id (7394370553)
   └─ Isolação: Global (cada tenant é completamente isolado)
   └─ Natureza: String numérica ou UUID
   └─ Origem: Criado na primeira vez que um dono inicia

2. actor_id ("whatsapp:55199999006")
   └─ Isolação: Dentro de tenant (mesmo phone em tenants diferentes = atores diferentes)
   └─ Natureza: String com prefix "whatsapp:"
   └─ Origem: Derivado de phone_number

3. wa_id / from_number ("55199999006")
   └─ Isolação: Global (não isolado por tenant)
   └─ Natureza: String numérica (número de telefone)
   └─ Origem: Webhook WhatsApp (campo "from")

4. phone_number_id (endpoint WhatsApp do negócio)
   └─ Isolação: Aponta para um tenant
   └─ Natureza: String ID da API WhatsApp
   └─ Origem: Configuração do negócio
   └─ Resolução: phone_number_id → tenant_id (lookup)

5. tipo_usuario ("dono", "cliente", "profissional")
   └─ Isolação: Dentro de tenant
   └─ Natureza: String enum
   └─ Origem: Campo em Firestore documento

6. telefone (número bruto sem prefix)
   └─ Isolação: Global
   └─ Natureza: String numérica
   └─ Origem: Parsed de WhatsApp from_number
```

### Mapeamento de Relações

```
Fluxo WhatsApp Inbound:
┌─────────────────────────────────────────┐
│ Webhook: message_received               │
├─────────────────────────────────────────┤
│ from_number: "55199999006"              │ ← wa_id
│ phone_number_id: "12345..." (endpoint)  │ ← endpoint ID
│ message: "Quero agendar"                │
└─────────────────────────────────────────┘
  │
  ├─ Extrair: telefone = "55199999006"
  │
  ├─ Resolver: phone_number_id → tenant_id = "7394370553"
  │
  ├─ Montar: actor_id = f"whatsapp:{telefone}" = "whatsapp:55199999006"
  │
  └─ Buscar contexto: MemoriaTemporaria[actor_id][tenant_id]

Relações:
  phone_number_id ────────→ tenant_id (lookup 1:1)
  (telefone, tenant_id) ──→ actor_id (derivado, unique per tenant)
  actor_id ───────────────→ tipo_usuario (campo no Firestore)
```

### Decisão Arquitetural (VALIDADA)

```
✅ SEPARAÇÃO CONFIRMADA

- tenant_id: Global, isolador principal
- wa_id: Global, por telefone
- actor_id: (tenant_id, wa_id) combinado, único por tenant
- phone_number_id: Endpoint WhatsApp → tenant_id mapper
- tipo_usuario: Papel dentro do tenant
- telefone: Componente de wa_id

INVARIANTES:
- actor_id NÃO é igual a wa_id (tem prefix "whatsapp:")
- actor_id NÃO é único globalmente (mesmo em tenants diferentes)
- (tenant_id, actor_id) É ÚNICO GLOBALMENTE
- phone_number_id é único globalmente (one endpoint per business)
```

---

## 🆔 PROBLEMA 3: DEFINIR O ACTOR_ID CANÔNICO

### Análise Atual

```
Padrão: actor_id = f"whatsapp:{phone_number}"

Exemplo: actor_id = "whatsapp:55199999006"
```

### Propriedades a Validar

```
1. Como nasce?
   ✅ Determinístico: Derivado de from_number do WhatsApp
   ✅ Reproduzível: Mesmo phone sempre gera mesmo actor_id

2. É determinístico?
   ✅ SIM: f"whatsapp:{phone}" é uma função pura

3. É imutável?
   ⚠️ NÃO COMPLETAMENTE: Se troca de telefone, novo actor_id é criado
   └─ Problema: Histórico se perde

4. Pode sobreviver à troca de telefone?
   ❌ NÃO: Novo telefone = novo actor_id (histórico perdido)
   └─ Decisão necessária

5. Pode existir em múltiplos tenants?
   ✅ SIM: Mesmo telefone em Tenant A e Tenant B = atores diferentes
   └─ (tenant_id, actor_id) uniqueness garantida

6. Um mesmo humano pode possuir atores distintos por tenant?
   ✅ SIM: Uma pessoa física pode ter papel diferente em cada tenant
   └─ Exemplo: Dono em Salão 1, Cliente em Salão 2

7. Como evitar colisão?
   ✅ RESOLVIDO: Prefix "whatsapp:" garante namespacing
   └─ Mas: Possível adicionar outros prefixes (sms:, email:, etc.)
```

### Decisão Arquitetural (NOVA)

```
REGRA 3: ACTOR_ID CANÔNICO

Formato: "{prefix}:{identificador_unico}"

Prefixes:
  - "whatsapp:{phone_number}" ← Padrão atual
  - "sms:{phone_number}" ← Futuro (SMS)
  - "email:{email}" ← Futuro (Email)
  - "telegram:{user_id}" ← Futuro (Telegram)

Propriedades:
  ✅ Determinístico: função pura do identificador
  ❌ Imutável: Apenas enquanto phone não muda
  ❌ Persistência entre telefones: Requer migração explícita
  ✅ Multi-tenant: Mesmo actor_id em tenants diferentes = atores isolados
  ✅ Sem colisão: Prefix garante namespacing

Implicações:
  - Troca de telefone = novo actor_id
  - Histórico anterior é perdido (ou requer merge manual)
  - Precisa de fluxo explícito para "manter histórico ao trocar"

Status: EXISTENTE E VALIDADA (com ressalvas sobre troca de telefone)
```

---

## 📱 PROBLEMA 4: DEFINIR IDENTIDADE WHATSAPP

### Mapeamento Atual

```
phone_number_id (endpoint WhatsApp do negócio)
    ↓ (lookup in Firestore)
tenant_id (7394370553)
    ↓ (dentro do tenant)
actor_id (whatsapp:55199999006)
```

### Propriedades a Validar

```
PROPRIEDADE 1: SEM RESOLUÇÃO GLOBAL DE wa_id
  Status: ✅ CONFIRMADA
  Significado: wa_id não pode ser usado sozinho para resolver tenant
  Requerimento: phone_number_id é necessário como mapper

PROPRIEDADE 2: SEM RESOLUÇÃO GLOBAL DE actor_id
  Status: ✅ CONFIRMADA
  Significado: actor_id sozinho não pode buscar dados de outro tenant
  Garantia: Isolação por path Firestore (Clientes/{tenant_id}/...)

PROPRIEDADE 3: MESMO WA_ID EM TENANTS DIFERENTES
  Status: ✅ PERMITIDO
  Exemplo: 55199999006 é cliente em Salão A, profissional em Salão B
  Implicação: Sem risco (isolação por tenant)

PROPRIEDADE 4: WA_ID NOVO NÃO RECEBE PAPEL AUTOMATICAMENTE
  Status: ⚠️ VIOLADO NO CÓDIGO
  Problema: Novo actor acessa → automaticamente torna-se dono
  Solução: Implementar validação de autorização

PROPRIEDADE 5: VÍNCULO REQUER AUTORIZAÇÃO
  Status: ❌ NÃO IMPLEMENTADO
  Problema: Novo ator pode se vincular sem aprovação
  Requerimento: Fluxo de autorização para profissional/gerente
```

### Decisão Arquitetural (NOVA)

```
REGRA 4: IDENTIDADE WHATSAPP

Resolução:
  phone_number_id → lookup(Firestore:endpoints) → tenant_id ✅
  dentro tenant: actor_id → lookup(Firestore:Clientes/{tenant}) → tipo_usuario ✅

Isolação:
  - wa_id é global
  - actor_id é local per tenant
  - Sem resolução cross-tenant de actor_id ✅

Autorização:
  - Novo wa_id + novo tenant = requer CONFIRMAÇÃO
  - Novo wa_id + tenant existente = registra como CLIENTE (automático)
  - Promover a PROFISSIONAL = requer aprovação DONO

Status: PARCIALMENTE EXISTENTE (faltam controles de autorização)
```

---

## 👥 PROBLEMA 5: DEFINIR CRIAÇÃO DOS TRÊS PAPÉIS

### Estado Atual no Código

```
┌─ DONO
│  ├─ Quem pode criar? ⚠️ QUALQUER PESSOA (primeiro acesso)
│  ├─ Condição? ⚠️ Nenhuma (FALHA DE SEGURANÇA)
│  ├─ Impedir segundo? ❌ NÃO EXISTE VALIDAÇÃO
│  └─ Status: CRÍTICO - REQUER FIX

├─ PROFISSIONAL
│  ├─ Quem autoriza? ❌ NÃO ENCONTRADO
│  ├─ Vínculo ao tenant? ❌ SEM FLUXO
│  ├─ Multi-tenant? ⚠️ IMPLÍCITO (mesma lógica)
│  └─ Status: LACUNA CRÍTICA

└─ CLIENTE
   ├─ Como é criado? ⚠️ IMPLÍCITO (automático ao contato)
   ├─ Automático? ✅ SIM
   ├─ Informação mínima? ⚠️ APENAS TELEFONE
   ├─ Evitar confusão? ❌ SEM VALIDAÇÃO CENTRAL
   └─ Status: FUNCIONA MAS SEM VALIDAÇÃO
```

### Decisão Arquitetural (NOVA)

```
REGRA 5: CRIAÇÃO DOS TRÊS PAPÉIS

┌─ DONO
│  Criação:
│  ├─ Novo tenant + primeiro ator
│  ├─ Requer código de autorização (email ou pré-shared)
│  ├─ OU email whitelisted
│  └─ OU aprovação de admin
│  
│  Protecção:
│  ├─ Máximo 1 dono por tenant
│  ├─ Validar: não há outro dono já
│  └─ Rejeitar se segundo dono tentar registrar
│
│  Status: IMPLEMENTAR

├─ PROFISSIONAL
│  Criação:
│  ├─ Apenas através do DONO (menu/API)
│  ├─ Dono registra: "Adicionar profissional"
│  ├─ Informação: telefone + nome
│  └─ Automático: tipo_usuario = "profissional"
│  
│  Multi-tenant:
│  ├─ SIM, profissional pode atuar em múltiplos tenants
│  ├─ Cadastro separado por tenant (isolado)
│  └─ Sem sincronização de agenda entre tenants
│
│  Status: IMPLEMENTAR

└─ CLIENTE
   Criação:
   ├─ Automático ao primeiro contato por WhatsApp
   ├─ Informação mínima: phone + tenant
   ├─ Tipo: tipo_usuario = "cliente"
   └─ Pode fornecer nome depois
   
   Validação:
   ├─ Sempre validar: telefone ≠ null
   ├─ Sempre validar: tenant_id válido
   ├─ Distinguir: cliente ≠ profissional
   │  └─ Validar tipo_usuario em cada fluxo
   └─ Status: PARCIALMENTE EXISTENTE (faltam validações)
```

---

## 📞 PROBLEMA 6: DEFINIR TROCA DE NÚMERO

### Cenário: Actor trocar número WhatsApp

```
Situação:
  Antes: actor_id = "whatsapp:55199999006" com histórico em Tenant A
  Depois: mesmo ator adquire número novo "55199999999"

Opção A: NOVO ACTOR_ID (histórico perdido)
  ├─ novo actor_id = "whatsapp:55199999999"
  ├─ histórico antigo fica órfão
  ├─ vantagem: simples, determinístico
  └─ desvantagem: perde histórico

Opção B: MIGRAÇÃO EXPLÍCITA (histórico preservado)
  ├─ Dono autoriza: "Este é o novo número de [cliente/prof]"
  ├─ Operação: merge(whatsapp:55199999006 → whatsapp:55199999999)
  ├─ Vantagem: histórico preservado, rastreável
  └─ Desvantagem: requer UI/UX, complexidade
```

### Decisão Arquitetural (NOVA)

```
REGRA 6: TROCA DE NÚMERO

Decisão: OPÇÃO B (Migração Explícita) RECOMENDADA

Fluxo:
1. Cliente/Profissional: "Meu número mudou"
2. Sistema: Identifica ator antigo (whatsapp:55199999006)
3. Dono: Aprova troca em menu "Atualizar número"
4. Sistema: 
   ├─ Cria novo ator (whatsapp:55199999999)
   ├─ Migra histórico: eventos, agendamentos, etc.
   ├─ Marca ator antigo como ARCHIVED
   └─ Mapeia novo → antigo para auditoria

Status: NÃO IMPLEMENTADO (requer Migração Explícita)
```

---

## 🏷️ PROBLEMA 7: DEFINIR TIPO_USUARIO

### Estado Atual

```
Campo: tipo_usuario (string)

Valores encontrados:
  - "dono" ✅
  - "profissional" ✅
  - "cliente" ✅

Validação: ❌ NÃO ENCONTRADA (falta validação centralizada)
Transições: ❌ IMPLÍCITAS (sem regras claras)
Promover/rebaixar: ⚠️ NÃO CLARO
Exclusividade: ⚠️ NÃO DEFINIDA
Inválido: ❌ SEM TRATAMENTO
```

### Decisão Arquitetural (NOVA)

```
REGRA 7: TIPO_USUARIO CONTRATO CENTRAL

Domínio:
  tipo_usuario ∈ {
    "dono",
    "profissional",
    "cliente"
  }

Validação Central:
  ├─ Validar em CADA leitura
  ├─ Usar enum/constantes (não strings soltas)
  ├─ Rejeitar valores inválidos
  └─ Log/alerta se encontrar inválido

Transições Permitidas:
  cliente      → profissional  (aprovação dono)
  profissional → cliente       (degradação)
  cliente      → cliente       (sem mudança)
  dono         → (imutável)
  
Exclusividade:
  ❌ NÃO exclusivo: mesmo ator pode ter tipos em tenants diferentes
  └─ Exemplo: dono em A, cliente em B

Promover/Rebaixar:
  ├─ Operação: UPDATE tipo_usuario
  ├─ Autorizado por: DONO do tenant
  ├─ Validação: não rebaixar dono
  └─ Auditoria: log de mudança

Status: IMPLEMENTAR validação centralizada
```

---

## 📄 PROBLEMA 8: DEFINIR MODELO FIRESTORE

### Estrutura Proposta

```
Clientes/{tenant_id}/
├─ (base doc)
│  ├─ nome: "Salão da Maria"
│  ├─ tipo_usuario: "dono"
│  ├─ dono_actor_id: "whatsapp:55199999006"  ← NOVO (C3.15+)
│  ├─ dataAssinatura: "2026-09-25"
│  └─ (outros campos de configuração do negócio)
│
├─ Donos/{actor_id}/
│  ├─ (identity doc)
│  │  ├─ actor_id: "whatsapp:55199999006"
│  │  ├─ tenant_id: "7394370553"
│  │  ├─ tipo_usuario: "dono"
│  │  ├─ email: "proprietario@email.com"  ← Opcional
│  │  └─ (dados pessoais do dono)
│  │
│  └─ onboarding/
│     ├─ ativo
│     │  ├─ etapa: 3
│     │  └─ (progresso de onboarding)
│     └─ (histórico de onboarding)
│
├─ Profissionais/{actor_id}/
│  ├─ actor_id
│  ├─ nome
│  ├─ especialidades
│  └─ disponibilidade
│
├─ Clientes/...  ← Subcoleção de clientes
│  └─ (se necessário persistir)
│
└─ (outras subcoleções: Comercial, onboarding, eventos, etc.)

SEPARAÇÃO:
  ✅ Identidade: Clientes/{tenant}/Donos/{actor_id}
  ✅ Onboarding: Clientes/{tenant}/Donos/{actor_id}/onboarding
  ✅ Configuração: Clientes/{tenant} (base doc)
  ✅ Papéis: Clientes/{tenant}/{Profissionais,Clientes,...}
```

### Status

```
✅ EXISTENTE (em C3.15.2+)
  - Novo path isolado implementado
  - Leitura isolada funcionando
  - Escrita isolada funcionando
  
⚠️ LACUNA HISTÓRICA
  - Documento base ainda tem tipo_usuario
  - dono_actor_id é NOVO, campo legado dono_id não preenchido
  - Migração de legacy para novo precisa de backfill (C3.15.5)
```

---

## 🧪 PROBLEMA 9: CENÁRIOS DE TESTE

```
Cenários Esperados (15):

[T1] Novo tenant + primeiro dono
  └─ Requer autorização → dono criado com tipo_usuario="dono"

[T2] Tenant existente + novo cliente
  └─ Automático → cliente criado com tipo_usuario="cliente"

[T3] Tenant existente + novo profissional
  └─ Dono aprova → profissional criado com tipo_usuario="profissional"

[T4] Mesmo cliente em dois tenants
  └─ Isolado → cliente isolado por tenant_id

[T5] Mesmo profissional em dois tenants
  └─ Isolado → profissional isolado por tenant_id (sem agenda sincronizada)

[T6] Mesmo wa_id em dois tenants
  └─ Isolado → actor_id derivado do (tenant_id, wa_id)

[T7] Troca de número
  └─ Requer migração explícita do dono

[T8] Segundo usuário tentando assumir dono
  └─ Rejeitado → "Tenant já tem dono"

[T9] Actor_id desconhecido
  └─ Criar novo cliente automaticamente

[T10] wa_id desconhecido
  └─ Mesmo que T9

[T11] Endpoint desconhecido
  └─ Erro/reject (endpoint não registrado no tenant)

[T12] Endpoint conhecido + actor desconhecido
  └─ Criar novo cliente para este actor no tenant

[T13] Tentativa cross-tenant
  └─ Rejeitado (validação de tenant_id em path Firestore)

[T14] Webhook duplicado
  └─ Idempotente (processado apenas uma vez)

[T15] Retry concorrente
  └─ Sincronização por idempotência (SHA256 + verificação)
```

---

## 📋 PROBLEMA 10: RESULTADO FINAL

## ✅ CONTRATO FINAL DE IDENTIDADE

| Decisão | Status | Tipo | Notas |
|---------|--------|------|-------|
| **1A** Tenant novo + primeiro dono | LACUNA | ARQUITETURAL | Requer autorização explícita |
| **1B** Tenant existente + novo ator | PARCIAL | ARQUITETURAL | Sem validação clara |
| **1C** Cliente desconhecido | FUNCIONAL | IMPLÍCITO | Automático, não formalizado |
| **1D** Profissional desconhecido | LACUNA CRÍTICA | — | Sem fluxo de autorização |
| **2** Separar identidades | ✅ VALIDADA | EXISTENTE | tenant_id, actor_id, wa_id, etc. |
| **3** Actor_id canônico | ✅ VALIDADA | EXISTENTE | whatsapp:{phone} |
| **4** Identidade WhatsApp | PARCIAL | EXISTENTE | Faltam controles de autorização |
| **5A** Criar dono | CRÍTICA | LACUNA | Sem autorização |
| **5B** Criar profissional | LACUNA | — | Sem fluxo |
| **5C** Criar cliente | FUNCIONAL | IMPLÍCITO | Automático |
| **6** Troca de número | LACUNA | — | Requer implementação (migração) |
| **7** Tipo_usuario contrato | LACUNA | — | Sem validação centralizada |
| **8** Modelo Firestore | ✅ VALIDADA | EXISTENTE | C3.15.2+ implementado |
| **9** Cenários de teste | PARCIAL | — | T1, T3, T7, T8, T15 faltam |

---

## 🚨 CRÍTICOS PARA C3.15.5

```
ANTES de executar C3.15.5-E1 (Backfill):

❌ BLOQUEADOR 1: Validação de autorização para DONO
   └─ Novo tenant sem autorização pode virar dono (segurança)

❌ BLOQUEADOR 2: Campo tipo_usuario sem validação centralizada
   └─ Cliente pode ser confundido com profissional

❌ BLOQUEADOR 3: Fluxo de criação de PROFISSIONAL
   └─ Sem forma clara de autorizar novo profissional

⚠️ AVISO 1: Troca de número sem fluxo
   └─ Histórico será perdido se número mudar

⚠️ AVISO 2: Segundo dono pode tentar se registrar
   └─ Sem proteção explícita
```

---

## 📌 RECOMENDAÇÃO

**NÃO PROSSEGUIR COM C3.15.5-E1 (Backfill) até:**

1. ✅ Implementar validação de autorização para DONO
2. ✅ Implementar validação centralizada de tipo_usuario
3. ✅ Implementar fluxo de criação de PROFISSIONAL
4. ⚠️ Documentar comportamento de troca de número

**Sequência Recomendada:**

```
Implementação Patches:
  C3.17-P1: Validação de autorização para DONO
  C3.17-P2: Validação centralizada de tipo_usuario
  C3.17-P3: Fluxo de criação de PROFISSIONAL
  C3.17-P4: Fluxo de troca de número (se crítico)
    ↓
Testes E2E dos 15 cenários
    ↓
C3.15.5-E1: Backfill seguro
```

---

**Status:** C3.16-R1 CONCLUÍDO  
**Próximo:** C3.17 (Patches de Segurança) OU C3.15.5-E1 (com riscos aceitos)

**WRITES EXECUTADAS: 0**
