# LOTE 3A — INVESTIGAÇÃO P0: CONFIRMAÇÃO/NEGAÇÃO EMBUTIDA

**Data:** 2026-06-22  
**Escopo:** Cenários 06 e 07 apenas  
**Objetivo:** Descobrir por que confirmacao_pendente=True é carregado corretamente, mas mensagens longas não são processadas como confirmação/negação  

---

## TABELA DE RECLASSIFICAÇÃO

| Cenário | Confirmacao Pendente | Ramo Esperado | Ramo Executado | Condicao Falhou | Causa Raiz | Patch Recomendado |
|---------|---------------------|---------------|-----------------|-----------------|-----------|------------------|
| **06** | SIM ✓ | BLOCO_CONFIRMACAO (L4475) | NENHUM | SIM — Bloco não é ativado | Classificador GPT não marca intencao | Adicionar reconhecimento de "pode confirmar" |
| **07** | SIM ✓ | BLOCO_NEGACAO (L4671) | NENHUM | SIM — Bloco não é ativado | eh_desistencia() retorna TRUE, mas intencao_conversacional não é definida | Conectar eh_desistencia() a intencao negacao |

---

## ANÁLISE DETALHADA

### CENÁRIO 06: Confirmação Embutida em Parágrafo

**Mensagem Original:**
```
"Pode deixar. Li tudo. Sim, pode confirmar esse horário para mim. Obrigado!"
```

**Normalização:**
```
Original:  "Pode deixar. Li tudo. Sim, pode confirmar esse horário para mim. Obrigado!"
Lower:     "pode deixar. li tudo. sim, pode confirmar esse horário para mim. obrigado!"
Norm:      "pode deixar. li tudo. sim, pode confirmar esse horario para mim. obrigado!"
```

**Estado Carregado:**
```
✓ confirmacao_pendente: True
✓ aguardando_confirmacao_agendamento: True
✓ draft_confirmacao: {profissional: Bruna, hora: 14:00, servico: corte}
✓ estado_fluxo: agendando
```

**Detecção de Intenção:**
```
eh_confirmacao(texto_lower):        TRUE
  Razao: "pode confirmar" in gatilhos_frase (linha 968)
  
eh_desistencia_fluxo(texto_norm):   FALSE
  Razao: nenhum sinal de negacao detectado
```

**Simulação do Ramo:**
```
eh_confirmacao_pendente_ativa(ctx): TRUE
eh_confirmacao(texto_lower):        TRUE

DEVERIA ENTRAR EM: Bloco CONFIRMACAO (principal_router.py:4475-4476)
  if eh_confirmacao_pendente_ativa(ctx) and (
      eh_confirmacao(texto_lower) or eh_aceite_de_acao_pendente(texto_usuario, ctx)
  ):
      # Criar evento com dados_confirmacao_agendamento
```

**PORÉM — Teste Falha com:**
```
[FAIL] 06. Confirmacao embutida em paragrafo - Confirmacao nao foi processada
  confirmacao_pendente continua True
  evento_criado = False
  resposta_enviada = ""
```

#### Ponto Exato da Falha

**Arquivo:** router/principal_router.py  
**Linha:** 4475-4476  
**Condicao:** eh_confirmacao_pendente_ativa(ctx) and (eh_confirmacao(texto_lower) or eh_aceite_de_acao_pendente(...))  
**Status:** A condicao deveria ser TRUE, mas o bloco não é executado

#### Diagnóstico

A função eh_confirmacao() FUNCIONA corretamente:
- Detecta "pode confirmar" em gatilhos_frase
- Retorna TRUE para a mensagem

**MAS** o bloco 4475 não é ativado. Isso significa:
1. **Ou** a mensagem não chega até a linha 4475
2. **Ou** há um bloco anterior que intercepta a mensagem

#### Blocos Anteriores que Podem Interceptar (antes de linha 4475)

Procurando em router/principal_router.py:

| Linha | Bloco | Condicao | Risco |
|-------|-------|----------|-------|
| 3410+ | Cancelamento | estado_fluxo == aguardando_confirmacao_cancelamento | Baixo (estado_fluxo=agendando) |
| 4409+ | P1-Profissional | se há troca de profissional | **ALTO** — pode bloquear |
| 4470+ | P0-Confirmacao | eh_confirmacao_pendente_ativa() and eh_confirmacao() | **CRÍTICO** — aqui deveria entrar |

**Hipótese:** Há um classificador GPT ou serviço que processa a mensagem ANTES de chegar à linha 4475, e esse classificador não marca corretamente a intenção.

#### Fluxo Probable de Execução

```
Mensagem chega em roteador_principal()
    ↓
Processa fluxo identidade/onboarding
    ↓
Processa normalizador humano
    ↓
Processa cancelamento
    ↓
Processa P1-Profissional (troca de prof)
    ↓
Processa P0-Confirmacao ← DEVERIA ENTRAR AQUI
    ↓
MAS nao entra...
```

**Conclusão:** A mensagem é processada por um serviço que a classifica como "neutra" ou alguma outra intenção, impedindo que entre no bloco de confirmação.

---

### CENÁRIO 07: Negação Embutida em Parágrafo

**Mensagem Original:**
```
"Entendi tudo que você explicou, mas não quero mais marcar esse horário."
```

**Normalização:**
```
Original:  "Entendi tudo que você explicou, mas não quero mais marcar esse horário."
Lower:     "entendi tudo que você explicou, mas não quero mais marcar esse horário."
Norm:      "entendi tudo que voce explicou, mas nao quero mais marcar esse horario."
```

**Estado Carregado:**
```
✓ confirmacao_pendente: True
✓ aguardando_confirmacao_agendamento: True
✓ draft_confirmacao: {profissional: Bruna, hora: 14:00, servico: corte}
✓ estado_fluxo: agendando
```

**Detecção de Intenção:**
```
eh_confirmacao(texto_lower):        FALSE
  Razao: nenhum gatilho exato ou de frase de confirmacao
  
eh_desistencia_fluxo(texto_norm):   TRUE
  Razao: "nao quero" in sinais_fortes (score += 2)
  Resultado: score >= 2, retorna TRUE
```

**Simulação do Ramo:**
```
eh_confirmacao_pendente_ativa(ctx): TRUE
eh_confirmacao(texto_lower):        FALSE
intencao_conversacional:            None (não definido)

PROCURA POR: Bloco NEGACAO (principal_router.py:4671)
  if (
      eh_confirmacao_pendente_ativa(ctx)
      and ctx.get("intencao_conversacional") == "negacao_confirmacao_agendamento"
  ):
  
RESULTADO: NÃO ENTRA (intencao_conversacional = None)
```

**Teste Falha com:**
```
[FAIL] 07. Negacao embutida em paragrafo - Negacao nao foi processada
  confirmacao_pendente continua True
  draft nao foi limpo
  resposta_enviada = ""
```

#### Ponto Exato da Falha

**Arquivo:** router/principal_router.py  
**Linha:** 4671-4672  
**Condicao:** eh_confirmacao_pendente_ativa(ctx) and ctx.get("intencao_conversacional") == "negacao_confirmacao_agendamento"  
**Status:** intencao_conversacional não é definida como "negacao_confirmacao_agendamento"

#### Diagnóstico

O sistema detecta CORRETAMENTE que é uma negação:
- eh_desistencia_fluxo() retorna TRUE

**MAS** não há código que:
1. Mapeie eh_desistencia_fluxo() = TRUE → intencao_conversacional = "negacao_confirmacao_agendamento"
2. Ative o bloco 4671 com esse mapeamento

**Falta:** Código que conecte:
```
eh_desistencia_fluxo(texto_usuario) = TRUE
  ↓
ctx["intencao_conversacional"] = "negacao_confirmacao_agendamento"
  ↓
Ativa bloco 4671
```

