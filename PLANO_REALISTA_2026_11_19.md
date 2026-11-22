# 🎯 PLANO DE EXECUÇÃO REALISTA — NEOEVE

**Data:** 2026-11-19  
**Atualizado:** Com prazos REAIS (incluindo review, testes, docs)  
**Timeline Total:** 10-13 meses (1-2 devs)  
**Investimento:** €96K-€146K  

---

## 📋 RESUMO EXECUTIVO

```
HOJE (Semana 1):        Começar Segurança Crítica
SEMANAS 1-16:           Segurança + Bugs (PARALELO)
SEMANAS 17-28:          Billing (4 fases)
SEMANAS 29-56:          IA Roadmap (5 phases)
TOTAL:                  ~13 meses (1 dev) ou ~10 meses (2 devs)
```

---

## 🔴 PHASE A: SEGURANÇA CRÍTICA (Semanas 1-7)

### **A1: Remover Credentials + Rotacionar** (Dias 1-5)

**O que fazer:**
```bash
# 1. Validar se estão commitadas
git log --all --full-history -- firebase_credentials.json

# 2. Se estão, remover do histórico
git filter-branch --force --index-filter \
  'git rm --cached -r firebase_credentials*.json' \
  --prune-empty --tag-name-filter cat -- --all

# 3. Rotacionar credenciais no Firebase
# (Processo manual no Firebase Console)

# 4. Atualizar scripts para usar variáveis de ambiente
```

**Prazos Reais:**
- Implementação: 1 dia
- Code review: 0.5 dias
- Validação: 1 dia
- **SUBTOTAL: 2.5 dias**

---

### **A2: Autenticação Cliente (JWT/OAuth)** (Semanas 2-3)

**O que fazer:**
```python
# 1. Design JWT token structure
#    - Payload: tenant_id, actor_id, permissions, exp
#    - Algoritmo: HS256 ou RS256

# 2. Implementar JWT generation + validation
#    - POST /auth/login → gera JWT
#    - Middleware valida em todas requisições

# 3. Integrar com Firestore
#    - Salvar token + expiry
#    - Validar contra DB a cada requisição

# 4. Testes
#    - 20+ testes: válido, expirado, inválido, replay attack
#    - E2E: login → requisição autenticada
```

**Prazos Reais:**
- Design: 2 dias
- Implementação JWT: 3 dias
- Integração router: 3 dias
- Testes (20+): 4 dias
- Code review: 2 dias
- Docs: 1 dia
- **SUBTOTAL: 2 semanas = 80 horas**

---

### **A3: Guard Tenant Obrigatório** (Semanas 2-3)

**O que fazer:**
```python
# 1. Criar decorator/middleware
#    @guard_tenant_required
#    def alguma_operacao(tenant_id, ...):

# 2. Aplicar em TODAS operações:
#    - router/principal_router.py (16+ pontos)
#    - services/*.py (60+ pontos)
#    - handlers/*.py (20+ pontos)

# 3. Validações:
#    - tenant_id obrigatório
#    - Formato válido (UUID pattern)
#    - Sem injeção de caracteres especiais

# 4. Testes
#    - 30+ testes: válido, inválido, missing, injection attempts
```

**Prazos Reais:**
- Implementar decorator: 1 dia
- Aplicar em 60+ pontos: 3 dias
- Testes (30+): 3 dias
- Code review: 2 dias
- Regressão: 2 dias
- **SUBTOTAL: 2 semanas = 80 horas**

---

### **A4: Validação Entrada (Sanitização)** (Semanas 4-5)

**O que fazer:**
```python
# 1. Criar sanitizer universal
#    - Remove HTML tags
#    - Escapa caracteres especiais
#    - Limita comprimento
#    - Valida formato (email, phone, date, etc)

# 2. Aplicar em TODOS entrada:
#    - Texto de mensagem
#    - IDs de cliente
#    - Dados de formulário
#    - Query parameters

# 3. Testes de segurança
#    - SQL injection attempts
#    - XSS payloads
#    - NoSQL injection
#    - Command injection

# 4. Integração com router
```

