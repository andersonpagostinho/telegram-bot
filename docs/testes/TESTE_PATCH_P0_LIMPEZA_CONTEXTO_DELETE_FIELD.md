# TESTE OBRIGATÓRIO — PATCH P0 Limpeza Centralizada com DELETE_FIELD

**Data:** 2026-06-19  
**Status:** 🟢 PATCH APLICADO — TESTES OBRIGATÓRIOS  
**Objetivo:** Validar que DELETE_FIELD remove TODOS os campos transitórios

---

## 📋 RESUMO DO PATCH

**Arquivos alterados:**
- ✅ `utils/contexto_temporario.py` — 2 funções corrigidas
- ✅ `services/gpt_service.py` — 2 chamadas corrigidas com tenant_id
- ✅ `handlers/bot.py` — já tinha tenant_id
- ✅ `handlers/acao_router_handler.py` — já tinham tenant_id (3 locais)
- ✅ `handlers/event_handler.py` — já usa v2

**Funções corrigidas:**
1. `limpar_contexto_agendamento_v2()` — v2 multi-tenant ✅
2. `limpar_contexto_agendamento()` — v1 legado ✅

**Campos com DELETE_FIELD:** 28 campos transitórios
**Campos preservados:** estado_fluxo, aguardando_confirmacao_*, ultima_acao, metadados

---

## 🧪 TESTES OBRIGATÓRIOS (10 cenários)

### TESTE 1: Criar Contexto Sujo com TODOS os Campos

**Objetivo:** Garantir que contexto começa completamente preenchido

```python
# Pseudo-código para setup
contexto_sujo = {
    # Metadados
    "estado_fluxo": "confirmando_agendamento",
    "_tenant_id_guard": "dono_test_123",
    "_actor_id": "user_7371670478",
    
    # Fluxo de agendamento (TODOS sujo)
    "draft_agendamento": {
        "profissional": "Bruna",
        "servico": "Corte",
        "data_hora": "2026-06-20T14:00:00"
    },
    "dados_confirmacao_agendamento": {...},
    "dados_anteriores": {...},
    "profissional_escolhido": "Bruna",
    "data_hora": "2026-06-20T14:00:00",
    "servico": "Corte",
    "hora_confirmada": "14:00",
    "evento_criado": True,
    
    # Fluxo de cancelamento (SUJO se houver)
    "cancelamento_pendente": {...},
    "evento_id_candidato_cancelamento": "evt_123",
    "candidatos_cancelamento": [...],
    
    # Interpretação
    "interpretacao_conversacional": {...},
    "intencao_conversacional": "agendar",
    "objetivo_conversacional": "corte",
    "tipo_ajuste_incremental": "data",
    "modo_conversa": "conversacional",
    
    # Horários
    "modo_escolha_horario": True,
    "horarios_sugeridos": [...],
    "sugestoes": [...],
    
    # Alternativas
    "alternativa_profissional": "Carla",
    "ultima_opcao_profissionais": ["Bruna", "Carla"],
    
    # Histórico
    "historico_texto": ["msg1", "msg2", "msg3"],
    "ultima_consulta": "2026-06-19T10:00:00",
    "ultima_intencao": "agendar",
    
    # Questões
    "pergunta_amanha_mesmo_horario": True,
    "data_hora_pendente": "2026-06-21T14:00:00",
}

# Salvar no Firestore
await atualizar_dado_em_path("Clientes/dono_test_123/Sessoes/user_7371670478", contexto_sujo)
```

**Validação:**
- [ ] Contexto foi salvo com TODOS os 28 campos
- [ ] Firestore mostra documento com todos os campos

---

### TESTE 2: Rodar limpar_contexto_agendamento_v2()

**Objetivo:** Aplicar limpeza v2 multi-tenant

```python
resultado = await limpar_contexto_agendamento_v2("dono_test_123", "user_7371670478")
```

**Validação:**
- [ ] Função retorna True
- [ ] Logs mostram `[PATCH_P0_CLEAR]` e contagem de DELETE_FIELD
- [ ] DELETE_FIELD count == 28

---

### TESTE 3: Recarregar do Firestore

**Objetivo:** Verificar que campos foram deletados

```python
contexto_recarregado = await buscar_dado_em_path("Clientes/dono_test_123/Sessoes/user_7371670478")
```

