# ESPECIFICAÇÃO — INTERPRETAÇÃO CONTEXTUAL COM FLUXO ATIVO

**Data:** 2026-06-28  
**Status:** ✅ ESPECIFICAÇÃO OFICIAL  
**Versão:** 1.0 — Congelada  

---

## PRINCÍPIO CENTRAL

```
Sem fluxo ativo:
    └─ mensagem pode ser neutra
    └─ GPT classifica intenção do usuário
    └─ motor roteador decide próximo passo

Com fluxo ativo:
    └─ mensagem é resposta ao fluxo até prova contrária
    └─ GPT interpreta linguagem DENTRO DO CONTEXTO do fluxo
    └─ motor determinístico executa lógica resolvida
```

**Regra:** Contexto muda tudo. Mensagem idêntica significa coisas diferentes conforme o fluxo.

---

## O QUE GPT FAZ

### ✅ GPT INTERPRETA LINGUAGEM

- Extrair intenção dentro do contexto
- Mapear linguagem humana para estrutura determinística
- Humanizar feedback
- Resolver ambiguidade semântica

### ❌ GPT NÃO FAZ LÓGICA DE NEGÓCIO

```
❌ Escolher profissional
   (Motor: busca disponibilidade, resolve)

❌ Calcular horário
   (Motor: valida conflito, sugere)

❌ Criar/alterar evento
   (Motor: persiste após validação)

❌ Verificar conflito
   (Motor: consulta Firestore, bloqueia)

❌ Decidir regra de negócio
   (Motor: aplica regra determinística)

❌ Retornar contexto_neutro com fluxo ativo
   (Proibido: fluxo merece resposta contextual)
```

---

## ESTADOS SUPORTADOS

### 1️⃣ AGUARDANDO_PROFISSIONAL

**Contexto:** Cliente agendou servico + data/hora, falta profissional.

**Input:**
```python
estado_fluxo = "aguardando_profissional"
draft_agendamento = {
    "servico": "corte",
    "data_hora": "2026-06-29T16:00:00"
}
mensagem = "Não tenho preferência"
```

**GPT Interpreta:**
- "Não tenho preferência" → profissional_indiferente=true
- "Com a Maria" → profissional_nome="Maria"
- "Qualquer um" → profissional_indiferente=true
- "A mesma de antes" → profissional_referencia=true

**GPT Retorna:**
```python
{
    "tipo_resposta": "preferencia_profissional",
    "profissional_indiferente": bool,
    "profissional_nome": str | None,
    "profissional_referencia": bool,
    "ambigua": bool,
    "confianca": float  # 0.0-1.0
}
```

**Motor Faz:**
1. Se `profissional_indiferente=true`:
   - Buscar profissional com menor carga (agenda_lock_service)
   - Validar disponibilidade
   - Retornar profissional + horário ao cliente
   
2. Se `profissional_nome`:
   - Validar nome existe
   - Validar disponibilidade nesse horário
   - Ou retornar: "profissional indisponível, alternativas?"
   
3. Se `profissional_referencia`:
   - Buscar último profissional em histórico
   - Validar disponibilidade
   - Ou retornar: "última profissional indisponível, alternativas?"

---

### 2️⃣ AGUARDANDO_DATA_HORA

**Contexto:** Cliente quer agendar, falta data/hora.

**Input:**
```python
estado_fluxo = "aguardando_data_hora"
draft_agendamento = {
    "servico": "escova"
}
mensagem = "Segunda-feira à tarde"
```

**GPT Interpreta:**
- "Segunda-feira à tarde" → data=(próxima segunda), hora=14:00 (aprox)
- "Amanhã cedo" → data=(amanhã), hora=08:00 (aprox)
- "Próxima semana" → ambigua=true, sugerir calendário
- "17:30" → hora=17:30

**GPT Retorna:**
```python
{
    "tipo_resposta": "data_hora",
    "data_extraida": str | None,  # YYYY-MM-DD
    "hora_extraida": str | None,  # HH:MM
    "intervalo_extraido": str | None,  # "manhã", "tarde", "noite"
    "ambigua": bool,
    "confianca": float
}
```

**Motor Faz:**
1. Validar data_extraida não está no passado
2. Validar hora está dentro do expediente
3. Buscar slots disponíveis
4. Se ambigua=true: apresentar calendário com 3-5 opções
5. Se horário indisponível: sugerir alternativas

---

### 3️⃣ AGUARDANDO_SERVICO

**Contexto:** Cliente quer agendar, falta serviço.

