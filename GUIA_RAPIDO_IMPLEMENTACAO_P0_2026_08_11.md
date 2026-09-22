# GUIA RÁPIDO — IMPLEMENTAÇÃO P0 REAGENDAMENTO
**Para:** Desenvolvedor começando implementação  
**Tempo de leitura:** 10 min  
**Resultado:** Entender exatamente o que fazer

---

## 1. ANTES DE QUALQUER LINHA DE CÓDIGO

Leia NESTA ORDEM:

1. **CONTRATO_MOTOR_REAGENDAMENTO_2026_08_11.md** (15 min)
   - Entender o que motor garante
   - Entender como chamar motor CORRETAMENTE
   - Validar erros comuns

2. **PLANO_P0_REAGENDAMENTO_CONVERSACIONAL_REVISADO_2026_08_11.md** (30 min)
   - Arquitetura (3 camadas)
   - 3 Atores
   - 7 Máquina de estados
   - Fluxo conversacional

3. **REVISAO_P0_STATUS_2026_08_11.md** (10 min)
   - Resumo executivo
   - Mudanças vs versão anterior
   - Cronograma

---

## 2. ARQUITETURA EM 30 SEGUNDOS

```
Cliente fala
  ↓
[CAMADA 1] GPT interpreta e estrutura
  └─ Retorna: {intenção, cliente, data, hora, confiança}
  ↓
[CAMADA 2] Router valida permissão + orquestra
  └─ Valida: tenant_id, actor_id, role
  └─ Gerencia: estado_fluxo (7 estados)
  ↓
[CAMADA 3] Motor executa
  └─ verificar_conflito_e_sugestoes_profissional()
  └─ alterar_agendamento() (preserva event_id, registra histórico)
```

**Crítico:** Cada camada faz APENAS seu trabalho.

---

## 3. 3 ATORES

| Ator | Pode fazer | Validação |
|------|-----------|-----------|
| **Cliente** | Alterar seus próprios eventos | `evento.cliente_id == actor_id` |
| **Dono** | Alterar eventos do seu tenant | `evento.tenant_id == actor_tenant_id` |
| **Profissional** | Alterar onde trabalha | `evento.profissional == actor_id` |

**Implementação:** Checar `role` e `actor_id` ANTES de chamar motor.

---

## 4. 7 MÁQUINA DE ESTADOS

```
1. REAGENDAMENTO_INICIADO
   ├─ Armazenar: intenção, actor_id, tenant_id
   └─ Próximo: IDENTIFICANDO_EVENTO

2. IDENTIFICANDO_EVENTO
   ├─ Listar eventos (cliente vê seus, dono vê todos do tenant)
   └─ Próximo: AGUARDANDO_NOVO_HORARIO

3. AGUARDANDO_NOVO_HORARIO
   ├─ GPT interpreta data/hora
   ├─ Guardar em draft_reagendamento
   └─ Próximo: VALIDANDO_DISPONIBILIDADE

4. VALIDANDO_DISPONIBILIDADE (automático)
   ├─ Chamar motor: verificar_conflito_e_sugestoes_profissional()
   ├─ ⚠️ CRÍTICO: Passar event_id (ignora evento sendo alterado)
   └─ Próximo: (se sem conflito → AGUARDANDO_CONFIRMACAO)
               (se com conflito → AGUARDANDO_ESCOLHA_ALTERNATIVA)

5. AGUARDANDO_ESCOLHA_ALTERNATIVA
   ├─ Cliente/dono escolhe entre sugestões
   ├─ Revalidar alternativa
   └─ Próximo: AGUARDANDO_CONFIRMACAO

6. AGUARDANDO_CONFIRMACAO
   ├─ Pedir "Confirma?"
   ├─ Se "Sim" → AGENDAMENTO_REAGENDANDO
   └─ Se "Não" → IDLE (sem alterar)

7. AGENDAMENTO_REAGENDANDO (automático)
   ├─ Chamar: alterar_agendamento()
   ├─ ✅ Validações defensivas já estão no motor
   └─ Próximo: CONCLUIDO → IDLE
```

---

## 5. CONTEXTO MÍNIMO (O QUE GUARDAR)

```python
contexto = {
    # Estado
    "estado_fluxo": "AGUARDANDO_NOVO_HORARIO",
    
    # Atores
    "actor_id": user_id,
    "tenant_id": dono_id,
    "role": "cliente",  # ou "dono" ou "profissional"
    
    # Evento sendo alterado
    "evento_id": "EVT123",
    "agendamento_anterior": {
        "data": "2026-08-14",
        "hora": "14:30",
        "profissional": "Carla",
        "duracao_minutos": 30
    },
    
    # Novo horário (draft)
    "draft_reagendamento": {
        "data": "2026-08-15",
        "hora": "17:00",
        "duracao_minutos": 30
    },
    
    # Conflito (se houver)
    "conflito": False,
    "sugestoes": []
}
```

