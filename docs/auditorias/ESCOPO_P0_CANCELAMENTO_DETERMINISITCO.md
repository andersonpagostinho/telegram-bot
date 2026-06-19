# ESCOPO: P0 Cancelamento Determinístico

**Data**: 2026-06-19  
**Complexidade**: ALTA (novo motor determinístico)  
**Status**: Escopo e Plano

---

## 1. PROBLEMA CONFIRMADO

**Cenário**: Estado `aguardando_confirmacao_cancelamento` + mensagem "Com a Bruna"

**Comportamento errado**:
```
Message: "Com a Bruna"
Estado: aguardando_confirmacao_cancelamento
Resultado: ❌ Interpretado como ajuste_incremental
Efeito: Chama resolver_alteracao_draft_agendamento() → quebra com data_hora=None
```

**Causa**: Falta guarda que bloqueia ajuste incremental quando em cancelamento

---

## 2. REGRA ARQUITETURAL

### Hierarquia de Estados

```
aguardando_confirmacao_cancelamento
    ↓ (bloqueia)
- Ajuste incremental
- Fluxo de draft de agendamento
- Interpretação GPT genérica
    ↓ (permite)
- Motor determinístico de cancelamento
- Desambiguação de candidatos
- Confirmação final
```

### Fluxo Correto

```
Intenção de cancelamento
    ↓
Localizar eventos candidatos (filtros)
    ↓
Desambiguar (1 vs múltiplos)
    ↓
Pedir confirmação explícita
    ↓
Alteração de status (status='cancelado')
    ↓
Histórico + liberar horário
```

---

## 3. TRABALHO NECESSÁRIO

### Fase 1: Bloquear Ajuste Incremental (CRÍTICO)

**Localização**: Antes de todas as chamadas a `resolver_alteracao_draft_agendamento()`

**Guardas necessárias** (linhas):
- 5314
- 5366
- 5399
- 5654
- 9497

**Código**:
```python
# Adicionar ANTES de cada chamada:
if ctx.get("estado_fluxo") == "aguardando_confirmacao_cancelamento":
    return await resolver_fluxo_cancelamento(...)
    # (não chama resolver_alteracao_draft_agendamento)
```

### Fase 2: Motor Determinístico de Cancelamento (IMPLEMENTAÇÃO)

**Função**: `async def resolver_fluxo_cancelamento(update, context, user_id, ctx, texto_usuario, dono_id)`

**Lógica**:
1. Extrair features (profissional, data, hora, serviço) da mensagem
2. Buscar eventos em `Clientes/{dono_id}/Eventos` com filtros
3. Validar status (ativo/agendado/confirmado)
4. Desambiguar:
   - 0 resultados → "Não encontrei agendamento ativo..."
   - 1 resultado → "Encontrei X. Pode confirmar?"
   - N resultados → Listar numeradas com opção de seleção
5. Aguardar confirmação final ("sim" ou número)
6. Alteração de status: `status='cancelado'`
7. Salvar histórico em `evento.historico_cancelamento`

### Fase 3: Testes (9 testes obrigatórios)

Conforme especificado no escopo do usuário.

### Fase 4: Validação Multi-tenant

- Todas as buscas em `Clientes/{dono_id}/Eventos`
- Nunca `Clientes/{actor_id}/Eventos` exceto se actor_id == dono_id
- Usar `tenant_id=dono_id` em todos os salva_contexto

---

## 4. IMPLEMENTAÇÃO RECOMENDADA

### Passo 1: Guarda Simples (10 minutos)

Adicionar antes de cada `resolver_alteracao_draft_agendamento()`:

```python
# Bloquear ajuste incremental durante cancelamento
if ctx.get("estado_fluxo") == "aguardando_confirmacao_cancelamento":
    # Redirecionar para fluxo de cancelamento
    # Por enquanto, resposta segura:
    return await _send_and_stop(
        context,
        user_id,
        "Para cancelar, diga qual horário ou profissional. Ex: 'Com a Bruna amanhã à noite'"
    )
```

**Benefício**: Bloqueia quebra imediata; impede cair em resolver_alteracao

**Tempo**: ~10 min (5 locais, mesmo padrão)

### Passo 2: Implementação Completa (2-3 horas)

Implementar `resolver_fluxo_cancelamento()` com:
- Extração de features (use regex existente)
- Busca em Firestore (use buscar_subcolecao existente)
- Filtros (profissional, data, hora, status)
- Desambiguação (1 vs N)
- Confirmação + alteração de status

**Benefício**: Fluxo completo e determinístico

### Passo 3: Testes (1 hora)

9 testes conforme especificado

**Benefício**: Validação de todos os cenários

---

## 5. RECOMENDAÇÃO

### IMEDIATO (Hoje)

Implementar **Passo 1 (Guarda Simples)** para bloquear quebra:
- ✅ Previne UnboundLocalError/AttributeError
- ✅ Redireciona para fluxo seguro
- ✅ Tempo: ~10 min
- ✅ Risco: ZERO

### PRÓXIMO (Amanhã)

Implementar **Passo 2 + 3 (Motor Completo + Testes)**:
- ✅ Fluxo determinístico completo
- ✅ Suporta desambiguação
- ✅ Multi-tenant correto
- ✅ Tempo: ~3 horas

---

## 6. ESTRUTURA DE CÓDIGO

### Funções a implementar/modificar

```
resolver_fluxo_cancelamento()
    ├─ extrair_features_cancelamento(texto_usuario)
    ├─ buscar_eventos_candidatos(dono_id, profissional, data, hora, status)
    ├─ desambiguar_candidatos(candidatos)
    ├─ pedir_confirmacao(candidato ou candidatos)
    ├─ alteracao_status_cancelado(evento_id, dono_id)
    └─ salvar_historico_cancelamento(evento_id, motivo)
```

### Guardar em bloco

```
linha 5314 (antes de resolver_alteracao_draft_agendamento)
    ↓
if ctx.get("estado_fluxo") == "aguardando_confirmacao_cancelamento":
    return await resolver_fluxo_cancelamento(...)
```

---

## 7. MULTI-TENANT CHECKLIST

- [ ] Todas as buscas usam `Clientes/{dono_id}/Eventos`
- [ ] Nunca `Clientes/{actor_id}/Eventos`
- [ ] `dono_id` resolvido no início da função roteador_principal()
- [ ] `tenant_id=dono_id` em todas as salvar_contexto
- [ ] Validar que evento.dono_id == dono_id antes de cancelar

---

## 8. PRIORIZAÇÃO

### P0 (CRÍTICO — Hoje)
1. ✅ Guarda para bloquear ajuste incremental
2. ✅ Resposta segura que redireciona para cancelamento

### P1 (IMPORTANTE — Amanhã)
3. ⏳ Motor determinístico de busca
4. ⏳ Desambiguação de candidatos
5. ⏳ Confirmação + cancelamento

### P2 (MELHORIAS)
6. ⏳ Histórico detalhado de cancelamento
7. ⏳ Notificações após cancelamento
8. ⏳ Liberação automática de horários

---

**Próxima Ação**: Implementar Guarda Simples (Passo 1) como P0 CRÍTICO hoje.

