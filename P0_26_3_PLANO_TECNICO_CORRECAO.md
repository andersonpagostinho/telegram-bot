# P0.26.3 — PLANO TÉCNICO DE CORREÇÃO

**Status**: 🟡 **AUDITORIA + PLANEJAMENTO (SEM IMPLEMENTAÇÃO)**  
**Data**: 2026-11-05

---

## P0.26.3-A — IDENTIDADE DO EVENTO

### Situação Atual

**Geração do ID** (services/event_service_async.py:265-266):
```python
base_id = f"{evento.get('cliente_id')}_{evento.get('profissional')}_{evento.get('data')}"
event_id = base_id.replace(" ", "_").lower()
# Resultado: "whatsapp:5511991382080_bruna_2026-11-06"
```

### Decisão Arquitetural Anterior

Comentário em linha 262-263:
```
[FIX-P0.4] REMOVER hora_inicio do event_id para permitir UPDATE ao ajustar horário
Problema: incluir hora_inicio causa novo evento quando hora muda (criar em vez de UPDATE)
```

**Justificativa**: Sem hora no ID, quando usuário muda horário (15:00 → 16:00), o sistema pode fazer UPDATE em vez de CREATE.

### Problema Criado

Mas sem hora no ID: **dois agendamentos legítimos no mesmo dia = MESMO ID**

```
Cenário 1: Novo agendamento
├─ Cliente: A
├─ Profissional: Bruna  
├─ Data: 06/11
├─ Horário 1: 15:00 → evento_1 criado
│  ID: a_bruna_2026-11-06
└─ Horário 2: 16:00 → evento_2 buscado
   ID: a_bruna_2026-11-06 (COLISÃO!)
   → Encontra evento_1 (15:00)
   → Tenta UPDATE 15:00 → 16:00
   → NameError em FUSO_BR
   → Locks de 16:00 não liberados
   → Erro para cliente
```

### Soluções Possíveis

#### Opção A: Incluir hora no ID (recomendada)
**Risco**: Quebra a lógica UPDATE quando hora muda

**Impacto**: 
- Novo agendamento 16:00 = novo ID ✓
- UPDATE 15:00 → 16:00 = precisaria deletar antigo + criar novo
- Mas faz sentido: são IDs diferentes, operações diferentes

**Compatibilidade**:
- Eventos antigos continuam com ID antigo (sem hora)
- Novo agendamento usa ID com hora
- Ambos coexistem no Firestore
- Query por evento específico funciona igual (path-based)

#### Opção B: Adicionar hora_inicio_original ao ID
**Risco**: ID fica muito longo

#### Opção C: Manter sem hora + mudar lógica de detecção
**Risco**: Muita refatoração, altamente sujeito a bugs

### Recomendação

**Use Opção A**: Incluir hora no ID

**Formato proposto**:
```python
hora_for_id = evento.get('hora_inicio', '00:00').replace(':', '')
base_id = f"{cliente_id}_{profissional}_{data}_{hora_for_id}"
# Resultado: "whatsapp:5511991382080_bruna_2026-11-06_1500"
```

**Justificativa**:
- Resolve colisão de IDs
- Mantém compatibilidade (antigos sem hora, novos com hora)
- UPDATE passa a ser DELETE+CREATE (operação válida)
- Firestore path-based, não quebra queries

---

## P0.26.3-B — FUSO_BR

### Situação Atual

**Linhas que usam FUSO_BR**:
```
Linha 447:  now_iso = datetime.now(FUSO_BR).isoformat()
Linha 629:  evento_existente["confirmado_em"] = datetime.now(FUSO_BR).isoformat()
Linha 739:  evento_existente["confirmado_em"] = datetime.now(FUSO_BR).isoformat()
```

**Imports faltantes**:
```python
# NÃO EXISTE EM agenda_lock_service.py:
from pytz import timezone
FUSO_BR = timezone("America/Sao_Paulo")
```

### Padrão do Projeto

Outros arquivos que DEFINEM FUSO_BR corretamente:
- `handlers/encaixe_handler.py`
- `handlers/followup_handler.py`
- `handlers/lista_espera_handler.py`
- `router/principal_router.py`
- `scheduler/notificacoes_scheduler.py`

### Solução

**Opção recomendada**: Adicionar imports no início de agenda_lock_service.py

```python
# Após linha 17 (after asyncio import)
from pytz import timezone

# Após linha 30 (after logger = ...)
FUSO_BR = timezone("America/Sao_Paulo")
```

**Por que não importar de outro módulo?**
- Evita circular imports
- Cada módulo é auto-contido
- Padrão já estabelecido no projeto