**Input:**
```python
estado_fluxo = "aguardando_servico"
mensagem = "Quero un corte com escova"
```

**GPT Interpreta:**
- "Corte com escova" → [servico_1="corte", servico_2="escova"]
- "Hidratação" → servico="hidratacao"
- "Um reparo no cabelo" → ambigua=true

**GPT Retorna:**
```python
{
    "tipo_resposta": "servico",
    "servicos_extraidos": [str],  # nomes encontrados
    "ambigua": bool,
    "confianca": float
}
```

**Motor Faz:**
1. Validar cada serviço existe no cadastro
2. Se ambigua=true: mostrar 3-5 serviços próximos
3. Calcular duração combinada
4. Validar disponibilidade para duração total

---

### 4️⃣ AGUARDANDO_CONFIRMACAO_AGENDAMENTO

**Contexto:** Agendamento pronto, aguardando confirmação.

**Input:**
```python
estado_fluxo = "aguardando_confirmacao_agendamento"
draft_agendamento = {
    "servico": "corte",
    "data_hora": "2026-06-29T16:00:00",
    "profissional": "Maria"
}
mensagem = "Tá certo"
```

**GPT Interpreta:**
- "Tá certo" → confirmacao=true
- "Sim" → confirmacao=true
- "Não, prefiro..." → confirmacao=false, motivo
- "Pode ser" → confirmacao=true
- "Espera aí" → ambigua=true

**GPT Retorna:**
```python
{
    "tipo_resposta": "confirmacao_agendamento",
    "confirmacao": bool,
    "motivo_negacao": str | None,
    "ambigua": bool,
    "confianca": float
}
```

**Motor Faz:**
1. Se confirmacao=true:
   - Criar evento em Firestore
   - Persistir agendamento
   - Enviar confirmação ao cliente
   - Notificar profissional
   - Limpar draft_agendamento
   
2. Se confirmacao=false:
   - Perguntar qual parte mudar
   - Retornar para fluxo apropriado
   - Preservar draft para alternações

---

### 5️⃣ AGUARDANDO_CLIENTE_NOME

**Contexto:** Novo cliente, falta nome.

**Input:**
```python
estado_fluxo = "aguardando_cliente_nome"
mensagem = "Sou a Ana"
```

**GPT Interpreta:**
- "Sou a Ana" → cliente_nome="Ana"
- "Meu nome é Maria dos Santos" → cliente_nome="Maria"
- "A filha da Carla" → cliente_nome="filha da Carla" (guardar relação)

**GPT Retorna:**
```python
{
    "tipo_resposta": "cliente_nome",
    "cliente_nome": str,
    "cliente_relacao": str | None,  # "filho", "esposa", "dependente"
    "confianca": float
}
```

**Motor Faz:**
1. Salvar cliente_nome em Clientes/{tenant}/Clientes/{actor_id}
2. Se cliente_relacao: anotar contexto
3. Prosseguir para próximo passo do fluxo

---

## CONTRATO GENÉRICO

### Entrada para GPT

```python
{
    "estado_fluxo": str,           # estado do fluxo ativo
    "draft_agendamento": dict,     # dados coletados até agora
    "historico": [dict],           # contexto histórico
    "mensagem": str,               # mensagem do usuário
    "tenant_config": dict,         # configuração do negócio (serviços, profissionais, etc)
    "prompt_instrucoes": str       # instruções específicas do estado
}
```

### Saída de GPT

```python
{
    "tipo_resposta": str,          # tipo de interpretação (OBRIGATÓRIO)
    # ... campos específicos do tipo ...
    "ambigua": bool,               # se há ambiguidade
    "confianca": float,            # 0.0-1.0
    "motivo_se_recusou": str | None  # se não conseguiu interpretar
}
```

**Contrato obrigatório:**
- ✅ Sempre retornar `tipo_resposta`
- ✅ Sempre retornar `ambigua` e `confianca`
- ✅ Nunca retornar `contexto_neutro` se fluxo ativo
- ✅ Campos específicos variam por `tipo_resposta`

---

## PADRÃO PROIBIDO

### ❌ Lista de Frases

```python
# PROIBIDO:
if "sim" in mensagem.lower():
    confirmacao = True
elif "não" in mensagem.lower():
    confirmacao = False
else:
    ambigua = True
```

**Por quê:** Frágil, não generaliza, falha em variações.

### ❌ Listas Hardcoded

```python
# PROIBIDO:
NOMES_PROFISSIONAIS = ["Maria", "Carla", "Ana"]
if any(nome in mensagem for nome in NOMES_PROFISSIONAIS):
    profissional = ...
```

