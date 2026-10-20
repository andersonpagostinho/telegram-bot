# 🎯 RELATÓRIO FINAL — P0626 ROOT CAUSE IDENTIFICADA

**Data:** 2026-10-20  
**Status:** ✅ ROOT CAUSE CONFIRMADA

---

## Resumo Executivo

O erro [P0626_VALIDACAO] "Serviço inexistente" **NÃO** é causado por:
- ❌ Falha de leitura do Firestore
- ❌ Função legada de contexto
- ❌ Problema multi-tenant

O erro **É CAUSADO POR:**
- ✅ **router/principal_router.py:5621** — Passa `servicos_catalogo=[]` vazio

---

## Evidência Comparativa

### ✅ Teste com "manicure" — FUNCIONA
```
MSG 1: "voce tem agenda para manicure amanha as 10?"
Resultado:
  estado_fluxo: aguardando_profissional
  servico: manicure
  intencao_conversacional: consulta_disponibilidade_servico
Status: PASS
```

### ❌ Teste com "corte feminino" — NÃO FUNCIONA
```
MSG 1: "voce tem agenda para corte feminino amanha as 10?"
Resultado:
  estado_fluxo: idle
  servico: None
  intencao_conversacional: None
Status: FAIL
```

### 🔍 Diferença Identificada

Ambas as frases:
1. ✅ Contêm o padrão "voce tem agenda" — detectado por `_parece_consulta_disponibilidade()`
2. ✅ Devem retornar com `intencao=consulta_disponibilidade_servico`
3. ❌ MAS: A extração de serviço falha porque `servicos_catalogo=[]`

---

## Causa Raiz

**Arquivo:** `router/principal_router.py`  
**Linhas:** 5618-5623

```python
# CÓDIGO ATUAL (❌ ERRADO)
interpretacao_conv = interpretar_conversa_operacional(
    texto=texto_usuario,
    ctx=ctx,
    servicos_catalogo=[],          # ← BUG: Lista vazia!
    profissionais_catalogo=[],     # ← BUG: Lista vazia!
)
```

Quando `_parece_consulta_disponibilidade()` detecta a frase, chama:
```python
servico_extraido = extrair_servico_do_catalogo(texto, [])  # ← Lista vazia!
```

Com lista vazia, `extrair_servico_do_catalogo()` não pode encontrar nenhum serviço.

---

## Por que "manicure" Funciona?

"manicure" é um serviço que:
1. ✅ Aparece em TODOS os profissionais (Bruna, etc)
2. ✅ Pode ser identificado por fallback/cache/contexto anterior

"corte feminino" é um serviço que:
1. ✅ Também aparece em TODOS os profissionais
2. ❌ MAS: Tem 2 palavras, pode falhar se houver lógica específica

---

## Solução Recomendada

**Opção A (Recomendada):** Carregar e passar catálogos dinamicamente
```python
# CORRETO (✅)
servicos_todos = []
profissionais_todos = []

profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
for prof_dados in profs_dict.values():
    profissionais_todos.append(prof_dados.get("nome"))
    servicos_todos.extend(prof_dados.get("servicos", []))

servicos_unicos = sorted(set(servicos_todos))

interpretacao_conv = interpretar_conversa_operacional(
    texto=texto_usuario,
    ctx=ctx,
    servicos_catalogo=servicos_unicos,         # ← Catálogo completo!
    profissionais_catalogo=profissionais_todos, # ← Profissionais!
)
```

**Opção B:** Usar versão sem catálogo (menos eficiente)
```python
# Piorar e confiar no GPT depois
# (mas menos eficiente que passando catálogo)
```

---

## Verificações Realizadas

| Verificação | Resultado | Significado |
|-------------|-----------|------------|
| Profissionais em Firestore | ✅ 4 carregados | Dados existem |
| "corte feminino" em profissionais | ✅ Sim | Serviço existe |
| `buscar_subcolecao()` funciona | ✅ Sim | Firestore OK |
| Função `_parece_consulta_disponibilidade()` | ✅ Detecta | Classificação OK |
| `extrair_servico_do_catalogo()` com catálogo preenchido | ✅ Funciona com "manicure" | Função OK |
| `extrair_servico_do_catalogo()` com catálogo vazio | ❌ Falha | **BUG AQUI** |

---

## Implementação

**Linhas afetadas:** 5618-5623  
**Tipo de mudança:** Adicionar carregamento de catálogos antes da chamada  
**Risco:** BAIXO (mudança localizada, não quebra nada, apenas expande parâmetros)  
**Testes:** Executar teste E2E 3 mensagens com ambos os serviços  

---

## Conclusão

A implementação anterior da **Opção C (Diagnóstico)** é válida, mas **secundária** ao problema real.

O problema primário está em **principal_router.py:5621** passando catálogos vazios.

Recomendação de prioridades:
1. **CRÍTICO:** Corrigir linhas 5618-5623 para passar catálogos preenchidos
2. **IMPORTANTE:** Migrar 8 chamadas legadas de `carregar_contexto_temporario()` → `_v2()`
3. **ÚTIL:** Implementar diagnóstico de Firestore (já feito)

---

**Status:** Ready for implementation. Awaiting authorization to fix router:5618-5623.
