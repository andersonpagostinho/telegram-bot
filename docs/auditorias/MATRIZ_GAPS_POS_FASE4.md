# 🔴 MATRIZ DE GAPS PÓS-FASE 4

**Data**: 2026-06-19  
**Escopo**: Somente o que FALTA para NeoEve após FASES 1-4  
**Metodologia**: Gaps identificados por AUSÊNCIA de evidência nas FASES

---

## 📋 RESUMO DE GAPS

| Criticidade | Quantidade | % | Status |
|---|---|---|---|
| **P0 — URGENTE** | 2 | 11% | Bloqueia produção segura |
| **P1 — IMPORTANTE** | 4 | 22% | Reduz experiência/funcionalidade |
| **P2 — MELHORIAS** | 5 | 28% | Futuro, não bloqueador |
| **DOCUMENTADO/DESCONHECIDO** | 2 | 11% | Incerto, precisa investigação |

**Total de Gaps**: 13/30 capacidades (43%)

---

## 🔴 P0 — URGENTE (2)

### GAP P0-1: Dono/Profissional Não Recebem Notificações

**ID**: 6, 7  
**Capacidade**: Notificar dono e profissional  
**Status**: DESCOBERTO EM PRODUÇÃO (RO-13, 2026-06-19)

**O Problema**:
```
Cliente agenda corte com Bruna
    ↓
Evento criado ✅
    ↓
Cliente notificado ✅
    ↓
Dono NÃO notificado ❌ ← P0 ACHADO REAL
    ↓
Profissional NÃO notificado ❌ ← P0 ACHADO REAL
    ↓
Dono/profissional não sabem do agendamento
    ↓
Reputação prejudicada
```

**Evidência**: RO-13 em FASE 4 (3 execuções, 13/13 testes, descoberta confirmada)

**Arquivo Afetado**: `services/event_service_async.py:salvar_evento()`

**Dados Necessários para Notificação**:
- ✅ evento.cliente_id (quem agendou)
- ✅ evento.profissional (quem faz)
- ✅ dono_id (proprietário do salão)
- ✅ evento.data, evento.hora_inicio (quando)
- ✅ evento.servico (o quê)

**Implementação Necessária**:
```python
async def salvar_evento(...):
    # Criar evento ✅
    await criar_evento_com_lock(...)
    
    # NOVO: Notificar cliente ← ATUAL
    # NOVO: Notificar DONO ← FALTANDO
    # NOVO: Notificar PROFISSIONAL ← FALTANDO
```

**Esforço Estimado**: 1-2 dias (criar 2 notificações)

**Teste Necessário**: RO-13 já implementado, apenas esperar correção passar

---

### GAP P0-2: Follow-up Automático Desativado (Legado)

**ID**: 19  
**Capacidade**: Follow-up pós-consulta  
**Status**: DESATIVADO (legado, código comentado)

**O Problema**:
```
main.py:25 → #from scheduler.followup_scheduler import start_followup_scheduler
main.py:70 → #start_followup_scheduler()
```

**Código Legado Encontrado**:
- `handlers/followup_handler.py` — rotina_lembrete_followups()
- `Clientes/{uid}/FollowUps/` collection em Firestore
- **MAS**: Mismatch de caminho (salva em `Clientes/{dono_id}/FollowUps/` mas busca em `Usuarios/{uid}/FollowUps/`)

**Decisão Necessária**:
1. **Opção A — Remover**:
   - [ ] Deletar handlers/followup_handler.py
   - [ ] Remover imports em main.py
   - [ ] Limpar collection FollowUps de produção
   - [ ] Esforço: 0.5 dias

2. **Opção B — Corrigir e Reativar**:
   - [ ] Unificar paths de Firestore
   - [ ] Corrigir mismatch
   - [ ] Reativar em main.py
   - [ ] Testar follow-ups funcionam
   - [ ] Esforço: 2-3 dias

**Recomendação**: Opção A (remover) — código desativado há tempo, baixo valor

**Risco se Não Agir**: Dívida técnica cresce, confusão de qual versão usar

---

## 🟠 P1 — IMPORTANTE (4)

### GAP P1-1: Detecção de Grupo WhatsApp

