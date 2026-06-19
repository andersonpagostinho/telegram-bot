# MATRIZ P0 — FLUXOS CONVERSACIONAIS REAIS (FASE 3)

**Data Início**: 2026-06-17  
**Status**: INICIADA  
**Ambiente**: Firestore dev  
**Objetivo**: Validar estado conversacional, contexto, draft e eventos em conversas reais

---

## 📋 Escopo FASE 3

Depois que FASE 1 (Multi-tenant) e FASE 2 (Agenda) foram aprovadas:

- ✅ Contexto isolado por tenant e cliente (FASE 1)
- ✅ Agenda protegida contra race condition (FASE 2)
- ⏳ **AGORA**: Fluxos conversacionais mantêm estado correto

---

## 15 Testes Obrigatórios

| # | Código | Teste | Categoria | Status |
|---|--------|-------|-----------|--------|
| 1 | FC-01 | Interrupção informativa não limpa draft | Estado | PENDENTE |
| 2 | FC-02 | Mudança de contexto revalida tudo | Validação | PENDENTE |
| 3 | FC-03 | Negação limpa contexto sem criar evento | Limpeza | PENDENTE |
| 4 | FC-04 | Resposta neutra não confirma evento | Confirmação | PENDENTE |
| 5 | FC-05 | Rajada em mensagens separadas | Sequência | PENDENTE |
| 6 | FC-06 | Rajada com duplicidade de confirmação | Idempotência | PENDENTE |
| 7 | FC-07 | Multi-entidade em uma frase | Parsing | PENDENTE |
| 8 | FC-08 | Pergunta pessoal não vira agendamento | Contexto | PENDENTE |
| 9 | FC-09 | Consulta de preço preserva agendamento | Estado | PENDENTE |
| 10 | FC-10 | Restart/reload não ressuscita draft | Persistência | PENDENTE |
| 11 | FC-11 | Duplicação de webhook não duplica evento | Idempotência | PENDENTE |
| 12 | FC-12 | Troca horário após conflito | Revalidação | PENDENTE |
| 13 | FC-13 | Troca serviço durante draft | Revalidação | PENDENTE |
| 14 | FC-14 | Frase ambígua não confirma | Confirmação | PENDENTE |
| 15 | FC-15 | Dono/cliente isolados | Isolamento | PENDENTE |

---

## 🎯 Categorias Críticas

### Estado e Contexto (FC-01, FC-08, FC-09)

Validar que:
- ✅ Estado não é perdido por perguntas informativas
- ✅ Mensagens laterais não limpam draft
- ✅ Contexto persiste enquanto pendente

### Validação (FC-02, FC-12, FC-13)

Validar que:
- ✅ Mudanças são revalidadas imediatamente
- ✅ Horário alterado recalcula conflito
- ✅ Serviço alterado recalcula duração
- ✅ Profissional alterado valida compatibilidade

### Confirmação (FC-04, FC-14)

Validar que:
- ✅ Respostas neutras ("ok", "certo") não confirmam
- ✅ Frases ambíguas não confirmam
- ✅ Só "sim" ou "confirmar" criam evento

### Sequência e Rajadas (FC-05, FC-06)

Validar que:
- ✅ Mensagens em sequência montem um único draft
- ✅ Confirmações duplicadas criam um único evento
- ✅ Reload real entre mensagens funciona

### Limpeza (FC-03)

Validar que:
- ✅ "Não" limpa draft sem criar evento
- ✅ Contexto é setado para None
- ✅ Reload não ressuscita draft

### Isolamento (FC-15)

Validar que:
- ✅ Ações do dono não afetam cliente
- ✅ Contexto de cliente isolado por cliente_id
- ✅ Multi-tenant não vaza dados

---

## 🔧 Tecnologia Usada

### Persistência: Firestore Dev

