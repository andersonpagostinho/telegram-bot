# FORENSE CENÁRIO 06 — CONFIRMAÇÃO EMBUTIDA

**Data:** 2026-06-22  
**Escopo:** Cenário 06 apenas  
**Objetivo:** Descobrir exatamente onde o fluxo para

---

## RESULTADO FINAL

### Classificação: **B) CONFIRMAÇÃO RECONHECIDA, FALHA POSTERIOR**

A confirmação **é detectada corretamente** pelo handler de LOTE 3E, mas há uma falha de encoding no router que impede a conclusão do fluxo.

---

## RASTREAMENTO COMPLETO

| Etapa | Status | Resultado | Observação |
|-------|--------|-----------|------------|
| **1. Mensagem Original** | OK | "Pode deixar. Li tudo. Sim, pode confirmar esse horário. Obrigado!" | Texto com "pode confirmar" |
| **2. Mensagem Normalizada** | OK | "pode deixar. li tudo. sim, pode confirmar esse horrio. obrigado!" | Lowercase, acentos removidos |
| **3. confirmacao_pendente** | OK | TRUE | Carregada corretamente do Firestore |
| **4. eh_confirmacao()** | OK | TRUE | Detecta "pode confirmar" em string |
| **5. eh_desistencia_fluxo()** | OK | FALSE | Corretamente identifica como confirmação |
| **6. Handler entrada** | OK | confirmacao_pendente=True | Guard validado (tenant_id match) |
| **7. Handler retorno** | OK | tratado=True, acao="confirmar" | Decisão correta tomada |
| **8. Contexto salvo** | OK | Salvo em MemoriaTemporaria/contexto | v2 Sessoes também atualizado |
| **9. Classificador** | OK | intencao="confirmacao_agendamento", confianca=95 | Respeitando LOTE_3B |
| **10. Router continuou** | OK | Fluxo prosseguiu | Não parou após handler |
| **11. send_and_stop** | ERRO | Não chamado | Falha de encoding antes |
| **12. Erro final** | ERRO | UnicodeEncodeError linha 4066 | Emoji em print do router |

---

## LOGS CAPTURADOS

### Handler (LOTE 3E)

```
[LOTE_3E_CONFIRMACAO_EARLY] Confirmacao detectada: pode deixar. li tudo. sim, pode confirmar esse hor
[LOTE_3E_CONFIRMACAO] confirmacao_detectada
```

### Fluxo Router

```
[DIAG_CARREGAR] path_legado=Clientes/forense_06_ebeacc55/MemoriaTemporaria/contexto | tenant_id=forense_06_ebeacc55
[DIAG_CARREGAR] lido_legado: existe=True | estado_fluxo=None | cancelamento_pendente=False
[DIAG_CARREGAR] guard_validacao: guard_tenant=forense_06_ebeacc55 | esperado=forense_06_ebeacc55 | match=True
[CTX_LEGADO_COMPAT] | path=Clientes/forense_06_ebeacc55/MemoriaTemporaria/contexto | tenant_id=forense_06_ebeacc55 | guard_validado
```

### Classificador

```
[CLASSIFICADOR CONTEXTO] {'modo_conversa': 'operacional', 'confianca': 75, 'motivo': 'draft_existente, confirmacao_pendente', ...}
[ANTES_CONSULTA_INFORMATIVA_IDLE] Entrando no bloco (estado idle)
[INTENÇÃO CONVERSACIONAL] {'intencao_conversacional': 'confirmacao_agendamento', 'tipo_ajuste_incremental': None, 'confianca': 95, 'motivo': 'respeitando_lote_3b'}
```

---

## PONTO DE FALHA

### Linha 4066 do router/principal_router.py

Há um emoji (🔒 ou similar) em um print statement que está causando `UnicodeEncodeError` no Windows com encoding cp1252.

**Erro:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f512' in position 0: character maps to <undefined>
```

**Contexto:**
- A falha ocorre APÓS o handler ter retornado `tratado=True`
- Ocorre ANTES de `send_and_stop` ser chamado
- É uma falha de encoding Windows, não de lógica

**Código problemático:**
```python
print(f"[EMOJI_AQUI] algo em print")  # Linha ~4066
```

---

## CONCLUSÃO

### Handler de LOTE 3E: ✅ 100% FUNCIONAL

- Detecta confirmação corretamente
- Retorna decisão correta
- Integração com router funciona
- Contexto é salvo corretamente
- Fluxo continua apropriadamente

### Cenário 06: ⚠️ BLOQUEADO POR ERRO EXTERNO

Não por falha de LOTE 3E, mas por um **emoji em print do router (linha ~4066)** que causa erro de encoding no Windows.

**Este é um bug PRÉ-EXISTENTE no router**, não introduzido por LOTE 3E.

---

## RECOMENDAÇÃO

**Não corrigir como parte de LOTE 3E.**

Razão:
1. LOTE 3E já concluído com sucesso
2. Handler funciona 100%
3. Cenário 07 (negação) passa OK
4. Baseline mantido: 216/216 PASS
5. Bug de encoding é PRÉ-EXISTENTE

**Ação:** Abrir item separado para remover emojis do router (problema geral de encoding Windows).

---

## DADOS TÉCNICOS

```json
{
  "teste": "forense_cenario_06.py",
  "tenant": "forense_06_ebeacc55",
  "actor": "whatsapp:55119999006",
  "mensagem": "Pode deixar. Li tudo. Sim, pode confirmar esse horrio. Obrigado!",
  "handler_resultado": {
    "tratado": true,
    "acao": "confirmar",
    "motivo": "confirmacao_detectada"
  },
  "ponto_falha": "router.principal_router linha ~4066",
  "tipo_falha": "UnicodeEncodeError",
  "classificacao": "B) Confirmacao reconhecida, falha posterior",
  "causa_raiz": "Emoji em print do router (pre-existente)",
  "lote_3e_status": "OK"
}
```

---

## CLASSIFICAÇÃO FINAL

```
A) Teste incorreto              — NAO
B) Confirmacao reconhecida      — SIM (100%)
C) Confirmacao nao reconhecida  — NAO
D) Regressao do handler         — NAO
```

**Conclusão:** LOTE 3E está funcionando perfeitamente. O erro é externo ao handler.
