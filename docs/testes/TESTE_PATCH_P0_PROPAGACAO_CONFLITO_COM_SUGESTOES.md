# TESTE OBRIGATÓRIO — PATCH P0 Propagação de Conflito com Sugestões

**Data:** 2026-06-19  
**Status:** 🟢 PATCH APLICADO — TESTES OBRIGATÓRIOS  
**Arquivo:** `handlers/event_handler.py` linhas 978-1055

---

## 📋 RESUMO DO PATCH

Quando `salvar_evento()` detecta conflito/lock:

1. ❌ **Não imprime** "✅ Evento salvo"
2. ❌ **Não cria** notificação
3. ❌ **Não limpa** contexto como sucesso
4. ✅ **Gera** sugestões de horários
5. ✅ **Responde** ao usuário com opções
6. ✅ **Salva** estado `aguardando_escolha_horario`
7. ✅ **Preserva** dados originais em `draft_agendamento`

---

## 🧪 TESTES OBRIGATÓRIOS (8 cenários)

### TESTE 1: Detecção de Conflito

**Cenário:** `salvar_evento()` retorna `"conflito_lock_existente"`

**Validação:**
- [ ] Log mostra `[PATCH_P0_CONFLITO] Conflito detectado: lock_existente`
- [ ] NÃO imprime `✅ Evento salvo`
- [ ] Função `verificar_conflito_e_sugestoes_profissional()` é chamada
- [ ] Retorna True (parou fluxo)

**Código de teste:**
```python
resultado_salvamento = "conflito_lock_existente"

# Patch deve capturar
assert resultado_salvamento.startswith("conflito_")
# Deve gerar sugestões
# NÃO deve imprimir "Evento salvo"
```

---

### TESTE 2: Sem Criação de Notificação

**Cenário:** Conflito detectado, sem enviar notificação

**Validação:**
- [ ] Não chama `criar_ou_atualizar_profile_apos_evento()`
- [ ] Não envia WhatsApp
- [ ] Não envia notificação de confirmação
- [ ] Apenas responde no Telegram com opções

**Verificar logs:**
```
❌ Não deve conter: "Notificação enviada"
❌ Não deve conter: "WhatsApp enviado"
❌ Não deve conter: "Profile atualizado"
```

---

### TESTE 3: Salva Estado Correto

**Cenário:** Contexto é salvo com `estado_fluxo="aguardando_escolha_horario"`

**Validação:**
- [ ] Firestore contém campo `estado_fluxo: "aguardando_escolha_horario"`
- [ ] Firestore contém `motivo_bloqueio: "lock_existente"` (ou outro tipo de erro)
- [ ] Firestore contém `draft_agendamento: {...}` (dados originais preservados)
- [ ] Firestore contém `horarios_sugeridos: [...]` (sugestões geradas)
- [ ] Firestore contém `ultima_acao: "conflito_detectado"`

**Verificar em Firestore:**
```json
{
  "estado_fluxo": "aguardando_escolha_horario",
  "motivo_bloqueio": "lock_existente",
  "draft_agendamento": {
    "descricao": "Corte",
    "data": "2026-06-20",
    "hora_inicio": "10:00",
    "profissional": "Bruna"
  },
  "horarios_sugeridos": ["10:30", "11:00", "11:30"],
  "alternativa_profissional": ["Carla", "Marina"],
  "ultima_acao": "conflito_detectado"
}
```

---

### TESTE 4: Resposta ao Usuário com Sugestões

**Cenário:** Usuário recebe mensagem clara com opções

**Resposta esperada:**
```
❌ A Bruna não tem esse horário disponível.

✅ Posso oferecer estes horários:
*10:30*, *11:00*, *11:30*

💡 Ou posso agendar com: *Carla*, *Marina*

Qual preferir?
```

**Validação:**
- [ ] Mensagem contém nome do profissional
- [ ] Mensagem contém indicação de conflito (❌)
- [ ] Mensagem lista sugestões de horários (até 3)
- [ ] Mensagem oferece profissionais alternativos (até 2)
- [ ] Mensagem pergunta preferência clara

---

### TESTE 5: Preservação de Dados Originais

**Cenário:** `draft_agendamento` contém exatamente os dados que falharam

**Verificar:**
```python
draft = contexto.get("draft_agendamento")

assert draft["data"] == "2026-06-20"
assert draft["hora_inicio"] == "10:00"
assert draft["profissional"] == "Bruna"
assert draft["servico"] == "Corte"
assert draft["cliente_nome"] == "João"
```

**Validação:**
- [ ] Todos os campos originais estão em `draft_agendamento`
- [ ] Nenhum campo foi alterado ou perdido
- [ ] Dados podem ser reutilizados para nova tentativa

---

### TESTE 6: Sugestões Válidas

**Cenário:** Sugestões retornadas são realmente disponíveis

**Validação:**
- [ ] `horarios_sugeridos` contém apenas horários livres
- [ ] Cada horário foi verificado contra agenda do profissional
- [ ] Sugestões respeitam duração do evento
- [ ] Sugestões respeitam expediente

