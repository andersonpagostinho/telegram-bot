# DEPLOY SEMANA 1 — FEATURE FLAG + TESTES E2E

**Data:** 2026-10-26  
**Commits:** 86ea2f4 + e95b423  
**Status:** Pronto para deploy em ambiente de teste/staging

---

## 📦 O QUE FOI ALTERADO

### Implementação (Production)
- **Arquivo:** `utils/contexto_temporario.py`
- **Mudança:** Adicionado parâmetro `permitir_fallback_legado=True` em:
  - `carregar_sessao_temporaria(actor_id, tenant_id, permitir_fallback_legado=True)`
  - `carregar_contexto_temporario_v2(dono_id, cliente_id, permitir_fallback_legado=True)`
- **Impacto:** ZERO — default=True mantém status quo (backwards compatible)

### Testes (Não Production)
- **Arquivos:** 
  - `tests/test_bloqueadores_t1_t3_contexto_legado.py` (550 linhas)
  - `tests/test_t1_t3_e2e_webhook_completo.py` (385 linhas)
- **O que testam:** Reativação após 100+ dias + isolamento multi-tenant
- **Status:** 4/4 testes passando

---

## 🚀 DEPLOY STEPS

### Pré-Deploy Checklist

```bash
# 1. Verificar commits
cd /c/dev/neoeve
git log --oneline -5
# Esperado: 
#   e95b423 test: Adicionar testes bloqueadores T1+T3 E2E webhook completo
#   86ea2f4 feat: Adicionar feature flag para desabilitar fallback legado...

# 2. Verificar que feature flag não quebrou nada
git diff 86ea2f4~1 utils/contexto_temporario.py
# Esperado: +16 linhas adicionadas, -7 removidas, default=True

# 3. Rodar testes críticos P1 (2 min)
OPENAI_API_KEY="sk-test" python -m pytest \
  tests/test_p1_9_cenarios_e2e_real.py::TestP19CenariosE2EReal::test_e2e_t2_continuacao_valida \
  tests/test_p1_9_cenarios_e2e_real.py::TestP19CenariosE2EReal::test_e2e_t3_confirmacao_explicita \
  tests/test_p1_9_cenarios_e2e_real.py::TestP19CenariosE2EReal::test_e2e_t4_alteracao_horario \
  tests/test_p1_9_cenarios_e2e_real.py::TestP19CenariosE2EReal::test_e2e_t5_escolha_profissional \
  -v
# Esperado: 4/4 PASS
```

### Deploy para Staging/Produção

```bash
# 1. Pull latest (se múltiplas máquinas)
git pull origin main

# 2. Instalar dependências (se necessário)
pip install -r requirements.txt

# 3. Validar syntax
python -m py_compile utils/contexto_temporario.py
# Esperado: Zero errors

# 4. Rodar testes bloqueadores E2E (5 min)
OPENAI_API_KEY="sk-test" python -m pytest \
  tests/test_t1_t3_e2e_webhook_completo.py -v -s
# Esperado: 2/2 PASS

# 5. Restart da aplicação (conforme seu setup)
# Exemplo (se usar systemd):
# sudo systemctl restart neoeve
# Ou se usar Docker:
# docker-compose restart web
# Ou se usar gunicorn:
# pkill -f gunicorn; gunicorn main:app &

# 6. Validar que aplicação está up
curl http://localhost:8000/health
# Ou acessar /webhook/whatsapp para validar endpoint
```

---

## ✅ TESTES PÓS-DEPLOY

### Validação Imediata (5 min)

```bash
# Rodar suite E2E completa
OPENAI_API_KEY="sk-test" python -m pytest \
  tests/test_t1_t3_e2e_webhook_completo.py \
  tests/test_p1_9_cenarios_e2e_real.py \
  -v --tb=short

# Esperado:
#   T1 E2E WEBHOOK: ✅ PASS
#   T3 E2E WEBHOOK: ✅ PASS
#   P1 T2-T5: ✅ PASS (4/4)
```

### Validação de Produção (Manual)

