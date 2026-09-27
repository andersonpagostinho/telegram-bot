# C3.15.2 — PLANO DE EXECUÇÃO (LEITURA)

**Status:** Auditoria Pré-Execução  
**Data:** 2026-09-26  
**Escopo:** Implementar nova leitura `pegar_etapa_onboarding(tenant_id, actor_id)`  

---

## PARTE 1: AUDITORIA PRÉ-EXECUÇÃO

### Função Atual

**Arquivo:** `services/onboarding_dono_service.py:83-114`

```python
async def pegar_etapa_onboarding(tenant_id: str) -> dict:
    """Obtém etapa atual do onboarding."""
    
    # ATUAL: Lê de Clientes/{tenant_id}/Configuracao/negocio
    # PROBLEMA: Ignora actor_id, compartilha entre donos
```

**Assinatura Atual:**
```
pegar_etapa_onboarding(tenant_id: str) -> dict | None
```

**Assinatura Nova (Aprovada C3.15):**
```
pegar_etapa_onboarding(tenant_id: str, actor_id: str) -> dict | None
```

---

### Callsites em Código Produção

**Total:** 3 callsites

#### Callsite 1
**Arquivo:** `router/integracao_identidade_onboarding.py:107`
```python
async def resolver_ator_e_validar_guard(
    user_id: str,
    tenant_id: str,
    canal: str = "whatsapp",
    identificador: str = None,
    ctx: dict = None,
) -> dict:
    # Linha 107:
    etapa_info = await pegar_etapa_onboarding(tenant_id)
    # CONTEXTO: actor_id está disponível (parâmetro/variável local)
    # AÇÃO: Adicionar actor_id
```
**Disponibilidade de actor_id:** ✅ Sim (variável local `actor_id`)

#### Callsite 2
**Arquivo:** `router/integracao_identidade_onboarding.py:221`
```python
async def resolver_ator_e_validar_guard(
    # mesma função acima
    # Linha 221:
    etapa_info = await pegar_etapa_onboarding(tenant_id)
    # CONTEXTO: actor_id está disponível (variável local)
    # AÇÃO: Adicionar actor_id
```
**Disponibilidade de actor_id:** ✅ Sim (variável local `actor_id`)

#### Callsite 3
**Arquivo:** `services/onboarding_service.py:256`
```python
async def processar_resposta_onboarding_dono(
    user_id: str,
    tenant_id: str,
    texto_usuario: str,
    ctx: dict,
    context
):
    # Linha 256:
    etapa_info = await pegar_etapa_onboarding(tenant_id)
    # CONTEXTO: ctx["actor_id"] foi definido pelo router (linha 319 integracao_identidade_onboarding.py)
    # AÇÃO: Passar ctx["actor_id"]
```
**Disponibilidade de actor_id:** ✅ Sim (em `ctx["actor_id"]`)

---

### Análise de Compatibilidade

**Conclusão:** ✅ TOTALMENTE COMPATÍVEL

Todos os 3 callsites em produção têm `actor_id` disponível.
Nenhuma incompatibilidade estrutural.

---

## PARTE 2: ARQUIVOS E FUNÇÕES A ALTERAR

### Arquivos a Alterar

| Arquivo | Linhas | Alteração | Impacto |
|---------|--------|-----------|---------|
| `services/onboarding_dono_service.py` | 83-114 | REWRITE função + ADICIONAR imports | MAIOR |
| `router/integracao_identidade_onboarding.py` | 107, 221 | UPDATE callsites | MENOR |
| `services/onboarding_service.py` | 256 | UPDATE callsite | MENOR |

### Funções a Alterar

```
onboarding_dono_service.py:
  └─ pegar_etapa_onboarding()  [REWRITE]
     ├─ Adicionar parâmetro actor_id
     ├─ Ler de novo path: Donos/{actor_id}/...
     ├─ Implementar fallback legacy
     ├─ Validar ownership (legacy.dono_actor_id == actor_id)
     └─ Bloquear cross-actor (se legacy de outro actor, return None)
```

### Callsites a Alterar

```
integracao_identidade_onboarding.py:
  └─ resolver_ator_e_validar_guard() [2 callsites]
     ├─ Linha 107: ADD actor_id
     └─ Linha 221: ADD actor_id

onboarding_service.py:
  └─ processar_resposta_onboarding_dono() [1 callsite]
     └─ Linha 256: ADD ctx["actor_id"]
```

---

## PARTE 3: IMPLEMENTAÇÃO DETALHADA

### Assinatura Nova

```python
async def pegar_etapa_onboarding(
    tenant_id: str,
    actor_id: str
) -> dict | None:
    """
    Obtém etapa atual do onboarding isolado por actor.
    
    Comportamento:
    1. Tenta novo path: Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
    2. Se não existe, tenta legacy: Clientes/{tenant_id}/Configuracao/negocio
       - Se legacy.dono_actor_id == actor_id: retornar (compatibilidade)
       - Se legacy pertence a outro actor: retornar None (bloqueio)
       - Se nenhum dos dois: retornar None
    
    Args:
        tenant_id: ID do tenant
        actor_id: ID do ator (obrigatório)
    
    Returns:
        {"etapa_atual": str, "indice": int, "status": str, "dados": dict}
        ou None se não encontrado
    """
```

