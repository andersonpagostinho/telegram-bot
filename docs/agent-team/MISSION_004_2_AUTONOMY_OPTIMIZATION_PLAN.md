# MISSÃO 004.2 — Autonomia Operacional e Redução de Prompts

**Data**: 2026-11-22  
**Escopo**: Auditoria e Otimização de Permissões  
**Status**: 🔍 **ANÁLISE E PLANEJAMENTO**  
**Objetivo**: Reduzir solicitações repetitivas mantendo segurança

---

## Executive Summary

**Objetivo**: Permitir que agentes executem tarefas rotineiras sem solicitar autorização repetitiva para operações já permitidas.

**Estratégia**: 
1. Auditar permissões atuais
2. Identificar operações que exigem prompt desnecessário
3. Configurar regras automáticas para rotinas seguras
4. Manter proteções rigorosas para operações críticas
5. Testar configuração completa

**Resultado esperado**: Autonomia operacional elevada com segurança preservada.

---

## 1. Análise de Permissões Atuais

### 1.1 — Configuração Global

**Local**: `.claude/settings.json` (padrão do Claude Code)

**Estrutura observada**:
```json
{
  "permissions": {
    "allow": [...],
    "ask": [...],
    "deny": [...]
  }
}
```

### 1.2 — Configuração Local

**Local**: `.claude/settings.local.json` (projeto-específico)

**Achados**:
- 400+ linhas de permissões específicas
- Muitas entradas herdadas de projetos anteriores
- Padrões muito específicos (caminhos absolutos, nomes exatos)
- Sem consolidação de padrões genéricos

**Problema**: Permissões ultrarrestritas = solicita YES frequentemente

---

## 2. Operações Que DEVEM Ser Automáticas

### 2.1 — Leitura e Análise

```
✅ Read(*)                    — Ler qualquer arquivo do projeto
✅ Glob(pattern)              — Encontrar arquivos
✅ Grep(pattern)              — Buscar conteúdo
✅ Bash(cat)                  — Exibir conteúdo
✅ Bash(ls)                   — Listar diretórios
✅ Bash(find)                 — Localizar arquivos
```

### 2.2 — Edição Autorizada

```
✅ Edit(*.py)                 — Editar código Python
✅ Edit(*.md)                 — Editar documentação
✅ Edit(test_*.py)            — Editar testes
✅ Edit(docs/*)               — Editar docs/
✅ Write(*.md)                — Criar Markdown
✅ Write(test_*.py)           — Criar testes
```

### 2.3 — Verificações Locais

```
✅ Bash(pytest *)             — Executar testes
✅ Bash(python -m pylint)     — Linting
✅ Bash(python -m black)      — Formatação
✅ Bash(python -m mypy)       — Type checking
✅ Bash(python -c)            — Executar Python
```

### 2.4 — Git — Sem Modificação Remota

```
✅ Bash(git status)           — Status do repositório
✅ Bash(git diff)             — Diferenças
✅ Bash(git log)              — Histórico
✅ Bash(git show)             — Exibir commit
✅ Bash(git branch)           — Listar branches
✅ Bash(git add)              — Staged arquivos
✅ Bash(git commit)           — Criar commit
```

### 2.5 — Comunicação Interna

```
✅ Agent(subagent_type)       — Invocar subagentes
✅ ArtifactData(read)         — Ler dados compartilhados
✅ SendMessage(to: "agent")   — Comunicação entre agentes
```

---

## 3. Operações Que DEVEM Continuar Protegidas

### 3.1 — Git Remoto (Exigir Autorização)

```
❌ Bash(git push)             — Deve sempre pedir
❌ Bash(git reset)            — Deve sempre pedir
❌ Bash(git rebase)           — Deve sempre pedir
❌ Bash(git merge)            — Deve sempre pedir
```

### 3.2 — Produção e Dados (Exigir Autorização)

```
❌ Bash(firebase *)           — Acesso Firebase
❌ Bash(gcloud *)             — Acesso GCP
❌ Bash(docker *)             — Containerização
❌ Bash(export OPENAI_API_KEY) — Secrets
```

### 3.3 — Destrutivo (Exigir Autorização)

```
❌ Bash(rm)                   — Deleção
❌ Bash(rm -rf)               — Deleção recursiva
❌ PowerShell(Remove-Item)    — Deleção PS
```

### 3.4 — Infraestrutura (Exigir Autorização)

