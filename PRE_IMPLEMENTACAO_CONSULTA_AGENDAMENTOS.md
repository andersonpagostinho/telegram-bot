# PRÉ-IMPLEMENTAÇÃO TÉCNICA — Consulta de Agendamentos do Usuário

**Data:** 2026-09-14  
**Status:** Análise Técnica Validada — Pronto para Implementação (NENHUMA ALTERAÇÃO FEITA)

---

## 1. PRINCIPAL_ROUTER.PY — PONTO EXATO DE DIFERENCIAÇÃO

**Arquivo:** `router/principal_router.py`  
**Função:** Anônima em `roteador_principal()`  
**Seção:** CAMADA 1.1 — OBJETIVO CONVERSACIONAL  
**Linhas Exatas:** 4127-4163

### Código Atual:

```python
# Linha 4127-4135
if preservar_continuidade_data:
    intencao_conv = ctx.get("intencao_conversacional")
else:
    intencao_conv = class_intencao.get("intencao_conversacional")

objetivo_conversacional = None

if intencao_conv == "consulta_disponibilidade_aberta":
    objetivo_conversacional = "descobrir_servico_para_consulta"  # ← AQUI
```

### Variáveis Disponíveis Neste Ponto:

```python
# Contexto (ctx):
ctx["estado_fluxo"]                    # "idle", "aguardando_servico", etc.
ctx["draft_agendamento"]               # dict com slots (None se vazio)
ctx["servico"]                         # string ou None
ctx["profissional_escolhido"]          # string ou None
ctx["data_hora"]                       # ISO string ou None
ctx["aguardando_confirmacao_agendamento"]  # bool

# Classificação:
intencao_conv                          # "consulta_disponibilidade_aberta"
class_intencao.get("intencao_conversacional")  # mesma

# Flags de preservação:
preservar_continuidade_data            # bool
preservar_confirmacao_pendente         # bool

# Métodos auxiliares disponíveis (já importados):
tem_contexto_agendamento_ativo(ctx)    # função definida em arquivo
eh_confirmacao_pendente_ativa(ctx)     # função definida em arquivo
```

### Condição de Diferenciação (PROPOSTA):

**Algoritmo determinístico:**

```python
if intencao_conv == "consulta_disponibilidade_aberta":
    # Diferenciação de objetivo baseada no contexto
    
    # Critério 1: Se há fluxo ativo de agendamento
    #            → continuar em "descobrir_servico_para_consulta"
    em_fluxo_agendamento = ctx.get("estado_fluxo") in [
        "aguardando_servico",
        "aguardando_profissional",
        "aguardando_horario",
        "agendando",
        "aguardando_confirmacao"  # não em idle
    ]
    
    # Critério 2: Se há draft ou confirmação pendente
    #            → continuar em "descobrir_servico_para_consulta"
    tem_agendamento_pendente = (
        bool(ctx.get("draft_agendamento")) or
        bool(ctx.get("aguardando_confirmacao_agendamento"))
    )
    
    # Critério 3: Se está em estado_fluxo="idle" E
    #            não há draft E
    #            não há confirmação pendente
    #            → novo objetivo "consultar_agendamentos_usuario"
    
    if em_fluxo_agendamento or tem_agendamento_pendente:
        objetivo_conversacional = "descobrir_servico_para_consulta"
    else:
        objetivo_conversacional = "consultar_agendamentos_usuario"  # NOVO
```

### Validação de Casos:

| Mensagem | estado_fluxo | draft | confirmacao | Objetivo Esperado | Resultado |
|----------|--------------|-------|-------------|-------------------|-----------|
| "Tenho algo agendado hoje?" | idle | None | False | consultar_agendamentos_usuario | ✅ Novo |
| "Tem disponível hoje?" | idle | None | False | consultar_agendamentos_usuario | ⚠️ Problema |
| "Tem vaga?" (em contexto idle) | idle | None | False | consultar_agendamentos_usuario | ⚠️ Problema |

**DESCOBERTA:** A diferenciação por contexto NÃO é suficiente.

