# FASE 4 — E2E CONTROLADO: PLANO DE TESTE

**Status**: 📋 **PLANO PRONTO PARA EXECUÇÃO**

**Prerequisito**: Firestore Emulator rodando em localhost:8080

---

## 1. SETUP DO AMBIENTE

### Iniciar Firestore Emulator

```bash
# Terminal 1: Iniciar emulator
gcloud beta emulators firestore start --host-port=localhost:8080

# Terminal 2: Set variáveis (Windows PowerShell)
$env:FIRESTORE_EMULATOR_HOST = "localhost:8080"
```

### Configurar Projeto de Teste

```python
# No início do teste
import os
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

from services.firebase_service_async import inicializar_firebase
inicializar_firebase()  # Conectará ao emulator
```

---

## 2. CENÁRIOS OBRIGATÓRIOS

### Cenário 1: Detectar Divergência e Pedir Esclarecimento

**Entrada**: "Agendar para 18/11/2026, sexta-feira"

**Passos**:
1. Usuario envia mensagem
2. Router extrai data=18/11/2026, weekday=sexta
3. Validação detecta: 18/11/2026 é quarta (não sexta)
4. Sistema bloqueia e pede: "Qual dia você prefere?"

**Verificações**:
- ✅ `ctx["conflito_data_weekday"]` = {data_explicita: "18/11/2026", dia_semana_mencionado: "sexta"}
- ✅ `ctx["estado_fluxo"]` = "aguardando_clareza_data_weekday"
- ✅ Logs: "[BLOQUEIO_DATA_WEEKDAY]"
- ✅ **Motor NÃO foi chamado** (verificar logs do event_service)
- ✅ Contagem de chamadas ao motor = 0

---

### Cenário 2: Corrigir Data e Continuar Fluxo

**Entrada após Cenário 1**: "Prefiro sexta-feira, dia 20"

**Passos**:
1. Usuario responde com esclarecimento
2. Sistema extrai nova data: 20/11/2026
3. Validação: 20/11/2026 é sexta ✅
4. Sem conflito, retoma fluxo
5. Consulta disponibilidade com data corrigida

**Verificações**:
- ✅ `ctx["conflito_data_weekday"]` = None (limpo)
- ✅ `ctx["estado_fluxo"]` = "agendando" ou "aguardando_profissional"
- ✅ `ctx["data_hora"]` = "2026-11-20T..." (corrigida)
- ✅ Serviço preservado (se informado antes)
- ✅ Profissional preservado (se informado antes)
- ✅ **Motor FOI chamado** com data=2026-11-20
- ✅ Contagem de chamadas ao motor = 1

---

### Cenário 3: Aceitar Data Sem Conflito

**Entrada**: "Agendar para 18/11/2026, quarta-feira"

**Passos**:
1. Usuario envia data + weekday compatível
2. Validação: 18/11/2026 é quarta ✅
3. Sem conflito, fluxo continua normalmente
4. Consulta disponibilidade imediatamente

**Verificações**:
- ✅ `ctx["conflito_data_weekday"]` = None
- ✅ Sem estado "aguardando_clareza_data_weekday"
- ✅ `ctx["data_hora"]` = "2026-11-18T..." (original)
- ✅ **Motor FOI chamado** na primeira mensagem
- ✅ Contagem de chamadas ao motor = 1

---

### Cenário 4: Isolamento Multi-Tenant

**Setup**:
- Tenant A: tenant_id="TENANT_A", actor_id="USER_A"
- Tenant B: tenant_id="TENANT_B", actor_id="USER_B"

**Passos**:
1. USER_A envia conflito de data
2. Sistema armazena em sessão de TENANT_A
3. USER_B envia mesma mensagem
4. Sistema armazena em sessão de TENANT_B (separado)

**Verificações**:
- ✅ Sessão USER_A contém conflito para TENANT_A
- ✅ Sessão USER_B contém conflito para TENANT_B
- ✅ Leitura cruzada: USER_A não vê dados de USER_B
- ✅ Logs registram tenant_id e actor_id corretos
- ✅ Sem vazamento de dados entre tenants

---

### Cenário 5: Autorização - Sem Criação sem Confirmação

**Entrada**: "Agendar para 20/11/2026, sexta-feira, às 14:00 com Bruna"

**Passos**:
1. Usuario seleciona horário
2. Sistema CONSULTA disponibilidade ✅
3. Sistema NUNCA cria evento automaticamente ❌
4. Aguarda confirmação explícita: "Confirma esse horário?"

