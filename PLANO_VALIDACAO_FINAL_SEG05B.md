# PLANO DE VALIDAÇÃO FINAL COMPLETA — SEG-05B MEC-03

**Data:** 2026-06-27  
**Status:** Fase de Validação Final (NÃO produção ainda)  
**Gate:** Todos PASS = Liberar PR | Qualquer FAIL = Bloquear Produção

---

## 📋 Ordem de Execução Obrigatória

### ETAPA 1: Testes Firestore (13 testes)

**Responsável:** QA / Desenvolvedor

**Comando:**
```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
pytest tests/test_seg_05b_mec03_firestore.py -v --tb=short
```

**Timeout:** 5 minutos

**Resultado Esperado:**
```
13 PASSED
0 FAILED
0 ERRORS
```

**Se FALHAR:** 🛑 **BLOQUEIO PRODUÇÃO**
- [ ] Investigar causa do teste
- [ ] Não prosseguir para próxima etapa
- [ ] Registrar erro em documento

**Se PASSAR:** ✅ Continuar para ETAPA 2
- [ ] Registrar resultado: `13/13 PASS`
- [ ] Timestamp: ___________
- [ ] Responsável: ___________

---

### ETAPA 2: Regressão P0 (174 cenários)

**Responsável:** QA / Desenvolvedor

**Comando:**
```bash
python tests/runner_p0_regressao_completa.py
```

**Timeout:** 30 minutos

**Resultado Esperado:**
```
P0 Regressão: 174/174 PASS
0 FAILED
0 ERRORS
```

**Cenários críticos a monitorar:**
- [ ] p0_bateria_real_fluxo_completo_conflito_a_criacao (7)
- [ ] p0_bateria_real_cancelamento_completo (15)
- [ ] p0_real_confirmacao_pendente_completo (17)
- [ ] p0_real_mudanca_contexto_completo (25)
- [ ] p0_real_multi_entidades_completo (15)
- [ ] p0_real_ajuste_incremental_avancado (20)
- [ ] p0_real_notificacoes_e2e (20)
- [ ] p0_real_admin_dono_completo (25)
- [ ] p0_real_profissional_completo (30)

**Se FALHAR:** 🛑 **BLOQUEIO PRODUÇÃO**
- [ ] Qual cenário falhou? ___________
- [ ] Investigar regressão
- [ ] Não prosseguir para próxima etapa
- [ ] Registrar erro em documento

**Se PASSAR:** ✅ Continuar para ETAPA 3
- [ ] Registrar resultado: `174/174 PASS`
- [ ] Timestamp: ___________
- [ ] Responsável: ___________

---

### ETAPA 3: Regressão P1 E2E (3 testes)

**Responsável:** QA / Desenvolvedor

**Comando:**
```bash
pytest tests/p1_e2e_onboarding_identidade_real.py \
        tests/p1_e2e_onboarding_individual_real.py \
        tests/p1_e2e_onboarding_operacional_completo_real.py -v
```

**Timeout:** 15 minutos

**Resultado Esperado:**
```
p1_e2e_onboarding_identidade_real.py — PASSED
p1_e2e_onboarding_individual_real.py — PASSED
p1_e2e_onboarding_operacional_completo_real.py — PASSED

3 PASSED
0 FAILED
0 ERRORS
```

**Se FALHAR:** 🛑 **BLOQUEIO PRODUÇÃO**
- [ ] Qual teste falhou? ___________
- [ ] Investigar regressão
- [ ] Não prosseguir para próxima etapa
- [ ] Registrar erro em documento

**Se PASSAR:** ✅ Continuar para ETAPA 4
- [ ] Registrar resultado: `3/3 PASS`
- [ ] Timestamp: ___________
- [ ] Responsável: ___________

---

### ETAPA 4: Teste Manual /pausar → /retomar

**Responsável:** QA (manual)

**Plataforma:** Telegram ou WhatsApp em desenvolvimento