"Tem disponível hoje?" também ativa `consulta_disponibilidade_aberta` e chegará com `estado_fluxo="idle"`.

---

## 🚨 PROBLEMA ARQUITETURAL DESCOBERTO

**A intenção `consulta_disponibilidade_aberta` cobre DOIS casos semanticamente diferentes:**

1. **"Tenho alguma coisa agendada para hoje?"** ← Consultar MEUS agendamentos
2. **"Tem horário disponível para marcar hoje?"** ← Consultar DISPONIBILIDADE para agendar

**Ambos têm mesmas features:**
- tem_pergunta = True
- tem_tempo = True
- tem_indefinido = True

**O contexto (estado_fluxo) não diferencia porque ambos chegam com estado_fluxo="idle"**

---

## SOLUÇÃO ALTERNATIVA PROPOSTA

**Ao invés de diferenciação por objetivo:**

Adicionar **filtro léxico no classificador** ANTES da atribuição de objetivo.

**Implementar em `classificador_conversa.py` (novo bloco antes da linha 338):**

```python
# NOVO: Detecção de "consultar meus agendamentos"
tem_posessivo = _tem(r"\b(tenho|meu|minha|meus|minhas|com que|agendado|marcado|compromisso)\b", t)
tem_referencia_pessoal = (
    "tenho" in t or
    "o que tenho" in t or
    "qual é meu" in t or
    "meus" in t
)

if f["tem_pergunta"] and f["tem_tempo"] and (tem_posessivo or tem_referencia_pessoal):
    # Novo: consultar meus agendamentos
    return {"intencao_conversacional": "consultar_agendamentos_usuario", "confianca": 85, "features": f}

if f["tem_pergunta"] and f["tem_tempo"] and f["tem_indefinido"]:
    # Antigo: disponibilidade para agendar
    return {"intencao_conversacional": "consulta_disponibilidade_aberta", "confianca": 88, "features": f}
```

**IMPACTO:** Novo ramo em `classificador_conversa.py` (não em objetivo)

---

## 2. INFORMACAO_SERVICE.PY — FUNÇÕES EXISTENTES

**Arquivo:** `services/informacao_service.py`  
**Linhas:** 71-311

### Funções Encontradas:

#### A. `responder_consulta_informativa(mensagem: str, user_id: str) -> str | None`
**Linha:** 71  
**O que faz:** Responde consultas informativas (endereço, preços, serviços, disponibilidade)  
**Retorna:** String (resposta) ou None (não é consulta informativa)  

**Gatilhos existentes:**
- "endereco", "onde fica" → endereço
- "servi" + "oferec"/"tem" → lista serviços
- "quem faz" → profissionais por serviço
- "quanto custa" → preços
- "quem tem disponivel" → disponibilidade

**Problema:** NÃO tem gatilho para "tenho agendado", "o que tenho agendado", etc.

**Decisão:** Adicionar novo bloco gatilho aqui OU criar wrapper que chama `buscar_eventos_por_intervalo()`

#### B. Nenhuma outra função de consulta de eventos encontrada

**Conclusão:** A função a reutilizar é `buscar_eventos_por_intervalo()` de `event_service_async.py`, não algo em `informacao_service.py`.

---

## 3. EVENT_SERVICE_ASYNC.PY — ASSINATURA REAL

**Arquivo:** `services/event_service_async.py`  
**Linha:** 192-256

### Assinatura Exata:

```python
async def buscar_eventos_por_intervalo(
    user_id: str,
    dias: int = 0,           # dias offset (+0 = hoje, +1 = amanhã)
    semana: bool = False,    # intervalo de semana
    dia_especifico: date | None = None  # data específica
) -> list[dict]
```

### Funcionamento Técnico:

**Linha 199-207 (Resolução de tenant):**
```python
dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
user_id_efetivo = user_id

if dados_usuario:
    tipo = dados_usuario.get("tipo_usuario", "cliente")
    modo = dados_usuario.get("modo_uso", "")
    if tipo == "cliente" or modo == "atendimento_cliente":
        user_id_efetivo = await obter_id_dono(user_id)

eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
```

