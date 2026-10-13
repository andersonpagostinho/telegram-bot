# 🔬 INVESTIGAÇÃO PROFUNDA — Contratos Reais vs Testes

**Data:** 2026-10-08  
**Objetivo:** Determinar se testes mascarando bugs reais ou apenas mal especificados  
**Status:** ✅ Análise de contrato real concluída  

---

## 📋 TESTE 1: test_patch_p0_cancelamento.py

### Contrato do Teste

**Setup:**
```python
user_id = "user_123"
dono_id = "dono_456"
evento_mock = {
    "evento_id": "ev_001",
    "cliente_id": user_id,  # ← "user_123" (SEM prefixo)
    "profissional": "Bruna",
    "status": "confirmado",
}

# Mock simula buscar_subcolecao retornando evento_mock
with patch("services.event_service_async.buscar_subcolecao") as mock_buscar:
    mock_buscar.return_value = {"ev_001": evento_mock}
    
    # Chamada
    ok, msg, candidatos = await cancelar_evento_por_texto(
        user_id=user_id,  # "user_123" (SEM prefixo)
        termo="com Bruna amanhã",
        tenant_id=dono_id  # "dono_456"
    )
    
# Resultado esperado: ok=False (aguardando confirmação)
```

### Contrato Real (Produção)

**Rastreamento do fluxo real:**

```
1. WhatsApp webhook recebe mensagem
   ↓ wa_id = "5511991382080" (raw do WhatsApp)
   
2. router/principal_router.py:3482
   identidade_p01 = criar_identidade_whatsapp(wa_id="5511991382080", ...)
   
   Resultado:
   ├─ wa_id = "5511991382080" (SEM prefixo)
   ├─ actor_id = "whatsapp:5511991382080" (COM prefixo) ← criado na linha 93
   └─ user_id = "5511991382080" (mantém SEM prefixo)

3. handlers/event_handler.py:632-638 (ao criar evento)
   cliente_id = (dados or {}).get("cliente_id") or user_id
   
   if not str(cliente_id).startswith("whatsapp:"):
       cliente_id = f"whatsapp:{cliente_id}"
   
   Resultado: cliente_id = "whatsapp:5511991382080" (COM prefixo)

4. handlers/event_handler.py:1161
   evento = {
       ...
       "cliente_id": cliente_id,  # "whatsapp:5511991382080" ← ARMAZENADO COM PREFIXO
       ...
   }
   
   Firestore persiste: Clientes/{dono_id}/Eventos/{evento_id}
   {"cliente_id": "whatsapp:5511991382080", ...}

5. Cancelamento (router/principal_router.py:3719)
   user_id_para_cancelamento = identidade_p01.actor_id  # "whatsapp:5511991382080"
   
   ok = await cancelar_evento(
       user_id=user_id_para_cancelamento,  # "whatsapp:5511991382080"
       event_id=evento_id,
       ...
   )

6. Validação em event_service_async.py:306
   cliente_id_evento = ev.get("cliente_id")  # "whatsapp:5511991382080" (do Firestore)
   
   if cliente_id_evento != user_id:  # "whatsapp:..." != "whatsapp:..."
       return False
   
   Resultado: ✅ PASSA (ambos COM prefixo)
```

### Comparação

| Campo | Teste Atual | Produção Real | Divergência |
|-------|------------|---------------|------------|
| `wa_id` | N/A | `"5511991382080"` | Teste simula com "user_123" |
| `actor_id` | N/A | `"whatsapp:5511991382080"` | Teste não cria `identidade_p01` |
| `user_id` em mock | `"user_123"` | `"5511991382080"` | SEM prefixo |
| `cliente_id` em mock | `"user_123"` | `"whatsapp:5511991382080"` | **DIVERGÊNCIA: SEM vs COM prefixo** |
| `user_id` em cancelamento | `"user_123"` | `"whatsapp:5511991382080"` | **DIVERGÊNCIA: SEM vs COM prefixo** |
| Validação `!=` | `"user_123" != "user_123"` (False) | `"whatsapp:..." != "whatsapp:..."` (False) | ✅ Ambos passam, mas por razões diferentes |