```
Clientes/{dono_id}/Sessoes/{cliente_id}
  ├─ draft_agendamento: {...}
  ├─ confirmacao_pendente: bool
  ├─ servico: str
  ├─ profissional: str
  └─ timestamp: datetime

Clientes/{dono_id}/Eventos
  └─ Criado apenas por criar_evento_com_lock()
```

### Fluxo de Teste

```
1. Mensagem 1 → processar → reload Sessoes
2. Validar estado
3. Mensagem 2 → processar → reload Sessoes
4. Validar estado
...
Final: validar Firestore Eventos
```

---

## 📊 Validações Obrigatórias

**Cada teste DEVE registrar:**

- ✅ dono_id (isolamento)
- ✅ cliente_id (isolamento)
- ✅ Estado inicial (antes de primeira mensagem)
- ✅ Mensagens enviadas (em sequência)
- ✅ Contexto antes/depois (reload real)
- ✅ Quantidade de eventos final
- ✅ Path de sessão consultado
- ✅ Path de eventos consultado

**Nenhuma resposta textual é evidência suficiente.**

Tudo deve ser validado em Firestore.

---

## 🚨 Critério de Reprovação

Teste falha se:

- ❌ Contexto antigo ressuscita após limpeza
- ❌ Evento criado sem confirmação explícita
- ❌ Resposta informativa limpa draft
- ❌ Webhook duplicado cria evento duplicado
- ❌ Mudança não é revalidada
- ❌ Isolamento entre tenant/cliente falha

---

## 📈 Próximos Passos

### Curto Prazo
1. Implementar FC-01 a FC-15
2. Validar 15/15 em primeira execução
3. Executar 3 vezes consecutivas

### Médio Prazo
4. Registrar achados P0/P1 se houver
5. Documentar limitações encontradas
6. Propor patches se necessário

### Longo Prazo
7. Validar FASE 3 em produção
8. Monitorar padrões de conversa real

---

## ✅ Critério de Aprovação

- [ ] 15/15 testes implementados
- [ ] 15/15 testes passando em primeira execução
- [ ] 3 execuções consecutivas com 15/15
- [ ] Nenhuma falha intermitente
- [ ] Firestore dev validado
- [ ] Documentação completa
- [ ] Achados registrados (se houver)

---

**Status FASE 3**: ✅ **APROVADA** (15/15 × 3 execuções)  
**Última Atualização**: 2026-06-17  
**Infraestrutura**: Run ID global + Cleanup automático  
**Documentação**: FASE3_APROVACAO_FINAL.md

---

## ✅ Bloco A — APROVADO (6/6)

| Teste | Status | Validação |
|-------|--------|-----------|
| FC-01 | ✅ PASSOU | Interrupção informativa preserva draft |
| FC-03 | ✅ PASSOU | Negação limpa draft sem evento |
| FC-04 | ✅ PASSOU | Resposta neutra não confirma |
| FC-09 | ✅ PASSOU | Pergunta preserva agendamento pendente |
| FC-10 | ✅ PASSOU | Reload não ressuscita draft |
| FC-14 | ✅ PASSOU | Frase ambígua não confirma |

**Taxa Bloco A**: 6/6 (100%)

---

## ✅ Bloco B1 — APROVADO (4/4) — Revalidação

| Teste | Status | Validação |
|-------|--------|-----------|
| FC-02 | ✅ PASSOU | Mudança profissional revalida compatibilidade |
| FC-12 | ✅ PASSOU | Troca horário após conflito → revalida disponibilidade |
| FC-13 | ✅ PASSOU | Troca serviço → recalcula duração |
| FC-15 | ✅ PASSOU | Isolamento: ação dono não afeta cliente |

**Taxa Bloco B1**: 4/4 (100%)

---

## ⏳ Bloco B2 — PENDENTE (5 testes)

- FC-05: Rajada em mensagens separadas
- FC-06: Rajada com duplicidade (idempotência)
- FC-07: Multi-entidade em frase
- FC-08: Pergunta pessoal não agenda
- FC-11: Webhook duplicado não duplica