**Duração:** ~10 minutos

**Procedimento:**

#### Passo 1: Enviar `/pausar`

```
Ação: Contato A-06 envia "/pausar"
Esperado: Bot responde "⏸️ NeoEve pausada para você"
Validação: [ ] Resposta recebida
```

**Log esperado:**
```
[MEC-03] /pausar executado: user_id=... | sucesso=True
```

#### Passo 2: Enviar mensagem comum

```
Ação: Mesmo contato envia "Oi, tudo bem?"
Esperado: Bot responde "⏸️ Você pausou as respostas automáticas"
Validação: [ ] Bloqueio funcionou
           [ ] SEM resposta do GPT
```

**Log esperado:**
```
[MEC-03-BLOQUEIO-ATIVO] user_id=... | motivo=responder_automaticamente=False...
```

#### Passo 3: Enviar confirmação `/sim`

```
Ação: Mesmo contato envia "/sim"
Esperado: Processado normalmente (A-01 está em whitelist)
Validação: [ ] Mensagem permitida
           [ ] Fluxo continua
```

**Log esperado:**
```
[MEC-03-PERMITIDO-WHITELIST] user_id=... | mensagem permitida
```

#### Passo 4: Enviar `/retomar`

```
Ação: Contato envia "/retomar"
Esperado: Bot responde "▶️ NeoEve retomada para você"
Validação: [ ] Resposta recebida
```

**Log esperado:**
```
[MEC-03] /retomar executado: user_id=... | sucesso=True
```

#### Passo 5: Enviar mensagem comum

```
Ação: Contato envia "Como você funciona?"
Esperado: Resposta normal do GPT
Validação: [ ] Fluxo normalizado
           [ ] Resposta conversacional recebida
```

**Se QUALQUER PASSO FALHAR:** 🛑 **BLOQUEIO PRODUÇÃO**
- [ ] Qual passo falhou? ___________
- [ ] Descrição do erro: ___________
- [ ] Screenshot anexado: [ ] Sim [ ] Não
- [ ] Não prosseguir para próxima etapa

**Se TODOS OS PASSOS PASSAREM:** ✅ Continuar para ETAPA 5
- [ ] Registrar resultado: `5/5 passos PASS`
- [ ] Screenshots dos logs: [ ] Anexados
- [ ] Timestamp: ___________
- [ ] Responsável: ___________

---

### ETAPA 5: Teste Multi-tenant

**Responsável:** QA / Desenvolvedor

**Duração:** ~10 minutos

**Setup:** Dois tenants (A e B) com mesmo contato X

#### Passo 1: Pausar em Tenant A

```
Ação: Login em Tenant A com contato X
      Enviar "/pausar"

Verificação Firestore:
  Clientes/tenant_a/Governanca/{actor_id}
  └─ responder_automaticamente: false

Validação: [ ] Campo alterado em Firestore
```

#### Passo 2: Verificar Tenant B

```
Ação: Login em Tenant B com mesmo contato X
      Enviar mensagem qualquer

Esperado: Contato responde normalmente (não pausado)

Verificação Firestore:
  Clientes/tenant_a/Governanca/{actor_id}
  └─ responder_automaticamente: false ✓
  
  Clientes/tenant_b/Governanca/{actor_id}
  └─ responder_automaticamente: true (ou não existe) ✓

Validação: [ ] Tenant A pausado, Tenant B normal
           [ ] Isolamento completo
```

**Se FALHAR:** 🛑 **BLOQUEIO PRODUÇÃO**
- [ ] Qual passo falhou? ___________
- [ ] Tenant A ou B? ___________
- [ ] Firestore validado? [ ] Sim [ ] Não
- [ ] Não prosseguir para próxima etapa

**Se PASSAR:** ✅ Continuar para ETAPA 6
- [ ] Registrar resultado: `Multi-tenant OK`
- [ ] Firestore screenshots: [ ] Anexadas
- [ ] Timestamp: ___________
- [ ] Responsável: ___________

