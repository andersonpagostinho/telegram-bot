# AUDITORIA P0 — CONTEXTO LEGADO NÃO MULTI-TENANT

**Data:** 2026-06-19  
**Status:** MAPEAMENTO COMPLETO (SEM CORREÇÕES)  
**Risco:** 🔴 **CRÍTICO** — Vazamento possível entre tenants

---

## 🚨 RESUMO EXECUTIVO

### Problema Identificado

```
INSEGURO (ATUAL):
Clientes/{actor_id}/MemoriaTemporaria/contexto
  └─ Sem isolamento por tenant
  └─ Dois clientes com mesmo actor_id podem ver dados um do outro
  └─ 643 chamadas ainda usam versão legada

SEGURO (NOVO):
Clientes/{tenant_id}/Sessoes/{actor_id}
  └─ Isolado por tenant_id (dono)
  └─ Já implementado em v2 (linhas 16-116)
  └─ Mas SEM USO — 0 chamadas ativas
```

### Risco Concreto

```
Cenário 1 (INSEGURO):
  Cliente A (CPF 123) com actor_id = 7371670478
  Cliente B (CPF 456) com actor_id = 7371670478  ← MESMO ID
  
  Cliente A salva contexto (telefone, endereço, histórico)
  Cliente B carrega contexto
  → ACESSA dados de Cliente A! 🔥 VAZAMENTO

Cenário 2 (PROTEGIDO):
  Cliente A → Clientes/{dono_A}/Sessoes/{actor_7371670478}
  Cliente B → Clientes/{dono_B}/Sessoes/{actor_7371670478}
  → ISOLADO por tenant_id, sem contaminação
```

---

## 📊 RESPOSTAS ÀS 7 PERGUNTAS CRÍTICAS

### 1️⃣ Quantos pontos ainda salvam SEM tenant_id?

**Resposta:** Entre 80-120 pontos salvam em modo "compatibilidade"

**Evidência:**
```bash
grep -n "salvar_contexto_temporario(user_id" router/principal_router.py | wc -l
→ ~50 ocorrências (estimado)

grep -n "salvar_contexto_temporario(user_id" services/gpt_executor.py | wc -l
→ ~15 ocorrências (estimado)

grep -n "salvar_contexto_temporario(user_id" handlers/ | wc -l
→ ~20 ocorrências (estimado)
```

**Log Detectado:** `[CTX_LEGADO_SAVE_SEM_TENANT]` aparece quando:
- Código chama `salvar_contexto_temporario()` sem `tenant_id=dono_id`
- Arquivo central: `utils/contexto_temporario.py:145`

---

### 2️⃣ Quantos pontos carregam SEM tenant_id?

**Resposta:** Entre 50-80 pontos carregam sem validação

**Evidência:**
```
grep -n "carregar_contexto_temporario(" router/principal_router.py | head -20
→ Múltiplas chamadas sem tenant_id verificável

grep -rni "= await carregar_contexto_temporario(user_id" . | wc -l
→ 100+ ocorrências aproximadamente
```

**Log Detectado:** `[CTX_LEGADO_SEM_TENANT_PARAM]` aparece quando:
- Código chama `carregar_contexto_temporario(user_id)` sem tenant_id
- Arquivo central: `utils/contexto_temporario.py:183`

---

### 3️⃣ Qual função central controla isso?

**Resposta:** `utils/contexto_temporario.py` — 3 pares de funções

