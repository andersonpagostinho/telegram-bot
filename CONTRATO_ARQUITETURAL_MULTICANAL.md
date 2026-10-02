# CONTRATO ARQUITETURAL MULTICANAL — ANÁLISE ARQUITETURAL

**Data:** 2026-10-02  
**Status:** 📋 ANÁLISE DE SOMENTE LEITURA (NÃO IMPLEMENTA)  
**Escopo:** Definir contrato antes de qualquer implementação  

---

## PREÂMBULO

Este documento é uma análise arquitetural pura baseada em:
- `GATE_C3153A_AUDITORIA_IDENTIDADE_WHATSAPP.md`
- `ANALISE_ARQUITETURAL_SEND_AND_STOP.md`
- `RELATORIO_IMPLEMENTACAO_SEND_AND_STOP.md`
- Código existente em Telegram e WhatsApp

**NÃO contém:**
- ❌ Implementação
- ❌ Testes
- ❌ Commits
- ❌ Pushes
- ❌ Deploys

**Contém:**
- ✅ Decisões arquiteturais
- ✅ Contrato de interfaces
- ✅ Mapeamento de responsabilidades
- ✅ Fluxos ideais vs. atuais
- ✅ Plano de implementação

---

## 1. CONTRATO DE IDENTIDADE

### 1.1 Atual (Fragmentado)

```
Telegram:
  user_id → telegram_id (único, numérico)
    ↓
  obter_id_dono(telegram_id) → tenant_id ou fallback: telegram_id
    ↓
  dono_id = tenant_id ou str(telegram_id)

WhatsApp:
  user_id → wa_id (número de telefone)
  phone_number_id → tenant_id (resolvido via WhatsAppEndpoints/)
    ↓
  obter_id_dono(wa_id) → None (wa_id não é cliente registrado)
    ↓
  dono_id = str(wa_id) ← FALLBACK INCORRETO
    ↓
  Carrega contexto de Clientes/{wa_id}/ ← TENANT ERRADO
```

---

### 1.2 Proposta: Contexto Normalizado de Identidade

**Objeto a criar em cada requisição (canal-agnóstico):**

```python
class IdentidadeContexto:
    """Contexto normalizado de identidade, canal-independente."""
    
    # Obrigatório
    user_id: str           # ID do usuário no canal (telegram_id ou wa_id)
    tenant_id: str         # ID da organização/proprietário (resolvido via canal)
    actor_id: str          # ID canônico do ator (whatsapp:5511... ou tg:123...)
    canal: str             # "telegram" ou "whatsapp"
    
    # Opcional (contexto adicional)
    actor_tipo: str | None        # "dono", "cliente", "profissional" (resolvido após identidade)
    actor_nome: str | None        # Nome do ator (para logs)
    tenant_nome: str | None       # Nome da organização (para logs)
```

---

### 1.3 Campos: Obrigatório vs. Opcional vs. Derivado

| Campo | Obrigatório | Derivado de | Quem Define |
|-------|-------------|------------|------------|
| **user_id** | ✅ SIM | Mensagem recebida | Canal (Telegram/WhatsApp) |
| **tenant_id** | ✅ SIM | Webhook → resolver | Webhook adapter |
| **actor_id** | ✅ SIM | canal + user_id | Identidade service |
| **canal** | ✅ SIM | Tipo de requisição | Canal |
| **actor_tipo** | ⚠️ OPCIONAL | Firestore lookup | Identidade service (após carregar ator) |
| **actor_nome** | ⚠️ OPCIONAL | Firestore lookup | Identidade service (após carregar ator) |
| **tenant_nome** | ⚠️ OPCIONAL | Firestore lookup | Identidade service (após carregar tenant) |

---

### 1.4 Diferença Semântica: user_id vs. actor_id

**user_id (canal-específico):**
- Telegram: `123456789` (user_id do Telegram)
- WhatsApp: `5511991382080` (número de telefone)
- **Propriedade:** Único por canal, pode não existir em Firestore

**actor_id (canônico):**
- Telegram: `tg:123456789`
- WhatsApp: `whatsapp:5511991382080`
- **Propriedade:** Identificador único em `Clientes/{tenant_id}/Atores/{actor_id}`

**Relação:**
```
user_id → [normalização por canal] → actor_id
```

**Nunca:**
```
actor_id ← user_id
```

---

### 1.5 Preenchimento por Canal

#### Telegram
```python
identidade = IdentidadeContexto(
    user_id="123456789",           # from message.from_user.id
    tenant_id=None,                # Não disponível em Telegram (legado)
    actor_id="tg:123456789",       # Computado
    canal="telegram",
)

# Se tenant_id é None:
# → Fallback para obter_id_dono(user_id) (compatibilidade legada)
# → Se nada encontrar: usar user_id como tenant (apenas para Telegram antigo)
```

