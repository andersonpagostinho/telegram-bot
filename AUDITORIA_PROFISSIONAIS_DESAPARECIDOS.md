# 🔴 AUDITORIA: Bug de Profissionais Desaparecidos

**Entrada:** "quem você tem disponível amanhã no período da manhã para corte de cabelo"

**Resultado Esperado:** Lista com Bruna, Gloria, Joana

**Resultado Obtido:** "No momento, não há profissionais cadastrados"

**Status:** Auditoria — Nenhuma correção aplicada ainda

---

## 1. Onde Profissionais São Buscados no Firestore

### Local 1: handlers/bot.py, linhas 152-154
```python
# 🔍 busca profissionais
profissionais_dict = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
nomes_profissionais = [p.get("nome") for p in profissionais_dict.values() if p.get("nome")]
```

✅ Profissionais SÃO buscados aqui para verificar bloqueios.

### Local 2: router/principal_router.py, linhas 1083-1084
```python
profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
nomes_profs = [str(p.get("nome", "")).strip() for p in profs_dict.values() if p.get("nome")]
```

✅ Profissionais SÃO buscados aqui para detecção de profissional na mensagem.

### Local 3: services/gpt_service.py, FALTANDO
```
❌ NÃO há busca de profissionais antes de chamar montar_prompt_com_contexto()
```

**ACHADO CRÍTICO:** Em nenhum lugar do fluxo `processar_com_gpt_com_acao()` há uma chamada a `buscar_subcolecao("Profissionais")`.

---

## 2. Onde Deveriam Ser Filtrados por Serviço

### Código que TENTA filtrar (linhas 810-894 de gpt_service.py)

```python
# --- 4.9) FILTRO + TRAVA: profissionais aptos ao serviço (ANTES do prompt) ---
try:
    servico_ctx = (contexto_salvo or {}).get("servico")
    prof_escolhido_ctx = (contexto_salvo or {}).get("profissional_escolhido")
    profs = (contexto or {}).get("profissionais") or []  # ← LINHA 814
    
    if isinstance(profs, list):
        profs_filtrados = profs
        
        # 1) Se houver serviço, filtra pelos aptos ao serviço
        if servico_ctx:
            servico_norm = unidecode.unidecode(str(servico_ctx).lower().strip())
            tmp = []
            
            for p in profs_filtrados:
                if not isinstance(p, dict):
                    continue
                servs = p.get("servicos") or []
                ...
                if servico_norm in servs_norm:
                    tmp.append(p)
            
            profs_filtrados = tmp
        
        # substitui no contexto
        contexto["profissionais"] = profs_filtrados  # ← LINHA 860
```

**O PROBLEMA:** 
- Linha 814 tenta ler `contexto.get("profissionais")`
- MAS `contexto` é passado como `{}` vazio (veja ponto 4 abaixo)
- Portanto `profs = []` e toda a filtragem não funciona

---

## 3. Onde Contexto é Montado para o GPT

### Fluxo de entrada:

**handlers/gpt_text_handler.py:**
```python
async def handle_text_message(...):
    resultado = await processar_com_gpt_com_acao(...)
```

↓

**services/gpt_service.py, linhas 50-80 (`processar_com_gpt`):**
```python
async def processar_com_gpt(texto_usuario, user_id="desconhecido"):
    try:
        cliente = await buscar_cliente(user_id)
        
        resultado = await processar_com_gpt_com_acao(
            texto_usuario=texto_usuario,
            contexto={},  # ← **LINHA 77: CONTEXTO VAZIO!**
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
        )
```

↓

**services/gpt_service.py, linhas 111-899 (`processar_com_gpt_com_acao`):**
```python
async def processar_com_gpt_com_acao(
    texto_usuario: str,
    contexto: dict,  # ← RECEBE {}
    instrucao: str,
    user_id: str | None = None,
):
    uid = user_id or ...
    
    # Carrega contexto salvo
    contexto_salvo = await carregar_contexto_temporario(uid) or {}
    
    # ← NUNCA POPULA contexto["profissionais"]
    
    # Tenta filtrar profissionais
    profs = (contexto or {}).get("profissionais") or []  # ← LINHA 814: VAZIO!
```

---

## 4. Por que CTX->GPT Mostra profs=0 nomes=[]

**Cadeia de causas:**

```
1. processar_com_gpt() [linha 77]
   ↓
   contexto={}  (vazio)
   
2. processar_com_gpt_com_acao() [linha 814]
   ↓
   profs = contexto.get("profissionais") or []
   ↓
   profs = [] (porque contexto é vazio)
   
3. [Linhas 876-892] Log auditoria:
   ↓
   profs_final = (contexto or {}).get("profissionais") or []
   ↓
   profs_final = []
   ↓
   print(f"profs={len(profs_final)}")
   ↓
   🧾 [CTX->GPT] ... profs=0 nomes=[]
```

**Log exato que aparece:**
```
🧾 [CTX->GPT] uid=... servico=corte profs=0 nomes=[]
```

---

## 5. Por que Prompt Diz "Profissionais: nenhum"

**Fluxo:**

1. `montar_prompt_com_contexto()` em gpt_utils.py, linhas 19-38

```python
profissionais = contexto.get("profissionais", []) or []  # ← VAZIO

# Linhas 32-38: Extrai nomes
prof_nomes = []
for p in profissionais:
    if isinstance(p, dict) and p.get("nome"):
        prof_nomes.append(str(p["nome"]))
    elif isinstance(p, str):
        prof_nomes.append(p.strip())
resumo_prof = ", ".join(prof_nomes[:12]) + (", ..." if len(prof_nomes) > 12 else "")
# ↑ resumo_prof = "" (vazio)
```

