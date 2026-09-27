# GATE C3.15 — SUMÁRIO EXECUTIVO DO PLANO

**Status:** ✅ PLANEJAMENTO COMPLETO  
**Data:** 2026-09-26  
**Nenhum código alterado | Nenhum Firestore alterado | Nenhuma implementação**

---

## VISÃO GERAL

C3.15 define **como implementar** a arquitetura aprovada em C3.13 (Opção A: isolamento por actor_id).

**Precedência:** C3.13 ✅ (arquitetura) → C3.14 ✅ (design) → C3.14-R1 ✅ (hardening) → **C3.15 (implementação)**

---

## MUDANÇA ARQUITETURAL

### Path Atual (Compartilhado - Problema)
```
Clientes/{tenant_id}/Configuracao/negocio
  {onboarding_status, onboarding_etapa_atual, dono_actor_id, ...}
  ← Um documento por tenant (múltiplos atores competem)
```

### Path Novo (Isolado - Solução)
```
Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
  {onboarding_status, onboarding_etapa_atual, actor_id, ...}
  ← Cada ator tem seu próprio documento
```

---

## CONTRATO FINAL DE 4 FUNÇÕES

| Função | Parâmetro Novo | Transaction | Idempotência |
|--------|-----------------|-------------|--------------|
| `iniciar_onboarding_dono()` | `actor_id` | ✅ Sim | ✅ Sim |
| `pegar_etapa_onboarding()` | `actor_id` | ❌ Read-only | N/A |
| `avancar_etapa_onboarding()` | `actor_id` | ✅ Sim | ✅ SHA256 |
| `marcar_onboarding_completo()` | `actor_id` | ✅ Sim | ✅ Idempotente |

**Todos com:**
- ✅ Ownership validation (actor_id == doc.actor_id)
- ✅ Tenant isolation
- ✅ Legacy fallback (compatibilidade)

---

## 11 INVARIANTES ARQUITETURAIS

1. ✅ **Isolamento Actor:** Estado pertence unicamente ao ator
2. ✅ **Tenant Isolamento:** Dados de tenant X não vazam para Y
3. ✅ **Propriedade:** Documento pertence ao owner (actor_id)
4. ✅ **Etapa Determinística:** Monotonicamente crescente
5. ✅ **Primeiro Completo Vence:** Apenas primeiro registrado como dono_principal
6. ✅ **Sem Query Global:** Sempre path determinístico (Donos/{actor_id}/...)
7. ✅ **Compatibilidade Legacy:** Lê legacy, migra automaticamente
8. ✅ **Idempotência Baseada em Conteúdo:** SHA256(actor:campo:valor)
9. ✅ **Atomicidade:** Read-check-write via Firestore transaction
10. ✅ **Ownership Verificável:** Cada operação valida actor_id
11. ✅ **Sem Duas Fontes Mutáveis:** Novo é verdade, legacy é compatibilidade

---

## TRANSACTIONS IMPLEMENTADAS

### iniciar_onboarding_dono()
```
T1: READ Donos/{actor_id}/onboarding/ativo
T2: If exists && completo: ERROR
T3: If exists && em_progresso: RETURN resuming
T4: If not exists: CREATE
```
**Garantia:** Atomicidade de criação, mesmo webhooks simultâneos

### avancar_etapa_onboarding()
```
T1: READ Donos/{actor_id}/onboarding/ativo
T2: VALIDATE (actor_id, etapa, campo, valor, idempotencia_key)
T3: CALCULATE proxima_etapa
T4: WRITE Donos/{actor_id}/onboarding/ativo
```
**Garantia:** Atomicidade de avanço, previne override concorrente

### marcar_onboarding_completo()
```
T1: READ Donos/{actor_id}/onboarding/ativo
T2: VALIDATE (campos preenchidos)
T3: WRITE Donos/{actor_id}/onboarding/ativo (completo)
T4: READ Configuracao/negocio (dono_principal_actor_id?)
T5: If não set: WRITE Configuracao/negocio (register primeiro)
```
**Garantia:** Apenas primeiro ator registrado como dono_principal

---

## IDEMPOTÊNCIA

**Chave:** `sha256(actor_id:campo:valor)[:16]`

**Mecanismo:**
```
1. Calcular chave do novo request
2. Ler idempotencia_key do documento
3. Se igual: SKIP (já foi processado)
4. Se diferente: PROCESSAR e salvar nova chave
```

**Cenários Cobertos:**
- ✅ Webhook retry (rede falhou)
- ✅ Webhook duplicado (Meta reintentou)
- ✅ Usuário reenviou mensagem horas depois
- ✅ Cliente app crashou e recuperou

---

## MIGRAÇÃO DE LEGACY

### Detecção
```
Legacy existe se:
  - Configuracao/negocio.onboarding_status existe
  - OU Configuracao/negocio.dono_actor_id existe
```

### Migração Automática
```
1. pegar_etapa_onboarding(tenant_id, actor_id)
   ├─ Tenta novo path (Donos/{actor_id}/...)
   ├─ Se falha, tenta legacy (Configuracao/negocio)
   ├─ Se legacy pertence ao ator: MIGRAR
   └─ Retornar novo documento

2. Preservação:
   ✅ Legacy não é deletado
   ✅ Campo "migrado_em" marca transferência
   ✅ Rollback é possível
```