```
❌ Bash(sudo)                 — Escalação de privilégio
❌ Alterações bilheteria      — Alterações de custos
❌ Migrações de banco         — Alterações destrutivas
```

---

## 4. Configuração Recomendada

### 4.1 — Arquivo: `.claude/settings.json` (Global)

```json
{
  "permissions": {
    "allow": [
      // === LEITURA ===
      "Read",
      "Glob",
      "Grep",
      
      // === EDIÇÃO AUTORIZADA ===
      "Edit",
      "Write",
      
      // === BASH — LEITURA ===
      "Bash(cat *)",
      "Bash(ls *)",
      "Bash(find *)",
      "Bash(wc *)",
      "Bash(stat *)",
      
      // === BASH — GIT (SEM PUSH/RESET) ===
      "Bash(git status *)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git show *)",
      "Bash(git branch *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      
      // === BASH — TESTES ===
      "Bash(pytest *)",
      "Bash(python -m pytest *)",
      "Bash(python -c *)",
      
      // === BASH — VALIDAÇÃO ===
      "Bash(python -m pylint *)",
      "Bash(python -m black *)",
      "Bash(python -m mypy *)",
      
      // === AGENTS ===
      "Agent",
      
      // === ARTIFACTS ===
      "Artifact"
    ],
    "ask": [
      // === GIT REMOTO ===
      "Bash(git push *)",
      "Bash(git reset *)",
      "Bash(git rebase *)",
      "Bash(git merge *)",
      "Bash(git revert *)",
      
      // === DESTRUTIVO ===
      "Bash(rm *)",
      
      // === PRODUÇÃO ===
      "Bash(firebase *)",
      "Bash(gcloud *)",
      "Bash(docker *)",
      
      // === SECRETS ===
      "Bash(export OPENAI_API_KEY *)",
      "Bash(export FIREBASE_CREDENTIALS *)"
    ],
    "deny": [
      // === NUNCA ===
      "Bash(sudo *)",
      "Bash(rm -rf *)"
    ]
  }
}
```

### 4.2 — Arquivo: `.claude/settings.local.json` (Projeto)

**Recomendação**: Manter limpo, usar apenas para exceções específicas do projeto.

---

## 5. Matriz de Teste Obrigatório

### Teste 1: Operações Rotineiras (DEVEM ser automáticas)

```
1. Read arquivo                    → ✅ SEM PROMPT
2. Glob find files                 → ✅ SEM PROMPT
3. Grep search code                → ✅ SEM PROMPT
4. Edit arquivo .py                → ✅ SEM PROMPT
5. Write teste novo                → ✅ SEM PROMPT
6. Bash(pytest)                    → ✅ SEM PROMPT
7. Bash(git status)                → ✅ SEM PROMPT
8. Bash(git diff)                  → ✅ SEM PROMPT
9. Bash(git commit)                → ✅ SEM PROMPT
10. Agent(subagent)                → ✅ SEM PROMPT
```

**Resultado esperado**: 10/10 automáticas

### Teste 2: Operações Protegidas (DEVEM pedir autorização)

```
1. Bash(git push)                  → ✅ COM PROMPT
2. Bash(git reset)                 → ✅ COM PROMPT
3. Bash(rm arquivo)                → ✅ COM PROMPT
4. Bash(firebase operations)       → ✅ COM PROMPT
5. Bash(export SECRET)             → ✅ COM PROMPT
```

**Resultado esperado**: 5/5 com prompt

### Teste 3: Operações Negadas (DEVEM ser bloqueadas)

```
1. Bash(sudo comando)              → ❌ BLOQUEADO
2. Bash(rm -rf)                    → ❌ BLOQUEADO
```

**Resultado esperado**: 2/2 bloqueadas

---

## 6. Autonomia por Agente

### ARCHITECT
```
Automático:
  ✅ Receber objetivos
  ✅ Analisar código
  ✅ Produzir planos
  ✅ Validar contratos

Exigir autorização:
  ❌ Deploy
  ❌ Produção
```

### BACKEND-DEVELOPER
```
Automático:
  ✅ Ler código
  ✅ Editar arquivos
  ✅ Executar testes
  ✅ Fazer commits

Exigir autorização:
  ❌ Git push
  ❌ Deploy
  ❌ Acesso Firebase
```