#### WhatsApp (Correto)
```python
identidade = IdentidadeContexto(
    user_id="5511991382080",       # from message.from_number
    tenant_id="7394370553",        # from resolver_tenant_por_endpoint(phone_number_id)
    actor_id="whatsapp:5511991382080",  # Computado
    canal="whatsapp",
)

# tenant_id DEVE estar preenchido desde o webhook
```

---

### 1.6 Responsabilidade de Preenchimento

| Campo | Quem Cria | Local |
|-------|-----------|-------|
| **user_id** | Canal | `main.py` (WhatsApp) ou `bot.py` (Telegram) |
| **tenant_id** | Webhook adapter | `main.py` (WhatsApp) ou handler (Telegram) |
| **actor_id** | Identidade service | Router (antes de usar) |
| **canal** | Handler | Handler (baseado em onde vem a mensagem) |

---

### 1.7 Garantia Fundamental

**Regra Obrigatória (P0):**
```
Para WhatsApp:
  tenant_id DEVE ser resolvido ANTES de chegar ao router.
  ❌ NUNCA cair em TENANT_FALLBACK.

Para Telegram:
  tenant_id pode vir vazio.
  → Usar obter_id_dono(user_id).
  → Se falhar: fallback user_id (apenas legado).
```

---

## 2. CONTRATO DO EXECUTOR

### 2.1 Assinatura Atual

**Arquivo:** `services/gpt_executor.py:228-300`

```python
async def executar_acao_gpt(
    acao: str,
    parametros: dict,
    dados_contexto: dict,
    user_id: str,
    canal_origem: str = "telegram",
    openai_client: object = None,
) -> dict:
    """Executa ação determinística ou delegada ao GPT."""
```

**Problemas:**
- ❌ Não recebe `identidade` normalizada
- ❌ Precisa computar actor_id localmente
- ❌ Não sabe tenant_id a menos que venha em `dados_contexto`
- ❌ `canal_origem` opcional (sempre "telegram")
- ❌ Mistura identidade com execução

---

### 2.2 Assinatura Proposta

**Versão agnóstica de canal:**

```python
async def executar_acao_gpt(
    acao: str,
    identidade: IdentidadeContexto,
    parametros: dict,
    dados_contexto: dict,
    openai_client: object = None,
) -> ResultadoAcao:
    """
    Executa ação determinística ou delegada ao GPT.
    
    Argumentos:
    - acao: nome da ação ("criar_evento", "confirmar_agendamento", etc.)
    - identidade: IdentidadeContexto (user_id, tenant_id, actor_id, canal)
    - parametros: argumentos específicos da ação
    - dados_contexto: contexto conversacional
    - openai_client: cliente GPT (opcional, usa padrão se None)
    
    Retorna:
    - ResultadoAcao estruturado (sucesso/erro/resposta)
    """
```

---

### 2.3 Análise de Argumentos Atuais

| Argumento | Necessário | Motivo | Nova Posição |
|-----------|-----------|---------|--------------|
| **acao** | ✅ | Qual ação executar | Mantém |
| **parametros** | ✅ | Dados específicos da ação | Mantém |
| **dados_contexto** | ✅ | Conversação anterior | Mantém |
| **user_id** | ⚠️ | Pode vir de identidade.user_id | ← Removido |
| **canal_origem** | ⚠️ | Pode vir de identidade.canal | ← Removido |
| **openai_client** | ⚠️ | Opcional, padrão global | Mantém |

---

### 2.4 Campos Obrigatórios vs. Opcionais Finais

```python
Obrigatórios:
  ✅ acao
  ✅ identidade (novo, combinado de user_id + canal + tenant_id)
  ✅ parametros
  ✅ dados_contexto

Opcionais:
  ⚠️ openai_client (padrão: cliente global)
```

---

### 2.5 O que Não Muda

**Importante:** GPT NUNCA deve:
- ❌ Decidir profissional (determinístico)
- ❌ Decidir serviço (determinístico)
- ❌ Decidir tenant (já vem do identidade)
- ❌ Decidir actor_tipo (já resolvido)
- ❌ Acessar Firestore diretamente (camada de negócio)

**GPT continua:**
- ✅ Interpretando linguagem natural
- ✅ Extraindo intenção e dados
- ✅ Sugerindo (sem decidir)

---

## 3. CONTRATO DE EXECUÇÃO VS. RESPOSTA

### 3.1 Problema Atual

`executar_acao_gpt()` e `_send_and_stop()` misturam:

```
A) EXECUÇÃO (criar evento, confirmar, etc.)
B) RESPOSTA (texto para enviar ao usuário)
C) TRANSPORTE (como enviar: Telegram, WhatsApp)

Resultado:
- Código duplicado entre canais
- Lógica espalhada entre router, executor, handlers
- Impossível reutilizar execução em novos canais
```

---

### 3.2 Separação Proposta

#### A) EXECUÇÃO DA AÇÃO (Agnóstica de Canal)

