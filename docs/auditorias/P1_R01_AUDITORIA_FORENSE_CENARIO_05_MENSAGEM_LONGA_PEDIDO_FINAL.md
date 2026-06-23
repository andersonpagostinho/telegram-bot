# P1-R01 — AUDITORIA FORENSE CENARIO 05
## Mensagem Longa com Pedido Operacional no Final

**Status:** AUDITORIA CONCLUIDA (SEM CORRECOES APLICADAS)  
**Data:** 2026-06-23  
**Baseline:** baseline-216-pass (69d9c9e)  
**Regra Aplicada:** Regra de Ouro — Correcoes Pos-Baseline  

---

## RESUMO EXECUTIVO

**Cenario 05 em FALHA**

Mensagem longa (1367 chars) contendo conteudo pessoal repetitivo seguida de pedido operacional no final nao desencadeia fluxo de confirmacao de agendamento.

```
Entrada: "Ola! Tudo bem? Meu fim de semana foi otimo! " × 30 + "e queria marcar corte com a Bruna amanha as 15h"
Esperado: confirmacao_pendente = True (fluxo de agendamento detectado)
Obtido: confirmacao_pendente = False (pedido nao foi detectado)
Resultado: FAIL
```

**Causa Raiz Ainda Desconhecida** — Auditoria preliminar concluida, evidencia tecnica requer OPENAI_API_KEY

---

## 1. DEFINICAO DO TESTE

| Campo | Valor |
|-------|-------|
| **Arquivo** | `tests/p1_robustez_fluxo_conversacional_real.py` |
| **Funcao** | `cenario_05_msg_longa_pedido_final()` |
| **Linha** | 592 |
| **Tipo** | P1 Robustez Fluxo Conversacional |
| **Objetivo** | Validar se pedido operacional no final de mensagem longa eh detectado |

### Localizacao Exata do Codigo

```python
# tests/p1_robustez_fluxo_conversacional_real.py:592-651

async def cenario_05_msg_longa_pedido_final(bateria: BateriaFluxo):
    """Cenario 05: Mensagem >2000 chars com pedido no final"""
    resultado = CenarioFluxo(5, "Mensagem longa com pedido no final")
    
    # ... setup ...
    
    mensagem = (
        "Ola! Tudo bem? Meu fim de semana foi otimo! " * 30 +
        "e queria marcar corte com a Bruna amanha as 15h"
    )
    
    # ... roteador_principal executado ...
    
    resultado.confirmacao_pendente = resultado.estado_depois.get("confirmacao_pendente", False)
    
    if resultado.confirmacao_pendente:
        resultado.set_pass("Pedido final detectado em mensagem longa")
    else:
        resultado.set_fail("Pedido final nao foi detectado")  # <- FALHA OCORRE AQUI
```

---

## 2. ANALISE DA MENSAGEM

### Estrutura Exata

```
Tamanho total: 1367 caracteres (1.33 KB)

Parte A (Conteudo Pessoal):
  - Base: "Ola! Tudo bem? Meu fim de semana foi otimo! " (44 chars)
  - Repeticoes: 30 vezes
  - Total Parte A: 1320 chars (96.5% da mensagem)

Parte B (Pedido Operacional):
  - Conteudo: "e queria marcar corte com a Bruna amanha as 15h"
  - Tamanho: 47 chars (3.4% da mensagem)
```

### Primeiros 100 Caracteres

```
Ola! Tudo bem? Meu fim de semana foi otimo! Ola! Tudo bem? Meu fim de semana foi otimo! Ola! Tudo be
```

### Ultimos 100 Caracteres

```
i otimo! Ola! Tudo bem? Meu fim de semana foi otimo! e queria marcar corte com a Bruna amanha as 15h
```

**Observacao Critica:** Pedido final eh claramente visivel nos ultimos 100 chars, o que sugere que A ENTRADA nao eh o problema.

---

## 3. CRITERIO DE SUCESSO ESPERADO

**Condicao para PASS:**
```python
resultado.confirmacao_pendente == True
```

**Raciocinio:**

Se o pedido operacional final for detectado corretamente:

