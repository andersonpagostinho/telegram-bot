# 🎯 Análise de Pontos — PATCH P0 Respostas Óbvias e Testes Negativos

**Data:** 2026-06-16  
**Objetivo:** Localizar e documentar exatamente onde as mudanças P0 serão necessárias

---

## 📍 PONTO 1: Pergunta Sim/Não Sem Handler

**Arquivo:** `router/principal_router.py`  
**Linhas:** 1847-1868  
**Tipo:** Pergunta de sim/não sem handler explícito

### Código Atual
```python
# =========================================================
# 🔥 VALIDAR COMPATIBILIDADE ANTES DE CONFLITO
# =========================================================
valido = await validar_profissional_para_servico(
    dono_id=dono_id,
    profissional=prof,
    servico=servico
)

print(f"[PRE-CHECK COMPATIBILIDADE] prof={prof} | servico={servico} | ok={valido.get('ok')}", flush=True)
if not valido.get("ok"):
    draft = ctx.get("draft_agendamento") or {}
    ctx["draft_agendamento"] = draft
    ctx["servico"] = servico
    ctx["data_hora"] = data_hora
    await salvar_contexto_temporario(user_id, ctx)
    return await _send_and_stop(
        context,
        user_id,
        (
            f"❌ {prof} não atende {servico}.\n\n"
            "Quer escolher outra profissional?"  # ← PERGUNTA SEM HANDLER
        ),
        parse_mode=None
    )
```

### Problema
- ✅ Valida se profissional atende serviço
- ❌ Mas faz pergunta: "Quer escolher outra profissional?"
- ❌ Não há handler explícito para "sim" ou "não" naquele contexto
- ❌ Violada a regra: "Se faz pergunta sim/não, deve existir handler explícito"

### Solução Necessária
Remover pergunta de sim/não. Listar opções válidas imediatamente:
```python
# Buscar profissionais que ATENDEM esse serviço
profissionais_validos = await buscar_profissionais_por_servico(
    servicos=[servico],
    user_id=user_id
)

profissionais_nomes = ", ".join(profissionais_validos.keys()) if profissionais_validos else "ninguém"

resposta = (
    f"❌ *{prof}* não atende {servico}.\n"
    f"Para *{servico}*, posso verificar com: {profissionais_nomes}.\n"
    f"Qual você prefere?"
)

# Salvar contexto com motivo
ctx["motivo_estado"] = "profissional_nao_atende_servico"
ctx["profissional_rejeitado"] = prof
ctx["profissionais_validos"] = list(profissionais_validos.keys())
ctx["draft_agendamento"] = {
    "servico": servico,
    "data_hora": data_hora,
    "profissional": None
}
ctx["estado_fluxo"] = "aguardando_profissional"

await salvar_contexto_temporario(user_id, ctx)
return await _send_and_stop(context, user_id, resposta)
```

---

## 📍 PONTO 2: Draft Contaminado com Serviço Antigo

**Arquivo:** `router/principal_router.py`  
**Linhas:** 1560-1568 (aproximadamente)  
**Tipo:** Sobrescrita de draft.servico com valor antigo

### Contexto
```python
# Linha ~1558-1570
if ctx.get("servico_antigo") or draft.get("servico"):
    servico_do_draft = draft.get("servico") or ctx.get("servico_antigo")
    # ... usa servico_do_draft como fallback
    draft["servico"] = servico_do_draft  # ← SOBRESCRITA
```

### Problema
- Se mensagem atual menciona "corte" explicitamente
- Mas draft antigo tem "botox capilar"
- Sistema usa "botox capilar" do draft antigo
- ❌ Mensagem atual é ignorada

### Solução Necessária
Priorizar serviço da mensagem atual sobre draft antigo:

```python
# Ordem de prioridade:
# 1. Serviço mencionado AGORA na mensagem
# 2. Serviço em draft (se nenhum novo foi mencionado)
# 3. Serviço em contexto antigo (fallback)

if servico_mencionado_agora:
    draft["servico"] = servico_mencionado_agora
    ctx["servico"] = servico_mencionado_agora
elif draft.get("servico"):
    # Manter draft existente
    pass
else:
    # Fallback para contexto antigo
    draft["servico"] = ctx.get("servico_antigo")
```

