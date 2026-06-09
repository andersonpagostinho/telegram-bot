# 🚨 BUG P0: Rajada Data+Hora em Confirmação Pendente

**Status:** 🔴 DOCUMENTADO - NÃO CORRIGIDO  
**Data descoberta:** 2026-06-09  
**Descoberto via:** test runner_stress_rajada_alteracao_pendente.py  
**Severidade:** P0 - Quebra fluxo crítico

---

## 📋 Descrição do Problema

Quando cliente em confirmação pendente envia rajada de alterações com **data em uma mensagem** e **hora em mensagem seguinte**, o sistema desativa a confirmação pendente e quebra o fluxo.

### Entrada (rajada):
```
1. "quero escova"        → altera serviço (corte → escova)
2. "com Gloria"          → altera profissional (Bruna → Gloria)
3. "amanhã"              → altera data (SÓ data, sem hora)
4. "às 16"               → altera hora (tenta completar)
```

### Esperado:
```
PASSO 4: "às 16"
  ✅ Reconstruir: data(amanhã) + hora(16) 
  ✅ Manter: aguardando_confirmacao_agendamento = True
  ✅ Sincronizar: draft + ctx + dados_confirmacao
  ✅ Resultado: escova + Gloria + amanhã às 16
```

### Obtido:
```
PASSO 3: "amanhã"
  ❌ Zera: ctx["data_hora"] = None
  ❌ Desativa: aguardando_confirmacao_agendamento = False
  ❌ Muda estado: aguardando_horario

PASSO 4: "às 16"
  ❌ ctx["data_hora"] é None → interpreta como hora passada
  ❌ Chama: _perguntar_amanha_mesmo_horario_e_bloquear()
  ❌ Perde: escova, Gloria, amanhã
```

---

## 🔍 Localização

**Arquivo:** `router/principal_router.py`

**Bloco problema:** Linhas 2113-2143  
```python
if alteracao.get("tipo") == "data":
    ...
    ctx["data_hora"] = None                              # ← PROBLEMA 1
    ctx["estado_fluxo"] = "aguardando_horario"          # ← PROBLEMA 2
    ctx["aguardando_confirmacao_agendamento"] = False   # ← PROBLEMA 3
```

**Cascata de falhas:**
1. **Linha 2124:** Zera `ctx["data_hora"]`
2. **Linha 2126:** Desativa `aguardando_confirmacao_agendamento`
3. **Linha 3712:** Bloco "horario passado" também zera `ctx["data_hora"]`
4. **Linha 6595-6596:** Detecta "hora passada" porque `ctx["data_hora"]` é None
5. **Linha 3712:** Chama `_perguntar_amanha_mesmo_horario_e_bloquear()` que zera tudo

---

## ⚠️ Por Que NÃO É Solução Simples

**Solução incorreta** (tentadora mas perigosa):
```python
# ❌ ERRADO: apenas manter aguardando_confirmacao_agendamento = True
ctx["aguardando_confirmacao_agendamento"] = True  # PERIGO!
```

**Risco:** Sem `ctx["data_hora"]` completa, o sistema poderia:
- Confirmar agendamento sem hora
- Confirmar com hora anterior quebrada
- Criar evento com dados incompletos

---

## ✅ Solução Correta (Não Aplicada)

Deve implementar **padrão de "data pendente"**:

### Quando usuário envia APENAS data:
```python
# Em vez de:
ctx["data_hora"] = None                     # ❌ Perde data

# Preservar como pendente:
ctx["data_hora_pendente"] = "2026-06-10"   # ✅ Mantém data
ctx["estado_fluxo"] = "aguardando_horario"
ctx["aguardando_confirmacao_agendamento"] = False  # Sai temporariamente
```

### Quando usuário envia hora (próxima mensagem):
```python
# Reconstruir data+hora:
data_pendente = ctx.get("data_hora_pendente")
hora_nova = "16:00"

if data_pendente:
    data_hora_completa = f"{data_pendente}T{hora_nova}:00"
    
    # Sincronizar draft + ctx + confirmacao
    draft["data_hora"] = data_hora_completa
    ctx["data_hora"] = data_hora_completa
    ctx["dados_confirmacao_agendamento"]["data_hora"] = data_hora_completa
    ctx["aguardando_confirmacao_agendamento"] = True
    ctx["estado_fluxo"] = "agendando"
```

---

## 🧪 Como Reproduzir

Executar:
```bash
PYTHONIOENCODING=utf-8 python tests/runner_stress_rajada_alteracao_pendente.py
```

Esperado: ✅ SUCESSO  
Obtido: ❌ FALHA com erros de data_hora

---

## 🔗 Relacionado

- [[aprendizado_p0_prioridade_dados]] — Sincronização de dados
- Bug similar: Linha 3936 (faltava sincronizar ctx["data_hora"] em alteração de hora)
  - ✅ Patch aplicado: ctx["data_hora"] = data_hora_ajustada (linha 3938)

---

## 📝 Checklist para Correção Futura

Quando corrigir, validar:

- [ ] `ctx["data_hora_pendente"]` existe quando só data é fornecida
- [ ] Próxima hora completa a data pendente
- [ ] Draft sincronizado (data_hora)
- [ ] Contexto sincronizado (data_hora)
- [ ] Confirmação sincronizada (data_hora)
- [ ] Estado correto (aguardando_confirmacao_agendamento = True quando completo)
- [ ] Teste rajada passa com 4 mensagens
- [ ] Sem evento criado prematuro
- [ ] Sincronização entre draft/ctx/confirmacao validada

---

**Última atualização:** 2026-06-09  
**Descoberto por:** stress test - rajada durante confirmação pendente  
**Prioridade:** P0 - Bloqueia fluxo crítico de agendamento
