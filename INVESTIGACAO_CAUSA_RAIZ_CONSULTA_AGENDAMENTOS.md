# INVESTIGAÇÃO DE CAUSA RAIZ — Mensagem "Tenho alguma coisa agendada para hoje?"

**Data da Investigação:** 2026-09-14  
**Mensagem do Usuário:** "Tenho alguma coisa agendada para hoje?"  
**Comportamento Esperado:** Consultar agendamentos do usuário para hoje  
**Comportamento Observado:** "Esse horário (10/09/2026 às 00:00) já passou. Só me diz qual serviço..."  

---

## 🔴 CADEIA DO BUG — MAPA COMPLETO

```
MENSAGEM DO USUÁRIO
├─ "Tenho alguma coisa agendada para hoje?"
│
├─ [A] CLASSIFICADOR DE INTENÇÃO ⬇️
│  ├─ Arquivo: services/classificador_conversa.py
│  ├─ Função: classificar_intencao_conversacional()
│  ├─ Linha: 338-339
│  ├─ Condição: if f["tem_pergunta"] and f["tem_tempo"] and f["tem_indefinido"]
│  ├─ Features Detectadas:
│  │  - tem_pergunta = True (tem "?")
│  │  - tem_tempo = True (tem "hoje")
│  │  - tem_indefinido = True (tem "alguma coisa")
│  ├─ Intenção Resultante: "consulta_disponibilidade_aberta"
│  ├─ Confiança: 88
│  └─ Status: ✅ FUNCIONANDO CORRETAMENTE
│
├─ [B] OBJETIVO CONVERSACIONAL ⬇️
│  ├─ Arquivo: router/principal_router.py
│  ├─ Função: processar_mensagem_operacional()
│  ├─ Linhas: 4134-4135
│  ├─ Código:
│  │  if intencao_conv == "consulta_disponibilidade_aberta":
│  │      objetivo_conversacional = "descobrir_servico_para_consulta"
│  ├─ Objetivo Resultante: "descobrir_servico_para_consulta"
│  └─ Status: ✅ CORRETO (mas objetivo é errado para o caso)
│
├─ [C] PARSER DE DATA/HORA ⬇️
│  ├─ Arquivo: utils/interpretador_datas.py
│  ├─ Função: interpretar_data_e_hora()
│  ├─ Linhas: 217-385
│  ├─ Entrada: "Tenho alguma coisa agendada para hoje?"
│  ├─ Processamento:
│  │  1. texto_reduzido = "hoje" (extrair_trecho_temporal)
│  │  2. dateparser("hoje") → 2026-09-10 09:56:28.695585
│  │  3. Detecta "hoje" em linha 239-252
│  │  4. Retorna datetime com hora 09:56:28 (hora do parse, não hora do usuário)
│  ├─ Saída: datetime(2026, 9, 10, 9, 56, 28)
│  └─ Status: ⚠️ PROBLEMÁTICO (preserva hora do parse, deveria não ter hora)
│
├─ [D] MESCLAR DATA/HORA ⬇️
│  ├─ Arquivo: router/principal_router.py
│  ├─ Função: processar_mensagem_operacional() → bloco MESCLAR
│  ├─ Linhas: 1353-1665
│  ├─ Entrada: dt_detectado = datetime(2026, 9, 10, 9, 56, 28)
│  ├─ Processamento:
│  │  1. Verificar se há horários explícitos: NÃO (apenas "hoje")
│  │  2. Verificar múltiplos horários: NÃO
│  │  3. Verificar data sem hora (linhas 1600-1651):
│  │     - data_iso = "2026-09-10"
│  │     - Procura por hora anterior válida:
│  │       * ctx.get("data_hora") = None
│  │       * draft.get("data_hora") = None
│  │       * ultima_consulta.get("data_hora") = None
│  │     - hora_anterior = None
│  │  4. Vai para ELSE (linhas 1633-1651):
│  │     - dt_final = dt_detectado.replace(hour=0, minute=0, second=0)
│  │     - iso = "2026-09-10T00:00:00"
│  │     - ctx["data_hora"] = "2026-09-10T00:00:00"
│  │     - ctx["data_sem_hora"] = True
│  ├─ Saída: data_hora = "2026-09-10T00:00:00" | data_sem_hora = True
│  └─ Status: ⚠️ PROBLEMÁTICO (transforma qualquer data sem hora em 00:00)
│
├─ [E] FLUXO B-INICIO (AGENDAMENTO) ⬇️
│  ├─ Arquivo: router/principal_router.py
│  ├─ Função: processar_mensagem_operacional()
│  ├─ Linhas: ~5000-9000 (bloco B-INICIO)
│  ├─ Contexto:
│  │  - estado_fluxo = "idle"
│  │  - objetivo_conversacional = "descobrir_servico_para_consulta"
│  │  - data_hora = "2026-09-10T00:00:00"
│  │  - servico = None
│  │  - profissional_escolhido = None
│  ├─ Status: ⚠️ PROBLEMÁTICO (entra em fluxo de agendamento em vez de consulta)
│  └─ Isso dispara o fluxo de agendamento determinístico
│
├─ [F] BLOQUEIO DE HORÁRIO PASSADO ⬇️
│  ├─ Arquivo: router/principal_router.py
│  ├─ Função: processar_mensagem_operacional()
│  ├─ Linhas: 7555-7558
│  ├─ Código:
│  │  if ctx.get("data_hora"):
│  │      dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
│  │      if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
│  │          return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])
│  ├─ Entrada: ctx["data_hora"] = "2026-09-10T00:00:00"
│  ├─ Verificação:
│  │  - dt_naive_existente = 2026-09-10 00:00:00
│  │  - _agora_br_naive() = 2026-09-10 09:56:30 (aprox)
│  │  - 00:00 <= 09:56 ? SIM → passa na condição
│  ├─ Função Chamada: _perguntar_amanha_mesmo_horario_e_bloquear()
│  └─ Status: ⚠️ PROBLEMÁTICO (interpreta 00:00 como horário solicitado)
│
├─ [G] RESPOSTA AO USUÁRIO ⬇️
│  ├─ Arquivo: router/principal_router.py
│  ├─ Função: _perguntar_amanha_mesmo_horario_e_bloquear()
│  ├─ Linhas: 4438-4483
│  ├─ Condição 1: Tem serviço ou profissional? NÃO
│  ├─ Respostainc (linhas 4465-4473):
│  │  f"Esse horário (*{formatar_data_hora_br(data_hora_iso)}*) já passou.\n"
│  │  "Só me diz rapidinho: *qual serviço* você quer fazer (ou *com qual profissional* prefere), "
│  │  "pra eu conferir a agenda certinho."
│  ├─ Formatação: formatar_data_hora_br("2026-09-10T00:00:00") = "10/09/2026 às 00:00"
│  ├─ Saída: "Esse horário (10/09/2026 às 00:00) já passou..."
│  └─ Status: ❌ RESPOSTA ERRADA
│
└─ FIM DA CADEIA
```

