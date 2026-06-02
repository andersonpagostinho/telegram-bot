# 🔴 AUDITORIA: Bug Real no Merge de Data/Hora

**Status:** BUG CONFIRMADO NO FLUXO REAL  
**Severidade:** P0 — Hora é sobrescrita, agendamentos com horário errado  
**Rastreamento:** Linha exata localizada com evidência

---

## FLUXO REAL RASTREADO

```
[ENTRADA DO USUÁRIO]
"corte cabelo da Suri às 16 horas amanhã"
        ↓
[PARSER]
utils/interpretador_datas.py::interpretar_data_e_hora()
resultado = 2026-06-03 16:00:00  ✅ CORRETO
        ↓
[GPT_SERVICE - PRÉ-PROCESSAMENTO]
services/gpt_service.py::processar_com_gpt_com_acao()
        ↓
[LINHA 453-461: BUG ACONTECE AQUI]
Contexto anterior tem: 2026-06-03T09:00:00
Lógica: "Se há contexto antigo E há hora explícita, manter contexto antigo"
resultado = 2026-06-03T09:00:00  ❌ ERRADO!
        ↓
[PRE-SAVE dados_update]
data_hora = 2026-06-03T09:00:00  ❌ Hora perdida
        ↓
[CONTEXTO_BASE ATUALIZADO]
contexto_base.update(dados_update)
data_hora = 2026-06-03T09:00:00  ❌ Propagado
        ↓
[CTX->GPT]
data_hora = 2026-06-03T09:00:00  ❌ GPT recebe hora errada
        ↓
[RESULTADO FINAL]
Evento criado com 09:00 (deveria ser 16:00)
```

---

## LOCALIZAÇÃO EXATA DO BUG

### Arquivo
```
services/gpt_service.py
```

### Função
```python
async def processar_com_gpt_com_acao(
    texto_usuario: str,
    contexto: dict,
    instrucao: str,
    user_id: str | None = None,
)
```
**Função começa linha:** 111  
**Bug acontece linhas:** 449-470

---

## CÓDIGO DO BUG

### Linha 453: Parser retorna valor correto
```python
dt = interpretar_data_e_hora(texto_usuario)
# dt = datetime(2026, 6, 3, 16, 0, 0)  ✅ CORRETO
```

### Linhas 456-461: BUG — Sobrescrita indevida
```python
if dt:
    # 🔥 NÃO sobrescrever se já existe data_hora válida no contexto
    data_hora_existente = (contexto_salvo or {}).get("data_hora")
    # data_hora_existente = "2026-06-03T09:00:00"  ← DO CONTEXTO ANTERIOR

    if data_hora_existente and tem_hora_explicita:
        # ❌ BUG: MANTÉM HORA ANTIGA EM VEZ DE USAR RESULTADO DO PARSER
        # mantém o valor existente (mais confiável)
        dados_update["data_hora"] = data_hora_existente
        # dados_update["data_hora"] = "2026-06-03T09:00:00"  ❌ ERRADO!

    else:
        if tem_hora_explicita:
            dados_update["data_hora"] = dt.replace(  # ← Nunca executa quando tem data_hora_existente
                second=0,
                microsecond=0
            ).isoformat()
```

---

## RAIZ DO BUG

### Lógica Errada
```
SE (existe data_hora no contexto antigo) E (há hora explícita no texto novo):
    MANTER a hora antiga
SENÃO:
    USAR resultado do parser
```

### Por Que É Errado
```
Texto: "amanhã às 16"
Parser retorna: 2026-06-03 16:00:00 (NOVO, CORRETO)

Contexto tem: 2026-06-03T09:00:00 (ANTIGO, DESATUALIZADO)

Lógica diz: "contexto é mais confiável que parser"
Resultado: Usa 09:00 (ERRADO!)

Deveria ser: Parser sempre sobrescreve contexto quando nova data é explícita
```

---

## EVIDÊNCIA DO BUG

### Logs Capturados do Fluxo Real
```
[PARSER]
🧪 [PARSER] fonte_parse=manual_hoje_amanha | resultado=2026-06-03 16:00:00

[PRE-SAVE]
🧪 [PRE-SAVE dados_update] {'data_hora': '2026-06-03T09:00:00', ...}

[CTX->GPT]
Contexto enviado para GPT contém: data_hora=2026-06-03T09:00:00

Discrepância: 16:00 (parser) → 09:00 (dados_update)
Local: services/gpt_service.py linhas 456-461
```

---

## VARIÁVEIS RASTREADAS

