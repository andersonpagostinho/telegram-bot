# SPEC P0.1 — CANCELAMENTO SEGURO: REGRAS FALTANTES

**Data:** 2026-06-15  
**Status:** ✅ APROVADO COM AJUSTES  
**Escopo:** Apenas regras não definidas pela auditoria  
**Não Inclui:** Implementação de código, refatoração, encaixe, reagendamento  

---

## 🎯 OBJETIVO

Definir as 8 regras de negócio críticas para implementar P0.1 com segurança.

---

## 📋 REGRA 1: CONFIRMAÇÃO DE CANCELAMENTO

### Decisão

```
✅ Evento ÚNICO também exige confirmação
✅ Usar resposta natural (texto): não / desistir / manter / deixa como está
❌ NÃO aceitar "cancelar" como negação (ambíguo)
✅ Números continuam APENAS para escolher entre múltiplos eventos
```

### Fluxo

**Cenário: 1 evento encontrado**
```
Cliente: "cancela meu corte"
    ↓
Sistema busca: 1 evento encontrado
    ↓
Sistema: "Tem certeza de cancelar Corte com Carla em 20/06 às 15h? (sim/não)"
    ↓
Cliente: "sim"
    ↓
[Prosseguir com cancelamento]
    OR
Cliente: "não" / "desistir" / "manter" / "deixa como está"
    ↓
[Abortar, limpar estado, evento fica ativo]
```

**Cenário: Múltiplos eventos encontrados**
```
Cliente: "cancela corte"
    ↓
Sistema: "Encontrei 3:
          1) Corte com Carla — 20/06 às 15h
          2) Corte com Paula — 21/06 às 10h
          3) Corte com Marina — 22/06 às 14h
          Responda o número (1/2/3):"
    ↓
Cliente: "2"
    ↓
Sistema: "Tem certeza de cancelar Corte com Paula em 21/06 às 10h? (sim/não)"
    ↓
Cliente: "sim"
    ↓
[Prosseguir com cancelamento]
```

### Estado em Contexto Temporário

**Onde salvar:**
```python
ctx = {
    "estado_fluxo": "aguardando_confirmacao_cancelamento",  # novo estado
    "cancelamento_pendente": {
        "evento_id": "uuid_do_evento",
        "cliente_id": "user_123",                           # quem solicitou
        "tenant_id": "dono_456",                            # a qual dono pertence
        "origem": "cliente" | "dono" | "profissional",     # quem está cancelando
        "resumo_evento": {                                  # para mostrar em confirmação
            "descricao": "Corte com Carla",
            "data": "2026-06-20",
            "hora_inicio": "15:00",
            "profissional": "Carla"
        }
    }
}
```

### Resposta Negativa

Se cliente responder `"não"` / `"desistir"` / `"manter"` / `"deixa como está"`:
```python
# Ação:
1. Limpar: ctx["cancelamento_pendente"] = None
2. Limpar: ctx["estado_fluxo"] = anterior (ou "idle")
3. Manter: Evento ativo (status não alterado)
4. Resposta: "Tudo bem, cancelamento abortado. Seu horário continua reservado."
5. Log: "Cancelamento abortado por cliente: evento_id={evento_id}"
```

### Compatibilidade

Este estado **não interfere** com:
```
✅ Outras ações simultâneas (conversa segue normal)
✅ Confirmação de agendamento (estado separado)
✅ Contexto temporário persistente (MemoriaTemporaria)
❌ Timeout (será implementado em futuro)
```

---

## 📋 REGRA 2: PERMISSÃO DE CANCELAMENTO

### Validação Obrigatória

**Antes de proceder com qualquer cancelamento, validar:**

#### 2.1 Cliente Cancelando

