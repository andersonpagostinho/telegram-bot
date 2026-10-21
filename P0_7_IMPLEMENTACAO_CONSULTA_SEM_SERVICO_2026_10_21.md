# 🔧 P0.7 — CORREÇÃO MÍNIMA: Rejeição Indevida de Consultas de Disponibilidade

## 📋 RESUMO

**Problema:** Consultas informacionais sem serviço específico (ex: "Tem horário para hoje às 15 com a Bruna?") eram rejeitadas como inválidas.

**Causa raiz:** Validador em `router/principal_router.py` (linhas 5463-5469) exigia serviço válido mesmo para consultas, sem diferenciar `intencao="consulta"` de `intencao="agendamento_direto"`.

**Solução:** Bifurcar tratamento — se `intencao="consulta"`, permitir e reutilizar infraestrutura existente de `consulta_disponibilidade_aberta`.

**Resultado:** ✅ 7/7 testes focados PASS, nenhuma regressão, escopo mínimo.

---

## 🎯 VERIFICAÇÃO PRÉ-IMPLEMENTAÇÃO

### Checklist de Contrato

- ✅ `salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)` — aceita dict, salva em Firebase
- ✅ `interpretacao_gpt["entidades"]` — estrutura: `{profissional, data, horario, servico}`
- ✅ `intencao_conversacional="consulta_disponibilidade_aberta"` → objetivo = `"descobrir_servico_para_consulta"`
- ✅ Handler de `descobrir_servico_para_consulta` (linhas 323-329) já sabe perguntar por serviço
- ✅ Handler `perguntar_servico` (linhas 413-464) preserva contexto na pergunta

### Handlers Reutilizados

| Handler | Localização | Função |
|---------|------------|--------|
| `descobrir_servico_para_consulta` | Linhas 323-329 | Determina próximo passo quando faltam dados |
| `perguntar_servico` | Linhas 413-464 | Gera pergunta preservando profissional/data/hora |
| `consulta_disponibilidade_aberta` | Linhas 5567-5568 | Mapeia intenção para objetivo |

---

## 🔧 IMPLEMENTAÇÃO

**Arquivo:** `router/principal_router.py`  
**Linhas:** 5463-5469 (com extensão para 5463-5492)  
**Mudança:** Adicionar bifurcação para `intencao="consulta"`

### Código Adicionado

```python
else:
    # [P0.7 FIX] Verificar se é CONSULTA sem serviço (esperado)
    # vs. AGENDAMENTO sem serviço válido (deve rejeitar)
    if interpretacao_gpt.get("intencao") == "consulta":
        # ✅ Consulta informacional sem serviço é VÁLIDA
        # Reutilizar infraestrutura de consulta_disponibilidade_aberta
        ctx["intencao_conversacional"] = "consulta_disponibilidade_aberta"
        ctx["objetivo_conversacional"] = "descobrir_servico_para_consulta"
        ctx["confianca_intencao_conversacional"] = interpretacao_gpt.get("confianca", 70)
        
        # Preservar entidades extraídas (data, hora, profissional)
        entidades = interpretacao_gpt.get("entidades", {})
        if entidades.get("data"):
            ctx["data"] = entidades.get("data")
        if entidades.get("horario"):
            ctx["horario"] = entidades.get("horario")
        if entidades.get("profissional"):
            ctx["profissional"] = entidades.get("profissional")
        
        await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)
        print(f" [P0.7_CONSULTA_SEM_SERVICO] ACEITA | dados={{'data': ...}}")
        
        # Continuar fluxo normal — handlers já sabem como processar
    else:
        # GPT retornou AGENDAMENTO sem serviço válido → rejeitar
        print(f" [P0.6.2_FALLBACK_REJEITO] ...")
        # [resto do código de rejeição original]
```

**Alteração:** +30 linhas (incluindo comentários), 1 bifurcação adicional, reutiliza handlers existentes.

---

## ✅ VALIDAÇÃO REALIZADA

### Testes Focados — 7/7 PASS

```
test_t1_consulta_pura_bruna_hoje_15h_estrutura_valida ✅
  → Estrutura GPT válida para consulta sem serviço

test_t2_agendamento_sem_servico_rejeitado ✅
  → Agendamento continua sendo rejeitado (sem regressão)

test_t3_contexto_consulta_preservado ✅
  → Profissional, data, hora preservados

test_t4_handler_descobrir_servico_processa_contexto ✅
  → Handler direciona para "perguntar_servico"

test_t5_servico_explicito_preservado ✅
  → Serviço mencionado é validado e preservado

test_t6_consulta_nao_cria_evento ✅
  → Consulta não toca em lógica de criar evento

test_t7_regressao_nao_split_none ✅
  → Guard P0.5 (data_hora=None) continua funcionando
```

