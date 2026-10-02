# INVESTIGAÇÃO — FLUXO PÓS-P3

**Data:** 2026-10-01  
**Objetivo:** Rastrear caminho após `detectar_alteracao_draft_agendamento()` retorna `None`

---

## CENÁRIO

```
Mensagem: "quero um corte para amanhã às 9"

Contexto Atual:
  servico: "corte"
  data_hora: "2026-10-02T09:00:00"
  profissional: None
  estado_fluxo: "aguardando_profissional"
  draft_agendamento: {
    "servico": "corte",
    "data_hora": "2026-10-02T09:00:00",
    "profissional": None
  }

Com P3:
  detectar_alteracao_draft_agendamento() → None (porque data_hora é idêntica)
```

---

## CALLSITE PRINCIPAL: Linha 5048

**Arquivo:** router/principal_router.py  
**Função:** roteador_principal()  
**Contexto:** Bloco de ajuste incremental / preenchimento de slot

### Código

```python
5045: if ctx.get("intencao_conversacional") == "indefinida":
5046:     alteracao = None
5047: else:
5048:     alteracao = await detectar_alteracao_draft_agendamento(...)
5053: 
5054: # SLOT FALTANTE — profissional
5055: if (
5056:     alteracao
5057:     and alteracao.get("tipo") == "profissional"
5058:     and ctx.get("estado_fluxo") == "aguardando_profissional"
5059: ):
```

### Comportamento Com P3

**Quando `alteracao = None`:**
- Linha 5055 `if alteracao`: **FALSE** (porque None é falsy)
- **NÃO entra** no bloco de preenchimento de slot profissional
- Fluxo continua a próxima seção

---

## FLUXO APÓS ALTERACAO = NONE

**Callsite 1 não processa nada → Continua para próximo bloco importante**

### Bloco: Preenchimento de Serviço (Linha ~5260-5440)

```python
if (
    alteracao
    and alteracao.get("tipo") == "servico"
    and ctx.get("estado_fluxo") == "aguardando_servico"
):
    # ... processa mudança de serviço
```

**Comportamento:** `alteracao = None` → **NÃO entra**

### Bloco: Preenchimento de Data (Linha ~5457+)

```python
if (
    alteracao
    and alteracao.get("tipo") == "data"
    and ctx.get("estado_fluxo") == "aguardando_data"
):
    # ... processa mudança de data
```

**Comportamento:** `alteracao = None` → **NÃO entra**

---

## ONDE INTERCEPTA AGENDAMENTO_DIRETO?

### Localização: Linha 3670

**Arquivo:** router/principal_router.py  
**Contexto:** Bloco de roteamento por intenção

```python
3670: if (
3671:     (ctx.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"])
3672:     and not ctx.get("aguardando_confirmacao_agendamento")
3673: )
```

### Dentro deste bloco, Linha 3723

```python
3723: if ctx.get("estado_fluxo") == "aguardando_profissional":
         # [INTERCEPTOR: BLOQUEIA NOVO AGENDAMENTO COM ESTADO ATIVO]
```

---

## PROBLEMA IDENTIFICADO

### Sequência Real

```
1. Mensagem: "quero um corte para amanhã às 9"
   ↓
2. Classificação: intencao_conversacional = "agendamento_direto"
   ↓
3. Linha 3670: `if intencao_conversacional in ["agendamento_direto", ...]`
   ↓
4. Linha 3723: `if estado_fluxo == "aguardando_profissional"`
   ↓
5. [CÓDIGO NESTA LINHA REDIRECIONA OU BLOQUEIA]
```

### Verificação Obrigatória

**Localização:** router/principal_router.py:3720-3750  
**Questão:** O que o código faz quando `estado_fluxo == "aguardando_profissional"` DENTRO do bloco de `agendamento_direto`?

---

## ACHADOS PRELIMINARES

| Linha | Situação | Comportamento |
|-------|----------|---------------|
| 5048 | `alteracao` chamado | Retorna None para data idêntica |
| 5055 | `if alteracao:` | **False (None)** → Não processa slot |
| 3670 | `if agendamento_direto:` | **True** → Entra no bloco |
| 3723 | `if estado_fluxo == "aguardando_profissional":` | **True** → Código crítico aqui |

---

## 🔴 CAUSA RAIZ ENCONTRADA — LINHA 3670-3680

### Localização Exata

**Arquivo:** router/principal_router.py  
**Linhas:** 3670-3680  
**Bloco:** Detecção de novo agendamento (PATCH_P0.5)

### Código Problemático

```python
3670: if (
3671:     (ctx.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"])
3672:     and not ctx.get("aguardando_confirmacao_agendamento")
3673: ):
3674:     print(f"[PATCH_P0.5] Novo agendamento detectado via intenção_conversacional...")
3675:     ctx.pop("motivo_estado", None)
3676:     ctx.pop("estado_fluxo", None)              # ← DELETA ESTADO!
3677:     ctx.pop("profissional_rejeitado", None)
3678:     ctx.pop("profissionais_validos", None)
3679:     ctx.pop("draft_agendamento", None)         # ← DELETA DRAFT!
3680:     ctx.pop("profissional_escolhido", None)
```

### Problema

Quando mensagem é classificada como **"agendamento_direto"**:

```
"quero um corte para amanhã às 9" (com draft residual)
    ↓
Classificador: intencao_conversacional = "agendamento_direto"
    ↓
Linha 3670-3680: CONDIÇÃO VERDADEIRA (agendamento_direto E não aguardando_confirmacao)
    ↓
ctx.pop("estado_fluxo")           [REMOVE estado_fluxo = "aguardando_profissional"]
ctx.pop("draft_agendamento")      [REMOVE servico=corte, data_hora, profissional=None]
    ↓
Toda a informação anterior é APAGADA
    ↓
Fluxo começa do ZERO (não reconhece servico/data_hora já fornecidos)
```

### Resultado Observado

Ao invés de:
```
servico = corte
data_hora = 2026-10-02T09:00:00
profissional = None
→ Pergunta qual profissional? ✅
```

Acontece:
```
Estado deletado
Draft deletado
→ Começa do zero
→ Comportamento inesperado ❌
```

---

## IMPACTO DO P3

O P3 **não causou** este problema. O P3 apenas bloqueou a **falsa alteração** retornando `None`.

**Antes do P3:**
- detectar_alteracao_draft_agendamento() retornava `{"tipo": "data_hora"}`
- resolver_alteracao_draft_agendamento() era chamada
- Exibia "Consigo ajustar o horário..." ❌

**Com o P3:**
- detectar_alteracao_draft_agendamento() retorna `None`
- **REVELA** o segundo problema: linha 3670-3680 deleta o draft quando vê "agendamento_direto"

---

## RECOMENDAÇÃO PARA INVESTIGAÇÃO FUTURA

**Questão:** Por que o PATCH_P0.5 (linhas 3670-3680) deleta o estado/draft quando vê "agendamento_direto"?

**Análise:** 
- Se o objetivo era limpar estado anterior para novo agendamento, faz sentido SOMENTE se não há draft ativo
- Quando há draft ativo com estado_fluxo="aguardando_profissional", deletar significa perder contexto

**Possível Solução (conceitual, não implementada):**
```python
if (
    (ctx.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"])
    and not ctx.get("aguardando_confirmacao_agendamento")
    and ctx.get("estado_fluxo") != "aguardando_profissional"  # ← Não deletar se aguardando profissional
):
    # ... delete state ...
```

---

**Status:** CAUSA RAIZ IDENTIFICADA — BLOQUEADOR SECUNDÁRIO (Sem alterações conforme instrução)
