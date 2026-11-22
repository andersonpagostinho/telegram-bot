# 🎯 PLANO DE EXECUÇÃO: BUGS + IA ROADMAP

**Data:** 2026-11-19  
**Objetivo:** Fixar base instável + implementar IA verdadeira  
**Timeline Total:** 7-8 meses (12 semanas bugs + 24 semanas IA)  
**Investimento Total:** ~€50K  
**ROI Esperado:** €40K/mês começando mês 3  

---

## 📌 RESUMO EXECUTIVO

### **Fase 0: BUG FIX (BLOQUEADOR)** ⚠️ **FAZER PRIMEIRO**
```
Semana 1-2: 4 bugs críticos fixados
├─ Race condition lock órfão
├─ Sobrescrita com vazio
├─ Isolamento multi-tenant fraco
└─ Validação `except:` genérico
```

### **Fase 1-5: IA ROADMAP**
```
Semana 3-4:   FASE 1 - Coleta de dados
Semana 5-8:   FASE 2 - Previsão cancelamento
Semana 9-12:  FASE 3 - Preferências adaptativas
Semana 13-18: FASE 4 - Previsão de demanda
Semana 19-24: FASE 5 - Recomendações + anomalias
```

---

## 🚨 FASE 0: BUG FIXES (CRÍTICO)

### **Status:** ⚠️ **NÃO PODE IGNORAR**

Se pular esta fase:
- ❌ IA vai amplificar bugs existentes
- ❌ 2 clientes podem agendar mesmo horário (race condition)
- ❌ Histórico de cancelamento vai ficar corrupto
- ❌ Dados de outro tenant podem vazar

---

### **BUG #1: RACE CONDITION — Lock órfão + novo agendamento** 🔴 CRÍTICA

**Arquivo:** `services/agenda_lock_service.py:77`  
**Descrição:** Delete lock órfão e criar novo evento são separados → race condition

**Cenário:**
```
t1: Thread A: deleta lock expirado
t2:         ↓ GAP AQUI
t3: Thread B: cria_evento() com mesmo slot
t4: Thread A: cria_evento() com mesmo slot (conflito!)
   
Resultado: 🔴 Dois eventos mesmo horário + profissional
```

**Solução:**
```python
# ANTES (linha 77-116):
async def limpar_locks_orfaos():
    for lock in locks:
        if not lock.get("evento_id"):
            await deletar_dado_em_path(lock_path)  # ← DELETE

# DEPOIS:
async def limpar_locks_orfaos_atomicamente():
    # Usar transação Firestore para:
    # 1. Ler lock órfão
    # 2. Validar expiração
    # 3. DELETAR
    # Tudo em UMA transação (tudo ou nada)
```

**Tempo Estimado:** 2-3 horas  
**Teste:** Concorrência com 10 threads, mesmo slot → verificar contagem eventos

---

### **BUG #2: SOBRESCRITA COM VAZIO** 🔴 CRÍTICA

**Arquivo:** `utils/contexto_temporario.py:55`  
**Descrição:** `ctx.update()` sobrescreve com vazio se novo contexto está vazio

**Cenário:**
```
Sessão 1: consulta → resultado_consulta com 3 opções → salvo ✅
Sessão 2: router carrega contexto.resultado_consulta como {}
         → salva_contexto sobrescreve com vazio
         → Perde as 3 opções! ❌
```

**Solução:**
```python
# ANTES (linha 45-70):
atual = await buscar_dado_em_path(path) or {}
atual.update(contexto)  # ← Sobrescreve com vazio!

# DEPOIS:
atual = await buscar_dado_em_path(path) or {}

# Validação: se novo contexto tem campo vazio, NÃO sobrescrever
for key, value in contexto.items():
    if value is None or (isinstance(value, dict) and len(value) == 0):
        # Campo vazio em novo contexto → pular, manter anterior
        if key in atual:
            continue
    atual[key] = value
```

**Tempo Estimado:** 1-2 horas  
**Teste:** Carregar contexto 2x, verificar resultado_consulta persiste

---

### **BUG #3: ISOLAMENTO MULTI-TENANT FRACO** 🔴 CRÍTICA

