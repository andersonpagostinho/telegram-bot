# C4.4.8 — AUDITORIA DE IMPLEMENTAÇÃO: Eliminar Leitura Redundante

**Data:** 2026-09-25  
**Status:** AUDITORIA APENAS (ZERO ALTERAÇÕES DE PRODUÇÃO)  
**Base:** Commits 9c08266 (C4.4.7-A) + 18156d8 (C4.4.7-B)  

---

## A) DIAGNÓSTICO

### Situação Atual

```
checar_e_propor_recorrencias(user_id: str)
  ↓ Linha 243
  Leitura #1 (Firestore):
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
    └─ CARREGA TODOS os eventos do tenant em memória
  
  ↓ Linhas 247-258
  Agregação em memória:
    por_cliente_serv: Dict[(cliente_id, servico), List[dict]]
  
  ↓ Para CADA par (cliente_id, servico), lst in por_cliente_serv.items():
    
    ↓ Linha 296
    horarios = await _gerar_3_horarios_livres(
        user_id=user_id,           # ← Passa user_id
        data_sugerida=data_alvo,
        servico_chave=servico_chave,
        profissional=profissional,
        duracao_min=duracao
    )
    
    ↓ Dentro _gerar_3_horarios_livres(), Linha 124
    eventos_dia = await buscar_eventos_por_intervalo(
        user_id,                   # ← Recebe user_id
        dia_especifico=data_alvo
    ) or []
    
    ↓ event_service_async.py, Linha 210
    Leitura #2 (Firestore) — REDUNDANTE!
      eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
      └─ RELÊ TODOS os eventos do tenant novamente!
    
    ↓ Filtra por data_alvo
    return eventos que correspondem ao dia
```

### Problema

**Leitura #2 é redundante:**
- Leitura #1 já carregou TODOS os eventos do tenant (linha 243)
- Leitura #2 carrega os MESMOS eventos (linha 124 / event_service_async.py:210)
- Se tenant tem 100 eventos e 50 pares (cliente, serviço):
  - Leitura #1: 100 eventos
  - Leitura #2: 100 eventos × 50 vezes = 5.000 leituras redundantes
  - **Total: 5.100 leituras para dados que já estavam em memória**

---

## B) ASSINATURA PROPOSTA

### Assinatura Atual

```python
async def _gerar_3_horarios_livres(
    user_id: str,
    data_sugerida: date,
    servico_chave: Optional[str] = None,
    profissional: Optional[str] = None,
    duracao_min: Optional[int] = None
) -> List[str]:
```

### Assinatura Proposta

```python
async def _gerar_3_horarios_livres(
    user_id: str,
    data_sugerida: date,
    servico_chave: Optional[str] = None,
    profissional: Optional[str] = None,
    duracao_min: Optional[int] = None,
    eventos_disponiveis: Optional[List[dict]] = None  # ← NOVO PARÂMETRO
) -> List[str]:
```

### Retrocompatibilidade

✅ **SIM, completamente retrocompatível:**
- Novo parâmetro é opcional (default `None`)
- Quando `None`, comportamento é idêntico ao atual
- Callers existentes não precisam ser alterados
- Apenas 1 caller existe (linha 296) — ele será alterado para aproveitar otimização

---

## C) DIFF MÍNIMO PROPOSTO

### Modificação 1: Assinatura (Linha 101-107)

```diff
  async def _gerar_3_horarios_livres(
      user_id: str,
      data_sugerida: date,
      servico_chave: Optional[str] = None,
      profissional: Optional[str] = None,
      duracao_min: Optional[int] = None,
+     eventos_disponiveis: Optional[List[dict]] = None
  ) -> List[str]:
```

**Linhas alteradas:** 1

---

### Modificação 2: Docstring (Linha 108-114)

```diff
  """
  Retorna 3 horários realmente livres no dia (sem conflito com agenda global)
  e, se houver PROFISSIONAL, sem conflito do PROFISSIONAL também.

  Estratégia:
    - Tenta horários base: 10:00, 14:00, 16:00
    - Se não achar, varre 09:00→18:00 em passos de 30 min
+
+ Parâmetros opcionais:
+   - eventos_disponiveis: Se fornecido, evita leitura redundante do Firestore
+     filtrando eventos do dia a partir desta lista em vez de buscar novamente.
  """
```

**Linhas alteradas:** 3 (comentário, não lógica)

---

### Modificação 3: Lógica de Carregamento (Linhas 123-133)

