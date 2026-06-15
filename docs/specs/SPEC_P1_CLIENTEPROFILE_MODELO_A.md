# SPEC: Implementação de ClienteProfile (Modelo A)

**Versão:** 1.0  
**Data:** 2026-06-14  
**Status:** APROVADO PARA IMPLEMENTAÇÃO  
**Fase:** P1 Personalização — Data Layer

---

## 1. OBJETIVO

Implementar uma camada de perfil de cliente agregado que:
- Coleta dados historicamente existentes (eventos, preferências)
- Não altera fluxo de agendamento atual (P0)
- Fornece base para personalização futura (P1)
- Mantém segurança multi-tenant
- Preserva eventos como source of truth

**Objetivo funcional:** Quando implementado, sistema saberá quem é cada cliente, qual é sua recorrência, profissional preferido e histórico. Mas agendamento funciona exatamente igual a hoje.

---

## 2. ESCOPO P1 MÍNIMO (Fase 1)

### Funcionalidades que ENTRAM nesta release:

✅ **Criação de Profile**
- Criar `Clientes/{tenant_id}/ClienteProfiles/{cliente_id}` na primeira vez que cliente agenda

✅ **Aggregação Histórica**
- Após cada evento salvo: atualizar campos agregados do profile

✅ **Métricas Básicas**
- Contar: total_eventos, profissionais_usados, servicos_usados
- Registrar: primeira_contato, ultima_contato
- Detectar: profissional_mais_frequente, servico_mais_frequente

✅ **Segurança Multi-Tenant**
- Path seguro com tenant_id
- Validação de isolamento
- Sem vazamento cross-tenant

✅ **Compatibilidade P0**
- Eventos continuam salvos em `Clientes/{tenant_id}/Eventos`
- Nenhuma mudança na estrutura de eventos
- Agendamento funciona idêntico

### Funcionalidades que NÃO entram nesta release:

❌ **Personalização Automática**
- NÃO usar profile para sugerir horários
- NÃO usar para sugerir profissionais
- NÃO usar para priorizar serviços

❌ **Preferências do Cliente**
- NÃO coletar "preferência de conversa" (pessoal vs direto)
- NÃO coletar "melhor horário para contatar"
- NÃO coletar "taxa de confirmação"

❌ **Histórico Conversacional**
- NÃO salvar mensagens
- NÃO criar histórico de chat
- Apenas eventos de agendamento

❌ **Analytics Avançado**
- NÃO calcular patterns complexos
- NÃO score de cliente
- NÃO machine learning

---

## 3. FORA DE ESCOPO

| Item | Por quê | Quando |
|---|---|---|
| Alterar Eventos | P0 não deve mudar | P2 (refactor) |
| MemoriaTemporaria | Contexto temp, não relacionado | N/A |
| Histórico Conversacional | Apenas P1.2 | P1.2 (semana 2) |
| Preferências explícitas | Sem coleta hoje | P1.4 (semana 4) |
| Follow-up inteligente | Legado, separado | P2 |
| Analytics dashboard | Não é P1 | P2 |

---

## 4. SCHEMA INICIAL DE CLIENTEPROFILE

### Estrutura Firestore

```
Clientes/{tenant_id}/ClienteProfiles/{cliente_id}/
  ├─ # Identity (imutável)
  ├─ cliente_id: string (copy of document ID)
  ├─ tenant_id: string (copy of parent ID)
  ├─ criado_em: ISO datetime
  │
  ├─ # Informação básica (preenchida uma vez)
  ├─ nome: string (from evento.cliente_nome)
  ├─ email: string | null (from Clientes/{uid}.email)
  │
  ├─ # Agregação histórica (atualizado a cada evento)
  ├─ historico: object
  │   ├─ primeira_contato: ISO datetime
  │   ├─ ultima_contato: ISO datetime
  │   ├─ total_eventos: int (>=0)
  │   ├─ profissionais_atendidos: array<string> (unique)
  │   ├─ servicos_atendidos: array<string> (unique)
  │   └─ proxima_sugestao: ISO datetime | null
  │
  ├─ # Tendências (detectadas)
  ├─ tendencias: object
  │   ├─ profissional_mais_frequente: string | null
  │   ├─ profissional_mais_frequente_count: int
  │   ├─ servico_mais_frequente: string | null
  │   ├─ servico_mais_frequente_count: int
  │   └─ intervalo_medio_dias: int | null
  │
  ├─ # Metadata
  ├─ atualizado_em: ISO datetime
  ├─ versao: int (starts at 1)
  └─ # Reserved for future
    └─ # (preferencias, metricas, status — não adicionar ainda)
```

