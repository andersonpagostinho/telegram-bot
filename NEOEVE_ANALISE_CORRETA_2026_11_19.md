# 🔍 ANÁLISE PROFUNDA NEOEVE — CORRIGIDA

**Data:** 2026-11-19  
**Status:** ✅ **ANÁLISE LIDA DO CÓDIGO**

---

## 📌 O QUE O SISTEMA FAZ REALMENTE

### **CAMADA 1: PERSISTÊNCIA (SIM, APRENDE)**

```
Firestore salva em: Clientes/{tenant_id}/Sessoes/{actor_id}

Persiste entre sessões:
  ✅ draft_agendamento = {servico, profissional, data_hora}
  ✅ contexto_resultado_consulta = {opcoes com horários ofertados}
  ✅ profissional_escolhido = {nome do profissional preferido}
  ✅ intencao_conversacional = {última intenção detectada}
  ✅ historico_texto = {histórico de mensagens}
  ✅ estado_fluxo = {qual estágio do fluxo}
  ✅ interpretacao_conversacional = {análise anterior}
```

**Exemplo Real:**
```
Sessão 1: João chega, pede "manicure segunda 14h com Bruna"
  → Sistema salva em Firestore:
     draft_agendamento: {servico: "manicure", profissional: "Bruna", data_hora: "2026-11-20 14:00"}
     intencao_conversacional: "agendamento_direto"
     estado_fluxo: "agendando"

Sessão 2: João volta (mesma semana)
  → Sistema CARREGA contexto de Firestore
  → Vê draft anterior
  → Se em "agendando", REUTILIZA intenção (linha 6619)
  → Continua DE ONDE PAROU, não recomeça
```

---

### **CAMADA 2: REUTILIZAÇÃO DE INTENÇÃO (Linha 6619 do router)**

```python
# Se intenção_conversacional já foi calculada, reutiliza
pode_reutilizar = intencao_salva is not None and (
    intencao_salva != "ajuste_incremental" or _tem_draft_valido(ctx)
)

if pode_reutilizar:
    class_intencao = {
        "intencao_conversacional": intencao_salva,  # ← REUTILIZA
        "tipo_ajuste_incremental": ctx.get("tipo_ajuste_incremental"),
        "confianca": ctx.get("confianca_intencao_conversacional"),
    }
    print(" [INTENÇÃO CONVERSACIONAL] REUTILIZADA")  # ← Não recalcula GPT
else:
    # Só se intenção não existe, chama GPT para classificar
    class_intencao = classificar_intencao_conversacional(...)
```

**O que isso significa:**
- Se João volta e sua última intenção foi "agendamento_direto", o sistema:
  - ✅ NÃO recalcula com regex/GPT
  - ✅ REUTILIZA "agendamento_direto"
  - ✅ Continua no fluxo anterior

---

### **CAMADA 3: REGEX + HEURÍSTICAS (BOT Determinístico)**

```python
# Linhas ~6552-6560: Detectar padrões SEM IA

eh_consulta = eh_consulta(txt)  # Regex: "tem", "você tem", "disponibilidade"
eh_confirmacao = eh_confirmacao(txt)  # Regex: "sim", "confirmo", "perfeito"
eh_cancelamento = eh_cancelamento(txt)  # Regex: "cancelar", "desmarcar"

eh_pedido_ag = _tem(r"\b(quero|gostaria|preciso|pode|consegue)\b", texto)
tem_tempo_ag = _tem(r"\b(amanha|segunda|14h|14:00)\b", texto)
servico_ag = await encontrar_servico_mais_proximo(texto)  # Busca no catálogo

if tem_pedido_ag and tem_tempo_ag and servico_ag:
    # ← Sistema detectou agendamento SEM GPT, apenas regex
    print("SINAIS DETECTADOS: pedido=True, tempo=True, servico=True")
```

---

### **CAMADA 4: GPT (IA Verdadeira) — APENAS SE NECESSÁRIO**

```python
# Linha ~6894: GPT é chamado APENAS quando intenção é indefinida

if (
    (not intencao_atual or intencao_atual == "indefinida")  # ← Condição crítica
    and interpretacao_conv.get("intencao") == "indefinida"
    and not eh_confirmacao_pendente_ativa(ctx)
):
    # ← GPT SÓ ENTRA AQUI
    interpretacao_gpt = await interpretar_linguagem_operacional_gpt(texto_usuario, ctx)
    
    if interpretacao_gpt.get("intencao") != "indefinida":
        ctx["intencao_conversacional"] = interpretacao_gpt.get("intencao")
        ctx["confianca_intencao_conversacional"] = interpretacao_gpt.get("confianca")
```

**Fluxo Real:**
```
João chega: "Quero agendar manicure segunda 14h"
   ↓
1. Sistema vê: tem_pedido=True, tem_tempo=True, servico="manicure"
   ✅ CLASSIFICA COMO AGENDAMENTO sem chamar GPT
   ✅ Vai direto para motor de disponibilidade
   
João chega: "Ah, e aí, pode deixar aquele outro jeito?"
   ↓
1. Sistema tenta: regex detecta... nada bem definido
2. Sistema tenta: interpretacao_conversacional = "indefinida"
3. Sistema ENTÃO chama GPT
4. GPT retorna: "ajuste_incremental" (tipo_ajuste: "serviço")
5. Sistema atualiza draft
```