**Resolução de Tenant:** ✅ AUTOMÁTICA
- Se user_id é cliente → resolve para tenant (dono)
- Se user_id é dono → usa direto
- Consulta: `Clientes/{tenant_id}/Eventos`

**Filtro de Eventos (Linha 231):**
```python
if evento_deve_ser_ignorado(evento, event_id):
    continue  # pula eventos cancelados, etc.
```

**Retorno (Linha 248-250):**
```python
ev_out = dict(evento)
ev_out["event_id"] = event_id  # ✅ preserva ID
resultado.append(ev_out)
```

### Estrutura de Retorno (Evento):

```python
{
    "servico": "corte",
    "profissional": "Amanda",
    "data": "2026-09-10",          # formato YYYY-MM-DD
    "hora_inicio": "10:00",        # formato HH:MM
    "duracao": 30,                 # minutos
    "cliente_id": "7371670478",    # user_id do cliente
    "status": "confirmado",        # "confirmado", "cancelado", etc.
    "event_id": "abc123..."        # adicionado pela função
}
```

### Como Usar:

```python
# Hoje
eventos_hoje = await buscar_eventos_por_intervalo(user_id=user_id, dias=0)

# Amanhã
eventos_amanha = await buscar_eventos_por_intervalo(user_id=user_id, dias=1)

# Dia específico
from datetime import datetime, date
data = date(2026, 9, 10)
eventos_data = await buscar_eventos_por_intervalo(user_id=user_id, dia_especifico=data)

# Próxima semana
eventos_semana = await buscar_eventos_por_intervalo(user_id=user_id, semana=True)
```

---

## 4. FILTRO POR SERVIÇO

**Pergunta:** "Tenho corte hoje?"

### Análise:

O classificador vai detectar:
- tem_pergunta = True ("?")
- tem_tempo = True ("hoje")
- tem_contexto_servico = True ("corte")
- tem_indefinido = False (não tem "algo", "alguma")

**Intenção resultante:** NÃO é `consulta_disponibilidade_aberta`

**Provavelmente:** `consulta_disponibilidade_servico` (linha 355 do classificador)

```python
if f["tem_pergunta"] and f["tem_contexto_servico"]:
    return {"intencao_conversacional": "consulta_disponibilidade_servico", ...}
```

### Solução Necessária:

Mesmo tratamento da "consulta_disponibilidade_aberta":
- Adicionar novo ramo no classificador para "consultar_agendamentos_usuario_com_servico"
- OU filtrar post-hoc nos eventos retornados

**Recomendação:** Adicionar check léxico de posessivo TAMBÉM no ramo de `consulta_disponibilidade_servico`

```python
# NOVO: Adicionar antes da linha 355
tem_posessivo_servico = _tem(r"\b(tenho|meu|minha|agendado|marcado)\b", t) and f["tem_contexto_servico"]

if f["tem_pergunta"] and f["tem_contexto_servico"] and tem_posessivo_servico:
    # Novo: consultar meus agendamentos de serviço específico
    return {"intencao_conversacional": "consultar_agendamentos_usuario", "confianca": 85, "features": f}

if f["tem_pergunta"] and f["tem_contexto_servico"]:
    # Antigo: quem faz este serviço?
    return {"intencao_conversacional": "consulta_disponibilidade_servico", "confianca": 85, "features": f}
```

### Problema com Filtragem Post-hoc:

Se retornarmos todos os eventos e filtrar em Python, corremos risco de mostrar eventos de outro serviço por acidente.

**Decisão:** Melhor filtrar no classificador (mais seguro).

---

## 5. "QUAL É MEU PRÓXIMO HORÁRIO?"

### Análise:

- tem_pergunta = True ("?")
- tem_indefinido = False (não tem "algo", "alguma")
- tem_tempo = False (apenas "próximo", sem data/hora específica)
- tem_contexto_servico = False

**Intenção provavelmente:** `indefinida` (fallback, linha 375)

**Problema:** O classificador não detecta essa intenção

### Solução Necessária:

Adicionar novo padrão de detecção **antes** de `indefinida`:

```python
# NOVO: Adicionar na função classificar_intencao_conversacional
tem_referencia_proxima = _tem(r"\b(proximo|próximo|nex|seguinte|vem ai)\b", t)
tem_referencia_meu = _tem(r"\b(tenho|meu|minha|meus|agendado)\b", t)

if f["tem_pergunta"] and (tem_referencia_proxima or tem_referencia_meu):
    # Novo objetivo: obter próximo evento
    return {"intencao_conversacional": "consultar_agendamentos_usuario", "confianca": 80, "features": f}
```

### Implementação do Próximo Evento:

```python
# No bloco de novo objetivo em principal_router.py
if objetivo_conversacional == "consultar_agendamentos_usuario":
    # Chamar buscar_eventos_por_intervalo com intervalo amplo (próximos 30 dias)
    # Depois selecionar o com data mais próxima
    
    from datetime import datetime, timedelta
    hoje = datetime.now().date()
    proximos_30 = []
    
    for dias_offset in range(0, 31):
        eventos = await buscar_eventos_por_intervalo(
            user_id=user_id,
            dias=dias_offset
        )
        proximos_30.extend(eventos)
    
    if proximos_30:
        # Ordenar por data + hora
        proximos_30.sort(
            key=lambda ev: (ev.get("data", ""), ev.get("hora_inicio", ""))
        )
        proximo = proximos_30[0]
        # responder com proximo
    else:
        # "você não tem agendamentos"
```

---

## 6. DATA SEM HORA — ANÁLISE DE IMPACTO

**Arquivo:** `utils/interpretador_datas.py`  
**Função:** `interpretar_data_e_hora(texto: str) -> datetime | None`

### Chamadores Críticos:

**Busca por chamadas:**

```bash
grep -r "interpretar_data_e_hora" --include="*.py"
```

**Encontrados:**
1. `router/principal_router.py:1353` — Bloco MESCLAR
2. `services/event_service_async.py:414` — `detectar_bloqueio_agenda_salao()`
3. `services/informacao_service.py:204` — `responder_consulta_informativa()` (disponibilidade)

### Impacto de Retornar None:

| Chamador | Linha | O Que Faz | Impacto de None |
|----------|-------|----------|-----------------|
| MESCLAR | 1353-1665 | Processa data/hora | ✅ Seguro (tem checks para None) |
| detectar_bloqueio_agenda_salao | 414 | Bloqueia datas | ✅ Seguro (tem checks para None) |
| responder_consulta_informativa | 204 | Consulta avail | ⚠️ Retorna "qual dia?" (fallback) |

### Verificação no MESCLAR:

**Linha 1353:**
```python
dt_detectado = interpretar_data_e_hora(texto)

# ... mais abaixo
if dt_detectado:  # ← CHECK
    # processa data/hora
else:
    # se não há data detectada, não faz nada
```

✅ **Seguro:** Tem check `if dt_detectado`

### Conclusão:

Retornar `None` para "data pura" **NÃO quebra** os chamadores existentes.

**MUDANÇA PROPOSTA:**

Em `utils/interpretador_datas.py` (linhas ~239-252):

```python
# ANTES:
if ("hoje" in texto_norm or "amanh" in texto_norm) and \
   re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm):
    # tem hora explícita → montar com hora
    ...

# DEPOIS:
if "hoje" in texto_norm or "amanh" in texto_norm:
    if re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm):
        # tem hora explícita → montar com hora
        ...
    else:
        # SEM hora explícita → retornar None
        return None  # ← NOVO
```

---

## 7. GUARD DE HORÁRIO PASSADO

**Arquivo:** `router/principal_router.py`  
**Linhas Exatas:** 7555-7558

### Código Atual:

```python
if ctx.get("data_hora"):
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])
```

### Problema:

`data_hora = "2026-09-10T00:00:00"` (sem hora real) é bloqueado como passado.

### Solução Técnica:

**Flag já existe:** `ctx.get("data_sem_hora")`

Definido em linha 1646: `ctx["data_sem_hora"] = True`

### Mudança Proposta:

```python
# ANTES:
if ctx.get("data_hora"):
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])

# DEPOIS:
if ctx.get("data_hora") and not ctx.get("data_sem_hora"):  # ← ADD guard
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])
```

**Impacto:** +1 condicional (ultra-seguro)

### Casos Cobertos:

| Entrada | data_sem_hora | Ação |
|---------|---------------|------|
| "2026-09-10T15:30" | False | Verifica se passou (bloqueia se sim) |
| "2026-09-10T00:00" | True | SKIPA verificação (novo objetivo) |
| "2026-09-10T00:00" | False (bug) | Verifica (bloqueia se passou) |
| None | False | Skipa (check `if ctx.get()`) |

---

## 8. PERFORMANCE — CARREGAMENTOS DESNECESSÁRIOS

**Log observado:**
```
[DOC] Documento encontrado em Clientes/7394370553/Profissionais/Amanda: {...}
[DOC] Documento encontrado em Clientes/7394370553/Profissionais/Bruna: {...}
[DOC] Documento encontrado em Clientes/7394370553/Profissionais/Carla: {...}
... (6 profissionais carregados)
```

### Causa:

Fluxo de agendamento (B-INICIO) carrega profissionais para processar `descobrir_servico_para_consulta`.

### Solução:

Novo objetivo `consultar_agendamentos_usuario` deve sair **antes** de B-INICIO.

**Pseudocódigo:**

```python
# No roteador_principal(), após objetivo ser definido (linha 4160):

if ctx.get("objetivo_conversacional") == "consultar_agendamentos_usuario":
    # ✅ SAIR CEDO — não entrar em B-INICIO
    # Executar consulta de eventos
    # Responder
    return {...}

# Resto do fluxo (B-INICIO, etc.) só executa para outros objetivos
```

### Localização de Saída:

Após linha 4163 (print de objetivo conversacional), ANTES de qualquer outro processamento.

---

## 9. TENANT/ACTOR — VALIDAÇÃO

### Verificação de `buscar_eventos_por_intervalo()`:

```python
# Linhas 199-207
dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
user_id_efetivo = user_id

if dados_usuario:
    tipo = dados_usuario.get("tipo_usuario", "cliente")
    if tipo == "cliente" or modo == "atendimento_cliente":
        user_id_efetivo = await obter_id_dono(user_id)

eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
```

✅ **Validan Tenant:** SIM
- Resolve `user_id` → `tenant_id` (dono)
- Busca em `Clientes/{tenant_id}/Eventos`
- Não usa chave global

✅ **Isolamento Multi-tenant:** SIM
- User A não consegue eventos de User B (paths diferentes)

✅ **Reutilizável:** SIM
- Mesma função usada em cancelamento, listagem, etc.

---

## 10. TESTES EXISTENTES

### Busca de Testes:

```bash
find . -name "test_*.py" -o -name "*_test.py" | xargs grep -l "evento\|agendament\|buscar_evento"
```

### Testes Encontrados:

| Arquivo | Tipo | Função Testada | Padrão |
|---------|------|----------------|--------|
| `test_agenda_service_p0.py` | P0 | Agendamento completo | Firestore real |
| `test_ponta_a_ponta.py` | E2E | Fluxo até confirmação | Firestore real |
| `test_e2e_patch.py` | E2E | Alterações recentes | Firestore real |
| `test_confirmacao_reserva_patch.py` | Patch | Confirmação | Firestore real |

### Padrão de Setup:

```python
@pytest.mark.asyncio
async def test_exemplo():
    user_id = "7371670478"  # ID real do tenant
    tenant_id = await obter_id_dono(user_id)
    
    # 1. Preparar evento em Firestore
    path = f"Clientes/{tenant_id}/Eventos/evt_001"
    await salvar_dado_em_path(path, {
        "servico": "corte",
        "profissional": "Amanda",
        "data": "2026-09-10",
        "hora_inicio": "10:00",
        ...
    })
    
    # 2. Chamar função
    resultado = await buscar_eventos_por_intervalo(
        user_id=user_id,
        dia_especifico=date(2026, 9, 10)
    )
    
    # 3. Validar
    assert len(resultado) == 1
    assert resultado[0]["servico"] == "corte"
```

