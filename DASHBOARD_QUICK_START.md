# 📊 Dashboard do Dono — Quick Start

**Arquivo:** `services/dashboard_service.py`  
**Feature:** F9 — Dashboard do Dono  
**Status:** ⚙️ EM DESENVOLVIMENTO  
**Progresso:** 30% (estrutura + funções vazias)

---

## 🎯 O QUE FOI CRIADO

### Estrutura Completa

✅ 6 funções públicas principais:
- `obter_resumo_hoje(tenant_id)`
- `obter_resumo_semana(tenant_id)`
- `obter_metricas_profissionais(tenant_id)`
- `obter_metricas_clientes(tenant_id)`
- `obter_metricas_servicos(tenant_id)`
- `obter_alertas_operacionais(tenant_id)`
- `obter_dashboard_completo(tenant_id)` ← Retorna tudo junto

✅ Dataclasses para estruturar retorno:
- `ResumoOperacional` — Dados de operação
- `MetricasCliente` — Dados de clientes
- `MetricasProfissional` — Dados por profissional
- `MetricasServico` — Dados por serviço
- `AlertaOperacional` — Alertas
- `DashboardCompleto` — Tudo junto

✅ 10+ funções auxiliares privadas para cálculos

---

## 🚀 COMO USAR

### Importar

```python
from services.dashboard_service import (
    obter_resumo_hoje,
    obter_resumo_semana,
    obter_metricas_profissionais,
    obter_metricas_clientes,
    obter_metricas_servicos,
    obter_alertas_operacionais,
    obter_dashboard_completo,
)
```

### Exemplo 1: Resumo do Dia

```python
# No handler ou command
resumo = await obter_resumo_hoje(tenant_id="salao_123")

print(f"""
📊 RESUMO DE HOJE
├─ Total de agendamentos: {resumo.agendamentos_total}
├─ Confirmados: {resumo.agendamentos_confirmados}
├─ Cancelados: {resumo.agendamentos_cancelados}
├─ Concluídos: {resumo.agendamentos_concluidos}
├─ Ocupação: {resumo.taxa_ocupacao:.1f}%
├─ Cancelamento: {resumo.taxa_cancelamento:.1f}%
├─ Encaixes convertidos: {resumo.encaixes_convertidos}
└─ Fila de espera: {resumo.fila_espera_ativa}
""")
```

### Exemplo 2: Métricas de Profissionais

```python
profs = await obter_metricas_profissionais(tenant_id="salao_123")

for prof in profs:
    print(f"""
👩‍💼 {prof.profissional}
├─ Atendimentos: {prof.atendimentos}
├─ Ocupação: {prof.ocupacao_percentual:.1f}%
├─ Faturamento: R$ {prof.faturamento_estimado:.2f}
├─ Cancelamentos: {prof.cancelamentos_recebidos}
├─ Taxa cancelamento: {prof.taxa_cancelamento:.1f}%
├─ Serviços top: {prof.servicos_mais_realizados}
└─ Dias sem agenda: {prof.dias_sem_agendamento}
""")
```

### Exemplo 3: Alertas Operacionais

```python
alertas = await obter_alertas_operacionais(tenant_id="salao_123")

for alerta in alertas:
    emoji = "🚨" if alerta.severidade == "critical" else "⚠️"
    print(f"""
{emoji} {alerta.tipo.upper()}
├─ {alerta.descricao}
└─ Ações: {', '.join(alerta.acoes_sugeridas[:2])}
""")
```

### Exemplo 4: Dashboard Completo

```python
dashboard = await obter_dashboard_completo(tenant_id="salao_123")

print(f"""
📱 DASHBOARD COMPLETO — {dashboard.timestamp}

HOJE:
├─ Ocupação: {dashboard.resumo_hoje.taxa_ocupacao:.1f}%
└─ Cancelamentos: {dashboard.resumo_hoje.taxa_cancelamento:.1f}%

SEMANA:
├─ Total agendamentos: {dashboard.resumo_semana.agendamentos_total}
└─ Ocupação: {dashboard.resumo_semana.taxa_ocupacao:.1f}%

CLIENTES:
├─ Novos (7 dias): {dashboard.metricas_clientes.clientes_novos_7_dias}
├─ Recorrentes: {dashboard.metricas_clientes.clientes_recorrentes}
└─ Sem retorno (90 dias): {dashboard.metricas_clientes.clientes_sem_retorno_90_dias}

PROFISSIONAIS: {len(dashboard.metricas_profissionais)}
SERVIÇOS: {len(dashboard.metricas_servicos)}
ALERTAS: {len(dashboard.alertas)}
""")
```

---

## 📋 TESTES OBRIGATÓRIOS (F9)

