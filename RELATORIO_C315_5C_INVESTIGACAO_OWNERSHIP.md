# C3.15.5-C — INVESTIGAÇÃO READ-ONLY DO OWNERSHIP

**Data:** 2026-09-26 18:33:06 UTC  
**Tenant:** 7394370553  
**Modo:** READ-ONLY (zero escritas)  
**Status:** ❌ BLOCKED

---

## 📋 RESULTADO FINAL

```
OWNER_DETERMINADO: NÃO

Motivo: Evidência insuficiente para determinar o proprietário 
        inequivocamente a partir de dados existentes.

AUDIT STATUS: ❌ C3.15.5-C — OWNERSHIP AUDIT: BLOCKED
```

---

## 🔍 INVESTIGAÇÃO DETALHADA

### PASSO 1: Campos de Identidade/Ownership Encontrados em Clientes/7394370553

**Total de campos no documento:** 16

**Campos de identidade/ownership encontrados:** 3

| Campo | Valor | Tipo | Relevância |
|-------|-------|------|-----------|
| `tipo_usuario` | `dono` | string | ✓ Indica papel (INDIRETO) |
| `calendar_id` | `andersonpagostinho@gmail.com` | email | ✗ Email pessoal, não actor_id |
| `id_negocio` | `7394370553` | string | ✗ = tenant_id (redundante) |

**Campos NÃO encontrados:**
- ❌ `dono_id` — não existe
- ❌ `dono_actor_id` — não existe
- ❌ `actor_id` — não existe
- ❌ `user_id` — não existe
- ❌ `phone_number_id` — não existe
- ❌ `owner_id` — não existe

**Conclusão Passo 1:** Não há campo explícito armazenando o actor_id do dono.

---

### PASSO 2: Evidências Históricas Dentro do Tenant no Firestore

**Subcoleções verificadas:** 10

| Subcoleção | Status | Documentos |
|------------|--------|-----------|
| `Donos` | ❌ Vazio | 0 |
| `Comercial` | ❌ Vazio | 0 |
| `onboarding` | ❌ Vazio | 0 |
| `sessoes` | ❌ Vazio | 0 |
| `atores` | ❌ Vazio | 0 |
| `auditorias` | ❌ Vazio | 0 |
| `eventos` | ❌ Vazio | 0 |
| `criacao` | ❌ Vazio | 0 |
| `configuracao` | ❌ Vazio | 0 |
| `_metadata` | ❌ Vazio | 0 |

**Conclusão Passo 2:** Não há evidências históricas no Firestore que relacionem um actor_id ao tenant.

---

### PASSO 3: Evidências em Arquivos Locais do Projeto

**Arquivos pesquisados:** 6  
**Arquivos com referências a 7394370553:** 5

#### Arquivo 1: `rastreio_p0_real.py` (linha 106)

```python
dono_id = "7394370553"
```

**Contexto:**
```python
# Dados da simulação
user_id = "7371670478"
dono_id = "7394370553"
chat_id = user_id
mensagem = "Quero corte com Bruna amanhã às 10"
```

**Análise:**
- Variável: `dono_id`
- Valor: `"7394370553"` (= tenant_id, não actor_id)
- Propósito: Simulação/teste de fluxo
- **Força de evidência:** ❌ **INSUFICIENTE** (é um tenant_id, não um actor_id de dono)

---

#### Arquivo 2: `handlers/bot.py` (linha 81)

```python
OWNER_ID = "7394370553"  # <- coloca aqui o dono desse número/bot
```

**Análise:**
- Constante: `OWNER_ID`
- Valor: `"7394370553"` (= tenant_id, não actor_id)
- Comentário: "coloca aqui o dono desse número/bot" → INCOMPLETO
- **Força de evidência:** ❌ **INSUFICIENTE** (placeholder não preenchido, confunde tenant com owner)

---

#### Arquivo 3: `handlers/whatsapp_bridge_handler.py` (múltiplas linhas)

```python
{
  "canal": "whatsapp",
  "tenant_id": "7394370553",
  "neoeve_number": "5519994443694",
  "actor_id": "5519999999999"
}
```

**Análise:**
- Campo: `actor_id`
- Valor: `"5519999999999"` (número telefônico de teste)
- Propósito: Exemplo/stub do webhook WhatsApp
- **Força de evidência:** ❌ **INSUFICIENTE** (valor de teste/stub, não real)

---

### PASSO 4: Verificação do Actor Suspeito

**Actor suspeito:** 5511991382080

**Resultado:** ❌ Não encontrado

- Não aparece no documento Clientes/7394370553
- Não aparece em subcoleções do tenant
- Não aparece em arquivos locais com associação clara
- **Conclusão:** Sem evidência de relação com tenant 7394370553

---

### PASSO 5: Análise de Candidatos

**Total de candidatos identificados:** 0

**Motivo:** Todos os "candidatos" encontrados em arquivos são:
- Exemplos de teste (`"5519999999999"`)
- Placeholders vazios (`OWNER_ID = "7394370553"` com comentário incompleto)
- Valores confundindo tenant_id com actor_id

**Nenhum candidato tem evidência explícita.**

---

### PASSO 6: Contrato Canônico

**Pesquisa em código de produção:**

| Arquivo | Campo Encontrado | Uso |
|---------|-----------------|-----|
| `onboarding_dono_service.py` | ✓ `dono_actor_id` | Caminho isolado C3.15 |
| `onboarding_dono_service.py` | ✓ `actor_id` | Parâmetro de função |
| `onboarding_service.py` | ✓ `dono_id` | Função legada |
| `onboarding_service.py` | ✓ `actor_id` | Novo sistema |
| `integracao_identidade_onboarding.py` | ✓ `actor_id` | Propagação de identidade |

