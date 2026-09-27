# DIFF PLANEJADO — C4.2.2 INTEGRAÇÃO IDEMPOTÊNCIA

**Data:** 2026-09-25  
**Escopo:** Integração controlada sem commit/push  
**Status:** PRÉ-EXECUÇÃO (aguardando aprovação implícita)  

---

## 1. AJUSTE EM: notificacoes_idempotencia_service.py

### Mudança: Timeout de Claim

**Linha atual:** `CLAIM_TIMEOUT_MINUTOS = 5`

**Mudança planejada:**
```python
# ANTES
CLAIM_TIMEOUT_MINUTOS = 5

# DEPOIS
CLAIM_TIMEOUT_MINUTOS = 1  # Reduzido de 5 para 1 minuto (60 segundos)
```

**Justificativa:** R2 (timeout muito longo) — máx latência de bot.send_message() é ~30s

---

## 2. INTEGRAÇÃO EM: scheduler/notificacoes_scheduler.py

### 2.1 Adição de Imports

**Local:** Início do arquivo (após imports existentes)

**Adicionar:**
```python
import uuid
from services.notificacoes_idempotencia_service import (
    tentar_claim_notificacao,
    confirmar_notificacao_processada,
    marcar_notificacao_erro,
)
```

### 2.2 Variável Global de Processo

**Local:** Dentro de `processar_notificacoes_agendadas()`, linha ~92 (após `bot = await _get_bot()`)

**Adicionar:**
```python
# Identificador único desta instância de processamento
processo_id = str(uuid.uuid4())
logger.info(f"[IDEMPOT] Sessão de processamento ID: {processo_id}")
```

### 2.3 Integração no Fluxo Normal (antes de CONFIRMAR_RESERVA)

**Local:** Linha 119, dentro do loop `for notif_id, notif in notificacoes.items():`

**ANTES DE QUALQUER PROCESSAMENTO, adicionar (após linha 121):**
```python
# =========================================================
# 🔒 IDEMPOTÊNCIA: Tentar obter claim exclusivo
# =========================================================
try:
    sucesso_claim, _ = await tentar_claim_notificacao(
        user_id, notif_id, processo_id
    )
    if not sucesso_claim:
        logger.info(
            f"[IDEMPOT] Notificação já está sendo processada por outro worker: "
            f"{user_id}/{notif_id}"
        )
        continue  # Outro processo tem o claim, pular
except Exception as e:
    logger.error(f"[IDEMPOT] Erro ao tentar claim: {user_id}/{notif_id}: {e}")
    continue
```

### 2.4 Integração no Fluxo CONFIRMAR_RESERVA

**Local:** Linha 206-207 (após atualização bem-sucedida de confirmação)

Após o `continue` de confirmação bem-sucedida, adicionar:
```python
# ✅ Confirmar que foi processada com sucesso
try:
    await confirmar_notificacao_processada(
        user_id, notif_id, processo_id
    )
except Exception as e:
    logger.warning(
        f"[IDEMPOT] Erro ao confirmar CONFIRMAR_RESERVA: "
        f"{user_id}/{notif_id}: {e}"
    )
```

**E NO TRATAMENTO DE ERRO (linha 210-217)**, modificar exceção para liberar claim:
```python
except Exception as e:
    logger.error(f"❌ Erro ao processar CONFIRMAR_RESERVA para {destinatario_id}: {e}")
    
    # Liberar claim em caso de erro
    try:
        await marcar_notificacao_erro(
            user_id, notif_id, processo_id, 
            f"CONFIRMAR_RESERVA: {str(e)}"
        )
    except Exception as mark_e:
        logger.error(f"[IDEMPOT] Erro ao marcar erro: {mark_e}")
    continue
```

### 2.5 Integração no Fluxo Normal de Envio (Principal)

**Local:** Linhas 243-256

