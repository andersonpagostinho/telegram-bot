# PLANO P0: REAGENDAMENTO CONVERSACIONAL
**Data:** 2026-08-11  
**Abordagem:** Estender arquitetura EXISTENTE (não criar novos handlers)  
**Status:** 📋 **PLANO DETALHADO**

---

## ARQUITETURA EXISTENTE (O que usar)

### 1. Router Principal
```
router/principal_router.py
├── eh_gatilho_agendar()        ✅ Detecta "agendar"
├── eh_confirmacao()            ✅ Detecta "sim/confirmar"
├── eh_desistencia_fluxo()      ✅ Detecta "não/cancelar"
├── eh_continuacao_de_agendamento()  ← PRECISA DE REAGENDAMENTO
└── [ADICIONAR] eh_gatilho_reagendamento()  ❌ CRIAR
```

### 2. Orquestrador Central
```
handlers/bot.py
├── Detecta gatilho via router
├── Carrega contexto_temporario (dono_id, user_id)
├── Verifica estado_fluxo
├── Roteio a handler apropriado
└── Gerencia confirmação/desistência
```

### 3. Estado Minimalista
```
contexto_temporario = {
    "estado_fluxo": "aguardando_novo_horario_reagendamento",
    "draft_reagendamento": {
        "evento_id": "EVT123",
        "nova_data": "2026-08-12",
        "nova_hora": "17:00"
    },
    "ultima_acao": "aguardando_novo_horario"
}
```

### 4. Motor Determinístico
```
verificar_conflito_e_sugestoes_profissional()
└── Já existe, reutilizar

alterar_agendamento()
└── Já existe, reutilizar
```

---

## PLANO: 3 IMPLEMENTAÇÕES MINIMALISTAS

### PASSO 1: Adicionar Detector de Intenção
**Arquivo:** `router/principal_router.py`  
**Mudança:** +15 linhas

```python
def eh_gatilho_reagendamento(txt: str) -> bool:
    """
    Detecta intenção de reagendamento
    
    Exemplos:
    - "Quero mudar meu horário"
    - "Gostaria de reagendar"
    - "Posso alterar meu agendamento?"
    - "Quero trocar de dia"
    - "Adiar meu compromisso"
    """
    palavras_chave = [
        "reagendar", "remarcar", "mudar horário",
        "alterar horário", "trocar horário", "trocar dia",
        "adiantar", "adiar", "postergar", "alterar data",
        "mudança de horário", "outro horário", "horário diferente"
    ]
    
    txt_norm = unidecode(txt.lower().strip())
    return any(palavra in txt_norm for palavra in palavras_chave)
```

---

### PASSO 2: Listar Agendamentos (Integrado em bot.py)
**Arquivo:** `handlers/bot.py`  
**Mudança:** +40 linhas (não novo handler, estender orquestrador)

```python
# Após detectar eh_gatilho_reagendamento() no router:

if eh_gatilho_reagendamento(mensagem):
    # Estado 1: Listar agendamentos do cliente
    agendamentos = await buscar_agendamentos_cliente(user_id, dono_id)
    
    if not agendamentos:
        await update.message.reply_text(
            "Você não tem agendamentos para alterar."
        )
        raise ApplicationHandlerStop
    
    # Formatar lista
    opcoes_texto = "\n".join([
        f"{i+1}. {agendamento['servico']} - "
        f"{agendamento['data']} às {agendamento['hora']}"
        for i, agendamento in enumerate(agendamentos)
    ])
    
    # Guardar contexto
    contexto["estado_fluxo"] = "aguardando_escolha_agendamento_reagendamento"
    contexto["agendamentos_para_reagendar"] = agendamentos
    await salvar_contexto_temporario(dono_id, user_id, contexto)
    
    await update.message.reply_text(
        f"Qual deles você quer alterar?\n\n{opcoes_texto}"
    )
    raise ApplicationHandlerStop
```

---

### PASSO 3: Máquina de Estados (Estender bot.py)
**Arquivo:** `handlers/bot.py`  
**Mudança:** +120 linhas (estender fluxo existente)

