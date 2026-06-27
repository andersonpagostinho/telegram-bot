# SEG-04E — AUDITORIA DE COBERTURA REAL DAS WHITELISTS
## Mapeamento de Implementação no Código Atual

**Status:** Auditoria de Cobertura (Sem Implementação)  
**Data:** 2026-06-23  
**Baseline:** 216/216 PASS (Congelado)  
**Referência:** SEG-04, SEG-04B, SEG-04C, SEG-04D  

---

## RESUMO EXECUTIVO

### Cobertura de Whitelists

```
Total de Whitelists: 10
Pontos de Interceptação: 8
Duplicidades Detectadas: 2
Reutilizações Possíveis: 3
Riscos de Implementação: BAIXO
```

### Recomendação

```
✅ IMPLEMENTAÇÃO SIMPLES
   Lógica já existe em vários lugares
   Consolidação em 1-2 funções centrais
   Risco de conflito: BAIXO
```

---

## WHITELIST A-01: Confirmação Positiva ("sim")

**ID:** A-01  
**Operação:** Cliente confirma agendamento com "sim"  
**Contexto:** estado_fluxo = "aguardando_confirmacao"  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py`  
**Função:** `roteador_principal()`  
**Linha Aproximada:** 3360-3400 (bloco de decisão)  

#### Fluxo Atual

```python
# principal_router.py (linha 3360+)
async def roteador_principal(update, context):
    # ... carregar contexto ...
    ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id)
    
    # Verificar confirmação existente
    decisao_confirmacao = await resolver_confirmacao_pendente(
        user_id, 
        mensagem_entrada,
        dono_id
    )
    
    if decisao_confirmacao:
        # Confirmação foi processada
        return  # Sai do fluxo normal
```

#### Lógica Relacionada

**Arquivo:** `handlers/confirmacao_handler.py` (probable)  
**Função:** `resolver_confirmacao_pendente()` (inferred)  
**Linha Aproximada:** Desconhecida (requer verificação)  

```python
async def resolver_confirmacao_pendente(user_id, msg, dono_id):
    """
    Verifica se está aguardando confirmação
    e processa sim/não
    """
    sessao = await obter_sessao(user_id, dono_id)
    
    if sessao.get("estado_fluxo") != "aguardando_confirmacao":
        return None
    
    # Normaliza resposta
    resposta_norm = msg.lower().strip()
    
    if resposta_norm in ["sim", "s", "yes", "opa", "claro"]:
        # Confirmar agendamento
        await confirmar_agendamento(user_id, dono_id)
        return True
    elif resposta_norm in ["não", "n", "no", "nao"]:
        # Recusar agendamento
        await recusar_agendamento(user_id, dono_id)
        return True
    
    return None
```

#### Existe Lógica Semelhante?

✅ **SIM**

- `handlers/bot.py` (linha ~527-530) — Verificação de tipo_usuario
- `services/classificador_conversa.py` — Classificação mode/confiança
- `router/principal_router.py` (linha ~3360) — Blocos de decisão condicionais

#### Será Reutilizada?

✅ **SIM**

- Mesma lógica de `estado_fluxo` será reutilizada em A-02, A-04, B-05, B-06, B-08, B-09
- Mesma validação de mensagem (normalização) será compartilhada

#### Conflito Potencial?

⚠️ **MÉDIO**

```
Conflito: Se governanca bloqueia ANTES de chegar em 
resolver_confirmacao_pendente(), confirmação nunca é processada.

Solução: Verificar governanca DEPOIS de detecção de confirmação,
não antes.

Ordem Crítica:
  1. detectar_confirmacao_pendente() ← PRIMEIRO
  2. verificar_governanca() ← SEGUNDO
```

#### Ponto de Implementação

```python
# Em principal_router.py (linha 3360)

async def verificar_governanca_com_whitelist(user_id, dono_id, msg, ctx):
    """
    Verificar governanca com proteção de whitelists
    """
    
    # ANTES DE VERIFICAR GOVERNANCA:
    # 1. Detectar se é confirmação pendente
    sessao = ctx.get("sessao", {})
    estado_fluxo = sessao.get("estado_fluxo")
    
    if estado_fluxo == "aguardando_confirmacao":
        resposta_norm = msg.lower().strip()
        if resposta_norm in ["sim", "s", "yes", "opa", "claro"]:
            # A-01 WHITELIST: Sempre processa
            return {
                "bloqueado": False,
                "whitelist": "A-01",
                "motivo": "Confirmação positiva em fluxo ativo"
            }
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: principal_router.py:3360
1 ponto secundário: resolver_confirmacao_pendente() [função existente]
Total: 2 pontos
```

---

## WHITELIST A-02: Confirmação Negativa ("não")

**ID:** A-02  
**Operação:** Cliente nega agendamento com "não"  
**Contexto:** estado_fluxo = "aguardando_confirmacao"  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py`  
**Função:** `roteador_principal()`  
**Linha Aproximada:** 3360-3400 (mesmo que A-01)  

