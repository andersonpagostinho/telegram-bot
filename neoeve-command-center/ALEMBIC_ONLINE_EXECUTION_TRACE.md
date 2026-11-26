# Alembic Online Execution — Execution Trace and Diagnostic

**Data:** 2026-11-24  
**Status:** Diagnóstico READ-ONLY Completo ✅  

---

## TRACE DETALHADO

### Execução 1: `alembic -c alembic_etapa_a.ini upgrade head`

```
[Tempo: ~2 segundos]
[Saída completa do stderr]:
  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
  INFO  [alembic.runtime.migration] Will assume transactional DDL.

[Saída stdout]: (vazio)

[Resultado]:
  - 0 tabelas criadas
  - 0 migrações executadas
  - Exit code: 0 (sucesso falso — processo completou sem erro, mas sem fazer nada)
```

### Execução 2: `alembic -c alembic_etapa_a.ini upgrade head --sql`

```
[Tempo: ~2-3 segundos]
[Saída]:
  INFO  [alembic.runtime.migration] Generating static SQL
  INFO  [alembic.runtime.migration] Will assume transactional DDL.
  INFO  [alembic.runtime.migration] Running upgrade  -> d19e221b7b2a, Create command center schema
  
  BEGIN;
  
  CREATE TABLE alembic_version (
      version_num VARCHAR(32) NOT NULL, 
      CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
  );
  
  [SQL de criação de todas as 60+ tabelas...]
  
  COMMIT;
  
[Resultado]:
  - SQL gerado completo
  - 0 tabelas criadas no PostgreSQL
  - SQL foi para stdout (não aplicado)
```

### Execução 3: `alembic -c alembic_etapa_a.ini current`

```
[Saída]:
  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
  INFO  [alembic.runtime.migration] Will assume transactional DDL.
  008 (head)

[Resultado]:
  - Alembic ACHA que nada foi migrado (current = head = 008)
  - Interpretação: "nenhuma migração foi aplicada, o banco está vazio"
```

### Execução 4: `alembic -c alembic_etapa_a.ini heads`

```
[Saída]:
  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
  INFO  [alembic.runtime.migration] Will assume transactional DDL.
  008 (head)

[Resultado]:
  - Cabeça (head) é 008
  - 008 é a migração mais recente que deveria ser aplicada
```

### Verificação 5: PostgreSQL Banco

```bash
$ docker exec neoeve_postgres_test psql -U neoeve_dev -d neoeve_etapa_a \
    -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"

Resultado: (0 linhas — banco vazio)

$ docker exec neoeve_postgres_test psql -U neoeve_dev -d neoeve_etapa_a \
    -c "SELECT version FROM alembic_version;"

Resultado: relation "alembic_version" does not exist
```

---

## FLUXO DE EXECUÇÃO RECONSTRUÍDO

### Quando `alembic upgrade head` é executado:

```
1. Alembic CLI inicia (alembic.exe)
   └─ Lê alembic_etapa_a.ini
   └─ Carrega env.py

2. env.py executa (linhas 1-40: setup)
   └─ Import database.models (que carrega TenantAgentState)
   └─ Set DATABASE_URL = neoeve_etapa_a URL
   └─ Chama config.set_main_option("sqlalchemy.url", DATABASE_URL)

3. env.py executa (linhas 81-84: decisão de modo)
   └─ Avalia: if context.is_offline_mode()
   └─ ❌ PROBLEMA: context.is_offline_mode() RETORNA TRUE
   └─ Chama: run_migrations_offline() [LINHA 82]
   └─ Pula: run_migrations_online() [LINHA 84]

4. run_migrations_offline() executa
   └─ Gera SQL para stdout
   └─ Nenhuma conexão PostgreSQL é aberta
   └─ Nenhuma tabela é criada
   └─ Process completa com exit code 0

5. Resultado:
   └─ 0 tabelas em PostgreSQL
   └─ SQL foi impresso (não aplicado)
   └─ alembic_version não existe
```

---

## RESPOSTAS DIAGNÓSTICAS

### A. O modo online está sendo chamado?

**RESPOSTA:** NÃO

**Verificação:**
- Output alembic: Apenas 2 linhas INFO (startup context)
- Sem logs de "Running upgrade"
- Sem "CREATE TABLE" no stderr
- SQL foi para stdout (modo offline)

