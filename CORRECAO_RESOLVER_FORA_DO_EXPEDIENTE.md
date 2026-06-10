# Correcao: resolver_fora_do_expediente()

**Data:** 2026-06-09  
**Status:** ✅ IMPLEMENTADO E VALIDADO  
**Arquivo:** services/agenda_service.py (Linhas 717-830)

---

## Problemas Corrigidos

### P0 #1: profissional=None sem validacao de conflito geral
**Antes:** Se profissional era None, funcao retornava horario direto sem verificar conflitos
**Depois:** Verifica conflito geral contra TODOS eventos do dia

**Implementacao (Linhas 724-773):**
```python
if not (profissional or "").strip():
    try:
        eventos_dia = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
        ocupados_geral = []

        candidato_dt = datetime.fromisoformat(f"{data_iso}T{hora_candidata}")
        candidato_fim = candidato_dt + timedelta(minutes=duracao_min)

        for eid, ev in eventos_dia.items():
            # ... validacoes de data, horario ...
            ocupados_geral.append((ev_ini, ev_fim))

        tem_conflito = any(
            not (candidato_fim <= oi or candidato_dt >= of)
            for oi, of in ocupados_geral
        )

        if tem_conflito:
            print(f"... candidato {hora_candidata} tem conflito geral, pulando")
            continue

    except Exception as e:
        print(f"... erro ao verificar conflito geral: {e}")
        continue

    # Revalidar antes de retornar
    revalidacao = await validar_horario_funcionamento(...)
    if not revalidacao.get("permitido"):
        continue

    return { "ok": True, ... }
```

---

### P0 #2: verificar_conflito retorna None ou {} tratado como "livre"
**Antes:** `if not resultado.get("conflito"):` retornava True quando None ou {}
**Depois:** `if resultado.get("conflito", True) is not False:` assume conflito se invalido

**Implementacao (Linhas 793-811):**
```python
try:
    resultado = await verificar_conflito_e_sugestoes_profissional(...)
except Exception as e:
    print(f"... erro ao verificar conflito: {e}")
    continue

if resultado is None or not isinstance(resultado, dict):
    print(f"... resultado invalido, pulando {hora_candidata}")
    continue

if resultado.get("conflito", True) is not False:
    print(f"... candidato {hora_candidata} tem conflito, pulando")
    continue
```

**Garantias:**
- `None` → continua para proximo candidato
- `{}` (dict vazio) → `.get("conflito", True)` retorna `True` → `is not False` = `True` → continua
- `{"conflito": False}` → apenas passa
- `{"conflito": True}` → continua
- Exception → loggado e continua

---

### P0 #3: Sugestao final nao era revalidada
**Antes:** Retornava horario direto apos validacoes iniciais
**Depois:** Chama `validar_horario_funcionamento()` antes de retornar

**Implementacao (Linhas 812-819):**
```python
revalidacao = await validar_horario_funcionamento(
    user_id=user_id,
    data_iso=data_iso,
    hora_inicio=hora_candidata,
    duracao_min=duracao_min,
    profissional=profissional,
)

if not revalidacao.get("permitido"):
    print(f"... candidato {hora_candidata} falhou revalidacao, pulando")
    continue
```

**Colocado em 2 lugares:**
- Linha 765 (caso profissional=None)
- Linha 813 (caso profissional definido)

---

## Imports Adicionados

**Linhas 5-9:**
```python
from services.event_service_async import verificar_conflito_e_sugestoes_profissional, _parse_event_interval
from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path, salvar_dado_em_path, buscar_subcolecao
```

---

## Testes Criados

### test_resolver_fora_do_expediente.py (6 testes, 6/6 PASS)

1. **[PASS] profissional=None + conflito**
   - Evento 14:00-15:00 existente
   - Sugestao pulou 14:00 (tinha conflito)
   - Retornou 15:00 (proximo livre)

2. **[PASS] profissional=None + proximo livre**
   - Validou que 14:00, 14:20, 14:40 foram pulados
   - 15:00 foi retornado (primeiro sem conflito)

3. **[PASS] verificar_conflito retorna None**
   - Exception ou timeout em verificar_conflito
   - Continua para proximo candidato
   - Nao retorna como livre

4. **[PASS] verificar_conflito retorna {} (dict vazio)**
   - Dict vazio nao interpreta como conflito=False
   - Continua para proximo candidato
   - Logica: `.get("conflito", True) is not False` → continua

5. **[PASS] sugestao falha revalidacao**
   - validar_horario_funcionamento() retorna permitido=False
   - Continua para proximo candidato
   - Não retorna horario que falhou

6. **[PASS] 17:40 + 30min em janela ate 18:00 bloqueada**
   - Validacao de linha 687 continua protegendo
   - 17:40 nunca entra na lista de candidatos
   - Nenhuma regressao

---

## Validacoes Executadas

### Sintaxe
```bash
python -m py_compile services/agenda_service.py
[OK] Sintaxe validada
```

### Testes Novos
```bash
python test_resolver_fora_do_expediente.py
TOTAL: 6/6 testes passaram
```

### Regressao (Testes Anteriores)
```bash
python test_agenda_service_p0.py
TOTAL: 18/18 testes passaram
```

---

## Garantias de Seguranca

✅ **Toda sugestao retornada passa por:**
1. Validacao de janela de funcionamento (linha 640-644)
2. Geracao segura de candidatos com duracao (linha 687)
3. Validacao de conflito geral (profissional=None) OU profissional específico (profissional definido)
4. Validacao final por `validar_horario_funcionamento()` (linha 765 ou 813)

✅ **Profissional=None:**
- Verifica conflito contra TODOS eventos do dia
- Falha fechada (assume conflito se erro)
- Nao retorna horario ocupado

✅ **Profissional definido:**
- Trata None, {}, Exception seguramente
- Revalidacao final obrigatoria
- Falha fechada (assume conflito se resultado invalido)

✅ **Sem regressao:**
- 17:40 + 30min continua bloqueado (linha 687)
- Todos casos anteriores continuam passando

---

## Risco Residual

**NENHUM risco critico identificado.**

Funcao agora eh defensiva em 3 niveis:
1. Geracao de candidatos (linha 687)
2. Validacao de conflito geral (profissional=None) ou verificacao profissional
3. Revalidacao final (validar_horario_funcionamento)

---

## Status Final

✅ **IMPLEMENTADO E VALIDADO**

- Correcoes implementadas: 3/3
- Testes novos: 6/6 PASS
- Regressoes: 0
- Sintaxe: OK
- Bloqueadores: NENHUM

**Pronto para producao.**
