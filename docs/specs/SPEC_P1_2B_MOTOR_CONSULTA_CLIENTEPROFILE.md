# 📖 MICRO-SPEC P1.2B: Motor Determinístico Consulta ClienteProfile

**Data:** 2026-06-14  
**Status:** ✅ PRONTA PARA IMPLEMENTAÇÃO  
**Escopo:** Motor lê contexto, sem alterar resposta  
**Restrição:** Leitura e Contexto Apenas (Zero Influência)  

---

## 🎯 Objetivo de P1.2B

```
Permitir que o motor determinístico consulte ClienteProfile
para ENTENDER o contexto do cliente,
sem ALTERAR a resposta, draft, confirmação ou criação de evento.

P1.2B = Motor lê e entende contexto
P1.3 = Motor usa contexto para sugerir com confirmação
```

---

## ✅ ESCOPO PERMITIDO EM P1.2B

### 1. Ler ctx["clienteprofile"]
```python
# ✅ PERMITIDO
if "clienteprofile" in ctx and ctx["clienteprofile"]:
    profile = ctx["clienteprofile"]
    # ... usar para contexto apenas
```

### 2. Extrair Apenas Contexto Interno
```python
# ✅ PERMITIDO: Ler estes campos
total_eventos = profile.get("historico", {}).get("total_eventos", 0)
prof_mais_freq = profile.get("tendencias", {}).get("profissional_mais_frequente")
serv_mais_freq = profile.get("tendencias", {}).get("servico_mais_frequente")
ultima_contato = profile.get("historico", {}).get("ultima_contato")

# ✅ Usar para ENTENDER contexto
if total_eventos > 20:
    log: "Cliente com histórico significativo"
elif total_eventos < 5:
    log: "Cliente novo, histórico limitado"
```

### 3. Criar Estrutura Interna (Contexto Neutro Apenas)
```python
# ✅ PERMITIDO: Adicionar contexto interno ao ctx
# IMPORTANTE: Usar APENAS nomes neutros (sem "sugestão", "oferta", "ação")
ctx["clienteprofile_contexto_motor"] = {
    # Métricas extraídas (neutro)
    "total_eventos": total_eventos,
    "profissional_mais_frequente": prof_mais_freq,
    "servico_mais_frequente": serv_mais_freq,
    "ultima_contato": ultima_contato,
    
    # Flags de categorização (neutro)
    "cliente_novo": total_eventos < 5,
    "cliente_veterano": total_eventos > 20,
    "cliente_inativo": (agora - parse(ultima_contato)).days > 30,
    
    # Metadados de fonte e modo
    "fonte": "clienteprofile",
    "modo": "contexto_apenas",
}

# ✅ Usar para logs/auditoria
log: f"[MOTOR P1.2B] Contexto carregado: {ctx['clienteprofile_contexto_motor']}"
```

**PROIBIDO em P1.2B:**
```python
# ❌ NÃO adicionar campos com nomes de ação
"profissional_sugestao": prof_mais_freq,  # ❌ É P1.3
"servico_sugestao": serv_mais_freq,      # ❌ É P1.3
"reengajement_elegivel": True,           # ❌ É P1.3+
"oferta_premium_elegivel": True,         # ❌ É P1.3+
"pode_pular_prof": True,                 # ❌ É P1.3

# Razão: P1.2B é contexto NEUTRO
# Vocabulário de ação/sugestão pertence a P1.3+
```

### 4. Logar Contexto para Auditoria
```python
# ✅ PERMITIDO: Logs informativos
print(f"[P1.2B] Profile disponível para motor")
print(f"[P1.2B] Cliente com {total_eventos} eventos históricos")
print(f"[P1.2B] Último contato: {ultima_contato}")
print(f"[P1.2B] Profissional mais frequente: {prof_mais_freq}")
```

