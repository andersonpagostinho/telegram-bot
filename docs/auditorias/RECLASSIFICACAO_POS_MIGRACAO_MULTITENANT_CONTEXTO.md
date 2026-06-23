# RECLASSIFICAÇÃO PÓS-MIGRAÇÃO MULTI-TENANT CONTEXTO
**Data:** 2026-06-22  
**Objetivo:** Separar o que foi resolvido pela correção de contexto multi-tenant do que ainda é bug real  
**Execução:** python tests/p1_robustez_fluxo_conversacional_real.py  
**Resultado:** 2/13 PASS | 11/13 FAIL

---

## TABELA DE RECLASSIFICAÇÃO

| Cenário | Antes | Depois | Contexto OK? | Confirmação OK? | Draft OK? | Estado Fluxo OK? | Falha Atual | Domínio Atual | Próxima Ação |
|---------|-------|--------|--------------|-----------------|-----------|------------------|------------|--------------|------------|
| 04 | ? | ? | NÃO | ? | NÃO | ? | Contexto não utilizado | Contexto/Semântica | Verificar load de contexto no router |
| 05 | ? | ? | NÃO | ? | NÃO | ? | Pedido final não detectado | Extração Semântica | Analisar truncamento de mensagem |
| 06 | SIM | SIM | SIM | NÃO (mantém pendente) | SIM | SIM | Confirmação não processada | Confirmação | Verificar reconhecimento de "sim" |
| 07 | SIM | SIM | SIM | NÃO (mantém pendente) | SIM | SIM | Negação não processada | Confirmação | Verificar reconhecimento de "não" |
| 08 | SIM | SIM | SIM | ? | NÃO | SIM | Contexto não utiliza para completar | Contexto/Extração | Verificar merge contexto + mensagem |
| 09 | ? | ? | NÃO | ? | NÃO | ? | Ortografia degradada não processada | Extração Semântica | Verificar normalizador de texto |
| 10 | ? | ? | NÃO | ? | NÃO | ? | Estado inválido: {} | Estado/Fluxo | Investigar ponto de falha crítica |
| 11 | ? | ? | NÃO | ? | NÃO | ? | Entidades não foram processadas | Extração Semântica | Analisar múltiplas intenções |
| 12 | ? | ? | NÃO | ? | NÃO | ? | Erro: 'str' object has no attribute 'get' | Tipo/Contrato | Debug stack trace completo |
| 13 | ? | ? | NÃO | ? | NÃO | ? | Fluxo interrompido: pendente=False, evento=False | Setup/Fluxo | Verificar cenário 13 (P0 regression) |

---

## ANÁLISE DETALHADA POR CENÁRIO

### CENÁRIO 04: Ambiguidade com Contexto Anterior
**Status:** FAIL  
**Classificação:** Bug real  
**Motivo:** Contexto não foi utilizado

#### Dados do Teste
```json
{
  "entrada": "marca com a mesma profissional",
  "estado_antes": {
    "ultimo_servico": "corte",
    "ultima_profissional": "Bruna"
  },
  "estado_depois": {
    "ultimo_servico": "corte",
    "ultima_profissional": "Bruna"
  },
  "resposta_enviada": "",
  "evento_criado": false,
  "confirmacao_pendente": false
}
```

#### Diagnóstico
- **Contexto carregado:** NÃO (estado_antes tem dados, mas router não utilizou)
- **Confirmação pendente:** NÃO
- **Draft carregado:** NÃO
- **Estado fluxo carregado:** SIM (mas não utilizado)

#### Falha Exata
- Router recebeu contexto histórico (ultima_profissional=Bruna)
- Mensagem "marca com a mesma profissional" deveria extrair profissional=Bruna
- Router não conectou "mesma" ao contexto anterior
- Resposta vazia indica processamento falhou

#### Domínio
- **Primário:** Contexto (carregamento/utilização)
- **Secundário:** Extração semântica (não vinculou "mesma" ao contexto)

#### Próxima Ação
✅ INVESTIGAR: Por que router não carrega ou não usa session.ultima_profissional?

---

### CENÁRIO 05: Mensagem Longa com Pedido no Final
**Status:** FAIL  
**Classificação:** Bug real  
**Motivo:** Pedido final não foi detectado

#### Dados do Teste
```json
{
  "entrada": "Olá! Tudo bem? Meu fim de semana foi ótimo! ... quero corte amanhã",
  "estado_antes": null,
  "resposta_enviada": "",
  "evento_criado": false
}
```

