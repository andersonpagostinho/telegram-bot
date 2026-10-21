# 🚀 DEPLOY — P0.5 Proteção contra `data_hora=None` (2026-10-21)

## Resumo da Correção

**Problema:** `resolver_alteracao_draft_agendamento()` acessava `data_hora.split()` na seção de ALTERAÇÃO DE HORÁRIO (linha 2822) sem validar se era `None`, causando `AttributeError` quando draft estava incompleto.

**Solução:** Guard defensivo antes de `.split()` na linha 2822, seguindo o padrão já aplicado em 2965.

**Commit:** `112f91a` - Fix: P0.5 Proteção contra data_hora=None em ajuste de horário

---

## Mudanças Implementadas

### Arquivo: `router/principal_router.py` (linhas 2822-2829)

**ANTES:**
```python
if alteracao.get("tipo") == "horario":
    direcao = alteracao.get("direcao")

    data = data_hora.split("T")[0]  # ← FALHA SE data_hora=None
    hora_atual = data_hora.split("T")[1][:5]
```

**DEPOIS:**
```python
if alteracao.get("tipo") == "horario":
    direcao = alteracao.get("direcao")

    # GUARD P0.5: Verificar se data_hora é None antes de split (draft incompleto)
    if not data_hora:
        await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)
        return await _send_and_stop(
            context,
            user_id,
            "Preciso que você me diga a data e hora do agendamento. Qual data você prefere?",
            parse_mode=None
        )

    data = data_hora.split("T")[0]
    hora_atual = data_hora.split("T")[1][:5]
```

---

## Validação Realizada

### Testes com Mocks (7/7 PASS)
- ✅ T1: Draft incompleto sem data_hora
- ✅ T2: Draft completo com ajuste
- ✅ T3: Dados de confirmação com data
- ✅ T4: Consulta informativa
- ✅ T6: Ajuste de horário SEM data_hora
- ✅ T7: Ajuste de horário COM data_hora válida
- ✅ T8: Regressão em ajuste de profissional

**Arquivo de testes:** `tests/test_p05_data_hora_none_correcao.py`

---

## Restrições Cumpridas

| Restrição | Status |
|-----------|--------|
| Escopo limitado (apenas linha 2822, não 3299) | ✅ |
| Sem escrever em Firestore real | ✅ |
| Sem alterar classificador GPT | ✅ |
| Sem alterar roteador ou outra seção | ✅ |
| Sem inventar dados ou horários | ✅ |
| Sem commit/push até autorização | ✅ |

---

## Risk Assessment

🟢 **LOW RISK**

- Mudança minimal (11 linhas, apenas guard defensivo)
- Segue exatamente padrão de 2965 (reutiliza estrutura)
- Não afeta fluxos legítimos (apenas bloqueia acesso a .split() de None)
- Testes com mocks validam 100%
- Sem Firebase real consumido (quota preservada em 90%)

---

## Rollback

Se necessário:
```bash
git revert 112f91a
git push origin main
```

---

## Deploy Instructions

### Pré-Deploy Checklist
- ✅ Commit `112f91a` está em `origin/main`
- ✅ 7/7 testes focados PASS
- ✅ Sem Firebase real consumido
- ✅ Escopo rigorosamente limitado

### Passos de Deploy
1. Fazer deploy do commit `112f91a` do branch `main`
2. Monitorar logs para `AttributeError` em linha 2822 (deve desaparecer)
3. Testar em produção:
   - Consulta de horário: "Tem horário para hoje às 15 com a Bruna?"
   - Ajuste de horário com draft incompleto: "Mais cedo, por favor"

### Validação Pós-Deploy
- ✅ Nenhum `AttributeError: 'NoneType' object has no attribute 'split'` em 2822
- ✅ Mensagem clara enviada ao usuário se data_hora faltante
- ✅ Ajustes com data_hora válida continuam funcionando

---

## Nota: Ocorrência não coberta

**Linha 3299** (alteração de DATA) tem falha similar, mas **NÃO foi protegida** conforme escopo autorizado. Se necessário, seguir mesmo padrão:
```python
if alteracao.get("tipo") == "data":
    nova_data = alteracao.get("valor")
    
    # Similar guard aqui se data_hora pode ser None
```

---

**Status:** ✅ **READY FOR PRODUCTION DEPLOYMENT**
**Date:** 2026-10-21 15:55 UTC
**Tested:** 7/7 mocks PASS, quota preserved