### 5. NÃO Alterar Resposta, Draft, Confirmação ou Criação
```python
# ✅ GARANTIDO: Nenhuma alteração
resposta_P1.2A = "Confirmando: *corte* com *Carla*..."
resposta_P1.2B = "Confirmando: *corte* com *Carla*..."
assert resposta_P1.2A == resposta_P1.2B  # ✅ IDÊNTICA

draft_P1.2A = {"servico": "corte", "profissional": "Carla"}
draft_P1.2B = {"servico": "corte", "profissional": "Carla"}
assert draft_P1.2A == draft_P1.2B  # ✅ IDÊNTICO

confirmacao_P1.2A = True
confirmacao_P1.2B = True
assert confirmacao_P1.2A == confirmacao_P1.2B  # ✅ IDÊNTICA
```

---

## ❌ PROIBIDO EM P1.2B

### Sugerir Profissional (SEM Confirmação)
```python
# ❌ PROIBIDO: Sugerir sem confirmação (P1.3)
if prof_mais_freq:
    resposta = f"Você quer com {prof_mais_freq}?"  # ❌ É P1.3

ctx["draft_agendamento"]["profissional"] = prof_mais_freq  # ❌ É P1.3

# ✅ P1.2B: Apenas armazenar como contexto neutro
ctx["clienteprofile_contexto_motor"]["profissional_mais_frequente"] = prof_mais_freq
# (sem nome de "sugestao" — é apenas contexto)
```

### Sugerir Serviço (SEM Confirmação)
```python
# ❌ PROIBIDO: Sugerir sem confirmação (P1.3)
resposta = f"Você quer fazer {serv_mais_freq}?"  # ❌ É P1.3

ctx["draft_agendamento"]["servico"] = serv_mais_freq  # ❌ É P1.3

# ✅ P1.2B: Apenas armazenar como contexto neutro
ctx["clienteprofile_contexto_motor"]["servico_mais_frequente"] = serv_mais_freq
# (sem nome de "sugestao" — é apenas contexto)
```

### Preencher Default
```python
# ❌ PROIBIDO: Alterar draft baseado em profile
if prof_mais_freq and not ctx.get("profissional_escolhido"):
    ctx["profissional_escolhido"] = prof_mais_freq  # ❌ É P1.3

# ❌ PROIBIDO: Alterar resposta com default
resposta = f"Qual profissional? ({prof_mais_freq} é recomendado)"  # ❌ É P1.3
```

### Reduzir Perguntas
```python
# ❌ PROIBIDO: Pular perguntas baseado em profile
if prof_mais_freq:
    # Não perguntar profissional  # ❌ É P1.3
    perguntar_profissional = False

# ✅ PERMITIDO: Apenas documentar
ctx["clienteprofile_contexto_motor"]["pode_pular_prof"] = prof_mais_freq is not None
# (Será usado em P1.3)
```

### Re-engajamento (P1.3+)
```python
# ❌ PROIBIDO: Oferecer promoção/reativação em P1.2B
if cliente_inativo > 30:
    oferecer_promocao = True  # ❌ É P1.3

# ✅ PERMITIDO: Apenas marcar no contexto
ctx["clienteprofile_contexto_motor"]["cliente_inativo_dias"] = cliente_inativo
```

### Oferta/Promoção/Segmentação
```python
# ❌ PROIBIDO: Toda decisão comercial é P1.3+
if cliente_novo:
    oferecer_onboarding = True  # ❌ É P1.3

if cliente_veterano:
    oferecer_premium = True  # ❌ É P1.3

# ✅ PERMITIDO: Apenas registrar flag
ctx["clienteprofile_contexto_motor"]["cliente_novo"] = total_eventos < 5
ctx["clienteprofile_contexto_motor"]["cliente_veterano"] = total_eventos > 20
```

### Mudar Prompt GPT
```python
# ❌ PROIBIDO: Alterar como GPT extrai slots
prompt_customizado = f"Cliente histórico: {prof_mais_freq}"
resposta_gpt = await chamar_gpt(prompt_customizado)  # ❌ É P1.2B+

# ✅ PERMITIDO: GPT continua recebendo contexto normal
resposta_gpt = await chamar_gpt(mensagem_usuario, ctx_normal)
# (Profile pode ser passado em P1.2B+ se não alterar extração)
```

