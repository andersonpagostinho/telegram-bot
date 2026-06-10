# Notificação de Lembrete para Profissional

## Visão Geral

Quando um evento é criado com um profissional responsável, o sistema cria automaticamente **duas notificações de lembrete**:

1. **Cliente**: recebe lembrete do seu agendamento
2. **Profissional**: recebe lembrete do atendimento agendado

Ambas as notificações disparam X minutos antes do horário do evento (padrão: 30 minutos).

---

## Implementação

### Função Principal

```python
from services.notificacao_service import criar_notificacoes_evento_cliente_e_profissional

resultado = await criar_notificacoes_evento_cliente_e_profissional(
    tenant_id="usuario123",           # ID do dono
    evento_id="evento_001",           # ID do evento
    cliente_id="cliente_bruna",       # ID do cliente
    cliente_nome="Bruna",             # Nome do cliente
    profissional_nome="Carla",        # Nome do profissional
    profissional_user_id="prof_carla", # ID/telegram_id do profissional
    data="2026-06-10",                # Data (YYYY-MM-DD)
    hora_inicio="14:00",              # Horário (HH:MM)
    canal_cliente="telegram",         # Canal: "telegram" ou "whatsapp"
    canal_profissional="telegram",    # Canal: "telegram" ou "whatsapp"
    minutos_antes=30,                 # Minutos antes do evento
    descricao="lembrete_evento",      # Tipo de notificação
)

# Resultado retorna:
# {
#     "cliente": {
#         "sucesso": True,
#         "notif_id": "uuid-notif-cliente"
#     },
#     "profissional": {
#         "sucesso": True,
#         "notif_id": "uuid-notif-profissional"
#     }
# }
```

---

## Campos da Notificação

Cada notificação contém:

```json
{
  "tenant_id": "usuario123",
  "evento_id": "evento_001",
  "destinatario_user_id": "cliente_bruna ou prof_carla",
  "papel_destinatario": "cliente ou profissional",
  "profissional_nome": "Carla",
  "cliente_nome": "Bruna",
  "tipo": "lembrete_evento",
  "data_hora": "2026-06-10T13:30:00-03:00",
  "avisado": false,
  "processada": false,
  "status": "pendente",
  "motivo_expiracao": null,
  "canal": "telegram ou whatsapp",
  "minutos_antes": 30,
  "criado_em": "2026-06-09T10:00:00-03:00",
  "alvo_evento": {
    "data": "2026-06-10",
    "hora_inicio": "14:00",
    "cliente_nome": "Bruna",
    "profissional": "Carla"
  }
}
```

---

## Proteções Implementadas

### 1. **Não Duplica Notificações**

Se a função for chamada 2x para o mesmo evento:
- **Primeira chamada**: cria notificações de cliente e profissional
- **Segunda chamada**: detecta duplicação e pula (loga aviso)

```python
# Verifica antes de criar:
if await _notificacao_ja_existe(tenant_id, destinatario_user_id, evento_id):
    # Pula criação
    resultado["motivo"] = "duplicada"
```

### 2. **Profissional Sem ID Não Quebra**

Se o profissional não tiver `profissional_user_id`:
- ✅ Cria notificação para **cliente normalmente**
- ⚠️ Loga aviso sobre profissional sem ID
- ✅ **Não quebra o agendamento**

```python
if profissional_user_id:
    # Cria notificação profissional
else:
    logger.warning(f"Profissional sem ID: {profissional_nome}")
    resultado["profissional"]["motivo"] = "profissional_sem_id"
```

### 3. **Path Tenant Mantido**

Todas as notificações são salvas no path do tenant:
```
Clientes/{tenant_id}/NotificacoesAgendadas/{notif_id}
```

Garante isolamento multi-tenant.

### 4. **Expiração Automática**

O scheduler valida expiração:
- Notificações com atraso > 15 minutos são marcadas como expiradas
- Não são enviadas se o sistema voltar ao ar dias depois