### QA-ENGINEER
```
Automático:
  ✅ Executar testes
  ✅ Produzir relatórios
  ✅ Analisar cobertura
  ✅ Detectar regressões

Exigir autorização:
  ❌ Deploy
  ❌ Produção
```

### SECURITY-AUDITOR
```
Automático:
  ✅ Ler logs
  ✅ Produzir auditorias
  ✅ Detectar riscos
  ✅ Verificar isolamento

Exigir autorização:
  ❌ Alterações
  ❌ Produção
```

### RELEASE-MANAGER
```
Automático:
  ✅ Revisar gates
  ✅ Produzir relatórios
  ✅ Verificar compliance

Exigir autorização:
  ❌ Deploy
  ❌ Publish
  ❌ Produção
```

### DEBUGGER
```
Automático:
  ✅ Analisar código
  ✅ Produzir diagnósticos
  ✅ Traceback

Exigir autorização:
  ❌ Corrigir código
  ❌ Produção
```

### OPENAI-VALIDATOR
```
Automático:
  ✅ Analisar evidências
  ✅ Produzir validação
  ✅ Registrar auditoria

Exigir autorização:
  ❌ Deploy
  ❌ Produção
```

---

## 7. Pré-Auditoria do Event Bus

### 7.1 — Arquitetura Necessária

#### Componentes

```
1. Event Registry
   - Tipos de eventos
   - Schemas
   - Validação

2. Event Bus
   - Pub/Sub messaging
   - Persistence
   - Filtering

3. Agent Registry
   - Identificação de agentes
   - Capacidades
   - Permissões

4. Task Coordinator
   - Atribuição de tarefas
   - Dependências
   - Serialização

5. Execution Tracker
   - Estado de execução
   - Timestamps
   - Resultados

6. Audit Trail
   - Integração com OpenAI Validator
   - Conformidade
   - Rastreabilidade
```

#### Eventos Identificados

```
✅ TASK_CREATED
   - task_id, assignee, description, scope, dependencies

✅ TASK_STARTED
   - task_id, assignee, timestamp

✅ TASK_COMPLETED
   - task_id, assignee, result, evidence

✅ VALIDATION_REQUESTED
   - task_id, evidence, validator_config

✅ VALIDATION_COMPLETED
   - task_id, verdict, confidence, audit_trail

✅ APPROVAL_GRANTED
   - task_id, approver, timestamp

✅ DEPLOYMENT_AUTHORIZED
   - task_id, release_manager, environment

✅ TASK_BLOCKED
   - task_id, blocker, reason
```

#### Integração Com Claude Code

```
❓ Webhook para novos eventos
❓ Mecanismo de delegação automática
❓ Estado compartilhado entre agentes
❓ Histórico persistido
```

---

## 8. Recomendações Priorizadas

### IMEDIATO (P0)
1. ✅ Aplicar configuração de permissões global
2. ✅ Testar matriz de 15 operações
3. ✅ Validar redução de prompts

### CURTO PRAZO (P1)
1. ⏳ Event Bus pre-audit (documentar arquitetura)
2. ⏳ Mapear integração Claude Code
3. ⏳ Definir schemas de eventos

### MÉDIO PRAZO (P2)
1. ⏳ MISSÃO 005: Implementar Event Bus
2. ⏳ MISSÃO 006: Implementar Command Center
3. ⏳ MISSÃO 007: Integração nativa Claude Code

---

## 9. Próximas Ações

### Fase 1: Implementar Permissões (1-2 horas)
- Atualizar `.claude/settings.json` com configuração recomendada
- Testar matriz de 15 operações
- Registrar resultados

### Fase 2: Validar Autonomia (1-2 horas)
- QA Engineer verifica matriz
- Security Auditor valida proteções
- Release Manager aprova configuração

### Fase 3: Pre-Audit Event Bus (2-3 horas)
- Documentar arquitetura necessária
- Mapear eventos
- Definir schemas
- Criar `EVENT_BUS_PREIMPLEMENTATION_AUDIT.md`

---

## Conclusão

**Plano de Autonomia está pronto para implementação.**

Próximas ações:
1. Aplicar permissões recomendadas
2. Testar configuração
3. Validar redução de prompts
4. Preparar Event Bus para MISSÃO 005

**Aguardando autorização para iniciar implementação.**

---

**Plano Criado**: 2026-11-22  
**Status**: Pronto para Fase 1 (Implementação de Permissões)