**Validação:** Nenhum desses campos deve existir:
- [ ] draft_agendamento ✅ DELETADO
- [ ] dados_confirmacao_agendamento ✅ DELETADO
- [ ] cancelamento_pendente ✅ DELETADO
- [ ] evento_id_candidato_cancelamento ✅ DELETADO
- [ ] candidatos_cancelamento ✅ DELETADO
- [ ] profissional_escolhido ✅ DELETADO
- [ ] data_hora ✅ DELETADO
- [ ] servico ✅ DELETADO
- [ ] interpretacao_conversacional ✅ DELETADO
- [ ] intencao_conversacional ✅ DELETADO
- [ ] objetivo_conversacional ✅ DELETADO
- [ ] tipo_ajuste_incremental ✅ DELETADO
- [ ] modo_conversa ✅ DELETADO
- [ ] modo_escolha_horario ✅ DELETADO
- [ ] horarios_sugeridos ✅ DELETADO
- [ ] sugestoes ✅ DELETADO
- [ ] alternativa_profissional ✅ DELETADO
- [ ] ultima_opcao_profissionais ✅ DELETADO
- [ ] historico_texto ✅ DELETADO
- [ ] ultima_consulta ✅ DELETADO
- [ ] ultima_intencao ✅ DELETADO
- [ ] pergunta_amanha_mesmo_horario ✅ DELETADO
- [ ] data_hora_pendente ✅ DELETADO
- [ ] evento_criado ✅ DELETADO
- [ ] hora_confirmada ✅ DELETADO
- [ ] dados_anteriores ✅ DELETADO
- [ ] aguardando_confirmacao_agendamento ✅ DELETADO

---

### TESTE 4: Validar Campos Preservados

**Objetivo:** Confirmar que metadados estruturais foram mantidos

```python
assert contexto_recarregado.get("estado_fluxo") == "idle"
assert contexto_recarregado.get("_tenant_id_guard") == "dono_test_123"
assert contexto_recarregado.get("_actor_id") == "user_7371670478"
assert contexto_recarregado.get("aguardando_confirmacao_agendamento") == False
assert contexto_recarregado.get("aguardando_confirmacao_cancelamento") == False
assert contexto_recarregado.get("ultima_acao") == "contexto_limpo"
```

**Validação:**
- [ ] estado_fluxo == "idle"
- [ ] _tenant_id_guard == "dono_test_123"
- [ ] _actor_id == "user_7371670478"
- [ ] aguardando_confirmacao_agendamento == False
- [ ] aguardando_confirmacao_cancelamento == False
- [ ] ultima_acao == "contexto_limpo"
- [ ] _updated_at é timestamp válido

---

### TESTE 5: Rodar limpar_contexto_agendamento() Legado

**Objetivo:** Validar que v1 legado também funciona

```python
# Primeiro, criar contexto sujo novamente no path legado
path_legado = "Clientes/user_7371670478/MemoriaTemporaria/contexto"
await atualizar_dado_em_path(path_legado, contexto_sujo)

# Limpar com v1
resultado = await limpar_contexto_agendamento("user_7371670478", tenant_id="dono_test_123")
```

**Validação:**
- [ ] Função retorna True
- [ ] Logs mostram `[PATCH_P0_CLEAR]` e contagem de DELETE_FIELD == 28
- [ ] Recarregar mostra que TODOS os 28 campos foram deletados
- [ ] Campos preservados ainda existem com valores corretos

---

### TESTE 6: Fluxo Real — Agendar → Confirmar → Novo Pedido

**Objetivo:** Garantir que contexto limpo não interfere no novo fluxo

**Cenário:**
```
MENSAGEM 1: "Quero agendar corte com Bruna segunda às 14h"
  → Sistema preenche contexto (draft_agendamento, data_hora, etc.)
  → Oferece confirmação

MENSAGEM 2: "Sim"
  → Handler confirma agendamento
  → Chama limpar_contexto_agendamento_v2(dono, user)
  → ✅ TODOS os campos transitórios deletados

MENSAGEM 3: "Quero manicure terça às 10h"
  → Sistema carrega contexto
  → Verifica: estado_fluxo = "idle" ✅
  → Verifica: draft_agendamento = (não existe) ✅
  → Verifica: dados_confirmacao_agendamento = (não existe) ✅
  → Novo fluxo começa limpo, sem lixo do anterior
```

**Validação:**
- [ ] Logs após MENSAGEM 2 mostram DELETE_FIELD aplicado
- [ ] Logs de MENSAGEM 3 carregamento mostram estado_fluxo = "idle"
- [ ] Logs de MENSAGEM 3 não mostram "draft_agendamento encontrado"
- [ ] Novo agendamento flui normalmente
- [ ] Firestore mostra apenas contexto novo após MENSAGEM 3

---

### TESTE 7: Fluxo Real — Agendar → Confirmar → Cancelar → Novo

**Objetivo:** Garantir que patch PATCH_P0_CANCELAMENTO + DELETE_FIELD funciona integrado

**Cenário:**
```
MENSAGEM 1: "Agendar corte com Bruna segunda às 14h"
MENSAGEM 2: "Sim" → agendado + limpar_contexto_agendamento_v2() called
MENSAGEM 3: "Cancelar" → estado = aguardando_confirmacao_cancelamento
MENSAGEM 4: "Sim" → cancelamento confirmado + PATCH_P0_CANCELAMENTO deletar campos
MENSAGEM 5: "Novo agendamento..."
```

