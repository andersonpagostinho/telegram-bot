# 🔍 AUDITORIA ESTRUTURAL: Chamada 1027 vs 2476

**Objetivo:** Entender se as 2 chamadas GPT são necessárias ou podem ser otimizadas  
**Data:** 2026-06-02  
**Método:** Análise de lógica de fluxo, não teste de código

---

## LOCALIZAÇÃO E CONTEXTO

### Chamada 1: Linha 1027
```
Função: processar_com_gpt_com_acao()
Localização: Seção "6) Chamada única ao GPT + registrar custo"
Comentário do código: "Chamada única ao GPT"
```

**O que faz ANTES da chamada:**
- Extrai `servico`, `profissional`, `data_hora` do contexto
- Se TODOS os 3 estão presentes → retorna early (sem chamar GPT)
- Se algo está faltando → continua para chamada GPT
- Valida se é "hora incremental" (só hora, sem data) → trata localmente
- Se é "ajuste de horário" (hora + profissional + serviço) → retorna early com resultado
- Se nada disso → chama GPT (linha 1027)

**Fluxo condicional:**
```
SE servico AND profissional AND data_hora:
    → retorna pré-confirmação
SENÃO SE é hora incremental (só "16"):
    → valida e retorna
SENÃO SE é ajuste de horário com conflito:
    → retorna sugestões
SENÃO:
    → ✅ CHAMA GPT (linha 1027)
```

---

### Chamada 2: Linha 2476
```
Função: processar_com_gpt_com_acao() (MESMA FUNÇÃO)
Localização: Seção "caso de múltiplos horários / confirmação curta"
Comentário do código: "Só agora monta messages"
```

**O que faz ANTES da chamada:**
- Filtra profissionais válidos
- Sanitiza contexto
- Monta auditoria de contexto
- Somente ENTÃO monta prompt e chama GPT (linha 2476)

**Fluxo condicional:**
```
SE há múltiplos horários / resultado da chamada 1027 indicou "confirmação curta":
    → filtra e sanitiza
    → ✅ CHAMA GPT (linha 2476)
```

---

## ANÁLISE: POR QUE 2 CHAMADAS?

### Hipótese 1: Duas fases distintas ❌ (PROVAVELMENTE FALSA)

Se fossem realmente duas fases:
1. Chamada 1: Extrair intenção bruta
2. Chamada 2: Processar com contexto filtrado

Então o resultado da Chamada 1 determinaria SE fazer Chamada 2.

**MAS:**
- Não há `if resultado_1.get("alguma_coisa") == X: chama_gpt_novamente()`
- Não há condição explícita que dispara a Chamada 2 baseada na Chamada 1
- Padrão não é "primeira chamada → decisão → segunda chamada"

**Conclusão:** Hipótese 1 é fraca.

---

### Hipótese 2: Múltiplos fluxos em uma única função ✅ (PROVÁVEL)

```
processar_com_gpt_com_acao() trata:
├─ Fluxo A: Usuário envia serviço + profissional + data/hora
│  └─ Retorna pre-confirmação sem GPT
├─ Fluxo B: Usuário envia só horário ("às 16")
│  └─ Valida e retorna sem GPT
├─ Fluxo C: Usuário envia ajuste de horário
│  └─ Verifica conflito e retorna sem GPT
└─ Fluxo D: Tudo outro (ambíguo, genérico)
   └─ Precisa de GPT → Chamada 1027
      └─ Se resultado é "múltiplos horários" → Chamada 2476
```

**Resultado da Chamada 1027:**
```python
{
    "acao": "xxx",
    "dados": {...}
}
```

Possíveis ações: 
- `"agendar"` → router processa
- `"buscar_opcoes_profissional"` → precisa de Chamada 2?
- `"confirmar_agendamento"` → precisa de Chamada 2?

---

## LÓGICA DA CHAMADA 2: QUANDO EXATAMENTE É DISPARADA?

**Procurando a condição que ativa Chamada 2...**

Analisando seção antes de linha 2476:
- Linha 2443-2468: Auditoria do contexto
- Linha 2465: Monta messages (MESMO que Chamada 1)
- Linha 2470: Log "GPT CALL linha=1314"
- Linha 2476: `client.chat.completions.create()`

**OBSERVAÇÃO CRÍTICA:**
```python
# Linha 2465-2468 (ANTES de Chamada 2)
messages = montar_prompt_com_contexto(
    INSTRUCAO_SECRETARIA, contexto, contexto_salvo, texto_usuario
)

# Linha 1026-1030 (ANTES de Chamada 1)
resposta = await client.chat.completions.create(
    model="gpt-4o",
    temperature=0.4,
    messages=messages,  # ← MESMO messages!
)
```

**AS DUAS CHAMADAS USAM O MESMO `messages`!**