### Alterar Fluxo
```python
# ❌ PROIBIDO: Pular ou adicionar passos
if prof_mais_freq:
    estado_fluxo = "confirmacao"  # ❌ Pula "perguntar profissional"

# ✅ PERMITIDO: Fluxo continua igual
# (Apenas contexto interno adicionado)
```

---

## 🏗️ Estrutura de Dados P1.2B

### Entrada: ctx["clienteprofile"]
```python
{
    "cliente_id": "user123",
    "tenant_id": "dono123",
    "historico": {
        "total_eventos": 50,
        "profissionais_atendidos": ["Carla", "Paula", "Bruna"],
        "servicos_atendidos": ["corte", "escova"],
        "ultima_contato": "2026-06-10T14:30:00"
    },
    "tendencias": {
        "profissional_mais_frequente": "Carla",
        "servico_mais_frequente": "corte"
    }
}
```

### Saída: ctx["clienteprofile_contexto_motor"] (CONTEXTO NEUTRO APENAS)
```python
{
    # Métricas extraídas do profile (neutro)
    "total_eventos": 50,
    "profissional_mais_frequente": "Carla",
    "servico_mais_frequente": "corte",
    "ultima_contato": "2026-06-10T14:30:00",
    
    # Flags de categorização (neutro)
    "cliente_novo": False,          # total_eventos < 5
    "cliente_veterano": True,       # total_eventos > 20
    "cliente_inativo": False,       # ultima_contato > 30 dias
    
    # Metadados (neutro)
    "fonte": "clienteprofile",      # Identifica origem
    "modo": "contexto_apenas",      # Identifica que é P1.2B
}
```

**O que NÃO deve aparecer em P1.2B:**
```python
# ❌ PROIBIDO: Vocabulário de P1.3+
"profissional_sugestao": ...,      # ❌ É decisão P1.3
"servico_sugestao": ...,           # ❌ É decisão P1.3
"pode_pular_prof": ...,            # ❌ É otimização P1.3
"pode_pular_serv": ...,            # ❌ É otimização P1.3
"reengajement_elegivel": ...,      # ❌ É ação P1.3+
"premium_offer_elegivel": ...,     # ❌ É ação P1.3+

# Razão: P1.2B é contexto neutro
# Decisões/ações/ofertas são responsabilidade de P1.3+
# Motor em P1.2B apenas lê e categoriza (não oferece)
```

### Uso em P1.2B: Contexto Neutro Apenas
```python
# ✅ P1.2B: Motor lê contexto (zero ação)
if ctx.get("clienteprofile_contexto_motor"):
    contexto = ctx["clienteprofile_contexto_motor"]
    
    # Log informativo (contexto para auditoria)
    log: f"[MOTOR P1.2B] {contexto['fonte']} - {contexto['modo']}"
    if contexto["cliente_veterano"]:
        log: "Cliente com 20+ eventos históricos"
    
    # Usar APENAS para entender situação, NÃO para oferecer/decidir
    # NÃO alterar resposta/draft/fluxo
    resposta = "Confirmando: *corte* com *Carla*..."  # IDÊNTICA
    draft = {"servico": "corte", "profissional": "Carla"}  # IDÊNTICO

# ❌ P1.2B NUNCA usa contexto para oferta/sugestão/ação
# Isso é responsabilidade de P1.3+
```

---

## 🧪 Testes Obrigatórios

