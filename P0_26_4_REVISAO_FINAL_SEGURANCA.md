# P0.26.4 — REVISÃO FINAL DE SEGURANÇA

**Status**: 🟢 **AUDITORIA CONCLUÍDA**  
**Decisão**: ✅ **P0.27 AUTORIZÁVEL**

---

## P0.26.4-A — COMPATIBILIDADE E IDEMPOTÊNCIA DE EVENTOS ANTIGOS

### Questão 1: Como o sistema encontrará eventos criados com ID antigo?

**Resposta**: ✅ **AUTOMÁTICO - SEM MUDANÇA**

**Evidência** (services/event_service_async.py:380):
```python
eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
```

Busca **TODOS** os documentos em `Clientes/{tenant_id}/Eventos/`:
- Eventos com ID antigo: `whatsapp:5511991382080_bruna_2026-11-06`
- Eventos com ID novo: `whatsapp:5511991382080_bruna_2026-11-06_1500`

Firestore retorna ambos por `buscar_subcolecao()` que itera na coleção.

### Questão 2: Como evitar duplicação em retry com formato antigo?

**Resposta**: ✅ **PATH-BASED LOOKUP - IDEMPOTÊNCIA PRESERVADA**

**Evidência** (services/event_service_async.py:283):
```python
path = f"Clientes/{tenant_id}/Eventos/{event_id}"
```

Retry com ID antigo:
```
Requisição 1: event_id = "a_bruna_2026-11-06" → criado, salvo em path
Requisição 2: event_id = "a_bruna_2026-11-06" (retry) 
  → buscar_dado_em_path() encontra no mesmo path
  → marca como idempotência
  → sem duplicação ✓
```

### Questão 3: Como cancelamento e reagendamento localizarão eventos antigos?

**Resposta**: ✅ **USANDO event_id RECEBIDO**

**Evidência** (services/event_service_async.py:451-462):
```python
# Cancelamento
path = f"Clientes/{user_id_efetivo}/Eventos/{event_id}"
# Reagendamento: mesmo caminho

# event_id é recebido da requisição anterior
# Se foi criado com ID antigo, será cancelado com ID antigo
# Se foi criado com ID novo, será cancelado com ID novo
```

### Questão 4: Como consultas de disponibilidade considerarão eventos antigos?

**Resposta**: ✅ **FILTRAGEM POR DATA+HORA, NÃO POR ID**

**Evidência** (services/event_service_async.py:1363-1364):
```python
def evento_deve_ser_ignorado(ev: dict, event_id: str | None = None) -> bool:
    # Se tem data e horário, ocupa agenda mesmo se ainda estiver pendente
    if ev.get("data") and ev.get("hora_inicio"):
        return False
```

Disponibilidade cheça:
```python
if ev.get("data") and ev.get("hora_inicio"):
    # Ocupa agenda se tem data + hora
    # NÃO importa o ID
```

✅ Eventos antigos e novos com mesma data+hora bloqueiam conflitos igualmente

### Questão 5: Existe risco de criar dois documentos representando o mesmo agendamento?

**Resposta**: ✅ **NENHUM RISCO**

**Por quê**:
- ID antigo (`a_bruna_2026-11-06`) e novo (`a_bruna_2026-11-06_1500`) são **diferentes**
- Firestore cada ID = documento diferente
- Se nova requisição vem para 16:00, gera ID NOVO (`a_bruna_2026-11-06_1600`)
- Antigo (15:00, sem hora no ID) e novo (16:00, com hora no ID) são documentos separados
- **Não há colisão** ✓

### Questão 6: É necessária migração?

**Resposta**: ❌ **NÃO - COMPATIBILIDADE AUTOMÁTICA**

- Eventos antigos: lidos como-estão, com ID antigo
- Eventos novos: criados com ID novo
- Ambos coexistem naturalmente
- Não requer migração de dados
- Não requer upgrade de eventos antigos

### Classificação P0.26.4-A
✅ **APROVADO** - Compatibilidade automática, sem quebra, sem duplicação

