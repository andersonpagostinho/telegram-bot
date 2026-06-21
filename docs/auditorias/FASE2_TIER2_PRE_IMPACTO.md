# FASE 2 TIER 2 — AUDITORIA PRÉVIA DE IMPACTO

**Data:** 2026-06-21  
**Status:** 🔵 PLANEJADO  
**Precedente:** FASE 1 Tier 1 ✅ APROVADO

---

## 📋 Escopo da Fase 2

Migrar **20+ ocorrências AMARELO** em Tier 2 para padrão v2 (Clientes/{tenant_id}/Sessoes/{actor_id}).

**Fase 1 Resultado:**
- ✅ 17 ocorrências CRÍTICAS migradas (admin + gpt_actions)
- ✅ 0 escritas legadas residuais
- ✅ 174/174 P0 PASS

**Fase 2 Escopo:**
- AMARELO: 35 ocorrências (49% do total) com tenant_id guard rail presente
- Arquivos principais: router/, handlers/, services/

---

## 🔍 AUDITORIA PRÉVIA DE IMPACTO

Antes de iniciar implementação, executar auditoria estruturada em 5 fases:

### 1️⃣ Listar Arquivos Tier 2 Candidatos

**Objetivo:** Identificar todos os arquivos com `salvar_contexto_temporario` sem tenant_id explícito.

**Critério:** AMARELO (com guard rail) + VERMELHO (sem guard rail) não migrados em Fase 1.

**Saída esperada:**
- Arquivo → Linhas → Contexto de chamada
- Classificação por camada (router/, handlers/, services/)
- Contagem de ocorrências por arquivo

**Exemplo formato:**
```
router/principal_router.py
  └─ Linhas: 1140, 1890, 2340, ...
  └─ Contexto: normalização, confirmação, agendamento
  └─ Ocorrências: 20 AMARELO

handlers/bot.py
  └─ Linhas: 450, 670, ...
  └─ Contexto: fallback erro, retry
  └─ Ocorrências: 6 AMARELO

services/agenda_service.py
  └─ Linhas: 520, ...
  └─ Contexto: atualização agenda
  └─ Ocorrências: 3 VERMELHO (crítico)
```

---

### 2️⃣ Classificar Risco por Componente

**Objetivo:** Determinar impacto potencial de cada mudança.

**Critério:** Afeta motor de agenda, conflito, disponibilidade?

**Classificação:**

| Nível | Descrição | Exemplos | Risco |
|-------|-----------|----------|-------|
| 🔴 CRÍTICO | Afeta motor de agenda, conflito ou disponibilidade | agenda_service, conflito_handler, disponibilidade | Requer validação P0 completa |
| 🟠 ALTO | Afeta notificações, cancelamento, confirmação | notificacoes, cancelamento, confirmacao | Requer teste P0 associado |
| 🟡 MÉDIO | Afeta contexto geral, estado fluxo | contexto temporário, mudança contexto | Requer teste unitário |
| 🟢 BAIXO | Cache, histórico, preferências, metadata | logging, cache, histórico | Requer sanidade visual |

**Saída esperada:**
```
🔴 CRÍTICO (impacta P0)
  - services/agenda_service.py (3 ocorrências)
  - handlers/conflito_handler.py (2 ocorrências)

🟠 ALTO (impacta notificações/confirmação)
  - router/principal_router.py (10 ocorrências em confirmação)
  - services/notificacoes_service.py (2 ocorrências)

🟡 MÉDIO (impacta contexto)
  - router/principal_router.py (8 ocorrências em normalização)
  - handlers/context_manager.py (2 ocorrências)

🟢 BAIXO (metadata/logging)
  - handlers/gpt_text_handler.py (2 ocorrências)
```

---

### 3️⃣ Mapear Chamadas Legadas Restantes

**Objetivo:** Para cada ocorrência, entender como tensor_id pode ser obtido.

