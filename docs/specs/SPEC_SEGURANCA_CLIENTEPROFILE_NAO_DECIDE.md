# 🔒 SPEC SEGURANÇA: ClienteProfile Não Decide

**Data:** 2026-06-14  
**Status:** ✅ ATIVA  
**Escopo:** P1.2+ (Histórico, Preferências, Perfil Comportamental)  
**Prioridade:** CRÍTICA  

---

## 🎯 REGRA CENTRAL

**ClienteProfile INFLUENCIA sugestões, mas NUNCA DECIDE criação de evento.**

```
Perfil histórico NÃO representa intenção atual do cliente.

Histórico é CONTEXTO, não AUTORIDADE.

Mensagem atual sempre vence histórico.
```

---

## 🚨 POLÍTICA OBRIGATÓRIA DE CODE REVIEW

**Referência:** [`docs/policies/POLITICA_CODE_REVIEW_CLIENTEPROFILE.md`](../policies/POLITICA_CODE_REVIEW_CLIENTEPROFILE.md)

### Aplicabilidade

**TODO PR que envolva ClienteProfile DEVE:**

- ✅ Citar esta especificação (SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md)
- ✅ Incluir checklist de validação (10 itens obrigatórios)
- ✅ Ser revisado por alguém especializado em SPEC_SEGURANCA
- ✅ Incluir testes que validam a segurança

### Triggers para Revisão Especializada

PR é revisado por especialista em ClienteProfile se contém:

- `obter_profile()` - leitura de dados de cliente
- `profissional_mais_frequente` - consulta de histórico
- `servico_mais_frequente` - consulta de preferências
- `ClienteProfile` - qualquer uso de perfil
- `histórico do cliente` - contexto passado

### Bloqueio Automático

PRs são **automaticamente rejeitadas** se:

- ❌ Não incluem checklist de validação
- ❌ Não citam SPEC_SEGURANCA
- ❌ Criam evento sem confirmação explícita
- ❌ Sobrescrevem pedido atual com histórico
- ❌ Ignoram conflito ou disponibilidade
- ❌ Pulam passo obrigatório do fluxo

**Ação correta:** Citar feedback e referenciar `POLITICA_CODE_REVIEW_CLIENTEPROFILE.md` (seção "Critério de Aprovação")

---

## ✅ O QUE CLIENTEPROFILE PODE FAZER

### 1. Sugerir Baseado em Histórico

✅ **Pode:** "Você costuma fazer corte com Carla. Quer verificar com ela?"  
❌ **Nunca:** "Agendei corte com Carla quinta às 15h."

✅ **Pode:** Preencher draft com profissional_mais_frequente  
❌ **Nunca:** Usar draft para criar evento sem confirmação

---

### 2. Preencher Campos Provisoriamente

✅ **Pode:**
- Sugerir `profissional` mais frequente (como default no formulário)
- Sugerir `servico` mais frequente (como default no formulário)
- Sugerir `horario` baseado em intervalo médio (como sugestão)

❌ **Nunca:**
- Usar sugestão como valor final
- Preencher sem marcar como "sugestão baseada em histórico"
- Ignorar alteração do cliente sobre o valor sugerido

---

### 3. Personalizar Experiência

✅ **Pode:**
- Adaptar linguagem ("Olá de novo! Bem-vindo.")
- Mostrar histórico ("Últimas 5 agendamentos:")
- Contextualizar ("Última vez você agendou em 2 semanas")
- Reduzir perguntas ("Quer fazer um corte novamente?")

❌ **Nunca:**
- Pular confirmação
- Ignorar preferência expressa
- Assumir consentimento baseado em histórico

---

### 4. Informar Motor Determinístico

✅ **Pode:**
- Passar `primeira_contato` ao motor para cálculo de disponibilidade
- Passar `ultima_contato` para validação de conflito
- Usar contexto para validar se sugestão é viável

❌ **Nunca:**
- Permitir que motor ignore conflito por "histórico"
- Deixar motor decidir horário sem passar por disponibilidade

---

## ❌ O QUE CLIENTEPROFILE NUNCA PODE FAZER

### 1. Criar Evento

❌ **PROIBIDO:**
```python
# Nunca fazer isso:
if profissional_mais_frequente:
    criar_evento(profissional=profissional_mais_frequente)

# Nunca fazer isso:
if servico_mais_frequente and cliente_confirmou_fluxo:
    criar_evento_automaticamente()
```

✅ **Correto:** Sugerir, pedir confirmação, deixar cliente decidir, criar evento

---

### 2. Confirmar Evento

❌ **PROIBIDO:**
```
"Encontrei Carla disponível quinta às 15h. Confirmando..."
└─ Sem aguardar confirmação explícita do cliente
```

