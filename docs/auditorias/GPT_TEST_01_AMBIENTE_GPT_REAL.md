# GPT-TEST-01 — CONFIGURAÇÃO DE AMBIENTE PARA AUDITORIAS GPT REAIS

**Status:** Documentação de Setup e Execução  
**Data:** 2026-06-23  
**Baseline:** baseline-216-pass (determinístico, sem GPT)  
**Escopo:** Testes que usam GPT real (P1 Robustez, Auditoria)  

---

## CONTEXTO

O NeoEve tem dois tipos de testes:

### 1. Baseline Determinístico (216/216 PASS — Sem GPT)

```
P1 E2E (42 testes):
  ✓ Processam identidade + onboarding
  ✓ Sem chamadas ao principal_router
  ✓ Sem GPT
  ✓ Não requerem OPENAI_API_KEY

P0 Regressão (174 testes):
  ✓ Validam estado em Firestore
  ✓ Determinísticos
  ✓ Sem GPT
  ✓ Não requerem OPENAI_API_KEY
```

### 2. Testes que Usam GPT Real (Bloqueados sem chave)

```
P1 Robustez Conversacional (13 testes):
  ✗ Chama principal_router
  ✗ Requer GPT para interpretar mensagens
  ✗ OBRIGAM OPENAI_API_KEY
  ✗ NÃO estão no baseline (por isso 216/216 passou sem chave)

Auditoria Cenário 05:
  ✗ Cenário de mensagem longa com pedido final
  ✗ Requer GPT real para diagnosticar causa de falha
  ✗ OBRIGA OPENAI_API_KEY
```

---

## OBJETIVO DESTE SETUP

Criar ambiente seguro para:

1. ✅ Validar presença de OPENAI_API_KEY sem expor segredo
2. ✅ Testar conectividade com OpenAI API (smoke test barato)
3. ✅ Executar cenário 05 com captura de logs GPT reais
4. ✅ Diagnosticar falhas que requerem compreensão semântica
5. ✅ Manter separação entre baseline determinístico e testes GPT

---

## COMO CONFIGURAR OPENAI_API_KEY LOCALMENTE

### Passo 1: Obter a Chave

**Fonte:** https://platform.openai.com/api-keys

**Requisitos:**
- Conta OpenAI ativa
- Acesso a api-keys dashboard
- Saldo positivo (para testes)

**Formato esperado:**
```
sk-proj-... (v2 — recomendado)
ou
sk-... (v1 — legado)
```

### Passo 2: Configurar Variável de Ambiente

#### Opção A: PowerShell (Local)

```powershell
# Configurar para sessão atual
$env:OPENAI_API_KEY = "sk-proj-seu-token-aqui"

# Verificar
echo $env:OPENAI_API_KEY
# Deve retornar a chave
```

#### Opção B: Arquivo .env (Persistente)

Criar arquivo `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sk-proj-seu-token-aqui
```

Depois carregar (se usar python-dotenv):

```python
from dotenv import load_dotenv
load_dotenv()
```

#### Opção C: Variável de Ambiente do Windows (Persistente)

```powershell
# Definir permanentemente
[Environment]::SetEnvironmentVariable(
    "OPENAI_API_KEY",
    "sk-proj-seu-token-aqui",
    [EnvironmentVariableTarget]::User
)

# Reabrir terminal para aplicar
```

### Passo 3: Validar Configuração

```bash
# Verificar se está presente
python -c "import os; print('OK' if os.getenv('OPENAI_API_KEY') else 'FALHA')"
# Deve retornar: OK
```

---

## COMO VALIDAR SEM EXPOR SEGREDO

**Nunca:**
```bash
echo $env:OPENAI_API_KEY  # ❌ Expõe a chave completa!
```

**Sempre:**
```bash
python tests/audit_gpt_real_smoke.py
# Retorna:
#   ✓ OPENAI_API_KEY presente
#   - Prefixo: sk-proj-...
#   - Tamanho: 123 chars
#   - Origem: API Key v2 (sk-proj-...)
```

---

## SEQUÊNCIA DE EXECUÇÃO

### 1. Validar Ambiente (Smoke Test)

```bash
python tests/audit_gpt_real_smoke.py
```

**Saída esperada:**

```
[1/2] VALIDANDO OPENAI_API_KEY...
  ✓ OPENAI_API_KEY presente
  - Prefixo: sk-proj-...
  - Tamanho: 123 chars
  - Origem: API Key v2 (sk-proj-...)

[2/2] TESTANDO CONEXÃO COM OPENAI...
  ✓ CONEXÃO ESTABELECIDA
  - Modelo: gpt-3.5-turbo
  - Resposta: ok
  - Tokens usados: 8
  - Custo estimado: $0.000015

Resultado salvo em: resultado_audit_gpt_real_smoke.json

PRÓXIMAS ETAPAS

GPT real está operacional. Pode executar auditorias:
  python tests/audit_cenario_05_gpt_real.py
```

