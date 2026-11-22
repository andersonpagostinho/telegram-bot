# 📋 BRIEFING PARA SEGUNDA OPINIÃO — NEOEVE

**De:** Claude Haiku (análise inicial)  
**Para:** GPT com memória do projeto  
**Data:** 2026-11-19  
**Objetivo:** Validar/questionar meus achados. O que EU perdi? Onde estou errado?

---

## 🎯 CONTEXTO

Sistema: **NeoEve** — Booking de salão via WhatsApp (Brasil)
- 85% BOT determinístico + 10% IA (GPT) + 5% híbrida
- Multi-tenant (salões múltiplos)
- Firestore persistence
- 16K linhas router + 70+ services + 127K linhas testes

**Estado:** Operacional mas com 4 bugs críticos + falhas segurança

---

## ✅ O QUE EU CONCLUÍ (Valide isso!)

### **ARQUITETURA**

```
✅ CONFIRMAR:
  - Motor varredura 100% BOT (loop 20 em 20 min)
  - Reutilização intenção linha 6619 (NÃO chama GPT se tem cache)
  - GPT APENAS se intenção == "indefinida" (linha 6894)
  - 10 campos persistem entre sessões em Firestore
  - Aprende CONTINUIDADE (retoma onde parou) mas NÃO PADRÕES
  
❓ QUESTIONAR:
  - Encontrei guard_tenant.py? Validação tenant é realmente forte?
  - Motor de conflito (verificar disponibilidade) — é 100% correto?
  - Lock service — race condition é realmente CRÍTICA ou marginal?
```

---

### **BUGS CRÍTICOS**

```
🔴 ENCONTRADOS (Confirmar):
  1. Race condition lock órfão (agenda_lock_service:77)
  2. Sobrescrita com vazio (contexto_temporario:55)
  3. Fallback inseguro multi-tenant (event_service:237)
  4. except: genérico (50+ locais no código)
  5. Draft não limpo após sucesso (contexto_temporario:200)

❓ QUESTIONAR:
  - Há MAIS bugs que eu não encontrei?
  - Esses 5 são REALMENTE críticos ou Low priority?
  - Qual deveria ser fixado PRIMEIRO?
```

---

### **SEGURANÇA**

```
🔴 CRÍTICAS (Confirmar):
  - Credentials NO repositório (firebase_credentials.json)
  - SEM autenticação cliente (qualquer ID → acesso)
  - SEM autorização/guard tenant obrigatório
  - SEM validação entrada (XSS/injection possível)

🟠 ALTAS (Confirmar):
  - SEM auditoria de acesso
  - SEM encriptação dados sensível
  - SEM rate limiting
  - SEM CORS/CSRF
  - GDPR/LGPD não implementado

❓ QUESTIONAR:
  - Faltam OUTRAS vulnerabilidades que não vi?
  - Qual é a ORDEM DE PRIORIDADE certa?
  - E autenticação com WhatsApp? É suficiente?
```

---

### **BILLING (INCOMPLETO)**

```
✅ ENCONTRADO:
  - Máquinas de estado (Trial, Assinatura, Pagamento, Acesso, Retenção)
  - Rastreamento custo GPT em custos_gpt.py
  - AcessoState.SUSPENSO existe

❌ FALTA:
  - Guard no router validando acesso_state ANTES de GPT
  - Limite de custo por cliente
  - Alertas de alto uso
  - Dashboard para dono ver consumo

❓ QUESTIONAR:
  - Billing está EM PRODUÇÃO ou skeleton?
  - Sistema bloqueia cliente suspenso REALMENTE?
  - Como é calculado custo — está correto?
```

---

## 🤔 MINHAS DÚVIDAS (Para você responder)

### **SOBRE ARQUITETURA**

1. **Reutilização de intenção (linha 6619):**
   - Timeout? Quanto tempo reutiliza antes de recalcular?
   - Que eventos FORÇAM recalcular mesmo com cache?

2. **Persistência:**
   - Qual exatamente é a "continuidade" que sistema aprende?
   - Por que "não aprende PADRÕES"? Qual seria diferença?

3. **Isolamento tenant:**
   - Há query que valida `tenant_id` obrigatoriamente em TODAS operações?
   - Ou algumas passam sem validar?

---