**Verificar:**
```python
sugestoes = contexto.get("horarios_sugeridos")

# Cada sugestão deve ser HH:MM válido
for s in sugestoes:
    assert ":" in s  # é hora

# Máximo 3 sugestões
assert len(sugestoes) <= 3

# Sugestões são strings
assert all(isinstance(s, str) for s in sugestoes)
```

---

### TESTE 7: Alternativas Corretas

**Cenário:** Profissionais alternativos oferecem o mesmo serviço

**Validação:**
- [ ] Cada profissional alternativo oferece o serviço solicitado
- [ ] Cada alternativo está disponível no horário original
- [ ] Máximo 2 alternativas oferecidas
- [ ] Nomes são reais (conferir contra base de profissionais)

**Verificar:**
```python
alts = contexto.get("alternativa_profissional")

# Máximo 2
assert len(alts) <= 2

# Devem ser strings com nomes
assert all(isinstance(p, str) for p in alts)

# Cada deve ser profissional cadastrado
for p in alts:
    assert await buscar_profissional(p)  # existe
    assert servico in profissional.get("servicos")  # faz o serviço
```

---

### TESTE 8: Fluxo Seguinte Válido

**Cenário:** Usuário escolhe uma sugestão e motor revalida antes de criar

**Fluxo:**
```
1. Conflito detectado → resposta com sugestões
2. Usuário: "10:30"
3. Motor valida se 10:30 está REALMENTE livre
4. Se sim → cria evento
5. Se não → novo conflito (cycle)
```

**Validação:**
- [ ] Ao escolher horário sugerido, motor valida novamente
- [ ] Se ainda há conflito, responde com novas sugestões
- [ ] Se disponível, cria evento com sucesso
- [ ] Contexto é limpo após sucesso

---

## ✅ CRITÉRIO DE ACEITE

**Todos os 8 testes DEVEM passar:**

- ✅ Teste 1: Conflito é detectado e logs corretos
- ✅ Teste 2: Sem notificação (não é sucesso)
- ✅ Teste 3: Estado correto em Firestore
- ✅ Teste 4: Resposta ao usuário clara e útil
- ✅ Teste 5: Dados originais preservados
- ✅ Teste 6: Sugestões são válidas
- ✅ Teste 7: Alternativas fazem o serviço
- ✅ Teste 8: Fluxo seguinte revalida

**Logs que NÃO devem aparecer em conflito:**
- ❌ `✅ Evento salvo`
- ❌ `Notificação enviada`
- ❌ `WhatsApp enviado`
- ❌ `Profile atualizado`

**Logs que DEVEM aparecer em conflito:**
- ✅ `[PATCH_P0_CONFLITO] Conflito detectado`
- ✅ `[PATCH_P0_CONFLITO] Sugestões geradas`
- ✅ `[PATCH_P0_CONFLITO] Contexto salvo: estado_fluxo=aguardando_escolha_horario`

---

## 📊 CENÁRIO COMPLETO DE TESTE

### Setup
```python
# Criar agenda com slot ocupado
evento_existente = {
    "profissional": "Bruna",
    "data": "2026-06-20",
    "hora_inicio": "10:00",
    "hora_fim": "10:20"
}
await salvar_evento(dono_id, evento_existente)

# Tentar agendar no mesmo horário
evento_novo = {
    "profissional": "Bruna",
    "data": "2026-06-20",
    "hora_inicio": "10:00",  # ← Conflito!
    "duracao": 20
}
```

### Execução
```python
resultado = await salvar_evento(user_id, evento_novo)
assert resultado.startswith("conflito_")

# Handler deve:
# 1. Gerar sugestões
sugestoes = await verificar_conflito_e_sugestoes_profissional(...)
assert len(sugestoes) > 0

# 2. Responder ao usuário
await update.message.reply_text(resposta_com_sugestoes)

# 3. Salvar estado
contexto = {
    "estado_fluxo": "aguardando_escolha_horario",
    "draft_agendamento": evento_novo,
    "horarios_sugeridos": sugestoes
}
await salvar_contexto_temporario(user_id, contexto)
```

### Verificação
```python
# Confirmações
assert contexto.get("estado_fluxo") == "aguardando_escolha_horario"
assert contexto.get("draft_agendamento") is not None
assert len(contexto.get("horarios_sugeridos")) > 0
assert "evento foi salvo" not in logs_handler  # Não foi sucesso
```

---

## 🎯 PRÓXIMOS PASSOS

Após testes passarem:

1. **Implementar fluxo de escolha:**
   - Usuário: "10:30" (escolhe sugestão)
   - Motor: Revalida se 10:30 está livre
   - Se sim → cria evento
   - Se não → volta ao passo 1

2. **Implementar escolha de profissional alternativo:**
   - Usuário: "Carla"
   - Motor: Valida se Carla oferece serviço e tem horário
   - Se sim → cria com Carla
   - Se não → novo conflito

3. **Implementar limpeza após sucesso:**
   - `draft_agendamento` → removido
   - `estado_fluxo` → "idle"
   - `horarios_sugeridos` → removido

---

**Status:** 🟢 **PRONTO PARA TESTE**