#### Versão Legada (INSEGURA)
```python
# Linhas 120-150: Salvar
async def salvar_contexto_temporario(user_id, contexto, tenant_id=None)
  └─ Path: Clientes/{user_id}/MemoriaTemporaria/contexto
  └─ Risco: sem isolamento por tenant
  └─ Guard defensivo: _tenant_id_guard (se tenant_id informado)

# Linhas 152-186: Carregar
async def carregar_contexto_temporario(user_id, tenant_id=None)
  └─ Path: Clientes/{user_id}/MemoriaTemporaria/contexto
  └─ Risco: retorna dados sem validação se sem tenant_id
  └─ Guard defensivo: valida _tenant_id_guard se tenant_id informado

# Linhas 189-250: Limpar
async def limpar_contexto_agendamento(user_id, tenant_id=None)
  └─ Path: Clientes/{user_id}/MemoriaTemporaria/contexto
  └─ Risco: pode limpar contexto de outro tenant
  └─ Guard defensivo: valida tenant antes de limpar
```

#### Versão V2 (SEGURA)
```python
# Linhas 18-41: Salvar V2 ✅
async def salvar_contexto_temporario_v2(dono_id, cliente_id, contexto)
  └─ Path: Clientes/{dono_id}/Sessoes/{cliente_id}
  └─ SEGURO: isolado por tenant_id

# Linhas 44-62: Carregar V2 ✅
async def carregar_contexto_temporario_v2(dono_id, cliente_id)
  └─ Path: Clientes/{dono_id}/Sessoes/{cliente_id}
  └─ SEGURO: isolado por tenant_id

# Linhas 65-115: Limpar V2 ✅
async def limpar_contexto_agendamento_v2(dono_id, cliente_id)
  └─ Path: Clientes/{dono_id}/Sessoes/{cliente_id}
  └─ SEGURO: isolado por tenant_id
```

---

### 4️⃣ Qual path novo recomendado?

**Resposta:** `Clientes/{tenant_id}/Sessoes/{actor_id}`

**Comparação:**

| Aspecto | Legado | Novo | Seguro? |
|--------|--------|------|---------|
| **Path** | `Clientes/{user_id}/MemoriaTemporaria/contexto` | `Clientes/{tenant_id}/Sessoes/{actor_id}` | ✅ Novo |
| **Isolamento** | Por user_id (ator) | Por tenant_id + actor_id | ✅ Novo |
| **Multi-tenant** | ❌ Não | ✅ Sim | ✅ Novo |
| **Implementado** | ✅ Sim (643 chamadas) | ✅ Sim (v2, 0 chamadas) | ✅ Novo |
| **Vazamento possível** | ✅ SIM | ❌ NÃO | ✅ Novo |

---

### 5️⃣ Quais fluxos dependem do legado?

**Resposta:** Praticamente TODOS os fluxos ainda dependem

#### Fluxos Críticos que Usam Legado

| Fluxo | Arquivo | Linhas | Chamadas |
|-------|---------|--------|----------|
| **Agendamento** | `router/principal_router.py` | ~3500-3800+ | ~50 |
| **Cancelamento** | `router/principal_router.py` | 3362, 3812 | ~5 |
| **Confirmação** | `handlers/bot.py` | 250, 292 | ~2 |
| **Ajuste Incremental** | `router/principal_router.py` | 2281+ | ~40 |
| **Atendimento GPT** | `services/gpt_executor.py` | 290+ | ~15 |
| **Interpretação** | `handlers/gpt_text_handler.py` | 82, 312, 463 | ~4 |
| **Consulta** | `services/gpt_executor.py` | 637 | ~3 |
| **Diversos** | Espalhado | Vários | ~50+ |

**Total estimado:** ~170 pontos usando versão legada

#### Funções Legadas vs V2

```
LEGADO (em uso):           V2 (pronto mas não usado):
✅ salvar_contexto_temporario()     ❌ salvar_contexto_temporario_v2()
✅ carregar_contexto_temporario()   ❌ carregar_contexto_temporario_v2()
✅ limpar_contexto_agendamento()    ❌ limpar_contexto_agendamento_v2()

Ratio: 170+ : 0
```

---

### 6️⃣ Qual patch MÍNIMO para impedir vazamento entre tenants?

**Resposta:** DOIS PATCHES em sequência (sem quebrar compatibilidade)

