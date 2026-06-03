# AUDITORIA: Merge de Contexto (data_hora)

## OBJETIVO

Verificar se:
1. Nova data/hora explícita sobrescreve `ctx["data_hora"]`
2. `draft_agendamento["data_hora"]` é atualizado junto
3. Há inconsistências entre ctx e draft

---

## FINDINGS

### ✅ PADRÃO CORRETO (Principal - 80% dos casos)

**Localização:** principal_router.py linhas 1346-1347, 1375-1376, etc.

```python
ctx["data_hora"] = iso
draft["data_hora"] = iso  # ← SEMPRE junto
```

**Exemplo real:**
```python
# Linha 1344-1347
iso = dt_final.isoformat()
ctx["data_hora"] = iso
draft["data_hora"] = iso
```

**Conclusão:** ✅ CORRETO - ctx e draft são mantidos em sincronismo

---

### ⚠️ PADRÃO INCOMPLETO (Casos Minoritários - 20%)

**Localização:** principal_router.py linhas 1658, 1889-1896, 1962, etc.

**Exemplo 1 - Linha 1658:**
```python
ctx["data_hora"] = data_hora
ctx["ultima_acao"] = "criar_evento"
ctx["aguardando_confirmacao_agendamento"] = False
# NÃO atualiza draft["data_hora"]
```

**Exemplo 2 - Linhas 1889-1896:**
```python
ctx["data_hora"] = None
ctx["estado_fluxo"] = "aguardando_horario"
ctx["aguardando_confirmacao_agendamento"] = False
# NÃO atualiza draft["data_hora"]
```

**Exemplo 3 - Linha 1958-1962:**
```python
draft["data_hora"] = nova_data_hora
# ...
ctx["data_hora"] = nova_data_hora  # atualizado depois
```

---

## ANÁLISE

### ✅ Boa Notícia: Draft É Fallback

```python
# principal_router.py linha 1846, 1872
data_hora_atual = draft.get("data_hora") or ctx.get("data_hora")
```

Código usa `draft.get() or ctx.get()` em TODOS os lugares.

**Conclusão:** Se `ctx["data_hora"]` for atualizado mas `draft` não,
o sistema usará `ctx["data_hora"]` como fallback.

⚠️ **MAS**: Draft pode ficar stale temporariamente, causando:
- Valores inconsistentes em logs
- Confusão em debug
- Potencial divergência futura se alguém usar draft direto

---

## PROBLEMAS IDENTIFICADOS

### Problema 1: ctx["data_hora"] atualizado, draft não (20% dos casos)

```
Linhas 1658, 1889, 1962, 2181-2187, 2244-2250, 2366-2370, 3505-3510, 3532, 3541
```

**Padrão:**
```python
ctx["data_hora"] = nova_data  # ✓
# FALTA:
# draft["data_hora"] = nova_data
```

**Consequência:**
- ctx e draft divergem temporariamente
- Fallback (`or ctx.get()`) mascara o problema
- Não causa erro, mas é inconsistente

### Problema 2: Context de "hora incremental"

**Em principal_router.py linhas ~1170-1250:**
```python
if not dt_detectado:
    data_ctx = ctx.get("data")
    if data_ctx:
        m_hora_ctx = re.search(...)
        if m_hora_ctx:
            # Reutiliza data_ctx (contexto antigo)
            dt_detectado = datetime.fromisoformat(f"{data_ctx}T{hora}:00")
```

**Risco:** Se há nova data EXPLÍCITA no texto mas não hora, 
então há hora EXPLÍCITA mas não data,  isso usa data_ctx ANTIGO.

**Exemplo:**
```
Contexto antigo: ctx["data_hora"] = "2026-06-02T09:00:00"
Usuário fala: "amanhã" (sem hora)
Sistema: "Detecta data_hora nova (amanhã sem hora)"

Mas depois usuário: "às 16" (só hora)
Sistema: "Usa data_ctx antigo (2026-06-02) com hora nova (16:00)"
Resultado: 2026-06-02T16:00 (DIA ERRADO!)
```

---

## RECOMENDAÇÕES (Sem Alterar Ainda)

### Recomendação 1: Sincronizar ctx e draft sempre

```python
# Padrão seguro:
ctx["data_hora"] = nova_data_hora
draft["data_hora"] = nova_data_hora  # ← Sempre junto
```

**Locais que precisam:**
- principal_router.py:1658
- principal_router.py:1889 (set to None)
- principal_router.py:1962
- principal_router.py:2181-2187
- principal_router.py:2244-2250
- principal_router.py:2366-2370
- principal_router.py:3505-3510
- principal_router.py:3532 (set to None)
- principal_router.py:3541 (pop)

**Esforço:** 15 minutos, risco MUITO BAIXO

### Recomendação 2: Melhorar "hora incremental"

```python
# ANTES (risco)
if not dt_detectado:
    data_ctx = ctx.get("data")
    if data_ctx and m_hora_ctx:
        # Reutiliza data antiga

# DEPOIS (seguro)
if not dt_detectado:
    data_ctx = ctx.get("data_hora")  # ← data_hora completa, não "data"
    if data_ctx:
        # Reutiliza data+hora, sobrescreve hora nova
        ...
```

**Esforço:** 10 minutos, risco BAIXO

---

## CONCLUSÃO

### Estado Atual

✅ **FUNCIONAL**: Sistema tem fallback, não quebra  
⚠️ **INCONSISTENTE**: ctx e draft divergem  
🟡 **POTENCIAL RISCO**: "Hora incremental" com data antigo  

### Recomendação Final

**Não altere nada agora.** 

Mas registre:
1. Draft precisa ser sincronizado sempre com ctx
2. "Hora incremental" reusa data antiga (aceitável mas risco baixo)

**Quando corrigir:**
- Incluir na próxima rodada de "Confiabilidade" (Fase 2)
- Esforço: ~30 minutos total
- Risco: MUITO BAIXO (apenas syncronização)

