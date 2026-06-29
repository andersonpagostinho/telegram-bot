---
name: f3g_datas_horarios_timezone_concluido
description: F3G (Datas/Horários/Timezone) implementado e validado 5/5 PASS
metadata: 
  node_type: memory
  type: project
  originSessionId: 1f9a5ad4-1258-449b-a4aa-f9c0269d13d6
---

## F3G Datas, Horários e Timezone — Implementação Concluída

**Data:** 2026-06-28  
**Status:** ✅ 5/5 PASS  

### 5 Cenários Implementados

1. **G1: Data impossível** — 30/02, 29/02 (não-bissexto), 31/04, 31/11 rejeitadas
2. **G2: Horário inválido** — 25:00, -1:00, 99:99, 14:61, 14:-5 rejeitados
3. **G3: Evento no passado** — 1h atrás, ontem, semana passada rejeitados
4. **G4: Timezone UTC/São Paulo** — 16:30 local persiste como 16:30 (não vira 13:00)
5. **G5: Virada de meia-noite** — "Amanhã" a 23:55 = próximo dia (não duplo ou skipped)

### Funções de Validação

- `validar_data(ano, mes, dia)` — date() constructor, rejeita impossíveis
- `validar_hora(hora, minuto)` — intervalo [0,24) × [0,60)
- `validar_hora_string(hora_str)` — parse HH:MM + validação
- `data_no_passado_local(ano, mes, dia, hora, minuto, tz_str)` — pytz timezone-aware

### Timezone

**Constante:** TIMEZONE_BRASIL = "America/Sao_Paulo"
- Verão (set-fev): UTC-3
- Inverno (mar-set): UTC-2
- Persistência: ISO 8601 com offset (-03:00 ou -02:00)
- Nunca confundir UTC com local na tela do usuário

### Validação Completa

- **F3G isolado:** 5/5 PASS
- **F3 agregado:** 34/34 PASS (29 bloqueantes + 5 G3)
- **P0 regressão:** 4/4 PASS
- **Sem alterações de código de produção**

### Documentação

- `tests/f3_robustez/test_f3g_datas_horarios_timezone_real.py` — implementação (~500 linhas)
- `docs/auditorias/F3G_IMPLEMENTACAO_CONCLUIDA.md` — relatório completo

### Why

F3G garante que NeoEve nunca:
- Cria evento com data impossível
- Aceita horário inválido
- Agenda no passado
- Confunde 16:30 com 13:00 por erro UTC
- Interpreta "amanhã" errado próximo a 00:00

Essencial para agendar com confiança em produção.

Próxima: F3F (Falhas Externas) ⏳