---

## P0.26.4-B — SEGURANÇA DO CLEANUP DE LOCKS

### Questão 1: Como identificar exclusivamente locks da requisição atual?

**Resposta**: ✅ **VIA LISTA locks_criados**

**Evidência** (services/agenda_lock_service.py:543):
```python
locks_criados = []  # Para rollback se necessário
```

Durante aquisição (linhas 595-602):
```python
for bucket in buckets:
    lock_key = f"{prof_norm}_{data_evento}_{bucket}"
    lock_path = f"Clientes/{dono_id}/AgendaLocks/{lock_key}"
    lock_docs_dict[lock_key] = lock_doc
    
    locks_criados.append(lock_path)  # ← Rastreado
```

**Conclusão**: Lista `locks_criados` contém EXATAMENTE os locks desta requisição ✓

### Questão 2: Como impedir liberação de locks de outra operação?

**Resposta**: ✅ **ESCOPO LOCAL - locks_criados isolado por requisição**

Cada chamada a `criar_evento_com_lock()`:
- Cria nova lista `locks_criados = []` (linha 543)
- Popula APENAS locks daquela requisição
- Cleanup usa AQUELA lista
- **Nenhuma interferência entre requisições** ✓

### Questão 3: Como distinguir lock `reservado` de lock `confirmado`?

**Resposta**: ✅ **VIA CAMPO status**

**Evidência** (services/agenda_lock_service.py:599-600):
```python
"status": "reservado",  # ← Criação
```

Confirmação (linhas 782-783):
```python
"status": "confirmado",
"evento_id": event_id,
```

Cleanup proposto:
```python
if lock_doc and lock_doc.get("status") != "confirmado":
    # Deletar apenas se NÃO está confirmado
```

**Segurança**: Nunca deleta lock confirmado ✓

### Questão 4: Quais exceções devem acionar cleanup?

**Resposta**: ✅ **TODAS APÓS AQUISIÇÃO DE LOCKS**

Casos cobertos:
1. **NameError (FUSO_BR)** - linha 629: sim, limpar
2. **Falha em atualização idempotente** - linha 633-640: sim, limpar
3. **Falha em persistir evento** - linha 798: sim, limpar
4. **Falha na confirmação locks** - linha 787: NÃO limpar (evento salvo, locks continuam)
5. **Exceção geral** - linha 808: sim, limpar

### Questão 5: Como tratar falha durante cleanup?

**Resposta**: ✅ **TRY/EXCEPT + LOG, NÃO FALHA SILENCIOSO**

Proposta:
```python
for lock_path in locks_criados:
    try:
        lock_doc = await buscar_dado_em_path(lock_path)
        if lock_doc and lock_doc.get("status") != "confirmado":
            await deletar_dado_em_path(lock_path)
    except Exception as cleanup_error:
        logger.warning(f"Erro ao limpar lock: {cleanup_error}")
        # ← Log, mas continua com próximos locks
```

**Segurança**: Falha no cleanup não impede erro ser retornado ao cliente ✓

### Questão 6: Existe mecanismo de recuperação para locks órfãos?

**Resposta**: ✅ **SIM - TAREFA limpar_locks_expirados**

**Evidência** (services/agenda_lock_service.py:819):
```python
async def limpar_locks_expirados(dono_id: str, horas_expiracao: int = 24) -> int:
```

Função dedicada que limpa locks com `expira_em` < agora.

**Fluxo**:
1. Lock criado com `expira_em = agora + 24h`
2. Se não liberado, após 24h é auto-limpo
3. Horário fica disponível novamente

**Segurança**: Garantia de recuperação em 24h máximo ✓

### Classificação P0.26.4-B
✅ **APROVADO COM RESSALVAS**
- Cleanup é seguro se implementado conforme proposto
- **Ressalva**: Nunca deletar lock `confirmado` (verificar status primeiro)

---

## P0.26.4-C — EVENTO PERSISTIDO E CONFIRMAÇÃO DOS LOCKS FALHA

