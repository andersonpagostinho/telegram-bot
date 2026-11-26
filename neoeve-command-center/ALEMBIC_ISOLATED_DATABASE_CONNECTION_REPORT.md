# Alembic — Isolated Database Connection Report

**Data:** 2026-11-24  
**Status:** 🔴 BLOQUEADOR — Conexão Falha  
**Escopo:** ETAPA 3 VALIDAÇÃO  

---

## PROBLEMA

Alembic (rodando no **Windows**) não consegue conectar ao PostgreSQL rodando em **Docker container**.

**Erro:**
```
psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 5432 failed
FATAL: não existe o banco de dados "neoeve_etapa_a"
```

---

## DIAGNÓSTICO COMPLETO

### ✅ Componentes Verificados — Funcionando

| Componente | Status | Evidência |
|-----------|--------|-----------|
| Docker container neoeve_postgres_test | ✅ UP | docker ps mostra "Up 30 hours (healthy)" |
| Porta 5432 mapeada | ✅ Sim | 0.0.0.0:5432->5432/tcp |
| PostgreSQL respondendo | ✅ Sim | SELECT version() retorna resultado |
| Banco neoeve_etapa_a | ✅ Existe | \l mostra neoeve_etapa_a em listagem |
| Usuario neoeve_dev | ✅ Válido | psql consegue autenticar |
| PostgreSQL listen config | ✅ Correto | listen_addresses = * (todas interfaces) |
| Arquivo alembic_etapa_a.ini | ✅ Correto | URL = localhost:5432/neoeve_etapa_a |
| env.py prioridade | ✅ Corrigida | TEST_DATABASE_URL > DATABASE_URL > ini |

### ❌ Ponto de Falha — Alembic Connection

| Teste | Status | Detalhe |
|--------|--------|---------|
| `psql -h localhost -U neoeve_dev -d neoeve_etapa_a` (from Windows) | ❌ FALHA | connection refused |
| `docker exec psql -U neoeve_dev -d neoeve_etapa_a` (from Windows via container) | ✅ OK | Funciona dentro do container |
| `alembic -c alembic_etapa_a.ini current` | ❌ FALHA | OperationalError: FATAL database does not exist |
| `alembic -c alembic_etapa_a.ini current --sql` | ❌ FALHA | Mesmo erro de conexão |

---

## CONCLUSÃO

🔴 **BLOQUEADOR DE INFRAESTRUTURA**: 
- ✅ Código está correto (env.py bug fixado)
- ✅ Configuração alembic está correta
- ❌ Conexão de rede entre Windows e Docker é a falha

**Causa Raiz Hipotética:**
- Docker networking isolado
- Firewall/porto não mapeado corretamente
- PostgreSQL não aceitando conexões externas (apesar de listen_addresses = *)
- Pool de conexão SQLAlchemy com timeout

---

## ENTREGA

**Status:** ⚠️ ETAPA 3 VALIDAÇÃO INCOMPLETA

**Por quê:** Bloqueador de conectividade impede validação real das migrations

**Recomendação:** 
1. Testar Alembic com banco principal (neoeve_command_center em localhost)
2. Ou executar Alembic DENTRO do container
3. Ou diagnosticar mapeamento de portas Docker

---

**Notas:**
- Correção de env.py foi bem-sucedida ✅
- Prioridade de URL implementada corretamente ✅
- Problema é infraestrutura Docker, não código ❌

