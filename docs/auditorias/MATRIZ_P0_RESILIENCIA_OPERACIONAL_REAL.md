# 🔐 MATRIZ P0 — RESILIÊNCIA OPERACIONAL REAL

**FASE 4** — Validação de recuperação da NeoEve em cenários de falha operacional.

**Data de Início:** 2026-06-19  
**Status:** INICIANDO  
**Critério Aprovação:** 13/13 testes passando em 3 execuções consecutivas

---

## 🎯 Objetivo

Validar que o sistema NeoEve recupera-se de forma segura e confiável quando ocorrem:
- Restarts de processo
- Timeouts e falhas de rede
- Duplicação de mensagens/updates
- Indisponibilidade temporária de serviços
- Falhas no meio de operações críticas

**Diferencial FASE 4:** Testa RESILIÊNCIA com Firestore REAL (não mock).

---

## 📊 Matriz de Testes

### RO-01 — Restart com confirmação pendente

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Criar draft aguardando confirmação<br/>2. Simular reload total lendo Firestore<br/>3. Usuário confirma |
| **Esperado** | - Cria 1 evento confirmado<br/>- Limpa contexto "aguardando_confirmacao" |
| **Validação** | Draft + evento confirmado no Firestore<br/>Contexto sem duplicação de estado |
| **Risco** | Contexto perdido = fluxo travado |
| **Tipo Falha** | Restart/Perda contexto |

---

### RO-02 — Restart após sugestão de horário

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Conflito detectado<br/>2. Sistema oferece sugestões de horário<br/>3. Restart durante sugestão<br/>4. Cliente confirma sugestão |
| **Esperado** | - Evento criado no horário SUGERIDO<br/>- Não no horário original conflitado |
| **Validação** | Firestore: evento com hora_inicio = horário sugerido |
| **Risco** | Evento criado no slot errado = agenda inconsistente |
| **Tipo Falha** | Restart entre sugestão e confirmação |

---

### RO-03 — Restart após salvar contexto e antes da resposta

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Salvar contexto completo<br/>2. Não enviar resposta (falha)<br/>3. Novo processamento |
| **Esperado** | - Sistema continua com estado correto<br/>- Não duplica evento |
| **Validação** | Contexto intacto + 1 evento criado (idempotência) |
| **Risco** | Duplicação de evento = overbooking |
| **Tipo Falha** | Falha entre salvar contexto e enviar resposta |

---

### RO-04 — Restart durante criação de evento

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Criar lock de proteção<br/>2. Falha DEPOIS lock, ANTES/DEPOIS evento<br/>3. Verificar estado |
| **Esperado** | - Sem lock órfão permanente<br/>- OU documentar bug e recuperação |
| **Validação** | Lock não bloqueia agenda indefinidamente |
| **Risco** | 🔴 P0: Lock órfão = slot inacessível para sempre |
| **Tipo Falha** | Falha crítica durante lock → evento |

---

### RO-05 — Lock órfão expira ou é recuperável

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. AgendaLock criado SEM evento associado<br/>2. Tentar agendar mesmo horário |
| **Esperado** | - Sistema recupera de lock expirado (>24h)<br/>- OU registra bloqueio técnico |
| **Validação** | Novo evento criado OU erro registrado |
| **Risco** | 🔴 P0: Lock indefinido = indisponibilidade permanente |
| **Tipo Falha** | Lock orphan sem limpeza automática |

---

### RO-06 — Webhook retry após evento criado

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Criar evento com confirmação<br/>2. Reprocessar MESMA confirmação (webhook duplicado) |
| **Esperado** | - Retorna sem criar novo evento<br/>- Idempotência garantida |
| **Validação** | 1 evento, 1 notificação (não 2) |
| **Risco** | 🔴 P0: Duplicação = overbooking |
| **Tipo Falha** | Webhook retry |

---

### RO-07 — Timeout/erro de envio de mensagem após criar evento

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Evento criado (confirmado)<br/>2. Falha no envio da RESPOSTA<br/>3. Retry |
| **Esperado** | - Evento persiste<br/>- Retry NÃO cria segundo evento |
| **Validação** | Firestore: 1 evento<br/>Logs: erro de envio isolado |
| **Risco** | 🔴 P0: Duplicação de evento |
| **Tipo Falha** | Falha de comunicação pós-criação |

---

### RO-08 — Scheduler reiniciado não duplica notificações

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Criar evento com notificações<br/>2. Scheduler executa 2 vezes (após restart) |
| **Esperado** | - 1 notificação por destinatário/tipo/evento<br/>- Não duplica |
| **Validação** | `notificacoes.enviada = True` apenas uma vez |
| **Risco** | 🟠 P1: Usuário recebe múltiplas notificações |
| **Tipo Falha** | Scheduler duplicado |

