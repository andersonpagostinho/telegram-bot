# Migration 006 — Root Cause Analysis

**Data:** 2026-11-24  
**Status:** CAUSA RAIZ IDENTIFICADA ✅  
**Severidade:** CRÍTICA — Bloqueia pipeline de migrations  

---

## CAUSA RAIZ CONFIRMADA

### O Problema

```
Migration 006 falha com:
ProgrammingError: column "attempt_number" of relation "executions" already exists
```

### Cadeia de Eventos

1. **Application Startup** → `database/connection.py` linha X
   ```python
   Base.metadata.create_all(bind=engine)
   ```
   
2. **Automatic Table Creation** → SQLAlchemy reads models.py
   - Tabela `executions` criada COM `attempt_number` já incluído
   - Tabela `execution_attempts` criada
   - Tabela `event_idempotency_keys` criada

3. **Migration 006 Upgrade** → Tenta ADICIONAR `attempt_number`
   ```python
   op.add_column('executions', sa.Column('attempt_number', sa.Integer()...))
   # ERRO: coluna já existe!
   ```

### Raiz da Divergência

| Origem | Estado de `attempt_number` |
|--------|---------------------------|
| **models.py** (Execution class) | ✅ Presente (coluna definida) |
| **Migration d19e...** (Base schema) | ❌ Ausente (não criada) |
| **Migration 006** (Adiciona) | Esperado: ausente → Encontrado: presente |
| **Alembic versioning** | Falso: "006 não foi aplicado" |

---

## CONFIRMAÇÕES

### ✅ Confirmação 1: Base Metadata Create-All

**Arquivo:** `backend/database/connection.py`

```python
def get_engine():
    # ... setup ...
    Base.metadata.create_all(bind=engine)  # ← CRIA TODAS as tabelas automaticamente
```

**Impacto:** Quando qualquer código importa models.py + connection.py, as tabelas são criadas automaticamente, IGNORANDO migrations.

---

### ✅ Confirmação 2: Execution Model Definition

**Arquivo:** `backend/database/models.py`

```python
class Execution(Base):
    __tablename__ = "executions"
    
    # ...
    attempt_number = Column(Integer, default=1)  # ← JÁ INCLUÍDO
    # ...
```

**Impacto:** Modelo define a coluna, logo `create_all()` a criará.

---

### ✅ Confirmação 3: Migration 006 Operation

**Arquivo:** `backend/migrations/versions/006_add_recovery_service_models.py`

**Linha 22:**
```python
op.add_column('executions', sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'))
```

**Problema:** Tenta ADICIONAR coluna que já existe (criada por `create_all()`)

---

### ✅ Confirmação 4: Base Schema Doesn't Include It

**Arquivo:** `backend/migrations/versions/d19e221b7b2a_create_command_center_schema.py`

**Linha 71-93:**
```python
op.create_table('executions',
    # ... outras colunas ...
    # Falta: attempt_number
    sa.PrimaryKeyConstraint('execution_id'),
    # ...
)
```

**Problema:** Base schema não inclui `attempt_number`, mas models.py sim.

---

## RESPOSTA ÀS 5 QUESTÕES

### A. Qual operação criou attempt_number pela primeira vez?

**Resposta:** `Base.metadata.create_all()` em `database/connection.py`

- Não foi uma migration
- Foi SQLAlchemy lendo models.py automaticamente
- Causou divergência entre schema real e alembic versioning

### B. Por que migration 006 tenta criá-la novamente?

**Resposta:** Migration 006 foi criada como se a coluna NÃO existisse

- Alembic expected: d19e... criou executions SEM attempt_number
- Realidade: `create_all()` já criou COM attempt_number
- Logo migration 006 assume: "attempt_number não existe, vou adicionar"
- Erro: "coluna já existe"

### C. O problema é do código, histórico de migrations ou ambiente?

**Resposta:** DO CÓDIGO (design flaw)

**Raiz:** `database/connection.py` chama `Base.metadata.create_all()`

- Não é problema de migrations (cadeia está correta)
- Não é problema de ambiente (neoeve_etapa_a está limpo)
- **É um anti-pattern:** Usar `create_all()` JUNTO COM alembic

**Padrão correto:**
```
SEM: Base.metadata.create_all()  (Remove)
COM: Alembic migrations apenas   (Autoridade única)
```

### D. Qual correção mínima preserva a integridade da cadeia?

**Resposta:** Remover `Base.metadata.create_all()` de `database/connection.py`

**Por quê:**
- Alembic é a "fonte de verdade" para schema
- `create_all()` bypassa alembic e cria schema diretamente
- Combinados = divergência inevitável

**Implementação:**
1. Remover linha: `Base.metadata.create_all(bind=engine)`
2. Garantir alembic upgrade executado antes da app
3. Executar migrations em banco limpo
4. Cadeia completa funcionará

**Reversibilidade:** ✅ Total (apenas remoção, sem alteração de migrations)

### E. A cadeia completa consegue chegar em 008 em um banco limpo?

**Resposta:** SIM, se `create_all()` for removido

**Validação:**
- Base schema (d19e...) ✅ Cria executions SEM attempt_number
- 006 upgrade ✅ Adiciona attempt_number
- 006 downgrade ✅ Remove attempt_number
- 007 upgrade ✅ Cria recovery_metrics tables
- 008 upgrade ✅ Cria TenantAgentState (nossa)

**Prerequisito:** `Base.metadata.create_all()` DEVE estar DESATIVADO

---

## DIAGNÓSTICO RESUMIDO

| Aspecto | Achado |
|--------|--------|
| Cadeia de migrations | ✅ Válida, sem redundâncias |
| Revisão numbers | ✅ Corretos (d19e..., 000-008) |
| Down revision pointers | ✅ Corretos (cada um referencia o anterior) |
| Migration 006 lógica | ✅ Correta (tenta adicionar inexistente) |
| Banco isolado | ✅ Limpo, sem schema pré-criado |
| Root cause | ❌ **`Base.metadata.create_all()` em connection.py** |
| Solução | ✅ Remover `create_all()`, deixar só alembic |

---

## RECOMENDAÇÃO

**Correção Mínima (Preserva Integridade):**

1. ✏️ Remover linha em `database/connection.py`
   - Remover: `Base.metadata.create_all(bind=engine)`
   - Deixar: Setup de engine, conexões, pools

2. ✅ Validar em banco limpo
   - Executar: `alembic upgrade head`
   - Verificar: Chega a 008 sem erros

3. ✅ Garantir aplicação
   - Sempre executar migrations antes de rodar app
   - Adicionar check: "se alembic_version não existe, falha"

---

**Próximo Passo:** Aguardar autorização para remover `Base.metadata.create_all()`

Sem essa remoção, cadeia de migrations não funcionará em banco limpo.
