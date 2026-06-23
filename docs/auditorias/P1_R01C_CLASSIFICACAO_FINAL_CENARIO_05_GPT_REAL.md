# P1-R01C — CLASSIFICAÇÃO FINAL CENÁRIO 05 COM GPT REAL

**Status:** ⏸️ BLOQUEADO — Erro de Importação em Código  
**Data:** 2026-06-23  
**Baseline:** baseline-216-pass (69d9c9e)  
**GPT Real:** ✅ Conectado (Smoke test PASSOU)  

---

## BLOQUEIO ENCONTRADO

### Erro ao Executar Auditoria

```
File: utils/priority_utils.py:6
ImportError: cannot import name 'db' from 'services.firebase_service_async'

Root cause:
- firebase_service_async.py NÃO exporta 'db'
- Módulo usa 'client' via get_db() do firestore_client.py
- priority_utils tentando importar 'db' que não existe
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

### 1. Resolver Erro de Importação (Pré-requisito)

```
Bug: utils/priority_utils.py importa 'db' de firebase_service_async
Solução: Usar get_db() de firestore_client.py

Impacto: Bloqueador para qualquer teste que use principal_router
```

### 2. Após Desbloquear: Re-executar Auditoria GPT

```bash
python tests/audit_cenario_05_gpt_real.py

Resultará em: resultado_audit_cenario_05_gpt_real.json
Permitirá: Classificação A/B/C/D/E com 100% certeza
```

### 3. Se Classificação = A: Aplicar Patch Mínimo

```python
# Em prompts/manual_secretaria.py
SECAO_7_5 = """
[instrução acima]
"""
```

### 4. Validar Com Regressão

```bash
python tests/p1_robustez_fluxo_conversacional_real.py

Cenário 05 deve passar (confirmacao_pendente = True)
Outros cenários devem manter status
```

---

## STATUS FINAL

| Aspecto | Status | Evidência |
|---------|--------|-----------|
| GPT Conectado | ✅ OK | Smoke test passou |
| Auditoria Executada | ⏸️ Bloqueado | Erro ImportError em priority_utils |
| Classificação | 🔄 Preliminar | Baseada em análise indireta (Hipótese A) |
| Patch Recomendado | ✅ Pronto | prompts/manual_secretaria.py:7.5 |
| Teste Pronto | ✅ Pronto | Aguardando desbloquio de importação |

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
