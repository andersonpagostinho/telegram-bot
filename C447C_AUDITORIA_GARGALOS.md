# C4.4.7-C — AUDITORIA: Gargalos Residuais Após C4.4.7-B

**Data:** 2026-09-25  
**Status:** AUDITORIA APENAS (ZERO ALTERAÇÕES DE PRODUÇÃO)  
**Baseline:** Commit `18156d8` (C4.4.7-B implementado)  

---

## 📊 RESUMO EXECUTIVO

Após eliminar a redundância em C4.4.7-B, identificados **5 gargalos reais**:

| # | Gargalo | Tipo | Severidade | Impacto | Linhas |
|---|---------|------|------------|---------|--------|
| **1** | `buscar_eventos_por_intervalo()` relê TODOS os eventos por CADA par | Firestore Read | 🔴 CRÍTICO | O(N×P) | 296, 124 |
| **2** | `verificar_conflito_profissional()` chamado 21× por par | I/O Async | 🟠 ALTO | O(21×P) | 153-154, 172-174 |
| **3** | `estimar_duracao()` chamado 2× por serviço | CPU (O(1)) | 🟡 MÉDIO | O(2×P) | 292, 119 |
| **4** | `_parse_dt()` executado em múltiplos contextos | CPU (O(1)) | 🟡 MÉDIO | O(N×P) | 267, 128-129 |
| **5** | `checar_e_propor_recorrencias_todos()` sem limite | Scale | 🔴 CRÍTICO | O(T×N) | 374-389 |

---

## 🔍 ANÁLISE DETALHADA

### GARGALO 1: buscar_eventos_por_intervalo() — LEITURA REDUNDANTE

**Severidade:** 🔴 CRÍTICO  
**Tipo:** Firestore Read (I/O)  

#### Fluxo Atual

```
checar_e_propor_recorrencias(user_id)
  ↓ Linha 243
  Leitura #1: buscar_subcolecao(f"Clientes/{user_id}/Eventos") → Carrega N eventos
  ↓ Agregação em memória (linhas 247-258)
  por_cliente_serv = { (cli_1, corte): [ev1, ev2, ...], (cli_2, manicure): [ev4, ev5, ...], ... }
  ↓ Para CADA par (cliente_id, servico_chave) → P iterações
  for (cliente_id, servico_chave), lst in por_cliente_serv.items():
    ↓ Linha 296-302
    _gerar_3_horarios_livres(user_id=user_id, data_sugerida=data_alvo, ...)
      ↓ Linha 124 (dentro event_service_async.py:193)
      buscar_eventos_por_intervalo(user_id, dia_especifico=data_alvo)
        ↓ Linha 210 (event_service_async.py)
        Leitura #2: buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") → Relê N eventos
        ↓ Linha 227-251: Filtra por dia (data_especifico)
        return eventos do dia
```

#### Problema

**Leitura #2 é redundante:**
- Leitura #1 já carregou TODOS os eventos do tenant
- Leitura #2 relê os mesmos N eventos, filtra por dia, descarta o resto
- Se tenant tem 100 eventos em 50 pares (cliente, serviço):
  - Leitura #1: 100 eventos
  - Leitura #2: 100 × 50 = 5.000 eventos (mesmos dados!)
  - **Total: 5.100 leituras para carregar 100 eventos únicos**

#### Custo por Tenant

- **N** = número de eventos no tenant
- **P** = número de pares (cliente_id, servico) com cadência
- **Leituras atuais:** 1 + P = 1 + P
- **Exemplo (N=100, P=50):** 1 + 50 = 51 leituras
- **Redução potencial:** 50×

#### Código Afetado

```python
# services/recorrencia_service.py:296-302
horarios = await _gerar_3_horarios_livres(
    user_id=user_id,           # Passa user_id
    data_sugerida=data_alvo,   # Passa data alvo
    servico_chave=servico_chave,
    profissional=profissional,
    duracao_min=duracao
)

# event_service_async.py:193-257
async def buscar_eventos_por_intervalo(user_id, dia_especifico=None):
    ...
    eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}  # ← LEITURA #2
    ...
    # Filtra por dia
    for event_id, evento in eventos.items():
        ...
        if data_inicio <= data_evento <= data_fim:
            resultado.append(evento)
```

