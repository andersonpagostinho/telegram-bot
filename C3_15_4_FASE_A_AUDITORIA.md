# C3.15.4 — FASE A: AUDITORIA

**Status:** Auditoria Concluída  
**Data:** 2026-09-26  
**Escopo:** Mapear implementação atual, consumidores, schema e riscos de consolidação  

---

## PARTE 1: IMPLEMENTAÇÃO ATUAL

### Escritas em `Configuracao/negocio` (Legacy)

**Função:** `iniciar_onboarding_dono()` (C3.15.3)
- Arquivo: `services/onboarding_dono_service.py:30-106`
- Localização: REFATORADA → escreve em novo path isolado
- **Status:** Não escreve mais em legacy

**Função:** `avancar_etapa_onboarding()` (C3.15.3)
- Arquivo: `services/onboarding_dono_service.py:108-229`
- Localização: REFATORADA → escreve em novo path isolado
- **Status:** Não escreve mais em legacy

**Função:** `marcar_onboarding_completo()` (C3.15.3)
- Arquivo: `services/onboarding_dono_service.py:231-296`
- Localização: REFATORADA → escreve em novo path isolado
- **Status:** Não escreve mais em legacy

**Conclusão:** Nenhuma escrita ativa em `Configuracao/negocio` para onboarding individual.

### Leituras de `Configuracao/negocio`

**Função:** `validar_onboarding_minimo()` (Consumidor)
- Arquivo: `services/onboarding_dono_service.py:403-457`
- Localização: `Clientes/{tenant_id}/Configuracao/negocio` (linha 420)
- Validação: Verifica campos obrigatórios para onboarding mínimo
- Campos Lidos:
  ```
  nome_negocio
  segmento
  endereco
  agenda_padrao
  primeiro_profissional
  canal_primeiro_profissional
  primeiro_servico
  duracao_primeiro_servico
  ```
- **Risco:** Esta função AINDA espera dados em legacy

---

## PARTE 2: CONSUMIDORES DE `Configuracao/negocio`

### Diretos (Código de Produção)

1. **`validar_onboarding_minimo()`** (Identificado)
   - Lê 8 campos obrigatórios
   - Usado por: `processar_resposta_onboarding_dono()` (onboarding_service.py:305)

### Indiretos (Testes)

Referências encontradas em:
- `test_c315_1_schema_isolado.py` (C3.15.1 tests)
- `test_c315_3_escrita_isolada.py` (C3.15.3 tests)
- `p1_e2e_onboarding_*.py` (E2E tests)

**Status:** Testes usam schema C3.15.1, não leem direto de legacy.

---

## PARTE 3: SCHEMA C3.15.1 (NOVO PATH)

**Caminho:** `Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo`

**Campos Definidos:**

```
tenant_id              → tenant do onboarding
actor_id               → ator que está completando
dono_actor_id          → cópia do ator (para compatibilidade)
dono_nome              → nome do dono
dono_email             → email do dono
onboarding_status      → em_progresso | completo
onboarding_etapa_atual → nome_negocio, segmento, ...
onboarding_indice      → 0-11
criado_em              → ISO timestamp
criado_por             → actor_id
atualizado_em          → ISO timestamp
_ultimo_campo_idempotencia → SHA256 hash (C3.15.3)

[Campos de Dados Coletados]
nome_negocio
segmento
endereco
agenda_padrao
primeiro_profissional
canal_primeiro_profissional
primeiro_servico
duracao_primeiro_servico
```

---

## PARTE 4: CONTRATO C3.15.3

### Funções Atuais

```python
async def iniciar_onboarding_dono(
    tenant_id: str,
    actor_id: str,
    dono_nome: str,
    dono_email: str
) -> dict

async def avancar_etapa_onboarding(
    tenant_id: str,
    actor_id: str,
    campo: str,
    valor: str
) -> dict

async def marcar_onboarding_completo(
    tenant_id: str,
    actor_id: str
) -> bool
```

### Comportamentos Garantidos

- ✅ `iniciar`: idempotente, novo path isolado
- ✅ `avancar`: transacional, SHA256 idempotência
- ✅ `marcar`: ownership validated, não ressetar se completo
- ✅ Nenhuma escrita em legacy atualmente
- ✅ Leitura com fallback via C3.15.2

---

## PARTE 5: DOCUMENTO LEGACY (`Configuracao/negocio`)

### Campos Observados

**Metadados:**
```
criado_em
criado_por
atualizado_em
dono_actor_id        ← importante para ownership
dono_nome
dono_email
```

**Onboarding State (ANTIGO):**
```
onboarding_status
onboarding_etapa_atual
onboarding_indice
```

**Dados Coletados:**
```
nome_negocio
segmento
endereco
agenda_padrao
primeiro_profissional
canal_primeiro_profissional
primeiro_servico
duracao_primeiro_servico
```

**Campos Comerciais Adicionais (POSSIVELMENTE):**
```
[campos a validar]
```

### Status Atual

- **Novas escritas de onboarding:** Em novo path (C3.15.3)
- **Leituras existentes:** Ainda esperando dados em legacy
- **Legacy não deletado:** Preservado para compatibilidade
- **Validação mínima:** Ainda lê de legacy

---