### Exemplo de Documento Completo

```json
{
  "cliente_id": "123456789",
  "tenant_id": "987654321",
  "criado_em": "2026-06-01T10:30:00Z",
  "nome": "Suri",
  "email": "suri@example.com",
  "historico": {
    "primeira_contato": "2026-06-01T10:30:00Z",
    "ultima_contato": "2026-06-14T15:45:00Z",
    "total_eventos": 3,
    "profissionais_atendidos": ["Carla", "Bruna"],
    "servicos_atendidos": ["corte", "escova"],
    "proxima_sugestao": "2026-06-21T10:30:00Z"
  },
  "tendencias": {
    "profissional_mais_frequente": "Carla",
    "profissional_mais_frequente_count": 2,
    "servico_mais_frequente": "corte",
    "servico_mais_frequente_count": 2,
    "intervalo_medio_dias": 14
  },
  "atualizado_em": "2026-06-14T15:45:00Z",
  "versao": 1
}
```

---

## 5. CAMPOS OBRIGATÓRIOS

Esses campos SEMPRE devem existir no documento:

| Campo | Tipo | Inicializado | Razão |
|---|---|---|---|
| `cliente_id` | string | Na criação | Identidade |
| `tenant_id` | string | Na criação | Multi-tenant safety |
| `criado_em` | ISO datetime | Na criação | Auditoria |
| `atualizado_em` | ISO datetime | Na criação | Rastreamento |
| `versao` | int | 1 na criação | Versionamento |
| `historico.primeira_contato` | ISO datetime | Na criação | Auditoria |
| `historico.ultima_contato` | ISO datetime | Na criação | Métrica |
| `historico.total_eventos` | int | 0 na criação | Métrica |
| `historico.profissionais_atendidos` | array | [] na criação | Agregação |
| `historico.servicos_atendidos` | array | [] na criação | Agregação |

---

## 6. CAMPOS OPCIONAIS (Não usar em P1)

Esses campos devem ser DEIXADOS EM BRANCO ou não inclusos até P1.2+:

| Campo | Quando adicionar | Razão |
|---|---|---|
| `preferencias.profissional_preferido` | P1.4 | Requer coleta de preferência |
| `preferencias.horario_preferido` | P1.4 | Requer análise de padrão |
| `preferencias.modo_conversacao` | P1.3 | Requer classificação |
| `metricas.taxa_confirmacao` | P1.3 | Requer cálculo |
| `metricas.tempo_medio_resposta` | P2 | Requer rastreamento |
| `status` | P1.5 | Requer regras de estado |
| `email` | P1.1 (opcional) | Pode não ter |
| `telefone` | P2 | Não coletamos hoje |

---

## 7. COMO IDENTIFICAR cliente_id

### Regra de Identificação

```
cliente_id = {
  SE evento.cliente_id existe:
    USAR evento.cliente_id
  SENÃO:
    cliente_id = evento.cliente_id = user_id (quem agendou)
}
```

### Evidência Técnica

**Localização:** `handlers/event_handler.py:513`

```python
# Quando evento é criado:
cliente_id = event_data.get("cliente_id") or user_id
# event_data.cliente_id vem de GPT extraction (manual_secretaria.py)
```

### Casos

| Caso | cliente_id | Exemplo |
|---|---|---|
| **Agendamento próprio** | Quem agendou | João agenda para si → cliente_id = João |
| **Agendamento para dependente** | GPT extrai | João agenda para Suri → cliente_id = Suri |
| **Agendamento para terceiro** | GPT extrai | João agenda para esposa → cliente_id = "esposa" ou nome |

### Validação

```
REGRA: cliente_id não pode ser vazio
  SE cliente_id vazio após extraction:
    LOG warning: "cliente_id não determinado"
    USAR user_id como fallback
    MARCAR profile como "identificacao_incerta"
```

---

## 8. QUANDO CRIAR PROFILE

### Trigger de Criação

**Evento:** Evento salvo com sucesso em `Clientes/{tenant_id}/Eventos/{event_id}`

**Local:** `event_service_async.py` ou `handlers/event_handler.py` (após salvar evento)

**Lógica:**

