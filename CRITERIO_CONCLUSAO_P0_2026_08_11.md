# CRITÉRIO DE CONCLUSÃO — P0 REAGENDAMENTO
**Data:** 2026-08-11  
**Definição:** P0 só termina quando TUDO isso está VERDE em teste real

---

## O PROBLEMA QUE ORIGINOU TUDO

```
Observação: Motor alterar_agendamento() existe (testado 7/7)
Lacuna: Mas usuário NÃO consegue dizer ao NeoEve "quero mudar meu agendamento"
        e o sistema concluir a operação com segurança

P0: Fechar essa lacuna com fluxo conversacional end-to-end
```

---

## CRITÉRIO DE CONCLUSÃO (REAL)

P0 está **CONCLUÍDO** quando:

### ✅ 5 Fluxos Conversacionais Funcionam

#### Fluxo 1: Cliente + Linguagem Natural + Sem Conflito
```
Input:    "Quero adiar minha manicure para amanhã"
         (linguagem natural, não palavras-chave exatas)

Processo:
  1. Sistema detecta intenção (heurística ou GPT)
  2. Lista agendamentos do cliente
  3. Cliente escolhe qual
  4. Cliente fornece novo horário ("17h")
  5. Motor valida: SEM CONFLITO
  6. Sistema pede confirmação
  7. Cliente confirma: "Sim"
  8. Motor altera evento

Output:   ✅ Evento alterado
          ✅ event_id preservado
          ✅ Histórico registrado
          ✅ Status confirmado
```

**Teste:** `cenario_1_cliente_linguagem_natural_sem_conflito()`

#### Fluxo 2: Cliente + Linguagem Natural + Com Conflito + Alternativas
```
Input:    "Preciso remarcar meu corte"

Processo:
  1. Sistema detecta intenção
  2. Lista agendamentos
  3. Cliente escolhe qual
  4. Cliente solicita: "Amanhã às 15h"
  5. Motor valida: CONFLITO (já há evento às 15h)
  6. Sistema oferece alternativas: "Tenho 16h ou 17h"
  7. Cliente escolhe: "17h"
  8. Motor revalida: "17h" SEM CONFLITO
  9. Sistema pede confirmação
  10. Cliente confirma: "Sim"
  11. Motor altera para 17h

Output:   ✅ Conflito detectado
          ✅ Alternativas oferecidas
          ✅ Alternativa revalidada
          ✅ Evento alterado
          ✅ Histórico registrado
```

**Teste:** `cenario_2_cliente_conflito_alternativas()`

#### Fluxo 3: Dono Altera Evento de Cliente
```
Input:    "Mude a consulta da Maria para amanhã às 16h"
          (dono falando sobre cliente seu)

Processo:
  1. Sistema valida: ator é dono ✓
  2. Sistema valida: tenant_id é o do dono ✓
  3. Sistema busca evento de Maria
  4. Motor valida: dono pode alterar (tenant match) ✓
  5. Motor valida conflito
  6. Motor altera evento
  7. Histórico registra: actor_id = dono_id

Output:   ✅ Permissão validada
          ✅ Tenant validado
          ✅ Evento alterado
          ✅ Histórico registra dono como actor
```

**Teste:** `cenario_3_dono_altera_cliente()`

#### Fluxo 4: Profissional Altera Seu Atendimento
```
Input:    "Mude meu atendimento com João para sexta"
          (profissional falando)

Processo:
  1. Sistema valida: ator é profissional ✓
  2. Sistema busca eventos onde: profissional == actor_id
  3. Motor valida: profissional pode alterar (é o profissional) ✓
  4. Motor altera evento
  5. Histórico registra: actor_id = profissional_id

Output:   ✅ Permissão validada
          ✅ Evento alterado
          ✅ Histórico registra profissional como actor
```

**Teste:** `cenario_4_profissional_altera_seu_atendimento()`

#### Fluxo 5: Tentativa Fora do Escopo → Bloqueada
```
Input:    Cliente A tenta alterar evento de Cliente B
         (tenant diferente)

Processo:
  1. Sistema resolve tenant_id de Cliente A
  2. Sistema tenta buscar evento em Tenant A
  3. Evento pertence a Tenant B
  4. Motor detecta: tenant mismatch
  5. Motor bloqueia: "Evento não pertence a esse tenant"

Output:   ✅ Acesso bloqueado
          ✅ Nenhuma alteração foi feita
          ✅ Segurança mantida
```

**Teste:** `cenario_5_tenant_isolation()`

---

### ✅ Validações Técnicas (Todas Verde)