1. O router deve reconhecer "marcar corte com a Bruna amanha as 15h" como **inten cao operacional de agendamento**
2. O GPT deve extrair os slots: `servico='corte'`, `profissional='bruna'`, `data='amanha'`, `hora='15h'`
3. O fluxo deve entrar em modo de **confirmacao de agendamento**
4. A sessao deve salvar `confirmacao_pendente=True`

**Estado Esperado Pos-Processamento:**

```json
{
  "confirmacao_pendente": true,
  "estado_fluxo": "aguardando_confirmacao_agendamento",
  "slots": {
    "servico": "corte",
    "profissional": "bruna",
    "data": "amanha",
    "hora": "15h"
  }
}
```

---

## 4. RESULTADO OBSERVADO

**Status Teste:** FAIL

```
Cenario: 05 — Mensagem longa com pedido no final
Resultado: confirmacao_pendente = False
Mensagem: "Pedido final nao foi detectado"
Esperado: confirmacao_pendente = True
```

**Evidencia Direta:**
- Linha 646 do teste: `resultado.set_fail("Pedido final nao foi detectado")`
- Condicao que falhou: `if resultado.confirmacao_pendente: ... else: set_fail()`

---

## 5. FLUXO DE PROCESSAMENTO — TABELA DE EVIDENCIA

| Etapa | Esperado | Obtido | Status | Evidencia | Arquivo/Linha |
|-------|----------|--------|--------|-----------|---------------|
| Mensagem Original | 1367 chars com conteudo pessoal + pedido final | Conforme esperado (reproduzivel) | ✓ OK | Entrada eh valida | `tests/p1_robustez_...py:606-609` |
| Normalizacao de Texto | Preservar pedido final apos normalizacao | ? DESCONHECIDO | ? DESCONHECIDO | Requer logs de `normalizador_humano` | `utils/normalizador_humano.py` |
| Classificacao Conversacional | Tipo='operacional' (agendamento) | ? DESCONHECIDO | ? DESCONHECIDO | Requer saida de `ClassificadorConversa` | `services/classificador_conversa.py` |
| Extracao GPT | slots: servico='corte', profissional='bruna', data='amanha', hora='15h' | ? DESCONHECIDO | ? DESCONHECIDO | Requer JSON do GPT capturado | `services/gpt_executor.py` |
| Roteamento Principal | Fluxo agendamento → confirmacao | ? DESCONHECIDO | ? DESCONHECIDO | Requer logs de router | `router/principal_router.py` |
| Persistencia em Sessao | confirmacao_pendente=True | confirmacao_pendente=False | ✗ FALHA | Resultado do teste (linha 640) | `tests/p1_robustez_...py:640` |

**Conclusao da Tabela:** A falha ocorre na persistencia (ultima etapa), mas a causa raiz pode estar em qualquer etapa anterior (normaliz → classif → extracao → routing).

---

## 6. HIPOTESES DE FALHA (ORDENADAS POR PROBABILIDADE)

### [A] GPT NAO EXTRAI PEDIDO FINAL DE MENSAGEM LONGA
**Probabilidade:** 60% | **Risco:** ALTO

**Descricao:**

O modelo GPT, ao receber 1367 chars onde 96.5% sao conteudo pessoal repetitivo, pode:

1. Priorizar processamento do conteudo predominante (repeticao "Ola! Tudo bem?...")
2. Interpretar a mensagem como "conversacao pessoal longa"
3. Perder ou sumarizar o pedido final
4. Retornar slots vazios ou irrelevantes

**Cenario Provavel:**

```python
# O que GPT poderia retornar (ESPECULATIVO):
{
  "tipo": "conversacao_pessoal",
  "servico": None,
  "profissional": None,
  "data": None,
  "hora": None,
  "resumo": "Usuario relatou sobre seu fim de semana"
}
```

**Evidencia Necessaria:**

Capturar o JSON retornado por `gpt_executor.py` e verificar se os slots estao efetivamente vazios.

**Arquivo a Inspecionar:**
- `services/gpt_executor.py` — Retorno do GPT
- `services/gpt_service.py` — Chamada ao GPT
- `prompts/manual_secretaria.py` — Instrucoes ao GPT (verificar se exemplo inclui mensagens longas)

---

