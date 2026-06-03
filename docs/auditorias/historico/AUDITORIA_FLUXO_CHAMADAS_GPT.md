# 🔍 AUDITORIA: Fluxo Real das 2 Chamadas GPT

**Evidência Crítica Encontrada**

---

## ESTRUTURA ENCONTRADA

### Chamada 1: Linha 1027
```python
# Linhas 1019-1047: Try/Except DIRETO
try:
    resposta = await client.chat.completions.create(...)  # Linha 1027
    await registrar_custo_gpt(resposta, "gpt-4o", uid, firestore_client)
except Exception as e:
    print(f"❌ Erro ao chamar OpenAI: {type(e).__name__}: {e}")
    return {...}  # Linha 1043 - RETORNA SE ERRO
```

**Se sucesso na Chamada 1:** Continua para linhas 1049-1172

```python
# Linhas 1049-1120: Processa resultado
try:
    resultado = json.loads(conteudo)
    # ... processamento ...
except Exception as e:
    # ... log ...

# Linhas 1122-1171: Mais processamento
# ... histórico, guard rails, etc ...

# Linha 1172:
return resultado  # RETORNA RESULTADO
```

**CRÍTICO:** Linha 1172 é `return resultado` - Chamada 1 retorna aqui!

---

### Chamada 2: Linha 2476
```python
# Linhas 2300-2303: Condicional guardião
cliente = await buscar_cliente(user_id)
if cliente:  # ← GUARDA A CHAMADA 2

    # Linhas 2309-2364: Filtragem de profissionais
    # Linhas 2366-2368: Primeira montagem de messages
    messages = montar_prompt_com_contexto(...)
    
    # Linhas 2370-2463: Sanitização e auditoria
    # ... sem chamar GPT ainda ...
    
    # Linhas 2465-2468: SEGUNDA montagem de messages
    messages = montar_prompt_com_contexto(...)  # RECALCULADO!
    
    # Linhas 2470-2478:
    resposta = await client.chat.completions.create(...)  # Linha 2476
    await registrar_custo_gpt(resposta, "gpt-4o", user_id, firestore_client)
    
    # Linhas 2483-2544: Processa resultado
    try:
        resultado = json.loads(conteudo)
        # ... processamento ...
    except Exception as e:
        # ... log ...
        return {...}
```

**SE `cliente` é nulo:** Chamada 2 NUNCA EXECUTA

---

## RESPOSTAS ÀS 6 PERGUNTAS

### 1. A primeira chamada retorna antes em quais casos?

**SIM, em muitos casos:**
- Linhas 945-947: Se usuário enviou serviço+profissional+data → return pré-confirmação
- Linhas 962-969: Se é ajuste de horário com conflito → return sugestões
- Linhas 1013-1017: Se está faltando dados → return erro
- **Linha 1172: `return resultado`** após Chamada 1

---

### 2. Em quais casos o código continua até a segunda chamada?

**NÃO É SEQUENCIAL!**

Chamada 1 e Chamada 2 estão em **CAMINHOS DIFERENTES DA MESMA FUNÇÃO**:

```
processar_com_gpt_com_acao():
├─ Linha ~945: Se tiver servico+prof+data → return (não chama GPT)
├─ Linha ~962: Se é ajuste → return (não chama GPT)
├─ Linha 1019-1172: Se nada acima → CHAMADA 1 → return resultado
│
└─ **NEM SEMPRE CHEGA AQUI** ↓
    
    Linha 2302: cliente = await buscar_cliente(user_id)
    Linha 2303: if cliente:
        └─ Linhas 2309-2544: **CHAMADA 2** (SÓ SE cliente NÃO É NULL)
```

---

### 3. A segunda chamada recebe exatamente o mesmo `messages`?

**NÃO! Mas MUITO PRÓXIMO:**

```python
# Primeira vez (Linha ~2366)
messages = montar_prompt_com_contexto(
    INSTRUCAO_SECRETARIA, contexto, contexto_salvo, texto_usuario
)

# [Linhas 2370-2463: Filtragem e sanitização - CONTEXTO PODE MUDAR]
contexto["profissionais"] = profs_filtrados  # ← CONTEXTO MUDA!
contexto_salvo["profissional_escolhido"] = None  # ← CONTEXTO MUDA!

# Segunda vez (Linha 2466)
messages = montar_prompt_com_contexto(  # RECALCULADO COM CONTEXTO MODIFICADO
    INSTRUCAO_SECRETARIA, contexto, contexto_salvo, texto_usuario
)
```