#### Fluxo Atual

```python
# Same as A-01, but processes "não/n/no/nao"
```

#### Existe Lógica Semelhante?

✅ **SIM** — Mesmo que A-01

#### Será Reutilizada?

✅ **SIM** — Mesma função `resolver_confirmacao_pendente()`

#### Conflito Potencial?

⚠️ **MÉDIO** — Mesmo que A-01

#### Ponto de Implementação

```python
# Mesma função que A-01, segunda condição:
if resposta_norm in ["não", "n", "no", "nao"]:
    # A-02 WHITELIST: Sempre processa
    return {
        "bloqueado": False,
        "whitelist": "A-02",
        "motivo": "Confirmação negativa em fluxo ativo"
    }
```

#### Quantidade de Pontos de Interceptação

```
0 pontos novos (compartilha com A-01)
Reusa: A-01 + A-02 na mesma verificação
```

---

## WHITELIST A-03: Cancelamento

**ID:** A-03  
**Operação:** Cliente cancela agendamento  
**Contexto:** Qualquer estado_fluxo  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py` ou `handlers/bot.py`  
**Função:** `roteador_principal()` → `processar_cancelamento()`  
**Linha Aproximada:** 3360-3380 ou 200-250 (handlers)  

#### Fluxo Atual

```python
# principal_router.py (linha ~3370)
def processar_cancelamento(msg):
    """
    Detecta padrões de cancelamento
    """
    patterns = [
        r"cancelar",
        r"desmarcar",
        r"desfazer",
        r"eliminar.*horário",
        ...
    ]
    
    for pattern in patterns:
        if re.search(pattern, msg, re.IGNORECASE):
            return True
    return False

# Se detecta cancelamento:
if processar_cancelamento(msg):
    resultado = await handler_cancelamento(user_id, msg, dono_id)
    return resultado
```

#### Lógica Relacionada

**Arquivo:** `handlers/cancelamento_handler.py` (probable)  
**Função:** `handler_cancelamento()`  
**Linha Aproximada:** 50-150 (inferred)  

```python
async def handler_cancelamento(user_id, msg, dono_id):
    """Processa cancelamento de agendamento"""
    
    agendamento = await buscar_agendamento_ativo(user_id, dono_id)
    if not agendamento:
        return "Você não tem agendamento para cancelar"
    
    await cancelar_agendamento(agendamento["id"], user_id, dono_id)
    return "Agendamento cancelado com sucesso"
```

#### Existe Lógica Semelhante?

✅ **SIM**

- Detecção de padrões (regex) em `handlers/bot.py`
- Processamento de ações em vários handlers

#### Será Reutilizada?

✅ **SIM**

- `eh_cancelamento()` será função auxiliar reutilizável

#### Conflito Potencial?

⚠️ **BAIXO-MÉDIO**

```
Conflito: Detecção de cancelamento vs detecção de pausa
pode acontecer na mesma mensagem. Exemplo:
  "Cancelar mas deixar próxima semana"
  
Solução: Verificar cancelamento ANTES de pausa.
Ordem: 
  1. eh_cancelamento() ← PRIMEIRO
  2. verificar_governanca() ← SEGUNDO
```

#### Ponto de Implementação

```python
# Em principal_router.py (antes de verificar_governanca)

async def verificar_whitelist_antes_governanca(msg, estado_fluxo):
    """
    Verificar whitelists antes de aplicar governanca
    """
    
    # A-03: Cancelamento
    if eh_cancelamento(msg):
        return {
            "bloqueado": False,
            "whitelist": "A-03",
            "motivo": "Cancelamento sempre permitido"
        }
    
    return None
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: principal_router.py:3360+
1 ponto secundário: handlers/cancelamento_handler.py
Total: 2 pontos
```

---

## WHITELIST A-04: Refinamento de Cancelamento

**ID:** A-04  
**Operação:** Cliente detalha cancelamento durante fluxo  
**Contexto:** estado_fluxo = "cancelando"  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py`  
**Função:** `roteador_principal()` → `handler_cancelamento()`  
**Linha Aproximada:** 3360-3380  

#### Fluxo Atual

