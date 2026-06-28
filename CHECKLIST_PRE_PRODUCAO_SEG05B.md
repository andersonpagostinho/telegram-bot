# CHECKLIST PRÉ-PRODUÇÃO — SEG-05B MEC-03

**Data:** 2026-06-27  
**Status:** Pendente validação final  
**Responsável:** QA/DevOps

---

## 1. TESTES FIRESTORE REAIS (13 TESTES)

**Comando:**
```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
pytest tests/test_seg_05b_mec03_firestore.py -v
```

**Testes esperados (TODOS devem PASS):**

- [ ] `test_pausar_contato_autorizado_salva_firestore` — /pausar salva em Firestore
  - Esperado: `responder_automaticamente=false`
  - Local: `Clientes/{tenant_id}/Governanca/{actor_id}`

- [ ] `test_retomar_contato_autorizado_salva_firestore` — /retomar retorna True
  - Esperado: `responder_automaticamente=true`
  - Confirmação em Firestore

- [ ] `test_pausar_desconhecido_bloqueado` — Desconhecido não consegue pausar
  - Esperado: `sucesso=False`
  - Mensagem de bloqueio recebida

- [ ] `test_isolamento_multitenant_pausado` — Tenant A não afeta B
  - Esperado: Isolamento completo
  - Path separado por tenant_id

- [ ] `test_governanca_padrão_responder_automaticamente_true` — Default True
  - Esperado: Novo contato tem `responder_automaticamente=true`

- [ ] `test_auditoria_registrada_pausar` — Auditoria registra comando
  - Esperado: Campo `auditoria` populado
  - Comando `/pausar` registrado

- [ ] `test_mensagem_bloqueada_antes_gpt` — Bloqueio antes do GPT
  - Esperado: Verificação em `bot.py:149-205`
  - GPT não é chamado

- [ ] `test_multiplos_contatos_isolados` — Estados independentes
  - Esperado: Contato 1 pausado, Contato 2 normal

- [ ] `test_mec02_nao_ativado` — MEC-02 não ativado
  - Esperado: Apenas MEC-03

- [ ] `test_mec04_nao_ativado` — MEC-04 não ativado
  - Esperado: Apenas MEC-03

- [ ] `test_mec05_nao_ativado` — MEC-05 não ativado
  - Esperado: Apenas MEC-03

- [ ] `test_agenda_conflito_nao_alterados` — Agenda intacta
  - Esperado: Sem mudanças em agenda/conflito

- [ ] `test_memoria_temporaria_nao_persiste_responder` — MemoriaTemporaria OK
  - Esperado: `responder_automaticamente` NOT em MemoriaTemporaria

**Resultado:** `___ PASS / 13 ___` 

---

## 2. REGRESSÃO P0 (174 CENÁRIOS)

**Comando:**
```bash
python tests/runner_p0_regressao_completa.py
```

**Cenários por script:**

- [ ] `p0_bateria_real_fluxo_completo_conflito_a_criacao.py` — 7 cenários
  - Esperado: 7/7 PASS

- [ ] `p0_bateria_real_cancelamento_completo.py` — 15 cenários
  - Esperado: 15/15 PASS

- [ ] `p0_real_confirmacao_pendente_completo.py` — 17 cenários
  - Esperado: 17/17 PASS

- [ ] `p0_real_mudanca_contexto_completo.py` — 25 cenários
  - Esperado: 25/25 PASS

- [ ] `p0_real_multi_entidades_completo.py` — 15 cenários
  - Esperado: 15/15 PASS

- [ ] `p0_real_ajuste_incremental_avancado.py` — 20 cenários
  - Esperado: 20/20 PASS

- [ ] `p0_real_notificacoes_e2e.py` — 20 cenários
  - Esperado: 20/20 PASS

- [ ] `p0_real_admin_dono_completo.py` — 25 cenários
  - Esperado: 25/25 PASS

- [ ] `p0_real_profissional_completo.py` — 30 cenários
  - Esperado: 30/30 PASS

**Resultado:** `___ PASS / 174 ___`

---

## 3. REGRESSÃO P1 E2E (3 TESTES)

**Comando:**
```bash
pytest tests/p1_e2e_onboarding_*.py -v
```

**Testes esperados (TODOS devem PASS):**

- [ ] `p1_e2e_onboarding_identidade_real.py`
  - Esperado: 15/15 PASS

- [ ] `p1_e2e_onboarding_individual_real.py`
  - Esperado: 15/15 PASS

- [ ] `p1_e2e_onboarding_operacional_completo_real.py`
  - Esperado: 15/15 PASS

**Resultado:** `___ PASS / 3 ___`

---

## 4. TESTE MANUAL: /PAUSAR E /RETOMAR

**Plataforma:** Telegram ou WhatsApp com bot em desenvolvimento

### Passo 1: Enviar `/pausar`

```
Usuário: /pausar
Bot responde: "⏸️ NeoEve pausada para você. Use /retomar para voltar."
```

