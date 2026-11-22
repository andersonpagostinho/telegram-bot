# 📋 PLANO — SEGUNDA AUDITORIA FORENSE AMANHÃ (2026-11-20)

**Preparado por:** Claude Haiku  
**Data:** 2026-11-19 (Noite)  
**Status:** ⏳ AGUARDANDO EXECUÇÃO AMANHÃ  

---

## 🎯 OBJETIVO

Executar investigação READ-ONLY profunda de NeoEve com 10 ETAPAS, gerando documento final:
📄 `SEGUNDA_AUDITORIA_FORENSE_NEOEVE_2026_11_19.md`

**Regra de Ouro:** Nenhuma modificação de código. Apenas READ-ONLY.

---

## 📝 CHECKLIST DAS 10 ETAPAS

### ✅ ETAPA 1: REPRODUZIR 5 BUGS
**Arquivos a revisar:**
- `services/agenda_lock_service.py` (Bug #1: Race condition/lock órfão)
- `utils/contexto_temporario.py` (Bug #2: Sobrescrita com vazio)
- `services/event_service_async.py` (Bug #3: Fallback multi-tenant)
- `services/` + `router/` (Bug #4: 34 × `except:` genéricos)
- `utils/contexto_temporario.py:170-251` (Bug #5: Draft limpeza)

**Para cada bug, documentar:**
```
[ ] Arquivo exato
[ ] Função exata
[ ] Linhas exatas
[ ] Código responsável
[ ] Caminho de execução
[ ] Cenário reprodução
[ ] Impacto real
[ ] Teste existente? (sim/não)
[ ] Classificação (P0/P1/P2)
[ ] Status: Confirmado / Parcialmente Mitigado / Não Reproduzido
```

---

### ✅ ETAPA 2: ISOLAMENTO MULTI-TENANT
**Prioridade:** MÁXIMA

**Montar matriz:**
```
| Arquivo | Função | Recebe tenant_id? | Valida? | Fallback? | Risco |
```

**Verificar TODOS os pontos:**
- [ ] Leitura Firestore (queries)
- [ ] Gravação Firestore (creates/updates)
- [ ] Fallback para user_id
- [ ] Resolução de tenant por telefone
- [ ] Serviços com tenant_id opcional
- [ ] Jobs e schedulers
- [ ] Notificações
- [ ] Histórico
- [ ] Sessões
- [ ] Clientes
- [ ] Eventos
- [ ] Profissionais
- [ ] Serviços
- [ ] Billing

**Responder:** Algum tenant consegue acessar dados de outro?

---

### ✅ ETAPA 3: IDEMPOTÊNCIA DE WEBHOOKS
**Verificar:**
- [ ] message_id implementado?
- [ ] Deduplicação?
- [ ] Persistência do identificador?
- [ ] Retries?
- [ ] Mensagens fora de ordem?

**Cenários a simular (conceitualmente):**
1. Uma mensagem chega 1x
2. Mesma mensagem chega 2x
3. Mesma mensagem chega simultaneamente em 2 workers
4. Primeira processação cria evento, falha antes de responder
5. Provedor reenvia

**Risco:** Agendamento duplicado?

---

### ✅ ETAPA 4: CONCORRÊNCIA REAL AGENDA
**Arquivo crítico:** `services/agenda_lock_service.py`

**Verificar:**
- [ ] @firestore.transactional implementado?
- [ ] Aquisição de locks atômica?
- [ ] TTL correto?
- [ ] Limpeza de locks órfãos?
- [ ] Propriedade do lock?
- [ ] Revalidação de conflitos?
- [ ] Criação de evento protegida?
- [ ] Recuperação após crash?

**Procurar por:** Testes com `asyncio.gather`, threads, processos, múltiplos workers

**Se não existir:** Declarar explicitamente

**Cenário:** 2 clientes tentam reservar MESMO profissional, MESMO horário
- Resultado esperado: Apenas 1 confirmada

---

### ✅ ETAPA 5: GUARD DE BILLING
**Arquivos a auditoria:**
- [ ] `main.py`
- [ ] `router/principal_router.py` (linhas 6894+)
- [ ] `services/billing_state_machines.py` (AcessoState.SUSPENSO)
- [ ] `services/billing_domain_service.py`
- [ ] `utils/custos_gpt.py`

**Testar:** Cliente com SUSPENSO=True consegue:
- [ ] Chamar GPT?
- [ ] Consultar agenda?
- [ ] Criar agendamento?
- [ ] Alterar agendamento?
- [ ] Cancelar agendamento?
- [ ] Consumir recursos pagos?

**Procurar por:** Guard em handler/middleware ANTES de operações

**Responder:** Qual é a posição correta do guard?

---

### ✅ ETAPA 6: CREDENCIAIS E SEGURANÇA
**Verificar:**
- [ ] `firebase_credentials.json` localmente?
- [ ] Cópias de credenciais?
- [ ] Rastreadas pelo Git?
- [ ] Histórico de commits?
- [ ] Variáveis de ambiente?
- [ ] Secrets do Render?
- [ ] Privilégios service account?
- [ ] Assinatura webhook?
- [ ] Autorização por ator?
- [ ] Dados pessoais nos logs?

**Diferenciar:**
1. Arquivo existe localmente
2. Arquivo rastreado no Git
3. Credencial realmente válida
4. Credencial publicada no histórico
5. Credencial já revogada

**Recomendação:** Se credenciais reais expostas → Rotação IMEDIATA

---

### ✅ ETAPA 7: CONTEXTO E SESSÕES
**Arquivo crítico:** `utils/contexto_temporario.py`

**Verificar:**
- [ ] Campos persistidos (quais?)
- [ ] Timeout efetivo (60min? 24h? outro?)
- [ ] Renovação de sessão?
- [ ] Continuidade?
- [ ] Cache de intenção?
- [ ] Invalidadores (quantos? quais?)
- [ ] Merge de contexto defensivo?
- [ ] Campos vazios protegidos?
- [ ] DELETE_FIELD implementado?
- [ ] Limpeza após sucesso?

**DIVERGÊNCIA ENCONTRADA:** Registros antigos dizem 60min, auditoria anterior achou 24h
- **Resolver:** Qual é o timeout REAL no código atual?

**Não confundir:** Continuidade ≠ Memória de preferências

---

### ✅ ETAPA 8: RISCOS ADICIONAIS
**Verificar ESPECIFICAMENTE:**
- [ ] Inconsistência timezone
- [ ] Virada de dia (23:59:59)
- [ ] Concorrência entre profissionais
- [ ] Firestore quota 429
- [ ] Dados pessoais em logs
- [ ] Backup/Restauração
- [ ] Cópias de credenciais
- [ ] Retries implementado?
- [ ] Falhas parciais tratadas?
- [ ] Notificações duplicadas?
- [ ] Sessões concorrentes?
- [ ] Queries sem escopo tenant?

**Para cada:** Indicar evidência + impacto

---

### ✅ ETAPA 9: ESTADO REAL DE PRODUÇÃO
**Verificar:**
- [ ] Branch atual
- [ ] Commit atual
- [ ] Últimos 50 commits
- [ ] Arquivos modificados
- [ ] `main.py` (como está?)
- [ ] Integração WhatsApp (operacional?)
- [ ] Deployment (onde?)
- [ ] CI/CD (qual?)
- [ ] Monitoramento (existe?)
- [ ] Testes reais (quantos? quais?)
- [ ] Testes de segurança (existem?)
- [ ] Testes de carga (existem?)

**Não afirmar:** Clientes reais sem evidências operacionais
**Não confundir:** Testes Firebase real ≠ Clientes reais

---

### ✅ ETAPA 10: PLANO P0 DEFINITIVO
**Montar matriz:**
```
| Ordem | Problema | Arquivos | Correção | Dependências | Esforço | Critério Aceite |
```

**Priorização:**
1. Credenciais expostas
2. Isolamento multi-tenant
3. Autenticação/autorização
4. Idempotência
5. Integridade concorrência
6. Guard acesso
7. Contexto/drafts
8. Recuperação falhas

**Não:** Estimativas genéricas
**Sim:** Decomposição completa
**Verificar:** O que pode rodar em paralelo?

---

## 📊 FORMATO DE ENTREGA

**Documento:** `SEGUNDA_AUDITORIA_FORENSE_NEOEVE_2026_11_19.md`

**Estrutura:**
1. Resumo executivo
2. Bugs comprovados
3. Falsos positivos
4. Vulnerabilidades críticas
5. Isolamento multi-tenant
6. Idempotência
7. Concorrência
8. Billing
9. Credenciais
10. Sessões e contexto
11. Riscos adicionais
12. Estado real de produção
13. Matriz de prioridades
14. Plano de correção
15. Critérios de liberação comercial

**Para cada achado:**
```
Arquivo: ...
Função: ...
Linhas: ...
Evidência: ...
Grau de confiança: Alto/Médio/Baixo
```

---

## 🎯 PERGUNTAS FINAIS (Responder ao fim)

1. ✅ NeoEve está segura para receber clientes pagantes?
2. ✅ Qual é o risco mais grave?
3. ✅ Qual é a primeira correção que precisa ser feita?
4. ✅ Quais correções são bloqueadoras para um piloto?
5. ✅ O que podemos preservar sem refatorar?
6. ✅ Quanto trabalho realmente falta para liberar um piloto comercial?
7. ✅ Quais riscos permanecem mesmo depois das correções P0?

---

## ⚠️ REGRAS OBRIGATÓRIAS

- [ ] NÃO modificar código
- [ ] NÃO inventar resultados
- [ ] NÃO declarar testes aprovados sem executar
- [ ] NÃO considerar ausência de evidência como segurança
- [ ] NÃO remover funcionalidades sem necessidade
- [ ] NÃO propor refatoração ampla sem comprovação
- [ ] ✅ Preservar compatibilidade com dados existentes
- [ ] ✅ Preservar isolamento multi-tenant
- [ ] ✅ TODA conclusão com evidência rastreável

---

## 🚀 COMO EXECUTAR AMANHÃ

**Comando:**
```
Claude, execute a segunda auditoria forense usando este plano.
```

**Ou simplesmente:**
```
Pode começar a auditoria forense agora.
```

---

**STATUS:** 🟢 **PRONTO PARA AMANHÃ**

**Documento criado:** 2026-11-19 23:XX  
**Próxima ação:** Executar quando você acordar