**Prazos Reais:**
- Sanitizer library: 2 dias
- Integração router (40+ pontos): 4 dias
- Testes segurança (50+): 5 dias
- Code review: 2 dias
- Docs: 1 dia
- **SUBTOTAL: 2 semanas = 80 horas**

---

### **A5: Encriptação Dados Sensível** (Semanas 6-7)

**O que fazer:**
```python
# 1. Setup Fernet encryption
#    - Gerar encryption key
#    - Armazenar em variável ambiente

# 2. Encriptar campos sensíveis:
#    - Nome cliente
#    - Telefone
#    - Email
#    - Endereço
#    - Histórico de mensagens

# 3. Implementar encrypt/decrypt helpers
# 4. Aplicar em 20+ pontos de leitura/escrita
# 5. Testes
```

**Prazos Reais:**
- Setup: 1 dia
- Implementação: 2 dias
- Integração (20+ pontos): 3 dias
- Testes (25+): 2 dias
- Code review: 1 dia
- **SUBTOTAL: 1.5 semanas = 60 horas**

---

### **A6: Auditoria + Rate Limiting + CORS/CSRF** (Semanas 6-7)

**O que fazer:**
```python
# 1. Auditoria logging
#    - Cada acesso registra: who, what, when, ip
#    - Salva em Firestore audits collection

# 2. Rate limiting
#    - 100 req/min por IP geral
#    - 10 req/min para GPT (caro)
#    - Per-client limits

# 3. CORS/CSRF protection
#    - Allow specific origins
#    - Validate CSRF tokens
```

**Prazos Reais:**
- Auditoria: 2 dias
- Rate limiting: 2 dias
- CORS/CSRF: 1 dia
- Testes: 2 dias
- **SUBTOTAL: 1 semana = 40 horas**

---

### **A7: Penetration Testing + Docs** (Semana 7)

**O que fazer:**
- Manual security testing (50+ vectors)
- Create security.md documentation
- Create auth.md documentation

**Prazos Reais:** 1 semana = 40 horas

---

## **TOTAL SEGURANÇA: 7-8 semanas = 320-400 horas**

(Se 2 devs: Semanas 1-5 paralelo, depois 2 semanas integração = 5-6 semanas)

---

## 🟠 PHASE B: BUG FIXES (Semanas 1-9, paralelo com segurança após semana 5)

### **B1: Race Condition Lock** (Semanas 2-3)

**O que fazer:**
- Usar transação Firestore para delete + create atomicamente
- 15+ testes de concorrência (100 threads simultâneas)
- Validar zero conflitos

**Prazos Reais:** 2 semanas = 80 horas

---

### **B2: Sobrescrita com Vazio** (Semana 2)

**O que fazer:**
- Validação: se novo contexto vazio, manter anterior
- 10+ testes (10 cenários de sobrescrita)

**Prazos Reais:** 1 semana = 40 horas

---

### **B3: Multi-tenant Isolamento** (Semanas 3-4)

**O que fazer:**
- Remover fallback inseguro
- Validação obrigatória de tenant
- 20+ testes multi-tenant

**Prazos Reais:** 2 semanas = 80 horas

---

### **B4: Except Genérico** (Semanas 4-5)

**O que fazer:**
- Encontrar todos 50+ `except:` no código
- Mudar para específico (ValueError, KeyError, etc)
- 30+ testes de erro handling

**Prazos Reais:** 2 semanas = 80 horas

---

### **B5: Draft Não Limpo** (Semana 5)

**O que fazer:**
- Transação: validar → deletar draft → criar evento
- 10+ testes

**Prazos Reais:** 1 semana = 40 horas

---

### **B6: Regressão Completa** (Weeks 8-9)

**O que fazer:**
- Rodar todos 50+ testes
- Validar zero regressão
- E2E tests com Firestore real

**Prazos Reais:** 2 semanas = 80 horas

---

## **TOTAL BUGS: 9 semanas = 360 horas**

(Se 2 devs em paralelo com segurança: 5-6 semanas)

---

## 💰 PHASE C: BILLING (Semanas 17-28, após segurança+bugs)

### **C1: Validação Acesso** (Weeks 1-2)

- Guard no router: validar `acesso_state` antes de GPT
- Bloquear se SUSPENSO
- 15+ testes