```python
class ResultadoAcao:
    sucesso: bool
    acao: str
    dados: dict          # Resultado estruturado (evento criado, etc.)
    mensagem: str        # Mensagem para o usuário (sem formatação de canal)
    erro: str | None
    
    def __init__(self, sucesso, acao, dados=None, mensagem="", erro=None):
        self.sucesso = sucesso
        self.acao = acao
        self.dados = dados or {}
        self.mensagem = mensagem
        self.erro = erro
```

**Exemplos:**

```python
# Ação bem-sucedida
ResultadoAcao(
    sucesso=True,
    acao="criar_evento",
    dados={"evento_id": "123", "data": "2026-10-02 14:00"},
    mensagem="Agendamento confirmado para amanhã às 14h com João"
)

# Erro
ResultadoAcao(
    sucesso=False,
    acao="criar_evento",
    mensagem="",
    erro="Horário não disponível com João"
)
```

---

#### B) APRESENTAÇÃO/TRANSPORTE (Específica de Canal)

```python
class AdapterResposta:
    """Converte ResultadoAcao para formato do canal."""
    
    async def formatar(
        resultado: ResultadoAcao,
        canal: str,
        usuario_pref: dict = None,
    ) -> str | dict:
        """
        Converte resposta estruturada para formato do canal.
        
        Telegram → Markdown formatado + buttons
        WhatsApp → Texto puro + emojis
        """
```

---

### 3.3 Fluxo Novo (Separado)

```
1. EXECUÇÃO (agnóstica)
   identidade → executar_acao_gpt() → ResultadoAcao

2. APRESENTAÇÃO (específica do canal)
   ResultadoAcao → adapter_telegram/whatsapp → texto/dict formatado

3. TRANSPORTE (específica do canal)
   Texto → context.bot.send_message() (Telegram)
   Dict → whatsapp_service.enviar() (WhatsApp)
```

**Benefício:**
- ✅ Lógica de negócio desacoplada de canal
- ✅ Fácil adicionar novo canal
- ✅ Sem `if update is None` espalhado
- ✅ Reutilizável por APIs, webhooks, CLIs

---

### 3.4 Mapeamento de Linhas Atuais

#### gpt_executor.py:223
**Atual:**
```python
resultado_dict = {"acao": acao, "handled": True}
```

**Responsabilidade:** Execução + Transporte (MISTURADO)

**Proposta:** Apenas execução
```python
resultado = ResultadoAcao(
    sucesso=True,
    acao=acao,
    dados=...,
    mensagem="..."
)
```

---

#### gpt_executor.py:224
**Atual:**
```python
if contexto_existente:
    resultado_dict["resultado"] = {...}
```

**Responsabilidade:** Decisão de resposta (EXECUTADA AQUI)

**Proposta:** Em adapter
```python
# resultado.dados já contém o que precisa
# Adapter decide como formatar
```

---

#### gpt_executor.py:237+
**Atual:**
```python
return {"acao": acao, "resposta": mensagem, "handled": True}
```

**Responsabilidade:** Execução + Formatação + Transporte (TUDO JUNTO)

**Proposta:** Separado
```python
resultado = ResultadoAcao(sucesso=True, acao=acao, mensagem=mensagem)
# Adapter cuida de formatação
# Handler/webhook cuida de transporte
```

---

#### principal_router.py:3501
**Atual:**
```python
if context is not None:
    await context.bot.send_message(...)
return {"handled": True, "already_sent": True}
```

**Responsabilidade:** Decisão de envio + Transporte + Resposta (TODOS)

**Proposta:** Separado
```python
resultado = ResultadoAcao(sucesso=True, mensagem=texto)

if context is not None:
    # Telegram: enviar direto
    adapter = AdapterTelegram()
    await adapter.enviar(resultado, context, user_id)
else:
    # WhatsApp: retornar para handler enviar
    return resultado
```

---

## 4. PRINCIPAL_ROUTER

### 4.1 Papel Atual (Confuso)

```
principal_router() faz TUDO:
  1. Resolve identidade (obter_id_dono, carregar ator)
  2. Classifica intenção (classificador)
  3. Executa lógica de negócio (P0: agenda, etc.)
  4. Constrói resposta (texto ao usuário)
  5. Escolhe transporte (enviar ou retornar)
  6. Envia resposta (context.bot.send_message)
```

**Resultado:** 3500+ linhas, difícil entender fluxo

---

### 4.2 Papel Proposto (Orquestrador)

```
principal_router() deve ORQUESTRAR:

1. ✅ Resolver identidade
   ↓ identidade = IdentidadeContexto(...)

2. ✅ Classificar intenção
   ↓ intencao = classificador(texto, identidade, contexto)

3. ✅ Delegar execução
   ↓ resultado = await dominio.executar(acao, identidade, ...)

4. ❌ NÃO construir resposta (adapter cuida)

5. ❌ NÃO escolher transporte (handler cuida)

6. ❌ NÃO enviar (adapter/webhook cuida)
```

---

### 4.3 Fluxo Ideal do Router

