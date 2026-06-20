# DIAGNÓSTICO AUTOMATIZADO — Contexto Órfão Após Cancelamento

## 📋 Objetivo

Provar a hipótese: `ctx.pop(...) + merge=True não remove campos do Firestore`.

## 🚀 Como Executar

### Pré-requisitos

- Firebase configurado e credenciais no ambiente
- Python 3.7+
- Dependências: `firebase-admin`, `google-cloud-firestore`

### Executar o teste

```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"

python tests/debug/teste_diagnostico_contexto_orfao_cancelamento.py
```

## 📊 O que o teste faz

### Etapa 1: Criar Contexto Sujo
- Cria documento em `Clientes/{tenant_id}/Sessoes/{actor_id}`
- Adiciona campos sujos:
  - `estado_fluxo="aguardando_confirmacao_cancelamento"`
  - `cancelamento_pendente={...}`
  - `draft_agendamento={...}`
  - `dados_confirmacao_agendamento={...}`
  - `aguardando_confirmacao_agendamento=True`

### Etapa 2: Carregar e Validar
- Carrega contexto do Firestore
- Valida que TODOS os campos existem

### Etapa 3: Limpeza Atual (pop + merge)
- Simula exatamente o que o handler faz:
  ```python
  ctx.pop("cancelamento_pendente", None)
  ctx.pop("draft_agendamento", None)
  ctx.pop("dados_confirmacao_agendamento", None)
  ctx["estado_fluxo"] = "idle"
  atualizar_dado_em_path(path, ctx)  # merge=True
  ```

### Etapa 4: Verificar Problema
- Recarrega do Firestore
- Verifica se campos removidos ainda existem
- **SE SIM:** Problema confirmado ✅
- **SE NÃO:** Problema não existe ❌

### Etapa 5-6: Testar Patch com DELETE_FIELD
- Aplica patch com `DELETE_FIELD` explícito:
  ```python
  payload = {
      "estado_fluxo": "idle",
      "cancelamento_pendente": DELETE_FIELD,
      "draft_agendamento": DELETE_FIELD,
      "dados_confirmacao_agendamento": DELETE_FIELD,
  }
  db.document(path).update(payload)
  ```
- Valida que DELETE_FIELD funciona

### Etapa 7: Limpeza
- Remove documento de teste do Firestore

## 📊 Resultado

Gera arquivo JSON: `resultado_diagnostico_contexto_orfao_cancelamento.json`

Exemplo de resultado:
```json
{
  "timestamp": "2026-06-19T...",
  "tenant_id": "dono_test_123",
  "actor_id": "user_test_7371670478",
  "etapas": [...],
  "conclusao": {
    "problema_encontrado": true,
    "hipotese_confirmada": true,
    "patch_delete_field_funciona": true,
    "recomendacao": "Usar DELETE_FIELD em salvar_contexto_temporario()"
  }
}
```

## 🔍 Interpretação dos Resultados

### ✅ Se `problema_encontrado = true`

**Significa:**
- `ctx.pop()` remove localmente MAS não do Firestore
- `merge=True` preserva campos não mencionados
- DELETE_FIELD é a solução

**Ação:**
- Implementar patch em `utils/contexto_temporario.py`
- Usar `DELETE_FIELD` explicitamente

### ❌ Se `problema_encontrado = false`

**Significa:**
- Problema NÃO é merge=True
- Causa raiz diferente:
  - Contexto carregado de cache stale?
  - Carregamento lê path errado?
  - Outro motivo?

**Ação:**
- Investigar logs diagnósticos
- Verificar instrumentação adicional

## 📝 Próximos Passos Após Resultado

### Se Hipótese Confirmada (problema=true)

1. **Leitura:** Verificar resultado JSON
2. **Análise:** Entender por que DELETE_FIELD é necessário
3. **Implementação:** Modificar `salvar_contexto_temporario()` para usar DELETE_FIELD
4. **Validação:** Rerun do teste automatizado após patch

### Se Hipótese Refutada (problema=false)

1. **Análise:** Qual é a verdadeira causa?
2. **Investigação:** Voltar aos logs [DIAG_*]
3. **Hipótese 2:** Verificar se problema é no load (cache/path errado)

## 📚 Referência

- **Script:** `tests/debug/teste_diagnostico_contexto_orfao_cancelamento.py`
- **Resultado:** `tests/debug/resultado_diagnostico_contexto_orfao_cancelamento.json`
- **Análise original:** `docs/auditorias/DIAGNOSTICO_SAVE_LOAD_CANCELAMENTO_ORFAO.md`
- **Auditoria:** `docs/auditorias/AUDITORIA_CANCELAMENTO_CONTEXTO_ORFAO.md`

## 🚨 Importante

**NÃO altera produção:**
- Teste cria/remove apenas dados de teste
- Usa `tenant_id="dono_test_123"` e `actor_id="user_test_*"`
- Limpa Firestore após execução
- Seguro para rodar em produção (não afeta dados reais)

---

**Status:** 🟢 Pronto para execução. Resultado determinará o patch necessário.
