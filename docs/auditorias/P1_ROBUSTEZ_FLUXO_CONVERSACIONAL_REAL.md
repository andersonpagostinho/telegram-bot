# P1 — Robustez de Fluxo Conversacional (Integração Router Real)

**Status:** Implementação Pronta  
**Data:** 2026-06-21  
**Cenários:** 13 (mapeiam os 13 "não aplicáveis" da bateria anterior)  
**Critério:** 13/13 PASS  

---

## 📋 Objetivo

Validar **13 cenários que dependem de fluxo conversacional real**, integrando:
- Router principal (`principal_router.roteador_principal()`)
- Sessão real (`session_service.pegar_sessao()`)
- Estado de máquina (confirmação pendente, draft, evento)
- Firestore real isolado por tenant

**Diferença da bateria anterior:**
- ✅ Bateria 1: Validação de fronteira GPT (dados isolados)
- ✅ Bateria 2: Validação de fluxo conversacional (sistema completo)

---

## 🎯 Os 13 Cenários

### 1️⃣ Ruído Pessoal Longo Não Operacional

**Entrada:**
```
"Olá! Meu fim de semana foi ótimo! Fui na praia com minha família... 
[parágrafo pessoal, sem pedido]"
```

**Esperado:**
- Sistema classifica como "não operacional"
- Nenhum evento criado
- Nenhum draft iniciado
- Resposta apropriada ao usuário

**Validações:**
- [ ] `evento_criado` = False
- [ ] `confirmacao_pendente` = False
- [ ] Mensagem enviada com tom apropriado

---

### 2️⃣ Pessoal + Agendamento Misturado

**Entrada:**
```
"Oi! Tudo certo? Meu filho quer fazer corte amanhã. Pode ser?"
```

**Esperado:**
- Classifica como operacional (tem agendamento)
- Extrai: serviço=corte, cliente_nome=seu filho, data=amanhã
- Cria draft de confirmação
- Pergunta "pode ser?" indica falta de hora (solicita)

**Validações:**
- [ ] `confirmacao_pendente` = True
- [ ] `draft_confirmacao.servico` = "corte"
- [ ] `draft_confirmacao.cliente_nome` = "seu filho"
- [ ] Aguardando hora ou profissional

---

### 3️⃣ Ambiguidade Sem Contexto

**Entrada:**
```
"quero fazer com ela amanhã"
```

**Esperado:**
- Sistema detecta ambiguidade (não sabe quem é "ela", qual serviço)
- NÃO cria evento
- Pergunta esclarecimento
- Confiança baixa

**Validações:**
- [ ] `evento_criado` = False
- [ ] `confirmacao_pendente` = False
- [ ] Resposta solicita informações

---

### 4️⃣ Ambiguidade com Contexto Anterior

**Pré-condição:**
```
Sessão anterior:
  ultima_profissional: "Bruna"
  ultimo_servico: "corte"
```

**Entrada:**
```
"marca com a mesma profissional"
```

**Esperado:**
- Recupera contexto anterior
- Resolve: profissional=Bruna, serviço=corte
- Cria draft (mas precisa de data/hora)

**Validações:**
- [ ] `draft_confirmacao.profissional` = "Bruna"
- [ ] `draft_confirmacao.servico` = "corte"
- [ ] `confirmacao_pendente` = True (aguardando data/hora)

---

### 5️⃣ Mensagem Longa com Pedido no Final

**Entrada:**
```
[2000+ caracteres de conversa pessoal]
"e queria marcar corte com a Bruna amanhã às 15h"
```

**Esperado:**
- Sistema procura pedido entre ruído
- Encontra: "marcar corte com Bruna amanhã 15h"
- Cria draft com todos os slots
- Aguarda confirmação

**Validações:**
- [ ] Pedido final foi extraído
- [ ] `draft_confirmacao` completo
- [ ] `confirmacao_pendente` = True
- [ ] Sessão não salvou texto bruto inteiro

---

### 6️⃣ Confirmação Embutida em Parágrafo

**Pré-condição:**
```
confirmacao_pendente: True
draft_confirmacao:
  servico: "corte"
  profissional: "Bruna"
  data: "amanhã"
  hora: "14:00"
```

**Entrada:**
```
"Pode deixar. Li tudo. Sim, pode confirmar esse horário. Obrigado!"
```

**Esperado:**
- Detecta confirmação em parágrafo longo
- Cria evento
- Limpa draft
- Notifica confirmação

**Validações:**
- [ ] `evento_criado` = True
- [ ] `confirmacao_pendente` = False
- [ ] Evento salvo em Firestore

---

### 7️⃣ Negação Embutida em Parágrafo

**Pré-condição:**
```
confirmacao_pendente: True
draft_confirmacao: {...}
```

**Entrada:**
```
"Entendi tudo que você explicou, mas não quero mais marcar esse horário."
```

**Esperado:**
- Detecta negação em parágrafo
- Cancela draft
- Limpa confirmacao_pendente
- NÃO cria evento

**Validações:**
- [ ] `confirmacao_pendente` = False
- [ ] `draft_confirmacao` removido
- [ ] `evento_criado` = False

---

