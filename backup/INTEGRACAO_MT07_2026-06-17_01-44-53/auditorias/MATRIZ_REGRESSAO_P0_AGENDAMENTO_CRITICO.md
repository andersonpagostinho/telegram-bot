# 🔒 MATRIZ PERMANENTE P0 — Regressão Crítica de Agendamento

**Status:** 📋 BATERIA PERMANENTE DE TESTES  
**Data:** 2026-06-16  
**Escopo:** 15 cenários críticos para evitar regressão no agendamento  
**Objetivo:** Garantir que cenários óbvios NUNCA voltam a quebrar

---

## 🎯 Objetivo

Bateria permanente que deve rodar **ANTES DE TODO COMMIT** que altere:
- Router de agendamento
- Handler de profissional
- Handler de serviço
- Fluxo de confirmação
- Persistência de agendamento
- Lógica de disponibilidade

---

## 📊 15 Cenários Críticos Obrigatórios

### GRUPO A: Fluxo Positivo Básico (2 testes)

| ID | Nome | Entrada | Esperado | Status |
|----|------|---------|----------|--------|
| 1 | Serviço + prof + data válidos | "Quero corte com Bruna amanhã às 10" | Pré-confirmação, sem pedir prof novamente | 📋 TODO |
| 2 | Serviço + data, sem prof | "Quero corte amanhã às 10" | Pergunta profissional com opções válidas | 📋 TODO |

**Validação comum:**
- ✅ `draft_agendamento` preserva campos válidos
- ✅ `estado_fluxo` correto
- ✅ Resposta contém o que foi pedido
- ✅ Não cria evento

---

### GRUPO B: Profissional Inválido/Incompatível (3 testes)

| ID | Nome | Entrada | Esperado | Status |
|----|------|---------|----------|--------|
| 3 | Prof existe, não atende serviço | "Quero corte com Carla amanhã às 10" | "*Carla* não atende corte. Para corte, posso verificar com: [lista]. Qual prefere?" | 📋 TODO |
| 4 | Prof não existe | "Quero corte com Fernanda amanhã às 10" | "Não encontrei *Fernanda* entre os profissionais. Para corte, posso verificar com: [lista]" | 📋 TODO |
| 5 | Prof informado depois, inválido | Fluxo: "Quero corte" → "Carla" | "Carla não atende corte. Para corte, posso verificar com: [lista]" | 📋 TODO |

**Validação comum:**
- ✅ Menciona nome do profissional mencionado
- ✅ Menciona motivo explícito (não atende)
- ✅ Lista profissionais válidos para o serviço
- ✅ `motivo_estado = "profissional_nao_atende_servico"` (para continuidade)
- ✅ Draft preserva serviço e data_hora
- ✅ Não cria evento

**Validação específica Test 3:**
- ✅ `profissional_rejeitado = "Carla"`
- ✅ `profissionais_validos` contém Bruna, Gloria, Joana
- ✅ Não menciona "Qual profissional você prefere?" (genérico)

---

### GRUPO C: Serviço Inválido (2 testes)

| ID | Nome | Entrada | Esperado | Status |
|----|------|---------|----------|--------|
| 6 | Serviço não existe | "Quero massagem com Bruna amanhã às 10" | "Não encontrei *massagem* no catálogo. Temos: [lista com Corte, Escova, etc]" | 📋 TODO |
| 7 | Serviço atual vence draft antigo | Draft anterior: botox. Entrada: "Quero corte com Bruna amanhã às 10" | Draft.servico = corte; resposta não menciona botox | 📋 TODO |

**Validação comum:**
- ✅ Menciona o serviço mencionado (ex: "massagem")
- ✅ Lista serviços disponíveis
- ✅ Não confunde com profissional
- ✅ Não cria evento

**Validação específica Test 7:**
- ✅ Dados explícitos (mensagem atual) vencem draft antigo
- ✅ `draft.servico` atualizado para novo valor
- ✅ `draft.data_hora` atualizado

---

