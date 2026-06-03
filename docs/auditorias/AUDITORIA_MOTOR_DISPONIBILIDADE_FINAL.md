# 🔍 AUDITORIA FINAL: Como Usar Motor Determinístico SEM Inventar Horários

**Objetivo:** Verificar como gerar sugestões de horários sem hardcodificar

**Data:** 2026-06-02

---

## 1. ASSINATURA EXATA DA FUNÇÃO

**Arquivo:** services/profissional_service.py, linhas 41-105

```python
async def buscar_profissionais_disponiveis_no_horario(
    user_id: str,                      # obrigatório
    data: datetime.date,                # obrigatório  
    hora: str,                          # obrigatório, formato "HH:MM"
    duracao: int = 60                   # OPCIONAL (padrão 60 min)
) -> dict:
    """Retorna dict com profissionais disponíveis naquele horário."""
```

**Entrada esperada:**
- `user_id="usuario123"`
- `data=datetime.date(2026, 6, 3)`
- `hora="09:00"` (STRING)
- `duracao=30` ou `duracao=60`

**Saída:**
```python
{
    "Bruna": {"nome": "Bruna", "servicos": ["corte", ...]},
    "Gloria": {...},
    "Joana": {...}
}
```

**Se ninguém disponível:**
```python
{}  # dict vazio
```

---

## 2. O PROBLEMA: NÃO EXISTE FUNÇÃO PARA GERAR HORÁRIOS

**Procurado:**
- `gerar_horarios_dia()` → **NÃO EXISTE**
- `listar_horarios_periodo()` → **NÃO EXISTE**  
- `obter_proximos_horarios()` → **NÃO EXISTE**
- `horarios_de_trabalho()` → **NÃO EXISTE**

**O que existe:**
- `buscar_profissionais_disponiveis_no_horario()` → recebe hora, verifica conflito
- `periodo_compativel_com_hora()` → valida se hora está no período

**Conclusão:** Motor espera que **a lógica de iteração de horários** seja implementada por quem chama.

---

## 3. PADRÃO CORRETO: LOOP COM PERÍODO

**Em vez de:**
```python
horarios = ["09:00", "10:00", "11:00"]  # ❌ HARDCODED
```

**Usar:**
```python
# 1. Determinar intervalo do período
if "manha" in mensagem_normalizada:
    hora_inicio = 9    # 9h
    hora_fim = 12      # até 11:59 (última hora possível)
elif "tarde" in mensagem_normalizada:
    hora_inicio = 14
    hora_fim = 18
elif "noite" in mensagem_normalizada:
    hora_inicio = 18
    hora_fim = 20
else:
    hora_inicio = 8
    hora_fim = 20      # dia inteiro

# 2. Iterar e verificar disponibilidade
horarios_disponiveis = {}
for hora in range(hora_inicio, hora_fim + 1):  # ← INTERVALO, não lista fixa
    hora_str = f"{hora:02d}:00"  # "09:00", "10:00", etc
    
    disponiveis = await buscar_profissionais_disponiveis_no_horario(
        user_id=user_id,
        data=data_obj,
        hora=hora_str,
        duracao=duracao_estimada  # ← RETIRAR DO SERVIÇO, não hardcode
    )
    
    if disponiveis:
        horarios_disponiveis[hora_str] = disponiveis

# 3. Retornar horários encontrados
```

---

## 4. DURAÇÃO: DE ONDE VEM?

**PROBLEMA ENCONTRADO:** Não existe função que retorna duração padrão de um serviço.

**O que existe:**
- `obter_precos_servico()` → retorna preço, não duração
- `listar_servicos_cadastrados()` → retorna nomes, não duração
- `encontrar_servico_mais_proximo()` → identifica, não retorna duração

**Opções:**

### A) Usar duração fixa (mais simples)
```python
duracao = 60  # 1 hora padrão
```

### B) Buscar duração do profissional
```python
# Procurar se profissional tem campo "duracao_servico"
profissionais = await buscar_profissionais_por_servico([servico], user_id)
for prof_nome, prof_dados in profissionais.items():
    duracao = prof_dados.get("duracao_padrao", 60)  # default 60
    break  # usar primeira
```

### C) Usar informação do contexto
```python
# Se usuário anteriormente agendou, usar mesma duração
contexto = await carregar_contexto_temporario(user_id)
duracao = contexto.get("ultima_duracao", 60)
```

**Recomendação:** Opção A (simples) + Opção B (se disponível).

```python
duracao = 60  # default
if profissionais:  # se encontrou
    primeira_prof = next(iter(profissionais.values()))
    duracao = primeira_prof.get("duracao_padrao", 60)
```

---

## 5. FLUXO CORRETO (MÍNIMO, SEM INVENTAR)