#### 1. event_id Preservado
```
Antes:  evento_id = "EVT123"
Depois: evento_id = "EVT123"  ← MESMA ID

NÃO:    evento_id = "EVT456" (novo)
```

**Validação em teste:**
```python
evento_alterado = await buscar_evento("EVT123")
assert evento_alterado is not None
assert evento_alterado.get("id") == "EVT123"
```

#### 2. Histórico Registrado Corretamente
```
evento.historico_alteracoes = [{
    "timestamp": "2026-08-11T18:30:00Z",
    "anterior": {
        "data": "2026-08-14",
        "hora": "14:30"
    },
    "novo": {
        "data": "2026-08-15",
        "hora": "17:00"
    },
    "actor_id": "cliente_001",  ← Quem alterou
    "motivo": "Reagendamento do cliente"
}]
```

**Validação em teste:**
```python
historico = evento_alterado.get("historico_alteracoes", [])
assert len(historico) >= 1
assert historico[0]["actor_id"] == "cliente_001"
assert "anterior" in historico[0]
assert "novo" in historico[0]
```

#### 3. Conflito Detectado Corretamente
```
Quando motor detecta conflito:
  ✅ Retorna: {"conflito": True, "sugestoes": [...]}
  ✅ NÃO altera evento
  ✅ Oferece alternativas

Quando motor valida sem conflito:
  ✅ Retorna: {"conflito": False}
  ✅ Pronto para alterar
```

**Validação em teste:**
```python
validacao = await verificar_conflito_e_sugestoes_profissional(
    ..., event_id="EVT123"  # Crítico!
)

if validacao["conflito"]:
    sugestoes = validacao["sugestoes"]
    assert len(sugestoes) > 0
```

#### 4. Duração Variável Suportada
```
Evento original: duração = 30 min
Alteração: duração = 60 min  ← Pode variar

Esperado:
  ✅ hora_inicio = 17:00
  ✅ hora_fim = 18:00  (calculado automaticamente)
  ✅ duracao_minutos = 60
```

**Validação em teste:**
```python
resultado = await alterar_agendamento(
    ..., nova_duracao_minutos=60
)

evento = await buscar_evento("EVT123")
assert evento["duracao_minutos"] == 60
```

#### 5. Tenant Isolation Validado
```
Tenant A:
  ├─ evento_id = "EVT_A_001"
  └─ Cliente A pode alterar ✓

Tenant B:
  ├─ evento_id = "EVT_B_001"
  ├─ Cliente B pode alterar seu evento ✓
  └─ Cliente B NÃO pode alterar "EVT_A_001" ✓

Cross-tenant:
  ├─ Cliente A tenta alterar "EVT_B_001" → BLOQUEADO ✓
  └─ evento_id não foi alterado ✓
```

**Validação em teste:**
```python
# Tenant A cria evento
evento_a = await criar_evento(tenant="TENANT_A", event_id="EVT_A_001")

# Tenant B tenta alterar
resultado = await alterar_agendamento(
    event_id="EVT_A_001",
    tenant_id="TENANT_B"
)

# Esperado: falha
assert resultado["ok"] == False

# Validar que não foi alterado
evento_final = await buscar_evento_em_tenant("TENANT_A", "EVT_A_001")
assert evento_final["hora_inicio"] == "14:00"  # Não mudou
```

#### 6. Permissões Respeitadas
```
Cliente:
  ✅ Pode alterar seus próprios eventos
  ❌ Não pode alterar evento de outro cliente

Dono:
  ✅ Pode alterar eventos de qualquer cliente do seu tenant
  ❌ Não pode alterar evento de outro tenant

Profissional:
  ✅ Pode alterar eventos onde é o profissional
  ❌ Não pode alterar evento onde não trabalha
```

**Validação em teste:**
```python
# Cliente tenta alterar evento de outro
resultado = await alterar_agendamento(
    event_id="EVT_OUTRO_CLIENTE",
    tenant_id=tenant,
    user_id="cliente_a"
)
assert resultado["ok"] == False

# Dono altera evento de cliente
resultado = await alterar_agendamento(
    event_id="EVT_CLIENTE_B",
    tenant_id=tenant,
    user_id=dono_id  # Dono é o ator
)
assert resultado["ok"] == True
```

#### 7. Operação Atômica
```
Se alterar_agendamento() retorna {"ok": True}:
  ✅ Evento foi alterado NO Firestore (não é rascunho)
  ✅ Histórico foi registrado atomicamente
  ✅ Operação é irrevogável
  ✅ Status permanece "confirmado"

Se retorna {"ok": False}:
  ✅ NENHUMA alteração foi feita
  ✅ NENHUM histórico foi registrado
  ✅ Estado anterior intacto
```

