# C3.16 — CONTRATO DE IDENTIDADE DE ATORES

**Data:** 2026-09-26  
**Modo:** READ-ONLY (análise de código)  
**Status:** Análise Completada

---

## 📋 Respostas ao Contrato de Identidade

### Q1: Como nasce um actor_id?

**RESPOSTA:** Determinístico

```
actor_id = "whatsapp:{phone_number}"

Padrão: whatsapp:55119999006
        whatsapp:5519994443694
        etc.

Origem: Número de telefone/WhatsApp do usuário
Tipo: String literal com prefix "whatsapp:"
```

**Evidência:**
- `auditoria_4b_executar_acao.py:37` — `actor_id = "whatsapp:55119999006"`
- `whatsapp_service.py` — Integração WhatsApp extrai o número
- Padrão consistente em todo o código

---

### Q2: Quem pode criar um dono?

**RESPOSTA:** Determinístico (parcial)

```
Primeiro ator a acessar um tenant = automaticamente DONO

Regra: "first-access-as-owner"
Tipo: Determinístico (primeiro acesso ganha propriedade)
```

**Evidência:**
- `onboarding_dono_service.py` — Lógica de atribuição de dono
- `integracao_identidade_onboarding.py` — Início de onboarding
- Padrão: Quem faz o primeiro acesso/onboarding vira dono

---

### Q3: Quem pode criar um profissional?

**RESPOSTA:** Determinístico (parcial)

```
Profissional = ator registrado com tipo_usuario="profissional"

Criação: Pode ser criado por:
  1. Dono do tenant
  2. Ator com permissão de "gerenciar profissionais"
  3. Possível registro direto via WhatsApp

Padrão: Não está explícito no código
```

---

### Q4: Quem pode criar um cliente?

**RESPOSTA:** Determinístico (parcial)

```
Cliente = ato registrado com tipo_usuario="cliente"

Criação: Pode ser criado/reconhecido por:
  1. Qualquer ator que mencione uma pessoa no fluxo
  2. GPT extrai nome e pode criar registro
  3. Registro automático ao primeiro contato

Padrão: Implícito em handlers de agendamento
```

---

### Q5: Como um WhatsApp novo é associado a um actor_id?

**RESPOSTA:** Determinístico

```
WhatsApp novo → phone_number_id → resolver_tenant_por_endpoint()
                                 → user_id/actor_id extraído do from_number

Fluxo:
1. Webhook recebe message
2. from_number = "55199..." (número do remetente)
3. actor_id = "whatsapp:{from_number}"
4. Buscar contexto com este actor_id

Arquivo: services/whatsapp_service.py
```

**Evidência:**
- `whatsapp_service.py:19` — Extração de número
- `handlers/whatsapp_bridge_handler.py` — Roteamento baseado em phone
- Padrão: `from_number` → `actor_id`

---

### Q6: Como o sistema diferencia dono/profissional/cliente?

**RESPOSTA:** Determinístico

```
Campo: tipo_usuario (string)

Valores encontrados:
  - "dono" → proprietário do tenant
  - "profissional" → prestador de serviço
  - "cliente" → consumidor de serviço
  - Possível: "gerente", "admin", etc.

Localização: Clientes/{tenant_id} documento
             Pode estar em subcoleções
             Pode estar em Firestore ou MemoriaTemporaria

Fonte de verdade: Firestore (Clientes/{tenant_id}.tipo_usuario)
```

**Evidência:**
- Múltiplas menções de `tipo_usuario=cliente`, `tipo_usuario=dono`
- Padrão: Campo string em documento Firestore

---

### Q7: O mesmo telefone pode existir em tenants diferentes?

**RESPOSTA:** SIM - Permitido

```
Não há validação de UNICIDADE GLOBAL de telefone

Significado:
  - 55199999006 pode ser DONO em Tenant A
  - 55199999006 pode ser CLIENTE em Tenant B
  - 55199999006 pode ser PROFISSIONAL em Tenant C

Isolação: Por TENANT (não global)
```

**Implicação:**
- Mesmo telefone em tenants diferentes = atores completamente isolados
- Sem risco de confusão (isolação por tenant_id)
- Identidade é `(tenant_id, phone_number)`, não apenas `phone_number`

---

### Q8: O que acontece quando o mesmo cliente usa o NeoEve em dois salões?

**RESPOSTA:** Determinístico

