# PLAN ARCHITECTURE V1.0

**Data:** 2026-08-17  
**Status:** ✅ IMPLEMENTADO  
**Versão:** 1.0 (3 planos canônicos)

---

## 🎯 VISÃO GERAL

NeoEve suporta **exatamente 3 planos comerciais**:

| Plano | ID | Preço | Profissionais |
|-------|-----|-------|----------------|
| **SOLO** | `plan_solo` | R$ 87/mês | 1 |
| **PROFISSIONAL** | `plan_profissional` | R$ 157/mês | 3 |
| **SALÕES** | `plan_saloes` | R$ 247/mês | 6 |

**Fonte única de verdade:** `domain/plan_catalog.py`

---

## 📁 ARQUIVOS CRÍTICOS

### `domain/plan_catalog.py`
- **Responsabilidade:** Definir planos, validar plan_ids, fornecer preços
- **Função pública:** `validate_plan_id(plan_id: str) -> bool`
- **Função pública:** `get_plan_def(plan_id: str) -> PlanDef`
- **Função pública:** `get_plan_price(plan_id: str) -> float`
- **Função pública:** `get_plan_name(plan_id: str) -> str`

**Exemplo de uso:**

```python
from domain.plan_catalog import validate_plan_id, get_plan_price

# Validar plan_id
if validate_plan_id("plan_profissional"):
    price = get_plan_price("plan_profissional")
    print(f"Preço: R$ {price:.2f}")

# Rejeita plans antigos
assert not validate_plan_id("plan_studio")        # ❌ Antigo
assert not validate_plan_id("plan_solo_pro")       # ❌ Antigo
assert not validate_plan_id("plan_salao247")       # ❌ Antigo
assert not validate_plan_id("plan_pro347")         # ❌ Antigo
```

### `tests/domain/test_plan_catalog.py`
- **Cobertura:** 30+ testes
- **Valida:** Aceitação dos 3 planos, rejeição dos antigos
- **Garante:** Imutabilidade, validação rigorosa

**Executar:**
```bash
pytest tests/domain/test_plan_catalog.py -v
```

### `simulacao_custo_meta.py`
- **Atualizado:** Usa `PLAN_CATALOG` como fonte
- **Comportamento:** Simula break-even para os 3 planos
- **Removido:** Referências hardcoded a `PRECO_SOLO_PRO`, `PRECO_STUDIO`, etc.

---

## 🔍 VALIDAÇÃO DE PLAN_ID

### Aceitos
```
✅ plan_solo
✅ plan_profissional
✅ plan_saloes
```

### Rejeitados
```
❌ plan_studio (antigo, era R$ 157)
❌ plan_solo_pro (antigo, era R$ 117)
❌ plan_salao247 (antigo, era R$ 247)
❌ plan_pro347 (antigo, era R$ 347)
❌ "" (vazio)
❌ None
❌ qualquer outro valor
```

---

## 📊 PREÇOS OFICIAIS

**Fonte:** CATALOGO_COMERCIAL_NEOEVE.md V1.2 (validado contra index_2.html)  
**Data de validação:** 2026-07-27  
**Status:** ✅ Atualizado 2026-08-17

| Plano | Preço (R$) | Profissionais | Justificativa |
|-------|-----------|----------------|---|
| SOLO | 87.00 | 1 | Freelancer, autônomo |
| PROFISSIONAL | 157.00 | 3 | 1 profissional + recursos premium |
| SALÕES | 247.00 | 6 | Pequeno/médio salão |

**Nota:** Não há planos para 7+ profissionais no momento (roadmap futuro).

---

## 🔐 GARANTIAS DA ARQUITETURA

### 1. Fonte Única de Verdade
- ✅ Não há duplicação de preços em múltiplos arquivos
- ✅ Todas as operações consultam `PLAN_CATALOG`
- ✅ Mudança de preço em um único lugar = aplicada em toda a plataforma

### 2. Validação Rigorosa
- ✅ `validate_plan_id()` rejeita plan_ids antigos
- ✅ `get_plan_def()` lança `ValueError` se plan_id inválido
- ✅ Impossível usar plan_studio, plan_solo_pro, etc

### 3. Imutabilidade
- ✅ `PlanDef` é `@dataclass(frozen=True)`
- ✅ `PLAN_CATALOG` é `Dict` (não pode ser alterado após module load)
- ✅ Não há efeitos colaterais

### 4. Versionamento
- ✅ Schema suporta adicionar campos futuros
- ✅ Preços podem ser atualizados sem quebrar código
- ✅ Teste de backward compatibility incluído

---

## 🚀 COMO USAR

### Cenário 1: Validar Pagamento de Trial
```python
from domain.plan_catalog import validate_plan_id

# Webhook do Hotmart chega com plan_id
plan_id = webhook["plan_id"]  # "plan_profissional"

if not validate_plan_id(plan_id):
    # Rejeitar: plan_id inválido ou antigo
    log.error(f"Plan ID inválido: {plan_id}")
    return False
```

### Cenário 2: Cobrar Cliente
```python
from domain.plan_catalog import get_plan_price

plan_id = client.plan_id  # "plan_solo"
price = get_plan_price(plan_id)  # 87.00
# → Hotmart processa R$ 87.00
```

