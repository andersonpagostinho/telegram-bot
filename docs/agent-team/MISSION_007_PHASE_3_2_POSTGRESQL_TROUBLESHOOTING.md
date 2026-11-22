# POSTGRESQL TROUBLESHOOTING — ETAPA 3.2

**Data**: 2026-11-22  
**Erro**: Authentication failed for user "neoeve_dev"

---

## 🔴 PROBLEMA

```
sqlalchemy.exc.OperationalError: connection failed
FATAL: autenticação do tipo senha falhou para o usuário "neoeve_dev"
```

---

## ✅ VERIFICAÇÃO NECESSÁRIA

Você mencionou que PostgreSQL estava "autenticado", mas a migração Alembic não consegue conectar.

**Preciso confirmar o estado do banco:**

### **Passo 1: Verificar banco e usuário**

Abra PowerShell como Admin e execute:

```powershell
$env:PGPASSWORD="<SENHA-QUE-USOU-NA-INSTALACAO>"
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -c "\l"
```

**Esperado**: Ver lista de bancos

Se der erro, a senha do postgres está errada.

---

### **Passo 2: Listar usuários**

```powershell
$env:PGPASSWORD="<SENHA-POSTGRES>"
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -c "\du"
```

**Esperado**: Ver lista de usuários incluindo `neoeve_dev`

Se `neoeve_dev` não aparecer, precisa ser criado.

---

### **Passo 3: Testar conexão com neoeve_dev**

```powershell
$env:PGPASSWORD="neoeve_dev_123"
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U neoeve_dev -h localhost -d neoeve_command_center -c "SELECT 1 as ok;"
```

**Esperado**: Ver `ok` = 1

Se der erro de autenticação, a senha está errada ou usuário não existe.

---

## 🔧 POSSÍVEIS SOLUÇÕES

### **Solução A: Recriar banco e usuário**

Como postgres (super-user):

```sql
-- Terminar conexões existentes
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'neoeve_command_center'
AND pid <> pg_backend_pid();

-- Dropar banco
DROP DATABASE IF EXISTS neoeve_command_center;

-- Criar banco
CREATE DATABASE neoeve_command_center;

-- Dropar usuário se existe
DROP USER IF EXISTS neoeve_dev;

-- Criar usuário
CREATE USER neoeve_dev WITH PASSWORD 'neoeve_dev_123';

-- Conceder permissões
GRANT ALL PRIVILEGES ON DATABASE neoeve_command_center TO neoeve_dev;
GRANT USAGE ON SCHEMA public TO neoeve_dev;
GRANT CREATE ON SCHEMA public TO neoeve_dev;

-- Verificar
\l
\du
```

---

### **Solução B: Usar usuário postgres diretamente**

Se preferir não reconfigurara, use credenciais do postgres:

```
Host: localhost
Port: 5432
User: postgres
Password: <SENHA-USADA-NA-INSTALACAO>
Database: neoeve_command_center (ou qualquer outro)
```

---

## 📝 INFORMAÇÕES NECESSÁRIAS

Para que eu continue:

1. **Qual foi a senha que você usou na instalação do PostgreSQL?**
   - Precisarei dessa para conectar como `postgres`

2. **O banco `neoeve_command_center` foi criado?**
   - Verifique: `\l` no psql

3. **O usuário `neoeve_dev` foi criado?**
   - Verifique: `\du` no psql

4. **Qual senha quer usar para `neoeve_dev`?**
   - Padrão: `neoeve_dev_123`
   - Ou pode ser outra

---

## 🎯 PRÓXIMA AÇÃO

Execute os passos de **VERIFICAÇÃO NECESSÁRIA** acima e volte com:

1. Resultado de `\l` (lista de bancos)
2. Resultado de `\du` (lista de usuários)
3. Confirmação se `neoeve_command_center` existe
4. Confirmação se `neoeve_dev` existe

Assim posso proceder com as migrations corretamente.

