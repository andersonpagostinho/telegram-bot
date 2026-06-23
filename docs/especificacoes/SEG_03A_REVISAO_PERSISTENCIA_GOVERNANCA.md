# SEG-03A — REVISÃO DE PERSISTÊNCIA DA GOVERNANÇA CONVERSACIONAL

**Status:** Análise Arquitetural (Sem Implementação)  
**Data:** 2026-06-23  
**Contexto:** SEG-03 propôs persistência em Sessões, mas precisa revisar  
**Risco Identificado:** Violação de princípio arquitetural (Sessão ≠ dados do negócio)

---

## 1. PRINCÍPIO ARQUITETURAL A PROTEGER

### Regra de Camadas de Persistência

```
Sessões/{actor_id}
├─ Uso: Estado transitório do fluxo conversacional
├─ Exemplos: estado_fluxo, draft, ultima_acao
├─ Característica: TTL, limpa entre turnos
└─ Regra: NÃO guardar dados permanentes

Atores/{actor_id}
├─ Uso: Identidade e papel do ator
├─ Exemplos: tipo_usuario, canal, tenant_id
├─ Característica: Permanente, multi-tenant
└─ Regra: Identidade do ator

Clientes/{tenant_id}
├─ Uso: Dados do negócio
├─ Exemplos: nome, contatos, configurações
└─ Regra: Dados operacionais permanentes

Governanca/{actor_id}
├─ Uso: Políticas de automação por ator
├─ Exemplos: responder_automaticamente, modo_dono
├─ Característica: Permanente, auditável
└─ Regra: Preferir este local para governança

AuditoriaGovernanca/{evento_id}
├─ Uso: Histórico imutável
├─ Exemplos: comando /pausar em 2026-06-23T12:00Z
├─ Característica: Append-only, timestamp
└─ Regra: Histórico de mudanças
```

---

## 2. ANÁLISE CAMPO A CAMPO

### Campo: `responder_automaticamente`

| Aspecto | Análise |
|---------|---------|
| **Natureza** | Permanente (policy do contato) |
| **Transitório?** | ❌ Não — persiste entre mensagens |
| **Path: Sessões** | ❌ Violação (dados permanentes em transiente) |
| **Path: Atores** | ⚠️ Possível (identidade relativa) |
| **Path: Governanca** | ✅ Recomendado |
| **Motivo** | É uma política de automação, não contexto de conversa |
| **Risco se em Sessão** | Sessão é recarregada/limpa, campo perdido |
| **Recomendação** | `Clientes/{tenant}/Governanca/{actor}` |

---

### Campo: `modo_dono`

| Aspecto | Análise |
|---------|---------|
| **Natureza** | Permanente (escolha do dono) |
| **Transitório?** | ❌ Não — persiste entre mensagens |
| **Path: Sessões** | ❌ Violação (dono configura modo, não transitório) |
| **Path: Atores** | ⚠️ Possível (atributo do dono) |
| **Path: Governanca** | ✅ Recomendado |
| **Motivo** | Preferência persistida do dono sobre automação |
| **Risco se em Sessão** | Reload perde modo, dono volta a fluxo normal |
| **Recomendação** | `Clientes/{tenant}/Governanca/{actor}` |

---

### Campo: `tipo_usuario`

| Aspecto | Análise |
|---------|---------|
| **Natureza** | Permanente (identidade) |
| **Transitório?** | ❌ Não — é identidade do ator |
| **Path: Sessões** | ❌ Violação (identidade não é transitória) |
| **Path: Atores** | ✅ Recomendado (JÁ EXISTE) |
| **Path: Clientes** | ✅ Alternativa (se cliente específico) |
| **Motivo** | `tipo_usuario` já está em Atores/{actor_id} |
| **Risco se em Sessão** | Duplicação, inconsistência, confusão |
| **Recomendação** | `Clientes/{tenant}/Atores/{actor}` (manter lá) |

---

### Campo: `identificado`

