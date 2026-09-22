# PLANO DE AÇÃO — P0 REAGENDAMENTO
**Data:** 2026-08-11  
**Objetivo:** Completar implementação de todos os 6 gates  
**Tempo total estimado:** 4-6 horas  
**Status:** 🟡 PARCIALMENTE IMPLEMENTADO (1/3)

---

## SITUAÇÃO ATUAL

### Implementado ✅

1. **Gate 1 — Detecção (100%)**
   - ✅ `eh_gatilho_reagendamento()` criada em router/principal_router.py
   - ✅ Detecta 8 variações de mensagem
   - ✅ Importada em bot.py

2. **Testes E2E (100%)**
   - ✅ TESTE_P0_REAGENDAMENTO_E2E_2026_08_11.py criado
   - ✅ 13 cenários de Gates + 1 cenário crítico
   - ✅ Pronto para executar

3. **Documentação (100%)**
   - ✅ P0_REAGENDAMENTO_GATES_E2E_2026_08_11.md (especificação)
   - ✅ P0_IMPLEMENTACAO_STATUS_2026_08_11.md (status atual)
   - ✅ Código de exemplo para Gates 2-5

### Falta Implementar ❌

1. **Gates 2-5 em bot.py (0%)**
   - ❌ Integração no fluxo de bot.py
   - ❌ Máquina de estados de fluxo
   - ❌ Integração com motor de conflito
   - ❌ Integração com alterar_agendamento()

2. **Validação (0%)**
   - ❌ Executar TESTE_P0_REAGENDAMENTO_E2E_2026_08_11.py
   - ❌ Validar 14/14 cenários passam
   - ❌ Validar regressão P0 174/174 + P1 42/42

---

## ROADMAP DETALHADO

### ETAPA 1: IMPLEMENTAR GATES 2-5 EM BOT.PY
**Tempo:** 2-3 horas  
**Prioridade:** CRÍTICA  
**Bloqueador:** Sem bloqueador, pode iniciar imediatamente

#### Tarefa 1.1: Localizar ponto de integração em bot.py
- [ ] Ler handlers/bot.py linhas 240-350
- [ ] Identificar onde adicionar detecção de reagendamento
- [ ] Mapear onde está a lógica de "aguardando_escolha_horario" existente
- [ ] Entender padrão de estado_fluxo

**Referência:**
```python
# Linha 242 em bot.py:
if eh_gatilho_agendar(mensagem):
    # Aqui entra o código de agendamento

# Próximo: Adicionar detecção de reagendamento na mesma altura
```

#### Tarefa 1.2: Implementar Gate 2 — Identificação
- [ ] Criar função auxiliar `buscar_agendamentos_cliente(user_id, dono_id)`
  - Busca eventos com status="confirmado"
  - Retorna lista com evento_id, data, hora, serviço, profissional
  
- [ ] Adicionar detecção em bot.py após linha 242:
  ```python
  if eh_gatilho_reagendamento(mensagem):
      agendamentos = await buscar_agendamentos_cliente(user_id, dono_id)
      
      if not agendamentos:
          await update.message.reply_text(...)
          raise ApplicationHandlerStop
      
      if len(agendamentos) == 1:
          # Caso 1: Identificação automática
      else:
          # Caso 2: Listar opções
  ```

- [ ] Validar: Função busca eventos corretamente
- [ ] Validar: 1 evento → identificação automática
- [ ] Validar: N eventos → lista opções

**Teste:** Testar_gate2_identificacao_um_evento() + testar_gate2_identificacao_multiplos()

#### Tarefa 1.3: Implementar Gate 3 — Novo Horário
- [ ] Adicionar estado `aguardando_novo_horario_reagendamento` em bot.py
- [ ] Quando cliente fornece horário:
  - Interpretar via GPT (usar função existente)
  - Guardar em `contexto["novo_horario"]`
  - Transicionar para estado `validando_conflito`

- [ ] Validar: Interpretação de 3 formatos diferentes
- [ ] Validar: Datas futuras são calculadas corretamente

**Teste:** testar_gate3_novo_horario()

#### Tarefa 1.4: Implementar Gate 4 — Conflito
- [ ] Adicionar estado `validando_conflito` (automático)
- [ ] Chamar `verificar_conflito_e_sugestoes_profissional()`:
  - Passar event_id para ignorar evento sendo alterado
  - Receber validação com conflito/sugestões
  
- [ ] Se SEM conflito:
  - Transicionar para `aguardando_confirmacao_reagendamento`
  - Perguntar "Confirma?"
  
- [ ] Se COM conflito:
  - Transicionar para `aguardando_escolha_horario_reagendamento`
  - Oferecer até 3 alternativas
  - Cliente escolhe número (1, 2, ou 3)

- [ ] Validar: Horário livre passa sem conflito
- [ ] Validar: Horário ocupado oferece alternativas
- [ ] Validar: Cliente pode escolher alternativa