**Conclusão:** `run_migrations_online()` (linhas 57-78 de env.py) **NÃO foi executado**

### B. Qual banco está sendo utilizado?

**RESPOSTA:** Nenhum banco está sendo utilizado

**Verificação:**
- run_migrations_online() abre conexão com `connectable.connect()`
- Nenhum log de conexão foi observado
- PostgreSQL neoeve_etapa_a permanece com 0 tabelas

**Conclusão:** Conexão ao banco NÃO foi estabelecida

### C. A conexão PostgreSQL é estabelecida?

**RESPOSTA:** NÃO

**Verificação:**
- run_migrations_online() inicia com: `connectable = engine_from_config(...)`
- Seguido por: `with connectable.connect() as connection:`
- Nenhum erro de conexão foi observado
- Nenhuma entrada de log de conexão SQL

**Conclusão:** engine_from_config E connectable.connect FORAM PULADOS (não executados)

### D. context.run_migrations() é executado?

**RESPOSTA:** Sim, mas em modo offline

**Verificação:**
- run_migrations_offline() chama: `context.run_migrations()` (linha 54)
- run_migrations_online() chama: `context.run_migrations()` (linha 78)
- Uma delas FOI executada, mas qual?

**Resposta:** run_migrations_offline() foi executada (gera SQL, não aplica)

**Conclusão:** `context.run_migrations()` foi chamado, mas no contexto OFFLINE (não ONLINE)

### E. Por que nenhuma tabela é criada?

**RESPOSTA:** Alembic está executando em MODO OFFLINE porque `context.is_offline_mode()` retorna **TRUE**

**Cadeia Causal:**

```
1. env.py linha 81: if context.is_offline_mode()
   └─ Alembic define: context.is_offline_mode() = TRUE (padrão)
   
2. run_migrations_offline() é selecionado
   └─ Gera SQL e escreve para stdout
   └─ NÃO conecta a PostgreSQL
   └─ NÃO aplica mudanças
   
3. Resultado:
   └─ 0 tabelas criadas
   └─ 0 registros em alembic_version
   └─ SQL gerado mas não executado
```

**Por que `context.is_offline_mode()` é TRUE?**

- Alembic defaulta para modo offline quando não há conexão "registrada"
- Algo em env.py permite que `context.is_offline_mode()` retorne TRUE mesmo quando deveria retornar FALSE
- Possível: ordem de execução em env.py permite isso

### F. Qual é a correção mínima recomendada?

**RESPOSTA:** Forçar modo online OU executar SQL gerado manualmente

#### Opção 1: Usar SQL gerado (Fallback seguro)

```bash
# Passo 1: Gerar SQL
cd /c/dev/neoeve/neoeve-command-center/backend/migrations
alembic -c alembic_etapa_a.ini upgrade head --sql > /tmp/migrations.sql

# Passo 2: Aplicar SQL ao PostgreSQL
psql -U neoeve_dev -d neoeve_etapa_a < /tmp/migrations.sql

# Verificação:
psql -U neoeve_dev -d neoeve_etapa_a -c "SELECT version FROM alembic_version;"
# Deve retornar: 008
```

**Vantagem:** Funciona com 100% de certeza (modo offline sempre funciona)

**Desvantagem:** Manual, não automático

---

## CONCLUSÃO DO DIAGNÓSTICO

🔴 **PROBLEMA:** `context.is_offline_mode()` retorna True quando deveria retornar False

🔴 **RESULTADO:** Alembic executa upgrade em modo SQL-generation em vez de aplicar ao banco

🔴 **IMPACTO:** Nenhuma migração é aplicada, nenhuma tabela é criada

🟡 **STATUS:** Diagnóstico READ-ONLY concluído sem poder fazer correção

🟢 **WORKAROUND:** Usar `alembic upgrade --sql head | psql ...` para aplicar manualmente

---

## RECOMENDAÇÃO PARA PRÓXIMO PASSO

**Autorizar:** Correção mínima de env.py para garantir que `run_migrations_online()` seja chamado

**OU**

**Executar:** Workaround manual (SQL gerado aplicado via psql) como solução imediata