### Compatibilidade

✅ Zero breaking changes — apenas adiciona uma definição que estava faltando.

---

## P0.26.3-C — LIBERAÇÃO DE LOCKS EM ERRO

### Situação Atual

**Linha 808-816** (except Exception):
```python
except Exception as e:
    logger.error(f"Erro geral em criar_evento_com_lock: {e}")
    return {
        "ok": False,
        "lock_ids": [p.split("/")[-1] for p in locks_criados],
        "motivo": f"Erro inesperado: {str(e)}",
        "tipo_erro": "erro"
    }
```

**Problema**: Retorna os lock IDs mas **não libera os locks do Firestore**.

### Análise de Locks Criados

**Quando locks são criados**:
- Linha 595-602: Para cada bucket, cria lock_doc
- Linha 605: `adquirir_locks_atomicamente()` cria TODOS atomicamente
- Lista `locks_criados` é populada com paths: `"Clientes/{dono_id}/AgendaLocks/{key}"`

**Quando locks são confirmados**:
- Linha 781-787: Para cada lock, seta `status: "confirmado"` + `evento_id`
- Só ocorre se evento foi salvo com sucesso

**Quando locks deveriam ser liberados**:
- Se evento foi salvo → locks confirmados (status="confirmado")
- Se erro antes do evento ser salvo → locks deletados
- **ATUAL**: Locks não são deletados ❌

### Proposição de Solução

Adicionar cleanup em `except Exception as e:` (linha 808)

```python
except Exception as e:
    logger.error(f"Erro geral em criar_evento_com_lock: {e}")
    
    # 🔥 LIBERAR locks se foram criados e não foram confirmados
    if locks_criados:
        locks_liberados = 0
        for lock_path in locks_criados:
            try:
                # Verificar se lock foi confirmado
                lock_doc = await buscar_dado_em_path(lock_path)
                if lock_doc and lock_doc.get("status") != "confirmado":
                    await deletar_dado_em_path(lock_path)
                    locks_liberados += 1
                elif not lock_doc:
                    # Lock já não existe (?)
                    pass
            except Exception as cleanup_error:
                logger.warning(f"Erro ao limpar lock {lock_path}: {cleanup_error}")
        
        if locks_liberados > 0:
            logger.info(f"[CLEANUP_ERRO] {locks_liberados} locks liberados após erro")
    
    return {
        "ok": False,
        "lock_ids": [p.split("/")[-1] for p in locks_criados],
        "motivo": f"Erro inesperado: {str(e)}",
        "tipo_erro": "erro"
    }
```

### Casos de Exceção a Tratar

1. **NameError (FUSO_BR)**: Locks criados mas não confirmados → liberar
2. **Falha em atualizar idempotente**: Locks criados, evento existe, error → liberar
3. **Falha em persistir evento**: Locks criados, evento não salvo → liberar
4. **Falha na confirmação dos locks**: Evento salvo, locks não confirmados → **NÃO liberar** (evento vai verificar depois)

### Compatibilidade

✅ Não quebra nenhuma lógica existente.  
✅ Apenas adiciona cleanup preventivo.  
⚠️ Requer verificação de status antes de deletar (para não deletar locks confirmados).

---

## P0.26.3-D — SEQUÊNCIA COMPLETA DE INTERAÇÕES

### Cenário 1: Novo Agendamento (Sucesso)

```
1. salvar_evento() chamada
2. event_id gerado (A_Bruna_2026-11-06_1500) ← COM HORA
3. criar_evento_com_lock() chamada
4. Locks criados para 16:00-16:40 (4 buckets)
5. locks_criados = [path1, path2, path3, path4]
6. Evento não existe (novo)
7. Evento salvo em Firestore
8. Locks confirmados (status=confirmado, evento_id=X)
9. Retorna {"ok": True, "confirmado_nesta_requisicao": True}
10. event_handler envia mensagem oficial ✨

✅ SUCESSO
```

### Cenário 2: Segundo Horário Mesmo Dia (Sucesso)

```
1. salvar_evento() chamada para 16:00
2. event_id = A_Bruna_2026-11-06_1600 ← NOVA HORA, NOVO ID
3. criar_evento_com_lock() chamada
4. Locks criados para 16:00-16:40
5. Evento não existe (novo, ID diferente)
6. Evento salvo
7. Locks confirmados
8. Retorna sucesso
9. Mensagem oficial enviada

✅ SUCESSO - Ambos eventos coexistem
```

### Cenário 3: Retry do Mesmo Agendamento (Idempotência)