---

### RO-09 — Notificação atrasada expira

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Criar notificação antiga (>24h no passado)<br/>2. Scheduler executa limpeza |
| **Esperado** | - Não dispara mensagem vencida<br/>- Remove de fila |
| **Validação** | Notificação não entra em queue de envio |
| **Risco** | 🟠 P1: Notificação tardia (fora do contexto) |
| **Tipo Falha** | Notificação obsoleta |

---

### RO-10 — Firestore indisponível temporariamente

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Simular exceção Firestore em leitura/escrita<br/>2. Tentar criar evento |
| **Esperado** | - Falha segura<br/>- Nenhum evento PARCIAL criado |
| **Validação** | `evento.confirmado != True` ou não existe em Firestore |
| **Risco** | 🔴 P0: Evento parcial = dados corrompidos |
| **Tipo Falha** | Indisponibilidade de Firestore |

---

### RO-11 — GPT timeout durante interpretação

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. GPT timeout antes de criar draft<br/>2. Tentar reprocessar |
| **Esperado** | - Não cria evento<br/>- Retorna erro ao usuário |
| **Validação** | Sem evento em Firestore<br/>Mensagem de erro enviada |
| **Risco** | 🔴 P0: Evento criado sem confirmação |
| **Tipo Falha** | Timeout de IA |

---

### RO-12 — Telegram/WhatsApp envia update duplicado com mesmo ID

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Mesmo `update_id` chega 2 vezes<br/>2. Processar confirmação |
| **Esperado** | - Evita reprocessamento crítico<br/>- Se duplica resposta: P1<br/>- Se duplica evento: 🔴 P0 |
| **Validação** | 1 evento criado (não 2) |
| **Risco** | 🔴 P0: Evento duplicado = overbooking |
| **Tipo Falha** | Update duplicado de messaging |

---

### RO-13 — Matriz de Notificações por Evento

| Aspecto | Detalhe |
|---------|---------|
| **Cenário** | 1. Cliente agenda corte com Bruna amanhã 15h<br/>2. Evento criado com confirmado=True<br/>3. Validar notificações para: cliente, dono, profissional |
| **Esperado** | - Cliente recebe notificação<br/>- Dono recebe notificação<br/>- Profissional responsável recebe notificação<br/>- Conteúdo completo (evento_id, cliente, serviço, prof, data, hora)<br/>- Cada notificação referencia evento correto |
| **Validação** | 3 notificações criadas<br/>Conteúdo validado<br/>user_ids corretos<br/>evento_id referenciado |
| **Risco** | 🔴 P0: Cliente ou dono não notificado = agendamento invisível |
| **Tipo Falha** | Falha na matriz de notificações |

**Achado Real:** 2026-06-19 — Cliente agendou e dono não recebeu aviso. Profissional também não recebeu. Necessário validar matriz completa de notificações.

---

## 🏗️ Infraestrutura de Testes

### Firestore Setup (REAL, não mock)

```
Clientes/{dono_id}/
  ├─ Eventos/
  │  └─ {evento_id}: { data, hora_inicio, hora_fim, confirmado, ... }
  ├─ AgendaLocks/
  │  └─ {lock_id}: { status, timestamp_lock, evento_id?, ... }
  ├─ Notificacoes/
  │  └─ {notif_id}: { timestamp, enviada, tipo, ... }
  └─ MemoriaTemporaria/
     └─ {usuario_id}: { contexto, draft, ... }
```

### Dados de Teste

```
dono_id = "test_owner_{run_id}"
cliente_id = "test_cliente_{run_id}"
run_id = timestamp único por execução
```

### Mocks Permitidos

✅ **Mock permitido** para falhas EXTERNAS:
- GPT timeout/erro
- Envio de mensagem falha
- Timeout de rede

❌ **Mock PROIBIDO:**
- Firestore (usar real/dev)
- Agenda/contexto
- Locks
- Notificações

---

## 🧪 Como Executar

### Execução 1

```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"

python tests/runner_p0_resiliencia_operacional_real.py > logs/RO_exec1.log 2>&1
```

Verificar resultado:
- Todos os 13 testes executaram?
- Quantos passaram?
- Quais falhas aparecem?

### Execução 2 e 3

Repetir sem alterações no código (validar repetibilidade).

### Saída Esperada

```json
{
  "run_id": "test_20260619_143025",
  "resumo": {
    "total": 12,
    "passou": 12,
    "falhou": 0,
    "bug_encontrado": 0
  },
  "testes": [...]
}
```

---

## ✅ Critério Aprovação FASE 4

**Todos os critérios abaixo são obrigatórios:**