**Teste:** testar_gate4_conflito_livre() + testar_gate4_conflito_ocupado()

#### Tarefa 1.5: Implementar Gate 5 — Confirmação
- [ ] Adicionar estado `aguardando_confirmacao_reagendamento` em bot.py
- [ ] Quando cliente responde:
  - Se `eh_confirmacao()`: proceder para alterar
  - Se `eh_desistencia_fluxo()`: cancelar (limpar contexto)
  
- [ ] Chamar `alterar_agendamento()` com:
  - event_id (preservado do contexto)
  - nova_data, nova_hora_inicio (do draft)
  - tenant_id = dono_id

- [ ] Se sucesso: responder "Pronto! Alterado." e limpar contexto
- [ ] Se falha: responder com erro

- [ ] Validar: "Sim" confirma e altera
- [ ] Validar: "Não" cancela sem alterar

**Teste:** testar_gate5_confirmacao_positiva()

#### Tarefa 1.6: Tratamento de transição automática (Gate 4)
- [ ] Implementar transição automática de `validando_conflito`
- [ ] Não requer intervenção do usuário para validar
- [ ] Após validação, enviar mensagem e aguardar próximo passo

**Código modelo:**
```python
# Transição automática (não aguarda input do user)
if ctx.get("estado_fluxo") == "validando_conflito":
    # Validar e transicionar automaticamente
    # (não usar raise ApplicationHandlerStop)
    # Passar para próximo handler
```

---

### ETAPA 2: TESTES UNITÁRIOS DOS GATES
**Tempo:** 30 minutos  
**Prioridade:** ALTA  
**Bloqueador:** Etapa 1 completa

#### Tarefa 2.1: Executar testes da Etapa 1
- [ ] Teste_gate2_identificacao_um_evento()
- [ ] Teste_gate2_identificacao_multiplos()
- [ ] Teste_gate3_novo_horario()
- [ ] Teste_gate4_conflito_livre()
- [ ] Teste_gate4_conflito_ocupado()
- [ ] Teste_gate5_confirmacao_positiva()

**Esperado:** 6/6 cenários PASS

#### Tarefa 2.2: Debug de falhas
- [ ] Se qualquer teste falhar:
  - Identificar qual gate falhou
  - Verificar estado_fluxo sendo setado
  - Verificar contexto sendo persistido
  - Verificar função de motor retorna esperado

**Referência:** P0_IMPLEMENTACAO_STATUS_2026_08_11.md (seção "O que Falta")

---

### ETAPA 3: TESTE E2E COMPLETO
**Tempo:** 1 hora  
**Prioridade:** CRÍTICA  
**Bloqueador:** Etapa 1 + 2 completas

#### Tarefa 3.1: Executar TESTE_P0_REAGENDAMENTO_E2E_2026_08_11.py
```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
python TESTE_P0_REAGENDAMENTO_E2E_2026_08_11.py
```

**Esperado:**
```
Total de testes: 30+
Passaram: 30+
Falharam: 0
Taxa de sucesso: 100%
```

#### Tarefa 3.2: Cenário crítico (máquina de estados completa)
- [ ] Teste simula fluxo completo:
  - Cliente: "Quero mudar meu horário"
  - Bot: Lista agendamentos
  - Cliente: Escolhe qual
  - Bot: Pergunta novo horário
  - Cliente: "17h"
  - Motor: Detecta conflito (se houver)
  - Bot: Oferece alternativas OU pede confirmação
  - Cliente: Escolhe alternativa OU confirma
  - Motor: Altera evento
  - Bot: Confirma alteração

- [ ] Validar cada etapa do cenário

#### Tarefa 3.3: Validar persistência
- [ ] Após teste, verificar em Firestore:
  ```
  Clientes/{tenant_id}/Eventos/{evento_id}
  ```
  - evento_id deve ser MESMO (não novo)
  - hora_inicio deve ser novo horário
  - historico_alteracoes deve ter 1+ registro
  - status deve ser "confirmado"

---

### ETAPA 4: REGRESSÃO E VALIDAÇÃO FINAL
**Tempo:** 1-2 horas  
**Prioridade:** CRÍTICA  
**Bloqueador:** Etapa 3 completa

#### Tarefa 4.1: Regressão P0 (174/174)
```bash
python TESTE_REGRESSAO_P0_2026_06_23.py
# Esperado: 174/174 PASS
```

#### Tarefa 4.2: Regressão P1 (42/42)
```bash
python TESTE_REGRESSAO_P1_2026_06_23.py
# Esperado: 42/42 PASS
```

#### Tarefa 4.3: Validação de zero regressão
- [ ] Verificar que nenhum novo teste falhou
- [ ] Verificar que nenhum novo timeout gRPC
- [ ] Verificar que Firestore está limpo de lixo de teste

