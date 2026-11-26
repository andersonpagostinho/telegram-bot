# Docker PostgreSQL Connectivity — Final Report

**Data:** 2026-11-24  
**Status:** 🔴 BLOQUEADOR CRÍTICO — Conectividade Windows ↔ Docker Falha  

---

## PROBLEMA

**Alembic (Windows) não consegue conectar ao PostgreSQL (Docker container)**, apesar de:
- ✅ Container UP e healthy
- ✅ Porta 5432 mapeada (0.0.0.0:5432)
- ✅ Banco neoeve_etapa_a existe
- ✅ TCP Connection funciona (Test-NetConnection = True)
- ✅ psql (dentro container) consegue acessar
- ❌ psycopg (Windows) falha ao conectar

---

## DIAGNÓSTICO DOCKER

| Componente | Status | Resultado |
|-----------|--------|-----------|
| Container state | ✅ | Up 30 hours (healthy) |
| Port mapping | ✅ | 5432/tcp -> 0.0.0.0:5432 |
| PostgreSQL listen | ✅ | listen_addresses = * |
| Banco neoeve_etapa_a | ✅ | EXISTS (dropped and recreated) |
| Usuario neoeve_dev | ✅ | Superuser, Create DB |
| neoeve_dev access | ✅ | Via docker exec psql: OK |

---

## DIAGNÓSTICO WINDOWS

| Teste | Status | Resultado |
|--------|--------|-----------|
| Test-NetConnection localhost 5432 | ✅ | TcpTestSucceeded = True |
| TCP Connection 127.0.0.1:5432 | ✅ | Aceita conexão |
| psql -h 127.0.0.1 | ⚠️ | Exige PGPASSWORD |
| psql login via neoeve_dev | ⚠️ | "permissão negada" (sem privilégios de superuser externo) |

---

## ERRO ALEMBIC

```
psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 5432 failed
FATAL: não existe o banco de dados "neoeve_etapa_a"

Multiple connection attempts failed:
- host: 'localhost', port: 5432, hostaddr: '::1' — FAILED
- host: 'localhost', port: 5432, hostaddr: '127.0.0.1' — FAILED
```

---

## PERSISTÊNCIA APÓS RECRIAÇÃO

Banco foi **dropado e recriado** via Docker, mas Alembic AINDA retorna mesmo erro.

**Conclusão:** Problema NÃO é "banco não existe" mas **falha de comunicação real entre psycopg (Windows) e PostgreSQL (Docker)**.

---

## POSSÍVEIS CAUSAS

1. **Network Isolation** — Container Docker em rede isolada que psycopg não consegue acessar
2. **Firewall Windows** — Bloqueando porta 5432
3. **psycopg Pool** — Pool de conexão com timeout excessivo
4. **PostgreSQL Host Binding** — Escutando em interface diferente do esperado
5. **DNS Resolution** — localhost/127.0.0.1 resolvem diferentemente para psycopg

---

## RECOMENDAÇÃO

**ETAPA 3 VALIDAÇÃO INCOMPLETA** devido a bloqueador de infraestrutura Docker.

**Próximos Passos:**
1. ❌ Usar `docker run -it` para terminal interativo direto no container
2. ❌ Executar Alembic DENTRO do container
3. ⚠️ OU diagnosticar rede Docker (docker network inspect)
4. ⚠️ OU testar com banco principal (neoeve_command_center)

---

## ENTREGA ETAPA A

✅ **Código:** Bugs corrigidos em env.py  
✅ **Prioridade URLs:** Implementada  
✅ **Modo Online:** Confirmado  
🔴 **Validação Real:** Bloqueada (infraestrutura)

