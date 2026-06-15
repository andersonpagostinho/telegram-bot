# MENSAGENS CATEGORIA B - CONFIRMAÇÕES

**Data:** 2026-06-14
**Objetivo:** Extrair 10-20 mensagens de confirmação com maior impacto visual
**Status:** Análise apenas - SEM APLICAR PATCH

---

## Mensagens de Confirmação de Agendamento (Sucesso)

| ID | Arquivo | Linha | Função | Texto Atual | Momento |
|----|---------|-------|--------|-------------|---------|
| B-001 | handlers/norm_nome.py | 955 | eh_confirmacao() | Esse horário já foi confirmado. Está tudo certo 😊 | Confirmação de horário já existente |
| B-002 | handlers/bot.py | 125 | tratar_mensagens_gerais() | ✅ Cancelamento concluído. Horário liberado. | Confirmação de cancelamento |
| B-003 | handlers/test_handler.py | 15 | testar_avisos() | ✅ Horários salvos com sucesso no Firebase! | Confirmação de salvamento de horários |
| B-004 | handlers/gpt_text_handler.py | 51 | processar_texto() | ✅ Sim, os profissionais foram importados com sucesso! | Confirmação de importação de profissionais |
| B-005 | handlers/gpt_text_handler.py | 102 | processar_texto() | ✅ Não encontrei agendamentos nesse período — está livre para marcar. | Confirmação de disponibilidade |

---

## Mensagens de Confirmação Pendente / Reagendamento

| ID | Arquivo | Linha | Função | Texto Atual | Momento |
|----|---------|-------|--------|-------------|---------|
| B-006 | handlers/bot.py | 272 | tratar_mensagens_gerais() | Tudo bem — não confirmei esse horário. | Resposta a confirmação não aceita |
| B-007 | handlers/reagendamento_handler.py | 47 | handle_resposta_reagendamento() | ❌ Não encontrei seu agendamento para mover. Pode tentar novamente mais tarde? | Erro ao processar reagendamento |
| B-008 | handlers/encaixe_handler.py | 90 | handle_pedido_encaixe() | 📨 Enviei pedido(s) de reagendamento para clientes com perfil flexível. Te aviso ao receber resposta. | Confirmação de envio de reagendamento |
| B-009 | handlers/event_handler.py | 177 | confirmar_reuniao() | ⚠️ Informe a descrição do evento para confirmar. | Pedido de informação para confirmar |

---

## Mensagens de Configuração de Horários / Avisos

| ID | Arquivo | Linha | Função | Texto Atual | Momento |
|----|---------|-------|--------|-------------|---------|
| B-010 | handlers/followup_handler.py | 222 | verificar_avisos() | ⏰ Você está usando os horários *padrão* de lembretes:\n\n• 09:00\n• 13:00\n• 17:00 | Informação de horários padrão |
| B-011 | handlers/followup_handler.py | 234 | configurar_avisos() | ⚠️ Apenas o dono pode configurar os horários de aviso. | Restrição de permissão |
| B-012 | handlers/event_handler.py | 84 | add_agenda() | ⚠️ Data ou hora em formato inválido. Use o formato 2025-03-25 14:00. | Validação de entrada de data/hora |

---

## Detalhe Completo por Mensagem

### [B-001] Confirmação de Horário Já Existente
- **Arquivo:** handlers/norm_nome.py
- **Linha:** 955
- **Função:** `eh_confirmacao()`
- **Contexto:** Fluxo de confirmação de agendamento
- **Texto Atual:**
  ```
  Esse horário já foi confirmado. Está tudo certo 😊
  ```
- **Análise:**
  - Usa emoji 😊 que pode ser informal para contextos profissionais
  - Tom positivo mas poderia ser mais profissional
  - Impacto: ALTO (confirmação positiva final)

---

### [B-002] Cancelamento Concluído
- **Arquivo:** handlers/bot.py
- **Linha:** 125
- **Função:** `tratar_mensagens_gerais()`
- **Contexto:** Fluxo de cancelamento de agendamento
- **Texto Atual:**
  ```
  ✅ Cancelamento concluído. Horário liberado.
  ```
- **Análise:**
  - Direto e operacional
  - Emoji ✅ apropriado
  - Poderia adicionar "obrigado" ou confirmação de ação futura
  - Impacto: ALTO (conclusão de ação crítica)

---

### [B-003] Horários Salvos com Sucesso
- **Arquivo:** handlers/test_handler.py
- **Linha:** 15
- **Função:** `testar_avisos()`
- **Contexto:** Confirmação de salvamento de configuração
- **Texto Atual:**
  ```
  ✅ Horários salvos com sucesso no Firebase!
  ```
- **Análise:**
  - Técnico demais (menciona "Firebase")
  - Usuário não precisa saber sobre banco de dados
  - Poderia dizer: "Horários salvos com sucesso!"
  - Impacto: MÉDIO (configuração interna)

---

### [B-004] Importação de Profissionais
- **Arquivo:** handlers/gpt_text_handler.py
- **Linha:** 51
- **Função:** `processar_texto()`
- **Contexto:** Confirmação de importação bem-sucedida
- **Texto Atual:**
  ```
  ✅ Sim, os profissionais foram importados com sucesso!
  ```
- **Análise:**
  - "Sim, os profissionais" soa redundante
  - Poderia ser: "Os profissionais foram importados com sucesso!"
  - Tom conversacional apropriado
  - Impacto: MÉDIO (operação administrativa)

---