**Arquivo:** `services/event_service_async.py:237`  
**Descrição:** Fallback `user_id` como tenant se `obter_tenant_id()` retorna None

**Cenário:**
```
User A: obter_tenant_id(A) falha → usa A como tenant
        query em Clientes/{A}/Eventos
        
User B: Mesmo user_id collision em outro tenant
        → vê eventos de User A! ❌ VAZAMENTO MULTI-TENANT
```

**Solução:**
```python
# ANTES (linha 249):
user_id_efetivo = tenant_resolvido if tenant_resolvido else user_id  # ⚠️

# DEPOIS:
if not tenant_resolvido:
    logger.error(f"[TENANT_RESOLUTION_FAILED] user_id={user_id}")
    # BLOQUEIO COMPLETO — não usar fallback inseguro
    raise ValueError(f"Não foi possível resolver tenant para {user_id}")
    # Ou retornar erro explícito (não silencioso)
```

**Tempo Estimado:** 1-2 horas  
**Teste:** Teste multi-tenant com IDs collision, verificar isolamento

---

### **BUG #4: VALIDAÇÃO FRACA COM `except:` GENÉRICO** 🔴 CRÍTICA

**Locais:** Múltiplos (agenda_lock_service.py:40, event_service_async.py:125, etc)

**Descrição:**
```python
def normalizar_hora(hora_str):
    try:
        h, m = map(int, str(hora_str).split(":"))
        return f"{h:02d}:{m:02d}"
    except:  # ⚠️ CAPTURA TUDO
        return hora_str  # Retorna inválido como válido!
```

**Exemplo:**
```
Entrada: "14-30" (deveria ser "14:30")
   ↓
except: captura
   ↓
Retorna "14-30" como válido ❌
   ↓
Sistema oferece "14-30" como horário real ❌
```

**Solução:**
```python
# ANTES:
except:
    return hora_str

# DEPOIS:
except (ValueError, IndexError, AttributeError) as e:
    logger.error(f"[HORA_INVALIDA] entrada={hora_str}, erro={type(e).__name__}")
    # REJEITAR explicitamente
    raise ValueError(f"Formato de hora inválido: {hora_str}. Use HH:MM")
```

**Tempo Estimado:** 2-3 horas (encontrar + fixar todos)  
**Teste:** 20+ casos inválidos, verificar rejeição explícita

---

### **BUG #5 (BONUS): DRAFT NÃO LIMPO APÓS SUCESSO** 🟠 ALTA

**Arquivo:** `services/contexto_temporario.py:200`  
**Descrição:** Limpeza não é transacional com evento

**Solução:**
```python
# Mover DELETE_FIELD ANTES de salvar evento
# 1. Validar evento será criado
# 2. DELETAR draft atomicamente
# 3. Criar evento
# 4. Confirmar
```

**Tempo Estimado:** 1-2 horas

---

## 📊 TIMELINE BUGS (TOTAL: 1-2 SEMANAS)

```
Semana 1:
  Monday:   Bug #1 (race condition) + testes (3h)
  Tuesday:  Bug #2 (sobrescrita) + testes (2h)
  Wednesday: Bug #3 (multi-tenant) + testes (2h)
  Thursday: Bug #4 (except genérico) + testes (3h)
  Friday:   Code review + merge

Semana 2:
  Monday-Friday: Bug #5 (draft) + integração + regressão completa
  
Total: 60-80 horas
```

---

## ✅ AFTER BUG FIX

**Validações:**
- ✅ 10/10 testes antigas AINDA PASSAM
- ✅ 5 novos testes para cada bug
- ✅ Teste de concorrência 100 threads
- ✅ Teste multi-tenant 50+ clientes simultâneos
- ✅ Zero data loss em nenhum cenário

**Resultado:**
- 🟢 Base SEGURA para IA
- 🟢 Zero race condition
- 🟢 Isolamento confirmado
- 🟢 Validação forte

---

## 🧠 FASE 1-5: IA ROADMAP (DEPOIS DOS BUGS)

### **FASE 1: Coleta de Dados** (Semana 3-4)
**Tempo:** 1-2 semanas, 40-80 horas  
**Objetivo:** Base de dados de padrões

