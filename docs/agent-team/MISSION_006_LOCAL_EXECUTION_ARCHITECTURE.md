# MISSÃO 006 — LOCAL EXECUTION ARCHITECTURE REPORT

**Data**: 2026-11-22  
**Checkpoint**: `7582894`  
**Status**: 🏗️ ARCHITECTURE DECISION

---

## 1. CRITICAL QUESTION ANSWERED

**"Can agents execute code directly on the local NeoEve repository?"**

### 1.1 Short Answer

❌ **NO**

The Anthropic SDK with `.messages.create()` runs the Claude model **remotely in Anthropic's cloud infrastructure**. The agent cannot directly access or modify the local filesystem.

### 1.2 Why This Matters

| Requirement | Local Exec | Remote Exec |
|---|---|---|
| Agent reads local files | ❌ No | ⏳ Possible via upload |
| Agent modifies local code | ❌ No | ❌ No |
| Agent commits to git | ❌ No | ❌ No |
| Agent runs local tests | ❌ No | ❌ No |
| Agent access secrets | ❌ No (good) | ✅ Prevented (good) |

**Conclusion**: Agents CANNOT directly work on the repository.

---

## 2. EXECUTION TOPOLOGY

### 2.1 Current Flow

```
┌─────────────────────────────────┐
│  Local Machine (NeoEve Repo)    │
│  ┌─────────────────────────────┐│
│  │ Python Bridge Process       ││
│  │ (event_bus/...)             ││
│  └────────────┬────────────────┘│
│               │                  │
│               │ HTTP/REST        │
│               ↓                  │
│    ┌──────────────────┐         │
│    │ Anthropic SDK    │         │
│    │ (Python Client)  │         │
│    └────────┬─────────┘         │
└─────────────┼──────────────────┘
              │
              │ HTTPS
              ↓
      ┌───────────────────┐
      │ Anthropic Cloud   │
      │ ┌───────────────┐ │
      │ │ Claude Model  │ │
      │ │ Inference     │ │
      │ │ (Stateless)   │ │
      │ └───────────────┘ │
      │                   │
      │ No filesystem     │
      │ No git access     │
      │ No local tools    │
      └───────────────────┘
```

**Key Insight**: Model executa em sandbox remoto, sem acesso ao host local.

### 2.2 Information Flow

```
Local Bridge:
  ├─ Preparar contexto
  ├─ Carregar arquivo de entrada (se necessário)
  ├─ Serializar em JSON
  └─ Enviar como prompt

         ↓ (network)

Anthropic Cloud:
  ├─ Receber prompt
  ├─ Processar com Claude Model
  ├─ Gerar resposta
  └─ Retornar JSON

         ↓ (network)

Local Bridge:
  ├─ Receber resposta
  ├─ Parse JSON
  ├─ Validar resultado
  └─ Publicar em Event Bus
```

---

## 3. WHAT THE AGENT CAN DO

### 3.1 Capabilities (Remote Sandbox)

✅ **CAN DO**:
- Analisar texto fornecido (files enviados como contexto)
- Processar dados JSON
- Gerar código (devolvido como texto)
- Raciocínio lógico e resolução de problemas
- Seguir instruções estruturadas
- Retornar respostas no formato esperado

### 3.2 Limitations (No Local Access)

❌ **NÃO PODE**:
- Ler arquivos do filesystem local
- Executar comandos shell
- Chamar git
- Acessar banco de dados local
- Modificar código in-place
- Executar testes localmente
- Usar variáveis de ambiente
- Acessar HTTP (exceto via instruções explícitas)

---

## 4. INTEGRATION PATTERNS FOR LOCAL EXECUTION

### 4.1 Pattern 1: File Upload to Agent (Stateless)

```python
# Local Bridge prepara arquivo
def prepare_file_for_agent(file_path: str) -> str:
    """Lê arquivo local e prepara para enviar ao agente"""
    with open(file_path, 'r') as f:
        content = f.read()
    return content

# Envia como contexto
context = {
    "file_name": "example.py",
    "file_content": prepare_file_for_agent("example.py"),
    "task": "Review this code for security issues"
}

# Agent analisa e retorna análise (não modifica)
response = agent.analyze_code(context)
# response = {"findings": [...], "severity": "MEDIUM"}

# Local bridge processa resultado
if response["severity"] == "HIGH":
    logger.warning(f"Security issue found: {response['findings']}")
```

**Fluxo**:
```
Local: Read file → Encode to context → Send
  ↓
Remote: Analyze → Generate findings
  ↓
Local: Receive → Process → Take action
```