### Pseudocódigo da Implementação

```python
async def pegar_etapa_onboarding(tenant_id: str, actor_id: str) -> dict | None:
    # 1. Validar entrada
    if not tenant_id or not actor_id:
        return None
    
    try:
        # 2. Tentar novo path
        novo_ref = db.collection("Clientes").document(tenant_id)\
            .collection("Donos").document(actor_id)\
            .collection("onboarding").document("ativo")
        
        novo_doc = await ler_novo_path(novo_ref)
        if novo_doc.exists:
            # Novo path tem prioridade
            return {
                "etapa_atual": novo_doc.get("onboarding_etapa_atual"),
                "indice": novo_doc.get("onboarding_indice", 0),
                "status": novo_doc.get("onboarding_status"),
                "dados": novo_doc.to_dict()
            }
        
        # 3. Fallback legacy
        legacy_ref = db.collection("Clientes").document(tenant_id)\
            .collection("Configuracao").document("negocio")
        
        legacy_doc = await ler_legacy_path(legacy_ref)
        if legacy_doc.exists:
            legacy_data = legacy_doc.to_dict()
            
            # 3a. Validar ownership
            if legacy_data.get("dono_actor_id") != actor_id:
                # Legacy pertence a outro actor
                print(f"[ISOLAMENTO] Legacy de {legacy_data.get('dono_actor_id')} para {actor_id}")
                return None
            
            # 3b. Retornar legacy como fallback compatível
            return {
                "etapa_atual": legacy_data.get("onboarding_etapa_atual"),
                "indice": legacy_data.get("onboarding_indice", 0),
                "status": legacy_data.get("onboarding_status"),
                "dados": legacy_data
            }
        
        # 4. Nenhum encontrado
        return None
    
    except Exception as e:
        print(f"[ERRO] Pegar etapa onboarding: {e}")
        return None
```

---

## PARTE 4: TESTES A IMPLEMENTAR

### 12 Testes Obrigatórios

| ID | Teste | Status | Tipo |
|----|-------|--------|------|
| T1 | Novo path retorna onboarding | ⬜ TODO | Leitura |
| T2 | Actor A não recebe de B | ⬜ TODO | Isolamento |
| T3 | Mesmo actor, tenants diferentes isolados | ⬜ TODO | Isolamento |
| T4 | Novo path tem prioridade sobre legacy | ⬜ TODO | Prioridade |
| T5 | Legacy do próprio actor funciona como fallback | ⬜ TODO | Compatibilidade |
| T6 | Legacy de outro actor retorna None | ⬜ TODO | Bloqueio |
| T7 | Nenhum estado retorna None | ⬜ TODO | Edge case |
| T8 | Dados novo path não alterados na leitura | ⬜ TODO | Integridade |
| T9 | Legacy não alterado na leitura | ⬜ TODO | Integridade |
| T10 | Múltiplas leituras não criam docs | ⬜ TODO | Idempotência |
| T11 | Schema inválido tratado com segurança | ⬜ TODO | Robustez |
| T12 | Parâmetro obrigatório actor_id | ⬜ TODO | Contrato |

---

## PARTE 5: REGRESSÃO A EXECUTAR

**Testes a rodar após implementação:**

1. ✅ Testes novos C3.15.2 (12 testes)
2. ✅ Testes C3.15.1 (10 testes)
3. ✅ Testes existentes onboarding:
   - `tests/runner_p1_identidade_canal_onboarding.py`
   - `tests/test_onboarding_dono_fluxo_conversacional_real.py`
   - `tests/test_c312_novo_dono_onboarding_firebase_real.py`

---

## PARTE 6: VALIDAÇÕES DE SEGURANÇA

### ✅ Pre-Requisitos Confirmados

- [x] actor_id disponível em todos os 3 callsites
- [x] Nenhuma incompatibilidade estrutural
- [x] Novo path não conflita com estrutura existente
- [x] Legacy fallback implementável sem risks
- [x] Nenhuma escrita será introduzida
- [x] Nenhum commit será feito
- [x] Nenhum push será feito

---

## PARTE 7: RESTRIÇÕES DO C3.15.2

### ✅ NÃO FAZER

- ❌ Não implementar iniciar_onboarding_dono()
- ❌ Não implementar avancar_etapa_onboarding()
- ❌ Não implementar marcar_onboarding_completo()
- ❌ Não fazer migração automática
- ❌ Não fazer dual-write
- ❌ Não remover legacy
- ❌ Não alterar Configuracao/negocio
- ❌ Não alterar WhatsApp/tenant_resolver
- ❌ Não fazer commit
- ❌ Não fazer push

---

## RESUMO EXECUTIVO

**Objetivos de C3.15.2:**
1. ✅ Implementar nova leitura isolada por actor_id
2. ✅ Adicionar actor_id a 3 callsites em produção
3. ✅ Implementar fallback legacy seguro
4. ✅ Bloquear cross-actor leakage
5. ✅ Criar 12 testes de validação
6. ✅ Executar regressão completa

**Impacto:**
- Leitura isola actors (tenant_id + actor_id)
- Compatibilidade mantida via legacy fallback
- Zero escrita, zero migração
- Pronto para C3.15.3 (escrita)

---

**Próximo passo:** Executar C3.15.2 conforme este plano.
