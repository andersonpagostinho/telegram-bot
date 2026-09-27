# C4.4.7-B — Auditoria: Redundância de Leitura Firestore

**Data:** 2026-09-25  
**Status:** AUDITORIA APENAS (sem alterações)  
**Baseline:** Commit `9c08266` (C4.4.7-A)  

---

## A) DIAGNÓSTICO: LEITURA REDUNDANTE ATUAL

### Fluxo Atual (com redundância)

```
checar_e_propor_recorrencias(user_id: str)
  ↓
  Linha 246: eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")  ← LEITURA #1
  ↓
  Linhas 250-261: Agregar por (cliente_id, servico_chave)
  ↓
  por_cliente_serv = {
    ("cli_1", "corte cabelo"): [ev1, ev2, ev3],
    ("cli_2", "manicure"): [ev4, ev5],
    ...
  }
  ↓
  Linha 265: for (cliente_id, servico_chave), lst in por_cliente_serv.items():
    ↓
    Linha 282: cadencia = await _descobrir_cadencia(user_id, cliente_id, servico_chave)
      ↓
      _descobrir_cadencia():
        Linha 197: eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")  ← LEITURA #2 (REDUNDANTE!)
        ↓
        Linhas 202-213: Filtrar novamente por cliente_id e servico_chave
        ↓
        Calcular cadência
```

### Problema