| Aspecto | Análise |
|---------|---------|
| **Natureza** | Permanente (ator foi identificado?) |
| **Transitório?** | ❌ Não — uma vez identificado, permanece |
| **Path: Sessões** | ⚠️ Problemático (perdido em reload) |
| **Path: Atores** | ✅ Recomendado (estado do ator) |
| **Path: Clientes** | ✅ Alternativa (se documento de cliente) |
| **Motivo** | Estado de identidade do ator (documento ou não) |
| **Risco se em Sessão** | Ator não identificado volta a "novo" após reload |
| **Recomendação** | `Clientes/{tenant}/Atores/{actor}` |

---

### Campo: `origem_contato`

| Aspecto | Análise |
|---------|---------|
| **Natureza** | Permanente (metadado do ator) |
| **Transitório?** | ❌ Não — origem não muda |
| **Path: Sessões** | ❌ Violação (metadado permanente) |
| **Path: Atores** | ✅ Recomendado (atributo do ator) |
| **Motivo** | Como o ator chegou (referência, site, campanaha) |
| **Risco se em Sessão** | Perdido em reload |
| **Recomendação** | `Clientes/{tenant}/Atores/{actor}` |

---

### Campo: `motivo_bloqueio`

| Aspecto | Análise |
|---------|---------|
| **Natureza** | Transitório (contexto da decisão atual) |
| **Transitório?** | ✅ Sim — por que foi bloqueado AGORA |
| **Path: Sessões** | ✅ OK (contexto de conversa) |
| **Path: Governanca** | ⚠️ Não (é contexto, não policy) |
| **Path: Auditoria** | ✅ Também OK (para log) |
| **Motivo** | Contexto de uma decisão específica |
| **Risco se em Sessão** | Nenhum (é transitório) |
| **Recomendação** | `Clientes/{tenant}/Sessoes/{actor}` (contexto) |

---

### Campo: `_decisoes_log`

| Aspecto | Análise |
|---------|---------|
| **Natureza** | Permanente + Histórico |
| **Transitório?** | ❌ Não — é histórico |
| **Path: Sessões** | ❌ Violação (histórico não é transitório) |
| **Path: Governanca** | ⚠️ Array crescente (anti-pattern) |
| **Path: Auditoria** | ✅ Recomendado (histórico imutável) |
| **Motivo** | Auditoria de todas as decisões |
| **Risco se em Sessão** | Histórico perdido em limpeza, sem rastreamento |
| **Recomendação** | `Clientes/{tenant}/AuditoriaGovernanca/{evento_id}` |

---

### Campo: `histórico de overrides`

| Aspecto | Análise |
|---------|---------|
| **Natureza** | Permanente + Histórico |
| **Transitório?** | ❌ Não — é auditoria |
| **Path: Sessões** | ❌ Violação (histórico em transitório) |
| **Path: Governanca** | ⚠️ Crescerá indefinidamente |
| **Path: Auditoria** | ✅ Recomendado (append-only) |
| **Motivo** | Quem pausou, quando, até quando |
| **Risco se em Sessão** | Sem rastreamento de mudanças |
| **Recomendação** | `Clientes/{tenant}/AuditoriaGovernanca/{evento_id}` |

---

## 3. TABELA DE RECOMENDAÇÕES

| Campo | Natureza | Path Recomendado | Motivo | Risco se Sessão |
|-------|----------|------------------|--------|-----------------|
| `responder_automaticamente` | Permanente | Governanca/{actor} | Policy de automação | Perdido em reload |
| `modo_dono` | Permanente | Governanca/{actor} | Preferência do dono | Volta a modo normal |
| `tipo_usuario` | Permanente | Atores/{actor} | Já existe lá | Duplicação/inconsistência |
| `identificado` | Permanente | Atores/{actor} | Estado do ator | Volta a "novo" |
| `origem_contato` | Permanente | Atores/{actor} | Metadado do ator | Perdido |
| `motivo_bloqueio` | Transitório | Sessoes/{actor} | Contexto atual | Nenhum (OK em sessão) |
| `_decisoes_log` | Histórico | AuditoriaGovernanca/{id} | Auditoria imutável | Sem rastreamento |
| `histórico_overrides` | Histórico | AuditoriaGovernanca/{id} | Append-only | Sem auditoria |