## PARTE 6: CONSOLIDAÇÃO PROPOSTA

### Objetivo

Transicionar dados de `Donos/{actor_id}/onboarding/ativo` para `Configuracao/negocio` quando onboarding completa, garantindo:
1. Só o **primeiro** a completar torna-se dono principal
2. Operação **idempotente**
3. Sem **race conditions**
4. **Imutabilidade** de `dono_principal_actor_id`

### Boundary de Consolidação

**Origem:** `Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo`  
**Destino:** `Clientes/{tenant_id}/Configuracao/negocio`

**Campos a Consolidar:**
```
✅ nome_negocio
✅ segmento
✅ endereco
✅ agenda_padrao
✅ primeiro_profissional
✅ canal_primeiro_profissional
✅ primeiro_servico
✅ duracao_primeiro_servico

✅ dono_principal_actor_id (NOVO, imutável)
✅ dono_nome (do primeiro a completar)
✅ dono_email (do primeiro a completar)
```

**Campos NÃO Consolidados:**
```
❌ onboarding_etapa_atual (estado individual)
❌ onboarding_indice (estado individual)
❌ onboarding_status (estado individual)
❌ _ultimo_campo_idempotencia (C3.15.3 internal)
❌ criado_por (rastreabilidade do ator)
```

### Invariantes a Preservar

1. **`dono_principal_actor_id` imutável**
   - Uma vez definido, nunca sobrescrever
   - Só o primeiro a completar o define

2. **Sem destruição de dados**
   - Legacy não deletado
   - Campos compartilhados não sobrescritos cegamente

3. **Transação garantida**
   - Decisão de "primeiro" é atômica
   - Nenhuma race condition possível

4. **Idempotência**
   - Retry de conclusão não muda `dono_principal_actor_id`
   - Retry não duplica consolidação

5. **Validação explícita**
   - Ownership verificado
   - Tenant verificado
   - Estado válido verificado

---

## PARTE 7: RISCOS IDENTIFICADOS

| Risco | Severidade | Mitigation |
|-------|-----------|-----------|
| **Dois atores completam simultaneamente** | ALTA | Use Firestore Transaction |
| **`dono_principal_actor_id` pode ser sobrescrito** | ALTA | Campo imutável após definido |
| **Legacy destruído acidentalmente** | ALTA | Preservar, não sobrescrever |
| **Retry altera dono principal** | MÉDIA | Idempotência determinística |
| **Validação mínima ainda lê legacy** | MÉDIA | Depois: migrar para novo path |
| **Campos individuais contaminam negócio** | MÉDIA | Separação explícita na lógica |

---

## PARTE 8: QUESTÕES CRÍTICAS

1. **Como `validar_onboarding_minimo()` será afetada?**
   - Atualmente lê de `Configuracao/negocio`
   - Depois de C3.15.4: qual será a fonte de verdade?
   - Opções:
     - A) Ler de novo path (Donos/{actor_id}/...)
     - B) Ler de Configuracao/negocio (legacy)
     - C) Dual-read com fallback

   **Recomendação:** Clarificar antes de implementar

2. **Se documento `Configuracao/negocio` não existir inicialmente?**
   - É possível ou sempre existe?
   - Se não existe: criar ou retornar erro?

3. **Qual é a semântica exata de "onboarding mínimo"?**
   - Os 8 campos listados são realmente obrigatórios?
   - Ou há múltiplas definições de "mínimo"?

4. **Campo `dono_principal_actor_id`: tipo?**
   - string (actor_id normalizado)?
   - Campo que não existia antes — precisa ser adicionado?

---

## PARTE 9: RECOMENDAÇÕES PRÉ-IMPLEMENTAÇÃO

### Antes de Prosseguir para Fase B (Desenho)

1. **Validar schema:** Confirmar que C3.15.1 cobre todos os campos necessários
2. **Clarificar consumidores:** Entender como `validar_onboarding_minimo()` mudará
3. **Definir atomicidade:** Confirmar que Firestore Transaction é a ferramenta certa
4. **Definir imutabilidade:** Como garantir que `dono_principal_actor_id` não é sobrescrito
5. **Testar concorrência:** Garantir que dois atores simultâneos não geram race condition

### Checklist Antes de Fase C (Implementação)

- [ ] Auditoria completa entregue ao usuário
- [ ] Plano/Design aprovado (Fase B)
- [ ] Questões críticas respondidas
- [ ] Invariantes documentadas
- [ ] Testes de concorrência planejados
- [ ] Estratégia de idempotência definida
- [ ] Nenhuma dúvida bloqueadora

---

## RESUMO DA AUDITORIA

**Estado Atual:**
- ✅ Novo path isolado criado (C3.15.1)
- ✅ Leitura isolada implementada (C3.15.2)
- ✅ Escrita isolada implementada (C3.15.3)
- ⚠️ Legacy `Configuracao/negocio` ainda é fonte de verdade para validação

**Próximo Passo:**
- Nenhuma implementação em C3.15.4 ainda
- Aguardando aprovação da auditoria
- Pronto para Fase B (Desenho) após confirmação

---

**Auditoria Completada:** 2026-09-26  
**Pronto para:** Fase B — DESENHO (após aprovação)  
**NÃO IMPLEMENTAR:** Fase C aguarda autorização  