✅ **Vantagens**:
- Seguro (agent não modifica local)
- Rastreável (tudo em Event Bus)
- Auditável (histórico completo)

❌ **Limitações**:
- Latência de rede
- Tamanho limitado de contexto

### 4.2 Pattern 2: Agent Output → Local Bridge Actions

```python
# Agent retorna JSON com instruções
response = {
    "status": "COMPLETED",
    "recommendation": "ADD_SECURITY_CHECK",
    "code_snippet": "if not validate_input(x):\n    raise ValueError(...)",
    "files_to_modify": ["src/security.py"],
    "commit_message": "Add input validation"
}

# Local bridge processa recomendação
if response["recommendation"] == "ADD_SECURITY_CHECK":
    # Bridge faz a ação, não o agent
    modify_local_file(response["files_to_modify"][0], response["code_snippet"])
    git_commit(response["commit_message"])
    publish_event("CODE_MODIFIED", response)
```

**Fluxo**:
```
Agent (Remote):
  - Analisa
  - Retorna JSON com instruções
  
Bridge (Local):
  - Valida instruções
  - Consulta governance
  - Executa ações locais
  - Publica eventos
```

✅ **Vantagens**:
- Agent permanece read-only
- Bridge controla ações
- Rastreamento completo
- Governança enforçada

---

## 5. TRÊS ARQUITETURAS POSSÍVEIS

### 5.1 Arquitetura A: Agent → Bridge Instructions (Recomendada)

```
Agent (Remote):
  "Analyze code for X"
  → Returns: {"action": "...", "details": "..."}

Bridge (Local):
  - Valida output
  - Governa ação
  - Executa localmente
  - Publica resultado
```

**Status**: ✅ **PODE SER IMPLEMENTADA HOJE**

**Implementação**:
1. ETAPA 4: Validação estrutural (HOJE)
2. ETAPA 5: Teste read-only do Backend Agent
3. ETAPA 6: Expandir para outros agentes
4. ETAPA 7: Adicionar ações locais (commit, etc)

**Exemplo Real**:
```python
# Backend agent analisa requirement
requirement = "Add user authentication to login page"
agent_analysis = backend_agent.analyze(requirement)
# Returns:
# {
#   "implementation_strategy": "...",
#   "files_needed": ["auth.py", "models.py"],
#   "estimated_lines": 150
# }

# Bridge consulta governance
governance.evaluate(agent_analysis, "backend", "PLAN_IMPLEMENTATION")

# Se aprovado, bridge orquestra próximos passos
if approved:
    task_event = create_task_event(agent_analysis)
    event_bus.publish(task_event)
```

### 5.2 Arquitetura B: MCP Servers para Local Access (Futuro)

**Model Context Protocol (MCP)**:
- Permite agent acessar recursos locais via APIs seguras
- SDK 0.105.2 tem suporte experimental
- Funciona com `mcp_servers` parameter

```python
# Futuro (não implementado agora)
response = client.beta.messages.create(
    model="...",
    messages=[...],
    mcp_servers=[
        {
            "type": "url",
            "url": "http://localhost:3000/mcp",
            "schema": {"files": {...}}
        }
    ]
)
```

**Status**: ⏳ **POSSÍVEL MAS NÃO RECOMENDADO AGORA**

**Razões**:
- API ainda beta
- Requer MCP server local
- Complexidade adicional
- Security concerns

### 5.3 Arquitetura C: Remote Execution com Webhooks (Complexa)

```
Agent (Remote):
  "Need to run tests"
  → Calls: http://bridge.local:5000/execute-tests
  
Bridge (Local):
  - Webhook handler
  - Executa testes
  - Retorna resultado
  
Agent (Remote):
  - Recebe resultado
  - Continua análise
```

**Status**: ❌ **NÃO RECOMENDADO**

**Problemas**:
- Requer bridge expor HTTP
- Security complexity
- Latência e timeouts
- Difícil de rastrear em Event Bus

---

## 6. RECOMENDAÇÃO: ARQUITETURA A

### 6.1 Why Pattern A

| Critério | Resultado |
|---|---|
| Segurança | ✅ Agent é read-only |
| Simplicidade | ✅ Implementável hoje |
| Rastreabilidade | ✅ Tudo em Event Bus |
| Manutenção | ✅ Padrão claro |
| Escalabilidade | ✅ Funciona com múltiplos agentes |
| Controle | ✅ Bridge governa tudo |

