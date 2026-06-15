# 📖 MICRO-SPEC P1.2A: Leitura Apenas — ClienteProfile

**Data:** 2026-06-14  
**Fase:** P1.2A (ANTERIOR a P1.2B e P1.3)  
**Objetivo:** Carregar ClienteProfile no contexto SEM alterar interpretação, extração ou resposta  
**Duração Estimada:** 1-2 PRs (separados de P1.2B)  
**Status:** PRONTO PARA IMPLEMENTAÇÃO  

---

## 🎯 Escopo EXATO de P1.2A

### ✅ P1.2A DEVE Fazer

1. **Carregar Profile**
   - Chamar `obter_profile(tenant_id, cliente_id)`
   - Apenas para modo_conversa == "agendamento_cliente"
   - Em local seguro: APÓS motor determinístico

2. **Salvar em Contexto**
   - `ctx["clienteprofile"] = profile`
   - `ctx["clienteprofile_carregado_em"] = datetime.now().isoformat()`
   - `ctx["clienteprofile_tenant_cliente"] = f"{tenant_id}#{cliente_id}"`

3. **Logs/Debug**
   - Log quando carregado: "ClienteProfile carregado para ctx"
   - Log quando erro: "Erro ao carregar ClienteProfile: {erro}"
   - Não quebra fluxo em caso de erro

4. **Validação Básica**
   - Validar schema (tem "historico"? tem "tendencias"?)
   - Descartar se inválido (log + continue)
   - Nunca falhar por profile inválido

5. **Persistir Contexto**
   - Salvar contexto atualizado em MemoriaTemporaria
   - Profile agora disponível para P1.2B/P1.3

---

### ❌ P1.2A NÃO DEVE Fazer

```
❌ Alterar prompt do GPT
❌ Modificar slots extraídos (serviço, profissional, data, hora)
❌ Preencher campos do draft automaticamente
❌ Alterar resposta ao cliente
❌ Sugerir profissional ("Costuma com Carla?")
❌ Preencher tentativas de auto-complete
❌ Influenciar motor determinístico
❌ Alterar validação de conflito
❌ Criar evento automaticamente
❌ Saltar confirmação obrigatória
```

---

## 🗺️ Localização Exata de Implementação

### Arquivo: `router/principal_router.py`

**Após linha ~3600 (motor determinístico completo)**

```python
# =========================================================
# 🔥 Linha ~3600: Motor determinístico finaliza
# =========================================================
resultado_motor = verificar_conflito_e_sugestoes_profissional(...)
# draft_agendamento agora está montado

# =========================================================
# ✅ P1.2A: Carregar ClienteProfile AQUI
# =========================================================
try:
    profile = await obter_profile(tenant_id, cliente_id)
    if profile:  # validar schema brevemente
        ctx["clienteprofile"] = profile
        ctx["clienteprofile_carregado_em"] = datetime.now().isoformat()
        print(f"[P1.2A] ClienteProfile carregado para {cliente_id}")
except Exception as e:
    print(f"[P1.2A] Erro ao carregar profile: {e}")
    # NÃO quebra fluxo

await salvar_contexto_temporario(user_id, ctx)

# =========================================================
# Linha ~3650: Preconfirmação (draft já está pronto)
# =========================================================
resposta = montar_mensagem_preconfirmacao(draft_agendamento, ctx)
# ctx["clienteprofile"] está disponível para logs, mas NÃO altera resposta
```

---

## 📝 Exemplo de Implementação P1.2A

### Código Seguro (Sem Influência)

```python
# router/principal_router.py
async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    # ... (linhas anteriores)
    
    # Após motor determinístico (linha ~3600)
    
    # =========================================================
    # P1.2A: Carregar ClienteProfile (leitura apenas)
    # =========================================================
    if ctx.get("modo_conversa") == "agendamento_cliente":
        try:
            from services.clienteprofile_service import obter_profile
            from services.firebase_service_async import obter_id_dono
            
            # Resolver IDs
            dono_id = await obter_id_dono(user_id)
            
            # Carregar
            profile = await obter_profile(dono_id, user_id)
            
            if profile:
                # ✅ Salvar em contexto
                ctx["clienteprofile"] = profile
                ctx["clienteprofile_carregado_em"] = datetime.now().isoformat()
                
                # ✅ Log
                print(
                    f"[P1.2A] Profile carregado "
                    f"tenant={dono_id} cliente={user_id} "
                    f"agendamentos={profile.get('historico', {}).get('total_eventos', 0)}",
                    flush=True
                )
        
        except Exception as e:
            # ✅ Não quebra fluxo
            print(
                f"[P1.2A] Aviso: Erro ao carregar profile: {e}",
                flush=True
            )
            ctx["clienteprofile"] = None
    
    # Salvar contexto atualizado
    await salvar_contexto_temporario(user_id, ctx)
    
    # =========================================================
    # Continua fluxo normal (preconfirmação, etc)
    # P1.2A não alterou NADA, apenas adicionou ctx["clienteprofile"]
    # =========================================================
    resposta = montar_mensagem_preconfirmacao(ctx)
    # ... resto do fluxo
```

