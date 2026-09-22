# P0 REAGENDAMENTO CONVERSACIONAL — STATUS DEBUG
**Data:** 2026-08-11 20:12  
**Resultado E2E:** 3/5 PASS (60%)  
**Gate:** 🔴 REPROVADO — EM DEBUG  

---

## CENÁRIOS E2E

### ✅ PASSANDO (3/5)

**Cenário 1: Cliente + Linguagem Natural (sem conflito)**
- Cliente altera seu próprio evento sem conflito
- event_id preservado ✅
- Histórico registrado ✅
- Confirmação obrigatória ✅

**Cenário 4: Profissional Altera Seu Atendimento**
- Profissional altera evento onde é o profissional
- Validação de permissão funciona ✅
- Histórico registra profissional como actor_id ✅

**Cenário 5: Tenant Isolation (Bloqueado)**
- Cross-tenant bloqueado corretamente ✅
- Acesso negado ✅
- Sem alteração no evento ✅

---

### ❌ FALHANDO (2/5) — INVESTIGAÇÃO NECESSÁRIA

**Cenário 2: Cliente + Conflito + Alternativas**

Erro: `Motor não detectou conflito em 15h`

Estado: Cliente solicita alterar para 15h, mas existe evento de 15h-15:30 para mesmo profissional.

Fluxo a investigar:
```
cliente_id (cliente_002)
    ↓
tenant_id (teste_p0_tenant_a_20260811)
    ↓
evento_alterar_id (evt_c2_alter)
    ↓
nova_data = 2026-08-15
nova_hora_inicio = 15:00
profissional = Bruno
duracao = 30 min
    ↓
verificar_conflito_e_sugestoes_profissional(
    user_id=tenant_id,
    data="2026-08-15",
    hora_inicio="15:00",
    duracao_min=30,
    profissional="Bruno",
    event_id="evt_c2_alter"  ← deve ignorar este
)
    ↓
Deveria retornar: conflito=True, sugestoes=[...]
Retorna: conflito=False ← BUG
```

**Causas possíveis:**
1. Evento bloqueante (evt_c2_bloqueante 15:00-15:30) não está sendo encontrado
2. Filtro de event_id_ignorar não está funcionando
3. Resolução de tenant_id está errada
4. Comparação de horário está errada

---

**Cenário 3: Dono Altera Evento de Cliente**

Erro: `Evento não pertence ao tenant do dono`

Estado: Dono tenta alterar evento de cliente dentro do mesmo tenant.

Fluxo a investigar:
```
dono_id (teste_p0_dono_20260811)
    ↓
cliente_evento (cliente_maria_001)
    ↓
evento_id (evt_c3_maria)
    ↓
tenant_id = teste_p0_dono_20260811
    ↓
alterar_agendamento(
    user_id=dono_id,
    event_id=evt_c3_maria,
    tenant_id=teste_p0_dono_20260811
)
    ↓
VALIDACAO OWNERSHIP (linha 1648):
    tipo_usuario = "dono"
    cliente_id_evento = "cliente_maria_001"
    
    tenant_evento = obter_id_dono(cliente_id_evento)
    if tenant_evento != tenant_id:
        return ERRO ← AQUI FALHA
```

**Causa raiz provável:**
`obter_id_dono("cliente_maria_001")` retorna algo diferente de `teste_p0_dono_20260811`

Possibilidades:
1. cliente_maria_001 não tem id_negocio correto
2. obter_id_dono() tem lógica errada
3. Test setup não criou documento de cliente corretamente

---

## ARQUITETURA VALIDADA ✅

Os 3 cenários que passam validam:

1. **Separação motor/router/GPT** ✅
   - Cenário 1 prova fluxo completo funciona

2. **Validação de permissão multi-ator** ✅
   - Cliente: próprio evento (cenário 1)
   - Profissional: evento seu (cenário 4)
   - Cross-tenant: bloqueado (cenário 5)

3. **Atomicidade + histórico** ✅
   - event_id preservado em todos os casos
   - Histórico registra actor_id correto
   - Duração variável funcionando

4. **Tenant isolation** ✅
   - Bloqueio cross-tenant funciona

---

## PRÓXIMAS AÇÕES

**Não fazer:** Alterações especulativas, testes adicionais sem investigação, fuzzy de parâmetros.

**Fazer:**

1. **Cenário 2:**
   - Verificar: evento bloqueante (evt_c2_bloqueante) está em Firestore? ✓
   - Verificar: call a verificar_conflito_e_sugestoes_profissional() com event_id="evt_c2_alter"
   - Verificar: resposta do motor (conflito sim/não, sugestoes)
   - Confirmar: tenant_id resolução

2. **Cenário 3:**
   - Verificar: cliente_maria_001 tem documento em Firestore?
   - Verificar: qual valor de id_negocio em cliente_maria_001?
   - Verificar: obter_id_dono("cliente_maria_001") retorna?
   - Confirmar: teste setup criou documento do cliente

3. **Depois:** Regressão P0 174/174 + P1 42/42

---

## CHECKLIST FINAL (NÃO FAZER AINDA)

```
[ ] Cenário 1: PASS ✅
[ ] Cenário 2: DEBUG em andamento
[ ] Cenário 3: DEBUG em andamento
[ ] Cenário 4: PASS ✅
[ ] Cenário 5: PASS ✅

[ ] 5/5 E2E PASS (bloqueado em 2, 3)
[ ] P0 174/174 PASS (aguardando)
[ ] P1 42/42 PASS (aguardando)
```

**Gate não será aberto até:** Todos os cenários E2E + regressão verde.

---

**Status:** 🔴 REPROVADO  
**Motivo:** Cenários 2 e 3 em debug, regressão pendente  
**Data esperada de conclusão:** Após investigação causa raiz dos 2 cenários
