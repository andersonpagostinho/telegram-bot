# LOTE 4C — CORREÇÃO SETUP DO CENÁRIO 06 COM MockUpdate

**Data:** 2026-06-22  
**Escopo:** Somente cenário 06 (e 07 para regressão)  
**Objetivo:** Corrigir setup para passar object Update válido em vez de None

---

## RESULTADO: PROGRESSO SIGNIFICATIVO ✅

### Antes (LOTE 4B)

```
AttributeError: 'NoneType' object has no attribute 'message'
❌ Falha imediatamente em executar_acao_gpt:178
```

### Depois (LOTE 4C)

```
✅ executar_acao_gpt é chamado e executa
✅ add_evento_por_gpt é chamado
❌ Falha posterior em operação diferente (novo stacktrace)
```

---

## IMPLEMENTAÇÃO

### MockUpdate Class

Adicionada em `tests/p1_robustez_fluxo_conversacional_real.py:336`:

```python
class MockUpdate:
    """Mock mínimo de Update do Telegram para cenários que precisam de update real"""

    def __init__(self, user_id: str, chat_id: str = "12345", text: str = ""):
        # Estrutura mínima que executar_acao_gpt espera
        self.message = MagicMock()
        self.message.from_user = MagicMock()
        self.message.from_user.id = user_id
        self.message.chat = MagicMock()
        self.message.chat.id = chat_id
        self.message.text = text
        self.message.reply_text = AsyncMock(return_value={"ok": True})

        # Fallback para effective_user/effective_chat
        self.effective_user = self.message.from_user
        self.effective_chat = self.message.chat
```

### Atualização de Cenários

- **Cenário 06:** Linha 649 — `update=None` → `update=MockUpdate(actor_id, chat_id=tenant_id, text=mensagem)`
- **Cenário 07:** Linha 719 — `update=None` → `update=MockUpdate(actor_id, chat_id=tenant_id, text=mensagem)`

---

## VALIDAÇÃO PÓS-CORREÇÃO

### Cenário 07 (Negação): ✅ PASS CONFIRMADO

```
[LOTE_3E_NEGACAO_EARLY] Negação detectada
[LOTE_3E_NEGACAO] Desistencia detectada
[PASS] 07. Negação embutida em parágrafo
```

**Status:** MANTÉM-SE PASS (sem regressão)

### Cenário 06 (Confirmação): ❌ AVANÇA MAS FALHA

**Novo Ponto de Falha Identificado:**

```
[LOTE_3E_CONFIRMACAO_EARLY] Confirmação detectada ✅
[LOTE_3E_CONFIRMACAO] Confirmacao detectada ✅
[AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto ✅
🪵 Ação recebida: 'criar_evento' ✅
🔁 Ação recebida: criar_evento ✅
📦 Dados: {...} ✅
[TESTE_SURI] 3️⃣ DADOS_EXECUTAR_ACAO: ... ✅
⚙️ Executando add_evento_por_gpt ✅
❌ [CTX_LEGADO_TENANT_MISMATCH] CRÍTICO | tenant mismatch
```

---

## NOVO ERRO IDENTIFICADO

### Tipo: Tenant Mismatch em gpt_executor.py

**Log Detalhado:**

```
[DIAG_CARREGAR] path_legado=Clientes/whatsapp:55119999006/MemoriaTemporaria/contexto 
               | tenant_id=whatsapp:55119999006 
               | user_id=whatsapp:55119999006
[DIAG_CARREGAR] guard_validacao: 
               guard_tenant=teste_fluxo_p1_705bdc58 
               | esperado=whatsapp:55119999006 
               | match=False
🚨 [CTX_LEGADO_TENANT_MISMATCH] CRÍTICO | 
   path=Clientes/whatsapp:55119999006/MemoriaTemporaria/contexto 
   | tenant mismatch: 
   esperado=whatsapp:55119999006 
   | armazenado=teste_fluxo_p1_705bdc58, 
   leitura RECUSADA
```

### Causa Raiz

Em `services/gpt_executor.py:543-561`:

```python
user_id = _obter_user_id(update, context)  # user_id = whatsapp:55119999006
dono_id = await obter_id_dono(user_id)     # dono_id = whatsapp:55119999006 (ERRADO!)

contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=dono_id)
# Tenta carregar de:
# path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"
#      = "Clientes/whatsapp:55119999006/MemoriaTemporaria/contexto"
# 
# Mas busca guard_tenant de:
# contexto = "Clientes/whatsapp:55119999006/MemoriaTemporaria/contexto"
# guard_tenant = "teste_fluxo_p1_705bdc58"
# 
# Valida com tenant_id=dono_id = "whatsapp:55119999006"
# Match: "teste_fluxo_p1_705bdc58" != "whatsapp:55119999006"
# ❌ MISMATCH → contexto rejeitado
```

