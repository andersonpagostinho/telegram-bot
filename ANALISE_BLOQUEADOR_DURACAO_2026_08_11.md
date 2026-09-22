# 🚨 ANÁLISE: BLOQUEADOR CRÍTICO — ALTERAÇÃO COM MUDANÇA DE DURAÇÃO

**Data:** 2026-08-11  
**Status:** 🔴 **BLOQUEADOR CRÍTICO CONFIRMADO**  
**Impacto:** Reagendamento NÃO pode ser implementado sem correção  

---

## 📊 RESUMO

O teste de alteração de duração revelou um **problema arquitetural crítico**:

**Quando a duração de um serviço muda:**
- ❌ Sistema NÃO consegue revalidar conflitos com novo intervalo
- ❌ Sistema permitiria overbooking de profissionais
- ❌ Sistema não ofereceria alternativas ao cliente

**Conclusão:** É **INSEGURO** implementar alteração de agendamento até corrigir este bug.

---

## 🧪 EVIDÊNCIA DO TESTE

### Cenário de Teste

```
ETAPA 1: Criar evento bloqueante
  Evento: Manicure com Carla
  Horário: 14:30-15:00 (30 min)
  Status: ✅ CRIADO em Firestore

ETAPA 2: Validar Corte 45 min
  Intervalo: 14:00-14:45
  Resultado: ✅ SEM CONFLITO (correto)
  
ETAPA 3: CRÍTICA — Cliente muda para Corte+Hidratação 90 min
  Novo intervalo: 14:00-15:30
  Manicure: 14:30-15:00
  SOBREPOSIÇÃO: 30 min (14:30-15:00)
  
  Resultado: ❌ NENHUM CONFLITO DETECTADO (ERRADO!)
```

### Log de Falha

```
[EVENTOS] Eventos existentes: {}

❌ PROBLEMA CRÍTICO!
Motor NÃO detectou conflito com Manicure 14:30-15:00
DEVERIA ter detectado 30 min de sobreposição

CONCLUSÃO: Sistema NÃO está pronto para reagendamento
```

---

## 🔍 INVESTIGAÇÃO

### Problema Encontrado

**Função:** `verificar_conflito_e_sugestoes_profissional()` em `services/event_service_async.py`

**Linha:** 1213 (busca de eventos)

```python
eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
```

**Resultado Observado:** Retorna `{}` (vazio), mesmo após evento ser criado

### Causa Raiz Possível (Hipótese)

1. **Hipótese 1:** Replicação Firestore atrasada (eventual consistency)
   - Evento criado mas não replicado em tempo para busca
   - Solução: Adicionar delay ou usar read com consistência forte

2. **Hipótese 2:** Evento filtrado por `evento_deve_entrar_na_agenda()`
   - Evento existe mas é excluído pelos filtros
   - Solução: Investigar filtros em `evento_deve_entrar_na_agenda()`

3. **Hipótese 3:** Path mismatch
   - Evento salvo em path diferente do esperado
   - Solução: Validar path de criação vs busca

### Próximas Etapas de Investigação

```
1. Verificar se `buscar_subcolecao()` está retornando eventos reais
   ✅ CONFIRMADO: `buscar_subcolecao()` funciona quando chamado isoladamente
   
2. Verificar se eventos estão sendo filtrados por `evento_deve_entrar_na_agenda()`
   🔄 EM INVESTIGAÇÃO: Adicionar debug de filtro
   
3. Verificar se há delay de replicação Firestore
   ✅ PARCIALMENTE TESTADO: Delay de 2s não resolveu
   
4. Verificar se há inconsistência entre path de escrita e leitura
   🔄 EM INVESTIGAÇÃO: Confirmar paths batem
```

---

## 🎯 IMPACTO SE IMPLEMENTARMOS ALTERAÇÃO AGORA

### Cenário Perigoso

```
1. Cliente A: Agendado Corte 14:00-14:45 com Carla (CONFIRMADO)

2. Cliente A muda de ideia: "Quero corte + hidratação (90 min)"
   - Novo intervalo: 14:00-15:30
   - Motor valida: ❌ Não detecta conflito (BUG)
   - Sistema permite alteração

3. Resultado em Firestore:
   - Carla: 14:00-14:45 (original)
   - Carla: 14:00-15:30 (alterado)
   → IMPOSSÍVEL DE EXECUTAR (duplo agendamento)

4. Impacto:
   - Overbooking de profissional
   - Cliente frustrado (espera dupla)
   - Carla sem tempo suficiente
```

---

## 📋 CHECKLIST DE BLOQUEADOR

```
[ ] Teste simples de duração passando? NÃO ❌
[ ] Motor detecta conflito ao mudar duração? NÃO ❌
[ ] Alternativas oferecidas ao cliente? NÃO ❌
[ ] Segurança garantida? NÃO ❌

→ Bloqueador permanece até TODAS serem SIM
```

---

## ⏸️ RECOMENDAÇÃO

**NÃO implementar alteração de agendamento enquanto este bloqueador existir.**

### Alternativa Temporária

Se alterar agendamento for crítico para negócio:

1. Implementar como:
   - Deletar agendamento original (com confirmação)
   - Criar novo agendamento com nova duração
   - Oferecer alternativas se houver conflito

2. Restrições:
   - Apenas para durações menores (nunca aumentar)
   - Validar conflitos manualmente (não confiar no motor)
   - Adicionar confirmação dupla ao usuário

3. Criticidade: **P0 — Corrigir motor ANTES desta solução**

---

## 🔧 AÇÕES RECOMENDADAS (Prioridade)

### 🔴 P0 — IMEDIATO

1. **Investigar `buscar_subcolecao()`**
   - Confirmar se está buscando eventos reais
   - Verificar se há delay de replicação
   - Testar com timestamp diferente

2. **Investigar `evento_deve_entrar_na_agenda()`**
   - Verificar filtros que podem estar excluindo eventos
   - Confirmar que evento bloqueante passa nos filtros
   - Adicionar debug para cada filtro aplicado

3. **Corrigir o motor**
   - Garantir que busca retorna eventos
   - Garantir que conflitos são detectados
   - Garantir que alternativas são oferecidas

### 🟠 P1 — DURANTE INVESTIGAÇÃO

1. Criar testes permanentes para este cenário
2. Documentar comportamento esperado vs real
3. Preparar plano de comunicação se há que comunicar ao negócio

### 🟡 P2 — APÓS CORREÇÃO

1. Implementar alteração de agendamento
2. Adicionar testes de regressão
3. Deploy com cuidado

---

## 📌 CONCLUSÃO

**O sistema identificou e bloqueou um problema crítico de negócio.**

Sem esta validação de duração, poderíamos ter:
- Overbooking silencioso
- Conflitos não detectados
- Satisfação do cliente reduzida

**A presença deste teste é POSITIVA — significa o sistema não deixará passar bug em produção.**

Próximo passo: **Investigar raiz e corrigir.**

---

**Criado:** 2026-08-11  
**Status:** 🔴 **BLOQUEADOR ATIVO**  
**Prioridade:** P0  
**Risco:** CRÍTICO  