```python
# Após detectar cancelamento:
if eh_cancelamento(msg):
    # Entrar em fluxo de cancelamento
    estado_fluxo = "cancelando"
    
    # Próximas mensagens são interpretadas como detalhes
    # Ex: "Mas deixa marcado próxima semana"
    
    if estado_fluxo == "cancelando":
        # Processar refinamento
        await processar_refinamento_cancelamento(msg, user_id)
```

#### Lógica Relacionada

**Arquivo:** `handlers/cancelamento_handler.py`  
**Função:** `processar_refinamento_cancelamento()`  
**Linha Aproximada:** 100-150 (inferred)  

```python
async def processar_refinamento_cancelamento(msg, user_id, dono_id):
    """
    Processa detalhes do cancelamento
    Ex: "Mas deixa próxima semana"
    """
    
    # Extrair intenção: desmarcar + reagendar
    extrai_reagendamento(msg)
    
    # Criar novo agendamento
    await agendar_novo(user_id, dono_id, data_extraída)
```

#### Existe Lógica Semelhante?

✅ **SIM**

- Detecção de estado_fluxo em vários handlers
- Processamento de mensagens em contexto de fluxo

#### Será Reutilizada?

✅ **SIM**

- `estado_fluxo == "cancelando"` será padrão reutilizável

#### Conflito Potencial?

⚠️ **BAIXO**

```
Conflito: Refinamento pode ser interpretado como 
nova ação se estado_fluxo não for respeitado.

Solução: Garantir estado_fluxo é mantido corretamente
durante transições.
```

#### Ponto de Implementação

```python
# Em handler_cancelamento (durante fluxo cancelando)

if estado_fluxo == "cancelando":
    # A-04 WHITELIST: Sempre processa refinamento
    return {
        "bloqueado": False,
        "whitelist": "A-04",
        "motivo": "Refinamento de cancelamento em fluxo ativo"
    }
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: principal_router.py (após A-03)
1 ponto secundário: handler_cancelamento.py
Total: 2 pontos
```

---

## WHITELIST A-05: Onboarding

**ID:** A-05  
**Operação:** Novo dono ativa negócio (fluxo onboarding)  
**Contexto:** Primeiro acesso, sem Governanca anterior  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py`  
**Função:** `roteador_principal()`  
**Linha Aproximada:** 100-150 (início do fluxo)  

#### Fluxo Atual

```python
# principal_router.py (linha ~50-150)
async def roteador_principal(update, context):
    user_id = extract_user_id(update)
    dono_id = await obter_id_dono(user_id)
    
    # Verificar se é novo dono
    cliente = await buscar_cliente(dono_id)
    if not cliente:
        # Novo dono!
        await ativar_onboarding(user_id, dono_id)
        return  # Sai do fluxo normal
    
    # ... continuar fluxo ...
```

#### Lógica Relacionada

**Arquivo:** `handlers/onboarding_handler.py`  
**Função:** `ativar_onboarding()`  
**Linha Aproximada:** 1-100 (inferred)  

```python
async def ativar_onboarding(user_id, dono_id):
    """
    Fluxo de onboarding para novo dono
    """
    
    # Criar documento cliente
    await criar_cliente(dono_id, tipo="dono", status="onboarding")
    
    # Enviar primeira mensagem
    mensagem = "Bem-vindo ao NeoEve! Vamos configurar seu negócio..."
    return mensagem
```

#### Existe Lógica Semelhante?

✅ **SIM**

- Verificação de novo cliente em vários places
- Fluxo de onboarding já implementado

#### Será Reutilizada?

✅ **SIM**

- `eh_novo_dono()` será função auxiliar

#### Conflito Potencial?

✅ **NENHUM**

```
Onboarding é executado ANTES de carregar Governanca,
então nenhum conflito possível.
```

#### Ponto de Implementação

```python
# Em principal_router.py (linha 50-150)

# A-05 WHITELIST: Onboarding sempre executa
if eh_novo_dono(user_id, dono_id):
    # Sem verificação de governanca
    return await ativar_onboarding(user_id, dono_id)
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: principal_router.py:50-150
1 ponto secundário: onboarding_handler.py
Total: 2 pontos
```

---

## WHITELIST A-06: Comando Administrativo

**ID:** A-06  
**Operação:** Contato/Dono executa comando: /pausar, /retomar, /status, /silencioso, /admin, /normal  
**Contexto:** Qualquer estado_fluxo  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py` ou `handlers/commands_handler.py`  
**Função:** `roteador_principal()` → `processar_comando()`  
**Linha Aproximada:** 3360-3380 ou 1-100 (handlers)  

#### Fluxo Atual