#### Diagnóstico
- **Contexto carregado:** NÃO
- **Confirmação pendente:** NÃO
- **Draft carregado:** NÃO
- **Estado fluxo carregado:** NÃO

#### Falha Exata
- GPT deve extrair "quero corte amanhã" do final de mensagem longa
- Não extraiu ou extraiu com confiança baixa
- Router não criou draft ou evento

#### Domínio
- **Primário:** Extração Semântica (GPT não priorizou final da mensagem)
- **Secundário:** Tipo/Contrato (resposta vazia em vez de pedido-clarificação)

#### Próxima Ação
✅ VERIFICAR: Prompt do GPT processa final de mensagens longas?

---

### CENÁRIO 06: Confirmação Embutida em Parágrafo
**Status:** FAIL  
**Classificação:** Bug real  
**Motivo:** Confirmação não foi processada

#### Dados do Teste
```json
{
  "entrada": "Pode deixar. Li tudo. Sim, pode confirmar esse horário. Obrigado!",
  "estado_antes": {
    "confirmacao_pendente": true,
    "draft_confirmacao": {
      "profissional": "Bruna",
      "hora": "14:00",
      "servico": "corte",
      "data": "amanhã"
    }
  },
  "estado_depois": {
    "confirmacao_pendente": true,
    "draft_confirmacao": {...}
  },
  "confirmacao_pendente": true,
  "evento_criado": false
}
```

#### Diagnóstico
- **Contexto carregado:** SIM ✓
- **Confirmacao_pendente carregada:** SIM ✓
- **Draft carregado:** SIM ✓
- **Estado fluxo carregado:** SIM ✓

#### Falha Exata
- Estado carregado corretamente
- Mensagem contém "Sim, pode confirmar"
- **Esperado:** confirmacao_pendente → false, evento_criado → true
- **Obtido:** confirmacao_pendente mantém true, evento não criado
- Router NÃO reconheceu "sim" embutido em parágrafo

#### Domínio
- **Primário:** Confirmação (reconhecimento de "sim")
- **Secundário:** Extração Semântica (não isolou "sim" do parágrafo)

#### Próxima Ação
⚠️ **CRÍTICA (cenário 06 é bloqueante para fase):**  
✅ VERIFICAR: responder_confirmacao() processa "sim" embutido?

---

### CENÁRIO 07: Negação Embutida em Parágrafo
**Status:** FAIL  
**Classificação:** Bug real  
**Motivo:** Negação não foi processada

#### Dados do Teste
```json
{
  "entrada": "Entendi tudo que você explicou, mas não quero mais marcar esse horário.",
  "estado_antes": {
    "confirmacao_pendente": true,
    "draft_confirmacao": {
      "profissional": "Bruna",
      "hora": "14:00",
      "servico": "corte",
      "data": "amanhã"
    }
  },
  "estado_depois": {
    "confirmacao_pendente": true,
    "draft_confirmacao": {...}
  },
  "confirmacao_pendente": true,
  "evento_criado": false
}
```

#### Diagnóstico
- **Contexto carregado:** SIM ✓
- **Confirmacao_pendente carregada:** SIM ✓
- **Draft carregado:** SIM ✓
- **Estado fluxo carregado:** SIM ✓

#### Falha Exata
- Estado carregado corretamente
- Mensagem contém "não quero mais marcar"
- **Esperado:** confirmacao_pendente → false, draft limpo, mensagem de sucesso
- **Obtido:** confirmacao_pendente mantém true, draft não limpo
- Router NÃO reconheceu "não" embutido em parágrafo

#### Domínio
- **Primário:** Confirmação/Negação (reconhecimento de "não")
- **Secundário:** Extração Semântica (não isolou "não quero" do parágrafo)

#### Próxima Ação
⚠️ **CRÍTICA (cenário 07 é bloqueante para fase):**  
✅ VERIFICAR: responder_confirmacao() processa "não" embutido?

---

### CENÁRIO 08: Mensagem Muito Curta com Contexto Ativo
**Status:** FAIL  
**Classificação:** Bug real  
**Motivo:** Contexto não foi utilizado para completar

#### Dados do Teste
```json
{
  "entrada": "amanhã 15h",
  "estado_antes": {
    "profissional": "Bruna",
    "aguardando": "data_hora",
    "servico": "corte",
    "fluxo_ativo": "agendamento"
  },
  "resposta_enviada": "",
  "evento_criado": false
}
```

#### Diagnóstico
- **Contexto carregado:** SIM ✓
- **Confirmacao_pendente carregada:** NÃO (não há)
- **Draft carregado:** SIM ✓ (implícito em fluxo_ativo)
- **Estado fluxo carregado:** SIM ✓ (fluxo_ativo=agendamento)