**Verificações**:
- ✅ Horário foi consultado (motor chamado)
- ✅ Hora foi armazenada em ctx["horario_sugerido"] ou similar
- ✅ **Evento NÃO foi criado** em eventos/calendário
- ✅ Estado é "aguardando_confirmacao" ou similar
- ✅ Logs mostram: "[INFO] Horário selecionado, aguardando confirmação"
- ✅ Sem chamadas a criar_evento() ou salvar_evento()

---

## 3. SCRIPT DE TESTE

### Arquivo: `tests/test_fase4_e2e_data_weekday.py`

```python
# -*- coding: utf-8 -*-
import pytest
import asyncio
import os
from datetime import datetime
from services.firebase_service_async import inicializar_firebase, buscar_dado_em_path, salvar_dado_em_path
from router.principal_router import extrair_slots_e_mesclar

# Setup Firestore Emulator
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

@pytest.fixture(scope="session")
async def firebase():
    inicializar_firebase()
    yield
    # Cleanup if needed

@pytest.mark.asyncio
async def test_cenario1_detectar_divergencia(firebase):
    """Cenário 1: Detectar divergência e pedir esclarecimento"""
    
    # Setup
    tenant_id = "test_tenant_1"
    actor_id = "test_actor_1"
    texto = "Agendar para 18/11/2026, sexta-feira"
    
    # Dados iniciais
    ctx = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "servico": "corte",
        "profissional_escolhido": "Bruna",
    }
    
    # Executar
    resultado = await extrair_slots_e_mesclar(ctx, texto, tenant_id, actor_id)
    
    # Verificações
    assert resultado.get("conflito_data_weekday") is not None, "Conflito não foi detectado"
    assert resultado.get("estado_fluxo") == "aguardando_clareza_data_weekday"
    assert resultado.get("data_hora") is None, "data_hora foi setada (deveria estar bloqueada)"
    
    # Verificar que serviço e profissional foram preservados
    assert resultado.get("servico") == "corte"
    assert resultado.get("profissional_escolhido") == "Bruna"
    
    print("✓ Cenário 1 PASS")

@pytest.mark.asyncio
async def test_cenario2_corrigir_data(firebase):
    """Cenário 2: Corrigir data e continuar fluxo"""
    
    # Setup com estado de bloqueio anterior
    tenant_id = "test_tenant_2"
    actor_id = "test_actor_2"
    
    ctx = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "conflito_data_weekday": {
            "data_explicita": "18/11/2026",
            "dia_semana_mencionado": "sexta",
        },
        "estado_fluxo": "aguardando_clareza_data_weekday",
        "servico": "corte",
        "profissional_escolhido": "Bruna",
    }
    
    # Usuario corrige: prefere sexta (20/11/2026)
    texto = "Prefiro sexta-feira, dia 20"
    
    # Executar
    resultado = await extrair_slots_e_mesclar(ctx, texto, tenant_id, actor_id)
    
    # Verificações
    assert resultado.get("conflito_data_weekday") is None, "Conflito não foi limpo"
    assert resultado.get("data_hora") is not None, "data_hora deveria estar setada"
    assert "2026-11-20" in resultado.get("data_hora", "")
    assert resultado.get("estado_fluxo") in ["agendando", "aguardando_profissional"]
    
    print("✓ Cenário 2 PASS")

@pytest.mark.asyncio
async def test_cenario3_data_compativel(firebase):
    """Cenário 3: Data + weekday compatível"""
    
    tenant_id = "test_tenant_3"
    actor_id = "test_actor_3"
    texto = "Agendar para 18/11/2026, quarta-feira, às 14:00"
    
    ctx = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "servico": "corte",
    }
    
    # Executar
    resultado = await extrair_slots_e_mesclar(ctx, texto, tenant_id, actor_id)
    
    # Verificações
    assert resultado.get("conflito_data_weekday") is None, "Falso positivo de conflito"
    assert resultado.get("data_hora") is not None, "data_hora deveria estar setada"
    assert "2026-11-18" in resultado.get("data_hora", "")
    
    print("✓ Cenário 3 PASS")

@pytest.mark.asyncio
async def test_cenario4_isolamento_multitenant(firebase):
    """Cenário 4: Isolamento multi-tenant"""
    
    # Tenant A
    ctx_a = {
        "tenant_id": "TENANT_A",
        "actor_id": "USER_A",
        "servico": "pedicure",
    }
    resultado_a = await extrair_slots_e_mesclar(ctx_a, "Agendar para 18/11/2026, sexta", "TENANT_A", "USER_A")
    
    # Tenant B (mesma mensagem)
    ctx_b = {
        "tenant_id": "TENANT_B",
        "actor_id": "USER_B",
        "servico": "manicure",
    }
    resultado_b = await extrair_slots_e_mesclar(ctx_b, "Agendar para 18/11/2026, sexta", "TENANT_B", "USER_B")
    
    # Verificações
    assert resultado_a.get("conflito_data_weekday") is not None, "Conflito em TENANT_A"
    assert resultado_b.get("conflito_data_weekday") is not None, "Conflito em TENANT_B"
    
    # Dados não se misturam
    assert resultado_a.get("servico") == "pedicure", "Serviço de TENANT_A alterado"
    assert resultado_b.get("servico") == "manicure", "Serviço de TENANT_B alterado"
    
    # Logs separam contextos
    assert resultado_a.get("tenant_id") == "TENANT_A"
    assert resultado_b.get("tenant_id") == "TENANT_B"
    
    print("✓ Cenário 4 PASS")

@pytest.mark.asyncio
async def test_cenario5_sem_criacao_automatica(firebase):
    """Cenário 5: Sem criação sem confirmação"""
    
    tenant_id = "test_tenant_5"
    actor_id = "test_actor_5"
    
    # Preparar dados completos
    ctx = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-11-20T14:00:00",  # Data válida
    }
    
    # Simulando seleção de horário
    texto = "Vou confirmar às 14:00"
    
    # Executar
    resultado = await extrair_slots_e_mesclar(ctx, texto, tenant_id, actor_id)
    
    # Verificações
    assert resultado.get("estado_fluxo") != "agendado", "Evento foi criado automaticamente!"
    assert resultado.get("hora_confirmada") is not True or resultado.get("estado_fluxo") != "confirmado"
    
    # Verificar que nenhum evento foi criado no Firestore
    try:
        evento = await buscar_dado_em_path(f"Clientes/{tenant_id}/Eventos/teste_evento")
        assert evento is None, "Evento foi criado sem confirmação!"
    except:
        pass  # Esperado se documento não existe
    
    print("✓ Cenário 5 PASS")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 4. PROCEDIMENTO DE EXECUÇÃO

### Com Firestore Emulator

```bash
# Terminal 1
gcloud beta emulators firestore start --host-port=localhost:8080

