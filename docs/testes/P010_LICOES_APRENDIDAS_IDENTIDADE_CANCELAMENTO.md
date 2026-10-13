# 📚 P0.10 — Lições Aprendidas: Identidade e Cancelamento

**Data:** 2026-10-08  
**Commit:** 850252a  
**Escopo:** Cancelamento de eventos com identidade canônica  
**Status:** ✅ Resolvido

---

## 🎯 Problema Identificado

### Erro Original
```
[CANCELAMENTO_BLOQUEADO] usuario=5511991382080 nao eh cliente_id=whatsapp:5511991382080
```

**Divergência:** Comparação entre formatos diferentes de identidade
- `usuario` recebido: `"5511991382080"` (SEM prefixo)
- `cliente_id` em Firestore: `"whatsapp:5511991382080"` (COM prefixo)
- Validação: `if cliente_id_evento != user_id` → BLOQUEADO

---

## 🔍 Análise da Causa-Raiz

### Código Problemático (Antes)
```python
# router/principal_router.py:3719-3721 (ANTES)
user_id_para_cancelamento = (
    identidade_p01.actor_id 
    if identidade_p01 and identidade_p01.actor_id 
    else user_id
)
# Remove prefixo (whatsapp:) para manter compatibilidade com cliente_id armazenado
user_id_para_cancelamento = user_id_para_cancelamento.split(":")[-1] if ":" in user_id_para_cancelamento else user_id_para_cancelamento

ok = await cancelar_evento(user_id=user_id_para_cancelamento, ...)
```

**Problema:** A transformação `split(":")[-1]` estava removendo o prefixo `whatsapp:` desnecessariamente.

**Fluxo problemático:**
```
identidade_p01.actor_id = "whatsapp:5511991382080"
    ↓ split(":")[-1]
user_id_para_cancelamento = "5511991382080"  ← SEM prefixo
    ↓
cancelar_evento(user_id="5511991382080")
    ↓
cliente_id_evento = "whatsapp:5511991382080"  ← COM prefixo
    ↓
"5511991382080" != "whatsapp:5511991382080"  → BLOQUEADO ❌
```

---

## ✅ Solução Aplicada

### Código Corrigido (Depois)
```python
# router/principal_router.py:3719 (DEPOIS)
user_id_para_cancelamento = (
    identidade_p01.actor_id 
    if identidade_p01 and identidade_p01.actor_id 
    else user_id
)

ok = await cancelar_evento(user_id=user_id_para_cancelamento, ...)
```

**Mudança:** Remover a transformação `split(":")[-1]`

**Fluxo corrigido:**
```
identidade_p01.actor_id = "whatsapp:5511991382080"
    ↓ (SEM transformação)
user_id_para_cancelamento = "whatsapp:5511991382080"  ← COM prefixo
    ↓
cancelar_evento(user_id="whatsapp:5511991382080")
    ↓
cliente_id_evento = "whatsapp:5511991382080"  ← COM prefixo
    ↓
"whatsapp:5511991382080" == "whatsapp:5511991382080"  ✅ IGUAL
```

---

## 🧪 Validação

### Testes Executados
- ✅ `test_p0_cancelamento_e2e_firebase_real.py`: 2/2 PASS
- ✅ `test_c310_fase2b2_ownership_checks.py`: T1, T2 PASS (cancelamento)

### Validação de Contrato
| Variável | Esperado | Obtido | Status |
|----------|----------|--------|--------|
| `identidade_p01.actor_id` | `whatsapp:...` | `whatsapp:5511991382080` | ✅ |
| `user_id_para_cancelamento` | `whatsapp:...` | `whatsapp:5511991382080` | ✅ |
| `cliente_id_evento` | `whatsapp:...` | `whatsapp:5511991382080` | ✅ |
| Comparação | Igual | Igual | ✅ |

---

## 🎓 Lições para Próximos Testes

### 1. **Identidade Canônica é Crítica**
- **Regra:** Sempre preservar a identidade canônica COM prefixo através de todo o fluxo
- **Aplicar em:** Todos os fluxos que envolvem cancelamento, edição ou deleção
- **Teste:** Validar que `actor_id` com prefixo chega ao endpoint de validação