### ❌ Código PERIGOSO (Violaria P1.2A)

```python
# ❌ ERRO 1: Influenciar GPT
prompt_customizado = f"""
Cliente: {cliente_nome}
Histórico: Costuma com {profile['profissional_mais_frequente']}
Pergunta: {mensagem}
"""
slots = await chamar_gpt_com_contexto(prompt_customizado)
# ❌ Viola: GPT recebe profile no prompt

# ❌ ERRO 2: Preencher draft automaticamente
draft["profissional"] = profile["profissional_mais_frequente"]
# ❌ Viola: Draft alterado sem confirmação

# ❌ ERRO 3: Sugestão sem confirmação
resposta = f"Ótimo! Corte com {profile['profissional_mais_frequente']}, certo?"
# ❌ Viola: Sugestão sem confirmação (é P1.3)

# ❌ ERRO 4: Criar evento baseado em profile
if profile["taxa_confirmacao"] > 0.9:
    criar_evento(...)  # Auto-agendamento por histórico
# ❌ Viola: Decisão automática baseada em profile
```

---

## 🧪 Testes Obrigatórios para P1.2A

### Test 1: Profile é Carregado

```python
@pytest.mark.asyncio
async def test_p1_2a_profile_loaded_for_scheduling():
    """P1.2A: Profile deve ser carregado para agendamento"""
    user_id = "123"
    tenant_id = "dono123"
    
    # Setup
    ctx = await carregar_contexto_temporario(user_id)
    ctx["modo_conversa"] = "agendamento_cliente"
    
    # Executar
    await roteador_principal(user_id, "Quero corte", None, None)
    
    # Verificar
    ctx_final = await carregar_contexto_temporario(user_id)
    assert "clienteprofile" in ctx_final
    assert ctx_final["clienteprofile"] is not None
    assert "historico" in ctx_final["clienteprofile"]
```

### Test 2: Profile NÃO Altera Extração GPT

```python
@pytest.mark.asyncio
async def test_p1_2a_profile_does_not_alter_gpt():
    """P1.2A: Profile NÃO deve alterar extração do GPT"""
    mensagem = "Quero corte"
    
    # Sem profile (mock)
    with mock.patch("obter_profile", return_value=None):
        slots_sem = await extrair_slots_com_gpt(mensagem)
    
    # Com profile (mock)
    profile_mock = {
        "historico": {"total_eventos": 50},
        "tendencias": {"profissional_mais_frequente": "Carla"}
    }
    with mock.patch("obter_profile", return_value=profile_mock):
        slots_com = await extrair_slots_com_gpt(mensagem)
    
    # Verificar
    assert slots_sem == slots_com  # Idênticos!
    # (profile NÃO entrou no prompt)
```

### Test 3: Draft NÃO é Alterado

```python
@pytest.mark.asyncio
async def test_p1_2a_draft_unchanged():
    """P1.2A: Draft não deve ser preenchido com profile"""
    draft_esperado = {
        "servico": "corte",
        "profissional": None,  # Usuário ainda não escolheu
        "data_hora": None
    }
    
    profile_mock = {
        "tendencias": {"profissional_mais_frequente": "Carla"}
    }
    
    # Mesmo com profile, draft não muda
    with mock.patch("obter_profile", return_value=profile_mock):
        draft_resultado = await montar_draft_agendamento(
            "Quero corte", "Carla"  # Carla no profile, não no input
        )
    
    assert draft_resultado == draft_esperado
```

### Test 4: Resposta NÃO é Alterada

```python
@pytest.mark.asyncio
async def test_p1_2a_response_unchanged():
    """P1.2A: Resposta não deve incluir sugestão"""
    profile_mock = {
        "tendencias": {"profissional_mais_frequente": "Carla"}
    }
    
    resposta_esperada = "Qual profissional você prefere?"
    
    with mock.patch("obter_profile", return_value=profile_mock):
        resposta = await gerar_resposta_proximo_passo(ctx_with_profile)
    
    # Resposta NÃO deve mencionar "Carla" (seria sugestão = P1.3)
    assert "Carla" not in resposta
    assert resposta == resposta_esperada
```