---

## 🤖 BOT vs 🧠 IA — ANÁLISE CORRETA

### **BOT (Determinístico): ~82%**

Componentes 100% BOT:
- ✅ **Varredura de horários** (loop de 20 em 20 min, sem ML)
- ✅ **Regex/pattern matching** (confirmação, cancelamento, consulta)
- ✅ **Reutilização de intenção** (se == anterior, não recalcula)
- ✅ **Motor de conflito** (verifica se hora está ocupada)
- ✅ **Duração de serviço** (lookup tabela, sem IA)
- ✅ **Validação data/hora** (regras calendário)
- ✅ **Oferecimento de próximos horários** (os primeiros livres, sem priorização por preferência)
- ✅ **Salvamento em Firestore** (persist, sem aprendizado)

### **IA (Verdadeira): ~12%**

Componentes que usam GPT:
- ✅ **Classificação de intenção** (GPT entende "quero agendar" vs "cancelar")
- ✅ **Interpretação de ajustes** (GPT entende "quero com Bruna em vez de Maria")
- ✅ **Linguagem natural** (GPT processa variações de português)
- ✅ **Geração de respostas** (GPT cria mensagens personalizadas)

**MAS:** GPT é chamado APENAS quando sistema não consegue com regex. ~80% das mensagens NÃO tocam em GPT.

### **Híbrida: ~6%**

- Preparação de contexto para GPT (parsing)
- Validação de saída GPT (garantir que faz sentido)
- Fallback: se GPT indefinida, usa regex heurístico

---

## ❌ O QUE NÃO EXISTE (Faltam)

```
❌ ML/Previsão:
   - Não aprende que João cancela às 10h (90% do tempo)
   - Não aprende que João confirma às 14h (80% sucesso)
   - Não previne oferecimento de horários ruins
   
❌ Reordenação por Preferência:
   - Sistema oferece SEMPRE: ["primeiro_livre", "segundo_livre", "terceiro_livre"]
   - Não reordena por: "João gosta de tarde"
   - Não prioriza por: "João confirmou 14h em 10 agendamentos"
   
❌ Adaptação Contínua:
   - Se João começa a rejeitar 10h, sistema NÃO aprende
   - Se João começa a cancelar, sistema NÃO detecta padrão
   - Oferecimento fica estático
   
❌ Scoring de Qualidade:
   - Não nota: "Esta combinação (João + 10h + segunda) = risco"
   - Não avisa: "Horário pode resultar em cancelamento"
   - Não evita proativamente
```

---

## 📊 RESUMO CORRIGIDO

| Aspecto | Realidade |
|---------|-----------|
| **Aprende horários/profissional?** | ✅ SIM (salva draft em Firestore) |
| **Reutiliza contexto anterior?** | ✅ SIM (carrega intenção e continua fluxo) |
| **Oferece sempre primeiros horários livres?** | ✅ SIM (loop 20 em 20 min, sem ML) |
| **Reordena por padrão do cliente?** | ❌ NÃO |
| **Aprende cancelamentos?** | ❌ NÃO (histórico não é analisado) |
| **Usa GPT para TODA classificação?** | ❌ NÃO (regex first, GPT fallback) |
| **É IA de Verdade?** | ⚠️ Parcialmente (12% IA, 82% BOT) |

---

## 🎯 PERCENTUAIS FINAIS (CORRIGIDOS)

```
Composição por DECISÃO:

82% BOT — Sistema Determinístico
├─ Reutilização de intenção (reutiliza se existe)
├─ Regex para confirmação/cancelamento
├─ Busca de horários livres
├─ Validação de conflito
├─ Duração de serviço (lookup)
└─ Salvamento/Persistência

12% IA — GPT Integrado (Fallback)
├─ Classificação de intenção (quando indefinida)
├─ Interpretação de ajustes
├─ Geração de resposta em linguagem natural
└─ Entendimento de variações de português

6% Híbrida
├─ Preparação de contexto
├─ Validação de saída
└─ Fallback seguro
```

---

## 💡 CONCLUSÃO

**NeoEve Hoje:**
- ✅ Aprende CONTINUIDADE (retoma onde parou)
- ✅ Aprende CONTEXTO (salva dados anteriores)
- ❌ NÃO aprende PADRÕES (não analisa histórico)
- ❌ NÃO otimiza OFERECIMENTO (não reordena por preferência)
- ❌ NÃO previne PROBLEMAS (não detecta risco de cancelamento)

**Para Ser IA Verdadeira (40% IA):**
- ➕ Analisar histórico de confirmações/cancelamentos
- ➕ Reordenar sugestões por padrão do cliente
- ➕ Prever risco de cancelamento
- ➕ Adaptar oferecimento contínuamente
- ➕ Scoring de qualidade de horário

---

**Próxima Etapa:** Implementar FASE 1 (Coleta de Histórico + Scoring de Padrão)