```
APÓS salvar evento em Firestore:
  1. Extrair: tenant_id, cliente_id
  2. Verificar: EXISTS Clientes/{tenant_id}/ClienteProfiles/{cliente_id}
  3. SE não existe:
       Criar documento com valores iniciais
       tenant_id = extrair do path
       cliente_id = extrair do evento
       criado_em = now()
       atualizado_em = now()
       historico.primeira_contato = now()
       historico.ultima_contato = now()
       historico.total_eventos = 1
       historico.profissionais_atendidos = [evento.profissional]
       historico.servicos_atendidos = [evento.servico]
  4. SE já existe:
       PULAR criação, seguir para "QUANDO ATUALIZAR"
```

### Idempotência

```
IMPORTANTE: operação CREATE + UPDATE devem ser idempotentes
  - Se criar duas vezes mesmo profile: deve ser seguro
  - Se chamar UPDATE antes de CREATE: deve criar se não existe
  - Usar operação SET com merge:true (Firestore)
```

### Rollback

```
SE falhar criação de profile:
  LOG error: "falha ao criar profile"
  CONTINUAR (não bloqueia agendamento)
  Profile pode ser criado em background job depois
```

---

## 9. QUANDO ATUALIZAR PROFILE

### Trigger de Atualização

**Evento:** Novo evento salvo com `status = "confirmado"`

**Local:** Mesma função que cria (após salvar evento)

**Lógica:**

```
APÓS salvar evento (sempre):
  1. Extrair: tenant_id, cliente_id, evento.profissional, evento.servico
  2. GET Clientes/{tenant_id}/ClienteProfiles/{cliente_id}
  3. UPDATE com:
       atualizado_em = now()
       historico.ultima_contato = now()
       historico.total_eventos += 1
       historico.profissionais_atendidos = unique([...existing, evento.profissional])
       historico.servicos_atendidos = unique([...existing, evento.servico])
       tendencias.profissional_mais_frequente = calcular_moda(profissionais_atendidos)
       tendencias.servico_mais_frequente = calcular_moda(servicos_atendidos)
       versao += 1
```

### Frequência

| Operação | Frequência | Razão |
|---|---|---|
| CREATE | 1x por cliente | Primeira vez |
| UPDATE | 1x por evento criado | Sempre agregar |
| LEITURA | 0x em P1 | Nenhum uso em P1 |

### Operação Atômica

```
USAR: Firestore transaction OU operação UPDATE atômica
  NÃO fazer: read → modify → write (race condition)
  FAZER: update com campo 'versao' para otimistic locking
```

---

## 10. QUAIS EVENTOS ALIMENTAM PROFILE

### Eventos que Disparam Atualização

| Tipo de Evento | Alimenta Profile | Por quê | Campo Afetado |
|---|---|---|---|
| **Evento criado (confirmado)** | ✅ SIM | Histórico | `historico.total_eventos` |
| **Evento com profissional** | ✅ SIM | Preferência | `historico.profissionais_atendidos` |
| **Evento com serviço** | ✅ SIM | Preferência | `historico.servicos_atendidos` |
| **Evento cancelado** | ❌ NÃO (P1) | Não contar cancelado | - |
| **Evento reagendado** | ❌ NÃO (P1) | Apenas novo é contado | - |
| **Evento pendente** | ❌ NÃO | Esperar confirmação | - |

### Regra de Filtering

```
APENAS eventos com status = "confirmado" alimentam profile

NÃO contar:
  - evento.status = "pendente"
  - evento.status = "cancelado"
  - evento.status = "reagendamento"

SE evento é atualizado de "pendente" → "confirmado":
  ENTÃO alimenta profile (uma única vez)
```

---

## 11. QUAIS MÉTRICAS CALCULAR AGORA

### P1.1 — Fase 1 (Esta Sprint)

✅ **Obrigatórias:**

1. **total_eventos**: Count de eventos confirmados
   ```
   SELECT COUNT(*) FROM Eventos WHERE cliente_id = X AND status = "confirmado"
   ```

2. **profissionais_atendidos**: Array único de profissionais
   ```
   SELECT DISTINCT profissional FROM Eventos WHERE cliente_id = X
   ```

3. **servicos_atendidos**: Array único de serviços
   ```
   SELECT DISTINCT servico FROM Eventos WHERE cliente_id = X
   ```

4. **primeira_contato**: Data do primeiro evento
   ```
   SELECT MIN(criado_em) FROM Eventos WHERE cliente_id = X
   ```

5. **ultima_contato**: Data do evento mais recente
   ```
   SELECT MAX(criado_em) FROM Eventos WHERE cliente_id = X
   ```