```diff
  # 2) eventos do dia para checar conflito geral (independente de profissional)
- eventos_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=data_sugerida) or []
- ocupados: List[Tuple[datetime, datetime]] = []
- for ev in eventos_dia:
+ if eventos_disponiveis is not None:
+     # Usar lista pré-carregada e filtrar por data
+     eventos_dia = [
+         ev for ev in eventos_disponiveis
+         if ev.get("data") == data_sugerida.isoformat()
+     ]
+ else:
+     # Fallback: ler do Firestore (comportamento original)
+     eventos_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=data_sugerida) or []
+ 
+ ocupados: List[Tuple[datetime, datetime]] = []
+ for ev in eventos_dia:
      try:
          ini = _parse_dt(ev["data"], ev["hora_inicio"])
          fim = _parse_dt(ev["data"], ev["hora_fim"])
          if ini and fim and fim > ini:
              ocupados.append((ini, fim))
      except Exception:
          continue
```

**Linhas alteradas:** 8 (4 linhas novas + 4 linhas reordenadas)

**Total diff:** ~12 linhas

---

### Modificação 4: Chamada em checar_e_propor_recorrencias() (Linha 296-302)

```diff
  horarios = await _gerar_3_horarios_livres(
      user_id=user_id,
      data_sugerida=data_alvo,
      servico_chave=servico_chave,
      profissional=profissional,
-     duracao_min=duracao
+     duracao_min=duracao,
+     eventos_disponiveis=[ev for ev in eventos.values() if isinstance(ev, dict)]
  )
```

**Linhas alteradas:** 2

---

## D) TODOS OS CALLERS

### Caller Identificado

| Arquivo | Linha | Contexto | Eventos Disponíveis? |
|---------|-------|----------|----------------------|
| `services/recorrencia_service.py` | 296 | `checar_e_propor_recorrencias()` | ✅ YES (variável `eventos` linha 243) |

### Análise de Cada Caller

#### Caller 1: checar_e_propor_recorrencias() — Linha 296

**Contexto:**
```python
# Linha 243: Eventos já carregados
eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}

# ... agregação ...

# Linha 296: Chamar _gerar_3_horarios_livres
horarios = await _gerar_3_horarios_livres(
    user_id=user_id,
    data_sugerida=data_alvo,
    servico_chave=servico_chave,
    profissional=profissional,
    duracao_min=duracao
    # ↑ AQUI: eventos já estão em memória (variável `eventos`)
)
```

**Eventos Disponíveis?**
- ✅ SIM — variável `eventos` contém todos os eventos do tenant (linha 243)
- Estrutura: `Dict[event_id, evento_dict]`
- Pode ser convertida: `eventos.values()` → `List[dict]`

**Alteração Necessária:**
```python
eventos_disponiveis=[ev for ev in eventos.values() if isinstance(ev, dict)]
```

---

## E) MATRIZ DE TESTES NECESSÁRIOS

### Testes Novos (4 obrigatórios)

| # | Teste | Validação | Criticidade |
|---|-------|-----------|-------------|
| T1 | **fallback Firestore** | `eventos_disponiveis=None` usa `buscar_eventos_por_intervalo()` original | ✅ MUST |
| T2 | **lista pré-carregada** | `eventos_disponiveis=[...]` filtra por data, sem chamar Firestore | ✅ MUST |
| T3 | **equivalência resultado** | horários retornados são idênticos em ambos casos | ✅ MUST |
| T4 | **sem redundância** | mock Firestore para falhar; com `eventos_disponiveis`, não falha | ✅ MUST |

### Testes Regressão (32 existentes)

| Suite | Testes | Status Esperado |
|-------|--------|-----------------|
| C4.4.7-B (novo) | 8 | ✅ 8/8 PASS |
| C4.4.7-A (atualizado) | 10 | ✅ 10/10 PASS |
| C4.4.6 Fase A (existente) | 5 | ✅ 5/5 PASS |
| C4.2.5 (existente) | 9 | ✅ 9/9 PASS |
| **TOTAL** | **32** | **32/32 PASS** |

### Testes Propostos para C4.4.8