### GRUPO D: Respostas Óbvias (2 testes)

| ID | Nome | Entrada | Contexto | Esperado | Status |
|----|------|---------|---------|----------|--------|
| 8 | "Sim" após prof incompatível | "Sim" | `motivo_estado="profissional_nao_atende_servico"`, `profissionais_validos=[...]` | "Pode escolher: [lista]" + manter contexto | 📋 TODO |
| 9 | "Não/cancelar" após prof incompatível | "Desistir" | `motivo_estado="profissional_nao_atende_servico"` | "Tudo bem. Não alterei." + limpar `motivo_estado` | 📋 TODO |

**Validação comum:**
- ✅ Handler explícito para sim/não (não ambíguo)
- ✅ Sem criar evento
- ✅ Sem alterar `draft_agendamento.servico`
- ✅ Sem alterar `draft_agendamento.data_hora`
- ✅ Contexto não diverge em múltiplas respostas

---

### GRUPO E: Não Regressão de Agenda (6 testes)

| ID | Nome | Validação | Esperado | Status |
|----|------|----------|----------|--------|
| 10 | Conflito de horário sugere alternativa | Horário ocupado | Oferece "amanhã às 14h" ou similar, não cria evento | 📋 TODO |
| 11 | Confirmação pendente exige "sim" explícito | `estado_fluxo="agendamento_pronto"`, entrada: "Ok" | Não confirma. Pede "sim" explícito | 📋 TODO |
| 12 | Resposta neutra "beleza" não confirma | `estado_fluxo="agendamento_pronto"`, entrada: "Beleza" | Não confirma. Pede "sim" | 📋 TODO |
| 13 | Escolha numérica funciona (horários sugeridos) | `estado_fluxo="escolhendo_horario"`, entrada: "2" | Seleciona opção 2 corretamente | 📋 TODO |
| 14 | Troca de prof válida mantém serviço/data | Prof válida, estado "aguardando_profissional" | `draft.profissional` atualizado, serviço/data não alteram | 📋 TODO |
| 15 | Troca de prof inválida explica motivo | Prof inválida, estado "aguardando_profissional" | Responde como test 3 (motivo explícito) | 📋 TODO |

**Validação comum (Grupo E):**
- ✅ Draft não alterado desnecessariamente
- ✅ Fluxo continua, não reinicia
- ✅ Resposta menciona contexto correto
- ✅ Não cria evento em cenários negativos

---

## 🧪 Como Rodar

### Local Development

```bash
cd "Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
python tests/runner_regressao_p0_agendamento_critico.py
```

### Saída esperada

```
================================================================================
BATERIA P0 — REGRESSÃO CRÍTICA DE AGENDAMENTO
================================================================================

[✅] Test  1 (A): Serviço + profissional + data/hora válidos
[✅] Test  2 (A): Serviço + data/hora, sem profissional
...
[✅] Test 15 (E): Troca de profissional inválida explica motivo

================================================================================
RESULTADO: 15 PASSOU, 0 FALHOU, 0 ERRO
================================================================================
```

### CI/CD Integration

```yaml
# .github/workflows/regressao_p0.yml
- name: Test P0 Regressão Agendamento
  run: python tests/runner_regressao_p0_agendamento_critico.py
  
- name: Check Results
  if: failure()
  run: |
    echo "P0 tests failed!"
    cat tests/resultado_regressao_p0_agendamento_critico.json
    exit 1
```

---

## ✅ Validações Comuns Todos os Testes

### Resposta (output)

- ✅ Contém texto esperado
- ✅ Não contém texto proibido (genérico)
- ✅ Menção explícita do que foi pedido
- ✅ Sem misturas de contexto (botox em pergunta de corte)

### Contexto (estado)

- ✅ `estado_fluxo` correto para a fase
- ✅ `draft_agendamento` preserva campos válidos
- ✅ `motivo_estado` (se aplicável) correto
- ✅ Sem contaminação cruzada de campos

### Persistência (não-funcionalidade)