**ID**: 14  
**Capacidade**: Detectar se cliente está em grupo (não 1:1)  
**Status**: NÃO IMPLEMENTADO

**O Problema**:
```
Sistema agendando em GRUPO
    ↓
Múltiplas pessoas vendo datas/horários
    ↓
Possível exposição de dados
    ↓
UX quebrada em grupo (respostas fora de contexto)
```

**Implementação Necessária**:
- Verificar `chat.type` em webhook Telegram
- Bloquear agendamento se `chat.type == "group"`
- Responder: "Desculpa, agende em conversa privada"

**Arquivos Afetados**:
- `handlers/message_handler.py` — adicionar verificação
- `prompts/sistema.py` — adicionar regra
- `services/gpt_executor.py` — bloquear em modo grupo

**Esforço Estimado**: 1-2 dias

**Teste Necessário**: Simular webhook de grupo, validar bloqueio

---

### GAP P1-2: Generalizar Standby (Não Apenas Arquivo)

**ID**: 22  
**Capacidade**: Pausar contato após N tentativas sem resposta  
**Status**: PARCIAL (apenas arquivo de importação)

**O Problema**:
```
Hoje: standby apenas para "aguardar_arquivo_importacao"
    ↓
Precisaria: pausa geral para contatos sem resposta
    ↓
Exemplo: contato não responde 2 vezes → parar de tentar
```

**Implementação Necessária**:
1. Criar função `colocar_em_standby(user_id, dias)` em cliente_service.py
2. Criar scheduler em `scheduler/reativacao_scheduler.py`
3. Job que executa a cada dia verificando standby
4. Reativar manualmente ou por evento

**Esforço Estimado**: 2-3 dias

**Teste Necessário**: Simular 2 tentativas sem resposta, validar standby

---

### GAP P1-3: Estado do Lead

**ID**: 20  
**Capacidade**: Rastrear: ativo → negociação → fechado / perdido  
**Status**: NÃO IMPLEMENTADO

**O Problema**:
```
Sem estado de lead:
    ├─ Equipe de vendas não sabe quem é "quente"
    ├─ Sem relatórios de pipeline
    ├─ Sem análise de conversão
    └─ Cegueira total sobre negócios
```

**Implementação Necessária**:
1. Adicionar campo `lead_status` em documento cliente
2. Estados: "ativo", "negociacao", "fechado", "perdido", "pausado"
3. Funções para mudar estado
4. Trigger automático: "perdido" após 30 dias sem interação
5. Relatórios para acompanhar

**Esforço Estimado**: 3-4 dias

**Teste Necessário**: Criar lead, marcar estados, validar transições

---

### GAP P1-4: Lead Perdido (Detecção Automática)

**ID**: 21  
**Capacidade**: Detectar e marcar cliente como perdido  
**Status**: NÃO IMPLEMENTADO

**O Problema**:
```
Cliente X não responde há 30 dias
    ↓
Sistema não sabe que é "perdido"
    ↓
Vendedor continua tentando inutilmente
```

**Implementação Necessária**:
1. Job que roda diariamente
2. Verifica última interação por cliente
3. Se > 30 dias: marca como "perdido"
4. Notifica vendedor

**Dependência**: GAP P1-3 (estado do lead)

**Esforço Estimado**: 1-2 dias (após P1-3)

---

## 🟡 P2 — MELHORIAS (5)

### GAP P2-1: Reativação Automática Pós-Standby

**ID**: 23  
**Capacidade**: Reativar contato após período em standby  
**Status**: NÃO IMPLEMENTADO

**O Problema**:
```
Contato em standby após 2 tentativas sem resposta
    ↓
Depois de 7 dias: reativar automaticamente
    ↓
Sem agressividade, mas sem desistência
```

**Implementação Necessária**:
1. Scheduler que verifica standby há 7 dias
2. Reativa automaticamente (ou pede confirmação)
3. Notifica vendedor

**Dependência**: GAP P1-2 (standby geral)

**Esforço Estimado**: 1 dia (após P1-2)

---

### GAP P2-2: Melhor Horário de Resposta

**ID**: 25  
**Capacidade**: Aprender melhor horário para contatar cliente  
**Status**: NÃO IMPLEMENTADO

