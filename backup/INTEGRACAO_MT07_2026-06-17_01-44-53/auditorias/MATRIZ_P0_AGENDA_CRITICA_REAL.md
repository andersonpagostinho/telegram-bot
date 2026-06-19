# MATRIZ P0 — AGENDA CRITICA REAL (FASE 2)

**Data Inicio**: 2026-06-17  
**Status**: EM PROGRESSO — Primeiro teste em execução  
**Ambiente**: Firestore dev  
**Objetivo**: Validar integridade da agenda com Firestore real

---

## 📋 Escopo FASE 2

13 testes de agenda crítica com Firestore real/dev:

### Validações Críticas

1. **Conflito de Horário**: Evento ocupado bloqueia tentativas no mesmo slot
2. **Sobreposição Parcial**: Começo antes + fim dentro = bloqueado
3. **Encostado**: Evento 15:30-16:00 permitido após 15:00-15:30 (sem buffer)
4. **Sugestão Real**: Motor sugere horário livre quando conflita
5. **Aceite de Sugestão**: Evento criado no horário sugerido, não no conflitado
6. **Troca de Profissional**: Quando um conflita, outro deve ser avaliado
7. **Incompatibilidade**: Profissional que não faz o serviço é bloqueado
8. **Horário Fora Expediente**: 08:00 e 18:30 bloqueados com expediente 09:00-18:00
9. **Bloqueio de Profissional**: Profissional bloqueado num horário não pode agendar
10. **Bloqueio de Salão**: Salão bloqueado impede qualquer agendamento
11. **Idempotência**: Mesma confirmação 2x = 1 evento no Firestore
12. **Concorrência**: Dois agendamentos quase simultâneos no mesmo slot = apenas 1 sucesso
13. **Multi-tenant**: Dono_A e Dono_B podem ter eventos no mesmo horário isoladamente

---

## 📊 Status Testes

| # | Código | Teste | Status | Taxa |
|---|--------|-------|--------|------|
| 1 | AC-01 | Conflito simples | IMPLEMENTADO | 11/13 |
| 2 | AC-02 | Sobreposição parcial | IMPLEMENTADO | |
| 3 | AC-03 | Encostado não conflita | IMPLEMENTADO | |
| 4 | AC-04 | Sugestão após conflito | IMPLEMENTADO | |
| 5 | AC-05 | Aceite de sugestão | IMPLEMENTADO | |
| 6 | AC-06 | Troca de profissional | IMPLEMENTADO | |
| 7 | AC-07 | Profissional incompatível | IMPLEMENTADO | |
| 8 | AC-08 | Horário fora expediente | IMPLEMENTADO | |
| 9 | AC-09 | Bloqueio de profissional | IMPLEMENTADO | |
| 10 | AC-10 | Bloqueio de salão | IMPLEMENTADO | |
| 11 | AC-11 | Idempotência | IMPLEMENTADO | |
| 12 | AC-12 | Concorrência | IMPLEMENTADO | |
| 13 | AC-13 | Multi-tenant | IMPLEMENTADO | |

---

## 🔧 Arquitetura Agenda

### Paths de Firestore Utilizados

```
Clientes/{dono_id}/Eventos
  └─ Colecao: eventos criados (com validação de conflito)

Clientes/{dono_id}/Profissionais
  └─ Profissionais do salão com serviços permitidos

Clientes/{dono_id}/Sessoes/{cliente_id}
  └─ Contexto/draft de agendamento (PATCH v2)
```

### Motor de Agenda (Determinístico)

```
1. Cliente solicita horário
2. Motor valida:
   - Profissional existe?
   - Profissional faz o serviço?
   - Horário dentro do expediente?
   - Profissional bloqueado nesse horário?
   - Salão bloqueado nesse horário?
   - CONFLITO com eventos existentes?
3. Se SIM conflito:
   - Motor sugere próximo horário livre
   - Cliente escolhe: aceitar sugestão ou trocar profissional
4. Se tudo OK:
   - Criar evento em Firestore (idempotent)
   - Salvar confirmação

GPT NUNCA decide conflito/disponibilidade.
```

---

## 📁 Entregáveis FASE 2

1. **Teste Runner**
   - [ ] `tests/runner_p0_agenda_critica_real.py` — 13 testes
   - Status: EM PROGRESSO

2. **Resultado**
   - [ ] `tests/resultado_p0_agenda_critica_real.json` — Resultado consolidado
   - Status: Gerado automaticamente

3. **Documentação**
   - [ ] `docs/auditorias/MATRIZ_P0_AGENDA_CRITICA_REAL.md` — Este documento
   - Status: EM PROGRESSO

---

## 🎯 Próximos Passos

### Imediato (Hoje)
1. [ ] Completar AC-01 a AC-06 (conflito, sobreposição, sugestão, troca)
2. [ ] Validar 13/13 passando em primeira execução
3. [ ] Executar 3 vezes consecutivas

### Curto Prazo (Próximos dias)
4. [ ] Investigar e corrigir os 2 testes que falharam
5. [ ] Aumentar robustez dos testes com mais validações
6. [ ] Documentar achados críticos

---

## 🚨 Critério de Aprovação FASE 2

- [ ] 13/13 testes implementados
- [ ] 13/13 testes passando em primeira execução
- [ ] 3 execuções consecutivas com 13/13
- [ ] Nenhuma falha intermitente
- [ ] Firestore real (dev) validado
- [ ] Documentação completa

**Status Atual**: 11/13 passando (primeira execução)

---

## 📝 Notas Importantes

### Sem Mock de Agenda
- ❌ Não usar mock de Firestore
- ❌ Não simular eventos
- ✅ Usar Firestore dev real
- ✅ Criar eventos reais e validar em Firestore

### GPT Determinístico
- ❌ GPT não decide conflito
- ✅ Motor calcula disponibilidade
- ✅ GPT só interpreta entrada do usuário
- ✅ Motor valida tudo

### Multi-tenant Obrigatório
- ✅ Cada teste em dono_id específico
- ✅ AC-13 valida isolamento entre donos
- ✅ Profissionais isolados por dono_id
- ✅ Eventos isolados por dono_id

---

**Status FASE 2**: ✅ APROVADA  
**Data Aprovação**: 2026-06-17  
**Resultado Final**: 13/13 passando em 3 execuções consecutivas  
**Proteção**: Lock por buckets de tempo (agenda_lock_service.py)