---

### ✅ Regressão (Tudo Verde)

#### P0 Existente: 174/174 PASS
```bash
python TESTE_REGRESSAO_P0_2026_06_23.py
# Esperado: 174/174 PASS
#           Nenhuma regressão
```

#### P1 Existente: 42/42 PASS
```bash
python TESTE_REGRESSAO_P1_2026_06_23.py
# Esperado: 42/42 PASS
#           Nenhuma regressão
```

---

## O TESTE QUE PROVA TUDO

**Arquivo:** `TESTE_P0_REAGENDAMENTO_E2E_CONVERSACIONAL_2026_08_11.py`

**5 Cenários Críticos:**
1. ✅ `cenario_1_cliente_linguagem_natural_sem_conflito()`
2. ✅ `cenario_2_cliente_conflito_alternativas()`
3. ✅ `cenario_3_dono_altera_cliente()`
4. ✅ `cenario_4_profissional_altera_seu_atendimento()`
5. ✅ `cenario_5_tenant_isolation()`

**Execução:**
```bash
python TESTE_P0_REAGENDAMENTO_E2E_CONVERSACIONAL_2026_08_11.py
```

**Esperado:**
```
[OK] Cenário 1: Cliente com Linguagem Natural (sem conflito)
[OK] Cenário 2: Cliente com Conflito + Alternativas
[OK] Cenário 3: Dono Altera Evento de Cliente
[OK] Cenário 4: Profissional Altera Seu Atendimento
[OK] Cenário 5: Tenant Isolation (Tentativa Bloqueada)

[SUCESSO] P0 REAGENDAMENTO CONVERSACIONAL VALIDADO
```

---

## CHECKLIST FINAL

Antes de declarar P0 **CONCLUÍDO**:

```
[ ] Fluxo 1: Cliente + Linguagem Natural + Sem Conflito → PASS
[ ] Fluxo 2: Cliente + Conflito + Alternativas → PASS
[ ] Fluxo 3: Dono Altera Cliente → PASS
[ ] Fluxo 4: Profissional Altera Atendimento → PASS
[ ] Fluxo 5: Tenant Isolation Bloqueado → PASS

[ ] Validação 1: event_id preservado → PASS
[ ] Validação 2: Histórico com actor_id → PASS
[ ] Validação 3: Conflito detectado → PASS
[ ] Validação 4: Duração variável → PASS
[ ] Validação 5: Tenant isolation → PASS
[ ] Validação 6: Permissões respeitadas → PASS
[ ] Validação 7: Operação atômica → PASS

[ ] Regressão P0: 174/174 PASS
[ ] Regressão P1: 42/42 PASS

[ ] Nenhuma alteração quando conflito
[ ] Confirmação é obrigatória
[ ] GPT apenas interpreta
[ ] Router apenas orquestra
[ ] Motor apenas executa
```

**Se todos os checkboxes estão marcados → P0 CONCLUÍDO**

---

## O QUE SIGNIFICA "LACUNA FECHADA"

Antes:
```
Sistema tem alterar_agendamento()
Mas usuário não consegue usar conversacionalmente
Lacuna: Fluxo de reagendamento conversacional não existe
```

Depois:
```
Sistema tem alterar_agendamento()
+ Fluxo conversacional implementado
+ 5 cenários reais funcionando
+ Testes validando tudo
+ Regressão verde
= Lacuna FECHADA
```

**Resultado:** Usuário pode dizer "Quero mudar meu horário" e o sistema conclui com segurança.

---

## QUANDO CONSIDERAR NÃO CONCLUÍDO

P0 **NÃO** é considerado concluído se:

```
❌ Alguns cenários falharem
❌ Regressão não ficar verde
❌ event_id não for preservado
❌ Histórico não for registrado
❌ Conflito não for detectado
❌ Tenant isolation falhar
❌ Permissões não forem respeitadas
❌ Algum teste falhar
```

Se qualquer ponto acima acontecer: voltar para implementação e corrigir.

---

**Conclusão:** P0 está concluído quando o teste E2E ` TESTE_P0_REAGENDAMENTO_E2E_CONVERSACIONAL_2026_08_11.py` executa e retorna:

```
[SUCESSO] P0 REAGENDAMENTO CONVERSACIONAL VALIDADO
```

Com todos os 5 cenários e 7 validações PASS, e regressão verde (174/174 + 42/42).

**Nada menos do que isso é considerado "concluído".**