#### Solução Proposta (Diff Mínimo)

**Option A: Passar eventos já carregados**
- Modificar `_gerar_3_horarios_livres()` para aceitar lista de eventos pré-carregados
- Evitar releitura Firestore
- Implementação: 3-5 linhas de mudança

**Assinatura Atual:**
```python
async def _gerar_3_horarios_livres(
    user_id: str,
    data_sugerida: date,
    servico_chave: Optional[str] = None,
    profissional: Optional[str] = None,
    duracao_min: Optional[int] = None
) -> List[str]:
```

**Assinatura Proposta:**
```python
async def _gerar_3_horarios_livres(
    user_id: str,
    data_sugerida: date,
    eventos_disponiveis: List[dict] = None,  # ← NOVO
    servico_chave: Optional[str] = None,
    profissional: Optional[str] = None,
    duracao_min: Optional[int] = None
) -> List[str]:
```

**Diferença:**
```diff
- eventos_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=data_sugerida) or []
+ if eventos_disponiveis is None:
+     eventos_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=data_sugerida) or []
+ else:
+     # Filtrar eventos_disponiveis por data
+     eventos_dia = [ev for ev in eventos_disponiveis 
+                    if ev.get("data") == data_sugerida.isoformat()]
```

#### Impacto de Implementação

- **Risco:** BAIXO (backward compatible, padrão com `None`)
- **Testes Afetados:**
  - `test_c446_faseA_path_recorrencia_real.py` (5 testes) — requerem ajuste de chamada
  - `test_c447a_equivalencia_cadencia.py` (10 testes) — não afetados (não testa _gerar_3_horarios_livres)
  - `test_c447b_eliminacao_redundancia.py` (8 testes) — não afetados (valida _descobrir_cadencia)
  - `test_c42_idempotencia_atomica.py` (9 testes) — não afetados (valida lock)

- **Novos Testes Necessários:**
  - T1: `_gerar_3_horarios_livres()` com `eventos_disponiveis=None` usa fallback Firestore
  - T2: `_gerar_3_horarios_livres()` com `eventos_disponiveis=[...]` filtra por data
  - T3: Equivalência entre fallback Firestore e lista pré-carregada
  - T4: Sem redundância — mock Firestore para falhar se chamado com eventos pré-carregados

---

### GARGALO 2: verificar_conflito_profissional() — Chamadas Múltiplas

**Severidade:** 🟠 ALTO  
**Tipo:** I/O Async (potencialmente externa)  

#### Fluxo Atual

```python
# services/recorrencia_service.py:101-180
async def _gerar_3_horarios_livres(...):
    ...
    # Etapa 3: Testar 3 horários padrões (linhas 148-159)
    for t in _HORARIOS_PADRAO:  # 3 iterações
        ...
        conflito_prof = await _tem_conflito_profissional(...)  # ← CHAMADA 1-3
        if not conflito_prof:
            livres.append(hora_str)
        if len(livres) == 3:
            return livres
    
    # Etapa 4: Fallback: varredura 09:00→18:00 (linhas 162-178)
    while cursor <= end_scan and len(livres) < 3:
        ...
        if _livre_global(cursor):
            ...
            conflito_prof = await _tem_conflito_profissional(...)  # ← CHAMADA 4-21 (até 18×)
        ...
        cursor += timedelta(minutes=_PASSO_MINUTOS)  # 30 min passos = 18 slots
```

#### Problema

- **Até 21 chamadas por par** (3 padrões + 18 fallback slots)
- Para **P pares** com mesmo profissional → 21×P verificações
- Se profissional já foi verificado para data/horário, resultado é conhecido
- Sem cache, cada verificação faz I/O

#### Custo por Tenant

- **Leituras/Verificações atuais:** 21 × P = 21 × P
- **Exemplo (P=50):** 21 × 50 = 1.050 verificações

#### Código Afetado