1. ✅ **13/13 testes passando** — Nenhum falho
2. ✅ **3 execuções consecutivas** — Repetibilidade comprovada
3. ✅ **Firestore real/dev** — Não mock
4. ✅ **Sem locks órfãos** — RO-04, RO-05 validadas
5. ✅ **Sem duplicação de eventos** — RO-03, RO-06, RO-07, RO-12
6. ✅ **Sem eventos parciais** — RO-10 validada
7. ✅ **Cleanup robusto** — Cada teste limpa seu contexto

**Se algum critério falhar:**
- ❌ Não aprova FASE 4
- 📝 Registra como bug/achado
- 🔧 Requer patch mínimo antes de reexecução

---

## 🐛 Bugs Encontrados

| Teste | Tipo Erro | Descrição | Status | Ação |
|-------|-----------|-----------|--------|------|
| RO-04 | DESCOBRIR | Lock órfão | — | — |
| RO-05 | DESCOBRIR | Expiração lock | — | — |
| ... | ... | ... | ... | ... |

---

## 📋 Checklist Aprovação

### Antes de Iniciar Testes

- [ ] Firestore dev configurado
- [ ] Credenciais Firebase ativas
- [ ] Pasta `logs/` criada
- [ ] Arquivo `resultado_p0_resiliencia_operacional_real.json` pronto
- [ ] Documentação lida (CLAUDE.md + Regra Zero)

### Durante Execução

- [ ] Registrar cada execução com timestamp
- [ ] Não modificar código entre execuções 1-3
- [ ] Monitorar Firestore para dados orphan
- [ ] Coletar logs completos

### Após 3 Execuções

- [ ] Todos 12 testes passaram em todas 3?
  - SIM: Prosseguir para aprovação
  - NÃO: Registrar bugs, corrigir, reexecutar
- [ ] Nenhum lock órfão permaneceu?
- [ ] Cleanup de dados de teste funcionou?
- [ ] Atualizar `resultado_p0_resiliencia_operacional_real.json`

### Aprovação Final

- [ ] Atualizar status em MEMORIA.md
- [ ] Documentar qualquer bug encontrado
- [ ] Criar commit com resultados
- [ ] FASE 4 aprovada ou bloqueada por bug

---

## 🚨 Regras Críticas

### Firestore Obrigatório

Não é permitido:
- ❌ Mock de Firestore
- ❌ Simular estado em memória
- ❌ Testar lógica sem persistência real

Porque:
- Race conditions aparecem apenas com concorrência real
- Locks órfãos aparecem apenas com Firestore real
- Duplicação de eventos detectada apenas com persistência real

### Rollback Automático

Cada teste deve:
1. Criar dados de teste
2. Executar cenário
3. **Validar resultados**
4. **Limpar tudo** (eventos, locks, notificações, contexto)

Sem limpeza: próximo teste herda estado anterior.

### Nenhum Patch Durante Testes

Execuções 1-3 devem usar **EXATAMENTE o mesmo código**.

Se descobrir bug:
1. Registrar em `bugs_encontrados`
2. Depois das 3 execuções: criar patch mínimo
3. Reexecutar com código corrigido

---

## 📊 Exemplo Resultado

```json
{
  "run_id": "test_20260619_143025",
  "timestamp": "2026-06-19T14:30:25.123456",
  "resumo": {
    "total": 12,
    "passou": 12,
    "falhou": 0,
    "bug_encontrado": 0,
    "bloqueado": 0
  },
  "testes": [
    {
      "teste_id": "RO-01",
      "nome": "Restart com confirmação pendente",
      "status": "passou",
      "duracao_ms": 145,
      "erro": null,
      "achados": [],
      "observacoes": "Contexto preservado, confirmação processada, evento criado"
    },
    ...
  ],
  "bugs_encontrados": [],
  "observacoes_gerais": "Execução 1/3 — Todos os testes passaram"
}
```

---

## 🔗 Referências

- **CLAUDE.md** — Regra Zero + 13 regras (leitura obrigatória)
- **event_service_async.py** — Lógica de salvar_evento
- **agenda_lock_service.py** — Implementação de locks
- **notificacao_service.py** — Gestão de notificações
- **firebase_service_async.py** — Operações Firestore

---

## 📅 Timeline

| Data | Milestone | Status |
|------|-----------|--------|
| 2026-06-19 | Criar testes + documentação | ✅ |
| 2026-06-19 | Execução 1 | ⏳ |
| 2026-06-19 | Execução 2 | ⏳ |
| 2026-06-19 | Execução 3 | ⏳ |
| 2026-06-19 | Análise + aprovação/patches | ⏳ |

---

**Status FASE 4:** Aguardando execuções reais.

Documento atualizado: 2026-06-19  
Responsável: NeoEve Automation  
Crítica: P0