**Prazos Reais:** 2 semanas = 80 horas

---

### **C2: Limite de Custo** (Weeks 3-5)

- Schema `Clientes/{id}/custos_mes`
- Validação ANTES chamar GPT
- Dashboard backend
- 20+ testes

**Prazos Reais:** 3 semanas = 120 horas

---

### **C3: Bloqueio Acesso** (Weeks 6-7)

- Quando `SUSPENSO`: bloquear TUDO
- Cascata de bloqueios
- 20+ testes

**Prazos Reais:** 2 semanas = 80 horas

---

### **C4: Dashboard Alertas + Integração** (Weeks 8-12)

- Frontend dashboard (React/Vue)
- Backend API alertas
- Notificações em tempo real
- 30+ testes

**Prazos Reais:** 5 semanas = 200 horas

---

## **TOTAL BILLING: 12 semanas = 480 horas**

---

## 🧠 PHASE D: IA ROADMAP (Semanas 29-56+)

### **D1: Coleta de Dados** (Weeks 1-4)

- Gerar dataset sintético (ou coletar real se em produção)
- 1000+ registros confirmação/cancelamento
- Schema em Firestore

**Prazos Reais:** 4 semanas = 160 horas

---

### **D2: Previsão Cancelamento** (Weeks 5-12)

- Treinar XGBoost
- 50+ testes
- A/B test (2 semanas)
- Validar -15% cancelamentos

**Prazos Reais:** 8 semanas = 320 horas

---

### **D3: Preferências Adaptativas** (Weeks 13-20)

- Similarity matching
- Reordenação sugestões
- Integração motor
- A/B test

**Prazos Reais:** 8 semanas = 320 horas

---

### **D4: Previsão Demanda** (Weeks 21-30)

- Time series ARIMA
- Preços dinâmicos
- Dashboard dono
- A/B test

**Prazos Reais:** 10 semanas = 400 horas

---

### **D5: Recomendações+Anomalias** (Weeks 31-40)

- Clustering K-means
- Anomaly detector
- Churn alerts
- Dashboard

**Prazos Reais:** 10 semanas = 400 horas

---

## **TOTAL IA: 28 semanas = 1120 horas**

---

## 📊 CRONOGRAMA FINAL

```
SEMANAS 1-7:   SEGURANÇA (320-400h)
SEMANAS 1-9:   BUGS (360h, paralelo após sem 5)
SEMANAS 17-28: BILLING (480h)
SEMANAS 29-56: IA (1120h)

1 DEV:  13 meses = 2360 horas = €118K
2 DEVS: 10 meses = 1180 horas = €59K (paralelo)
```

---

## 🎯 INVESTMENT vs ROI

```
Mês 1-7:   Segurança + Bugs + Billing     (€35K)
Mês 8-13:  IA                            (€59K)
TOTAL:     €94K investimento

ROI:
- Mês 8: Billing ativo                    = €0 (fase ramp)
- Mês 10: Fase 2 IA (-15% cancelamentos) = €5K/mês
- Mês 12: Fase 3 IA (+20% confirmação)   = €8K/mês  
- Mês 14: Fase 4 IA (+25% margem)        = €12K/mês
- Mês 16: Fase 5 IA (+30% ticket)        = €40K/mês

Year 1 total: €432K (break-even mês 10)
```

---

## ⚠️ RISCOS REALISTAS

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---|---------|-----------|
| Security audit revela mais vuln | Alta | 2-4 sem | Hire external security firm |
| IA models don't converge | Média | 4-8 sem | Use simpler models first |
| Dados sintéticos ruins | Média | 2-4 sem | Collect real data early |
| Scaling issues | Média | 2-3 sem | Load test durante dev |
| Team turnover | Baixa | 4-8 sem | Documentation obrigatória |

---

## ✅ PRÓXIMOS PASSOS (HOJE)

- [ ] Aprovar cronograma
- [ ] Desig 1-2 devs
- [ ] Começar PHASE A (Segurança) semana que vem
- [ ] Configurar CI/CD para testes automatizados
- [ ] Hiring: security consultant (part-time, semanas 1-7)

---

**STATUS:** 🟢 **PRONTO PARA COMEÇAR**

