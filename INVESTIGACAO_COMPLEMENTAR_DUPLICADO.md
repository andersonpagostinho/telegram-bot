# INVESTIGAÇÃO COMPLEMENTAR: Causa Raiz da Resposta Genérica

**Status**: 🔍 READ-ONLY Analysis (sem alterações de código)  
**Data**: 2026-11-04  
**Referência**: `ANALISE_BUG_RESPOSTA_DUPLICADO.md`

---

## PARTE 1: RECONSTRUÇÃO DOS 6 CENÁRIOS

### ✅ CENÁRIO A: Evento pendente, primeira confirmação legítima

**Estado Inicial**:
- Evento NÃO existe em Firebase
- Contexto tem `aguardando_confirmacao_agendamento=True` (memória temporária)
- Dados armazenados em `MemoriaTemporaria`, NÃO em `Eventos`

**Operação Executada**:
```
Usuário: "Sim, confirma"
→ add_evento_por_gpt() chamada com confirmado=True
```

**Fluxo Esperado** ✨:
1. `add_evento_por_gpt()` chama `salvar_evento()` com `confirmado=True`
2. `salvar_evento()` pula o bloco NÃO confirmado (linha 288-302)
3. Entra no bloco confirmado (linha 267)
4. Chama `criar_evento_com_lock()`
5. `criar_evento_com_lock()` **NÃO encontra evento existente** (linha 570)
6. Cria locks, salva evento (linha 592), retorna sucesso (linha 604-610)
7. `salvar_evento()` retorna `True`
8. `add_evento_por_gpt()` recebe `True`, chama `montar_mensagem_confirmacao_sucesso()`
9. ✅ Envia mensagem formatada: "✨ Corte feminino com Bruna..."

**Resultado Atual Observado** ❌:
```
"Esse horário já está confirmado."
```

**Causa** 🔴:
Evento **ESTAVA em Firebase com `confirmado=False`** de uma execução anterior.

Quando `criar_evento_com_lock()` o encontra (linha 570), retorna `duplicado=True` SEM verificar se `confirmado=False`.

---

### ✅ CENÁRIO B: Evento já confirmado, repetição da mesma confirmação

**Estado Inicial**:
- Evento EXISTE em Firebase com `confirmado=True`
- Lock EXISTE e está marcado `status=confirmado`
- Mesmo event_id (client + prof + data)

**Operação Executada**:
```
Usuário tenta confirmar novamente (página recarregou, etc)
→ add_evento_por_gpt() chamada com confirmado=True
```

**Fluxo**:
1. `salvar_evento()` com `confirmado=True`
2. Chama `criar_evento_com_lock()`
3. Falha ao adquirir locks (já existem) → linha 472-501
4. Fallback idempotência: encontra evento existente (linha 482)
5. Retorna `{"ok": True, "duplicado": True}` (linha 485-492)
6. `salvar_evento()` retorna `"duplicado"` (linha 283)
7. `event_handler.py` recebe "duplicado" → mostra genérica (linha 1323)
8. ⚠️ Envia: "Esse horário já está confirmado."

**Resultado Atual** ⚠️:
```
"Esse horário já está confirmado."
```

**Análise**:
- ✅ Idempotência está funcionando (evento não foi duplicado)
- ❌ Mas não diferencia entre "confirmação legítima de pendente" vs "retentar confirmado"

---

### ✅ CENÁRIO C: Evento pendente, duas confirmações concorrentes

**Estado Inicial**:
- Evento EXISTE em Firebase com `confirmado=False` (salvo em primeira tentativa)
- Lock NÃO existe (eventos não confirmados não usam lock)
- Dois requests chegam simultaneamente

**Operação Executada**:
```
REQUEST 1: Usuário "Sim" 
REQUEST 2: Usuário "Sim" (ao mesmo tempo)
```

**Fluxo REQUEST 1**:
1. `salvar_evento()` com `confirmado=True`
2. Chama `criar_evento_com_lock()`
3. Adquire locks atomicamente → sucesso
4. Verifica conflito (linha 536-542) → nenhum
5. Verifica idempotência (linha 570) → encontra evento com `confirmado=False`
6. **[CRÍTICO] Retorna `duplicado=True` SEM verificar estado**
7. `salvar_evento()` retorna `"duplicado"`
8. Cliente recebe genérica