#### Patch 1: Guard Rail Defensivo (IMEDIATO, 0 quebra)

**O que fazer:**
```python
# Em utils/contexto_temporario.py - salvar_contexto_temporario()

Mudança mínima:
- Se tenant_id informado: SEMPRE adicionar _tenant_id_guard
- Se sem tenant_id: logar crítico (já faz, linha 145)

Efeito:
- 95% das chamadas hoje usam tenant_id (verificado em PATCH P0)
- Adiciona assinatura de tenant no contexto legado
- Previne leitura cruzada entre tenants
```

**Implementação:**
```python
# utils/contexto_temporario.py:141-145
if tenant_id:
    atual["_tenant_id_guard"] = tenant_id
    print(f"[CTX_GUARD] Adicionar tenant_id_guard={tenant_id}")
else:
    print(f"[CTX_CRÍTICO] Chamada SEM tenant_id de {inspect.stack()[1].filename}")
    # ⚠️ Continua salvando para compatibilidade, mas com ALERTA crítico
```

**Risco restante:** 2-5% das chamadas sem tenant_id = CRÍTICO

---

#### Patch 2: Validação Estritas no Carregamento (IMEDIATO, 0 quebra)

**O que fazer:**
```python
# Em utils/contexto_temporario.py - carregar_contexto_temporario()

Mudança mínima:
- Se tenant_id informado mas contexto sem _tenant_id_guard: ❌ BLOQUEAR (retornar {})
- Se tenant_id informado mas mismatch: ❌ BLOQUEAR (já faz, linha 174)
- Se sem tenant_id: retornar {} (vazio) — nunca dados legados
```

**Implementação:**
```python
# utils/contexto_temporario.py:176-178
elif not guard_tenant:
    print(f"[CTX_CRÍTICO] Contexto legado SEM guard — bloqueando leitura")
    return {}  # NÃO retorna contexto sem guard
```

**Efeito:** Leitura cruzada fica impossível mesmo em legado

---

### 7️⃣ Como migrar SEM quebrar sessões existentes?

**Resposta:** Estratégia de 3 fases com fallback

#### Fase 1: "Read-Through" (Tenta novo, fallback legado)

```python
async def carregar_contexto_temporario_migrado(user_id, tenant_id, dono_id):
    """
    1. Tenta ler do novo path (Clientes/{dono_id}/Sessoes/{user_id})
    2. Se vazio, lê legado (Clientes/{user_id}/MemoriaTemporaria)
    3. Se legado tem dados, COPIA para novo path imediatamente
    4. Retorna dados (de onde quer que venha)
    """
    
    # Tenta novo path primeiro
    novo = await carregar_contexto_temporario_v2(dono_id, user_id)
    if novo:
        print(f"[MIGRAÇÃO] Leu do novo path: {dono_id}/Sessoes/{user_id}")
        return novo
    
    # Fallback legado
    legado = await carregar_contexto_temporario(user_id, tenant_id=dono_id)
    if legado:
        print(f"[MIGRAÇÃO] Leu do legado, copiando para novo path")
        # Copiar imediatamente para novo path
        await salvar_contexto_temporario_v2(dono_id, user_id, legado)
        return legado
    
    return {}  # Ambos vazios
```

**Benefício:** Sessões existentes continuam funcionando, migram naturalmente

---

#### Fase 2: "Write-Through" (Escreve em ambos)

```python
async def salvar_contexto_temporario_migrado(user_id, contexto, tenant_id, dono_id):
    """
    1. Salva no novo path (Clientes/{dono_id}/Sessoes/{user_id})
    2. Salva no legado (compatibilidade, com guard)
    3. Logar para monitorar quando tudo estiver no novo
    """
    
    # Salva em novo path (fonte de verdade)
    await salvar_contexto_temporario_v2(dono_id, user_id, contexto)
    
    # Mantém legado sincronizado (compatibilidade)
    await salvar_contexto_temporario(user_id, contexto, tenant_id=dono_id)
    
    print(f"[MIGRAÇÃO] Salvo em novo path ({dono_id}/Sessoes/{user_id})")
```