```python
# Estado 1: Cliente escolhe qual agendamento alterar
if ctx.get("estado_fluxo") == "aguardando_escolha_agendamento_reagendamento":
    escolha = extrair_numero(mensagem)  # Reutilizar função existente
    
    if escolha is None or escolha > len(ctx["agendamentos_para_reagendar"]):
        await update.message.reply_text("Opção inválida. Escolha novamente.")
        raise ApplicationHandlerStop
    
    agendamento_selecionado = ctx["agendamentos_para_reagendar"][escolha - 1]
    
    contexto["evento_id"] = agendamento_selecionado["evento_id"]
    contexto["agendamento_anterior"] = agendamento_selecionado
    contexto["estado_fluxo"] = "aguardando_novo_horario_reagendamento"
    
    await salvar_contexto_temporario(dono_id, user_id, contexto)
    await update.message.reply_text(
        f"Para qual data e horário você quer mudar?\n"
        f"(Ex: 'quinta 17h' ou '2026-08-15 17:00')"
    )
    raise ApplicationHandlerStop

# Estado 2: Cliente escolhe novo horário
if ctx.get("estado_fluxo") == "aguardando_novo_horario_reagendamento":
    # Interpretar data/hora
    resultado_data = interpretar_data_e_hora(mensagem)
    
    if not resultado_data or "erro" in resultado_data:
        await update.message.reply_text(
            "Não entendi o horário. Tente novamente.\n"
            "(Ex: 'quinta 17h' ou '15 às 5 da tarde')"
        )
        raise ApplicationHandlerStop
    
    nova_data = resultado_data["data"]
    nova_hora = resultado_data["hora"]
    duracao = ctx["agendamento_anterior"]["duracao_minutos"]
    profissional = ctx["agendamento_anterior"]["profissional"]
    
    # Validar conflito via motor
    validacao = await verificar_conflito_e_sugestoes_profissional(
        user_id=dono_id,
        data=nova_data,
        hora_inicio=nova_hora,
        duracao_min=duracao,
        profissional=profissional,
        servico=ctx["agendamento_anterior"]["servico"],
        event_id=ctx["evento_id"]  # Ignora o evento sendo alterado
    )
    
    # Estado 3a: Sem conflito → confirmação
    if not validacao.get("conflito"):
        contexto["draft_reagendamento"] = {
            "evento_id": ctx["evento_id"],
            "nova_data": nova_data,
            "nova_hora": nova_hora,
            "duracao_minutos": duracao
        }
        contexto["estado_fluxo"] = "aguardando_confirmacao_reagendamento"
        await salvar_contexto_temporario(dono_id, user_id, contexto)
        
        await update.message.reply_text(
            f"Certo! Vou mudar seu {ctx['agendamento_anterior']['servico']} "
            f"para {nova_data} às {nova_hora}.\n"
            f"Confirma? (Sim/Não)"
        )
        raise ApplicationHandlerStop
    
    # Estado 3b: Conflito → oferece alternativas
    else:
        sugestoes = validacao.get("sugestoes", [])
        sugestoes_texto = "\n".join([
            f"{i+1}. {s}" for i, s in enumerate(sugestoes[:3])
        ])
        
        contexto["estado_fluxo"] = "aguardando_escolha_horario_reagendamento"
        contexto["sugestoes"] = sugestoes
        contexto["draft_reagendamento"] = {
            "evento_id": ctx["evento_id"],
            "duracao_minutos": duracao,
            "original": ctx["agendamento_anterior"]
        }
        await salvar_contexto_temporario(dono_id, user_id, contexto)
        
        await update.message.reply_text(
            f"Esse horário está ocupado. Tenho essas opções:\n\n{sugestoes_texto}\n\n"
            f"Qual você prefere? (1, 2 ou 3)"
        )
        raise ApplicationHandlerStop

# Estado 4: Cliente escolhe entre alternativas
if ctx.get("estado_fluxo") == "aguardando_escolha_horario_reagendamento":
    escolha = extrair_numero(mensagem)
    sugestoes = ctx.get("sugestoes", [])
    
    if escolha is None or escolha > len(sugestoes):
        await update.message.reply_text("Opção inválida. Escolha novamente.")
        raise ApplicationHandlerStop
    
    horario_selecionado = sugestoes[escolha - 1]  # Ex: "16:30 - 17:30"
    nova_hora = horario_selecionado.split(" - ")[0]
    
    contexto["draft_reagendamento"]["nova_hora"] = nova_hora
    contexto["estado_fluxo"] = "aguardando_confirmacao_reagendamento"
    await salvar_contexto_temporario(dono_id, user_id, contexto)
    
    await update.message.reply_text(
        f"Perfeito! Vou mudar para {nova_hora}.\n"
        f"Confirma? (Sim/Não)"
    )
    raise ApplicationHandlerStop

# Estado 5: Confirmação
if ctx.get("estado_fluxo") == "aguardando_confirmacao_reagendamento":
    # Usa eh_confirmacao() existente
    if eh_confirmacao(mensagem):
        draft = ctx.get("draft_reagendamento", {})
        
        resultado = await alterar_agendamento(
            user_id=user_id,
            event_id=draft["evento_id"],
            nova_data=draft["nova_data"],
            nova_hora_inicio=draft["nova_hora"],
            nova_duracao_minutos=draft.get("duracao_minutos"),
            tenant_id=dono_id
        )
        
        if resultado.get("ok"):
            # Limpar contexto
            await limpar_contexto_agendamento(user_id, tenant_id=dono_id)
            
            await update.message.reply_text(
                f"✅ Pronto! Seu agendamento foi alterado para "
                f"{resultado['detalhes']['data']} às {resultado['detalhes']['hora_inicio']}."
            )
        else:
            await update.message.reply_text(
                f"❌ Não consegui alterar: {resultado.get('motivo')}"
            )
        
        raise ApplicationHandlerStop
    
    # Desistência
    if eh_desistencia_fluxo(mensagem):
        await limpar_contexto_agendamento(user_id, tenant_id=dono_id)
        await update.message.reply_text(
            "Certo, não vou alterar nada. Quando quiser, é só me chamar."
        )
        raise ApplicationHandlerStop
```

