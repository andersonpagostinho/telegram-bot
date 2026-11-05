# P0.26.2 — AUDITORIA DE FALHA EM PRODUÇÃO

**Data**: 2026-11-05  
**Status**: 🔴 **3 BUGS CRÍTICOS IDENTIFICADOS**

---

## RESUMO EXECUTIVO

Investigação de falha em produção onde cliente não conseguiu criar segundo agendamento no mesmo dia com mesmo profissional.

**Caso Real**:
- Cliente: whatsapp:5511991382080
- Profissional: Bruna
- Data: 2026-11-06
- Evento existente: 15:00
- Tentativa: Novo agendamento para 16:00 → **FALHOU**

**Causa Raiz**: Combinação de 3 bugs críticos:

1. **BUG #1 (CRÍTICO)**: Event ID não inclui horário → colisão de IDs
2. **BUG #2 (CRÍTICO)**: FUSO_BR não importado → NameError
3. **BUG #3 (CRÍTICO)**: Locks órfãos não liberados em erro → deadlock

---

## BUG #1: EVENT ID NÃO INCLUI HORÁRIO

### Localização
`services/event_service_async.py:265-266`

### Código
```python
base_id = f"{evento.get('cliente_id')}_{evento.get('profissional')}_{evento.get('data')}"
event_id = base_id.replace(" ", "_").lower()
```

### Problema
Event ID é gerado APENAS com: `cliente_id_profissional_data`

**Não inclui**: `hora_inicio`

### Impacto
Um cliente NÃO PODE ter 2 agendamentos no mesmo dia com o mesmo profissional!

```
Evento 1: 15:00 → ID: whatsapp:5511991382080_bruna_2026-11-06
Evento 2: 16:00 → ID: whatsapp:5511991382080_bruna_2026-11-06 (COLISÃO!)
```

### Caso Real
```
✓ Cliente Bruna às 15:00 em 06/11 → ID criado
✗ Cliente Bruna às 16:00 em 06/11 → MESMO ID, marcado como idempotência
```

### Classificação
**🔴 CRÍTICO**
- Bloqueia funcionalidade legítima
- Afeta agenda inteira do profissional
- Sem workaround

---

## BUG #2: FUSO_BR NÃO IMPORTADO

### Localização
`services/agenda_lock_service.py:447, 629, 739`

### Problema
Três linhas usam `datetime.now(FUSO_BR).isoformat()`:

**Linha 447** - Função `_atualizar_evento_com_locks_idempotente()`:
```python
now_iso = datetime.now(FUSO_BR).isoformat()
```

**Linha 629** - Fallback idempotência quando evento pendente:
```python
evento_existente["confirmado_em"] = datetime.now(FUSO_BR).isoformat()
```

**Linha 739** - Função de atualização com locks:
```python
evento_existente["confirmado_em"] = datetime.now(FUSO_BR).isoformat()
```

### Imports Atuais
```python
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from services.firebase_service_async import (...)
from services.firestore_client import get_db
from firebase_admin import firestore
```

### Falta
```python
from pytz import timezone
FUSO_BR = timezone("America/Sao_Paulo")
```

### Erro
```
NameError: name 'FUSO_BR' is not defined
Traceback:
  File "services/agenda_lock_service.py", line 447
    now_iso = datetime.now(FUSO_BR).isoformat()
                           ^^^^^^^
```

### Padrão do Projeto
Outros arquivos definem corretamente:
- `handlers/encaixe_handler.py`: `FUSO_BR = timezone("America/Sao_Paulo")`
- `router/principal_router.py`: `FUSO_BR = pytz.timezone("America/Sao_Paulo")`
- `scheduler/notificacoes_scheduler.py`: `FUSO_BR = timezone("America/Sao_Paulo")`

### Classificação
**🔴 CRÍTICO**
- Lançamento de exceção
- Falha silenciosa em fallback idempotência
- Bloqueia atualização de evento

---

## BUG #3: LOCKS ÓRFÃOS NÃO LIBERADOS

### Localização
`services/agenda_lock_service.py:605-816`

### Problema

**Sequência de Locks**:
1. Linha 605: `adquirir_locks_atomicamente()` cria locks para 16:00-16:40
2. Locks criados: 4 buckets adicionados a `locks_criados = []`
3. Linha 629: Tenta usar `FUSO_BR` → NameError
4. Linha 808: Exceção é capturada
5. **Linha 810-816**: Retorna erro
6. **❌ Locks NÃO são liberados!**

### Código Problemático
```python
except Exception as e:
    logger.error(f"Erro geral em criar_evento_com_lock: {e}")
    return {
        "ok": False,
        "lock_ids": [p.split("/")[-1] for p in locks_criados],
        # ❌ Apenas retorna IDs, não libera os locks!
        "motivo": f"Erro inesperado: {str(e)}",
        "tipo_erro": "erro"
    }
```

### Falta
```python
# DEVERIA ter:
if locks_criados:
    await liberar_locks(dono_id, locks_criados)
```

### Impacto

**Estado no Firestore após erro**:
```
Clientes/tenant_7394370553/AgendaLocks/bruna_20261106_160000
{
    "status": "reservado",  # ← RESERVADO, não liberado!
    "profissional": "bruna",
    "bucket": "160000",
    "timestamp_lock": "2026-11-05T...",
    "expira_em": "2026-11-06T..." (24h depois)
}

Clientes/tenant_7394370553/AgendaLocks/bruna_20261106_161000
{
    "status": "reservado",  # ← Idem
}

... etc (4 locks órfãos)
```

### Ciclo Completo de Falha