✅ **Correto:**
```
"Encontrei Carla disponível quinta às 15h. Quer confirmar?"
└─ Aguardar "sim" do cliente antes de criar
```

---

### 3. Escolher Horário Final

❌ **PROIBIDO:**
```
Cliente: "Quero agendar corte com alguém"
Sistema: "Agendei com Carla quinta às 15h" (baseado em histórico)
```

✅ **Correto:**
```
Cliente: "Quero agendar corte com alguém"
Sistema: "Você costuma ir com Carla. Qual dia/hora prefere?"
├─ Cliente escolhe dia/hora
├─ Motor valida disponibilidade
└─ Sistema pede confirmação antes de criar
```

---

### 4. Escolher Profissional/Serviço Final

❌ **PROIBIDO:**
```
Cliente: "Quero manicure"
Sistema: "Agendando com Paula (sua manicure habitual)"
└─ Sem perguntar, só porque frequenta Paula
```

✅ **Correto:**
```
Cliente: "Quero manicure"
Sistema: "Você costuma ir com Paula. Quer com ela ou outra?"
├─ Cliente escolhe
└─ Sistema confirma antes de criar
```

---

### 5. Ignorar Conflito de Horário

❌ **PROIBIDO:**
```
"Quinta às 15h tem conflito, mas você agendou lá 3 vezes.
 Colocando mesmo assim."
```

✅ **Correto:**
```
"Quinta às 15h tem conflito.
 Que tal quarta às 14h ou sexta às 16h?"
```

---

### 6. Ignorar Disponibilidade do Profissional

❌ **PROIBIDO:**
```
Cliente: "Quero com Carla sábado"
Sistema: "Carla não trabalha sábado, mas vou agendar mesmo"
```

✅ **Correto:**
```
Cliente: "Quero com Carla sábado"
Sistema: "Carla não trabalha sábado.
          Que tal sábado com outro profissional ou Carla em outro dia?"
```

---

### 7. Substituir Pedido Explícito do Cliente

❌ **PROIBIDO:**
```
Cliente: "Escova com a Marina"
Sistema: "Você costuma ir com Carla. Agendando com ela."
└─ Ignorou pedido explícito
```

✅ **Correto:**
```
Cliente: "Escova com a Marina"
Sistema: "Agendando escova com Marina, correto?"
└─ Respeita escolha explícita
```

---

### 8. Sobrescrever Dados da Conversa Atual

❌ **PROIBIDO:**
```
Conversa atual:
├─ Cliente: "Quero corte"
├─ Sistema: "Com qual profissional?"
├─ Cliente: "Com Bruna"
└─ Sistema: "Agendando com Carla (seu usual)"
   └─ Ignorou "Bruna" que foi dito na conversa
```

✅ **Correto:**
```
Conversa atual:
├─ Cliente: "Quero corte"
├─ Sistema: "Com qual profissional?"
├─ Cliente: "Com Bruna"
└─ Sistema: "Corte com Bruna, certo?"
   └─ Usa exatamente o que foi dito
```

---

## 📋 REGRAS OBRIGATÓRIAS

### Regra 1: Pedido Explícito Sempre Vence Perfil

```
Hierarquia de autoridade:

1. ⬆️ Mensagem atual do cliente (máxima autoridade)
2. ⬆️ Valores informados na conversa
3. ⬇️ Histórico/Perfil (menor autoridade)
4. ⬇️ Defaults do sistema
```

**Implementação:**
```python
# Pseudocódigo
if cliente_disse_explicitamente(profissional):
    usar = cliente_disse_explicitamente(profissional)  # Vence tudo
elif perfil_sugere(profissional_mais_frequente):
    sugerir = perfil_sugere(profissional_mais_frequente)  # Se não disse
else:
    usar = default_sistema()  # Último recurso
```

---

### Regra 2: Perfil Entra Apenas Se Faltar Informação

```
Cliente disse profissional? → Usar exatamente isso
Cliente NOT disse profissional? → Sugerir histórico
Cliente rejeitou sugestão? → Limpar e seguir fluxo normal
```

**Implementação:**
- Nunca sobrescrever dados informados com sugestões
- Sugestões só entram em campo vazio
- Se cliente rejeita sugestão, volta ao fluxo padrão

---

### Regra 3: Toda Sugestão Baseada em Perfil Exige Confirmação

```
NUNCA fazer:
└─ Sugerir silenciosamente

SEMPRE fazer:
├─ "Você costuma com X. Quer?"
├─ Aguardar "sim" / "não" / "outro"
└─ Respeitar a resposta
```

**Exemplo correto:**
```
Sistema: "Você agendou com Carla 5 vezes. 
          Quer fazer corte com ela de novo?"

Cliente: "Não, prefiro com outra"

Sistema: "Ok, qual profissional prefere?"
```

