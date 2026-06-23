# LOTE 4F — WRAPPER executar_acao_gpt_resultado

**Data:** 2026-06-22  
**Escopo:** Criar wrapper que normaliza retorno bool→dict (sem alterar função original)  
**Objetivo:** Resolver cenário 06 (confirmação pendente) sem alterar contrato histórico de `executar_acao_gpt`

---

## IMPLEMENTAÇÃO

### 1. Wrapper Criado

**Arquivo:** `services/gpt_executor.py` (linhas 170-217)

```python
async def executar_acao_gpt_resultado(update: Update, context: ContextTypes.DEFAULT_TYPE, acao: str, dados: dict):
    """
    Wrapper que normaliza o retorno de executar_acao_gpt para sempre ser dict.
    
    Retorno normalizado:
    {
        "ok": bool,           # True se sucesso, False se falha
        "acao": str,          # Nome da ação executada
        "resultado": any,     # Resultado específico da ação
        "erro": str | None,   # Mensagem de erro se houver
        "tipo_erro": str | None  # Tipo/classe do erro
    }
    """
    resultado = await executar_acao_gpt(update, context, acao, dados)

    # Se já é dict, garantir que tem chave "ok"
    if isinstance(resultado, dict):
        if "ok" not in resultado:
            resultado["ok"] = resultado.get("sucesso", True)
        return resultado

    # Se é bool, normalizar para dict
    if isinstance(resultado, bool):
        return {
            "ok": resultado,
            "acao": acao,
            "resultado": resultado,
            "erro": None if resultado else "executar_acao_gpt_retornou_false",
            "tipo_erro": None if resultado else "retorno_false"
        }

    # Fallback: algo inesperado
    return {
        "ok": False,
        "acao": acao,
        "resultado": resultado,
        "erro": f"tipo_retorno_inesperado: {type(resultado).__name__}",
        "tipo_erro": "tipo_retorno_desconhecido"
    }
```

---

### 2. Uso em Router

**Arquivo:** `router/principal_router.py`

**Import atualizado (linha 9):**
```python
from services.gpt_executor import executar_acao_gpt, executar_acao_gpt_resultado
```

**Uso (linha 4687):**
```python
# Antes:
return await executar_acao_gpt(update, context, "criar_evento", dados_exec)

# Depois:
return await executar_acao_gpt_resultado(update, context, "criar_evento", dados_exec)
```

---

### 3. Validação de Sintaxe

✅ **Validação realizada:**
```
python -m py_compile services/gpt_executor.py
python -m py_compile router/principal_router.py
```

Resultado: **OK**

---

## RESULTADO DE TESTES

### Teste Cenário 06: ❌ FALHA (estado de confirmação não foi limpado)

**Status:** FAIL  
**Motivo:** Confirmação não foi processada

**Observações:**
- Wrapper foi chamado corretamente
- `executar_acao_gpt` retornou `True` (bool)
- Wrapper normalizou para dict com chaves esperadas
- add_evento_por_gpt foi chamado
- ❌ Evento não foi criado
- ❌ confirmacao_pendente não foi removida do estado
- `resposta_enviada` vazia

**Estado após cenário 06:**
```json
{
  "evento_criado": false,
  "confirmacao_pendente": true,
  "intencao_conversacional": "confirmacao_agendamento",
  "dados_confirmacao_agendamento": {...}
}
```

---

### Teste Cenário 07: ✅ PASS (negação detectada)

**Status:** PASS  
**Motivo:** Negação embutida detectada, draft limpado

Sem regressão.

---

### Teste Baseline: 4/13 PASS

**Resultado:** 4 cenários passaram, 9 falharam

Nota: Cenário 06 agora falha por razão diferente:
- ❌ **Antes (LOTE 4E):** Erro `'bool' object has no attribute 'get'`
- ❌ **Depois (LOTE 4F):** "Confirmação não foi processada" (tipo mismatch resolvido, mas lógica de criação falha)

---

## ANÁLISE DO PROBLEMA

### Tipo Mismatch: ✅ RESOLVIDO

O wrapper normalizou o retorno de `executar_acao_gpt` corretamente:
- `True` (bool) → `{"ok": True, "acao": "criar_evento", ...}` (dict)
- Test pode fazer `.get()` sem erro

### Criação de Evento: ❌ NÃO RESOLVIDO

O evento não está sendo criado por uma razão fora do escopo do wrapper:

**Hipóteses:**
1. **Data/hora não normalizada:** Input `"amanhã 14:00"` pode não estar sendo convertida para formato ISO corretamente
2. **add_evento_por_gpt silenciosamente falha:** Não há logs de erro ou sucesso após a chamada
3. **Contexto não é preservado:** dados_exec pode estar incompleto

**Evidência:**
- Log mostra "Executando add_evento_por_gpt" (função foi chamada)
- Nenhum log subsequente de sucesso ou erro
- Evento não aparece em Firestore
- Estado permanece com `confirmacao_pendente=true` após chamada

---

## CONTRATO DO WRAPPER

### Entrada
```
update: Update
context: ContextTypes.DEFAULT_TYPE
acao: str
dados: dict
```

### Saída (SEMPRE dict)
```json
{
  "ok": bool,           # True: sucesso, False: falha
  "acao": str,          # Nome da ação que foi executada
  "resultado": any,     # Resultado específico (pode ser bool, dict, etc)
  "erro": str | None,   # Mensagem de erro ou None
  "tipo_erro": str | None  # Tipo do erro ou None
}
```

### Garantias
- ✅ Nunca retorna bool
- ✅ Sempre retorna dict
- ✅ Sempre contém chave "ok"
- ✅ Compatível com `.get()` method
- ✅ Mantém função original intacta (não altera nenhum return)

---

## DÉBITO TÉCNICO REGISTRADO

```markdown
**Contrato Histórico vs Novo:**

- executar_acao_gpt:   mantém retorno bool (18 returns True/False)
- executar_acao_gpt_resultado: normaliza para dict (wrapper)

Situação:
- 3 handlers históricos usam executar_acao_gpt diretamente (esperam bool)
- Novo fluxo confirmação pendente usa wrapper (espera dict)
- Função original NÃO foi modificada

Débito técnico:
- Dois contratos coexistindo (bool e dict)
- Wrapper é ponte transitória
- Futura migração para unificar retornos (LOTE 4G/4H)

Status:
- Tipo mismatch RESOLVIDO (wrapper normaliza)
- Criação de evento PENDENTE (problema em add_evento_por_gpt, não no wrapper)
```

---

## PRÓXIMOS PASSOS

### Investigação Necessária (fora do escopo LOTE 4F)

**Problema:** add_evento_por_gpt está sendo chamado, mas não cria evento

**O que investigar:**
1. Logs de add_evento_por_gpt (procurar sucesso/erro)
2. Conversão de data "amanhã 14:00" → ISO
3. Validação de dados_exec
4. Firestore: confirmação_pendente está sendo clean
up?

**Recomendação:** LOTE 4G para investigar add_evento_por_gpt flow

---

## VALIDAÇÃO

| Aspecto | Status | Nota |
|---------|--------|------|
| Wrapper criado | ✅ OK | Normaliza bool→dict |
| Router atualizado | ✅ OK | Usa wrapper em crear_evento |
| Sintaxe validada | ✅ OK | sem erros |
| Tipo mismatch resolvido | ✅ OK | Test pode fazer `.get()` |
| Cenário 07 regressão | ✅ PASS | Sem quebra |
| Cenário 06 evento criado | ❌ FAIL | Problema em add_evento_por_gpt |
| Cenário 06 confirmacao limpada | ❌ FAIL | Problema em add_evento_por_gpt |

---

## CONCLUSÃO

**LOTE 4F alcançou objetivo parcial:**

✅ **Wrapper normaliza retorno bool→dict com sucesso**
- Tipo mismatch resolvido
- Test cenários podem usar `.get()` sem erro
- Função original intacta (débito técnico mínimo)

❌ **Evento ainda não é criado**
- Problema não é no contrato de retorno (wrapper ok)
- Problema é em `add_evento_por_gpt` ou pré-condições
- Fora do escopo do wrapper

**Recomendação:** LOTE 4G para investigar por que add_evento_por_gpt não cria evento mesmo sendo chamado.

---

## ARQUIVOS ENTREGUES

- services/gpt_executor.py (wrapper adicionado)
- router/principal_router.py (import + uso do wrapper)
- docs/auditorias/LOTE_4F_WRAPPER_EXECUTAR_ACAO_GPT_RESULTADO.md (este documento)

---

**Status:** Wrapper implementado e funcionando. Próxima investigação necessária em add_evento_por_gpt.