### Antes do Bug (Linha 453)
```python
texto_usuario = "amanhã às 16"
dt = interpretar_data_e_hora(texto_usuario)
# dt = datetime.datetime(2026, 6, 3, 16, 0, 0)
# dt.isoformat() = "2026-06-03T16:00:00"
```

### Valor Intermediário (Linha 457)
```python
contexto_salvo = {
    "data_hora": "2026-06-03T09:00:00",  # ← ANTERIOR, DESATUALIZADO
    "usuario": {...},
    ...
}
data_hora_existente = contexto_salvo.get("data_hora")
# data_hora_existente = "2026-06-03T09:00:00"
```

### Detecção de Hora Explícita (Linhas 424-429)
```python
texto_hora_only = "amanhã às 16"
tem_hora_explicita = bool(
    re.search(r"\b(?:às|as)\s*\d{1,2}(?::\d{2})?\b", texto_hora_only)
    or ...
)
# tem_hora_explicita = True  ✅ Detectado corretamente
```

### Decisão Errada (Linhas 459-461)
```python
if data_hora_existente and tem_hora_explicita:
    # Condition: "2026-06-03T09:00:00" is not None/False/empty = True
    #            tem_hora_explicita = True
    # → ENTRA NO IF
    dados_update["data_hora"] = data_hora_existente
    # dados_update["data_hora"] = "2026-06-03T09:00:00"  ❌ DESCARTA resultado do parser!
```

### Saída (Linha 665 + 671)
```python
print("🧪 [PRE-SAVE dados_update] ", dados_update, flush=True)
# {'data_hora': '2026-06-03T09:00:00', ...}  ❌ HORA PERDIDA

contexto_base.update(dados_update)
# contexto_base["data_hora"] = "2026-06-03T09:00:00"

await salvar_contexto_temporario(uid, dados_update)
# Salva contexto com hora errada
```

---

## IMPACTO

### Usuários Afetados
```
Qualquer agendamento onde:
1. Existe contexto anterior com hora X
2. Usuário quer mudar para hora Y explicitamente
3. Resultado: hora Y é ignorada, mantém X
```

### Exemplos de Falha
```
❌ Caso 1:
   Contexto: 2026-06-03T09:00:00
   Usuário: "amanhã às 16"
   Resultado: 2026-06-03T09:00:00 (ERRADO - deveria ser 16:00)

❌ Caso 2:
   Contexto: 2026-06-02T14:00:00
   Usuário: "sexta às 10"
   Resultado: 2026-06-02T14:00:00 (ERRADO - deveria ser sexta às 10)

❌ Caso 3:
   Contexto: 2026-06-03T09:00:00
   Usuário: "às 16"
   Resultado: 2026-06-03T16:00:00 (CORRETO - porque interpreta hora)
```

---

## RAÇA RAIZ

### Problema Arquitetural
```
A lógica assume que "contexto antigo é mais confiável que interpretação nova"

Mas isso é FALSO quando:
- Usuário manda mensagem COM hora explícita
- Hora explícita deve SEMPRE sobrescrever contexto antigo

A regra deveria ser:
IF usuário disse hora explícita:
    USAR resultado do parser (sempre)
ELSE:
    Usar contexto antigo para data, sem hora (ou com hora antiga se necessário)
```

---

## CORREÇÃO NECESSÁRIA

### Lógica Corrigida
```python
# ANTES (errado):
if data_hora_existente and tem_hora_explicita:
    dados_update["data_hora"] = data_hora_existente  # ❌

# DEPOIS (correto):
if tem_hora_explicita:
    # Usuário foi explícito: usar resultado do parser SEMPRE
    dados_update["data_hora"] = dt.isoformat()  # ✅
elif data_hora_existente:
    # Sem hora explícita: usar contexto anterior
    dados_update["data_hora"] = data_hora_existente
else:
    # Sem contexto, sem hora: resultado do parser sem hora
    dados_update["data_hora"] = dt_sem_hora.isoformat()
```

---

## RESUMO

| Campo | Valor |
|-------|-------|
| **Arquivo** | services/gpt_service.py |
| **Função** | processar_com_gpt_com_acao() |
| **Linhas do Bug** | 456-461 |
| **Valor Antes** | 2026-06-03 16:00:00 (parser) |
| **Valor Depois** | 2026-06-03T09:00:00 (contexto antigo) |
| **Causa** | Lógica que prioriza contexto antigo sobre hora explícita |
| **Impacto** | Horas são sobrescritas, agendamentos com horário errado |
| **Severidade** | P0 |

**Bug confirmado. Pronto para correção.**