---

### Regra 4: Fluxo de Agendamento NUNCA Pula Passos

```
Fluxo obrigatório:

1. Interpretar: qual serviço?
2. Validar: serviço existe?
3. Confirmar: duração correta?
4. Disponibilidade: motor verifica slots
5. Conflito: motor valida horário
6. Sugestão: perfil pode sugerir aqui
7. Confirmação: cliente confirma
8. Criação: evento é criado

ClienteProfile pode influenciar em 6.
Nunca pode pular 1, 2, 3, 4, 5, 7, 8.
```

---

### Regra 5: GPT Nunca Usa Profile para Decidir

```
PROIBIDO:
├─ GPT lê profissional_mais_frequente e assume

PERMITIDO:
├─ GPT recebe "último agendamento foi com Carla"
├─ GPT sugere "Quer com Carla de novo?"
└─ GPT aguarda resposta antes de usar
```

---

### Regra 6: Motor Determinístico Valida Sugestões

```
Antes de apresentar sugestão ao cliente:

Motor DEVE validar:
├─ Profissional existe?
├─ Profissional está ativo?
├─ Profissional trabalha nesse serviço?
├─ Profissional trabalha nesse dia?
├─ Existe horário disponível?
└─ Não há conflito?

Se qualquer um falhar:
└─ Não sugerir, seguir fluxo normal
```

---

### Regra 7: Conflito Entre Histórico e Atual, Atual Vence

```
Cenário:
├─ Histórico: último agendamento às 15h
├─ Motor: 15h tem conflito
└─ Cliente: "Quer verificar às 15h?"

Cliente diz: "Prefiro às 14h"

Ação: Usar 14h, NÃO 15h (mesmo que seja histórico)
```

---

### Regra 8: Recusa de Sugestão Limpa o Draft

```
Cenário:
├─ Sistema sugere: "Com Carla?"
├─ Cliente: "Não"
└─ Draft tinha: profissional=Carla

Ação imediata:
├─ Limpar profissional do draft
├─ Perguntar novamente: "Com qual profissional?"
└─ Seguir fluxo normal
```

---

### Regra 9: Nunca Agendar Automaticamente por Recorrência

❌ **PROIBIDO:**
```
Cliente agendou toda terça há 10 meses
→ Agendar próxima terça automaticamente
```

⏳ **FUTURO (com autorização explícita):**
```
Quando houver feature de "recorrência automática":
├─ Cliente ativa: "Repetir todo mês"
├─ Cliente vê: "Próximos 3 meses agendados"
└─ Cliente pode desativar a qualquer momento
```

✅ **AGORA (sem autorização):**
```
Cliente agendou toda terça há 10 meses
→ Sugerir: "Quer agendar próxima terça?"
→ Aguardar confirmação
→ Criar evento
```

---

### Regra 10: Documentar como Regra Permanente

Esta especificação será documentada permanentemente em:
- ✅ `docs/specs/SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md`
- ✅ `docs/roadmap/MAPA_CAPACIDADES_REAIS_NEOEVE.md`
- ✅ Será validada em TODOS os PRs de P1.2, P1.3, P1.4

**Quando submeter PR relacionado a ClienteProfile:**
- Incluir seção "Validação SPEC_SEGURANCA" na descrição do PR
- Listar quais regras foram respeitadas
- Apontar mudanças de comportamento

---

## 📊 MATRIZ DE DECISÃO

| Situação | Pode ClienteProfile? | Ação | Confirmação Necessária |
|----------|---------------------|------|----------------------|
| Cliente disse profissional | ❌ Não sobrescrever | Usar exatamente | Não |
| Cliente NÃO disse profissional | ✅ Sugerir histórico | "Costuma com X. Quer?" | Sim |
| Cliente rejeitou sugestão | ❌ Limpar | Voltar a fluxo normal | Sim |
| Conflito de horário | ❌ Ignorar não | Oferecer alternativa | Sim |
| Profissional indisponível | ❌ Agendar mesmo | Oferecer outro ou dia | Sim |
| Recorrência aprendida | ❌ Agendar automático | Sugerir e aguardar | Sim |
| Linguagem personalizada | ✅ Adaptar tom | "Bem-vindo de novo!" | Não |
| Histórico no contexto | ✅ Informar | "Você já agendou 10x" | Não |

---

## 🚨 ANTI-PADRÕES (NUNCA FAZER)