---

## 4. ESTRUTURA DE PERSISTÊNCIA RECOMENDADA

### 4.1 Clientes/{tenant_id}/Atores/{actor_id}

```json
{
  "actor_id": "whatsapp:5511999005",
  "tipo_usuario": "cliente|profissional|dono",
  "canal": "whatsapp",
  "identificado": true,
  "origem_contato": "site|referencia|campanha",
  "_tenant_id_guard": "{tenant_id}",
  "_created_at": "2026-06-20T10:00:00Z",
  "_schema_version": 2
}
```

**Responsabilidade:** Identidade e papel

---

### 4.2 Clientes/{tenant_id}/Governanca/{actor_id}

```json
{
  "actor_id": "whatsapp:5511999005",
  "responder_automaticamente": true,
  "bloqueado_ate": "2026-06-24T15:30:00Z" | null,
  "modo_dono": "normal|admin|silencioso",
  "modo_profissional": "silencioso|operacional",
  "_ultima_alteracao": "2026-06-23T12:00:00Z",
  "_alterado_por": "dono",
  "_motivo": "comando /pausar",
  "_schema_version": 1
}
```

**Responsabilidade:** Políticas de automação persistidas

---

### 4.3 Clientes/{tenant_id}/Sessoes/{actor_id}

```json
{
  "actor_id": "whatsapp:5511999005",
  "estado_fluxo": "agendando|consultando|etc",
  "draft_agendamento": {...},
  "ultima_acao": "perguntar_profissional",
  "motivo_bloqueio": "responder_automaticamente=false",
  "_tenant_id_guard": "{tenant_id}",
  "_updated_at": "2026-06-23T12:05:00Z",
  "_ttl": 3600
}
```

**Responsabilidade:** Estado transitório da conversa

---

### 4.4 Clientes/{tenant_id}/AuditoriaGovernanca/{evento_id}

```json
{
  "evento_id": "audit_20260623_120000_whatsapp5511999005",
  "timestamp": "2026-06-23T12:00:00Z",
  "actor_id": "whatsapp:5511999005",
  "tipo_evento": "comando|decisao_governanca",
  "comando": "/pausar",
  "campo_alterado": "responder_automaticamente",
  "valor_anterior": true,
  "valor_novo": false,
  "bloqueado_ate": "2026-06-24T12:00:00Z",
  "motivo": "usuario pausado em sessao ativa",
  "executado_por": "dono|sistema",
  "_tenant_id_guard": "{tenant_id}",
  "_schema_version": 1
}
```

**Responsabilidade:** Auditoria imutável (append-only)

---

## 5. REGRAS DE DECISÃO APLICADAS

### Regra 1: Sessão só para Transitório

✅ **Permitido em Sessões:**
- `estado_fluxo` (onde estamos no fluxo)
- `draft_agendamento` (dados em edição)
- `motivo_bloqueio` (por que bloqueado agora)
- TTL curto (segundos/minutos)

❌ **Proibido em Sessões:**
- `responder_automaticamente` (policy permanente)
- `modo_dono` (preferência persistida)
- `_decisoes_log` (histórico)
- Dados sem TTL

---

### Regra 2: Atores para Identidade

✅ **Deve estar em Atores:**
- `tipo_usuario` (quem é)
- `identificado` (foi conhecido?)
- `origem_contato` (como veio)
- Vinculação com tenant

❌ **Não pertence a Atores:**
- `responder_automaticamente` (é policy, não identidade)
- `modo_dono` (é preference, não identity)

---

### Regra 3: Governança para Policies

✅ **Deve estar em Governanca:**
- `responder_automaticamente` (MEC-03)
- `modo_dono` (MEC-04)
- `modo_profissional` (MEC-05)
- Flags de automação permanentes

---

### Regra 4: Auditoria para Histórico

✅ **Deve estar em Auditoria:**
- Cada comando /pausar, /retomar, /status
- Cada alteração de policy
- Timestamp e quem fez
- Imutável (append-only)