```
def roteador_principal(
    user_id: str,
    mensagem: str,
    update=None,          # Telegram (pode ser None)
    context=None,         # Telegram (pode ser None)
    tenant_id: str = None # WhatsApp (obrigatório)
):
    1. Determinar canal
       canal = "telegram" se context else "whatsapp"

    2. Criar identidade
       identidade = IdentidadeContexto(
           user_id=user_id,
           tenant_id=tenant_id or obter_id_dono(user_id) or user_id,
           actor_id=f"{canal}:{user_id}",
           canal=canal
       )

    3. Carregar contexto conversacional
       ctx = await carregar_contexto(identidade)

    4. Verificar estado (onboarding, fluxo especial)
       if ctx["estado_fluxo"] == "onboarding_dono":
           resultado = processar_onboarding(identidade, ctx, mensagem)
           return resultado

    5. Classificar intenção
       classificacao = await classificador(mensagem, identidade, ctx)

    6. Executar ação
       resultado = await dominio.executar(
           acao=classificacao.acao,
           identidade=identidade,
           parametros=classificacao.parametros,
           contexto=ctx
       )

    7. APENAS RETORNAR resultado
       return resultado
       # Handler cuida de envio
```

---

### 4.4 O que NÃO Muda no Router

- ✅ Detecção de onboarding (antes de P0)
- ✅ Verificação de guards (bloqueios)
- ✅ Lógica de classificação (GPT + rules)
- ✅ Persistência de contexto
- ✅ Tratamento de erros

---

## 5. PRINCIPAL_ROUTER:3501 — ANÁLISE CRÍTICA

### 5.1 Código Atual

**Arquivo:** `router/principal_router.py:3501`

```python
if context is not None:
    await context.bot.send_message(
        chat_id=user_id,
        text="...",
        parse_mode="Markdown"
    )
return {"handled": True, "already_sent": True}
```

---

### 5.2 Classificação

| Aspecto | Responsabilidade |
|---------|------------------|
| **Qual mensagem?** | Resposta (escrita no router) |
| **Por que existe?** | Transporte (enviada aqui) |
| **Quem deveria receber?** | Canal (handler decide) |
| **É necessária?** | SIM (mas em local errado) |
| **É duplicada?** | TALVEZ (pode estar em outro lugar) |
| **Deve virar retorno?** | SIM (estruturado) |
| **Deve ser enviada pelo adapter?** | SIM (canal decide como) |

---

### 5.3 Proposta de Decisão

**Opção A: Mover para adapter (Recomendada)**

```python
# No router: apenas retornar
return ResultadoAcao(
    sucesso=True,
    acao="saudacao",
    mensagem="Olá! Como posso te ajudar?"
)

# No handler/webhook:
resultado = await roteador_principal(...)
adapter = AdapterTelegram() if context else AdapterWhatsApp()
await adapter.enviar(resultado, context, user_id)
```

**Vantagens:**
- ✅ Agnóstico de canal no router
- ✅ Adapter cuida de transporte
- ✅ Sem `if context is not None` espalhado
- ✅ Fácil adicionar novo canal

**Desvantagens:**
- ❌ Requer alteração em handlers/bot.py
- ❌ Requer alteração em main.py

---

**Opção B: Compatibilidade com Telegram (Mínima)**

Se Telegram PRECISA que a mensagem seja enviada do router:

```python
# No router: enviar E retornar
if context is not None:
    await context.bot.send_message(...)
    return {"handled": True, "already_sent": True, "resposta": texto}
else:
    return {"resposta": texto, "handled": True}

# No handler/webhook:
# Telegram: verifica already_sent, não reenvia
# WhatsApp: extrai resposta, envia
```

**Vantagens:**
- ✅ Compatível com Telegram existente
- ✅ Mínimo de alterações
- ✅ Funciona imediatamente

**Desvantagens:**
- ❌ Mistura responsabilidades
- ❌ Mantém `if context is not None`
- ❌ Não escalável para novos canais

---

### 5.4 Decisão Recomendada

**Usar Opção B (curto prazo) + Planejar Opção A (longo prazo)**

Razão: Telegram já funciona, não quebrar. Criar estrutura para futuros adapters em paralelo.

---

## 6. GPT EXECUTOR

### 6.1 Papel Atual

**Função:** `executar_acao_gpt(acao, parametros, dados_contexto, user_id, canal_origem)`

**Responsabilidades:**
```
A) Executar ações de negócio (criar_evento, confirmar, etc.)
B) Fazer queries ao GPT (quando necessário)
C) Construir resposta (texto ao usuário)
D) Retornar resultado estruturado ou string
E) Conhecer canal_origem (para formatação)
```

---

### 6.2 Análise de Responsabilidades

| Responsabilidade | Pertence a GPT Executor? | Razão |
|------------------|-------------------------|-------|
| **A) Executar ações** | ✅ SIM | Core da função |
| **B) Chamar GPT** | ✅ SIM | Interpretação |
| **C) Construir resposta** | ⚠️ TALVEZ | Poderia ser adapter |
| **D) Retornar resultado** | ✅ SIM | Necessário |
| **E) Conhecer canal** | ❌ NÃO | Adapter cuida |