**Por quê:** Não escala, precisa atualização manual.

### ❌ Contexto_Neutro com Fluxo Ativo

```python
# PROIBIDO:
if estado_fluxo == "aguardando_confirmacao":
    if não_entendi:
        return contexto_neutro  # ❌ ERRADO
```

**Por quê:** Fluxo merece resposta contextual, não abandono.

---

## PADRÃO CORRETO

### ✅ Interpretação Semântica

```python
# CORRETO:
# GPT interpreta "Não tenho preferência" como:
# → em contexto de profissional?
#   → { profissional_indiferente: true }
# → em contexto de data?
#   → { data_flexivel: true }
# → em contexto geral?
#   → ambigua: true, precisa esclarecimento

# Lógica depende do CONTEXTO, não da frase literal
```

### ✅ Falha Graceful

```python
# CORRETO:
if não_consegui_interpretar:
    return {
        "tipo_resposta": estado_esperado,
        "ambigua": true,
        "confianca": 0.3,
        "motivo_se_recusou": "Não consegui interpretar..."
    }

# Motor recebe estrutura, não assume falha
# Motor pode: pedir esclarecimento OU sugerir opções
```

---

## IMPLEMENTAÇÃO: SERVIÇO INTERPRETACAO_CONTEXTUAL_SERVICE.PY

**Arquivo:** `services/interpretacao_contextual_service.py`

**Responsabilidades:**

1. ✅ Dispatcher por `estado_fluxo`
2. ✅ Chamar GPT com contexto apropriado
3. ✅ Validar resposta (sempre tipo_resposta?)
4. ✅ Garantir nunca contexto_neutro com fluxo ativo
5. ✅ Retornar estrutura tipada

**Assinatura:**

```python
async def interpretar_com_fluxo_ativo(
    estado_fluxo: str,
    draft_agendamento: dict,
    mensagem: str,
    tenant_id: str,
    actor_id: str,
    contexto: dict
) -> dict:
    """
    Interpreta mensagem dentro do contexto do fluxo ativo.
    
    Garantias:
    - Nunca contexto_neutro se estado_fluxo é ativo
    - Sempre tipo_resposta na saída
    - Resposta é estrutura determinística (não texto)
    """
```

---

## TESTES OBRIGATÓRIOS

### 1️⃣ Teste: Ambiguidade Resolvida por Contexto

```python
# Entrada idêntica, contextos diferentes

# Cenário A: agendamento em progresso
estado_fluxo = "aguardando_profissional"
mensagem = "Não tenho preferência"
# Esperado: profissional_indiferente=true

# Cenário B: agendamento completo
estado_fluxo = "aguardando_confirmacao"
mensagem = "Não tenho preferência"
# Esperado: ambigua=true (não faz sentido confirmar com "não tenho preferência")

# Validação: Mesma frase, interpretações diferentes
assert interpretacao_A["profissional_indiferente"] == true
assert interpretacao_B["ambigua"] == true
```

### 2️⃣ Teste: Nunca Contexto_Neutro com Fluxo Ativo

```python
# Garantia: com estado_fluxo ativo, nunca retorna contexto_neutro

for estado in ["aguardando_profissional", "aguardando_data_hora", ...]:
    resultado = await interpretar_com_fluxo_ativo(
        estado_fluxo=estado,
        mensagem="xyz"  # qualquer coisa
    )
    
    assert resultado["tipo_resposta"] != "contexto_neutro"
    assert resultado.get("tipo_resposta") is not None
```

### 3️⃣ Teste: Ambiguidade Detectada

```python
# Garantia: ambiguidade é explícita, não silenciosa

mensagem = "Próxima semana"  # quando exatamente?
resultado = await interpretar_com_fluxo_ativo(
    estado_fluxo="aguardando_data_hora",
    mensagem=mensagem
)

assert resultado["ambigua"] == true
assert resultado["confianca"] < 0.8
# Motor pode: pedir esclarecimento OU sugerir opções
```

### 4️⃣ Teste: Confiança Baixa Sinalizada

```python
# Garantia: se confiança baixa, motor não age cegamente

mensagem = "Sabe né"  # ininteligível
resultado = await interpretar_com_fluxo_ativo(
    estado_fluxo="aguardando_confirmacao",
    mensagem=mensagem
)

assert resultado["confianca"] < 0.5
assert resultado["ambigua"] == true
# Motor: pede confirmação explícita antes de persistir
```

### 5️⃣ Teste: Estrutura Sempre Tipada

