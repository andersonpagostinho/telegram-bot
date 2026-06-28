# F1-04 — Auditoria Prévia: Reativação Manual

**Data:** 2026-06-28  
**Escopo:** Sugerir reativação de clientes inativos (SEM enviar mensagens)

---

## 📍 Ponto 1: Impacto em F1-01 (Estado do Lead)

### Verificação

F1-01 implementou:
- `lead_status` com 7 estados: novo, interessado, negociacao, agendado, atendido, retorno_pendente, inativo
- Transições determinísticas
- Auditoria de mudanças

### Impacto de F1-04

**ZERO impacto:**
- F1-04 apenas LEITURA de lead_status
- F1-04 não modifica lead_status
- F1-04 não altera transições
- F1-04 não afeta campos de F1-01

**Risco:** Nenhum

---

## 📍 Ponto 2: Impacto em F1-02 (Backlog Comercial)

### Verificação

F1-02 implementou:
- `listar_por_status()`
- `listar_interessados_sem_agendamento()`
- `listar_clientes_em_negociacao()`
- `listar_retorno_pendente()`
- `listar_clientes_inativos()`
- `gerar_resumo_comercial()`

### Impacto de F1-04

**EXTENSÃO compatível:**
- F1-04 reusa `listar_clientes_inativos()` de F1-02
- F1-04 reusa conceito de `resumo_comercial()`
- F1-04 adiciona formatação com sugestões (texto humanizado)
- F1-04 não altera lógica de F1-02

**Integração:**
- F1-02 lista clientes inativos
- F1-04 lista inativos + sugestões de reativação

**Risco:** Baixo (apenas read + formatação)

---

## 📍 Ponto 3: Impacto em F1-03 (Retorno Pendente)

### Verificação

F1-03 implementou:
- `verificar_retorno_pendente()` com regra temporal
- `atualizar_retorno_pendente_tenant()` batch
- `listar_clientes_retorno_pendente()` com verificação
- `recuperar_de_retorno_pendente()` transição

### Impacto de F1-04

**ZERO impacto:**
- F1-04 apenas lista retorno_pendente
- F1-04 não dispara verificação
- F1-04 não faz transição
- F1-04 não afeta batch processing

**Risco:** Nenhum

---

## 📍 Ponto 4: Campos Disponíveis para F1-04

### Path
`Clientes/{tenant_id}/Clientes/{cliente_actor_id}`

### Campos Utilizados

Já existentes em F1-01:
```
lead_status: string (7 valores)
ultima_interacao: ISO timestamp
ultimo_atendimento: ISO timestamp (nullable)
primeira_interacao: ISO timestamp
total_agendamentos: integer
```

Também consultáveis:
```
nome_detectado: string
canal: string
identificador: string
primeira_interacao: ISO timestamp
criado_em: ISO timestamp
```

**Status:** [CONFIRMADO] Todos campos já existem

---

## 📍 Ponto 5: Regra de Inatividade

### Definição

Cliente inativo SE:
```
lead_status == "inativo"
OU
(hoje - ultima_interacao) > 30 dias
```

### Não Enviar Mensagens

**PROIBIDO:**
- ❌ WhatsApp automático
- ❌ Email automático
- ❌ Notificação automática
- ❌ Campanha automática
- ❌ FollowUp automático

**PERMITIDO:**
- ✅ Dono visualiza lista
- ✅ Dono vê sugestões
- ✅ Dono clica "Entrar em contato" (ação manual)

---

## 📍 Ponto 6: Impacto em Agenda/Conflito/Disponibilidade

### Verificação

Agenda depende de:
- Profissional disponível
- Slot sem conflito
- Duração configurada

F1-04 não toca em nada disso.

**Risco:** Nenhum

---

## 📍 Ponto 7: Impacto em Sessões/MemoriaTemporaria

### Verificação

F1-04 apenas lê Firestore, não escreve em:
- Sessões
- MemoriaTemporaria
- Cache local
- Contexto temporário

**Risco:** Nenhum

---

## 📍 Ponto 8: Impacto em ClienteProfile

### Verificação

ClienteProfile é metadata histórica, não decisória.

F1-04 não altera ClienteProfile.

F1-04 apenas lê ultima_interacao, numero de agendamentos.

**Risco:** Nenhum

---

## 📍 Ponto 9: Uso de GPT

### PROIBIDO:

❌ Decidir prioridade de reativação
❌ Escolher quais clientes contactar
❌ Definir urgência
❌ Gerar campanhas

### PERMITIDO:

✅ Opcionalmente formatar texto para exibição
✅ Se usado, deve ser apenas estético
✅ Seleção dos clientes SEMPRE em código

---

## 📊 Sumário de Impacto

### Arquivos a Criar

1. **services/reativacao_manual_service.py** (NOVO)
   - Lógica de listagem e sugestões
   - Formatação de dados

2. **tests/test_f1_04_reativacao_manual_firebase_real.py** (NOVO)
   - 11 testes Firebase

### Arquivos a Modificar

**NENHUM**

F1-04 é completamente isolado:
- Não modifica F1-01
- Não modifica F1-02
- Não modifica F1-03
- Não modifica handlers
- Não modifica routers
- Não modifica agenda

### Arquivos NÃO a Modificar

✅ Intocados:
- lead_status_service (F1-01)
- backlog_comercial_service (F1-02)
- retorno_pendente_service (F1-03)
- bot.py, principal_router.py
- agenda, conflito, disponibilidade
- Sessões, MemoriaTemporaria

---

## 🚨 Validações Críticas

1. **Nenhuma escrita em Firestore**
   - F1-04 apenas lê
   - ✅ Verificar no código-fonte

2. **Nenhuma mensagem automática**
   - Sem WhatsApp
   - Sem Email
   - Sem notificação
   - ✅ Verificar no código-fonte

3. **Nenhuma decisão por IA**
   - Seleção é em código
   - ✅ Verificar no código-fonte

4. **Multi-tenant isolado**
   - tenant_id_guard em cada query
   - ✅ Verificar no código-fonte

---

**Próximo passo:** Implementar reativacao_manual_service.py + testes