---

### 6.3 Proposta de Simplicidade

```python
async def executar_acao_gpt(
    acao: str,
    identidade: IdentidadeContexto,  # ← novo, combinado
    parametros: dict,
    dados_contexto: dict,
    openai_client: object = None,
) -> ResultadoAcao:
    """
    Executa ação de forma determinística ou com interpretação GPT.
    
    NÃO sabe:
    - Que é Telegram ou WhatsApp
    - Como formatar a resposta
    - Como enviar a resposta
    
    Sabe:
    - Qual ação executar
    - Qual identidade = qual tenant/ator
    - Qual contexto anterior
    """
    
    # Execução normal (determinística)
    if acao == "criar_evento":
        return await dominio.criar_evento(identidade, parametros)
    
    # Ou com GPT (interpretação)
    if acao == "interpretar_servico":
        servico = await gpt_service.extrair_servico(texto, identidade, dados_contexto)
        return ResultadoAcao(sucesso=True, acao=acao, dados={"servico": servico})
    
    # Sem conhecer canal
```

---

### 6.4 O que Não Muda

**Contrato GPT permanece:**
- ✅ GPT não decide profissional
- ✅ GPT não decide tenant
- ✅ GPT não decide evento (domínio decide)
- ✅ GPT não acessa Firestore direto
- ✅ GPT apenas interpreta e sugere

---

## 7. ADMIN_COMMAND_SERVICE

### 7.1 Análise de Divisão

**Arquivo:** `services/admin_command_service.py`

Funções encontradas (por tipo):

#### Telegram-only
```
- responder_comando_ola()
- responder_comando_ajuda()
- responder_comando_sair()
→ Usam reply_text, context.bot
→ Não são reutilizáveis
```

#### Lógica + Transporte
```
- listar_agendamentos()
- cancelar_agendamento()
→ Lógica de negócio + reply_text
→ Poderiam ser separadas
```

#### Puro Negócio
```
- validar_horario()
- checar_disponibilidade()
→ Sem reply_text, agnóstlco
→ Já reutilizável
```

---

### 7.2 Classificação Proposta

| Função | Tipo | Ação Proposta |
|--------|------|---------------|
| responder_comando_ola | Telegram-only | Deixar como está (compatibilidade) |
| responder_comando_ajuda | Telegram-only | Deixar como está |
| responder_comando_sair | Telegram-only | Deixar como está |
| listar_agendamentos | Lógica + Transporte | Separar: lógica em domínio, transporte em adapter |
| cancelar_agendamento | Lógica + Transporte | Idem |
| validar_horario | Puro Negócio | Nenhuma ação (já reutilizável) |
| checar_disponibilidade | Puro Negócio | Nenhuma ação (já reutilizável) |

---

### 7.3 Não Tocar Agora

**Recomendação:** Não refatorar admin_command_service agora.

**Razão:** Ainda funciona, compatível com Telegram, não bloqueador.

**Para depois:** Quando implementar adapter de resposta, considerar mover lógica pura para domínio.

---

## 8. COMPATIBILIDADE TELEGRAM

### 8.1 Comportamento Atual (Funcionando)

```
Message in → bot.py:handle_message()
              ↓
              roteador_principal(
                  user_id=message.from_user.id,
                  mensagem=message.text,
                  update=update,
                  context=context
              )
              ↓
         resposta (dict ou string)
              ↓
         if resposta.get("already_sent"):
             → não reenvia ✓
         else:
             → context.bot.send_message() → usuário recebe ✓
```

---

### 8.2 Estratégia de Preservação

**Não quebrar o fluxo existente:**

```
Proposta NÃO pode exigir:
- ❌ Reescrever todos os handlers Telegram
- ❌ Alterar assinatura de funções críticas
- ❌ Mudar schema de Firestore
- ❌ Remover fallback user_id (ainda necessário para legado)
```

**Proposta PODE fazer:**
- ✅ Adicionar `tenant_id` opcional a `roteador_principal()`
- ✅ Adicionar `identidade` internamente se não passado
- ✅ Usar fallback para tenant se não resolvido
- ✅ Manter retorno dict/string como está
- ✅ Adicionar campos extras ao dict (não quebra consumo)

---

### 8.3 Fluxo com Compatibilidade

```
Telegram (existente):
  bot.py → roteador_principal(user_id, mensagem, update, context)
           ↓
           identidade = IdentidadeContexto(
               user_id=user_id,
               tenant_id=None,  # Não vem do webhook
               actor_id=f"tg:{user_id}",
               canal="telegram"
           )
           ↓
           resultado = await executar(acao, identidade, ...)
           ↓
           if context is not None:
               context.bot.send_message(resultado.mensagem)
               return {"already_sent": True, "resposta": resultado.mensagem}
           
           # Compatível ✓
```

---

