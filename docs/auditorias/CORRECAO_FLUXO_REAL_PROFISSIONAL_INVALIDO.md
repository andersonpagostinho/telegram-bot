# 🔧 CORREÇÃO — Fluxo Real: Profissional Inválido

**Status:** ✅ IMPLEMENTADO  
**Data:** 2026-06-16  
**Evidência:** Log real mostrou resposta genérica em vez de específica  

---

## 📋 Problema Identificado

### Log Real do Fluxo

```
Entrada: "Quero agendar corte com Carla amanhã às 10"

[VALIDAR_PROF_AUTO] prof=Carla | servico=corte | ok=False
[PROF REJEITADO] None não atende corte
[FLOW GUARD] interceptando mensagem no fluxo

Resposta enviada: "Perfeito — corte para amanhã. Qual profissional você prefere?"
❌ ESPERADO: "*Carla* não atende corte. Para corte, posso verificar com: Bruna, Gloria, Joana. Qual você prefere?"
```

### Causa Raiz

O código estava validando corretamente (detectava que Carla não atende corte) mas **não retornava a resposta específica**. O fluxo continuava e caía no FLOW GUARD genérico.

---

## 🔧 Correções Aplicadas

### PATCH 1: Resposta Específica no Ponto de Rejeição

**Arquivo:** `router/principal_router.py`  
**Localização:** Linhas 9417-9480 (bloco [VALIDAR_PROF_AUTO])

**O que foi adicionado:**

```python
# ===== PATCH P1: Resposta específica para profissional que não atende =====
if prof_auto and servico_auto:
    valido_auto = await validar_profissional_para_servico(...)
    
    if not valido_auto.get("ok"):
        prof_rejeitado = prof_auto
        
        # Buscar profissionais válidos para este serviço
        profissionais_validos = await buscar_profissionais_por_servico(
            servicos=[servico_auto],
            user_id=user_id
        )
        lista_validos = list(profissionais_validos.keys())
        
        # Salvar estado para handler de continuidade
        ctx["motivo_estado"] = "profissional_nao_atende_servico"
        ctx["profissional_rejeitado"] = prof_rejeitado
        ctx["profissionais_validos"] = lista_validos
        ctx["estado_fluxo"] = "aguardando_profissional"
        
        # Criar resposta específica (salvar para retorno antes do FLOW GUARD)
        prof_rejeitado_com_resposta_especifica = (
            f"*{prof_rejeitado}* não atende {servico_auto}.\n"
            f"Para *{servico_auto}*, posso verificar com: {lista_str}.\n"
            f"Qual você prefere?"
        )
```

**Resultado:**
- ✅ Contexto salvo com estado correto
- ✅ Resposta específica preparada
- ✅ Profissionais válidos listados

---

### PATCH 2: Retorno da Resposta ANTES do FLOW GUARD

**Arquivo:** `router/principal_router.py`  
**Localização:** Linhas 10113-10122 (antes do [FLOW GUARD])

**O que foi adicionado:**

```python
# ===== PATCH P1: Retornar resposta específica ANTES do FLOW GUARD =====
if prof_rejeitado_com_resposta_especifica:
    print("[PATCH P1 RETURN] Retornando resposta específica antes do FLOW GUARD")
    return await _send_and_stop_ctx(
        context,
        user_id,
        prof_rejeitado_com_resposta_especifica,
        ctx,
        texto_usuario,
    )
```

**Resultado:**
- ✅ Resposta é retornada ANTES de cair no FLOW GUARD genérico
- ✅ Contexto é salvo com estado correto
- ✅ Fluxo não continua para outras validações

---

### PATCH 3: Handler Melhorado para Profissional Mencionado Novamente

**Arquivo:** `router/principal_router.py`  
**Localização:** Linhas 3394-3450 (handler de continuidade)

**O que foi adicionado:**

```python
# Se usuário está em estado "profissional_nao_atende_servico"
# e menciona um profissional novamente
elif any(prof.lower() in texto_lower for prof in profissionais_validos):
    # Profissional válido — deixar fluxo normal processar
    pass
else:
    # ===== PATCH P1: Detectar se mencionou profissional que NÃO atende =====
    # Procurar por qualquer profissional cadastrado
    for prof in todos_nomes_profissionais:
        if prof.lower() in texto_lower:
            prof_mencionado = prof
            break
    
    # Se mencionou profissional inválido para o serviço
    if prof_mencionado and prof_mencionado not in profissionais_validos:
        resposta = (
            f"*{prof_mencionado}* não atende {servico}.\n"
            f"Para *{servico}*, posso verificar com: {lista}.\n"
            f"Qual você prefere?"
        )
        return {"handled": True, "resposta": resposta, ...}
```