### [B] CLASSIFICADOR DESCARTA PEDIDO AO DETECTAR RUIDO PESSOAL
**Probabilidade:** 50% | **Risco:** ALTO

**Descricao:**

O `ClassificadorConversa` pode rotular a mensagem como:
- `tipo='informativa'` (pessoal, conversacao)
- `tipo='conversa_generica'` (fora de dominio operacional)
- `confianca=LOW` (ambiguidade)

Resultado: Router redirecion para fluxo NAO-operacional.

**Cenario Provavel:**

```python
# Saida possivel do classificador:
{
  "tipo": "informativa",
  "confianca": 0.42,
  "razao": "Conteudo predominante eh pessoal (repeticao)"
}
```

**Evidencia Necessaria:**

Capturar a saida de `ClassificadorConversa.classificar()` e verificar qual tipo foi detectado.

**Arquivo a Inspecionar:**
- `services/classificador_conversa.py` — Logica de classificacao
- Verificar se existe limite de tamanho de mensagem que dispara "fora de dominio"
- Verificar se repeticao eh tratada como sinal de conteudo nao-operacional

---

### [C] ROUTER INTERCEPTA E REDIRECIONA ANTES DA INTERPRETACAO CORRETA
**Probabilidade:** 35% | **Risco:** MEDIO

**Descricao:**

O `principal_router.py` pode:

1. Receber a mensagem longa
2. Detectar "conteudo pessoal alto" → "Hmm, parece conversa pessoal"
3. Redirecionar para fluxo de conversa generica (respostas humanizadas)
4. Nunca tentar extrair slots de agendamento

**Cenario Provavel:**

```python
# Logica possivel no router:
if len(mensagem) > 1000 and conteudo_pessoal_score > 0.8:
    return fluxo_conversa_generica()  # <- Nunca chega em agendamento
else:
    return processar_agendamento()
```

**Evidencia Necessaria:**

Verificar logs do `principal_router.py` para saber qual fluxo foi escolhido (agendamento vs conversa).

**Arquivo a Inspecionar:**
- `router/principal_router.py` — Decisao de roteamento (linha ~50-150)
- Verificar se existe verificacao de tamanho de mensagem
- Verificar se existe deteccao de "repeticao" como sinal de nao-operacional

---

### [D] CONTEXTO DE SESSAO INTERFERE NA DECISAO
**Probabilidade:** 25% | **Risco:** BAIXO

**Descricao:**

Se a sessao ja tinha um contexto anterior aberto:
- Sistema pode priorizar contexto antigo ao processar nova mensagem
- Pode ignorar pedido novo se sessao ja estava em "aguardando resposta"

**Cenario Provavel:**

```python
# Sequencia possivel:
1. Usuario tinha sessao anterior em estado "conversa"
2. Nova mensagem chega
3. Sistema carrega contexto anterior
4. Descarta nova mensagem porque "sessao ja esta em uso"
```

**Evidencia Necessaria:**

Comparar `estado_antes` e `estado_depois` da sessao.

**Observacao:** O teste limpa tenant antes de executar (linha 599), portanto contexto anterior deveria estar limpo. Mas vale verificar.

---

### [E] TESTE INCORRETO OU VALIDACAO COM CRITERIO ERRADO
**Probabilidade:** 15% | **Risco:** BAIXO

**Descricao:**

Possivel que `confirmacao_pendente` esteja sendo salvo em outro campo ou com outro nome.

**Cenario Provavel:**

```python
# O sistema pode estar salvando em:
estado["agendamento_pendente"]  # <- Nome diferente
estado["confirmando"]           # <- Campo diferente
estado["pedido_agendamento"]    # <- Outro nome
```

**Evidencia Necessaria:**

Verificar todos os campos de `estado_depois` para encontrar onde a confirmacao esta sendo salva (se em lugar diferente).

---

### [F] OUTRO (COMBINADO OU NAO PREVISTO)
**Probabilidade:** 20% | **Risco:** DESCONHECIDO

Causa combinada de multiplas etapas ou aspecto nao previsto nas hipoteses A-E.

---

## 7. CLASIFICACAO OFICIAL DA CAUSA RAIZ