```
Regra: Cliente só cancela evento em que é participante
    (cliente_id do evento == user_id do solicitante)

Validação:
  1. Obter evento: evento = buscar_evento(evento_id)
  2. Obter user_id solicitante: user_id = update.effective_user.id
  3. Verificar: if evento["cliente_id"] != user_id → BLOQUEAR
  
Mensagem se bloqueado:
  "❌ Você não pode cancelar evento de outro cliente."
  
Exemplo PERMITIDO:
  ├─ Cliente Maria (user_123)
  ├─ Evento tem cliente_id = user_123
  └─ ✅ Pode cancelar

Exemplo BLOQUEADO:
  ├─ Cliente João (user_789)
  ├─ Evento tem cliente_id = user_123 (Maria)
  └─ ❌ Não pode cancelar
```

#### 2.2 Dono Cancelando

```
Regra: Dono cancela QUALQUER evento dentro do seu tenant

Validação:
  1. Obter tenant_id do solicitante: tenant_id = await obter_id_dono(user_id)
  2. Obter tenant_id do evento: evento_tenant = obter_id_dono(evento["cliente_id"])
  3. Verificar: if evento_tenant != tenant_id → BLOQUEAR
  
Mensagem se bloqueado:
  "❌ Evento não pertence ao seu negócio."
  
Exemplo PERMITIDO:
  ├─ Dono João (user_456)
  ├─ Evento cliente_id = user_123
  ├─ Dono de user_123 = user_456
  └─ ✅ Pode cancelar

Exemplo BLOQUEADO:
  ├─ Dono A (user_100)
  ├─ Evento cliente_id = user_789
  ├─ Dono de user_789 = user_200 (diferente)
  └─ ❌ Não pode cancelar
```

#### 2.3 Profissional Cancelando

```
Regra: Profissional cancela APENAS eventos vinculados ao próprio nome/id
       SOMENTE SE papel "profissional" estiver definido

Validação:
  1. Verificar: if user_type != "profissional" → BLOQUEAR
  2. Obter nome/id profissional: prof_id = user_id ou dados_usuario["nome_profissional"]
  3. Verificar: if evento["profissional"] != prof_id → BLOQUEAR
  
Mensagem se bloqueado:
  ❌ "Você não pode cancelar eventos de outros profissionais."
  ❌ "Você não tem permissão para cancelar eventos."
  
Exemplo PERMITIDO:
  ├─ Profissional Carla (user_888, tipo="profissional")
  ├─ Evento tem profissional="Carla"
  └─ ✅ Pode cancelar
  
Exemplo BLOQUEADO:
  ├─ Profissional Carla (user_888)
  ├─ Evento tem profissional="Paula"
  └─ ❌ Não pode cancelar
```

### Se Validação Não For Possível

```
Decisão: BLOQUEAR o cancelamento

Cenário:
  ├─ Sistema não consegue validar ownership
  ├─ Dados malformados ou incompletos
  └─ Resposta: "❌ Não consegui validar permissão. Tente novamente."
  
Log: "PERMISSAO_BLOQUEADA: evento_id={id}, user_id={user}, motivo=validacao_falhou"
```

---

## 📋 REGRA 3: REGISTRAR ORIGEM DO CANCELAMENTO

### Campos Obrigatórios

Adicionar ao evento (soft delete update):

```python
cancelamento = {
    "cancelado_por": "user_123",                    # user_id de quem cancelou
    "cancelado_por_tipo": "cliente",                # ou "dono" ou "profissional" ou "sistema"
    "cancelado_em": "2026-06-15T14:30:00-03:00",   # ISO timestamp
    "motivo_cancelamento": "opcional texto",        # OPCIONAL
    "cancelamento_confirmado_em": "2026-06-15T14:30:05-03:00"  # timestamp da confirmação
}

# Aplicar
await atualizar_dado_em_path(
    f"Clientes/{tenant_id}/Eventos/{evento_id}",
    {
        "status": "cancelado",
        **cancelamento
    }
)
```

### Campo: cancelado_por

```
Regra: user_id de quem executa o cancelamento

Exemplos:
  ├─ Cliente cancela seu evento
  │  └─ cancelado_por = user_id do cliente
  ├─ Dono cancela evento de cliente
  │  └─ cancelado_por = user_id do dono
  ├─ Profissional marca indisponibilidade (P0.2)
  │  └─ cancelado_por = user_id do profissional
  └─ Sistema cancela por erro/conflito (raro)
     └─ cancelado_por = "SISTEMA"
```

