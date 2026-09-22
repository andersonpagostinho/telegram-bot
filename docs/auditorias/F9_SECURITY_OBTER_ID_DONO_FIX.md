# F9 SECURITY — obter_id_dono() Fallback Inseguro

**Status:** BLOQUEADO CRÍTICO  
**Data Descoberta:** 2026-07-01  
**Teste que descobriu:** runner_f9_dashboard_firestore_real.py — F9-SEC-01  
**Severidade:** P0 — Vazamento de dados  

---

## Problema Descoberto

### Reprodução com Firebase Real

```
Test: F9-SEC-01 (Cliente é bloqueado)
Resultado: FALHOU
Evidência: obter_id_dono(cliente_f9_01_56bea89f) retornou: cliente_f9_01_56bea89f
Impacto: Cliente identificado como dono → Acessa dashboard do dono
```

### Código Vulnerable

**Arquivo:** `services/firebase_service_async.py:358-360`

```python
async def obter_id_dono(user_id: str) -> str:
    cliente = await buscar_cliente(user_id)
    return cliente.get("id_negocio", user_id) if cliente else user_id
    #                                                           ^^^^^^^ BUG
```

### Por Que É Inseguro

1. Busca cliente em `Clientes/{user_id}`
2. Se não encontrado:
   - Retorna `user_id` como fallback silencioso
   - Qualquer ator desconhecido vira "dono"
3. Role check usa essa função:
   ```python
   tenant_id = await obter_id_dono(user_id)
   eh_dono = (user_id == tenant_id)  # ← Sempre True se não encontrado!
   ```
4. **Resultado:** Cliente/desconhecido passa na validação de dono

---

## Causa Raiz

### Cenário Problemático

```
Actor: cliente_f9_01_56bea89f (cliente comum)
Localização: Clientes/{tenant_01}/ClientesComuns/{cliente_f9_01_56bea89f}

obter_id_dono(cliente_f9_01_56bea89f):
  ├─ Busca: Clientes/{cliente_f9_01_56bea89f} ← Não existe!
  ├─ Resultado: None
  └─ Fallback: return cliente_f9_01_56bea89f ← Retorna como dono!

Role check:
  ├─ tenant_id = cliente_f9_01_56bea89f
  ├─ eh_dono = (cliente_f9_01_56bea89f == cliente_f9_01_56bea89f) ← TRUE!
  └─ Acesso concedido ← VAZAMENTO!
```

---

## Estrutura de Dados Esperada

### Cliente Registrado Corretamente

```
Clientes/
  └─ {tenant_01}/                          # Dono/Negócio
     ├─ Proprietarios/...
     └─ ClientesComuns/
        └─ cliente_001/
           ├─ nome: "João"
           ├─ cliente_id: "cliente_001"
           └─ tenant_id: "tenant_01"       # ← Referência ao dono
```

### Problema

Cliente está registrado DENTRO da estrutura do tenant, mas `buscar_cliente()` 
procura apenas em `Clientes/{user_id}` (raiz), não em `Clientes/{tenant}/ClientesComuns/`.

---

## Correção Obrigatória

### 1. Alterar obter_id_dono()

**Arquivo:** `services/firebase_service_async.py:358-360`

```python
# ANTES (INSEGURO)
async def obter_id_dono(user_id: str) -> str:
    cliente = await buscar_cliente(user_id)
    return cliente.get("id_negocio", user_id) if cliente else user_id

# DEPOIS (SEGURO)
async def obter_id_dono(user_id: str) -> str | None:
    """
    Resolve tenant_id para um ator.
    
    CRÍTICO: NUNCA retorna user_id como fallback em operação crítica.
    
    Retorna:
    - tenant_id se ator é cliente vinculado a negócio
    - None se ator não encontrado/inválido
    """
    cliente = await buscar_cliente(user_id)
    if cliente:
        return cliente.get("id_negocio")  # Pode ser None também!
    return None  # ← Não fazer fallback para user_id


async def obter_id_dono_com_fallback(user_id: str) -> str:
    """
    Versão com fallback (use APENAS para contexto não-crítico).
    
    Use NUNCA em:
    - Autenticação
    - Autorização
    - Acesso a dados sensíveis
    
    Use APENAS em:
    - Logs não-críticos
    - Formatação de mensagens
    - Contexto informativo
    """
    tenant_id = await obter_id_dono(user_id)
    return tenant_id if tenant_id else user_id
```

### 2. Role Check Seguro

**Arquivo:** `handlers/dashboard_handler.py:38-53`

```python
async def _validar_acesso_dono(user_id: str) -> tuple[bool, str | None]:
    """
    CRÍTICO: Valida se user_id é realmente um DONO (owner/tenant).
    
    Retorna: (é_dono: bool, tenant_id: str | None)
    
    Sem isso, CLIENTES E PROFISSIONAIS acessam dados de outros!
    """
    tenant_id = await obter_id_dono(user_id)
    
    # NUNCA aceitar None
    if tenant_id is None:
        return False, None
    
    # Dono se user_id == tenant_id
    eh_dono = (user_id == tenant_id)
    return eh_dono, tenant_id if eh_dono else None
```