**Se falhar:**

```
  ✗ OPENAI_API_KEY NÃO CONFIGURADA
  - Bloqueio: Não é possível continuar

Resultado salvo em: resultado_audit_gpt_real_smoke.json
```

### 2. Auditar Cenário 05 com Logs Reais

Se smoke test passou:

```bash
python tests/audit_cenario_05_gpt_real.py
```

**Saída esperada:**

```
[1/9] SETUP TENANT...
  ✓ Tenant criado: audit_cenario_05_gpt_a1b2c3d4

[2/9] TEXTO ORIGINAL...
  Tamanho: 1367 chars

[3/9] NORMALIZAÇÃO...
  1367 → 1250 chars

[4/9] CLASSIFICAÇÃO CONVERSACIONAL...
  Tipo: operacional
  Confiança: 0.75

[5/9] ESTADO SESSÃO ANTES...
  confirmacao_pendente: False

[6/9] EXECUTANDO ROUTER PRINCIPAL...
  ✓ Router executado

[7/9] PROMPT ENVIADO AO GPT...
  ✓ Prompt capturado (2050 chars)

[8/9] RESPOSTA GPT BRUTA...
  ✓ JSON parseado
    - serviço: corte
    - profissional: bruna
    - data: amanhã
    - hora: 15h

[9/9] ESTADO SESSÃO DEPOIS...
  confirmacao_pendente: True

RESULTADO FINAL

✓ PASS — Pedido final foi detectado

Auditoria salva em: resultado_audit_cenario_05_gpt_real.json
```

---

## RISCOS

### 1. Exposição de Chave

| Risco | Mitigação |
|-------|-----------|
| Echo da chave completa em terminal | ✓ Use `audit_gpt_real_smoke.py` (mostra apenas prefixo) |
| Chave em arquivo .git | ✓ `.env` é incluído em `.gitignore` |
| Chave em logs | ✓ Scripts não imprimem chave completa |
| Chave em resultado JSON | ✓ Resultado contém apenas prefixo e status |

### 2. Custos de API

| Operação | Custo Estimado | Limite |
|----------|----------------|--------|
| Smoke test (gpt-3.5-turbo, 10 tokens) | ~$0.000015 | 1000/mês = $0.015 |
| Auditoria cenário 05 (1-2 chamadas GPT) | ~$0.002 | 100/mês = $0.20 |
| P1 Robustez (13 cenários, 13 chamadas) | ~$0.026 | Na demanda = variável |

**Recomendação:** Usar gpt-3.5-turbo (mais barato) para auditorias

### 3. Limites de Rate

OpenAI tem limites por minuto/hora. Para evitar throttling:

- Smoke test: 1 requisição (sem limite)
- Auditoria cenário 05: ~5 requisições (dentro do limite)
- P1 Robustez: ~13 requisições (monitorar)

---

## CUSTOS ESTIMADOS

### Cenário: Executar Todas as Auditorias Uma Vez

```
Smoke test (1x):          $0.000015
Cenário 05 (1x):         $0.002000
P1 Robustez (1x, 13x):   $0.026000
────────────────────────────────
TOTAL:                    $0.028015 (~3 centavos)
```

**Por mês (desenvolvimento):**
- Smoke tests diários: $0.00045
- Auditorias ocasionais: $0.01
- **Total esperado:** ~$0.02-0.05/mês

---

## DIFERENÇA ENTRE BASELINE E TESTES GPT

| Aspecto | Baseline (216/216) | Testes GPT |
|---------|-------------------|-----------|
| **O que testa** | Firestore + regras | Interpretação semântica |
| **Requer GPT?** | Não | Sim |
| **Requer OPENAI_API_KEY?** | Não | Sim |
| **Router chamado** | processar_fluxo_identidade_onboarding | principal_router |
| **Determinístico?** | Sim | Não (GPT pode variar) |
| **Custo** | $0 | ~$0.002-0.03 por exec |
| **Tempo** | ~50 segundos | ~5-30 segundos |
| **Risco de falso-positivo** | Baixo | Médio (interpretação) |

---

## COMANDOS DE EXECUÇÃO

### Setup Completo

```bash
# 1. Configurar chave
$env:OPENAI_API_KEY = "sk-proj-..."

# 2. Validar smoke test
python tests/audit_gpt_real_smoke.py

# 3. Se passou, executar auditoria
python tests/audit_cenario_05_gpt_real.py

# 4. Verificar resultados
type resultado_audit_gpt_real_smoke.json | jq .
type resultado_audit_cenario_05_gpt_real.json | jq .
```