### Test 1: Contexto Motor Criado (Profile Existe)
```python
def test_p1_2b_contexto_motor_criado():
    """P1.2B: ctx['clienteprofile_contexto_motor'] criado quando profile existe"""
    
    ctx = {
        "clienteprofile": {
            "historico": {"total_eventos": 50},
            "tendencias": {"profissional_mais_frequente": "Carla"}
        }
    }
    
    # Executar P1.2B (motor consulta profile)
    ctx["clienteprofile_contexto_motor"] = extrair_contexto(ctx["clienteprofile"])
    
    # Validação (CAMPOS NEUTROS, não "sugestao")
    assert ctx["clienteprofile_contexto_motor"] is not None
    assert ctx["clienteprofile_contexto_motor"]["total_eventos"] == 50
    assert ctx["clienteprofile_contexto_motor"]["profissional_mais_frequente"] == "Carla"  # Neutro!
    assert ctx["clienteprofile_contexto_motor"]["fonte"] == "clienteprofile"
    assert ctx["clienteprofile_contexto_motor"]["modo"] == "contexto_apenas"
```

### Test 2: Contexto Motor None (Profile Não Existe)
```python
def test_p1_2b_contexto_motor_none():
    """P1.2B: ctx['clienteprofile_contexto_motor'] None quando profile não existe"""
    
    ctx = {}  # Sem profile
    
    # Executar P1.2B (motor tenta consultar profile)
    if "clienteprofile" in ctx:
        ctx["clienteprofile_contexto_motor"] = extrair_contexto(ctx["clienteprofile"])
    else:
        ctx["clienteprofile_contexto_motor"] = None
    
    # Validação
    assert ctx["clienteprofile_contexto_motor"] is None
```

### Test 3: Draft Permanece Igual
```python
def test_p1_2b_draft_permanece_igual():
    """P1.2B: draft_agendamento não é alterado"""
    
    draft_antes = {
        "servico": "corte",
        "profissional": "Bruna",
        "data_hora": "2026-06-20T15:00:00"
    }
    
    ctx = {
        "draft_agendamento": draft_antes.copy(),
        "clienteprofile": {
            "tendencias": {
                "profissional_mais_frequente": "Carla",  # DIFERENTE de Bruna
                "servico_mais_frequente": "escova"  # DIFERENTE de corte
            }
        }
    }
    
    # Executar P1.2B (motor lê profile)
    ctx["clienteprofile_contexto_motor"] = extrair_contexto(ctx["clienteprofile"])
    
    # Validação: draft NÃO foi alterado
    assert ctx["draft_agendamento"] == draft_antes
    assert ctx["draft_agendamento"]["profissional"] == "Bruna"  # NÃO mudou
    assert ctx["draft_agendamento"]["servico"] == "corte"  # NÃO mudou
```

### Test 4: Mensagem Confirmação Permanece Igual
```python
def test_p1_2b_mensagem_confirmacao_igual():
    """P1.2B: resposta de confirmação não é alterada"""
    
    msg_antes = "Confirmando: *corte* com *Bruna* em *20/06*. Responda *sim*."
    
    ctx = {
        "clienteprofile": {
            "historico": {"total_eventos": 100},
            "tendencias": {"profissional_mais_frequente": "Carla"}
        }
    }
    
    # Executar P1.2B (motor lê profile)
    ctx["clienteprofile_contexto_motor"] = extrair_contexto(ctx["clienteprofile"])
    msg_depois = "Confirmando: *corte* com *Bruna* em *20/06*. Responda *sim*."
    
    # Validação
    assert msg_antes == msg_depois
```

### Test 5: Nenhuma Sugestão Nova Aparece
```python
def test_p1_2b_sem_sugestao_nova():
    """P1.2B: nenhuma sugestão é oferecida"""
    
    ctx = {
        "clienteprofile": {
            "tendencias": {
                "profissional_mais_frequente": "Carla",
                "servico_mais_frequente": "escova"
            }
        }
    }
    
    # Executar P1.2B
    ctx["clienteprofile_contexto_motor"] = extrair_contexto(ctx["clienteprofile"])
    
    # Validação: resposta não contém sugestão
    resposta = "Confirmando: *corte* com *Bruna*..."
    assert "Carla" not in resposta  # NÃO sugere profissional
    assert "escova" not in resposta  # NÃO sugere serviço
    assert "Você quer" not in resposta  # NÃO oferece opção
```