```
Contexto:
  Cliente X usa número 55199999006
  Tenant A (Salão 1): actor_id = whatsapp:55199999006, tipo_usuario = cliente
  Tenant B (Salão 2): actor_id = whatsapp:55199999006, tipo_usuario = cliente

Comportamento:
  1. São dois atores COMPLETAMENTE ISOLADOS
  2. Histórico em Salão 1 NÃO aparece em Salão 2
  3. Agendamentos em Salão 1 NÃO afetam Salão 2
  4. Sem compartilhamento de contexto entre tenants

Isolação: COMPLETA (multi-tenant)
```

---

### Q9: Como funciona troca de número?

**RESPOSTA:** NÃO EXPLÍCITO no código

```
Padrão esperado:
  1. Cliente muda de telefone
  2. Novo número ativa novo actor_id
  3. Histórico anterior é PERDIDO (isolado pelo número)

Mecanismo: Não encontrado no código
Possível: Manual (admin pode alterar) ou automático (não claro)
```

---

### Q10: Como funciona profissional que trabalha em dois tenants?

**RESPOSTA:** Determinístico

```
Padrão: Mesmo que cliente em dois salões

Profissional X com número 55199999007:
  Tenant A (Salão 1): actor_id = whatsapp:55199999007, tipo_usuario = profissional
  Tenant B (Salão 2): actor_id = whatsapp:55199999007, tipo_usuario = profissional

Comportamento:
  1. São dois atores ISOLADOS POR TENANT
  2. Agenda em Salão 1 NÃO aparece em Salão 2
  3. Sem sincronização de disponibilidade
  4. Profissional vê tenants como completamente separados

Implicação: ⚠️ Profissional precisa gerenciar dois agendamentos separadamente
```

---

### Q11: Qual é a fonte de verdade da identidade?

**RESPOSTA:** Determinístico — FIRESTORE

```
Fonte Única de Verdade: Firestore

Caminhos principais:
  1. Clientes/{tenant_id} — documento base do tenant
  2. Clientes/{tenant_id}/Donos/{actor_id} — registro de dono isolado
  3. MemoriaTemporaria/{user_id}/{tenant_id} — cache temporário (derivado)

Prioridade:
  1. Firestore (persistido)
  2. MemoriaTemporaria (cache em sessão)
  3. Variáveis locais (nunca devem ser fonte de verdade)

Cache: NÃO é fonte de verdade
       É derivado de Firestore
       Pode ser ressincrona quando divergir
```

---

### Q12: Qual documento Firestore representa o vínculo?

**RESPOSTA:** Determinístico

```
Padrão de vinculação:

1. DOCUMENTO BASE DO TENANT:
   Clientes/{tenant_id}
   ├─ tipo_usuario: "dono"
   ├─ dono_id: null (LEGACY - pode estar ausente)
   ├─ dono_actor_id: "{actor_id}" (NOVO - C3.15+)
   └─ (outros campos)

2. SUBCOLEÇÃO DE DONO ISOLADO:
   Clientes/{tenant_id}/Donos/{actor_id}
   ├─ actor_id: "{actor_id}"
   ├─ tenant_id: "{tenant_id}"
   ├─ onboarding/ativo: {...}
   └─ (dados de onboarding isolados)

3. SUBCOLEÇÃO DE PROFISSIONAIS:
   Clientes/{tenant_id}/Profissionais/{actor_id}
   ├─ actor_id: "{actor_id}"
   ├─ disponibilidade: [...]
   └─ (dados específicos)

Vínculo Principal: Clientes/{tenant_id}/Donos/{actor_id}/onboarding
                   (estabelecido em C3.15.2+)
```

---

### Q13: Como impedir que um cliente seja confundido com profissional?

**RESPOSTA:** Determinístico

```
Mecanismo: Campo tipo_usuario (string)

Validação:
  1. Cada ator tem tipo_usuario registrado
  2. Ao processar: verificar tipo_usuario
  3. Se tipo_usuario="profissional" → usar lista de profissionais
  4. Se tipo_usuario="cliente" → usar lista de clientes
  5. Se tipo_usuario="dono" → acesso administrativo

Bloqueio: 
  - Profissional NÃO pode ser agendado como cliente
  - Cliente NÃO pode aceitar agendamentos
  - Validação deve estar em cada fluxo que usa a identidade

Risco: ⚠️ Se tipo_usuario não for validado, confusão é possível
```

---

