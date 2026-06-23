# P1-R01C — CLASSIFICAÇÃO FINAL CENÁRIO 05 COM GPT REAL

**Status:** ⏸️ AGUARDANDO EXECUÇÃO DE AUDITORIA GPT REAL  
**Data:** 2026-06-23  
**Pré-requisito:** resultado_audit_cenario_05_gpt_real.json  
**Baseline:** baseline-216-pass  

---

## BLOQUEIO ATUAL

### Arquivo Esperado Não Encontrado

```
Arquivo: resultado_audit_cenario_05_gpt_real.json
Status: NÃO EXISTE
Razão: Script audit_cenario_05_gpt_real.py ainda não foi executado
Requisito: OPENAI_API_KEY deve estar configurada
```

---

## COMO DESBLOQUEAR

### Passo 1: Configurar OPENAI_API_KEY

```powershell
$env:OPENAI_API_KEY = "sk-proj-sua-chave-aqui"
```

### Passo 2: Validar com Smoke Test

```bash
python tests/audit_gpt_real_smoke.py
```

Saída esperada:
```
✓ OPENAI_API_KEY presente
✓ CONEXÃO ESTABELECIDA
Resultado salvo em: resultado_audit_gpt_real_smoke.json
```

### Passo 3: Executar Auditoria Cenário 05

```bash
python tests/audit_cenario_05_gpt_real.py
```

Saída esperada:
```
[1/9] SETUP TENANT...
[2/9] TEXTO ORIGINAL...
[3/9] NORMALIZAÇÃO...
[4/9] CLASSIFICAÇÃO CONVERSACIONAL...
[5/9] ESTADO SESSÃO ANTES...
[6/9] EXECUTANDO ROUTER PRINCIPAL...
[7/9] PROMPT ENVIADO AO GPT...
[8/9] RESPOSTA GPT BRUTA...
[9/9] ESTADO SESSÃO DEPOIS...

Auditoria salva em: resultado_audit_cenario_05_gpt_real.json
```

### Passo 4: Executar Classificação Final

```bash
# Este documento será preenchido automaticamente após execução
python docs/scripts/gerar_p1_r01c.py resultado_audit_cenario_05_gpt_real.json
```

---

## TEMPLATE DE CLASSIFICAÇÃO (Será Preenchido Após Execução)

Este documento seguirá a estrutura abaixo uma vez que a auditoria GPT real for executada:

---

## ESTRUTURA DO DOCUMENTO FINAL

### 1. EVIDÊNCIA EXTRAÍDA DO JSON

#### 1.1 JSON Bruto do GPT

```json
[Será extraído de resultado_audit_cenario_05_gpt_real.json:
  etapas[8].nome == "resposta_gpt_bruta"
  etapas[8].conteudo
]
```

#### 1.2 JSON Parseado

```json
[Será extraído de resultado_audit_cenario_05_gpt_real.json:
  etapas[8.5].nome == "resposta_gpt_parseada"
  etapas[8.5].completo
]
```

#### 1.3 Slots Extraídos

| Slot | Valor |
|------|-------|
| serviço | [etapas[8.5].servico] |
| profissional | [etapas[8.5].profissional] |
| data | [etapas[8.5].data] |
| hora | [etapas[8.5].hora] |

#### 1.4 Decisão do Router

```
[Será extraído de resultado_audit_cenario_05_gpt_real.json:
  etapas[6].nome == "router_principal"
  etapas[6].resposta
]
```

#### 1.5 Estado Final

```json
[Será extraído de resultado_audit_cenario_05_gpt_real.json:
  etapas[9].nome == "estado_depois"
  etapas[9].confirmacao_pendente
  etapas[9].completo
]
```

---

### 2. FLUXO DE ANÁLISE

#### 2.1 Verificação Ponto 1: GPT Extraiu Pedido?

```python
# Pergunta: JSON parseado tem slots preenchidos?

if resultado["slots_extraidos"]["servico"] and \
   resultado["slots_extraidos"]["profissional"] and \
   resultado["slots_extraidos"]["data"] and \
   resultado["slots_extraidos"]["hora"]:
    return "SIM - GPT extraiu pedido"
else:
    return "NÃO - GPT não extraiu pedido (HIPÓTESE A)"
```

#### 2.2 Verificação Ponto 2: Parser Descartou?

```python
# Pergunta: JSON bruto tem dados, mas parseado não?

bruto_tem_dados = bool(resultado["resposta_gpt_bruta"])
parseado_vazio = not bool(resultado["slots_extraidos"]["servico"])

if bruto_tem_dados and parseado_vazio:
    return "SIM - Parser descartou (HIPÓTESE B)"
```

#### 2.3 Verificação Ponto 3: Router Descartou?

