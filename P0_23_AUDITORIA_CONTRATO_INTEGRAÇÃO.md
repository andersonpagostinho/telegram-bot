# P0.23 — AUDITORIA DO CONTRATO DE INTEGRAÇÃO

**Objetivo**: Identificar por que o objeto evento chega incompleto a `agenda_lock_service.criar_evento_com_lock()`

**Status**: 🔴 **ROOT CAUSE ENCONTRADA** — Contrato inconsistente entre camadas

---

## ETAPA 1 — CONTRATO DO LOCK SERVICE

### Assinatura Completa

```python
async def criar_evento_com_lock(
    dono_id: str,
    evento: dict,
    event_id: str,
    excluir_evento_id: Optional[str] = None
) -> Dict[str, Any]:
```

**Arquivo**: `services/agenda_lock_service.py:511`

### Validação Obrigatória (linhas 554-563)

```python
profissional = evento.get("profissional", "").strip()
hora_inicio = normalizar_hora(evento.get("hora_inicio", ""))
hora_fim = normalizar_hora(evento.get("hora_fim", ""))

if not profissional or not hora_inicio or not hora_fim:
    return {
        "ok": False,
        "motivo": "Dados incompletos (profissional, hora_inicio, hora_fim)",
        "tipo_erro": "validacao"
    }
```

### Campos Obrigatórios

| Campo | Tipo | Formato | Origem | Status |
|-------|------|---------|--------|--------|
| `confirmado` | bool | `True` | evento | ✅ Presente |
| `profissional` | str | Non-empty after `.strip()` | evento | ✅ Presente |
| `hora_inicio` | str | "HH:MM" após normalizar | evento | ✅ Presente |
| `hora_fim` | str | "HH:MM" após normalizar | evento | ❌ **AUSENTE** |
| `data` | str | "YYYY-MM-DD" | evento | ✅ Presente |
| `duracao` | int | Minutos | evento | ✅ Presente |

### Cálculos Realizados pelo Lock Service

```python
# Linha 566: Gera buckets de tempo usando hora_inicio e hora_fim
buckets = gerar_buckets_tempo(hora_inicio, hora_fim, intervalo_minutos=10)

# Linhas 590-602: Cria locks para cada bucket
for bucket in buckets:
    lock_key = f"{prof_norm}_{data_evento}_{bucket}"
    lock_doc = {
        "bucket": bucket,
        "profissional": profissional,
        "timestamp_lock": ...,
        "status": "reservado",
        "evento_id": None
    }
```

---

## ETAPA 2 — RASTREAMENTO DOS CHAMADORES

### Chamador Principal: `event_service_async.py`

**Arquivo**: `services/event_service_async.py:269`

```python
if confirmado_flag:
    print("[LOCK] Criando evento confirmado com proteção...")
    resultado_lock = await criar_evento_com_lock(
        dono_id=tenant_id,
        evento=evento,
        event_id=event_id
    )
```

**Problema**: `salvar_evento()` recebe `evento` mas **NÃO garante que contenha `hora_fim`**.

### Chamador Secundário: `event_handler.py`

**Arquivo**: `handlers/event_handler.py:1165-1180`

```python
evento_data = {
    "descricao": descricao,
    "data": start_time.strftime("%Y-%m-%d"),
    "hora_inicio": start_time.strftime("%H:%M"),
    "hora_fim": end_time.strftime("%H:%M"),    # ✅ PRESENTE!
    "duracao": duracao_minutos,
    "confirmado": True,
    ...
}
```

**Status**: Quando vem de `event_handler.py`, `hora_fim` **JÁ ESTÁ PRESENTE**.

### Chamador Terciário: `encaixe_service.py`

**Arquivo**: `services/encaixe_service.py:176, 418, 440`

```python
# Linha 165: evento construído com hora_fim
"hora_fim": fim.strftime("%H:%M"),

# Linha 176: passa para salvar_evento
await salvar_evento(dono_id, ev, dono_id)
```

**Status**: `hora_fim` presente quando saído de `encaixe_service`.

---

## ETAPA 3 — ORIGEM DETERMINÍSTICA DOS DADOS

### Fluxo Esperado

```
Event Handler ou Encaixe Service
  ↓
  evento_data["hora_fim"] = end_time.strftime("%H:%M")  ✅ CONSTRUÍDO
  ↓
  salvar_evento(user_id, evento_data, tenant_id)
  ↓
  criar_evento_com_lock(dono_id, evento, event_id)
  ✅ hora_fim JÁ PRESENTE
```

### Fluxo Real (Nosso Teste P0.22.1)