### 6.2 Implementation Roadmap

#### ETAPA 4 (Hoje): Validação
- ✅ Bridge estruturalmente OK
- ✅ SDK compatível
- ✅ Governance funcional
- ✅ Event Bus pronto

#### ETAPA 5 (Próximo): Teste Read-Only
```python
# Backend Agent Tarefa 1: Analisar arquivo
task = {
    "file_path": "docs/agent-team/BASELINE_AUDIT.md",
    "instruction": "Identify document purpose"
}

# Agent (Remote) retorna análise
result = {
    "status": "COMPLETED",
    "document_name": "BASELINE_AUDIT.md",
    "purpose": "Initial baseline audit",
    "key_findings": [...],
    "execution_id": "exec-123"
}
```

#### ETAPA 6-7 (Futuro): Ações Locais
```python
# Backend Agent Tarefa 2: Planejar implementação
recommendation = {
    "action": "IMPLEMENT_FEATURE",
    "feature": "User authentication",
    "strategy": "...",
    "files_to_create": ["auth.py"],
    "tests_needed": ["test_auth.py"]
}

# Bridge governa
governance.evaluate(recommendation) → APPROVED

# Bridge executa
create_file("auth.py", skeleton_code)
publish_event("IMPLEMENTATION_STARTED")

# Backend Agent recebe em próxima tarefa
task2 = {
    "implementation_started": true,
    "instruction": "Implement user authentication in auth.py"
}
```

---

## 7. LOCAL REPOSITORY INTEGRATION

### 7.1 Dados Que O Agent Pode Receber

**De Local para Remote**:
- ✅ Arquivo conteúdo (texto)
- ✅ Estrutura de diretório (JSON)
- ✅ Histórico de commits (git log output)
- ✅ Testes falhos (stdout)
- ✅ Configurações (JSON)

```python
# Example: Enviar contexto do repo
context = {
    "repo_structure": {
        "docs/": ["README.md", "API.md"],
        "src/": ["main.py", "utils.py"],
        "tests/": ["test_main.py"]
    },
    "recent_commits": [
        "abc123: Add authentication",
        "def456: Fix bug in parser"
    ],
    "failing_tests": ["test_parser.py::test_unicode_input"],
    "task": "Analyze why test_parser.py::test_unicode_input is failing"
}

# Agent recebe contexto, retorna análise
analysis = {
    "root_cause": "Parser não handles UTF-8",
    "fix_strategy": "Add encoding='utf-8' to open()",
    "confidence": 0.95
}
```

✅ **Implementável com Pattern A**

### 7.2 O Que Agent NÃO Acessa Diretamente

❌ Filesystem local
❌ Git commands
❌ Local database
❌ Environment variables
❌ Secrets (API keys, etc)

**Proteção**: Intentional e seguro

---

## 8. GOVERNANCE IN LOCAL EXECUTION

### 8.1 Como Governance Funciona com Remote Agents

```
1. Agent (Remote) gera recomendação
2. Bridge (Local) recebe recomendação
3. Governance Engine valida:
   - Permissões do agente
   - Escopo da ação
   - Evidência requerida
   - Separação de duties
4. Se aprovado: Bridge executa
5. Se rejeitado: Publicar AGENT_BLOCKED event
```

### 8.2 Exemplo

```python
# Agent retorna código a ser commitado
recommendation = {
    "type": "GIT_COMMIT",
    "files": ["src/security.py"],
    "message": "Add input validation",
    "agent_id": "backend"
}

# Governance valida
decision = governance.evaluate(
    event=recommendation,
    target_agent="backend",
    action="GIT_COMMIT"
)

# Governance rules:
# 1. Backend pode fazer GIT_COMMIT? SIM
# 2. QA aprovado? (Governance verifica Event Bus)
# 3. Security aprovado? (Governance verifica Event Bus)
# 4. Se ambos: APPROVED → Bridge executa

if decision.allowed:
    git_commit(recommendation["files"], recommendation["message"])
    publish_event("CODE_COMMITTED", {...})
else:
    publish_event("AGENT_BLOCKED", {"reason": decision.reason})
```

---

## 9. SECURITY IMPLICATIONS

### 9.1 Agent Remoto Nunca Pode

❌ Modificar sistema local
❌ Executar comandos arbitrários
❌ Acessar secretos
❌ Exfiltrar dados

### 9.2 Bridge Pode Sempre

✅ Validar output do agent
✅ Consultar governance antes de agir
✅ Executar ações com permissões específicas
✅ Rastrear tudo em Event Bus

