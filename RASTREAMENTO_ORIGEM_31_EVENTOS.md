# 🔍 RASTREAMENTO FORENSE — ORIGEM DOS 31 EVENTOS

**Status:** ✅ ANÁLISE COMPLETA  
**Conclusão:** Origem identificada com precisão  

---

## A) LOCALIZAÇÃO DO LOG

**Arquivo:** `services/event_service_async.py`  
**Linha:** 1321  
**String exata:** `"[DIAG] Total de eventos encontrados: {len(eventos)}"`  
**Variável:** `eventos` (dict)  

```python
print(
    f"[DIAG] Total de eventos encontrados: {len(eventos)}",
    flush=True
)
```

---

## B) FUNÇÃO QUE GERA O LOG

**Arquivo:** `services/event_service_async.py`  
**Linhas:** 1175-1586  
**Função:** `async def verificar_conflito_e_sugestoes_profissional(...)`  

**Assinatura:**
```python
async def verificar_conflito_e_sugestoes_profissional(
    user_id: str,
    data: str,
    hora_inicio: str,
    duracao_min: int,
    profissional: str,
    servico,
    event_id: str = None,
    tenant_id: str | None = None
) -> dict:
```

---

## C) VARIÁVEL CONTENDO OS 31 EVENTOS

**Variável:** `eventos` (type: dict)  
**Atribuída em linha:** 1277  

```python
eventos = await buscar_subcolecao(path_eventos) or {}
```

Onde:
- `path_eventos = f"Clientes/{user_id_efetivo}/Eventos"` (linha 1271)

---

## D) ORIGEM DA VARIÁVEL

**Função:** `buscar_subcolecao()`  
**Arquivo:** `services/firebase_service_async.py:212-232`  

**Query Firestore:**
```python
ref.stream()  # SEM FILTRO DE DATA
```

**Retorna:** Todos os documentos da subcoleção (não apenas 2026-10-03)

**Conclusão:** ✅ Os 31 eventos vêm de `buscar_subcolecao()` que busca **TODOS os eventos do tenant, sem filtro de data**

---

## E) CALLER(S)

Múltiplos callers de `verificar_conflito_e_sugestoes_profissional()`:

| Arquivo | Linha | Função | Observação |
|---------|-------|--------|-----------|
| `principal_router.py` | ~1913 | (diversas) | Chamadas principales em produção |
| `principal_router.py` | ~2636 | (diversas) | Múltiplas ocorrências |

**Principal caller ativo:** `principal_router.py` (múltiplas funções)

---

## F) ORIGEM DO EVENTO DE JUNHO

**Evento:** `7394370553_bruna_2026-06-05_08:00`  

**Rastreamento:**

```
1. ORIGEM: Firestore Clientes/7394370553/Eventos

2. CONSULTADO POR: buscar_subcolecao()
   └─ linha 1277 de verificar_conflito_e_sugestoes_profissional()

3. RETORNADO EM: dict `eventos`
   └─ contém ~31 documentos, TODAS as datas

4. PROCESSADO EM: loop linha 1346-1367
   ├─ Para cada evento em eventos.items()
   ├─ Chama evento_deve_entrar_na_agenda(
   │    evento_id=eid,
   │    evento=ev,
   │    data_consulta=data   ← passada na linha 1354
   │  )
   │
   └─ Se evento_deve_entrar_na_agenda() retorna False
      └─ evento é adicionado a `eventos_descartados[]`
      └─ Imprime: "[DESCARTADO] {eid}: nao passou em evento_deve_entrar_na_agenda()"

5. DESCARTADO POR: evento_deve_entrar_na_agenda()
   └─ Condição 5 (linha 57 em event_service_async.py:30-60)
   └─ if data_consulta and evento.get("data") != data_consulta: return False
```

**Cadeia completa:**
```
Firestore (Clientes/7394370553/Eventos)
  ↓
buscar_subcolecao(path) — linha 1277
  ↓
eventos = {...31 docs de TODAS datas...}
  ↓
loop for eid, ev in eventos.items() — linha 1346
  ↓
evento_deve_entrar_na_agenda(data_consulta="2026-10-03")
  ↓
"2026-06-05" != "2026-10-03" → False
  ↓
[DESCARTADO]
```

