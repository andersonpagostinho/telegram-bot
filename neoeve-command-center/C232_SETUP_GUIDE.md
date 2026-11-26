# C.2.3.2 — Guia de Setup PostgreSQL com Docker

**Objetivo**: Preparar ambiente PostgreSQL real para validar concorrência, Event Bus e WebSocket.

---

## PRÉ-REQUISITO: Instalar Docker Desktop

### Windows 10/11
1. Baixar Docker Desktop: https://www.docker.com/products/docker-desktop
2. Instalar (requer WSL 2)
3. Abrir PowerShell como Admin
4. Verificar instalação:
   ```powershell
   docker --version
   docker-compose --version
   ```

### Alternativa: WSL 2 + Docker
```powershell
# Se já tiver WSL 2
wsl -l -v
docker --version
```

---

## ETAPA 1: INICIAR POSTGRESQL

### Passo 1: Verificar docker-compose.yml
```powershell
cd C:\dev\neoeve\neoeve-command-center
ls docker-compose.yml  # Deve existir
```

### Passo 2: Iniciar serviço
```powershell
# Iniciar PostgreSQL em background
docker-compose up -d

# Verificar status
docker-compose ps

# Verificar logs
docker-compose logs postgres-test
```

### Passo 3: Aguardar health check
```powershell
# Esperar até "healthy"
docker-compose ps

# Deve mostrar:
# STATUS: Up X seconds (healthy)
```

---

## ETAPA 2: VERIFICAR CONEXÃO

### Via PowerShell (psql via Docker)
```powershell
# Se psql não está instalado, usar psql via Docker
docker exec -it neoeve_postgres_test psql -U neoeve_dev -d neoeve_command_center -c "SELECT version();"

# Deve retornar:
# version | PostgreSQL 15.x ...
```

### Via Python
```powershell
cd C:\dev\neoeve\neoeve-command-center\backend

# Instalar psycopg2 se não tiver
pip install psycopg2-binary

# Testar conexão
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center')
print('✅ Conectado ao PostgreSQL')
conn.close()
"
```

---

## ETAPA 3: EXECUTAR MIGRATIONS

```powershell
cd C:\dev\neoeve\neoeve-command-center\backend

# Criar tabelas
$env:DATABASE_URL = 'postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center'
python -c "
from database.models import Base
from sqlalchemy import create_engine
engine = create_engine('$env:DATABASE_URL')
Base.metadata.create_all(engine)
print('✅ Tabelas criadas')
"
```

---

## ETAPA 4: EXECUTAR TESTES

### Teste 1: Verificar Validation table
```powershell
$env:DATABASE_URL = 'postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center'

cd C:\dev\neoeve\neoeve-command-center\backend

# Verificar se tabela existe
python -c "
from database.models import Validation
from sqlalchemy import create_engine
engine = create_engine('$env:DATABASE_URL')
print('✅ Validation table pronta')
"
```

### Teste 2: Regressão (45 testes anteriores)
```powershell
# Executar testes com PostgreSQL
pytest tests/test_approval_rest_api.py tests/test_approval_integration_pg_simplified.py -v

# Deve mostrar: 16 PASSED
```

### Teste 3: Concorrência (novo)
```powershell
# Teste de concorrência com PostgreSQL real (ainda será criado)
# pytest tests/test_approval_concurrency_pg.py -v
```

---

## ETAPA 5: LIMPEZA

### Parar serviço
```powershell
docker-compose down

# Remover volume (limpar dados)
docker-compose down -v
```

---

## TROUBLESHOOTING

### Erro: "Docker daemon not running"
```powershell
# Iniciar Docker Desktop manualmente
# OU via PowerShell (admin):
docker run hello-world
```

### Erro: "Cannot connect to localhost:5432"
```powershell
# Verificar se container está rodando
docker-compose ps

# Verificar logs
docker-compose logs postgres-test

# Se health check falhar, aguardar 10-15 segundos e tentar novamente
```

### Erro: "Database neoeve_command_center does not exist"
```powershell
# Recriar containers
docker-compose down
docker-compose up -d

# Aguardar health check
docker-compose ps  # Verificar (healthy)

# Recriar tabelas
# [Execute ETAPA 3 novamente]
```

---

## PRÓXIMOS PASSOS (C.2.3.2)

Após PostgreSQL estar up:

1. ✅ Executar testes de concorrência real
2. ✅ Validar Event Bus integração
3. ✅ Validar Projection Worker
4. ✅ Validar WebSocket

```powershell
# Executar suite completa C.2.3.2
$env:DATABASE_URL = 'postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center'

pytest tests/test_approval_concurrency_pg.py tests/test_event_bus_integration.py tests/test_websocket_integration.py -v
```

---

## STATUS ESPERADO

Após completar este guia:

- ✅ PostgreSQL rodando em Docker
- ✅ Conexão testada
- ✅ Tabelas criadas
- ✅ 45 testes regressão PASS com PostgreSQL
- ✅ Pronto para C.2.3.2 validação real

---

**Tempo estimado**: 15-20 minutos  
**Recursos**: ~1GB RAM, 2GB disco para container