**SUBSTITUIR** (linhas 243-256):
```python
# ✅ ANTES (CÓDIGO ATUAL):
try:
    if canal == "telegram":
        await bot.send_message(chat_id=int(destinatario_id), text=mensagem)
    elif canal == "whatsapp":
        from services.whatsapp_service import enviar_mensagem_whatsapp
        await enviar_mensagem_whatsapp(destinatario_id, mensagem)
    else:
        await bot.send_message(chat_id=int(destinatario_id), text=mensagem)

    await atualizar_dado_em_path(f"{path}/{notif_id}", {
        "avisado": True,
        "status": "enviado",
        "enviado_em": agora.isoformat()
    })
    logger.info(f"✅ Notificação enviada para {destinatario_id} via {canal}: {mensagem}")

except Exception as e:
    logger.error(f"Erro ao enviar notificação para {destinatario_id} via {canal}: {e}")
    await atualizar_dado_em_path(f"{path}/{notif_id}", {
        "status": "erro",
        "erro": str(e),
        "atualizado_em": agora.isoformat()
    })

# ✅ DEPOIS (COM IDEMPOTÊNCIA):
try:
    if canal == "telegram":
        await bot.send_message(chat_id=int(destinatario_id), text=mensagem)
    elif canal == "whatsapp":
        from services.whatsapp_service import enviar_mensagem_whatsapp
        await enviar_mensagem_whatsapp(destinatario_id, mensagem)
    else:
        await bot.send_message(chat_id=int(destinatario_id), text=mensagem)

    # ✅ Envio bem-sucedido → confirmar processamento
    try:
        await confirmar_notificacao_processada(
            user_id, notif_id, processo_id
        )
    except Exception as confirm_e:
        logger.error(f"[IDEMPOT] Erro ao confirmar: {user_id}/{notif_id}: {confirm_e}")
        # Continuamos mesmo com erro na confirmação (já foi enviada)
        await atualizar_dado_em_path(f"{path}/{notif_id}", {
            "avisado": True,
            "status": "enviado",
            "enviado_em": agora.isoformat(),
            "confirmacao_erro": str(confirm_e)
        })
    
    logger.info(f"✅ Notificação enviada para {destinatario_id} via {canal}: {mensagem}")

except Exception as e:
    logger.error(f"Erro ao enviar notificação para {destinatario_id} via {canal}: {e}")
    
    # ❌ Envio falhou → marcar erro e liberar claim
    try:
        await marcar_notificacao_erro(
            user_id, notif_id, processo_id,
            f"Envio {canal}: {str(e)}"
        )
    except Exception as mark_e:
        logger.error(f"[IDEMPOT] Erro ao marcar erro: {mark_e}")
```

---

## 3. RESUMO DAS MUDANÇAS

| Arquivo | Tipo | Linhas | O quê | Por quê |
|---------|------|--------|-------|---------|
| notificacoes_idempotencia_service.py | MODIFY | 33 | Timeout 5 min → 1 min | R2 |
| scheduler/notificacoes_scheduler.py | ADD | ~94-97 | Imports + uuid | Função idempotência |
| scheduler/notificacoes_scheduler.py | ADD | ~95-96 | processo_id global | Identificar instância |
| scheduler/notificacoes_scheduler.py | ADD | ~122-131 | Claim antes processar | Atomicidade |
| scheduler/notificacoes_scheduler.py | ADD | ~206-211 | Confirmar RESERVA | Fluxo sucesso |
| scheduler/notificacoes_scheduler.py | MODIFY | ~210-218 | Erro RESERVA libera claim | Fluxo erro |
| scheduler/notificacoes_scheduler.py | MODIFY | ~243-265 | Envio + confirmar/erro | Fluxo principal |

---

## 4. ESTATÍSTICAS

- **Linhas adicionadas:** ~60
- **Linhas modificadas:** ~5
- **Linhas removidas:** 0
- **Novos imports:** 2 (uuid, idempotencia_service)
- **Novos tries-except:** 3 (claim, confirmar, erro)

---

## 5. FLUXO APÓS INTEGRAÇÃO

```
Para cada notificação:

1. [NOVO] Tentar claim exclusivo
   ├─ Sucesso → continua
   └─ Falha → pula (outro worker processando)

2. [EXISTENTE] Validação (avisado, data, expiração)
   ├─ OK → continua
   └─ FAIL → marca erro/expira

3. [EXISTENTE] CONFIRMAR_RESERVA (se aplicável)
   ├─ Sucesso:
   │  └─ [NOVO] Confirmar processamento
   └─ Erro:
      └─ [NOVO] Marcar erro (libera claim)

4. [EXISTENTE] Envio via bot (se aplicável)
   ├─ Sucesso:
   │  ├─ [NOVO] Confirmar processamento
   │  └─ Log sucesso
   └─ Erro:
      ├─ [NOVO] Marcar erro (libera claim)
      └─ Log erro

5. [NOVO] Próxima notificação
```

---

## 6. GARANTIAS APÓS INTEGRAÇÃO

| Garantia | Antes | Depois | Teste |
|----------|-------|--------|-------|
| Sem duplicação enquanto claim válido | ❌ | ✅ | T7 |
| Claim expires em 60 segundos | ❌ | ✅ | T3 |
| Sucesso confirma AVISADO | ✅ | ✅ | T4 |
| Erro não confirma AVISADO | ✅ | ✅ | T5 |
| Isolamento tenant | ✅ | ✅ | T8 |
| At-least-once (não exactly-once) | ❌ | ✅* | T9 |

*documented, not guaranteed

---

## 7. RISCO RESIDUAL

**R1: Duplicação pós-envio ainda existe**

Se bot.send_message() sucede mas confirmar_notificacao_processada() falha ou não é executado, notificação fica em "processando" com avisado=false.

Mitigação: timeout reduzido para 60s (vs 5 min antes).

---

## 8. PRÓXIMOS PASSOS (NÃO EXECUTAR AINDA)

1. Aplicar modificação em notificacoes_idempotencia_service.py
2. Aplicar modificações em scheduler/notificacoes_scheduler.py
3. Rodar testes T1-T9 (novos específicos de integração)
4. Validar `git diff --check`
5. Executar testes existentes de regressão
6. Documentar resultado