**Validação:**
- [ ] Resposta recebida
- [ ] Mensagem contém "pausada"
- [ ] Mensagem contém "/retomar"

### Passo 2: Enviar mensagem comum

```
Usuário: Oi, tudo bem?
Bot responde: "⏸️ Você pausou as respostas automáticas..."
```

**Validação:**
- [ ] Mensagem bloqueada (sem resposta do GPT)
- [ ] Mensagem contém "pausou as respostas"
- [ ] SEM resposta conversacional do bot

**LOG esperado:**
```
[MEC-03-BLOQUEIO-ATIVO] user_id=... | motivo=responder_automaticamente=False e mensagem fora de Whitelist
```

### Passo 3: Enviar confirmação `/sim`

```
Usuário: /sim
Bot responde: [normal - permitido pela whitelist A-01]
```

**Validação:**
- [ ] Mensagem processada (A-01 está em whitelist)
- [ ] Resposta contextual recebida
- [ ] Fluxo continua normalmente

**LOG esperado:**
```
[MEC-03-PERMITIDO-WHITELIST] user_id=... | mensagem permitida
```

### Passo 4: Enviar `/retomar`

```
Usuário: /retomar
Bot responde: "▶️ NeoEve retomada para você. Estou aqui para ajudar!"
```

**Validação:**
- [ ] Resposta recebida
- [ ] Mensagem contém "retomada"
- [ ] Fluxo voltou ao normal

**LOG esperado:**
```
[MEC-03] /retomar executado: user_id=... | sucesso=True
```

### Passo 5: Enviar mensagem comum

```
Usuário: Como você funciona?
Bot responde: [resposta normal do GPT]
```

**Validação:**
- [ ] Resposta do GPT recebida
- [ ] Fluxo normalizado
- [ ] Sem bloqueios

---

## 5. TESTE MULTI-TENANT

**Cenário:** Dois tenants (A e B) com mesmo contato

### Passo 1: Pausar em Tenant A

```
1. Fazer login em Tenant A com contato X
2. Enviar: /pausar
3. Verificar em Firestore:
   Clientes/tenant_a/Governanca/{actor_id}
   - responder_automaticamente: false [esperado]
```

**Validação:**
- [ ] Documento criado/atualizado
- [ ] Campo `responder_automaticamente=false`

### Passo 2: Verificar Tenant B (mesmo contato X)

```
1. Fazer login em Tenant B com contato X
2. Enviar mensagem qualquer
3. Esperar resposta normal
```

**Validação:**
- [ ] Contato X em Tenant B responde normalmente
- [ ] Verificar em Firestore:
  - `Clientes/tenant_a/Governanca/{actor_id}.responder_automaticamente` = false
  - `Clientes/tenant_b/Governanca/{actor_id}.responder_automaticamente` = true (ou não existe)

**Resultado:** Isolamento completo ✓

---

## 6. PERSISTÊNCIA E ARQUITETURA

### Verificação 1: Reinício Preserva responder_automaticamente=false

**Propósito:** Validar que a governança é persistida em Firestore (não é apenas sessão)

**Procedimento:**

1. Enviar `/pausar` como contato A-06
   ```
   Esperado: responder_automaticamente=false salvo em Firestore
   ```

2. Verificar em Firestore:
   ```
   Clientes/{tenant_id}/Governanca/{actor_id}
   responder_automaticamente: false ✓
   ```

3. **Reiniciar a aplicação/bot**
   ```
   Esperado: Aplicação reinicia, contexto de sessão é perdido
   Mas: Firestore PRESERVA responder_automaticamente=false
   ```

4. Enviar mensagem com mesmo contato APÓS reinício
   ```
   Usuário: "Oi"
   Bot responde: "⏸️ Você pausou as respostas automáticas..."
   ```

**Validações:**

- [ ] /pausar salva em Firestore com `responder_automaticamente=false`
- [ ] Reinício da aplicação ocorre sem erro
- [ ] Após reinício, governança continua carregada do Firestore
- [ ] Contato pausado CONTINUA pausado após reinício (não é sessão)
- [ ] Bloqueio funciona MESMO APÓS reinício

**Objetivo:** Confirmar que governança é **persistente** (Firestore), não **efêmera** (sessão)

---

### Verificação 2: Contato Pausado Continua Podendo Enviar (Sem Processamento)

**Propósito:** Validar que bloqueio é de **RESPOSTA**, não de **RECEBIMENTO**

**Procedimento:**

1. Contato A-06 envia `/pausar`
   ```
   Esperado: responder_automaticamente=false
   ```

2. Contato envia série de mensagens
   ```
   Mensagem 1: "Olá"
   Mensagem 2: "Como você funciona?"
   Mensagem 3: "Me ajuda com agendamento"
   ```

3. **Para CADA mensagem, validar:**
   - Mensagem foi **recebida** pelo bot (não rejeitada na camada de input)
   - Mensagem foi **bloqueada** (antes do processamento)
   - Nenhuma ação foi tomada:
     - ❌ GPT não foi chamado
     - ❌ Contexto não foi atualizado
     - ❌ Agenda não foi consultada
     - ❌ Notificação não foi criada
     - ❌ Resposta não foi enviada