**Critério:** Verificar a origem do tenant_id (ctx, user_id, request, variable local).

**Análise por contexto:**

```
router/principal_router.py
  ├─ Linha 1140 (normalização)
  │   └─ Origem tenant_id: ctx["tenant_id"] (disponível)
  │   └─ Ação: Passar como parâmetro
  │
  ├─ Linha 1890 (confirmação)
  │   └─ Origem tenant_id: ctx["dono_id"] (mapped from user_id)
  │   └─ Ação: Usar dono_id como tenant_id
  │
  └─ Linha 2340 (erro handling)
      └─ Origem tenant_id: user_id → resolver ator
      └─ Ação: Chamar identidade_service.resolver_ator_por_canal

services/agenda_service.py
  └─ Linha 520 (atualizar agenda)
      └─ Origem tenant_id: ? (não claro)
      └─ Ação: Investigar fluxo de chamada, rastrear ctx
```

**Saída esperada:**
- Matriz: Arquivo × Linha × Origem tenant_id × Estratégia

---

### 4️⃣ Separar Alteração de Persistência de Comportamento

**Objetivo:** Garantir que mudança de caminho NÃO altera lógica de negócio.

**Validação por tipo:**

#### A. Leitura (carregar_contexto_temporario)

```
ANTES: ctx = carregar_contexto_temporario(user_id)
  └─ Lê de: Clientes/{user_id}/MemoriaTemporaria/contexto
  └─ Dados: [json completo]

DEPOIS: ctx = carregar_contexto_temporario(user_id, tenant_id=tenant_id)
  └─ Lê de: Clientes/{tenant_id}/Sessoes/{actor_id}
  └─ Dados: [json idêntico]

VERIFICAÇÃO: Estrutura de dados não muda ✅
```

#### B. Escrita (salvar_contexto_temporario)

```
ANTES: salvar_contexto_temporario(user_id, ctx)
  └─ Escreve em: Clientes/{user_id}/MemoriaTemporaria/contexto
  └─ Dados: [json completo]

DEPOIS: salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)
  └─ Escreve em: Clientes/{tenant_id}/Sessoes/{actor_id}
  └─ Dados: [json idêntico]

VERIFICAÇÃO: Transformação zero, apenas path muda ✅
```

#### C. Processamento (lógica entre read/write)

```
ANTES: ctx["chave"] = valor  →  normaliza  →  agenda
DEPOIS: ctx["chave"] = valor  →  normaliza  →  agenda

VERIFICAÇÃO: Algoritmo não muda ✅
```

**Saída esperada:**
- Checklist: Cada arquivo sem transformações de dados
- Evidência: Diff mostrando apenas "ctx.get(..., tenant_id=...)" adicionado

---

### 5️⃣ Garantir Segurança de Componentes Críticos

**Objetivo:** Zero alterações comportamentais em motor de agenda, conflito, disponibilidade.

**Validação por Sistema:**

#### Motor de Agenda
```
Camada: services/agenda_service.py

CRÍTICO INVIOLÁVEL:
  ✅ Cálculo de disponibilidade: IDÊNTICO
  ✅ Inserção de evento: IDÊNTICO
  ✅ Validação de conflito: IDÊNTICO
  ✅ Formato de resposta: IDÊNTICO

P0 Validation: Baterias que testam agenda devem PASS
  └─ p0_bateria_real_fluxo_completo_conflito_a_criacao (7/7)
  └─ p0_real_confirmacao_pendente_completo (17/17)
```

#### Sistema de Conflito
```
Camada: handlers/conflito_handler.py (ou equivalente)

CRÍTICO INVIOLÁVEL:
  ✅ Detecção de sobreposição: IDÊNTICO
  ✅ Resolução de conflito: IDÊNTICO
  ✅ Cálculo de alternativas: IDÊNTICO
  ✅ Notificação de conflito: IDÊNTICO

P0 Validation: Baterias que testam conflito devem PASS
  └─ p0_bateria_real_fluxo_completo_conflito_a_criacao (7/7)
  └─ p0_real_mudanca_contexto_completo (25/25)
```