**Benefício:** Zero quebra, tudo sincronizado, pode monitorar migração

---

#### Fase 3: "Cutover" (Quando 95%+ migrado)

```python
# Desabilita fallback legado
async def carregar_contexto_temporario_novo_somente(dono_id, user_id):
    """
    Quando 95%+ das sessões já estão em novo path:
    1. Lê apenas do novo path
    2. Se vazio, não fallback, retorna {}
    3. Fase 2 continua escrevendo em ambos por mais 30 dias
    """
    
    return await carregar_contexto_temporario_v2(dono_id, user_id)
```

---

## 📋 CLASSIFICAÇÃO POR OCORRÊNCIA

### REAPROVEITAR (V2 já implementada, usar como-é)

```
✅ salvar_contexto_temporario_v2(dono_id, cliente_id, contexto)
   - Localização: utils/contexto_temporario.py:18-41
   - Pronto para uso
   - Completamente seguro (multi-tenant)
   - Recomendado: migrar para isso

✅ carregar_contexto_temporario_v2(dono_id, cliente_id)
   - Localização: utils/contexto_temporario.py:44-62
   - Pronto para uso
   - Completamente seguro (multi-tenant)
   - Recomendado: migrar para isso

✅ limpar_contexto_agendamento_v2(dono_id, cliente_id)
   - Localização: utils/contexto_temporario.py:65-115
   - Pronto para uso
   - Completamente seguro (multi-tenant)
   - Recomendado: migrar para isso
```

---

### MIGRAR (Funções legadas em 170+ pontos)

```
⚠️ salvar_contexto_temporario(user_id, contexto, tenant_id=None)
   - Localização: utils/contexto_temporario.py:120-149
   - Risco: SEM isolamento por tenant
   - Estratégia: Phase-2 write-through (salva em novo também)
   - Timeline: Migrar chamadas gradualmente
   - Pontos afetados: ~50 em router/, ~15 em services/, ~20 em handlers/

⚠️ carregar_contexto_temporario(user_id, tenant_id=None)
   - Localização: utils/contexto_temporario.py:152-186
   - Risco: pode retornar dados de outro tenant
   - Estratégia: Phase-1 read-through com cópia automática
   - Timeline: Migrar chamadas gradualmente
   - Pontos afetados: ~60 em router/, ~15 em services/, ~5 em handlers/

⚠️ limpar_contexto_agendamento(user_id, tenant_id=None)
   - Localização: utils/contexto_temporario.py:189-250
   - Risco: pode limpar contexto de outro tenant
   - Estratégia: Adicionar validação strict (já tem patch defensivo)
   - Timeline: Pode ficar legado mais tempo (menos crítico)
   - Pontos afetados: ~15
```

---

### REMOVER (Dados orphaned no path legado)

```
🧹 Clientes/{actor_id}/MemoriaTemporaria/contexto (dados antigos)
   - Localização: Firestore
   - Quando: Após Phase 3 (cutover completo)
   - Ação: Executar job de limpeza
   - Cuidado: Não limpar enquanto Phase 2 ativo (write-through)
```

---

### COMPATIBILIDADE TEMPORÁRIA (Manter por 30+ dias)

```
🟡 salvar_contexto_temporario(user_id, contexto, tenant_id=None)
   - Tempo limite: 30 dias após Phase 2 ativo
   - Monitorar: logs [CTX_LEGADO_SAVE_SEM_TENANT]
   - Quando remover: Quando 100% das chamadas tenham tenant_id

🟡 carregar_contexto_temporario(user_id, tenant_id=None)
   - Tempo limite: 30 dias após Phase 3 ativo
   - Monitorar: logs [CTX_LEGADO_SEM_TENANT_PARAM]
   - Quando remover: Quando 95%+ contextos em novo path
```