2. Linha 75 de gpt_utils.py

```python
f"- Profissionais: {resumo_prof or 'nenhum'}\n"
# ↓
f"- Profissionais: nenhum\n"
```

3. Mensagem enviada ao GPT contém:

```
📌 CONTEXTO ATUAL DO ATENDIMENTO
- Data atual: 2026-06-02
- Pagamento ativo (assumido): True
- Módulos ativos (assumidos): secretaria
- Tipo de negócio: salao
- Profissionais: nenhum  ← **AQUI**
- Tarefas (amostra): nenhuma
- ...
```

4. GPT responde:

```
"resposta": "No momento, não há profissionais cadastrados."
```

---

## LOCALIZAÇÃO EXATA DO PROBLEMA

| # | Arquivo | Linha | Problema | Severidade |
|---|---------|-------|---------|-----------|
| 1 | gpt_service.py | **77** | `contexto={}` passado vazio | **CRÍTICO** |
| 2 | gpt_service.py | **814** | Tenta ler `contexto["profissionais"]` que é vazio | **Sintoma** |
| 3 | gpt_utils.py | **19** | Não há fallback para carregar profissionais | **Raiz** |
| 4 | gpt_service.py | Não há `buscar_subcolecao("Profissionais")` | **Raiz** |
| 5 | gpt_utils.py | 75 | Mostra "nenhum" quando lista está vazia | **Sintoma** |

---

## ANÁLISE DE RAIZ CAUSA

### Causa 1: Contexto Vazio na Entrada ⚠️ **PRINCIPAL**

**Arquivo:** services/gpt_service.py, linhas 75-80

```python
resultado = await processar_com_gpt_com_acao(
    texto_usuario=texto_usuario,
    contexto={},  # ← SEMPRE VAZIO
    instrucao=INSTRUCAO_SECRETARIA,
    user_id=user_id,
)
```

**Por que?** A função `processar_com_gpt()` é um wrapper que não carrega profissionais antes de chamar `processar_com_gpt_com_acao()`.

**Esperado:**
```python
contexto = {}

# Carregar profissionais
if user_id != "desconhecido":
    try:
        cliente = await buscar_cliente(user_id)
        id_dono = cliente.get("id_negocio", user_id)
        profs_dict = await buscar_subcolecao(f"Clientes/{id_dono}/Profissionais") or {}
        contexto["profissionais"] = [
            {
                "nome": p.get("nome"),
                "servicos": p.get("servicos", [])
            }
            for p in profs_dict.values()
            if p.get("nome")
        ]
    except Exception as e:
        print(f"⚠️ Falha ao carregar profissionais: {e}")

resultado = await processar_com_gpt_com_acao(
    texto_usuario=texto_usuario,
    contexto=contexto,  # ← PREENCHIDO
    instrucao=INSTRUCAO_SECRETARIA,
    user_id=user_id,
)
```

---

### Causa 2: Falta de Fallback em `processar_com_gpt_com_acao()` ⚠️ **SECUNDÁRIA**

**Arquivo:** services/gpt_service.py, linhas 810-894

O código TEM a filtragem de profissionais, MAS assume que `contexto["profissionais"]` já está preenchido. Não há fallback para carregar profissionais se estiverem ausentes.

**Esperado:** Se `contexto["profissionais"]` está vazio, carregar do Firestore:

```python
profs = (contexto or {}).get("profissionais") or []

# Fallback: se profissionais não estão no contexto, carregar do Firestore
if not profs and uid != "desconhecido":
    try:
        cliente = await buscar_cliente(uid)
        id_dono = cliente.get("id_negocio", uid)
        profs_dict = await buscar_subcolecao(f"Clientes/{id_dono}/Profissionais") or {}
        profs = [
            {
                "nome": p.get("nome"),
                "servicos": p.get("servicos", [])
            }
            for p in profs_dict.values()
            if p.get("nome")
        ]
    except Exception as e:
        print(f"⚠️ Fallback de profissionais falhou: {e}")
        profs = []
```

---

## REGRA ARQUITETURAL VIOLADA

**Regra que o usuário mencionou:**
> "Consulta de disponibilidade é motor determinístico, não GPT."

**O que acontece agora:**
```
Usuário: "quem você tem disponível para corte de cabelo?"
    ↓
GPT recebe: "Profissionais: nenhum"
    ↓
GPT responde: "Não há profissionais"
```

**O que deveria acontecer:**
```
Usuário: "quem você tem disponível para corte de cabelo?"
    ↓
Sistema: Busca profissionais que fazem "corte"
    ↓
Sistema: Filtra por disponibilidade no período/data
    ↓
Sistema: Retorna lista real (Bruna, Gloria, Joana)
```

---

## RESUMO

| Aspecto | Encontrado | Status |
|---------|-----------|--------|
| Profissionais em Firestore | ✅ Bruna, Gloria, Joana | Existem |
| Busca em gpt_service.py | ❌ `contexto={}` | **FALTANDO** |
| Filtro por serviço | ✅ Código existe | Não executa |
| CTX->GPT mostra | ❌ profs=0 | Consequência |
| Prompt diz | ❌ "Profissionais: nenhum" | Consequência |

**Linha exata do problema:** services/gpt_service.py, linha **77**

```python
contexto={},  # ← AQUI: Contexto vazio, profissionais nunca carregados
```

---

**Status da Auditoria:** ✅ Completo. Nenhuma correção aplicada conforme solicitado.

