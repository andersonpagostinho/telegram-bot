# 🔍 AUDITORIA: Fluxo Determinístico para Consultas de Disponibilidade

**Entrada:** "quem você tem disponível amanhã no período da manhã para corte de cabelo"

**Fluxo Esperado:** Determinístico (sem GPT)

**Fluxo Atual:** Via GPT com contexto vazio

---

## 1. FUNÇÕES EXISTENTES PARA DISPONIBILIDADE

### ✅ Função 1: `buscar_profissionais_por_servico()`

**Arquivo:** services/profissional_service.py, linhas 11-38

```python
async def buscar_profissionais_por_servico(servicos: list[str], user_id: str) -> dict:
    """
    Retorna um dicionário com os profissionais que oferecem TODOS os serviços listados.
    Resolve o dono primeiro, para suportar clientes falando com o bot.
    """
    dono_id = await obter_id_dono(user_id)
    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
```

**Entrada:** `servicos=["corte"]`, `user_id=usuario`  
**Saída:** Dicionário com Bruna, Gloria, Joana (os que fazem corte)  
**Status:** ✅ Implementado e funcional

---

### ✅ Função 2: `buscar_profissionais_disponiveis_no_horario()`

**Arquivo:** services/profissional_service.py, linhas 41-105

```python
async def buscar_profissionais_disponiveis_no_horario(
    user_id: str,
    data: datetime.date,
    hora: str,
    duracao: int = 60
) -> dict:
    """
    Retorna os profissionais que estão disponíveis no horário e duração informados.
    Resolve o dono primeiro.
    """
    dono_id = await obter_id_dono(user_id)
    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos") or {}
    
    # Verifica conflitos com eventos existentes
    profissionais_ocupados = set()
    for evento_id, evento in eventos.items():
        if conflito:
            profissionais_ocupados.add(prof_evento)
    
    disponiveis = {
        nome: dados for nome, dados in profissionais.items()
        if nome.lower() not in profissionais_ocupados
    }
    
    return disponiveis
```

**Entrada:** `user_id=usuario`, `data=2026-06-03`, `hora=09:00`, `duracao=30`  
**Saída:** Profissionais sem conflitos naquele horário  
**Status:** ✅ Implementado e funcional

---

### ✅ Função 3: `gerar_mensagem_profissionais_disponiveis()`

**Arquivo:** services/profissional_service.py, linhas 130-152

```python
def gerar_mensagem_profissionais_disponiveis(
    servico: str,
    data: datetime.date,
    hora: str,
    disponiveis: dict,
    todos: dict
) -> str:
    """Gera mensagem formatada com profissionais disponíveis."""
    if disponiveis:
        lista = "\n".join([f"- {nome}: ..." for nome, info in disponiveis.items()])
        return f"✅ Segue a lista de profissionais disponíveis para *{servico}* no dia *{data_str}* às *{hora}*:\n{lista}"
    else:
        if todos:
            return f"😕 No momento, ninguém está com horário disponível... Mas estas profissionais realizam esse serviço..."
        else:
            return "❌ Nenhum profissional cadastrado até o momento."
```

**Entrada:** Resultados das funções anteriores  
**Saída:** Mensagem formatada pronta para usuário  
**Status:** ✅ Implementado e funcional

---

### ✅ Função 4: `periodo_compativel_com_hora()`

**Arquivo:** router/principal_router.py, linhas 253-268

```python
def periodo_compativel_com_hora(periodo: str, hora_str: str) -> bool:
    try:
        hora = int(str(hora_str).split(":")[0])
        
        periodo = normalizar(periodo or "")
        
        if periodo in ["manha", "manhã", "cedo"]:
            return hora <= 11
        
        if periodo in ["tarde", "fim_tarde"]:
            return 12 <= hora <= 17
        
        if periodo == "noite":
            return hora >= 18
        
        return True
```

**Entrada:** `periodo="manhã"`, `hora_str="09:00"`  
**Saída:** `True` (compatível)  
**Status:** ✅ Implementado e funcional

---

## 2. FUNÇÕES PARA DETECÇÃO DE CONSULTAS

### ✅ Função: `responder_consulta_informativa()`

**Arquivo:** services/informacao_service.py, linhas 7-100

