# 📋 INSTRUÇÕES DE VALIDAÇÃO EM PRODUÇÃO

**Objetivo:** Validar o patch mínimo usando o fluxo real da NeoEve  
**Tempo estimado:** 10-15 minutos  
**Risco:** Nenhum (patch já está implementado, só capturam logs)

---

## PASSO 1: PREPARAR O AMBIENTE

### 1.1 Verificar configuração
```bash
# Confirmar que .env tem:
TOKEN=<seu_token_telegram>
FIREBASE_PROJECT_ID=<seu_projeto>
OPENAI_API_KEY=<sua_key_openai>

# Confirmar que Firebase está acessível:
# - Ou com credenciais reais
# - Ou com emulador local rodando
```

### 1.2 Verificar patch está em lugar
```bash
# Confirmar que o arquivo tem os logs:
grep -n "fonte_parse" utils/interpretador_datas.py
# Deve retornar linhas ~250, ~290, ~330 com logs do patch
```

---

## PASSO 2: INICIAR O BOT

### 2.1 Abrir terminal
```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
```

### 2.2 Iniciar o bot
```bash
# Opção A: Modo local com polling (mais fácil para teste)
python main.py

# Ou Opção B: Se usar webhook
# (certifique-se que WEBHOOK_URL está correto)
python main.py
```

### 2.3 Verificar inicialização
```
Deve aparecer:
✅ Handlers registrados
✅ Bot started on polling (ou webhook)
✅ Aguardando mensagens...
```

---

## PASSO 3: ENVIAR 3 MENSAGENS

**Importante:** Envie uma de cada vez. Espere os logs aparecerem antes de enviar a próxima.

### TESTE 1: Slots + Data + Hora Completos
```
Abra seu Telegram (chat pessoal com o bot)

Digite EXATAMENTE isto:
    corte cabelo da Suri às 16 horas amanhã

Aguarde 2-3 segundos. Procure no terminal por:
    🧪 [PARSER] fonte_parse=manual_hoje_amanha | resultado=2026-06-03 16:00:00
```

### TESTE 2: Contexto Anterior + Nova Hora
```
Antes de enviar:
- Você deve ter um agendamento anterior com data 2026-06-03T09:00:00
- Ou acesse Firebase e defina manualmente:
  contexto/usuario_123/data_hora = "2026-06-03T09:00:00"

Digite EXATAMENTE isto:
    amanhã às 16

Aguarde logs. Procure por:
    🧪 [PARSER] fonte_parse=manual_hoje_amanha | resultado=2026-06-03 16:00:00
    (hora DEVE ser 16:00, não 09:00)
```

### TESTE 3: Contexto Anterior + Só Hora
```
Com mesmo contexto anterior (09:00):

Digite EXATAMENTE isto:
    às 16

Aguarde logs. Procure por:
    (pode não ter [PARSER] de heurística)
    (router deve usar contexto anterior para data)
```

---

## PASSO 4: CAPTURAR OS LOGS

### 4.1 Procure por estes padrões NO TERMINAL

#### Para cada teste, copie todos os logs que começam com:
```
🧪 [PARSER]
🧪 [MESCLAR]
🔥 [PRE-CHECK]
🧑‍💼 [HANDOFF]
🛡️ [SLOT]
🧠 [INTENÇÃO]
🧪 [CTX]
[INFO] [extrair_slots_e_mesclar]
[INFO] [chamar_gpt]
[INFO] [JSON]
```

#### Logs OBRIGATÓRIOS a copiar:

**[PARSER]** — do interpretador_datas.py
```
🧪 [PARSER] fonte_parse=<heurística_ou_dateparser> | resultado=<datetime>
```

**[SLOTS_EXTRAIDOS]** — do router
```
Procure por referencias a "Suri", "corte", "16"
nos logs de [MESCLAR] ou [CTX]
```

**[CTX_ANTES_MERGE]** — do router antes de processar
```
Estado anterior: data_hora, servico, cliente_nome, etc
```

**[CTX_APOS_MERGE]** — do router depois de processar
```
Estado atualizado: data_hora novo, cliente_nome, etc
```

**[ANTES_GPT]** — contexto enviado para GPT
```
Procure por logs que mostrem dados passados ao chamar GPT
```

**[JSON_BRUTO]** — resposta bruta do GPT
```
Resposta direta da API OpenAI
```

**[JSON_DO_GPT]** — resposta processada do GPT
```
JSON com campos: servico, cliente_nome, profissional, data_hora, etc
```

**[DADOS_EXECUTAR_ACAO]** — payload para acao_router_handler
```
Dados finais passados para criar evento
```

### 4.2 Salvar logs
```
Opção A: Copiar direto do terminal
  1. Selecionar todo log
  2. Ctrl+C para copiar
  3. Colar em arquivo

Opção B: Redirecionar para arquivo
  python main.py 2>&1 | tee bot_logs.txt
  (depois envie bot_logs.txt)

Opção C: Ver arquivo de log se configurado
  tail -f logs/neoeve.log
```

