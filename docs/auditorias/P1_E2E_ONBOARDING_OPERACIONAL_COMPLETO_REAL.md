# P1 E2E — ONBOARDING OPERACIONAL COMPLETO (FIRESTORE REAL)

**Data:** 2026-06-21  
**Status:** 🚀 Pronto para Execução  
**Objetivo:** Validar que um dono consegue deixar NeoEve operacional apenas por conversa, sem painel externo  

---

## 🎯 OBJETIVO

Um dono novo entra no sistema e, através de conversa, consegue:
1. Criar configuração do negócio
2. Criar profissional
3. Criar serviço
4. Definir agenda
5. Aceitar cliente
6. Cliente agenda
7. Profissional consulta
8. Tudo isolado por tenant

**Sem painel externo. Sem clicks manuais. Apenas conversa.**

---

## 📊 CENÁRIOS OBRIGATÓRIOS (20/20)

### FASE 1: Identidade e Onboarding (1-10)

**1. Dono primeiro acesso inicia onboarding**
- Entrada: Primeiro contato do dono
- Esperado:
  - ✅ tenant_id criado/resolvido
  - ✅ actor_id normalizado
  - ✅ tipo_usuario=dono
  - ✅ estado_fluxo=onboarding_dono
  - ✅ onboarding_status=incompleto

**2. Coleta nome do negócio**
- Entrada: "Salão da Maria"
- Esperado:
  - ✅ Configuracao/dados_negocio.nome_negocio salvo
  - ✅ sessão avança próxima etapa
  - ✅ sessão não guarda catálogo

**3. Coleta segmento**
- Entrada: "Salão de beleza"
- Esperado:
  - ✅ segmento salvo em Configuracao
  - ✅ próxima etapa

**4. Coleta endereço**
- Entrada: "Rua João Baroni, 550"
- Esperado:
  - ✅ endereco salvo em Configuracao
  - ✅ próxima etapa

**5. Coleta agenda padrão**
- Entrada: "segunda a sábado das 8 às 18"
- Esperado:
  - ✅ agenda_padrao salva em Configuracao
  - ✅ estrutura normalizada por dia
  - ✅ próxima etapa

**6. Coleta primeiro profissional (nome)**
- Entrada: "Carla"
- Esperado:
  - ✅ draft/onboarding registra nome profissional
  - ✅ profissional ainda não criado (aguarda canal)
  - ✅ próxima etapa pede canal

**7. Coleta canal do profissional**
- Entrada: "11988887777"
- Esperado:
  - ✅ Atores/{whatsapp:11988887777} criado como profissional
  - ✅ Profissionais/{carla} criado
  - ✅ criado_por = dono_actor_id
  - ✅ canal vinculado

**8. Coleta primeiro serviço (nome)**
- Entrada: "Corte feminino"
- Esperado:
  - ✅ draft/onboarding registra serviço
  - ✅ próxima etapa pede duração
  - ✅ serviço ainda não criado

**9. Coleta duração do serviço → cria ServicosNegocio**
- Entrada: "40 minutos"
- Esperado:
  - ✅ ServicosNegocio/{corte_feminino} criado
  - ✅ Profissionais/{carla}.servicos inclui corte_feminino
  - ✅ duração = 40
  - ✅ onboarding_status=completo
  - ✅ estado_fluxo=idle
  - ✅ sistema pronto para atendimento

**10. Sessão limpa após onboarding**
- Esperado:
  - ✅ sessão não contém catálogo completo
  - ✅ sessão não contém agenda_padrao como dado permanente
  - ✅ sessão contém apenas: estado/ultima_acao/draft mínimo

### FASE 2: Operacional (11-14)

**11. Cliente novo entra após onboarding**
- Entrada: Novo cliente WhatsApp
- Esperado:
  - ✅ cliente automático criado
  - ✅ tipo_usuario=cliente
  - ✅ pode agendar serviços cadastrados

**12. Cliente confirma agendamento**
- Entrada: Confirmação de evento
- Esperado:
  - ✅ evento criado em Clientes/{tenant_id}/Eventos
  - ✅ profissional=Carla
  - ✅ serviço=Corte feminino
  - ✅ duração=40
  - ✅ cliente_id correto

**13. Profissional entra após onboarding**
- Entrada: Carla (profissional cadastrada)
- Esperado:
  - ✅ resolve como profissional
  - ✅ vê agenda própria
  - ✅ não vira cliente
  - ✅ não vê eventos de outro profissional

**14. Dono consulta agenda**
- Entrada: "agenda de amanhã"
- Esperado:
  - ✅ vê agenda completa do tenant
  - ✅ inclui eventos recém-criados
  - ✅ não vê outro tenant

### FASE 3: Robustez (15-20)

**15. Multi-tenant isolamento completo**
- Setup: Tenant A e Tenant B com donos diferentes
- Esperado:
  - ✅ cada tenant tem próprio dono
  - ✅ cada tenant tem própria Configuracao
  - ✅ eventos isolados
  - ✅ cliente de A não aparece em B

