# VALIDACAO: FLUXO CONVERSACIONAL COMPLETO DE REAGENDAMENTO
**Data:** 2026-08-11  
**Status:** 🟡 **EM ABERTO - GAP IDENTIFICADO**

---

## O QUE FOI IMPLEMENTADO

### ✅ Motor de Domínio
```
services/event_service_async.py:alterar_agendamento()
├─ Valida ownership
├─ Checa conflito (via motor)
├─ Altera evento (MESMO ID)
└─ Registra histórico (atômico)
```

### ✅ Testes de Domínio
```
TESTE_ALTERAR_SIMPLES_2026_08_11.py
├─ Altera evento
├─ Preserva ID
├─ Valida histórico
└─ Regressão: 37/37 PASS
```

---

## O QUE FALTA: FLUXO CONVERSACIONAL

### Arquitetura Atual
Sistema usa `estado_fluxo` para gerenciar diálogos:

```
handlers/bot.py (orquestrador principal)
├─ Detecta gatilhos (router)
├─ Gerencia estado_fluxo
└─ Roteado para handlers específicos

handlers/event_handler.py
├─ Processa agendamento
└─ Estados:
   - aguardando_escolha_horario
   - aguardando_confirmacao_cancelamento
   - etc.

handlers/acao_handler.py
├─ Processa ações específicas
└─ Inteligência de calendário
```

### GAP CRÍTICO: Reagendamento não tem fluxo

```
❌ Não existe:
- Detector "reagendamento" em principal_router
- Handler "reagendar_agendamento" 
- Estados de fluxo para reagendamento
- Integração com alterar_agendamento()
- Teste conversacional E2E
```

---

## FLUXO CONVERSACIONAL QUE FALTA

### Passo 1: Cliente Solicita Reagendamento
```
Cliente: "Quero mudar meu horário de quinta"
        ↓
GPT interpreta como "reagendamento"
        ↓
[FALTA] principal_router.eh_gatilho_reagendamento()
```

### Passo 2: Motor Identifica Agendamentos
```
[FALTA] Listar agendamentos do cliente
        ↓
Motor pergunta: "Qual agendamento? Tenho esses:"
        ↓
1. Corte - quinta 15:00
2. Escova - terça 10:00
```

### Passo 3: Cliente Escolhe Qual Alterar
```
Cliente: "O das 15 horas"
        ↓
Motor registra: contexto["agendamento_selecionado"] = EVT123
        ↓
estado_fluxo = "aguardando_novo_horario_reagendamento"
```

### Passo 4: Motor Pergunta Novo Horário
```
Motor: "Para qual horário você quer mudar?"
        ↓
Cliente: "17 horas"
        ↓
Motor valida: verificar_conflito_e_sugestoes_profissional()
```

### Passo 5: Se Disponível
```
Sem conflito:
        ↓
Motor: "Perfeito! Vou reagendar para 17h"
        ↓
alterar_agendamento(event_id, nova_data, nova_hora)
        ↓
Evento alterado + histórico registrado
```

### Passo 6: Se Ocupado
```
Conflito detectado:
        ↓
Motor: "17h está ocupado. Tenho essas opções:"
- 16:30
- 17:30
- 18:00
        ↓
Cliente: "17:30 está bom"
        ↓
Validação novamente
        ↓
alterar_agendamento()
```

---

## O QUE PRECISA SER IMPLEMENTADO

### 1. Router Principal
**Arquivo:** `router/principal_router.py`

```python
def eh_gatilho_reagendamento(mensagem: str) -> bool:
    """Detecta se cliente quer reagendar"""
    palavras_chave = [
        "reagendar", "remarcar", "mudar horário",
        "alterar horário", "trocar horário", "trocar data",
        "adiantar", "postergar", "adiar"
    ]
    msg_norm = unidecode(mensagem.lower().strip())
    return any(palavra in msg_norm for palavra in palavras_chave)
```

### 2. Handler de Reagendamento
**Arquivo:** `handlers/reagendamento_handler.py` (NOVO)