### 3. Criar Índice Cliente → Tenant (Recomendado)

**Novo documento:** `Atores/{actor_id}`

```
Atores/
  └─ cliente_f9_01_56bea89f/
     ├─ tipo: "cliente"
     ├─ tenant_id: "tenant_f9_01"
     ├─ criado_em: ISO
     └─ ativo: true
```

**Benefício:**
- Busca O(1) sem rastreamento de hierarquia
- Resolução rápida de tenant para qualquer ator
- Validação independente de estrutura

---

## Testes de Segurança Obrigatórios (6)

### SEC-01: Actor Desconhecido NÃO Vira Dono

```python
# Dado
actor_desconhecido = "ator_xyz_nao_existe"

# Quando
tenant = await obter_id_dono(actor_desconhecido)

# Então
assert tenant is None  # ← Não None, não user_id!
assert await _validar_acesso_dono(actor_desconhecido) == (False, None)
```

### SEC-02: Cliente Comum NÃO Acessa Dashboard

```python
# Dado
cliente = "cliente_f9_01"
dashboard = cmd_dashboard(update=mock(from_user.id=cliente), context=None)

# Então
assert "negado" in mensagem.lower()
assert dashboard_dados is None
```

### SEC-03: Profissional NÃO Acessa Dashboard

```python
# Dado
profissional = "prof_001"

# Quando
tenant = await obter_id_dono(profissional)

# Então
assert tenant is None  # ou apenas seu próprio tenant se tiver
assert await _validar_acesso_dono(profissional)[0] == False  # NÃO é dono
```

### SEC-04: Dono Real Acessa Dashboard

```python
# Dado
dono = "tenant_f9_01"

# Quando
tenant = await obter_id_dono(dono)

# Então
assert tenant == dono
assert await _validar_acesso_dono(dono) == (True, dono)
```

### SEC-05: Tenant A NÃO Acessa Dashboard Tenant B

```python
# Dado
tenant_a = "tenant_f9_01"
tenant_b = "tenant_f9_02"

# Quando
dashboard_a = await obter_dashboard_completo(tenant_a)
dashboard_b = await obter_dashboard_completo(tenant_b)

# Então
assert dashboard_a != dashboard_b
assert "clientes_novos" em dashboard_a não veio de tenant_b
```

### SEC-06: Fallback Legado NÃO Permite Dashboard

```python
# Dado
usar fallback inseguro = True (simulado)

# Quando
dashboard = cmd_dashboard(ator_desconhecido, context)

# Então
assert dashboard é negado
# Mesmo que obter_id_dono_com_fallback retorne user_id,
# role check rejeita porque tenant_id != user_id (apenas se for dono real)
```

---

## Plano de Implementação

### Fase 1: Correção (CRÍTICA)

1. [ ] Alterar `obter_id_dono()` para retornar `None` se não encontrado
2. [ ] Alterar `_validar_acesso_dono()` para rejeitar `None`
3. [ ] Testar com F9-SEC-01 a F9-SEC-06

### Fase 2: Validação com Firestore Real

1. [ ] Executar `runner_f9_dashboard_firestore_real.py`
2. [ ] Validar: F9-SEC-01 PASSA (cliente bloqueado)
3. [ ] Validar: F9-SEC-02 PASSA (dono aceito)

### Fase 3: Regressão

1. [ ] F8 8/8 PASS
2. [ ] Baseline 54/54 PASS
3. [ ] P0 174/174 PASS

### Fase 4: Limpeza + Documentação

1. [ ] Remover F9 mock (`runner_f9_dashboard.py` com mocks)
2. [ ] Manter F9 real (`runner_f9_dashboard_firestore_real.py`)
3. [ ] Atualizar `RESULTADO_F9_VALIDACAO.md`

---

## Status F9

### BLOQUEADO

F9 (Dashboard do Dono) está **bloqueado** até:
- [ ] Correção de `obter_id_dono()` implementada
- [ ] 6 testes de segurança PASSANDO
- [ ] Firestore real validado (F9-SEC-01, F9-SEC-02)
- [ ] Regressão baseline OK (54/54 ou 174/174)

### Razão

Vazamento crítico de dados: cliente acessa dashboard do dono.

---

## Validação Esperada (Após Correção)

```
[ANTES - INSEGURO]
F9-SEC-01: Cliente é bloqueado → FALHOU
           Evidência: cliente foi identificado como dono

[DEPOIS - SEGURO]
F9-SEC-01: Cliente é bloqueado → PASSAR
           Evidência: tenant_id = None, bloqueio funcionou
           
F9-SEC-02: Dono acessa dashboard → PASSAR
           Evidência: tenant_id = dono, acesso concedido
```

---

## Documentação Relacionada

- `handlers/dashboard_handler.py` — Role check será atualizado
- `RESULTADO_F9_VALIDACAO.md` — Status será atualizado para BLOQUEADO
- `CLAUDE.md` — Regra: "Nunca usar fallback silencioso em operação crítica"

---

**Responsável pela Correção:** Claude Code  
**Deadline:** Antes de liberar F9 para produção  
**Criticidade:** P0 — Não liberar sem correção  