**Validação:**
- [ ] Após MENSAGEM 2: contexto limpo, sem draft
- [ ] Após MENSAGEM 4: contexto limpo, sem cancelamento_pendente
- [ ] MENSAGEM 5 não cai em GUARD_P0_CANCELAMENTO (campos deletados)
- [ ] Novo agendamento flui normalmente

---

### TESTE 8: Verificar Que None/False/[] Não Ficam No Firestore

**Objetivo:** Confirmar que DELETE_FIELD foi usado, não None/False/[]

```python
# Criar contexto com campos que seriam setados para vazio
payload_antigo = {
    "draft_agendamento": {},
    "data_hora": None,
    "servico": False,
    "sugestoes": []
}
await atualizar_dado_em_path(path, payload_antigo)

# Limpeza antiga (se tivesse sido feita assim)
# Isso NÃO funcionaria com merge=True

# Mas com DELETE_FIELD (novo patch):
payload_novo = {
    "draft_agendamento": firestore.DELETE_FIELD,
    "data_hora": firestore.DELETE_FIELD,
    "servico": firestore.DELETE_FIELD,
    "sugestoes": firestore.DELETE_FIELD,
}
await atualizar_dado_em_path(path, payload_novo)

# Verificar que campos não existem
recarregado = await buscar_dado_em_path(path)
assert "draft_agendamento" not in recarregado
assert "data_hora" not in recarregado
assert "servico" not in recarregado
assert "sugestoes" not in recarregado
```

**Validação:**
- [ ] DELETE_FIELD realmente remove campos
- [ ] None, False, [] não ficam no Firestore
- [ ] Contraste com comportamento antigo está claro

---

### TESTE 9: Guardrails Não Bloqueiam Contexto Limpo

**Objetivo:** Confirmar que guards não acionam falsos positivos

```python
# Após limpeza
contexto = await carregar_contexto_temporario("user_7371670478", tenant_id="dono_test_123")

# Guards devem passar:
assert contexto.get("estado_fluxo") == "idle"  # ✅ safe
assert not contexto.get("draft_agendamento")  # ✅ safe
assert not contexto.get("cancelamento_pendente")  # ✅ safe
```

**Validação:**
- [ ] Guards não bloqueiam por contexto sujo
- [ ] Novo fluxo não é interceptado
- [ ] Logs não mostram `[GUARD_P0_*] bloqueando`

---

### TESTE 10: Teste de Concorrência (Dois Usuários)

**Objetivo:** Garantir que DELETE_FIELD funciona mesmo com múltiplos usuários

```python
# Usuário 1 limpa
await limpar_contexto_agendamento_v2("dono1", "user1")

# Usuário 2 limpa simultaneamente
await limpar_contexto_agendamento_v2("dono1", "user2")

# Usuário 1 novo fluxo
await carregar_contexto_temporario("user1", tenant_id="dono1")

# Usuário 2 novo fluxo
await carregar_contexto_temporario("user2", tenant_id="dono1")
```

**Validação:**
- [ ] Ambos os contextos limparam corretamente
- [ ] Nenhuma interferência entre usuários
- [ ] DELETE_FIELD funciona para múltiplos docs simultaneamente

---

## ✅ CRITÉRIO DE ACEITE

**Todos os 10 testes DEVEM passar:**

- ✅ Teste 1: Contexto sujo criado
- ✅ Teste 2: limpar_contexto_agendamento_v2() executa com DELETE_FIELD
- ✅ Teste 3: TODOS os 28 campos foram DELETADOS
- ✅ Teste 4: Metadados estruturais foram PRESERVADOS
- ✅ Teste 5: v1 legado também deleta corretamente
- ✅ Teste 6: Fluxo real (agendar → confirmar → novo) limpo
- ✅ Teste 7: Fluxo com cancelamento limpo
- ✅ Teste 8: DELETE_FIELD realmente remove (não None/False/[])
- ✅ Teste 9: Guards não bloqueiam contexto limpo
- ✅ Teste 10: Múltiplos usuários funcionam

**Logs que NÃO devem aparecer após limpeza:**
- ❌ `draft_agendamento antigo encontrado`
- ❌ `estado_fluxo=agendando`
- ❌ `estado_fluxo=aguardando_confirmacao_cancelamento`
- ❌ `dados_confirmacao_agendamento antigo`
- ❌ `[GUARD_P0_*] bloqueando`

---

## 📊 RESULTADO ESPERADO

Após todos os testes passarem:

✅ **Contexto verdadeiramente limpo**
✅ **Novo fluxo começa do zero**
✅ **Sem interferência de estado anterior**
✅ **DELETE_FIELD confirmado como solução**

---

**Próximo passo:** Executar testes automatizados e validar em produção.

