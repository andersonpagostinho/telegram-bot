# 📋 FRAMEWORK DE VALIDAÇÃO — 373 TESTES P0

**Regra de Ouro**: Todos os testes DEVEM validar até Firestore  
**Estabelecida**: 2026-10-18  
**Razão**: Testes rasos passavam, testes reais descobriam bugs (UnboundLocalError)

---

## ✅ O QUE SIGNIFICA "PASSAR"

Um teste P0 **PASSA VALIDAÇÃO** somente se:

### Nível 1: Entrada Real
```python
✅ Input WhatsApp real (não mock)
✅ Processamento completo
✅ Contexto propagado
```

### Nível 2: Execução Completa
```python
✅ add_evento_por_gpt() executado
✅ Validação de expediente
✅ Conflito de agenda verificado
✅ Notificação agendada
```

### Nível 3: Persistência em Firestore
```python
✅ Evento criado em Clientes/{tenant_id}/Eventos
✅ Confirmado=True após validação
✅ Campo cliente_id correto
✅ Campo profissional correto
✅ Campo data/hora correto
```

### Nível 4: Isolamento
```python
✅ Sem queda em Clientes/None
✅ Sem queda em Clientes/user_id
✅ Sem fallback inseguro
✅ Multi-tenant isolado
```

---

## ❌ O QUE SIGNIFICA "FALHAR"

### Tipo A: Não vai até Firestore
```
Teste validou apenas resposta do router
Não verificou criação de evento em Firestore
❌ NÃO CONTA COMO PASS (violação regra de ouro)
```

### Tipo B: Erro em Firestore
```
UnboundLocalError
AttributeError
IndexError
ValueError
❌ FAIL (precisa corrigir)
```

### Tipo C: Fixture Missing
```
fixture 'firebase_sync' not found
ERROR at setup
❌ SKIP (não pode rodar)
```

### Tipo D: Assertion Falha
```
AssertionError: Expected True but got False
assert evento['confirmado'] == True
❌ FAIL (lógica incorreta)
```

---

## 📊 LEVANTAMENTO ESPERADO

Após execução, relatório terá:

```
Total de testes: 373
├─ PASS (validação até Firestore): N
├─ FAIL (erro descoberto): N
├─ ERROR (setup/fixture): N
├─ SKIP (configuração): N
└─ TOTAL_VALIDO: PASS + FAIL + SKIP

Taxa de Sucesso Válida: PASS / TOTAL_VALIDO * 100%
```

---

## 🎯 CRITÉRIO DE SUCESSO

✅ **APROVADO**: Taxa >= 95% de testes passando até Firestore  
⚠️ **ATENÇÃO**: Taxa 85-94% (alguns bugs)  
❌ **BLOQUEADOR**: Taxa < 85% (falhas críticas)

---

## 📝 NOTAS IMPORTANTES

1. **Testes que não vão até Firestore NÃO contam como válidos**
   - Mesmo que passem (assertion no router)
   - Violam a regra de ouro

2. **Testes com ERROR/SKIP serão reportados mas não contam no PASS**
   - Podem indicar problemas de setup
   - Precisam investigação separada

3. **Cada FAIL será registrado**
   - Stack trace guardado
   - Não serão corrigidos (read-only)
   - Apenas reportado para próxima ação

4. **Resultado final será JSON estruturado**
   - Fácil de processar
   - Rastreável
   - Auditável

---

## 🔄 FLUXO DE CADA TESTE

```
Teste inicia
  ↓
Input WhatsApp real
  ↓
add_evento_por_gpt() ou similar
  ↓
Validação de expediente
  ↓
Evento criado?
  ├─ SIM → Verificar Firestore
  │         ├─ Em Clientes/{tenant_id}/Eventos? ✅
  │         ├─ confirmado=True? ✅
  │         ├─ Campos corretos? ✅
  │         └─ PASS
  └─ NÃO → Erro ou FAIL
```

---

**Status**: Execução em background  
**Próxima etapa**: Processar resultados conforme framework