**16. Interrupção informativa durante onboarding**
- Entrada: Pergunta fora de contexto durante etapa
- Esperado:
  - ✅ responde conforme regra
  - ✅ mantém etapa atual
  - ✅ não limpa draft
  - ✅ não salva dado incorreto

**17. Entrada inválida durante onboarding**
- Entrada: "duração = um tempinho"
- Esperado:
  - ✅ não avança etapa
  - ✅ pede duração válida
  - ✅ não cria serviço incompleto

**18. Duplicidade de profissional**
- Ação: Dono tenta cadastrar Carla novamente (mesmo telefone)
- Esperado:
  - ✅ não duplica Atores
  - ✅ não duplica Profissionais
  - ✅ mantém vínculo existente

**19. Duplicidade de serviço**
- Ação: Dono tenta cadastrar Corte feminino novamente
- Esperado:
  - ✅ não duplica ServicosNegocio
  - ✅ atualiza/avisa (conforme regra)
  - ✅ não quebra catálogo

**20. Regressão P0 após instalação**
- Ação: Rodar fluxo simples: cliente → agendamento → confirmação
- Esperado:
  - ✅ P0 continua funcionando
  - ✅ conflito/disponibilidade determinísticos
  - ✅ evento criado corretamente

---

## ✅ VALIDAÇÕES POR CENÁRIO

Cada cenário valida:

| Campo | Descrição |
|-------|-----------|
| tenant_id | Identificador do tenant |
| actor_id | Ator normalizado (canal:identificador) |
| tipo_usuario | dono\|profissional\|cliente |
| canal | whatsapp, sms, email, etc |
| mensagem | Input do usuário |
| resposta | Output do sistema |
| estado_antes | Firestore antes da ação |
| estado_depois | Firestore depois da ação |
| Configuracao | Dados permanentes do negócio |
| Atores | Identidades (dono, prof, cliente) |
| Profissionais | Profissionais registrados |
| ServicosNegocio | Serviços oferecidos |
| Clientes | Cliente novo registrado |
| Eventos | Agendamentos criados |
| PASS/FAIL | Status do cenário |
| motivo_falha | Descrição de erro (se falho) |

---

## 🚀 EXECUÇÃO

### 1. Validação de Compilação

```bash
python -m py_compile tests/p1_e2e_onboarding_operacional_completo_real.py
```

**Esperado:** OK (sem errors)

### 2. Executar Bateria

```bash
python tests/p1_e2e_onboarding_operacional_completo_real.py
```

**Esperado:** 20/20 PASS

**Saída:** `tests/resultado_p1_e2e_onboarding_operacional_completo.json`

### 3. Se 20/20 PASS: Validar Regressão

```bash
# P1 E2E Identidade (deve manter 15/15)
python tests/p1_e2e_onboarding_identidade_real.py

# P0 Regressão (deve manter 174/174)
python tests/runner_p0_regressao_completa.py
```

### 4. Critério Final

| Suite | Esperado | Status |
|-------|----------|--------|
| Onboarding Operacional | 20/20 PASS | 🚀 |
| P1 E2E Identidade | 15/15 PASS | ✅ |
| P0 Regressão | 174/174 PASS | ✅ |

---

## 🔒 REGRAS OBRIGATÓRIAS

| Regra | Status |
|-------|--------|
| ✅ Firestore real | Não usar mocks |
| ✅ Sem GPT lógica crítica | Determinístico |
| ✅ Multi-tenant isolation | Clientes/{tenant_id}/... |
| ✅ Sessão ≠ Catálogo | Estado/draft apenas |
| ✅ Não alterar produção | Apenas testes |
| ✅ Documentar bugs | Antes de patch |

---

## 📝 SAÍDAS

### 1. Resultado JSON

`tests/resultado_p1_e2e_onboarding_operacional_completo.json`

```json
{
  "total": 20,
  "pass": 20,
  "fail": 0,
  "cenarios": [
    {
      "cenario": 1,
      "nome": "Dono primeiro acesso inicia onboarding",
      "status": "PASS",
      "mensagem": "",
      "detalhes": {...},
      "timestamp": "2026-06-21T19:30:00+00:00"
    },
    ...
  ]
}
```

### 2. Documentação de Auditoria

`docs/auditorias/P1_E2E_ONBOARDING_OPERACIONAL_COMPLETO_REAL.md` (este arquivo)

---

## 🎯 PRÓXIMAS AÇÕES

1. ✅ Executar: `python tests/p1_e2e_onboarding_operacional_completo_real.py`
2. ✅ Validar: 20/20 PASS
3. ✅ Regressão: P1 E2E + P0
4. ✅ Commit: Resultado final

---

## 📊 STATUS

| Componente | Status |
|-----------|--------|
| Teste criado | ✅ |
| Documentação | ✅ |
| Pronto para execução | ✅ |

---

**Objetivo:** Validar que instalação e onboarding deixam o sistema operacional.  
**Escopo:** Primeiro acesso → configuração → profissional → serviço → cliente → agendamento.  
**Critério:** 20/20 PASS + Zero regressão P0 + P1 Identidade mantém 15/15.

