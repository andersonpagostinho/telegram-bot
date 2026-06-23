# LOTE 3C — RASTREIO DE ORDEM DE BLOCOS P0

**Data:** 2026-06-22  
**Escopo:** Cenários 06 e 07 apenas  
**Status:** ✅ CAUSA RAIZ IDENTIFICADA

---

## DESCOBERTA CRÍTICA

**Bloco que intercepta:** CONSULTA INFORMATIVA IDLE (linha 3876-3908)

**Por que intercepta:** Após detectar confirmacao/negacao e salvar em LOTE_3B, o fluxo retorna à iteração principal. O contexto carregado tem `estado_fluxo=None`. O bloco CONSULTA_INFORMATIVA_IDLE entra quando `not estado_fluxo or estado_fluxo == "idle"` e retorna uma resposta genérica, impedindo que chegue ao P0_CONFIRMACAO.

---

## SEQUÊNCIA DE EXECUÇÃO MAPEADA

### Cenário 06: Confirmação Embutida

```
[TRACE_P0_ROUTE] step=LOTE_3B confirmacao_pendente=True estado_fluxo=None
    ↓ intencao setada como "confirmacao_agendamento"
[LOTE_3B_CONFIRMACAO] Detectada confirmação
    ↓ contexto salvo em Clientes/{tenant}/Sessoes/{actor}
[TRACE_P0_ROUTE] step=P0_CANCELAMENTO ... estado_fluxo=None
    ↓ estado_fluxo não é "aguardando_confirmacao_cancelamento", não entra
[TRACE_P0_ROUTE] step=HANDOFF intencao=confirmacao_agendamento ... estado_fluxo=None
    ↓ quer_falar_com_humano() retorna False, não entra
[TRACE_P0_ROUTE] step=CAMADA_ADMIN intencao=confirmacao_agendamento ... estado_fluxo=None
    ↓ Admin não processa, continua
[TRACE_P0_ROUTE] step=CONSULTA_INFORMATIVA_IDLE intencao=confirmacao_agendamento estado_fluxo=None
    ↓ ENTRA: "not None" é True
    ↓ responder_consulta_informativa("Pode deixar. Li tudo...")
    ↓ Retorna resposta genérica (ex: "Como posso ajudar?")
    ↓ NÃO TEM (tem_agendar and tem_temporal), então RETORNA
[TRACE_P0_RETURN] step=CONSULTA_INFORMATIVA_IDLE → NEVER REACHES P0_CONFIRMACAO

❌ P0_CONFIRMACAO NUNCA É ALCANÇADO
❌ Bloco de criação de evento não é acionado
❌ Mensagem "Confirmação não foi processada"
```

### Cenário 07: Negação Embutida

```
[TRACE_P0_ROUTE] step=LOTE_3B confirmacao_pendente=True estado_fluxo=None
    ↓ intencao setada como "negacao_confirmacao_agendamento"
[LOTE_3B_NEGACAO] Detectada negação
    ↓ contexto salvo em Clientes/{tenant}/Sessoes/{actor}
[TRACE_P0_ROUTE] step=P0_CANCELAMENTO ... estado_fluxo=None
    ↓ não entra
[TRACE_P0_ROUTE] step=HANDOFF intencao=negacao_confirmacao_agendamento ... estado_fluxo=None
    ↓ não entra
[TRACE_P0_ROUTE] step=CAMADA_ADMIN intencao=negacao_confirmacao_agendamento ... estado_fluxo=None
    ↓ continua
[TRACE_P0_ROUTE] step=CONSULTA_INFORMATIVA_IDLE intencao=negacao_confirmacao_agendamento estado_fluxo=None
    ↓ ENTRA: "not None" é True
    ↓ responder_consulta_informativa("Entendi tudo...")
    ↓ Retorna resposta genérica
    ↓ RETORNA

❌ P0_NEGACAO NUNCA É ALCANÇADO
❌ Contexto não é limpo
❌ Mensagem "Negação não foi processada"
```