---

## 6. IMPACTO NA SEG-03

### Mudanças Necessárias

**Seção 3 (Modelo de Dados):**
- ✅ Atores/{actor_id}: Adicionar identificado, origem_contato
- ✅ Governanca/{actor_id}: Criar nova coleção
- ✅ AuditoriaGovernanca/{id}: Criar nova coleção
- ✅ Sessoes/{actor_id}: Manter apenas transitório

**Seção 4 (Ordem de Decisão):**
- ✅ Consultar Atores para tipo_usuario
- ✅ Consultar Governanca para responder_automaticamente
- ✅ Manter transitório em Sessoes
- ✅ LOG vai para AuditoriaGovernanca

**Seção 8 (Critérios de Aceite):**
- ✅ CA-1 a CA-7 permanecem válidos
- ✅ Adicionar: "Governanca persiste entre reloads"
- ✅ Adicionar: "Auditoria é imutável"

---

## 7. COMPARAÇÃO DE OPÇÕES DE PERSISTÊNCIA

### Opção A: Tudo em Sessões (Proposta Original)

| Aspecto | Avaliação |
|---------|-----------|
| Implementação | ✅ Rápida (um lugar) |
| Multiplicidade | ❌ Viola arquitetura |
| Persistência | ❌ Dados permanentes em transitório |
| Auditoria | ❌ Histórico perdido |
| Multi-tenant | ✅ OK (via tenant_id) |
| **Score** | **2/5** |

---

### Opção B: Distribuído (Recomendado)

| Aspecto | Avaliação |
|---------|-----------|
| Implementação | ⚠️ Mais pontos, mas natural |
| Multiplicidade | ✅ Respeta camadas |
| Persistência | ✅ Dados no local certo |
| Auditoria | ✅ Histórico imutável |
| Multi-tenant | ✅ OK (via tenant_id guard) |
| **Score** | **4.5/5** |

---

## 8. IMPACTO EM CONSULTAS

### Bloco de Governança (linha 3360 router)

```python
# OPÇÃO A (Original — anti-pattern)
ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id)
if ctx.get("responder_automaticamente") == False:
    return bloqueado  # ❌ Recarrega session cada vez

# OPÇÃO B (Recomendado)
ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id)
ator = await buscar_ator(actor_id, tenant_id=dono_id)
governanca = await buscar_governanca(actor_id, tenant_id=dono_id)

if governanca.get("responder_automaticamente") == False:
    return bloqueado  # ✅ Consulta persistência real

if ator.get("tipo_usuario") == "profissional":
    return bloqueado  # ✅ Identidade em Atores

if governanca.get("modo_dono") == "silencioso":
    return bloqueado  # ✅ Preferência em Governanca
```

**Impacto:** +2 consultas Firestore (negligenciável, mas necessárias)

---

## 9. RECOMENDAÇÃO FINAL

### Adotar Opção B (Distribuído)

**Justificativa:**
- ✅ Respeita arquitetura em camadas
- ✅ Dados permanentes não em transitório
- ✅ Auditoria imutável e rastreável
- ✅ Facilita futuras extensões
- ✅ Minimiza risco de perda de dados

**Alterações em SEG-03:**
- Mover `responder_automaticamente` → Governanca
- Mover `modo_dono` → Governanca
- Mover `tipo_usuario` → Atores (já está)
- Mover `identificado` → Atores
- Mover `origem_contato` → Atores
- Manter `motivo_bloqueio` → Sessoes (transitório)
- Mover `_decisoes_log` → AuditoriaGovernanca
- Mover `histórico_overrides` → AuditoriaGovernanca

---

## 10. CONCLUSÃO

**Risco Identificado:** ✅ Confirmado  
**Solução:** ✅ Distribuição em 4 coleções  
**Arquitetura:** ✅ Respeitada  
**Auditoria:** ✅ Garantida  
**Regressão:** ✅ Improvável (mudança estrutural, não lógica)  

---

**Revisão:** SEG-03A  
**Status:** ✅ Completa  
**Próximo:** Aplicar errata em SEG-03

---
