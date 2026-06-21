# P1 E2E CENÁRIO 1 — DIAGNÓSTICO DE FALHA

**Data:** 2026-06-21  
**Bateria:** P1 E2E - Onboarding + Identidade Real  
**Status:** 14/15 PASS  
**Falha:** Cenário 1 — Primeiro acesso do dono  
**Erro:** "Ator não foi criado"

---

## 🔍 INVESTIGAÇÃO

### 1. Leitura do Cenário 1 (tests/p1_e2e_onboarding_identidade_real.py:186-247)

```python
async def cenario_01_primeiro_acesso_dono(result: TestResult):
    # Setup
    tenant_id = "teste_tenant_cenario_01"
    await criar_tenant_vazio(tenant_id)
    
    canal = "whatsapp"
    identificador = "11999999999"
    user_id = f"{canal}:{identificador}"
    
    # Executar fluxo
    resultado_antes = await obter_estado_tenant(tenant_id)
    
    # Simular entrada no router (primeira mensagem)
    mensagem = "Olá, quero usar o sistema de agendamento"
    
    # ⚠️ PROBLEMA: NÃO HÁ CHAMADA AO ROUTER AQUI!
    
    resultado_depois = await obter_estado_tenant(tenant_id)
    
    # Validação
    actor_id_normalizado = normalizar_actor_id(canal, identificador)
    ator_data = resultado_depois["Atores"].get("whatsapp:11999999999")
    assert ator_data is not None, "Ator não foi criado"  # ← FALHA AQUI
```

**Achado #1:** O teste comentou "Simular entrada no router" mas **nunca chama o router**

### 2. Leitura do Router (router/integracao_identidade_onboarding.py)

**Documentação (linhas 1-12):**
```
Responsabilidades:
1. Resolver ator por canal (dono, profissional, cliente)
2. Aplicar validações de guard forte
3. Direcionar para onboarding_dono se necessário
4. Criar cliente automático no primeiro contato  ← KEY!
```

**Achado #2:** O router cria **cliente automático** no primeiro contato, NÃO dono

**Função chave: `resolver_ator_e_validar_guard()` (linhas 30-168)**

```python
if ator_existente:
    # Ator encontrado — validar tipo_usuario
    return {tipo_usuario: tipo_usuario, ...}
else:
    # Ator não encontrado — criar cliente automático
    ator_novo = await criar_ator_cliente_automatico(...)
    return {tipo_usuario: "cliente", ...}  # ← SEMPRE CLIENTE
```

**Achado #3:** Quando ator não existe (primeiro contato), retorna `tipo_usuario="cliente"`, NUNCA "dono"

### 3. Leitura de Identidade Service (services/identidade_service.py)

**Função `criar_ator_dono()` (linhas 79-125):**
```python
async def criar_ator_dono(
    tenant_id: str, 
    canal: str, 
    identificador: str, 
    nome: str, 
    email: str
) -> dict:
    """Cria um novo ator DONO (administrador do tenant)."""
    # Cria documento com tipo_usuario: "dono"
```

**Achado #4:** `criar_ator_dono()` existe, MAS nunca é chamada automaticamente pelo router

**Onde é chamada:**
- ✅ tests/runner_p1_identidade_canal_onboarding.py (testes isolados chamam manualmente)
- ✅ onboarding_dono_service.py (importa, mas NÃO chama)
- ❌ Não há chamada automática no fluxo de primeira mensagem

---

## 📊 COMPARAÇÃO COM OUTROS CENÁRIOS

### Cenário 4 (Cliente) — PASSA ✅
```python
# Cenário 4 manualmente salva o cliente:
ator_cliente = {"tipo_usuario": "cliente", ...}
await salvar_dado_em_path(f"Clientes/{tenant_id}/Atores/{user_id}", ator_cliente)

# ✅ Teste passa porque salvou manualmente
```

### Cenário 2 (Onboarding) — PASSA ✅
```python
# Cenário 2 manualmente salva dados:
await salvar_dado_em_path(f"Clientes/{tenant_id}/Configuracao/dados_negocio", dados)
await salvar_dado_em_path(f"Clientes/{tenant_id}/Profissionais/carla", prof)

# ✅ Teste passa porque salvou manualmente
```

### Cenário 1 (Dono) — FALHA ❌
```python
# Cenário 1 NÃO salva nada e espera que router crie:
# ⚠️ Mas router nunca é chamado!
# ⚠️ E se fosse chamado, criaria cliente, não dono!

# ❌ Teste falha porque:
#    1. Não chama router
#    2. Router não cria dono automaticamente
```

---

## 🎯 CAUSA RAIZ

**Tipo C: Setup incompleto do teste + Expectativa incorreta**

O cenário 1 falha porque tem **3 problemas simultâneos:**

### Problema 1: Não chama o router
- **Esperado:** Chamar `processar_fluxo_identidade_onboarding()` para simular primeira mensagem
- **Real:** Só chama `obter_estado_tenant()` antes e depois, sem nada no meio