#### Disponibilidade
```
Camada: services/disponibilidade_service.py (ou em agenda_service)

CRÍTICO INVIOLÁVEL:
  ✅ Cálculo de slot disponível: IDÊNTICO
  ✅ Aplicação de expediente: IDÊNTICO
  ✅ Aplicação de folgas: IDÊNTICO
  ✅ Aplicação de bloqueios: IDÊNTICO

P0 Validation: Baterias que testam disponibilidade devem PASS
  └─ Todas as 9 baterias (174/174)
```

#### Notificações
```
Camada: services/notificacoes_service.py

CRÍTICO INVIOLÁVEL:
  ✅ Construção de mensagem: IDÊNTICO
  ✅ Fila de envio: IDÊNTICO
  ✅ Entrega/fallback: IDÊNTICO
  ✅ Estado de notificação: IDÊNTICO

P0 Validation: Baterias de notificação devem PASS
  └─ p0_real_notificacoes_e2e (20/20)
```

#### Cancelamento
```
Camada: services/cancelamento_service.py

CRÍTICO INVIOLÁVEL:
  ✅ Lógica de cancelamento: IDÊNTICO
  ✅ Reembolso/crédito: IDÊNTICO
  ✅ Notificação ao profissional: IDÊNTICO
  ✅ Atualização de disponibilidade: IDÊNTICO

P0 Validation: Baterias de cancelamento devem PASS
  └─ p0_bateria_real_cancelamento_completo (15/15)
```

---

## 📊 Matriz de Risco Fase 2

| Componente | Arquivo | Ocorrências | Risco | P0 Validação |
|------------|---------|-------------|-------|--------------|
| Router | router/principal_router.py | 20 | 🟠 ALTO | Sim (174/174) |
| Handlers | handlers/context_manager.py | 2 | 🟡 MÉDIO | Sanidade |
| Handlers | handlers/bot.py | 6 | 🟡 MÉDIO | Sanidade |
| Handlers | handlers/gpt_text_handler.py | 4 | 🟢 BAIXO | Opcional |
| Services | services/agenda_service.py | 3 | 🔴 CRÍTICO | Sim (174/174) |
| Utils | utils/contexto_temporario.py | 2 | 🟡 MÉDIO | Sanidade |

**Total Tier 2:** 37 ocorrências (vs 72 totais)  
**CRÍTICO:** 3 ocorrências (motor agenda)  
**Validação requerida:** P0 174/174 PASS + teste unitário

---

## 🚀 Próximas Etapas (Após Auditoria Prévia)

### Fase 2.1: Implementação Crítica
- Migrar 3 ocorrências CRÍTICO em services/agenda_service.py
- Validar P0 174/174 PASS após cada mudança

### Fase 2.2: Implementação Alto Risco
- Migrar 20 ocorrências ALTO em router/principal_router.py
- Validar P0 174/174 PASS

### Fase 2.3: Implementação Médio Risco
- Migrar 12 ocorrências MÉDIO (handlers, utils)
- Teste unitário + sanidade visual

### Fase 2.4: Limpeza
- 2 ocorrências BAIXO em handlers/gpt_text_handler.py
- Documentar conclusão Tier 2

---

## ✅ Checklist de Aprovação Fase 2

- [ ] Auditoria Prévia Completa (5 fases)
- [ ] Matriz de Risco Validada
- [ ] Estratégia de Implementação Definida
- [ ] Roadmap Tier 2.1-2.4 Aceito
- [ ] Pronto para Implementação

---

**Status:** 🔵 AGUARDANDO AUDITORIA PRÉVIA  
**Responsável:** Equipe NeoEve  
**Próximo:** Executar 5 fases de auditoria estruturada