---

## 📊 ANÁLISE POR PONTO

### A) CLASSIFICAÇÃO DE INTENÇÃO — `services/classificador_conversa.py:338-339`

**Arquivo:** `services/classificador_conversa.py`  
**Função:** `classificar_intencao_conversacional(texto: str, ctx: dict | None = None) -> dict`  
**Linhas:** 338-339  

```python
if f["tem_pergunta"] and f["tem_tempo"] and f["tem_indefinido"]:
    return {"intencao_conversacional": "consulta_disponibilidade_aberta", "confianca": 88, "features": f}
```

**Análise:**
- ✅ A classificação é **tecnicamente correta** (é uma "consulta de disponibilidade aberta")
- ❌ Mas não distingue entre:
  - **Consultar agendamentos do usuário** ("Tenho alguma coisa agendada hoje?")
  - **Consultar disponibilidade para agendar** ("Tem alguém disponível para corte hoje?")

**Features Detectadas:**
```
tem_pergunta = True       (tem "?")
tem_tempo = True          (tem "hoje")
tem_indefinido = True     (tem "alguma coisa")
```

**Causa Raiz neste Ponto:** A classificação não distingue consultas de **Quais são meus compromissos hoje** de consultas de **Quem está disponível**. Ambas ativam a mesma intenção.