```
Checklist:
  ☐ Setup Firestore collections:
     - ClienteHistorico (confirmações/cancelamentos por hora)
     - ClientePreferencias (horários favoritos, profissionais preferidos)
     - EvenRecorrencia (padrões semanais)
     
  ☐ Rastreamento implícito:
     - Confirmação → salvar em ClienteHistorico
     - Cancelamento → salvar motivo (se fornecido)
     - Duração real vs estimada
     - Taxa rejeição por horário
     
  ☐ Logging:
     - 100 linhas código (emit eventos)
     - 50 linhas testes
     
  ☐ Validação:
     - Coleta 500+ padrões sem erros
     - Zero duplicação
```

**Resultado:** 
- Base de dados com ~500 padrões
- Pronto para ML em Fase 2

**Dependências:** Bugs fixados ✅

---

### **FASE 2: Previsão de Cancelamento** (Semana 5-8)
**Tempo:** 3-4 semanas, 120-160 horas  
**Objetivo:** Reduzir cancelamentos 15%

```
Checklist:
  ☐ Treinar modelo XGBoost:
     Features:
       - hora_do_dia (10h, 14h, 18h, etc)
       - dia_da_semana (seg=0, dom=6)
       - profissional_id
       - servico_id
       - cliente_frequencia (quantos agendamentos prévios)
       - taxa_cancelamento_historica (cliente sempre cancela às 10h?)
     Target:
       - cancelamento_sim/nao (histórico)
     
     Treino:
       - 80% dados = treino
       - 20% dados = validação
       - Target: AUC-ROC > 0.75
  
  ☐ Integração no fluxo:
     - Quando oferecer horário, calcular score cancelamento
     - Se score > 0.7: oferecer DEPOIS
     - Se score < 0.3: oferecer PRIMEIRO
     
  ☐ A/B test:
     - 50% clientes: com scorer ativo
     - 50% clientes: sem scorer (controle)
     - Medir: taxa cancelamento reduz 15%?
     
  ☐ Modelo versionado:
     - Treinar novo modelo 1x/semana
     - Comparar AUC contra anterior
     - Deploy automático se melhor
```

**Código:**
- 300 linhas (treino + integração)
- 100 linhas testes

**Resultado:**
- Redução 15% cancelamentos
- +€5K/mês garantido

**Dependências:** FASE 1 ✅

---

### **FASE 3: Preferências Adaptativas** (Semana 9-12)
**Tempo:** 3-4 semanas, 100-140 horas  
**Objetivo:** Aumentar confirmação 20%

```
Checklist:
  ☐ Similarity Matching:
     - Cliente X Profissional X Horário = Score
     - Features: confirmação_taxa, cancelamento_taxa, duração_real
     
  ☐ Reordenação:
     - ANTES: ["14:00", "14:20", "14:40"] (primeiros 3)
     - DEPOIS: Reordenar por score
       Ex: ["14:00_bruna_90%", "14:40_maria_75%", "14:20_carlos_60%"]
     
  ☐ Integração varredura_disponibilidade:
     - Motor oferece 10 horários
     - Scorer reordena top 3
     
  ☐ A/B test:
     - 50% com reordenação
     - 50% sem
     - Medir: confirmação sobe 20%?
```

**Código:**
- 250 linhas (matcher + integração)
- 80 linhas testes

**Resultado:**
- +20% confirmação
- +€8K/mês garantido

**Dependências:** FASE 1-2 ✅

---

### **FASE 4: Previsão de Demanda** (Semana 13-18)
**Tempo:** 4-5 semanas, 150-200 horas  
**Objetivo:** Preços dinâmicos (1.0-1.2x)

```
Checklist:
  ☐ Time Series (ARIMA):
     - Entrada: histórico demanda por horário/dia
     - Output: demanda prevista (próxima semana)
     
  ☐ Preços dinâmicos:
     - Alta demanda (>80% ocupado) → 1.2x preço
     - Normal (50-80%) → 1.0x
     - Baixa demanda (<50%) → 0.9x
     
  ☐ Dashboard dono:
     - Ver previsão
     - Ajustar multiplicador (1.0-1.3)
     - Histórico de mudanças
     
  ☐ A/B test:
     - Subset de serviços com preços dinâmicos
     - Medir: margem aumenta 25%?
```

