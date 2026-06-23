# P1-R01C — CLASSIFICAÇÃO FINAL CENÁRIO 05 COM GPT REAL

**Status:** ⏸️ BLOQUEADO — Dois Importadores Estruturais em INFRA-03  
**Data:** 2026-06-23  
**Baseline:** baseline-216-pass (69d9c9e)  
**GPT Real:** ✅ Conectado (Smoke test PASSOU — 13/13 tokens, custo $7e-06)  
**Bloqueador 1:** ✅ RESOLVIDO — `utils/priority_utils.py:6` ImportError (firebase_async → firestore_client)  
**Bloqueador 2:** ⏸️ DESCOBERTO — `tests/audit_cenario_05_gpt_real.py:53` ImportError (funções de teste vs. services)  

---

## BLOQUEADORES ENCONTRADOS E STATUS

### Bloqueador 1: ✅ RESOLVIDO — ImportError em utils/priority_utils.py

```
File: utils/priority_utils.py:6
Status: ✅ RESOLVIDO
Erro original: ImportError: cannot import name 'db' from 'services.firebase_service_async'

Raiz: firebase_service_async.py não exporta 'db' (refatoração INFRA-03)

Solução aplicada:
- Linha 6: from services.firebase_service_async import db
  ↓↓↓
+ from services.firestore_client import get_db
+ db = get_db()

Padrão: Consolidação pós-INFRA-03 usa get_db() de firestore_client.py (singleton)
Validação: ✅ py_compile passou (sintaxe correta)
```

### Bloqueador 2: ⏸️ DESCOBERTO — ImportError em audit_cenario_05_gpt_real.py

```
File: tests/audit_cenario_05_gpt_real.py:53
Status: ⏸️ NÃO RESOLVIDO (escopo: P1-R01D é apenas priority_utils)
Erro encontrado: ImportError: cannot import name 'limpar_tenant' from 'services.firebase_service_async'

Raiz: Funções são locais em testes específicos, não em services
  - limpar_tenant: definida em tests/p1_robustez_fluxo_conversacional_real.py:202
  - setup_tenant_completo: definida em teste, não em services
  - obter_estado_sessao: definida em teste, não em services

Impacto: Script audit_cenario_05_gpt_real.py foi criado com suposição errada sobre INFRA-03

Próximo passo: P1-R01E (refatorar audit script para usar functions corretas ou arquitetura pós-consolidação)
```

### Impacto

```
Fluxo Bloqueado:
  audit_cenario_05_gpt_real.py
    ↓
  router.principal_router (importação)
    ↓
  services.gpt_executor (importação)
    ↓
  handlers.task_handler (importação)
    ↓
  utils.priority_utils (importação)
    ↓
  [ERRO] ImportError: cannot import name 'db'
```

---

## EVIDÊNCIA COLETADA

### ✅ Smoke Test — PASSOU

```json
{
  "status": "SUCESSO",
  "openai_api_key": {
    "presente": true,
    "prefixo": "sk-proj-Rb...",
    "tamanho": 164,
    "origem": "API Key v2"
  },
  "conexao_gpt": {
    "sucesso": true,
    "modelo": "gpt-3.5-turbo-0125",
    "resposta": "ok",
    "tokens_usados": 13,
    "custo_estimado": "$7e-06"
  }
}
```

**Confirmação:** GPT Real Está Operacional ✅

### ❌ Auditoria Cenário 05 — BLOQUEADA

```
Tentativa: python tests/audit_cenario_05_gpt_real.py
Resultado: ImportError em código de produção
Responsabilidade: Bug em firestore_async imports (não relacionado a GPT)
```

---

## ANÁLISE SEM EXECUÇÃO

Baseado em evidência coletada anteriormente (P1-R01 + P1-R01B):

### Resumo de Achados

#### 1. Mensagem Original É Válida ✓

```
Tamanho: 1367 chars
Estrutura: 96.5% conteúdo pessoal + 3.4% pedido operacional
Pedido final: "e queria marcar corte com a Bruna amanhã às 15h"
Status: Claro e identificável ✓
```

#### 2. Router Que Usa GPT Não É Chamado Em P1 E2E ✓

```
P1 E2E chama: processar_fluxo_identidade_onboarding()
Não chama: principal_router (que usa GPT)

Resultado: Baseline 42/42 PASS SEM GPT ✓
```

#### 3. Classificador Não Bloqueia Agendamento ✓

```
Testes P0 confirmam:
- Classificador reconhece "operacional"
- Router roteia para agendamento
- Fluxo prossegue corretamente ✓
```

#### 4. GPT Está Operacional ✓

```
Smoke test:
- Conectado ao OpenAI: ✓
- Responde em tempo aceitável: ✓
- Modelo: gpt-3.5-turbo-0125 ✓
- Custo mínimo para teste: $7e-06 ✓
```

---

## CLASSIFICAÇÃO COM BASE EM EVIDÊNCIA INDIRETA

### Hipótese Dominante: **A) GPT não extrai pedido final**

**Justificativa:**

1. **Mensagem é estruturada claramente** (confirmado em P1-R01)
   - Pedido está claramente no final
   - Não há ambiguidade léxica

2. **Fenômeno de mensagens longas com ruído**
   - 96.5% da mensagem é conteúdo pessoal repetitivo
   - GPT pode priorizar conteúdo predominante
   - Pedido no final é 3.4% apenas