**Trata:**
- ✅ "quem faz corte?" → Lista profissionais que fazem corte
- ✅ "quanto custa?" → Lista preços
- ✅ "quais serviços?" → Lista serviços disponíveis

**NÃO trata:**
- ❌ "quem tem disponível amanhã?" → **FALTA**
- ❌ "quem está livre no período da manhã?" → **FALTA**
- ❌ Combinação de: profissional + data + período → **FALTA**

**Verificação:** Nenhuma linha busca por palavras como "amanhã", "disponível" + "período", "manhã" + "hora".

---

### ✅ Função: `eh_consulta()`

**Arquivo:** router/principal_router.py, linhas 445-540

**Detecta como "consulta":**
- ✅ Linha 503: "disponivel", "disponível"
- ✅ Linha 500: "tem horario", "tem vaga"
- ✅ Linha 505: "quem faz", "quem atende"

**MAS:**
- ❌ Não combina: "quem" + "disponível" + "período"
- ❌ Não verifica se tem data/período junto

**Evidência:** Linhas 451-479 detectam presença de "disponível" como consulta, mas `responder_consulta_informativa()` não sabe processar esse tipo de consulta.

---

## 3. PONTO DE INTERCEPTAÇÃO ANTES DO GPT

### Encontrado em: router/principal_router.py

**Linhas 3204-3207** (e repetidas em outros pontos):
```python
from services.informacao_service import responder_consulta_informativa
resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
if resposta_informativa:
    return resposta_informativa  # Retorna sem chamar GPT ✅
```

**Linhas 4886-4891:**
```python
if eh_consulta(texto_usuario):
    from services.informacao_service import responder_consulta_informativa
    resposta_info = await responder_consulta_informativa(mensagem, user_id)
    if resposta_info:
        return resposta_info
```

**Linhas 6224-6228:**
```python
if eh_consulta(texto_lower) and estado_fluxo == "idle":
    ...responder_consulta_informativa...
    if resposta_info:
        return resposta_info
```

---

## 4. POR QUE NÃO FOI INTERCEPTADO

**Fluxo atual:**

```
"quem você tem disponível amanhã no período da manhã para corte"
    ↓
eh_consulta(texto) = ???
    ↓
Procura por "disponivel" → ENCONTRA (linha 503)
    ↓
Marca como consulta = True
    ↓
responder_consulta_informativa(mensagem, user_id)
    ↓
Procura por "quem faz" → NÃO ENCONTRA
Procura por "quanto custa" → NÃO ENCONTRA
Procura por "qual serviço" → NÃO ENCONTRA
    ↓
Retorna None (não tratou)
    ↓
Cai para GPT ❌
```

**Por quê?**

1. ✅ `eh_consulta()` detecta "disponível" como consulta
2. ❌ MAS `responder_consulta_informativa()` não sabe processar "quem tem disponível AMANHÃ NO PERÍODO"

Falta um bloco em `responder_consulta_informativa()` que:
- Detecte "quem" + "disponível" + (data OU período)
- Extraia: serviço, data, período
- Chame `buscar_profissionais_por_servico()`
- Converta período para janela de horários
- Chame `buscar_profissionais_disponiveis_no_horario()` para cada hora da janela
- Agregue resultados e retorne mensagem

---

## 5. PATCH MÍNIMO NECESSÁRIO

### Local: `services/informacao_service.py`

**Adicionar ANTES da linha 7:**

```python
from datetime import datetime, date, timedelta
from utils.interpretador_datas import interpretar_data_e_hora
from services.profissional_service import (
    gerar_mensagem_profissionais_disponiveis
)
```

**Adicionar ANTES do fim da função `responder_consulta_informativa()` (após linha 100, antes do return final):**