### Classificação

**CATEGORIA: B — TESTE INCORRETO E NÃO HÁ BUG DE PRODUÇÃO**

**Por quê:**

- ✅ Produção está **CORRETA**: `cliente_id` é armazenado COM prefixo, validação bate
- ❌ Teste está **INCORRETO**: usa SEM prefixo, nunca testa o contrato real
- ⚠️ **Não há bug real de produção**, apenas teste deficiente

**Porém, há risco:**

Se alguém em produção chamar `cancelar_evento()` com `user_id` SEM prefixo:
```python
# Erro hipotético:
ok = await cancelar_evento(
    user_id="5511991382080",  # SEM prefixo (errado)
    event_id="...",
)
# Resultado: FALHA em validação (bloqueado)
# Mensagem: [CANCELAMENTO_BLOQUEADO] usuario=5511991382080 nao eh cliente_id=whatsapp:5511991382080
```

Isso **não pode acontecer** em fluxo atual porque:
- Linha 3719: `user_id_para_cancelamento = identidade_p01.actor_id` (sempre COM prefixo)
- Linha 52 em test: chama `cancelar_evento_por_texto()` que não passa `user_id` direto

---

## 📋 TESTE 2: test_p0_cancelamento_idle.py

### Contrato do Teste

```python
async def mock_obter_id_dono(user_id):
    return "dono_teste"  # ← SEMPRE retorna sucesso

async def mock_carregar_contexto_temporario(user_id, tenant_id=None):
    return {"estado_fluxo": "idle"}  # ← Contexto vazio garantido

async def mock_salvar_contexto_temporario(user_id, ctx, tenant_id=None):
    assert ctx.get("estado_fluxo") == "aguardando_confirmacao_cancelamento"
    return True

# Teste chama roteador_principal com tudo mockado
result = await roteador_principal(
    user_id="user_123",
    mensagem="Quero cancelar com a Bruna amanhã",
    ...
)

assert result.get("handled") == True
```

### Contrato Real (Produção)

```
1. WhatsApp webhook → wa_id="5511991382080"

2. router/principal_router.py:3482
   identidade_p01 = criar_identidade_whatsapp(wa_id, phone_number_id, tenant_id)
   └─ Resolve tenant_id corretamente ou falha

3. router/principal_router.py:3495-3520
   if identidade_p01 is None:
       return None  # ← PODE FALHAR SE IDENTIDADE NÃO CRIADA

4. Detecção de cancelamento (roteador)
   eh_cancelamento = eh_cancelamento(mensagem)  # lógica real, não mock
   
   if eh_cancelamento:
       estado_novo = "aguardando_confirmacao_cancelamento"
       
5. Salvamento de contexto (REAL no Firestore)
   path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
   
   resultado = await salvar_contexto_temporario_v2(
       tenant_id=tenant_id,  # ← REAL, pode divergir
       actor_id=actor_id,     # ← COM prefixo "whatsapp:"
       contexto={...}
   )
   
   if resultado is False:
       # Salvamento falhou (sem espaço, permissão, etc)
       return None  # ← PODE FALHAR SILENCIOSAMENTE
```

### Comparação

| Aspecto | Teste | Produção | Divergência |
|---------|-------|----------|-----------|
| `obter_id_dono()` | Mock retorna sempre "dono_teste" | REAL retorna None ou ID real | 🔴 **ALTO**: Teste nunca valida caso de None |
| `carregar_contexto()` | Mock retorna `{"estado_fluxo": "idle"}` | REAL busca em Firestore | ⚠️ **MÉDIO**: Firestore pode estar vazio, não retornar nothing |
| `salvar_contexto()` | Mock retorna True | REAL salva em Firestore, pode falhar | 🔴 **ALTO**: Teste nunca valida falha de salvamento |
| `eh_cancelamento()` | Mock retorna `{}` | REAL analisa mensagem, pode não detectar | ⚠️ **MÉDIO**: Lógica de detecção pode mudar |
| `tenant_id` | Hardcoded "dono_456" | Resolvido de phone_number_id | 🔴 **ALTO**: Colisão se múltiplos testes paralelos |
| `identidade_p01` | Não testada | Crítica para fluxo real | 🔴 **ALTO**: Teste nunca cria identidade real |