```python
class TestC448OptimizacaoBuscarEventos:
    """Validar eliminação de redundância em buscar_eventos_por_intervalo"""
    
    @pytest.mark.asyncio
    async def test_T1_fallback_firestore_sem_eventos_disponiveis():
        """T1: eventos_disponiveis=None usa buscar_eventos_por_intervalo (comportamento original)"""
        # Arrange
        user_id = "test_user_123"
        data_alvo = datetime.now().date() + timedelta(days=10)
        
        # Act
        horarios = await _gerar_3_horarios_livres(
            user_id=user_id,
            data_sugerida=data_alvo,
            servico_chave="corte",
            profissional="João",
            duracao_min=30,
            eventos_disponiveis=None  # ← Usar Firestore
        )
        
        # Assert
        assert len(horarios) == 3 or len(horarios) == 0  # 3 ou nenhum
        # (Comportamento original: tenta encontrar 3, se não achar retorna lista vazia ou parcial)
    
    @pytest.mark.asyncio
    async def test_T2_lista_precarga_sem_firestore():
        """T2: eventos_disponiveis=[...] filtra sem chamar Firestore"""
        # Arrange
        user_id = "test_user_456"
        data_alvo = datetime(2026, 9, 26).date()
        eventos_disponiveis = [
            {
                "data": "2026-09-26",
                "hora_inicio": "10:00",
                "hora_fim": "11:00",
                "cliente_id": "cli_1",
                "descricao": "corte",
                "profissional": "Bruna",
                "status": "confirmado"
            },
            {
                "data": "2026-09-26",
                "hora_inicio": "14:00",
                "hora_fim": "15:00",
                "cliente_id": "cli_2",
                "descricao": "escova",
                "profissional": "João",
                "status": "confirmado"
            }
        ]
        
        # Act
        with patch('services.recorrencia_service.buscar_eventos_por_intervalo', side_effect=Exception("Firestore chamado!")):
            horarios = await _gerar_3_horarios_livres(
                user_id=user_id,
                data_sugerida=data_alvo,
                servico_chave="corte",
                profissional=None,
                duracao_min=30,
                eventos_disponiveis=eventos_disponiveis  # ← Usar lista pré-carregada
            )
        
        # Assert
        assert isinstance(horarios, list)  # Não falhou com exceção
        assert len(horarios) >= 1  # Encontrou pelo menos 1 horário
    
    @pytest.mark.asyncio
    async def test_T3_equivalencia_resultado():
        """T3: Resultado com lista pré-carregada == resultado Firestore"""
        user_id = "test_user_789"
        data_alvo = datetime.now().date() + timedelta(days=15)
        
        # Cenário: 2 eventos ocupando alguns horários
        eventos_mock = [
            {"data": data_alvo.isoformat(), "hora_inicio": "10:00", "hora_fim": "11:00",
             "cliente_id": "cli_1", "descricao": "corte", "profissional": "Prof1", "status": "confirmado"},
            {"data": data_alvo.isoformat(), "hora_inicio": "14:00", "hora_fim": "15:00",
             "cliente_id": "cli_2", "descricao": "escova", "profissional": "Prof2", "status": "confirmado"}
        ]
        
        # Chamar com lista pré-carregada
        with patch('services.recorrencia_service.buscar_eventos_por_intervalo', return_value=eventos_mock):
            resultado_firestore = await _gerar_3_horarios_livres(
                user_id=user_id,
                data_sugerida=data_alvo,
                servico_chave="manicure",
                profissional=None,
                duracao_min=30,
                eventos_disponiveis=None  # Força Firestore
            )
        
        # Chamar com lista pré-carregada
        resultado_lista = await _gerar_3_horarios_livres(
            user_id=user_id,
            data_sugerida=data_alvo,
            servico_chave="manicure",
            profissional=None,
            duracao_min=30,
            eventos_disponiveis=eventos_mock  # Usa lista
        )
        
        # Assert
        assert resultado_firestore == resultado_lista  # Idênticos
    
    @pytest.mark.asyncio
    async def test_T4_sem_redundancia_firestore():
        """T4: Com eventos_disponiveis, Firestore não é chamado"""
        user_id = "test_user_999"
        data_alvo = datetime.now().date() + timedelta(days=20)
        eventos_disponiveis = []  # Vazio, mas fornecido
        
        mock_buscar = AsyncMock(side_effect=Exception("buscar_eventos_por_intervalo foi chamada! (redundância)"))
        
        with patch('services.recorrencia_service.buscar_eventos_por_intervalo', mock_buscar):
            horarios = await _gerar_3_horarios_livres(
                user_id=user_id,
                data_sugerida=data_alvo,
                servico_chave="teste",
                profissional=None,
                duracao_min=30,
                eventos_disponiveis=eventos_disponiveis  # ← Evita Firestore
            )
        
        # Assert
        mock_buscar.assert_not_called()  # Firestore NÃO foi chamado
        assert isinstance(horarios, list)  # Função completou sem erro
```

---

## F) ANÁLISE DE RISCOS

### Risco 1: Equivalência de Dados

**Questão:** Filtro sobre `eventos_disponiveis` é equivalente a `buscar_eventos_por_intervalo()`?

**Análise:**

```python
# Filtro proposto
eventos_dia_lista = [
    ev for ev in eventos_disponiveis
    if ev.get("data") == data_sugerida.isoformat()
]

# Comportamento de buscar_eventos_por_intervalo (event_service_async.py:193-257)
# Linha 244: data_evento = datetime.strptime(data_str, "%Y-%m-%d").date()
# Linha 248: if data_inicio <= data_evento <= data_fim:
```

