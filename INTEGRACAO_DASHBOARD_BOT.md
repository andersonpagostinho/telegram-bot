# 🔗 INTEGRAÇÃO DO DASHBOARD NO BOT

**Arquivo:** Modificar `handlers/bot.py`  
**Novo arquivo:** `handlers/dashboard_handler.py` ✅ (criado)  
**Status:** Pronto para integração

---

## ✅ O QUE FOI CRIADO

### `handlers/dashboard_handler.py`

**Funções:**
- ✅ `cmd_dashboard()` — `/dashboard` (completo)
- ✅ `cmd_resumo_hoje()` — `/hoje` (apenas hoje)
- ✅ `cmd_resumo_semana()` — `/semana` (apenas semana)
- ✅ `cmd_metricas_profissionais()` — `/profissionais`
- ✅ `cmd_alertas()` — `/alertas` (apenas críticos)

**Formatadores:**
- ✅ `_formatar_dashboard_completo()` — Mensagem HTML completa
- ✅ `_formatar_resumo_hoje()` — Resumo dia
- ✅ `_formatar_resumo_semana()` — Resumo semana
- ✅ `_formatar_metricas_profissionais()` — Tabela profissionais
- ✅ `_formatar_servicos_resumo()` — Top serviços
- ✅ `_formatar_alertas()` — Lista de alertas
- ✅ `_formatar_top_clientes()` — Clientes recorrentes
- ✅ `_formatar_profissionais_resumo()` — Ocupação por prof

---

## 🔧 COMO INTEGRAR NO BOT

### Passo 1: Importar

**Em `handlers/bot.py`, adicionar no topo:**

```python
# Após imports existentes

from handlers.dashboard_handler import (
    cmd_dashboard,
    cmd_resumo_hoje,
    cmd_resumo_semana,
    cmd_metricas_profissionais,
    cmd_alertas,
)
```

### Passo 2: Registrar Handlers

**Em `register_handlers()` function, adicionar:**

```python
def register_handlers(application: Application):
    logger.info("✅ Registrando handlers...")

    # ... handlers existentes ...

    # 🆕 DASHBOARD (adicionar após relatórios existentes)
    application.add_handler(CommandHandler(
        ["dashboard", "dados", "saude"],
        cmd_dashboard
    ))
    application.add_handler(CommandHandler("hoje", cmd_resumo_hoje))
    application.add_handler(CommandHandler("semana", cmd_resumo_semana))
    application.add_handler(CommandHandler("profissionais", cmd_metricas_profissionais))
    application.add_handler(CommandHandler("alertas", cmd_alertas))

    # ... resto dos handlers ...
```

---

## 📍 EXATAMENTE ONDE ADICIONAR

### Em `handlers/bot.py`, linha ~770 (relatórios):

**ANTES:**
```python
    # relatórios
    application.add_handler(CommandHandler(["relatorio_diario", "relatoriodiario"], relatorio_diario))
    application.add_handler(CommandHandler(["relatorio_semanal", "relatoriosemanal"], relatorio_semanal))
    application.add_handler(CommandHandler("enviar_relatorio_email", enviar_relatorio_email))

    # perfil/negócio
```

**DEPOIS:**
```python
    # relatórios
    application.add_handler(CommandHandler(["relatorio_diario", "relatoriodiario"], relatorio_diario))
    application.add_handler(CommandHandler(["relatorio_semanal", "relatoriosemanal"], relatorio_semanal))
    application.add_handler(CommandHandler("enviar_relatorio_email", enviar_relatorio_email))

    # 🆕 DASHBOARD DO DONO (F9)
    application.add_handler(CommandHandler(
        ["dashboard", "dados", "saude"],
        cmd_dashboard
    ))
    application.add_handler(CommandHandler("hoje", cmd_resumo_hoje))
    application.add_handler(CommandHandler("semana", cmd_resumo_semana))
    application.add_handler(CommandHandler("profissionais", cmd_metricas_profissionais))
    application.add_handler(CommandHandler("alertas", cmd_alertas))

    # perfil/negócio
```

---

## 📝 MUDANÇAS NECESSÁRIAS

### Arquivo 1: `handlers/bot.py`

```diff
+ from handlers.dashboard_handler import (
+     cmd_dashboard,
+     cmd_resumo_hoje,
+     cmd_resumo_semana,
+     cmd_metricas_profissionais,
+     cmd_alertas,
+ )

  def register_handlers(application: Application):
      # ... existentes ...

      # relatórios
      application.add_handler(CommandHandler(["relatorio_diario", "relatoriodiario"], relatorio_diario))
      application.add_handler(CommandHandler(["relatorio_semanal", "relatoriosemanal"], relatorio_semanal))
      application.add_handler(CommandHandler("enviar_relatorio_email", enviar_relatorio_email))

+     # 🆕 DASHBOARD DO DONO (F9)
+     application.add_handler(CommandHandler(
+         ["dashboard", "dados", "saude"],
+         cmd_dashboard
+     ))
+     application.add_handler(CommandHandler("hoje", cmd_resumo_hoje))
+     application.add_handler(CommandHandler("semana", cmd_resumo_semana))
+     application.add_handler(CommandHandler("profissionais", cmd_metricas_profissionais))
+     application.add_handler(CommandHandler("alertas", cmd_alertas))

      # perfil/negócio
```

