# 🔍 Investigação: Por que Serviço Fica Vazio em MSG 3

## Rastreamento Completo do Fluxo

### MSG 1: "voce tem agenda para corte amanha as 10?"

#### Etapa 1: Classificação (linhas 5732-5735)
```python
eh_consulta_detectado = eh_nova_consulta_pura(texto_usuario)
if eh_consulta_detectado:
    ctx["objetivo_conversacional"] = "consultar_disponibilidade_por_servico"
    ctx["intencao_conversacional"] = "consulta_disponibilidade_servico"
    # ❌ NÃO EXTRAI SERVIÇO AQUI
```

**Status:** ✅ Classificação OK, mas sem extração de serviço

---

#### Etapa 2: Salva Contexto (linhas 5760-5770)
```python
await salvar_contexto_temporario_v2(dono_id, cliente_id, {
    "intencao_conversacional": ctx.get("intencao_conversacional"),  # = "consulta_disponibilidade_servico"
    "objetivo_conversacional": ctx.get("objetivo_conversacional"),  # = "consultar_disponibilidade_por_servico"
    "servico": ctx.get("servico"),  # ❌ VAZIO (None)
    "data_hora": ctx.get("data_hora"),  # Pode estar preenchido
})
```

**Status:** ⚠️ Serviço salvo como `None`

---

#### Etapa 3: Consulta Pura - Extração (linhas 13471-13517)

Detecta `eh_consulta_pura = True` (baseado em `intencao_conversacional` setada em Etapa 1)

**3.1 Primeira Tentativa: `_match_servico_puro()` (linha 13491)**

```python
todos_servicos = []
for p in profs_dict.values():  # profs_dict = await buscar_subcolecao(...)
    todos_servicos.extend(p.get("servicos") or [])

servicos_unicos = list(dict.fromkeys(todos_servicos))
encontrou, servico_para_resposta = _match_servico_puro(servicos_unicos, tnorm)
```

**`_match_servico_puro()` implementação (linhas 106-142):**

```python
def _match_servico_puro(lista_servs: list, texto_normalizado: str) -> tuple[bool, str | None]:
    if not lista_servs or not texto_normalizado:
        return (False, None)  # ❌ FALHA #1: lista vazia

    lista_ord = sorted(lista_servs, key=lambda s: len(normalizar(str(s))), reverse=True)

    # FASE 1: Match exato com word boundaries
    for s in lista_ord:
        s_norm = normalizar(str(s))
        if not s_norm:
            continue
        if re.search(rf"\b{re.escape(s_norm)}\b", texto_normalizado):  # ❌ FALHA #2: regex falha
            return (True, str(s).strip())

    # FASE 2: Match de prefixo
    for s in lista_ord:
        s_norm = normalizar(str(s))
        if not s_norm:
            continue
        s_palavras = s_norm.split()
        if s_palavras:
            primeira_palavra = s_palavras[0]
            if re.search(rf"\b{re.escape(primeira_palavra)}\b", texto_normalizado):  # ❌ FALHA #3: prefixo falha
                return (True, str(s).strip())

    return (False, None)  # ❌ FALHA #4: nenhuma técnica funcionou
```

**Onde pode falhar em `_match_servico_puro()`:**

| # | Falha | Causa | Resultado |
|---|-------|-------|-----------|
| 1 | `lista_servs` vazio | `buscar_subcolecao()` retornou `{}` | Retorna `(False, None)` |
| 2 | `texto_normalizado` vazio | Texto malformado | Retorna `(False, None)` |
| 3 | Regex word boundary falha | "corte feminino" VS "corte" — precisa match EXATO | Não encontra |
| 4 | Prefixo falha | "corte" como primeira palavra não encontrada em texto | Não encontra |
| 5 | `normalizar()` retorna vazio | Serviço tem apenas caracteres especiais | Pula iteração |

---

**3.2 Fallback: `encontrar_servico_mais_proximo()` (linha 13497)**

Se `_match_servico_puro()` falhou, tenta:

```python
if not servico_para_resposta:
    servico_para_resposta = await encontrar_servico_mais_proximo(texto_usuario, dono_id)
```

**Implementação (linhas 86-157):**

```python
async def encontrar_servico_mais_proximo(texto_usuario: str, user_id: str = None, dono_id: str = None):
    texto_normalizado = unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", texto_usuario.lower())
    ).strip()

    if not dono_id:  # ❌ FALHA #1: sem tenant
        if user_id:
            try:
                dono_id = await obter_id_dono(user_id)  # ❌ FALHA #1b: resolução falha
            except Exception as e:
                dono_id = None
        else:
            return None

    if not dono_id:  # ❌ FALHA #2: dono_id ainda None
        return None

    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    todos_servicos = set()
    for dados in profissionais.values():  # ❌ FALHA #3: profissionais vazio
        servs = dados.get("servicos", [])
        for s in servs:
            if isinstance(s, str):
                s_norm = unidecode.unidecode(re.sub(r"[^\w\s]", " ", s.lower())).strip()
                todos_servicos.add(s_norm)

    candidatos = list(todos_servicos)
    if not candidatos:  # ❌ FALHA #4: candidatos vazio
        return None

    # 3 técnicas de matching (podem todas falhar)
    for candidato in candidatos:
        if candidato in texto_normalizado:
            return candidato

    for palavra in texto_normalizado.split():
        match = difflib.get_close_matches(palavra, candidatos, n=1, cutoff=0.8)  # 80% tolerance
        if match:
            return match[0]

    match = difflib.get_close_matches(texto_normalizado, candidatos, n=1, cutoff=0.4)  # 40% tolerance
    if match:
        return match[0]

    return None  # ❌ FALHA #5: todas as técnicas falharam
```