### Test 6: GPT Não Recebe Profile
```python
def test_p1_2b_gpt_sem_profile():
    """P1.2B: GPT continua recebendo o mesmo contexto"""
    
    # GPT sem P1.2B
    slots_sem = chamar_gpt(mensagem, ctx_normal)
    
    # GPT com P1.2B (profile adicionado ao ctx)
    ctx_com_profile = ctx_normal.copy()
    ctx_com_profile["clienteprofile_contexto_motor"] = {...}
    slots_com = chamar_gpt(mensagem, ctx_com_profile)
    
    # Validação: GPT extraiu IGUAL
    assert slots_sem == slots_com
    # (Profile está em ctx, mas não é passado ao prompt do GPT)
```

### Test 7: Re-engagement Não Acionado
```python
def test_p1_2b_sem_reengagement():
    """P1.2B: nenhuma oferta de re-engagement"""
    
    ultima_contato = "2026-05-10"  # 35 dias atrás (inativo)
    
    ctx = {
        "clienteprofile": {
            "historico": {"ultima_contato": ultima_contato}
        }
    }
    
    # Executar P1.2B
    ctx["clienteprofile_contexto_motor"] = extrair_contexto(ctx["clienteprofile"])
    
    # Validação: contexto marca como inativo mas NÃO oferece promoção
    assert ctx["clienteprofile_contexto_motor"]["cliente_inativo_dias"] == 35
    assert "promoção" not in resposta  # NÃO oferecida em P1.2B
    assert "desconto" not in resposta  # NÃO oferecido em P1.2B
```

### Test 8: Resposta Antes == Resposta Depois
```python
def test_p1_2b_resposta_identica():
    """P1.2B: resposta é EXATAMENTE igual"""
    
    # Simular fluxo ANTES de P1.2B
    resposta_antes = fluxo_agendamento_completo(user_id, mensagem)
    
    # Simular fluxo COM P1.2B
    resposta_depois = fluxo_agendamento_completo(user_id, mensagem)
    # (Profile carregado em P1.2A, contexto extraído em P1.2B)
    
    # Validação: IDÊNTICAS
    assert resposta_antes == resposta_depois
```

---

## 🚫 REGRA INVIOLÁVEL

```
P1.2B = Motor lê e entende contexto (ZERO alteração de resposta)
P1.3 = Motor usa contexto para sugerir COM CONFIRMAÇÃO
```

### O Que Muda em P1.2B
```
✅ Adiciona ctx["clienteprofile_contexto_motor"]
✅ Adiciona logs informativos
✅ Adiciona contexto interno (flags para P1.3)
```

### O Que NÃO Muda em P1.2B
```
❌ Resposta ao cliente (idêntica)
❌ Draft agendamento (idêntico)
❌ Fluxo de confirmação (idêntico)
❌ Criação de evento (idêntica)
❌ Prompt do GPT (idêntico)
❌ Número de perguntas (idêntico)
```

---

## 📋 Checklist de Implementação P1.2B

Antes de iniciar P1.2B, garantir:

- [ ] Profile carregado em P1.2A (já feito ✅)
- [ ] ctx["clienteprofile_contexto_motor"] é criado após profile
- [ ] Contexto é extraído do profile (5 campos)
- [ ] Estrutura interna é criada corretamente
- [ ] Logs informativos são adicionados
- [ ] Nenhuma sugestão é oferecida
- [ ] Nenhuma resposta é alterada
- [ ] Nenhum passo é pulado
- [ ] Draft permanece igual
- [ ] GPT recebe contexto igual
- [ ] Todos os 8 testes passam
- [ ] Resposta antes == resposta depois

---

**Micro-Spec Status:** ✅ PRONTA PARA IMPLEMENTAÇÃO  
**Data:** 2026-06-14  
**Próximo:** P1.2B Implementation (Motor lê contexto, sem alterar comportamento)
