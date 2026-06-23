# P1 Fluxo Conversacional — Auditoria Arquitetural

**Data:** 2026-06-21  
**Objetivo:** Validar quais funções serão chamadas, paths Firestore, e o que será mockado  
**Status:** PRÉ-IMPLEMENTAÇÃO  

---

## 🔍 Funções Principais a Chamar

### Função Raiz: `roteador_principal()`

**Localização:** `router/principal_router.py:3342`

**Assinatura:**
```python
async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
```

**O que ela faz:**
1. Normaliza mensagem (remove quebras, espaços múltiplos)
2. Resolve tenant_id via `obter_id_dono(user_id)`
3. Carrega contexto via `carregar_contexto_temporario(user_id, tenant_id=dono_id)`
4. Processa fluxo P1 identidade/onboarding
5. Processa fluxo P0 (cancelamento, agendamento, etc)
6. Retorna resposta

**Retorno:**
```python
{
    "handled": bool,
    "resposta": str,
    "evento_criado": bool,
    # ... outros campos
}
```

---

## 🗺️ Paths Firestore Usados

### Paths Críticos Identificados

| Path | Uso | Descrição |
|------|-----|-----------|
| `Clientes/{tenant_id}/Configuracao/info` | Leitura | Config do salão |
| `Clientes/{tenant_id}/Atores/{actor_id}` | Leitura/Escrita | Perfil do ator (dono/prof/cliente) |
| `Clientes/{tenant_id}/Sessoes/{actor_id}` | Leitura/Escrita | Contexto conversacional |
| `Clientes/{tenant_id}/Profissionais/{prof_id}` | Leitura | Dados do profissional |
| `Clientes/{tenant_id}/ServicosNegocio/{serv_id}` | Leitura | Dados do serviço |
| `Clientes/{tenant_id}/Eventos/{evento_id}` | Escrita | Evento criado |
| `Clientes/{tenant_id}/Agendas/{prof_id}/{data}` | Leitura | Agenda do profissional |

### Paths Legados (PROIBIDOS nesta bateria)

❌ `Clientes/{id}/...` (sem tenant_id)
❌ Qualquer path fora de `Clientes/{tenant_id}/`

---

## ⚙️ Serviços Usados

### Session Service

```python
from services.session_service import pegar_sessao

await pegar_sessao(user_id, tenant_id)
```

**O que faz:** Busca sessão em `Clientes/{tenant_id}/Sessoes/{user_id}`

---

### Firebase Service Async

```python
from services.firebase_service_async import obter_id_dono, buscar_subcolecao

dono_id = await obter_id_dono(user_id)
profs = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais")
```

**O que faz:** Operações básicas em Firestore

---

### GPT Service

```python
from services.gpt_service import (
    tratar_mensagem_usuario,
    processar_com_gpt_com_acao,
    gerar_resposta_p1,
)

json_resposta = await tratar_mensagem_usuario(texto, prompt)
```

**O que faz:** Chama OpenAI GPT real (ou mockado nos testes)

---

### Agenda Service

```python
from services.agenda_service import (
    validar_data_funcionamento,
    validar_horario_funcionamento,
    resolver_fora_do_expediente,
)

disponivel = await validar_horario_funcionamento(
    tenant_id, profissional_id, data, hora
)
```

**O que faz:** Verifica disponibilidade determinística

---

### Event Service

```python
from services.event_service_async import (
    verificar_conflito_e_sugestoes_profissional,
    salvar_evento
)

conflito, sugestoes = await verificar_conflito_e_sugestoes_profissional(...)
```

**O que faz:** Valida e cria eventos em Firestore

---

## ✅ O Que Será Mockado (Permitido)

```python
# 1. Envio de mensagem Telegram (não afeta lógica)
context.bot.send_message()  ← MOCKAR ✓

# 2. Chamada OpenAI (controlável para testes)
services.gpt_service.tratar_mensagem_usuario()  ← MOCKAR CONTROLADAMENTE ✓
```

---

## ❌ O Que NÃO Será Mockado (Proibido)