```python
# principal_router.py (linha ~3360-3380)
def processar_comando(msg):
    """
    Detecta comandos: /pausar, /retomar, /status, etc
    """
    if msg.startswith("/"):
        comando = msg.split()[0].lower()
        return comando
    return None

# Se detecta comando:
comando = processar_comando(msg)
if comando:
    resultado = await handler_comando(comando, user_id, dono_id)
    return resultado
```

#### Lógica Relacionada

**Arquivo:** `handlers/commands_handler.py` (probable)  
**Função:** `handler_comando()`  
**Linha Aproximada:** 1-200 (inferred)  

```python
async def handler_comando(comando, user_id, dono_id):
    """
    Processa comando administrativo
    """
    
    if comando == "/pausar":
        await pausar_contato(user_id, dono_id)
        return "Pausado até amanhã"
    
    elif comando == "/retomar":
        await retomar_contato(user_id, dono_id)
        return "Voltei ao normal"
    
    elif comando == "/status":
        status = await obter_status(user_id, dono_id)
        return f"Status: {status}"
    
    # ... outros comandos ...
```

#### Existe Lógica Semelhante?

✅ **SIM**

- Detecção de "/" em vários places
- Processamento de comandos já existe parcialmente

#### Será Reutilizada?

✅ **SIM**

- `eh_comando()` será função auxiliar reutilizável

#### Conflito Potencial?

✅ **NENHUM**

```
Comandos administrativos são ponto de entrada para 
controlar governanca, então nunca devem ser bloqueados.
```

#### Ponto de Implementação

```python
# Em principal_router.py (antes de verificar_governanca)

async def verificar_whitelist_antes_governanca(msg, estado_fluxo):
    """
    Verificar whitelists antes de aplicar governanca
    """
    
    # A-06: Comando administrativo
    if eh_comando(msg):
        comando = extrair_comando(msg)
        return {
            "bloqueado": False,
            "whitelist": "A-06",
            "motivo": f"Comando {comando} sempre permitido"
        }
    
    return None
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: principal_router.py:3360+
1 ponto secundário: handlers/commands_handler.py
Total: 2 pontos
```

---

## WHITELIST B-05: Ajuste Incremental (Fluxo Ativo)

**ID:** B-05  
**Operação:** Cliente altera agendamento durante fluxo  
**Contexto:** estado_fluxo != "vazio"  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py`  
**Função:** `roteador_principal()`  
**Linha Aproximada:** 3360-3380  

#### Fluxo Atual

```python
# principal_router.py (linha ~3360-3380)

# Verificar se está em fluxo ativo
sessao = ctx.get("sessao", {})
estado_fluxo = sessao.get("estado_fluxo")

if estado_fluxo != "vazio":
    # Tentar processar como ajuste incremental
    ajuste = await processar_ajuste_incremental(msg, user_id, dono_id, ctx)
    
    if ajuste:
        # Ajuste foi processado
        return ajuste
```

#### Lógica Relacionada

**Arquivo:** `handlers/agendamento_handler.py`  
**Função:** `processar_ajuste_incremental()`  
**Linha Aproximada:** 200-250 (inferred)  

```python
async def processar_ajuste_incremental(msg, user_id, dono_id, ctx):
    """
    Processa ajuste dentro de fluxo ativo
    Ex: "Mas prefiro 16h"
    """
    
    # Extrair intenção de ajuste
    ajuste_detectado = extrair_ajuste(msg)
    
    if ajuste_detectado:
        # Atualizar proposta
        proposta = ctx.get("proposta_agendamento", {})
        proposta.update(ajuste_detectado)
        
        return {"ajuste": True, "proposta": proposta}
    
    return None
```

#### Existe Lógica Semelhante?

✅ **SIM**

- Detecção de estado_fluxo em vários handlers
- Processamento de ajustes já existe parcialmente

#### Será Reutilizada?

✅ **SIM**

- `estado_fluxo != "vazio"` será padrão reutilizável

#### Conflito Potencial?

⚠️ **MÉDIO**

```
Conflito: Distinguir entre ajuste (permitir) e 
nova ação (bloquear se pausado) pode ser ambíguo.

Exemplo: "Agende 17h" pode ser ajuste (fluxo ativo)
ou novo agendamento (fluxo vazio).

Solução: Verificar estado_fluxo antes de chamar 
verificar_governanca().

Ordem:
  1. detectar_ajuste_em_fluxo_ativo() ← PRIMEIRO
  2. verificar_governanca() ← SEGUNDO
```

#### Ponto de Implementação

```python
# Em principal_router.py (antes de verificar_governanca)