---

### B) OBJETIVO CONVERSACIONAL — `router/principal_router.py:4134-4135`

**Arquivo:** `router/principal_router.py`  
**Função:** `processar_mensagem_operacional()`  
**Linhas:** 4134-4135  

```python
if intencao_conv == "consulta_disponibilidade_aberta":
    objetivo_conversacional = "descobrir_servico_para_consulta"
```

**Análise:**
- ✅ A transformação é **mecanicamente correta** (intenção → objetivo)
- ❌ Mas assume que "consulta_disponibilidade_aberta" sempre significa "preciso descobrir qual serviço"
- ❌ Não considera que pode ser "consultar meus agendamentos"

**Causa Raiz neste Ponto:** Objetivo "descobrir_servico_para_consulta" é inadequado para "Tenho alguma coisa agendada hoje?". Deveria haver objetivo "consultar_agendamentos_usuario".

---

### C) PARSER DE DATA/HORA — `utils/interpretador_datas.py:239-252`

**Arquivo:** `utils/interpretador_datas.py`  
**Função:** `interpretar_data_e_hora(texto: str) -> datetime | None`  
**Linhas:** 239-252  

```python
# ✅ Se tiver "hoje" ou "amanhã" e tiver hora, monta a data manualmente
if ("hoje" in texto_norm or "amanh" in texto_norm) and re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm):
    base = agora_br_aware()
    if "amanh" in texto_norm:
        base = base + timedelta(days=1)

    m = re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm)
    hora = int(m.group(1))
    minuto = int(m.group(2) or 0)

    dt_aware = FUSO_BR.localize(datetime(base.year, base.month, base.day, hora, minuto, 0, 0))
    result = dt_aware.astimezone(FUSO_BR).replace(tzinfo=None)
    print(f"[PARSER] fonte_parse=manual_hoje_amanha resultado={result}", flush=True)
    return result
```

**Entrada:** `"Tenho alguma coisa agendada para hoje?"`  
**Redução:** `"hoje"` (via `extrair_trecho_temporal()`)  
**Processamento:**
- Detecta "hoje" ✅
- Mas há horário explícito? NÃO
- Continua para dateparser genérico

**Fallback (linhas 344-385):**
- `dateparser.parse("hoje", settings={...})`
- Retorna: `datetime(2026, 9, 10, 9, 56, 28)` (hora do parse, não hora do usuário)

**Causa Raiz neste Ponto:** `interpretar_data_e_hora()` retorna uma hora (9:56:28) ao invés de retornar `None` quando é apenas data. Quando é "hoje" sem horário explícito, deveria retornar apenas a data ou um sinalizador especial.

---

### D) MESCLAR DATA/HORA — `router/principal_router.py:1600-1651`

**Arquivo:** `router/principal_router.py`  
**Função:** `processar_mensagem_operacional()`  
**Linhas:** 1600-1651 (CASO 3: data sem hora)  

```python
# =========================================================
# 🔥 CASO 3 — data sem hora
# Se já existe horário anterior válido no fluxo, preserva.
# Ex.: "amanhã", "troca para sexta", "joga para amanhã"
# =========================================================
else:
    data_iso = dt_detectado.date().isoformat()

    data_hora_anterior = (
        ctx.get("data_hora")
        or draft.get("data_hora")
        or (ctx.get("ultima_consulta") or {}).get("data_hora")
    )

    hora_anterior = None

    if data_hora_anterior and "T" in str(data_hora_anterior):
        hora_ant = str(data_hora_anterior).split("T")[1][:5]

        if hora_ant and hora_ant != "00:00":
            hora_anterior = hora_ant

    # ...SE TEM HORA ANTERIOR: preserva, SENÃO:
    
    if hora_anterior:
        iso = f"{data_iso}T{hora_anterior}:00"
        ctx["data_hora"] = iso
        # ...preservação bem-sucedida
    
    else:  # AQUI: sem hora anterior
        dt_final = dt_detectado.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        iso = dt_final.isoformat()

        ctx["data_hora"] = iso  # ← "2026-09-10T00:00:00"
        draft["data_hora"] = iso
        ctx["hora_confirmada"] = False
        ctx["data_sem_hora"] = True  # ← flag set

        print(
            f"🧠 [DATA_SEM_HORA] sem hora anterior válida | iso={iso}",
            flush=True
        )
```

