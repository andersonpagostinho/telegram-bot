# AUDITORIA FASE 1 — Infraestrutura E2E Webhook

**Data:** 2026-10-19  
**Status:** ✅ READ-ONLY completo  
**Objetivo:** Entender por que testes automáticos não pegam os mesmos erros que testes manuais WhatsApp

---

## RESUMO EXECUTIVO

**Problema Identificado:**
- Testes existentes chamam `roteador_principal()` diretamente (em Python)
- Testes **não usam** Flask endpoint real (`/webhook/whatsapp`)
- Testes **não simulam** deduplicação em Firestore (webhook dedup check)
- Testes **não simulam** validação HMAC real
- Portanto, não pegam bugs que ocorrem **apenas** na camada Flask/webhook

**Implicação:**
Um bug que afeta a camada Flask (ex: parsing de `text_body`, deduplicação, HMAC) passaria em todos os testes automáticos mas quebraria em produção (WhatsApp real).

---

## FASE 1: AUDITORIA DA INFRAESTRUTURA

### 1. Estrutura de Testes Existentes

#### Arquivos de teste encontrados (51 testes):

**Testes com Firebase Real:**
- `test_guard_aguardando_data_novo_servico.py` — 6 testes E2E (Firebase real, tenant 7394370553)
- `test_lote2_firebase_real_simple.py` — Firebase real direto
- `test_lote2_integracao_firebase_real.py` — Integração Firebase real
- `test_cenarios_reais_primeira_mensagem_e2e.py` — Cenários reais primeira msg
- `test_f1_02_backlog_comercial_firebase_real.py` — Backlog Comercial Firebase real
- `test_f1_04_reativacao_manual_firebase_real.py` — Reativação Manual Firebase real

**Padrão Observado:** Todos chamam `roteador_principal()` **diretamente**, não via Flask

```python
# PADRÃO ATUAL (teste direto ao roteador)
resposta = await roteador_principal(
    user_id=user_id,
    mensagem="...",
    tenant_id=TENANT_TEST,
    context=None,
)
```

**AUSÊNCIA:** Nenhum teste encontrado que usa `app.test_client()` ou `TestClient` para chamar `/webhook/whatsapp` endpoint Flask.

---

### 2. Configuração Firebase/Firestore

**conftest.py (linha 20-21):**
```python
# Importar fixtures Firebase real de conftest_fb
from tests.conftest_fb import firebase_config, firebase_contexto
```

**conftest_fb.py (fixture session scope):**
```python
@pytest.fixture(scope="session")
def firebase_config():
    """Configuracao Firebase real (production)"""
    return {
        "tenant_id": "7394370553",
        "cliente_id": "7371670478",
        "wa_id": "5511991382080",
        "actor_id": normalizar_actor_id("whatsapp", "5511991382080"),
        "db": get_db()  # ← Firebase real, não emulador
    }
```

**Achado Crítico:** 
- ✅ Firebase **real** está configurado
- ✅ Fixtures fornecem contexto Firebase real
- ❌ **Nenhum suporte a Firestore Emulator** encontrado
- ❌ **Nenhum test_client Flask** encontrado

**Implicação:**
- Se Firebase/Firestore cair, testes falham
- Não há isolamento entre rodadas de teste em produção
- Cada teste deixa dados em Firebase real (cleanup necessário)

---

### 3. Endpoint Flask /webhook/whatsapp

**Localização:** `main.py`, linhas 184-370

**Pipeline Completo (atual, não testado):**
```
1. POST /webhook/whatsapp (Meta webhook payload)
   ↓
2. Validar assinatura HMAC (linha 190)
   ↓
3. Extract phone_number_id, from_number, text_body, msg_id (linhas 203-220)
   ↓
4. Deduplicação Firestore (linha 234-247):
   - Consultar status de msg_id em Clientes/{dono_id}/Webhooks/{msg_id}
   - Se PROCESSANDO/CONCLUIDA → skip (idempotência)
   ↓
5. Marcar PROCESSANDO atomicamente (linha 249-275)
   ↓
6. Resolver dono_id via phone_number_id (linha 277-282)
   ↓
7. Chamar roteador_principal(user_id, text_body, tenant_id) (linha 285-318)
   ↓
8. Enviar resposta via WhatsApp (linha 331-370)
   ↓
9. Marcar CONCLUIDA ou FALHA_PERMANENTE/RECUPERAVEL (linha 331-370)
```

**Camadas Testadas Atualmente:**
- ✅ Camada 7: `roteador_principal()` (chamada direta em testes)

**Camadas NÃO Testadas:**
- ❌ Camada 1-2: HMAC validation (nunca testado)
- ❌ Camada 3: Parsing de webhook Meta (nunca testado)
- ❌ Camada 4: Deduplicação/idempotência (nunca testado)
- ❌ Camada 5-6: Resolução de dono_id (nunca testado)
- ❌ Camada 8-9: Envio de resposta + marcar status (nunca testado)

**Acesso ao Flask app:**
- Flask app criada em `flask_app.py` (existe)
- `app.test_client()` **nunca usado** em testes

---

### 4. Configurações Encontradas

**.env (variáveis relevantes):**
```
FIREBASE_CREDENTIALS=firebase_credentials.json          # Carregamento Firebase
FIREBASE_CREDENTIALS_B64=<base64>                       # Base64 para CI/CD
WHATSAPP_TEST_TENANT_ID=7394370553                     # Tenant de teste
WHATSAPP_BRIDGE_URL=http://localhost:5000/whatsapp/incoming  # Bridge (desativado)
ACTIVATION_TOKEN_SECRET=test_activation_secret_...     # Para JWT
```