**Fluxo REQUEST 2**:
1. Tenta adquirir locks → FALHA (REQUEST 1 as criou)
2. Fallback idempotência → encontra evento
3. Retorna `duplicado=True` também

**Resultado** 🔴:
- Ambas as requisições veem "duplicado"
- Nenhuma diferencia entre "primeira confirmação" vs "retry"
- Cliente fica confuso: "Por que diz que já está confirmado se eu ainda não tinha confirmado?"

---

### ✅ CENÁRIO D: Evento confirmado, nova mensagem após timeout/falha

**Estado Inicial**:
- Evento EXISTE em Firebase com `confirmado=True`
- Lock EXISTE com `status=confirmado`
- Confirmação anterior SUCEDEU, mas resposta não chegou ao cliente (timeout de rede)

**Operação Executada**:
```
Cliente retorna e tenta confirmar novamente
→ add_evento_por_gpt() chamada
```

**Fluxo**:
1. Mesmo que Cenário B
2. Retorna `"duplicado"`
3. ✅ Correto: "já está confirmado"

**Resultado** ✅:
```
"Esse horário já está confirmado." — CORRETO NESTE CASO
```

**Análise**:
- ✅ Este é um caso onde a resposta genérica faz sentido
- ❌ Mas o código NÃO consegue distinguir entre C (primeira confirmação) e D (retentar)

---

### ✅ CENÁRIO E: Lock existente, mas evento ainda não confirmado

**Estado Inicial**:
- Lock CRIADO (status=reservado) do Cenário C onde REQUEST 1 adquiriu locks
- Evento COM `confirmado=False` (não foi atualizado para True)
- Situação de inconsistência

**Causa Raiz**:
`criar_evento_com_lock()` linha 570-589 encontra evento existente e retorna `duplicado=True` antes de atualizar `confirmado` para True.

**Resultado** 🔴:
- Locks marcados como `status=confirmado_idempotente` (linha 576)
- Evento não foi atualizado para `confirmado=True`
- Próxima tentativa encontra evento com `confirmado=False` ainda

---

### ✅ CENÁRIO F: Evento confirmado, lock ausente ou expirado

**Estado Inicial**:
- Evento EXISTE com `confirmado=True`
- Lock EXPIRADO (24h) ou DELETADO

**Operação Executada**:
```
Usuário tenta confirmar novamente após 25 horas
```

**Fluxo**:
1. `criar_evento_com_lock()` tenta adquirir locks → SUCESSO (foram expirados)
2. Verifica conflito (linha 536) → vê evento do mesmo profissional/hora
3. Retorna `conflito` (tipo_erro) (linha 544-552)
4. `salvar_evento()` retorna `"conflito_conflito"` (linha 279)
5. `event_handler.py` trata como conflito, mostra alternativas

**Resultado** ⚠️:
```
Mensagem de conflito (não confirmação)
```

**Problema** 🔴:
- Lock expirado levou a recrear locks
- Evento já confirmado não foi encontrado como "duplicado"
- Sistema oferece alternativas quando deveria dizer "já agendado"

---

## PARTE 2: VALIDAÇÃO DE IDEMPOTÊNCIA

### Definição Contratual de Idempotência

**Idempotência esperada**: Chamar a mesma operação N vezes com os mesmos parâmetros = mesmo resultado sem efeitos colaterais.

**Parâmetros que definem "mesma operação"**:
- tenant_id
- cliente_id
- profissional
- data
- hora_inicio
- hora_fim

**Chave de Idempotência Usada**:
```python
event_id = f"{cliente_id}_{profissional}_{data}".replace(" ", "_").lower()
```

**Problema**: NÃO inclui `hora_inicio` (foi removido em FIX-P0.4, linha 243-244).

Isso significa que se o cliente confirmar:
- "Corte com Bruna em 04/11 às 14h" 
- "Corte com Bruna em 04/11 às 15h" (mesmo dia, profissional, cliente)

Ambas teriam o **MESMO event_id** → segunda sobrescreve a primeira!

---

### Situações de Não-Idempotência Detectadas

**Problema 1**: Eventos com `confirmado=False` e `confirmado=True` têm o mesmo event_id

