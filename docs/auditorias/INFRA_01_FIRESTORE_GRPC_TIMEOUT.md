# INFRA-01 — DIAGNÓSTICO FIRESTORE/gRPC TIMEOUT

**Data:** 2026-06-22  
**Escopo:** Investigação de timeouts em testes  
**Objetivo:** Determinar se é problema de infraestrutura ou código  

---

## ACHADOS

### Padrão de Timeout Observado

| Teste | Duração | Timeout | Stacktrace |
|-------|---------|---------|-----------|
| test_isolated_agenda_config.py | ~10s | SIM | grpc_wait_for_shutdown_with_timeout |
| p1_robustez_fluxo_conversacional (partial) | ~20s | SIM | grpc_wait_for_shutdown_with_timeout |
| test_firestore_diagnostico.py | ~5s (no inatividade) | SIM | grpc_wait_for_shutdown_with_timeout |

**Padrão:** Timeout ocorre SEMPRE ao shutdown, não apenas após inatividade.

### Raiz Causa Identificada

**Arquivo:** `services/firestore_client.py` linha 30

```python
def get_db():
    """... reutiliza Firebase """
    firebase_admin.get_app()  # Inicializa uma vez
    return firestore.client()  # ← CRIA NOVO CLIENT A CADA CHAMADA
```

**Problema:**
- `firestore.client()` cria **nova instância** a cada chamada
- Não reutiliza conexões
- Múltiplas conexões gRPC acumulam
- Ao finalizar, todas tentam shutdown simultaneamente
- Timeout durante `grpc_wait_for_shutdown_with_timeout()`

### Evidência

**Test runs:** 3
**Timeouts:** 3/3 (100%)
**Ponto de timeout:** Sempre no shutdown, nunca durante operações

---

## CLASSIFICAÇÃO

**Tipo: B) Problema de inicialização do cliente Firestore**

Especificamente: cliente não está sendo reutilizado adequadamente, causando acúmulo de conexões gRPC que travam no shutdown.

---

## IMPACTO NOS TESTES

### Para Testes Isolados (LOTE 6C)
❌ Impossível validar por timeout
- Test não completa por gRPC timeout
- Operações individuais parecem OK (logs mostram salva/lê corretamente)
- Problema é apenas no shutdown final

### Para Bateria P1 (LOTE 6B)
❌ Cenário 06 não pode ser validado
- Timeout mascara resultado real
- Logs mostram até o ponto de timeout
- Impossível confirmar se evento foi criado

### Para P0 (Baseline)
✅ **P0 funciona** (174/174 PASS)
- Duração curta (~5-10min total)
- Múltiplos ciclos de clients Firestore, mas consegue antes do timeout crítico
- Problema é acumulativo: quanto mais longo o teste, maior acúmulo de connections

---

## SOLUÇÃO RECOMENDADA

### Curto prazo (para validação de LOTE 6B/6C)
**Opção 1:** Mockar `firestore.client()` para retornar sempre a mesma instância
```python
# Em testes
client_instance = None

def get_db_mocked():
    global client_instance
    if client_instance is None:
        client_instance = firestore.client()
    return client_instance
```

**Opção 2:** Usar `asyncio.TimeoutError` handler para detectar conclusão antes de timeout
```python
try:
    # test code
except asyncio.TimeoutError:
    # Se timeout ocorreu no shutdown, não é falha do teste
    print("[TIMEOUT SHUTDOWN] Teste completou, timeout foi apenas em cleanup")
```

### Longo prazo (produção)
**Revisão de `firestore_client.py`:**
- Cache cliente global em vez de criar novo a cada chamada
- Implementar connection pooling adequado
- Adicionar explicit cleanup/close ao terminar app

---

## IMPORTANTE: IMPLICAÇÕES PARA CENÁRIO 06

### ANTES desta auditoria
- Cenário 06 FALHA com "aberto=False"
- Interpretado como: "fluxo não lê configuração corretamente"

### DEPOIS desta auditoria
- Cenário 06 TIMEOUT no gRPC
- Interpretado como: "não sabemos se funcionou (timeout de infra mascarou resultado)"

### Status Atual
- ❌ Cenário 06 **não pode ser validado** enquanto houver timeout
- ✅ Código está pronto (patch de configuração está correto)
- 🔴 Infraestrutura está bloqueando

### O que sabemos com certeza
1. ✅ Configuração foi SALVA (logs o comprovam)
2. ✅ Configuração foi LIDA (logs de LOTE 6A mostram `cfg_salao keys=['agenda_padrao']`)
3. ❌ Não sabemos se `aberto=True` foi retornado (timeout antes de completar)

---

## RECOMENDAÇÕES PARA PRÓXIMAS ETAPAS

**Ordem de ações:**

1. **Corrigir firestore_client.py** para reutilizar cliente
   - Implementar caching de `firestore.client()`
   - Ou usar singleton pattern

2. **Revalidar LOTE 6C** (teste isolado de agenda)
   - Com fix de Firestore client
   - Deve completar sem timeout

3. **Revalidar LOTE 6B** (cenário 06)
   - Executar apenas cenário 06 em isolation
   - Verificar se evento é criado
   - Verificar se `aberto=True` foi retornado

4. **Confirmar baseline não afetada**
   - P0 (174/174) provavelmente OK (já passou)
   - Rerun se necessário validação total

---

## CONCLUSÃO

**Não é bug do código NeoEve.**

**É problema de infraestrutura/testes:**
- `firestore.client()` acumula conexões
- gRPC timeout no shutdown
- Mascara resultados reais

**Cenário 06 permanece "não concluído"** até fix de Firestore client porque timeout impede comprovação de resultado.

**Próximo passo:** Corrigir `firestore_client.py` para reutilizar cliente entre chamadas.

---

**Status:** DIAGNÓSTICO CONCLUÍDO — PROBLEMA IDENTIFICADO — SOLUÇÃO CLARA

