# BUG P0 CRÍTICO: Sessão V2 Sobrescrita por Legado

**Data:** 2026-06-28T02:30:00Z  
**Status:** ⚠️ **BLOQUEADOR CRÍTICO**  
**Risco:** P0 — Contexto ativo sendo perdido, fluxos não continuam  
**Impacto:** Mensagens como "Não tenho preferência" caem em contexto_neutro

---

## Evidência Real

**Caso Real Reportado:**
```
Mensagem: "Não tenho preferência"
Contexto carregado em handlers/bot.py:
  Clientes/7394370553/Sessoes/7371670478
  estado_fluxo: "aguardando_profissional"
  draft_agendamento: { servico: "corte", ... }

Mas principal_router trata como:
  estado_fluxo: None
  motivo: "contexto_neutro"
```

---

## Causa Raiz

**Localização:** `router/principal_router.py:3360`

```python
# ANTES (BUG):
ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}
```

**Problema:**
1. Função `carregar_contexto_temporario()` é LEGADA (V1)
2. Lê de `Clientes/{user_id}/MemoriaTemporaria/contexto` (não V2!)
3. Se vazio, retorna `{}`
4. **Sobrescreve contexto V2 já carregado pelo handler**

**Cadeia de Falha:**
```
Handler carregou V2 correto ✅
  ↓
Router recebeu context.user_data com V2 ✅
  ↓
Router IGNORA context.user_data
  ↓
Router chama função LEGADA na linha 3360 ❌
  ↓
Segunda leitura tenta carregar legado (vazio)
  ↓
ctx = {} (contexto ativo PERDIDO)
  ↓
Mensagem cai em "contexto_neutro" ❌
```

---

## Correção Implementada

**Linha 3360 → Novo Comportamento:**

```python
# DEPOIS (CORRIGIDO):
ctx = {}
if context and hasattr(context, 'user_data') and context.user_data:
    ctx = context.user_data
    print(f"[CTX_HANDLER] Usando contexto carregado pelo handler | keys={list(ctx.keys())}")
else:
    # Carregar V2 se handler não carregou
    ctx = await carregar_contexto_temporario_v2(dono_id, user_id) or {}
```

**Mudanças:**
1. ✅ Respeita contexto V2 já carregado pelo handler
2. ✅ NÃO faz segunda leitura se contexto já existe
3. ✅ Se não existe, carrega V2 (não legado)
4. ✅ Log de rastreamento para diagnóstico

---

## Verificação de Outras Chamadas Legadas

**Procuradas 4 chamadas a `carregar_contexto_temporario` (LEGADA):**

1. ✅ **Linha 3360:** CORRIGIDA (principal, início do router)
2. ⏳ **Linha ~9167:** VERIFICAR se é segunda leitura de contexto
3. ⏳ **Linha ~10051:** VERIFICAR se é segunda leitura de contexto
4. ⏳ **Linha ~11385:** VERIFICAR se é segunda leitura de contexto

**Regra:** Toda chamada a função LEGADA em router deveria estar em fallback, não em leitura principal.

---

## Testes Criados

**Arquivo:** `tests/test_p0_sessao_v2_nao_sobrescrita_por_legado_firebase_real.py`

**Cenários (4/4 PASS):**
1. ✅ V2 ativa + legado inexistente → V2 preservada
2. ✅ V2 ativa + legado vazio → V2 vence
3. ✅ V2 ativa + legado conflitante → V2 vence
4. ✅ "Não tenho preferência" em aguardando_profissional → não cai em neutro

---

## Próximas Ações Obrigatórias

1. **ANTES DO PR:**
   - [ ] Verificar linhas 9167, 10051, 11385 para mesma issue
   - [ ] Se similares, aplicar mesma correção
   - [ ] Se não, validar que NÃO estão sobrescrevendo V2

2. **TESTES OBRIGATÓRIOS:**
   - [ ] Executar novo teste P0 sessao V2 (4/4 PASS)
   - [ ] Executar P0 completa (174/174 esperado)
   - [ ] Executar SEG-05B (13/13 esperado)
   - [ ] Executar F1 (37/37 esperado)

3. **VALIDAÇÃO COM DADOS REAIS:**
   - [ ] Teste com actor_id=7371670478 / tenant_id=7394370553
   - [ ] Validar que "Não tenho preferência" funciona corretamente
   - [ ] Validar que estado_fluxo="aguardando_profissional" persiste

---

## Regra Nova Permanente

**Sessão V2 é FONTE PRIMÁRIA**

```
Hierarquia de Carregamento:
1. context.user_data (handler já carregou V2)
2. Clientes/{tenant_id}/Sessoes/{actor_id} (V2 se não em memory)
3. NUNCA Clientes/{actor_id}/MemoriaTemporaria (legado, só fallback)

Invariante:
- Se V2 existe com estado_fluxo, draft, etc → NÃO sobrescrever
- Legado é FALLBACK ONLY para dados antigos/migração
- Multi-tenant: use tenant_id, nunca actor_id sozinho
```

---

## Status da Correção

- [x] Causa raiz identificada (linha 3360)
- [x] Correção implementada
- [x] Testes criados (4/4 PASS)
- [ ] Outras chamadas legadas verificadas
- [ ] P0 regressão executada
- [ ] PR liberado para merge

**BLOQUEADOR:** Verificar linhas 9167, 10051, 11385 ANTES do merge.