**Arquivo de testes:** `tests/test_p07_consulta_disponibilidade_sem_servico.py`

### Cobertura

- ✅ Consulta sem serviço: preserva dados e pergunta qual serviço
- ✅ Agendamento sem serviço: continua rejeitado
- ✅ Serviço inválido: tratado como sem serviço (consulta)
- ✅ Contexto persistido entre mensagens
- ✅ Nenhum evento criado durante consulta informativa
- ✅ Guard contra `data_hora=None` não foi afetado

---

## 📊 FLUXO ESPERADO (PÓS-IMPLEMENTAÇÃO)

### Cenário: "Tem horário para hoje às 15 com a Bruna?"

```
1️⃣ ENTRADA
   Mensagem: "Tem horário para hoje às 15 com a Bruna?"

2️⃣ GPT CLASSIFICA
   intencao = "consulta"
   entidades = {
     profissional: "Bruna",
     data: "2026-12-19",
     horario: "15:00",
     servico: []  ← VAZIO
   }
   confianca: 85%

3️⃣ VALIDAÇÃO P0.7
   ✅ intencao == "consulta" → ACEITA
   ✅ Preserva Bruna, data, hora
   ✅ salva contexto com intencao="consulta_disponibilidade_aberta"

4️⃣ FLUXO NORMAL CONTINUA
   objetivo = "descobrir_servico_para_consulta"
   ↓
   proxim_passo = "perguntar_servico" (porque servico vazio)
   ↓
   SISTEMA PERGUNTA: "Qual serviço você gostaria de consultar?"
   (com contexto: "com Bruna, hoje às 15")

5️⃣ CLIENTE RESPONDE
   "Coloração"

6️⃣ SISTEMA VALIDA
   Valida "coloração" no catálogo da Bruna
   Consulta disponibilidade REAL
   Responde: "Com Bruna, coloração, hoje às 15:
   - 10:00 ✅
   - 14:30 ✅
   - 16:00 ✅"

7️⃣ SEM CRIAR EVENTO
   ✅ Consulta é informativa apenas
   ❌ Nenhum agendamento confirmado
   ❌ Nenhum evento no Firestore
```

---

## 🛡️ RISCO E IMPACTO

### Risk Assessment: **🟢 LOW**

**Mudança mínima:**
- Apenas 1 bifurcação adicional (if/else)
- Reutiliza handlers existentes
- Sem novos campos de contexto
- Sem alteração de banco de dados

**Impacto limitado:**
- Apenas afeta mensagens com `intencao="consulta"`
- Agendamentos continuam validando serviço
- Nenhum change em fluxos operacionais existentes

**Regressão testada:**
- P0.5 (guard data_hora=None) — ✅ continua funcionando
- Agendamentos sem serviço — ✅ continuam rejeitados
- Consultas com serviço — ✅ funcionam normalmente

---

## 📝 CHECKLIST DE RESTRIÇÕES

| Restrição | Status |
|-----------|--------|
| Sem commit/push/deploy | ✅ Não executado |
| Sem alterações em produção | ✅ Apenas código local |
| Sem Firestore real (além do setup) | ✅ Testes com estruturas |
| Não remover validações de agendamento | ✅ Mantidas |
| Não inventar dados | ✅ Apenas preservar GPT |
| Não criar evento durante consulta | ✅ Fluxo informativo |
| Não alterar P0.5 ou outros independentes | ✅ Totalmente isolado |

---

## 📦 ARTEFATOS

| Arquivo | Tipo | Status |
|---------|------|--------|
| `router/principal_router.py` | Implementação | ✅ Editado (linhas 5463-5492) |
| `tests/test_p07_consulta_disponibilidade_sem_servico.py` | Testes | ✅ 7/7 PASS |

---

## 🚀 PRÓXIMOS PASSOS

1. **Revisão de código** — Verificar que bifurcação é minimal e clara
2. **Teste E2E com Firebase real** — Validar com mensagem real no roteador (opcional, aguardando autorização)
3. **Commit e deploy** — Quando autorizado pelo usuário
4. **Monitoramento pós-deploy** — Validar que consultas fluxo normalmente

---

**Data:** 2026-10-21  
**Status:** ✅ IMPLEMENTAÇÃO CONCLUÍDA, TESTES PASSANDO  
**Pronto para:** Code review → Deploy

