# HIERARQUIA DE DOCUMENTOS COMERCIAL — NeoEve

**Data:** 2026-07-27  
**Versão:** 1.0  
**Status:** Referência de Arquitetura Documental  

---

## 🏗️ PIRÂMIDE DE AUTORIDADE

```
                    ┌─────────────┐
                    │  Auditoria  │ (Decisões já tomadas)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Domínio    │ (Arquitetura comercial)
                    │ Comercial   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────────┐
                    │  Catálogo      │ FONTE ÚNICA DA VERDADE
                    │  Comercial     │ (Preços, planos, trial, etc)
                    └──────┬──────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
      ┌─────▼─────┐  ┌─────▼─────┐  ┌────▼──────┐
      │  Trial    │  │  Billing  │  │ Elegib.  │
      │ Contract  │  │ Contract  │  │ Comercial │
      └─────┬─────┘  └─────┬─────┘  └────┬─────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                    ┌──────▼────────────┐
                    │ Conversão Lead-   │ (depende de Trial + Billing)
                    │ Tenant (Futuro)   │
                    └──────┬────────────┘
                           │
                    ┌──────▼──────────┐
                    │ Roteamento      │ (fluxos concretos)
                    │ Comercial       │
                    └──────┬──────────┘
                           │
                    ┌──────▼──────────┐
                    │ Prompt da Eve   │ (implementação)
                    └─────────────────┘
```

---

## 📐 ESTRUTURA

### NÍVEL 1: FUNDAÇÃO

**AUDITORIA_PROMESSA_VS_CAPACIDADE_NEOEVE.md**
- Lacunas identificadas (P0-P3)
- Decisões de voltar a canal único (WhatsApp)
- Define escopo de competência

→ **Autoridade:** Decisões já validadas. Não muda sem revisão ampla.

---

### NÍVEL 2: CONTRATO-MÃE

**CONTRATO_DOMINIO_COMERCIAL_NEOEVE.md (V1.1)**
- Arquitetura de domínios (COMERCIAL, ONBOARDING, OPERACIONAL, BILLING, SUPORTE)
- Roteamento por domínio
- Decisões arquiteturais consolidadas

→ **Autoridade:** Estrutura que todos os documentos seguem. Muda raramente.

---

### NÍVEL 3: FONTE ÚNICA

**CATALOGO_COMERCIAL_NEOEVE.md (V1.2) — 🔒 CONGELADO**

Contém e APENAS:
- ✅ Preços (R$ 87, R$ 117, R$ 157, R$ 247, R$ 347)
- ✅ Planos (SOLO87, SOLOPRO117, STUDIO157, SALAO247, PRO347)
- ✅ Funcionalidades por plano (matriz completa)
- ✅ Limites operacionais (profissionais, clientes, agendamentos, etc.)
- ✅ Trial (duração, cartão, política)
- ✅ Roadmap (Disponível, Em Desenvolvimento, Planejado, Não Suportado)
- ✅ Elegibilidade Comercial (quem, pré-requisitos, upgrade/downgrade, migração)
- ✅ Objeções pré-aprovadas
- ✅ Encaminhamento (quando não responder)

**Regra de Ouro:** Nenhum valor aqui é duplicado em outro documento.

**Exemplo de Conformidade:**
```
✅ CORRETO: "Conforme Catálogo Comercial V1.2, seção 6.1, SOLO87 custa R$ 87/mês"
❌ ERRADO: "SOLO87 custa R$ 87/mês" (sem referência, duplica)
```

→ **Autoridade:** Suprema para valores comerciais. Muda apenas com nova versão oficial.

---

### NÍVEL 4: OPERACIONAL (Referenciam Catálogo)

#### A. CONTRATO_TRIAL_NEOEVE.md (V1.0)

Define **estados, transições, regras operacionais** do trial.

