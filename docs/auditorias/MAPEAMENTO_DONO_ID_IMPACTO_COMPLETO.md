# Mapeamento Completo: dono_id e Impacto de Alterações

**Data:** 2026-06-28  
**Status:** Auditoria de Impacto  
**Objetivo:** Entender completamente onde e como `dono_id` é utilizado antes de qualquer alteração  

---

## 📊 Resumo Executivo

```
Total de referências em principal_router.py: 63
Funções que dependem de dono_id: 15+
Padrão crítico: Multi-tenant isolation via dono_id
Risco de alteração: MUITO ALTO (quebra isolamento)
```

---

## 🔍 Pontos de Obtencão de dono_id

### 1️⃣ **Linha 63** — Função helper (contexto.py)
```python
dono_id = await obter_id_dono(user_id)
await salvar_contexto_temporario_v2(dono_id, user_id, ctx)
```
**Uso:** Salvamento isolado de contexto  
**Risco:** Se remover, perde isolamento por tenant  

### 2️⃣ **Linha 2261** — Meio do fluxo (PATCH_P0)
```python
# [PATCH_P0] Obter dono_id para salvar contexto com tenant_id correto
dono_id = await obter_id_dono(user_id)
```
**Uso:** Re-obtenção durante processamento  
**Por quê segunda vez?** Porque há funções que recebem parâmetros mas precisam garantir contexto correto  
**Risco:** Se remover, pode haver desincronização  

### 3️⃣ **Linha 3355** — Início da função principal
```python
dono_id = await obter_id_dono(user_id)
if not dono_id:
    dono_id = str(user_id)  # Fallback seguro
```
**Uso:** Resolver tenant para todo o fluxo  
**Risco:** CRÍTICO — sem isso, não há isolamento  

---

## 🎯 Padrões de Uso de dono_id

### Pattern A: Acesso a subcoleções
```python
# Linhas: 1096, 1191, 1301, 2134
profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
```
**Impacto:** Isolamento de dados por tenant  
**Quantidade:** 4 ocorrências  
**Risco:** ⚠️ ALTO — Sem dono_id correto, acessa dados de outro tenant  

### Pattern B: Salvamento de contexto V2
```python
# Linhas: 64, 1798, 1839, 1903, 2001, ... (14+ ocorrências)
await salvar_contexto_temporario_v2(dono_id, user_id, ctx)
```
**Impacto:** Persistência de estado com isolamento  
**Quantidade:** 14 ocorrências  
**Risco:** ⚠️ CRÍTICO — Contextos se misturam entre tenants  

### Pattern C: Passagem como parâmetro
```python
# Linhas: 1274, 1766, 1854, 2100, 2197, 3046
async def funcao_sub(dono_id: str, ...):
    # usa dono_id para construir paths
```
**Impacto:** Threading correto através de sub-handlers  
**Quantidade:** 15+ funções  
**Risco:** ⚠️ ALTO — Propagação de tenant_id errado afeta toda cadeia  

### Pattern D: Construção de identificadores
```python
# Linhas: 2070, 2075
ctx["clienteprofile_tenant_cliente"] = f"{dono_id}#{user_id}"
```
**Impacto:** Chaves compostas para isolamento  
**Quantidade:** 2 ocorrências  
**Risco:** ⚠️ MÉDIO — Chaves podem conflitar se dono_id errado  

### Pattern E: Operações validadas por tenant
```python
# Linhas: 1084, 1781
validacao = await validar_profissional_para_servico(dono_id, prof, servico)
```
**Impacto:** Validação de dados pertence a tenant correto  
**Quantidade:** 2 ocorrências  
**Risco:** ⚠️ ALTO — Valida profissional errado (multi-tenant)  

### Pattern F: Obtenção de profiles
```python
# Linha: 2064
profile = await obter_profile(dono_id, user_id)
```
**Impacto:** Recuperação de dados do perfil isolado  
**Quantidade:** 1 ocorrência  
**Risco:** ⚠️ ALTO — Profile de outro tenant  

---

## 📋 Função: obter_id_dono(user_id)

### Responsabilidade
```
user_id (pode ser cliente, pode ser dono)
    ↓
Resolver para tenant_id (sempre dono_id)
    ↓
Retornar dono_id ou None
```

### Contrato
```python
async def obter_id_dono(user_id: str) -> str | None:
    """
    Retorna: ID do dono do tenant que o user_id pertence
    
    Casos:
    - user_id é dono → retorna user_id
    - user_id é cliente → retorna tenant_id (dono que o criou)
    - user_id inexistente → retorna None
    """
```

### Por que é crítica
```
Sin dono_id resolvido:
- Não há isolamento multi-tenant
- Acessar dados de outro tenant
- Salvar contexto errado
- Validações incorretas
- UX: dados misturados entre clientes
```

