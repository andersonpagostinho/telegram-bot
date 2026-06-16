# 🔍 Análise: Por Que a Bateria Anterior Não Pegou Este Cenário?

**Data:** 2026-06-16  
**Cenário não coberto:** Profissional explícito que não atende o serviço

---

## 📊 Mapa de Cobertura Anterior

### Runner: `runner_stress_profissional_alternativo_completo.py`

**Objetivo documentado:**
```
Validar 4 cenários críticos de seleção de profissional alternativo:
1. ACEITA SUGESTÃO
2. REJEITA SUGESTÃO
3. MÚLTIPLAS ALTERNATIVAS
4. SEM ALTERNATIVAS
```

**Cenários testados:**
1. ✅ Bruna ocupada → Sistema sugere Carla
2. ✅ Bruna ocupada → Usuario rejeita sugestão
3. ✅ Bruna ocupada → Múltiplas alternativas (Carla, Amanda)
4. ✅ Todas ocupadas → Sem alternativas

**Tipo de problema abordado:** Conflito de horário

---

### O Que Está Faltando

```
┌─────────────────────────────────────────┐
│  PROBLEMAS COM PROFISSIONAL             │
├─────────────────────────────────────────┤
│                                         │
│ 1. Conflito de Horário (COBERTO)        │
│    ├─ Bruna ocupada às 10h              │
│    ├─ Sugere Carla                      │
│    └─ Usuário escolhe Carla             │
│                                         │
│ 2. NÃO ATENDE SERVIÇO (NÃO COBERTO)    │
│    ├─ Carla não atende CORTE            │
│    ├─ Bruna/Gloria/Joana atendem CORTE  │
│    ├─ Sistema deveria informar          │
│    └─ Usuário escolhe alternativa       │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🔎 Por Que Não Foi Detectado Antes?

### 1. Diferença de Raiz Cause

**Cenário coberto (Profissional Alternativo por Conflito):**
```
Fluxo: profissional válido → verificar conflito → encontra conflito → sugere alternativa
Ponto de entrada: Depois que profissional foi VALIDADO e está em disponiveis
Função: verificar_conflito_e_sugestoes_profissional()
```

**Cenário não coberto (Profissional Inválido por Serviço):**
```
Fluxo: profissional mencionado → procurar em disponiveis → NOT FOUND → ???
Ponto de entrada: ANTES de validar se profissional atende serviço
Função: nenhuma (era genérico "Qual profissional você prefere?")
```

### 2. Diferença de Localização no Código

**Cenário coberto:** Linhas 398-434 em `acao_handler.py`
```python
if profissional_escolhido in disponiveis:  # ✅ Profissional encontrado
    conflito_info = await verificar_conflito_e_sugestoes_profissional(...)
```

**Cenário não coberto:** Linhas 382-391 em `acao_handler.py`
```python
if not profissional_escolhido:  # ❌ Profissional NÃO encontrado
    return "Qual profissional você prefere?"  # ← Antes do patch
```

### 3. Diferença na Entrada de Dados

**Cenário coberto:**
```
Fluxo sequencial:
1. "Quero agendar corte com Bruna"
   → Bruna detectada, salva em sessão
   → Estado = aguardando_data

2. "Amanhã"
   → Data interpretada
   → Verificação de disponibilidade
   → Detecta conflito de Bruna
   → Sugere Carla

3. Usuário responde à sugestão
```

**Cenário não coberto:**
```
Fluxo direto (input única com tudo):
1. "Quero agendar corte com Carla"
   → Carla mencionada
   → Data/hora também vem na mensagem
   → Sistema passa por múltiplos estados
   → Em "aguardando_profissional", Carla não está em disponiveis
   → Sistema não tinha lógica para "profissional mencionado mas inválido"