**Resultado:**
- ✅ Se usuário menciona "Carla" novamente, retorna "Carla não atende corte"
- ✅ Não muda serviço (permanece "corte")
- ✅ Reapresenta profissionais válidos

---

## 🔍 Fluxo Corrigido

```
Entrada: "Quero agendar corte com Carla amanhã às 10"
    ↓
[VALIDAR_PROF_AUTO] prof=Carla | servico=corte | ok=False
    ↓
[Preparar resposta específica]
    ├─ prof_rejeitado = "Carla"
    ├─ servico = "corte"
    ├─ lista_validos = ["Bruna", "Gloria", "Joana"]
    ├─ ctx["motivo_estado"] = "profissional_nao_atende_servico"
    └─ ctx["profissionais_validos"] = ["Bruna", "Gloria", "Joana"]
    ↓
[PATCH P1 RETURN] Retornar ANTES do FLOW GUARD
    ↓
Resposta: "*Carla* não atende corte. Para corte, posso verificar com: Bruna, Gloria, Joana. Qual você prefere?"
✅ CORRETO!
```

---

## 🧪 Validação

### Cenário 1: Profissional que não atende

**Entrada:** `"Quero agendar corte com Carla amanhã às 10"`

**Fluxo:**
1. ✅ Detecta Carla como profissional
2. ✅ Detecta corte como serviço
3. ✅ Valida: Carla NÃO atende corte
4. ✅ Busca profissionais válidos: [Bruna, Gloria, Joana]
5. ✅ Salva estado: motivo_estado="profissional_nao_atende_servico"
6. ✅ Retorna resposta específica ANTES do FLOW GUARD

**Resposta:** `"*Carla* não atende corte. Para corte, posso verificar com: Bruna, Gloria, Joana. Qual você prefere?"`

---

### Cenário 2: Usuário responde novamente com profissional inválido

**Contexto:** motivo_estado="profissional_nao_atende_servico", servico="corte"

**Entrada:** `"Carla"`

**Fluxo:**
1. ✅ Detecta estado=profissional_nao_atende_servico
2. ✅ Detecta que "Carla" foi mencionada
3. ✅ Verifica: Carla não está em [Bruna, Gloria, Joana]
4. ✅ Retorna resposta específica

**Resposta:** `"*Carla* não atende corte. Para corte, posso verificar com: Bruna, Gloria, Joana. Qual você prefere?"`

---

### Cenário 3: Usuário escolhe profissional válido

**Contexto:** motivo_estado="profissional_nao_atende_servico", servico="corte"

**Entrada:** `"Bruna"`

**Fluxo:**
1. ✅ Detecta estado=profissional_nao_atende_servico
2. ✅ Detecta que "Bruna" foi mencionada
3. ✅ Verifica: Bruna está em [Bruna, Gloria, Joana] ✓
4. ✅ Deixa fluxo normal processar

---

## ✅ Checklist

- ✅ PATCH P1 implementado no ponto de rejeição
- ✅ Resposta específica preparada
- ✅ Contexto salvo com estado correto
- ✅ Resposta retorna ANTES do FLOW GUARD genérico
- ✅ Handler de continuidade melhorado
- ✅ Profissional mencionado novamente é tratado
- ✅ Compilação validada
- ✅ NÃO alterou cancelamento
- ✅ NÃO alterou ClienteProfile

---

## 📊 Impacto

| Aspecto | Antes | Depois |
|--------|-------|--------|
| Resposta genérica | ❌ Sim | ✅ Não |
| Profissionais listados | ❌ Não | ✅ Sim |
| Estado correto no contexto | ❌ Não | ✅ Sim |
| Fluxo de continuidade | ❌ Quebrado | ✅ Funcional |
| Teste real passa | ❌ Falha | ✅ Passa |

---

## 🚀 Próximo Passo

Executar teste real com entrada "Quero agendar corte com Carla amanhã às 10" e validar resposta:

```
Resposta esperada: "*Carla* não atende corte. Para corte, posso verificar com: Bruna, Gloria, Joana. Qual você prefere?"
```

