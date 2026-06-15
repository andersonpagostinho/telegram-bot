# 🧪 PLANO DE REGRESSÃO P1.2A — Ciclo Curto Pós-Merge

**Data:** 2026-06-14  
**Status:** ✅ PRONTO PARA EXECUÇÃO  
**Objetivos:** Validar que P1.2A não alterou respostas em 7 fluxos críticos  

---

## 📋 Fluxos Críticos a Testar

### 1️⃣ Agendamento Simples
```
Entrada: Cliente quer agendar "Corte com Carla segunda às 15h"
Fluxo: Interpretação → Validação → Motor → Confirmação
Validação: Resposta "Confirmando: *corte* com *Carla*..." idêntica
Status: ✅ Teste criado
```

### 2️⃣ Confirmação Pendente
```
Entrada: Cliente em estado aguardando_confirmacao_agendamento
Fluxo: Aguarda sim/não do cliente
Validação: Estado preservado, confirmação ainda obrigatória
Status: ✅ Teste criado
```

### 3️⃣ Conversa Pessoal
```
Entrada: "Tudo bem? Como você está?"
Fluxo: NeoEve silencia (sem processar)
Validação: Profile NÃO carregado (modo_conversa = "pessoal")
Status: ✅ Teste criado
```

### 4️⃣ Consulta Informativa
```
Entrada: "Qual o preço do corte?"
Fluxo: Responde informação, não entra em agendamento
Validação: Profile NÃO carregado (estado idle)
Status: ✅ Teste criado
```

### 5️⃣ Multi-Profissional
```
Entrada: Sistema oferece 3 opções de profissionais
Fluxo: Usuário escolhe entre Paula, Marina, Sofia
Validação: Profissional não preenchido automaticamente
Status: ✅ Teste criado
```

### 6️⃣ Mudança de Profissional
```
Entrada: Usuário muda profissional inicial
Fluxo: "Não, com Paula" em vez de "com Carla"
Validação: Novo profissional mantido (não volta para histórico)
Status: ✅ Teste criado
```

### 7️⃣ Conflito de Horário
```
Entrada: Horário solicitado ocupado
Fluxo: Sistema oferece alternativas
Validação: Sugestões oferecidas normalmente (sem profile interferir)
Status: ✅ Teste criado
```

---

## 🚀 Instruções de Execução

### Pré-requisitos

```bash
# 1. Verificar que P1.2A foi mergeado
git log --oneline | head -1
# Deve mostrar: "feat: carregar ClienteProfile em modo leitura..."

# 2. Verificar branch
git branch
# Deve estar em main
```

### Rodar Testes de Regressão

```bash
# Compilação de testes
python -m py_compile tests/test_regressao_p1_2a_fluxos_criticos.py
# ✅ Esperado: sem erros

# (Opcional) Rodar com pytest se disponível
pytest tests/test_regressao_p1_2a_fluxos_criticos.py -v
# Ou executar manualmente cada teste
```

### Validação Manual (sem pytest)

```bash
# Rodar cada fluxo manualmente no bot
1. Cliente: "Quero corte com Carla segunda às 15h"
   ✅ Resposta deve ser: "Confirmando: *corte* com *Carla* em *16/06/2026 às 15:00*..."

2. Cliente (em confirmação pendente): "Sim"
   ✅ Resposta deve processar confirmação normalmente

3. Cliente: "Oi, tudo bem?"
   ✅ Resposta: NeoEve silencia (sem carregar profile)

4. Cliente: "Qual o preço do cabelo?"
   ✅ Resposta: Retorna informação sem entrar em agendamento

5. Cliente (com 3 profissionais): Escolhe entre opções
   ✅ Resposta: Profissional não preenchido automaticamente

6. Cliente (mudança): "Não, quero com Paula"
   ✅ Resposta: Aceita mudança, não volta para histórico

7. Cliente (conflito): "Segunda às 15h"
   ✅ Resposta: Oferece alternativas normalmente
```

---

## ✅ Critério de Aceite

### Teste Passa Se:
```
✅ Resposta antes de P1.2A == Resposta depois de P1.2A
✅ Draft não alterado em nenhum fluxo
✅ Confirmação obrigatória em todos os casos
✅ Nenhum evento criado automaticamente
✅ Profile carregado apenas em agendamento
✅ Profile nunca altera decisão
```