### 2. **Contrato Firestore = Contrato de Validação**
- **Regra:** Se um campo em Firestore tem prefixo, a comparação DEVE ser contra o mesmo prefixo
- **Aplicar em:** `event_service_async.py:306` e qualquer função que valida ownership
- **Teste:** Verificar que `cliente_id_evento` e `user_id` param têm MESMO formato

### 3. **Transformações de Identidade São Perigosas**
- **Regra:** Não remover/adicionar prefixos no meio do fluxo sem motivo comprovado
- **Anti-padrão:** `.split(":")[-1]` para "normalização local"
- **Padrão correto:** Manter identidade canônica até o ponto de persistência/validação

### 4. **Dois Fluxos Paralelos = Dois Riscos**
- **Descoberta:** Havia 2 callsites de `cancelar_evento()`
  - ✅ `router/principal_router.py:3722` (WhatsApp, via roteador)
  - ❌ `handlers/bot.py:411` (Telegram, sem normalização de identidade)
- **Aplicar em:** Quando há 2+ callsites, validar TODOS em testes
- **Teste:** Criar teste que executa AMBOS os fluxos (WhatsApp e Telegram)

### 5. **Testes Automatizados Podem Esconder Bugs**
- **Descoberta:** Teste automatizado PASSED mas produção falhou
  - Causa: Teste construía identidade manualmente (nunca era `None`)
  - Produção: Identidade chegava através do webhook (tinha prefixo)
  - Gap: Teste não reproduzia fluxo real
- **Aplicar em:** Sempre usar E2E com Firestore real, não mocks
- **Teste:** Validar que teste falha SEM o prefixo, passa COM o prefixo

### 6. **Rastreamento de Variável é Obrigatório**
- **Descoberta:** Não é óbvio que `split(":")[-1]` fosse prejudicial
- **Aplicar em:** Para qualquer transformação de identidade, documentar:
  - Valor esperado antes
  - Valor esperado depois
  - Por que é feita
  - Onde será usado
- **Teste:** Mock com valores diferentes (com/sem prefixo) e validar caminho

### 7. **Documentação de Contrato é Chave**
- **Descoberta:** Contrato Firestore vs contrato function param estava implícito
- **Aplicar em:** Documentar em comentário qual formato esperar em cada ponto
- **Padrão:**
```python
# [CONTRATO] user_id deve estar COM prefixo whatsapp: para WhatsApp
# [ORIGEM] vem de identidade_p01.actor_id (sempre tem prefixo)
# [VALIDAÇÃO] Será comparado com cliente_id em Firestore (também tem prefixo)
```

---

## 🔧 Checklist para Próximos Testes P0

- [ ] **Teste E2E completo** com Firestore real (não mocks)
- [ ] **Múltiplos callsites** se existem 2+ pontos de entrada
- [ ] **Rastreamento de identidade** da origem até validação
- [ ] **Teste com/sem prefixo** para verificar que transformações funcionam
- [ ] **Fluxo WhatsApp e Telegram** separados, se ambos existem
- [ ] **Contrato documentado** em comentários do código
- [ ] **Validação de ownership** com valores reais (não genéricos)
- [ ] **Log de valor interpolado** no warning (para debug futuro)

---

## 📊 Impacto em Próximas Features

### P1 (Onboarding Dono)
**Aplicar:** Use identidade canônica COM prefixo em toda a cadeia de validação

### P2 (Reagendamento)
**Aplicar:** Rastreamento de identidade em `roteador_principal()` → `agenda_service()` → `salvar_evento()`

### Cualquier Feature com Identidade
**Aplicar:** 
1. Documentar contrato de identidade em cada função
2. Testar com E2E real (não mocks)
3. Validar que prefixo é preservado ou removido CONSISTENTEMENTE

---

## 🎯 Resumo Executivo

**Lição Central:** Identidade canônica COM prefixo é o contrato verdadeiro no sistema. Não remover prefixos no meio do fluxo "por compatibilidade" — manter consistência é a verdadeira compatibilidade.

**Aplicação:** Para TODOS os testes P0+ que envolvem identidade, ownership ou cancelamento, validar que prefixo é preservado até o ponto de persistência/comparação.

---

**Commit relacionado:** `850252a` (Fix: P0.10 — Preservar identidade canônica com prefixo no cancelamento)  
**Data de implementação:** 2026-10-08  
**Atualização de memória:** [[P0.10 Lições Aprendidas Identidade]]