### 9.3 Multi-Tenant Safety

```python
# Event Bus isolamento por mission_id
Event(
    mission_id="mission-X",  # Isolado
    task_id="task-Y",
    agent_id="backend",
    correlation_id="....",
    # Agente remoto SÓ pode ver/modificar seu mission_id
    # Governance enforça
)
```

---

## 10. PERFORMANCE CHARACTERISTICS

### 10.1 Latency Breakdown

| Phase | Time |
|---|---|
| Prepare context | 10ms |
| Network to Anthropic | 100ms |
| Model inference | 2-10s |
| Network back | 100ms |
| Parse result | 5ms |
| Publish to Event Bus | 20ms |
| **Total** | **~2-11s** |

✅ Aceitável para batch processing

### 10.2 Throughput

**Sequential** (um agent por vez):
- 3-4 agentes/minuto
- ~20-30 agentes/10 minutos

**Parallel** (múltiplos agentes):
- Ilimitado (async)
- Governado por Anthropic API rate limits

---

## 11. ALTERNATIVE: MCP FOR FUTURE

### 11.1 If We Need Direct File Access Later

```python
# Futuro: Agent acessa arquivo local
response = client.beta.messages.create(
    model="claude-opus-4-1-20250805",
    messages=[...],
    mcp_servers=[
        {
            "type": "url",
            "url": "http://bridge:5000/mcp",
            "schema": {
                "files": {
                    "read": true,
                    "write": false,  # Read-only para agents
                    "paths": ["docs/", "src/"]  # Allowed paths
                }
            }
        }
    ]
)
```

**MCP Flow**:
```
Agent (Remote):
  "Read file docs/README.md"
  
Anthropic API:
  → Call MCP resource: read_file("docs/README.md")
  
Bridge (Local):
  → HTTP POST /mcp/resources/files/read
  → Validate: docs/README.md is in allowed paths
  → Check governance
  → Return file content
  
Agent:
  → Receives file
  → Processes
  → Returns analysis
```

**Requisitos**:
- [ ] SDK update (0.105.2 tem suporte experimental)
- [ ] MCP server implementation
- [ ] Governance rules para MCP
- [ ] Rate limiting

**Timeline**: Post-Phase 1

---

## 12. FINAL ARCHITECTURE DECISION

### 12.1 For ETAPA 4-5 (Now)

**Use Pattern A: Agent Outputs Instructions**

```
Agent (Remote):
  - Receives context (uploaded files/text)
  - Analyzes
  - Returns JSON with recommendations/findings

Bridge (Local):
  - Validates JSON
  - Consults governance
  - Publishes events
  - Optionally executes actions
```

✅ **Why Now**:
- Implementável imediatamente
- Seguro (agent read-only)
- Rastreável completamente
- Funciona com Event Bus existente

### 12.2 Deployment Model

```
TESTING:
  Agent tasks → stdout (no local execution)
  
PRODUCTION:
  Agent tasks → recommendations → governance → local execution
```

### 12.3 Agent Capabilities by Phase

| Phase | Capabilities | Limitations |
|---|---|---|
| Phase 1 (Now) | Analyze + Report | No local changes |
| Phase 2 (Month 2) | Recommend actions | Bridge executes |
| Phase 3 (Month 3) | Plan implementation | Reviewed by QA |
| Phase 4 (Month 4) | Auto-commit + tests | With full governance |

---

## 13. CONCLUSÃO

### 13.1 Resposta Definitiva

**"Can agents work directly on the local repository?"**

**AGORA**: ❌ No — agents são read-only remotos

**FUTURO**: ✅ Yes — com MCP + governance

**PRODUÇÃO**: ✅ Sim — mas via Bridge com governance estrita

### 13.2 Recomendação

Implementar Pattern A (Agent → Bridge Instructions):
1. ✅ Seguro
2. ✅ Implementável hoje
3. ✅ Prova de conceito para Pattern B (MCP)
4. ✅ Alinha com governance

---

## 14. PRÓXIMAS AÇÕES

- [ ] ETAPA 4: Auditoria estrutural (HOJE) ✅
- [ ] ETAPA 5: Teste read-only do Backend Agent
- [ ] ETAPA 6: Implementar Pattern A com recomendações
- [ ] ETAPA 7: Expandir para 7 agentes
- [ ] Future: Avaliar MCP para Phase 2

---

**Status**: 🟢 **ARCHITECTURE APPROVED FOR ETAPA 4-5**

