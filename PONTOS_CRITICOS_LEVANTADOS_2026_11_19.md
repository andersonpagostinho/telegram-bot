# ⚠️ PONTOS CRÍTICOS LEVANTADOS — 2026-11-19

## ✅ PONTOS CONFIRMADOS

### **PHASE 0: 4 BUGS CRÍTICOS**
- [ ] Bug #1: Race condition lock órfão (2-3h)
- [ ] Bug #2: Sobrescrita com vazio (1-2h)
- [ ] Bug #3: Multi-tenant isolamento (1-2h)
- [ ] Bug #4: except: genérico (2-3h)
- [ ] Bug #5: Draft não limpo (1-2h)

**Status:** Precisa ser feito ANTES de tudo

---

### **PHASE 00: BILLING CRÍTICO (INCOMPLETO)**

#### **00A: Validação de Acesso** ⚠️
- [ ] Guard no router: validar `acesso_state` ANTES de GPT
- [ ] Bloquear se `acesso_state == "SUSPENSO"`
- [ ] Retornar erro claro: "Acesso suspenso por falta de pagamento"
- **Tempo:** 1-2 dias

#### **00B: Limite de Custo GPT** ⚠️
- [ ] Criar schema `Clientes/{id}/custos_mes`
- [ ] Validar ANTES de chamar GPT
- [ ] `if novo_custo + total > limite: bloqueia`
- **Tempo:** 2-3 dias

#### **00C: Bloqueio de Acesso Completo** ⚠️
- [ ] Quando `AcessoState.SUSPENSO`: bloquear TUDO
- [ ] Não apenas GPT, mas todas operações
- [ ] Mensagem clara de bloqueio
- **Tempo:** 1 dia

#### **00D: Dashboard de Alertas** ⚠️
- [ ] Endpoint: `GET /dono/alertas-uso`
- [ ] Mostrar: custo_mes, limite, percentual, status
- [ ] Alertas quando >50%, >100%
- **Tempo:** 3-5 dias

**DESCOBERTA:** Sistema registra custo GPT DEPOIS (passivo), não bloqueia ANTES (ativo)

**Status:** Precisa ser implementado IMEDIATAMENTE APÓS bugs

---

### **PHASE 1-5: IA ROADMAP** (DESCRITO EM DETALHE)
- [ ] PHASE 1: Coleta de dados (Semana 3-4)
- [ ] PHASE 2: Previsão cancelamento (Semana 5-8)
- [ ] PHASE 3: Preferências adaptativas (Semana 9-12)
- [ ] PHASE 4: Previsão de demanda (Semana 13-18)
- [ ] PHASE 5: Recomendações+anomalias (Semana 19-24)

**Status:** Pronto para começar APÓS Phase 00

---

## 🔐 SEGURANÇA — ANÁLISE COMPLETA ✅

**Arquivo:** `AUDITORIA_SEGURANCA_2026_11_19.md`

### **🔴 CRÍTICAS (Precisa fazer AGORA):**
1. ✅ Credenciais NO repositório (firebase_credentials.json)
2. ✅ SEM autenticação cliente (qualquer um com IDs pode acessar)
3. ✅ SEM autorização/isolamento tenant (fallback inseguro)
4. ✅ SEM validação entrada (XSS, injection possível)

### **🟠 ALTAS (Semana 1-2):**
5. Sem encriptação dados em repouso
6. Sem auditoria de acesso
7. Sem rate limiting
8. Sem CORS/CSRF
9. GDPR/LGPD não implementado

### **Status:** ⚠️ **NÃO PRONTO PARA PRODUÇÃO COM DADOS REAIS**

**Recomendação:** Fixar 4 críticas PRIMEIRO, depois Phase 00 billing, depois Phase 0 bugs, depois IA roadmap.