---

## TABELA DE RASTREIO

| Cenário | Intencao Setada | Bloco Esperado | Bloco que Interceptou | Linha Exacta | Motivo Interceptação | Patch Recomendado |
|---------|-----------------|---------------|-----------------------|-------------|---------------------|-------------------|
| **06** | confirmacao_agendamento | P0_CONFIRMACAO (L4281) | CONSULTA_INFORMATIVA_IDLE (L3876) | 3908 | `return resposta_informativa` quando "pura consulta" | Adicionar guard: `if intencao_conversacional in ['confirmacao_agendamento', 'negacao_confirmacao_agendamento']: skip` |
| **07** | negacao_confirmacao_agendamento | P0_NEGACAO (L4378) | CONSULTA_INFORMATIVA_IDLE (L3876) | 3908 | `return resposta_informativa` quando "pura consulta" | Adicionar guard: mesmo acima |

---

## ANÁLISE DO BLOCO INTERCEPTOR

### Código Problemático (Linhas 3876-3908)

```python
if not estado_fluxo or estado_fluxo == "idle":
    # ...
    resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
    
    if resposta_informativa:
        tem_agendar = ...  # verifica keywords agendamento
        tem_temporal = ...  # verifica keywords tempo
        
        if tem_agendar and tem_temporal:
            # Híbrido: salva e continua
        else:
            # AQUI: Pura consulta — RETORNA
            return await _send_and_stop(context, user_id, resposta_informativa)
```

### Por que Quebra

1. **Cenário 06:** "Pode deixar. Li tudo. **Sim, pode confirmar** esse horário. Obrigado!"
   - `tem_agendar` = False (não menciona "agendar", "marcar", etc especificamente)
   - `tem_temporal` = False (não menciona data/hora futura)
   - Resultado: Classificado como "pura consulta" → RETORNA

2. **Cenário 07:** "Entendi tudo que você explicou, mas **não quero mais marcar** esse horário."
   - `tem_agendar` = True ("marcar")
   - `tem_temporal` = False (não menciona data futura)
   - Resultado: NÃO é "híbrido" → RETORNA

### Problema Estrutural

O bloco CONSULTA_INFORMATIVA_IDLE foi projetado para:
- Responder perguntas em contexto idle (ex: "qual é o horário de funcionamento?")
- Detectar hybrid (pergunta + agendamento simultâneos)

**MAS** não foi projetado para:
- Respeitar `intencao_conversacional` pré-determinada
- Permitir que P0_CONFIRMACAO/NEGACAO sobrescrevam "pura consulta"

---

## SOLUÇÃO RECOMENDADA

### Patch Mínimo (Guard)

**Locação:** Linha 3876

**ANTES:**
```python
if not estado_fluxo or estado_fluxo == "idle":
    # ... resto do código
```

**DEPOIS:**
```python
# 🔒 GUARD P0: Não interceptar se há confirmacao/negacao determinística setada
intencao_p0 = ctx.get("intencao_conversacional")
if intencao_p0 in ["confirmacao_agendamento", "negacao_confirmacao_agendamento"]:
    print(f"[GUARD_P0_CONSULTA] Pulando CONSULTA_INFORMATIVA_IDLE pois intencao_p0={intencao_p0} foi determinada", flush=True)
    # Continuar para P0_CONFIRMACAO ou P0_NEGACAO
else:
    if not estado_fluxo or estado_fluxo == "idle":
        # ... resto do código (consulta informativa)
```

**Impacto:** Nenhum — apenas pula o bloco quando há intenção P0 já determinada

---

## LOGS DE RASTREIO COMPLETOS

### Cenário 06 - Trace Completo