### Campo: cancelado_por_tipo

```
Valores permitidos: "cliente" | "dono" | "profissional" | "sistema"

Mapeamento:
  ├─ Cliente (tipo_usuario="cliente" ou modo_uso="atendimento_cliente")
  │  └─ cancelado_por_tipo = "cliente"
  ├─ Dono (é proprietário do tenant)
  │  └─ cancelado_por_tipo = "dono"
  ├─ Profissional (tipo_usuario="profissional" e está vinculado ao evento)
  │  └─ cancelado_por_tipo = "profissional"
  └─ Sistema (operação automática, não implementado em P0.1)
     └─ cancelado_por_tipo = "sistema"
```

### Campo: motivo_cancelamento

```
Regra: OPCIONAL, capturado se cliente oferecer

Cenário 1: Sem oferecer motivo
  Cliente: "cancela meu corte"
  └─ motivo_cancelamento = None

Cenário 2: Oferecendo motivo
  Cliente: "cancela meu corte, tenho outro compromisso"
  └─ motivo_cancelamento = "tenho outro compromisso"

Extração:
  ├─ GPT pode extrair na resposta JSON
  ├─ Ou sistema oferece lista (futuro)
  └─ Se não extraído, deixar null
  
Se EXISTIR motivo, incluir na notificação ao cliente.
Ver REGRA 5 para detalhes.
```

### Campo: cancelamento_confirmado_em

```
Regra: timestamp de quando cliente confirmou (respondeu "sim")

Timeline:
  1. Cliente: "cancela meu corte" (T0)
  2. Sistema pergunta: "Tem certeza?" (T1)
  3. Cliente: "sim" (T2) ← cancelamento_confirmado_em = T2
  4. Sistema: marca status="cancelado", cancelado_em=T3, cancelamento_confirmado_em=T2
```

### Log Obrigatório

```
Após cada cancelamento, registrar:

"[CANCELAMENTO] evento_id={id} | cancelado_por={user} | tipo={tipo} | motivo={motivo}"

Exemplo:
"[CANCELAMENTO] evt_abc123 | cancelado_por=user_123 | tipo=cliente | motivo=outro_compromisso"
```

---

## 📋 REGRA 4: NOTIFICAÇÕES

### Canais

```
Decisão: Usar MESMO CANAL DA CONVERSA ATUAL

Implementação:
  ├─ Se conversa é Telegram → notificação por Telegram
  ├─ Se conversa é WhatsApp → notificação por WhatsApp
  ├─ Se conversa é SMS → notificação por SMS
  └─ Não há fallback email em P0.1

Responsabilidade:
  ├─ Detectar canal atual: update.message.chat.type
  ├─ Usar mesmo bot/API para enviar notificação
  └─ Se falhar, logar erro mas não abortar cancelamento
```

### Quem Notificar

#### 4.1 Se Cliente Cancela

```
Notificar:
  1. ✅ Dono (proprietário do evento)
  2. ✅ Profissional (quem atende)

Não notificar:
  ❌ Outros clientes
  ❌ Terceiros
```

#### 4.2 Se Dono Cancela

```
Notificar:
  1. ✅ Cliente (quem recebe o atendimento)
  2. ✅ Profissional (quem atende)

Contexto:
  └─ "Seu horário precisou ser cancelado pelo negócio"
```

#### 4.3 Se Profissional Cancela (P0.2)

```
Notificar:
  1. ✅ Dono (proprietário)
  2. ✅ Cliente (quem recebe o atendimento)

Contexto:
  └─ "Seu profissional marcou indisponibilidade"
```

### Momento da Notificação

```
Regra: SOMENTE APÓS cancelamento ser salvo com sucesso

Timeline:
  1. Cliente confirma: "sim"
  2. Validar permissão ✓
  3. SALVAR: status="cancelado" em Firestore
  4. DEPOIS: enviar notificações
  
Se erro no passo 3:
  └─ Não enviar notificações, retornar erro ao cliente

Se erro no passo 4:
  └─ Cancelamento já ocorreu (status salvo)
  └─ Logar erro de notificação
  └─ Não reverter cancelamento
```

