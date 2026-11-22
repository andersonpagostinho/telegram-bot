# MISSÃO 006-R1 — RUNTIME AUDIT

**Data**: 2026-11-22  
**Objetivo**: Mapear dependências e pontos de integração para migração para Claude Subscription  
**Status**: 🔍 **ETAPA 1 COMPLETA**

---

## 1. ESCOPO DE AUDITORIA

### 1.1 Componentes Auditados

✅ Arquivos inspecionados:
- `event_bus/agent_invocation_bridge.py` (312 linhas)
- `event_bus/dispatcher.py` (187 linhas)  
- `event_bus/governance.py` (260 linhas)
- `event_bus/event_bus.py` (123 linhas)
- `event_bus/agent_handlers.py` (436 linhas)
- `requirements.txt` (66 linhas)

**Total**: ~1.4k linhas auditadas

---

## 2. PONTOS CRÍTICOS IDENTIFICADOS

### 2.1 Dependência do Anthropic SDK

**Localização**: `event_bus/agent_invocation_bridge.py`

| Linha | Código | Propósito |
|---|---|---|
| 10 | `from anthropic import Anthropic` | Import SDK |
| 47 | `self.anthropic_client = Anthropic()` | Inicialização |
| 259 | `response = self.anthropic_client.messages.create(...)` | Execução principal |

### 2.2 Fluxo de Execução via SDK

```
Bridge.invoke_agent()
  ↓
_validate_target()
  ↓
governance.evaluate()
  ↓
_prepare_context()
  ↓
_execute_via_anthropic() ← AQUI ESTÁ O PONTO DE INTEGRAÇÃO
  ├─ Build messages (system_prompt + task)
  ├─ Call anthropic_client.messages.create()  ← CHAMADA À API
  ├─ Parse JSON response
  └─ Return structured result
  ↓
publish(result_event) → Event Bus
```

### 2.3 Contrato de Execução (Preservado)

```python
Input:
  - event: Event (task + context)
  - target_agent: AgentRole
  - task_description: str
  - config: AgentConfig (system_prompt, tools, timeout)

Processing:
  - Governance authorization
  - Context preparation
  - System prompt + task delivery
  - Tool authorization

Output:
  - result_json: Dict (status, result, metadata)
  - Published to Event Bus with causation chain
  - Duration, tokens, execution_id tracked
```

**Crítico**: Este contrato DEVE ser preservado

---

## 3. CONFIGURAÇÃO DE AGENTES

### 3.1 Registrados

| Agente | Role | Tools | Timeout | Max Tokens |
|---|---|---|---|---|
| Backend | BACKEND | read, write, test, git | 300s | 2000 |
| QA | QA | read, test | 180s | 1500 |
| Security | SECURITY | read | 180s | 1500 |

### 3.2 Não Implementados (Esperados)

| Agente | Role | Status |
|---|---|---|
| Architect | ARCHITECT | — |
| Debugger | DEBUGGER | — |
| Release Manager | RELEASE | — |
| OpenAI Validator | VALIDATOR | Separado (não Claude) |

**Total esperado para NeoEve**: 7 agentes

---

## 4. DEPENDÊNCIAS

### 4.1 SDK Anthropic

```
Versão: 0.105.2
Localização: requirements.txt (linha 4)
Uso: Apenas em agent_invocation_bridge.py
Alternativa possível: Claude Code CLI
```

### 4.2 Autenticação Atual

```
Método: ANTHROPIC_API_KEY (variável de ambiente)
Carregamento: Automático em Anthropic()
Faturamento: Pagamento por API
```

### 4.3 Resposta Esperada

```json
{
  "id": "msg-...",
  "content": [
    {
      "type": "text",
      "text": "{...JSON...}"
    }
  ],
  "usage": {
    "input_tokens": N,
    "output_tokens": N
  }
}
```

---

## 5. GOVERNANÇA E EVENT BUS

### 5.1 Pontos de Integração

```
invoke_agent()
  ├─ Governance.evaluate() — BLOQUEADOR (nenhuma mudança)
  ├─ Event Bus.publish() — PERSISTÊNCIA (nenhuma mudança)
  ├─ Event Bus.mark_completed() — LOGGING (nenhuma mudança)
  └─ Event Bus.mark_failed() — ERROR LOGGING (nenhuma mudança)
```

**Conclusão**: Governance e Event Bus são INDEPENDENTES do runtime

### 5.2 Correlação de Eventos

```python
Event(
  correlation_id=event.correlation_id,  # Cadeia preservada
  causation_id=event.event_id,          # Rastreamento
  ...
)
```

**Conclusão**: Correlação funciona com qualquer runtime

---

## 6. FLUXO DE DADOS SENSÍVEIS

### 6.1 System Prompt

```python
# Armazenado em AgentConfig
system_prompt = """You are a Backend Developer agent.
...
Format your response as JSON: {...}"""
```

**Sensibilidade**: Baixa (definido localmente)

### 6.2 Contexto da Tarefa

```python
context = {
    "task_id": event.task_id,
    "mission_id": event.mission_id,
    "task_payload": event.payload,
    "timestamp": ...,
    "execution_id": ...
}
```

**Sensibilidade**: Baixa (dados da aplicação)

### 6.3 Resultado da Tarefa

```python
result_json = {
    "status": "COMPLETED",
    "result": {...},
    "execution_id": "...",
    "duration_seconds": N
}
```