### **SOBRE TESTES**

1. **10/10 testes passam — mas:**
   - Existem testes de segurança (injection, xss)?
   - Existem testes de concorrência (race conditions)?
   - Existem testes de multi-tenant (isolamento)?

2. **E2E com Firestore real:**
   - Validam com múltiplos clientes simultâneos?
   - Ou apenas single-tenant test?

---

### **SOBRE PRAZOS**

1. **Meus prazos estão realistas?**
   - Segurança 7 semanas (320h) — parece muito? Pouco?
   - Bugs 9 semanas (360h) — adequado?
   - Billing 12 semanas (480h) — fazer sentido?

2. **Paralelo é possível?**
   - Segurança + Bugs podem rodar paralelo após semana 5?
   - Ou Bugs precisa de Segurança completa primeiro?

---

### **SOBRE PRIORIDADES**

1. **Qual é a ORDEM certa?**
   - Meu plano: Segurança → Bugs → Billing → IA
   - Faz sentido ou é diferente?

2. **GPT está em produção AGORA?**
   - Ou é algo a ativar no futuro?
   - Qual é o custo GPT mensal HOJE?

---

## 🔍 COISAS QUE EU NÃO LI

```
Arquivos que NÃO abri ainda:
  - main.py (integração)
  - Integração com WhatsApp real
  - Scripts de deployment
  - CI/CD pipeline
  - Monitoring/alertas em produção
  - Histórico de issues/bugs
  - Commits recentes (últimos 50?)
  - Performance tests (latência, throughput)
  - Database schema (Firestore estrutura)
  
❓ Desses, qual é CRÍTICO para eu ter entendido?
```

---

## 📊 MATRIZ DE CONFIANÇA

| Aspecto | Confiança | Razão |
|---------|-----------|-------|
| Arquitetura geral | 85% | Leitura profunda router + services |
| Bugs críticos | 70% | Encontrados em código, NÃO testei |
| Segurança | 60% | Leitura superficial, sem pentesting |
| Prazos | 40% | Baseados em estimativa, não experiência |
| Prioridades | 50% | Lógico, mas pode estar errado |

---

## 🎯 PERGUNTAS DIRETAS

**Se você tem memória do projeto, responda:**

1. **Qual é o BUG mais crítico REALMENTE?**
   - Meu voto: Race condition (pode corromper DB)
   - Ou outro?

2. **Qual é a VULNERABILIDADE mais crítica?**
   - Meu voto: Falta autenticação cliente
   - Ou outro?

3. **Quanto tempo REALMENTE leva:**
   - Implementar JWT seguro? (Meu voto: 2 semanas)
   - Fixar race condition? (Meu voto: 2 semanas)
   - Implementar billing completo? (Meu voto: 12 semanas)

4. **System está em produção COM CLIENTES REAIS?**
   - Se SIM: qual é o risco de fazer essas mudanças?
   - Se NÃO: posso fazer breaking changes?

5. **Há OUTRO Tim trabalhando nisso?**
   - Se SIM: como evitar conflitos?
   - Se NÃO: posso mexer em TUDO sem coordenação?

---

## 🚀 MINHA RECOMENDAÇÃO (que pode estar errada)

```
FASE 0 (HOJE):
  → Começar segurança crítica IMEDIATAMENTE
  → Remover credentials do repo HOJE
  → Não deployar nada até segurança mínima

FASE 1 (Semanas 1-7):
  → Segurança crítica em paralelo com bugs quando possível
  → Code review de CADA mudança

FASE 2 (Semanas 8-20):
  → Billing + regressão completa
  → Validação em staging com múltiplos clientes

FASE 3 (Semana 21+):
  → IA roadmap (se sistema estável)
```

---

## ✅ O QUE EU PRECISO DE VOCÊ

```
1. VALIDAÇÃO: Meus achados estão certos?
2. CORREÇÃO: Onde estou errado?
3. ADIÇÃO: O que EU PERDI?
4. PRIORIZAÇÃO: Qual ordem é CERTA?
5. REALISMO: Meus prazos fazem sentido?
6. CONTEXTO: System está em produção? Com clientes?
```

---

**POR FAVOR RESPONDA:** O que você vê que eu não vi? Qual é o problema REAL que eu não identifiquei?

