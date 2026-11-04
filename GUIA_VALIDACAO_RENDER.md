# GUIA — VALIDAÇÃO PÓS-DEPLOY RENDER
## P0 Humanização da Eve

**Commit Esperado**: `e48ce5cc2830ec75c7ecf39c92a1b768eed775eb`  
**Branch**: `main`  
**Data de Deploy**: 2026-11-01  
**Executado por**: Claude Code

---

## PASSO 1: ACESSAR PAINEL DO RENDER

### Ação:
1. Abrir https://dashboard.render.com
2. Fazer login com suas credenciais
3. Selecionar projeto "telegram-bot" (ou nome similar)
4. Ir para aba "Deployments"

---

## PASSO 2: IDENTIFICAR DEPLOY DO COMMIT e48ce5c

### O que procurar:

**Na lista de Deployments**, deve aparecer um deployment com:

```
Commit Hash:      e48ce5cc... (ou e48ce5c)
Branch:           main
Mensagem:         "feat(neoeve): humaniza mensagens conversacionais da Eve"
Data:             2026-11-01 (aproximadamente)
Status:           "Deployed" ou "Live"
```

### Informações a coletar:

| Campo | Valor | Status |
|-------|-------|--------|
| **Commit hash** | `e48ce5cc2830ec75c7ecf39c92a1b768eed775eb` | ☐ Encontrado |
| **Branch** | `main` | ☐ Confirmado |
| **Status do Build** | [PREENCHER] | ☐ Sucesso / ☐ Falha |
| **Status do Deploy** | [PREENCHER] | ☐ Ativo / ☐ Falha |
| **Timestamp de início** | [PREENCHER] | ☐ |
| **Timestamp de conclusão** | [PREENCHER] | ☐ |

---

## PASSO 3: CONSULTAR LOGS DE INICIALIZAÇÃO

### Ação:
1. Clicar no deployment do commit e48ce5c
2. Ir para aba "Logs"
3. Procurar por (em ordem):

### Logs esperados (SUCESSO):

```
▶ Building...
  Running: pip install -r requirements.txt
  ✓ Requirements installed
  
Running: python main.py
✓ Application started
[INFO] Server listening on port 10000
[INFO] Roteador Principal inicializado
[INFO] Webhook WhatsApp ativo
```

### Logs suspeitos (ERRO):

```
❌ ModuleNotFoundError
❌ ImportError
❌ SyntaxError
❌ CRITICAL
❌ RuntimeError
❌ Connection refused (Firestore/GPT)
❌ Failed to install requirements
```

### Checklist:

| Indicador | Status | Observação |
|-----------|--------|-----------|
| Build iniciado | ☐ Sim / ☐ Não | [PREENCHER] |
| Requirements instalados | ☐ Sim / ☐ Não | [PREENCHER] |
| Application started | ☐ Sim / ☐ Não | [PREENCHER] |
| Webhook ativo | ☐ Sim / ☐ Não | [PREENCHER] |
| Nenhum erro crítico | ☐ Sim / ☐ Não | [PREENCHER] |

---

## PASSO 4: VERIFICAR STATUS DO SERVIÇO

### Ação:
1. Ir para aba "Settings" ou "Overview"
2. Procurar por "Service Status"
3. Confirmar:
   - [ ] Service is Live
   - [ ] No ongoing issues
   - [ ] Memory usage < 80%
   - [ ] CPU usage < 80%

---

## PASSO 5: EXECUTAR TESTES DE FUMAÇA

### Pré-requisitos:
- [ ] Acesso ao WhatsApp ou simulador do webhook
- [ ] Ambiente de teste (não usar clientes reais sem autorização)
- [ ] Paciência para 5-10 testes

### Teste 1: Saudação inicial (MSG-001)

**Ação**:
```
Enviar: "Olá" (via webhook ou WhatsApp)
```

**Esperado**:
```
"Voltamos! 😊

Como posso ajudar com seu agendamento?"
```

**NÃO deve conter**:
```
"Reiniciamos a conversa 🔄"
```

**Resultado**:
- [ ] PASS — Mensagem humanizada recebida
- [ ] FAIL — Mensagem antiga ou erro

**Observação**: [PREENCHER]

---

### Teste 2: Apresentação da Eve (MSG-002)

**Ação**:
```
Enviar: "Oi" (primeira mensagem, sem contexto)
```

**Esperado**:
```
"Oi! 👋 Sou a Eve, secretária aqui. Posso ajudar com agendamentos, 
cancelamentos ou informações sobre disponibilidade."
```

**NÃO deve conter**:
```
"Tudo bem. Se precisar, estou por aqui!"
```

**Resultado**:
- [ ] PASS — Eve se apresenta
- [ ] FAIL — Mensagem antiga ou genérica

**Observação**: [PREENCHER]

---

### Teste 3: Coleta de serviço (MSG-003)

**Ação**:
```
Enviar: "Quero agendar um corte"
Responder a "Qual serviço?": qualquer serviço inválido ou vago
```

