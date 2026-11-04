# ANÁLISE: Por que a resposta é "Esse horário já está confirmado"

## Fluxo Esperado
```
✨ Corte feminino com Bruna
📆 em 04/11 às 14h

✅ Horário confirmado!
```

**Origem**: `utils/mensagens_agendamento.py:42-52` → `montar_mensagem_confirmacao_sucesso()`

## Fluxo Atual (BUG)
```
Esse horário já está confirmado.

Se precisar alterar ou cancelar, é só me avisar.
```

**Origem**: `handlers/event_handler.py:1323`

---

## CAUSA RAIZ

### 1️⃣ **Event ID é idempotente** (por design)
Arquivo: `services/event_service_async.py:245-247`

```python
if not event_id:
    base_id = f"{evento.get('cliente_id')}_{evento.get('profissional')}_{evento.get('data')}"
    event_id = base_id.replace(" ", "_").lower()
```

**Resultado**: `event_id = "cliente_id_bruna_2026-11-04"` (sempre igual se mesmos parâmetros)

---

### 2️⃣ **Detecção de duplicado inadvertida**
Arquivo: `services/agenda_lock_service.py:481-492` (primeira ocorrência)

```python
evento_path = f"Clientes/{dono_id}/Eventos/{event_id}"
evento_existente = await buscar_dado_em_path(evento_path)
if evento_existente:
    return {
        "ok": True,
        "evento_id": event_id,
        "duplicado": True,  # ⚠️ PROBLEMA: retorna True sem distinguir pendente vs confirmado
        ...
    }
```

E novamente em `agenda_lock_service.py:570-589` (segunda ocorrência)

---

### 3️⃣ **Propagação do erro**
Arquivo: `services/event_service_async.py:281-283`

```python
if resultado_lock.get("duplicado"):
    print("♻️ Evento já existe (idempotente). Não criando duplicado.")
    return "duplicado"  # Retorna string "duplicado"
```

---

### 4️⃣ **Mensagem genérica é mostrada**
Arquivo: `handlers/event_handler.py:1322-1332`

```python
if resultado_salvamento == "duplicado":
    msg_duplicado = "Esse horário já está confirmado.\n\nSe precisar alterar ou cancelar, é só me avisar."
    # ... envia mensagem genérica
    return True
```

❌ **Nunca usa** `montar_mensagem_confirmacao_sucesso()`

---

## O PROBLEMA CONCEITUAL

O código **NÃO SABE** diferenciar entre:

| Cenário | O que está em Firebase | O que deveria acontecer |
|---------|-------|---------|
| **A) Confirmando pendente** | Evento em `Eventos/{event_id}` com `confirmado=False` ou ausente | ✅ Mostrar mensagem de sucesso formatada |
| **B) Reconfirmando confirmado** | Evento em `Eventos/{event_id}` com `confirmado=True` | ⚠️ Mostrar "já confirmado" (idempotente) |

**O código atual trata ambos como "duplicado"**, independentemente do estado anterior.

---

## ARQUIVOS E LINHAS CRÍTICAS

| Arquivo | Linha | Função | Problema |
|---------|-------|--------|----------|
| `services/agenda_lock_service.py` | 481-492 | `criar_evento_com_lock()` | Retorna `duplicado=True` sem verificar se evento está pendente |
| `services/agenda_lock_service.py` | 570-589 | `criar_evento_com_lock()` | Idem acima (segunda vez) |
| `services/event_service_async.py` | 281-283 | `salvar_evento()` | Transforma `duplicado=True` em string `"duplicado"` |
| `handlers/event_handler.py` | 1322-1332 | `add_evento_por_gpt()` | Mostra mensagem genérica em vez de sucesso |
| `utils/mensagens_agendamento.py` | 42-52 | `montar_mensagem_confirmacao_sucesso()` | **NUNCA É CHAMADA** quando confirmamos |

---

## FLUXO ATUAL (ERRADO)

```
1. Usuário diz "Sim, confirma"
2. add_evento_por_gpt() chama salvar_evento()
3. salvar_evento() chama criar_evento_com_lock()
4. criar_evento_com_lock() detecta evento existente
   → retorna {"ok": True, "duplicado": True}
5. salvar_evento() vê "duplicado" → retorna "duplicado" (string)
6. add_evento_por_gpt() vê resultado_salvamento == "duplicado"
   → mostra "Esse horário já está confirmado"
7. ❌ RESULTADO: Mensagem genérica em vez de sucesso formatado
```

---

## FLUXO ESPERADO (CORRETO)

```
1. Usuário diz "Sim, confirma"
2. add_evento_por_gpt() chama salvar_evento()
3. salvar_evento() chama criar_evento_com_lock()
4. criar_evento_com_lock() detecta evento existente
   → VERIFICA se confirmado=False (pendente) ou confirmado=True
   → Se pendente: marca como confirmado, retorna sucesso normal
   → Se confirmado: retorna duplicado (idempotente)
5. Se sucesso normal:
   → salvar_evento() retorna True
   → add_evento_por_gpt() chama montar_mensagem_confirmacao_sucesso()
   → Mostra: ✨ Corte feminino com Bruna / 📆 em 04/11 às 14h / ✅ Horário confirmado!
6. ✅ RESULTADO: Mensagem formatada, não genérica
```

---

## ONDE O EVENTO VEM DE?

O evento que já existe em Firebase provavelmente foi salvo em uma destas situações:

1. **Aguardando confirmação** (`handlers/event_handler.py:710-728`)
   - Usuário não confirmou ainda
   - Contexto tem `aguardando_confirmacao_agendamento=True`
   - Evento parcialmente salvo com `confirmado=False` ou não foi salvo, só guardado em contexto

2. **Retomada após reinício**
   - Contexto anterior pode ter criado evento incompleto
   - Agora tentamos confirmar

---

## SOLUÇÃO (SEM IMPLEMENTAR AINDA)

Deve verificar o estado `confirmado` do evento antes de retornar `duplicado`:

**Em `agenda_lock_service.py:570-589`**:
```python
evento_existente = await buscar_dado_em_path(evento_path)
if evento_existente:
    # NOVO CÓDIGO: Verificar se está pendente
    se evento_existente.get("confirmado") is False:
        # É confirmação legítima de pendente
        # Proceder normalmente sem retornar "duplicado"
        # (deixar salvar_dado_em_path() fazer update)
    else:
        # Evento já estava confirmado = retentar idempotente
        return {"ok": True, "duplicado": True, ...}
```

---

## IMPACTO

- **Severidade**: 🟠 ALTA — Resposta incorreta em fluxo principal de confirmação
- **Frequência**: 🟠 ALTA — Afeta todo agendamento que passa por confirmação pendente
- **Usuário vê**: Mensagem genérica genérica em vez de confirmação visual formatada
- **Esperado**: Mensagem com emojis e formatação clara
- **Status**: ❌ SEM CORRIGIR AINDA — Apenas análise completada
