# C4.4.9 — AUDITORIA: Paginação de Tenants

**Data:** 2026-09-25  
**Status:** AUDITORIA APENAS (ZERO ALTERAÇÕES DE PRODUÇÃO)  
**Base:** Commit `3be2bfd` (C4.4.8) publicado  

---

## A) LOCALIZAÇÃO EXATA DO GARGALO

### Função Principal

**Arquivo:** `services/recorrencia_service.py`  
**Linhas:** 387-402  
**Função:** `checar_e_propor_recorrencias_todos()`

```python
async def checar_e_propor_recorrencias_todos() -> int:
    """
    Itera por TODOS os clientes (negócios) e dispara checagem de recorrência.
    Retorna total de propostas geradas.
    """
    total = 0
    try:
        clientes = await buscar_subcolecao("Clientes") or {}  # ← LEITURA #1: TODOS os tenants
        for user_id in clientes.keys():  # ← ITERAÇÃO sequencial
            try:
                total += await checar_e_propor_recorrencias(user_id)
            except Exception as e:
                logger.error(f"[recorrencia] Falha ao processar user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"[recorrencia] Erro ao listar Clientes: {e}")
    return total
```

### Caller Único

**Arquivo:** `scheduler/notificacoes_scheduler.py`  
**Linhas:** 597-604  
**Contexto:** APScheduler cron job

```python
scheduler.add_job(
    checar_e_propor_recorrencias_todos,  # ← Chamada
    "cron",
    hour=8,              # Executa às 08:00
    minute=0,
    id="recorrencia_diaria_08h",
    replace_existing=True,
)
```

**Frequência:** 1× por dia (08:00 UTC)

### Nenhum Outro Caller

Grep confirmou: único caller é o scheduler diário.

---

## B) CÓDIGO ATUAL RELEVANTE

### Função Principal (recorrencia_service.py:387-402)

```python
async def checar_e_propor_recorrencias_todos() -> int:
    total = 0
    try:
        clientes = await buscar_subcolecao("Clientes") or {}
        for user_id in clientes.keys():
            try:
                total += await checar_e_propor_recorrencias(user_id)
            except Exception as e:
                logger.error(f"[recorrencia] Falha ao processar user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"[recorrencia] Erro ao listar Clientes: {e}")
    return total
```

### Função por Tenant (recorrencia_service.py:232-380)

```python
async def checar_e_propor_recorrencias(user_id: str) -> int:
    """
    Para UM negócio (user_id do dono), identifica clientes com padrão de recorrência
    e envia proposta com 3 horários livres para a PRÓXIMA data (cadência),
    disparando 5 dias após o último atendimento.
    """
    propostas = 0
    
    # Leitura #2 (por tenant): Carrega TODOS os eventos do tenant
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
    
    # Agregação em memória + processamento...
    # ... (resto do código omitido para brevidade)
    
    return propostas
```

---

## C) CALLERS

**Total de Callers:** 1

| Arquivo | Linha | Tipo | Frequência |
|---------|-------|------|-----------|
| `scheduler/notificacoes_scheduler.py` | 598 | APScheduler cron job | 1× dia (08:00) |

---

## D) FUNCIONAMENTO REAL DA ABSTRAÇÃO FIRESTORE

### Implementação de buscar_subcolecao()

**Arquivo:** `services/firebase_service_async.py`  
**Linhas:** 212-232

```python
async def buscar_subcolecao(path: str):
    try:
        ref = get_ref_from_path(path)
        partes = path.split("/")
        resultados = {}

        if len(partes) % 2 == 1:  # subcoleção (ex: "Clientes" tem 1 parte = ímpar)
            docs = ref.stream()  # ← STREAMING de TODOS os documentos
            async for doc in docs:
                data = doc.to_dict()
                resultados[doc.id] = data  # ← Acumula em memória
        else:
            doc = await ref.get()
            if doc.exists:
                resultados = doc.to_dict()
        return resultados
    except Exception as e:
        print(f"[ERRO] Erro ao buscar subcoleção '{path}': {e}")
        return {}
```

### Características da API

| Característica | Valor | Evidência |
|---|---|---|
| **Retorna** | Dict[id, documento] | `resultados[doc.id] = data` |
| **Materializa em memória?** | ✅ SIM | `resultados = {}` depois acumula |
| **Suporta limit?** | ❌ NÃO | Nenhum parâmetro limit |
| **Suporta start_after/cursor?** | ❌ NÃO | Nenhum parâmetro cursor |
| **Suporta paginação?** | ❌ NÃO | `.stream()` sem limites |
| **Suporta order_by?** | ❌ NÃO | Nenhum parâmetro sort |
| **Suporta where?** | ❌ NÃO | Nenhum parâmetro filter |