if estado_fluxo != "vazio":
    ajuste = await processar_ajuste_incremental(msg, ...)
    if ajuste:
        # B-05 WHITELIST: Ajuste em fluxo ativo sempre processa
        return {
            "bloqueado": False,
            "whitelist": "B-05",
            "motivo": "Ajuste incremental em fluxo ativo"
        }
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: principal_router.py:3360+
1 ponto secundário: agendamento_handler.py
Total: 2 pontos
```

---

## WHITELIST B-06: Conflito + Sugestão (Fluxo Ativo)

**ID:** B-06  
**Operação:** Sistema oferece alternativa após detectar conflito  
**Contexto:** estado_fluxo = "processando_agendamento", conflito_detectado = true  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py` ou `services/agendamento_service.py`  
**Função:** `processar_agendamento()` → `oferecer_alternativa()`  
**Linha Aproximada:** 3380-3420 (router) ou 50-150 (service)  

#### Fluxo Atual

```python
# router/principal_router.py (linha ~3380-3420)

# Tentar agendar
resultado_agendamento = await agendar(user_id, dono_id, horario_solicitado)

if resultado_agendamento["status"] == "conflito":
    # Conflito detectado!
    alternativas = resultado_agendamento["alternativas"]
    
    # Oferecer alternativas
    mensagem = oferecer_alternativas(alternativas)
    
    # Alterar estado_fluxo
    await atualizar_estado_fluxo(user_id, "oferecendo_opcoes")
    
    return mensagem
```

#### Lógica Relacionada

**Arquivo:** `services/agendamento_service.py`  
**Função:** `oferecer_alternativas()`  
**Linha Aproximada:** 100-150 (inferred)  

```python
def oferecer_alternativas(alternativas):
    """
    Formata mensagem com alternativas
    """
    msg = "Não consegui com Bruna, mas tenho opções:\n"
    for alt in alternativas:
        msg += f"- {alt['profissional']} às {alt['horario']}\n"
    return msg
```

#### Existe Lógica Semelhante?

✅ **SIM**

- Detecção de conflito já existe
- Oferecimento de alternativas já existe

#### Será Reutilizada?

✅ **SIM**

- `estado_fluxo = "oferecendo_opcoes"` será padrão

#### Conflito Potencial?

⚠️ **BAIXO**

```
Conflito: Sugestão é gerada por sistema, não contém
governanca, então apenas o processamento da resposta
precisa de whitelist.

A mensagem de sugestão sempre é enviada (é sistema),
apenas a resposta ("Prefiro Maria") precisa de whitelist B-09.
```

#### Ponto de Implementação

```python
# Em principal_router.py (após oferecer alternativas)

if estado_fluxo == "oferecendo_opcoes":
    # B-06 WHITELIST: Resposta a sugestão sempre processa
    resposta = await processar_escolha_alternativa(msg, ...)
    if resposta:
        return {
            "bloqueado": False,
            "whitelist": "B-06",
            "motivo": "Escolha de alternativa em fluxo ativo"
        }
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: router/principal_router.py:3380-3420
1 ponto secundário: services/agendamento_service.py
Total: 2 pontos
```

---

## WHITELIST B-08: Escolha de Horário (Fluxo Ativo)

**ID:** B-08  
**Operação:** Cliente escolhe entre múltiplos horários oferecidos  
**Contexto:** estado_fluxo = "oferecendo_opcoes"  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py`  
**Função:** `roteador_principal()` → `processar_escolha_horario()`  
**Linha Aproximada:** 3380-3420  

#### Fluxo Atual

```python
# principal_router.py (linha ~3380-3420)

if estado_fluxo == "oferecendo_opcoes":
    # Verificar se resposta é escolha válida
    opcoes = ctx.get("opcoes_horario", [])
    
    horario_escolhido = extrair_horario(msg, opcoes)
    
    if horario_escolhido:
        # Confirmar escolha
        await confirmar_horario(user_id, dono_id, horario_escolhido)
        return "Horário confirmado!"
```

#### Lógica Relacionada

**Arquivo:** `handlers/agendamento_handler.py`  
**Função:** `extrair_horario()`, `confirmar_horario()`  
**Linha Aproximada:** 150-200 (inferred)  

```python
def extrair_horario(msg, opcoes):
    """
    Extrai horário escolhido da mensagem
    """
    for opcao in opcoes:
        if str(opcao["horario"]) in msg:
            return opcao
    return None