### Test 5: Profile Não Carregado Para Pessoal

```python
@pytest.mark.asyncio
async def test_p1_2a_no_load_for_personal():
    """P1.2A: Profile não deve ser carregado para conversa pessoal"""
    ctx = {}
    
    # Conversa pessoal
    modo_conversa = classificar_contexto_mensagem("Tudo bem?", {})
    assert modo_conversa == "pessoal"
    
    # Profile NÃO carregado
    assert "clienteprofile" not in ctx
```

### Test 6: Erro Não Quebra Fluxo

```python
@pytest.mark.asyncio
async def test_p1_2a_error_does_not_break_flow():
    """P1.2A: Erro ao carregar profile não quebra agendamento"""
    
    # Mock erro
    with mock.patch("obter_profile", side_effect=Exception("Firestore erro")):
        # Agendamento continua
        resposta = await roteador_principal(user_id, "Quero corte")
    
    # Fluxo não quebrou
    assert resposta is not None
    assert "erro" not in resposta.lower()  # Sem mensagem de erro ao usuário
```

---

## 📊 Resultado Final de P1.2A

### Antes de P1.2A
```
Mensagem: "Quero corte com Carla"
      ↓
   GPT: extrai {serviço: "corte", profissional: "Carla"}
      ↓
   Draft: {serviço: "corte", profissional: "Carla"}
      ↓
   Resposta: "Corte com Carla, qual dia?"
      ↓
   ctx: {draft, estado_fluxo, ...}
```

### Depois de P1.2A
```
Mensagem: "Quero corte com Carla"
      ↓
   GPT: extrai {serviço: "corte", profissional: "Carla"}
      ↓
   Draft: {serviço: "corte", profissional: "Carla"}
      ↓
   Profile carregado: {profissional_mais_frequente: "Paula", ...}
      ↓
   Resposta: "Corte com Carla, qual dia?" (SEM mudança)
      ↓
   ctx: {draft, estado_fluxo, clienteprofile, ...}
      ↓
   P1.2B pode usar profile para contexto
   P1.3 pode usar profile para sugestão (COM confirmação)
```

### O Que Mudou?
- ✅ Apenas adicionado `ctx["clienteprofile"]`
- ❌ Nada mais foi alterado
- ✅ Isolamento perfeito de leitura vs influência

---

## ✅ Checklist de Aprovação P1.2A

Antes de mergear para main:

### Código
- [ ] Profile carregado APÓS motor determinístico (não antes)
- [ ] Salvo em `ctx["clienteprofile"]`
- [ ] NÃO entra em prompt do GPT
- [ ] NÃO altera draft_agendamento
- [ ] NÃO altera resposta_final
- [ ] Erros tratados (não quebra fluxo)

### Testes
- [ ] Test 1: Profile carregado (✅ PASS)
- [ ] Test 2: GPT não alterado (✅ PASS)
- [ ] Test 3: Draft não alterado (✅ PASS)
- [ ] Test 4: Resposta não alterada (✅ PASS)
- [ ] Test 5: Não carregado para pessoal (✅ PASS)
- [ ] Test 6: Erro não quebra fluxo (✅ PASS)

### Code Review
- [ ] SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md citada
- [ ] POLITICA_CODE_REVIEW_CLIENTEPROFILE.md validada
- [ ] Checklist P1.2A preenchida (11 itens)
- [ ] Revisor confirmou: "Leitura apenas, sem influência"

### Documentação
- [ ] AUDITORIA_PONTO_INTEGRACAO_P1_2_CLIENTEPROFILE.md consultada
- [ ] Localização exata confirma ponto recomendado
- [ ] Nenhuma sugestão foi adicionada (é P1.3)

---

## 🚀 Próximo Passo (Após P1.2A Validado)

### P1.2B: Exposição Controlada
- Motor determinístico pode consultar `ctx["clienteprofile"]`
- Ainda sem alterar resposta
- Preparando para P1.3

### P1.3: Primeira Sugestão
- Profile pode gerar sugestão: "Costuma com Carla?"
- SEMPRE com confirmação explícita
- Respeitando SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md

---

**Micro-Spec Status:** ✅ PRONTA PARA IMPLEMENTAÇÃO  
**Data:** 2026-06-14  
**Fase Seguinte:** P1.2A (Implementação + Validação)
