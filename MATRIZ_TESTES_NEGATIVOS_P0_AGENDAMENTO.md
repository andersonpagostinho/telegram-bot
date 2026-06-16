# 🔴 MATRIZ DE TESTES NEGATIVOS P0 — Agendamento

**Data:** 2026-06-16  
**Status:** DEFINIÇÃO  
**Objetivo:** Cobrir cenários onde usuário informa dados existentes/inexistentes ou incompatíveis

---

## 📋 Definição de Escopo

**Testes Negativos** = cenários onde o usuário fornece entrada que:
- ❌ Referencia entidade inexistente (profissional/serviço)
- ❌ Referencia entidade incompatível (profissional não atende serviço)
- ❌ Referencia slot indisponível (horário/data ocupado/fechado)
- ❌ É ambígua/inconsistente (múltiplas entidades, nomes variados)

**Outcome esperado** = resposta clara + lista de opções válidas + contexto preservado + SEM criar evento

---

## 🎯 10 Cenários de Teste

### 1️⃣ Profissional Existe, Não Atende Serviço

**Categoria:** Incompatibilidade de Serviço  
**Status:** ✅ JÁ IMPLEMENTADO (P0)

**Entrada:**
```
Estado: aguardando_profissional
Serviço: corte
Mencionado: Carla
Carla atende: [escova, hidratação]
Disponiveis: [Bruna, Gloria, Joana]
```

**Cenário Real:**
```
"Carla"
```

**Resposta Esperada:**
```
"*Carla* não atende corte.
 Para *corte*, posso verificar com: Bruna, Gloria, Joana.
 Qual você prefere?"
```

**Validações:**
- [x] Resposta informa "não atende"
- [x] Resposta menciona serviço
- [x] Resposta lista profissionais válidos
- [x] Draft preserva: servico=corte, data, hora
- [x] Estado = aguardando_profissional
- [x] profissional != "Carla"
- [x] Nenhum evento criado

---

### 2️⃣ Profissional Não Existe

**Categoria:** Entidade Inexistente  
**Status:** ❌ NÃO TESTADO

**Entrada:**
```
Estado: aguardando_profissional
Serviço: corte
Mencionado: Fernanda
Profissionais cadastrados: [Carla, Bruna, Gloria, Joana]
Disponiveis: [Bruna, Gloria, Joana]
```

**Cenário Real:**
```
"Fernanda"
```

**Resposta Esperada:**
```
"Não encontrei *Fernanda* entre os profissionais.
 Para *corte*, tenho: Bruna, Gloria, Joana.
 Com qual você prefere?"
```

**Validações:**
- [ ] Resposta informa "não encontrei"
- [ ] Resposta menciona nome mencionado
- [ ] Resposta lista profissionais válidos
- [ ] Draft preserva serviço
- [ ] Estado = aguardando_profissional
- [ ] profissional is None
- [ ] Nenhum evento criado

---

### 3️⃣ Serviço Não Existe

**Categoria:** Entidade Inexistente  
**Status:** ❌ NÃO TESTADO

**Entrada:**
```
Estado: aguardando_servico
Mencionado: massagem
Serviços disponíveis: [corte, escova, hidratação, manicure, coloração]
```

**Cenário Real:**
```
"Quero massagem"
```

**Resposta Esperada:**
```
"Não encontrei o serviço 'massagem'.
 Oferecemos: corte, escova, hidratação, manicure, coloração.
 Qual você prefere?"
```

**Validações:**
- [ ] Resposta informa "não encontrei"
- [ ] Resposta menciona serviço mencionado
- [ ] Resposta lista serviços disponíveis
- [ ] Draft vazio ou anterior preservado
- [ ] Estado = aguardando_servico
- [ ] servico is None
- [ ] Nenhum evento criado

---

### 4️⃣ Serviço Existe, Nenhum Profissional Atende

**Categoria:** Indisponibilidade de Profissional  
**Status:** ❌ NÃO TESTADO

**Entrada:**
```
Estado: aguardando_profissional
Serviço: botox capilar (existe, mas nenhum profissional atende)
Serviços_busca: [botox capilar]
Profissionais que atendem: []
Data: 2026-06-17
Hora: 10:00
```