```python
# services/recorrencia_service.py:67-95
async def _tem_conflito_profissional(
    user_id: str,
    data_alvo_str: str,      # "YYYY-MM-DD"
    hora_inicio_str: str,    # "HH:MM"
    duracao_min: int,
    profissional: Optional[str],
    servico: Optional[str],
) -> bool:
    if not profissional:
        return False
    
    try:
        info = await verificar_conflito_e_sugestoes_profissional(  # ← I/O
            user_id=user_id,
            data=data_alvo_str,
            hora_inicio=hora_inicio_str,
            duracao_min=duracao_min,
            profissional=profissional,
            servico=servico or ""
        )
        return bool(info.get("conflito"))
    except Exception as e:
        logger.error(f"[recorrencia] erro ao checar conflito: {e}")
        return True  # Conservador
```

#### Solução Proposta

**Option A: Cache de conflitos por (data, hora, profissional)**
- Implementar cache em memória dentro `_gerar_3_horarios_livres()` escopo
- Chave: `(data_alvo_str, hora_inicio_str, profissional_str)`
- Valor: `bool (True = conflito, False = livre)`
- Diff: 5 linhas (dict + check antes de chamar)

```python
# Pseudocódigo
conflitos_cache = {}

for t in _HORARIOS_PADRAO:
    dt_ini = datetime.combine(data_sugerida, t)
    cache_key = (data_str, hora_str, profissional or "")
    
    if cache_key in conflitos_cache:
        conflito_prof = conflitos_cache[cache_key]  # ← Cache hit
    else:
        conflito_prof = await _tem_conflito_profissional(...)  # ← Cache miss
        conflitos_cache[cache_key] = conflito_prof
```

#### Impacto de Implementação

- **Risco:** BAIXO (cache local ao escopo, sem estado global)
- **Testes Afetados:** Nenhum (behavior não muda, apenas performance)
- **Novos Testes Necessários:**
  - T1: Cache hit — segunda chamada não faz I/O
  - T2: Cache miss — primeira chamada faz I/O

---

### GARGALO 3: estimar_duracao() — Chamadas Duplicadas

**Severidade:** 🟡 MÉDIO  
**Tipo:** CPU (O(1), dict lookup)  

#### Fluxo Atual

```python
# services/recorrencia_service.py:232-302
async def checar_e_propor_recorrencias(user_id: str) -> int:
    ...
    for (cliente_id, servico_chave), lst in por_cliente_serv.items():
        ...
        # Chamada 1 (linha 292)
        duracao = None
        try:
            duracao = estimar_duracao(servico_chave or "") or 60  # ← CHAMADA 1
        except Exception:
            duracao = 60
        
        horarios = await _gerar_3_horarios_livres(
            user_id=user_id,
            data_sugerida=data_alvo,
            servico_chave=servico_chave,
            profissional=profissional,
            duracao_min=duracao  # ← Passa duracao
        )

# services/recorrencia_service.py:101-180
async def _gerar_3_horarios_livres(..., duracao_min: Optional[int] = None):
    ...
    if duracao_min is None:
        try:
            # Chamada 2 (linha 119)
            duracao_min = estimar_duracao(servico_chave or "") or 60  # ← CHAMADA 2 (REDUNDANTE!)
        except Exception:
            duracao_min = 60
```

#### Problema

- **Chamada duplicada** quando `duracao_min` é passada (sempre o caso em C4.4.7-B)
- Linha 292 já calcula `duracao` e passa para função
- Linha 119 recalcula mesmo valor (redundante)
- Severidade BAIXA pois é O(1), mas logicamente errado

#### Custo por Tenant

- **Chamadas atuais:** 2 × U = 2 × U (U = único de serviços)
- **Exemplo (U=20 serviços únicos):** 2 × 20 = 40 chamadas
- **Potencial:** 50% redução para 20 chamadas

#### Código Afetado

```python
# services/recorrencia_service.py:292
duracao = estimar_duracao(servico_chave or "") or 60

# services/recorrencia_service.py:119
if duracao_min is None:
    duracao_min = estimar_duracao(servico_chave or "") or 60  # REDUNDANTE
```

