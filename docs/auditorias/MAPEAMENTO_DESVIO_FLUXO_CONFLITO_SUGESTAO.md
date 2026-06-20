# MAPEAMENTO — DESVIO DE FLUXO: lock_existente vs conflito_old

**Data:** 2026-06-19  
**Objetivo:** Mapear onde o novo fluxo lock_existente desvia do fluxo antigo de conflito  
**Problema:** Quando Bruna está ocupada, motor detecta `lock_existente`, mas não reutiliza lógica de sugestão

---

## 🔍 FLUXO ANTIGO (que funcionava com sugestões)

### Antes (FUNCIONAVA):
```
Usuario: "Quero corte com Bruna segunda 10h"
    ↓
verificar_conflito_e_sugestoes_profissional()  
    ↓
if conflito:
    return {
        "conflito": True,
        "sugestoes": ["10:30", "11:00", "11:30"],
        "profissional_alternativo": ["Carla", "Marina"]
    }
    ↓
Handler responde ao usuário:
    "Bruna não tem 10h disponível"
    "Tente: 10:30, 11:00, 11:30"
    "Ou com Carla/Marina"
    ↓
Usuário escolhe sugestão
    ↓
Evento criado
```

**Ponto-chave:** Função `verificar_conflito_e_sugestoes_profissional()` retorna sugestões automaticamente

---

## ❌ FLUXO NOVO (que não retorna sugestões)

### Agora (QUEBRADO):
```
Usuario: "Quero corte com Bruna segunda 10h"
    ↓
salvar_evento()
    ↓
crear_evento_com_lock()
    ↓
if lock_existente:
    return {
        "ok": False,
        "motivo": "Slot ocupado",
        "tipo_erro": "lock_existente"
    }
    ↓
Função retorna SEM SUGESTÕES
    ↓
Handler (event_handler.py) recebe "conflito_lock_existente"
    ↓
[PATCH_P0 NOVO] Chama verificar_conflito_e_sugestoes_profissional()
    ↓
[DEVERIA] Retornar sugestões e responder ao usuário
    ↓
[MAS] Status atual desconhecido (precisa testar)
```

**Ponto de desvio:** Entre `lock_existente` no motor e `verificar_conflito...` no handler

---

## 🗺️ MAPA DE CHAMADAS

### CAMINHO ANTIGO (conflito simples):

```
event_service_async.py:salvar_evento()
    ↓
(confirmado=True)
    ↓
verificar_conflito_e_sugestoes_profissional()  ← Retorna sugestões AQUI
    ↓
Retorna ao handler com sugestões já prontas
```

**Arquivo:** `services/event_service_async.py:125`

```python
if confirmado_flag:
    # Chamar verificar_conflito_e_sugestoes DIRETAMENTE
    resultado = await verificar_conflito_e_sugestoes_profissional(...)
    if resultado["conflito"]:
        # Retornar sugestões para handler
        return sugestoes  # ← Já tem sugestões!
```

---

### CAMINHO NOVO (lock_existente):

```
event_handler.py:add_evento_por_gpt()
    ↓
salvar_evento()
    ↓
crear_evento_com_lock()  ← Bloqueia com lock
    ↓
Retorna {"ok": False, "tipo_erro": "lock_existente"}
    ↓
event_handler.py recebe "conflito_lock_existente"
    ↓
[PATCH_P0 NOVO] Chama verificar_conflito... NOVAMENTE
    ↓
Gera sugestões no handler
```

**Arquivo:** `handlers/event_handler.py:978-1055`

---

## 🎯 ACHADO CRÍTICO: O DESVIO

### PONTO DE DESVIO 1: Ordem de validação

**Fluxo antigo:**
```
1. Verificar conflito (rápido)
2. Se conflito → retornar sugestões
3. Só depois bloquear com lock (atomicidade)
```

**Fluxo novo:**
```
1. Bloquear com lock PRIMEIRO (atomicidade)
2. Se lock_existe → retornar erro SEM sugestões
3. Handler chama verificar_conflito NOVAMENTE (ineficiente)
```

**Problema:** Dupla verificação + Motor não retorna sugestões