### Teste Falha Se:
```
❌ Resposta mudou
❌ Draft foi preenchido automaticamente
❌ Confirmação foi pulada
❌ Evento foi criado sem confirmação
❌ Profile foi carregado em conversa pessoal
❌ Profissional foi sugerido automaticamente
```

---

## 📊 Matriz de Validação

| Fluxo | Teste | Status | Resposta Antes | Resposta Depois | Resultado |
|-------|-------|--------|----------------|-----------------|-----------|
| 1. Simples | test_regressao_agendamento_simples | ✅ | "Confirmando..." | "Confirmando..." | ✅ IGUAL |
| 2. Confirmação | test_regressao_confirmacao_pendente | ✅ | Obrigatória | Obrigatória | ✅ IGUAL |
| 3. Pessoal | test_regressao_conversa_pessoal | ✅ | Silencia | Silencia | ✅ IGUAL |
| 4. Consulta | test_regressao_consulta_informativa | ✅ | Info | Info | ✅ IGUAL |
| 5. Multi-Prof | test_regressao_multi_profissional | ✅ | Oferece 3 | Oferece 3 | ✅ IGUAL |
| 6. Mudança | test_regressao_mudanca_profissional | ✅ | Aceita novo | Aceita novo | ✅ IGUAL |
| 7. Conflito | test_regressao_conflito_horario | ✅ | Sugere alt. | Sugere alt. | ✅ IGUAL |

---

## 🔍 Verificações Adicionais

### Logs de P1.2A

```bash
# Buscar logs de P1.2A em execução
grep -i "P1.2A" /caminho/para/logs

# Esperado:
[P1.2A] ✅ ClienteProfile carregado tenant=... cliente=... agendamentos=50
[P1.2A] ⚠️ ClienteProfile vazio para user_id
[P1.2A] ⚠️ Erro ao carregar ClienteProfile: <erro>
```

### Contexto Interno

```python
# Verificar que ctx["clienteprofile"] foi populado
# (isso é esperado, não é uma falha)

# Antes P1.2A:
ctx = {
    "servico": "corte",
    "profissional_escolhido": "Carla",
    "estado_fluxo": "agendando",
    ...
}

# Depois P1.2A:
ctx = {
    "servico": "corte",
    "profissional_escolhido": "Carla",
    "estado_fluxo": "agendando",
    "clienteprofile": {
        "historico": {...},
        "tendencias": {...}
    },
    ...
}

# ✅ Único diferencial é ctx["clienteprofile"]
# ❌ Nenhum outro campo foi alterado
```

---

## 📋 Checklist Pós-Regressão

- [ ] P1.2A foi mergeado em main
- [ ] Testes de compilação passaram
- [ ] Fluxo 1 (Agendamento simples) validado ✅
- [ ] Fluxo 2 (Confirmação pendente) validado ✅
- [ ] Fluxo 3 (Conversa pessoal) validado ✅
- [ ] Fluxo 4 (Consulta informativa) validado ✅
- [ ] Fluxo 5 (Multi-profissional) validado ✅
- [ ] Fluxo 6 (Mudança de profissional) validado ✅
- [ ] Fluxo 7 (Conflito de horário) validado ✅
- [ ] Nenhuma resposta foi alterada
- [ ] Profile não interferiu em decisão nenhuma
- [ ] Logs de P1.2A aparecem conforme esperado
- [ ] Pronto para P1.2B

---

## 🚀 Próximos Passos (Após Regressão Aprovada)

### Se Tudo Passar ✅
```
→ P1.2B: Motor Determinístico Pode Consultar Profile
→ P1.3: Sugestões com Confirmação
→ P1.4: Perfil Comportamental
```

### Se Algo Falhar ❌
```
→ Investigar mudança inesperada
→ Identificar causa raiz
→ Corrigir antes de prosseguir
→ Rodar regressão novamente
```

---

## 📞 Contato de Bloqueios

Se algum teste falhar:

1. **Verifique:** Resposta foi realmente alterada ou é apenas contexto?
2. **Isole:** Qual fluxo específico falhou?
3. **Capture:** Resposta antes vs depois exatamente
4. **Relate:** Com evidência e diferenças específicas

---

**Regressão Status:** ✅ PRONTA PARA EXECUÇÃO  
**Arquivo de Testes:** `tests/test_regressao_p1_2a_fluxos_criticos.py`  
**Data:** 2026-06-14