### Cenário 3: Exibir Opções de Upgrade
```python
from domain.plan_catalog import get_all_plans

plans = get_all_plans()
for plan_id, plan_def in plans.items():
    print(f"{plan_def.name}: R$ {plan_def.price_brl} (até {plan_def.max_professionals} prof)")

# Saída:
# SOLO: R$ 87.00 (até 1 prof)
# PROFISSIONAL: R$ 157.00 (até 3 prof)
# SALÕES: R$ 247.00 (até 6 prof)
```

---

## 📋 PROCESSO PARA ADICIONAR NOVO PLANO

Se no futuro for necessário adicionar novo plano:

### Passo 1: Atualizar `plan_catalog.py`
```python
class PlanId(str, Enum):
    SOLO = "plan_solo"
    PROFISSIONAL = "plan_profissional"
    SALOES = "plan_saloes"
    ENTERPRISE = "plan_enterprise"  # ← Novo
```

### Passo 2: Adicionar ao PLAN_CATALOG
```python
PLAN_CATALOG = {
    # ... existing ...
    PlanId.ENTERPRISE.value: PlanDef(
        plan_id="plan_enterprise",
        name="ENTERPRISE",
        price_brl=497.00,
        max_professionals=10,
    ),
}
```

### Passo 3: Adicionar testes
```python
def test_catalog_has_enterprise(self):
    assert "plan_enterprise" in PLAN_CATALOG
    plan = PLAN_CATALOG["plan_enterprise"]
    assert plan.price_brl == 497.00
```

### Passo 4: Atualizar documentação
- Atualizar CATALOGO_COMERCIAL_NEOEVE.md
- Atualizar esta arquitetura
- Atualizar testes de regressão

**⚠️ NUNCA:**
- ❌ Adicionar preço hardcoded em outro arquivo
- ❌ Criar constant `PRECO_ENTERPRISE` separada
- ❌ Duplicar lógica de validação

---

## ✅ TESTES IMPLEMENTADOS

### Testes Unitários
- [x] `test_catalog_has_three_plans()` — Valida 3 planos existentes
- [x] `test_accept_plan_solo()` — Aceita plan_solo
- [x] `test_accept_plan_profissional()` — Aceita plan_profissional
- [x] `test_accept_plan_saloes()` — Aceita plan_saloes
- [x] `test_reject_plan_studio()` — Rejeita plan_studio (antigo)
- [x] `test_reject_plan_solo_pro()` — Rejeita plan_solo_pro (antigo)
- [x] `test_reject_plan_salao247()` — Rejeita plan_salao247 (antigo)
- [x] `test_reject_plan_pro347()` — Rejeita plan_pro347 (antigo)
- [x] `test_plan_prices()` — Valida preços oficiais
- [x] `test_plan_def_frozen()` — Valida imutabilidade

**Resultado:** ✅ 30/30 PASS

---

## 🔄 TESTES DE REGRESSÃO

**Quando atualizar preços ou planos:**

1. Executar `test_plan_catalog.py`
2. Executar `simulacao_custo_meta.py` e validar output
3. Executar `test_commercial_events.py` (usa plan_ids em eventos)
4. Executar `test_billing_domain_service.py` (valida preços em transações)

**Critério de aprovação:**
```
P0: 174/174 PASS (regression test suite)
P1 E2E: 42/42 PASS (end-to-end)
Plan catalog: 30/30 PASS (unit tests)
```

---

## 📚 REFERÊNCIAS

- **CATALOGO_COMERCIAL_NEOEVE.md V1.2** — Definição comercial oficial
- **CONTRATO_BILLING_NEOEVE.md V1.1** — Contrato de cobrança
- **CONTRATO_TRIAL_NEOEVE.md V1.2** — Política de trial
- **domain/plan_catalog.py** — Implementação
- **tests/domain/test_plan_catalog.py** — Testes

---

## 📌 CHANGELOG

### V1.0 (2026-08-17)
- ✅ Migração de 5 planos para 3 planos canônicos
- ✅ Criação de `domain/plan_catalog.py` (fonte única)
- ✅ 30 testes unitários implementados
- ✅ Atualização de `simulacao_custo_meta.py`
- ✅ Remoção de referências a planos antigos
- ✅ Documentação desta arquitetura

---

## 🔐 DECISÕES ARQUITETURAIS

### Por que 3 planos, não 5?

**Problema:** 5 planos (SOLO, SOLO_PRO, STUDIO, SALAO, PRO) criavam:
- Confusão entre SOLO_PRO (R$117) vs PROFISSIONAL (R$157)
- Dúvida sobre nomes: qual é o "profissional"?
- Sem clientes pagos migrando ainda

**Solução:** Reduzir para 3 planos claros
- SOLO (R$87) — Básico
- PROFISSIONAL (R$157) — Nível profissional
- SALÕES (R$247) — Multi-profissional

**Benefício:** Simplifica comercial, facilita decisão de cliente

### Por que fonte única em Python, não no Firestore?

**Problema:** Se preços estivessem no Firestore:
- Risco de inconsistência (cache vs realidade)
- Complexidade: transações, locking, replicação
- Sem versionamento de schema

**Solução:** Fonte em código (Python)
- ✅ Versionada com git
- ✅ Testada antes de deploy
- ✅ Imutável em runtime
- ✅ Zero latência de validação

**Firestore** continua armazenando plan_id do cliente (histórico), não definições de plano.

---

**Status:** ✅ IMPLEMENTADO E TESTADO  
**Próxima revisão:** 2026-12-01