```python
# Pergunta: Slots existem, mas router não entrou em confirmação?

slots_existem = bool(resultado["slots_extraidos"]["servico"])
confirmacao_ausente = not resultado["estado_final"]["confirmacao_pendente"]

if slots_existem and confirmacao_ausente:
    return "SIM - Router descartou (HIPÓTESE C)"
```

#### 2.4 Verificação Ponto 4: Classificador Bloqueou?

```python
# Pergunta: Classificador marcou como não-operacional?

if resultado["etapas"]["classificacao"]["tipo"] != "operacional":
    return "SIM - Classificador bloqueou (HIPÓTESE D)"
```

#### 2.5 Verificação Ponto 5: Setup Incorreto?

```python
# Pergunta: Houver erro antes de chegar no GPT?

if resultado.get("erro"):
    return "SIM - Teste/setup incorreto (HIPÓTESE E)"
```

---

### 3. CLASSIFICAÇÃO FINAL

**Hipótese Comprovada:** [Será determinada por verificação acima]

**Evidência Crítica:**
```
[Será extraída do JSON baseado em classificação]
```

**Arquivo:Linha de Origem:**
```
[Será referenciado código que implementa a falha]
```

---

### 4. PATCH MÍNIMO RECOMENDADO (Sem Implementar)

#### Se Hipótese A (GPT não extraiu)

**Arquivo:** `prompts/manual_secretaria.py`

**Tamanho:** +5-10 linhas

**Recomendação:**
```python
# Adicionar instrução explícita ao GPT:
"Se a mensagem é muito longa (>1000 chars) com conteúdo pessoal:
 - Procure pela ÚLTIMA frase operacional
 - Essa frase contém o pedido, mesmo que no final
 - Priorize extrair slots dessa frase"
```

#### Se Hipótese B (Parser descartou)

**Arquivo:** `services/gpt_executor.py`

**Tamanho:** +15-20 linhas

**Recomendação:**
```python
# Adicionar fallback se JSON bruto tiver conteúdo:
if not slots_extraidos and len(gpt_resposta) > 50:
    # Tentar re-parsear com formato alternativo
    # ou adicionar validação mais permissiva
```

#### Se Hipótese C (Router descartou)

**Arquivo:** `router/principal_router.py`

**Tamanho:** +10-15 linhas

**Recomendação:**
```python
# Adicionar fallback se slots vazios mas operacional:
if not slots_extraidos and classificacao["tipo"] == "operacional":
    # Forçar entrada em fluxo agendamento mesmo com slots incompletos
```

#### Se Hipótese D (Classificador bloqueou)

**Arquivo:** `services/classificador_conversa.py`

**Tamanho:** +20-30 linhas

**Recomendação:**
```python
# Adicionar score de pedido final:
if "marcar" or "agendar" or "reservar" in ultimas_palavras:
    # Aumentar score de operacionalidade independente de ruído inicial
```

---

## QUANDO SERÁ PREENCHIDO

Este documento será preenchido automaticamente após:

1. ✓ OPENAI_API_KEY ser configurada
2. ✓ `python tests/audit_gpt_real_smoke.py` passar
3. ✓ `python tests/audit_cenario_05_gpt_real.py` ser executado
4. ✓ `resultado_audit_cenario_05_gpt_real.json` ser gerado
5. ✓ Classificação final ser derivada do JSON

**Tempo estimado:** 5-10 minutos após desbloqueio

---

## CHECKLIST PARA DESBLOQUEAR

- [ ] OPENAI_API_KEY obtida em platform.openai.com
- [ ] Variável de ambiente configurada: `$env:OPENAI_API_KEY = "sk-..."`
- [ ] Smoke test passou: `python tests/audit_gpt_real_smoke.py`
- [ ] Auditoria cenário 05 executada: `python tests/audit_cenario_05_gpt_real.py`
- [ ] Arquivo gerado: `resultado_audit_cenario_05_gpt_real.json`
- [ ] Pronto para gerar classificação final

---

## DOCUMENTAÇÃO RELACIONADA

- `docs/auditorias/GPT_TEST_01_AMBIENTE_GPT_REAL.md` — Como configurar ambiente
- `tests/audit_gpt_real_smoke.py` — Validação de chave
- `tests/audit_cenario_05_gpt_real.py` — Execução da auditoria
- `docs/auditorias/P1_R01_AUDITORIA_FORENSE_CENARIO_05_MENSAGEM_LONGA_PEDIDO_FINAL.md` — Auditoria preliminar
- `docs/auditorias/P1_R01B_LOGS_REAIS_CENARIO_05.md` — Status de bloqueio anterior

---

**Status:** ⏸️ Bloqueado — Aguardando GPT-TEST-01  
**Próximo Passo:** Configurar OPENAI_API_KEY e executar smoke test  
**Tempo Estimado Desbloquio:** <15 minutos  
**Assinatura:** Claude Code — P1-R01C (Pronto para Classificação)