**Esperado (MSG-003)**:
```
"Qual serviço você gostaria? Posso ajudar com:"
```

**NÃO deve conter**:
```
"Perfeito. Qual serviço você quer agendar?"
```

**Resultado**:
- [ ] PASS — Pergunta humanizada
- [ ] FAIL — Pergunta antiga

**Observação**: [PREENCHER]

---

### Teste 4: Cancelamento (MSG-012 e MSG-013)

**Ação**:
```
Enviar: "Cancelar" (com agendamento pré-existente ou simulado)
Responder "Sim" para confirmar
```

**Esperado (MSG-012)**:
```
"Qual agendamento você quer cancelar?

• [evento1]
• [evento2]"
```

**NÃO deve conter**:
```
"Qual deseja cancelar?

1. [evento1]
2. [evento2]"
```

**Esperado (MSG-013)**:
```
"Pronto, cancelei. Precisar de algo mais, é só chamar!"
```

**NÃO deve conter**:
```
"Tudo bem! Cancelei o agendamento. Posso ajudar em algo mais?"
```

**Resultado**:
- [ ] PASS — Mensagens humanizadas (bullets + despedida amigável)
- [ ] FAIL — Mensagens antigas

**Observação**: [PREENCHER]

---

### Teste 5: Erro de interpretação (MSG-014)

**Ação**:
```
Enviar: "xyz123!@#$" (mensagem incoerente 3 vezes)
```

**Esperado (MSG-014)**:
```
"Não consegui entender. Pode tentar de novo, com mais detalhes?"
```

**NÃO deve conter**:
```
"Desculpe, não entendi. Pode reformular?"
```

**Resultado**:
- [ ] PASS — Mensagem humanizada
- [ ] FAIL — Mensagem antiga

**Observação**: [PREENCHER]

---

### Teste 6: Preservação de MSG-010

**Ação**:
```
Completar agendamento até confirmação final
(Serviço + Profissional + Data + Hora selecionados)
```

**Esperado (MSG-010)**:
```
"Só confirmando 😊

Você quer agendar seu *[SERVICO]* com *[PROF]* para *[DATA]*?

Responda *sim* para confirmar o agendamento."
```

**DEVE conter (confirmação que NÃO foi alterada)**:
```
"Responda *sim* para confirmar o agendamento."
```

**NÃO deve ser alterado para**:
```
"Quer agendar?"
```

**Resultado**:
- [ ] PASS — Mensagem original preservada
- [ ] FAIL — Mensagem alterada (não deveria estar)

**Observação**: [PREENCHER]

---

## RESUMO DOS TESTES

| Teste | MSG | Esperado | Resultado |
|-------|-----|----------|-----------|
| Saudação | MSG-001 | "Voltamos! 😊" | ☐ PASS / ☐ FAIL |
| Apresentação | MSG-002 | "Oi! 👋 Sou a Eve" | ☐ PASS / ☐ FAIL |
| Serviço | MSG-003 | "Qual serviço você gostaria?" | ☐ PASS / ☐ FAIL |
| Cancelamento (pergunta) | MSG-012 | "Qual agendamento...?" + bullets | ☐ PASS / ☐ FAIL |
| Cancelamento (resposta) | MSG-013 | "Pronto, cancelei..." | ☐ PASS / ☐ FAIL |
| Erro | MSG-014 | "Não consegui entender..." | ☐ PASS / ☐ FAIL |
| Preservação | MSG-010 | "Responda *sim*..." | ☐ PASS / ☐ FAIL |

---

## PASSO 6: VALIDAÇÃO GERAL

### Checklist final:

- [ ] Deploy status: Live/Ativo
- [ ] Logs sem erros críticos
- [ ] Teste 1 (MSG-001): PASS
- [ ] Teste 2 (MSG-002): PASS
- [ ] Teste 3 (MSG-003): PASS
- [ ] Teste 4 (MSG-012): PASS
- [ ] Teste 5 (MSG-013): PASS
- [ ] Teste 6 (MSG-014): PASS
- [ ] Teste 7 (MSG-010): PASS
- [ ] Eve responde normalmente
- [ ] Sem timeout de webhook
- [ ] Sem exceções em logs

---

## CONCLUSÃO

### Se todos os testes PASSAREM:

```
✅ PRODUÇÃO VALIDADA

Commit e48ce5cc2830ec75c7ecf39c92a1b768eed775eb 
está efetivamente em produção e funcional.

12 mensagens humanizadas ativas.
MSG-010, MSG-007, MSG-009 preservadas.
Nenhuma regressão detectada.

Status: READY FOR MONITORING
```

### Se qualquer teste FALHAR:

```
❌ PRODUÇÃO NÃO VALIDADA

Teste(s) falhando: [LISTAR]

Ação recomendada:
1. Consultar logs detalhados no Render
2. Se erro crítico: considerar rollback para commit anterior
3. Se erro menor: investigar e corrigir

Status: REQUIRES ATTENTION
```

---

**Documento preparado em**: 2026-11-01  
**Status**: Aguardando preenchimento pelo usuário