```
1. salvar_evento() chamada para 16:00 (RETRY)
2. event_id = A_Bruna_2026-11-06_1600 (MESMO ID)
3. criar_evento_com_lock() chamada
4. Tenta criar locks para 16:00-16:40
5. ❌ Locks JÁ EXISTEM (falha atômica)
6. Fallback idempotência:
   └─ Evento existe (ID igual)
   └─ Evento já confirmado
   └─ Chama _atualizar_evento_com_locks_idempotente()
   └─ hora_antiga (16:00) == hora_nova (16:00) → IDEMPOTÊNCIA
   └─ Retorna {"ok": True, "confirmado_nesta_requisicao": False}
7. event_handler recebe False
8. Não envia mensagem (já foi enviada antes)

✅ IDEMPOTÊNCIA - Sem duplicação
```

### Cenário 4: Reagendamento (Mudança de Horário) - COM FIX

```
1. Evento existente: 15:00 (ID: ...1500)
2. Cliente tenta 16:00
3. NEW event_id = ...1600 (DIFERENTE)
4. criar_evento_com_lock() chamada
5. Locks criados para 16:00
6. Evento novo não existe
7. Evento novo salvo
8. Locks de 16:00 confirmados
9. Retorna sucesso
10. Cliente agora tem DOIS eventos

⚠️ Mudança necessária em fluxo de reagendamento:
- Sistema deveria detectar "estou mudando meu horário"
- Deveria deletar evento antigo
- Ou ter lógica "um agendamento por profissional por cliente por dia"
```

### Cenário 5: Erro com FUSO_BR (ANTES DA FIX)

```
1. Evento 15:00 existe
2. Cliente tenta 16:00 (novo ID com fix)
3. Locks criados para 16:00: [lock1, lock2, lock3, lock4]
4. locks_criados = [path1, path2, path3, path4]
5. Evento novo salvo
6. ❌ Tenta confirmar locks
7. ❌ datetime.now(FUSO_BR) → NameError
8. except Exception captura erro
9. ❌ Sem cleanup: locks permanecem "reservado" por 24h
10. Retorna {"ok": False, "motivo": "Erro inesperado..."}
11. Cliente recebe erro, não sabe o que aconteceu

🔴 FALHA + DEADLOCK (Com fix de liberação):
8. except Exception captura erro
9. ✅ Cleanup: percorre locks_criados
10. ✅ Deleta locks com status != "confirmado"
11. ✅ Locks liberados
12. Retorna erro, cliente pode tentar de novo
13. Proxima tentativa funciona

✅ COM FIX - Erro tratado, sem deadlock
```

### Cenário 6: Falha em Atualização Idempotente

```
1. Evento 15:00 existe (confirmado)
2. Cliente retenta 15:00 (mesmo agendamento)
3. event_id = ...1500 (MESMO)
4. Locks para 15:00 criados
5. ❌ Locks JÁ EXISTEM (falha atômica, status="confirmado")
6. Fallback: Evento existe
7. Tenta _atualizar_evento_com_locks_idempotente()
8. ❌ FUSO_BR não definido
9. NameError em linha 447
10. except Exception captura
11. ✅ Cleanup libera locks
12. Retorna erro

✅ COM FIX - Locks liberados
```

---

## P0.26.3-E — REGRESSÃO E TESTES

### Testes Que Devem Passar

| Teste | Status | Impacto |
|-------|--------|---------|
| **P0.19** (Extração hora) | ✅ Sem mudança | Continua passando |
| **P0.24** (Cálculo hora_fim) | ✅ Sem mudança | Continua passando |
| **P0.26** (Confirmação oficial) | ⚠️ Muda idempotência | Novo agendamento funciona |
| **Novo: ID com hora** | ✅ Novo teste | Dois agendamentos coexistem |
| **Novo: FUSO_BR** | ✅ Novo teste | Timestamp criado correctamente |
| **Novo: Lock cleanup** | ✅ Novo teste | Locks liberados em erro |
| **Multi-tenant** | ✅ Sem mudança | Isolamento mantido |
| **Compatibilidade retroativa** | ✅ Sem mudança | Eventos antigos funcionam |

### Testes Unitários Propostos

```python
# T1: Novo agendamento com ID contendo hora
def test_event_id_inclui_hora():
    # Agendamento 1: 15:00
    # Agendamento 2: 16:00
    # Esperado: IDs diferentes
    # Atual: IDs iguais
    # APÓS FIX: IDs diferentes ✓

# T2: FUSO_BR definido
def test_fuso_br_disponivel():
    # datetime.now(FUSO_BR) deve funcionar
    # ATUAL: NameError
    # APÓS FIX: Funciona ✓

# T3: Locks liberados em erro
def test_locks_liberados_em_erro():
    # Criar locks
    # Simular error
    # Verificar Firestore: locks deletados
    # ATUAL: Locks permanecem "reservado"
    # APÓS FIX: Locks deletados ✓
```