---

## G) CADEIA COMPLETA ATÉ evento_deve_entrar_na_agenda()

```
principal_router.py (caller)
  └─ verificar_conflito_e_sugestoes_profissional(
       user_id="7394370553",
       data="2026-10-03",  ← data do pedido
       ...
     )
     └─ buscar_subcolecao("Clientes/7394370553/Eventos")
        └─ ref.stream() → 31 eventos de TODAS datas
        └─ eventos = {...}
        └─ for eid, ev in eventos.items()
           └─ evento_deve_entrar_na_agenda(
                evento_id=eid,
                evento=ev,
                data_consulta="2026-10-03"
              )
```

---

## H) PARTICIPA `buscar_eventos_por_intervalo()`?

**Resposta:** ❌ NÃO

**Evidência:** 
- `verificar_conflito_e_sugestoes_profissional()` chama `buscar_subcolecao()` **direto**
- Não chama `buscar_eventos_por_intervalo()`
- `buscar_eventos_por_intervalo()` é usada em OUTRO contexto (event_handler.py:836)

---

## I) PARTICIPA `MemoriaTemporaria`?

**Resposta:** ❌ NÃO

**Evidência:**
- Grep em `verificar_conflito_e_sugestoes_profissional()` não encontra referência a MemoriaTemporaria
- Única origem é `buscar_subcolecao()`

---

## J) EXISTE SEGUNDA CONSULTA / MERGE / CACHE?

**Resposta:** ❌ NÃO — Logo após buscar_subcolecao(), vai direto ao loop

**Evidência:**
- Linha 1277: `eventos = await buscar_subcolecao(path_eventos) or {}`
- Linha 1278: `profissionais = await buscar_subcolecao(...)`
- Linha 1280-1329: logs de diagnóstico
- Linha 1346: `for eid, ev in eventos.items()` ← usa direto, sem merge/processamento

**Não há:**
- Concatenação com outra lista
- Processamento que removeria eventos
- Merge com cache

---

## K) TENANT

**Tenant utilizado:** `7394370553`  
**Path Firestore:** `Clientes/7394370553/Eventos`  

**Confirmação:** ✅ Correto, nenhum tenant-leak detectado

---

## L) MENOR PONTO EXATO DE CORREÇÃO

**Sem implementar, apenas identificando:**

**OPÇÃO 1: Adicionar filtro Firestore** (mais eficiente)

**Localização:** `services/firebase_service_async.py:219`

Alterar de:
```python
docs = ref.stream()  # busca TODOS
```

Para:
```python
docs = ref.where("data", "==", data_consulta).stream()  # filtra por data
```

**OPÇÃO 2: Adicionar filtro Python**

**Localização:** `services/event_service_async.py:1346`

Alterar de:
```python
for eid, ev in eventos.items():
```

Para:
```python
for eid, ev in eventos.items():
    if ev.get("data") != data:
        continue  # pula eventos de outra data antes de chamar evento_deve_entrar_na_agenda()
```

---

## M) CONCLUSÃO OBJETIVA

**Os 31 eventos vêm de `buscar_subcolecao()` que retorna TODOS os eventos do tenant `7394370553`, sem filtro de data no Firestore.**

**Fluxo:**
1. `verificar_conflito_e_sugestoes_profissional()` é chamada com `data="2026-10-03"`
2. Consulta Firestore: `Clientes/7394370553/Eventos` (sem filtro)
3. Retorna 31 documentos (de TODAS as datas: junho, julho, outubro, etc.)
4. Loop testa cada um em `evento_deve_entrar_na_agenda(..., data_consulta="2026-10-03")`
5. Eventos de junho retornam False (data não bate)
6. Todos os 31 são descartados

**Resultado:** "Total descartados: 31" e "Total considerados para conflito: 0"

**Origem identificada corretamente sem alterações de código.**

---

**Status Final:** ✅ Rastreamento forense completo. Nenhuma alteração implementada.