---

## 🔗 Cadeia de Dependência

```
roteador_principal (linha 3355: obter dono_id)
    │
    ├─→ processar_resposta_onboarding_dono (pass dono_id)
    ├─→ resolver_confirmacao_pendente (pass dono_id)
    ├─→ extrair_slots_e_mesclar (pass dono_id → usa Profissionais/{dono_id})
    │
    └─→ (múltiplos handlers)
        │
        ├─→ validar_profissional_para_servico (pass dono_id)
        ├─→ buscar_subcolecao(Clientes/{dono_id}/...)
        ├─→ salvar_contexto_temporario_v2(dono_id, user_id, ctx)
        │
        └─→ obter_profile(dono_id, user_id)
```

**Criticalidade:** Se dono_id estiver ERRADO em QUALQUER nível:
- Toda a cadeia propaga o erro
- Difícil de diagnosticar (parece que funciona, mas com dados errados)
- Multi-tenant contamination

---

## ⚠️ Riscos de Alteração

### Risco 1: Remover obter_id_dono
```
❌ IMPACTO: 
- Sem resolução de tenant
- Usar user_id direto (inseguro)
- Dados de tenants se misturam
```

### Risco 2: Não passar dono_id para sub-funções
```
❌ IMPACTO:
- Funções não têm contexto de tenant
- Acessam dados de tenant errado
- Validações falham silenciosamente
```

### Risco 3: Usar dono_id de forma inconsistente
```
❌ IMPACTO:
- Alguns salvamentos com dono_id certo
- Outros com dono_id errado
- Contextos desincronizados em Firestore
```

### Risco 4: Remover segunda obtenção (linha 2261)
```
❌ IMPACTO:
- Alguns fluxos podem perder contexto correto
- Desincronização entre handlers
```

---

## ✅ Padrão Seguro de Alteração

**Se for necessário alterar algo relacionado a dono_id:**

1. ✅ Manter `obter_id_dono(user_id)` na entrada principal
2. ✅ Passar `dono_id` para TODAS as sub-funções
3. ✅ Usar `dono_id` (não `user_id`) para construir paths Firestore
4. ✅ Validar que isolamento multi-tenant está preservado
5. ✅ Executar teste com 2+ tenants simultâneos

**Exemplo seguro:**
```python
# Entrada
dono_id = await obter_id_dono(user_id)  ✅

# Propagação
resultado = await sub_funcao(dono_id, user_id, ctx)  ✅

# Acesso
path = f"Clientes/{dono_id}/Profissionais"  ✅

# Persistência
await salvar_contexto_temporario_v2(dono_id, user_id, ctx)  ✅
```

---

## 📊 Matriz de Impacto

| Linha | Padrão | Impacto | Risco |
|-------|--------|--------|-------|
| 63, 3355 | obter_id_dono | Resolução tenant | 🔴 CRÍTICO |
| 1096, 1191, 1301, 2134 | Acesso Firestore | Isolamento dados | 🔴 CRÍTICO |
| 64, 1798, 1839, ... | salvar V2 | Persistência isolada | 🔴 CRÍTICO |
| 1274, 1766, ... | Pass param | Propagação correto | 🟡 ALTO |
| 2070, 2075 | Chaves compostas | Identificação | 🟡 ALTO |
| 1084, 1781 | Validação | Negócio correto | 🟡 ALTO |
| 2064 | obter_profile | Dados perfil | 🟡 ALTO |

---

## 🚨 Conclusão

**dono_id é o linchpin do isolamento multi-tenant.**

Qualquer alteração que afete:
- Resolução de dono_id
- Propagação de dono_id
- Uso de dono_id em paths/validações

**Deve ser acompanhada de:**
1. Testes multi-tenant explícitos
2. Validação de isolamento
3. Auditoria de Firestore (confirmar dados isolados)
4. Regressão completa

---

## 📝 Checklist Antes de Alterar

```
[ ] Entendi por que dono_id é obtido em 3 lugares?
[ ] Verifiquei que TODAS as sub-funções recebem dono_id?
[ ] Confirmei que paths Firestore usam dono_id (não user_id)?
[ ] Testei com 2+ tenants de forma independente?
[ ] Regressão completa: P0 174/174, SEG-05B 13/13?
[ ] Validei isolamento: dados de um tenant não vazam em outro?
[ ] Documentei o motivo da alteração?
[ ] Deixei fallback seguro (user_id como fallback)?
```

Se algum [ ] não puder ser marcado: **NÃO PROSSEGUIR COM ALTERAÇÃO.**

---

**Última auditoria:** 2026-06-28  
**Próxima ação:** Aguardar aprovação antes de qualquer modificação em padrão de dono_id