### Arquivo 2: `handlers/dashboard_handler.py`

✅ **Já está criado.** Nenhuma modificação necessária.

### Arquivo 3: `services/dashboard_service.py`

✅ **Já está criado.** Nenhuma modificação necessária.

### Arquivo 4: `tests/test_f9_dashboard_do_dono.py`

✅ **Já está criado.** Nenhuma modificação necessária.

---

## 🧪 COMO TESTAR

### Teste Manual

```
1. Abrir chat do bot no Telegram
2. Digitar: /dashboard
3. Bot responde com dashboard completo

4. Digitar: /hoje
5. Bot responde com resumo do dia

6. Digitar: /alertas
7. Bot responde com alertas críticos
```

### Teste Automático

```bash
# Rodar testes F9
pytest tests/test_f9_dashboard_do_dono.py -v

# Esperado: 8/8 PASS
```

---

## 🎯 CHECKLIST DE INTEGRAÇÃO

```
[ ] Importar funções em handlers/bot.py
[ ] Adicionar imports do dashboard_handler
[ ] Adicionar CommandHandlers em register_handlers()
[ ] Testar /dashboard manualmente
[ ] Testar /hoje manualmente
[ ] Testar /semana manualmente
[ ] Testar /profissionais manualmente
[ ] Testar /alertas manualmente
[ ] Rodar testes F9 (8/8 PASS)
[ ] Validar regressão P0/F3/F4/F8
[ ] Documentar em ROADMAP_OFICIAL
```

---

## 🚀 EXEMPLO DE USO

### Usuário digita:
```
/dashboard
```

### Bot responde:
```
📊 DASHBOARD DO DONO
2026-07-01T10:30:45-03:00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 HOJE
├─ Ocupação: 72%
├─ Agendamentos: 18
│  └─ Confirmados: 16
│  └─ Cancelados: 2
├─ Taxa cancelamento: 11%
├─ Encaixes: 1
└─ Fila de espera: 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 SEMANA
├─ Total agendamentos: 95
├─ Ocupação média: 68%
├─ Taxa cancelamento: 9%
└─ Encaixes convertidos: 4

[... mais dados ...]

🚨 ALERTAS (1)
🟡 Ocupação na quarta-feira baixa (45%)
   Ações sugeridas:
   • Considerar promoção especial
   • Entrar em contato com clientes inativos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Comandos disponíveis:
/hoje — resumo de hoje
/semana — resumo da semana
/profissionais — métricas por profissional
/alertas — apenas alertas críticos
```

---

## ⚠️ IMPORTANTE

### Motor Determinístico (SEM GPT)

A interpretação do comando `/dashboard` é **100% determinística**:

```
Dono: "Quero ver os dados"
      ↓
[Motor] Não encontra comando exato
        Classifica como: "Não é comando reconhecido"
      ↓
[Bot] "Entendi que quer dados. Use /dashboard para ver relatório completo"
```

**NÃO usar GPT** para interpretar pedido de dashboard porque:
- ✅ Motor é rápido (instantâneo)
- ✅ Motor é confiável (sem erros de interpretação)
- ✅ Motor é barato (sem custo API)
- ✅ Motor é transparente (nenhuma "caixa preta")

---

## 📊 PERIODICIDADE (para depois)

**Esta semana (Semana 1):**
- ✅ Comando sob demanda (`/dashboard`)
- ✅ Sem avisos automáticos ainda

**Semana 2-3:**
- ⏳ Avisos automáticos de crises (scheduler)
- ⏳ Resumo diário (scheduler)

---

## 📋 PRÓXIMOS PASSOS

1. ✅ Integrar em `handlers/bot.py`
2. ✅ Testar manualmente no Telegram
3. ✅ Rodar testes F9 (8/8)
4. ✅ Validar regressão P0/F3/F4/F8
5. ✅ Atualizar `RASTREIO_PROGRESSO_SEMANAL.md`

---

## 🔗 ARQUIVOS RELACIONADOS

- ✅ `services/dashboard_service.py` — Implementação
- ✅ `handlers/dashboard_handler.py` — Handler
- ✅ `tests/test_f9_dashboard_do_dono.py` — Testes
- ✅ `ANALISE_AVISOS_DASHBOARD_DONO.md` — Análise
- ✅ `DASHBOARD_QUICK_START.md` — Quick start
- ✅ `RESUMO_IMPLEMENTACAO_DASHBOARD.md` — Resumo

---

**Pronto para integrar!** 🚀