```python
# 📅 Quem tem disponível em data/período
if any(p in mensagem_normalizada for p in [
    "quem tem disponivel", "quem voce tem disponivel",
    "tem disponivel", "quem esta disponivel"
]):
    
    # Extrair serviço
    servico = await encontrar_servico_mais_proximo(mensagem, user_id)
    if not servico:
        return "❌ Qual serviço?"
    
    # Extrair data
    dt = interpretar_data_e_hora(mensagem)
    if not dt:
        return "❌ Qual dia?"
    
    # Extrair período → intervalo de horas (NÃO lista fixa)
    if "manha" in mensagem_normalizada:
        hora_inicio, hora_fim = 9, 12
    elif "tarde" in mensagem_normalizada:
        hora_inicio, hora_fim = 14, 18
    elif "noite" in mensagem_normalizada:
        hora_inicio, hora_fim = 18, 21
    else:
        hora_inicio, hora_fim = 8, 20
    
    # Buscar profissionais que fazem o serviço
    profs_servico = await buscar_profissionais_por_servico([servico], user_id)
    if not profs_servico:
        return f"❌ Nenhum profissional para {servico}."
    
    # Determinar duração
    duracao = 60
    primeira_prof = next(iter(profs_servico.values()), None)
    if primeira_prof:
        duracao = primeira_prof.get("duracao_padrao", 60)
    
    # Iterar sobre período, verificar disponibilidade
    data_obj = dt.date()
    horarios_disponiveis = {}
    
    for hora_num in range(hora_inicio, hora_fim + 1):  # ← INTERVALO
        hora_str = f"{hora_num:02d}:00"
        
        disponiveis = await buscar_profissionais_disponiveis_no_horario(
            user_id=user_id,
            data=data_obj,
            hora=hora_str,
            duracao=duracao
        )
        
        # Filtrar apenas quem faz o serviço
        disponiveis_servico = {
            nome: info for nome, info in disponiveis.items()
            if nome in profs_servico
        }
        
        if disponiveis_servico:
            horarios_disponiveis[hora_str] = disponiveis_servico
    
    # Formatar resposta
    if horarios_disponiveis:
        periodo_str = {
            (9, 12): "de manhã",
            (14, 18): "à tarde",
            (18, 21): "à noite"
        }.get((hora_inicio, hora_fim), "")
        
        linhas = []
        for hora, profs in horarios_disponiveis.items():
            nomes = ", ".join(profs.keys())
            linhas.append(f"• {hora} — {nomes}")
        
        data_str = data_obj.strftime("%d/%m")
        return f"✅ Para *{servico}* em *{data_str}* {periodo_str}:\n\n" + "\n".join(linhas)
    else:
        return f"😕 Desculpe, nenhum disponível para {servico} {periodo_str}."
```

---

## 6. CHECKLIST: O QUE NÃO FAZER

❌ **Hardcodificar lista de horários:**
```python
horarios = ["09:00", "10:00", "11:00"]  # PROIBIDO
```

❌ **Inventar duração:**
```python
duracao = 30  # Sem saber o serviço? PROIBIDO
```

❌ **Não usar período:**
```python
# Iterar o dia inteiro mesmo quando usuário disse "manhã"
for hora in range(8, 21):  # ERRADO, ignora período
```

❌ **Não chamar o motor:**
```python
# Supor que está disponível sem verificar conflito
"Bruna está livre às 10h"  # ERRADO, não verificou
```

---

## 7. CHECKLIST: O QUE FAZER

✅ **Converter período em INTERVALO:**
```python
if "manha" in msg:
    hora_inicio, hora_fim = 9, 12  # Intervalo, não lista
```

✅ **Iterar sobre INTERVALO:**
```python
for hora_num in range(hora_inicio, hora_fim + 1):
    hora_str = f"{hora_num:02d}:00"
    # Verificar essa hora
```

✅ **Chamar o MOTOR para cada hora:**
```python
await buscar_profissionais_disponiveis_no_horario(
    user_id, data, hora_str, duracao
)
```

✅ **Filtrar por SERVIÇO:**
```python
disponiveis_servico = {
    nome: info for nome, info in disponiveis.items()
    if nome in profs_servico
}
```

✅ **Coletar RESULTADOS:**
```python
if disponiveis_servico:
    horarios_disponiveis[hora_str] = disponiveis_servico
```

---

## 8. IMPACTO NO CÓDIGO

**Adições necessárias ao imports (línea 1-10 de informacao_service.py):**

```python
from datetime import datetime, date, timedelta
from utils.interpretador_datas import interpretar_data_e_hora
from services.profissional_service import (
    buscar_profissionais_por_servico,
    buscar_profissionais_disponiveis_no_horario,
    encontrar_servico_mais_proximo
)
```

**Novo bloco em responder_consulta_informativa() (antes de linha 106 - antes do `return None`):**

~40-50 linhas (não 60).

---

## 9. RESUMO: Fluxo Seguro

```
"quem tem disponível amanhã de manhã para corte?"
    ↓
1. Extrair serviço: "corte" ✓
2. Extrair data: 2026-06-03 ✓
3. Extrair período: "manhã" → intervalo (9-12) ✓
4. Buscar profs do serviço: [Bruna, Gloria, Joana] ✓
5. Para cada HORA no intervalo (9, 10, 11):
   └─ Chamar motor: disponiveis = await buscar_...(hora) ✓
   └─ Filtrar por serviço ✓
   └─ Se houver, adicionar ao resultado ✓
6. Formatar resposta:
   "Para corte amanhã de manhã:
    • 09:00 — Bruna, Gloria
    • 10:00 — Joana
    • 11:00 — Bruna"
```

**Motor reutilizado completamente. Sem invenção de horários.**

---

**Status:** ✅ Auditoria completa. Pronto para implementar o patch.

Patch será ~45-50 linhas (elif novo em responder_consulta_informativa).

Sem duplicação. Sem hardcode. Usando motor existente corretamente.