**Onde pode falhar em `encontrar_servico_mais_proximo()`:**

| # | Falha | Causa | Resultado |
|---|-------|-------|-----------|
| 1 | `dono_id` não resolvido | `obter_id_dono(user_id)` falha | Retorna `None` |
| 2 | `dono_id` ainda None | Sem tenant para buscar profissionais | Retorna `None` |
| 3 | `profissionais` vazio | `buscar_subcolecao()` retorna `{}` (sem profissionais) | `candidatos = []` |
| 4 | `candidatos` vazio | Nenhum profissional tem serviços cadastrados | Retorna `None` |
| 5 | Substring não encontra | "corte feminino" não está em "voce tem agenda para corte amanha" | Tenta próxima |
| 6 | Fuzzy 80% falha | Nenhuma palavra tem 80% de similaridade com candidatos | Tenta próxima |
| 7 | Fuzzy 40% falha | Texto todo tem <40% similaridade | Retorna `None` |

---

### **3.3 Se AMBAS falharem:**

```python
encontrou, servico_para_resposta = _match_servico_puro(servicos_unicos, tnorm)
if not encontrou:
    servico_para_resposta = None

if not servico_para_resposta:  # ❌ Ambas falharam
    servico_para_resposta = await encontrar_servico_mais_proximo(...)

if not servico_para_resposta:  # ❌ AINDA vazio
    # Entra no bloco else (linha 13519)
    servico_para_resposta = None  # Continua None
```

**Linha 13503-13539:**

```python
if servico_para_resposta:  # ❌ FALSO!
    # Não entra aqui
    ctx.update({
        "servico_sugerido_consulta": servico_para_resposta,
        "servico": servico_para_resposta,
    })
    await salvar_contexto_temporario_v2(...)
    resposta_texto = f"Sim, fazemos {servico_para_resposta}! Gostaria de agendar?"
else:  # ✅ ENTRA AQUI
    resposta_texto = "Não consegui identificar... Qual você gostaria?"
    # NUNCA salva servico_sugerido_consulta
```

**Status:** ❌ **Serviço NÃO é salvo em `ctx["servico_sugerido_consulta"]`**

---

### MSG 2: Usuário responde "sim"

**Linha 5093:**
```python
servico_sugerido = ctx.get("servico_sugerido_consulta")  # ❌ = None (nunca foi salvo)
```

**Linha 5097:**
```python
if not servico_sugerido:  # ✅ TRUE!
    # Retorna pergunta ao usuário, NUNCA avança para agendamento
    return await _send_and_stop(context, user_id, "Perfeito. Qual serviço você quer agendar?")
```

**Status:** ❌ **Fluxo interrompido — usuário volta a ser perguntado**

---

## 🔴 CONCLUSÃO

### Cenário que Causa [P0626_VALIDACAO]

**Se o usuário CONSEGUE chegar em MSG 3 com erro [P0626_VALIDACAO], significa que:**

1. ✅ MSG 1: Serviço FOI extraído em algum lugar (não em `_match_servico_puro()` nem em `encontrar_servico_mais_proximo()`)
2. ✅ MSG 2: Serviço FOI salvo (em `servico_sugerido_consulta` ou diretamente em `ctx["servico"]`)
3. ❌ MSG 3: Serviço foi PERDIDO ou LIMPO

### Possíveis Causas de Sucesso em MSG 1-2 + Falha em MSG 3

**Opção A:** O serviço é extraído por outro caminho não investigado

**Opção B:** Entre MSG 2 e MSG 3, o contexto é limpo/recarregado de forma incompleta

**Opção C:** A `draft_agendamento` é sobrescrita sem preservar `servico`

---

## 📊 Matriz de Falhas Possíveis

```
PRIMEIRA TENTATIVA: _match_servico_puro()
├─ Lista vazia? → Falha
├─ Texto vazio? → Falha
├─ Regex word boundary não encontra? → Falha
└─ Prefixo não encontra? → Falha

SEGUNDA TENTATIVA: encontrar_servico_mais_proximo()
├─ Tenant não resolvido? → Falha
├─ Profissionais vazio? → Falha
├─ Candidatos vazio? → Falha
├─ Substring não encontra? → Tenta próxima
├─ Fuzzy 80% não encontra? → Tenta próxima
└─ Fuzzy 40% não encontra? → Falha

SE AMBAS FALHAREM:
└─ servico_para_resposta = None → Nunca salva servico_sugerido_consulta
```

---

**Criado:** 2026-10-19  
**Análise:** Completa, sem alterações de código