```
[ONBOARDING_PENDENTE]
    ↓
[TRIAL_ATIVO] ← Duração de X conforme Catálogo V1.2
    ↓
[TRIAL_EXPIRADO]
    ↓
[CLIENTE_ATIVO] OU [DELETADO]
```

**O que contém:**
- Estados (não dias específicos)
- Transições possíveis
- Acesso durante cada estado
- Conformidade LGPD

**O que REFERENCIA (não copia):**
- Duração exata: → Catálogo V1.2, Seção 6.2
- Retenção de dados: → Política de Privacidade (TBD)
- Direitos LGPD: → Política de Privacidade (TBD)

**O que NÃO contém:**
- ❌ "Trial é 7 dias" (hardcode) → Use "conforme Catálogo"
- ❌ "Dados deletados em 30 dias" (hardcode) → Use "conforme Política"
- ❌ Questões jurídicas (força maior, indenização) → Termos de Uso (TBD)

→ **Autoridade:** Define fluxo operacional. Referencia, não duplica.

---

#### B. CONTRATO_BILLING_NEOEVE.md (V1.0)

Define **assinatura, renovação, ciclos financeiros**.

```
[CLIENTE_ATIVO]
    ├─ Renovação automática (conforme ciclo)
    ├─ Upgrade/Downgrade possível
    └─ Falha de pagamento → [PAGAMENTO_FALHOU]
```

**O que contém:**
- Estados financeiros
- Ciclos de renovação
- Webhooks com Hotmart
- Upgrade/Downgrade (valores, prorateo)
- Falhas e retries

**O que REFERENCIA (não copia):**
- Preços: → Catálogo V1.2, Seção 6.1
- Elegibilidade de upgrade: → Catálogo V1.2, Seção 5.4
- Reembolso: → Termos de Uso (TBD)

→ **Autoridade:** Define ciclo financeiro. Referencia catálogo para valores.

---

#### C. ELEGIBILIDADE_COMERCIAL (Seção do Catálogo)

Dentro de CATALOGO_COMERCIAL_NEOEVE.md (Seção 5):

- Quem pode contratar (critérios)
- Pré-requisitos (onboarding)
- Elegibilidade por plano
- Regras de upgrade/downgrade
- Restrições comerciais

**É referenciada por:** Eve (validação), Suporte (onboarding), Trial/Billing

→ **Autoridade:** Parte do Catálogo (congelada).

---

### NÍVEL 5: DERIVADO (Futuro)

**CONTRATO_CONVERSAO_LEAD_TENANT.md** (Ainda não criado)

Será criado APÓS aprovação de Trial + Billing porque precisa referenciá-los.

```
Cria Lead
    ↓
    (Elegibilidade conforme Catálogo)
    ↓
    Inicia Trial
    ↓
    (States conforme Contrato de Trial)
    ↓
    Lead paga
    ↓
    (Billing conforme Contrato de Billing)
    ↓
    Tenant ativado
```

→ **Autoridade:** Consolida Trial + Billing. Criada por último.

---

### NÍVEL 6: IMPLEMENTAÇÃO

**Prompt da Eve**
- Respostas sobre preços: → Referencia Catálogo V1.2
- Respostas sobre trial: → Referencia Contrato Trial
- Respostas sobre pagamento: → Referencia Contrato Billing
- Respostas sobre roadmap: → Referencia Catálogo Roadmap

→ **Autoridade:** Zero. Apenas executa o definido acima.

---

## 🔄 FLUXO DE MUDANÇA

### Se mudar preço (ex: SOLO87 de R$ 87 para R$ 77):

```
1. Comercial decide: Novo preço é R$ 77
   ↓
2. Atualizar: CATALOGO_COMERCIAL_NEOEVE.md → V1.3
   ↓
3. Todos os outros documentos recebem aviso: "Catálogo atualizado, revise referências"
   ↓
4. Prompt da Eve atualizado automaticamente (referencia catálogo)
   ↓
5. Fim (nenhum outro documento precisa mudar)
```