---

## 📍 PONTO 3: Serviço Não Existe — Resposta Genérica

**Arquivo:** `handlers/acao_handler.py`  
**Linhas:** 163-176  
**Tipo:** Serviço não encontrado retorna resposta genérica

### Código Atual
```python
if not servico_normalizado:
    if servicos_set:
        servicos_formatados = "\n".join([f"• {s.capitalize()}" for s in sorted(servicos_set)])
        return (
            "Não entendi o serviço. Você pode escolher um destes:\n\n"
            f"{servicos_formatados}\n\n"
            "Qual você deseja?"
        )
    return "Não entendi o serviço. Qual serviço você deseja agendar?"
```

### Problema
- ❌ "Não entendi o serviço" é genérico
- ❌ Não menciona QUAL serviço o usuário pediu
- ✅ Lista serviços disponíveis (bom)
- ❌ Viola manual seção 7.4: "informe isso claramente"

### Solução Necessária
Ser específico sobre qual serviço foi pedido:

```python
# Tentar extrair o que usuário pediu
servico_mencionado = extrair_servico_mencionado_do_texto(mensagem, servicos_set)

if not servico_normalizado:
    if servico_mencionado:
        # Ser específico
        servicos_formatados = "\n".join([f"• {s.capitalize()}" for s in sorted(servicos_set)])
        return (
            f"Não encontrei *{servico_mencionado}* no catálogo.\n"
            f"Posso te mostrar os serviços disponíveis:\n\n"
            f"{servicos_formatados}\n\n"
            "Qual você prefere?"
        )
    else:
        # Resposta genérica (como agora)
        return "Não entendi o serviço. Qual você deseja agendar?"
```

---

## 📍 PONTO 4: Profissional Não Existe — Sem Informação Explícita

**Arquivo:** `handlers/acao_handler.py`  
**Linhas:** 382-391 (atual, após patch P0)  
**Tipo:** Profissional não encontrado responde genericamente

### Código Atual (Após Patch P0)
```python
# Procura em disponiveis
profissional_escolhido = None
for nome in disponiveis:
    if unidecode(nome.lower()) in texto_normalizado:
        profissional_escolhido = nome
        break

# Patch P0 tenta procurar em TODOS
if not profissional_escolhido:
    # ... procura em todos_profissionais
    if profissional_mencionado:
        if profissional_mencionado not in prof_que_atendem:
            # Informa que não atende (BORA IMPLEMENTADO)
            return f"*{profissional_mencionado}* não atende {servico}..."

# Se chegou aqui, não encontrou em lugar nenhum
if not profissional_escolhido:
    return "Qual profissional você prefere? (ex: Joana, Bruna, Carla...)"  # ← GENÉRICO
```

### Problema
- ✅ Se profissional não existe, responde genericamente
- ❌ Não menciona QUAL profissional o usuário pediu
- ❌ Exemplo "Carla..." é inapropriado se Carla foi mencionada

### Solução Necessária
Ser específico sobre qual profissional foi pedido:

```python
# Se procuramos em TODOS e não encontramos
profissional_mencionado_mas_nao_existe = extrair_nome_profissional_do_texto(texto_normalizado, todos_profissionais)

if not profissional_escolhido:
    if profissional_mencionado_mas_nao_existe:
        # Ser específico
        servico_atual = sessao.get("servico", "esse serviço")
        lista = ", ".join(disponiveis) if disponiveis else "ninguém"
        return (
            f"Não encontrei *{profissional_mencionado_mas_nao_existe}* entre os profissionais.\n"
            f"Para *{servico_atual}*, posso verificar com: {lista}.\n"
            f"Qual você prefere?"
        )
    else:
        # Resposta genérica (como agora)
        return "Qual profissional você prefere? (ex: Joana, Bruna, Carla...)"
```

---

