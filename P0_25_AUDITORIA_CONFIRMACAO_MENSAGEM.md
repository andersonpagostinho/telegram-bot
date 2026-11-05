# P0.25 — AUDITORIA DO MODELO OFICIAL DE CONFIRMAÇÃO

**Data**: 2026-11-05  
**Status**: 🔴 **ROOT CAUSE IDENTIFICADA**

---

## PROBLEMA

O evento é persistido corretamente, mas o cliente continua recebendo mensagem diferente do modelo oficial:

**Esperado**:
```
✨ *Corte feminino com Bruna*
📆 em 06/11 às 15h

✅ Horário confirmado!
```

**Atual**:
```
Esse horário já está confirmado.

Se precisar alterar ou cancelar, é só me avisar.
```

---

## ROOT CAUSE: CAMPO FALTANTE NO RETORNO

### Fluxo de Confirmação

**1. lock service (`criar_evento_com_lock()`) - linha 789-795**

Quando evento é NOVO e criado com sucesso:

```python
return {
    "ok": True,
    "evento_id": event_id,
    "lock_ids": [...],
    "lock_keys": [...],
    "motivo": "Evento criado com sucesso"
    # ❌ FALTA: "confirmado_nesta_requisicao"
}
```

**2. event_service (`salvar_evento()`) - linha 302**

```python
confirmado_agora = resultado_lock.get("confirmado_nesta_requisicao", False)
                                     # ↑ Defaults to False se field está ausente
```

**3. event_handler - linha 1344**

```python
if resultado_salvamento.get("confirmado_nesta_requisicao") is True:
    # ✅ Envia mensagem oficial com detalhes
    msg_sucesso = montar_mensagem_confirmacao_sucesso(...)
else:
    # ❌ Envia mensagem genérica "já confirmado"
    msg_duplicado = "Esse horário já está confirmado..."
```

---

## EVIDÊNCIA EXATA

### Cenário: Criar novo evento confirmado

**Entrada**:
```python
evento = {
    "data": "2026-11-05",
    "hora_inicio": "14:10",
    "duracao": 30,
    "confirmado": True
}
```

**Execução**:
1. `salvar_evento()` chama `criar_evento_com_lock()`
2. Lock service cria locks e salva evento
3. Lock service retorna (linha 789):
   ```python
   {"ok": True, "evento_id": "...", "motivo": "Evento criado com sucesso"}
   ```
4. `salvar_evento()` tenta extrair:
   ```python
   confirmado_agora = resultado_lock.get("confirmado_nesta_requisicao", False)
   # ↑ Campo não existe, defaults to False
   ```
5. Retorna para event_handler:
   ```python
   {
       "ok": True,
       "status": "duplicado_confirmado",  # ← Enganoso!
       "confirmado_nesta_requisicao": False  # ← INCORRETO (deveria ser True)
   }
   ```
6. event_handler na linha 1344:
   ```python
   if confirmado_nesta_requisicao is True:  # False, então não entra
       msg_sucesso = montar_mensagem_confirmacao_sucesso()
   else:  # ENTRA AQUI
       msg_duplicado = "Esse horário já está confirmado..."
   ```

---

## CAMINHO COMPLETO DA RESPOSTA INCORRETA

| Componente | Arquivo | Linha | Comportamento |
|-----------|---------|-------|---------------|
| **1. Lock Service** | `agenda_lock_service.py` | 789-795 | Retorna SUCESSO sem "confirmado_nesta_requisicao" |
| **2. Event Service** | `event_service_async.py` | 302 | Extrai field, defaults False se ausente |
| **3. Event Service** | `event_service_async.py` | 305-311 | Retorna dict com confirmado_nesta_requisicao=False |
| **4. Event Handler** | `event_handler.py` | 1342-1370 | Verifica confirmado_nesta_requisicao |
| **5. Event Handler** | `event_handler.py` | 1360-1370 | ENTRA EM CASE B, envia msg genérica |
| **6. WhatsApp Utils** | `whatsapp_utils.py` | (envio) | Envia mensagem genérica ao cliente |

---

## CONTRASTE: CASO QUE FUNCIONA

Quando evento está PENDENTE e é confirmado (linha 769):

```python
return {
    "ok": True,
    "status": "duplicado_pendente_agora" if confirmado_nesta_requisicao else "duplicado_confirmado",
    "confirmado_nesta_requisicao": confirmado_nesta_requisicao,  # ← PRESENTE!
    "motivo": "Confirmação concluída"
}
```

Aqui o field EXISTE e é True, então event_handler envia a mensagem correta.

---

## CAUSA RAIZ

**Lock service retorna estrutura diferente para:**
- ✅ UPDATE (evento pendente → confirmado): retorna "confirmado_nesta_requisicao"
- ❌ CREATE (novo evento): NÃO retorna "confirmado_nesta_requisicao"