**Sensibilidade**: Baixa (resultado estruturado)

---

## 7. PONTOS DE FALHA ATUAIS

### 7.1 Sem ANTHROPIC_API_KEY

```
Current: Anthropic() lê de env
Result: 401 Unauthorized na primeira chamada
```

### 7.2 Sem Conexão à Anthropic

```
Current: Exception capturada em line 281
Result: event_bus.mark_failed() com mensagem
```

### 7.3 Resposta Inválida

```
Current: JSON parse error em line 276
Result: Logged, retorna None
```

**Conclusão**: Tratamento de erro é ROBUSTO

---

## 8. ARQUITETURA PROPOSTA

### 8.1 Runtime Interface (Nova)

```python
class AgentRuntime:
    """Abstract interface for agent execution"""
    
    async def execute(
        self,
        agent_id: str,
        system_prompt: str,
        task_description: str,
        context: Dict[str, Any],
        tools: List[str],
        timeout_seconds: int
    ) -> Optional[Dict[str, Any]]:
        """Execute agent and return structured result"""
        pass
```

### 8.2 Runtimes

```
Current: AnthropicRuntime (SDK-based)
  └─ Uses: anthropic.messages.create()

New: ClaudeCodeRuntime (subscription-based)
  └─ Uses: claude CLI with owner auth
```

### 8.3 Bridge Refactorizado

```python
class AgentInvocationBridge:
    def __init__(self, event_bus, dispatcher, governance, runtime):
        # ...
        self.runtime = runtime  # NEW: injected
        # ...
    
    async def _execute_via_runtime(self, ...):
        # Delegate to runtime
        result = await self.runtime.execute(...)
        return result
```

**Impacto**: Minimal (1 injection point)

---

## 9. RISCOS IDENTIFICADOS

### 9.1 🔴 CRÍTICO

**Sem ANTHROPIC_API_KEY**: 
- Current: Falha com 401
- Proposed: Falha com mensagem clara
- Mitigation: Detectar e rejeitar API-based authentication

**Acidental API Billing**:
- Risk: Se claude CLI não estiver disponível, fallback para API
- Mitigation: `SUBSCRIPTION_ONLY` policy (recuso fallback explícito)

### 9.2 🟡 MÉDIO

**Timeout diferente no Claude CLI**:
- Current: config.timeout_seconds passa para SDK
- Risk: Claude CLI pode ignorar
- Mitigation: Wrapper com `subprocess.timeout`

**Ferramenta não disponível**:
- Current: SDK rejeita ferramentas inválidas
- Risk: Claude CLI pode não verificar
- Mitigation: Governance valida antes de enviar

### 9.3 🟢 BAIXO

**Resposta não-JSON**:
- Current: JSON parse error
- Risk: Mesmo com CLI
- Mitigation: Existente (line 276)

---

## 10. DECISÕES ARQUITETÔNICAS

### 10.1 ✅ PRESERVE

- ✅ Event Bus (nenhuma mudança)
- ✅ Governance Engine (nenhuma mudança)
- ✅ Dispatcher (nenhuma mudança)
- ✅ Causation chain (nenhuma mudança)
- ✅ Audit trail (nenhuma mudança)
- ✅ Agent configs (nenhuma mudança)
- ✅ System prompts (nenhuma mudança)

### 10.2 🔄 REFACTOR (Mínimo)

- 🔄 agent_invocation_bridge.py:
  - Extract `_execute_via_anthropic()` → Runtime interface
  - Inject Runtime dependency
  - Total changes: ~20 lines

### 10.3 ✨ NEW

- ✨ event_bus/runtime.py:
  - AgentRuntime abstract base
  - (~30 lines)

- ✨ event_bus/anthropic_runtime.py:
  - Current behavior as runtime
  - (~50 lines)

- ✨ event_bus/claude_code_runtime.py:
  - New subscription-based runtime
  - (~80-100 lines)

**Total new lines**: ~150-200

---

## 11. ESTIMATIVA DE ESFORÇO

| Tarefa | Horas | Risco |
|---|---|---|
| Design Runtime interface | 1 | Baixo |
| Refactor Bridge | 0.5 | Baixo |
| AnthropicRuntime wrapper | 1 | Baixo |
| ClaudeCodeRuntime impl | 2-3 | Médio |
| Testing (structural) | 1-2 | Médio |
| First real execution | 1 | Alto |
| **Total** | **6-8h** | **Médio** |

---

## 12. PRÓXIMO PASSO: ETAPA 2

Validar Claude Code CLI:
- Verificar instalação
- Verificar autenticação
- Consultar documentação oficial
- Verificar suporte a JSON
- Mapear ferramentas e limitações

**Relatório**: MISSION_006_R1_AUTH_VALIDATION.md

---

## 13. CONCLUSÃO

### ✅ Achados

1. ✅ Dependência de Anthropic SDK é **isolada** (apenas 1 arquivo)
2. ✅ Contrato de execução é **bem-definido** (preservável)
3. ✅ Event Bus e Governance são **independentes** do runtime
4. ✅ Correlação e auditoria funcionam com qualquer runtime
5. ✅ Arquitetura atual permite **migração limpa** via adapter pattern

### 🟢 Pronto para Próxima Etapa

- ✅ Arquitetura entendida
- ✅ Pontos de integração mapeados  
- ✅ Riscos identificados
- ✅ Plano de migração claro

**Status**: 🟢 **GO FOR ETAPA 2**

