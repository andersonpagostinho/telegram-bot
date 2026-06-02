# 🧪 Testes de Regressão Permanente da NeoEve

**Objetivo:** Casos que **revelam mais defeitos semânticos** do que dezenas de cenários "felizes".

Esses testes representam padrões **legítimos de produção**, não casos artificiais.

---

## 📈 Este Documento É EVOLUTIVO

**Contraste com CLAUDE.md:**

```
CLAUDE.md (Regras):           🔒 CONGELADO
├─ Mudança = mudança de filosofia
├─ Alto custo de mudança
└─ Apenas com evidência muito forte

TESTES_REGRESSAO_PERMANENTE.md: 📈 EVOLUTIVO
├─ Cresce sempre que bug revela nova classe de erro
├─ Baixo custo de adicionar teste
└─ Preferível a adicionar nova regra
```

**Quando adicionar novo teste:**

1. ✅ Bug encontrado em produção
2. ✅ Não coberto pelos 5 testes existentes
3. ✅ Representa padrão **legítimo de produção** (não artificial)
4. ✅ Adicione caso permanente para evitar regressão

**Quando NÃO adicionar novo teste:**

- ❌ Um caso único/outlier
- ❌ Padrão artificial/nunca acontece em produção real
- ❌ Apenas refinaria teste existente (refine, não crie)

---

**Hierarquia saudável:**

```
Bug novo em produção
    ↓
Análise: qual classe de erro?
    ↓
Teste permanente EXATAMENTE esse padrão
    ↓
Adiciona a TESTES_REGRESSAO_PERMANENTE.md
    ↓
Roda em toda mudança relacionada
    ↓
Bug não volta
```

**VS hierarquia prejudicial:**

```
Bug novo em produção
    ↓
Análise: "préciso de nova regra"
    ↓
Adiciona Regra 14 ao CLAUDE.md
    ↓
Documento fica 15% maior
    ↓
Ninguém lê Regra 14
    ↓
Mesmo bug volta 3 meses depois
```

---

## 📋 Caso 1: Pai Marcando Serviço para Filha (SURI)

**Por que este caso é crítico:**
- Padrão real de produção
- Expõe erros semânticos (não artificiais)
- Já revelou um bug real: confusão cliente vs profissional
- Deve ser executado em TODA mudança relacionada a agendamento

---

### ✅ Teste: Cliente Dependente (Filha)

**Mensagem de entrada (voz ou texto):**
```
"Quero marcar escova para minha filha Suri amanhã"
```

**Fluxo esperado:**

1. ✅ GPT extrai:
   - Serviço: "escova"
   - Dependente: "minha filha"
   - Nome do dependente: "Suri"
   - Data: "amanhã"
   - Profissional: (não informado)

2. ✅ Sistema mapeia dependente para cliente:
   ```json
   {
     "cliente_nome": "Suri",
     "cliente_tipo": "dependente",
     "servico": "escova",
     "profissional": null,
     "data_agendamento": "amanhã",
     "dono_original": "user_id_do_pai"
   }
   ```

3. ✅ NUNCA neste estado:
   ```json
   {
     "profissional": "Suri",  // ❌ ERRO SEMÂNTICO
     ...
   }
   ```

---

### 🧪 Validação Técnica

**Arquivo para verificar:** `prompts/manual_secretaria.py`
- Seção: 7.5 "CLIENTE / PESSOA ATENDIDA"
- Deve usar `cliente_nome` para "minha filha Suri"
- Deve usar `profissional` APENAS para profissionais

**Arquivo para verificar:** `handlers/event_handler.py`
- Função: `add_evento_por_gpt()`
- Linha: verificar se `cliente_nome` é respeitado

**Log esperado:**
```
[AGENDAMENTO] cliente_nome=Suri, tipo=dependente, profissional=null
[SUCESSO] Evento criado para Suri
```

**Log que indicaria regressão:**
```
[AGENDAMENTO] profissional=Suri  // ❌ REGRESSÃO
```

---

## 📋 Caso 2: Ambiguidade Nome = Profissional + Cliente

**Por que este caso é crítico:**
- Detecta falhas em desambiguação
- Expõe quando sistema não pede clarificação

---

### ✅ Teste: Mesmo Nome em Dois Contextos

**Cenário:** Tem profissional "Bruna" E mãe se chama "Bruna"

**Mensagem 1:**
```
"Quero com a Bruna"
```

**Fluxo esperado:**
- Sistema não assume
- Pergunta: "Você quer com a profissional Bruna ou para sua mãe Bruna?"

**Cenário 2:** Mensagem clara
```
"Quero escova com minha mãe Bruna"
```

**Fluxo esperado:**
```json
{
  "cliente_nome": "Bruna",
  "cliente_tipo": "dependente (mãe)",
  "profissional": null,
  "servico": "escova"
}
```

---

## 📋 Caso 3: Profissional Recorrente

**Por que este caso é crítico:**
- Testa referência contextual
- Detecta quando contexto não é respeitado

---

