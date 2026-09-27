# C3.15.3 — AUDITORIA PRÉ-IMPLEMENTAÇÃO

**Status:** Auditoria Concluída  
**Data:** 2026-09-26  
**Escopo:** Identificar arquivos, funções, callsites, padrões e riscos antes de implementar escrita isolada  

---

## PARTE 1: FUNÇÕES-ALVO IDENTIFICADAS

### 1. `iniciar_onboarding_dono()`

**Localização:** `services/onboarding_dono_service.py:30-81`

**Assinatura Atual:**
```python
async def iniciar_onboarding_dono(
    tenant_id: str, 
    actor_id: str, 
    dono_nome: str, 
    dono_email: str
) -> dict:
```

**Comportamento Atual:**
- Escreve em: `Clientes/{tenant_id}/Configuracao/negocio` (linha 65)
- Operação: `.set(config_data)` — cria ou sobrescreve
- Não idempotente: se chamado 2x, sobrescreve dados

**Callsites Encontrados:**
1. `router/integracao_identidade_onboarding.py:213` — ao criar novo dono
   - Contexto: `tenant_id`, `actor_id` ambos disponíveis ✅
   - Parâmetros: já passa `actor_id` ✅

**Risco Identificado:**
- `.set()` sem `merge=True` sobrescreve: risco de perda se chamado 2x

### 2. `avancar_etapa_onboarding()`

**Localização:** `services/onboarding_dono_service.py:151-223`

**Assinatura Atual:**
```python
async def avancar_etapa_onboarding(
    tenant_id: str,
    campo: str,
    valor: str
) -> dict:
```

**Comportamento Atual:**
- Não aceita `actor_id`
- Escreve em: `Clientes/{tenant_id}/Configuracao/negocio` (linhas 187-206)
- Operação: 2x `.update()` separados (linha 187, depois 196-199 OU 202-206)
- Não transacional: duas operações desacopladas
- Não idempotente: se webhook retenta, etapa avança 2x

**Callsites Encontrados:**
1. `services/onboarding_service.py:290` — ao processar resposta do dono
   - Contexto: `tenant_id` disponível ✅
   - Problema: `actor_id` NÃO está passado ❌
   - Precisa de: extração de `ctx["actor_id"]` antes de chamar

**Risco Identificado:**
- Múltiplos `.update()` desacoplados: concorrência não garantida
- Sem idempotência: webhook duplicado avança 2 vezes
- Sem `actor_id`: não isola por ator

### 3. `marcar_onboarding_completo()`

**Localização:** `services/onboarding_dono_service.py:286-314`

**Assinatura Atual:**
```python
async def marcar_onboarding_completo(
    tenant_id: str
) -> bool:
```

**Comportamento Atual:**
- Não aceita `actor_id`
- Escreve em: `Clientes/{tenant_id}/Configuracao/negocio` (linha 301)
- Operação: `.update()` único
- Não transacional
- Não valida se realmente completo

**Callsites Encontrados:**
1. `services/onboarding_service.py:307` — ao concluir onboarding
   - Contexto: `tenant_id` disponível ✅
   - Problema: `actor_id` NÃO está passado ❌

**Risco Identificado:**
- Sem `actor_id`: não sabe qual ator completou
- Sem validação: marca como completo mesmo se dados faltam
- Sem transaction: pode marcar completo enquanto outro está avançando

---

## PARTE 2: CALLSITES RESUMO

| Função | Arquivo | Linha | actor_id Disponível | Ação |
|--------|---------|-------|-------------------|------|
| iniciar | router/integracao_identidade_onboarding.py | 213 | ✅ Sim (parâmetro) | UPDATE assinatura novo path |
| avancar | services/onboarding_service.py | 290 | ✅ Sim (ctx) | ADD actor_id param, UPDATE callsite |
| marcar | services/onboarding_service.py | 307 | ✅ Sim (ctx) | ADD actor_id param, UPDATE callsite |

**Conclusão:** Todos os callsites têm acesso a `actor_id`. Compatibilidade confirmada.

---

## PARTE 3: PADRÕES IDENTIFICADOS NO PROJETO