---

## PASSO 5: ANALISAR OS LOGS

### 5.1 Validação esperada para TESTE 1

```
Entrada: "corte cabelo da Suri às 16 horas amanhã"

✅ DEVE TER:
  [PARSER] fonte_parse=manual_hoje_amanha | resultado=2026-06-03 16:00:00
  
  Logs contendo:
    - "corte" (serviço mencionado)
    - "Suri" (cliente)
    - "16" (hora)
    - "2026-06-03T16:00:00" (data_hora final)

✅ JSON_DO_GPT DEVE TER:
  "cliente_nome": "Suri" (NÃO profissional)
  "servico": "corte cabelo" (ou variação)
  "data_hora": "2026-06-03T16:00:00"

❌ NÃO DEVE TER:
  "profissional": "Suri" (seria bug)
  "data_hora": "2026-06-03T09:00:00" (seria hora antiga)
```

### 5.2 Validação esperada para TESTE 2

```
Contexto anterior: 2026-06-03T09:00:00
Entrada: "amanhã às 16"

✅ DEVE TER:
  [PARSER] fonte_parse=manual_hoje_amanha | resultado=2026-06-03 16:00:00
  
  [CTX_APOS_MERGE]:
    "data_hora": "2026-06-03T16:00:00"  (NOVO 16:00)
  
  [JSON_DO_GPT]:
    "data_hora": "2026-06-03T16:00:00"

✅ Validação adicional:
  ctx["data_hora"] == "2026-06-03T16:00:00"
  draft["data_hora"] == "2026-06-03T16:00:00"  (sincronizados)

❌ NÃO DEVE TER:
  "data_hora": "2026-06-03T09:00:00" (hora antiga)
```

### 5.3 Validação esperada para TESTE 3

```
Contexto anterior: 2026-06-03T09:00:00
Entrada: "às 16"

✅ DEVE TER:
  [PARSER] → retorna None (correto, sem data explícita)
  
  [CTX_APOS_MERGE]:
    Router deve usar contexto anterior:
    "data_hora": "2026-06-03T16:00:00"  (data anterior + hora nova)

✅ JSON_DO_GPT:
  "data_hora": "2026-06-03T16:00:00"

❌ NÃO DEVE TER:
  "data_hora": "2026-06-03T09:00:00" (hora antiga sobreviveu)
```

---

## PASSO 6: ENVIAR RESULTADO

Copie os logs capturados e envie:

**Formato esperado:**
```
TESTE 1: "corte cabelo da Suri às 16 horas amanhã"

[PARSER]
<logs aqui>

[SLOTS_EXTRAIDOS]
<evidência de Suri, corte, 16>

[CTX_ANTES_MERGE]
<estado anterior>

[CTX_APOS_MERGE]
<estado atualizado>

[ANTES_GPT]
<contexto enviado>

[JSON_DO_GPT]
<resposta do GPT>

[DADOS_EXECUTAR_ACAO]
<payload final>

---

TESTE 2: "amanhã às 16"
<repetir estrutura acima>

---

TESTE 3: "às 16"
<repetir estrutura acima>
```

---

## TROUBLESHOOTING

### Bot não inicia
```
Erro: "TOKEN inválido"
→ Verificar .env
→ Confirmar TOKEN não tem espaços

Erro: "Firebase não acessível"
→ Verificar credenciais
→ Tentar emulador local
→ Verificar conectividade
```

### Mensagens não aparecem
```
Erro: "Nenhuma resposta"
→ Verificar que o bot está rodando
→ Confirmar que enviou ao chat certo
→ Verificar se há handler para mensagens gerais
```

### Logs não aparecem
```
Erro: "Nenhum [PARSER]"
→ Verificar que patch está no código
→ Grep: grep "fonte_parse" utils/interpretador_datas.py
→ Confirmar que main.py rodou o código atualizado

Erro: "Logs no arquivo, não no terminal"
→ Verificar se há arquivo de log configurado
→ Procurar em logs/ ou .log files
```

---

## RESUMO FINAL

| Passo | Ação | Tempo |
|-------|------|-------|
| 1 | Preparar ambiente | 2 min |
| 2 | Iniciar bot | 1 min |
| 3 | Enviar 3 mensagens | 3 min |
| 4 | Capturar logs | 3 min |
| 5 | Analisar resultado | 3 min |
| 6 | Enviar resultado | 1 min |
| **TOTAL** | | **~15 min** |

---

## PRÓXIMO PASSO APÓS VALIDAÇÃO

Após capturar e analisar os logs:

```
✅ Se TUDO passou:
   → Patch validado em produção
   → Suri é cliente ✓
   → Hora 16:00 não 09:00 ✓
   → Texto original preservado ✓
   → Draft sincronizado ✓
   → BUG ENCERRADO

⚠️ Se ALGO não passou:
   → Enviar logs
   → Analisar qual validação falhou
   → Ajustar conforme necessário
```