```
1. Enviar mensagem WhatsApp real para seu salão:
   - "quero agendar"
   - "um corte"
   - "com a Bruna"
   - "terça"
   - "confirmado"

2. Validar em Firebase Console:
   - Clientes/{tenant_id}/Sessoes/whatsapp:{wa_id}
   - Draft deve ter: servico, profissional, data_hora
   - Histórico deve crescer (nova mensagem)

3. Testar reativação (após 1 hora):
   - Deixar passar 1 hora
   - Enviar nova mensagem
   - Validar que contexto foi carregado (não perdido)

4. Testar isolamento (se múltiplos tenants):
   - Logar como tenant A
   - Agendar serviço "coloracao"
   - Logar como tenant B (mesmo wa_id)
   - Validar que não vê "coloracao" de A
```

---

## 📊 CHECKLIST PÓS-DEPLOY

- [ ] 4/4 testes críticos P1 (T2-T5) PASS
- [ ] 2/2 testes bloqueadores E2E (T1+T3) PASS
- [ ] Aplicação iniciou sem erros
- [ ] Webhook POST /webhook/whatsapp respondendo
- [ ] Firebase real carregando contexto
- [ ] Agendamento sendo criado em Firebase
- [ ] Isolamento multi-tenant validado (se múltiplos tenants)

---

## 🔄 PRÓXIMOS PASSOS

### Semana 2-3: Validação em Produção

```
☐ Monitorar logs: "Fallback legado acionado"
☐ Esperar 7 dias: Métrica = "Zero fallbacks"
☐ Rodar suite de regressão P0 completa
☐ Validar: Zero novas falhas, zero crashes
```

### Semana 4: Desabilitar Fallback

```
✅ Quando:
   - 7 dias de operação com feature flag (default=True)
   - Zero fallbacks acionados
   - Zero regressão

⏳ Action:
   - Alterar default: permitir_fallback_legado=False
   - Deploy
   - Continuar monitorando 7 dias
```

### Mês 2: Deletar Path Legado

```
✅ Quando:
   - 30 dias de operação com fallback=False
   - Zero impacto
   - Confiança total

⏳ Action:
   - Script: DELETE Clientes/{actor_id}/MemoriaTemporaria/contexto
   - Ou: Deixar expirar (TTL no Firestore)
```

---

## 🆘 TROUBLESHOOTING

### Se T1 E2E Falhar

```
❌ "Contexto dormindo 100+ dias não foi carregado"
→ Validar: Path novo vazio? Path legado tem guard?

❌ "Draft não foi preservado"
→ Validar: DELETE_FIELD não foi chamado?
→ Validar: histórico_texto ainda existe?
```

### Se T3 E2E Falhar

```
❌ "Tenant B viu contexto de Tenant A"
→ Validar: obter_id_dono retornando tenant_id correto?
→ Validar: Guard validation está ativa?

❌ "Serviço de A apareceu em B"
→ Validar: Fallback legado foi desabilitado no mock?
```

### Se Regressão P1 Falhar

```
❌ "T2-T5 falhando"
→ Revert: git revert e95b423 86ea2f4
→ Validar: Status anterior (antes dos commits)
→ Report issue
```

---

## 📝 REFERÊNCIA RÁPIDA

| Commit | O quê | Por quê |
|--------|-------|--------|
| 86ea2f4 | Feature flag `permitir_fallback_legado=True` | Desabilitar fallback de forma segura |
| e95b423 | E2E testes T1+T3 webhook | Validar reativação + isolamento antes de desabilitar |

| Teste | Valida | Status |
|-------|--------|--------|
| T1 E2E | Contexto dormindo 100+ dias | ✅ PASS |
| T3 E2E | Isolamento multi-tenant | ✅ PASS |
| P1 T2-T5 | Regressão crítica | ✅ PASS (4/4) |

---

## 🎯 OBJETIVO SEMANA 1

✅ **ALCANÇADO**
- Feature flag implementada (zero breaking changes)
- Testes bloqueadores E2E webhook (2/2 PASS)
- Regressão validada (4/4 P1 PASS)
- Pronto para Semana 2-3 (validação em produção)

**Prossiga com segurança! ✅**