# Terminal 2 (PowerShell)
cd C:\dev\neoeve
$env:PYTHONPATH = "C:\dev\neoeve"
$env:FIRESTORE_EMULATOR_HOST = "localhost:8080"
python -m pytest tests/test_fase4_e2e_data_weekday.py -v
```

### Resultado Esperado

```
test_cenario1_detectar_divergencia PASSED
test_cenario2_corrigir_data PASSED
test_cenario3_data_compativel PASSED
test_cenario4_isolamento_multitenant PASSED
test_cenario5_sem_criacao_automatica PASSED

5 passed in 2.34s
```

---

## 5. EVIDÊNCIAS A COLETAR

Após execução bem-sucedida:

### Logs a Incluir

```
[BLOQUEIO_DATA_WEEKDAY] Conflito detectado em cenário 1
✓ Cenário 1 PASS: data=18/11/2026 != weekday=sexta

✓ Cenário 2 PASS: data_hora corrigida para 2026-11-20
✓ Cenário 3 PASS: Sem bloqueio, fluxo normal
✓ Cenário 4 PASS: Isolamento mantido (TENANT_A ≠ TENANT_B)
✓ Cenário 5 PASS: Sem evento criado automaticamente
```

### Contagem de Chamadas ao Motor

- Cenário 1: 0 chamadas (bloqueado)
- Cenário 2: 1 chamada (após correção)
- Cenário 3: 1 chamada (sem conflito)
- Cenário 4: 2 chamadas (uma por tenant)
- Cenário 5: 0 chamadas (sem confirmação ainda)

---

## 6. LIMITAÇÕES CONHECIDAS

⚠️ Este plano requer:
- Firestore Emulator rodando localmente
- Ou projeto de staging isolado no Google Cloud
- Ou mock completo do Firebase (não recomendado para E2E)

**Não aceitar**:
- Mocks parciais como E2E real
- Testes que não envolvem persistência
- Suposições sobre Firestore sem verificação

---

## 7. CLASSIFICAÇÃO

Será estabelecida após execução com ambiente real:
- ✅ **APROVADO**: Todos 5 cenários PASS, isolamento mantido, sem eventos criados sem autorização
- ⚠️ **APROVADO COM RESSALVAS**: 4/5 cenários PASS, ou violação menor de guardrail
- ❌ **REPROVADO**: <4 cenários PASS, ou violação de segurança (isolamento, autorização)

---

**Este plano aguarda execução com Firestore Emulator**