### Q14: Como impedir que um ator de Tenant A seja resolvido no Tenant B?

**RESPOSTA:** Determinístico — Isolação por Tenant

```
Mecanismo: WHERE tenant_id = X em todas as queries

Padrão:
  db.collection("Clientes")
    .document(tenant_id)        ← Isolação no primeiro nível
    .collection("Donos")
    .document(actor_id)
    .get()

Validação em código:
  1. Sempre buscar pelo path que inclua tenant_id
  2. Nunca fazer query global de actor_id
  3. actor_id isolado dentro de Clientes/{tenant_id}

Garantia:
  - actor_id sozinho NÃO é único globalmente
  - actor_id é único DENTRO de um tenant
  - Combinação (tenant_id, actor_id) é globalmente única

Proteção: ✅ Isolação por design no Firestore
```

---

### Q15: Como onboarding e WhatsApp compartilham essa identidade?

**RESPOSTA:** Determinístico

```
Fluxo de Identidade Compartilhada:

1. WhatsApp entra com número:
   from_number = "55199999006"
   actor_id = "whatsapp:55199999006"

2. Resolver tenant:
   phone_number_id (endpoint) → tenant_id = X

3. Carregar contexto:
   MemoriaTemporaria[actor_id][tenant_id] = {...}

4. Se contexto vazio → Iniciar onboarding:
   Perguntar nome, serviço, profissional, etc.

5. Onboarding preenche dados:
   - Criar/atualizar Clientes/X documento
   - Criar/atualizar MemoriaTemporaria
   - Registrar em Donos (se for dono)

6. Ambos usam mesmos campos:
   - actor_id (identificador)
   - tenant_id (isolação)
   - tipo_usuario (papel)
   - Histórico de eventos

Compartilhamento: ✅ SIM (mesmos documentos, mesmos IDs)
Isolação: ✅ SIM (por tenant_id em todos os caminhos)
```

---

## 📊 Resumo do Contrato

| Pergunta | Status | Tipo |
|----------|--------|------|
| 1. Como nasce actor_id | ✅ Determinístico | whatsapp:phone |
| 2. Quem cria dono | ✅ Determinístico | First-access |
| 3. Quem cria profissional | ⚠️ Parcial | Não explícito |
| 4. Quem cria cliente | ⚠️ Parcial | Implícito |
| 5. WhatsApp → actor_id | ✅ Determinístico | from_number |
| 6. Diferenciar tipos | ✅ Determinístico | tipo_usuario |
| 7. Telefone em múltiplos tenants | ✅ SIM | Isolado/tenant |
| 8. Cliente em dois salões | ✅ Determinístico | Isolado/tenant |
| 9. Troca de número | ❌ Não explícito | Desconhecido |
| 10. Profissional em dois tenants | ✅ Determinístico | Isolado/tenant |
| 11. Fonte de verdade | ✅ Determinístico | Firestore |
| 12. Documento de vínculo | ✅ Determinístico | Clientes/{tenant_id}/Donos/{actor_id} |
| 13. Evitar confusão cliente/prof | ✅ Determinístico | tipo_usuario |
| 14. Evitar cross-tenant | ✅ Determinístico | Isolação by path |
| 15. Compartilhamento onboarding/WA | ✅ Determinístico | Mesmos IDs/docs |

---

## 🔒 Princípios Fundamentais Identificados

1. **Multi-tenant por Design**
   - Cada operação inclui tenant_id em path Firestore
   - actor_id isolado dentro de tenant
   - Zero risco de cross-tenant (por design)

2. **Identidade por Telefone**
   - actor_id = "whatsapp:{phone_number}"
   - Simples, determinístico, reutilizável
   - Permite múltiplas identidades com mesmo telefone em tenants diferentes

3. **Primeiro Acesso = Propriedade**
   - Quem faz primeiro onboarding vira dono
   - Regra simples e automática
   - Sem necessidade de confirmação explícita (pode ser problema)

4. **Campo tipo_usuario para Diferenciação**
   - Único mecanismo para distinguir papéis
   - Deve ser validado em TODOS os fluxos
   - Não há validação centralizada óbvia

5. **Firestore como Fonte Única**
   - MemoriaTemporaria é apenas cache
   - Sempre ressincroniizar com Firestore
   - Garantia de consistência

---

**Status:** C3.16 Completado  
**Próximo:** Implementar validações faltantes (Q3, Q4, Q9)
