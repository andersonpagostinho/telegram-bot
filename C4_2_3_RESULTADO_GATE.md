# C4.2.3 — RESULTADO DO REGRESSION GATE DO SCHEDULER

**Data:** 2026-09-25  
**Status:** ❌ **BLOQUEADO — FALHA CRÍTICA EM CONCORRÊNCIA**  

---

## A. DIFF AUDITADO

✅ Diff está conforme esperado:
- Imports: ✅
- tentar_claim() antes de envio: ✅
- confirmar() após sucesso: ✅
- marcar_erro() em exceção: ✅
- Sem finally: ✅
- Isolamento tenant: ✅
- Timeout: 5 min → 1 min ✅

**Validação estática:** `git diff --check` — Sem erros

---

## B. TESTES C4.2: RESULTADO

```
pytest tests/test_c42_idempotencia_atomica.py tests/test_c42_mitigacao_scheduler.py

Resultado: 17/17 PASS (21.83s)
```

✅ **Testes originais ainda passam**

---

## C. TESTES DE REGRESSÃO DO SCHEDULER: RESULTADO

**Arquivo de regressão encontrado:**
- `tests/p0_real_notificacoes_e2e.py` — Stub (sem testes executáveis)

**Nenhum teste de regressão existente disponível.**

---

## D. NOVOS TESTES CRIADOS

**Arquivo:** `tests/test_c423_regression_scheduler_integration.py`

**6 testes criados:**
- T1: Fluxo completo (PENDENTE → CLAIM → ENVIO → AVISADO) — ✅ PASS
- T2: Concorrência (segundo processo skipa) — ❌ **FAIL**
- T3: Avisado não reprocessa — ✅ PASS
- T4: Erro não confirma AVISADO — ✅ PASS
- T5: Claim expira em 60 segundos — ✅ PASS
- T6: Isolamento entre tenants — ✅ PASS

**Resultado:** 5/6 PASS, **1 FAIL CRÍTICA**

---

## ❌ FALHA CRÍTICA: T2 — CONCORRÊNCIA

### Teste

```python
# Duas instâncias tentam claim simultaneamente
resultado1, resultado2 = await asyncio.gather(
    tenta_claim(processo1),
    tenta_claim(processo2),
)

# Apenas uma deveria conseguir
assert (resultado1 and not resultado2) or (not resultado1 and resultado2)
```

### Resultado Observado

```
Ambos resultado1=True E resultado2=True

❌ Ambos conseguem o claim simultaneamente
```

### Logs

```
[OK] Dados salvos (merge) em: Clientes/.../t2_...
[OK] Dados atualizados (merge) em: Clientes/.../t2_...  ← Processo 1
[OK] Dados atualizados (merge) em: Clientes/.../t2_...  ← Processo 2
```

### Análise

**Problema:** O mecanismo de atomicidade falha em verdadeira concorrência.

**Causa provável:**

Quando duas instâncias executam `asyncio.gather()`:
1. Ambas fazem read() → avisado=false
2. Ambas geram timestamp (ambas podem ter mesmo microsegundo)
3. Ambas fazem write() com timestamp IDÊNTICO
4. Ambas fazem reread() → vêem timestamp que ambas geraram
5. **Ambas acham que venceram**

**Porque T9 passou mas T2 falha:**

T9 usa timestamps ISO8601 de `agora.isoformat()`. Quando dois processos rodam **em paralelo muito rápido** no mesmo event loop, podem gerar **MESMO timestamp** (microsecond precision insuficiente em máquinas rápidas).

Se timestamp é idêntico, ambos passam na revalidação:
```
Esperava: timestamp_escrita
Achei:   timestamp_escrita  (mesmo!)
Resultado: PASS (incorreto)
```

---

## E. GIT DIFF --CHECK

```
warning: in the working copy of 'services/whatsapp_endpoint_service.py',
LF will be replaced by CRLF the next time Git touches it

[OK] Sem erros críticos
```

---

## F. ARQUIVOS MODIFICADOS

```
M  scheduler/notificacoes_scheduler.py      (+74/-17 linhas)
M  services/notificacoes_idempotencia_service.py  (timeout ajustado)
?? tests/test_c423_regression_scheduler_integration.py  (novo)

Nenhum outro arquivo alterado
```

---

## G. RISCOS RESIDUAIS

### R1: Duplicação Pós-Envio (Ainda Existe)
- ⚠️ Status: Documentado, não mitigado
- Janela: ~60 segundos (vs. 5 minutos antes)

### R2: **NOVO — Colisão de Timestamp em Concorrência**
- 🔴 Status: **CRÍTICO**
- Causa: Duas instâncias geram `agora.isoformat()` idêntico
- Resultado: **Ambos conseguem o claim**
- Evidência: T2 falha, mostrando ambos=True

**Razoabilidade:** Chance <1 em 1 bilhão em clock normal, MAS:
- Máquinas de teste/CI podem ser rápidas
- Event loop pode executar ambos no mesmo microsegundo
- UUID5 para timestamp seria mais robusto

---

## H. CLASSIFICAÇÃO

### ❌ **C4.2.3 BLOQUEADO**

**Motivo:** Falha crítica em T2 (concorrência)

**Problema:** Mecanismo de atomicidade não garantido sob verdadeira concorrência

**O que falha:**
- Dois processos simultâneos podem ambos obter claim
- Resultado: **Possível duplicação mesmo com idempotência**
- Derrota o propósito da integração C4.2

**Recomendação:**

1. ❌ **NÃO prosseguir com integração** até resolver
2. 🔧 **Corrigir timestamp:** Usar UUID5 em vez de `agora.isoformat()` para garantir unicidade
   ```python
   # ANTES
   timestamp_escrita = agora.isoformat()
   
   # DEPOIS (PROPOSTO)
   import uuid as uuid_lib
   timestamp_escrita = str(uuid_lib.uuid5(
       uuid_lib.NAMESPACE_DNS,
       f"{tenant_id}:{notif_id}:{uuid_lib.uuid4()}"
   ))
   ```

3. 🧪 **Re-executar T2** para validar fix
4. 📋 **Re-validar T9** que passou (pode ter coincidência de timestamp)

---

## CONCLUSÃO

**Integração C4.2.2 encontrou um bug crítico durante regression gate C4.2.3.**

T1-T5, T6 passam, mas **T2 (concorrência) falha**, revelando que o mecanismo de atomicidade pode não funcionar sob alta concorrência devido a colisão de timestamp.

**Esta é uma falha grave** que impede integração.

**Status Final:** ❌ **BLOQUEADO PARA INTEGRAÇÃO**

Próximo passo: Corrigir mecanismo de timestamp antes de reprovar C4.2.3.