```python
# Garantia: resposta é sempre estrutura, nunca texto livre

resultado = await interpretar_com_fluxo_ativo(...)

# Sempre há campos esperados
assert "tipo_resposta" in resultado
assert "ambigua" in resultado
assert "confianca" in resultado

# Nunca "resposta" em texto livre
assert "resposta_texto" not in resultado
assert "mensagem_gpt" not in resultado
```

### 6️⃣ Teste: Fallback Graceful

```python
# Garantia: se não conseguir interpretar, retorna estrutura válida

resultado = await interpretar_com_fluxo_ativo(
    estado_fluxo="aguardando_profissional",
    mensagem="🎵🎶🎼"  # ruído
)

# Sempre estrutura válida
assert resultado["tipo_resposta"] == "preferencia_profissional"
assert resultado["ambigua"] == true
assert resultado["confianca"] < 0.3

# Motor recebe estrutura, não erro
assert isinstance(resultado, dict)
```

---

## INTEGRAÇÃO COM MOTOR DETERMINÍSTICO

### Fluxo Típico

```
1. Usuario envia mensagem
   ↓
2. Router identifica estado_fluxo ativo
   ↓
3. Chamar interpretar_com_fluxo_ativo()
   ↓
4. GPT retorna estrutura (tipo_resposta + campos específicos)
   ↓
5. Motor determinístico executa baseado em tipo_resposta:
   - Busca disponibilidade
   - Valida conflito
   - Cria evento
   - Persiste Firestore
   ↓
6. Responder ao cliente + evoluir fluxo
```

### Exemplo Real: Agendamento Completo

```python
# Cliente: "Segunda à tarde com a Maria"

# ===== FLUXO ATIVO =====
estado_fluxo = "aguardando_data_hora"
draft_agendamento = { "servico": "corte" }
mensagem = "Segunda à tarde com a Maria"

# ===== GPT INTERPRETA =====
resultado_gpt = await interpretar_com_fluxo_ativo(
    estado_fluxo="aguardando_data_hora",
    mensagem=mensagem
)
# Retorna:
# {
#   "tipo_resposta": "data_hora",
#   "data_extraida": "2026-07-01",
#   "hora_extraida": "14:00",
#   "intervalo_extraido": "tarde",
#   "ambigua": false,
#   "confianca": 0.95
# }

# ===== MOTOR DETERMINÍSTICO EXECUTA =====
# Nota: "com a Maria" foi mencionado mas não é resposta a "aguardando_data_hora"
# Motor segue: data + hora extraídos do contexto
# Maria será mencionada quando estado_fluxo = "aguardando_profissional"

# 1. Validar data não no passado
assert "2026-07-01" >= hoje

# 2. Validar hora no expediente
assert "14:00" between "08:00" and "18:00"

# 3. Buscar slots disponíveis para "corte" em 2026-07-01
slots = await buscar_slots(
    servico="corte",
    data="2026-07-01",
    horario_preferido="14:00"
)
# slots = ["14:00", "14:30", "15:00", ...]

# 4. Evoluir fluxo
draft_agendamento["data_hora"] = "2026-07-01T14:00:00"
estado_fluxo = "aguardando_profissional"

# 5. Responder ao cliente
resposta = f"Perfeito! Segunda às 14:00 está disponível. Qual profissional você prefere?"
```

---

## CHECKLIST FINAL

- ✅ GPT APENAS interpreta linguagem
- ✅ Motor faz toda lógica de negócio
- ✅ Estrutura tipada sempre (nunca texto livre)
- ✅ Nunca contexto_neutro com fluxo ativo
- ✅ Ambiguidade é explícita
- ✅ Confiança sinalizada
- ✅ Sem listas hardcoded de frases
- ✅ Padrão correto: semântica + contexto
- ✅ Testes de ambiguidade cobertos
- ✅ Integração com motor definida

---

## STATUS

✅ **ESPECIFICAÇÃO OFICIAL**

Data de implementação: 2026-06-28  
Data de validação: (a validar em BLOCO 4 testes)  

**Próximas mudanças não são permitidas sem decisão explícita.**

---

## REFERÊNCIAS

- [Especificação Final Identidade](SPEC_FINAL_IDENTIDADE_PAPEIS_ATORES.md)
- [P0 Identidade + Sessão V2 + Interpretação](../auditorias/P0_IDENTIDADE_SESSAO_V2_INTERPRETACAO_CONTEXTUAL_FINAL.md)
- [Serviço Interpretação Contextual](../../services/interpretacao_contextual_service.py)
- [CLAUDE.md — Regra Zero + 13 regras](../../CLAUDE.md)
