# 🎯 VALIDAÇÃO FINAL EM PRODUÇÃO

**Objetivo:** Confirmar que o patch P0 funciona no fluxo real da NeoEve  
**Tempo:** ~5 minutos  
**O que validar:** Log [MERGE_DATA_HORA] e data_hora preservada até GPT

---

## PASSO 1: Iniciar o bot

```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
python main.py
```

Aguarde:
```
✅ Handlers registrados
✅ Bot started on polling (ou webhook)
✅ Aguardando mensagens...
```

---

## PASSO 2: Enviar mensagem exata

**Abra seu Telegram ou teste local**

Digite EXATAMENTE:
```
corte cabelo da Suri às 16 horas amanhã
```

---

## PASSO 3: Procurar pelos logs

No terminal onde rodou `python main.py`, procure por **TODOS** estes logs:

### ✅ Log 1: [PARSER]
```
🧪 [PARSER] fonte_parse=manual_hoje_amanha | resultado=2026-06-03 16:00:00
```

### ✅ Log 2: [MERGE_DATA_HORA] — LOG NOVO DO PATCH
```
🛡️ [MERGE_DATA_HORA] explícita=True | dt_parser=2026-06-03 16:00:00 | antigo=<qualquer> | final=2026-06-03T16:00:00
```

### ✅ Log 3: [PRE-SAVE dados_update]
```
🧪 [PRE-SAVE dados_update] {..., 'data_hora': '2026-06-03T16:00:00', ...}
```

### ✅ Log 4: [PRE-SAVE contexto_base DEPOIS]
```
🧪 [PRE-SAVE contexto_base DEPOIS] {..., 'data_hora': '2026-06-03T16:00:00', ...}
```

### ✅ Log 5: [CTX->GPT] (ou equivalente)
```
Contexto final enviado para GPT com:
'data_hora': '2026-06-03T16:00:00'
```

---

## PASSO 4: Validação de Sucesso

### ✅ Critério 1: PARSER retorna 16:00
```
[PARSER] resultado=2026-06-03 16:00:00  ✅
```

### ✅ Critério 2: MERGE_DATA_HORA aparece e mostra 16:00
```
🛡️ [MERGE_DATA_HORA] ... final=2026-06-03T16:00:00  ✅
```

### ✅ Critério 3: PRE-SAVE TEM 16:00
```
🧪 [PRE-SAVE dados_update] data_hora=2026-06-03T16:00:00  ✅
(Não 09:00, não 00:00, exatamente 16:00)
```

### ✅ Critério 4: CTX->GPT TEM 16:00
```
Contexto final para GPT: data_hora=2026-06-03T16:00:00  ✅
```

### ✅ Critério 5: Agendamento criado com hora correta
```
Evento criado para: 2026-06-03 às 16:00  ✅
(não 09:00, não 00:00)
```

---

## PASSO 5: Copiar logs se necessário

Se precisar enviar logs de volta:

**Opção A: Do terminal**
```
Selecionar todo output
Ctrl+C para copiar
Colar em um arquivo texto
```

**Opção B: Redirecionar para arquivo**
```bash
python main.py 2>&1 | tee bot_logs.txt
# Depois envie bot_logs.txt
```

**Opção C: Ver arquivo de log**
```bash
tail -f logs/neoeve.log
# Se estiver configurado
```

---

## TROUBLESHOOTING

### ❌ Log [MERGE_DATA_HORA] não aparece
**Possível causa:** Patch não foi aplicado corretamente

**Verificação:**
```bash
grep -n "MERGE_DATA_HORA" services/gpt_service.py
# Deve retornar linhas com o novo log
```

**Solução:** Confirmar que services/gpt_service.py foi alterado:
```bash
git diff services/gpt_service.py | grep MERGE_DATA_HORA
```

### ❌ Log aparece mas com data_hora errada (09:00)
**Possível causa:** Patch foi aplicado mas não entrou na nova lógica

**Verificação:**
- `tem_hora_explicita` está True?
- `dt` (resultado do parser) é válido?
- `data_hora_existente` é do contexto anterior?

**Solução:** Adicionar print debug:
```python
print(f"DEBUG: dt={dt}, tem_hora={tem_hora_explicita}, existente={data_hora_existente}")
```

### ❌ Nenhum log aparece
**Possível causa:** Função não está sendo chamada

**Verificação:**
```bash
grep -n "processar_com_gpt_com_acao" router/principal_router.py
# Deve ter chamadas
```

---

## RESUMO DO SUCESSO

Se TODOS os 5 critérios aparecerem:

```
✅ [PARSER] resultado=2026-06-03 16:00:00
✅ 🛡️ [MERGE_DATA_HORA] ... final=2026-06-03T16:00:00
✅ 🧪 [PRE-SAVE dados_update] data_hora=2026-06-03T16:00:00
✅ 🧪 [PRE-SAVE contexto_base DEPOIS] data_hora=2026-06-03T16:00:00
✅ [CTX->GPT] data_hora=2026-06-03T16:00:00
```

Então o patch P0 foi **aplicado e funciona em produção**.

---

## PRÓXIMO PASSO

Após validação bem-sucedida em produção:

```
BUG ENCERRADO ✅

Razão: Evidência de produção mostra que:
1. Parser retorna 16:00 (correto)
2. Merge respeita dados explícitos (novo patch)
3. Data/hora preserva até GPT (sincronização funciona)
4. Agendamento criado com hora correta (resultado final)
```

**Pronto para merge em produção.**

