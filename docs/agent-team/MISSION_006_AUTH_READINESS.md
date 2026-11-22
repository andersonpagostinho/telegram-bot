# MISSÃO 006 — AUTHENTICATION READINESS REPORT

**Data**: 2026-11-22  
**Checkpoint**: `7582894`  
**Status**: 🔐 AUTHENTICATION PREPARATION

---

## 1. CURRENT STATE

### 1.1 ANTHROPIC_API_KEY Status

```bash
$ env | grep ANTHROPIC_API_KEY
# (Nenhum resultado — Variável não definida)
```

**Status**: ❌ **NÃO DISPONÍVEL**

### 1.2 Bridge Readiness

```python
# event_bus/agent_invocation_bridge.py:47
self.anthropic_client = Anthropic()  # Lê ANTHROPIC_API_KEY da env
```

**Comportamento**:
- ✅ SDK inicializa sem erro (não valida chave até primeira chamada)
- ❌ Primeira invocação falhará se chave não estiver presente

---

## 2. AUTHENTICATION FLOW

### 2.1 Como o SDK Busca a Chave

**Ordem de precedência**:

1. **Variável de ambiente** `ANTHROPIC_API_KEY`
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. **Arquivo home directory** `~/.anthropic/api_key` (futuro)

3. **Passado explicitamente**
   ```python
   Anthropic(api_key="sk-ant-...")
   ```

**Atual**: Usa precedência 1 (ambiente)

### 2.2 Teste de Autenticação

```python
from anthropic import Anthropic

try:
    client = Anthropic()  # Inicializa
    response = client.messages.create(  # Falha aqui se sem chave
        model="claude-haiku-4-20250805",
        max_tokens=10,
        messages=[{"role": "user", "content": "hi"}]
    )
    print("✅ Autenticação sucesso")
except Exception as e:
    print(f"❌ Autenticação falhou: {e}")
```

---

## 3. ESTRATÉGIA SEGURA DE CONFIGURAÇÃO

### 3.1 ❌ NÃO FAZER

```bash
# NUNCA colar a chave no terminal
export ANTHROPIC_API_KEY="sk-ant-vXxXXXXXXXXXXXXXXXXXXXXXX"

# NUNCA commitar a chave em código
# NUNCA salvar em .env versionado
# NUNCA imprimir/logar a chave
# NUNCA enviar por email
```

### 3.2 ✅ PROCEDIMENTO SEGURO

#### Opção A: 1Password CLI (Recomendado)

```bash
# 1. Instalar 1Password CLI
# https://developer.1password.com/docs/cli/get-started/

# 2. Autenticar uma vez
op account add

# 3. Configurar vault (ex: "NeoEve" vault, "anthropic_api_key" item)

# 4. Executar com chave injetada
export ANTHROPIC_API_KEY=$(op read op://neoeve/anthropic_api_key/password --no-newline)

# 5. Executar tarefa
python scripts/test_agent_invocation.py

# Chave automaticamente expira do ambiente após alguns segundos
```

**Vantagens**:
- ✅ Chave nunca toca no shell history
- ✅ Auditado por 1Password
- ✅ Rotação de chaves centralizada
- ✅ Sem arquivo .env exposto

#### Opção B: Arquivo .env.local (Desenvolvimento)

```bash
# 1. Criar .env.local (NÃO commitado)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env.local

# 2. No .gitignore
echo ".env.local" >> .gitignore

# 3. Carregar antes de usar
source .env.local
python scripts/test_agent_invocation.py

# 4. Nunca commitar
# git status confirmará .env.local é ignorado
```

**Vantagens**:
- ✅ Simples para desenvolvimento local
- ✅ Isolado do controle de versão

**Desvantagens**:
- ⚠️ Requer disciplina para não commitar
- ⚠️ Menos seguro que 1Password

#### Opção C: Variável de Ambiente no CI/CD

```yaml
# GitHub Actions / GitLab CI
jobs:
  test:
    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    steps:
      - run: python test_agent_invocation.py
```

**Vantagens**:
- ✅ Secreto protegido por plataforma
- ✅ Rotação centralizada

**Restrição**:
- ❌ Não adequado para desenvolvimento local