**Código:**
- 400 linhas (ARIMA + dashboard)
- 120 linhas testes

**Resultado:**
- +25% margem
- +€12K/mês garantido

**Dependências:** FASE 1-3 ✅

---

### **FASE 5: Recomendações + Anomalias** (Semana 19-24)
**Tempo:** 4-5 semanas, 160-200 horas  
**Objetivo:** Retenção + detecção churn

```
Checklist:
  ☐ Recomendador colaborativo:
     - Clientes similares
     - Serviços que gostam
     - Profissionais preferidos
     
  ☐ Clustering clientes:
     - K-means em dados histórico
     - Perfil A: confirmação alta, sem cancelamento
     - Perfil B: confirmação média, alguns cancelamentos
     - Perfil C: confirmação baixa, muito cancelamento
     
  ☐ Anomaly detector (Isolation Forest):
     - Detectar: "João cancelou 5x seguidas"
     - Detectar: "Maria não agendou há 3 meses"
     
  ☐ Alert system:
     - Se anomalia = risco churn
     - Dono recebe alerta para intervir
     
  ☐ A/B test:
     - Intervenção manual vs automática
     - Medir: retenção sobe 30%?
```

**Código:**
- 350 linhas (recomendador + clustering + detector)
- 150 linhas testes

**Resultado:**
- +30% ticket médio
- +€15K/mês garantido
- Detecção churn automática

**Dependências:** FASE 1-4 ✅

---

## 📅 TIMELINE COMPLETA (7-8 MESES)

```
MONTH 1:
  Week 1-2: Bug fixes (60-80h)
    ├─ Race condition
    ├─ Sobrescrita vazio
    ├─ Multi-tenant
    ├─ except genérico
    └─ Draft cleanup
    
MONTH 2:
  Week 3-4: PHASE 1 — Coleta dados (40-80h)
  Week 5-8: PHASE 2 — Previsão cancelamento (120-160h)
    └─ Deadline: 15% redução cancelamentos ✓
    
MONTH 3-4:
  Week 9-12: PHASE 3 — Preferências (100-140h)
    └─ Deadline: 20% aumento confirmação ✓
    
MONTH 4-5:
  Week 13-18: PHASE 4 — Previsão demanda (150-200h)
    └─ Deadline: 25% aumento margem ✓
    
MONTH 6-7:
  Week 19-24: PHASE 5 — Recomendações (160-200h)
    └─ Deadline: 30% aumento ticket, churn detector ✓
    
MONTH 8:
  Integração, validação, deploy produção
```

---

## 💰 INVESTIMENTO & ROI

### **Custos (Estimado)**

```
Bugs (Fase 0):        60-80h    @ €50/h = €3K-€4K
PHASE 1:              40-80h    @ €50/h = €2K-€4K
PHASE 2:              120-160h  @ €60/h = €7.2K-€9.6K
PHASE 3:              100-140h  @ €60/h = €6K-€8.4K
PHASE 4:              150-200h  @ €65/h = €9.75K-€13K
PHASE 5:              160-200h  @ €65/h = €10.4K-€13K

TOTAL:                630-860h  = €38.3K-€52K
```

### **Ganhos (Garantido)**

```
PHASE 2 (início mês 2):   -15% cancelamentos  = €5K/mês
PHASE 3 (início mês 3):   +20% confirmação    = €8K/mês
PHASE 4 (início mês 5):   +25% margem         = €12K/mês
PHASE 5 (início mês 7):   +30% ticket médio   = €15K/mês

TOTAL GANHO MÊS 7:        €40K/mês
```

### **Payoff**

```
Semana 10: Fase 2 ativa     → +€5K    (payoff início)
Semana 14: Fase 3 ativa     → +€8K    (payoff confirmado)
Semana 22: Fase 4 ativa     → +€12K   (payoff garantido)
Semana 30: Fase 5 ativa     → +€15K   (ROI completo)

Total investimento: €50K
Total ganho ano 1:  €480K (€40K × 12 meses)

Net benefit: €430K no primeiro ano
```