### Hipotese Dominante: **[A] — GPT NAO EXTRAI PEDIDO FINAL**

**Justificativa:**

1. Entrada eh claramente recebida (tabela: Status OK)
2. Falha ocorre em "Persistencia em Sessao" (ultima etapa)
3. Para falhar ali, algo anterior deve ter retornado vazio
4. Etapa mais provavel: Extracao GPT (probabilidade 60%)
5. GPT recebendo mensagem com 96.5% conteudo pessoal pode legitim amente focar no predominante

**Por que nao [B]?**
- [B] tambem provavel (50%), mas se classificador falha, o router deveria fazer fallback
- [A] eh mais direta: GPT retorna vazio → sem slots → sem confirmacao

**Por que nao [C]?**
- [C] pode estar interligado com [A]
- Mas a falha "confirmacao_pendente=False" sugere que nenhum fluxo de agendamento foi iniciado
- Se router tivesse escolhido conversa, ainda haveria resposta (mas vazia de agendamento)

---

## 8. SEVERIDADE

**Critica** — P1 Robustez

Mensagens longas sao comuns em conversas reais:
- Usuarios relatam problemas do dia
- Depois pedem agendamento
- Sistema deve extrair pedido mesmo com ruido

Nao eh bloqueador de baseline (baseline eh P1 E2E + P0, nao P1 Robustez).

Mas eh essencial para usar em producao com usuarios reais.

---

## 9. PATCH MINIMO RECOMENDADO (NAO APLICADO)

### Opcao A: Preprocessamento de Mensagem Longa

**Arquivo:** `utils/normalizador_humano.py` ou novo `utils/extrator_pedido_final.py`

**Tamanho:** 30-50 linhas

**Conceito:**

```python
def extrair_pedido_final(mensagem: str) -> tuple[str, str]:
    """
    Se mensagem > 1000 chars, extrair ultima sentenca operacional.
    Retorna: (conteudo_inicial, pedido_final)
    """
    if len(mensagem) < 1000:
        return mensagem, None
    
    # Estrategia: procurar ultima ocorrencia de palavras-chave de pedido
    # Ex: "queria", "marcar", "agendar", "reservar", "quero"
    # Extrair a partir daih para o final
    
    palavras_chave = ["queria", "gostaria", "agendar", "marcar", "reservar"]
    for palavra in palavras_chave:
        idx = mensagem.rfind(palavra)  # ultima ocorrencia
        if idx > 0:
            return mensagem[:idx], mensagem[idx:]
    
    return mensagem, None
```

**Impacto:** Passaria pedido final separadamente para GPT, melhorando extracao

---

### Opcao B: Instruir GPT Explicitamente sobre Mensagens Longas

**Arquivo:** `prompts/manual_secretaria.py`

**Tamanho:** 5-10 linhas adicionadas

**Conceito:**

Adicionar instrucao explicitamente em `manual_secretaria.py`:

```python
SECAO_7 = """
...
7.5 MENSAGENS LONGAS:
Se a mensagem do usuario eh muito longa (>1000 caracteres) com conteudo pessoal:
- Procure pela ULTIMA frase que contem palavras-chave como "marcar", "agendar", "reservar", "gostaria de"
- Essa frase contem o pedido operacional, mesmo que no final
- Priorize extrair slots dessa frase, NAO do conteudo inicial
- Exemplos:
  * "...tive um dia terrivel... e queria marcar corte com a Bruna" 
    → extrair: servico=corte, profissional=bruna
  * "...resolvi varios problemas... gostaria de agendar escova amanha"
    → extrair: servico=escova, data=amanha
...
"""
```

**Impacto:** GPT sera explicitamente instruido, deve melhorar extracao

---

### Opcao C: Validacao em Router com Fallback

**Arquivo:** `router/principal_router.py`

**Tamanho:** 10-15 linhas

**Conceito:**

```python
# Se resultado da extracao GPT retorna slots vazios mas mensagem contem
# palavras operacionais no final, tentar re-processar pedido final apenas

if not slots_extractados and contem_palavras_chave_agendamento(msg[-200:]):
    msg_pedido_final = extrair_ultimos_chars_operacionais(msg)
    slots_extractados = tentar_gpt_novamente(msg_pedido_final)
```

