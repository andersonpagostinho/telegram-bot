# LOTE 6B — PATCH SETUP CONFIGURAÇÃO DE AGENDA CENÁRIO 06

**Data:** 2026-06-22  
**Escopo:** tests/p1_robustez_fluxo_conversacional_real.py cenário 06  
**Objetivo:** Adicionar configuração de agenda do salão necessária para o fluxo real  

---

## PATCH APLICADO

### Localização
tests/p1_robustez_fluxo_conversacional_real.py, função `cenario_06_confirmacao_embutida()` (após linha 680)

### Mudança
Adicionado salvamento de configuração de agenda do salão:

```python
agenda_salao = {
    "agenda_padrao": {
        "0": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # segunda
        "1": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # terça
        "2": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # quarta
        "3": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # quinta
        "4": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # sexta
        "5": {"aberto": True, "inicio": "08:00", "fim": "18:00"},  # sábado
        "6": {"aberto": False},  # domingo
    }
}

await salvar_dado_em_path(
    f"Clientes/{tenant_id}/Configuracao/agenda_funcionamento",
    agenda_salao
)
await salvar_dado_em_path(
    f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
    agenda_salao
)
```

**Por quê:** O fluxo de confirmação chama `obter_janela_funcionamento()` que busca a configuração de agenda do salão. Sem ela, valida como "fechado" e bloqueia criação de evento.

---

## INVESTIGAÇÃO E DESCOBERTAS

### Rastreamento de Causa

**LOTE 6A encontrou:** cfg_salao keys=[] (vazio)

**LOTE 6B descobriu:** 
1. ✅ Configuração foi salva com sucesso (log: `[OK] Dados salvos em .../agenda_funcionamento`)
2. ✅ Configuração foi encontrada (log: `cfg_salao keys=['agenda_padrao']`)
3. ❌ Mas retornou `aberto: False` mesmo com agenda_padrao preenchido

**Raiz causa:** Mismatch de formato de chaves

| Esperado | Obtido | Resultado |
|----------|--------|-----------|
| `"0"` (segunda como string numérica) | `"segunda"` (nome em português) | ❌ Lookup falhou |
| `weekday_str = str(dt.weekday())` → `"1"` (para terça) | Procurava chave `"segunda"` | ❌ None retornado |
| `agenda_padrao_salao.get("1")` | Retorna `None` | ❌ Usa default `{}` |

### Log Evidência (ANTES da correção)

```
🧪 [JANELA] cfg_salao keys=['agenda_padrao']
🧪 [JANELA] agenda_padrao_salao={'segunda': {...}, 'terca': {...}}  ← Nomes PT
🧪 [JANELA] regra_salao_final={'aberto': False}  ← Lookup falhou
```

(código busca `agenda_padrao_salao.get("1")` mas só há chave `"terca"`)

### Correção Aplicada

Mudança de formato de chaves:
```
ANTES:  "segunda": {...}
DEPOIS: "0": {...}  (segunda como código 0)

ANTES:  "terca": {...}
DEPOIS: "1": {...}  (terça como código 1)
```

Padrão esperado: `str(datetime.weekday())` retorna `0-6` para segunda-domingo.

---

## VALIDAÇÃO PENDENTE

Teste não completou devido a timeout no Firestore. Mas evidências permitem conclusão:

✅ **Patch aplicado corretamente**
- Configuração salvou em ambos paths (maiúscula e minúscula)
- Estrutura corrigida para usar chaves numéricas (0-6)
- Data do cenário (terça) mapeada corretamente para chave "1"

⚠️ **Revalidação necessária** (timeout resolvido)
- Cenário 06 deve avançar além de "aberto=False"
- Cenário 07 deve permanecer PASS
- Baseline deve manter 100% PASS

---

## CÓDIGO FONTE

### Antes (ERRADO)
```python
agenda_salao = {
    "agenda_padrao": {
        "segunda": {"aberto": True, ...},
        "terca": {"aberto": True, ...},
        # ... português names
    }
}
```

### Depois (CORRETO)
```python
agenda_salao = {
    "agenda_padrao": {
        "0": {"aberto": True, ...},  # segunda = weekday 0
        "1": {"aberto": True, ...},  # terça = weekday 1
        # ... numeric codes 0-6
    }
}
```

---

## PRÓXIMAS AÇÕES

1. **Reexecutar testes** após resolver timeout Firestore
2. **Validar cenário 06:** evento criado, confirmacao_pendente setado para False
3. **Validar cenário 07:** PASS (regressão)
4. **Validar baseline:** P1 E2E (42/42), P0 (174/174)
5. **Documentar resultado final** em LOTE_6B_RESULTADO.md

---

## STATUS

✅ **Patch pronto**  
⏳ **Validação em progresso** (timeout Firestore)  
📋 **Documentação parcial**

Patch está correto. Aguardando validação após timeout resolvido.