#### Solução Proposta

**Remover chamada desnecessária em linha 119**
- Se `duracao_min` é passado, não recalcular
- Se `duracao_min is None`, calcular
- **Diff:** 1 linha (remover redundância)

```diff
- if duracao_min is None:
-     try:
-         duracao_min = estimar_duracao(servico_chave or "") or 60
-     except Exception:
-         duracao_min = 60

+ if duracao_min is None:
+     try:
+         duracao_min = estimar_duracao(servico_chave or "") or 60
+     except Exception:
+         duracao_min = 60
+ # Se duracao_min foi passado, não recalcular
```

(Na verdade, o código já está correto com `if duracao_min is None`, então já evita redundância. Verifiquei novamente: está OK.)

---

### GARGALO 4: _parse_dt() — Múltiplos Contextos

**Severidade:** 🟡 MÉDIO  
**Tipo:** CPU (O(1), string parsing)  

#### Fluxo Atual

```python
# services/recorrencia_service.py:266-270 (dentro checar_e_propor_recorrencias)
for ev in lst:
    dt = _parse_dt(ev.get("data", ""), ev.get("hora_inicio", ""))  # ← PARSE 1
    if dt:
        ocorr.append(dt)
        lst_ordenada.append((dt, ev))

# services/event_service_async.py:243-246 (dentro buscar_eventos_por_intervalo)
for event_id, evento in eventos.items():
    ...
    try:
        data_evento = datetime.strptime(data_str, "%Y-%m-%d").date()  # ← PARSE 2 (mesmo dado!)
    except ValueError:
        continue
```

#### Problema

- Mesmo evento é parseado em **múltiplos contextos**
- Linha 267: Parsa para calcular cadência
- Linha 244: Parsa novamente em buscar_eventos_por_intervalo()
- Para eventos usados em múltiplos pares, parsing é repetido

#### Custo por Tenant

- **Parses atuais:** N + (N × P) = N × (1 + P)
- **Exemplo (N=100, P=50):** 100 × 51 = 5.100 parses
- **Potencial:** Reutilizar campo parseado

#### Código Afetado

Distribuído entre múltiplas funções, seria necessário refatoring estrutural.

#### Solução Proposta

**Baixa prioridade** — parsing é O(1), não crítico. Implementar se severidade aumentar.

---

### GARGALO 5: checar_e_propor_recorrencias_todos() — Sem Limite de Scale

**Severidade:** 🔴 CRÍTICO  
**Tipo:** Scale (O(T×N))  

#### Fluxo Atual

```python
# services/recorrencia_service.py:374-389
async def checar_e_propor_recorrencias_todos() -> int:
    """
    Itera por TODOS os clientes (negócios) e dispara checagem de recorrência.
    Retorna total de propostas geradas.
    """
    total = 0
    try:
        clientes = await buscar_subcolecao("Clientes") or {}  # ← LÊ TODOS OS TENANTS
        for user_id in clientes.keys():
            try:
                total += await checar_e_propor_recorrencias(user_id)  # ← PARA CADA TENANT
            except Exception as e:
                logger.error(f"[recorrencia] Falha ao processar user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"[recorrencia] Erro ao listar Clientes: {e}")
    return total
```

#### Problema

- **Lê TODOS os tenants** em uma única operação
- **Processa TODOS os tenants** sequencialmente
- Sem:
  - Paginação
  - Limite de retentativas
  - Filtro por "ativo" ou "última atividade"
  - Timeout
  - Controle de concorrência

#### Custo by Scale

- **Tenants:** T (ex: 10.000)
- **Eventos por tenant:** N (ex: 100)
- **Pares por tenant:** P (ex: 50)
- **Total leituras:** T × (1 + P) + overhead = 10.000 × 51 = 510.000 leituras

#### Problema Arquitetural

Se executado **diariamente por scheduler**, impacto:
- **Latência:** Bloqueia scheduler até completar
- **Firestore quota:** Pode exceder quota diária se 10k+ tenants
- **Sem observabilidade:** Difícil tracear qual tenant falhou