```
REQUEST A: salvar_evento(..., confirmado=False) 
→ cria Clientes/{tenant}/Eventos/{event_id} com confirmado=False

REQUEST B: salvar_evento(..., confirmado=True)
→ tenta criar com lock, encontra evento, retorna duplicado
→ NÃO ATUALIZA confirmado para True
→ Evento fica em limbo: `confirmado=False` mas com locks marcados como confirmados
```

**Problema 2**: Horas diferentes, mesmo dia e profissional

```
REQUEST A: "14:00 com Bruna em 04/11" → event_id = "cliente_bruna_2026-11-04"
REQUEST B: "15:00 com Bruna em 04/11" → event_id = "cliente_bruna_2026-11-04" (IGUAL!)
→ REQUEST B sobrescreve REQUEST A
→ Segundo evento perde informação de hora
```

---

## PARTE 3: VERIFICAÇÕES DE SEGURANÇA

### ✅ Isolamento por Tenant_ID

**Implementação**: Path usa `f"Clientes/{tenant_id}/Eventos/{event_id}"`

**Validação**:
- ✅ `criar_evento_com_lock()` recebe `dono_id` como tenant_id
- ✅ Locks também isolados por tenant: `f"Clientes/{dono_id}/AgendaLocks/{lock_key}"`
- ✅ `event_handler.py` obtém `dono_id` via `obter_id_dono(user_id)`

**Risco Encontrado** 🟠:
- `obter_id_dono(user_id)` pode retornar None em alguns fluxos
- Se None, causa erro em `salvar_evento()` linha 183-186 ✅ (bem tratado)
- Mas em `add_evento_por_gpt()`, se dono_id é None, **fallback para dados** (linha 634-635)
  ```python
  if not dono_id:
      dono_id = (dados or {}).get("tenant_id")
  ```
  - ⚠️ Se dados também não tem tenant_id → dono_id continua None
  - Depois passado para `criar_evento_com_lock()` → erro

---

### ✅ Idempotência sob Concorrência

**Implementação**:
- Locks criados atomicamente em uma TRANSAÇÃO Firestore (linha 296-297 em agenda_lock_service.py)
- Se qualquer lock já existe → transação falha, nenhum lock criado
- Fallback: verifica se evento já existe (linha 482)

**Verificação**:
- ✅ Transação bloqueia corretamente
- ✅ Fallback para evento existente funciona

**Problema** 🔴:
- Fallback NÃO diferencia entre evento com `confirmado=False` vs `confirmado=True`
- Ambos retornam mesmo `duplicado=True`

---

### ✅ Nenhuma Confirmação Duplicada

**Implementação**:
- Evento salvo uma única vez (lock garante)
- `confirmado` marcado uma única vez

**Problema** 🔴:
- Se evento existe com `confirmado=False`, não é ATUALIZADO para `confirmado=True`
- Fica em estado inconsistente

---

### ✅ Nenhum Evento Perdido

**Implementação**:
- Salva evento antes de liberar locks
- Locks marcados com `evento_id` para rastreamento

**Verificação**: ✅ Evento não é perdido

**Problema**: Mas fica com `confirmado=False` se idempotência é acionada

---

### 🔴 Locks Órfãos

**Definição**: Lock existe mas evento_id não aponta para evento válido

**Cenário de Risco**:
```
REQUEST 1: Adquire locks, encontra evento duplicado (confirmado=False)
           → Marca locks como "confirmado_idempotente" + evento_id
           → Retorna duplicado
           → Evento NÃO é atualizado para confirmado=True
           
REQUEST 2: Tenta confirmar novamente
           → Tenta adquirir locks
           → Falha: locks já existem
           → Fallback idempotência: evento ainda com confirmado=False
           → Locks apontam para evento_id mas evento está em estado inconsistente
```

**Limpeza de Órfãos**:
- `limpar_locks_orfaos()` existe (linha 75-114)
- Baseado em: `lock.evento_id == None` AND expirado
- ⚠️ Não limpa locks VÁLIDOS cujos eventos estão em estado inconsistente

---

### 🔴 Liberação Indevida de Lock de Outro Evento

**Cenário de Risco**:
Se `event_id` não inclui hora_inicio, múltiplos eventos do mesmo dia podem compartilhar ID.