**Diferença potencial:**
- `buscar_eventos_por_intervalo()` usa `datetime.strptime(...).date()` (linha 244)
- Proposta usa `ev.get("data") == data_sugerida.isoformat()` (string comparison)

**Validação:**
- `eventos_disponiveis` contém dados de Firestore (valor de `eventos` em linha 243)
- Campo `data` é string "YYYY-MM-DD" (formato Firestore)
- `data_sugerida.isoformat()` produz "YYYY-MM-DD"
- ✅ **Equivalência confirmada**

**Mitigação:** Teste T3 valida equivalência

---

### Risco 2: Estrutura de Eventos

**Questão:** Estrutura de `eventos_disponiveis` é idêntica à saída de `buscar_eventos_por_intervalo()`?

**Análise:**

```python
# Origem 1: Firestore direto (eventos_disponiveis)
eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
# Retorna: Dict[event_id, evento_dict]
# evento_dict: {"data": "...", "hora_inicio": "...", "hora_fim": "...", ...}

# Origem 2: buscar_eventos_por_intervalo()
# event_service_async.py:249-251
ev_out = dict(evento)
ev_out["event_id"] = event_id  # ← ADICIONA event_id!
resultado.append(ev_out)
```

**Diferença:**
- `buscar_eventos_por_intervalo()` **adiciona** campo `event_id` (linha 250)
- `eventos_disponiveis` (de Firestore direto) **não tem** `event_id`

**Impacto:**
- Função `_gerar_3_horarios_livres()` usa eventos apenas para:
  - Extrair `data`, `hora_inicio`, `hora_fim` (linhas 128-129)
  - Construir `ocupados` list (linha 131)
- Nunca usa `event_id`
- ✅ **Nenhum impacto, seguro**

**Mitigação:** Teste T2 valida que não há erro com estrutura

---

### Risco 3: Eventos Inválidos

**Questão:** Se `eventos_disponiveis` contém dados corrompidos/inválidos?

**Análise:**
```python
for ev in eventos_dia:
    try:
        ini = _parse_dt(ev["data"], ev["hora_inicio"])
        fim = _parse_dt(ev["data"], ev["hora_fim"])
        if ini and fim and fim > ini:
            ocupados.append((ini, fim))
    except Exception:
        continue  # ← Ignora exceções
```

- Bloco `try/except` (linhas 127-133) já ignora eventos inválidos
- ✅ **Seguro contra dados corrompidos**

---

### Risco 4: Performance com Lista Grande

**Questão:** Filter sobre 100+ eventos a cada iteração é lento?

**Análise:**
```python
eventos_dia = [
    ev for ev in eventos_disponiveis
    if ev.get("data") == data_sugerida.isoformat()
]
```

- List comprehension é O(N) onde N = total de eventos
- Tipicamente N ≤ 500 (eventos em um tenant)
- O(500) é negligenciável comparado a I/O Firestore
- ✅ **Seguro, sem impacto**

---

### Risco 5: Alteração Não-Retrocompatível

**Questão:** Novas chamadas de `_gerar_3_horarios_livres()` em outros locais quebram?

**Análise:**
- Novo parâmetro é **opcional** (default `None`)
- Comportamento com `None` é **idêntico ao atual**
- Callers existentes **não precisam ser alterados**
- ✅ **100% retrocompatível**

---

### Risco 6: Desempenho Comparativo

**Questão:** List filtering é comparável a Firestore read?

**Análise:**
| Operação | Tempo |
|----------|-------|
| Firestore read 100 docs | ~100-200ms |
| List filter 100 items | ~1ms |
| Economia por pair | ~100ms |

- Economia: **100ms × 50 pares = 5 segundos por tenant**
- Impacto cumulativo: **Significante para 1000+ tenants**

---

## G) CONFIRMAÇÃO FINAL

```
✅ Diagnóstico completo
✅ Assinatura proposta retrocompatível
✅ Diff mínimo documentado (~12 linhas em _gerar_3_horarios_livres)
✅ Todos os callers identificados (1 caller)
✅ Eventos disponíveis confirmados no único caller
✅ Matriz de 4 testes novos + 32 regressão definida
✅ 6 riscos analisados e mitigados
✅ Nenhuma alteração em buscar_eventos_por_intervalo()
✅ Nenhuma alteração em handlers/router/scheduler
✅ Nenhuma alteração em schema Firestore
✅ Nenhuma alteração em _descobrir_cadencia()
✅ Nenhuma alteração em cache de conflitos

═══════════════════════════════════════════════════════════════════
ZERO ALTERAÇÕES DE PRODUÇÃO IMPLEMENTADAS
═══════════════════════════════════════════════════════════════════
```

---

**Status:** Auditoria completa — Aguardando autorização para implementar C4.4.8