### Contrato Quebrado

`obter_id_dono(whatsapp:55119999006)` está retornando `whatsapp:55119999006` (o mesmo) em vez de `teste_fluxo_p1_705bdc58` (o tenant_id real).

---

## PROBLEMA RAIZ: Mock de obter_id_dono

**Em teste cenário 06:**

```python
with patch('router.principal_router.obter_id_dono') as mock_obter_id:
    mock_obter_id.return_value = tenant_id
```

✅ **Router usa:** `tenant_id = teste_fluxo_p1_705bdc58`

❌ **gpt_executor.py não está patchado**, chama `obter_id_dono` de verdade:

```python
dono_id = await obter_id_dono(user_id)  # user_id = whatsapp:55119999006
# Sem patch, busca dono real no Firestore
# Para um novo actor_id aleatório, Firestore retorna None ou mesmo actor_id
# Nesse caso parece retornar o próprio user_id
```

---

## STATUS FINAL

| Item | Status | Nota |
|------|--------|------|
| MockUpdate implementado | ✅ | Estrutura válida do Telegram |
| Cenário 07 | ✅ PASS | Sem regressão |
| Cenário 06 - LOTE 3E Handler | ✅ FUNCIONA | Confirmação detectada corretamente |
| Cenário 06 - executar_acao_gpt | ✅ CHAMADO | MockUpdate resolve erro original |
| Cenário 06 - add_evento_por_gpt | ✅ CHAMADO | Avançou muito além do erro anterior |
| Cenário 06 - contexto em gpt_executor | ❌ TENANT MISMATCH | Novo ponto de falha |

---

## RECOMENDAÇÃO PRÓXIMO LOTE (4D)

**Problema:** `obter_id_dono()` não foi patchado para gpt_executor.py

**Opção 1:** Estender patch para gpt_executor também

```python
with patch('router.principal_router.obter_id_dono') as m1, \
     patch('services.gpt_executor.obter_id_dono') as m2:
    m1.return_value = tenant_id
    m2.return_value = tenant_id
```

**Opção 2:** Configurar test para que `obter_id_dono(whatsapp:xxx)` retorne tenant_id

**Opção 3:** Verificar se o contrato de `obter_id_dono` está correto

---

## LOGS COMPLETOS

### Sucesso: Handler + executar_acao_gpt

```
[LOTE_3E_CONFIRMACAO_EARLY] Confirmação detectada: pode deixar...
[LOTE_3E_CONFIRMACAO] Confirmacao detectada
[AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto
🪵 Ação recebida: 'criar_evento'
🔁 Ação recebida: criar_evento
📦 Dados: {'profissional': 'Bruna', 'servico': 'corte', 'data_hora': 'amanhã 14:00', 'duracao': 30, 'descricao': 'Corte com Bruna', 'confirmado': True, 'status': 'confirmado'}
[TESTE_SURI] 3️⃣ DADOS_EXECUTAR_ACAO: user_id='whatsapp:55119999006'
[TESTE_SURI] 3️⃣ DADOS_EXECUTAR_ACAO: acao='criar_evento'
[TESTE_SURI] 3️⃣ DADOS_EXECUTAR_ACAO: dados_keys=['profissional', 'servico', 'data_hora', 'duracao', 'descricao', 'confirmado', 'status']
[TESTE_SURI] 3️⃣ DADOS_EXECUTAR_ACAO: profissional='Bruna'
⚙️ Executando add_evento_por_gpt
```

### Falha: Tenant Mismatch

```
[DIAG_CARREGAR] guard_validacao: 
    guard_tenant=teste_fluxo_p1_705bdc58 
    | esperado=whatsapp:55119999006 
    | match=False
🚨 [CTX_LEGADO_TENANT_MISMATCH] CRÍTICO
[FAIL] 06. Confirmação embutida em parágrafo - Erro: 'bool' object has no attribute 'get'
```

---

## VALIDAÇÃO: BASELINE CONTINUADO

✅ **Baseline 216/216 PASS** — Não há risco, apenas teste local

---

## CONCLUSÃO

**LOTE 4C alcançou objetivo:** Setup corrigido com MockUpdate válido.

**Novo ponto identificado:** Tenant mismatch em contexto carregado dentro de gpt_executor.

**Próximo passo:** Estender patch de `obter_id_dono` para gpt_executor (LOTE 4D proposto).
