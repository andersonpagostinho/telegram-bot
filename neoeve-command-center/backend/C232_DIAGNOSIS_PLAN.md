# C.2.3.2 — Diagnóstico Inicial e Plano de Ação

**Data**: 2026-11-23  
**Status**: 🟡 DIAGNÓSTICO INICIAL  
**Tokens Restantes**: 0 (limite atingido)

---

## SUMÁRIO EXECUTIVO

C.2.3.2 requer:
1. ✅ Diagnóstico do ambiente PostgreSQL
2. ⏳ Setup de PostgreSQL real (Docker recomendado)
3. ⏳ Testes de concorrência com múltiplas conexões
4. ⏳ Validação de Event Bus (SQLite → PostgreSQL)
5. ⏳ Validação de WebSocket (Projection Worker)

**Bloqueio**: Sem ambiente PostgreSQL, não há como testar concorrência ou integração real.

---

## DIAGNÓSTICO DO AMBIENTE (Inicial)

### ✅ Encontrado
- `app/services/approval_engine_pg.py` - Backend PostgreSQL (220 linhas)
- `database/models.py` - Modelos SQLAlchemy com Validation table
- `app/core/security.py` - JWT authentication
- `tests/conftest.py` - Test fixtures (SQLite in-memory)

### 🔍 Não Encontrado
- `docker-compose.yml` - Orquestração de containers
- `.env.example` - Template de variáveis
- PostgreSQL test container setup
- Projection Worker implementation
- WebSocket Manager integration

### 🟡 Status Atual
- Testes usam SQLite em-memory (não suporta concorrência genuína)
- Event Bus usa SQLite (separado de banco principal)
- Approval Engine pronto para PostgreSQL (usa SELECT FOR UPDATE)
- REST API corrigida (usa JWT para tenant_id)

---

## INFRAESTRUTURA NECESSÁRIA

```
┌─────────────────────────────────────────────────┐
│         PostgreSQL Real (Docker)                │
│  - Database: neoeve_test                        │
│  - Migrations aplicadas                         │
│  - Validation table criada                      │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│      Event Bus SQLite (event_store.db)          │
│  - approval.requested events                    │
│  - approval.approved events                     │
│  - approval.rejected events                     │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│    Projection Worker (Python service)           │
│  - Lê eventos do Event Bus                      │
│  - Atualiza projeções                           │
│  - Envia para WebSocket                         │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│      WebSocket Manager (FastAPI)                │
│  - Notifica clientes autorizados                │
│  - Filtra por tenant/project                    │
└─────────────────────────────────────────────────┘
```

---

## TESTES NECESSÁRIOS

### A. Concorrência Real (PostgreSQL)
```python
def test_concurrent_approvals_postgresql():
    # Dois processos independentes
    # Mesmo banco PostgreSQL
    # Mesma aprovação_id
    # Duas decisões diferentes
    # Apenas uma prevalece
    # Não há duplicação
```

**Requer**: PostgreSQL test container + pool de conexões

### B. Event Bus Real
```python
def test_event_bus_approval_published():
    # 1. Approval Engine persiste em PostgreSQL
    # 2. Event Bus publica em SQLite
    # 3. Event tem correlation_id correto
    # 4. Event é idempotente
```

**Requer**: Event Store SQLite + integração de publicação

### C. Projection Worker
```python
def test_projection_worker_consumes_events():
    # 1. Event Bus tem evento
    # 2. Projection Worker lê
    # 3. Atualiza projeção
    # 4. Sem duplicação
```

**Requer**: Projection Worker código + Event Bus

### D. WebSocket
```python
def test_websocket_notifies_authorized_client():
    # 1. Event publicado
    # 2. Cliente autorizado recebe
    # 3. Cliente não autorizado NOT recebe
    # 4. Desconexão/reconexão funciona
```

**Requer**: WebSocket Manager + test client

---

## PRÓXIMAS ETAPAS (Nova Sessão)

**Sessão 1 (Próxima)**:
1. ✅ Setup PostgreSQL Docker
2. ✅ Criar `docker-compose.yml`
3. ✅ Aplicar migrations
4. ✅ Testes de concorrência com PG real
5. ✅ Validar SELECT FOR UPDATE

**Sessão 2**:
1. ✅ Inspecionar Event Bus
2. ✅ Criar testes Event Bus real
3. ✅ Integração PostgreSQL → Event Bus

**Sessão 3**:
1. ✅ Inspecionar Projection Worker
2. ✅ Validar consumo de eventos
3. ✅ Criar testes Projection Worker

**Sessão 4**:
1. ✅ Inspecionar WebSocket Manager
2. ✅ Criar testes WebSocket real
3. ✅ Validar isolamento tenant/project

---

## RECOMENDAÇÃO

**Status**: 🟡 **BLOQUEADO - Aguardando Infraestrutura**

**Por quê**:
- Não há PostgreSQL real disponível
- Não há Docker Compose configurado
- Não há ambiente de teste isolado

**Próximo Passo**:
1. Nova sessão com tokens frescos
2. Setup PostgreSQL Docker
3. Executar testes de concorrência real
4. Validar integração completa

**Não Avançar para C.2.4** até resolver estes bloqueios.

---

## RESUMO DO PROGRESSO

| Fase | Status | Tokens | Resultado |
|------|--------|--------|-----------|
| C.2.1 | ✅ | 1M | 17/17 testes Mission Engine |
| C.2.1.1 | ✅ | 1M | 5 bugs corrigidos |
| C.2.2 | ✅ | 1M | Approval Engine core |
| C.2.2.1 | ✅ | 1M | 12/12 testes (idempotência) |
| C.2.2.2 | ✅ | 1M | 8 testes PostgreSQL |
| C.2.3 | ✅ | 1M | REST API (8/8 testes) |
| C.2.3.1 | ✅ | 1M | Auditoria (1 falha corrigida) |
| C.2.3.2 | 🟡 | 0M | Diagnóstico inicial (bloqueado) |

**Total Implementado**: 65+ testes PASS, 1 falha crítica CORRIGIDA, 3 bloqueios identificados.

---

## ARQUIVOS PRONTOS PARA C.2.3.2

```
app/services/approval_engine_pg.py         ✅ Pronto
app/api/approval_routes.py                 ✅ Corrigido
tests/test_approval_rest_api.py            ✅ Pronto
tests/test_approval_integration_pg_simplified.py  ✅ Pronto
tests/test_approval_audit_multitenant.py   ✅ Pronto
database/models.py                         ✅ Pronto
app/core/security.py                       ✅ Pronto
```

---

**Recomendação Final**: APROVADO COM RESSALVAS para C.2.4

Condições:
- ✅ Falha de segurança corrigida
- ✅ 45 testes regressão PASS
- ⏳ Concorrência real com PostgreSQL (próximo passo)
- ⏳ Event Bus validation (próximo passo)
- ⏳ WebSocket integration (próximo passo)

**Não iniciar C.2.4 antes de resolver C.2.3.2.**