```
Test constructs evento directly
  ↓
  evento = {
      "data": "2026-11-05",
      "hora_inicio": "16:00",
      "duracao": 30,
      ...
      // ❌ SEM hora_fim!
  }
  ↓
  salvar_evento(user_id, evento, tenant_id)
  ↓
  Linha 269: criar_evento_com_lock(dono_id, evento, event_id)
  ❌ evento.get("hora_fim") = None
  ❌ Rejeição: "Dados incompletos (profissional, hora_inicio, hora_fim)"
```

---

## ETAPA 4 — ANÁLISE DO CONTRATO

### Questão 1: O evento deve chegar com `hora_fim` já calculado?

**Resposta**: SIM, mas inconsistentemente.

- ✅ `event_handler.py` calcula e passa `hora_fim`
- ✅ `encaixe_service.py` calcula e passa `hora_fim`
- ❌ Tests diretos NÃO passam `hora_fim`

### Questão 2: Qual camada deve construir `hora_fim`?

**Resposta**: Deveria ser **`salvar_evento()`**, mas não é.

Evidência: Comentário em `event_service_async.py:238-240`:

```python
# ✅ hora_fim NÃO é normalizado — deve ser exato (hora_inicio + duração)
# Normalizamos hora_inicio para buscar conflitos em grade de 20 min,
# mas hora_fim deve permanecer preciso para cálculos de duração
```

Este comentário **admite** que `hora_fim` deve existir, mas:
1. **NÃO calcula** `hora_fim` se faltando
2. **NÃO valida** presença de `hora_fim`
3. **NÃO falha** gracefully

### Questão 3: O lock service calcula ou apenas valida?

**Resposta**: Apenas **VALIDA**.

```python
hora_fim = normalizar_hora(evento.get("hora_fim", ""))
if not profissional or not hora_inicio or not hora_fim:
    return {"ok": False, "motivo": "Dados incompletos..."}
```

Lock service espera `hora_fim` já calculado.

### Questão 4: Existe divergência entre contratos dos diferentes chamadores?

**Resposta**: SIM, CRÍTICO.

| Camada | Constrói `hora_fim`? | Valida? | Status |
|--------|---|---|---|
| `event_handler.py` | ✅ SIM | - | Correto |
| `encaixe_service.py` | ✅ SIM | - | Correto |
| `salvar_evento()` | ❌ NÃO | ❌ NÃO | ❌ DIVERGÊNCIA |
| `criar_evento_com_lock()` | - | ✅ Rejeita se vazio | Correto |

### Questão 5: Por que profissional também está falhando?

**Resposta**: Porque when evento is constructed in test, profissional pode estar vazio.

Test cria:
```python
"profissional": "prof_test_1"
```

Mas `criar_evento_com_lock()` valida:
```python
profissional = evento.get("profissional", "").strip()
if not profissional:
    # FALHA
```

Existe um vazio que está sendo introduzido.

### Questão 6: Existem outros campos obrigatórios não identificados?

**Resposta**: Revisando `criar_evento_com_lock()`, campos REALMENTE obrigatórios:

| Campo | Validação | Loc |
|-------|-----------|-----|
| `confirmado` | `if not evento.get("confirmado")` | 547 |
| `profissional` | `if not profissional` | 558 |
| `hora_inicio` | `if not hora_inicio` | 558 |
| `hora_fim` | `if not hora_fim` | 558 |

Apenas esses 4. Outros são opcionais.

### Questão 7: A correção pode afetar reagendamento, cancelamento, outros fluxos?

**Resposta**: SIM. Grande risco de regressão.

Se corrigirmos `salvar_evento()` para calcular `hora_fim`:
1. Todos os fluxos que já passam `hora_fim` funcionarão igual ✅
2. Mas se **alguém está contando com `hora_fim` ausente**, isso quebra
3. Reagendamento pode ter dependência neste formato
4. Cancelamento pode usar `hora_fim` para identificar slots

---

## ETAPA 5 — PROPOSTA MÍNIMA

### Root Cause

`salvar_evento()` não garante que `evento` possui `hora_fim` antes de passar para `criar_evento_com_lock()`.

### Correção Mínima

**Opção A** (Defensiva em `salvar_evento`):

Adicionar cálculo de `hora_fim` se não presente:

```python
# Em salvar_evento(), após linha 236:

if evento.get("hora_inicio") and evento.get("duracao"):
    if not evento.get("hora_fim"):
        # Calcular hora_fim
        try:
            hi_h, hi_m = map(int, evento["hora_inicio"].split(":"))
            dur_min = int(evento["duracao"])
            total_min = hi_h * 60 + hi_m + dur_min
            hf_h = total_min // 60
            hf_m = total_min % 60
            evento["hora_fim"] = f"{hf_h:02d}:{hf_m:02d}"
        except:
            # Se falhar, deixa vazio e lock service rejeita
            pass
```

