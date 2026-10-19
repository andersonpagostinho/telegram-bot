# ETAPA2 — PLANO DE IMPLEMENTAÇÃO P0.6.2.6

**Data:** 2026-10-19  
**Autorização:** Implementar validações de agendamento conforme P0.6.2.6  
**Status:** Criado a partir da autorização

---

## 📋 Validadores Existentes

1. **`validar_horario_funcionamento()`** — `services/agenda_service.py:537`
   - Assinatura: `async def validar_horario_funcionamento(user_id, data_iso, hora_inicio, duracao_min, profissional=None, dono_id=None) -> dict`
   - Retorna: `{"permitido": bool, "motivo": str | None, "regra": dict}`
   - Valida se horário cabe na janela real da data (salão + profissional)

2. **`verificar_conflito_e_sugestoes_profissional()`** — `services/event_service_async.py:1230`
   - Assinatura: `async def verificar_conflito_e_sugestoes_profissional(user_id, data, hora_inicio, duracao_min, profissional, servico, event_id=None, tenant_id=None) -> dict`
   - Verifica conflito com eventos existentes

3. **`buscar_profissionais_por_servico()`** — `services/profissional_service.py:12`
   - Retorna profissionais que oferecem serviços listados

---

## 🚀 Implementação

**Arquivo:** `handlers/event_handler.py:add_evento_por_gpt()`

**Ponto de inserção:** Logo antes de `salvar_evento()` (linha ~1214)

**Validações necessárias:**

1. Profissional inexistente → Retornar erro, não criar
2. Profissional incompatível com serviço → Retornar erro, não criar
3. Duração zero ou negativa → Retornar erro, não criar
4. Serviço inexistente → Retornar erro, não criar
5. Horário fora do expediente → Retornar erro (já em execução, linha ~820)
6. Conflito de horário → Preservar sugestão existente
7. Agendamento válido → Criar evento
8. Reenvio → Não duplicar

---

## 🧪 9 Cenários de Teste

**Arquivo:** `tests/test_p0626_validacoes_prealva.py`

1. **Profissional inexistente**
   - Input: profissional="FakeProfissional", servico="escova"
   - Esperado: Nenhum evento criado, mensagem de erro

2. **Profissional incompatível com serviço**
   - Input: profissional="Bruna" (não faz manicure), servico="manicure"
   - Esperado: Nenhum evento criado, mensagem de erro

3. **Duração zero**
   - Input: duracao_minutos=0
   - Esperado: Nenhum evento criado, mensagem de erro

4. **Duração negativa**
   - Input: duracao_minutos=-30
   - Esperado: Nenhum evento criado, mensagem de erro

5. **Serviço inexistente**
   - Input: servico="frenologia"
   - Esperado: Nenhum evento criado, mensagem de erro

6. **Horário fora do expediente**
   - Input: hora_inicio="23:00" (fora do expediente), data=amanhã
   - Esperado: Nenhum evento criado, sugestões oferecidas

7. **Conflito de horário**
   - Input: mesmo horário de evento existente
   - Esperado: Nenhum evento criado, sugestões alternativas

8. **Agendamento válido**
   - Input: profissional válido, serviço compatível, horário livre, duração válida
   - Esperado: Evento criado em Firestore

9. **Reenvio da mesma confirmação**
   - Input: Mesmo agendamento enviado 2x
   - Esperado: Sem duplicação (idempotência)

---

## ✅ Regras de Segurança

- Validação reprovada → Impede criação
- Falha/exceção → Interrompe fluxo
- Validação aprovada → Prossegue (sem duplicar mensagens)
- Preservar tenant, actor, sessão, confirmação explícita

---

## 🔒 Locks e Concorrência

Verificar se:
- `salvar_evento()` usa lock (linha ~1214)
- Lock cobre validação + persistência atomicamente
- Documentar lacunas se encontradas