```python
async def processar_reagendamento(update, context):
    """
    Estados:
    1. "aguardando_escolha_agendamento_reagendamento"
       - Listar agendamentos do cliente
    
    2. "aguardando_novo_horario_reagendamento"
       - Pergunta novo horário
       - Valida conflito
    
    3. "aguardando_confirmacao_reagendamento"
       - Confirma alteração
       - Chama alterar_agendamento()
    """
```

### 3. Integração no Bot Principal
**Arquivo:** `handlers/bot.py`

```python
# Após detectar gatilho
if eh_gatilho_reagendamento(mensagem):
    return await processar_reagendamento(update, context)
```

### 4. Testes Conversacionais E2E
**Arquivo:** `TESTE_FLUXO_REAGENDAMENTO_E2E_2026_08_11.py` (NOVO)

```python
# Teste completo:
# Cliente: "Quero mudar meu horário"
#   ↓
# Motor: "Qual agendamento?"
#   ↓
# Cliente: "O das 15h"
#   ↓
# Motor: "Para qual horário?"
#   ↓
# Cliente: "17h"
#   ↓
# Motor: "Pronto! Alterado"
#   ↓
# Validar: evento alterado, histórico registrado
```

---

## ARQUITETURA: COMO INTEGRAR

### Fluxo Atual de Agendamento
```
Cliente → GPT (interpretação)
   ↓
principal_router (detecta ação)
   ↓
event_handler (processa agendamento)
   ↓
verificar_conflito_e_sugestoes_profissional() (valida)
   ↓
salvar_evento() (persiste)
```

### Fluxo de Reagendamento (A IMPLEMENTAR)
```
Cliente → GPT (interpretação)
   ↓
principal_router (detecta "reagendamento")
   ↓
reagendamento_handler (novo)
   ├─ Estado 1: Lista agendamentos
   ├─ Estado 2: Pergunta novo horário
   ├─ Estado 3: Valida conflito
   └─ Estado 4: Confirma
   ↓
verificar_conflito_e_sugestoes_profissional() (valida)
   ↓
alterar_agendamento() (persiste com histórico)
```

---

## RESUMO: O QUE ESTÁ FALTANDO

| Componente | Status | Impacto |
|---|---|---|
| Motor de domínio | ✅ PRONTO | alterar_agendamento() funciona |
| Detector "reagendamento" | ❌ FALTA | Router não identifica intenção |
| Handler de reagendamento | ❌ FALTA | Sem fluxo conversacional |
| Estados de fluxo | ❌ FALTA | Sem diálogo multi-passo |
| Integração com motor | ⚠️ PARCIAL | Função existe, não está conectada |
| Testes E2E | ❌ FALTA | Sem validação conversacional |
| Notificações | ❌ FALTA | Cliente não é notificado |

---

## PRÓXIMAS ETAPAS

### Prioridade Alta
1. Implementar `eh_gatilho_reagendamento()` em router
2. Criar `reagendamento_handler.py`
3. Criar testes conversacionais E2E
4. Integrar no `bot.py`

### Prioridade Média
1. Implementar notificações
2. Testar com múltiplos cenários
3. Testar com conflitos
4. Testar com sugestões

### Prioridade Baixa
1. Otimizar diálogos
2. Adicionar variações de linguagem
3. Melhorar UX

---

## CONCLUSÃO

### O que temos
✅ Motor de domínio funcional e testado  
✅ Função `alterar_agendamento()` operacional  
✅ Histórico registrado atomicamente  
✅ Validação de conflito integrada  

### O que falta
❌ Fluxo conversacional completo  
❌ Detecção de intenção "reagendamento"  
❌ Diálogo multi-passo  
❌ Testes E2E  

### Status Geral
🟡 **Motor pronto, fluxo conversacional ainda precisa ser implementado**

Esta é uma tarefa SIGNIFICATIVA que requer:
- Criação de novo handler
- Múltiplos estados de fluxo
- Integração com GPT
- Testes conversacionais
- Possível ajuste de prompts

---

**Data:** 2026-08-11  
**Validação:** Motor de domínio funciona, fluxo conversacional não.