**Não guardar:** Catálogo, lista completa de eventos, agenda.

---

## 6. CHAMAR MOTOR CORRETAMENTE

### ✅ Correto (FAÇA ASSIM)

```python
# Etapa 1: Validar permissão (antes do motor!)
if role == "cliente":
    if evento["cliente_id"] != actor_id:
        await bot.reply("Só pode alterar seus próprios eventos")
        return

# Etapa 2: Chamar motor com event_id
validacao = await verificar_conflito_e_sugestoes_profissional(
    user_id=dono_id,
    data=nova_data,
    hora_inicio=nova_hora,
    duracao_min=30,
    profissional="Carla",
    servico="Manicure",
    event_id="EVT123"  # ← CRÍTICO! Ignora evento sendo alterado
)

# Etapa 3: Validar resultado
if validacao["conflito"]:
    # Oferecer alternativas
    bot.reply(f"Ocupado. Tenho: {validacao['sugestoes']}")
else:
    # Pedir confirmação
    bot.reply("Confirma?")

# Etapa 4: Só chamar alterar_agendamento() se confirmado
if confirmacao == "Sim":
    resultado = await alterar_agendamento(
        event_id="EVT123",
        nova_data=nova_data,
        nova_hora_inicio=nova_hora,
        tenant_id=dono_id
    )
    
    if resultado["ok"]:
        bot.reply("Pronto! Alterado.")
        # Validar que evento_id é MESMO
        assert resultado["evento_id"] == "EVT123"
```

### ❌ Incorreto (NÃO FAÇA)

```python
# ❌ Não passar event_id
validacao = await verificar_conflito_e_sugestoes_profissional(
    ...,
    # FALTA: event_id="EVT123"
)
# Resultado: Detecta conflito consigo mesmo (falso positivo)

# ❌ Não respeitar conflito
if validacao["conflito"]:
    # Alterar mesmo com conflito!
    resultado = await alterar_agendamento(...)  # ERRADO!

# ❌ Não pedir confirmação
resultado = await alterar_agendamento(...)  # Sem perguntar ao cliente!

# ❌ Duplicar lógica
def meu_verificar_conflito():
    # Reimplementar motor
    ...
validacao = meu_verificar_conflito()  # Versão errada!
```

---

## 7. DETECÇÃO DE INTENÇÃO

### Heurística (Rápida)

```python
def eh_heuristica_reagendamento(mensagem: str) -> bool:
    t = normalizar(mensagem)
    palavras = ["reagendar", "remarcar", "mudar horário", "trocar dia"]
    return any(p in t for p in palavras)
```

**Cobertura:** ~70% dos casos  
**Custo:** 0 (sem GPT)

### Fallback GPT (Se heurística falha)

```python
if not eh_heuristica_reagendamento(mensagem):
    # Chamar GPT
    prompt = f"""
    Mensagem: "{mensagem}"
    
    Isso é reagendamento (mudar horário)?
    Responda APENAS JSON:
    {{
        "eh_reagendamento": true|false,
        "confianca": 0.0-1.0
    }}
    """
    
    resultado = await chamar_gpt(prompt)
    
    if resultado.get("eh_reagendamento") and resultado.get("confianca", 0) >= 0.7:
        # É reagendamento!
        intenção = "REAGENDAR"
    else:
        # Não é, deixar para roteador normal
        return None
```

**Benefício:** Reconhece qualquer linguagem natural sem lista infinita.

---

## 8. FLUXO REAL (EXEMPLO)

```
Cliente: "Quero mudar meu horário de manicure"
  ↓ [Heurística detecta "mudar horário"]
  ↓
Bot: "Qual manicure? 1. Terça 14h  2. Sexta 10h"
  ↓
[Estado: IDENTIFICANDO_EVENTO]
Cliente: "1"
  ↓
Bot: "Para qual horário?"
  ↓
[Estado: AGUARDANDO_NOVO_HORARIO]
Cliente: "Sexta às 17h"
  ↓ [GPT interpreta: data=sexta→2026-08-15, hora=17:00]
  ↓ [Estado automático: VALIDANDO_DISPONIBILIDADE]
  ↓ [Motor verifica]
  ↓
Motor: SEM CONFLITO
  ↓
[Estado: AGUARDANDO_CONFIRMACAO]
Bot: "Confirma sexta às 17h?"
  ↓
Cliente: "Sim"
  ↓ [Estado: AGENDAMENTO_REAGENDANDO]
  ↓ [Chamar alterar_agendamento()]
  ↓
Motor: Alterado ✅
  └─ evento_id = "EVT123" (MESMO)
  └─ histórico registrado
  └─ status = "confirmado"
  ↓
Bot: "Pronto! Manicure movida para sexta às 17h."
  ↓
[Limpar contexto, voltar IDLE]
```

