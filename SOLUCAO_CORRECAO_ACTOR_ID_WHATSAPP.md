# SOLUÇÃO — CORRIGIR ACTOR_ID PARA WHATSAPP

**Data:** 2026-10-03  
**Status:** Pronto para implementação  
**Bloqueador:** `criar_identidade_whatsapp()` requer `phone_number_id` (não disponível em linha 3466)

---

## PROBLEMA

**Linha 3466-3469 de router/principal_router.py:**

```python
if tenant_id:
    # WhatsApp: temos tenant_id e user_id (wa_id)
    identidade_p01 = criar_identidade_telegram(  # ← BUG: cria Telegram
        telegram_id=user_id,
        canal_tenant_id=dono_id,
    )
```

**Solução candidata:** Usar `criar_identidade_whatsapp()` em vez de `criar_identidade_telegram()`.

**Bloqueador:** `criar_identidade_whatsapp()` exige `phone_number_id`, que não está disponível nesse contexto.

---

## ANÁLISE DE OPÇÕES

### OPÇÃO 1: Construir IdentidadeContexto diretamente ✅ RECOMENDADA

**Vantagem:** Não precisa de `phone_number_id`, usa dados já disponíveis

**Implementação:**

```python
if tenant_id:
    # WhatsApp: construir identidade diretamente
    from utils.identidade_contexto import IdentidadeContexto
    
    actor_id = f"whatsapp:{user_id}"
    identidade_p01 = IdentidadeContexto(
        user_id=user_id,
        tenant_id=dono_id,
        actor_id=actor_id,
        canal="whatsapp"
    )
else:
    # Telegram: fallback para função existente
    identidade_p01 = criar_identidade_telegram(telegram_id=user_id)
```

**Resultado:**
- `identidade_p01.actor_id` = `"whatsapp:5511991382080"` ✅ CORRETO
- Sem dependência de `phone_number_id`
- Alinha com padrão: `f"whatsapp:{wa_id}"`

---

### OPÇÃO 2: Obter phone_number_id do update

**Problema:** `phone_number_id` não está mapeado em `update` nesse ponto

**Seria necessário:** Refatorar captura de metadata do webhook

**Status:** Muito invasivo, não recomendado

---

### OPÇÃO 3: Usar actor_id_whatsapp já resolvido

**Linha 3492 já tem:**
```python
actor_id_whatsapp = atar_canonico.get("actor_id")
```

**Problema:** `actor_id_whatsapp` é definido APÓS `identidade_p01` (linha 3466 vs 3492)

**Seria necessário:** Reordenar código

**Status:** Possível mas requer mudanças em fluxo

---

## IMPLEMENTAÇÃO RECOMENDADA (OPÇÃO 1)

**Arquivo:** `router/principal_router.py`  
**Linhas:** 3464-3478

**De:**
```python
try:
    if tenant_id:
        # WhatsApp: temos tenant_id e user_id (wa_id)
        identidade_p01 = criar_identidade_telegram(
            telegram_id=user_id,
            canal_tenant_id=dono_id,
        )
    else:
        # Telegram: apenas user_id
        identidade_p01 = criar_identidade_telegram(telegram_id=user_id)

    # Log para auditoria (não altera fluxo)
    print(f"[P0.1] IdentidadeContexto criado: {identidade_p01}", flush=True)
except Exception as e:
    print(f"[P0.1] Erro ao criar IdentidadeContexto: {e}", flush=True)
    identidade_p01 = None
```

**Para:**
```python
try:
    if tenant_id:
        # WhatsApp: construir identidade com actor_id canônico
        from utils.identidade_contexto import IdentidadeContexto
        
        actor_id = f"whatsapp:{user_id}"
        identidade_p01 = IdentidadeContexto(
            user_id=user_id,
            tenant_id=dono_id,
            actor_id=actor_id,
            canal="whatsapp"
        )
    else:
        # Telegram: usar factory existente
        identidade_p01 = criar_identidade_telegram(telegram_id=user_id)

    # Log para auditoria
    print(f"[P0.1] IdentidadeContexto criado: {identidade_p01}", flush=True)
except Exception as e:
    print(f"[P0.1] Erro ao criar IdentidadeContexto: {e}", flush=True)
    identidade_p01 = None
```

---

## IMPACTO ESPERADO

### Antes:
```
Webhook WhatsApp:
  identidade_p01.actor_id = "tg:5511991382080" ❌

P0.3 salva em:
  Clientes/7394370553/Sessoes/tg:5511991382080 ❌

Próximo webhook carrega de:
  Clientes/7394370553/Sessoes/whatsapp:5511991382080 ✅

RESULTADO: ultima_acao não encontrado ❌
```

### Depois:
```
Webhook WhatsApp:
  identidade_p01.actor_id = "whatsapp:5511991382080" ✅

P0.3 salva em:
  Clientes/7394370553/Sessoes/whatsapp:5511991382080 ✅

Próximo webhook carrega de:
  Clientes/7394370553/Sessoes/whatsapp:5511991382080 ✅

RESULTADO: ultima_acao encontrado ✅
```

---

## RESUMO

| Item | Detalhe |
|------|---------|
| **Arquivo** | router/principal_router.py |
| **Linhas** | 3464-3478 |
| **Mudança** | Construir IdentidadeContexto diretamente em vez de usar `criar_identidade_telegram()` para WhatsApp |
| **Import necessário** | `from utils.identidade_contexto import IdentidadeContexto` |
| **Linhas de código** | ~12 linhas |
| **Risco** | Baixo (apenas lógica condicional, sem dependências externas) |
| **Bloqueador P0.3** | Resolvido ✅ |
| **Fluxo "pode"** | Desbloqueado ✅ |

---

**Pronto para autorização de implementação.**