### Falha de Notificação

```
Decisão: Falha de notificação NÃO reverte cancelamento

Fluxo:
  1. Status="cancelado" salvo ✓
  2. Enviar notificação ao dono
     └─ Falha (dono offline, canal indisponível)
  3. Enviar notificação ao profissional
     └─ Falha
  4. Ação: logar erro, mas evento continua cancelado
  
Log:
  "[NOTIFICACAO_ERRO] evento_id={id} | destinatario=dono | erro={motivo}"
  "[NOTIFICACAO_ERRO] evento_id={id} | destinatario=profissional | erro={motivo}"
```

---

## 📋 REGRA 5: CONTEÚDO DAS MENSAGENS

### Variáveis Disponíveis

```python
{
    "cliente": "Maria Silva",           # nome do cliente
    "servico": "corte",                 # tipo de serviço
    "profissional": "Carla",            # nome profissional
    "data": "20/06/2026",               # formatado DD/MM/YYYY
    "hora": "15:00",                    # formatado HH:MM
    "motivo": "outro compromisso",      # OPCIONAL
}
```

### Mensagem 1: Confirmação ao Cliente que Cancelou

**Template:**
```
✅ Cancelado. Seu horário de {servico} com {profissional} em {data} às {hora} foi cancelado.
```

**Exemplos:**
```
✅ Cancelado. Seu horário de Corte com Carla em 20/06/2026 às 15:00 foi cancelado.
✅ Cancelado. Seu horário de Escova com Paula em 21/06/2026 às 10:30 foi cancelado.
```

---

### Mensagem 2: Notificação ao Dono/Profissional (Cliente Cancelou)

**Template:**
```
⚠️ Cancelamento: {cliente} cancelou {servico} com {profissional} em {data} às {hora}.
```

**Exemplos:**
```
⚠️ Cancelamento: Maria cancelou Corte com Carla em 20/06/2026 às 15:00.
⚠️ Cancelamento: João cancelou Escova com Paula em 21/06/2026 às 10:30.
```

---

### Mensagem 3: Notificação ao Cliente (Dono/Profissional Cancela)

**Template (SEM motivo):**
```
⚠️ Seu horário de {servico} com {profissional} em {data} às {hora} precisou ser cancelado.
```

**Template (COM motivo):**
```
⚠️ Seu horário de {servico} com {profissional} em {data} às {hora} precisou ser cancelado. Motivo: {motivo}.
```

**Exemplos:**
```
⚠️ Seu horário de Corte com Carla em 20/06/2026 às 15:00 precisou ser cancelado.

⚠️ Seu horário de Corte com Carla em 20/06/2026 às 15:00 precisou ser cancelado. Motivo: profissional indisponível.
```

---

## 📋 REGRA 6: ENCAIXE E REAGENDAMENTO (FORA DO ESCOPO)

### Decisão

```
❌ COMPLETAMENTE FORA DO ESCOPO P0.1
├─ Nenhum motor de encaixe automático
├─ Nenhuma auto-criação de novo evento
├─ Nenhuma auto-proposição de alternativas
└─ Nenhum re-arranjo de agenda

✅ O que P0.1 FAZ:
├─ Marca status="cancelado"
├─ Libera horário imediatamente
└─ Oferece mensagem: "Posso ajudar com novo agendamento?"
```

### Fluxo de Reagendamento (Manual, Fora de P0.1)

```
1. Evento cancelado ✓
2. Cliente recebe notificação ✓
3. Cliente responde: "Sim, quero agendar novo"
4. Sistema: inicia fluxo normal de agendamento
5. Cliente escolhe data/hora
6. Novo evento criado (fluxo normal)
```

### Não Fazer

```
❌ Auto-criar novo evento no horário original com outro profissional
❌ Auto-propor clientes com conflitos para mudar de horário
❌ Auto-mover cliente para próximo horário disponível
❌ Auto-notificar clientes de conflitos
❌ Auto-sugerir profissional alternativo sem confirmação
```