```
[SESSION_STORE] read_path=Clientes/teste_fluxo_p1_cc4e537b/Sessoes/whatsapp:55119999006 | same_path=True
[TRACE_P0_ROUTE] step=LOTE_3B line=3365 intencao=None confirmacao_pendente=True estado_fluxo=None
[LOTE_3B_CONFIRMACAO] Detectada confirmação
[DIAG] [SAVE SESSAO v2] path=Clientes/.../Sessoes/...
[TRACE_P0_ROUTE] step=P0_CANCELAMENTO intencao=confirmacao_agendamento confirmacao_pendente=True estado_fluxo=None
[TRACE_P0_ROUTE] step=HANDOFF intencao=confirmacao_agendamento confirmacao_pendente=True estado_fluxo=None
[TRACE_P0_ROUTE] step=CAMADA_ADMIN intencao=confirmacao_agendamento confirmacao_pendente=True estado_fluxo=None
[TRACE_P0_ROUTE] step=CONSULTA_INFORMATIVA_IDLE intencao=confirmacao_agendamento confirmacao_pendente=True estado_fluxo=None returned=False
[ANTES_CONSULTA_INFORMATIVA_IDLE] Resposta recebida: True
✅ [CONSULTA_INFORMATIVA_IDLE] tem_agendar=False | tem_temporal=False
[CONSULTA_INFORMATIVA_IDLE] Consulta pura — respondendo
[TRACE_P0_RETURN] step=CONSULTA_INFORMATIVA_IDLE reason=pura_consulta → RETURN LINE 3908
```

### Cenário 07 - Trace Completo

```
[SESSION_STORE] read_path=Clientes/teste_fluxo_p1_31f0a37d/Sessoes/whatsapp:55119999007 | same_path=True
[TRACE_P0_ROUTE] step=LOTE_3B intencao=None confirmacao_pendente=True estado_fluxo=None
[LOTE_3B_NEGACAO] Detectada negação
[DIAG] [SAVE SESSAO v2] path=Clientes/.../Sessoes/...
[TRACE_P0_ROUTE] step=P0_CANCELAMENTO intencao=negacao_confirmacao_agendamento confirmacao_pendente=True estado_fluxo=None
[TRACE_P0_ROUTE] step=HANDOFF intencao=negacao_confirmacao_agendamento confirmacao_pendente=True estado_fluxo=None
[TRACE_P0_ROUTE] step=CAMADA_ADMIN intencao=negacao_confirmacao_agendamento confirmacao_pendente=True estado_fluxo=None
[TRACE_P0_ROUTE] step=CONSULTA_INFORMATIVA_IDLE intencao=negacao_confirmacao_agendamento confirmacao_pendente=True estado_fluxo=None returned=False
[ANTES_CONSULTA_INFORMATIVA_IDLE] Resposta recebida: True
✅ [CONSULTA_INFORMATIVA_IDLE] tem_agendar=True | tem_temporal=False
[CONSULTA_INFORMATIVA_IDLE] Consulta pura — respondendo
[TRACE_P0_RETURN] step=CONSULTA_INFORMATIVA_IDLE reason=pura_consulta → RETURN LINE 3908
```

---

## INSTRUMENTAÇÃO REMOVIDA

**Logs de rastreio temporários adicionados para diagnóstico:**

```
[TRACE_P0_ROUTE] step=... line=... intencao=... confirmacao_pendente=... estado_fluxo=... returned=...
[TRACE_P0_RETURN] step=... line=... reason=... intencao=... estado_fluxo=...
```

**Status:** Ainda ativos (serão removidos após aprovação do patch)

---

## PRÓXIMOS PASSOS

1. ✅ **Rastreio concluído** — Causa raiz identificada com 100% certeza
2. ⏳ **Aguardando aprovação** — Patch guard está pronto para aplicação mínima
3. ⏳ **Aplicar patch** — Uma linha de guard antes do bloco CONSULTA_INFORMATIVA_IDLE
4. ⏳ **Remover logs** — Remover instrumentação temporária de rastreio
5. ⏳ **Re-testar P1** — Validar que cenários 06 e 07 passam

---

**Relatório gerado:** 2026-06-22T20:52:00Z  
**Status:** Diagnóstico 100% completo. Pronto para patch.