### Classificação

**CATEGORIA: A — TESTE INCORRETO, FALSOS POSITIVOS GARANTIDOS**

**Por quê:**

- 🔴 Teste é **TODO MOCK**: nunca testa fluxo real de Firestore
- 🔴 Teste pode passar com "dono_teste" mock enquanto real deveria retornar None
- 🔴 Teste identidade_p01 é None em alguns casos, teste nunca descobre
- 🔴 **Falsos positivos garantidos**: Se produção tem bug, teste ainda passa

**Bugs possíveis não capturados:**

1. `obter_id_dono()` retorna None em produção
   - Teste pass (mock retorna "dono_teste")
   - Produção falha (path = f"Clientes/{None}/...")

2. `salvar_contexto()` falha por permissão
   - Teste passa (mock retorna True)
   - Produção falha (Firestore rejeita)

3. Múltiplos testes paralelos com mesmo tenant_id
   - Teste passa (em isolamento)
   - Produção falha (dados interferem)

---

## 📋 TESTE 3: test_patch_p0_bloqueio_contexto.py

### Contrato do Teste

```python
with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
    mock_buscar.return_value = {}  # ← Sempre vazio
    
    resultado = await carregar_contexto_temporario(
        user_id="user_123",
        tenant_id=None  # ← SEM tenant
    )
    
    assert resultado == {}, "Retorna vazio quando sem tenant"

with patch("utils.contexto_temporario.atualizar_dado_em_path") as mock_salvar:
    mock_salvar.return_value = True  # ← Mock nunca falha
    
    resultado = await salvar_sessao_temporaria(
        actor_id="user_123",
        contexto={...},
        tenant_id="dono_456"
    )
    
    # Valida que chamou com path correto
    call_path = mock_salvar.call_args[0][0]
    assert "dono_456" in call_path, "Path deve conter tenant"
```

### Contrato Real (Produção)

```
1. Salvamento real em Firestore
   path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
   
   await atualizar_dado_em_path(path, contexto)
   
   Firestore persiste em:
   /Clientes/7394370553/Sessoes/whatsapp:5511991382080
   └─ actor_id COM prefixo "whatsapp:"

2. Carregamento em paralelo de outro teste
   path_teste_2 = f"Clientes/teste_123/Sessoes/user_456"
   contexto_teste_2 = await buscar_dado_em_path(path_teste_2)
   
   Se testes usam MESMO tenant_id (hardcoded):
   path_teste_1 = f"Clientes/dono_456/Sessoes/..."
   path_teste_2 = f"Clientes/dono_456/Sessoes/..."
   └─ COLISÃO! Dados interferem

3. Isolamento real
   DEVE usar UUID para tenant_id:
   tenant_id = f"test_{uuid.uuid4().hex[:8]}"
   └─ Garante isolamento mesmo em paralelo
```

### Comparação

| Aspecto | Teste | Produção | Divergência |
|---------|-------|----------|-----------|
| Armazenamento | Mock em memória | Firestore real | 🔴 **ALTO**: Path pode estar errado, dados podem não persistir |
| tenant_id | Hardcoded "dono_456" | Deve ser UUID | 🔴 **ALTO**: Colisão em paralelo |
| Isolamento | Simulado (mock único) | Real (Firestore collection) | 🔴 **ALTO**: Múltiplos testes podem interferir |
| Limpeza | Manual em teste | Deve usar fixture cleanup | ⚠️ **MÉDIO**: Dados acumulam entre testes |
| Falha de Firestore | Nunca testada | Pode falhar por quota, permissão | 🔴 **ALTO**: Teste nunca simula erro real |