---

## PASSO 4: Teste Conversacional E2E
**Arquivo:** `TESTE_FLUXO_REAGENDAMENTO_E2E_2026_08_11.py` (NOVO)

```python
"""
Teste conversacional completo de reagendamento

Simula o diálogo:
1. Cliente pede para reagendar
2. Bot lista agendamentos
3. Cliente escolhe qual alterar
4. Bot pergunta novo horário
5. Motor valida disponibilidade
6. Bot oferece alternativas (se conflito) ou pede confirmação (se livre)
7. Cliente confirma
8. Motor altera evento com histórico
9. Bot confirma e limpa contexto
"""

async def testar_fluxo_reagendamento_completo():
    # Criar agendamento base
    evento_base = await criar_agendamento_teste(...)
    
    # Simular mensagem 1: "Quero mudar meu horário"
    resultado1 = await simular_mensagem("Quero mudar meu horário de quinta")
    assert "Qual deles" in resultado1  # Bot lista agendamentos
    
    # Simular mensagem 2: Cliente escolhe
    resultado2 = await simular_mensagem("O primeiro")
    assert "Para qual horário" in resultado2  # Bot pergunta novo horário
    
    # Simular mensagem 3: Cliente tenta horário ocupado
    resultado3 = await simular_mensagem("17 horas")
    # Motor detecta conflito (se houver)
    # Bot oferece alternativas
    
    # Simular mensagem 4: Cliente escolhe alternativa
    resultado4 = await simular_mensagem("2")
    assert "Confirma" in resultado4  # Bot pede confirmação
    
    # Simular mensagem 5: Cliente confirma
    resultado5 = await simular_mensagem("Sim")
    assert "Pronto" in resultado5  # Sucesso!
    
    # Validar evento foi alterado
    evento_alterado = await buscar_evento(evento_base["evento_id"])
    assert evento_alterado["data"] == nova_data
    assert evento_alterado["hora_inicio"] == nova_hora
    assert len(evento_alterado.get("historico_alteracoes", [])) > 0
    
    print("[SUCESSO] Fluxo conversacional completo validado")
```

---

## RESUMO: 3 Implementações Minimalistas

| Item | Arquivo | Linhas | Tipo |
|------|---------|--------|------|
| 1. Detector | router/principal_router.py | +15 | Nova função |
| 2. Orquestração | handlers/bot.py | +160 | Extensão (NOT novo handler) |
| 3. Teste E2E | TESTE_FLUXO...py | 60 | Novo teste |

**Reutiliza:**
- ✅ Máquina de estados existente
- ✅ Carregamento de contexto (bot.py)
- ✅ Motor de conflito (verificar_conflito_e_sugestoes_profissional)
- ✅ Motor de persistência (alterar_agendamento)
- ✅ Detector de confirmação/desistência

**Não cria:**
- ❌ reagendamento_handler.py (novo handler isolado)
- ❌ Duplicação de estados
- ❌ Lógica espalhada

---

## DEFINIÇÃO DE PRONTO (GATE FINAL)

```
Cliente: "Quero mudar meu horário"
   ↓ [Bot lista agendamentos]
Cliente: "O das 15h"
   ↓ [Bot pergunta novo horário]
Cliente: "17h"
   ↓ [Motor valida]
   ├─ Se livre: Bot pede confirmação
   └─ Se conflito: Bot oferece alternativas
Cliente: "Sim" ou escolhe alternativa
   ↓ [alterar_agendamento()]
Bot: "Pronto! Alterado com histórico"

✅ Evento atualizado
✅ Histórico registrado
✅ Contexto limpo
✅ Notificação enviada (futuro)
```

---

## PRÓXIMOS PASSOS APÓS P0

1. Integrar notificações (Telegram, email)
2. Testar com múltiplos conflitos
3. Testar com lista de espera
4. Integrar com Dashboard/REBOOK
5. Adicionar suporte a WhatsApp

---

**Princípio:** Estender, não duplicar. Reutilizar arquitetura existente.