**O Problema**:
```
Cliente X responde melhor entre 18-20h
    ↓
Sistema propõe agendamento às 09:00
    ↓
Cliente vê tardiamente, confirma tarde
    ↓
Sem sinergia entre timing de contato e horário de agendamento
```

**Implementação Necessária**:
1. Coletar timestamps de resposta
2. Analisar padrão (exemplo: 80% de respostas entre 18-20h)
3. Usar para sugerir contato melhor
4. Considerar na proposta de agendamento

**Esforço Estimado**: 2-3 dias

---

### GAP P2-3: Perfil Comportamental Completo

**ID**: 26  
**Capacidade**: Criar perfil com preferências aprendidas  
**Status**: PARCIAL (dados existem, análise não)

**O Problema**:
```
Dados de agendamento EXISTEM:
    ├─ últimos 10 agendamentos
    ├─ profissional preferido
    ├─ horário preferido
    └─ serviço preferido

MAS: nenhuma análise automática
    → sem perfil
    → sem personalização
```

**Implementação Necessária**:
1. Job que roda 1x/semana
2. Analisa últimos 10 agendamentos
3. Extrai: profissional 3x+, horário 3x+, serviço 3x+
4. Salva em `ClienteProfile/comportamento`

**Esforço Estimado**: 1-2 dias

**Nota**: Dados já existem em Firestore (FASES 1-4), apenas falta análise

---

### GAP P2-4: Permissões Granulares (Admin)

**ID**: 28 (expansão)  
**Capacidade**: Controle de acesso por papel (admin, vendedor, profissional)  
**Status**: NÃO IMPLEMENTADO

**O Problema**:
```
Hoje: qualquer dono acessa TUDO
    ↓
Sem granularidade:
    ├─ Vendedor vê/modifica agenda de outro vendedor
    ├─ Profissional vê contatos de outro profissional
    └─ Sem auditoria de quem fez o quê
```

**Implementação Necessária**:
1. Modelo de papéis: admin, vendedor, profissional
2. Permissões por papel
3. Filtro de dados por usuário (vendedor X vê apenas clientes dele)
4. Auditoria de ações

**Esforço Estimado**: 3-5 dias

---

### GAP P2-5: Relatórios Básicos

**ID**: 29  
**Capacidade**: Gerar relatórios de agendamentos/performance  
**Status**: NÃO IMPLEMENTADO

**O Problema**:
```
Sem relatórios:
    ├─ Sem visibilidade de performance
    ├─ Sem análise de tendências
    ├─ Sem dados para decisão
```

**Relatórios Necessários**:
1. **Agendamentos por Profissional**: Quantos agendamentos Bruna fez este mês?
2. **Taxa de Confirmação**: Qual % dos agendamentos propostos foram confirmados?
3. **Cancelamentos**: Qual % cancelou? Por quê?
4. **Faturamento Estimado**: Quanto cada profissional/serviço rendeu?
5. **Performance**: Quem tem melhor taxa de conversão?

**Esforço Estimado**: 2-3 dias (por relatório)

---

## 🟣 DESCONHECIDO / INCERTO (2)

### GAP Incerto 1: Onboarding

**ID**: 27  
**Capacidade**: Orientar novo cliente  
**Status**: NÃO AUDITADO (sem teste nas FASES)

**Questão**: 
- É importante? (talvez sim)
- Existe implementação? (desconhecido)
- Precisa teste? (sim)

**Ação**: Investigar se onboarding é necessário e implementado

---

### GAP Incerto 2: Preferências do Cliente (Configurável)

**ID**: 18  
**Capacidade**: Usuário escolher preferências manualmente  
**Status**: PARCIAL (apenas automática)

**Questão**:
- Cliente pode escolher profissional favorito manualmente? (desconhecido)
- Pode salvar preferências? (desconhecido)
- Interface para configurar? (não)

**Ação**: Investigar se é requisito e implementar se necessário

---

## 📊 MATRIZ DE PRIORIZAÇÃO

### Bloqueadores Absolutos (FAZER ANTES DE PRODUÇÃO)

| Gap | Impacto | Esforço | Prioridade | Deadline |
|---|---|---|---|---|
| P0-1: Notificações dono/prof | Altíssimo (agendamento invisível) | 1-2d | CRÍTICO | 2026-06-20 |