4. Verificar logs:
   ```
   [MEC-03-BLOQUEIO-ATIVO] user_id=... | motivo=...
   [Nenhum outro log de processamento deve aparecer]
   ```

5. Verificar Firestore:
   ```
   ✓ MemoriaTemporaria/{user_id} — NÃO foi atualizada
   ✓ Clientes/{tenant_id}/Eventos — nenhum evento criado
   ✓ Clientes/{tenant_id}/Governanca — apenas responder_automaticamente alterado
   ```

**Validações:**

- [ ] Mensagens são RECEBIDAS (sem erro HTTP/conexão)
- [ ] Mensagens são BLOQUEADAS antes do GPT
- [ ] MemoriaTemporaria **NÃO** é atualizada
- [ ] Agenda **NÃO** é consultada
- [ ] Notificações **NÃO** são criadas
- [ ] Eventos **NÃO** são salvos
- [ ] Log mostra bloqueio (sem processamento posterior)
- [ ] Apenas governança é persistida (responder_automaticamente)

**Objetivo:** Confirmar que bloqueio é **no ponto de entrada** (bot.py:149-205), **ANTES** de qualquer processamento

---

### Resumo da Arquitetura Validada

```
GOVERNANÇA (Persistente):
  Clientes/{tenant_id}/Governanca/{actor_id}.responder_automaticamente
  └─ Persiste em Firestore
  └─ Sobrevive a reinícios
  └─ Isolado por tenant_id

SESSÃO (Efêmera):
  context.user_data / MemoriaTemporaria
  └─ Perdida em reinício
  └─ Não recebe responder_automaticamente
  └─ Não afeta bloqueio

BLOQUEIO:
  handlers/bot.py:149-205
  └─ ANTES de qualquer processamento
  └─ ANTES do GPT
  └─ ANTES de atualizar MemoriaTemporaria
  └─ ANTES de criar eventos/notificações
```

---

## 7. LOGS E EVIDÊNCIAS

**Arquivo de log:** `bot.log` ou stdout

**Padrões esperados:**

### Quando /pausar é executado
```
[MEC-03] /pausar executado: user_id=... | sucesso=True
```
- [ ] Log encontrado
- [ ] Contém `[MEC-03]`
- [ ] Contém `/pausar`
- [ ] Contém `sucesso=True`

### Quando /retomar é executado
```
[MEC-03] /retomar executado: user_id=... | sucesso=True
```
- [ ] Log encontrado
- [ ] Contém `[MEC-03]`
- [ ] Contém `/retomar`
- [ ] Contém `sucesso=True`

### Quando governança é carregada
```
[MEC-03-BLOQUEIO] user_id=... | responder_automaticamente=False
```
- [ ] Log encontrado durante teste manual

### Quando mensagem é bloqueada
```
[MEC-03-BLOQUEIO-ATIVO] user_id=... | motivo=responder_automaticamente=False e mensagem fora de Whitelist Classe A
```
- [ ] Log encontrado quando mensagem é rejeitada

### Quando mensagem é permitida
```
[MEC-03-PERMITIDO-WHITELIST] user_id=... | mensagem permitida
```
- [ ] Log encontrado para mensagens em whitelist

---

## RESULTADO FINAL

### Resumo de Validações

| Item | Status | Evidência |
|------|--------|-----------|
| Testes Firestore (13) | [ ] OK | __ PASS / 13 |
| Regressão P0 (174) | [ ] OK | __ PASS / 174 |
| Regressão P1 (3) | [ ] OK | __ PASS / 3 |
| Teste /pausar | [ ] OK | Resposta recebida |
| Teste /retomar | [ ] OK | Resposta recebida |
| Teste bloqueio | [ ] OK | Mensagem bloqueada |
| Teste whitelist | [ ] OK | A-01 permitido |
| Teste multi-tenant | [ ] OK | Isolamento validado |
| Persistência (reinício) | [ ] OK | Firestore preserva estado |
| Bloqueio sem processamento | [ ] OK | Nenhuma ação desencadeada |
| Logs MEC-03 | [ ] OK | Padrões encontrados |

### Aprovação Final

- [ ] TODOS os itens acima foram validados
- [ ] Nenhuma regressão detectada
- [ ] Escopo mantido (MEC-03 somente)
- [ ] Regra de Ouro respeitada
- [ ] **APROVADO PARA PRODUÇÃO**

---

## Assinatura

**Validador:** ________________________  
**Data:** ________________________  
**Resultado:** ✓ APROVADO / ✗ REJEITADO

---

## Instruções Finais

1. Executar todos os testes acima
2. Marcar [ ] após cada validação
3. Salvar este checklist preenchido
4. Fazer commit com evidências
5. Abrir PR para produção com checklist anexado

**Status:** PRONTO PARA VALIDAÇÃO