### Classificação

**CATEGORIA: A — TESTE INCORRETO E RISCO DE COLISÃO DE DADOS**

**Por quê:**

- 🔴 Teste simula isolamento, não testa real
- 🔴 tenant_id hardcoded = risco colisão em paralelo
- 🔴 Sem UUID = testes flaky se rodam juntos
- 🔴 Mock sucesso sempre = nunca descobre erro Firestore

**Bug possível:**

Se dois testes rodam em paralelo:
```
Teste A: salvar_sessao_temporaria(..., tenant_id="dono_456", ...)
Teste B: salvar_sessao_temporaria(..., tenant_id="dono_456", ...)

Ambos salvam em:
/Clientes/dono_456/Sessoes/...

Resultado: Dados interferem, testes ficam flaky (falham ~50% das vezes)
```

---

## 📋 TESTE 4: test_patch_p0_cancelamento_firebase.py

### Contrato do Teste

```python
# SETUP: Firebase real + credenciais
@classmethod
def setup_class(cls):
    """Setup Firebase conexão"""
    import firebase_admin
    cred = credentials.Certificate(FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred)
    cls.db = firestore.client()

# TESTE: E2E com Firebase real
async def test_e2e_criar_eventos_e_cancelar_com_filtro(self):
    dono_id = "test_dono_123"
    cliente_id = "test_cliente_456"
    
    # 1️⃣ Criar eventos de teste no Firebase
    evento_1 = {
        "cliente_id": cliente_id,  # "test_cliente_456" (SEM prefixo)
        "profissional": "Bruna",
        "status": "confirmado",
    }
    
    # Persistir
    await salvar_evento(evento_1, dono_id)
    
    # 2️⃣ Cancelar
    resultado = await cancelar_evento(
        user_id=cliente_id,  # "test_cliente_456"
        event_id=evento_1_id
    )
    
    assert resultado == True, "Cancelamento sucesso"
```

### Contrato Real (Produção)

```
1. Criação de evento em produção
   cliente_id = "whatsapp:5511991382080"  # COM prefixo
   evento = {
       "cliente_id": cliente_id,
       "status": "confirmado",
   }
   
   Firestore persiste COM prefixo

2. Cancelamento em produção
   user_id = "whatsapp:5511991382080"  # COM prefixo
   
   ok = await cancelar_evento(
       user_id=user_id,  # "whatsapp:..." COM prefixo
       event_id="...",
   )
   
   Validação:
   if cliente_id_evento != user_id:
       return False
   
   cliente_id_evento = "whatsapp:..." (do Firestore)
   user_id = "whatsapp:..." (passado)
   ✅ PASSA

3. Entre msg1 e msg2
   Contexto preservado?
   Identificação mantida?
   Paths consistentes?
```

### Comparação

| Aspecto | Teste | Produção | Divergência |
|---------|-------|----------|-----------|
| cliente_id | "test_cliente_456" (SEM) | "whatsapp:..." (COM) | 🔴 **ALTO**: Teste não valida prefixo real |
| Uma chamada? | Sim, só testa criação+cancel | REAL tem msg1, msg2, msg3... | 🔴 **ALTO**: Não testa continuidade |
| Múltiplas msg? | Não, apenas 2 etapas | REAL tem 5+ etapas | ⚠️ **MÉDIO**: Não testa todo fluxo |
| Cleanup? | Manual/ausente | Deve limpar depois | ⚠️ **MÉDIO**: Dados acumulam |
| UUID isolation? | Hardcoded tenant | Deve usar UUID | 🔴 **ALTO**: Colisão se múltiplos testes |

### Classificação

**CATEGORIA: A — TESTE INCOMPLETO E COM DIVERGÊNCIA**

**Por quê:**