### ✅ Teste: "Mesma Profissional"

**Contexto anterior:**
- Último serviço: Profissional "Carla", serviço "massagem"

**Mensagem nova:**
```
"Quero marcar outro serviço com a mesma profissional"
```

**Fluxo esperado:**
```json
{
  "cliente_nome": null,
  "profissional": "Carla",  // ✅ Do contexto anterior
  "servico": (usuário será perguntado),
  "data_agendamento": (usuário será perguntado)
}
```

**Não deve:**
- ❌ Esquecer Carla do contexto
- ❌ Interpretar "mesma" como profissional chamado "Mesma"

---

## 📋 Caso 4: Cliente Ambíguo (Pode Ser Nome Próprio)

**Por que este caso é crítico:**
- Nomes próprios podem ser profissionais ou clientes
- Sistema deve ser conservador

---

### ✅ Teste: Nome Simples Ambíguo

**Mensagem:**
```
"Quero marcar para Rita"
```

**Fluxo esperado:**
- Se "Rita" é um profissional cadastrado:
  ```json
  { "profissional": "Rita" }
  ```
- Se "Rita" PODE ser mãe/esposa/filha:
  ```
  Sistema pergunta: "Você quer com a profissional Rita ou para a Rita de sua família?"
  ```

**Não deve:**
- ❌ Assumir automaticamente
- ❌ Ficar em silêncio esperando clarificação

---

## 📋 Caso 5: Contexto Contaminado (Fluxo Anterior)

**Por que este caso é crítico:**
- Testa limpeza de contexto entre agendamentos
- Detecta data/profissional "pegajosa"

---

### ✅ Teste: Dois Agendamentos Sequenciais

**Primeiro agendamento:**
```
"Escova com Bruna para amanhã"
↓ (Sucesso, contexto limpo)
```

**Segundo agendamento imediatamente após:**
```
"Quero marcar para minha filha"
```

**Fluxo esperado:**
```json
{
  "cliente_nome": "filha",  // ✅ Nome não informado, deve pedir
  "profissional": null,  // ✅ NÃO pega Bruna de antes
  "data_agendamento": null,  // ✅ NÃO pega amanhã de antes
}
```

**Indicador de regressão:**
```json
{
  "profissional": "Bruna",  // ❌ CONTAMINAÇÃO
  "data_agendamento": "amanhã"  // ❌ CONTAMINAÇÃO
}
```

---

## 🔄 Frequência de Execução

| Momento | O que testar |
|---------|-------------|
| **Toda mudança em manual_secretaria.py** | Todos os 5 casos |
| **Toda mudança em event_handler.py** | Casos 1-5 |
| **Toda mudança em prompts/** | Casos 1, 2, 4 |
| **Antes de release** | Todos os 5 casos |
| **Após bug encontrado em agendamento** | Pelo menos Caso 1 |

---

## 📊 Template de Resultado

```markdown
# Resultado Teste Regressão Permanente

**Data:** 2026-06-03
**Versão:** commit XYZ
**Executor:** [nome]

## Caso 1: Filha Suri
- [ ] ✅ Entrada processada corretamente
- [ ] ✅ cliente_nome = "Suri"
- [ ] ✅ profissional = null
- [ ] ✅ tipo = "dependente"
- [ ] ❌ REGRESSÃO ENCONTRADA: [descrever]

## Caso 2: Ambiguidade Bruna
- [ ] ✅ Sistema pediu clarificação
- [ ] ✅ Cliente Bruna mapeado corretamente
- [ ] ✅ Profissional Bruna não confundida
- [ ] ❌ REGRESSÃO ENCONTRADA: [descrever]

## Caso 3: Mesma Profissional
- [ ] ✅ Contexto anterior respeitado
- [ ] ✅ "Carla" foi mantida
- [ ] ✅ Nenhuma contaminação cruzada
- [ ] ❌ REGRESSÃO ENCONTRADA: [descrever]

## Caso 4: Rita Ambígua
- [ ] ✅ Sistema perguntou "profissional ou cliente?"
- [ ] ✅ Sem assumição automática
- [ ] ❌ REGRESSÃO ENCONTRADA: [descrever]

## Caso 5: Contexto Limpo
- [ ] ✅ Segundo agendamento limpo
- [ ] ✅ Nenhuma "pegajosidade"
- [ ] ✅ Profissional anterior não carregou
- [ ] ✅ Data anterior não carregou
- [ ] ❌ REGRESSÃO ENCONTRADA: [descrever]

**RESULTADO FINAL:** ✅ PASSOU / ❌ REGRESSÃO
```

---

## 🎯 Filosofia

> "Um teste que representa um padrão legítimo de produção
> vale mais que 100 testes 'felizes' que ninguém usa."

O caso "Suri" é exatamente isso.

Não é artificial.
Não é edge case raro.

É pai marcando para filha.

**Quando esse teste falha, você encontra bugs reais.**

---

**Última atualização:** 2026-06-02  
**Recomendação:** Adicionar a suite de CI/CD da NeoEve
