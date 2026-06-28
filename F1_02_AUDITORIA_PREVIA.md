# F1-02 — Auditoria Prévia: Backlog Comercial

**Data:** 2026-06-28  
**Escopo:** Permitir dono consultar clientes por lead_status

---

## 📍 Ponto 1: Onde Comandos de Dono são Tratados

### Funções Encontradas

1. **handlers/bot.py:603** — `start_command()`
   - Diferencia tipo_usuario == "dono"
   - Mostra mensagens diferentes para dono vs cliente
   - **LIMITES:** Apenas onboarding, não consultas administrativas

2. **router/principal_router.py:3343** — `roteador_principal()`
   - Ponto central de roteamento de todas mensagens
   - Processa identidade, onboarding, confirmação, cancelamento
   - **LIMITES:** Não há ponto específico para "consultas administrativas"

3. **router/integracao_identidade_onboarding.py** — `processar_fluxo_identidade_onboarding()`
   - Resolve tipo_usuario (dono, profissional, cliente)
   - Valida onboarding
   - **LIMITES:** Apenas identidade e onboarding

### Impacto & Riscos

⚠️ **NÃO existe ponto específico para "consultas de dono"**

✅ **O que fazer:**
- Integração em `roteador_principal()` após resolver tipo_usuario
- Detectar intenção de "backlog comercial" por keywords
- Se detectado, chamar `backlog_comercial_service`
- Não delegar a GPT (determinístico)

⚠️ **Risco:**
- Se integrado incorretamente, pode quebrar fluxo normal de cliente
- Garantir isolamento: apenas se tipo_usuario == "dono"

---

## 📍 Ponto 2: Fonte Única de Verdade para Backlog

### Path Firestore

`Clientes/{tenant_id}/Clientes/{cliente_actor_id}`

**Campos utilizados:**
- `lead_status` (novo, interessado, negociacao, agendado, atendido, retorno_pendente, inativo)
- `total_agendamentos` (contador)
- `primeira_interacao` (ISO timestamp)
- `ultima_interacao` (ISO timestamp)
- `ultimo_atendimento` (ISO timestamp ou null)

### Consultas Necessárias

1. **listar_por_status(tenant_id, status)**
   - Query: `where("lead_status", "==", status)`
   - Ordena por: `ultima_interacao` DESC

2. **interessados_sem_agendamento(tenant_id)**
   - Query: `where("lead_status", "==", "interessado").where("total_agendamentos", "==", 0)`

3. **clientes_em_negociacao(tenant_id)**
   - Query: `where("lead_status", "==", "negociacao")`

4. **retorno_pendente(tenant_id)**
   - Query: `where("lead_status", "==", "retorno_pendente")`

5. **clientes_inativos(tenant_id)**
   - Query: `where("lead_status", "==", "inativo")`

6. **resumo_comercial(tenant_id)**
   - Conta cada status
   - Retorna JSON com totais

### Impacto & Riscos

✅ **O que fazer:**
- Usar queries Firestore diretas
- NÃO usar Sessões ou caches locais
- Ordenar por `ultima_interacao` para prioridade

⚠️ **Risco:**
- Se dados estiverem desatualizado em Firestore, relatório será desatualizado
- Garantir que F1-01 (lead_status) está sempre atualizado

---

## 📍 Ponto 3: Integração no Fluxo

### Fluxo Proposto

```
1. Mensagem do dono chega
   ↓
2. bot.py → roteador_principal()
   ↓
3. Resolver tipo_usuario (já faz)
   ↓
4. [NOVO] Detectar intenção de backlog (keywords)
   └─ "quem está em negociação?"
   └─ "clientes inativos"
   └─ "resumo comercial"
   └─ "interessados sem agendamento"
   ↓
5. Se SIM → chamar backlog_comercial_service
6. Se NÃO → continuar fluxo normal
   ↓
7. Retornar resultado formatado
```

### Pontos de Intercepção

**Opção A: Em bot.py (ANTES principal_router)**
- Detectar tipo_usuario == "dono"
- Detectar keywords de backlog
- Chamar serviço
- Retornar resultado
- **Vantagem:** Isolado, claro, sem contaminar principal_router

**Opção B: Em principal_router**
- Integrar após linha 3395 (após processar_fluxo_identidade_onboarding)
- Adicionar novo bloco de detecção
- **Vantagem:** Centralizado
- **Desvantagem:** principal_router já muito grande

**Recomendação:** Opção A — bot.py (melhor separação de responsabilidades)

---

## 📊 Sumário de Impacto

### Arquivos a Criar

1. **services/backlog_comercial_service.py** (NOVO)
   - Lógica de consultas e formatação

2. **tests/test_f1_02_backlog_comercial.py** (NOVO)
   - 10+ testes de validação

### Arquivos a Modificar

1. **handlers/bot.py**
   - [POSSÍVEL] Adicionar detecção de keywords de backlog
   - [POSSÍVEL] Chamar backlog_comercial_service se detectado
   - **IMPACTO:** Mínimo (nova branch de lógica, não altera fluxo existente)

### Arquivos NÃO a Modificar

✅ Não alterar:
- principal_router (muito grande, baixo benefício)
- agenda, conflito, disponibilidade
- gpt_service (não usa GPT)
- Sessões (não armazena backlog)

---

## 🚨 Pendências de Investigação

1. **Como dono consulta hoje?**
   - Existe interface admin?
   - Existe comando específico?
   - Ou ainda não existe?

2. **Formato esperado de resposta**
   - Texto simples?
   - Tabela formatada?
   - JSON?

3. **Multi-tenant**
   - Dono só vê seu próprio tenant?
   - Ou pode ver múltiplos?

---

**Próximo passo:** Implementar backlog_comercial_service.py + testes

