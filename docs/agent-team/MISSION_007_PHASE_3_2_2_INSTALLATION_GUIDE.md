# MISSÃO 007 FASE 3.2.2 — POSTGRESQL WINDOWS INSTALLATION GUIDE

**Data**: 2026-11-22  
**Status**: 🟡 **PENDENDO INSTALAÇÃO MANUAL DO USUÁRIO**  
**Checkpoint**: `dbdd87d`

---

## ✅ PRÉ-REQUISITOS VALIDADOS

```
✅ Windows 11 Pro (10.0.26200)
✅ Portas 5432 e 5433 livres
✅ Sem PostgreSQL anterior instalado
✅ Privilégios administrativos (necessário para instalar)
```

---

## 📥 PASSO 1: DOWNLOAD

Acesse a URL oficial:

```
https://www.postgresql.org/download/windows/
```

**Clique em**: "Download the installer"

**Escolha**: PostgreSQL 16.x (latest)

**Salve em**: `C:\Users\ANDERSON\Downloads\postgresql-16-windows-x64.exe`

---

## 🚀 PASSO 2: EXECUTE O INSTALADOR

1. **Clique duplo** em `postgresql-16-windows-x64.exe`
2. **Autorize** a alteração do sistema (clique "Sim")

---

## ⚙️ PASSO 3: WIZARD — CONFIGURAÇÃO

### Setup Wizard

**Página 1: Welcome**
- Clique: **Next**

**Página 2: Installation Directory**
- Aceite o padrão: `C:\Program Files\PostgreSQL\16`
- Clique: **Next**

**Página 3: Select Components**
- ✅ PostgreSQL Server
- ✅ pgAdmin 4
- ✅ Stack Builder
- ✅ Command Line Tools
- Clique: **Next**

**Página 4: Data Directory**
- Aceite o padrão: `C:\Program Files\PostgreSQL\16\data`
- Clique: **Next**

**Página 5: Password**
- **IMPORTANTE**: Defina uma senha **segura e memorável** para o usuário `postgres`
- Repita a senha
- Clique: **Next**

**Página 6: Port**
- Aceite o padrão: **5432**
- Clique: **Next**

**Página 7: Locale**
- Aceite o padrão: **[Default locale]**
- Clique: **Next**

**Página 8: Pre Installation Summary**
- Revise as configurações
- Clique: **Next**

**Página 9: Installation**
- Aguarde até 2-3 minutos
- Progresso será mostrado

**Página 10: Completing Setup**
- ✅ Marque: "Launch Stack Builder now?"
- Clique: **Finish**

---

## 📋 PASSO 4: STACK BUILDER (Opcional)

Pode aparecer uma janela "Stack Builder". Você pode:
- **Fechar** a janela (clique X)
- Ou clicar "Skip"

Não precisa instalar componentes adicionais para esta etapa.

---

## ✔️ VALIDAÇÃO PÓS-INSTALAÇÃO

Após o wizard terminar:

1. **Abra PowerShell** (clique direito, "Open in Windows Terminal")

2. **Execute este comando**:
   ```powershell
   psql --version
   ```

3. **Resultado esperado**:
   ```
   psql (PostgreSQL) 16.x
   ```

Se ver "psql is not recognized", a instalação falhou. Repita os passos.

---

## 🔧 PASSO 5: CRIAR BANCO DE DESENVOLVIMENTO

1. **Abra a linha de comando do PostgreSQL**:
   
   ```powershell
   # Conectar como postgres (super-user)
   psql -U postgres
   ```

2. **Será solicitada a senha**: Digite a senha que definiu na Página 5

3. **Você verá o prompt**: `postgres=#`

4. **Crie o banco**:
   ```sql
   CREATE DATABASE neoeve_command_center;
   ```

5. **Crie um usuário de desenvolvimento**:
   ```sql
   CREATE USER neoeve_dev WITH PASSWORD 'neoeve_dev_123';
   ```

6. **Conceda permissões**:
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE neoeve_command_center TO neoeve_dev;
   ```

7. **Saia**:
   ```
   \q
   ```

---

## 📝 INFORMAÇÕES PARA PRÓXIMO PASSO

Anote estas informações:

```
Host: localhost
Port: 5432
Database: neoeve_command_center
User: neoeve_dev
Password: neoeve_dev_123
Connection String: postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center
```

**⚠️ IMPORTANTE**: Não compartilhe a senha com ninguém. Remova este documento após anotar.

---

## ✅ CONCLUSÃO

Após completar estes passos:

1. PostgreSQL 16 estará instalado e rodando
2. Banco `neoeve_command_center` criado
3. Usuário `neoeve_dev` configurado
4. Pronto para a próxima etapa

**Volta aqui após completar a instalação e validação!**