---

### ETAPA 6: Validar Persistência Pós-Restart

**Responsável:** QA / DevOps

**Duração:** ~15 minutos

#### Passo 1: Preparar estado pausado

```
Ação: Contato A-06 envia "/pausar"
Aguardar: Confirmação em Firestore
  Clientes/{tenant_id}/Governanca/{actor_id}
  └─ responder_automaticamente: false

Validação: [ ] Firestore atualizado
```

#### Passo 2: Reiniciar aplicação

```
Ação: Parar o bot completamente
      Aguardar 5+ segundos
      Iniciar o bot novamente

Objetivo: Perder toda a sessão (context.user_data)
          Mas Firestore deve preservar governança
```

#### Passo 3: Validar após reinício

```
Ação: Mesmo contato envia mensagem "Oi"
Esperado: Bot carrega governança do Firestore
          Bloqueio funciona como antes

Resposta esperada:
"⏸️ Você pausou as respostas automáticas..."

Log esperado:
[MEC-03-BLOQUEIO] user_id=... | responder_automaticamente=False
```

**Validação Firestore:**
```
Clientes/{tenant_id}/Governanca/{actor_id}
├─ responder_automaticamente: false ✓
├─ atualizado_em: [timestamp anterior ao restart] ✓
├─ auditoria: [..., {comando: "/pausar"}] ✓
└─ _tenant_id_guard: {tenant_id} ✓
```

**Se FALHAR:** 🛑 **BLOQUEIO PRODUÇÃO**
- [ ] Contato desbloqueado após restart? (CRÍTICO!)
- [ ] Firestore foi carregado? [ ] Sim [ ] Não
- [ ] Logs mostram carregamento? [ ] Sim [ ] Não
- [ ] Não liberar para produção

**Se PASSAR:** ✅ Continuar para ETAPA 7
- [ ] Registrar resultado: `Persistência VALIDADA`
- [ ] Firestore screenshots: [ ] Anexadas
- [ ] Logs screenshot: [ ] Anexado
- [ ] Timestamp: ___________
- [ ] Responsável: ___________

---

### ETAPA 7: Validar Zero Side-Effects em Contato Pausado

**Responsável:** QA / Desenvolvedor

**Duração:** ~15 minutos

#### Passo 1: Preparar estado pausado

```
Ação: Contato pausado com responder_automaticamente=false
Verificar: MemoriaTemporaria está limpa
```

#### Passo 2: Enviar série de mensagens

```
Mensagem 1: "Oi"
Mensagem 2: "Como você funciona?"
Mensagem 3: "Agende corte de cabelo para amanhã"
Mensagem 4: "Quais profissionais estão livres?"

Para CADA mensagem, validar:
```

#### Para Mensagem 1: "Oi"

```
Resposta: "⏸️ Você pausou as respostas..."

Validação:
[ ] Mensagem foi RECEBIDA (HTTP 200)
[ ] Resposta é BLOQUEIO (não GPT)
[ ] MemoriaTemporaria/{user_id} — NÃO foi criado/atualizado
[ ] Agenda NÃO foi consultada
[ ] Eventos — nenhum novo
[ ] Notificações — nenhuma nova
[ ] Log: [MEC-03-BLOQUEIO-ATIVO]
[ ] Performance < 500ms

Firestore após: Sem mudanças (exceto Governanca)
```

#### Para Mensagem 2: "Como você funciona?"

```
Mesmas validações acima

Objetivo: Confirmar que mensagem 1 NÃO criou contexto
          Mensagem 2 não usa contexto de 1
          Bloqueio é independente por mensagem
```

#### Para Mensagem 3: "Agende corte..."

```
Mesmas validações acima

ESPECIAL: Validar que agenda NÃO foi consultada
          (mesmo que mensagem mencione agendamento)
```

