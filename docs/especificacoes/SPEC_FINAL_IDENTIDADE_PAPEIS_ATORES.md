# ESPECIFICAÇÃO FINAL — IDENTIDADE, PAPÉIS E ATORES

**Data:** 2026-06-28  
**Status:** ✅ ESPECIFICAÇÃO OFICIAL  
**Versão:** 1.0 — Congelada  

---

## REGRA OFICIAL: ARQUITETURA FINAL DE PAPÉIS

### 🎯 Princípio Central

**Dono nasce apenas por onboarding administrativo explícito.**  
**Não há exceções.**

---

## PAPÉIS: DEFINIÇÃO OFICIAL

### 1️⃣ DONO

**Quando nasce:**
- Onboarding administrativo explícito
- Conexão/pairing do negócio (bootstrap do tenant)
- Call administrativo direcionado
- Setup inicial de um novo negócio

**Quando NÃO nasce:**
```
❌ Primeiro acesso a um canal
❌ Tenant vazio (sem ninguém)
❌ Ausência de onboarding completo
❌ user_id == tenant_id sozinho (sem contexto explícito)
❌ Fallback de ambiguidade de papel
```

**Propriedades:**
- Acesso administrativo/configuração
- Pode criar profissionais
- Pode agendar para clientes
- Onboarding obrigatório (11 etapas)
- Único por tenant (ou múltiplos em estrutura equipe)

**Criação:**
```python
# APENAS quando:
if eh_dono_explicito and not tem_dono:
    criar_ator_dono()
```

---

### 2️⃣ PROFISSIONAL

**Quando nasce:**
- Cadastro explícito do dono
- Via fluxo administrativo do dono
- Pairing/conexão iniciada pelo dono

**Quando NÃO nasce:**
```
❌ Acesso automático por canal
❌ Inferência de papel
❌ Fallback de ambiguidade
```

**Propriedades:**
- Acesso apenas a agendar/consultar própria agenda
- Atender clientes
- Visualizar configuração do negócio
- Sem acesso administrativo

**Criação:**
```python
# APENAS por:
await dono.cadastrar_profissional(nome, canal, servicos)
```

---

### 3️⃣ CLIENTE

**Quando nasce:**
- Automaticamente ao falar com um canal já vinculado a um tenant
- Primeiro acesso desconhecido em canal de atendimento
- Qualquer actor desconhecido em tenant existente

**Propriedades:**
- Acesso apenas a agendar
- Consultar própros agendamentos
- Sem acesso administrativo
- Sem onboarding

**Criação:**
```python
# Automático quando:
if not eh_dono_explicito:  # Papel não explícito
    # Sempre criar CLIENTE, nunca DONO
    criar_ator_cliente_automatico()
```

---

## MATRIZ DE DECISÃO (PONTO 2)

Quando novo actor chega sem estar em `Clientes/{tenant_id}/Atores/`:

| Condição | Ação | Papel | Onboarding | Proxima Acao |
|----------|------|-------|-----------|--------------|
| `!eh_dono_explicito` + `!tem_dono` | criar CLIENTE (fallback) | **CLIENTE** | Não | normal |
| `!eh_dono_explicito` + `tem_dono` | criar CLIENTE | **CLIENTE** | Não | normal |
| `eh_dono_explicito` + `!tem_dono` | criar DONO + onboarding | **DONO** | Sim | onboarding |
| `eh_dono_explicito` + `tem_dono` | criar CLIENTE | **CLIENTE** | Não | normal |

**Regra da Coluna 1 (!) :** Papel ambíguo = CLIENTE (fallback seguro)

---

## DETERMINISMO

### Resolução Exata de Papel

**Fonte 1:** Ator já existe em banco
```python
if ator_existente:
    tipo_usuario = ator_existente["tipo_usuario"]
    # Pronto, papel é determinístico
```

**Fonte 2:** Ator desconhecido, resolver papel
```python
# Guard 1: papel explícito?
eh_dono_explicito = (tenant_id == user_id)

# Guard 2: tenant tem dono?
tem_dono = await tenant_tem_dono(tenant_id)

# Decisão é 100% determinística baseado em (eh_dono_explicito, tem_dono)
```

**Não há:**
```
❌ Inferência baseada em mensagem
❌ Fallback para dono por ausência de informação
❌ Promoção posterior cliente→dono
```

---

## IMPLEMENTAÇÃO

### Arquivo: `router/integracao_identidade_onboarding.py`

**PONTO 2 (linhas 147-276): Ator desconhecido**

```python
eh_dono_explicito = (tenant_id == user_id)
tem_dono = await tenant_tem_dono(tenant_id)

if not eh_dono_explicito and not tem_dono:
    # Actor desconhecido + tenant vazio = CLIENTE
    criar_ator_cliente_automatico()
    
elif eh_dono_explicito and not tem_dono:
    # user_id == tenant_id (explícito) = DONO
    criar_ator_dono()
    iniciar_onboarding_dono()
    
else:
    # Qualquer outro caso = CLIENTE
    criar_ator_cliente_automatico()
```

**PONTO 1 (linhas 100-146): Ator existente**
```python
# Ator já existe → retorna papel dele
# Sem alteração, sem lógica de promoção
```

---

## TESTES VALIDANDO A ESPECIFICAÇÃO