6. **profissional_mais_frequente**: Moda de profissionais
   ```
   SELECT profissional, COUNT(*) as freq
   FROM Eventos WHERE cliente_id = X
   GROUP BY profissional
   ORDER BY freq DESC
   LIMIT 1
   ```

7. **servico_mais_frequente**: Moda de serviços
   ```
   SELECT servico, COUNT(*) as freq
   FROM Eventos WHERE cliente_id = X
   GROUP BY servico
   ORDER BY freq DESC
   LIMIT 1
   ```

### P1.2+ — Fases Futuras (Não calcular ainda)

❌ **NÃO calcular em P1.1:**

- Taxa de confirmação (evento.confirmado = true %)
- Tempo médio de resposta (diferença entre criação e confirmação)
- Padrão de recorrência (intervalo entre eventos)
- Melhor horário de resposta (cluster de horários)
- Modo de conversa preferido (pessoal vs direto)
- Comportamento de cancelamento (taxa)

---

## 12. QUAIS MÉTRICAS DEIXAR PARA DEPOIS

### P1.2 (Semana 2+)

- [ ] `metricas.taxa_confirmacao_pct`
- [ ] `metricas.tempo_medio_resposta_horas`
- [ ] `metricas.intervalo_medio_dias` (recorrência)
- [ ] `preferencias.modo_conversacao` (pessoal vs direto)

### P1.3+ (Semana 3+)

- [ ] `metricas.melhor_horario` (análise estatística)
- [ ] `metricas.dia_semana_preferido` (Monday efeito)
- [ ] `tendencias.taxa_cancelamento_pct`

### P2 (Depois)

- [ ] Machine learning / clustering
- [ ] Scoring de cliente (hot/warm/cold)
- [ ] Predictive models
- [ ] Analytics avançada

---

## 13. COMO EVITAR DUPLICAÇÃO

### Problema

Cliente pode ser registrado de múltiplas formas:
- evento.cliente_id
- evento.cliente_nome  
- Clientes/{uid}.nome
- MemoriaTemporaria.cliente_nome

**Risco:** Mesmo cliente = múltiplos profiles

### Solução P1

**Usar cliente_id como chave única:**

```
REGRA OURO: cliente_id é a única chave para profile
  - NÃO usar cliente_nome (pode variar: "Suri", "suri", "SURI")
  - SEMPRE normalizar para cliente_id via evento
  - SE cliente_id não existe: usar user_id como fallback

DURANTE criação de evento:
  cliente_id = event_data.get("cliente_id") or user_id
  profile_key = cliente_id  ← SEMPRE usar isto
```

### Validação de Deduplicação

```
ANTES de criar profile, validar:
  1. Path correto: Clientes/{tenant_id}/ClienteProfiles/{cliente_id}
  2. cliente_id não é vazio
  3. cliente_id não tem espaços em branco
  4. cliente_id é alphanumeric (sem caracteres especiais)

SE validação falha:
  LOG error: "cliente_id inválido"
  USAR user_id como fallback
  MARCAR profile como "needs_manual_review"
```

### Limpeza Futura

```
EM P1.2 ou P1.3:
  Rodar script de deduplicação
  Merge profiles duplicados baseado em cliente_nome
  Consolidar histórico
  (Mas P1.1 não faz isto)
```

---

## 14. COMO PRESERVAR COMPATIBILIDADE COM P0

### Princípios

**1. Eventos são IMUTÁVEIS após P0**
```
Clientes/{tenant_id}/Eventos/{event_id}
  ✅ CREATE: adiciona novos campos se necessário (backward compatible)
  ❌ DELETE: nunca deletar eventos
  ❌ RENAME: nunca renomear campos existentes
  ❌ RESTRUCTURE: nunca alterar schema de eventos
```

**2. ClienteProfile não interfere com fluxo de agendamento**
```
handlers/event_handler.py:
  1. Salva evento (P0 existing flow)
  2. Cria profile (NEW, não-blocking)
  3. Retorna sucesso ao cliente

  SE profile falha:
    LOG erro
    CONTINUAR (não bloqueia agendamento)
```

**3. MemoriaTemporaria intocada**
```
Clientes/{tenant_id}/MemoriaTemporaria/contexto:
  ❌ Não adicionar profile references
  ❌ Não mudar cache logic
  ✅ Pode ler profile em P1.2+ (mas não altera)
```

### Checklist de Compatibilidade

- [ ] Evento ainda salva em `Clientes/{tenant_id}/Eventos/{event_id}`
- [ ] Evento mantém estrutura atual (sem renaming)
- [ ] Agendamento funciona sem profile (profile é optional)
- [ ] Fluxo de confirmação não muda
- [ ] Notificações não mudam
- [ ] Cancelamento não muda
- [ ] Relatórios ainda funcionam
- [ ] Testes de agendamento passam sem profile