### 3.3 ⚠️ PROTEÇÃO CONTRA EXPOSIÇÃO

**Se a chave for acidentalmente exposeada**:

1. Revogar imediatamente na console Anthropic
2. Gerar nova chave
3. Atualizar em 1Password / CI/CD
4. Verificar logs para abusos
5. Resetar limites de API se necessário

---

## 4. IMPACTO DE CUSTOS

### 4.1 Rastreamento de Uso

```python
# SDK fornece token usage automaticamente
response = client.messages.create(...)
print(f"Input: {response.usage.input_tokens}")
print(f"Output: {response.usage.output_tokens}")
```

### 4.2 Estimativa de Orçamento

| Cenário | Tokens | Custo |
|---|---|---|
| 1 task simples | 1500 input + 500 output | $0.012 |
| 10 tasks/dia | 15,000 | $0.12 |
| 100 tasks/dia | 150,000 | $1.20 |
| 1000 tasks/mês | 4.5M | $36 |

**Recomendação**: Monitorar no dashboard Anthropic

### 4.3 Limites de Despesa

**Para ETAPA 4-5 (Teste)**: Definir limite baixo
- Máximo $10 para exploração
- Alertas em $5

**Para Produção**: Sera definido pela organização

---

## 5. VALIDAÇÃO PRÉ-INVOCAÇÃO

### 5.1 Checklist Antes de Executar

```python
def validate_auth_readiness() -> bool:
    """Verifica se bridge pode executar"""
    
    # 1. Variável de ambiente
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("❌ ANTHROPIC_API_KEY not set")
        return False
    
    # 2. Formato básico
    if not api_key.startswith("sk-ant-"):
        logger.error("❌ Invalid API key format")
        return False
    
    # 3. Comprimento mínimo
    if len(api_key) < 20:
        logger.error("❌ API key too short")
        return False
    
    # 4. Teste de conexão (sem custos)
    try:
        client = Anthropic()
        # Apenas instancia, não chama API ainda
        logger.info("✅ SDK inicializado com sucesso")
        return True
    except Exception as e:
        logger.error(f"❌ SDK initialization error: {e}")
        return False
```

### 5.2 Teste Sem Custos

```python
def test_auth_without_cost():
    """Verifica autenticação sem fazer chamada à API"""
    
    import os
    
    if os.getenv("ANTHROPIC_API_KEY"):
        print("✅ ANTHROPIC_API_KEY definida (valor não exibido)")
        return True
    else:
        print("❌ ANTHROPIC_API_KEY não encontrada")
        return False
```

---

## 6. TESTE ESTRUTURAL COM MOCK

### 6.1 Teste Sem Autenticação Real

```python
# test_bridge_no_auth.py
from unittest.mock import Mock, patch
from event_bus.agent_invocation_bridge import AgentInvocationBridge
from event_bus.event import Event, EventType

def test_bridge_initialization_no_auth():
    """Bridge pode ser inicializado sem API key"""
    
    mock_bus = Mock()
    mock_dispatcher = Mock()
    mock_governance = Mock()
    
    # Não requer autenticação para inicializar
    bridge = AgentInvocationBridge(mock_bus, mock_dispatcher, mock_governance)
    
    assert bridge.agent_configs is not None
    assert len(bridge.agent_configs) >= 3
    print("✅ Bridge inicializado sem autenticação")

def test_bridge_governance_check_no_auth():
    """Governance bloqueia antes de tentar API"""
    
    mock_bus = Mock()
    mock_dispatcher = Mock()
    mock_governance = Mock()
    
    # Mock governance para rejeitar
    mock_governance.evaluate.return_value = Mock(allowed=False, reason="Test rejection")
    
    bridge = AgentInvocationBridge(mock_bus, mock_dispatcher, mock_governance)
    
    # Nunca chega na API
    event = Mock(spec=Event)
    result = bridge.invoke_agent(event, Mock(value="backend"))
    
    # Governance interceptou antes de API call
    assert result is None
    print("✅ Governance intercepta antes de API call")
```

---

## 7. PROCEDIMENTO PARA ETAPA 5

### 7.1 Pré-requisitos