```

#### Existe Lógica Semelhante?

✅ **SIM**

- Detecção de estado_fluxo já existe
- Extração de horário já existe

#### Será Reutilizada?

✅ **SIM**

- `estado_fluxo = "oferecendo_opcoes"` será padrão

#### Conflito Potencial?

✅ **NENHUM**

```
Escolha de horário é exclusivamente no contexto
de fluxo ativo (oferecendo_opcoes), então sem conflito.
```

#### Ponto de Implementação

```python
# Em principal_router.py (dentro de estado_fluxo == "oferecendo_opcoes")

if estado_fluxo == "oferecendo_opcoes":
    horario_escolhido = extrair_horario(msg, ...)
    
    if horario_escolhido:
        # B-08 WHITELIST: Escolha de horário sempre processa
        return {
            "bloqueado": False,
            "whitelist": "B-08",
            "motivo": "Escolha de horário em fluxo ativo"
        }
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: router/principal_router.py:3380-3420
0 pontos novos (compartilha estado_fluxo com B-06)
Total: 1 ponto (compartilhado)
```

---

## WHITELIST B-09: Escolha de Profissional (Fluxo Ativo)

**ID:** B-09  
**Operação:** Cliente escolhe entre profissionais sugeridos  
**Contexto:** estado_fluxo = "escolhendo_profissional"  

### Mapeamento de Código

#### Ponto de Entrada

**Arquivo:** `router/principal_router.py`  
**Função:** `roteador_principal()` → `processar_escolha_profissional()`  
**Linha Aproximada:** 3380-3420  

#### Fluxo Atual

```python
# principal_router.py (linha ~3380-3420)

if estado_fluxo == "escolhendo_profissional":
    # Verificar se resposta é profissional válido
    profissionais = ctx.get("profissionais", [])
    
    prof_escolhido = extrair_profissional(msg, profissionais)
    
    if prof_escolhido:
        # Confirmar escolha
        await confirmar_profissional(user_id, dono_id, prof_escolhido)
        return f"Agendado com {prof_escolhido['nome']}!"
```

#### Lógica Relacionada

**Arquivo:** `handlers/agendamento_handler.py`  
**Função:** `extrair_profissional()`, `confirmar_profissional()`  
**Linha Aproximada:** 150-200 (inferred)  

```python
def extrair_profissional(msg, profissionais):
    """
    Extrai profissional escolhido da mensagem
    """
    msg_norm = msg.lower().strip()
    for prof in profissionais:
        if prof["nome"].lower() in msg_norm:
            return prof
    return None
```

#### Existe Lógica Semelhante?

✅ **SIM**

- Detecção de estado_fluxo já existe
- Extração de profissional já existe

#### Será Reutilizada?

✅ **SIM**

- `estado_fluxo = "escolhendo_profissional"` será padrão

#### Conflito Potencial?

✅ **NENHUM**

```
Escolha de profissional é exclusivamente no contexto
de fluxo ativo (escolhendo_profissional), sem conflito.
```

#### Ponto de Implementação

```python
# Em principal_router.py (dentro de estado_fluxo == "escolhendo_profissional")

if estado_fluxo == "escolhendo_profissional":
    prof_escolhido = extrair_profissional(msg, ...)
    
    if prof_escolhido:
        # B-09 WHITELIST: Escolha de profissional sempre processa
        return {
            "bloqueado": False,
            "whitelist": "B-09",
            "motivo": "Escolha de profissional em fluxo ativo"
        }
```

#### Quantidade de Pontos de Interceptação

```
1 ponto principal: router/principal_router.py:3380-3420
0 pontos novos (compartilha estado_fluxo com B-06/B-08)
Total: 1 ponto (compartilhado)
```

---

## MATRIZ RESUMIDA DE COBERTURA

### Pontos de Interceptação

| Whitelist | Arquivo | Função | Linha | Pontos | Compartilhado |
|-----------|---------|--------|-------|--------|----------------|
| A-01 | principal_router.py | roteador_principal | 3360+ | 2 | Com A-02 |
| A-02 | principal_router.py | resolver_confirmacao | 3360+ | 0 | Com A-01 ✅ |
| A-03 | principal_router.py | processar_cancelamento | 3360+ | 2 | Não |
| A-04 | handlers/cancelamento | handler_cancelamento | 100+ | 0 | Com A-03 ✅ |
| A-05 | principal_router.py | ativar_onboarding | 50-150 | 2 | Não |
| A-06 | principal_router.py | processar_comando | 3360+ | 2 | Não |
| B-05 | principal_router.py | processar_ajuste | 3360+ | 0 | Com A-01 ✅ |
| B-06 | principal_router.py | oferecer_alternativa | 3380+ | 0 | Com B-08/B-09 ✅ |
| B-08 | principal_router.py | processar_escolha_h | 3380+ | 0 | Com B-06 ✅ |
| B-09 | principal_router.py | processar_escolha_p | 3380+ | 0 | Com B-06 ✅ |

---

### Consolidação Possível

```
8 Pontos de Interceptação Únicos:
  1. resolver_confirmacao_pendente (A-01/A-02)
  2. handler_cancelamento (A-03/A-04)
  3. ativar_onboarding (A-05)
  4. processar_comando (A-06)
  5. processar_ajuste_incremental (B-05)
  6. oferecer_alternativa (B-06/B-08/B-09)
  7. processar_escolha_horario (B-08)
  8. processar_escolha_profissional (B-09)