### Flags de Feature (Opcional)

```
SE necessário, adicionar feature flag:
  
  FEATURE_CLIENTEPROFILE_ENABLED = True/False
  
  NO código:
  IF FEATURE_CLIENTEPROFILE_ENABLED:
    criar_ou_atualizar_profile(...)
  ELSE:
    SKIP
```

---

## 15. TESTES OBRIGATÓRIOS

### Unit Tests (Desenvolvedores)

**test_clienteprofile_creation.py**
```python
def test_profile_created_on_first_event():
  # Arrange: evento novo, cliente novo
  # Act: salvar evento
  # Assert: profile criado com valores iniciais corretos
  
def test_profile_cliente_id_identificado():
  # Arrange: evento com cliente_id
  # Act: salvar
  # Assert: profile.cliente_id = evento.cliente_id
  
def test_profile_multi_tenant_isolated():
  # Arrange: dois tenants, mesmo cliente_id
  # Act: criar eventos em ambos
  # Assert: profiles isolados, sem cross-tenant
  
def test_profile_creation_idempotent():
  # Arrange: evento novo
  # Act: salvar 2x mesmo evento
  # Assert: apenas 1 profile criado
  
def test_profile_update_on_new_event():
  # Arrange: profile já existe
  # Act: novo evento confirmado
  # Assert: total_eventos incrementado
  
def test_profile_profissional_agregado():
  # Arrange: 3 eventos, 2 com Carla, 1 com Bruna
  # Act: atualizar
  # Assert: profissional_mais_frequente = "Carla"
  
def test_profile_nao_bloqueia_agendamento():
  # Arrange: profile creation vai falhar
  # Act: try salvar evento
  # Assert: evento criado mesmo que profile falhe
```

### Integration Tests (QA)

**test_profile_with_real_flow.py**
```python
def test_agendamento_flow_cria_profile():
  # Flow completo: chat → agendamento → confirmação → check profile
  
def test_multiplos_agendamentos_agregam():
  # Multiple eventos do mesmo cliente → profile agrega tudo
  
def test_profile_isolado_por_tenant():
  # Dois tenants, mesmo cliente → profiles separados
  
def test_cancelamento_nao_afeta_profile():
  # Cancelar evento → profile continua igual (não remove)
```

### Manual Tests (Tester)

**Checklist de Verificação Manual**

- [ ] Agendar evento → profile criado em Firestore
- [ ] Agendar 2º evento → profile atualizado (total_eventos = 2)
- [ ] Trocar profissional → profissional_mais_frequente correto
- [ ] Cancelar evento → profile não muda (ainda conta)
- [ ] Mudar de tenant → profiles isolados
- [ ] Salvar evento sem profissional → profile criado mesmo assim
- [ ] Salvar evento sem serviço → profile criado mesmo assim
- [ ] Agendamento não fica lento (profile async se necessário)

### Test Coverage Mínimo

```
MUST HAVE:
  - 100% coverage de profile creation path
  - 100% coverage de profile update logic
  - 100% coverage de multi-tenant isolation
  - 0% regressão em agendamento P0

NICE TO HAVE:
  - Performance tests (profile update < 100ms)
  - Stress tests (1000 profiles)
  - Concurrency tests (múltiplos eventos simultâneos)
```

---

## 16. RISCOS

### Risk Register

| Risco | Severidade | Probabilidade | Mitigação |
|---|---|---|---|
| **Profile creation bloqueia agendamento** | CRÍTICA | Média | Tornar async (não bloqueia agendamento) |
| **Multi-tenant data leakage** | CRÍTICA | Baixa | Validar tenant_id em todo código |
| **Cliente_id não identificado** | Alta | Média | Usar user_id como fallback, LOG warning |
| **Duplicação de cliente** | Média | Alta | Usar cliente_id como key única |
| **Profile desincronizado de eventos** | Média | Baixa | ETL job nightly para reconciliar |
| **Firestore quota excedida** | Média | Baixa | Monitor writes, podem limitar a N updates/dia |
| **Regressão em agendamento** | CRÍTICA | Baixa | Testes rigorosos de P0 |
| **Performance degradation** | Alta | Média | Profile update rápido (<100ms) |

### Mitigation Plan