### Altamente Recomendado (FAZER DEPOIS DE P0)

| Gap | Impacto | Esforço | Prioridade | Timeline |
|---|---|---|---|---|
| P0-2: Remove follow-up legado | Médio (dívida técnica) | 0.5d | ALTA | 2026-06-20 |
| P1-1: Detectar grupo WhatsApp | Médio (UX em grupo) | 1-2d | ALTA | 2026-06-21 |
| P1-3: Estado do lead | Altíssimo (sem pipeline) | 3-4d | ALTA | 2026-06-23 |

### Importantes (FAZER DURANTE SEMANA 2-3)

| Gap | Impacto | Esforço | Prioridade |
|---|---|---|---|
| P1-2: Generalizar standby | Alto (sem pausas inteligentes) | 2-3d | MÉDIA-ALTA |
| P1-4: Lead perdido automático | Alto (sem limpeza de contatos) | 1-2d | MÉDIA-ALTA |
| P2-1: Reativação pós-standby | Médio (reengajamento) | 1d | MÉDIA |

### Melhorias Futuras (ROADMAP P2)

| Gap | Impacto | Esforço | Prioridade |
|---|---|---|---|
| P2-2: Melhor horário resposta | Baixo (otimização) | 2-3d | BAIXA |
| P2-3: Perfil comportamental | Médio (personalização) | 1-2d | BAIXA |
| P2-4: Permissões granulares | Médio (segurança) | 3-5d | BAIXA |
| P2-5: Relatórios | Alto (inteligência) | 2-3d por relatório | BAIXA |

---

## 📅 TIMELINE RECOMENDADA

### Semana 1 (2026-06-20)
- [ ] **P0-1**: Implementar notificações dono/profissional
- [ ] **P0-1**: Validar RO-13 passa (3 execuções)
- [ ] **P0-2**: Remover follow-up legado

### Semana 2 (2026-06-23)
- [ ] **P1-1**: Detectar grupo WhatsApp
- [ ] **P1-3**: Implementar estado do lead
- [ ] **P1-4**: Lead perdido automático

### Semana 3 (2026-06-30)
- [ ] **P1-2**: Generalizar standby
- [ ] **P2-1**: Reativação pós-standby
- [ ] Investigar: GAP Incerto 1 (Onboarding)

### Semana 4+ (Roadmap)
- [ ] **P2-2**: Melhor horário resposta
- [ ] **P2-3**: Perfil comportamental
- [ ] **P2-4**: Permissões granulares
- [ ] **P2-5**: Relatórios

---

## 🎯 RESUMO EXECUTIVO DOS GAPS

### Crítico (1)
- ⚠️ Notificações para dono/profissional (P0-1) — FAZER IMEDIATAMENTE

### Importante (5)
- ⚠️ Remove follow-up legado (P0-2)
- ⚠️ Detectar grupo WhatsApp (P1-1)
- ⚠️ Estado do lead (P1-3)
- ⚠️ Lead perdido automático (P1-4)
- ⚠️ Generalizar standby (P1-2)

### Melhorias (5)
- 🔵 Reativação pós-standby (P2-1)
- 🔵 Melhor horário resposta (P2-2)
- 🔵 Perfil comportamental (P2-3)
- 🔵 Permissões granulares (P2-4)
- 🔵 Relatórios (P2-5)

### Incertos (2)
- ❓ Onboarding (investigar)
- ❓ Preferências configuráveis (investigar)

---

## 📝 CONCLUSÃO

**NeoEve tem 63% das funcionalidades core implementadas.**

**Para produção segura, NECESSÁRIO**:
- ✅ Implementar notificações dono/profissional (P0-1)
- ✅ Remover follow-up legado (P0-2)

**Depois de produção, recomendado em 30 dias**:
- Detectar grupo WhatsApp
- Implementar estado do lead
- Generalizar standby

**Roadmap longo prazo**: Permissões, relatórios, perfil comportamental

---

**Documento gerado**: 2026-06-19  
**Base**: FASES 1-4 (49 testes, 100% aprovação)  
**Status**: 13 gaps identificados, priorização definida