- 🔴 Usa Firestore real, mas cliente_id SEM prefixo (diverge do real)
- 🔴 Uma única chamada = não detecta P0.10 (divergência entre msg1/msg2)
- 🔴 Sem UUID = colisão em paralelo
- ⚠️ Se corrigido, seria bom teste (E2E real)

---

## 📊 RESUMO EXECUTIVO

### Quantidade de Testes Analisados

| Teste | Classificação | Risco Real | Ação Recomendada |
|-------|--------------|-----------|-----------------|
| test_patch_p0_cancelamento.py | B | Nenhum bug real | Refatorar para contrato real COM prefixo |
| test_p0_cancelamento_idle.py | A | Múltiplos possíveis | Reescrever com Firestore real |
| test_patch_p0_bloqueio_contexto.py | A | Colisão de dados | Adicionar UUID, múltiplas msgs |
| test_patch_p0_cancelamento_firebase.py | A | Divergência prefixo | Adicionar cliente_id COM prefixo, múltiplas msgs |

### Bugs Reais de Produção

**Resultado:** ❌ **NENHUM BUG REAL DETECTADO**

Explicação:
- ✅ Produção está CORRETA: cliente_id armazenado COM prefixo, validação consistente
- ✅ Fluxo é CORRETO: identidade_p01.actor_id é passado corretamente
- ❌ Testes estão INCORRETOS: usam SEM prefixo, hardcoded tenant_id, uma chamada

### Riscos Potenciais

1. **Colisão de dados em paralelo** — POSSÍVEL se dois testes usam mesmo tenant_id
2. **Falha silenciosa de Firestore** — NÃO DETECTADA em testes com mock
3. **Divergência entre msg1 e msg2** — NÃO DETECTADA em testes com uma chamada
4. **Prefixo de identidade** — NÃO VALIDADA em testes com SEM prefixo

---

## 🎯 DECISÃO FINAL

### Pergunta Crítica

**Podemos iniciar a preparação da Categoria A agora ou existe algum BUG DE PRODUÇÃO que precisa ser resolvido primeiro?**

### Resposta

✅ **SIM, PODEMOS INICIAR A PREPARAÇÃO**

**Motivo:**
- ❌ Não há bug real de produção confirmado
- ✅ Produção está funcionando corretamente
- 🔧 Testes estão apenas **mal especificados**
- 📝 Solução é **refatoração de testes**, não correção de código

### Ordem Recomendada

#### FASE 1: Refatoração Pré-Conversão (2-3 horas)

Para cada teste, ANTES de converter para E2E:

1. **test_patch_p0_cancelamento.py**
   - [ ] Adicionar cliente_id COM prefixo "whatsapp:"
   - [ ] Validar que user_id tem MESMO prefixo
   - [ ] Adicionar segunda chamada (confirmação)

2. **test_p0_cancelamento_idle.py**
   - [ ] Remover mocks, usar Firestore real
   - [ ] Adicionar múltiplas chamadas (msg1, msg2)
   - [ ] Usar UUID para tenant_id

3. **test_patch_p0_bloqueio_contexto.py**
   - [ ] Usar UUID para tenant_id (não hardcoded)
   - [ ] Verificar Firestore realmente isolou
   - [ ] Adicionar teste de paralelo/colisão

4. **test_patch_p0_cancelamento_firebase.py**
   - [ ] Manter Firestore real ✅
   - [ ] Adicionar cliente_id COM prefixo
   - [ ] Adicionar segunda chamada (confirmação)

#### FASE 2: Conversão Real (4-8 horas)

Após refatoração:
- [ ] Convert para E2E com fixtures
- [ ] Validar que testes PASSAM
- [ ] Validar que testes DETECTARIAM P0.10

---

**Conclusão:** Pode prosseguir com preparação. Nenhum bloqueador de produção.

**Próximo passo:** Iniciar refatoração pré-conversão seguindo checklist acima.

---

**FIM DA INVESTIGAÇÃO**

**Data:** 2026-10-08  
**Auditor:** Claude Code (Análise READ-ONLY, sem alterações)  
**Status:** ✅ Investigação Concluída