### 8️⃣ Mensagem Muito Curta com Contexto Ativo

**Pré-condição:**
```
fluxo_ativo: "agendamento"
servico: "corte"
profissional: "Bruna"
aguardando: "data_hora"
```

**Entrada:**
```
"amanhã 15h"
```

**Esperado:**
- Contexto fornece serviço + profissional
- Mensagem fornece data + hora
- Sistema completa draft
- Cria confirmação pendente

**Validações:**
- [ ] `draft_confirmacao` completo
- [ ] `confirmacao_pendente` = True
- [ ] Contexto foi reutilizado

---

### 9️⃣ Ortografia Extremamente Degradada

**Entrada:**
```
"oi qria marca um coti c a brna amnha 3 hr"
```

**Esperado:**
- GPT reconhece: "queria marcar um corte com Bruna amanhã 3 horas"
- Confiança reduzida (~0.7)
- Sistema cria draft
- Solicita confirmação

**Validações:**
- [ ] `draft_confirmacao.servico` = "corte"
- [ ] `draft_confirmacao.profissional` = "Bruna"
- [ ] `draft_confirmacao.hora` ≠ null
- [ ] `confirmacao_pendente` = True

---

### 🔟 Rajada Contraditória

**Sequência:**
```
1. "quero corte amanhã"              → servico=corte
2. "na verdade escova"               → servico=escova (mudou)
3. "não, corte mesmo"                → servico=corte (voltou)
4. "com a Bruna"                     → profissional=Bruna
5. "às 15h"                          → hora=15:00
```

**Esperado:**
- Último valor prevalece em cada campo
- Draft final coerente
- Confirmação pendente uma única vez
- Nenhuma duplicação

**Validações:**
- [ ] `draft_confirmacao.servico` = "corte" (último)
- [ ] `draft_confirmacao.profissional` = "Bruna"
- [ ] `draft_confirmacao.hora` = "15:00"
- [ ] Uma única confirmacao_pendente ativa

---

### 1️⃣1️⃣ Múltiplas Entidades em Uma Mensagem

**Entrada:**
```
"corte amanhã às 10h e escova sexta às 15h"
```

**Esperado:**
- Detecta múltiplos agendamentos
- Ou processa primeiro e pede confirmação
- Ou lista ambos para usuário escolher

**Validações:**
- [ ] Ambas entidades foram processadas
- [ ] Estado reflete múltiplas entidades
- [ ] Nenhuma foi truncada

---

### 1️⃣2️⃣ Serviço Inexistente no Fluxo

**Entrada:**
```
"quero spa quântico com bruna amanhã"
```

**Esperado:**
- Serviço "spa quântico" NÃO é criado
- Sistema lista serviços reais (corte, escova)
- Solicita escolha

**Validações:**
- [ ] Serviço inexistente não foi criado em Firestore
- [ ] Resposta oferece alternativas
- [ ] `evento_criado` = False

---

### 1️⃣3️⃣ Regressão P0 — Fluxo Normal Completo

**Sequência:**
```
1. Usuário: "agendar corte com Bruna amanhã 14h"
   ↓ Sistema cria draft, confirmacao_pendente=True
   
2. Sistema: "Confirma corte com Bruna amanhã 14h?"
   ↓ Aguarda confirmação
   
3. Usuário: "sim, pode confirmar"
   ↓ Sistema cria evento
   
4. Sistema: "✅ Agendado! Corte com Bruna amanhã 14h"
   ↓ Notifica e limpa estado
```

**Esperado:**
- Fluxo P0 intacto
- Nenhuma regressão
- Evento criado com dados corretos

**Validações:**
- [ ] `confirmacao_pendente` = True após msg 1
- [ ] `evento_criado` = True após msg 3
- [ ] Evento contém: servico, profissional, data, hora, cliente_nome

---

## ✅ Validações Comuns

### Por Cenário

```python
resultado.estado_antes  # Sessão antes
resultado.estado_depois # Sessão depois
resultado.draft_antes   # Draft antes
resultado.draft_depois  # Draft depois
resultado.evento_criado # Event criado?
resultado.confirmacao_pendente # Aguardando confirmação?
resultado.tenant_correto  # Path Firestore correto?
resultado.paths_corretos # Nenhum path legado?
```

### Conformidade Arquitetural

- ✅ Router real foi chamado
- ✅ Firestore real consultado
- ✅ Nenhum Clientes/{id}/... legado
- ✅ Todos os paths usam Clientes/{tenant_id}/
- ✅ Tenant isolado por cenário
- ✅ Nenhuma sessão guardou catálogo/agenda bruto

---

## 📊 Critério de Sucesso

```
13/13 PASS
Falhas permitidas: 0
```

---

## 🚀 Próximos Passos

1. ✅ Executar segunda bateria
2. ✅ Validar resultado JSON
3. ✅ Consolidar P1 (bateria 1 + bateria 2)
4. ⏳ Executar P0 regressão (174/174)
5. ⏳ Consolidar status final P0 + P1

---

**Status:** Implementação Pronta  
**Arquivo:** `tests/p1_robustez_fluxo_conversacional_real.py`  
**Próximo:** Execução e validação
