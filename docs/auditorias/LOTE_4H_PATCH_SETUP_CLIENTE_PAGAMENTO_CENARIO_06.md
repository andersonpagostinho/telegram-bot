# LOTE 4H — PATCH SETUP CLIENTE PAGAMENTO CENÁRIO 06

**Data:** 2026-06-22  
**Escopo:** tests/p1_robustez_fluxo_conversacional_real.py, cenário 06 apenas  
**Objetivo:** Criar cliente com pagamento ativo para resolver verificar_pagamento fail

---

## PATCH APLICADO

### 1. Import Adicionado

**Arquivo:** `tests/p1_robustez_fluxo_conversacional_real.py` (linha 53)

```python
from services.firebase_service_async import (
    ...
    salvar_cliente,  # ← ADICIONADO
)
```

---

### 2. Cliente com Pagamento Ativo (Cenário 06)

**Localização:** Linha ~632 de cenário_06_confirmacao_embutida()

**Patch:**
```python
# [LOTE 4H] Criar cliente com pagamento ativo (necessário para add_evento_por_gpt)
# Sem isso, verificar_pagamento() falha e evento não é criado
await salvar_cliente(actor_id, {
    "nome": "Cliente Teste",
    "pagamentoAtivo": True,
    "planosAtivos": ["secretaria"],
    "canal": "whatsapp"
})
```

**Impacto:** `verificar_pagamento()` agora passa (cliente existe e pagamento ativo)

---

### 3. Conversão de Data para ISO (Bonus)

**Problema adicional identificado:** Data estava em formato texto "amanhã 14:00" mas `add_evento_por_gpt` espera ISO

**Patch Adicional:**
```python
# [LOTE 4H] Converter data para ISO format (add_evento_por_gpt espera ISO)
import dateparser
amanha_dt = dateparser.parse("amanhã 14:00", languages=["pt"], settings={"PREFER_DATES_FROM": "future"})
data_hora_iso = amanha_dt.isoformat()
```

**Impacto:** Data agora é convertida para ISO antes de salvar contexto

---

## VALIDAÇÃO REALIZADA

### Sintaxe

✅ **Validação:** `python -m py_compile` — OK

### Teste Cenário 06

❌ **Status:** FAIL (nova razão, não mais verificar_pagamento)

**Análise:**
1. ✅ Cliente criado com pagamento ativo
2. ✅ verificar_pagamento() agora passa
3. ✅ Data convertida para ISO
4. ❌ Novo bloqueio: Tenant mismatch em session legada

**Log evidência:**
```
[DEBUG_4H] verificar_pagamento passou
[SESSAO LEGADO TENANT MISMATCH] RECUSADA
```

**Causa raiz do novo bloqueio:** Contexto sendo salvo em path legado (`Clientes/actor_id/MemoriaTemporaria`) mas função procura session v2 (`Clientes/tenant_id/Sessoes/actor_id`)

**Escopo deste bloqueio:** Fora do LOTE 4H (arquitetura de session legado vs v2)

### Teste Cenário 07

✅ **Status:** PASS (sem regressão)

### Baseline P0

⏳ **Status:** Não testado ainda (aguarda conclusão LOTE 4H)

---

## STATUS FINAL LOTE 4H

| Aspecto | Status | Nota |
|---------|--------|------|
| ✅ Import salvar_cliente | FEITO | Adicionado |
| ✅ Cliente com pagamento | CRIADO | Adicionado ao cenário 06 |
| ✅ Data convertida para ISO | FEITO | Bonus fix |
| ✅ verificar_pagamento passa | OK | Cliente encontrado |
| ✅ Cenário 07 sem regressão | PASS | Confirmado |
| ❌ Cenário 06 evento criado | FALHA | Nova razão: session v2 vs legado |
| ⏳ Baseline P0 | PENDENTE | A executar |

---

## ESCOPO DO PATCH MÍNIMO (LOTE 4H)

**Objetivo:** Resolver `verificar_pagamento()` fail

**Realizado:**
- ✅ Cliente criado com pagamento ativo (LOTE 4H original)
- ✅ Data convertida para ISO (bonus fix)
- ✅ verificar_pagamento agora passa

**Não realizado (fora do escopo LOTE 4H):**
- ❌ Resolver session legacy vs v2 mismatch
- ❌ Garantir cenário 06 passa
- ❌ Rearquitetar salvamento de contexto

---

## PRÓXIMOS PASSOS

### Se continuar para LOTE 4I (investigar session v2):

**Problema:** `add_evento_por_gpt` procura session em `Clientes/tenant_id/Sessoes/actor_id` mas teste salva em `Clientes/actor_id/MemoriaTemporaria`

**Opção A:** Usar salvamento de session v2 no teste (compatível com add_evento_por_gpt)

**Opção B:** Corrigir add_evento_por_gpt para usar carregar_contexto_temporario() que respeita o path legado

**Opção C:** Aceitar que cenário 06 é um caso especial que precisa de setup mais complexo

### Runnar baseline P0

```bash
python tests/p1_e2e_onboarding_identidade_real.py
python tests/p1_e2e_onboarding_operacional_completo_real.py
python tests/p1_e2e_onboarding_individual_real.py
python tests/runner_p0_regressao_completa.py
```

---

## CONCLUSÃO

**LOTE 4H:** Patch mínimo de cliente com pagamento ativo foi aplicado com sucesso.

**Resultado:** `verificar_pagamento()` agora passa, mas novo bloqueio (session v2 vs legado) apareceu.

**Escopo:** LOTE 4H completou seu objetivo específico (resolver verify_pagamento). Próximo bloqueio (session) está além do escopo.

**Recomendação:** Rodar baseline P0 para validar que não houve regressão, então decidir se continua investigação de cenário 06 ou aceita como case especial.