#### Para Mensagem 4: "Quais profissionais..."

```
Mesmas validações acima

ESPECIAL: Validar que profissionais NÃO foram consultados
          Validar que cache NÃO foi acessado
```

**Se QUALQUER mensagem FALHAR:** 🛑 **BLOQUEIO PRODUÇÃO**
- [ ] Qual mensagem? ___________
- [ ] Qual side-effect? ___________
- [ ] MemoriaTemporaria foi atualizada? (CRÍTICO!)
- [ ] GPT foi chamado? (CRÍTICO!)
- [ ] Eventos foram criados? (CRÍTICO!)

**Se TODOS PASSAREM:** ✅ Continuar para ETAPA 8
- [ ] Registrar resultado: `Zero side-effects VALIDADO`
- [ ] Firestore screenshots: [ ] Anexadas
- [ ] Logs screenshot: [ ] Anexado
- [ ] Performance medida: _____ ms
- [ ] Timestamp: ___________
- [ ] Responsável: ___________

---

### ETAPA 8: Anexar Logs e Evidências

**Responsável:** QA

**Duração:** ~5 minutos

**Checklist de evidências:**

```
[ ] Testes Firestore (13)
    [ ] pytest output (stdout)
    [ ] File: test_firestore_output.log

[ ] Regressão P0 (174)
    [ ] runner output (stdout)
    [ ] File: p0_regressao_output.log

[ ] Regressão P1 (3)
    [ ] pytest output (stdout)
    [ ] File: p1_regressao_output.log

[ ] Teste Manual /pausar|/retomar
    [ ] Screenshots das respostas
    [ ] File: screenshots_manual_test/

[ ] Teste Multi-tenant
    [ ] Firestore screenshots
    [ ] File: screenshots_multitenant/

[ ] Persistência Pós-Restart
    [ ] Antes do restart (screenshot Firestore)
    [ ] Depois do restart (log de bloqueio)
    [ ] File: evidence_persistence/

[ ] Zero Side-Effects
    [ ] Logs para cada mensagem
    [ ] Firestore screenshots
    [ ] Performance medições
    [ ] File: evidence_sideeffects/

[ ] Arquivo CHECKLIST_PRE_PRODUCAO_SEG05B.md
    [ ] Todos os itens marcados [X]
    [ ] Data preenchida
    [ ] Responsável assinado
```

**Procurar evidências em:**
- Stdout/logs do bot
- Firestore console (screenshots)
- GitHub Actions/CI logs
- Local logs directory

**Se QUALQUER evidência FALTAR:** ⚠️ **INCOMPLETO**
- [ ] Qual evidência falta? ___________
- [ ] Recolher antes de liberar PR

---

## 🚨 GATE DE BLOQUEIO PRODUÇÃO

**CONDIÇÃO OBRIGATÓRIA:** Todos os itens abaixo devem estar ✅ PASS

### Testes Automatizados
- [ ] ✅ Testes Firestore: 13/13 PASS
- [ ] ✅ Regressão P0: 174/174 PASS
- [ ] ✅ Regressão P1: 3/3 PASS

### Testes Manuais
- [ ] ✅ /pausar → resposta bloqueio
- [ ] ✅ /retomar → resposta retomada
- [ ] ✅ Multi-tenant isolado
- [ ] ✅ Persistência pós-restart
- [ ] ✅ Zero side-effects

### Evidências
- [ ] ✅ Logs anexados
- [ ] ✅ Screenshots anexadas
- [ ] ✅ Checklist preenchido
- [ ] ✅ Responsáveis assinados

### Regra de Ouro
- [ ] ✅ Sem suposições (evidência primária)
- [ ] ✅ Escopo mantido (MEC-03 somente)
- [ ] ✅ Sem regressões detectadas

---

## 🛑 BLOQUEADORES CRÍTICOS