```python
# 📅 Quem tem disponível em data específica/período
palavras_chave_disponibilidade = [
    "quem tem disponivel", "quem tem disponível",
    "quem voce tem disponivel", "quem você tem disponível",
    "tem disponivel", "tem disponível",
    "quem esta disponivel", "quem está disponível"
]

if any(p in mensagem_normalizada for p in palavras_chave_disponibilidade):
    
    # Extrair serviço
    from services.normalizacao_service import encontrar_servico_mais_proximo
    servico_detectado = await encontrar_servico_mais_proximo(mensagem, user_id)
    
    if not servico_detectado:
        return "❌ Qual serviço você quer? Mencionou corte, escova, manicure...?"
    
    # Extrair data e período
    dt = interpretar_data_e_hora(mensagem)
    if not dt:
        return f"❌ Qual dia você quer? (hoje, amanhã, segunda-feira...?)"
    
    # Extrair período (manhã/tarde/noite) ou usar horários padrão
    periodo = None
    if "manha" in mensagem_normalizada or "cedo" in mensagem_normalizada:
        periodo = "manhã"
        horarios = ["09:00", "10:00", "11:00"]
    elif "tarde" in mensagem_normalizada or "fim_tarde" in mensagem_normalizada:
        periodo = "tarde"
        horarios = ["14:00", "15:00", "16:00", "17:00"]
    elif "noite" in mensagem_normalizada:
        periodo = "noite"
        horarios = ["18:00", "19:00", "20:00"]
    else:
        # Se não especificou período, procurar próximos 3 horários do dia
        horarios = ["10:00", "14:00", "18:00"]
    
    # Buscar profissionais que fazem o serviço
    profs_servico = await buscar_profissionais_por_servico([servico_detectado], user_id)
    if not profs_servico:
        return f"❌ Nenhum profissional encontrado para {servico_detectado}."
    
    # Verificar disponibilidade para cada horário
    data_obj = dt.date()
    resultados_disponiveis = {}
    
    for hora in horarios:
        disponiveis = await buscar_profissionais_disponiveis_no_horario(
            user_id=user_id,
            data=data_obj,
            hora=hora,
            duracao=30  # duração estimada do serviço
        )
        
        # Filtrar apenas profissionais que fazem o serviço
        disponiveis_servico = {
            nome: info for nome, info in disponiveis.items()
            if nome in profs_servico
        }
        
        if disponiveis_servico:
            resultados_disponiveis[hora] = disponiveis_servico
    
    # Montar mensagem final
    if resultados_disponiveis:
        mensagem_resposta = f"✅ Para *{servico_detectado}* no dia *{data_obj.strftime('%d/%m')}*"
        if periodo:
            mensagem_resposta += f" ({periodo})"
        mensagem_resposta += ", tenho disponíveis:\n\n"
        
        for hora, profs in resultados_disponiveis.items():
            nomes = ", ".join(profs.keys())
            mensagem_resposta += f"• {hora} — {nomes}\n"
        
        return mensagem_resposta
    else:
        return f"😕 Desculpe, nenhum profissional de {servico_detectado} está disponível {periodo or 'naquele horário'}. Posso sugerir outro horário?"
```

---

## RESUMO TÉCNICO

| # | Item | Status | Localização |
|----|------|--------|-------------|
| 1 | Função buscar profissionais por serviço | ✅ Existe | profissional_service.py:11 |
| 2 | Função buscar disponibilidade por hora | ✅ Existe | profissional_service.py:41 |
| 3 | Função gerar mensagem formatada | ✅ Existe | profissional_service.py:130 |
| 4 | Função validar período vs hora | ✅ Existe | principal_router.py:253 |
| 5 | Detecção de "disponível" como consulta | ✅ Existe | principal_router.py:445 |
| 6 | **Processamento de "quem tem disponível AMANHÃ PERÍODO"** | ❌ **FALTA** | informacao_service.py |
| 7 | Ponto de interceptação ANTES do GPT | ✅ Existe | principal_router.py:3204 |

---

## CONCLUSÃO

**Todas as funções determinísticas EXISTEM.** 

O problema é que `responder_consulta_informativa()` não combina elas para processar a entrada "quem tem disponível amanhã de manhã para corte".

**Patch necessário:** Adicionar 1 bloco (~50 linhas) em `informacao_service.py` que:
- Detecte "quem" + "disponível" + data/período
- Extraia serviço, data, período
- Chame as funções existentes em sequência
- Retorne mensagem pronta (sem GPT)

**Tenant:** Usa `await obter_id_dono(user_id)` corretamente (linha 12) = não mistura tenants ✅

---

**Status da Auditoria:** ✅ Completo. Nenhuma mudança de código.