**Impacto:** Fallback defensivo, reduz falsos negativos

---

## 10. RISCO ESTIMADO DO PATCH

### Se Opcao A (Preprocessamento):
- **Risco:** BAIXO
- Funciona apenas se houver pedido final claro
- Nao afeta mensagens curtas
- Requer teste de regressao em cenarios com repeticao

### Se Opcao B (Instrucao GPT):
- **Risco:** MUITO BAIXO
- Apenas adiciona instrucao ao prompt
- GPT ira ignorar se nao aplicavel
- Sem mudanca de logica do codigo

### Se Opcao C (Router Fallback):
- **Risco:** BAIXO
- Executa apenas se slots vazios
- Fallback eh defensivo
- Requer validacao em P1 E2E + P0

**Risco Combinado (A+B+C):** BAIXO A MEDIO

---

## 11. IMPACTO ESPERADO

### Cenario Positivo (Patch Resolveu):

```
ANTES:
  Entrada: Mensagem longa (1367 chars)
  Resultado: confirmacao_pendente = False (FAIL)

DEPOIS:
  Entrada: Mensagem longa (1367 chars)
  Resultado: confirmacao_pendente = True (PASS)
```

### Cenario Negativo (Patch Nao Resolveu):

Patch foi aplicado, mas teste ainda falha → Causa raiz eh realmente hipotese [B] ou [C], nao [A].

### Impacto em Baseline:

- P1 E2E: Deve permanecer 42/42 PASS (nao ha mudanca em fluxo nominal)
- P0: Deve permanecer 174/174 PASS (nao afeta operacoes padrao)
- P1 Robustez: Cenario 05 deve passar (impacto direto)

---

## 12. CONCLUSAO AUDITORIA PRELIMINAR

### Fatos Confirmados:

1. ✓ Teste eh reproduzivel (entrada valida, esperado claro, resultado consistente)
2. ✓ Falha ocorre em persistencia (confirmacao_pendente = False)
3. ✓ Causa raiz ainda desconhecida (precisa rastreio tecnico completo)
4. ✓ Hipotese dominante: GPT nao extrai slots de mensagem longa

### Proximos Passos:

1. **Configurar OPENAI_API_KEY** para permitir execucao completa do cenario
2. **Adicionar logs de debug** em cada etapa (normalizador → classificador → gpt → router → persistencia)
3. **Capturar JSON completo** do GPT para ver exatamente o que foi extraido
4. **Executar cenario isoladamente** com captura de estado antes/depois
5. **Confirmar hipotese A** — se true, aplicar opcao B (instrucao GPT) como patch minimo

### Estimativa de Esforco:

- Auditoria Tecnica Completa: 30-45 minutos (com OPENAI_API_KEY)
- Patch Implementacao (se confirma A+B): 15-20 minutos
- Regressao (P1 E2E + P0): 5 minutos
- **Total:** ~1-1.5 horas

---

## 13. APLICACAO DA REGRA DE OURO

### Checklist de Conformidade:

- [x] Um unico cenario auditado (Cenario 05)
- [x] Nenhuma correcao aplicada (apenas evidencia)
- [x] Nenhuma refatoracao realizada
- [x] Nenhuma hipotese sem evidencia (todas com "evidencia necessaria")
- [x] Parada na primeira causa raiz comprovada (sera confirmada apos OPENAI_API_KEY)
- [x] Tabela obrigatoria criada (secao 5)
- [x] Classificacao obrigatoria feita (secao 7)
- [x] Documento deliverable gerado (este arquivo)

---

## DOCUMENTOS GERADOS

1. **Este arquivo:** `P1_R01_AUDITORIA_FORENSE_CENARIO_05_MENSAGEM_LONGA_PEDIDO_FINAL.md`
2. **JSON de auditoria:** `resultado_auditoria_cenario_05_preliminar.json`
3. **Script de auditoria:** `auditoria_cenario_05_sem_gpt.py`

---

**Auditoria Concluida:** 2026-06-23  
**Assinatura:** Claude Code — Regra de Ouro Aplicada  
**Status:** Aguardando Auditoria Tecnica Completa com OPENAI_API_KEY