**QUALQUER um desses BLOQUEIA PRODUÇÃO IMEDIATAMENTE:**

1. **Testes Automatizados Falhando**
   - ❌ Qualquer teste Firestore FAIL → Bloqueado
   - ❌ Qualquer cenário P0 FAIL → Bloqueado
   - ❌ Qualquer E2E P1 FAIL → Bloqueado

2. **Teste Manual com Resposta do GPT**
   - ❌ Contato pausado recebeu resposta conversacional → Bloqueado
   - ❌ /pausar enviado mas contato desbloqueado → Bloqueado
   - ❌ Bloqueio não funcionou → Bloqueado

3. **Regressão em Outro Fluxo**
   - ❌ Agenda parou de funcionar → Bloqueado
   - ❌ Confirmação quebrou → Bloqueado
   - ❌ Novo erro em fluxo existente → Bloqueado

4. **Persistência Quebrada**
   - ❌ Contato desbloqueado após restart → Bloqueado (CRÍTICO!)
   - ❌ Governança não carregou → Bloqueado (CRÍTICO!)
   - ❌ Isolamento multi-tenant quebrado → Bloqueado (CRÍTICO!)

5. **Side-Effects Detectados**
   - ❌ MemoriaTemporaria atualizada → Bloqueado (CRÍTICO!)
   - ❌ GPT foi chamado → Bloqueado (CRÍTICO!)
   - ❌ Evento foi criado → Bloqueado (CRÍTICO!)
   - ❌ Notificação foi agendada → Bloqueado (CRÍTICO!)

6. **Evidências Incompletas**
   - ❌ Logs não anexados → Bloqueado
   - ❌ Screenshots faltando → Bloqueado
   - ❌ Checklist não preenchido → Bloqueado

---

## ✅ GATE LIBERAÇÃO PR/DEPLOY

**SOMENTE liberar para próxima fase (PR/Deploy) se:**

```
✅ ETAPA 1: Testes Firestore 13/13 PASS
✅ ETAPA 2: Regressão P0 174/174 PASS
✅ ETAPA 3: Regressão P1 3/3 PASS
✅ ETAPA 4: Teste Manual /pausar|/retomar OK
✅ ETAPA 5: Teste Multi-tenant OK
✅ ETAPA 6: Persistência Pós-Restart OK
✅ ETAPA 7: Zero Side-Effects OK
✅ ETAPA 8: Todas as Evidências Anexadas

+ NENHUM bloqueador crítico

= ✅ LIBERADO PARA PR E DEPLOY
```

---

## 📊 Resumo de Status

| Etapa | Status | Pass/Fail | Responsável | Data |
|-------|--------|-----------|-------------|------|
| 1. Testes Firestore | [ ] | __/13 | __________ | __/__/__ |
| 2. Regressão P0 | [ ] | __/174 | __________ | __/__/__ |
| 3. Regressão P1 | [ ] | __/3 | __________ | __/__/__ |
| 4. Teste Manual | [ ] | __/5 | __________ | __/__/__ |
| 5. Multi-tenant | [ ] | OK/FAIL | __________ | __/__/__ |
| 6. Persistência | [ ] | OK/FAIL | __________ | __/__/__ |
| 7. Zero Side-Effects | [ ] | OK/FAIL | __________ | __/__/__ |
| 8. Evidências | [ ] | OK/FAIL | __________ | __/__/__ |

---

## Assinatura Final

**Status Final:** [ ] LIBERADO PR | [ ] BLOQUEADO PRODUÇÃO

**Motivo do Bloqueio (se aplicável):** ___________________________________________

**Assinado por:** ________________________  
**Data:** __/__/__  
**Timestamp:** ________________________

**Revisado por (antes do PR/Deploy):** ________________________  
**Data:** __/__/__

---

**Gate:** 🛑 **Todos PASS = Liberar** | **Qualquer FAIL = Bloquear**

**Status:** Fase de Validação Final Completa
