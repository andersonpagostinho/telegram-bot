# Plano: F3E + F3G Implementação (2026-06-28)

**Status:** PLANEJAMENTO  
**Data Início:** 2026-06-28  
**Meta:** F3E (5) + F3G (5) = 10 cenários em 34/34 PASS total  

---

## Priorização

**Ordem:** F3E ANTES de F3G

**Motivo:** Validação de catálogo é prévia à validação de datas
- Evento inválido por serviço → erro de imediato
- Evento inválido por data → erro que pode passar despercebido

---

## F3E — CATÁLOGO INCONSISTENTE (5 cenários)

### E1: Serviço Inexistente
**Descrição:** Tenta criar evento com `servico="servico_inexistente"`  
**Setup:**
- Sessão ativa: `{servico: "manicure_nao_existe", ...}`
- Tentar confirmação

**Validação:**
- ✅ Evento NÃO criado em Firestore
- ✅ Sessão preservada (não corrompida)
- ✅ Erro retornado ao usuário

**Arquivo Crítico:** `services/agenda_service.py` — função `validar_servico()` ou equivalente

---

### E2: Profissional Inexistente
**Descrição:** Tenta criar evento com profissional não cadastrado  
**Setup:**
- Sessão: `{profissional: "Pedro_Inexistente", ...}`
- Confirmar agendamento

**Validação:**
- ✅ Evento NÃO criado
- ✅ Sessão intacta
- ✅ Erro de profissional não encontrado

**Arquivo Crítico:** `services/agenda_service.py` — validação de profissional

---

### E3: Profissional Desativado
**Descrição:** Profissional foi removido do catálogo após decisão do dono  
**Setup:**
1. Criar evento com profissional ativo
2. Remover profissional do catálogo
3. Tentar criar novo evento com mesmo profissional

**Validação:**
- ✅ Primeiro evento: OK
- ✅ Segundo evento: FALHA (profissional não mais disponível)
- ✅ Sessão preservada

---

### E4: Serviço Removido (Evento Existente)
**Descrição:** Serviço foi removido mas evento anterior ainda referencia  
**Setup:**
1. Criar evento: `{servico: "limpeza", ...}`
2. Remover "limpeza" do catálogo
3. Carregar evento antigo (não deve quebrar)

**Validação:**
- ✅ Evento antigo carrega sem crash
- ✅ Sessão não corrompida
- ✅ Sistema reconhece serviço como "deletado"

---

### E5: Catálogo Vazio
**Descrição:** Nenhum serviço ou profissional disponível  
**Setup:**
- Tenant com zero serviços e zero profissionais
- Tentar iniciar agendamento

**Validação:**
- ✅ Não cria evento
- ✅ Mensagem clara: "Nenhum serviço disponível"
- ✅ Sessão preservada, fluxo pode continuar

---

## F3G — DATAS, HORÁRIOS E TIMEZONE (5 cenários)

### G1: Data Impossível
**Descrição:** Tenta agendar para 30 de fevereiro  
**Setup:**
- Entrada: `data="2026-02-30", hora="14:00"`

**Validação:**
- ✅ Evento NÃO criado
- ✅ Erro: "Data inválida"
- ✅ Sessão preservada

**Casos de teste:**
- `2026-02-30` (fevereiro)
- `2026-04-31` (abril)
- `2026-11-31` (novembro)

---

### G2: Horário Inválido
**Descrição:** Tenta agendar para `25:00` ou `14:61`  
**Setup:**
- Entrada: `hora="25:00"` ou `hora="14:61"`

**Validação:**
- ✅ Evento NÃO criado
- ✅ Erro: "Horário inválido"
- ✅ Sessão preservada

**Casos de teste:**
- `25:00`, `24:30`, `-01:00`
- `14:61`, `23:99`

---

### G3: Evento no Passado
**Descrição:** Tenta agendar para data/hora anterior a agora  
**Setup:**
- Agora: 2026-06-28 14:30 (São Paulo)
- Entrada: `data="2026-06-28", hora="10:00"` (antes de agora)

**Validação:**
- ✅ Evento NÃO criado
- ✅ Erro: "Data no passado"
- ✅ Sessão preservada

**Casos de teste:**
- Ontem
- Hoje mas hora anterior
- 1 minuto atrás

---