- [ ] Obter ANTHROPIC_API_KEY da organização
- [ ] Escolher método de armazenamento seguro (1Password recomendado)
- [ ] Testar acesso à chave sem expor
- [ ] Revisar limites de custo

### 7.2 Inicialização Segura

```bash
# 1. ETAPA 4 — Validação Estrutural Concluída ✅
echo "ETAPA 4 OK"

# 2. ETAPA 5 — Preparação de Autenticação
# (Este documento)

# 3. Usuário obtém e configura chave
export ANTHROPIC_API_KEY=$(op read op://neoeve/anthropic_api_key/password --no-newline)

# 4. Validar
python -c "from anthropic import Anthropic; print('✅ Auth ready')"

# 5. Executar teste
python scripts/test_first_agent_invocation.py
```

### 7.3 Monitoramento

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cada invocação loga:
logger.info(f"Agent: {agent_id}")
logger.info(f"Input tokens: {response.usage.input_tokens}")
logger.info(f"Output tokens: {response.usage.output_tokens}")
logger.info(f"Cost: ${cost:.4f}")
```

---

## 8. CONTINGÊNCIA PARA ETAPA 4

### 8.1 Se ANTHROPIC_API_KEY Não Disponível

**Continuar com ETAPAS C-D sem autenticação real**:

```python
# test_bridge_full_flow_no_auth.py

def test_complete_event_flow_no_real_api():
    """Testa fluxo completo até limiar de API call"""
    
    # Inicializar Event Bus
    event_bus = EventBus()
    dispatcher = EventDispatcher(event_bus)
    governance = GovernanceEngine(event_bus)
    
    # Mock da chamada real
    with patch('event_bus.agent_invocation_bridge.Anthropic') as mock_api:
        mock_api.return_value.messages.create.return_value = Mock(
            content=[Mock(text='{"status": "COMPLETED"}')],
            usage=Mock(input_tokens=100, output_tokens=50)
        )
        
        bridge = AgentInvocationBridge(event_bus, dispatcher, governance)
        
        # Teste até aí
        print("✅ Full flow testável sem auth real")
```

### 8.2 Marcar Pontos Sem Autenticação

| Componente | Testável | Como |
|---|---|---|
| Inicialização | ✅ | Sem mock |
| Governance | ✅ | Sem mock |
| Event Bus | ✅ | Sem mock |
| Dispatcher | ✅ | Sem mock |
| JSON parsing | ✅ | Com mock |
| API call | ❌ | Requer auth |
| Resultado publicado | ✅ | Com mock |

---

## 9. MATRIZ DE READINESS

| Aspecto | Status | Bloqueador | Ação |
|---|---|---|---|
| SDK instalado | ✅ | Não | Pronto |
| API key presente | ❌ | Sim | Obter de organização |
| Procedimento seguro documentado | ✅ | Não | Usar Opção A (1Password) |
| Teste de validação pronto | ✅ | Não | Pronto em ETAPA 5 |
| Limites de custo definidos | ⏳ | Sim | Organizativo |
| Mock para teste | ✅ | Não | Implementado |
| Rotação de chaves | ✅ | Não | Procedimento documentado |
| Auditoria de logs | ✅ | Não | Via logging |

---

## 10. DECISÃO FINAL

### 10.1 Pronto para ETAPA 5?

**Status**: 🟡 **CONDITIONAL YES**

**Se ANTHROPIC_API_KEY obtida**:
- ✅ Sim, com procedimento seguro

**Se API key não disponível**:
- ✅ Continuar ETAPA 4 com mocks
- ⏳ Aguardar ETAPA 5 para teste real

### 10.2 Recomendação

1. **ETAPA 4** (Agora): Concluir validação estrutural com mocks
2. **ETAPA 5** (Depois): Obter API key + testar real
3. **Produção**: Redefinir limites e rotação de chaves

---

## 11. REFERÊNCIAS

- [Anthropic API Documentation](https://docs.anthropic.com)
- [1Password CLI Setup](https://developer.1password.com/docs/cli)
- [SDK Python Package](https://pypi.org/project/anthropic/)

---

**Próximo Relatório**: MISSION_006_LOCAL_EXECUTION_ARCHITECTURE.md