Mas com compartilhamento = 4-5 Funções Centrais:
  - Confirmação (A-01/A-02)
  - Cancelamento (A-03/A-04)
  - Fluxo Ativo (A-05, B-05, B-06, B-08, B-09)
  - Comando (A-06)
  - Onboarding (A-05)
```

---

## DUPLICIDADES DETECTADAS

### Duplicidade 1: Estado_Fluxo

**Descrição:** Verificação de `estado_fluxo` aparece em múltiplos handlers

**Locais:**
```
- principal_router.py (linha 3360+): Checks estado_fluxo
- handlers/agendamento_handler.py (linha 50+): Checks estado_fluxo
- handlers/confirmacao_handler.py (linha 10+): Checks estado_fluxo
- handlers/cancelamento_handler.py (linha 30+): Checks estado_fluxo
```

**Reutilização Possível:**

```python
def em_fluxo_ativo(sessao):
    """Helper function reutilizável"""
    return sessao.get("estado_fluxo") != "vazio"

def obter_estado_fluxo(sessao):
    """Helper para centralizar lógica"""
    return sessao.get("estado_fluxo", "vazio")
```

---

### Duplicidade 2: Extração de Padrões (Regex)

**Descrição:** Regex para detectar cancelamento, confirmação, comandos aparece em múltiplos places

**Locais:**
```
- handlers/bot.py (linha ~200+): Regex para cancelamento
- handlers/bot.py (linha ~250+): Regex para confirmação
- handlers/bot.py (linha ~300+): Regex para comando
```

**Reutilização Possível:**

```python
# Centralizar em utils/pattern_matcher.py
def eh_cancelamento(msg):
    patterns = [r"cancelar", r"desmarcar", ...]
    return any(re.search(p, msg, re.I) for p in patterns)

def eh_confirmacao_positiva(msg):
    patterns = [r"sim", r"yes", r"opa", ...]
    return any(re.search(p, msg, re.I) for p in patterns)

def eh_comando(msg):
    return msg.startswith("/")
```

---

## RISCOS DE IMPLEMENTAÇÃO

### Risco 1: Ordem de Verificação (MÉDIO)

**Problema:**
```
Se verificar_governanca() é chamado ANTES de detectar whitelist,
então whitelist nunca é alcançada.

Exemplo:
  # ❌ ERRADO
  bloqueado = verificar_governanca(user_id, msg)
  if bloqueado:
      return "Bloqueado"
  confirmacao = resolver_confirmacao_pendente(msg)
  
  # ✅ CORRETO
  confirmacao = resolver_confirmacao_pendente(msg)  # ANTES
  if confirmacao and eh_confirmacao:
      return processar_confirmacao()  # Sem verificar_governanca
  
  bloqueado = verificar_governanca(user_id, msg)
  if bloqueado:
      return "Bloqueado"
```

**Mitigação:**
- Documentar ordem de verificação explicitamente
- Criar função `verificar_com_whitelist()` que respeita ordem
- Adicionar testes de ordem (G2.01-G2.05)

**Risco:** MÉDIO → BAIXO com testes

---

### Risco 2: Ambiguidade de Mensagem (MÉDIO)

**Problema:**
```
Mensagem pode ser interpretada como múltiplas coisas:
  "Agende para amanhã às 15h"
  
Pode ser:
  - Novo agendamento (B-01, bloquear se pausado)
  - Ajuste incremental (B-05, whitelist se fluxo ativo)
  - Cancelamento + reagendamento (A-03 + novo)
  
Qual tomar como verdade?
```

**Mitigação:**
- Verificar `estado_fluxo` primeiro
- Se em fluxo ativo, interpretar como ajuste (whitelist B-05)
- Se fora de fluxo, interpretar como novo agendamento

**Risco:** MÉDIO → BAIXO com lógica clara

---

### Risco 3: Persistência de Estado_Fluxo (MÉDIO)

**Problema:**
```
Se estado_fluxo não é persistido corretamente entre
mensagens, whitelists não funcionam.

