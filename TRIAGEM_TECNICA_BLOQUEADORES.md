# 🔴 TRIAGEM TÉCNICA — BLOQUEADORES CONFIRMADOS

**Data**: 2026-10-18  
**Modo**: READ-ONLY (sem alterações)  
**Status**: ✅ Inspeção de Causa Raiz

---

## 📋 BLOQUEADOR #1: Fixture `firebase_sync` Faltando (18 ERRORs)

### Evidência Concreta
- **Arquivo**: `tests/test_p01_confirmacao_firebase_real.py:59`
- **Erro**: `fixture 'firebase_sync' not found`
- **Linha do Erro**:
  ```python
  @pytest.fixture(autouse=True)
  async def setup(self, firebase_sync):  # ← pytest procura aqui
  ```

### Causa Raiz Confirmada
```
conftest.py (carregado por pytest)
├─ Não importa conftest_fb.py
└─ Fixture firebase_sync NÃO disponível

conftest_fb.py (existe mas não carregado)
└─ @pytest.fixture def firebase_sync (linha 131)
```

### Código de Produção Envolvido
- **Arquivo**: `tests/conftest_fb.py:131-165`
- **Função**: `firebase_sync(firebase_config)`
- **O que faz**: Wrapper sync para acesso ao Firestore em testes não-async

### Menor Alteração Necessária
**Arquivo**: `tests/conftest.py`  
**Ação**: Adicionar import
```python
# Adicionar após linhas 10-12 em conftest.py:
from tests.conftest_fb import *  # Carregar fixtures de Firebase real
```

### Teste que Comprovará
- **Arquivo**: `tests/test_p01_confirmacao_firebase_real.py`
- **Quantidade**: 18 testes
- **Comando**: `pytest tests/test_p01_confirmacao_firebase_real.py -v`
- **Esperado após fix**: 18 testes conseguem rodar (eram 18 ERROR)

### Risco de Regressão
**BAIXO**: Import apenas adiciona fixtures não conflitantes  
**Verificar**: Nenhum outro arquivo redefine `firebase_sync`

---

## 🔴 BLOQUEADOR #2: Isolamento de Tenant (1 FAIL Crítica)

### Evidência Concreta
- **Arquivo**: `tests/test_p0_firebase_real_tenant_isolation.py`
- **Teste**: Isolamento tenant
- **Falha**: Evento criado no tenant errado (Clientes/None ou Clientes/user_id)
- **Risco**: ⚠️ SEGURANÇA MULTI-TENANT

### Causa Raiz Hipotética (Verificar)
**Provável**: Fallback inseguro ainda ativo em uma função de criação de evento
```python
# Padrão perigoso (PROCURAR):
salao_id = tenant_id or user_id  # ← INSEGURO

# Ou:
path = f"Clientes/{user_id}/..."  # ← DEVE SER {tenant_id}
```

### Código de Produção a Inspecionar
- `services/agenda_service.py` — funções de criação/leitura
- `services/event_handler.py` — add_evento, add_evento_por_gpt
- `services/notificacao_service.py` — criar_notificacao_agendada
- Verificar linhas com `Clientes/` para confirmar uso de `tenant_id`

### Menor Alteração Necessária
**Procurar**: Qualquer fallback `tenant_id or user_id` ou path com `user_id`  
**Remover**: Fallback inseguro  
**Confirmar**: Validação `if not tenant_id: return` ou similar

### Teste que Comprovará
- **Arquivo**: `tests/test_p0_firebase_real_tenant_isolation.py`
- **Comando**: `pytest tests/test_p0_firebase_real_tenant_isolation.py -v`
- **Esperado**: Evento criado em `Clientes/{tenant_id}/Eventos` (não None/user_id)

### Risco de Regressão
**ALTO**: Isolamento é crítico. Qualquer alteração pode quebrar multi-tenant.  
**Mitigação**: Reexecutar TODOS os 368 testes após fix

---

## 🟠 BLOQUEADOR #3: Contrato de Mensagem (8 FAILs)

### Evidência Concreta
- **Arquivos**: 
  - `tests/test_p08_2_contrato_unitario_confirmacao.py` (6 FAILs)
  - `tests/test_p04_gate_direto.py` (2 FAILs)
  
- **Falha**: AssertionError na mensagem
  ```
  Esperado: "Pronto! Seu horário de corte com Bruna está confirmado para em 19/10 às 10h."
  Recebido: "✨ *Corte com Bruna*\n📆 amanhã às 10h\n\n✅ Horário confirmado!"
  ```

### Causa Raiz Confirmada
**Tipo**: Contrato desatualizado (teste espera formato antigo)  
**Origem**: Template mudou em `montar_mensagem_confirmacao_sucesso()`