---

## Suporte a Canais

| Canal | Classe | Status |
|-------|--------|--------|
| Telegram | `telegram.Bot.send_message()` | ✅ Suportado |
| WhatsApp | `whatsapp_service.enviar_mensagem_whatsapp()` | ✅ Suportado |

Canal pode ser configurado independentemente para cliente e profissional:

```python
# Cliente via Telegram, profissional via WhatsApp
await criar_notificacoes_evento_cliente_e_profissional(
    ...,
    canal_cliente="telegram",
    canal_profissional="whatsapp",
)
```

---

## Integração com Criação de Evento

### Onde Chamar?

Chamar `criar_notificacoes_evento_cliente_e_profissional()` **após** o evento ser salvo com sucesso:

```python
# Em handlers/event_handler.py ou onde eventos são criados:

# 1. Salvar evento
evento_criado = await salvar_evento(evento_data)

if evento_criado:
    # 2. Criar notificações
    resultado_notif = await criar_notificacoes_evento_cliente_e_profissional(
        tenant_id=tenant_id,
        evento_id=evento_criado["id"],
        cliente_id=cliente_id,
        cliente_nome=cliente_nome,
        profissional_nome=profissional_nome,
        profissional_user_id=profissional_user_id,
        data=data,
        hora_inicio=hora_inicio,
    )

    if not resultado_notif["cliente"]["sucesso"]:
        logger.warning("Notificação cliente falhou")

    if not resultado_notif["profissional"]["sucesso"]:
        logger.warning(f"Notificação profissional falhou: {resultado_notif['profissional'].get('motivo')}")
```

### NÃO QUEBRA Outras Operações

A criação de notificações é **assíncrona e isolada**:
- Se falhar, não interrompe agendamento
- Se profissional não tiver ID, continua normalmente
- Erros são apenas logados

---

## Fluxo do Scheduler

O scheduler `processar_notificacoes_agendadas()` processa essas notificações:

```
1. Busca notificações pendentes
   └─ status="pendente", avisado=False

2. Valida data_hora
   └─ Se muito antiga (>15min): marca como expirada, pula

3. Valida papel_destinatario
   └─ Cliente: envia para cliente
   └─ Profissional: envia para profissional

4. Envia via canal apropriado
   └─ Telegram: bot.send_message()
   └─ WhatsApp: whatsapp_service.enviar_mensagem_whatsapp()

5. Marca como enviado
   └─ avisado=True, status="enviado", enviado_em=timestamp
```

---

## Testes

Executar testes de notificação:

```bash
python test_notificacao_profissional.py
```

Testes cobrem:
- ✅ Criação de notificações cliente + profissional
- ✅ Profissional sem ID (aviso, não quebra)
- ✅ Não duplicação em segunda execução

---

## Campos Opcionais

- `minutos_antes`: padrão 30 minutos
- `canal_cliente`: padrão "telegram"
- `canal_profissional`: padrão "telegram"
- `descricao`: padrão "lembrete_evento"

---

## Erros Comuns

### "Profissional sem ID: João evento=evento_001"
**Solução**: Registrar telegram_id/chat_id do profissional em Clientes/{dono}/Profissionais/{prof_nome}

### Notificação não é enviada
**Verificar**:
1. Existe em Firestore? `Clientes/{tenant}/NotificacoesAgendadas`
2. Status é "pendente"? Se for "expirada", não será enviada
3. Atraso > 15 minutos? Sistema marca como expirada
4. Canal está correto? "telegram" ou "whatsapp"

### Duplicação de notificação
**Causa**: função chamada 2x sem verificação prévia

**Solução**: Função já valida, pula automaticamente na segunda execução

---

## Próximos Passos (Opcional)

- [ ] Dashboard de notificações enviadas/expiradas
- [ ] Confirmação de leitura (profissional confirmando lembrete)
- [ ] Notificação de cancelamento para profissional
- [ ] Customização de mensagem por profissional