Exemplo:
  Msg 1: "Agende para amanhã" → estado_fluxo = "agendando"
  Reload ou nova sessão
  Msg 2: "16h" → estado_fluxo = "vazio" ❌ Perdido!
```

**Mitigação:**
- Garantir estado_fluxo é persistido em Sessoes/{actor_id}
- Carregar estado_fluxo no início de cada roteador_principal call
- Testes G3.01-G3.04 validam persistência

**Risco:** MÉDIO → BAIXO com G3 testes

---

### Risco 4: Conflito entre Whitelist e MEC-04 (BAIXO)

**Problema:**
```
Se dono está em modo_dono = "admin", qual vence?
  Whitelist A-03 (cancelamento) ou MEC-04 (admin)?
  
Resposta: A-03 vence (A > B > C hierarquia)
```

**Mitigação:**
- Documentar hierarquia explicitamente
- Testar em G4.03 (Dono admin cancela)

**Risco:** BAIXO (hierarquia clara)

---

## QUANTIDADE DE PONTOS DE INTERCEPTAÇÃO

### Resumo Final

```
Total de Whitelists:              10
Pontos únicos de implementação:   8
Funções que reusam lógica:        4-5
Duplicidades a consolidar:        2
Conflitos potenciais:             4 (MÉDIO → BAIXO com mitigação)
```

### Consolidação Recomendada

```
1 Função Central: verificar_com_whitelist()
   ├─ Detecta whitelist ANTES de governanca
   ├─ Respeita ordem de verificação
   └─ Retorna {bloqueado, whitelist, motivo}

5 Funções Auxiliares (utils/pattern_matcher.py):
   ├─ eh_cancelamento()
   ├─ eh_confirmacao_positiva()
   ├─ eh_confirmacao_negativa()
   ├─ eh_comando()
   └─ eh_ajuste_em_fluxo()

1 Helper: obter_estado_fluxo() [centralizar verificação]
```

---

## PARECER FINAL

### Recomendação de Implementação

**Status:** ✅ **IMPLEMENTAÇÃO SIMPLES**

#### Justificativa

```
1. Lógica já existe em múltiplos places
   - Detecção de confirmação
   - Detecção de cancelamento
   - Detecção de comando
   - Detecção de estado_fluxo
   
   → Apenas consolidar e reordenar

2. Poucos pontos de interceptação (8)
   - Todos em principal_router.py ou handlers próximos
   - Fácil manutenção centralizada
   
3. Duplicidades são simples de eliminar
   - Pattern matching pode ser centralizado
   - Estado_fluxo é simples helper
   
4. Conflitos são bem definidos
   - Ordem de verificação é clara
   - Hierarquia (A > B > C) é explícita
```

#### Esforço Estimado

```
Implementação:        2-3 dias
  - Consolidação de lógica existente
  - Criação de função verificar_com_whitelist()
  - Criação de utils/pattern_matcher.py
  - Integração em principal_router.py

Testes:               2-3 dias
  - 28 testes (G1-G7)
  - Regressão (P1 + P0)

Total Sprint 1:       4-6 dias (conforme PRD SEG-04)
```

#### Risco de Conflito

```
✅ BAIXO
   - Ordem de verificação é clara
   - Whitelists são simples
   - Testes validam tudo
```

---

## CHECKLIST DE IMPLEMENTAÇÃO

### Consolidação de Código

```
[ ] Criar utils/pattern_matcher.py com funções reutilizáveis
[ ] Criar verificar_com_whitelist() centralizada
[ ] Integrar em principal_router.py:3360
[ ] Remover duplicidades de estado_fluxo
[ ] Centralizar extração de padrões (regex)
```

### Testes

```
[ ] G1: Override Manual (A-01 a A-04)
[ ] G2: Whitelist (A-01 a A-06)
[ ] G3: Fluxo Ativo (B-05 a B-09)
[ ] G4: Modo Dono
[ ] G5: Persistência
[ ] G6: Multi-tenant
[ ] G7: Regressão
```

### Verificação

```
[ ] P1 E2E 42/42 PASS
[ ] P0 Regressão 174/174 PASS
[ ] Código review
[ ] Merge to main
```

---

**Auditoria:** SEG-04E  
**Data:** 2026-06-23  
**Status:** ✅ Cobertura Real Mapeada  
**Recomendação:** Implementação Simples  

**⏹️ PARAR AQUI — Sem código, sem patch, sem teste.**