```
1. Cliente tenta 16:00
   ↓
2. Tenta criar locks 16:00-16:40
   ↓ [SUCESSO]
3. 4 locks criados com status="reservado"
   ↓
4. Encontra evento existente (15:00, mesmo ID)
   ↓
5. Tenta atualizar para 16:00
   ↓
6. datetime.now(FUSO_BR) → NameError ❌
   ↓
7. Except captura erro
   ↓
8. Retorna {"ok": False, "motivo": "Erro inesperado..."}
   ↓ [❌ LOCKS NÃO LIBERADOS]
9. Cliente recebe erro
   ↓
10. 16:00 agora está bloqueado (locks órfãos)
    ↓
11. Cliente não pode agendar 16:00 até locks expirem (24h)
    ↓
12. Servidor PODE ter tarefa de cleanup de locks expirados
    ↓
13. Locks permanecem reservados por 24h → deadlock
```

### Classificação
**🔴 CRÍTICO**
- Causa deadlock
- Bloqueia horários por 24h
- Sem recovery automático se cleanup não rodar

---

## IMPACTO SOBRE P0.19, P0.24, P0.26

### P0.19 (Extração de Horário)
- ✅ Não afetado diretamente
- ⚠️ Pode tentar criar segundo agendamento no mesmo dia → colide com BUG #1

### P0.24 (Cálculo hora_fim)
- ✅ Funciona quando não há exceção
- ⚠️ Se bug #2 lança NameError, hora_fim não ajuda

### P0.26 (Confirmação Oficial)
- ✅ Implementação correta
- ⚠️ Nunca alcança ponto de retornar confirmado_nesta_requisicao=True
- ⚠️ Cliente recebe erro antes

---

## TESTES RECOMENDADOS (NÃO EXECUTADOS - READ-ONLY)

Para validar os bugs:

### Teste 1: Event ID Collision
```python
# Criar 2 eventos mesmo cliente, profissional, data, horários diferentes
evento1 = {"cliente_id": "A", "profissional": "B", "data": "2026-11-06", "hora_inicio": "15:00"}
evento2 = {"cliente_id": "A", "profissional": "B", "data": "2026-11-06", "hora_inicio": "16:00"}

# Ambos geram ID: "a_b_2026-11-06"
# Esperado: IDs diferentes (incluir horário)
# Atual: IDs iguais → colisão
```

### Teste 2: FUSO_BR Missing
```python
# Chamar _atualizar_evento_com_locks_idempotente() com evento já confirmado
# Esperado: Update bem-sucedido
# Atual: NameError - FUSO_BR não definido
```

### Teste 3: Orphan Locks
```python
# Chamar criar_evento_com_lock() com evento que causa NameError
# Esperado: Locks criados são liberados, Firestore limpo
# Atual: Locks permanecem "reservado" por 24h
```

---

## CORREÇÃO MÍNIMA RECOMENDADA

### Correção 1: Incluir horário no Event ID
**Arquivo**: `services/event_service_async.py:265-266`

**Antes**:
```python
base_id = f"{evento.get('cliente_id')}_{evento.get('profissional')}_{evento.get('data')}"
```

**Depois**:
```python
# Incluir hora_inicio para permitir múltiplos eventos por profissional no mesmo dia
hora_inicio = evento.get('hora_inicio', '00:00').replace(':', '')
base_id = f"{evento.get('cliente_id')}_{evento.get('profissional')}_{evento.get('data')}_{hora_inicio}"
```

### Correção 2: Importar FUSO_BR
**Arquivo**: `services/agenda_lock_service.py:15-28`

**Adicionar**:
```python
from pytz import timezone
FUSO_BR = timezone("America/Sao_Paulo")
```

### Correção 3: Liberar locks em erro
**Arquivo**: `services/agenda_lock_service.py:808-816`

**Antes**:
```python
except Exception as e:
    logger.error(f"Erro geral em criar_evento_com_lock: {e}")
    return {
        "ok": False,
        "lock_ids": [p.split("/")[-1] for p in locks_criados],
        "motivo": f"Erro inesperado: {str(e)}",
        "tipo_erro": "erro"
    }
```

**Depois**:
```python
except Exception as e:
    logger.error(f"Erro geral em criar_evento_com_lock: {e}")
    # 🔥 LIBERAR locks órfãos em caso de erro
    if locks_criados:
        try:
            locks_liberados = 0
            for lock_path in locks_criados:
                await deletar_dado_em_path(lock_path)
                locks_liberados += 1
            logger.info(f"[CLEANUP_ERRO] {locks_liberados} locks liberados após erro")
        except Exception as cleanup_error:
            logger.error(f"[CLEANUP_ERRO] Falha ao limpar locks: {cleanup_error}")
    
    return {
        "ok": False,
        "lock_ids": [p.split("/")[-1] for p in locks_criados],
        "motivo": f"Erro inesperado: {str(e)}",
        "tipo_erro": "erro"
    }
```

---

## CONCLUSÃO

### Bloqueadores Críticos
- 🔴 **BUG #1**: Impede múltiplos agendamentos legítimos
- 🔴 **BUG #2**: Causa NameError que bloqueia atualizações
- 🔴 **BUG #3**: Cria deadlock de 24h por locks órfãos

### Severidade
Todos os 3 bugs são **CRÍTICOS** e devem ser corrigidos antes de P0.26 ser considerado pronto para produção.

### Impacto Potencial
- Usuários não conseguem agendar múltiplos compromissos no mesmo dia
- Erros aleatórios durante idempotência
- Deadlock de timeslots por até 24h

---

**Auditoria**: Investigação READ-ONLY completada  
**Status**: 🔴 3 BUGS CRÍTICOS IDENTIFICADOS  
**Recomendação**: **NÃO DEPLOY** até correções aplicadas