### Como Reutilizar:

```python
# Novo teste:
async def test_consultar_agendamentos_usuario():
    # Use EXATAMENTE o padrão acima
    # Prepara evento
    # Chama novo objetivo_conversacional="consultar_agendamentos_usuario"
    # Valida resposta
```

---

## MATRIZ FINAL — CONSOLIDAÇÃO

| Caso | Intenção Atual | Objetivo Atual | Objetivo Correto | Função Existente | Alteração Necessária |
|------|----------------|-----------------|------------------|------------------|----------------------|
| **"Tenho alguma coisa agendada para hoje?"** | consulta_disponibilidade_aberta | descobrir_servico_para_consulta | consultar_agendamentos_usuario | buscar_eventos_por_intervalo | Nova intenção NO classificador |
| **"O que tenho agendado hoje?"** | (nova) indefinida | indefinida | consultar_agendamentos_usuario | buscar_eventos_por_intervalo | Nova intenção NO classificador |
| **"Tenho horário marcado amanhã?"** | (nova) indefinida | indefinida | consultar_agendamentos_usuario | buscar_eventos_por_intervalo | Nova intenção NO classificador |
| **"Qual é meu próximo horário?"** | indefinida | indefinida | consultar_agendamentos_usuario | buscar_eventos_por_intervalo | Nova intenção NO classificador |
| **"Tenho corte hoje?"** | consulta_disponibilidade_servico | consultar_disponibilidade_por_servico | consultar_agendamentos_usuario | buscar_eventos_por_intervalo | Nova intenção NO classificador |
| **"Tem horário disponível hoje?"** | consulta_disponibilidade_aberta | descobrir_servico_para_consulta | descobrir_servico_para_consulta (SEM mudança) | buscar_profissionais_disponiveis | Nenhuma |
| **"Tem vaga amanhã?"** | consulta_disponibilidade_aberta | descobrir_servico_para_consulta | descobrir_servico_para_consulta (SEM mudança) | buscar_profissionais_disponiveis | Nenhuma |
| **"Quero marcar um corte hoje"** | agendamento_direto | preparar_prechecagem_agendamento | preparar_prechecagem_agendamento (SEM mudança) | - | Nenhuma |

---

## 🚨 PIVÔ CRÍTICO ENCONTRADO

**A análise revelou que a Opção B (novo objetivo) NÃO É SUFICIENTE.**

**Razão:** A intenção `consulta_disponibilidade_aberta` cobre 2 casos radicalmente diferentes, ambos chegando com `estado_fluxo="idle"`.

**Recomendação:** **IMPLEMENTAR OPÇÃO A MODIFICADA**

```
Novo: "consultar_agendamentos_usuario" (INTENÇÃO)
      ↓
Novo Objetivo: "consultar_agendamentos_usuario"
      ↓
Novo Roteamento: buscar eventos + responder
```

---

## ARQUIVOS QUE REALMENTE PRECISAM MUDAR

### A. Arquivo Primário:

**`services/classificador_conversa.py`** (NOVA INTENÇÃO)
- Linha 338-339: Adicionar novo bloco ANTES de `consulta_disponibilidade_aberta`
- Padrão: detecção léxica de posessivo + features
- Confiança: 85-90
- Adicionar também bloco paralelo em `consulta_disponibilidade_servico` (linha 355)

### B. Arquivo Secundário:

**`router/principal_router.py`**
- Linha 4134-4150: Adicionar novo elif para `consultar_agendamentos_usuario`
- Novo bloco de roteamento (~linha 5500): Executar novo objetivo (antes de B-INICIO)
- Linha 7555: Adicionar guard `and not ctx.get("data_sem_hora")`

### C. Arquivo de Suporte:

**`utils/interpretador_datas.py`**
- Linha ~239-252: Retornar None para data pura

---

## FUNÇÕES EXATAS

### Serão CRIADAS:

1. **Nova intenção em classificador:**
   ```python
   "consultar_agendamentos_usuario"  # confianca 85-90
   ```