```
REQUEST A: "14:00 com Bruna em 04/11"
REQUEST B: "15:00 com Bruna em 04/11" (mesmo event_id!)
→ REQUEST B sobrescreve REQUEST A em Firestore
→ Locks de REQUEST A apontam para evento_id de REQUEST B
→ Se REQUEST A é cancelado, pode liberar locks de REQUEST B
```

**Status** 🔴 ALTO RISCO: Falha de FIX-P0.4 comentada em agenda_lock_service.py linha 243-244

---

### ⚠️ Falhas Parciais entre Firestore e Resposta

**Cenário**:
1. Evento salvo em Firestore ✅
2. Locks marcados ✅
3. Transação de resposta começa...
4. FALHA DE REDE → resposta não chega ao cliente

**Resultado**:
- Evento confirmado em Firestore
- Cliente não vê a confirmação
- Cliente retenta → vê "já está confirmado" (idempotência salva)

**Avaliação** ✅: Seguro (idempotência recupera)

---

### ✅ Cancelamento e Reagendamento

**Cenários**:
1. Evento confirmado, cancela, reagenda
2. Evento pendente, cancela, refaz

**Verificação** ✅: 
- Evento cancelado muda `status=cancelado`
- Novo evento tem novo event_id (se data/hora diferentes) ou será rejeitado como duplicado (se iguais)

---

## PARTE 4: CONTRATO DE RESULTADO RECOMENDADO

### Atual (PROBLEMÁTICO)

```python
# salvar_evento() retorna:
True  # sucesso
"duplicado"  # idempotência, mas pode ser:
            # A) confirmação legítima de pendente
            # B) retentar confirmado
            # Não há como diferenciar
"conflito_{tipo}"  # conflito
False  # erro genérico
```

**Problema**: String `"duplicado"` é ambígua.

---

### RECOMENDADO (Novo Contrato)

#### Opção 1: Código Estruturado

```python
def salvar_evento(...) -> dict:
    return {
        "ok": bool,
        "status": "criado|confirmado_agora|ja_confirmado|conflito|erro",
        "evento_id": str,
        "motivo": str,
        "tipo_erro": str (se erro)
    }
```

**Mapeamento**:
- `status="criado"` → novo evento criado
- `status="confirmado_agora"` → evento pendente confirmado agora (PRIMEIRA VEZ)
- `status="ja_confirmado"` → evento já estava confirmado (idempotência)
- `status="conflito"` → conflito de horário
- `status="erro"` → erro geral

**Vantagem**: Sem ambiguidade. `event_handler.py` escolhe mensagem com precisão.

#### Opção 2: Booleanos Explícitos

```python
def salvar_evento(...) -> dict:
    return {
        "ok": bool,
        "criado_nesta_requisicao": bool,
        "evento_id": str,
        "motivo": str,
        ...
    }
```

**Problema**: Ainda ambíguo. "Criado nesta requisição" pode significar novo evento ou confirmação de pendente.

---

### Contrato Recomendado para `criar_evento_com_lock()`

```python
def criar_evento_com_lock(...) -> dict:
    return {
        "ok": bool,
        "status": "criado|duplicado_confirmado|duplicado_pendente_agora|conflito|erro",
        "evento_id": str,
        "motivo": str,
        ...
    }
```

**Valores de status**:
- `"criado"` → novo evento, locks criados, evento salvo → SHOW SUCCESS MESSAGE
- `"duplicado_confirmado"` → evento já confirmado → SHOW "JÁ CONFIRMADO"
- `"duplicado_pendente_agora"` → evento pendente sendo confirmado AGORA → SHOW SUCCESS MESSAGE
- `"conflito"` → conflito de horário com outro evento
- `"erro"` → erro geral

---

## PARTE 5: ARQUIVOS QUE PRECISARIAM MUDAR

### Tier 1: CRÍTICO (deve mudar)

| Arquivo | Função | Linha | O que mudar |
|---------|--------|-------|-----------|
| `services/agenda_lock_service.py` | `criar_evento_com_lock()` | 570-589 | Verificar estado `confirmado` do evento encontrado |
| `services/event_service_async.py` | `salvar_evento()` | 281-283 | Propagar status em vez de string "duplicado" |
| `handlers/event_handler.py` | `add_evento_por_gpt()` | 1322-1332 | Usar `status` para escolher mensagem |

### Tier 2: COMPLEMENTAR

