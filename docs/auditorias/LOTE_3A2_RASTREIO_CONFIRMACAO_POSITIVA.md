# LOTE 3A.2 — INVESTIGAÇÃO: CONFIRMAÇÃO POSITIVA EMBUTIDA (CENÁRIO 06)

**Data:** 2026-06-22  
**Escopo:** Cenário 06 apenas - Confirmação embutida em parágrafo  
**Objetivo:** Rastrear qual bloco intercepta a mensagem antes do bloco de confirmação  

---

## DESCOBERTA CRÍTICA

O cenário 07 (negação) falha por uma razão diferente: **o teste está salvando em local errado**.

- **Teste salva em:** `Clientes/{tenant_id}/Sessoes/{actor_id}`
- **Router carrega de:** `Clientes/{actor_id}/MemoriaTemporaria/contexto`

Esses são dois paths distintos! O campo `confirmacao_pendente` em Sessões não é visto pelo router.

---

## ANÁLISE DO CENÁRIO 06

**Mensagem:** `"Pode deixar. Li tudo. Sim, pode confirmar esse horário. Obrigado!"`

**Função eh_confirmacao():** Retorna TRUE ✓

**Função eh_confirmacao_pendente_ativa(ctx):** Deveria retornar TRUE se contexto foi carregado

**Blocos Que Podem Interceptar (antes da linha 4475):**

| Linha | Bloco | Condicao | Risco |
|-------|-------|----------|-------|
| 3410+ | Cancelamento | estado_fluxo == aguardando_confirmacao_cancelamento | Baixo |
| 3650+ | Identidade/Onboarding | novo user ou sem onboarding | Médio |
| 4144+ | Consulta Informativa | eh_consulta(texto) | Alto |
| 4408+ | Negação/Interpretador | intencao == negacao | Médio |
| **4475** | **Confirmação** | **eh_confirmacao()** | **AQUI DEVERIA ENTRAR** |

---

## HIPÓTESE PRINCIPAL

**O contexto provavelmente não é carregado como `aguardando_confirmacao_agendamento=True`**

Porque:
1. `eh_confirmacao_pendente_ativa()` verifica `ctx.get("aguardando_confirmacao_agendamento")`
2. Se esse campo não está definido no contexto carregado, a função retorna False
3. A condição na linha 4475 falha
4. O bloco não é ativado

---

## VERIFICAÇÃO NECESSÁRIA

Para confirmar essa hipótese, seria preciso:

1. **Adicionar logs temporários** em `roteador_principal()` logo após carregar contexto:
   ```python
   ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}
   print(f"[DEBUG_06] contexto carregado: {ctx.get('aguardando_confirmacao_agendamento')}")
   print(f"[DEBUG_06] eh_confirmacao_pendente_ativa(ctx): {eh_confirmacao_pendente_ativa(ctx)}")
   ```

2. **Adicionar logs antes do bloco 4475:**
   ```python
   print(f"[DEBUG_06_BLOCO] Verificando confirmacao: pendente={eh_confirmacao_pendente_ativa(ctx)} | confirmacao={eh_confirmacao(texto_lower)}")
   if eh_confirmacao_pendente_ativa(ctx) and eh_confirmacao(texto_lower):
       print(f"[DEBUG_06_BLOCO] ENTRANDO no bloco confirmacao")
   else:
       print(f"[DEBUG_06_BLOCO] REJEITADO - confirmacao_pendente={eh_confirmacao_pendente_ativa(ctx)} | confirmacao={eh_confirmacao(texto_lower)}")
   ```

3. **Executar cenário 06** e coletar logs

---

## CONCLUSÃO SEM PATCH

**Por que cenário 06 falha:**
- O contexto provavelmente não está sendo carregado com `aguardando_confirmacao_agendamento=True`
- Isso impede que `eh_confirmacao_pendente_ativa(ctx)` retorne True
- O bloco 4475 não é ativado, mesmo que `eh_confirmacao()` retorne True

**Próximo passo (LOTE 3A.3):**
- Adicionar logs de debug
- Rastrear contexto carregado
- Localizar exatamente onde o valor é perdido

---

## NOTAS TÉCNICAS

### Campos de Confirmação

O sistema usa múltiplos campos para representar confirmação pendente:

- **Em Sessões:** `confirmacao_pendente` (booleano simples)
- **Em MemoriaTemporaria/contexto:** `aguardando_confirmacao_agendamento` (usado pelo router)
- **Interpretador:** `interpretacao_conversacional["intencao"]` (via GPT)

**Esses não são sincronizados automaticamente!**

Isso explica por que o teste falha:
- Teste salva em Sessões
- Router lê do contexto
- Campo não existe no contexto
- Confirmação não é processada

---

**Relatório gerado:** 2026-06-22T20:20:00Z  
**Status:** Investigação incompleta - sem patch por solicitação  
**Próximo passo:** LOTE 3A.3 com rastreamento de contexto