### Se mudar duração de trial (ex: 7 dias para 14):

```
1. Produto decide: Trial é 14 dias
   ↓
2. Atualizar: CATALOGO_COMERCIAL_NEOEVE.md → V1.3
   ↓
3. CONTRATO_TRIAL_NEOEVE.md continua igual (já referencia catálogo)
   ↓
4. Implementação: Apenas ajustar constante no código (duração_trial)
   ↓
5. Fim (contrato não muda, apenas valor referenciado)
```

### Se mudar política de retenção de dados:

```
1. Jurídico decide: Retenção é 60 dias, não 30
   ↓
2. Atualizar: POLITICA_PRIVACIDADE_NEOEVE.md (TBD)
   ↓
3. CONTRATO_TRIAL_NEOEVE.md já referencia política, não muda
   ↓
4. Fim (nenhuma mudança em contrato)
```

---

## ✅ CHECKLIST DE CONFORMIDADE

Antes de criar/atualizar qualquer documento, verificar:

### Documento novo referencia corretamente?
```
☐ Preços → Catálogo V1.2, Seção 6.1?
☐ Planos → Catálogo V1.2, Seção 2?
☐ Limites → Catálogo V1.2, Seção 4?
☐ Trial → Contrato de Trial, Seção [X]?
☐ Billing → Contrato de Billing, Seção [X]?
☐ Elegibilidade → Catálogo V1.2, Seção 5?
☐ Roadmap → Catálogo V1.2, Seção 7?
```

### Documento antigo duplica valores?
```
☐ Tem preço explícito (R$ XXX)? → Remover, referenciar catálogo
☐ Tem "trial é 7 dias"? → Remover, referenciar catálogo
☐ Tem "dados deletados em 30 dias"? → Remover, referenciar política
☐ Tem lista de features? → Remover, referenciar catálogo
```

### Versionamento claro?
```
☐ Cabeçalho declara: "FONTE ÚNICA DE VERDADE para [itens]"?
☐ Cabeçalho lista: "Não copie para [documentos]"?
☐ Status está "CONGELADO" ou "RASCUNHO"?
☐ Data de última atualização presente?
```

---

## 📊 MATRIZ DE PROPRIEDADE

| Item | Proprietário | Encontre Em | Referenciado Por |
|------|---|---|---|
| Preços | Comercial | Catálogo V1.2 | Trial, Billing, Eve, Manual |
| Planos | Produto | Catálogo V1.2 | Elegibilidade, Billing, Eve |
| Limites | Engenharia | Catálogo V1.2 | Trial, Billing |
| Trial | Produto | Contrato Trial | Conversão, Eve |
| Billing | Finance | Contrato Billing | Conversão, Eve |
| Elegibilidade | Comercial | Catálogo V1.2 | Eve, Suporte |
| Roadmap | Produto | Catálogo V1.2 | Eve, Marketing (não prometer) |
| LGPD | Jurídico | Política Privacidade | Trial, Billing, Catálogo |
| Termos Gerais | Jurídico | Termos de Uso | Todos |

---

## 🎯 RESUMO EXECUTIVO

**O objetivo desta hierarquia:** Evitar contradições e retrabalho.

**Regras de Ouro:**

1. **Catálogo é fonte única** → Não copie preços/planos para outro documento
2. **Contratos referenciam, não duplicam** → "Conforme Catálogo" em vez de hardcode
3. **Semântica rigorosa** → "Planejado" ≠ "Disponível em breve"
4. **Versionamento claro** → Cada documento sabe se é congelado ou rascunho
5. **Ordem de aprovação** → Catálogo → Trial → Billing → Conversão

**Resultado:** Uma mudança no Catálogo não quebra documentos que já referenciavam.

---

**Hierarquia de Documentos:** 2026-07-27  
**Status:** Referência de Arquitetura  
**Próxima Revisão:** Após aprovação de documentos-chave