```python
# ❌ ANTI-PADRÃO 1: Substituir silenciosamente
if profissional_mais_frequente:
    criar_evento(profissional=profissional_mais_frequente)
# → Viola Regra 7 (pedido atual vence)

# ❌ ANTI-PADRÃO 2: Ignorar indisponibilidade
if profissional_mais_frequente:
    agendar_mesmo_se_indisponivel()
# → Viola Regra 6 (validação)

# ❌ ANTI-PADRÃO 3: Auto-agendar recorrência
if cliente_frequenta_toda_terca():
    criar_evento_proximo_terca()
# → Viola Regra 9 (autorização necessária)

# ❌ ANTI-PADRÃO 4: Não limpar recusa
if cliente_recusou_sugestao:
    pass  # Deixa draft com valor sugerido
# → Viola Regra 8 (limpeza necessária)

# ❌ ANTI-PADRÃO 5: Pular confirmação
evento = criar_evento(dados_sugeridos)
# → Viola Regra 3 (confirmação obrigatória)
```

---

## ✅ PADRÕES CORRETOS

```python
# ✅ PADRÃO 1: Sugerir e aguardar
if not cliente_escolheu_profissional:
    if profissional_mais_frequente:
        sugestao = obter_sugestao_perfil()
        apresentar_sugestao(sugestao)
        aguardar_confirmacao()

# ✅ PADRÃO 2: Respeitar escolha explícita
if cliente_escolheu_profissional:
    usar = cliente_escolheu_profissional
    # Perfil é ignorado aqui

# ✅ PADRÃO 3: Validar antes de apresentar
if profissional_mais_frequente:
    if motor_valida(profissional_mais_frequente):
        sugerir()
    else:
        # Se não valida, não sugerir
        seguir_fluxo_normal()

# ✅ PADRÃO 4: Limpar recusa
if cliente_rejeitou_sugestao:
    limpar_draft()
    solicitar_entrada_manual()

# ✅ PADRÃO 5: Confirmar antes de criar
if tudo_validado:
    pedir_confirmacao_final()
    if cliente_confirmou:
        criar_evento()
```

---

## 📝 EXEMPLOS REAIS

### Exemplo 1: Correto

```
Cliente: "Quero fazer um corte"
Sistema: "Com qual profissional? Você costuma ir com Carla."
Cliente: "Tá, com Carla mesmo"
Sistema: "Que dia prefere?"
Cliente: "Próxima terça"
Sistema: [Motor valida terça com Carla]
Sistema: "Terça às 15h com Carla, certo?"
Cliente: "Confirmo"
Sistema: ✅ Evento criado
```

---

### Exemplo 2: Errado (ANTI-PADRÃO)

```
Cliente: "Quero fazer um corte"
Sistema: ❌ "Agendei corte com Carla próxima terça às 15h"
          └─ (Sem perguntar, baseado apenas em histórico)
Cliente: "Mas eu queria com Bruna!"
         └─ Tarde demais, evento já foi criado
```

---

### Exemplo 3: Correto (Recusa)

```
Cliente: "Quero manicure"
Sistema: "Você costuma ir com Paula. Quer com ela?"
Cliente: "Não, quero com outro"
Sistema: [Limpa draft, esquece Paula]
Sistema: "Ok, qual profissional prefere?"
Cliente: "Marina"
Sistema: "Marina, certo?"
         [fluxo continua normal]
```

---

### Exemplo 4: Errado (Ignora Recusa)

```
Cliente: "Quero manicure"
Sistema: "Você costuma com Paula. Agendando com Paula"
Cliente: "Não, espera!"
Sistema: ❌ Já criou evento com Paula
         └─ Ignorou a recusa
```

---

## 🔐 CHECKLIST PARA CODE REVIEW

Quando PR envolver ClienteProfile, revisor deve validar:

- [ ] Sugestões baseadas em perfil pedem confirmação?
- [ ] Pedido explícito do cliente é respeitado?
- [ ] Dados da conversa atual sobrescrevem histórico?
- [ ] Conflitos são validados antes de sugerir?
- [ ] Recusa de sugestão limpa o draft?
- [ ] Não há criação automática baseada em recorrência aprendida?
- [ ] Motor determinístico valida sugestão antes de apresentar?
- [ ] Nenhum passo obrigatório foi pulado?
- [ ] GPT não decidiu baseado em perfil (apenas sugeriu)?
- [ ] Confirmação final antes de criar evento?

---

## 📌 CONCLUSÃO

**ClienteProfile é INFLUÊNCIA, não AUTORIDADE.**

```
Hierarquia clara:
1. Mensagem atual do cliente (máxima)
2. Histórico do cliente (contextual)
3. Defaults do sistema (mínima)

Nenhuma sugestão baseada em histórico é criada
automaticamente. Sempre exige confirmação explícita.
```

---

**Especificação criada:** 2026-06-14  
**Status:** ✅ ATIVA E OBRIGATÓRIA  
**Validade:** Permanente (até supersedida explicitamente)  
**Aplicável a:** P1.2, P1.3, P1.4 e todas as fases futuras com ClienteProfile  