| Arquivo | Função | Linha | O que mudar |
|---------|--------|-------|-----------|
| `services/agenda_lock_service.py` | `gerar_slot_key()` | 42-52 | Considerar incluir hora_inicio na chave (evitar sobreposição) |
| `services/event_service_async.py` | `salvar_evento()` | 245-247 | Validar colisões de event_id com horas diferentes |

---

## PARTE 6: TESTES NECESSÁRIOS

### Unit Tests (Isolado)

```python
test_criar_evento_com_lock_evento_novo()
→ Valida: status="criado"

test_criar_evento_com_lock_evento_confirmado_ja()
→ Valida: status="duplicado_confirmado"

test_criar_evento_com_lock_evento_pendente_confirmando_agora()
→ Valida: status="duplicado_pendente_agora" (NOVO)

test_idempotencia_sob_concorrencia()
→ 2 requests simultâneos devem resultar em 1 evento

test_colisao_event_id_horas_diferentes()
→ Dois eventos mesma data/prof/cliente mas horas diferentes
→ Não devem sobrescrever
```

### E2E Tests (Com Firestore Real)

```python
test_confirmacao_legítima_primeiro_fluxo()
→ Usuário não confirmou → confirma agora
→ Valida: mensagem = "✨ Corte feminino com Bruna / ✅ Horário confirmado!"

test_retentar_evento_ja_confirmado()
→ Usuário já confirmou → tenta confirmar novamente
→ Valida: mensagem = "Esse horário já está confirmado"

test_confirmacao_apos_timeout()
→ Evento confirmado mas resposta foi perdida
→ Cliente retenta
→ Valida: idempotência, mensagem = "já confirmado"
```

---

## PARTE 7: RISCOS DE REGRESSÃO

### 🔴 Alto Risco

1. **Mudança de contrato de retorno**
   - Qualquer código que faz `if resultado == "duplicado"` quebrará
   - Precisa auditar: `event_handler.py`, `gpt_service.py`, tests

2. **Lógica de atualização vs criação**
   - Se mudar para atualizar evento com `confirmado=False`, pode afetar:
     - Fluxos de cancelamento
     - Cálculos de duração
     - Validações de conflito

### 🟠 Médio Risco

3. **Locks órfãos**
   - Se mudar lógica de idempotência, locks podem ficar inconsistentes
   - Precisa garantir limpeza

4. **Concorrência**
   - Transações Firestore devem continuar atômicas
   - Qualquer mudança em `adquirir_locks_atomicamente()` pode quebrar

---

## PARTE 8: RESUMO EXECUTIVO

### Causa Raiz Comprovada

✅ **CENÁRIO A (primeira confirmação) gera mesmo resultado que CENÁRIO B (retentar)**

- Cenário A: Evento pendente (`confirmado=False`) → confirmação legítima
- Cenário B: Evento confirmado (`confirmado=True`) → retentar idempotente

**Ambos retornam `duplicado=True`** em `criar_evento_com_lock()` linha 571-589 **SEM VERIFICAR `confirmado`**

### O Código Não Sabe Diferenciar

```python
# Linha 570-589 de agenda_lock_service.py
evento_existente = await buscar_dado_em_path(evento_path)
if evento_existente:
    # ❌ Retorna "duplicado" sem verificar:
    #    evento_existente.get("confirmado") — é False? é True?
    return {"ok": True, "duplicado": True, ...}
```

### Consequência

- `salvar_evento()` retorna string `"duplicado"`
- `event_handler.py` mostra mensagem genérica **sempre**
- **NUNCA** mostra a mensagem formatada com sucesso

### Solução Estrutural

Introduzir status explícito que diferencia:
- `"criado"` → novo
- `"duplicado_pendente_agora"` → confirmação legítima (NOVO)
- `"duplicado_confirmado"` → retentar (NOVO)

Então `event_handler.py` usa status para escolher mensagem **sem ambiguidade**.

---

## CONCLUSÃO

A investigação confirmou a causa raiz identificada no documento anterior.

**Não há falsa alarma**: O bug existe e afeta **TODOS** os agendamentos que passam por confirmação pendente.

**Próximas ações**:
1. ✅ Análise completada
2. ⏸️ Aguardando aprovação
3. 🚫 NÃO iniciar FASE 7 ETAPA 2.2 sem resolver