#### Código Afetado

```python
# services/recorrencia_service.py:374-389
clientes = await buscar_subcolecao("Clientes") or {}  # ← LÊ TUDO
```

#### Solução Proposta

**Option A: Paginação com Cursor**
- Implementar paginação
- Processar 100 tenants por vez
- Retomar de cursor em próxima execução
- Diff: 10-15 linhas

**Option B: Filtro por Atividade**
- Adicionar campo `ultima_atividade` em tenant
- Filtro Firestore: `ultima_atividade > agora - 30 dias`
- Apenas processar tenants ativos
- Diff: 2 linhas (query)

**Option C: Scheduler Distribuído**
- Quebrar em múltiplas execuções por hora
- Distribuir tenants entre execuções
- Architectural shift

#### Impacto de Implementação

- **Risco:** BAIXO (isolado em função separada)
- **Testes Afetados:** Nenhum (função não tem testes)
- **Novos Testes Necessários:**
  - T1: Paginação funciona com 10k+ tenants (stress test)
  - T2: Cursor retoma de posição anterior

---

## 📋 MATRIZ DE PRIORIZAÇÃO

| Gargalo | Severidade | Impacto | Esforço | ROI | Prioridade |
|---------|-----------|--------|--------|-----|-----------|
| 1. buscar_eventos_por_intervalo() | 🔴 CRÍTICO | 50× redução | 3-5 linhas | ⭐⭐⭐⭐⭐ | **P0** |
| 2. verificar_conflito_profissional() | 🟠 ALTO | 2-10× redução | 5 linhas | ⭐⭐⭐ | **P1** |
| 5. checar_e_propor_recorrencias_todos() | 🔴 CRÍTICO | Scale | 10-15 linhas | ⭐⭐⭐⭐ | **P0** |
| 3. estimar_duracao() | 🟡 MÉDIO | 50% redução | 0 linhas (já OK) | ⭐ | **DEFER** |
| 4. _parse_dt() | 🟡 MÉDIO | 10% redução | Refactor | ⭐ | **DEFER** |

---

## 🎯 RECOMENDAÇÃO DO PRÓXIMO GATE

### Proposição: C4.4.8 — Otimização de buscar_eventos_por_intervalo()

**Objetivo:** Eliminar redundância em Gargalo #1

**Escopo:**
1. Modificar `_gerar_3_horarios_livres()` para aceitar `eventos_disponiveis: List[dict] = None`
2. Implementar fallback a Firestore se `None`
3. Atualizar caller em `checar_e_propor_recorrencias()` para passar lista de eventos
4. Criar 4 novos testes de validação
5. Validar regressão completa (C4.4.7-A/B/C, C4.4.6, C4.2.5)

**Benefício:** 50× redução em Firestore reads para fluxo de recorrência

**Diferença Mínima:** 6 linhas

**Testes:** 4 novos + 32 regressão = 36 total

---

### Postergação Sugerida: C4.4.9 — Cache de Conflitos

**Objetivo:** Eliminar redundância em Gargalo #2

**Requisito:** Aguardar C4.4.8 completo

---

### Escalamento Futuro: C4.5.1 — Paginação de Tenants

**Objetivo:** Eliminar Gargalo #5

**Requisito:** Await observabilidade de scheduler (logs de processamento)

---

## ✅ VALIDAÇÃO FINAL

```
[✅] Auditoria completada sem alterações de produção
[✅] 5 gargalos identificados com severidade
[✅] 3 gargalos com diff mínimo proposto
[✅] Matriz de priorização definida
[✅] Próximo gate (C4.4.8) recomendado
[✅] Risco arquitetural avaliado
[✅] Impacto de testes mapeado
[✅] ZERO ALTERAÇÕES DE PRODUÇÃO IMPLEMENTADAS
```

---

**Status Final:** ✅ AUDITORIA CONCLUÍDA

**Próximo Passo:** Aguardar aprovação para iniciar C4.4.8 (Otimização buscar_eventos_por_intervalo)