### Código de Produção Envolvido
- **Arquivo**: Procurar `montar_mensagem_confirmacao_sucesso()` 
- **Função**: Gera mensagem de confirmação de agendamento
- **Problema**: Template com emojis ≠ esperado pelo teste

### Menor Alteração Necessária
**Opção A**: Atualizar teste para esperar novo formato  
**Opção B**: Restaurar template antigo em `montar_mensagem_confirmacao_sucesso()`

### Qual Escolher?
**VERIFICAR REQUISITO**: A formatação com emojis é INTENCIONAL ou foi erro?
- Se intencional: Atualizar testes
- Se erro: Restaurar template antigo

### Teste que Comprovará
```bash
pytest tests/test_p08_2_contrato_unitario_confirmacao.py -v
pytest tests/test_p04_gate_direto.py -v
```
Esperado: 8 testes PASS após fix

### Risco de Regressão
**MÉDIO**: Mensagem afeta cliente final  
**Validar**: Cliente vai aceitar novo formato?

---

## 🟠 BLOQUEADOR #4: E2E WhatsApp Confirmação (1 FAIL)

### Evidência Concreta
- **Arquivo**: `tests/test_p0_e2e_whatsapp_confirmacao_completo.py:223`
- **Falha**: AssertionError na mensagem ou Firestore
- **Problema**: Evento não chega até Firestore (Règua de Ouro violada)

### Causa Raiz Hipotética
Verificar:
1. Evento criado em `add_evento_por_gpt()`?
2. Path correto em Firestore?
3. Campo `confirmado=True` setado?

### Código de Produção a Inspecionar
- `services/event_handler.py` → `add_evento_por_gpt()`
- Verificar parâmetro `tenant_id` propagado
- Verificar salvamento em Firestore

### Teste que Comprovará
```bash
pytest tests/test_p0_e2e_whatsapp_confirmacao_completo.py -v --tb=short
```

---

## 🟠 BLOQUEADOR #5: Timeout de Sessão (1 FAIL)

### Evidência Concreta
- **Arquivo**: `tests/test_p0_sessao_expirada_teste_rapido.py`
- **Problema**: Sessão não expira após 5 minutos
- **Impacto**: Estado residual pode afetar próximos testes

### Causa Raiz Hipotética
Verificar:
1. Scheduler de limpeza de sessão ativo?
2. Timeout configurado como 5 minutos?
3. Test valida expiração corretamente?

---

## 🟡 OUTROS 20 FAILs (Média/Baixa Severidade)

### Resumo
- **Tipo de Retorno**: 2 FAILs (função retorna dict, teste espera bool)
- **Mock Divergente**: 5 FAILs (problema de fixture/setup)
- **Validação**: 3 FAILs (regra não funcionando)
- **Regressão Menor**: 10 FAILs (diversos)

**Ação**: Inspecionar traceback de cada um após fixar 5 bloqueadores críticos

---

## 📋 PLANO MÍNIMO DE CORREÇÃO

### FASE 1: Desbloqueadores (sem risco)

| # | Bloqueador | Alteração | Arquivo | Tempo | Risco |
|---|-----------|-----------|---------|-------|-------|
| 1 | Fixture firebase_sync | Import conftest_fb | conftest.py | 5 min | BAIXO |
| 2 | Isolamento tenant | Remover fallback | agenda_service.py + outros | 1-2 h | ALTO |
| 3 | Contrato mensagem | Atualizar teste OU template | test_p08_2_*.py | 30 min | MÉDIO |
| 4 | E2E WhatsApp | Propagar tenant_id | event_handler.py | 1 h | ALTO |
| 5 | Timeout sessão | Ativar/verificar scheduler | conftest.py | 30 min | MÉDIO |

### Ordem Recomendada
```
1. Import conftest_fb (desbloqueará 18 ERROR imediatamente)
2. Isolamento tenant (segurança crítica)
3. Contrato mensagem (visível ao cliente)
4. E2E WhatsApp (fluxo crítico)
5. Timeout sessão (estado residual)
6. Outros 20 FAILs (caso-a-caso)
```

### Critérios Objetivos para Liberar Deploy

- [ ] 368 testes executados (não ERROR)
- [ ] **368 testes PASS (100%)**
- [ ] Teste de isolamento tenant PASS
- [ ] Teste E2E WhatsApp PASS
- [ ] Teste de timeout PASS
- [ ] Nenhum evento em `Clientes/None` ou `Clientes/user_id`
- [ ] Template mensagem confirmação validado com cliente

---

## ✅ TRIAGEM CONCLUÍDA

Próxima etapa: Aguardando autorização para começar FASE 1 de correções