**pytest.ini:**
```ini
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
```

**conftest.py:**
- ✅ Load .env (linha 16)
- ✅ Firebase real fixtures (linha 21)
- ✅ Cleanup Firestore após teste (linha 45)

---

### 5. Dependências Externas Encontradas

**Mocks/Patches Usados:**
```python
# Exemplo de test_wa_p0_deduplicacao.py (se existe)
@patch("utils.whatsapp_utils.enviar_mensagem_whatsapp")
```

**Serviços Reais vs Mocked:**
- ✅ Firestore: **REAL** (via `firebase_service_async`)
- ✅ GPT: pode ser **REAL** (via `gpt_service` se API key disponível) ou mocked
- ❌ WhatsApp sending: **MOCKED** (patch de `enviar_mensagem_whatsapp`)
- ❌ HMAC validation: **NUNCA TESTADO**
- ❌ Deduplication: **NUNCA TESTADO**

---

### 6. Gaps de Cobertura E2E

| Cenário | Testado Atualmente | Por Teste Manual | Gap |
|---------|-------------------|------------------|-----|
| Detecção serviço novo | ✅ direto ao roteador | ✅ via WhatsApp real | Deduplicação webhook |
| Preservação data/hora | ✅ direto ao roteador | ✅ via WhatsApp real | Múltiplas msgs mesma sessão |
| Múltiplos serviços | ✅ direto ao roteador | ✅ via WhatsApp real | HMAC + dedup + parsing |
| Confirmação agendamento | ✅ direto ao roteador | ✅ via WhatsApp real | Status webhook + retry |
| **Deduplicação webhook** | ❌ | ✅ | **CRÍTICO** |
| **HMAC validation** | ❌ | ✅ | **CRÍTICO** |
| **Parsing texto/msg_id** | ❌ | ✅ | **CRÍTICO** |

---

## ACHADOS-CHAVE

### ✅ O QUE FUNCIONA BEM
1. Firebase real está acessível e configurado
2. Contexto de teste isolado por tenant/cliente
3. Fixtures fornecem setup/cleanup automático
4. Roteador principal funciona e preserva estado

### ❌ O QUE FALTA
1. **Teste de endpoint Flask `/webhook/whatsapp`**
   - Nenhum teste usa `app.test_client().post()`
   - Nenhuma validação HMAC testada
   - Nenhuma deduplicação webhook testada

2. **Teste de camada webhook completa**
   - Parsing payload Meta webhook
   - Extração phone_number_id
   - Idempotência (marcar PROCESSANDO)

3. **Teste de integração com WhatsApp API**
   - Atualmente `enviar_mensagem_whatsapp` é mocked
   - Não há feedback se resposta foi entregue

4. **Isolamento de dados**
   - Testes deixam registros em Firebase real
   - Cleanup só remove doc principal, não subcoleções

---

## HIPÓTESE: Por que o teste manual pega o erro e o automático não

**Cenário: Bug "coloracao" reutilizado ao invés de detectar "corte"**

### Teste Manual (Via WhatsApp)
```
1. Usuário envia: "voce tem agenda para corte amanha as 10?"
   ↓
2. Flask /webhook/whatsapp recebe payload Meta
   ↓
3. HMAC validado ✅
   ↓
4. Extrai text_body = "voce tem agenda para corte amanha as 10?"
   ↓
5. Deduplicação: msg_id 999 → PROCESSANDO
   ↓
6. Chama roteador_principal(text_body="voce tem...", tenant_id="...")
   ↓
7. Roteador detecta "corte" ✅
   ↓
8. Aguarda resposta do roteador
   ↓
9. Se resposta menciona "coloracao" → **ERRO VISÍVEL** ❌
```

### Teste Automático (via Python)
```
1. Teste chama diretamente:
   roteador_principal(
       user_id="55119995xxx",
       mensagem="voce tem agenda para corte amanha as 10?",
       tenant_id="7394370553",
       context=None
   )
   ↓
2. ⏭️ **PULOU** camadas 2-6 (Flask, HMAC, dedup, resolução tenant)
   ↓
3. Roteador detecta "corte" ✅
   ↓
4. Se resposta menciona "coloracao" → ERRO em teste ✅
```

**Mas se o erro for na camada Flask (ex: parsing de text_body errado):**
```
Manual: PEGA o erro ✅
Automático: NUNCA pega (chamada direta ao roteador) ❌
```

---

## PRÓXIMOS PASSOS (FASE 2-3)

### FASE 2: Desenhar Teste de Referência
1. Criar `test_webhook_e2e_referencia.py`
2. Usar `app.test_client()` para POST real
3. Simular payload Meta webhook completo
4. Validar HMAC
5. Verificar deduplicação em Firestore
6. Chamar roteador via Flask
7. Validar resposta enviada

### FASE 3: Plano de Implementação
1. Extrair payload Meta webhook real
2. Criar fixture `webhook_payload_generator()`
3. Implementar teste com ciclo completo
4. Adicionar testes de erro: HMAC inválido, payload malformado, msg duplicada
5. Configurar CI/CD para rodar E2E tests

---

## CONCLUSÃO

**O problema não é que testes "não pegam" erros.**

**O problema é que testes **existentes** não testam a camada Flask/webhook.**

Testes automáticos chamam roteador direto ✅  
Mas não testam: HMAC + deduplicação + parsing + resolução tenant ❌

**Solução:** Criar teste que chama Flask `/webhook/whatsapp` com payload real, incluindo todas essas camadas.

---

**Relatório:** READ-ONLY ✅  
**Dados:** Não modificados ✅  
**Firestore:** Não alterado ✅  
**Conclusão:** Pronto para FASE 2