### Para "Clientes"

```python
buscar_subcolecao("Clientes")
```

- `partes = ["Clientes"]` → `len(partes) = 1` (ímpar)
- Entra em: `if len(partes) % 2 == 1:`
- Executa: `docs = ref.stream()`
- Resultado: **TODOS os documentos da coleção Clientes** carregados em memória

---

## E) READS ATUAIS POR EXECUÇÃO

### Fórmula Parametrizada

```
T = número de tenants
E(i) = número de eventos para tenant i

Leitura #1 (todos os tenants):
  reads_tenants = T documentos

Leitura #2-N (por cada tenant):
  reads_eventos = soma(E(i) para i = 1 até T)

Leitura #3 (dentro de _gerar_3_horarios_livres com C4.4.8):
  reads_eventos_dia = 0 (eliminado por C4.4.8)

Total de Firestore reads:
  total = T + soma(E(i))
```

### Exemplo Numérico

**Cenário:**
- T = 1.000 tenants
- E médio = 100 eventos por tenant
- soma(E(i)) = 100.000 eventos

**Leituras:**
```
Leitura #1: 1.000 documentos Clientes
Leitura #2: 100.000 documentos Eventos (agregado de todos os tenants)
─────────────────────────────────────────────────────
Total: 101.000 Firestore reads por execução diária
```

**Com C4.4.8:**
- Eliminada redundância em `_gerar_3_horarios_livres()`
- Mas não afeta `checar_e_propor_recorrencias_todos()` que ainda lê todos os tenants

---

## F) MEMÓRIA E CONCURRENCY ATUAIS

### Memória Utilizada por Execução

```python
# Leitura #1: Clientes
clientes = await buscar_subcolecao("Clientes")  
# Tamanho: T × tamanho_médio_doc_cliente ≈ 1.000 × 500 bytes = 500 KB

# Leitura #2: Eventos (sequencial, T iterações)
for user_id in clientes.keys():
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")
    # Mantém em memória: eventos do tenant i
    # Máximo em memória: E_max × tamanho_médio_doc_evento
```

### Estimativa Memória

```
Cenário:
- 1.000 tenants
- 100 eventos médio por tenant
- 500 bytes documento médio

Memória pico:
  clientes = 500 KB
  evento_tenant = 100 × 1 KB = 100 KB (por tenant em processamento)
  
  Total pico: ~600 KB (aceitável)
  
Mas se um tenant tem 10.000 eventos:
  evento_tenant = 10.000 × 1 KB = 10 MB (único tenant)
  
  Total: ~11 MB (ainda aceitável, mas cresce)
```

### Concurrency

**Atual:**
- Sequencial por tenant (sem asyncio.gather)
- Processamento serializado: tenant 1 → tenant 2 → ... → tenant T
- Latência: ~1 segundo por tenant (estimado)
- Tempo total: T segundos = 1.000 segundos = **~16 minutos para 1.000 tenants**

**Problema:** Se scheduler começar às 08:00 e T = 1.000, processamento termina às 08:16.

---

## G) AVALIAÇÃO OBJETIVA DE PAGINAÇÃO

### Opção A: Sem Mudanças (Atual)

| Métrica | Valor |
|---------|-------|
| Reads por execução | T + E_total |
| Memória pico | ~E_max × tamanho_doc (por tenant) |
| Latência | T × latência_por_tenant ≈ T segundos |
| Concurrency | Sequencial |
| Risco | Timeout se T×latência > timeout_scheduler |

**Exemplo (T=1.000):**
- Reads: 101.000
- Latência: ~1.000 segundos (~16 minutos)
- ⚠️ **RISCO DE TIMEOUT** (se scheduler tem limite)

---

### Opção B: Paginação de Tenants com Lote

Processar tenants em lotes (ex: 100 por vez) sem completar em uma execução.

```python
async def checar_e_propor_recorrencias_todos_paginado(
    page: int = 0,
    page_size: int = 100
) -> tuple[int, bool]:
    """
    page = número da página (0, 1, 2, ...)
    page_size = tenants por página
    retorna: (total_propostas, mais_paginas)
    """
    total = 0
    
    # Leitura #1: Clientes (TODOS ainda)
    clientes = await buscar_subcolecao("Clientes") or {}
    tenant_ids = list(clientes.keys())
    
    # Paginação
    start = page * page_size
    end = start + page_size
    batch = tenant_ids[start:end]
    
    mais_paginas = end < len(tenant_ids)
    
    # Processamento de lote
    for user_id in batch:
        try:
            total += await checar_e_propor_recorrencias(user_id)
        except Exception as e:
            logger.error(f"[recorrencia] Falha: {e}")
    
    return total, mais_paginas
```