```diff
- Chamada 1 (1027): messages = montar_prompt_com_contexto(...)
- Chamada 2 (2476): messages = montar_prompt_com_contexto(...)
```

**ISSO É DUPLICAÇÃO.**

---

## ACHADO CRÍTICO: POSSÍVEL DUPLICAÇÃO

### Cenário de Duplicação:

```
[Usuário envia áudio]
    ↓
[processar_com_gpt_com_acao()]
    ↓ [Nenhuma condição early-return é satisfeita]
    ↓
[Chamada 1: linha 1027] 
  messages = montar_prompt_com_contexto(...)
  resposta1 = await client.chat.completions.create(messages)
    ↓ [resultado da chamada 1]
    ↓ [alguma condição, talvez: if resultado["acao"] == "xxx"]
    ↓
[Chamada 2: linha 2476]
  messages = montar_prompt_com_contexto(...)  ← RECALCULADO
  resposta2 = await client.chat.completions.create(messages)  ← SEGUNDA CHAMADA AO MESMO TEXTO!
```

**O MESMO `messages` É RECALCULADO DUAS VEZES.**

**Impacto:**
```
1 áudio → 2x mesma pergunta ao GPT
= 2x uso de tokens
= 2x latência
= 2x em direção ao 429
```

---

## LÓGICA DE DECISÃO ENTRE AS DUAS CHAMADAS

**Procurando o `if resultado_1.alguma_coisa: chama_novamente()`**

Não encontrado explicitamente.

**Padrão observado:**
```python
# Chamada 1
resposta = await client.chat.completions.create(...)
resultado = json.loads(resposta.choices[0].message.content)
# ... processamento ...

# Depois, sem condição clara visível:
# Chamada 2
messages = montar_prompt_com_contexto(...)
resposta = await client.chat.completions.create(...)  # MESMA VARIÁVEL?
```

**Risco:** Chamada 2 pode estar SOBRESCREVENDO Chamada 1, não complementando.

---

## DUPLICAÇÃO DE LÓGICA PÓS-CHAMADA

### Após Chamada 1 (linhas 1056-1087):
```python
resultado = json.loads(conteudo)
resultado.setdefault("resposta", "OK")
resultado.setdefault("acao", None)
resultado.setdefault("dados", {})
# Bloqueios e validações
```

### Após Chamada 2 (linhas 2483-2508):
```python
resultado = json.loads(conteudo)
resultado.setdefault("resposta", "OK")
resultado.setdefault("acao", None)
resultado.setdefault("dados", {})
# Mesmos bloqueios e validações
```

**IDÊNTICO. Código duplicado.**

---

## RECOMENDAÇÃO: OTIMIZAÇÕES POSSÍVEIS

### Opção A: Combinar em 1 chamada (MAIOR IMPACTO)
```python
# Se Chamada 2 é apenas um refinamento:
resultado1 = chamar_gpt_1() 

# Usar resultado1 para refinar context, DEPOIS chamar 1x:
resposta_final = chamar_gpt_2(contexto_refinado)

# Eliminaria metade das requisições
# Economia: 50% em requisições GPT
```

### Opção B: Lógica condicional clara
```python
if resultado1.get("acao") == "X":
    # Fazer Chamada 2
else:
    # Retornar resultado1
```

Atualmente opaco.

### Opção C: Paralelizar se independentes
```python
# Se ambas as chamadas são independentes:
resultado1, resultado2 = await asyncio.gather(
    chamar_gpt_com_contexto_1(),
    chamar_gpt_com_contexto_2()
)
```

Reduziria latência (não requisições, mas latência).

---

## CAUSA PROVÁVEL DO 429

**NÃO é apenas retry excessivo.**

**É duplicação estrutural:**
```
1 áudio → 2 chamadas GPT (Chamada 1 + Chamada 2)
10 usuários simultâneos → 20 chamadas
60 usuários/segundo → 120 chamadas/segundo

Limite: ~1 chamada/segundo

120 >> 1 → 429 GARANTIDO
```

**Solução não é: adicionar backoff/retry**  
**Solução é: eliminar duplicação**

---

## PRÓXIMO PASSO: INVESTIGAÇÃO

Antes de fazer patch de retry:

1. **Localizar condicional explícito** que dispara Chamada 2
   - Procurar por: `if resultado_1.get("acao")...`
   - Procurar por: `if tipo_fluxo == ...`
   - Procurar por: `while ...`

2. **Verificar se Chamada 2 realmente precisa de recalcular `messages`**
   - Se sim: por quê?
   - Se não: reutilizar Chamada 1

3. **Validar se resultado1 é descartado ou utilizado**
   - Se descartado: Chamada 2 é redundante
   - Se utilizado: tem dependencies que justificam 2 chamadas

**Diagnóstico sem alterar código ainda.**