**Cenário Real:**
```
"Preciso de botox capilar"
```

**Resposta Esperada:**
```
"Entendi: você quer *botox capilar*.
 Infelizmente, nenhum profissional oferece esse serviço no momento.
 Posso ajudar com: corte, escova, hidratação, manicure, coloração?"
```

**Validações:**
- [ ] Resposta informa indisponibilidade
- [ ] Resposta menciona serviço solicitado
- [ ] Resposta lista serviços alternativos
- [ ] Draft vazio
- [ ] Estado = aguardando_profissional ou aguardando_servico
- [ ] servico = "botox capilar" (registrou tentativa)
- [ ] profissional is None
- [ ] Nenhum evento criado

---

### 5️⃣ Profissional Existe, Serviço Existe, Horário Indisponível

**Categoria:** Conflito de Horário  
**Status:** ⚠️ PARCIALMENTE TESTADO (covered by runner_stress_profissional_alternativo)

**Entrada:**
```
Estado: aguardando_profissional
Profissional: Bruna
Serviço: corte
Data: 2026-06-17
Hora: 10:00
Bruna agenda: [09:00-10:30 corte]
Eventos: conflita com 09:00-10:30
```

**Cenário Real:**
```
"Bruna"
```

**Resposta Esperada:**
```
"*Bruna* está com o horário ocupado para 17/06 às 10:00.
 Horários disponíveis: 14:00, 15:30, 16:00.
 Prefere algum desses? Ou gostaria de outro profissional?"
```

**Validações:**
- [ ] Resposta informa "horário ocupado"
- [ ] Resposta menciona profissional
- [ ] Resposta lista horários alternativos
- [ ] Draft preserva: servico, data, (hora antiga)
- [ ] Estado = aguardando_profissional (ou sugerindo alternativas)
- [ ] profissional != "Bruna"
- [ ] Nenhum evento criado

---

### 6️⃣ Profissional Existe, Serviço Existe, Data Fora do Expediente

**Categoria:** Indisponibilidade de Data  
**Status:** ❌ NÃO TESTADO

**Entrada:**
```
Estado: aguardando_profissional
Profissional: Bruna
Serviço: corte
Data: 2026-06-21 (domingo)
Hora: 10:00
Expediente: seg-sab, 08:00-18:00
```

**Cenário Real:**
```
"Bruna"  (em contexto de data=domingo)
```

**Resposta Esperada:**
```
"*Bruna* só atende seg-sab, das 08:00 às 18:00.
 O domingo está fora do expediente.
 Próxima disponibilidade: 22/06 (segunda) às 10:00.
 Confirma?"
```

**Validações:**
- [ ] Resposta informa "fora do expediente"
- [ ] Resposta menciona próxima data válida
- [ ] Draft preserva: servico, hora
- [ ] Data pode ser atualizada a próximo válido
- [ ] Estado = aguardando_profissional ou confirmacao
- [ ] Nenhum evento criado sem confirmação

---

### 7️⃣ Mensagem com Múltiplas Entidades Incompatíveis

**Categoria:** Ambiguidade/Inconsistência  
**Status:** ❌ NÃO TESTADO

**Entrada:**
```
Mensagem: "Quero corte com Carla e manicure com Larissa amanhã às 10"
Interpretação possível:
  - 2 serviços: [corte, manicure]
  - 2 profissionais: [Carla, Larissa]
  - 1 horário: 10:00
  - Problema: Carla não atende manicure, Larissa não atende corte
```

**Cenário Real:**
```
"corte com Carla e manicure com Larissa amanhã às 10"
```

**Resposta Esperada:**
```
"Entendi dois serviços: corte e manicure.
 Mas você mencionou profissionais diferentes.
 Vamos tratar um de cada vez?
 Qual você quer agendar primeiro: corte ou manicure?"
```

**Validações:**
- [ ] Resposta não mistura serviços/profissionais
- [ ] Resposta pede esclarecimento
- [ ] Draft vazio ou parcial
- [ ] Estado = aguardando_servico ou confirmacao
- [ ] Nenhum evento criado

---

### 8️⃣ Nome Parecido / Acentuação / Normalização

**Categoria:** Variação de Nome  
**Status:** ⚠️ PARCIALMENTE TESTADO (normalização existe)

