# ANÁLISE CATEGORIA C - MENSAGENS PARA REESCREVER

**Data:** 2026-06-14  
**Total de mensagens:** 5  
**Status:** Análise apenas - NÃO aplicar patch ainda  

---

## C-001: Número Inválido em Lista

| Campo | Valor |
|-------|-------|
| **Arquivo** | handlers\bot.py |
| **Linha** | 132 |
| **Função** | `tratar_mensagens_gerais()` |
| **Texto atual** | `⚠️ Número inválido. Envie apenas o número da opção listada.` |

### Por Que é Robótica/Genérica

- **Linguagem imperativa:** "Envie apenas..." soa como ordem
- **Sem contexto:** Não diz qual número é válido (esperado: 1-3, 1-5, etc)
- **Sem ajuda:** Não oferece retry ou opção alternativa
- **Sem humanização:** Mensagem técnica, não conversacional

### Proposta de Nova Mensagem

**Opção 1 (Amigável):**
```
"Que opção é essa? 😅 Envie um dos números que mostrei acima."
```

**Opção 2 (Educada):**
```
"Número não encontrado. Qual desses prefere?"
(com re-listagem das opções)
```

**Opção 3 (Contextual):**
```
"Hmm, esse número não está na lista. Tente novamente com um desses: 1, 2, 3."
```

### Risco de Alteração

**Risco:** BAIXÍSSIMO  
**Motivo:** Mensagem de validação pura, sem lógica crítica

---

## C-002: Data/Hora Não Entendida

| Campo | Valor |
|-------|-------|
| **Arquivo** | handlers\event_handler.py |
| **Linha** | 262 |
| **Função** | `add_evento_por_voz()` |
| **Texto atual** | `❌ Não entendi a data e hora. Pode tentar de outra forma?` |

### Por Que é Robótica/Genérica

- **Vago:** "De outra forma" não dá exemplos
- **Sem paciência:** Parece irritado ("Não entendi")
- **Sem ajuda:** Deveria sugerir formatos aceitos
- **Genérico:** Mesma mensagem para vários casos (data inválida, hora inválida, ambos)

### Proposta de Nova Mensagem

**Opção 1 (Exemplos):**
```
"Não captei direito a data e hora. Tenta assim: '14 de junho às 14 horas' ou '14/06 14h'"
```

**Opção 2 (Pergunta):**
```
"Qual é a data do agendamento? (tipo: amanhã, segunda, 15 de junho)"
```

**Opção 3 (Passo a passo):**
```
"Ótimo! Agora preciso de quando é esse atendimento. Qual dia você prefere?"
```

### Risco de Alteração

**Risco:** MUITO BAIXO  
**Motivo:** Apenas resposta de erro de parsing, sem fluxo crítico

---

## C-003: Nome do Cliente em Follow-up (Criação)

| Campo | Valor |
|-------|-------|
| **Arquivo** | handlers\followup_handler.py |
| **Linha** | 137 |
| **Função** | `criar_followup_por_gpt()` |
| **Texto atual** | `❌ Não entendi o nome do cliente para o follow-up.` |

### Por Que é Robótica/Genérica

- **Negativo:** "Não entendi" é desmotivador
- **Sem contexto:** Não explica o que é "follow-up"
- **Sem sugestão:** Deveria pedir de novo ou oferecer alternativa
- **Abordagem áspera:** Parece criticar o usuário, não o sistema

### Proposta de Nova Mensagem

**Opção 1 (Explicativa):**
```
"Qual é o nome do cliente que você quer acompanhar?"
```

**Opção 2 (Contexto + Pedir):**
```
"Entendi que quer criar um follow-up. Qual é o nome do cliente?"
```

**Opção 3 (Desculpe + Tente):**
```
"Desculpa, não captei o nome. Qual é o nome do cliente pra eu anotar?"
```

### Risco de Alteração

**Risco:** BAIXO  
**Motivo:** Follow-up é feature não-crítica (não afeta agenda principal)

---