---

## 9. TESTES QUE VALIDAM

**Mínimo de testes:**

| Grupo | Cenários |
|-------|----------|
| Cliente | 5 (1 evento, N eventos, sem conflito, com conflito, recusa) |
| Dono | 4 (altera cliente, cross-tenant falha, N clientes, tudo junto) |
| Profissional | 2 (seu escopo, fora do escopo) |
| Motor | 4 (event_id preservado, histórico, conflito não altera, atômico) |
| Arquitetura | 3 (GPT interpreta, router orquestra, tenant isolado) |
| Regressão | 1 (P0 174/174 + P1 42/42 continuam PASS) |

**Total:** 15+ cenários

---

## 10. ERROS COMUNS (EVITAR)

| Erro | Causa | Solução |
|------|-------|--------|
| Conflito falso positivo | Não passar event_id | Sempre passar `event_id="EVT123"` |
| Evento criado novo | Não preservar event_id | Validar `resultado["evento_id"] == "EVT123"` |
| Sem histórico | Não usar `atualizar_com_operacoes_atomicas()` | Motor já faz, confiar nele |
| Permissão ignorada | Validar depois do motor | Validar ANTES de chamar motor |
| Cross-tenant | Não validar tenant_id | Sempre: `evento.tenant_id == actor_tenant_id` |
| Sem confirmação | Alterar sem pedir | Sempre: "Confirma?" antes de alterar |
| GPT executa motor | Delegação errada | GPT apenas estrutura, motor executa |
| Lógica no router | Orquestração virou lógica | Router apenas chama motor, não contém lógica |

---

## 11. CHECKLIST ANTES DE CHAMAR alterar_agendamento()

```python
# Antes de chamar motor, validar:

[ ] event_id está definido (string válida)
[ ] nova_data está em ISO format "YYYY-MM-DD"
[ ] nova_hora_inicio está em formato "HH:MM"
[ ] duracao_minutos é número > 0
[ ] tenant_id está resolvido
[ ] actor_id está definido
[ ] Permissão foi validada (cliente/dono/profissional)
[ ] Conflito foi verificado
[ ] Resultado foi sem conflito OU alternativa foi escolhida
[ ] Cliente confirmou com "Sim"
[ ] Contexto tem evento_id e agendamento_anterior
```

Se qualquer item falha → **NÃO chamar motor, responder ao usuário**.

---

## 12. LEMBRETE CRÍTICO

```
⚠️  Três coisas não podem ser erradas:

1. Passar event_id ao motor
   └─ Se não passar, motor detecta conflito consigo mesmo

2. Validar permissão ANTES de chamar motor
   └─ Se validar depois, cliente pode alterar evento de outro

3. Pedir confirmação antes de alterar
   └─ Se não pedir, cliente não tem chance de recusar
```

---

## 13. QUANDO ESTIVER PRESO

Consulte:

| Dúvida | Seção | Arquivo |
|--------|-------|---------|
| "Como chamar motor?" | "Como Router/Bot Usa Motor" | CONTRATO_MOTOR |
| "Quais são os 7 estados?" | "Máquina de Estados" | PLANO_P0_REVISADO |
| "3 atores como?" | "Atores Suportados" | PLANO_P0_REVISADO |
| "Conflito como?" | "Conflito" | PLANO_P0_REVISADO |
| "Contexto o quê?" | "Contexto Temporário" | PLANO_P0_REVISADO |
| "Fluxo completo?" | "Fluxo Conversacional Completo" | PLANO_P0_REVISADO |

---

## 14. ORDEM DE IMPLEMENTAÇÃO

1. Detecção GPT (router/principal_router.py)
2. 7 Estados (handlers/bot.py)
3. Testes E2E (TESTE_P0_REAGENDAMENTO_E2E_v2.py)
4. Regressão (validar P0 174/174 + P1 42/42)

---

**Status:** Pronto para implementação. Basta seguir este guia + documentação detalhada.

**Tempo estimado:** 8-12h (inclui testes e regressão).

**Qualidade:** Arquitetura sólida, sem débito técnico.