**Resultado**: `salvar_evento()` não consegue distinguir entre:
- Uma confirmação bem-sucedida de NOVO evento
- Uma idempotência de evento já confirmado

---

## FLUXO ALTERNATIVO QUE DEVERIA FUNCIONAR

Se a NEW creation (linha 789) retornasse:

```python
return {
    "ok": True,
    "evento_id": event_id,
    "lock_ids": [...],
    "motivo": "Evento criado com sucesso",
    "confirmado_nesta_requisicao": True  # ← DEVERIA ESTAR AQUI
}
```

Então event_handler receberia:
```python
{
    "ok": True,
    "status": "duplicado_confirmado",
    "confirmado_nesta_requisicao": True  # ← TRUE!
}
```

E na linha 1344:
```python
if confirmado_nesta_requisicao is True:  # ← VERDADEIRO
    msg_sucesso = montar_mensagem_confirmacao_sucesso(servico, profissional, start_time)
    await enviar_mensagem_whatsapp(user_id, msg_sucesso, ...)
    # ✅ ENVIA MENSAGEM OFICIAL!
```

---

## ARQUIVO E LINHAS EXATAS

### Arquivo 1: `services/agenda_lock_service.py`

**Problema**: Linha 789-795

Nova criação de evento não retorna `"confirmado_nesta_requisicao"`:

```python
# ❌ PROBLEMA
return {
    "ok": True,
    "evento_id": event_id,
    "lock_ids": [...],
    "lock_keys": [...],
    "motivo": "Evento criado com sucesso"
    # Falta: "confirmado_nesta_requisicao": True
}
```

**Comparar com**: Linha 769 (UPDATE path que funciona)

```python
# ✅ FUNCIONA
return {
    "ok": True,
    "evento_id": event_id,
    "status": "duplicado_pendente_agora" if confirmado_nesta_requisicao else "duplicado_confirmado",
    "confirmado_nesta_requisicao": confirmado_nesta_requisicao,  # ← PRESENTE
    ...
}
```

### Arquivo 2: `services/event_service_async.py`

**Problema**: Linha 302

Tenta extrair field que pode não existir:

```python
# ❌ Defaults to False quando field não existe
confirmado_agora = resultado_lock.get("confirmado_nesta_requisicao", False)
```

---

## MOTIVO PELA QUAL O MODELO OFICIAL NÃO APARECE

1. **Novo evento criado**: lock service não sinaliza isso
2. **salvar_evento recebe**:  `confirmado_nesta_requisicao = False` (default)
3. **event_handler interpreta**: "Evento já estava confirmado"
4. **Envia mensagem errada**: "Esse horário já está confirmado..."

---

## SOLUÇÃO MÍNIMA ARQUITETURAL

### Opção A (Recomendada): Fix no Lock Service

**Arquivo**: `services/agenda_lock_service.py`  
**Linha**: 789

Adicionar field ao novo evento criado:

```python
# ✅ CORREÇÃO
return {
    "ok": True,
    "evento_id": event_id,
    "lock_ids": [p.split("/")[-1] for p in locks_criados],
    "lock_keys": [p.split("/")[-1] for p in locks_criados],
    "motivo": "Evento criado com sucesso",
    "confirmado_nesta_requisicao": True  # ← ADICIONAR ESTA LINHA
}
```

**Impacto**: Minimal, 1 linha, responde contrato correto

### Opção B: Fix em salvar_evento

**Arquivo**: `services/event_service_async.py`  
**Linha**: 301-311

Detectar novo evento criado:

```python
status = resultado_lock.get("status")
is_new_create = status is None or status == "novo"
confirmado_agora = resultado_lock.get("confirmado_nesta_requisicao") or is_new_create
```

**Impacto**: +2 linhas, menos elegante

---

## TESTES DE REGRESSÃO NECESSÁRIOS

1. **T1: Novo evento criado** → confirmado_nesta_requisicao deve ser True
2. **T2: Evento pendente confirmado** → confirmado_nesta_requisicao deve ser True
3. **T3: Evento já confirmado (retry)** → confirmado_nesta_requisicao deve ser False
4. **T4: Evento com conflito** → retorna erro, não afetado
5. **T5: Mensagem WhatsApp recebida** → deve ser modelo oficial em T1/T2
6. **T6: Isolamento multi-tenant** → sem contaminação entre tenants
7. **T7: E2E com P0.24** → hora_fim calculado + mensagem oficial

---

## RECOMENDAÇÃO

**Implementar Opção A** (lock service retorna `confirmado_nesta_requisicao: True`):
- Mínimo impacto (1 linha)
- Responde contrato correto
- Alinha CREATE e UPDATE paths
- Sem mudanças em camadas superiores

---

**P0.25**: Auditoria concluída  
**Root Cause**: Identificada e documentada  
**Status**: Aguardando autorização para P0.26 (implementação)