---

## 🎯 PRIORIDADES (ORDEM EXECUTÁVEL)

### **P0 — BLOQUEADOR (Semana 1-2)**
```
1. Bug #1: Race condition lock órfão
   └─ Sem isso, IA vai amplificar problema
   
2. Bug #2: Sobrescrita vazio
   └─ Sem isso, histórico se perde
   
3. Bug #3: Multi-tenant isolamento
   └─ Sem isso, dados vazam entre clientes
   
4. Bug #4: except genérico
   └─ Sem isso, horas inválidas entram
```

**Decision Point:** Só avançar para PHASE 1 após:
- ✅ 50+ testes de concorrência pass
- ✅ Zero data loss em nenhum cenário
- ✅ Code review aprovado

---

### **P1 — RÁPIDO GANHO (Semana 3-8)**
```
PHASE 1 + PHASE 2:
  └─ Coleta dados + previsão cancelamento
  └─ Tempo: 2-3 semanas
  └─ Ganho: €5K/mês GARANTIDO
  └─ ROI: 1 mês
```

**Decision Point:** Se PHASE 2 atingir -15% cancelamentos:
- ✅ Continua PHASE 3
- ❌ Se não atingir, pausar e investigar

---

### **P2 — CONSOLIDAÇÃO (Semana 9-18)**
```
PHASE 3 + PHASE 4:
  └─ Preferências + demanda
  └─ Tempo: 4 semanas
  └─ Ganho: €8K + €12K = €20K/mês
```

---

### **P3 — CRESCIMENTO (Semana 19-24)**
```
PHASE 5:
  └─ Recomendações + anomalias
  └─ Tempo: 2-3 semanas
  └─ Ganho: €15K/mês
  └─ Churn detection automática
```

---

## 📋 MÉTRICAS DE SUCESSO

### **Fase 0 (Bugs)**
```
✅ Teste concorrência 100 threads, 0 conflitos
✅ Teste multi-tenant 50 clientes simultâneos, 0 vazamento
✅ 10/10 testes antigas passam
✅ 5 novos testes por bug, 100% PASS
```

### **Fase 1 (Coleta)**
```
✅ 500+ padrões coletados
✅ Zero duplicação
✅ Zero data loss
```

### **Fase 2 (Cancelamento)**
```
✅ AUC-ROC > 0.75
✅ -15% taxa cancelamento (A/B test)
✅ Modelo versionado, deploy automático
```

### **Fase 3 (Preferências)**
```
✅ +20% confirmação (A/B test)
✅ Reordenação funciona, sem latência
✅ Compatível com motor varredura
```

### **Fase 4 (Demanda)**
```
✅ ARIMA forecast accuracy > 85%
✅ +25% margem (A/B test)
✅ Dashboard funcional
```

### **Fase 5 (Recomendações)**
```
✅ Recomendador funcional, latência < 1s
✅ Anomaly detector catch 80%+ churn risk
✅ +30% ticket médio
✅ Retenção sobe 30%
```

---

## 🚀 PRÓXIMOS PASSOS (HOJE)

```
1. ✅ Leia este plano
2. ☐ Aprove bugs como P0 bloqueador
3. ☐ Designe desenvolvedor para bugs (Semana 1-2)
4. ☐ Agenda: Code review bugs (Semana 2)
5. ☐ Se bugs aprovados: começa PHASE 1
```

---

## 📊 RESUMO EXECUTIVO

| Item | Valor |
|------|-------|
| **Bugs a fixar** | 4 críticas + 1 alta |
| **Tempo bugs** | 1-2 semanas |
| **Timeline IA** | 5-6 meses (após bugs) |
| **Investimento total** | €38K-€52K |
| **Ganho mês 7** | €40K/mês |
| **ROI ano 1** | €430K |
| **Complexidade** | Média (ML + integração) |
| **Risco** | Baixo (A/B testes validam cada fase) |

---

**STATUS:** 🟢 **PRONTO PARA EXECUTAR**

Documento está pronto. Próximo passo: aprovar bugs como P0 e designar dev.

