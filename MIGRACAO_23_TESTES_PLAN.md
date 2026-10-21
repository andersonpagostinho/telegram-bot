# PLANO DE MIGRAÇÃO: 23 TESTES UNITÁRIOS → E2E com FIRESTORE

**Data:** 2026-10-21  
**Status:** PLANEJADO (não iniciado)  
**Escopo:** Converter 23 testes de formato unitário/mock para E2E com Firestore Real  
**Objetivo:** Atingir 174/174 PASS com REGRA DE OURO (validação até Firestore)

---

## TESTES PENDENTES (23 arquivos)

### LOTE 1 (5 testes)
- [ ] `test_p0_3_1_classificacao_consulta_deterministica.py` — Classifica "você tem agenda para corte amanhã às 10?"
- [ ] `test_p0_cancelar_evento_passado.py` — Impede cancelamento de evento no passado
- [ ] `test_p0_classificar_confirmacao_cancelamento.py` — Classifica "cancelar agendamento"
- [ ] `test_p0_data_sem_hora_fix.py` — Extrai data sem hora
- [ ] `test_p0_extracao_termo_cancelamento.py` — Detecta padrões de cancelamento

### LOTE 2 (5 testes)
- [ ] `test_p0_hotfix_contexto_agendamento.py` — Hotfix de contexto em agendamento
- [ ] `test_p0_outra_profissional_gap.py` — Gap: "com outra profissional"
- [ ] `test_p0_p1_fixes_implementation.py` — Implementação de fixes P0/P1
- [ ] `test_p0_quais_voce_tem.py` — Consulta "quais você tem de corte?"
- [ ] `test_p0_selecao_evento_cancelamento.py` — Seleção de evento para cancelamento

### LOTE 3 (5 testes)
- [ ] `test_p0_servicos_dinamicos.py` — Extração dinâmica de serviços
- [ ] `test_p01_gate_validacao_commit.py` — Gate de validação P01
- [ ] `test_p01_identidade_contexto.py` — Identidade + contexto P01
- [ ] `test_p012_eh_pedido_generico_fix.py` — Fix de pedido genérico
- [ ] `test_p02_code_fix.py` — Code fix P02

### LOTE 4 (5 testes)
- [ ] `test_p04_completo_validacao.py` — Validação completa P04
- [ ] `test_p04_correção_cirurgica.py` — Correção cirúrgica P04
- [ ] `test_p04_identidade_phone_number_id.py` — Phone number ID em identidade
- [ ] `test_p04_validacao_final.py` — Validação final P04
- [ ] `test_p056_regra_x1_adjacencia.py` — Regra X1 de adjacência

### LOTE 5 (3 testes)
- [ ] `test_p061_intencao_fix.py` — Fix de intenção P061
- [ ] `test_p1_2b_contexto_motor.py` — Motor de contexto P1
- [ ] `test_p1c_bloqueador_focado.py` — Bloqueador focado P1

---

## ESTRATÉGIA DE CONVERSÃO

### ANTES (Unitário/Mock):
```python
def test_extrair_servico(self):
    catalogo = ["corte", "escova"]
    texto = "quero corte"
    resultado = extrair_servico_do_catalogo(texto, catalogo)
    assert resultado == "corte"
```

### DEPOIS (E2E com Firestore):
```python
@pytest.mark.asyncio
async def test_extrair_servico_e2e():
    # Tenant com catálogo real
    E2E_TENANT_ID = "7394370553"
    
    # Novo cliente (unique user_id)
    timestamp_ms = int(time.time() * 1000)
    user_id = f"551199{timestamp_ms % 10000000:07d}"
    
    # Chamar roteador COM FIRESTORE REAL
    resposta = await roteador_principal(
        user_id=user_id,
        mensagem="quero corte",
        tenant_id=E2E_TENANT_ID,
        context=None,  # SEM MOCK
    )
    
    # Validar resposta
    assert "corte" in resposta.get("resposta", "").lower()
    
    # CRITICAL: Validar até Firestore (REGRA DE OURO)
    from utils.contexto_temporario import carregar_contexto_temporario
    ctx = await carregar_contexto_temporario(E2E_TENANT_ID, user_id)
    assert ctx.get("servico") == "corte" or "corte" in str(ctx)
```

---

## CHECKLIST POR LOTE

### Antes de iniciar cada lote:
- [ ] Firebase quota LIBERADA
- [ ] Credenciais válidas (principal_router acessa Firestore)
- [ ] Tenant 7394370553 com dados de teste presentes
- [ ] Contexto limpo (sem dados residuais)

### Durante cada lote:
- [ ] Converter 5 testes
- [ ] Garantir cada teste usa `@pytest.mark.asyncio`
- [ ] Cada teste chama `roteador_principal(..., context=None)`
- [ ] Cada teste valida resultado + contexto em Firestore
- [ ] Sem `@patch`, `MagicMock`, `unittest.mock`

### Após cada lote:
```bash
pytest tests/test_p0*.py tests/test_p01*.py tests/test_p04*.py tests/test_p056*.py tests/test_p061*.py tests/test_p1*.py -v
# Esperado: 174/174 PASS (antes + 5 novos)
```

---

## EXECUTION TIMELINE

### Fase 1: LOTE 1 (5 testes)
- [ ] Converter e validar
- [ ] Confirmar 151 + 5 = 156 PASS
- [ ] Commit: "Migration: 5/23 tests → E2E+Firebase (LOTE 1)"

### Fase 2: LOTE 2 (5 testes)
- [ ] Converter e validar
- [ ] Confirmar 156 + 5 = 161 PASS
- [ ] Commit: "Migration: 10/23 tests → E2E+Firebase (LOTE 2)"

### Fase 3: LOTE 3 (5 testes)
- [ ] Converter e validar
- [ ] Confirmar 161 + 5 = 166 PASS
- [ ] Commit: "Migration: 15/23 tests → E2E+Firebase (LOTE 3)"

### Fase 4: LOTE 4 (5 testes)
- [ ] Converter e validar
- [ ] Confirmar 166 + 5 = 171 PASS
- [ ] Commit: "Migration: 20/23 tests → E2E+Firebase (LOTE 4)"

### Fase 5: LOTE 5 (3 testes)
- [ ] Converter e validar
- [ ] Confirmar 171 + 3 = 174 PASS
- [ ] Commit: "Migration: 23/23 tests → E2E+Firebase (LOTE 5 - COMPLETO)"

---

## PÓS-MIGRAÇÃO

**Validação Final:**
```bash
pytest tests/test_p*.py -v 2>&1 | grep -E "PASS|FAIL"
# Esperado: 174 PASS, 0 FAIL
```

**Regressão:**
- [ ] Sem breaking changes
- [ ] Todos os testes passam
- [ ] Firebase limpo (sem dados residuais)

---

## BLOQUEADORES RELACIONADOS

Após concluir migração dos 23 testes, proceder com:
- 4 bloqueadores pendentes (3 FAILs originais + P0.4 data_hora=None)
- Ver: [[bloqueadores-pendentes-corrigir-lote]]

---

**STATUS:** 🟡 PLANEJADO — Aguardando autorização para iniciar Fase 1