## 9. COMPATIBILIDADE WHATSAPP

### 9.1 Contrato Correto (Conforme Auditoria)

```
phone_number_id → resolver_tenant_por_endpoint() → tenant_id
wa_id → normalizar para actor_id
canal → "whatsapp"

Garantia: tenant_id NUNCA vira None ou wa_id
```

---

### 9.2 Fluxo Atual Errado (Conforme Auditoria)

```
main.py:225
tenant_id = resolver_tenant_por_endpoint(phone_number_id) ✓ (7394370553)
  ↓
main.py:237-242
roteador_principal(user_id=wa_id, ...)
  ↓ tenant_id PERDIDO aqui ❌
  ↓
principal_router.py:3376
dono_id = await obter_id_dono(wa_id)
  ↓ Retorna None (wa_id não é cliente)
  ↓
Fallback: dono_id = str(wa_id) ❌ (5511991382080)
  ↓
Carrega contexto de Clientes/5511991382080/ ❌ (TENANT ERRADO)
```

---

### 9.3 Fluxo Proposto (Correto)

```
main.py:225
tenant_id = resolver_tenant_por_endpoint(phone_number_id) ✓

main.py:237-242
roteador_principal(
    user_id=wa_id,
    mensagem=text_body,
    tenant_id=tenant_id,  ← ADICIONAR (passar aqui)
    update=None,
    context=None
)

principal_router:3364
async def roteador_principal(
    user_id: str,
    mensagem: str,
    tenant_id: str = None,  ← ADICIONAR (aceitar aqui)
    update=None,
    context=None
):

principal_router:3376
if tenant_id:
    dono_id = tenant_id  ← USAR tenant passado
else:
    dono_id = await obter_id_dono(user_id)  ← Fallback Telegram
```

---

### 9.4 Garantia Proposta

**Regra P0 (Obrigatória):**

```
Para WhatsApp:
1. ✅ tenant_id DEVE ser resolvido NO WEBHOOK
2. ✅ tenant_id DEVE ser passado AO ROUTER
3. ❌ NUNCA usar wa_id como tenant_id
4. ❌ NUNCA caiu em TENANT_FALLBACK para WhatsApp

Verificação:
- Se canal == "whatsapp" e tenant_id == wa_id → BUG
- Log deve avisar
```

---

## 10. CONTRATO DE RETORNO

### 10.1 Proposto: ResultadoAcao Estruturado

```python
class ResultadoAcao:
    """Resposta estruturada de uma ação, agnóstica de canal."""
    
    sucesso: bool             # True = executou sem erro
    acao: str                 # Nome da ação ("criar_evento", "confirmar", etc.)
    dados: dict               # Resultado estruturado (evento criado, etc.)
    mensagem: str             # Texto para usuário (sem formatação de canal)
    erro: str | None          # Mensagem de erro (se sucesso=False)
    
    # Opcional: para compatibilidade com código antigo
    handled: bool = True      # Sempre True (legado)
    already_sent: bool = None # None (não enviado pelo executor)
```

---

### 10.2 Exemplos

#### Ação bem-sucedida
```python
ResultadoAcao(
    sucesso=True,
    acao="criar_evento",
    dados={
        "evento_id": "evt_abc123",
        "data": "2026-10-03 14:00",
        "servico": "Corte",
        "profissional": "João",
        "duracao": 60,
    },
    mensagem="Agendamento confirmado para amanhã às 14h com João",
)
```

#### Ação com erro
```python
ResultadoAcao(
    sucesso=False,
    acao="criar_evento",
    dados={},
    mensagem="",
    erro="João não tem disponibilidade nesse horário",
)
```

#### Ação que precisa de mais contexto (GPT decidiu)
```python
ResultadoAcao(
    sucesso=True,
    acao="esclarecer_servico",
    dados={"servico_ambiguo": "cabelo"},
    mensagem="Qual tipo de cabelo? Corte, escova ou coloração?",
)
```

---

### 10.3 Como Adapter Consome

#### Telegram Adapter
```python
class AdapterTelegram:
    async def enviar(resultado: ResultadoAcao, context, user_id):
        # Formatar para Markdown
        texto = f"*{resultado.acao}*\n{resultado.mensagem}"
        
        # Adicionar buttons se necessário
        if resultado.acao == "esclarecer_servico":
            buttons = [...construir buttons...]
            await context.bot.send_message(texto, reply_markup=buttons)
        else:
            await context.bot.send_message(texto)
```

#### WhatsApp Adapter
```python
class AdapterWhatsApp:
    async def enviar(resultado: ResultadoAcao, wa_service, user_id):
        # Formatar para texto puro
        texto = resultado.mensagem
        
        # Enviar via WhatsApp
        await wa_service.enviar_mensagem(user_id, texto)
```

---

### 10.4 Compatibilidade com Código Antigo

**Até migração completa, ResultadoAcao pode ter:**