---

## 📋 REGRA 7: HARD DELETE

### Decisão

```
❌ deletar_evento() NÃO deve ser usado no fluxo normal de cancelamento
⚠️ Se existir, marcar como OPERAÇÃO ADMINISTRATIVA PERIGOSA
✅ P0.1 usa APENAS soft delete (status="cancelado")
```

### Uso de deletar_evento()

```
Classificação: LEGADO / OPERAÇÃO ADMINISTRATIVA

Permitido apenas em:
  ├─ Testes automatizados
  ├─ Limpeza de dados (admin)
  ├─ Recuperação de erro crítico (com auditoria)
  └─ Reversão (raro)

Proibido em:
  ❌ Cancelamento normal
  ❌ Fluxo de cliente
  ❌ Fluxo de dono
  ❌ Fluxo automático
```

### Marcação no Código

```python
async def deletar_evento(user_id: str, event_id: str) -> bool:
    """
    ⚠️ OPERAÇÃO ADMINISTRATIVA PERIGOSA - HARD DELETE
    
    Apaga evento completamente do Firestore.
    NÃO USAR em fluxos normais — usar cancelar_evento() (soft delete).
    
    Permitido apenas em testes, cleanup admin ou recuperação de erro crítico.
    """
```

---

## 📋 REGRA 8: TIMEOUT

### Decisão

```
❌ SEM timeout automático em P0.1
✅ Estado pendente limpo apenas por:
   ├─ Confirmação ("sim" → cancela)
   ├─ Negação ("não/desistir/manter/deixa como está" → aborta)
   ├─ Novo fluxo incompatível (muda estado_fluxo)
   └─ Limpeza de contexto existente (nova sessão)
```

### Quando Estado é Limpo

```
Evento: Cliente responde "não" / "desistir" / "manter" / "deixa como está"
  └─ Ação: limpar cancelamento_pendente imediatamente

Evento: Cliente inicia novo fluxo (ex: agendar novo evento)
  └─ Ação: limpar cancelamento_pendente (assumir interesse mudou)

Evento: Contexto expirado naturalmente (MemoriaTemporaria TTL)
  └─ Ação: automático (TTL do sistema)

Evento: Cliente sair e voltar (nova sessão)
  └─ Ação: limpar (novo contexto carregado)
```

### Melhoria Futura (P0.2+)

```
Considerar para futuro:
  ├─ Timeout de 5 minutos se cliente não responder
  ├─ Notificação de lembrete se pendente > 2 minutos
  ├─ Auto-abortar após timeout
  └─ Log de timeouts para análise
```

---

## ✅ VALIDAÇÃO DE COMPLETUDE

**Estas 8 regras cobrem:**

```
✅ Confirmação: não/desistir/manter/deixa como está, estado, negação
✅ Permissão: cliente, dono, profissional
✅ Auditoria: cancelado_por, tipo, timestamps, motivo (opcional, incluir em notificações)
✅ Notificações: canal, quem, quando, conteúdo com motivo, falha
✅ Encaixe: completamente fora
✅ Reagendamento: completamente fora
✅ Hard delete: classificado (legado)
✅ Timeout: sem timeout
```

**Pronto para:**
```
✅ Code review (regras claras)
✅ Implementação (nenhuma ambiguidade)
✅ Testes (critérios definidos)
✅ Documentação de mudanças
```

---

## 📖 REFERÊNCIAS

- **Auditoria Completa:** `docs/auditorias/AUDITORIA_P0_CANCELAMENTO_ATUAL.md`
- **Sumário Executivo:** `SUMARIO_AUDITORIA_P0_CANCELAMENTO.md`
- **Arquivos Afetados:**
  - `services/event_service_async.py` (cancelar_evento)
  - `services/gpt_executor.py` (fluxo GPT)
  - `handlers/event_handler.py` (confirmação)

---

**Status:** ✅ REGRAS APROVADAS COM AJUSTES  
**Data:** 2026-06-15  
**Próximo:** Plano de patch mínimo P0.1