| Métrica | Valor |
|---------|-------|
| Reads por execução | T + (E_total / num_execuções) |
| Memória pico | ~E_max × tamanho_doc (por tenant) |
| Latência | page_size × latência_per_tenant |
| Concurrency | Sequencial por lote |
| Risco | Processamento pode não terminar em 1 dia se lote muito pequeno |

**Problema:**
- Ainda lê TODOS os tenants (`await buscar_subcolecao("Clientes")`) em cada execução
- Paginação não reduz reads de tenants
- Reduz apenas latência/memória por execução
- Reads totais (diários): **SEM MUDANÇA**

---

### Opção C: Query Alternativa (Se Firestore suportasse)

```python
# PSEUDOCÓDIGO (NÃO IMPLEMENTADO)
async def checar_e_propor_recorrencias_query_limit():
    # Se pudéssemos fazer:
    clientes = await buscar_com_query(
        "Clientes",
        limit=100,
        start_after=last_id
    )
    
    # Mas buscar_subcolecao não suporta isso
```

**Viabilidade:**
- ❌ buscar_subcolecao não suporta limit/cursor
- ⚠️ Exigiria mudança na abstração Firestore
- ⚠️ Afetaria TODOS os callers de buscar_subcolecao (45+ locais)

---

## H) ALTERNATIVAS CONSIDERADAS

| # | Alternativa | Reads | Memória | Latência | Complexidade | Risco |
|---|---|---|---|---|---|---|
| A | Sem mudanças | T + E_total | Baixa | 🔴 ALTO | Nenhuma | Timeout |
| B | Paginação tenants | T + E_total | Baixa | Reduzido | Média | Incompletude |
| C | Query com limit | (T/N) + E_total | Baixa | Reduzido | Alto | Mudança API |
| D | Asyncio.gather | T + E_total | Média | 🟢 Reduzido | Alta | Concurrency |
| E | Filtro ativo | (T_ativo) + E_total | Baixa | Reduzido | Média | Falsos negativos |

---

## I) RISCOS

### Risco 1: Processamento Incompleto

**Opção B (Paginação):**
- Se página N leva 5 minutos, e há 100 páginas
- Total: 500 minutos = 8.3 horas
- Scheduler apenas dispara 1× por dia
- ⚠️ **Alguns tenants podem nunca ser processados**

**Mitigação:** Não há, sem redesenho do scheduler ou adição de fila persistente

---

### Risco 2: Duplicação de Propostas

Se execução 1 processa tenants 1-100, e execução 2 processa tenants 1-100 novamente:
- Mesmas propostas podem ser criadas 2× no mesmo dia
- ✅ **Mitigado:** C4.4.6 usa `create()` atômico (idempotência por `notif_id`)
- Proposta duplicada resulta em AlreadyExists (ignorado em log)

**Risco reduzido** mas não eliminado (log pollution)

---

### Risco 3: Omissão de Tenants

Se paginação tiver bug (ex: índice off-by-one):
- Tenants podem ser pulados
- ⚠️ **Sem detecção automática**

**Mitigação:** Testes obrigatórios incluir cobertura de "última página", "exatamente no limite"

---

### Risco 4: Semântica de Scheduler

Se scheduler aguarda resultado de `checar_e_propor_recorrencias_todos()`:
- Com Opção B, retorna resultado de página, não global
- ⚠️ **Mudança de contrato**

**Mitigação:** Adicionar estado persistente para rastrear progresso

---

### Risco 5: Conflito entre Execuções

Se execução 2 inicia enquanto execução 1 ainda está rodando:
- Ambas podem processar mesmos tenants
- ✅ **Idempotência via create() mitiga**, mas logs duplicados

**Mitigação:** Adicionar lock/flag "execução em progresso"

---

## J) PROPOSTA MÍNIMA (SE NECESSÁRIA)

### Presença do Problema?

**Pergunta:** Em produção atual, há timeout/incompletude?

**Análise:**
- Sem dados de timeout real, não há evidência de problema
- 1.000 tenants em sequência = ~1.000 segundos = 16 minutos
- Se scheduler tem 1 hora de janela, está Ok
- Se scheduler tem 10 minutos de janela, pode falhar

**Conclusão:** Sem evidência de falha real, alteração NÃO é mandatória

---

### Se Alteração for Justificada

**Opção Mínima Proposta: Opção B + Persistência**