**Entrada:**
```
Cadastrados: [Gloria, Joana, Carla]
Mencionado:
  - "gloria" (minúscula)
  - "Glória" (com acento)
  - "joana" (minúscula)
```

**Cenário Real:**
```
Estado: aguardando_profissional
Serviço: corte
Disponiveis: [Gloria, Joana]
Entrada: "gloria" ou "glória" ou "GLORIA"
```

**Resposta Esperada:**
```
"Ótimo, com *Gloria*!
 Corte amanhã às 10:00 com Gloria. Confirma?"
```

**Validações:**
- [ ] Normalização com unidecode funciona
- [ ] "gloria" == "Gloria"
- [ ] "Glória" == "Gloria"
- [ ] "GLORIA" == "Gloria"
- [ ] profissional = "Gloria" (versão correta)
- [ ] Nenhuma confusão de identidade

---

### 9️⃣ Serviço com Variação de Nome

**Categoria:** Variação de Serviço  
**Status:** ⚠️ PARCIALMENTE TESTADO (encontrar_servico_mais_proximo existe)

**Entrada:**
```
Cadastrados: [corte, escova, hidratação, coloração]
Mencionado:
  - "corte" → exato
  - "corte de cabelo" → variação
  - "cortando cabelo" → paráfrase
```

**Cenário Real:**
```
Estado: aguardando_servico
Entrada: "Quero corte de cabelo" ou "preciso cortar"
```

**Resposta Esperada:**
```
"Entendi, você quer *corte*.
 Qual profissional você prefere?"
```

**Validações:**
- [ ] "corte de cabelo" → "corte"
- [ ] "cortar cabelo" → "corte"
- [ ] Fuzzy match funciona
- [ ] servico = "corte" (canonical)
- [ ] Estado progride para aguardando_profissional

---

### 🔟 Profissional Informado Depois (Continuidade de Fluxo)

**Categoria:** Continuidade + Incompatibilidade  
**Status:** ✅ PARCIALMENTE (pode testar em sequência)

**Entrada:**
```
Passo 1: "Quero corte"
  → Estado: aguardando_data
  → servico = "corte"

Passo 2: "Amanhã às 10"
  → Estado: aguardando_profissional
  → disponiveis = [Bruna, Gloria, Joana]

Passo 3: "Carla"
  → Carla não está em disponiveis
  → Carla não atende corte
  → Estado: Still aguardando_profissional
```

**Cenário Real:**
```
Sequência:
  1. "Quero corte"
  2. "Amanhã às 10"
  3. "Carla"
```

**Resposta Esperada (após passo 3):**
```
"*Carla* não atende corte.
 Para *corte*, posso verificar com: Bruna, Gloria, Joana.
 Qual você prefere?"
```

**Validações:**
- [ ] Continuidade de fluxo mantida
- [ ] servico preservado = "corte"
- [ ] data_hora preservada = "17/06 10:00"
- [ ] Resposta específica (não genérica)
- [ ] Estado = aguardando_profissional
- [ ] profissional is None
- [ ] Nenhum evento criado

---

## 📊 Tabela Resumida

| # | Cenário | Categoria | Status | Tipo Validação |
|---|---------|-----------|--------|---|
| 1 | Prof. existe, não atende | Incompatibilidade | ✅ Feito | Resposta específica |
| 2 | Prof. não existe | Inexistente | ❌ TODO | Resposta informativa |
| 3 | Serviço não existe | Inexistente | ❌ TODO | Resposta informativa |
| 4 | Serviço existe, sem prof | Indisponibilidade | ❌ TODO | Resposta informativa |
| 5 | Prof/Serv, horário ocup | Conflito | ⚠️ Parcial | Resposta com sugestões |
| 6 | Prof/Serv, data fora exp | Indisponibilidade | ❌ TODO | Resposta com próximo válido |
| 7 | Múltiplas entidades | Ambiguidade | ❌ TODO | Resposta pede esclarecimento |
| 8 | Nome variado/acentuação | Normalização | ⚠️ Parcial | Match funciona |
| 9 | Serviço variado | Normalização | ⚠️ Parcial | Match funciona |
| 10 | Prof depois (continuidade) | Fluxo + Incompatibilidade | ✅ Testável | Resposta específica |