2. **Novo objetivo em principal_router:**
   ```python
   "consultar_agendamentos_usuario"
   ```

3. **Novo bloco de roteamento:**
   ```python
   if ctx.get("objetivo_conversacional") == "consultar_agendamentos_usuario":
       # executar consulta
   ```

### Serão REUTILIZADAS:

1. **`buscar_eventos_por_intervalo()`** ← USE ESTA
   ```python
   eventos = await buscar_eventos_por_intervalo(
       user_id=user_id,
       dia_especifico=data
   )
   ```

2. **`montar_frase_data_legivel()`**
   ```python
   frase = montar_frase_data_legivel(evento["data"])
   ```

3. **`salvar_contexto_temporario_v2()`**
   ```python
   await salvar_contexto_temporario_v2(dono_id, user_id, ctx)
   ```

---

## CONDIÇÕES EXATAS

### Classificador (novo padrão):

```python
# Padrão 1: Meus agendamentos
tem_posessivo = (
    "tenho" in t or
    "o que tenho" in t or
    "qual é meu" in t or
    "meu" in t or
    "agendado" in t or
    "marcado" in t or
    "compromisso" in t
)

if f["tem_pergunta"] and f["tem_tempo"] and tem_posessivo:
    return {
        "intencao_conversacional": "consultar_agendamentos_usuario",
        "confianca": 85,
        "features": f
    }
```

### Principal Router (novo roteamento):

```python
# Após objetivo conversacional (linha ~4165):
if ctx.get("objetivo_conversacional") == "consultar_agendamentos_usuario":
    # Extrair data do texto ou usar hoje
    data = interpretar_data_e_hora(texto_usuario).date() or date.today()
    
    # Buscar eventos
    eventos = await buscar_eventos_por_intervalo(
        user_id=user_id,
        dia_especifico=data
    )
    
    # Formatar resposta
    if eventos:
        # montar lista de eventos
        ...
        return await _send_and_stop(context, user_id, resposta)
    else:
        return await _send_and_stop(context, user_id, "Não, você não tem agendamentos para essa data")
```

---

## TESTES EXISTENTES QUE DEVEM SER REUTILIZADOS

1. **`test_agenda_service_p0.py`** — Padrão de setup Firestore
2. **`test_ponta_a_ponta.py`** — Fluxo E2E
3. **Testes de P0 regressão (174 tests)** — Estabilidade

---

## NOVOS TESTES NECESSÁRIOS

1. **Consultar agendamentos com eventos**
2. **Consultar agendamentos vazio**
3. **Agendamentos de serviço específico**
4. **Data/hora específica**
5. **Próximo evento**
6. **Classificação de nova intenção**

---

## RISCOS DE REGRESSÃO

| Risco | Severidade | Mitigação |
|-------|------------|-----------|
| Consulta de disponibilidade ("Tem vaga?") virar consulta de agendamentos | ALTA | Pattern léxico deve ser MUITO específico (posessivo obrigatório) |
| Data sem hora quebrar fluxos existentes | MÉDIA | Guard já existe; apenas respecitá-lo |
| Performance: duplo carregamento de eventos | BAIXA | Novo objetivo sai antes de B-INICIO |
| Multi-tenant isolamento | MUITO BAIXA | `buscar_eventos_por_intervalo` já resolve |

---

## SEQUÊNCIA EXATA DE IMPLEMENTAÇÃO

1. ✅ **Classificador** — Adicionar nova intenção (2 blocos, ~30 linhas)
2. ✅ **Principal Router** — Adicionar novo elif para objetivo (~2 linhas)
3. ✅ **Principal Router** — Adicionar novo bloco de roteamento (~80 linhas)
4. ✅ **Principal Router** — Adicionar guard de horário passado (1 linha)
5. ✅ **Interpretador Datas** — Retornar None para data pura (~5 linhas)
6. ✅ **Testes** — Novos testes de consulta (~200 linhas)
7. ✅ **Regressão** — 174 P0 + 42 P1

---

**STATUS FINAL:** Pré-implementação VALIDADA. Pronto para fase de código.