**Entrada:** 
- `dt_detectado = datetime(2026, 9, 10, 9, 56, 28)`
- Não há hora anterior no contexto

**Processamento:**
1. Extrai data: `"2026-09-10"`
2. Busca hora anterior em 3 lugares: NÃO encontra
3. Executa ELSE: transforma para `"2026-09-10T00:00:00"`
4. Seta flag `data_sem_hora = True`

**Causa Raiz neste Ponto:** Quando não há hora anterior, transforma a data em `00:00`. Isso posteriormente é interpretado como um horário solicitado e bloqueado por estar no passado.

---

### E) ROTEAMENTO PARA FLUXO B-INICIO — Linhas ~5000-9000

**Arquivo:** `router/principal_router.py`  
**Função:** `processar_mensagem_operacional()`  
**Contexto:**
- `objetivo_conversacional = "descobrir_servico_para_consulta"`
- `estado_fluxo = "idle"`
- `data_hora = "2026-09-10T00:00:00"`
- `servico = None`
- `profissional_escolhido = None`

**Causa Raiz neste Ponto:** Entra em fluxo de agendamento (B-INICIO) porque o objetivo é "descobrir_servico_para_consulta", que ativa o roteador de agendamento. Deveria ter um roteador paralelo para "consultar_agendamentos_usuario".

---

### F) BLOQUEIO DE HORÁRIO PASSADO — `router/principal_router.py:7555-7558`

**Arquivo:** `router/principal_router.py`  
**Função:** `processar_mensagem_operacional()` (antes de entrar em B-INICIO)  
**Linhas:** 7555-7558  

```python
# =========================================================
# ✅ (C) Bloqueio de data no passado -> pergunta amanhã mesmo horário
# =========================================================
if ctx.get("data_hora"):
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])
```

**Entrada:** 
- `ctx["data_hora"] = "2026-09-10T00:00:00"`
- `_agora_br_naive() = 2026-09-10 09:56:30 (aprox)`

**Verificação:**
- `dt_naive_existente = 2026-09-10 00:00:00`
- `00:00 <= 09:56:30` ? **SIM**
- Condição passa: chama `_perguntar_amanha_mesmo_horario_e_bloquear()`

**Causa Raiz neste Ponto:** O código interpreta qualquer data com hora `00:00` como um horário no passado, mesmo que `data_sem_hora = True` indique que não há horário válido.

---

### G) RESPOSTA AO USUÁRIO — `router/principal_router.py:4438-4483`

**Arquivo:** `router/principal_router.py`  
**Função:** `_perguntar_amanha_mesmo_horario_e_bloquear(data_hora_iso: str)`  
**Linhas:** 4438-4483  

```python
async def _perguntar_amanha_mesmo_horario_e_bloquear(data_hora_iso: str):
    # ...
    draft_local = ctx.get("draft_agendamento") or {}
    prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
    servico = draft_local.get("servico") or ctx.get("servico")

    # prepara bloqueio de amanhã
    ctx["estado_fluxo"] = "aguardando_data"
    ctx["pergunta_amanha_mesmo_horario"] = True
    ctx["data_hora_pendente"] = data_hora_iso
    ctx["data_hora"] = None

    # ...

    # ✅ primeiro coletar mínimo (serviço OU profissional)
    if not (prof or servico):
        return await _send_and_stop(
            context,
            user_id,
            (
                f"Esse horário (*{formatar_data_hora_br(data_hora_iso)}*) já passou.\n"
                "Só me diz rapidinho: *qual serviço* você quer fazer (ou *com qual profissional* prefere), "
                "pra eu conferir a agenda certinho."
            )
        )
```

**Entrada:** `data_hora_iso = "2026-09-10T00:00:00"`  
**Formatação:** `formatar_data_hora_br("2026-09-10T00:00:00")` = `"10/09/2026 às 00:00"`  
**Saída:** 
```
Esse horário (10/09/2026 às 00:00) já passou.
Só me diz rapidinho: qual serviço você quer fazer (ou com qual profissional prefere), pra eu conferir a agenda certinho.
```

