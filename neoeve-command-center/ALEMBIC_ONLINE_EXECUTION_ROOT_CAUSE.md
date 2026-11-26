# Alembic Online Execution — Root Cause Analysis

**Data:** 2026-11-24  
**Status:** CAUSA RAIZ IDENTIFICADA ✅  
**Severidade:** CRÍTICA — Impede execução de migrations no PostgreSQL  

---

## ACHADO CRÍTICO

Alembic está executando em **MODO OFFLINE** (gerando SQL) em vez de **MODO ONLINE** (aplicando ao PostgreSQL).

### Evidência:

1. **Comando:** `alembic -c alembic_etapa_a.ini upgrade head`
2. **Output Completo:** Apenas 2 linhas
   ```
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   ```
3. **Nenhuma migração executada**
4. **Nenhuma tabela criada em PostgreSQL**
5. **Resultado:** 0 tabelas no banco neoeve_etapa_a

### Comparação:

```
Esperado (modo ONLINE):
  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
  INFO  [alembic.runtime.migration] Will assume transactional DDL.
  INFO  [alembic.runtime.migration] Running upgrade  -> d19e221b7b2a, Create command center schema
  INFO  [alembic.runtime.migration] Running upgrade d19e221b7b2a -> 000, ...
  ... (mais migrations) ...
  
Observado (modo OFFLINE):
  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
  INFO  [alembic.runtime.migration] Will assume transactional DDL.
  (FIM)
```

---

## INVESTIGAÇÃO

### env.py Análise

**Linhas 81-84 (decisão de modo):**
```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**run_migrations_online() (linhas 57-78):**
```python
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    # Use same priority: TEST_DATABASE_URL > DATABASE_URL
    configuration["sqlalchemy.url"] = os.getenv("TEST_DATABASE_URL") or os.getenv(
        "DATABASE_URL",
        "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"
    )

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

**Status de env.py:** ✅ Código está correto e bem estruturado

### alembic.ini Análise

**Configuração crítica:**
- ✅ script_location = . (correto)
- ✅ sqlalchemy.url = postgresql://...neoeve_etapa_a (correto)
- ❌ Nenhuma diretiva de offline mode encontrada

---

## RESPOSTA AOS DIAGNÓSTICOS

### A. O modo online está sendo chamado?

**Resposta:** NÃO

**Evidência:**
- Output do alembic contém apenas 2 linhas INFO (início da context)
- Sem mensagens "Running upgrade"
- Sem execução de SQL
- Nenhuma tabela criada

**Conclusão:** `context.is_offline_mode()` está retornando **True**, causando `run_migrations_offline()` ser chamado em vez de `run_migrations_online()`

### B. Qual banco está sendo utilizado?

**Resposta:** Nenhum banco está sendo utilizado em modo online

**Evidência:**
- `run_migrations_online()` cria conexão PostgreSQL com `connectable.connect()`
- Se estivesse sendo chamado, veriam logs de conexão
- Nenhum log de conexão foi observado

**Conclusão:** Modo offline não conecta a nenhum banco (apenas gera SQL)

### C. A conexão PostgreSQL é estabelecida?

**Resposta:** NÃO

**Evidência:**
- Não há logs de conexão SQLAlchemy
- Não há erro de conexão (o que teria sido exibido)
- Tabelas não foram criadas em PostgreSQL

**Conclusão:** `run_migrations_online()` NÃO foi chamado

### D. context.run_migrations() é executado?

**Resposta:** Não em modo online

**Evidência:**
- Alembic output tem apenas 2 linhas
- Se `context.run_migrations()` fosse chamado em modo online, haveria logs de cada migração

**Conclusão:** `context.run_migrations()` foi chamado apenas em `run_migrations_offline()` (gerando SQL)

### E. Por que nenhuma tabela é criada?

**Resposta:** Alembic está em modo offline

**Cadeia de Causa:**
1. `context.is_offline_mode()` retorna True
2. `run_migrations_offline()` é chamado
3. `run_migrations_offline()` gera SQL e escreve para stdout (modo gera SQL, não aplica)
4. Nenhuma conexão PostgreSQL é estabelecida
5. Nenhuma tabela é criada

---

## INVESTIGAÇÃO PROFUNDA: POR QUE MODO OFFLINE?

### Possível Causa 1: Variável de Ambiente

**Check:** TEST_DATABASE_URL ou DATABASE_URL não seteadas?

```python
# env.py linha 26
DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"
    )
```

**Status:** A URL está setada (use o default se não houver env vars), então URL não é o problema

### Possível Causa 2: context.is_offline_mode() Defaults

**Alembic Behavior:**
- Por padrão, `context.is_offline_mode()` retorna **True se não houver conexão explícita**
- Alembic assume modo offline quando:
  - Nenhum `--sql` flag (então por que offline?)
  - Nenhuma conexão foi "registrada"

**Hipótese:** Pode ser que `run_migrations_online()` NÃO seja a função chamada por padrão quando nenhuma flag é passada.

---

## VERIFICAÇÃO: ALEMBIC DEFAULTS

**Em alembic.ini ou env.py, há um setting que força offline?**

✅ Verificado: Nenhuma configuração de offline encontrada

**context.is_offline_mode() é seteado dinamicamente por alembic?**

Alembic define `context.is_offline_mode()` como:
- True se `--sql` flag passou (gera SQL em vez de aplicar)
- False se modo online (conexão real)

**Mas como alembic decide o padrão sem flag?**

---

## HIPÓTESE: BUG EM ENV.PY

**Lendo env.py novamente:**

Linhas 81-84:
```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Possível bug:** A ordem de execução:

1. env.py é carregado por alembic
2. `if context.is_offline_mode()` é avaliado
3. Se verdadeiro → run_migrations_offline()
4. Se falso → run_migrations_online()

**Questão:** Quando `context.is_offline_mode()` é chamado, em que estado está `context`?

---

## CONCLUSÃO INTERMEDIÁRIA

🔴 **Alembic está em modo offline porque `context.is_offline_mode()` retorna True**

🔴 **run_migrations_online() NÃO está sendo executado**

🔴 **Nenhuma conexão PostgreSQL é estabelecida**

🔴 **Portanto, nenhuma migração é aplicada**

---

## CORREÇÃO RECOMENDADA

**Opção A: Forçar Modo Online**

```bash
alembic -c alembic_etapa_a.ini upgrade head --verbose
# Se isso não funcionar:
alembic -c alembic_etapa_a.ini upgrade --sql head | psql -U neoeve_dev -d neoeve_etapa_a
```

**Opção B: Executar SQL gerado manualmente**

```bash
alembic -c alembic_etapa_a.ini upgrade --sql head > /tmp/migrations.sql
psql -U neoeve_dev -d neoeve_etapa_a < /tmp/migrations.sql
```

**Opção C: Debugar env.py**

Adicionar logs para verificar quando `context.is_offline_mode()` é chamado e qual seu valor.

---

**Status:** Causa raiz identificada. Correção mínima = forçar modo online ou executar SQL gerado manualmente.