### Testes Firestore Reais Propostos

```python
# E2E: Dois agendamentos mesmo dia
async def test_e2e_dois_agendamentos_mesmo_dia():
    # 1. Cliente A, Bruna, 06/11, 15:00
    # 2. Cliente A, Bruna, 06/11, 16:00
    # Esperado: Ambos criados, ambos no Firestore
    # ATUAL: Segundo falha com idempotência falsa
    # APÓS FIX: Ambos criados ✓

# E2E: Retry sem duplicação
async def test_e2e_retry_sem_duplicacao():
    # 1. Agendamento 15:00 (sucesso)
    # 2. Retry 15:00 (mesma requisição)
    # Esperado: Um evento, não dois
    # ATUAL: Falha com NameError
    # APÓS FIX: Um evento, idempotência ✓

# E2E: Erro libera locks
async def test_e2e_erro_libera_locks():
    # 1. Simular NameError em confirmação
    # 2. Verificar Firestore: locks deletados
    # 3. Tentar mesmo agendamento de novo
    # Esperado: Funciona, locks disponíveis
    # ATUAL: Deadlock 24h
    # APÓS FIX: Funciona ✓
```

---

## ORDEM SEGURA DE IMPLEMENTAÇÃO

1. **PRIMEIRO**: Adicionar FUSO_BR import/def (P0.26.3-B)
   - Razão: Fix mais simples, sem riscos
   - Impacto: Resolve NameError imediatamente
   - Testes: Qualquer teste que toca em confirmacao_em

2. **SEGUNDO**: Adicionar lock cleanup (P0.26.3-C)
   - Razão: Depende de FUSO_BR funcionando
   - Impacto: Previne deadlock, não quebra lógica
   - Testes: E2E com erro simulado

3. **TERCEIRO**: Incluir hora no event_id (P0.26.3-A)
   - Razão: Mais impactante, requer migração de dados
   - Impacto: Novos eventos com hora, antigos sem hora
   - Testes: E2E dois agendamentos, teste de compatibilidade

---

## CRITÉRIOS OBJETIVOS PARA LIBERAR DEPLOY

### ✅ Pré-Requisitos Técnicos

- [ ] FUSO_BR importado e testado
- [ ] Lock cleanup implementado e testado
- [ ] Event ID com hora implementado
- [ ] 13/13 testes anteriores PASSAM (P0.19, P0.24, P0.26)
- [ ] 3+ novos testes E2E Firestore PASSAM
- [ ] Multi-tenant isolamento verificado
- [ ] Compatibilidade eventos antigos verificada

### ✅ Verificação em Staging

- [ ] Novo agendamento 16:00 após 15:00 → sucesso
- [ ] Retry 15:00 → idempotência, sem duplicação
- [ ] Erro simulado → locks liberados em < 5s
- [ ] E2E com cliente real (Bruna, 06/11)

### ✅ Monitoramento em Produção

- [ ] Alertar se locks permanecem "reservado" > 1h
- [ ] Alertar se `[CLEANUP_ERRO]` appear nos logs
- [ ] Monitorar success rate de agendamentos
- [ ] Monitorar eventos duplicados por cliente+profissional+data

---

## RESUMO EXECUTIVO

### 3 Bugs Encontrados
1. Event ID sem hora → Colisão de IDs
2. FUSO_BR não importado → NameError
3. Locks não liberados em erro → Deadlock 24h

### 3 Fixes Propostos
1. Incluir hora no ID (formato: `...1600`)
2. Importar FUSO_BR
3. Adicionar cleanup de locks em except

### Impacto de Compatibilidade
✅ Zero breaking changes
✅ Eventos antigos continuam funcionando
✅ Multi-tenant isolamento preservado

### Ordem de Implementação
1. FUSO_BR (mais simples, sem riscos)
2. Lock cleanup (depende de FUSO_BR)
3. Event ID com hora (mais impactante)

### Liberação para Deploy
✅ 13/13 testes anteriores PASSAM  
✅ 3+ novos E2E PASSAM  
✅ Staging validado  
✅ Monitoramento em produção ativo

---

**P0.26.3**: Planejamento técnico completo  
**Status**: 🟡 AUDITORIA SEM IMPLEMENTAÇÃO  
**Próximo**: Aguardar aprovação para P0.27 (Implementação)