**Causa Raiz neste Ponto:** A resposta é construída corretamente, mas baseada em premissas erradas. O fluxo anteriormente decidiu que `"2026-09-10T00:00:00"` é um horário que o usuário solicitou e que passou.

---

## 🎯 CAUSA RAIZ — ANÁLISE FINAL

### Cadeia de Problemas (em ordem de ocorrência):

```
PONTO A: Classificador não distingue tipo de consulta de disponibilidade
         ↓
PONTO B: Objetivo assume que toda consulta de disponibilidade é para agendar
         ↓
PONTO C: Parser retorna hora do parse (9:56) em vez de None para "hoje" puro
         ↓
PONTO D: Mesclar transforma data sem hora em T00:00:00
         ↓
PONTO E: Fluxo de agendamento é acionado com objetivo "descobrir_servico"
         ↓
PONTO F: Bloqueio de horário passado valida 00:00 como horário real
         ↓
PONTO G: Resposta interpreta 00:00 como horário que passou
```

### Causa Raiz Primária:

**FALTA DE INTENÇÃO OPERACIONAL PARA "CONSULTAR AGENDAMENTOS DO USUÁRIO"**

A mensagem "Tenho alguma coisa agendada para hoje?" deveria:
1. ✅ Ser reconhecida como consulta de agenda do usuário
2. ✅ Disparar fluxo de consulta (NOT agendamento)
3. ✅ Buscar eventos do usuário em Firestore
4. ✅ Responder com lista ou "Não tem agendamentos"

Mas em vez disso:
1. ❌ É classificada como "consulta_disponibilidade_aberta"
2. ❌ Objetivo vira "descobrir_servico_para_consulta"
3. ❌ Entra em fluxo de agendamento
4. ❌ Transforma "hoje" em "00:00"
5. ❌ Bloqueia "00:00" como passado
6. ❌ Responde pedindo serviço/profissional

---

## 🔍 ROTAS EXISTENTES NO CÓDIGO

### Rotas Implementadas:
✅ `responder_consulta_informativa()` — arquivo `services/informacao_service.py`
- Responde sobre endereço, serviços, preços
- Consulta disponibilidade para AGENDAR
- **NÃO** consulta agendamentos do usuário

### Rotas Não Implementadas:
❌ `consultar_agendamentos_usuario()` — não existe
❌ `listar_eventos_do_dia()` — não existe  
❌ `meus_agendamentos()` — não existe

**Por que a rota de consulta informativa não foi usada?**
- `responder_consulta_informativa()` só responde se a mensagem contiver gatilhos específicos como:
  - "quem tem disponível"
  - "quem faz"
  - "quanto custa"
  - "onde fica"
- "Tenho alguma coisa agendada para hoje?" não contém esses gatilhos
- Logo, retorna `None` e o fluxo cai na rota de agendamento

---

## 🚨 CAUSAS SECUNDÁRIAS

### 1. Data sem Hora → 00:00 é Problemático
**Arquivo:** `router/principal_router.py:1633-1641`  
**Problema:** Quando não há hora anterior, defaulta para `T00:00:00`  
**Consequência:** Qualquer data "pura" se torna "00:00" que é sempre no passado  
**Solução Temporária:** Deveria manter flag `data_sem_hora=True` e não validar como horário passado

### 2. Bloqueio de Horário Passado não Respeita `data_sem_hora`
**Arquivo:** `router/principal_router.py:7555-7558`  
**Problema:** Verifica `<= agora()` sem considerar `ctx.get("data_sem_hora")`  
**Consequência:** Todas as datas `00:00` são bloqueadas como passado  
**Solução:** Adicionar guarda: `if ctx.get("data_hora") and not ctx.get("data_sem_hora")`

### 3. Classificador não Diferencia Consultas
**Arquivo:** `services/classificador_conversa.py:338-339`  
**Problema:** Uma única intenção `"consulta_disponibilidade_aberta"` para dois casos diferentes  
**Consequência:** Fluxos completo mix-up  
**Solução:** Diferenciar em nível de features ou contexto