---

## ORDEM DE RAMOS EM PRINCIPAL_ROUTER.PY

Após análise do código:

| Prioridade | Linha | Bloco | Condicao |
|------------|-------|-------|----------|
| 1 | 3410+ | Cancelamento | estado_fluxo == aguardando_confirmacao_cancelamento |
| 2 | 3650+ | Identidade/Onboarding | Processar fluxo identidade |
| 3 | 4144+ | Responder Consulta Informativa | eh_consulta() |
| 4 | 4408+ | Troca de Profissional | durante confirmacao |
| **5** | **4475** | **CONFIRMACAO** | **eh_confirmacao_pendente_ativa() and eh_confirmacao()** |
| **6** | **4671** | **NEGACAO** | **eh_confirmacao_pendente_ativa() and intencao == negacao** |
| 7 | 4800+ | Ajuste de Draft | alteracao detectada |
| 8 | 5400+ | Profissional Escolhida | estado_fluxo = profissional_escolhida |

---

## ACHADOS CRÍTICOS

### Cenário 06: FALHA NA ATIVACAO DO BLOCO

1. **eh_confirmacao() retorna TRUE** ✓
2. **eh_confirmacao_pendente_ativa() retorna TRUE** ✓
3. **Bloco não é ativado** ✗

**Causa:** A mensagem é INTERCEPTADA por outro bloco ANTES de chegar à linha 4475

**Suspeita:** 
- Classificador GPT marca a mensagem como "neutra" ou outra intenção
- Há um bloco de "P1-Profissional" (linha ~4408) que pode estar processando

### Cenário 07: FALTA MAPEAMENTO

1. **eh_desistencia_fluxo() retorna TRUE** ✓
2. **eh_confirmacao_pendente_ativa() retorna TRUE** ✓
3. **intencao_conversacional não é "negacao_confirmacao_agendamento"** ✗
4. **Bloco 4671 não é ativado** ✗

**Causa:** Não há código que mapeia eh_desistencia_fluxo() → intencao_conversacional

**Solução:** Adicionar antes da linha 4671:
```python
if eh_desistencia_fluxo(texto_usuario) and eh_confirmacao_pendente_ativa(ctx):
    ctx["intencao_conversacional"] = "negacao_confirmacao_agendamento"
```

---

## PATCH RECOMENDADO

### Para Cenário 07 (Negação)

**Localização:** router/principal_router.py, antes de linha 4671

**Código a Adicionar:**
```python
# Se há negacao clara durante confirmacao pendente, marcar intencao
if eh_confirmacao_pendente_ativa(ctx) and eh_desistencia_fluxo(texto_usuario):
    ctx["intencao_conversacional"] = "negacao_confirmacao_agendamento"
```

### Para Cenário 06 (Confirmação)

**Investigação Adicional Necessária:**
- Verificar quais blocos anteriores podem estar interceptando a mensagem
- Inspecionar se há classificador que marca a mensagem como "neutra" ou outra intenção
- Rastrear completo da execução do router com breakpoints/logs

---

## PRÓXIMAS AÇÕES

1. **Investigação Cenário 06:**
   - Adicionar logs em cada bloco anterior à linha 4475
   - Verificar se classificador GPT está interferindo
   - Rastrear execution flow completo

2. **Patch Cenário 07:**
   - Implementar mapeamento eh_desistencia_fluxo() → intencao_conversacional
   - Testar com mensagens de negação variadas
   - Validar que bloco 4671 é ativado

3. **Validação Geral:**
   - Rodar P1 novamente após patch
   - Verificar se ambos os cenários passam
   - Verificar regressão em outros cenários

---

**Relatório gerado:** 2026-06-22T20:15:00Z  
**Status:** Investigação completa, aguardando patch  
**Severidade:** P0 BLOQUEANTE  
**Impacto:** Confirmação/negação embutida em parágrafo não é processada