```

---

## 🎯 Raiz Cause do Silêncio Anterior

### A Função `buscar_profissionais_por_servico()` Foi A Chave

Quando o sistema busca profissionais compatíveis com um serviço:

```python
profissionais_filtrados = await buscar_profissionais_por_servico(
    servicos=["corte"],
    user_id=user_id
)
# Resultado: {"Bruna": {...}, "Gloria": {...}, "Joana": {...}}
# Carla foi EXCLUÍDA porque não atende "corte"
```

Depois, a lista de `disponiveis` é reduzida ainda mais:

```python
disponiveis = {
    nome: profissionais_filtrados[nome]
    for nome in disponiveis_dict
    if nome in profissionais_filtrados  # ← Carla nunca entra aqui
}
```

**Resultado:** O sistema nunca soube que Carla foi mencionada, porque procurou apenas em `disponiveis` (que só contém profissionais que atendem o serviço).

---

## 📋 Checklist: O Que Estava Faltando

| Item | Status Anterior | Status Novo | Nota |
|------|-----------------|------------|------|
| Detectar profissional mencionado | ❌ | ✅ | Mesmo que não atenda serviço |
| Validar se atende serviço | Parcial* | ✅ | *Só validava se estava em disponiveis |
| Informar motivo da rejeição | ❌ | ✅ | "Carla não atende corte" |
| Listar alternativas válidas | Sim | Sim | Sem mudança |
| Preservar contexto | Sim | Sim | Sem mudança |
| Aguardar nova escolha | Sim | Sim | Sem mudança |

---

## 🏗️ Por Que Não Foi Apanhado por Testes Anteriores?

### 1. Scope dos Runners Existentes

```
runner_stress_profissional_alternativo_completo.py
├─ Testa: Alternativas por CONFLITO (não por SERVIÇO)
├─ Setup: Profissional já está em disponiveis
├─ Mock: verificar_conflito_e_sugestoes_profissional()
└─ Gap: Nunca testa "profissional inválido por serviço"
```

### 2. Configuração dos Mocks

```
Cenários testados:
- Bruna escolhida → conflita → sugere Carla (que ATENDE corte)
- Bruna escolhida → conflita → múltiplas alternativas (que ATENDEM corte)
- Bruna escolhida → conflita → sem alternativas

Cenário NÃO testado:
- Carla escolhida → não atende corte → nenhuma validação feita
```

### 3. Manual Violations

```
manual_secretaria.py seção 7.4:
"Se o profissional escolhido não oferece o serviço:
 → informe isso claramente
 → sugira apenas profissionais válidos"

Status anterior: VIOLADO (resposta genérica)
Status novo: CUMPRIDO (resposta específica)
```

---

## 🔬 Análise Estrutural

### Camadas de Validação

```
Camada 1: Existência do Profissional
├─ Anterior: ❌ Não validava "Carla" se não estava em disponiveis
└─ Novo: ✅ Valida em TODOS os profissionais

Camada 2: Compatibilidade com Serviço
├─ Anterior: ❌ Pressupunha compatibilidade (se estava em disponiveis)
└─ Novo: ✅ Valida explicitamente

Camada 3: Disponibilidade no Horário
├─ Anterior: ✅ Validava
└─ Novo: ✅ Validava (sem mudança)

Camada 4: Resposta Apropriada
├─ Anterior: ❌ Genérica ("Qual profissional você prefere?")
└─ Novo: ✅ Específica ("Carla não atende corte")
```

---

## 📈 Gap Analysis

| Gap | Descrição | Impacto | Severidade |
|-----|-----------|---------|-----------|
| **Falta validação semântica** | Não diferencia "não encontrado" de "inválido" | UX confusa | P0 |
| **Falta informação ao usuário** | Não explica por que profissional foi rejeitado | Confusão | P1 |
| **Falta busca em todos** | Só procura em `disponiveis` | Invisível para usuário | P0 |
| **Manual não cumprido** | Seção 7.4 não implementada | Violação contratual | P0 |

---

## ✅ Solução Aplicada

A implementação do patch resolve:

1. ✅ **Camada 1:** Agora busca em TODOS os profissionais
2. ✅ **Camada 2:** Agora valida compatibilidade explicitamente
3. ✅ **Camada 3:** Sem mudança (já funcionava)
4. ✅ **Camada 4:** Resposta agora é específica e informativa

---

## 📚 Lição Aprendida

**Insight:** Um cenário pode estar "coberto" para um tipo de problema mas não estar coberto para outro tipo.

```
COBERTO:   Profissional válido + conflito de horário
NÃO COBERTO: Profissional inválido + serviço incompatível

Ambos estão em "aguardando_profissional", mas:
- Um é testado pelos mocks de conflito
- Outro não tinha nem uma validação base
```

---

## 🎯 Recomendações Futuras

1. **Expandir runners:** Adicionar caso de "profissional inválido" ao suite de stress tests
2. **Documentação:** Atualizar lista de cenários cobertos nos runners
3. **Testes:** Criar matriz de profissional × serviço × horário para cobertura completa
4. **Review:** Verificar se há outros "gaps semelhantes" em outros fluxos

---

## 📞 Rastreamento

**Auditoria que identificou:** `AUDITORIA_CAUSA_RAIZ_PROFISSIONAL_INVALIDO.md`  
**Patch implementado:** `PATCH_P0_PROFISSIONAL_INVALIDO.md`  
**Teste adicionado:** `tests/test_profissional_explicito_nao_atende_servico.py`

---

**Conclusão:** O cenário não foi detectado anteriormente porque os runners existentes focavam em "profissional válido com conflito de horário", não em "profissional explícito que não atende o serviço". São problemas diferentes na mesma rota de código.