---

## 📋 ARQUIVOS QUE PRECISARIAM SER ALTERADOS

1. **services/classificador_conversa.py**
   - Adicionar detecção de "meus agendamentos" vs "disponibilidade para agendar"
   - Possível: adicionar check para `ctx.get("tem_agendamento_pessoal")`

2. **router/principal_router.py**
   - Adicionar proteção `if not ctx.get("data_sem_hora")` antes de bloquear por horário passado
   - Redirecionar "consulta_agendamentos_usuario" para fluxo de consulta (não agendamento)

3. **services/informacao_service.py**
   - Adicionar função para consultar agendamentos do usuário
   - Implementar busca em Firestore por eventos do usuário

4. **prompts/manual_secretaria.py** (se usar GPT)
   - Adicionar exemplos de "meus agendamentos" para GPT não confundir

5. **utils/interpretador_datas.py**
   - Retornar `None` quando é apenas data sem horário explícito
   - Ou retornar um objeto especial que distingua "data sem hora" de "data com hora"

---

## 🧪 TESTE DE REPRODUÇÃO DO BUG

```python
# Teste: Consultar agendamentos do usuário para hoje
usuario_msg = "Tenho alguma coisa agendada para hoje?"
esperado = "Sim, você tem: [lista de agendamentos] OU Não, você não tem agendamentos"
observado = "Esse horário (10/09/2026 às 00:00) já passou. Só me diz qual serviço..."

# Casos Adjacentes para Proteção:

# Caso 1: Variação de linguagem (como perguntar agendamentos)
"O que tenho agendado hoje?"
→ Deveria: Listar agendamentos
→ Atualmente: Entra em fluxo de agendamento

# Caso 2: Perguntar sobre dia diferente
"Tenho horário marcado amanhã?"
→ Deveria: Listar agendamentos para amanhã
→ Atualmente: Entra em fluxo de agendamento com data errada

# Caso 3: Diferenciar de consulta de disponibilidade real
"Tem horário disponível hoje?"
→ Deveria: Perguntar qual serviço/profissional
→ Atualmente: Correto (mas pode confundir com caso anterior)
```

---

## ✅ VERIFICAÇÃO ARQUITETURAL

**Regra de Arquitetura:** GPT nunca deve decidir sobre disponibilidade ou criação de evento.

**Status:** ✅ RESPEITADA
- O bug não vem de GPT fazendo cálculo errado
- Vem de rotas determinísticas no código estarem faltando

**Conclusão:** O sistema mantém separação correta (GPT = linguagem, Código = lógica). O problema é que a lógica determinística não contempla a rota de "consultar agendamentos do usuário".

---

## 📊 RESUMO EXECUTIVO

| Ponto | Arquivo | Função | Linha | Problema | Severidade |
|-------|---------|--------|-------|----------|------------|
| A | services/classificador_conversa.py | classificar_intencao_conversacional() | 338-339 | Intenção não distingue tipos de consulta | 🟠 Alta |
| B | router/principal_router.py | processar_mensagem_operacional() | 4134-4135 | Objetivo assume agendamento em vez de consulta | 🟠 Alta |
| C | utils/interpretador_datas.py | interpretar_data_e_hora() | 239-252 | Parser retorna hora do parse em vez de None | 🟡 Média |
| D | router/principal_router.py | processar_mensagem_operacional() | 1633-1641 | Mesclar transforma data pura em 00:00 | 🟠 Alta |
| E | router/principal_router.py | processar_mensagem_operacional() | 5000-9000 | Fluxo B-INICIO é acionado para consulta | 🟠 Alta |
| F | router/principal_router.py | processar_mensagem_operacional() | 7555-7558 | Bloqueio não respeita flag data_sem_hora | 🟠 Alta |
| G | router/principal_router.py | _perguntar_amanha_mesmo_horario_e_bloquear() | 4438-4483 | Resposta interpreta 00:00 como horário | 🟢 Baixa (consequência) |

---

**Investigação Concluída**  
**Próximos Passos:** Implementar rota de consulta de agendamentos do usuário (não implementada)