**Leitura #2 é totalmente redundante:**
- `checar_e_propor_recorrencias()` já carregou todos os eventos uma vez (Leitura #1)
- `checar_e_propor_recorrencias()` já filtrou e agrupou por (cliente_id, servico_chave)
- `_descobrir_cadencia()` carrega TODOS os eventos novamente (Leitura #2)
- Depois filtra novamente para o mesmo (cliente_id, servico_chave)

**Custo por iteração:**
- Leitura #1: N eventos lidos
- Leitura #2: N eventos lidos **novamente** para cada (cliente_id, servico_chave) par

**Se 1 negócio tem 1000 eventos em 50 pares diferentes:**
- Leitura #1: 1 × 1000 = 1000 eventos
- Leitura #2: 50 × 1000 = 50.000 eventos (mesmos dados!)

**Total: 51.000 leituras de documento Firestore por execução**

---

## B) PROPOSTA: DIFF MÍNIMO

### Alteração 1: Assinatura de `_descobrir_cadencia()`

**ANTES:**
```python
async def _descobrir_cadencia(
    user_id: str,
    cliente_id: str,
    chave_servico: str
) -> Optional[int]:
    # Busca TODOS os eventos (você pode otimizar p/ 180 dias, etc.)
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
    # filtra por cliente_id e serviço
    ...
```

**DEPOIS:**
```python
async def _descobrir_cadencia(
    lst: List[dict],
    chave_servico: str
) -> Optional[int]:
    # lst já contém apenas eventos do par (cliente_id, servico_chave)
    # Nenhuma leitura Firestore necessária
    ...
```

### Alteração 2: Chamada em `checar_e_propor_recorrencias()`

**ANTES (linha 282):**
```python
cadencia = await _descobrir_cadencia(user_id, cliente_id, servico_chave)
```

**DEPOIS (linha 282):**
```python
cadencia = await _descobrir_cadencia(lst, servico_chave)
```

### Alteração 3: Corpo de `_descobrir_cadencia()`

**ANTES (linhas 196-213):**
```python
eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
ocorrencias: List[datetime] = []
chave_norm = unidecode.unidecode(chave_servico.lower())

for _id, ev in eventos.items():
    if not isinstance(ev, dict):
        continue
    if str(ev.get("cliente_id") or "").strip() != str(cliente_id).strip():
        continue
    desc = _normalizar_servico(ev.get("descricao", ""))
    if chave_norm not in desc:
        continue

    dt = _parse_dt(ev.get("data", ""), ev.get("hora_inicio", ""))
    if dt:
        ocorrencias.append(dt)
```

**DEPOIS (linhas 196-213):**
```python
# lst já filtrado por (cliente_id, servico_chave) em checar_e_propor_recorrencias()
ocorrencias: List[datetime] = []
chave_norm = unidecode.unidecode(chave_servico.lower())

for ev in lst:
    if not isinstance(ev, dict):
        continue
    # Validação redundante removida: cliente_id e servico já foram filtrados
    # Apenas validar serviço novamente (segurança: checar normali zação)
    desc = _normalizar_servico(ev.get("descricao", ""))
    if chave_norm not in desc:
        continue

    dt = _parse_dt(ev.get("data", ""), ev.get("hora_inicio", ""))
    if dt:
        ocorrencias.append(dt)
```

---

## C) ASSINATURA NOVA PROPOSTA

### Antes
```python
async def _descobrir_cadencia(
    user_id: str,
    cliente_id: str,
    chave_servico: str
) -> Optional[int]:
```

### Depois
```python
async def _descobrir_cadencia(
    lst: List[dict],
    chave_servico: str
) -> Optional[int]:
```

### Chamada
```python
# ANTES:
cadencia = await _descobrir_cadencia(user_id, cliente_id, servico_chave)

# DEPOIS:
cadencia = await _descobrir_cadencia(lst, servico_chave)
```

---

## D) TESTES QUE DEVERÃO SER EXECUTADOS

### Testes Existentes (TODOS devem passar)

**1. C4.4.7-A (novo):**
```
tests/test_c447a_equivalencia_cadencia.py
  • 10 testes de equivalência
  • Deve passar 10/10 (não depende de assinatura)
```

**2. C4.4.6 (Fase A):**
```
tests/test_c446_faseA_path_recorrencia_real.py
  • 5/5 testes esperados PASS
  • Valida path correto e scheduler integração
```

**3. C4.2.5 (Regressão):**
```
tests/test_c42_idempotencia_atomica.py
  • 9/9 testes esperados PASS
  • Valida C4.2.5 não regrediu
```

### Novos Testes Necessários para C4.4.7-B

**Teste 1: Equivalência com lst vs Firestore**
```python
test_c447b_equivalencia_lst_vs_firestore()
  • Criar eventos no Firestore
  • Chamar _descobrir_cadencia(lst, chave) com lst pré-carregado
  • Chamar função antiga (se mantida) com (user_id, cliente_id, chave)
  • Validar resultado idêntico
```

**Teste 2: Sem leitura Firestore**
```python
test_c447b_sem_leitura_firestore()
  • Mock buscar_subcolecao() para falhar
  • Chamar _descobrir_cadencia(lst, chave) com dados locais
  • Deve calcular cadência sem acessar Firestore
  • Anterior: teria falhado (dependia de Firestore)
```

**Teste 3: Regressão checar_e_propor_recorrencias()**
```python
test_c447b_regressao_propor_recorrencias()
  • Criar cenário idêntico a C4.4.6
  • Executar checar_e_propor_recorrencias()
  • Validar propostas criadas == antes
  • Validar timing (menos Firestore lido = mais rápido, idealmente)
```

---

## E) RISCOS E REGRESSÕES POTENCIAIS

### Risco 1: Validação de Normali zação

**Problema:** Se `lst` contiver eventos já filtrados, pode-se pular validação de `cliente_id`.

**Mitigação:** Manter validação de `chave_norm` (linha 208) mesmo em lst.

**Teste:** `test_c447b_normalizacao_mantida()`

---

### Risco 2: Eventos Inválidos

**Problema:** Se `lst` contiver eventos sem data/hora, precisam ser descartados.

**Mitigação:** Manter validação `_parse_dt()` (linha 211).

**Teste:** `test_c447b_eventos_sem_data_ignorados()`

---

### Risco 3: Mudança de Semântica

**Problema:** `_descobrir_cadencia()` está sendo usada apenas em 1 local (linha 282).

**Validação:** Grep confirma única chamada.

**Teste:** Grep confirma nenhuma outra chamada após mudança.

---

### Risco 4: Performance

**Problema:** Se implementação for lenta, pode degradar performance.

**Validação:** Ciclo é O(n) em vez de O(n²), deve ser mais rápido.

**Teste:** Benchmark (opcional, não obrigatório).

---

## F) CONFIRMAÇÃO: NENHUM ARQUIVO FOI ALTERADO

```
✅ services/recorrencia_service.py — NÃO ALTERADO
✅ tests/test_c447a_equivalencia_cadencia.py — NÃO ALTERADO
✅ tests/test_c446_faseA_path_recorrencia_real.py — NÃO ALTERADO
✅ tests/test_c42_idempotencia_atomica.py — NÃO ALTERADO
✅ scheduler/* — NÃO ALTERADO
✅ handlers/* — NÃO ALTERADO
✅ router/* — NÃO ALTERADO
✅ Firestore schema — NÃO ALTERADO

Status: AUDITORIA SOMENTE (zero alterações)
```

---

## RESUMO: REDUÇÃO DE LEITURA FIRESTORE

| Métrica | Antes | Depois | Redução |
|---------|-------|--------|---------|
| Leituras por execução | N × (1 + P) | N × 1 | P vezes (P = pares) |
| Exemplo (1000 eventos, 50 pares) | 51.000 | 1.000 | 50× |
| Complexidade | O(N×P) | O(N) | Linear |
| Latência | ~5-10x lenterapidez | Base | Significativa |

---

**Pronto para implementação quando autorizado via novo gate C4.4.7-B.**