```python
# Para Telegram
if context is not None:
    return {
        "sucesso": True,
        "acao": acao,
        "dados": {...},
        "mensagem": mensagem,
        "already_sent": True,  # Telegram não reenvia
        "resposta": mensagem,  # Para main.py compatibilidade
    }

# Para WhatsApp
else:
    return {
        "sucesso": True,
        "acao": acao,
        "dados": {...},
        "mensagem": mensagem,
        "resposta": mensagem,  # main.py consegue extrair
    }
```

---

## 11. CRITÉRIO DE SUCESSO

### 11.1 Requisitos Não Negociáveis

```
Requisito 1: Nenhum acesso obrigatório a update.message em lógica compartilhada
  ✅ SUCESSO: _send_and_stop() não toca em update
  ✅ SUCESSO: executar_acao_gpt() não toca em update
  ✅ SUCESSO: domínio não toca em update

Requisito 2: Nenhum acesso obrigatório a context.bot em lógica compartilhada
  ✅ SUCESSO: executar_acao_gpt() não toca em context.bot
  ✅ SUCESSO: domínio não toca em context.bot
  ⚠️ PARCIAL: _send_and_stop() toca (compatibilidade Telegram)

Requisito 3: Identidade disponível independentemente do canal
  ✅ SUCESSO: IdentidadeContexto criado para ambos
  ✅ SUCESSO: tenant_id resolvido antes de router (WhatsApp)
  ✅ SUCESSO: fallback para Telegram

Requisito 4: tenant_id preservado
  ✅ SUCESSO: Passado do webhook ao router
  ✅ SUCESSO: Não vira wa_id
  ✅ SUCESSO: Usado em paths Firestore

Requisito 5: actor_id preservado
  ✅ SUCESSO: Canônico (whatsapp:5511...)
  ✅ SUCESSO: Usado em lookups

Requisito 6: Telegram continua funcionando
  ✅ SUCESSO: Nenhuma quebra de assinatura
  ✅ SUCESSO: Retorno continua dict/string
  ✅ SUCESSO: already_sent ainda presente

Requisito 7: WhatsApp continua funcionando
  ✅ SUCESSO: mensagens chegam ao usuário
  ✅ SUCESSO: contexto isolado por tenant
  ✅ SUCESSO: identidade correta

Requisito 8: Respostas não desaparecem silenciosamente
  ✅ SUCESSO: _send_and_stop() retorna "resposta"
  ✅ SUCESSO: main.py consegue extrair
  ✅ SUCESSO: whatsapp_service.enviar() é chamada

Requisito 9: Não espalhar "if update is None"
  ✅ PARCIAL: Alguns pontos ainda têm
  ⚠️ PARA DEPOIS: Refatorar para adapter

Requisito 10: Não duplicar regras de negócio
  ✅ SUCESSO: Lógica centralizada em domínio
  ✅ SUCESSO: Adapters apenas formatam

Requisito 11: Não alterar contrato GPT
  ✅ SUCESSO: GPT continua interpretando apenas
  ✅ SUCESSO: Não decide tenant, profissional, etc.

Requisito 12: Paths Firestore corretos
  ✅ SUCESSO: Clientes/{tenant_id}/Sessoes/{actor_id}
  ✅ SUCESSO: Clientes/{tenant_id}/Atores/{actor_id}
  ✅ SUCESSO: Nunca Clientes/{wa_id}/...
```

---

## 12. PLANO DE IMPLEMENTAÇÃO

### 12.1 Fases Propostas

```
P0.1: Contexto de Identidade (Foundation)
P0.2: Contratos de Executor (Core)
P0.3: Correção WhatsApp tenant_id (Critical)
P0.4: Adapter de Resposta (Transport)
P0.5: Refatoração Incremental (Long-term)
```

---

### 12.2 Etapa P0.1: IdentidadeContexto

**Objetivo:** Criar estrutura normalizada

| Aspecto | Detalhe |
|---------|---------|
| **Arquivo** | `utils/identidade_contexto.py` (novo) |
| **Função** | Classe `IdentidadeContexto` + factory |
| **Campos** | user_id, tenant_id, actor_id, canal |
| **Risco** | Muito baixo (apenas nova classe) |
| **Teste Necessário** | 5 testes unitários |
| **Dependência** | Nenhuma |

---

### 12.3 Etapa P0.2: Contrato de Executor

**Objetivo:** Alterar assinatura

| Aspecto | Detalhe |
|---------|---------|
| **Arquivo** | `services/gpt_executor.py` |
| **Função** | `executar_acao_gpt()` (alteração) |
| **Mudança** | Receber `identidade` em vez de `user_id` + `canal_origem` |
| **Risco** | Médio (todos os callsites precisam se adequar) |
| **Teste Necessário** | Regressão em 3 ações (criar_evento, confirmar, etc.) |
| **Dependência** | P0.1 |

---

### 12.4 Etapa P0.3: Correção WhatsApp tenant_id

**Objetivo:** Passar tenant_id ao router (CRÍTICO)