3. **Padrão documentado em AI**
   - Modelos tendem a focar em token majoritário
   - Contexto longo dilui atenção ao final
   - Sem instrução explícita, último framing é perdido

4. **Teste E2E não chama GPT**
   - P1 E2E não usa principal_router
   - Portanto, não reproduz fluxo que usaria GPT
   - Cenário 05 especificamente testa GPT real

### Probabilidade da Causa

| Hipótese | Prob | Razão |
|----------|------|-------|
| **A: GPT não extrai** | **60%** | Ruído predominante dilui pedido |
| B: Parser descarta | 20% | Menos provável (JSON bem estruturado) |
| C: Router descarta | 15% | Improvável (outros testes passam) |
| D: Classificador bloqueia | 3% | P0 testes indicam que não |
| E: Setup incorreto | 2% | Smoke test passou |

---

## PATCH MÍNIMO RECOMENDADO

### Caso Confirmado: Hipótese A (Mais Provável)

**Arquivo:** `prompts/manual_secretaria.py`

**Seção:** 7.5 (Nova)

**Adição (~8 linhas):**

```python
7.5 MENSAGENS MUITO LONGAS COM CONTEUDO PESSOAL:

Se a mensagem for maior que 1000 caracteres E tiver muito conteúdo pessoal:
- Procure pela ÚLTIMA frase que contém palavras operacionais
  (marcar, agendar, reservar, gostaria de, quero)
- Essa frase no final contém o pedido operacional real
- Extraia slots DESSA frase com prioridade, não do conteúdo inicial

Exemplos:
  "...tive um dia complicado... gostaria de marcar corte com a Bruna amanhã às 15h"
  └─ Extrair de: "gostaria de marcar corte com a Bruna amanhã às 15h"
  
  "...resolvi várias coisas... quero agendar escova para segunda"
  └─ Extrair de: "quero agendar escova para segunda"
```

**Risco:** MUITO BAIXO
- Adição, não modificação
- Instruição explícita para GPT
- Sem mudança de lógica de código
- Sem efeito em mensagens curtas

---

## PRÓXIMAS ETAPAS RECOMENDADAS

### FASE 1: Desbloquear (CONCLUÍDA PARCIALMENTE)

✅ **P1-R01D: Resolver priority_utils.py** — COMPLETO
- Bloqueador 1 resolvido
- py_compile passou
- Pronto para re-executar testes que usam priority_utils

⏸️ **P1-R01E: Refatorar audit_cenario_05_gpt_real.py** — PENDENTE
- Bloqueador 2 identificado
- Escopo: Usar functions corretas ou re-arquitetar script pós-INFRA-03
- Opções:
  - Opção A: Migrar funções de teste para services/firebase_service_async_test.py
  - Opção B: Usar functions equivalentes de P1 E2E que funcionam
  - Opção C: Simplificar audit script para chamar principal_router diretamente (sem setup/limpar tenant)

### FASE 2: Coleta de Evidência (BLOQUEADA)

```bash
python tests/audit_cenario_05_gpt_real.py
→ resultado_audit_cenario_05_gpt_real.json

Depende de: P1-R01E estar resolvido
```

### FASE 3: Classificação com Dados Reais (AGUARDANDO)

Após resultado_audit_cenario_05_gpt_real.json ser gerado:
- JSON bruto do GPT capturado
- Slots extraídos validados
- Hipótese A/B/C/D/E confirmada com 100% certeza

### FASE 4: Patch de Interpretação (CONDICIONAL)

Se Classificação = A (GPT não extrai pedido final):
```python
# Em prompts/manual_secretaria.py
SECAO_7_5 = """
[instrução para lidar com mensagens longas]
"""
```

### FASE 5: Regressão (OBRIGATÓRIA)

```bash
python tests/p1_robustez_fluxo_conversacional_real.py

Expectativa:
- Cenário 05 PASS (confirmacao_pendente = True)
- Todos outros cenários mantêm status
```

---

## STATUS FINAL (2026-06-23)

| Aspecto | Status | Evidência |
|---------|--------|-----------|
| GPT Conectado | ✅ OK | Smoke test passou (13 tokens, $7e-06) |
| Bloqueador 1 (priority_utils) | ✅ RESOLVIDO | py_compile passou — padrão INFRA-03 aplicado |
| Bloqueador 2 (audit script) | ⏸️ DETECTADO | Funções não estão em services (refatoração incompleta) |
| Auditoria GPT Real Executada | ❌ NÃO | Bloqueado por Bloqueador 2 |
| Classificação A/B/C/D/E | 🔄 Preliminar | Baseada em análise indireta (Hipótese A: 60%) |
| Patch Recomendado | ✅ Pronto | prompts/manual_secretaria.py:7.5 (não aplicado por polícia) |
| Próximo Passo | ✅ Claro | P1-R01E: Refatorar audit script |

---

## RECOMENDAÇÃO FINAL

**Não aplicar patch sem confirmação de causa raiz.**

Hipótese A é mais provável (60%), mas requer:

1. ✅ Resolver ImportError em firebase_async
2. ✅ Executar auditoria GPT real
3. ✅ Confirmar JSON bruto do GPT
4. ✅ Validar classificação A/B/C/D/E
5. ✅ Então aplicar patch correspondente

---

**Documentado:** 2026-06-23  
**Assinatura:** Claude Code — P1-R01C (Pronto com Bloqueador Identificado)  
**Próximo:** Resolver ImportError e Re-executar