---

## ✅ Critérios de Validação Comuns

Para **cada teste**, validar:

```python
class ValidacaoNegativa:
    def validar(self):
        # Resposta
        assert "resposta" in resultado
        assert len(resultado["resposta"]) > 0
        
        # Contexto/Draft
        assert resultado["draft_agendamento"]["servico"] == esperado["servico"] or servico is None
        assert resultado["draft_agendamento"]["data_hora"] == esperado["data_hora"] or data_hora is None
        
        # Estado
        assert resultado["estado_fluxo"] in [
            "aguardando_servico",
            "aguardando_data",
            "aguardando_horario",
            "aguardando_profissional",
            "confirmacao"
        ]
        
        # Preenchimento
        assert resultado["draft_agendamento"]["profissional"] is None or profissional_valido
        assert resultado["draft_agendamento"]["servico"] is None or servico_valido
        
        # Evento
        assert resultado["evento_criado"] == False
        assert resultado["chamadas_gpt_decisao"] == 0  # GPT não decide disponibilidade
        
        # Resposta qualitativa
        assert nao_generico(resultado["resposta"])  # Resposta específica, não genérica
        assert lista_opcoes(resultado["resposta"])  # Lista opções válidas quando aplicável
```

---

## 🏗️ Estrutura do Runner

**Arquivo:** `tests/runner_stress_negativos_agendamento_p0.py`

```python
async def main():
    # Inicializar mocks (baseado em runner existente)
    contexto_mock = ContextoMock()
    firebase_mock = FirebaseMock()
    session_mock = SessionMock()
    
    # Definir 10 testes (um para cada cenário)
    testes = [
        teste_1_prof_nao_atende(),
        teste_2_prof_nao_existe(),
        teste_3_servico_nao_existe(),
        # ...
        teste_10_prof_depois()
    ]
    
    resultados = []
    for teste in testes:
        resultado = await executar_teste(teste)
        resultados.append(resultado)
        validar_resultado(resultado)
    
    # Salvar resultados em JSON
    salvar_resultados_json(resultados, "resultado_stress_negativos_agendamento_p0.json")
```

---

## 📝 Saída Esperada

**Arquivo:** `tests/resultado_stress_negativos_agendamento_p0.json`

```json
{
  "suite": "stress_negativos_agendamento_p0",
  "data": "2026-06-16",
  "total_testes": 10,
  "passou": 10,
  "falhou": 0,
  "testes": [
    {
      "id": 1,
      "cenario": "Profissional existe, não atende serviço",
      "entrada": "Carla",
      "resposta": "*Carla* não atende corte. Para *corte*, posso verificar com: Bruna, Gloria, Joana. Qual você prefere?",
      "validacoes": {
        "menciona_nome": true,
        "menciona_motivo": true,
        "menciona_servico": true,
        "lista_opcoes": true,
        "draft_preservado": true,
        "evento_criado": false
      },
      "status": "PASSOU"
    },
    {
      "id": 2,
      "cenario": "Profissional não existe",
      "entrada": "Fernanda",
      "resposta": "Não encontrei *Fernanda*...",
      "validacoes": { /* ... */ },
      "status": "PASSOU"
    },
    /* ... 8 mais ... */
  ],
  "resumo": {
    "categoria": "Testes Negativos P0 — Agendamento",
    "objetivo": "Validar respostas para dados incompatíveis/inexistentes",
    "conclusao": "10/10 cenários validados com sucesso"
  }
}
```

---

## 🔧 Próximas Ações

1. ✅ Criar matriz de testes (este documento)
2. ⏳ Implementar runner com 10 testes
3. ⏳ Executar e coletar resultados em JSON
4. ⏳ Documentar descobertas em docs/auditorias/

---

## 📚 Referências

- `PATCH_P0_PROFISSIONAL_INVALIDO.md` — Implementação do cenário #1
- `prompts/manual_secretaria.py` — Regras de resposta
- `tests/runner_stress_profissional_alternativo_completo.py` — Template para runner
- `CLAUDE.md` — Regras de investigação

---

**Matriz versão:** 1.0  
**Data:** 2026-06-16  
**Status:** DEFINIÇÃO COMPLETA