---

### PONTO DE DESVIO 2: Responsabilidade

**Fluxo antigo:**
- `salvar_evento()` retorna: `{"conflito": True, "sugestoes": [...]}`
- Handler usa sugestões direto

**Fluxo novo:**
- `salvar_evento()` retorna: `"conflito_lock_existente"` (string!)
- Handler deve chamar `verificar_conflito...` NOVAMENTE
- Funcionalidade duplicada

---

## ⚠️ QUESTÕES ABERTAS

1. **O handler realmente chama `verificar_conflito...` após `lock_existente`?**
   - Implementado em PATCH P0 novo
   - Precisa testar se funciona

2. **Performance: dupla verificação?**
   - Sim, `verificar_conflito_e_sugestoes_profissional` é chamado 2x:
     - Vez 1: Dentro de `salvar_evento()` (implícito)
     - Vez 2: No handler após erro

3. **Sugestões são corretas?**
   - Dependem de `verificar_conflito_e_sugestoes_profissional`
   - Que busca eventos reais do Firestore
   - Precisa validar com Firestore real

---

## 📋 O QUE A BATERIA P0 VAI PROVAR

### ETAPA 1-2: Motor bloqueia lock_existente
```
✅ lock_existente detectado
✅ Múltiplas tentativas bloqueadas
```

### ETAPA 3: Sugestões geradas
```
✅ verificar_conflito_e_sugestoes_profissional() retorna sugestões
✅ Números de sugestões > 0
```

### ETAPA 4-5: Usuário aceita
```
✅ Contexto salvo com aceite
✅ Draft preservado
```

### ETAPA 6: Evento criado com horário aceito
```
✅ Novo horário (10:30) criado com sucesso
✅ Sem conflito no novo horário
```

### ETAPA 7: Limpeza com DELETE_FIELD
```
✅ draft_agendamento removido
✅ dados_confirmacao removido
✅ estado_fluxo = "idle"
```

---

## 🔄 FLUXO IDEAL PÓS-PATCH

```
Usuario: "Quero corte com Bruna segunda 10h"
    ↓ [ETAPA 1-2]
Motor: lock_existente (Bruna ocupada)
    ↓ [ETAPA 3]
Handler: Chama verificar_conflito_e_sugestoes_profissional()
    ↓
Retorna: {
    "conflito": True,
    "sugestoes": ["10:30", "11:00", "11:30"],
    "profissional_alternativo": ["Carla", "Marina"]
}
    ↓ [RESPOSTA]
Bot: "Bruna não tem 10h.
      Tente: 10:30, 11:00, 11:30
      Ou com Carla, Marina"
    ↓ [ETAPA 4-5]
Usuario: "10:30"
    ↓
Contexto: estado=aguardando_escolha, draft={hora: 10:30}
    ↓ [ETAPA 6]
Usuario: "Sim"
    ↓
Motor: Cria evento às 10:30 (sem conflito)
    ↓ [ETAPA 7]
Limpeza: draft_agendamento deletado, estado=idle
```

---

## 📍 ARQUIVOS CRÍTICOS

| Arquivo | Função | Linha | O que faz |
|---------|--------|-------|-----------|
| `services/agenda_lock_service.py` | `criar_evento_com_lock()` | 323 | Retorna `lock_existente` |
| `services/event_service_async.py` | `verificar_conflito_e_sugestoes_profissional()` | 959 | Gera sugestões |
| `handlers/event_handler.py` | `add_evento_por_gpt()` | 978 | Recebe erro, chama sugestões? |
| `utils/contexto_temporario.py` | `limpar_contexto_agendamento_v2()` | 133 | Limpa com DELETE_FIELD |

---

## 🎯 BATERIA P0 REAL TESTA

- ✅ Lock realmente bloqueia
- ✅ Sugestões são geradas
- ✅ Aceite de sugestão funciona
- ✅ Novo horário criado sem erro
- ✅ Limpeza remove campos

**Resultado:** JSON com PASS/FAIL por etapa

---

**Como executar:**
```bash
python tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py
```

**Resultado:** `tests/resultado_bateria_p0_fluxo.json`

