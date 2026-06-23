# LOTE 6A — RECLASSIFICAÇÃO CENÁRIO 06 PÓS SESSION V2

**Data:** 2026-06-22  
**Escopo:** Auditoria detalhada de cenário 06 (confirmação embutida)  
**Objetivo:** Mapear exatamente onde falha agora que session v2 está operacional  
**Metodologia:** Análise de logs sem aplicação de patch

---

## TABELA DE PROGRESSÃO

| Etapa | Esperado | Obtido | Status | Evidência |
|-------|----------|--------|--------|-----------|
| **1. Setup: sessão v2 criada** | confirmacao_pendente=True | ✓ | ✅ PASS | Linha 429: `[OK] Dados salvos em .../Sessoes/whatsapp:55119999006` |
| **2. Contexto legado criado** | guard_tenant=tenant_id | ✓ | ✅ PASS | Linha 436: `[OK] Dados salvos em .../MemoriaTemporaria/contexto` |
| **3. Mensagem enviada** | "Pode deixar..." | ✓ | ✅ PASS | Linha 452: `[ADMIN] entrada \| texto='Pode deixar...'` |
| **4. Confirmação detectada** | LOTE_3E_CONFIRMACAO | ✓ | ✅ PASS | Linha 444: `[LOTE_3E_CONFIRMACAO_EARLY] Confirmação detectada` |
| **5. Intenção classificada** | confirmacao_agendamento | confirmacao_agendamento | ✅ PASS | Linha 457: `'intencao_conversacional': 'confirmacao_agendamento'` |
| **6. Handler chamado** | criar_evento | criar_evento | ✅ PASS | Linha 475: `🪵 Ação recebida: 'criar_evento'` |
| **7. Dados recebidos** | profissional, servico, data_hora | ✓ | ✅ PASS | Linha 481-486: Dados completos no payload |
| **8. Sessão v2 carregada** | path_novo | ✓ | ✅ PASS | Linha 491: `[DIAG] [LOAD SESSAO v2] path=...Sessoes/...` |
| **9. Gate de confirmação** | confirmado=True | ✓ | ✅ PASS | Linha 492: `⚙️ Confirmado pelo chamador (confirmado=True)` |
| **10. Configuração de salão** | cfg_salao com agenda_padrao | **VAZIO** | ❌ FAIL | Linha 493: `cfg_salao keys=[]` |
| **11. Validação de janela** | aberto=True | aberto=False | ❌ FAIL | Linha 497: `'aberto': False, 'origem': 'agenda_padrao_salao'` |
| **12. add_evento_por_gpt** | Não chamada | Não chamada | ⚠️ N/A | Bloqueada antes de add_evento_por_gpt |
| **13. verificar_pagamento** | Não chamada | Não chamada | ⚠️ N/A | Bloqueada antes de add_evento_por_gpt |
| **14. salvar_evento** | Não chamada | Não chamada | ⚠️ N/A | Bloqueada antes de salvar_evento |
| **15. Evento criado** | evento_id em estado | Não | ❌ FAIL | Teste marca `confirmacao_pendente=False` ao final |
| **16. Resposta enviada** | Texto ao usuário | Mock enviado | ⚠️ N/A | MockContext não verifica resposta |

---

## ACHADO CRÍTICO

### 🔴 PONTO EXATO DE FALHA

**Linha 493-497 dos logs:**

```
🧪 [JANELA] cfg_salao keys=[]
🧪 [JANELA] agenda_padrao_salao={}
🧪 [JANELA] excecoes_salao={}
🧪 [JANELA] regra_salao_final={'aberto': False, ...}
🧪 AGENDA JANELA REAL: {'aberto': False, ...}
[FAIL] 06. Confirmação não foi processada
```

**Causa:** Configuração de agenda do salão não foi criada no setup.

### Rastreamento de Causa

1. **add_evento_por_gpt** chama `obter_janela_funcionamento(dono_id, data)`  
   - Busca em: `Clientes/{dono_id}/configuracao/agenda_funcionamento`
   - Esperado: caminho com configuração de agenda

2. **Setup do cenário 06** cria apenas:
   - `Clientes/{tenant_id}/Configuracao/info` (maiúscula)
   - Não cria: `Clientes/{tenant_id}/configuracao/agenda_funcionamento`

3. **Resultado:** `cfg_salao = {}` (vazio)  
   - `agenda_padrao_salao = {}` (vazio)
   - `aberto = False` (default quando vazio)

4. **Validação falha:**
   ```python
   if not aberto:
       return {}  # Bloqueia criação
   ```

---

## CAMADA DE ORIGEM

| Camada | Status | Evidência |
|--------|--------|-----------|
| **1. Interpretação (GPT)** | ✅ OK | Confirmação detectada, intenção correta |
| **2. Contexto (sessão)** | ✅ OK | Session v2 carregada, contexto disponível |
| **3. Fluxo (roteamento)** | ✅ OK | Ação criar_evento recebida e roteada |
| **4. Regra de negócio** | ❌ FALHA | Agenda do salão não existe → bloqueia |
| **5. Persistência** | ⚠️ N/A | Nunca chega (bloqueado em camada 4) |

---

## CLASSIFICAÇÃO FINAL

### 🔴 TIPO: **E — Expectativa do teste incorreta**

**Motivo:**

O teste foi criado com setup INCOMPLETO. A sequência é correta:

```
✅ Confirmação detectada
✅ Intenção correcta
✅ Handler chamado
✅ Dados completos
✅ Session v2 carregado
✅ Gate de confirmação pulado
❌ Agenda do salão não criada (TESTE NAO SETUP)
```

O produto **funciona corretamente** ao bloquear criação sem configuração de agenda. O teste **não configura a agenda**.

---

## NÃO É

- ❌ **A** (produto falha antes de criar) — Produto bloqueia corretamente
- ❌ **B** (evento criado, teste não encontra) — Evento nunca criado (bloqueado)
- ❌ **C** (evento criado, resposta não enviada) — Evento nunca criado
- ❌ **D** (falha em agenda/lock) — Bloqueio é ANTES de agenda/lock
- ✅ **E** (expectativa do teste incorreta) — Setup não cria agenda_funcionamento

---

## PRÓXIMAS AÇÕES

**Para corrigir cenário 06:**

Não alterar produto. Não alterar teste (mantém como está para auditoria).

O cenário 06 falha porque o **setup é incompleto**, não porque o produto esteja quebrado.

**Evidência:** Session v2 validada com sucesso em P1 E2E (42/42 PASS) e P0 (174/174 PASS).

---

## CONCLUSÃO

**Session v2 está OPERACIONAL.**

Cenário 06 falha em ETAPA DE SETUP, não em session ou fluxo de confirmação.

Confirmação é **detectada, processada e roteada corretamente**. Bloqueio é **legítimo** (ausência de configuração).

**Status:** ✅ **INVESTIGAÇÃO CONCLUÍDA** — Causa isolada, classificada como E (expectativa de teste)