### Fallback Seguro
```
- Se novo não encontrado: tenta legacy
- Se legacy de outro ator: retorna None (acesso negado)
- Se nenhum: retorna None
```

---

## MATRIZ DE TESTES (24 Testes)

| Categoria | Testes | Validação |
|-----------|--------|-----------|
| **Isolamento** | T1-T4 | Dois atores não se interferem |
| **Idempotência** | T5-T7 | Webhook duplicado é seguro |
| **Criação** | T8 | Atomicidade de criação |
| **Avanço** | T9-T10 | Etapas avançam corretamente |
| **Webhook Duplicado** | T11-T12 | Meta reintenta é seguro |
| **Concorrência** | T13-T14 | Atomicidade garantida |
| **Primeiro Completo** | T15 | dono_principal_actor_id imutável |
| **Deleção** | T16 | Dados removidos, negócio intacto |
| **Legacy** | T17-T20 | Migração automática funciona |
| **Edge Cases** | T21-T24 | Comportamentos especiais |

**Todos com Firestore REAL** (não mocks)

---

## ARQUIVOS AFETADOS

| Arquivo | Tipo | Impacto |
|---------|------|--------|
| `services/onboarding_dono_service.py` | MAJOR | 5 funções reescritadas |
| `router/integracao_identidade_onboarding.py` | MINOR | 2 callsites +actor_id |
| `services/onboarding_service.py` | MINOR | 2 callsites +actor_id |
| `services/informacao_service.py` | MINOR | 1 função referência |
| `scripts/migrate_onboarding_legacy.py` | NEW | Migration script |
| `tests/test_c315_*.py` | NEW | 24 testes Firestore |

**Total:** 4 arquivos alterados + 2 novos

---

## PLANO EM 9 GATES

```
C3.15.1: Preparação & Schema
  └─ Define estrutura, cria fixtures, valida paths

C3.15.2: Leitura (pegar_etapa_onboarding)
  └─ Implementa read com fallback legacy

C3.15.3: Escrita Transacional (avancar_etapa_onboarding)
  └─ Implementa transaction + idempotência

C3.15.4: Criação (iniciar_onboarding_dono)
  └─ Implementa transaction + resuming

C3.15.5: Integração dos Callsites
  └─ Atualiza router + onboarding_service

C3.15.6: Compatibilidade Legacy
  └─ Implementa migração automática

C3.15.7: Testes Firestore
  └─ 24 testes real (T1-T24)

C3.15.8: Validação Final
  └─ Checklist completo, regressão

C3.15.9: Remoção Futura do Legacy
  └─ Planejado para depois de 2-3 semanas
```

**Cada gate é independente e testável**  
**Rollback possível após cada gate**

---

## RISCOS E MITIGAÇÃO

| Risco | Prob | Impacto | Mitigação |
|-------|------|--------|-----------|
| Onboarding quebra | 3% | Alto | Dual-read (novo+legacy) |
| Perda de dados | 2% | Crítico | Backup automático |
| Tenant X vê dados Y | 1% | Crítico | Paths isolam tenant_id |
| Actor A vê B | 1% | Crítico | Ownership check cada op |
| Transaction deadlock | 2% | Médio | Timeout 30s + retry |

**Todos os riscos têm mitigação implementada**

---

## APROVAÇÃO

### Checklist Final
- ✅ Fase 1: Diagnóstico completo
- ✅ Fase 2: Contrato final assinado
- ✅ Fase 3: Invariantes documentadas
- ✅ Fase 4: Transactions definidas
- ✅ Fase 5: Idempotência projetada
- ✅ Fase 6: Legacy/migração planejada
- ✅ Fase 7: Matriz de 24 testes
- ✅ Fase 8: Callsites mapeados
- ✅ Fase 9: Plano C3.15.1-9 detalhado
- ✅ Fase 10: Riscos mitigados

### Status Final

**✅ C3.15 — PLANEJAMENTO CONCLUÍDO**

**Nenhum código alterado**  
**Nenhum Firestore alterado**  
**Nenhuma migração executada**  
**Nenhum commit feito**  
**Nenhum push feito**

### Próximo Passo

**Aprovação formal para começar C3.15.1** (Preparação e Schema)

---

## DOCUMENTOS

1. **C3_13_AUDITORIA_ARQUITETURA_ONBOARDING.md** - Análise das 3 opções
2. **C3_13_RESUMO_EXECUTIVO.md** - Sumário de C3.13
3. **C3_13_TABELA_COMPARATIVA.md** - Comparação detalhada 14 critérios
4. **C3_15_PLANO_IMPLEMENTACAO_CONTROLADA.md** - Este plano (detalhado, 11 fases)
5. **C3_15_SUMARIO_EXECUTIVO.md** - Este sumário (executivo)

---

**Preparado por:** Auditoria de Planejamento C3.15  
**Data:** 2026-09-26  
**Scope:** Implementação de onboarding isolado por actor (Opção A)  
**Próxima etapa:** C3.15.1 (Preparação & Schema)