## 📍 PONTO 5: Resposta "Sim" Sem Handler (Estado motivo_estado)

**Arquivo:** Novo estado em contexto  
**Localização:** Será criado quando PONTO 1 é corrigido  
**Tipo:** Handler para "sim" quando motivo_estado = "profissional_nao_atende_servico"

### Contexto
```python
ctx["motivo_estado"] = "profissional_nao_atende_servico"
ctx["profissionais_validos"] = ["Bruna", "Gloria", "Joana"]
```

Quando usuário responde "Sim", o sistema deve:

### Solução Necessária
Criar handler explícito:

```python
if ctx.get("motivo_estado") == "profissional_nao_atende_servico":
    if texto_usuario.lower() in ["sim", "sim", "ok", "ok", "tudo bem"]:
        # "Sim" apenas reapresenta opções
        profissionais_validos = ctx.get("profissionais_validos", [])
        servico = ctx.get("servico") or ctx.get("draft_agendamento", {}).get("servico")
        
        if not profissionais_validos:
            return "Algo deu errado. Vamos começar de novo?"
        
        lista = ", ".join(profissionais_validos)
        return f"Pode escolher: {lista}."
    
    elif texto_usuario.lower() in ["não", "nao", "desistir", "cancelar"]:
        # Limpar motivo_estado
        ctx.pop("motivo_estado", None)
        ctx.pop("profissional_rejeitado", None)
        ctx.pop("profissionais_validos", None)
        ctx["estado_fluxo"] = "idle"
        
        await salvar_contexto_temporario(user_id, ctx)
        return "Tudo bem. Posso ajudar com outra coisa?"
    
    elif qualquer_nome_profissional_valido_em(texto_usuario, profissionais_validos):
        # Usuário escolheu um profissional válido
        # Processar normalmente
        # (resto do fluxo de agendamento)
        pass
```

---

## 📊 Resumo de Pontos

| Ponto | Arquivo | Linhas | Tipo | Problema | Solução |
|-------|---------|--------|------|----------|---------|
| 1 | router/principal_router.py | 1847-1868 | Pergunta sim/não | Sem handler | Listar opções, salvar motivo_estado |
| 2 | router/principal_router.py | ~1560 | Draft contamina | Serviço antigo sobrescreve | Priorizar mensagem atual |
| 3 | handlers/acao_handler.py | 163-176 | Resposta genérica | Não menciona serviço | Ser específico com serviço mencionado |
| 4 | handlers/acao_handler.py | 382-391 | Resposta genérica | Não menciona profissional | Ser específico com profissional mencionado |
| 5 | Novo (contexto) | N/A | Handler novo | Sem handler para "sim" | Criar handler explícito com motivo_estado |

---

## ✅ Arquivos Impactados

- ✅ `router/principal_router.py` (2 pontos)
- ✅ `handlers/acao_handler.py` (2 pontos)
- ✅ Contexto (1 novo estado/motivo)
- ❌ `services/profissional_service.py` (reutilizar, não modificar)
- ❌ Cancelamento (não mexer)
- ❌ ClienteProfile (não mexer)

---

## 📝 Plano de Implementação

**Fase 1:** Corrigir PONTO 1 (principal_router.py:1847-1868)
- Remover pergunta "Quer escolher?"
- Listar opções válidas imediatamente
- Salvar motivo_estado

**Fase 2:** Corrigir PONTO 3 (acao_handler.py:163-176)
- Ser específico sobre serviço não encontrado
- Similar ao PONTO 1 mas para serviços

**Fase 3:** Corrigir PONTO 4 (acao_handler.py:382-391)
- Ser específico sobre profissional não encontrado

**Fase 4:** Implementar PONTO 5 (novo handler)
- Handler para "sim" após profissional inválido
- Testar continuidade de fluxo

**Fase 5:** Validar PONTO 2 (revisão)
- Verificar se serviço antigo contamina
- Se sim, priorizar serviço atual

---

**Status:** ANÁLISE COMPLETA  
**Pronto para implementação:** SIM