**O contexto é MODIFICADO entre as duas montagens.**

---

### 4. O `contexto`, `contexto_salvo` ou `texto_usuario` muda entre chamada 1 e 2?

**SIM - CONTEXTO MUDA:**

```python
# Linha 2334:
contexto["profissionais"] = aptos  # Filtra profissionais

# Linha 2398:
contexto["profissionais"] = profs_filtrados  # Filtra NOVAMENTE

# Linha 2406:
contexto_salvo["ultima_opcao_profissionais"] = nomes_ok  # ATUALIZA

# Linha 2437:
contexto_salvo["profissional_escolhido"] = None  # ANULA profissional
```

**Não há mudança em `texto_usuario` - ele permanece o mesmo.**

---

### 5. O resultado da primeira chamada é usado para decidir algo antes da segunda?

**NÃO ENCONTRADO.**

```
[Chamada 1: Linha 1027]
    ↓
[Processa resultado]
    ↓
[Line 1172: return resultado]
    ↓
FIM DA CHAMADA 1 (saída da função)

[Chamada 2 NUNCA USA resultado DA CHAMADA 1]
```

**Não há condicional do tipo:**
```python
if resultado_chamada_1.get("acao") == "X":
    fazer_chamada_2()
```

---

### 6. Existe algum `return` faltando depois da primeira chamada?

**ACHADO CRÍTICO: SIM, POSSÍVEL ERRO DE ESTRUTURA**

```python
# Linha 1172
return resultado  # ← Retorna após Chamada 1

# Linhas 1174-1180
except Exception as e:
    print(...)
    return {...}  # ← Retorna se Exception

# Linhas 1182-1436: CÓDIGO MORTO!
    # 🧼 Se a ação detectada não for de agendamento...
    if resultado.get("acao") not in ["agendar"]...
    # ← NUNCA EXECUTA (está após return)
```

**Observação:** Linhas 1182-1436 estão DENTRO do `except` mas APÓS um `return`.
Isso significa que **CÓDIGO NUNCA EXECUTA**.

Possível má indentação do try/except?

---

## CONCLUSÃO: AS 2 CHAMADAS SÃO...

### ❌ **NÃO duplicação simples**
Chamada 1 e 2 estão em caminhos DIFERENTES:
- Chamada 1: Sempre executada (se passa pelos guards anteriores)
- Chamada 2: **CONDICIONADA A `if cliente:`**

### ⚠️ **POSSÍVEL ESTRUTURA ERRADA**
```
SE cliente é nulo:
    ├─ Chamada 1 executa e retorna
    └─ Chamada 2 NUNCA executa

SE cliente existe:
    ├─ Código passa linha 1172 E continua?
    └─ OU Chamada 1 sempre retorna (linha 1172)?
```

**RISCO:** Se há CONDIÇÃO que faz a Chamada 1 NÃO retornar na linha 1172, então Chamada 2 executa. Mas isso não é claro no código.

---

## O QUE ESTÁ FALTANDO

Para confirmar se é duplicação ou múltiplos caminhos:

1. **Qual é a indentação real da linha 1172?**
   - Se está no nível da função → sempre retorna
   - Se está aninhada em um if → pode continuar até linha 2476

2. **Qual função contém a linha 2303?**
   - Aparentemente é a mesma `processar_com_gpt_com_acao()`
   - Mas o `if cliente:` é o guardião

3. **Existe alguma condição que faz a linha 1172 ser pulada?**
   - Um `if` que envolve Chamada 1?
   - Um `while` que re-executa?

---

## PRÓXIMO PASSO: TESTE PRÁTICO

Adicionar logs:

```python
# Após Chamada 1
[GPT_CALL_1_END] ✅
[RETURN_DECISION_1] Vai retornar? SIM/NÃO
[CONTINUANDO?] resultado=...

# Antes Chamada 2
[GPT_CALL_2_START] ✅
[CONTEXTO_DIFF] profissionais mudou? ultima_opcao_profissionais mudou?
[REASON_CALL_2] Por que Chamada 2 aconteceu?
```

Rodar com Suri para VER SE AMBAS EXECU...