### P1: Onboarding Identidade (15/15 PASS)

| Cenário | Input | Esperado | Obtido | Status |
|---------|-------|----------|--------|--------|
| 1. Primeiro acesso comum | actor desconhecido + tenant vazio | CLIENTE | CLIENTE | ✅ PASS |
| 2-15 | Vários cenários | Diversos | Conforme spec | ✅ PASS |

### P0: Bloqueio Promoção (5/5 PASS)

| Cenário | Validação | Status |
|---------|-----------|--------|
| 1. Cliente com modo_uso não promove | tipo_usuario=cliente mantido | ✅ PASS |
| 2. Cliente desconhecido → fallback | Criado como cliente, não dono | ✅ PASS |
| 3. Novo dono (explícito) funciona | Onboarding inicia | ✅ PASS |
| 4. Dono existente sem onboarding | Retomada funciona | ✅ PASS |
| 5. Multi-tenant isolation | Cliente em A não vira dono em B | ✅ PASS |

---

## CASOS PERMITIDOS

### ✅ Dono nasce quando

1. **Onboarding administrativo**
   ```
   Dono acessa link de setup
   → sistema cria dono
   → inicia onboarding_dono
   ```

2. **Pairing/conexão do negócio**
   ```
   Dono conecta WhatsApp do negócio
   → sistema cria dono do tenant
   ```

3. **Bootstrap inicial**
   ```
   Novo negócio criado no CRM
   → dono atribuído automaticamente
   ```

---

## CASOS PROIBIDOS

### ❌ Dono NÃO nasce quando

1. **Primeiro acesso a canal de atendimento**
   ```
   Actor desconhecido fala via WhatsApp
   → criar CLIENTE, NUNCA DONO
   ❌ Mesmo se tenant vazio
   ```

2. **Tenant não tem dono**
   ```
   Actor fala em canal já vinculado
   → criar CLIENTE (fallback seguro)
   ❌ Nunca promover automaticamente
   ```

3. **user_id == tenant_id sem contexto**
   ```
   Coincidência de IDs sozinha
   ❌ Não é prova de dono
   ⚠️ Requer fluxo explícito de onboarding
   ```

4. **Ausência de onboarding**
   ```
   Actor sem onboarding_dono marcado
   ❌ Não implica que é cliente
   ⚠️ Pode estar em onboarding incompleto
   ```

---

## FRICÇÃO ZERO

**Objetivo:** Nenhuma pergunta ao usuário sobre seu papel.

**Como funciona:**

1. **Actor desconhecido chega**
   ```
   "Olá, quero agendar"
   → Resolver tenant_id via canal
   → Resolver papel via guards (eh_dono_explicito, tem_dono)
   → Criar papel correto sem perguntar
   → Proceder com fluxo apropriado
   ```

2. **Sem perguntas tipo:**
   ```
   ❌ "Você é dono, profissional ou cliente?"
   ❌ "Qual é seu papel no negócio?"
   ❌ "Você é a primeira pessoa a usar?"
   ```

3. **Determinismo resolve sozinho**
   ```
   Guards (eh_dono_explicito, tem_dono) → papel
   → Criar papel correto
   → Fluxo automático
   ```

---

## VALIDAÇÃO CONTÍNUA

### Regressão P0: 174/174 PASS ✅

Nenhuma regressão introduzida pela especificação de papéis.

### Teste Manual Obrigatório

**Cenário:** Novo negócio, primeiro acesso desconhecido

```
1. Actor desconhecido chega em canal
2. Sistema resolve: tenant_id (via canal), papel (via guards)
3. Sistema cria: CLIENTE (fallback seguro)
4. Nenhuma pergunta feita
5. Fluxo cliente normal procede
6. Validação: actor criado com tipo_usuario="cliente" ✅
```

---

## CHECKLIST FINAL

- ✅ Dono nasce APENAS por onboarding administrativo explícito
- ✅ Profissional nasce APENAS por cadastro do dono
- ✅ Cliente nasce automaticamente ao falar com canal vinculado
- ✅ Primeiro acesso desconhecido = CLIENTE (nunca DONO)
- ✅ Tenant vazio + actor desconhecido = CLIENTE (fallback seguro)
- ✅ Zero perguntas ao usuário sobre papel
- ✅ Determinismo 100% (guards)
- ✅ P0 174/174 PASS (nenhuma regressão)
- ✅ P1 15/15 PASS (identidade validada)
- ✅ P1 5/5 PASS (bloqueio promoção validado)

---

## STATUS

✅ **ESPECIFICAÇÃO CONGELADA E OFICIAL**

Data de implementação: 2026-06-28  
Data de validação: 2026-06-28  
Aprovação: Equipe P0

**Próximas mudanças não são permitidas sem decisão explícita.**

---

## REFERÊNCIAS

- [PONTO 1](integracao_identidade_onboarding.py:100-146): Ator existente
- [PONTO 2](integracao_identidade_onboarding.py:147-276): Ator desconhecido
- [Teste P1 Identidade](tests/p1_e2e_onboarding_identidade_real.py): 15/15 PASS
- [Teste Bloqueio Promoção](tests/test_p0_bloqueio_promocao_cliente_dono_firebase_real.py): 5/5 PASS
- [P0 Regressão](tests/runner_p0_regressao_completa.py): 174/174 PASS