**Para "bloqueia agendamento":**
```
FAZER profile update ASSÍNCRONO:
  - Salvar evento (síncrono, rápido)
  - Queued job: criar/atualizar profile (assíncrono)
  - Cliente não espera profile
  - Profile pode levar 1-2 segundos
```

**Para "data leakage":**
```
VALIDAR em todo código:
  tenant_id = obter_id_dono(user_id)  # SEMPRE resolver tenant
  path = f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}"
  # Nunca hardcode tenant, sempre derivar
```

**Para "cliente_id não identificado":**
```
IF cliente_id is None or "":
  LOG warning: f"cliente_id not found for event {event_id}, usando fallback"
  cliente_id = user_id
  # Mais seguro que deixar vazio
```

---

## 17. PLANO DE ROLLBACK

### Se der tudo errado

**Cenário 1: Profile creation quebrando agendamento**

```
AÇÃO IMEDIATA:
  1. Feature flag: FEATURE_CLIENTEPROFILE_ENABLED = False
  2. Parar de criar profiles
  3. Agendamento volta ao normal (profiles já criados não afetam)
  4. Investigar root cause
  5. Deploy fix
  6. Reabilitar feature flag

TEMPO DE ROLLBACK: 5 minutos (feature flag)
DADOS PERDIDOS: Nenhum (profiles já criados continuam lá)
```

**Cenário 2: Multi-tenant data leakage**

```
AÇÃO IMEDIATA:
  1. Feature flag OFF
  2. Audit: rodar script para encontrar profiles "errados"
  3. Backup de dados antes de deletar
  4. Deletar profiles com tenant_id errado
  5. Investigar código
  6. Deploy fix com validação
  7. Recriar profiles via ETL job

TEMPO DE ROLLBACK: 1-2 horas (auditoria + fix)
DADOS PERDIDOS: Histórico de profiles (pode recriar de eventos)
```

**Cenário 3: Performance degradation**

```
AÇÃO IMEDIATA:
  1. Feature flag OFF
  2. Agendamento volta ao normal
  3. Análise de performance: qual operação lenta?
  4. Otimizar (índice, batch, cache, etc)
  5. Deploy fix
  6. Reabilitar

TEMPO DE ROLLBACK: 5 minutos
DADOS PERDIDOS: Nenhum
```

### Passos de Rollback Padrão

```
1. DISABLE feature flag (imediato, < 1 minuto)
2. MONITOR agendamento (tudo normal? sim/não)
3. COMMUNICATE com time (problema identificado)
4. ANALYZE root cause (durante next 30 min)
5. FIX código (durante next 1-2 horas)
6. TEST em staging (durante next 1 hora)
7. DEPLOY fix (durante next 30 min)
8. ENABLE feature flag
9. MONITOR próximas 2 horas (sem problemas?)
10. POST-MORTEM (por quê falhou? como prevenir?)
```

### Backup de Dados

```
ANTES de deploy:
  - Backup de Clientes/{tenant_id}/ClienteProfiles/*
  - Conservar por 30 dias
  - Verificar que backup é restaurável

DURANTE rollback:
  SE precisar, restaurar de backup
  Perder profiles criados depois do backup (aceitável em P1)
```

---

## SUMMARY

### Checklist Pré-Implementação

- [ ] Schema aprovado (seção 4)
- [ ] Identificação de cliente_id definida (seção 7)
- [ ] Lógica de criação revisada (seção 8)
- [ ] Lógica de atualização revisada (seção 9)
- [ ] Testes escritos (seção 15)
- [ ] Compatibilidade P0 validada (seção 14)
- [ ] Riscos mitigados (seção 16)
- [ ] Plano de rollback aprovado (seção 17)
- [ ] Feature flag implementada (opcional)
- [ ] Monitores de Firestore configurados

### GO/NO-GO Decision

**PODE INICIAR IMPLEMENTAÇÃO quando:**

✅ Todo checklist acima marcado  
✅ Code review de esta spec aprovado  
✅ Team agreement em approach  
✅ Staging environment pronto  

---

## PRÓXIMOS PASSOS

1. **Implementação:** Começar por seção 8 (criar profile) e seção 9 (atualizar)
2. **Teste:** Executar testes da seção 15
3. **Deploy:** Staging → Produção com feature flag OFF → ON
4. **Monitoramento:** 2 horas de observação
5. **P1.2:** Depois de 2-3 dias de P1.1 em produção, iniciar histórico inteligente

---

**Versão:** 1.0  
**Revisor:** [Pendente]  
**Aprovação:** [Pendente]  
**Data Aprovação:** [Pendente]  