#### Tarefa 4.4: Teste manual final
- [ ] Iniciar bot em homolog
- [ ] Cliente envia: "Quero remarcar"
- [ ] Bot lista agendamentos
- [ ] Cliente escolhe qual
- [ ] Bot pergunta novo horário
- [ ] Cliente responde: "Amanhã às 16h"
- [ ] Motor valida
- [ ] Bot pede confirmação (ou oferece alternativas)
- [ ] Cliente confirma: "Sim"
- [ ] Bot: "Pronto! Alterado."
- [ ] Verificar em Firebase que evento foi alterado

---

## CHECKLIST FINAL

### Gate 1 (Detecção)
- [x] Função criada em router/principal_router.py
- [x] Importada em bot.py
- [x] Testes unitários prontos
- [ ] Validado com 8/8 variações

### Gate 2 (Identificação)
- [ ] Implementado em bot.py
- [ ] Busca eventos corretamente
- [ ] Identifica automaticamente (1 evento)
- [ ] Lista opções (N eventos)
- [ ] Testes unitários PASS

### Gate 3 (Novo Horário)
- [ ] Implementado em bot.py
- [ ] Interpreta 3 formatos
- [ ] Guarda em contexto
- [ ] Testes unitários PASS

### Gate 4 (Conflito)
- [ ] Implementado em bot.py
- [ ] Transição automática funciona
- [ ] Motor validou corretamente
- [ ] Oferece alternativas se conflito
- [ ] Testes unitários PASS

### Gate 5 (Confirmação)
- [ ] Implementado em bot.py
- [ ] Bloqueio por confirmação
- [ ] Chamar alterar_agendamento()
- [ ] Limpar contexto após
- [ ] Testes unitários PASS

### Gate 6 (Persistência)
- [ ] evento_id preservado
- [ ] novo horário persistido
- [ ] histórico registrado
- [ ] status = confirmado
- [ ] Testes unitários PASS

### Teste E2E
- [ ] 14/14 cenários executados
- [ ] Cenário crítico validado
- [ ] Regressão P0 174/174 PASS
- [ ] Regressão P1 42/42 PASS
- [ ] Teste manual: ✅ PASS

---

## RECURSOS DISPONÍVEIS

### Código de Referência
```
✅ eh_gatilho_reagendamento()
✅ eh_confirmacao()
✅ eh_desistencia_fluxo()
✅ verificar_conflito_e_sugestoes_profissional()
✅ alterar_agendamento()
✅ carregar_contexto_temporario_v2()
✅ salvar_contexto_temporario_v2()
✅ limpar_contexto_agendamento()
```

### Arquivos de Suporte
- P0_REAGENDAMENTO_GATES_E2E_2026_08_11.md (especificação dos 6 gates)
- PLANO_P0_REAGENDAMENTO_CONVERSACIONAL_2026_08_11.md (plano arquitetural)
- P0_IMPLEMENTACAO_STATUS_2026_08_11.md (status atual)
- TESTE_P0_REAGENDAMENTO_E2E_2026_08_11.py (testes prontos)

### Funções Auxiliares Necessárias
```python
async def buscar_agendamentos_cliente(user_id, dono_id):
    """Buscar eventos confirmados do cliente"""
    eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos")
    # Filtrar: status="confirmado", cliente_id=user_id
    # Retornar: list com evento_id, data, hora, servico, profissional
```

---

## DEFINIÇÃO DE PRONTO

P0 REAGENDAMENTO está **PRONTO** quando:

```
✅ Gates 1-6 todos implementados
✅ TESTE_P0_REAGENDAMENTO_E2E_2026_08_11.py: 14/14 PASS
✅ Regressão P0: 174/174 PASS
✅ Regressão P1: 42/42 PASS
✅ Teste manual: funciona end-to-end
✅ Firestore: evento preserva ID, histórico registrado
✅ Documentação: atualizada com o que foi feito
```

---

## TIMELINE

| Etapa | Tempo | Status |
|-------|-------|--------|
| **1. Implementar Gates 2-5** | 2-3h | ❌ TODO |
| **2. Testes Unitários** | 30m | ❌ TODO |
| **3. Teste E2E** | 1h | ❌ TODO |
| **4. Regressão** | 1-2h | ❌ TODO |
| **TOTAL** | **4-6h** | 🟡 1/3 FEITO |

---

## PRÓXIMA AÇÃO

**👉 Implementar Tarefa 1.1: Localizar ponto de integração em bot.py**

```python
# Em handlers/bot.py, linha ~240-250, adicionar:

if eh_gatilho_reagendamento(mensagem):
    # [IMPLEMENTAR GATES 2-5 AQUI]
    pass
```

**Benefício:** Abre caminho para todas as 4 tarefas seguintes em paralelo.

---

**Data de Criação:** 2026-08-11  
**Status:** Plano de ação pronto para execução  
**Próximo:** Iniciar Etapa 1