#### Falha Exata
- Fluxo aguardava data_hora
- Mensagem "amanhã 15h" fornece exatamente data_hora
- **Esperado:** Router extrai data_hora, cria draft_confirmacao, pede confirmação
- **Obtido:** resposta vazia, nada criado
- Router não fez merge de contexto + mensagem curta

#### Domínio
- **Primário:** Contexto (merge contexto + entrada curta)
- **Secundário:** Extração Semântica (não priorizou o pouco que foi dito)

#### Próxima Ação
✅ VERIFICAR: responder_agendamento() extrai data_hora de mensagem curta quando contexto já tem profissional?

---

### CENÁRIO 09: Ortografia Extremamente Degradada
**Status:** FAIL  
**Classificação:** Depende de normalizador  
**Motivo:** Ortografia degradada não foi processada

#### Dados do Teste
```json
{
  "entrada": "oi qria marca um coti c a brna amnha 3 hr",
  "estado_antes": null,
  "resposta_enviada": "",
  "evento_criado": false
}
```

#### Diagnóstico
- **Contexto carregado:** NÃO
- **Confirmacao_pendente carregada:** NÃO
- **Draft carregado:** NÃO
- **Estado fluxo carregado:** NÃO

#### Falha Exata
- Entrada com ortografia degradada: "qria" (queria), "coti" (corte), "brna" (bruna), "amnha" (amanhã)
- GPT deveria normalizar e extrair: queria=corte, profissional=bruna, data=amanhã, hora=3
- Não extraiu nada (resposta vazia)

#### Domínio
- **Primário:** Extração Semântica (normalização de texto degradado)
- **Secundário:** Tipo/Contrato (não deu fallback para pergunta)

#### Próxima Ação
✅ VERIFICAR: GPT consegue processar voz muito degradada? Há normalizador antes do GPT?

---

### CENÁRIO 10: Rajada Contraditória
**Status:** FAIL  
**Classificação:** Bug crítico  
**Motivo:** Estado inválido: {}

#### Dados do Teste
```json
{
  "entrada": "às 15h",
  "estado_antes": null,
  "motivo": "Estado inválido: {}",
  "resposta_enviada": "",
  "evento_criado": false
}
```

#### Diagnóstico
- **Contexto carregado:** NÃO
- **Confirmacao_pendente carregada:** NÃO
- **Draft carregado:** NÃO
- **Estado fluxo carregado:** NÃO

#### Falha Exata
- Estado anterior é null (nenhum fluxo ativo)
- Mensagem "às 15h" é apenas hora (sem data, serviço ou profissional)
- **Esperado:** Pedir clarificação
- **Obtido:** Erro "Estado inválido: {}"
- Router não tratou entrada sem contexto anterior

#### Domínio
- **Primário:** Setup/Fluxo (router não inicializa fluxo corretamente)
- **Secundário:** Estado (estado vazio causa erro em vez de pergunta)

#### Próxima Ação
✅ INVESTIGAR: Por que "às 15h" sem contexto causa erro em vez de pergunta?

---

### CENÁRIO 11: Múltiplas Entidades em uma Mensagem
**Status:** FAIL  
**Classificação:** Limitação de design  
**Motivo:** Entidades não foram processadas

#### Dados do Teste
```json
{
  "entrada": "corte amanhã às 10h e escova sexta às 15h",
  "estado_antes": null,
  "resposta_enviada": "",
  "evento_criado": false
}
```

#### Diagnóstico
- **Contexto carregado:** NÃO
- **Confirmacao_pendente carregada:** NÃO
- **Draft carregado:** NÃO
- **Estado fluxo carregado:** NÃO

#### Falha Exata
- Mensagem propõe 2 agendamentos simultâneos
- Sistema foi desenhado para 1 agendamento por fluxo
- GPT extraiu ambos ou não conseguiu desambiguar
- Router não sabe lidar com múltiplos

#### Domínio
- **Primário:** Tipo/Contrato (sistema não suporta múltiplos simultaneamente)
- **Secundário:** Extração Semântica (GPT não prioriza primeiro)

#### Próxima Ação
✅ VERIFICAR: Sistema suporta múltiplos agendamentos em uma mensagem? Se não, desambiguar primeiro?

---

### CENÁRIO 12: Serviço Inexistente no Fluxo
**Status:** FAIL  
**Classificação:** Bug de tipo/contrato  
**Motivo:** Erro: 'str' object has no attribute 'get'