**Campo Canônico Recomendado:** `dono_actor_id`

**Razão:** 
- Usado no novo path isolado `Clientes/{tenant_id}/Donos/{actor_id}/onboarding`
- Diferencia claramente `dono` (proprietário) de `actor` (qualquer ator)
- Alinhado com C3.15.2 e C3.15.3

---

## 🚫 POR QUE OWNER NÃO PODE SER DETERMINADO

### Motivo 1: Nenhum Campo Explícito

O documento Clientes/7394370553 não tem:
- `dono_id` — simplesmente não existe
- `dono_actor_id` — não existe
- `owner_id` — não existe

O campo `tipo_usuario="dono"` diz qual é o **papel**, não quem é o proprietário.

**Analogia:** "tipo_usuario=dono" é como marcar uma cadeira com "assento do gerente". 
Não diz quem é o gerente.

### Motivo 2: Nenhuma Evidência Histórica no Firestore

Todas as subcoleções estão vazias:
- `Donos` — seria esperado ter documento com actor_id
- `onboarding` — seria esperado ter histórico de quem iniciou
- `atores` — seria esperado ter lista de atores
- Nenhuma auditoria ou log de criação

### Motivo 3: Evidências em Arquivos São Inconclusivas

```python
# rastreio_p0_real.py
dono_id = "7394370553"  # Mas 7394370553 é o TENANT, não o dono!

# handlers/bot.py
OWNER_ID = "7394370553"  # Placeholder vazio, pede para "colocar aqui"

# handlers/whatsapp_bridge_handler.py
actor_id = "5519999999999"  # Valor de teste/stub
```

Todos confundem tenant_id com actor_id ou usam placeholders.

### Motivo 4: Nenhum Candidato com Força Explícita

- **5511991382080:** Não encontrado em nenhum lugar
- **5519999999999:** Apenas em stub de teste WhatsApp
- **7394370553:** É tenant_id, não actor_id
- **andersonpagostinho@gmail.com:** É email, não identificador do sistema

---

## 📊 MAPEAMENTO DE IDENTIDADES

### O Que Sabemos (CONFIRMADO):

```
Clientes/7394370553
├─ tipo_usuario: "dono" .................... Papel, não identidade
├─ id_negocio: "7394370553" ............... Redundante (= tenant_id)
├─ calendar_id: "andersonpagostinho..." ... Email pessoal
├─ dataAssinatura: "2026-09-25" ........... Data, não identidade
└─ nome: "NeoEve Secretária" .............. Negócio, não identidade
```

### O Que NÃO Sabemos (ESPERADO):

```
FALTA:
├─ dono_actor_id: ??? ..................... DESCONHECIDO
├─ dono_id: ??? ........................... DESCONHECIDO
├─ owner_phone_number: ??? ................ DESCONHECIDO
├─ owner_user_id: ??? ..................... DESCONHECIDO
└─ owner_email: ??? ....................... DESCONHECIDO
```

---

## ⚠️ RISCOS DE ASSUMIR UM VALOR ARBITRÁRIO

**CRÍTICO:** Não pode-se simplesmente preencher `dono_actor_id` com um valor inventado porque:

1. **Segurança:** Um ator errado teria acesso completo ao tenant
2. **Auditoria:** Histórico de quem é o verdadeiro dono seria perdido
3. **Conformidade:** Sistema de multi-tenant ficaria comprometido
4. **Reversão:** Se descobrir depois que era outro ator, não há como corrigir

**Conclusão:** Melhor bloquear a migração do que assumir um valor errado.

---

## 🎯 COMO PROCEDER

### Opção A: Contato com Proprietário (Recomendado)

1. Usar `calendar_id` = `andersonpagostinho@gmail.com` para contato
2. Perguntar: "Qual é seu actor_id/phone_number no sistema?"
3. Validar a resposta contra logs de acesso
4. Backfill do campo `dono_actor_id` com confirmação
5. Re-auditar com C3.15.5-C

### Opção B: Análise de Logs/Auditoria Externa

1. Verificar logs de API (fora do escopo Firestore)
2. Verificar quem fez primeira chamada para criar tenant
3. Extrair actor_id de headers/contexto dessa chamada
4. Backfill com evidência forte
5. Re-auditar

### Opção C: Análise de Google Calendar

1. `calendar_id` = `andersonpagostinho@gmail.com`
2. Verificar quem criou o calendário associado
3. Correlacionar com sistema de usuários
4. Extrair actor_id
5. Backfill com evidência
6. Re-auditar

---

## 📎 GARANTIAS CUMPRIDAS

```
✅ Somente leituras executadas no Firestore
✅ ZERO escritas (.set, .update, .create, .delete)
✅ Nenhuma transaction ou batch
✅ Nenhum código alterado
✅ Nenhum documento criado
✅ Nenhum actor_id inventado
✅ Investigação rigorosa e documentada

WRITES EXECUTADAS: 0
```

---

## 🔴 STATUS FINAL

```
❌ C3.15.5-C — OWNERSHIP AUDIT: BLOCKED

Motivo: Evidência insuficiente para determinar o proprietário inequivocamente.

Próximo passo: Contato com proprietário ou análise de logs históricos.

NÃO prosseguir com C3.15.5-D (migração real) sem resolver isso.
```

---

**Relatório gerado:** 2026-09-26 18:33:06 UTC  
**Arquivo detalhado:** investigacao_c315_5c_7394370553_20260926_183307.json  
**Execução:** READ-ONLY, sem impacto nos dados  
**Recomendação:** Contato com proprietário via email (andersonpagostinho@gmail.com)