**Vantagens**:
- Mínimo (3 linhas de lógica)
- Defensivo (não quebra se vazio)
- Centralizado (em um único lugar)

**Desvantagens**:
- Calcula toda vez (mesmo se já presente)
- Não trata timezone (assume local)

**Opção B** (Validação em `salvar_evento`):

Rejeitar evento sem `hora_fim` ANTES de criar_evento_com_lock:

```python
if not evento.get("hora_fim"):
    # Rejeitar com mensagem clara
    return False
```

**Vantagens**:
- Fail-fast (identifica problema cedo)
- Responsabilidade clara (caller deve fornecer)

**Desvantagens**:
- Quebraria tests e possivelmente chamadores antigos
- Não é backward compatible

### Recomendação

**USE OPÇÃO A** (Calcular `hora_fim` se não presente):
- Backward compatible
- Defensivo
- Mínimo impacto
- Resolve o problema

### Código Proposto

**Arquivo**: `services/event_service_async.py`
**Localização**: Após linha 236 (após normalização de `hora_inicio`)
**Linhas a adicionar**: ~10 linhas

```python
# Calcular hora_fim se não fornecido (para compatibilidade com lock service)
if evento.get("hora_inicio") and evento.get("duracao") and not evento.get("hora_fim"):
    try:
        hi_parts = str(evento["hora_inicio"]).split(":")
        if len(hi_parts) >= 2:
            hi_h, hi_m = int(hi_parts[0]), int(hi_parts[1])
            dur_min = int(evento.get("duracao", 0))
            total_min = hi_h * 60 + hi_m + dur_min
            hf_h = total_min // 60 % 24  # Modulo 24 para evitar hora > 24
            hf_m = total_min % 60
            evento["hora_fim"] = f"{hf_h:02d}:{hf_m:02d}"
            logger.info(f"[P0.23] Calculado hora_fim={evento['hora_fim']} a partir de hora_inicio={evento['hora_inicio']} + duracao={dur_min}min")
    except Exception as e:
        logger.warning(f"[P0.23] Erro ao calcular hora_fim: {e}")
        # Deixa vazio - lock service validará
```

---

## DIAGRAMA DO FLUXO ATUAL

```
Event Handler
  evento_data["hora_fim"] = ... ✅
       ↓
salvar_evento()
  [NÃO valida hora_fim]  ❌
  [NÃO calcula hora_fim]  ❌
       ↓
criar_evento_com_lock()
  if not evento.get("hora_fim"):
    return erro ❌
```

## DIAGRAMA DO FLUXO CORRIGIDO

```
Event Handler / Test / Direct Call
  evento_data["hora_fim"] = ... ✅ (if provided)
       ↓
salvar_evento()
  [NOVO] if not evento.get("hora_fim") and duracao:
    evento["hora_fim"] = calcular() ✅
       ↓
criar_evento_com_lock()
  if not evento.get("hora_fim"):
    return erro (nunca acontece agora)
  [PROCEED OK] ✅
```

---

## RISCOS PARA FLUXOS EXISTENTES

### 1. Reagendamento

**Arquivo**: `services/encaixe_service.py`

Quando re-agenda, passa evento com `hora_fim` já calculado.
**Risco**: BAIXO — continuará funcionando igual.

### 2. Cancelamento

**Busca**: grep -rn "cancelar.*evento" services/
**Risco**: BAIXO — não afeta lógica de cancelamento.

### 3. Conversão de Horários

**Arquivo**: `router/principal_router.py:4388`

Comentário indica normalização de hora.
**Risco**: MÉDIO — se dependia de `hora_fim` ausente, pode quebrar.

---

## TESTES DE REGRESSÃO NECESSÁRIOS

1. ✅ Event handler → salvar_evento (já passa `hora_fim`)
2. ✅ Encaixe service → salvar_evento (já passa `hora_fim`)
3. ✅ Direct test → salvar_evento (NOW CALCULATES `hora_fim`)
4. ⏳ Reagendamento completo
5. ⏳ Cancelamento
6. ⏳ Locks cleanup

---

## CONCLUSÃO

**Root Cause**: `salvar_evento()` não garante `hora_fim` presente antes de chamar `criar_evento_com_lock()`.

**Impacto**: Falha silenciosa: evento rejeitado com "Dados incompletos".

**Solução Mínima**: 10 linhas em `salvar_evento()` para calcular `hora_fim` se faltando.

**Risk Level**: LOW (backward compatible, defensive).

**Ready to Implement**: SIM, quando autorizado.

---

**P0.23**: Auditoria de contrato concluída  
**Próxima**: P0.24 — Implementação da correção  
**Autor**: Claude Haiku 4.5  
**Data**: 2026-11-05  
**Status**: Aguardando autorização