```python
# 1. Router principal
roteador_principal()  ← CHAMAR REAL ✗

# 2. Session/Contexto
carregar_contexto_temporario()  ← FIRESTORE REAL ✗
salvar_contexto_temporario()  ← FIRESTORE REAL ✗

# 3. Agenda/Disponibilidade
validar_horario_funcionamento()  ← LÓGICA REAL ✗
verificar_conflito_e_sugestoes_profissional()  ← LÓGICA REAL ✗

# 4. Evento
salvar_evento()  ← FIRESTORE REAL ✗
cancelar_evento()  ← FIRESTORE REAL ✗

# 5. Firestore
buscar_subcolecao()  ← FIRESTORE REAL ✗
obter_id_dono()  ← FIRESTORE REAL ✗
```

---

## 🎯 Isolamento por Tenant

### Estratégia

```python
# Cada cenário:
tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
actor_id = normalizar_actor_id("whatsapp", f"551199999{i:04d}")

# Setup isolado
await setup_tenant_completo(tenant_id, actor_id)

# Teste isolado
resposta = await roteador_principal(
    user_id=actor_id,
    mensagem="...",
    update=None,
    context=None  # Mockar apenas isso
)

# Verificação isolada
estado = await obter_estado_firestore(tenant_id, actor_id)
assert estado["draft"] == {...}
```

### Limpeza Entre Cenários

```python
async def limpar_tenant(tenant_id: str):
    """Limpar tenant completamente"""
    for subcol in ["Sessoes", "Eventos", "Atores", ...]:
        docs = await buscar_subcolecao(f"Clientes/{tenant_id}/{subcol}")
        for doc in docs:
            await deletar_dado_em_path(f"Clientes/{tenant_id}/{subcol}/{doc['id']}")
```

---

## 📋 Checklist de Implementação

### Antes de Criar Cada Cenário

- [ ] Gerar `tenant_id` único
- [ ] Gerar `actor_id` determinístico
- [ ] Limpar tenant completamente
- [ ] Setup: config, profissional, serviço
- [ ] Capturar estado ANTES
- [ ] Chamar `roteador_principal()`
- [ ] Capturar estado DEPOIS
- [ ] Validar paths Firestore corretos
- [ ] Verificar nenhum path legado
- [ ] Limpar dados de teste

### Durante a Execução

- [ ] Nenhum mockado de router
- [ ] Nenhum mockado de agenda
- [ ] Nenhum mockado de disponibilidade
- [ ] Nenhum mockado de conflito
- [ ] Nenhum mockado de evento
- [ ] Apenas mockado: `context.bot.send_message()` e GPT controladamente
- [ ] Tenant_id correto em todos os paths
- [ ] Nenhum Clientes/{id}/... legado

---

## 🔐 Validações por Cenário

### Template de Validação

```python
resultado = CenarioFluxo(numero, nome)

try:
    # Setup
    tenant_id = f"teste_fluxo_p1_{uuid.uuid4().hex[:8]}"
    await limpar_tenant(tenant_id)
    await setup_tenant_completo(tenant_id)
    
    # Estado ANTES
    resultado.estado_antes = await obter_estado_firestore(tenant_id)
    
    # Executar
    resposta = await roteador_principal(
        user_id=actor_id,
        mensagem="...",
        update=None,
        context=MockContext()
    )
    
    # Estado DEPOIS
    resultado.estado_depois = await obter_estado_firestore(tenant_id)
    
    # Validações
    assert resposta["handled"] == True
    assert resultado.estado_depois["draft"]["servico"] == "corte"
    assert resultado.estado_depois["confirmacao_pendente"] == True
    assert resultado.evento_criado == False
    
    resultado.set_pass("Fluxo correto")
    
except Exception as e:
    resultado.set_fail(f"Erro: {str(e)}", e, traceback.format_exc())
```

---

## 🚀 Próximo Passo

Após aprovação desta auditoria:

1. ✅ Confirmar que paths estão corretos
2. ✅ Confirmar que nenhum path legado aparece
3. ✅ Confirmar que mocks são apenas I/O
4. ✅ Confirmar que isolamento é garantido
5. → Implementar `tests/p1_robustez_fluxo_conversacional_real.py`

---

**Status:** ✅ AUDITORIA PRONTA PARA IMPLEMENTAÇÃO  
**Arquivo gerado:** Este documento  
**Próximo:** Autorizar e criar segunda bateria