| Aspecto | Detalhe |
|---------|---------|
| **Arquivo 1** | `main.py:237-242` |
| **Mudança 1** | Adicionar `tenant_id=tenant_id` ao roteador_principal() |
| **Arquivo 2** | `router/principal_router.py:3364` |
| **Mudança 2** | Aceitar `tenant_id: str = None` na assinatura |
| **Arquivo 3** | `router/principal_router.py:3376-3379` |
| **Mudança 3** | Usar `tenant_id` passado em vez de tentar resolver |
| **Risco** | Baixo (3 pontos, sem lógica nova) |
| **Teste Necessário** | E2E WhatsApp (tenant correto) |
| **Dependência** | P0.1 (para ter IdentidadeContexto) |

---

### 12.5 Etapa P0.4: Adapter de Resposta

**Objetivo:** Separar transporte de execução

| Aspecto | Detalhe |
|---------|---------|
| **Arquivo 1** | `utils/resultado_acao.py` (novo) |
| **Função 1** | Classe `ResultadoAcao` |
| **Arquivo 2** | `adapters/adapter_resposta.py` (novo) |
| **Função 2** | Classe base + AdapterTelegram + AdapterWhatsApp |
| **Arquivo 3** | `handlers/bot.py` (alteração) |
| **Mudança 3** | Consumir `ResultadoAcao` em vez de dict |
| **Arquivo 4** | `main.py` (alteração) |
| **Mudança 4** | Consumir `ResultadoAcao` em vez de dict |
| **Risco** | Médio (muda padrão de resposta) |
| **Teste Necessário** | 8 testes (4 Telegram, 4 WhatsApp) |
| **Dependência** | P0.2 |

---

### 12.6 Etapa P0.5: Refatoração Incremental

**Objetivo:** Limpeza de código

| Aspecto | Detalhe |
|---------|---------|
| **Foco** | Remover `if update is None` desnecessários |
| **Foco** | Mover lógica pura de admin_command_service |
| **Foco** | Consolidar adapters |
| **Risco** | Baixo (incrementais) |
| **Teste Necessário** | Regressão completa após cada mudança |
| **Dependência** | P0.4 |

---

## 13. GATE ATUAL

Executar `git status --short`:

```bash
cd C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial
git status --short
```

**Esperado:**
- ✅ Nenhum `.py` alterado
- ✅ Nenhum teste alterado
- ✅ Somente este relatório (se já commited)

---

## CONCLUSÕES

### Achados Críticos

1. **Identidade fragmentada:**
   - Telegram: usa user_id como fallback de tenant
   - WhatsApp: perde tenant_id no webhook → router
   - Solução: IdentidadeContexto normalizado

2. **Responsabilidades misturadas:**
   - Executor: executa + formata + conhece canal
   - Router: orquestra + envia + formata
   - Adapter: (não existe)
   - Solução: Separação clara (executor → adapter → handler)

3. **_send_and_stop() é ponto de falha:**
   - Telegram: funciona (envia, marca already_sent)
   - WhatsApp: silêncio (retorna dict sem "resposta")
   - Solução: Adicionar "resposta" em retorno

4. **WhatsApp tenant_id é perdido:**
   - Resolvido no webhook (correto)
   - Não passado ao router (bug)
   - Cai em fallback wa_id (incorreto)
   - Solução: Passar tenant_id ao router

---

### Recomendações

**Curto prazo (1-2 sprints):**
1. ✅ P0.1: IdentidadeContexto
2. ✅ P0.3: Correção WhatsApp tenant_id (CRÍTICO)
3. ✅ Pequeninhos fixes em _send_and_stop() e executor

**Médio prazo (2-3 sprints):**
4. ✅ P0.2: Contrato Executor com identidade
5. ✅ P0.4: Adapter de Resposta

**Longo prazo (próximos sprints):**
6. ✅ P0.5: Refatoração e limpeza

---

### Risco de NÃO fazer

```
Se não fizer P0.3 (correção WhatsApp tenant_id):
  ❌ WhatsApp continua carregando contexto errado
  ❌ Onboarding processa com tenant errado
  ❌ Eventos criados em tenant errado
  ❌ Dados misturados entre clientes

Se não fizer P0.1-P0.2 (identidade + executor):
  ❌ Difícil adicionar novos canais
  ❌ Código continua fragmentado
  ❌ Risco de mais bugs semelhantes

Se não fizer P0.4 (adapter):
  ❌ Responsabilidades continuam misturadas
  ❌ "if update is None" espalhado
  ❌ Difícil testar lógica de negócio
```

---

## PRÓXIMOS PASSOS

1. ✅ **Aprovação desta arquitetura**
2. ✅ **Planejamento de P0.1**
3. ✅ **Implementação em paralelo com outros trabalhos**

---

**Documento:** `CONTRATO_ARQUITETURAL_MULTICANAL.md`  
**Data:** 2026-10-02  
**Status:** 📋 ANÁLISE COMPLETA — AGUARDANDO APROVAÇÃO