## C-004: Nome do Cliente em Follow-up (Conclusão)

| Campo | Valor |
|-------|-------|
| **Arquivo** | handlers\followup_handler.py |
| **Linha** | 195 |
| **Função** | `concluir_followup_por_gpt()` |
| **Texto atual** | `❌ Não entendi o nome do cliente para concluir o follow-up.` |

### Por Que é Robótica/Genérica

- **Mesma mensagem da C-003:** Duplicação
- **Muito longa:** Pode ser encurtada
- **Passiva-agressiva:** "Não entendi" culpa o usuário
- **Sem fluxo:** Deveria propor retry ou listar clientes

### Proposta de Nova Mensagem

**Opção 1 (Ativa):**
```
"Qual cliente você quer marcar como concluído?"
```

**Opção 2 (Com opções):**
```
"Qual desses clientes você terminou o acompanhamento?"
(listar clientes com follow-ups ativos)
```

**Opção 3 (Coloquial):**
```
"Beleza, qual é o cliente que você pode marcar como pronto?"
```

### Risco de Alteração

**Risco:** BAIXO  
**Motivo:** Mesma categoria de follow-up (não-crítica)

---

## C-005: Áudio Não Entendido

| Campo | Valor |
|-------|-------|
| **Arquivo** | handlers\voice_handler.py |
| **Linha** | 22 |
| **Função** | `handle_voice()` |
| **Texto atual** | `❌ Não entendi o áudio. Pode repetir?` |

### Por Que é Robótica/Genérica

- **Muito vaga:** "Não entendi" sem motivo (voz ruim? linguagem incomum? IA falhou?)
- **Sem contexto:** Não sugere melhorar voz ou tentar texto
- **Sem paciência:** "Pode repetir?" soa impaciente
- **Sem ajuda:** Deveria oferecer alternativa (digitar ao invés de falar)

### Proposta de Nova Mensagem

**Opção 1 (Com alternativa):**
```
"Não consegui entender o áudio bem. Tenta falar de novo, ou é mais fácil você digitar?"
```

**Opção 2 (Explicativa):**
```
"A voz ficou um pouco abafada. Pode repetir um pouco mais alto?"
```

**Opção 3 (Oferecer help):**
```
"Que pena! Pode tentar falar de novo ou escrever o que quer agendar?"
```

### Risco de Alteração

**Risco:** BAIXÍSSIMO  
**Motivo:** Validação de input de voz, sem efeito em agenda

---

## RESUMO COMPARATIVO

| ID | Função | Texto Atual | Classe | Risco |
|----|--------|------|--------|-------|
| C-001 | tratar_mensagens_gerais | Número inválido... | Validação | Baixíssimo |
| C-002 | add_evento_por_voz | Não entendi data/hora... | Validação | Muito baixo |
| C-003 | criar_followup | Não entendi nome... | Feature não-crítica | Baixo |
| C-004 | concluir_followup | Não entendi nome (conclusão)... | Feature não-crítica | Baixo |
| C-005 | handle_voice | Não entendi áudio... | Validação | Baixíssimo |

---

## RECOMENDAÇÃO GERAL

**Segurança:** Todas são SEGURAS de reescrever (risco baixíssimo a baixo)

**Prioridade:** 
1. C-001, C-005 (aparecem com frequência em fluxos normais)
2. C-002 (aparece em agendamentos por voz)
3. C-003, C-004 (features menos críticas)

**Padrão observado:** Mensagens negativas com "Não entendi" → Trocar por "Qual/Que/Pode tentar"

---

## PRÓXIMOS PASSOS

- [ ] Validar propostas com time de UX
- [ ] Testar com usuários reais (A/B test se possível)
- [ ] Aplicar patch mínimo (apenas texto, sem lógica)
- [ ] Monitorar qualidade de resposta pós-alteração
- [ ] Aplicar mesmo padrão a outras mensagens similares

---

**Status:** ANÁLISE COMPLETA - AGUARDANDO APROVAÇÃO PARA PATCH

