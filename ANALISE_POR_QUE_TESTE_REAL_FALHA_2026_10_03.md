# 🔍 ANÁLISE — Por Que Teste Passa Mas Teste Real Falha?

**Data:** 2026-10-03  
**Status:** Investigação  
**Questão:** Se `identidade=identidade_p01` está no código e testes unitários passam, por que o teste real falha?

---

## ✅ CONFIRMADO NO CÓDIGO

Verificação mostrou que as mudanças ESTÃO presentes:

```
[RESULTADO] Encontrados 3 callsites com 'identidade=identidade_p01'
  1. Linha 7600 ← ADICIONADO
  2. Linha 10909 ← JÁ EXISTIA
  3. Linha 11406 ← ADICIONADO
```

**Conclusão:** O código está CORRETO. Mudanças foram aplicadas com sucesso.

---

## ❓ POSSÍVEIS RAZÕES PARA FALHA DO TESTE REAL

Se o código está correto mas o teste real falha, o problema é provavelmente **ANTES** de `executar_acao_gpt()`:

### PROBLEMA 1: identidade_p01 está None

**Onde criada:** Linhas 3466-3478 em `router/principal_router.py`

```python
try:
    if tenant_id:
        identidade_p01 = criar_identidade_telegram(
            telegram_id=user_id,
            canal_tenant_id=dono_id,
        )
    else:
        identidade_p01 = criar_identidade_telegram(telegram_id=user_id)
except Exception as e:
    print(f"[P0.1] Erro ao criar IdentidadeContexto: {e}", flush=True)
    identidade_p01 = None  # ← AQUI! Se exception, identidade_p01 = None
```

**Cenário de falha:**
- `criar_identidade_telegram()` falha (exception)
- `identidade_p01` fica como None
- Código passa identidade=None para executar_acao_gpt()
- Resposta fica vazia

**Diagnóstico:**
- Verificar logs de "[P0.1] Erro ao criar IdentidadeContexto"

---

### PROBLEMA 2: tenant_id não está sendo resolvido

**Linha ~3456** (ANTES da criação de identidade):

```python
dono_id = await obter_id_dono(user_id)  # ← Isso falha silenciosamente?
```

Se `obter_id_dono()` retorna None:
- `tenant_id` permanece None
- `identidade_p01 = criar_identidade_telegram(telegram_id=user_id)` (sem tenant)
- Identidade criada sem canal_tenant_id
- Pode não ter dados suficientes

**Diagnóstico:**
- Verificar se `dono_id` está sendo resolvido corretamente
- Log: "[DIAG_TENANT] Tipo:" deveria mostrar CLIENTE ou TENANT

---

### PROBLEMA 3: execução nunca chega em um dos callsites

**Fluxo de decisão:**

```python
if pode_executar_p0 and tem_hora_real(data_hora_check):
    # Callsite linha 7600
    return await executar_acao_gpt(...)
elif pode_executar_p0:
    # Outras respostas
    ...
else:
    # P0 não é executado
    # Fluxo vai para GPT normal
```

**Cenário de falha:**
- Condição `pode_executar_p0` é False
- Fluxo pula AMBOS os callsites que adicionamos
- Vai para fluxo GPT (sem identidade configurada)
- GPT sem identidade = resposta vazia

**Diagnóstico:**
- Verificar logs: "[DEBUG FLOW]" mostra qual caminho foi tomado

---

### PROBLEMA 4: Update ou Context estão None

Se `update` é None:
- `bot.send_message()` falha
- Resposta não é enviada
- Usuário vê vazio

Se `context` é None:
- Funções que usam `context` falham
- `context.user_data` retorna erro
- Resposta fica vazia

**Diagnóstico:**
- Verificar se "[P0.2] ERRO: Nem identidade nem update fornecidos" aparece nos logs

---

### PROBLEMA 5: Firestore está lento ou offline

`crear_identidade_telegram()` pode fazer chamadas a Firestore:

```python
identidade_p01 = criar_identidade_telegram(
    telegram_id=user_id,
    canal_tenant_id=dono_id,  # ← Isso requer resolver dono_id
)
```

Se Firestore está lento:
- Chamada demora >30s
- Timeout
- identidade_p01 = None (na exception handler)

**Diagnóstico:**
- Logs de timeout do Firestore
- Verificar se há retry logic

---

### PROBLEMA 6: Fluxo não é executado no contexto certo

A função `processar_pre_checagem_p0()` pode ser chamada de múltiplos lugares:

1. **Webhook WhatsApp direto** (deve ter Update + Context)
2. **Callback de Telegram** (pode ter diferentes estruturas)
3. **Teste unitário** (mock Update + mock Context)

Se for chamado de um lugar diferente:
- Update pode estar None
- Context pode estar mal formado
- identidade_p01 pode não estar no escopo

**Diagnóstico:**
- Verificar stack trace completo
- Ver onde `processar_pre_checagem_p0()` foi chamado

---

## 🎯 COMO DIAGNOSTICAR O PROBLEMA REAL

### Passo 1: Ativar logs diagnósticos

No código de `processar_pre_checagem_p0()`, adicionar logo após criação de identidade_p01:

```python
print(f"[P0.1] identidade_p01: {identidade_p01}", flush=True)
print(f"[P0.1] identidade_p01 is None: {identidade_p01 is None}", flush=True)
if identidade_p01:
    print(f"[P0.1] identidade_p01.actor_id: {identidade_p01.actor_id}", flush=True)
    print(f"[P0.1] identidade_p01.user_id: {identidade_p01.user_id}", flush=True)
```

### Passo 2: Ativar logs nos callsites

Antes de chamar `executar_acao_gpt()`:

```python
print(f"[P0.CALLSITE] Entrando em executar_acao_gpt", flush=True)
print(f"[P0.CALLSITE] identidade: {identidade_p01}", flush=True)
print(f"[P0.CALLSITE] update: {update}", flush=True)
print(f"[P0.CALLSITE] context: {context}", flush=True)

return await executar_acao_gpt(
    update,
    context,
    "pre_confirmar_agendamento",
    {...},
    identidade=identidade_p01
)
```

### Passo 3: Executar fluxo real

1. Enviar mensagem WhatsApp: "quero corte amanhã as 9"
2. Coletar logs COMPLETOS
3. Procurar por:
   - `[P0.1]` logs
   - `[P0.CALLSITE]` logs
   - `[P0.2] ERRO`
   - `[DIAG FLOW]` para rastrear qual branch foi tomado

### Passo 4: Analisar resultado

**Se logs mostram:**
- `identidade_p01 is None` → Problema 1
- `identidade_p01.user_id None` → Problema 2
- Não chega em `[P0.CALLSITE]` → Problema 3
- `update: None` → Problema 4
- Timeout → Problema 5

---

## 📊 RESUMO

| Hipótese | Probabilidade | Sintoma |
|----------|--------------|---------|
| identidade_p01 = None | ⭐⭐⭐⭐⭐ | ALTA |
| dono_id não resolvido | ⭐⭐⭐⭐ | ALTA |
| Condição pode_executar_p0=False | ⭐⭐⭐ | MÉDIA |
| Update/Context None | ⭐⭐ | BAIXA |
| Firestore timeout | ⭐⭐ | BAIXA |
| Fluxo executado errado | ⭐ | MUITO BAIXA |

---

## ✅ AÇÃO RECOMENDADA

Para descobrir o REAL motivo da falha:

1. **NÃO ALTERE CÓDIGO AINDA**
2. Adicionar os logs diagnósticos acima
3. Executar teste real
4. Coletar e analisar logs
5. Identificar exatamente qual problema está ocorrendo
6. **ENTÃO** implementar correção específica

---

**Próximo passo:** Aguardar que você execute o fluxo real com logs diagnósticos habilitados.