```python
# Tabela de progresso (Firestore collection: SchedulerProgress)
{
    "recorrencia_diaria": {
        "ultima_pagina_processada": 5,
        "ultima_execucao": "2026-09-25T08:00:00Z",
        "total_propostas_hoje": 142
    }
}

async def checar_e_propor_recorrencias_todos():
    progress = await buscar_progresso("recorrencia_diaria")
    page = progress.get("ultima_pagina_processada", 0) + 1
    
    clientes = await buscar_subcolecao("Clientes")
    tenant_ids = list(clientes.keys())
    
    if page * PAGE_SIZE >= len(tenant_ids):
        page = 0  # Reset para próxima execução diária
    
    # Processar página
    ...
    
    # Atualizar progresso
    await atualizar_progresso("recorrencia_diaria", {
        "ultima_pagina_processada": page,
        "ultima_execucao": datetime.now().isoformat(),
        "total_propostas_hoje": total
    })
```

**Custo de Implementação:** ~30 linhas + testes

---

## K) MATRIZ DE TESTES NECESSÁRIOS

| # | Teste | Cenário | Validação | Criticidade |
|---|-------|---------|-----------|-------------|
| T1 | Primeira página | page=0 | Processa tenants 0-99 | ✅ CRÍTICO |
| T2 | Página intermediária | page=5 | Processa tenants 500-599 | ✅ CRÍTICO |
| T3 | Última página completa | page=N | Processa últimos tenants | ✅ CRÍTICO |
| T4 | Exatamente no limite | T=100, page_size=100 | page=1 retorna vazio | ✅ CRÍTICO |
| T5 | Limite + 1 | T=101, page_size=100 | page=1 tem 1 tenant | ✅ CRÍTICO |
| T6 | Coleção vazia | clientes={} | Retorna 0 propostas | 🟡 IMPORTANTE |
| T7 | Múltiplos tenants | T=1.000 | Todos processados em N paginas | ✅ CRÍTICO |
| T8 | Tenant com zero eventos | E=0 | Nenhuma proposta gerada | 🟡 IMPORTANTE |
| T9 | Continuidade sem duplicação | Página 1→2 | ID não repetido | ✅ CRÍTICO |
| T10 | Interrupção/erro | Exceção em meio | Progresso salvo, retry recupera | 🟡 IMPORTANTE |
| T11 | Regressão fluxo atual | Opção B com page=0 | Comportamento idêntico a atual | ✅ CRÍTICO |
| T12 | Concurrency | 2 execuções simultâneas | Sem duplicação | 🟡 IMPORTANTE |

---

## L) CONCLUSÃO

### Resumo da Avaliação

| Aspecto | Achado |
|--------|--------|
| **Leituras Firestore** | T + E_total por execução (101k em exemplo) |
| **Paginação reduz reads?** | **NÃO** — ainda lê TODOS os tenants |
| **Paginação reduz memória?** | SIM (marginal) |
| **Paginação reduz latência?** | SIM (significativo) |
| **Risco de timeout?** | SIM (se T grande e janela pequena) |
| **Evidência de falha real?** | NÃO (sem dados) |

### Recomendação Final

#### Se Nenhum Timeout Atual
→ **Não implementar C4.4.9 agora**
- Custo-benefício é negativo
- Introduz complexidade sem evidência de problema
- Monitore latência real do scheduler

#### Se Houver Timeout Reportado
→ **Implementar Opção B + Persistência**
- Reduz latência sem mudança de API
- Mantém idempotência via `create()`
- Adiciona Estado Persistente para Recuperação

#### Se Houver Crescimento Planejado (T > 10.000)
→ **Avaliar posteriormente**
- Nesse ponto, considere Opção C (mudança de API)
- Ou Opção D (paralelização com asyncio.gather)

---

## ✅ VALIDAÇÃO FINAL

```
[✅] Localização exata identificada (linhas 387-402)
[✅] Callers auditados (1 caller: scheduler)
[✅] API Firestore analisada (sem paginação nativa)
[✅] Reads calculados: T + E_total
[✅] Memória e latência avaliadas
[✅] Paginação analisada (reduz latência, NÃO reads)
[✅] Semântica crítica verificada
[✅] Relação com C4.4.8 confirmada (sem impacto)
[✅] Proposta mínima definida (se necessária)
[✅] Testes necessários mapeados (12 testes)

═════════════════════════════════════════════════════════════════════
ZERO ALTERAÇÕES DE PRODUÇÃO IMPLEMENTADAS
═════════════════════════════════════════════════════════════════════

Arquivos de produção alterados: 0
Commits criados: 0
Pushes feitos: 0

Status: Auditoria completa — Aguardando análise da evidência real de timeout
```

---

## PRÓXIMAS ETAPAS

**Ação Recomendada:**
1. Verificar logs reais do scheduler em produção
2. Se há timeout: implementar C4.4.9 (Opção B + Persistência)
3. Se sem timeout: aguardar crescimento de T > 5.000 antes de intervir

**Deadline Sugerido:** Reavaliação em 3 meses