### Apenas Smoke Test

```bash
python tests/audit_gpt_real_smoke.py
```

### Apenas Cenário 05 (se já validou smoke)

```bash
python tests/audit_cenario_05_gpt_real.py
```

---

## SAÍDAS ESPERADAS

### `resultado_audit_gpt_real_smoke.json`

```json
{
  "timestamp": "2026-06-23T10:30:00.123456",
  "teste": "smoke_gpt_real",
  "status": "SUCESSO",
  "etapas": {
    "env_var": {
      "presente": true,
      "prefixo": "sk-proj-...",
      "tamanho_chars": 123,
      "origem_provavel": "API Key v2 (sk-proj-...)"
    },
    "conexao_gpt": {
      "sucesso": true,
      "modelo": "gpt-3.5-turbo",
      "resposta": "ok",
      "tokens_usados": {
        "total": 8
      },
      "custo_estimado_usd": 0.000015
    }
  }
}
```

### `resultado_audit_cenario_05_gpt_real.json`

```json
{
  "timestamp": "2026-06-23T10:35:00.123456",
  "cenario": 5,
  "etapas": [
    {
      "numero": 1,
      "nome": "setup_tenant",
      "status": "OK"
    },
    {
      "numero": 8.5,
      "nome": "resposta_gpt_parseada",
      "servico": "corte",
      "profissional": "bruna",
      "data": "amanhã",
      "hora": "15h"
    },
    {
      "numero": 9,
      "nome": "estado_depois",
      "confirmacao_pendente": true
    }
  ],
  "resultado_final": {
    "status": "PASS",
    "confirmacao_pendente": true,
    "slots_extraidos": {
      "servico": "corte",
      "profissional": "bruna",
      "data": "amanhã",
      "hora": "15h"
    }
  }
}
```

---

## BLOQUEIOS E RECUPERAÇÃO

### Se OPENAI_API_KEY Não Estiver Presente

```
[BLOQUEIO] OPENAI_API_KEY não está configurada

Execute primeiro: python tests/audit_gpt_real_smoke.py
Depois configure: $env:OPENAI_API_KEY = 'sk-...'
```

**Ação:**
1. Obter chave em platform.openai.com/api-keys
2. Configurar variável (Passo 2 acima)
3. Re-executar smoke test

### Se Smoke Test Falhar (Sem Conexão)

```
  ✗ CONEXÃO FALHOU
  - Erro: APIConnectionError: Connection failed
  - Tipo: APIConnectionError
```

**Possíveis causas:**
- Rede bloqueada (firewall, proxy)
- Chave inválida
- Saldo OpenAI negativo
- Quota excedida

**Ação:**
1. Validar chave em platform.openai.com
2. Verificar conectividade: `ping api.openai.com`
3. Verificar saldo e quotas
4. Tentar novamente

---

## REGRA FINAL

**Esta etapa é somente para obter evidência.**

✅ Permitido:
- Executar smoke test
- Executar auditoria cenário 05
- Capturar logs do GPT
- Documentar fluxo
- Armazenar resultados JSON

❌ Proibido (até confirmação de causa raiz):
- Alterar prompts
- Alterar router
- Alterar serviços
- Aplicar patches funcionales
- Modificar código do NeoEve

**Objetivo:** Obter evidência técnica para decisão de patch, **não implementar correção.**

---

## CHECKLIST DE SETUP

- [ ] OPENAI_API_KEY obtida em platform.openai.com
- [ ] Variável de ambiente configurada localmente
- [ ] Smoke test executado com sucesso
- [ ] Conexão com GPT validada
- [ ] Custos estimados aceitos
- [ ] Arquivo `.env` adicionado a `.gitignore`
- [ ] `resultado_audit_gpt_real_smoke.json` gerado
- [ ] Pronto para executar auditoria cenário 05

---

## PRÓXIMOS PASSOS

### Se Smoke Test Passar

✓ Executar: `python tests/audit_cenario_05_gpt_real.py`

✓ Coletar evidência de:
- Prompt enviado ao GPT
- JSON retornado pelo GPT
- Slots extraídos
- Decisão do router
- Estado final da sessão

✓ Documentar causa raiz (A/B/C/D/E)

### Se Cenário 05 PASS

✓ Replicar o sucesso no baseline P1 Robustez

### Se Cenário 05 FAIL

✓ Analisar resultado JSON

✓ Confirmar qual das 5 hipóteses é verdadeira

✓ Decidir se patch é necessário

---

**Setup Documentado:** 2026-06-23  
**Versão:** 1.0  
**Assinatura:** Claude Code — GPT-TEST-01