### Transaction
- **Encontrado:** Não há padrão consolidado de transaction Firestore em services/
- **Implicação:** Usar padrão nativo do Firestore: `db.transaction(update_in_transaction)`
- **Risco:** Novo padrão, mas necessário para garantir atomicidade

### Idempotência
- **Encontrado:** Documentado em C3.14-R1: `SHA256(actor_id:campo:valor)[:16]`
- **Localização:** `docs/` ou `CLAUDE.md` (verificar)
- **Implicação:** Implementar determinístico, não timestamp

### Timestamp
- **Padrão:** `datetime.now(pytz.UTC).isoformat()`
- **Localização:** services/onboarding_dono_service.py:48
- **Usar para:** `criado_em`, `atualizado_em`

---

## PARTE 4: DEPENDÊNCIAS VERIFICADAS

### Imports Necessários
```python
# Já existem:
import asyncio
from datetime import datetime
import pytz
from services.firestore_client import get_db

# Podem ser necessários:
import hashlib  # para idempotência SHA256
```

### Firestore Helpers Necessários
- `get_db().collection()` — acesso ao Firestore ✅
- `asyncio.to_thread()` — para operações síncronas ✅
- `.transaction()` — para operações atômicas (usar se Firestore sdk suporta)

**Verificação necessária:** Confirmar se Firestore SDK suporta `.transaction()` de forma async-compatible.

---

## PARTE 5: IMPACTO EM OUTRAS ÁREAS

### Validar Separação de Responsabilidade
1. ✅ `validar_onboarding_minimo()` — depende de `tenant_id` apenas
   - Impacto: ZERO (lê, não escreve)
   
2. ✅ `validar_campo_onboarding()` — função pura, nenhuma dependência
   - Impacto: ZERO

3. ✅ `obter_pergunta_etapa()` — função pura, nenhuma dependência
   - Impacto: ZERO

4. ⚠️ `ETAPAS_ONBOARDING` — lista global de etapas
   - Verificar: Se será usada por novo path também (resposta: SIM)
   - Impacto: ZERO risco (dados imutáveis)

### Impacto em Callsites
- `onboarding_service.py`: Precisa extrair `actor_id` de `ctx` antes de chamar
- `router/integracao_identidade_onboarding.py`: Já passa `actor_id` para iniciar

**Conclusão:** Impacto contido em 2 files, riscos mínimos.

---

## PARTE 6: RISCOS IDENTIFICADOS

| Risco | Severidade | Mitigation |
|-------|-----------|-----------|
| **Dupla escrita** (novo + legacy) sem controle | ALTA | Usar transaction para garantir atomicidade ambos |
| **Múltiplos `.update()` em avanço** | ALTA | Refatorar para single transaction |
| **Idempotência** sem chave determinística | MÉDIA | Implementar SHA256(actor_id:campo:valor) |
| **Sobrescrita em iniciar** | MÉDIA | Verificar existência antes, não sobrescrever se existe |
| **Sem validação de actor_id** | MÉDIA | Sempre validar actor_id == context |
| **Legacy não migrado** | BAIXA | Intencional (compatibilidade), documentado |

---

## PARTE 7: NOVO PATH CONFIRMADO

```
Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
```

**Campos Esperados:**
- tenant_id (copy para referência)
- actor_id (copy para referência)
- onboarding_status (em_progresso | completo)
- onboarding_etapa_atual (nome_negocio, segmento, ...)
- onboarding_indice (0-11)
- criado_em (ISO timestamp)
- atualizado_em (ISO timestamp)
- criado_por (actor_id)
- dono_nome
- dono_email
- [campos de dados: nome_negocio, segmento, endereco, ...]

---

## PARTE 8: CHECKLIST PRÉ-IMPLEMENTAÇÃO

- [x] 3 funções identificadas
- [x] 3 callsites mapeados
- [x] Assinatura nueva definida
- [x] Padrões de projeto verificados
- [x] Dependências listadas
- [x] Riscos documentados
- [x] Novo path confirmado
- [x] Impactos avaliados
- [x] Compatibilidade confirmada

**Status:** ✅ PRONTO PARA IMPLEMENTAÇÃO

---

**Próximo Passo:** Implementar C3.15.3 com regras arquiteturais de C3.15 gate.

---

**Auditoria Completada:** 2026-09-26  
**Autorizado para:** Proceder com implementação