### G4: Timezone UTC ↔ America/Sao_Paulo
**Descrição:** Persistência e leitura com timezone correto  
**Setup:**
- Salvar evento em São Paulo: 14:30 (local)
- Verificar em Firestore: deve estar em UTC (17:30)
- Carregar e mostrar ao usuário: 14:30 (reconvertido)

**Validação:**
- ✅ Firestore armazena UTC
- ✅ Leitura reconverte para local
- ✅ Sem ambiguidade ou offset errado

**Casos de teste:**
- Horário de verão (UTC-3)
- Fora de horário de verão (UTC-2)
- Transição entre fusos

---

### G5: Meia-Noite Transição ("Amanhã" próximo a 00:00)
**Descrição:** Usuário diz "amanhã" perto de meia-noite  
**Setup:**
- Agora: 2026-06-28 23:55 (São Paulo)
- Usuário: "quero agendar para amanhã às 10:00"
- Esperado: 2026-06-29 10:00

**Validação:**
- ✅ "Amanhã" interpretado como 2026-06-29
- ✅ Não gira para dia posterior
- ✅ Evento criado corretamente

**Casos de teste:**
- 23:50 (10 min até meia-noite)
- 23:59 (1 min até meia-noite)
- 00:05 (5 min após meia-noite)

---

## Arquivos Críticos para Auditoria

### Antes de Implementação

1. **services/agenda_service.py**
   - Função: `validar_servico()`
   - Função: `validar_profissional()`
   - Função: `validar_data_hora()`

2. **services/timezone_service.py** (se existir)
   - Função: conversão UTC ↔ America/Sao_Paulo

3. **handlers/event_handler.py**
   - Onde data/hora é validada?
   - Onde timezone é aplicado?

4. **utils/data_util.py** (se existir)
   - Validação de data válida
   - Parsing de hora

---

## Validação Obrigatória

### Para Cada Cenário

1. ✅ **Setup:** Estado inicial definido
2. ✅ **Ação:** Input inválido aplicado
3. ✅ **Validação:** Comportamento correto
4. ✅ **Cleanup:** Tenant limpo (Firestore)
5. ✅ **Sessão:** Preservada ou erro claro

### Regressão Obrigatória

- **F3 Agregado:** 24/24 + 5 (F3E) + 5 (F3G) = 34/34
- **P0 Regressão:** 4/4 PASS
- **Sem nova regressão em F3C, F3D, F3B, F3A**

---

## Checklist de Implementação

### F3E
- [ ] E1: Serviço inexistente — 1/1 PASS
- [ ] E2: Profissional inexistente — 1/1 PASS
- [ ] E3: Profissional desativado — 1/1 PASS
- [ ] E4: Serviço removido — 1/1 PASS
- [ ] E5: Catálogo vazio — 1/1 PASS
- [ ] F3E isolado: 5/5 PASS
- [ ] F3 agregado: 29/29 PASS (24 + 5)
- [ ] P0 regressão: 4/4 PASS
- [ ] Documentação: `F3E_IMPLEMENTACAO_CONCLUIDA.md`

### F3G
- [ ] G1: Data impossível — 1/1 PASS
- [ ] G2: Horário inválido — 1/1 PASS
- [ ] G3: Evento no passado — 1/1 PASS
- [ ] G4: Timezone UTC ↔ São Paulo — 1/1 PASS
- [ ] G5: Meia-noite transição — 1/1 PASS
- [ ] F3G isolado: 5/5 PASS
- [ ] F3 agregado: 34/34 PASS (24 + 5 + 5)
- [ ] P0 regressão: 4/4 PASS
- [ ] Documentação: `F3G_IMPLEMENTACAO_CONCLUIDA.md`

---

## Timeline Estimada

- **F3E:** ~1-2 horas (validação de catálogo é straightforward)
- **F3G:** ~2-3 horas (timezone é complexo)
- **Regressão:** ~30 min cada
- **Total:** ~4-6 horas

---

## Próximas Fases

1. ✅ F3A (5) — COMPLETO
2. ⏳ F3E (5) — PLANEJADO
3. ⏳ F3G (5) — PLANEJADO
4. ❌ F3F (5) — APÓS F3E + F3G

**Target Final:** F3 Bloqueantes = 34/34 PASS + P0 = 4/4 PASS