- ✅ Não cria evento em cenário negativo
- ✅ Não altera `ClienteProfile`
- ✅ Não altera cancelamento
- ✅ Não mistura tenant
- ✅ Não deleta dados
- ✅ Não chama GPT para decidir conflito (usa motor determinístico)

---

## 📋 Checklist Antes de Commit

**Nenhum commit que altere agendamento pode ser feito sem:**

- [ ] Rodar `python tests/runner_regressao_p0_agendamento_critico.py`
- [ ] Validar 15/15 testes PASSARAM
- [ ] Revisar `tests/resultado_regressao_p0_agendamento_critico.json`
- [ ] Não há regressions (falhas que antes passavam)
- [ ] Se houver falhas novas: documentar motivo antes de merge

---

## 🚨 Protocolo em Caso de Falha

### Passo 1: Isolar
- Qual teste falhou? (ID e nome)
- Qual validação não passou?
- Contexto inicial vs contexto final (diff)

### Passo 2: Reproduzir
- Executar o teste isolado
- Verificar entrada/saída exata
- Consultar logs reais se possível

### Passo 3: Investigar Causa Raiz
- A falha é regressão (quebrou algo que funcionava)?
- Ou a falha é nova (implementação incompleta)?
- Qual mudança de código causou?

### Passo 4: Documentar e Decidir

**Se regressão confirmada:**
- Reverter o commit
- Investigar causa raiz (qual linha mudou?)
- Corrigir e retestetear

**Se implementação incompleta:**
- Completar a implementação
- Verificar se há efeitos colaterais

**Se falha é válida (comportamento mudou intencionalmente):**
- Atualizar teste para novo comportamento esperado
- Documentar mudança no commit message

---

## 📊 Métricas

Após cada rodada de testes, registrar:

```json
{
  "data": "2026-06-16",
  "total": 15,
  "passou": 15,
  "falhou": 0,
  "taxa_sucesso": "100%",
  "grupos": {
    "A": "2/2",
    "B": "3/3",
    "C": "2/2",
    "D": "2/2",
    "E": "6/6"
  },
  "regressions": 0,
  "novos_casos": 0
}
```

---

## 🔄 Evolução da Bateria

**Bateria congelada em 15 testes até:**
- ✅ Todos 15 testes passarem consistentemente
- ✅ Implementação estar 100% estável

**Quando adicionar novo teste:**

1. ✅ Bug descoberto em produção
2. ✅ Causa raiz confirmada
3. ✅ Teste que captura o bug é criado
4. ✅ Teste é adicionado a essa matriz
5. ✅ Implementação é feita
6. ✅ Novo teste passa
7. ✅ Bateria total atualizada

**Exemplo:**
```
Bug: "Usuário conseguiu agendar dois horários ao mesmo tempo"
    ↓
Causa: Race condition no conflito de horário
    ↓
Novo teste: Test 16 "Conflito de horário (concorrência)"
    ↓
Bateria agora: 16 testes
```

---

## 📚 Referências

- **Implementação:** `tests/runner_regressao_p0_agendamento_critico.py`
- **Resultados:** `tests/resultado_regressao_p0_agendamento_critico.json`
- **Patches P0:** `IMPLEMENTACAO_PATCH_P0_NEGATIVOS_FINAL.md`
- **Regras globais:** `CLAUDE.md` (Regra 13: Regressão Obrigatória)

---

## 🎯 Objetivo Final

**Esta bateria existe para:**

```
❌ Nunca mais deixar passar cenários óbvios
❌ Nunca mais ter regressões silenciosas
❌ Nunca mais quebrar agendamento sem aviso

✅ Garantir confiabilidade P0
✅ Evitar surpresas em produção
✅ Documentar comportamento esperado
```

**Sucesso é: 15/15 SEMPRE.**

Sem exceções. Sem "vamos corrigir depois".

---

**Status:** 🔒 CONGELADO ATÉ 100% PASSA

Documento criado: 2026-06-16  
Próxima revisão: 2026-06-30 (após período de validação)