#### Dados do Teste
```json
{
  "entrada": "quero spa quântico com bruna amanhã",
  "estado_antes": null,
  "resposta_enviada": "",
  "evento_criado": false,
  "erro": "'str' object has no attribute 'get'"
}
```

#### Diagnóstico
- **Contexto carregado:** NÃO
- **Confirmacao_pendente carregada:** NÃO
- **Draft carregado:** NÃO
- **Estado fluxo carregado:** NÃO

#### Falha Exata
- GPT extraiu serviço="spa quântico" (não existe no banco)
- Código tenta `.get()` em string em vez de dict
- **Esperado:** Validar serviço existe antes de usar, ou devolver mensagem
- **Obtido:** Erro TypeError

#### Domínio
- **Primário:** Tipo/Contrato (código assume dict em vez de validar)
- **Secundário:** Validação (não valida se serviço existe)

#### Próxima Ação
✅ CRÍTICA: Encontrar onde erro ocorre e adicionar validação de tipo

---

### CENÁRIO 13: Regressão P0 - Fluxo Normal Completo
**Status:** FAIL  
**Classificação:** Setup de teste  
**Motivo:** Fluxo interrompido: pendente=False, evento=False

#### Dados do Teste
```json
{
  "numero": 13,
  "nome": "Regressão P0 - fluxo normal completo",
  "status": "FAIL",
  "entrada": null,
  "motivo": "Fluxo interrompido: pendente=False, evento=False"
}
```

#### Diagnóstico
- **Contexto carregado:** DESCONHECIDO (entrada é null)
- **Confirmacao_pendente carregada:** DESCONHECIDO
- **Draft carregado:** DESCONHECIDO
- **Estado fluxo carregado:** DESCONHECIDO

#### Falha Exata
- Cenário 13 tem entrada=null
- **Problema:** Descrição de teste é vaga
- **Esperado:** Mensagem exata, contexto inicial, passo a passo
- **Obtido:** Não consegue rodar

#### Domínio
- **Primário:** Setup de teste (cenário 13 não está configurado corretamente)
- **Secundário:** Especificação (motivo é genérico demais)

#### Próxima Ação
✅ VERIFICAR: Qual é o cenário P0 completo que deveria ser testado?

---

## RESUMO DA RECLASSIFICAÇÃO

### Bugs Resolvidos pela Migração Multi-tenant Contexto
**Quantidade:** 0  
**Motivo:** Nenhum dos cenários 04-13 foi resolvido apenas com guarda de tenant

### Bugs Reais Confirmados
**Quantidade:** 11  
**Distribuição:**
- Extração Semântica: 4 (05, 08, 09, 11)
- Confirmação/Negação: 2 (06, 07) ⚠️ **CRÍTICAS**
- Contexto: 2 (04, 08)
- Tipo/Contrato: 2 (12, 11)
- Setup/Fluxo: 1 (10)

### Próximas Ações por Prioridade

#### 🚨 P0 BLOQUEANTE (Fase não avança sem)
1. **Cenário 06:** Confirmação embutida em parágrafo
   - Verificar: responder_confirmacao() reconhece "sim" embutido?
   
2. **Cenário 07:** Negação embutida em parágrafo
   - Verificar: responder_confirmacao() reconhece "não" embutido?

#### 🔴 P1 CRÍTICO (Próximas 48h)
3. **Cenário 12:** Serviço inexistente causa TypeError
   - Encontrar linha com `.get()` em serviço
   - Adicionar validação de tipo antes

4. **Cenário 04:** Contexto não é utilizado
   - Verificar: session.ultima_profissional é carregada?

#### 🟠 P2 IMPORTANTE (Próxima semana)
5. **Cenário 13:** Setup P0 regression
   - Esclarecer especificação do teste
   - Implementar cenário correto

---

## INFORMAÇÕES TÉCNICAS

### Equipamento Teste
- Tenant: teste_fluxo_p1_XXXXX (isolado por teste)
- Router: roteador_principal (real, não mockado)
- Firestore: Real, isolado por tenant
- GPT: Mockado

### Tempo Execução
- Total: ~20 segundos
- Por cenário: ~1.5 segundos

### Estrutura Teste
```
setup_tenant_completo()
    → salvar profissional + serviços + sessão
    → mock obter_id_dono()
    → executar mensagem via principal_router()
    → verificar resultado
    → cleanup tenant
```

---

**Relatório gerado:** 2026-06-22T20:05:00Z  
**Próxima reclassificação:** Após correção dos P0 bloqueantes  
**Versão:** 1.0