### [B-005] Disponibilidade Confirmada
- **Arquivo:** handlers/gpt_text_handler.py
- **Linha:** 102
- **Função:** `processar_texto()`
- **Contexto:** Verificação de disponibilidade
- **Texto Atual:**
  ```
  ✅ Não encontrei agendamentos nesse período — está livre para marcar.
  ```
- **Análise:**
  - Bem estruturado
  - Oferece ação próxima ("está livre para marcar")
  - Poderia ser mais entusiasmado: "Ótimo! Está disponível para marcar."
  - Impacto: ALTO (incentiva ação)

---

### [B-006] Confirmação Não Aceita
- **Arquivo:** handlers/bot.py
- **Linha:** 272
- **Função:** `tratar_mensagens_gerais()`
- **Contexto:** Resposta quando usuário rejeita confirmação
- **Texto Atual:**
  ```
  Tudo bem — não confirmei esse horário.
  ```
- **Análise:**
  - Coloquial e natural
  - Apropriado para rejeição
  - Poderia adicionar próximo passo: "Posso ajudar com outra coisa?"
  - Impacto: ALTO (transição de estado)

---

### [B-007] Agendamento Não Encontrado
- **Arquivo:** handlers/reagendamento_handler.py
- **Linha:** 47
- **Função:** `handle_resposta_reagendamento()`
- **Contexto:** Erro ao processar reagendamento
- **Texto Atual:**
  ```
  ❌ Não encontrei seu agendamento para mover. Pode tentar novamente mais tarde?
  ```
- **Análise:**
  - Educado com "pode tentar novamente?"
  - Mas muito vago sobre o problema
  - Impacto: MÉDIO (tratamento de erro)

---

### [B-008] Reagendamento Enviado
- **Arquivo:** handlers/encaixe_handler.py
- **Linha:** 90
- **Função:** `handle_pedido_encaixe()`
- **Contexto:** Confirmação de envio de pedido de reagendamento
- **Texto Atual:**
  ```
  📨 Enviei pedido(s) de reagendamento para clientes com perfil flexível. Te aviso ao receber resposta.
  ```
- **Análise:**
  - Longo e técnico ("perfil flexível")
  - Emoji 📨 apropriado
  - Poderia simplificar: "Enviei pedidos de reagendamento. Você será avisado das respostas."
  - Impacto: ALTO (ação assíncrona importante)

---

### [B-009] Pedido de Descrição para Confirmar
- **Arquivo:** handlers/event_handler.py
- **Linha:** 177
- **Função:** `confirmar_reuniao()`
- **Contexto:** Validação antes de confirmar evento
- **Texto Atual:**
  ```
  ⚠️ Informe a descrição do evento para confirmar.
  ```
- **Análise:**
  - Direto e claro
  - Poderia ser mais gentil: "Qual é a descrição do evento?"
  - Impacto: MÉDIO (coleta de dados)

---

### [B-010] Horários Padrão de Lembretes
- **Arquivo:** handlers/followup_handler.py
- **Linha:** 222
- **Função:** `verificar_avisos()`
- **Contexto:** Informação sobre configuração padrão
- **Texto Atual:**
  ```
  ⏰ Você está usando os horários *padrão* de lembretes:

  • 09:00
  • 13:00
  • 17:00
  ```
- **Análise:**
  - Bem estruturado com emoji apropriado
  - Informativo e claro
  - Poderia ser: "Seus lembretes estão configurados para:" (sem "padrão")
  - Impacto: BAIXO (informação)

---

### [B-011] Restrição de Permissão para Avisos
- **Arquivo:** handlers/followup_handler.py
- **Linha:** 234
- **Função:** `configurar_avisos()`
- **Contexto:** Bloqueio por permissão
- **Texto Atual:**
  ```
  ⚠️ Apenas o dono pode configurar os horários de aviso.
  ```
- **Análise:**
  - Claro sobre a restrição
  - Poderia oferecer alternativa: "Peça ao dono para configurar os horários"
  - Impacto: MÉDIO (acesso negado)

---

### [B-012] Validação de Data/Hora
- **Arquivo:** handlers/event_handler.py
- **Linha:** 84
- **Função:** `add_agenda()`
- **Contexto:** Erro de formato na entrada
- **Texto Atual:**
  ```
  ⚠️ Data ou hora em formato inválido. Use o formato 2025-03-25 14:00.
  ```
- **Análise:**
  - Oferece exemplo de formato correto (bom!)
  - Mas "Use o formato" é imperativo
  - Poderia ser: "Por favor, use o formato YYYY-MM-DD HH:MM (ex: 2025-03-25 14:00)"
  - Impacto: MÉDIO (validação)

---

## Resumo por Impacto Visual

### IMPACTO ALTO (Devem ser prioritárias):
- B-001: Confirmação final de agendamento
- B-002: Cancelamento concluído
- B-005: Disponibilidade confirmada
- B-006: Rejeição de confirmação
- B-008: Reagendamento enviado

### IMPACTO MÉDIO (Secundárias):
- B-003: Salvamento de horários
- B-004: Importação de profissionais
- B-007: Agendamento não encontrado
- B-009: Pedido de descrição
- B-010: Horários padrão
- B-011: Restrição de permissão
- B-012: Validação de formato

---

## Próximos Passos

1. ✅ **Análise completa** de 12 mensagens de confirmação
2. ⏳ **Aguardando aprovação** para seleção de mensagens para humanização
3. ⏳ **Aguardando propostas** de versões humanizadas
4. ⏳ **Implementação** após aprovação

---

**Status:** Análise completa. Pronto para receber propostas de humanização.