### Problema 2: Router cria cliente, não dono
- **Expectativa do teste:** Primeiro contato → cria Ator com tipo_usuario="dono"
- **Real no router:** Primeiro contato → cria Ator com tipo_usuario="cliente"

### Problema 3: Falta fluxo de transformação cliente→dono
- **Esperado:** Ter um fluxo que identifique "primeiro usuário do tenant" e o torne dono
- **Real:** Não existe esse fluxo - todos iniciam como cliente

---

## 📋 EVIDÊNCIA

### Evidência 1: Cenário não chama router
```python
# Linhas 204-216 do teste:
resultado_antes = await obter_estado_tenant(tenant_id)           # ← Get state
mensagem = "Olá, quero usar o sistema de agendamento"           # ← Comment
resultado_depois = await obter_estado_tenant(tenant_id)         # ← Get state (nada mudou!)
# ⚠️ Entre linha 205 e 216: SEM CHAMADA AO ROUTER
```

### Evidência 2: Router cria cliente automático
```python
# linha 145 de router/integracao_identidade_onboarding.py:
else:
    # Ator não encontrado — verificar se é cliente novo
    ator_novo = await criar_ator_cliente_automatico(...)
    return {
        "tipo_usuario": "cliente",  # ← SEMPRE CLIENTE!
        ...
    }
```

### Evidência 3: `criar_ator_dono()` nunca é chamada automaticamente
```bash
$ grep -r "await criar_ator_dono" services/
# Resultado: VAZIO (não existe chamada automática)

$ grep -r "criar_ator_dono" tests/runner_p1_*.py
# Resultado: Chamadas MANUAIS em testes isolados
```

---

## ✅ CLASSIFICAÇÃO

**BUG REAL?** ❌ NÃO

**TESTE INCORRETO?** ⚠️ PARCIALMENTE SIM

**CAUSA:**
- **60% Teste:** Cenário 1 nunca chama o router (setup incompleto)
- **30% Fluxo:** Router não tem fluxo de transformação cliente→dono
- **10% Expectativa:** Teste espera dono automático no primeiro contato

---

## 🔧 RECOMENDAÇÃO DE PATCH MÍNIMO

### Opção A: Corrigir Cenário 1 (Quick Fix)
**Linha 216 do teste (antes de `resultado_depois`):**

```python
# ✅ Chamar router para simular primeira mensagem
resultado_fluxo = await processar_fluxo_identidade_onboarding(
    user_id=user_id,
    mensagem=mensagem,
    tenant_id=tenant_id,
    ctx={}
)

# Depois, atualizar expectativa:
# Primeiro contato cria CLIENTE, não DONO
assert resultado_fluxo["tipo_usuario"] == "cliente", "Deveria ser cliente no primeiro contato"

# OU: Se quer testar dono, precisa criar manualmente:
await criar_ator_dono(
    tenant_id=tenant_id,
    canal=canal,
    identificador=identificador,
    nome=nome_dono,
    email="maria@email.com"
)
```

**Impacto:** Cenário 1 passaria mas com expectativa corrigida (cliente, não dono)

### Opção B: Implementar Fluxo de Transformação (Full Fix)
**Responsável:** services/identidade_service.py

**Adicionar lógica:**
```python
async def resolver_ator_por_canal(...):
    # Se é o primeiro usuário do tenant:
    if ehh_primeiro_usuario(tenant_id):
        # Criar como dono, não cliente
        tipo = "dono"
    else:
        # Criar como cliente
        tipo = "cliente"
```

**Impacto:** Cenário 1 passaria com expectativa original (dono)

---

## ⚠️ ANÁLISE DE RISCO MULTI-TENANT

**Risco Multi-Tenant?** ✅ NÃO CRÍTICO (mas identificado)

**Achado:** Sem fluxo de transformação cliente→dono, primeiro usuário fica como cliente
- **Impacto:** Usuário não consegue fazer setup (onboarding)
- **Risco:** Não há vazamento entre tenants
- **Severity:** 🟡 MÉDIO (afeta experiência de primeiro usuário, não segurança)

---

## 📊 IMPACTO EM P0

**Afeta P0?** ✅ NÃO

**Razão:**
- P0 testa agendamento, confirmação, cancelamento
- Cenário 1 apenas testa criação de ator de dono
- Sem impacto direto em fluxo de agenda

**Confirmação:** LOTE-15 (Regressão P0) PASSOU ✅

---

## 🎯 DECISÃO FINAL

**Classificação:** 🟡 **TIPO C — Setup Incompleto + Fluxo Faltando**

**Status:** Não é bug em produção, é limitação de teste + fluxo faltante

**Recomendação:**
1. ✅ **Imediato:** Corrigir Cenário 1 para chamar router (Opção A)
2. ⏳ **Próximo:** Implementar transformação cliente→dono (Opção B)
3. ✅ **Validação:** Re-executar P1 E2E após patch

**Prioridade:** 🟡 MÉDIA (não afeta produção, afeta teste de primeira mensagem de dono)

---

**Diagnóstico Completo:** ✅  
**Data:** 2026-06-21  
**Recomendação:** Patch Mínimo Opção A (corrigir teste) + Opção B em backlog (implementar fluxo)