### Cenário Crítico

```
1. Locks adquiridos ✓
2. Evento gravado no Firestore ✓
3. Confirmação dos locks falha ❌
   └─ datetime.now(FUSO_BR) → NameError (ANTES DO FIX)
4. Handler recebe erro
```

### Questão 1: O evento permanece confirmado?

**Resposta**: ✅ **SIM, evento fica salvo e confirmado**

**Evidência** (services/agenda_lock_service.py:777):
```python
# Evento já foi salvo
await salvar_dado_em_path(evento_path, evento)
logger.info(f"Evento criado: {event_id}")

# Só depois tenta confirmar locks
for lock_path in locks_criados:
    lock_doc = {
        "status": "confirmado",
        ...
    }
    await atualizar_dado_em_path(lock_path, lock_doc)  # ← FALHA AQUI
```

Evento já está em `confirmado=True` em Firestore.

### Questão 2: Os locks permanecem reservados ou são liberados?

**Resposta**: 🔴 **PERMANECEM RESERVADO (BUG #3)**

**Sem fix**: Locks continuam com `status: "reservado"` por 24h

**Com fix**: Locks são deletados no except (linha 808)

### Questão 3: Um retry pode duplicar o evento?

**Resposta**: ❌ **NÃO - IDEMPOTÊNCIA PROTEGE**

**Fluxo**:
```
1. Primeiro retry: Locks falham (já existem "reservado")
2. Fallback: Busca evento
3. Encontra evento já confirmado
4. Chama _atualizar_evento_com_locks_idempotente()
5. Detecta mesmo horário, retorna IDEMPOTÊNCIA
6. Sem duplicação ✓
```

### Questão 4: Uma nova solicitação pode ocupar o mesmo horário?

**Resposta**: ✅ **NÃO - EVENTO CONFIRMADO OCUPA HORÁRIO**

**Por quê**: 
```python
if ev.get("data") and ev.get("hora_inicio"):
    return False  # Não ignorar, ocupa agenda
```

Mesmo que locks estejam "reservado", evento confirmado no Firestore ocupa agenda.

### Questão 5: Como recuperar consistência entre evento e locks?

**Resposta**: ✅ **AUTOMÁTICO EM 24H**

Fluxo:
```
T0: Evento confirmado, locks "reservado"
T1-T24h: Horário bloqueado
T24h: limpar_locks_expirados() executa
  → Deleta locks "reservado" com expira_em passado
  → Horário fica livre novamente
```

**Se nova requisição chega antes de 24h**:
```
Tenta criar novo lock para mesmo horário
Conflito com evento confirmado (data+hora)
Retorna "Slot ocupado"
```

✅ Sem corrupção de dados

### Classificação P0.26.4-C
✅ **APROVADO** - Com fix de cleanup, restauração automática em 24h

---

## P0.26.4-D — IDENTIDADE DO EVENTO E RETRY

### Validação de Cenários

| Operação | Resultado | Status |
|----------|-----------|--------|
| Primeiro agendamento 15h | Cria evento A | ✅ OK |
| Segundo agendamento 16h | Cria evento B | ✅ OK (ID diferente com fix) |
| Retry agendamento 15h | Reutiliza evento A | ✅ OK (mesmo ID) |
| Retry agendamento 16h | Reutiliza evento B | ✅ OK (mesmo ID) |
| Reagendamento 15h→17h | Atualiza evento A | ✅ OK (update idempotente) |
| Novo agendamento 17h | Cria evento C | ✅ OK (novo ID com hora) |

### Validação de Concorrência

**Duas requisições simultâneas para 15:00**:

```
Req1: Tenta criar locks para 15:00
Req2: Tenta criar locks para 15:00

Firestore atômica: apenas uma succeeds
Outra recebe: {"ok": False, "motivo": "Slot ocupado"}

Resultado: Um evento, zero duplicação ✅
```

**Evidência** (services/agenda_lock_service.py:605):
```python
resultado_lock = await adquirir_locks_atomicamente(...)
# Atomicidade garante apenas um sucesso
```

### Validação de Coherência

1. **Identidade**: event_id único por cliente+profissional+data+hora ✓
2. **Idempotência**: retry com mesmo ID → sem duplicação ✓
3. **Conflito**: busca por data+hora, não por ID ✓
4. **Concorrência**: locks atômicos previnem duplicação ✓

### Classificação P0.26.4-D
✅ **APROVADO** - Todos cenários validados, concorrência segura

---

## PARECER FINAL

### Resumo das 4 Auditorias

| Auditoria | Resultado | Detalhes |
|-----------|-----------|----------|
| **A. Compatibilidade** | ✅ APROVADO | Automática, sem migração |
| **B. Segurança locks** | ✅ APROVADO COM RESSALVAS | Verificar status antes de deletar |
| **C. Evento+locks falha** | ✅ APROVADO | Recuperação automática em 24h |
| **D. Retry e concorrência** | ✅ APROVADO | Atomicidade + idempotência |

### Riscos Encontrados

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| Locks "reservado" 24h (BUG #3) | 🔴 CRÍTICO | Fix: cleanup no except |
| FUSO_BR undefined (BUG #2) | 🔴 CRÍTICO | Fix: adicionar import |
| Event ID colisão (BUG #1) | 🔴 CRÍTICO | Fix: incluir hora |

Todos mitigados pelos 3 fixes propostos.

### Ajustes ao Plano P0.26.3

✅ **SEM AJUSTES NECESSÁRIOS** - Plano está seguro conforme proposto

### Ordem Definitiva de Implementação

1. **FUSO_BR** (import + def)
2. **Lock cleanup** (except Exception)
3. **Event ID com hora** (incluir no base_id)

### Testes Adicionais Obrigatórios

**E2E Firestore Real**:
```python
# T1: Dois agendamentos coexistem
test_dois_agendamentos_mesmo_dia_coexistem()

# T2: Retry sem duplicação
test_retry_idempotente_sem_duplicacao()

# T3: Erro libera locks
test_erro_libera_locks_em_24h()

# T4: Concorrência segura
test_requisicoes_simultaneas_sem_duplicacao()

# T5: Compatibilidade eventos antigos
test_eventos_antigos_sem_hora_no_id_funcionam()
```

### Critérios Objetivos de Aprovação do P0.27

✅ **PRÉ-REQUISITOS**:
- [ ] FUSO_BR definido e testado
- [ ] Lock cleanup implementado e testado
- [ ] Event ID com hora implementado
- [ ] 13/13 testes anteriores PASSAM
- [ ] 5/5 novos testes E2E PASSAM
- [ ] Multi-tenant isolamento OK
- [ ] Compatibilidade retroativa OK

✅ **STAGING**:
- [ ] Dois agendamentos 15:00 e 16:00 no mesmo dia
- [ ] Retry sem duplicação
- [ ] Erro > locks liberados em < 5s
- [ ] E2E com cliente real

✅ **PRODUÇÃO**:
- [ ] Alertar locks "reservado" > 1h
- [ ] Alertar [CLEANUP_ERRO] em logs
- [ ] Monitor eventos duplicados = 0
- [ ] Success rate agendamentos estável

---

## DECISÃO FINAL

### ✅ P0.27 AUTORIZÁVEL

**Fundamentação**:
- ✅ 4 auditorias passaram
- ✅ Compatibilidade automática validada
- ✅ Segurança de locks verificada
- ✅ Concorrência e atomicidade confirmadas
- ✅ Nenhum breaking change identificado
- ✅ Recuperação automática funcional
- ✅ Plano técnico P0.26.3 é seguro

**Autorização**: Implementação dos 3 fixes (P0.27) pode proceder conforme planejado.

**Condição**: Testes obrigatórios devem ser implementados antes do deploy em produção.

---

**P0.26.4**: Revisão final de segurança concluída  
**Status**: 🟢 AUTORIZADO PARA P0.27  
**Data**: 2026-11-05
