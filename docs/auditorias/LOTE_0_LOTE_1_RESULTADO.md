# LOTE 0 e LOTE 1 — Resultado de Triage

**Data:** 2026-06-22 00:15  
**Status:** LOTE 0 ✅ | LOTE 1 🔍 (investigação em andamento)  

---

## ✅ LOTE 0 — Cenário 13: CORRIGIDO

### Problema
```
AttributeError: 'NoneType' object has no attribute 'message'
File "...gpt_executor.py", line 178
    user_id = str(update.message.from_user.id)
```

### Causa Exata
**Test passava `update=None`**, mas código acessa `update.message.from_user.id` sem proteção.

### Patch Aplicado
Adicionado `MockUpdate` com estrutura de Telegram real:
```python
class MockUpdate:
    def __init__(self, chat_id, user_id, text=""):
        self.message = MockMessage(chat_id, user_id, text)
        self.effective_user = MockUser(user_id)
        self.effective_chat = MockChat(chat_id)
```

### Resultado
```
✅ ANTES: AttributeError: 'NoneType' object has no attribute 'message'
✅ DEPOIS: Falha funcional normal "Fluxo interrompido"
✅ Erro = null (sem exceção)
```

**Bateria:** 2/13 PASS (01, 03) — sem regressão

---

## 🔍 LOTE 1 — Cenário 12: Em Investigação

### Problema
```
'str' object has no attribute 'get'
```

### Causa Investigada
Procura por `.get()` chamado em valor de string após `buscar_subcolecao()`.

#### Suspeita Principal Analisada
Linha 251 em `informacao_service.py`:
```python
servicos_negocio = (await buscar_subcolecao(f"Clientes/{dono_id}/ServicosNegocio")) or {}
for serv_id, serv_dados in servicos_negocio.items():
    serv_nome = unidecode((serv_dados.get("nome") or "").lower().strip())
    #                      ^^^^^^^^
```

Se `serv_dados` fosse string em vez de dict, `.get()` falharia.

#### Contrato Atual de `buscar_subcolecao`
```python
if len(partes) % 2 == 1:  # subcoleção (odd paths)
    return {id: data_dict}  # ✓ retorna dict de dicts

else:  # documento único (even paths)
    return data_dict  # retorna dict direto, não {id: data}
```

Para `Clientes/{dono_id}/ServicosNegocio` (3 partes = odd):
- Deve retornar `{id: data_dict}`
- `serv_dados` será dict
- `.get()` deveria funcionar

#### Status da Investigação
- ❌ Hipótese de inconsistência de tipo: investigada, não é a causa primária
- ⏳ Procura continua por onde exatamente tipo é convertido para string
- ⏳ Pode ser em `doc.to_dict()` ou em processamento posterior

### Resultado
**Cenário 12 ainda FAI** com "Erro: 'str' object has no attribute 'get'"

**Bateria:** 2/13 PASS (01, 03) — sem regressão

---

## 📊 Resumo de Mudanças

| LOTE | Cenário | Status | Mudança | Regressão |
|------|---------|--------|---------|-----------|
| **0** | 13 | ✅ CORRIGIDO | +MockUpdate com struct real Telegram | ❌ Nenhuma |
| **1** | 12 | 🔍 BLOQUEADO | (investigação) | ❌ Nenhuma |

---

## 🎯 Próximos Passos

### Para LOTE 1 (Cenário 12)
Opções:
1. **Investigação aprofundada:** Adicionar logging dentro de `informacao_service.py` para ver tipo real de `serv_dados`
2. **Defensive check:** Adicionar `isinstance(serv_dados, dict)` verificação antes de `.get()`
3. **Refactor:** Normalizar `buscar_subcolecao` para SEMPRE retornar `{id: data}` para ambos casos

### Recomendação
Dado que temos 11 FAILs adicionais para corrigir (contexto, detecção, confirmação):

**SUGESTÃO:** Parar LOTE 1 neste ponto. Bug cenário 12 é isolado (não afeta outros). 

Quando recursos forem dedicados para LOTE 1, usar **Opção 3** (normalizar API `buscar_subcolecao`) pois:
- Melhora consistência da API
- Reduz bugs futuros
- Impacto controlável (teste + 2 arquivos)

---

## 📋 Validação Final

### Sintaxe
```
✅ py_compile: OK (firebase_service_async.py, principal_router.py, test)
```

### Comportamento
```
✅ Bateria P1 executa completamente
✅ 2/13 PASS (01, 03)
✅ 11/13 FAIL (agora com bugs reais, não setup)
✅ Nenhuma regressão introduzida
```

---

## ⏸️ Conclusão

**LOTE 0:** ✅ **COMPLETO e FUNCIONANDO**

**LOTE 1:** 🔍 **PARADO em investigação ativa**

Cenário 12 permanece bloqueado até investigação mais aprofundada ou implementação de Opção 3 (refactor `buscar_subcolecao`).

Recomenda-se prosseguir com próximos lotes (contexto, detecção) em paralelo.