### F9-1: Métricas Diárias Corretas
```python
def test_f9_1_metricas_diarias():
    """Verifica se resumo_hoje calcula corretamente."""
    # Precisa:
    # - Criar agendamentos de teste para hoje
    # - Chamar obter_resumo_hoje()
    # - Validar: total, confirmados, cancelados, ocupação, etc
    pass
```

### F9-2: Ocupação Semanal Correta
```python
def test_f9_2_ocupacao_semanal():
    """Verifica se resumo_semana calcula corretamente."""
    # Precisa:
    # - Criar agendamentos de teste para semana
    # - Chamar obter_resumo_semana()
    # - Validar ocupação entre 0-100%
    pass
```

### F9-3: Faturamento por Profissional
```python
def test_f9_3_faturamento_profissional():
    """Verifica se calcula faturamento correto."""
    # Precisa:
    # - Criar agendamentos com preços
    # - Chamar obter_metricas_profissionais()
    # - Validar faturamento = soma de preços confirmados
    pass
```

### F9-4: Clientes Recorrentes
```python
def test_f9_4_clientes_recorrentes():
    """Verifica se identifica clientes recorrentes."""
    # Precisa:
    # - Criar cliente com 4+ agendamentos
    # - Chamar obter_metricas_clientes()
    # - Validar contagem correta
    pass
```

### F9-5: Alertas Operacionais
```python
def test_f9_5_alertas_operacionais():
    """Verifica se gera alertas corretos."""
    # Cenários:
    # - Ocupação < 50% → alerta "ocupacao_baixa"
    # - Cancelamento > 15% → alerta "cancelamento_alto"
    # - Profissional sem agenda > 7 dias → alerta
    pass
```

### F9-6: Isolamento Multi-Tenant
```python
def test_f9_6_isolamento_multitenant():
    """Verifica se isolamento por tenant_id funciona."""
    # Precisa:
    # - Criar dados em tenant_1
    # - Criar dados em tenant_2
    # - Chamar obter_dashboard_completo(tenant_1)
    # - Validar que NÃO retorna dados de tenant_2
    pass
```

### F9-7: Dados Vazios Não Quebram
```python
def test_f9_7_dados_vazios():
    """Verifica se funciona com Firestore vazio."""
    # Precisa:
    # - Tenant sem agendamentos
    # - Chamar todas as funções
    # - Validar que retornam estrutura vazia, não erro
    pass
```

### F9-8: Regressão P0/F3/F4/F8
```python
def test_f9_8_regressao():
    """Verifica que Dashboard não quebrou nada."""
    # Precisa:
    # - Rodar P0: 174/174 PASS
    # - Rodar F3: 39/39 PASS
    # - Rodar F4: 8/8 PASS
    # - Rodar F8: Funcional
    pass
```

---

## 🔧 PRÓXIMOS PASSOS (ESTA SEMANA)

### O que falta implementar:

1. **Funções auxiliares** — Implementar as funções privadas:
   - [ ] `_buscar_agendamentos_data()` — Usar query real do Firestore
   - [ ] `_buscar_agendamentos_periodo()` — Usar query real
   - [ ] `_buscar_fila_espera_ativa()` — Usar query real
   - [ ] Demais helpers

2. **Testes unitários** — Implementar F9 (8 testes)
   - [ ] F9-1 até F9-8

3. **Integração no bot** — Criar comando `/dashboard`
   - [ ] Handler em `handlers/bot.py`
   - [ ] Comando que chama `obter_dashboard_completo()`

4. **Validação** — Verificar que P0/F3/F4/F8 continuam 100%
   - [ ] P0: 174/174 PASS
   - [ ] F3: 39/39 PASS
   - [ ] F4: 8/8 PASS
   - [ ] F8: Funcional

---

## 📊 CHECKLIST DESTA SEMANA

```
[X] Estrutura criada: services/dashboard_service.py
[X] Funções públicas estruturadas (6)
[X] Dataclasses definidas (6)
[X] Funções auxiliares estruturadas (10+)

[ ] Implementar funções auxiliares (queries Firestore)
[ ] Criar testes F9 (8 testes)
[ ] Integrar comando /dashboard no bot
[ ] Validar regressão P0/F3/F4/F8
[ ] Documentar endpoints para API
```

---

## 🔗 REFERÊNCIAS

- **Roadmap:** `ROADMAP_OFICIAL_INTELIGENCIA.md` → P1.1
- **Progresso:** `RASTREIO_PROGRESSO_SEMANAL.md` → Semana 1
- **Status:** `STATUS_ATUAL_DEVELOPMENT.md`

---

## 💡 PRÓXIMA FASE

Quando Dashboard estiver 100% pronto (F9: 8/8):
1. Iniciar F5 (WhatsApp Adapter)
2. Iniciar Evolução F8 (múltiplos clientes)
3. Mover para Semana 2

---

**Criado:** 2026-07-01  
**Status:** 🔨 EM DESENVOLVIMENTO  
**Owner:** NeoEve Team