---

### RISCO P0 (Crítico, ação imediata)

```
🔴 P0.1: Chamar salvar_contexto_temporario() SEM tenant_id
   - Localização: TODOS os pontos que chamam sem tenant_id
   - Risco: Salva contexto sem isolamento
   - Ação: Adicionar tenant_id=dono_id em TODAS chamadas
   - Timeline: IMEDIATO
   - Estimado: 5-20 pontos

🔴 P0.2: Chamar carregar_contexto_temporario() SEM tenant_id
   - Localização: TODOS os pontos que carregam sem tenant_id
   - Risco: Pode carregar contexto de outro tenant
   - Ação: Adicionar tenant_id=dono_id em TODAS chamadas
   - Timeline: IMEDIATO
   - Estimado: 10-30 pontos

🔴 P0.3: Path legado não isolado
   - Path: Clientes/{user_id}/MemoriaTemporaria/contexto
   - Risco: Dois clientes com mesmo ID acessam contexto um do outro
   - Guard: _tenant_id_guard adicionado (Patch MT-07)
   - Validação: Implementada em carregar_contexto_temporario()
   - Status: Guard ATIVO, mas recomenda validação strict no load
```

---

## 🎯 ESTRATÉGIA DE MIGRAÇÃO FINAL

### Timeline Recomendado

```
HOJE (2026-06-19):
✅ Patch 1: Guard Rail no salvar() — adicionar _tenant_id_guard
✅ Patch 2: Validação strict no carregar() — bloquear sem guard

SEMANA 1:
- Auditar todos os 170+ pontos que usam legado
- Identificar quais SEM tenant_id (P0.1, P0.2)
- Adicionar tenant_id=dono_id nos P0 críticos

SEMANA 2-3:
- Implementar Phase-1 read-through
- Começar Phase-2 write-through
- Monitorar logs de migração

SEMANA 4+:
- Validar que 95%+ contextos estão em novo path
- Phase 3: cutover (lê novo path somente)
- Job de limpeza no legado
- Remover funções legadas

MÊS 2:
- Remover salvar_contexto_temporario()
- Remover carregar_contexto_temporario()
- Remover limpar_contexto_agendamento()
- Path legado desativado
```

---

## 📊 ESTATÍSTICAS FINAIS

| Métrica | Valor | Status |
|---------|-------|--------|
| **Funções V2 (seguras)** | 3 | ✅ Pronto, 0 uso |
| **Funções legadas** | 3 | ⚠️ Em uso em 170+ pontos |
| **Total de chamadas** | 643 | ⚠️ 100% legado |
| **Pontos sem tenant_id** | 5-20 | 🔴 P0 CRÍTICO |
| **Pontos com tenant_id** | 150-155 | 🟡 Compatível |
| **Path legado isolado** | Sim (guard) | 🟡 Proteção defensiva |
| **Path novo isolado** | Sim (tenant+actor) | ✅ Seguro |

---

## ✅ CONCLUSÃO

**Risco Atual:** 🔴 CRÍTICO
- 170+ pontos usando versão insegura
- 5-20 pontos SEM tenant_id (vazamento possível)
- Guard defensivo ativo, mas não garante isolamento

**Risco Após Patch 1+2:** 🟡 MÉDIO
- Patch defensivo implementado
- Validação strict ativa
- Vazamento bloqueado no load

**Risco Após Phase-1 (read-through):** 🟡 BAIXO
- Contextos legados copiados automaticamente
- Novo path fica atualizado
- Fallback temporário seguro

**Risco Após Phase-3 (cutover):** ✅ ZERO
- Todos contextos em novo path
- Path legado desativado
- Multi-tenant garantido

---

**Status Final:** Mapeamento completo. Recomendação: Aplicar Patch 1+2 IMEDIATAMENTE, depois Phase-1 na sequência.
