# CLAUDE.md — Regras Obrigatórias para NeoEve

---

## 🚨 REGRA ZERO: Nunca Assumir (A Regra Mais Valiosa)

**⭐ ESTA É A REGRA MAIS IMPORTANTE DO DOCUMENTO.**

**ANTES de qualquer outra regra.**

Nunca assua que:
- ❌ Documentação representa o código atual
- ❌ Plano representa a implementação real
- ❌ Fluxo desenhado representa o fluxo executado

---

**Toda afirmação sobre comportamento deve apontar para:**

1. ✅ **Arquivo** — caminho exato
2. ✅ **Função** — nome exato
3. ✅ **Linha** — número exato
4. ✅ **Evidência de execução** — log real, teste real, breakpoint real

---

**Por que é a mais valiosa:**

Em sistemas com múltiplos handlers, routers, MemoriaTemporaria, Firestore e GPT:

```
Documentação ≠ Implementação
    ↓
Implementação ≠ Execução real
    ↓
Diagnósticos completamente errados
```

REGRA ZERO elimina uma quantidade **enorme** de diagnósticos incorretos.

Ela é o antídoto para suposições que parecem óbvias mas são completamente erradas.

```
❌ ERRADO:
"Acho que o fluxo faz isso"
    ↓
Não faz

✅ CORRETO:
"O fluxo faz isso porque:
 - handlers/event_handler.py:454
 - função: add_evento_por_gpt()
 - linha 929: await salvar_evento()
 - log real em [DATA] mostra o comportamento"
```

---

**Por quê:**

NeoEve está repleta de bugs que vieram de exatamente isso:

```
"Acho que o código faz X" ← Suposição
    ↓
Não faz (faz Y)
    ↓
Bug

"Mas a documentação diz..." ← Documentação é stale
```

A REGRA ZERO previne suposições erradas **antes** das outras 13 regras.

---

## 🚫 Proibição de Solução Antes do Diagnóstico

**É proibido propor correção antes de concluir investigação completa.**

Ordem obrigatória:

```
Observação (bug/comportamento inesperado)
    ↓
Reprodução (replicar o cenário)
    ↓
Investigação (rastrear a causa)
    ↓
Causa raiz confirmada (arquivo + função + evidência)
    ↓
Camada de origem identificada
    ↓
SOMENTE ENTÃO: Solução
```

Antiwrong:

```
❌ Observação
   ↓
   Solução (propor correção baseado em intuição)
   ↓
   Investigação (verificar depois)
```

**Sintomas não são causas.**

Correções devem ser justificadas por causa raiz confirmada, não por observação superficial.

**Exemplo histórico - Suri:**
```
❌ ERRADO:
Observação: "Suri é salvo como profissional"
Solução: "Adicionar validação de profissional"
Investigação: "..."

✅ CORRETO:
Observação: "Suri é salvo como profissional"
Reprodução: "Mensagem de voz: 'corte cabelo da Suri'"
Investigação: "Rastrear: voice_handler → gpt_service → evento_data"
Causa raiz: "GPT extrai como profissional, não cliente_nome"
Camada: "Interpretação (camada 1)"
Solução: "Ajustar manual_secretaria.py seção 7.5"
```

---

## 🎯 Regra da Reprodutibilidade

**Nenhum bug deve ser corrigido até ser reproduzido.**

Nota: Relatos sem reprodução não devem ser descartados. Precisam apenas ser marcados como "não confirmado" até reprodução.

Antes de investigar, corrigir ou alterar código:

**Registro Obrigatório:**

1. ✅ **Mensagem exata do usuário**
   - Texto completo, sem paráfrase
   - Contexto: voz, texto, comando?
   
2. ✅ **Resultado obtido**
   - O que realmente aconteceu
   - Exemplo: "Suri foi salvo como profissional"

3. ✅ **Resultado esperado**
   - O que deveria ter acontecido
   - Exemplo: "Suri deveria ser salvo como cliente_nome"

4. ✅ **Tenant**
   - Qual usuário/cliente?
   - Qual organização?
   
5. ✅ **Fluxo percorrido**
   - Por onde passou a mensagem?
   - Exemplo: voice_handler → gpt_service → gpt_executor → add_evento

**Sem reprodução:**
- ❌ Não corrigir
- ❌ Não refatorar
- ❌ Não alterar arquitetura
- ❌ Não adicionar validação

**Por que:** Muitas vezes o problema não está no código.

```
Suposição: "Sistema está salvando Suri como profissional"
    ↓
Reprodução: "Usuário DISSE 'Suri' quando quis dizer 'para Suri'"
    ↓
Causa real: Interpretação de fala, não bug de código
```

---

## 🔍 Buscar Antes de Criar

Antes de criar QUALQUER COISA:
- arquivo
- função
- classe
- utilitário
- helper
- serviço
- constante
- tipo
- enum

é obrigatório executar:

1. ✅ **Buscar por nome semelhante**
   ```
   grep -rn "nome_parcial" --include="*.py"
   grep -rn "conceito_relacionado" --include="*.py"
   ```

2. ✅ **Buscar por responsabilidade semelhante**
   ```
   # Se quer criar: validar_profissional()
   grep -rn "profissional" --include="*.py"
   grep -rn "validar" --include="*.py"
   ```

3. ✅ **Listar candidatos encontrados**
   - Arquivo: qual já existe?
   - Função: qual já faz algo parecido?
   - Responsabilidade: quem já trata isso?

4. ✅ **LER os candidatos encontrados**
   - Não basta localizar, é obrigatório compreender
   - Abrir cada candidato e validar:
     * Entradas esperadas
     * Saídas produzidas
     * Side effects (mudanças de estado)
     * Persistência (o que é salvo)
     * Validações (quais regras)
     * Tratamento de erros
   - **Porque:** Muitos bugs estão escondidos em responsabilidades, não em nomes
   - Exemplo: `salvar_evento()` contém validação, conflito, idempotência, profissional, cliente, agenda — nada disso no nome

5. ✅ **Justificar por que NÃO reutilizar**
   - Se encontrou algo, por que não usar?
   - Se não encontrou, por que criar?
   - Alternativa: estender o existente?

---

**Sem essa busca: NÃO CRIAR.**

---

**Padrão proibido:**

```
❌ "Vamos criar um novo utilitário para X"
   (sem procurar se já existe)

❌ "Vou fazer uma função helper"
   (sem verificar se existe equivalente)

❌ "Preciso de um novo serviço"
   (sem listar alternativas)
```

---

**Padrão correto:**

```
✅ "Preciso de função para X"
   ↓
   Buscar: grep -rn "X" --include="*.py"
   ↓
   Encontrou: [lista de candidatos]
   ↓
   Análise: por que essas não servem?
   ↓
   ENTÃO: criar se realmente necessário
```

---

**Exemplo histórico - o que quase aconteceu:**

```
❌ ERRADO:
"Suri é salvo como profissional, vamos criar validação"
    ↓
Procurar depois se já existe

✅ CORRETO:
"Suri é salvo como profissional"
    ↓
Procurar ANTES: "existe validação de profissional?"
    ↓
Encontrou: salvar_evento já tem verificação de conflito
    ↓
Procurar: "existe campo cliente_nome?"
    ↓
Encontrado: evento_data já suporta cliente_nome
    ↓
Análise: problema não está em código novo
    ↓
Conclusão: ajustar interpretação GPT
```

---

**Por que:**

Muitos erros começam com:

```
"vamos criar"

antes de:

"vamos procurar"
```

Resultado:
- Duplicação de código
- Múltiplas implementações da mesma coisa
- Confusão sobre qual usar
- Código mais difícil de manter

---

## 🎯 Fonte Única de Verdade

Antes de criar qualquer coisa nova:
- campo
- estado
- coleção
- contexto
- cache
- flag
- variável persistida

é obrigatório responder:

**"Qual é a fonte única de verdade atual?"**

Se já existir uma fonte de verdade:
- ✅ Reutilizar
- ❌ Não duplicar
- ❌ Não espelhar
- ❌ Não sincronizar duas estruturas

**Por que:** Se dois lugares podem divergir, existe risco de bug.

---

**Exemplos proibidos:**

```
❌ contexto_agendamento + draft_agendamento
   └─ Qual é a verdade? Quando divergem?

❌ profissional_atual + profissional_escolhido
   └─ Qual prevalece? Em qual ordem?

❌ status_evento + evento_confirmado
   └─ Dois estados? Sincronizar como?

❌ cache_eventos + eventos_firestore
   └─ Cache desatualizado? Quem é confiável?
```

---

**Padrão correto:**

```
✅ Uma única fonte
   ↓
   Derivar tudo dela
   ↓
   Sem sincronização
   ↓
   Sem divergência
```

Exemplo:
```
Fonte de verdade: MemoriaTemporaria/contexto (Firestore)
    ↓
Derivado: contexto_cache (em memória, temporário)
    ↓
Qualquer alteração: salvar em Firestore, depois atualizar cache
```

---

## ⚡ Anti-Hipóteses

**Nunca assumir nada sobre o código.**

Toda afirmação técnica deve ser **classificada e justificada**:

### [CONFIRMADO]
- arquivo
- função
- evidência (trecho de código ou comportamento observado)

Exemplo ilustrativo:
```
[CONFIRMADO] cliente_nome é suportado em add_evento_por_gpt
- handlers/event_handler.py
- Função: add_evento_por_gpt()
- Evidência: Código extrai e usa dados.get("cliente_nome")
```

Nota: Não incluir números de linha específicos. Linhas mudam ao longo do tempo, a regra não.

### [HIPÓTESE]
- descrição da suspeita
- por que precisa de evidência
- próximo passo para confirmar

Exemplo:
```
[HIPÓTESE] salvar_evento filtra cliente_nome
- Suspeita: campo pode estar sendo removido antes de persistir
- Evidência necessária: ler event_service_async.py:57-140
- Próximo passo: grep por "cliente_nome" e buscar filtros
```

---

**Regra de Ouro:**

Se você não pode citar arquivo + função + linha, é [HIPÓTESE].

Não proceda com base em [HIPÓTESE].

Verifique primeiro.

---

### Proibição de Cascata de Hipóteses

**É proibido construir uma nova hipótese baseada em outra hipótese.**

Cada hipótese deve ser validada (com [CONFIRMADO]) antes de gerar a próxima.

Exemplo de cascata proibida:

```
[HIPÓTESE] cliente_nome não é salvo
    ↓ (proibido prosseguir para baixo)
[HIPÓTESE] precisamos criar nova coleção
    ↓ (proibido prosseguir para baixo)
[HIPÓTESE] Firestore não suporta o caso
```

**Correto:**

```
[HIPÓTESE] cliente_nome não é salvo
    ↓
[CONFIRMADO] Verificado: evento_data INCLUI cliente_nome (handlers/event_handler.py)
[CONFIRMADO] Verificado: salvar_evento NÃO filtra campo (services/event_service_async.py)
    ↓
[CONCLUSÃO] cliente_nome É salvo. Hipótese refutada.
```

**Por que:** No caso da "Suri", quase construímos cascata:
- H1: "cliente_nome não é suportado"
- H2: "Precisa criar novo campo"
- H3: "Firestore não preserva"
- H4: "Deve haver validação diferente"

Cada uma não verificada levaria a uma solução errada.

---

**Aplicar a todos os contextos:**
- Análise de bugs
- Proposta de alterações
- Diagnóstico de problemas
- Discussão de arquitetura
- Tomada de decisão técnica

Exemplo de erro comum:
```
❌ "salvar_evento deve validar profissional"
   (nenhuma verificação, apenas intuição)

✅ "[CONFIRMADO] salvar_evento não valida profissional
   - Verificado: Leitura de event_service_async.py
   - Encontrado: Nenhuma validação de profissional no código"
```

## 📐 Regra da Menor Camada

**Ao encontrar um erro, sempre corrigir na camada mais próxima da origem.**

As camadas do sistema, da origem para o fim:

```
1. Interpretação (GPT, prompt, manual)
2. Contexto (dados passados ao GPT, variáveis)
3. Fluxo (roteamento, decisão de ação)
4. Persistência (salvamento, Firestore)
5. Infraestrutura (schema, collections, transações)
```

**Regra:**

Evitar corrigir em camadas inferiores quando a causa raiz está em camada superior.

**Exceção:**

Quando uma proteção defensiva for necessária para evitar corrupção de dados.

Exemplo de exceção legítima:

```
Causa raiz (camada 1): GPT extrai tenant errado
Solução principal: Corrigir prompt

MAIS: Adicionar guard rail em salvar_evento (camada 4)
- Validar: user_id não é vazio?
- Validar: tenant está correto?
- Validar: evento tem data?
- Bloquear persistência se inválido
```

Casos que justificam guard rail:
- tenant errado
- user_id vazio ou None
- evento sem data obrigatória
- profissional nulo em contexto que exige
- valores que causariam corrupção Firestore

**Princípio:** Corrigir na origem, proteger na persistência.

**Método:**

1. Reproduzir o erro
2. Rastrear até a primeira camada onde diverge
3. Corrigir ali
4. Não tocar em camadas downstream

**Exemplo real - Caso "Suri":**

```
Erro observado: "Suri" salvo como profissional em Firestore
    ↓
Rastreamento: onde diverge?
    ↓
Camada 4 (Firestore): "Suri" está lá como profissional ✓
Camada 3 (fluxo): evento_data contém profissional="Suri" ✓
Camada 2 (contexto): dados do GPT contêm profissional="Suri" ✓
Camada 1 (interpretação): GPT extraiu "profissional":"Suri" ← PRIMEIRA DIVERGÊNCIA
    ↓
Solução: Corrigir prompts/manual_secretaria.py (camada 1)
    ↓
NÃO fazer: 
  ❌ Adicionar validação em salvar_evento (camada 4)
  ❌ Criar nova coleção (camada 5)
  ❌ Alterar fluxo de roteamento (camada 3)
```

**Benefício:** Solução na origem evita efeitos colaterais, mantém código simples, reduz complexidade.

---

## 🧪 Simulação Obrigatória

**Nenhuma alteração de fluxo pode ser considerada concluída sem simulação completa.**

Resultado esperado deve ser documentado ANTES do teste.

### Cenários Obrigatórios (Todos os Fluxos)

1. ✅ **Caminho feliz** — tudo como esperado
2. ✅ **Dados faltando** — cada campo essencial faltando
3. ✅ **Dados ambíguos** — entrada que pode ter múltiplas interpretações
4. ✅ **Confirmação curta** — confirmação mínima possível
5. ✅ **Usuário interrompendo fluxo** — cancelar no meio
6. ✅ **Dois usuários simultâneos** — concorrência básica

### Cenários Específicos para Agenda

7. ✅ **Conflito de horário** — slot ocupado
8. ✅ **Profissional indisponível** — data fora do expediente
9. ✅ **Troca de profissional** — usuário muda de ideia
10. ✅ **Confirmação duplicada** — dois "sim" seguidos
11. ✅ **Reenvio da mesma mensagem** — idempotência
12. ✅ **Concorrência** — dois usuários agendando mesmo slot

### Método

**Antes de testar:**

Para cada cenário, documentar:
- Input exato
- Fluxo esperado passo a passo
- Estado esperado em Firestore
- Mensagem esperada ao usuário

**Ao testar:**

- Input: [reproduzir exatamente]
- Output: [verificar cada passo]
- Estado: [verificar Firestore]
- Mensagem: [comparar com esperado]

**Resultado:** [aprovado] ou [reprovado + diferença]

---

**Conexão com documentação:**

Esses cenários devem estar em `TEST_PLAN_AGENDAMENTO.md`.

Cada mudança no fluxo → atualizar testes simulados.

## 🔒 Arquivos

- **NUNCA** criar um arquivo sem antes verificar se já existe algo equivalente no projeto.
- Antes de criar qualquer arquivo novo, **listar os arquivos candidatos já existentes**.
- **Preferir editar arquivos existentes** ao invés de criar novos.
- Sempre informar em qual arquivo pretende atuar antes de gerar alterações.

## 📦 Dependências

- **NUNCA** instalar dependências sem verificar:
  - `requirements.txt`
  - `pyproject.toml`
  - ambiente virtual existente
  - imports já utilizados no projeto
  
- Antes de sugerir instalação, informar:
  - dependência encontrada?
  - versão encontrada?
  - onde foi encontrada?

## 🌍 Ambiente

- **NUNCA** editar arquivos `.env`.
- **NUNCA** criar variáveis de ambiente automaticamente.
- Apenas informar ao usuário quais variáveis precisam ser adicionadas.

## 💾 Alterações de Código

- **NUNCA** aplicar patches diretamente.
- Sempre gerar alteração em formato `.diff` (ou mostrar contexto suficiente).
- Explicar o impacto da alteração antes de aplicá-la.

## ⚠️ Segurança de Alteração

Antes de qualquer ação destrutiva (delete, overwrite, rename, move):
- **Solicitar confirmação explícita**.
- **Nunca remover código** sem mostrar exatamente o que será removido.

## 🏗️ Arquitetura

- **NUNCA** criar fluxo novo sem verificar se já existe fluxo equivalente.
- Antes de implementar qualquer funcionalidade:
  1. localizar fluxo existente
  2. identificar ponto de entrada
  3. identificar funções já utilizadas
  4. reutilizar componentes existentes
  
- **Priorizar correção do fluxo existente** ao invés de criar fluxo paralelo.

- **NUNCA duplicar:**
  - regras de negócio
  - validações
  - templates
  - verificações de conflito
  - verificações de disponibilidade
  
- Se existir função equivalente, **reutilizar**.

## 🚨 Evidência Tem Prioridade Sobre Documentação

Antes de criar:
- plano de testes
- documentação
- utilitário
- refatoração
- abstração
- novo arquivo
- novo fluxo

é obrigatório responder:

**"Existe evidência real do problema?"**

Evidência válida pode vir de:
- ✅ produção (logs, erro de usuário)
- ✅ homologação (teste manual)
- ✅ testes automatizados (falha)
- ✅ revisão de código (análise estática)
- ✅ logs (comportamento observado)
- ✅ simulação (caso de teste)

Se NÃO existir evidência real:
```
❌ Não criar plano
❌ Não criar documentação
❌ Não criar arquitetura
❌ Não criar abstração
❌ Não criar utilitário
```

Ação correta:

```
1. Reproduzir o bug
2. Validar com dados reais
3. Verificar logs reais
4. Analisar JSON real do GPT
5. Consultar Firestore real
6. Rastrear fluxo real
7. Identificar causa raiz
8. SOMENTE DEPOIS: Documentar + Planejar + Testar
```

**Razão histórica - Caso "Suri":**

```
❌ ERRADO (o que quase aconteceu):
Problema observado ("Suri é salvo como profissional")
    ↓
Criar TEST_PLAN_AGENDAMENTO.md (documentação)
    ↓
Criar FLUXO_CONFIRMACAO_REAL.md (documentação)
    ↓
Criar plano de testes (12 cenários)
    ↓
Criar utilitário de validação
    ↓
Depois: "Espera... o problema realmente existe?"
    (spoiler: não era problema de código)

✅ CORRETO:
Problema observado
    ↓
Coletar evidência real:
  - Log do GPT mostrando extração
  - JSON retornado pelo GPT
  - Verificar Firestore
  - Rastrear fluxo no código
    ↓
Confirmar causa raiz (interpretação GPT)
    ↓
Depois: Documentar + Planejar + Testar
```

**Princípio:**

Documentação é para validar compreensão.

Não deve vir antes da evidência.

Evidência pode vir de qualquer ambiente (prod, homolog, testes, logs, simulação).

---

## 🧠 Semântica Antes de Código

Quando o erro envolve interpretação:
- nomes
- pessoas
- parentesco
- profissionais
- clientes
- contexto conversacional

é proibido assumir erro de persistência, Firestore, router ou handler antes de inspecionar:

1. ✅ **Prompt** — O que o GPT foi instruído a fazer?
2. ✅ **JSON retornado pelo GPT** — Qual foi a extração real?
3. ✅ **Dados extraídos da mensagem** — Como foi interpretado?

---

**Pergunta obrigatória:**

**"O sistema entendeu errado ou salvou errado?"**

Se entendeu errado:
→ corrigir interpretação (prompt/manual)

Se entendeu certo e salvou errado:
→ corrigir código (persistência)

---

**Padrão proibido:**

```
❌ "Suri virou profissional"
   ↓
   Vamos alterar salvar_evento()
   ↓
   Vamos alterar event_handler()
   ↓
   Vamos criar validação
   
   (sem verificar o prompt ou JSON do GPT)
```

---

**Padrão correto:**

```
✅ "Suri virou profissional"
   ↓
   Verificar prompt: instrui cliente_nome?
   ↓
   Verificar JSON do GPT: {"profissional": "Suri"}
   ✅ Entendi errado (não extraiu cliente_nome)
   ↓
   Solução: ajustar prompt
   ✅ NÃO: alterar código de persistência
```

---

**Por que:**

A cadeia é: texto → semântica → JSON → código → persistência

Erro no início afeta tudo depois.

Corrigir no final mascara o problema.

---

## 🎯 Confirmar Hipótese Dominante

Para qualquer bug conversacional:

**Classificar o defeito em UMA ÚNICA categoria:**

```
[ ] Semântica     (interpretação/extração GPT)
[ ] Contexto      (memória/estado conversacional)
[ ] Fluxo         (roteamento/sequência)
[ ] Regra negócio (validação/decisão)
[ ] Persistência  (Firestore/salvamento)
[ ] Infraestrutura (transações/locks)
```

**Escolher a hipótese dominante.**

**É proibido corrigir múltiplas categorias simultaneamente sem evidência.**

---

**Padrão correto:**

```
Bug: "Suri virou profissional"

Hipótese dominante:
☑ Semântica

Portanto:
❌ Não alterar Firestore
❌ Não alterar salvar_evento()
❌ Não alterar agenda
❌ Não alterar contexto

Ação:
✅ Corrigir prompt
✅ Testar
✅ Validar

Somente se persistir:
investigar próxima camada.
```

---

**Padrão proibido:**

```
❌ Bug observado
   ↓
   Corrigir prompt
   +
   Alterar contexto
   +
   Refatorar evento
   +
   Mudar Firestore
   
   (sem saber qual mudança resolveu)
```

---

**Por que:**

Bugs conversacionais cascateiam por múltiplas camadas:

```
Bug observado
    ↓
Prompt (semântica)
    ↓
Contexto (memória)
    ↓
Evento (estrutura)
    ↓
Firestore (persistência)
    ↓
Logs (visibilidade)
```

Corrigir múltiplas ao mesmo tempo:
- Impossível saber qual resolveu
- Introduz complexidade desnecessária
- Cria débito técnico
- Dificulta reverter se precisar

---

**Metodologia:**

1. Hipótese dominante com evidência
2. Corrigir APENAS essa camada
3. Testar completamente
4. Se resolver: ✅ pronto
5. Se persistir: investigar próxima
6. Cada camada é um commit separado
7. Cada camada testada independentemente

---

## 🔬 Evidência Mínima Obrigatória

Nenhuma hipótese pode ser escolhida sem evidência observável.

**Para cada categoria:**

### Semântica
- ✅ Visualizar prompt (o que GPT foi instruído?)
- ✅ Visualizar JSON retornado (qual foi a extração?)

### Contexto
- ✅ Verificar contexto salvo (o que foi persistido?)
- ✅ Verificar contexto carregado (o que foi lido?)

### Fluxo
- ✅ Rastrear entrada (qual dados chegaram?)
- ✅ Rastrear saída (qual dados saíram?)

### Persistência
- ✅ Payload salvo (qual JSON foi para Firestore?)
- ✅ Payload lido (qual JSON veio do Firestore?)

### Infraestrutura
- ✅ Logs (qual erro específico?)
- ✅ Conflitos (qual lock/transação?)
- ✅ Transações (qual operação falhou?)

---

**Sem evidência observável: hipótese inválida.**

---

**Padrão proibido:**

```
❌ "O problema é semântica"
   (sem olhar o JSON do GPT)

Isso ainda é uma suposição.
```

---

**Padrão correto:**

```
✅ Hipótese: Semântica
   Evidência:
   - Prompt inspecionado: ✓
   - JSON do GPT visualizado: {"profissional": "Suri"}
   - Confirmado: não extraiu cliente_nome
   
   → Hipótese válida com evidência
```

---

## 🧪 Regressão Obrigatória (Fase 2: INFLEXÃO DE PARADIGMA)

**⚠️ Esta é a primeira regra que realmente muda a natureza do projeto.**

```
REGRAS 1-12: Melhoram capacidade de ENCONTRAR bugs
    └─ Foco: Diagnóstico mais preciso, investigação mais rigorosa
    └─ Pergunta: "Qual é a causa raiz?"

REGRA 13: Melhora capacidade de EVITAR que bugs VOLTEM
    └─ Foco: Confiabilidade, robustez, prevenção de regressão
    └─ Pergunta: "O que pode quebrar com essa correção?"

São domínios completamente diferentes.
```

---

Toda correção deve responder 3 perguntas antes de considerar concluída:

1. ✅ **O bug foi corrigido?**
   - Cenário original funciona?
   - Teste do bug passa?

2. ✅ **O que pode ter quebrado?**
   - Listei efeitos colaterais?
   - Cenários adjacentes podem falhar?

3. ✅ **Quais cenários adjacentes foram testados?**
   - Teste 3-5 variações do mesmo caso
   - Teste casos limítrofes
   - Teste integração com fluxo

---

**Nenhuma correção é considerada concluída sem regressão.**

---

**Por que:**

NeoEve está em fase diferente:

```
FASE 1 (anterior): Construção
├─ Foco: Funcionalidade
├─ Risco: Não funciona

FASE 2 (agora): Confiabilidade
├─ Foco: Robustez
├─ Risco: Funciona de forma errada
```

Confiabilidade não vem da correção.

Vem dos testes de regressão.

---

**Exemplo - Suri:**

```
Bug: "Suri salvo como profissional"

Correção: prompt + cliente_name extraction

Regressão:
1. ✅ Original funciona? "para Suri" → cliente_name
2. ✅ O que quebrou? 
   - "com Bruna" ainda funciona?
   - "para minha filha Suri" ainda funciona?
   - "quero com a mesma profissional" ainda funciona?
3. ✅ Variações testadas:
   - Cliente comum: ✓
   - Profissional: ✓
   - Dependente: ✓
   - Referência: ✓
   - Nome ambíguo: ✓
   - Cliente recorrente: ✓

Sem esses 6 testes: não considerar corrigido.
```

---

## 🚨 Não Concluir Pela Primeira Evidência

Uma evidência confirma uma hipótese.

**NÃO elimina hipóteses concorrentes.**

Antes de corrigir:

1. ✅ Definir hipótese dominante
2. ✅ Coletar evidência da hipótese dominante
3. ✅ **Verificar a hipótese mais provável concorrente**

**Nota:** Não é sobre quantidade de alternativas. É sobre qual alternativa poderia mais invalidar sua conclusão.

---

**Exemplo:**

```
Hipótese A: Semântica (90% provável)
Hipótese B: Contexto (8% provável)
Hipótese C: Persistência (2% provável)

Verificar B vale mais que verificar C e D.
B é a que mais poderia mudar sua conclusão.
```

---

**Padrão perigoso:**

```
❌ Vi uma evidência
   ↓
   Parei de investigar
   ↓
   Corrigi baseado nela
   ↓
   Bug continua
```

---

**Padrão correto:**

```
✅ Encontrei evidência
   ↓
   Hipótese A: Semântica
   ✅ Evidência coletada: JSON = profissional
   ↓
   Hipótese B: Contexto contaminado?
   ✅ Verificar: contexto_anterior contém profissional?
   ↓
   Hipótese C: Persistência errada?
   ✅ Verificar: Firestore tem campo profissional?
   ↓
   Hipótese A é realmente dominante?
   ✅ Sim, evidência B e C descartam alternativas
   ↓
   ENTÃO corrigir
```

---

**Por que:**

Múltiplos cenários podem produzir a mesma evidência observada:

```
"Suri é salvo como profissional"
    ↓
Pode ser:
- GPT extraiu profissional (semântica)
- Contexto anterior contaminado (contexto)
- Campo profissional recebeu cliente_name (persistência)
- Múltiplas causas simultâneas

Uma evidência não diz qual.
```

---

**Exemplo histórico:**

```
Observação: Log mostra X=wrong_value

❌ Parei na evidência 1:
   "Ah, GPT retornou valor errado"
   → Corrigi prompt
   → Bug continua

✅ Verifiquei alternativas:
   1. GPT retornou valor certo?
      (não, era realmente errado)
   2. Contexto salvou valor certo?
      (não, salvou o valor errado)
   3. Firestore persistiu valor certo?
      (não, persistiu valor errado)
      
   → Descobri: problema é na persistência, não no GPT
   → Corrigi local certo
```

---

**Regra final:**

Sempre questione: "Mesmo que isso seja verdade, há outras explicações possíveis?"

Investigue ao menos uma alternativa antes de agir.

---

## 🧪 Teste Obrigatório de Ambiguidade

Toda mudança envolvendo agendamento deve ser testada com casos ambíguos.

**Casos obrigatórios:**

1. ✅ **Cliente direto**
   - "agendar para Suri"
   - Esperado: cliente_nome="Suri", profissional=?

2. ✅ **Profissional direto**
   - "agendar com Bruna"
   - Esperado: profissional="Bruna", cliente_nome=usuário

3. ✅ **Dependente (filho)**
   - "cortar cabelo da minha filha Suri"
   - Esperado: cliente_nome="Suri", profissional=?

4. ✅ **Dependente (esposa)**
   - "agendar para minha esposa"
   - Esperado: cliente_nome="esposa", profissional=?

5. ✅ **Referência contextual**
   - "quero com a mesma profissional"
   - Esperado: buscar contexto anterior, recuperar profissional

6. ✅ **Nome ambíguo (existe como profissional)**
   - "agendar para Carla"
   - (Carla existe como profissional cadastrada)
   - Esperado: pergunta esclarecimento OU contexto resolve

---

**Sem esses testes: NÃO considerar a correção validada.**

---

**Por que:**

Sistemas conversacionais não quebram com teste feliz.

Quebram nos casos ambíguos.

Semântica é a fragilidade, não persistência ou transação.

---

## 🧪 Teste de Persona Obrigatório

Toda alteração relacionada a agendamento deve ser simulada com diferentes contextos semânticos.

**Personas obrigatórias:**

1. ✅ **Cliente comum** — "Quero manicure"
2. ✅ **Filho(a)** — "Agende corte para minha filha"
3. ✅ **Esposa(o)** — "Marque para minha esposa"
4. ✅ **Funcionário** — "Agende para o João (meu funcionário)"
5. ✅ **Nome ambíguo** — "Escova da Bruna" (é profissional? é cliente?)
6. ✅ **Pet** — "Banho para o Thor (meu cachorro)"
7. ✅ **Profissional existente** — "Corte com Carla"
8. ✅ **Cliente recorrente** — "Quero com a mesma profissional da última vez"

---

**Exemplos de entrada:**

```
"Agende corte para Suri"
"Marque horário para minha filha Suri"
"Agende banho para Thor"
"Corte com Carla"
"Escova da Bruna"
"Quer agendar manicure? Qual é o seu nome?"
"Para meu marido, por favor"
"Cabelereiro para a Maria"
```

---

**Validação esperada:**

Cada entrada deve ser corretamente interpretada como:
- cliente_nome (quem recebe)
- profissional (quem faz)
- acompanhante (alguém mencionado)
- dependente (relação com usuário)
- animal (tipo pet)
- terceiro mencionado (contexto)

---

**Por que:**

O caso "Suri" revelou que interpretação semântica é crítica.

- "corte DA Suri" não é unívoco
- "Suri" pode ser cliente, profissional, dependente
- Contexto linguístico determina a interpretação

**Teste de Persona valida se o sistema distingue corretamente.**

---

**Integração:**

Adicionar estas personas ao `TEST_PLAN_AGENDAMENTO.md`:

Cada persona deve ter resultado esperado documentado:
- Cliente → cliente_nome = X
- Profissional → profissional = Y
- Ambíguo → pergunta esclarecimento

---

## 🔄 Teste de Continuidade

Toda alteração deve validar que o fluxo não é reiniciado inapropriadamente.

**Fases obrigatórias:**

1. ✅ **Início do fluxo** — primeiro contato, usuário diz o que quer
2. ✅ **Meio do fluxo** — IA pede dados, usuário responde
3. ✅ **Retomada do fluxo** — usuário envia mensagem fora do esperado
4. ✅ **Conclusão do fluxo** — confirmação e fechamento

---

**Validação crítica: Retomada**

Quando usuário envia mensagem inesperada no meio do fluxo:

```
IA: "Qual profissional você quer?"
    ↓
Usuário: "oi"
    ↓
IA: ??? O que acontece?
```

❌ ERRADO: Reiniciar atendimento, perder contexto

✅ CORRETO: Continuar fluxo, não reiniciar

---

**Exemplo de teste:**

```
Passo 1 - Início:
  Usuário: "quero escova"
  IA: "qual profissional?"

Passo 2 - Retomada (contexto existente):
  Usuário: "oi"
  IA: deve CONTINUAR perguntando profissional
       (não reiniciar com "olá, como posso ajudar?")

Passo 3 - Continuação:
  Usuário: "Carla"
  IA: "qual dia e horário?"

Passo 4 - Conclusão:
  Usuário: "segunda às 14h"
  IA: oferece confirmação
```

---

**Por que:**

Historicamente, NeoEve sofreu muito com "loops de contexto":
- Usuário retoma fluxo
- Sistema reinicia do zero
- Contexto se perde
- Usuário repete informações

Teste de Continuidade valida que isso não acontece.

---

## 🚫 Não Criar Camadas de Conveniência

É proibido criar:
- wrappers
- helpers
- utilitários
- abstrações
- managers
- adapters
- serviços genéricos

apenas para evitar ler o código existente.

**Antes de criar uma camada, provar:**

1. ✅ Reutilização em 3+ locais (4-5 é legítimo)
2. ✅ Redução real de complexidade
3. ✅ Responsabilidade é única e clara
4. ✅ Que não existe equivalente no projeto

**Critério legítimo para abstração:**

NÃO criar abstrações para **evitar entender o código**.

Criar abstrações **apenas quando:**
- responsabilidade é única
- reutilização é comprovada (3+)
- reduz duplicação real
- responsável é claro

---

**Padrão proibido:**

```
❌ utils/helper_x.py (usa algo único)
❌ services/manager_x.py (wrapper de uma função)
❌ adapters/adapter_x.py (transforma um tipo)

Porque cria:
- Duplicação de lógica
- Confusão de responsabilidade
- Proliferação de arquivos
- Código mais difícil de entender
```

---

**Padrão correto:**

```
✅ Usar código existente diretamente
✅ Se precisa centralizar:
   - verificar se existe equivalente
   - reutilizar se existe
   - só criar se usado em 3+ lugares

✅ Cada abstração deve ter motivo claro
```

---

**Risco histórico da NeoEve:**

Hoje o maior risco não é o GPT.

É a proliferação de:
```
utils_x.py
helper_x.py
service_x.py
manager_x.py
adapter_x.py
```

fazendo praticamente a mesma coisa.

**Resultado:**
- Código espalhado
- Dificuldade para manter
- Duplicação de lógica
- Novos desenvolvedores perdidos

---

## 🚨 Antes de Corrigir Bug P0: Rastrear Fluxo Completo

Para qualquer bug P0:

É obrigatório rastrear o fluxo COMPLETO antes de corrigir.

**Pontos de rastreamento obrigatórios:**

1. ✅ **Onde nasce o dado**
   - Entrada do usuário?
   - GPT?
   - Contexto?
   - Firestore?
   - Qual arquivo/função?

2. ✅ **Onde é transformado**
   - Qual função altera?
   - Como é processado?
   - Validações aplicadas?
   - Roteamento?

3. ✅ **Onde é persistido**
   - Em qual coleção?
   - Com qual estrutura?
   - Quais campos?
   - Firestore real consultado?

4. ✅ **Onde é exibido**
   - Qual mensagem ao usuário?
   - Qual log?
   - Qual estado visível?

---

**Por que rastrear completo:**

O erro pode estar em qualquer ponto:
- voz (transcrição)
- GPT (interpretação)
- router (roteamento)
- contexto (estado)
- evento (estrutura)
- Firestore (persistência)

Sem rastrear fluxo inteiro, qualquer correção é aposta.

---

**Exemplo histórico - Suri:**

```
❌ ERRADO (aposta):
"Suri é salvo como profissional"
"Vamos adicionar validação em salvar_evento"
(pode ser errado, pode acertar por sorte)

✅ CORRETO (rastreado):
"Suri é salvo como profissional"
    ↓
1. Nasce em: voice → gpt_service (linha XXX)
2. Transformado em: gpt_executor (linha XXX)
3. Persistido em: evento_data → Firestore (confirmado)
4. Exibido em: log de salvamento (confirmado)

Conclusão: origem é GPT (passo 1)
Solução: ajustar manual_secretaria.py
```

---

**Regra:** Sem rastrear fluxo completo, não corrigir P0.

---

## 🚨 Evidência Antes de Arquitetura

**Antes de propor qualquer mudança estrutural:**

Não é permitido propor:
- nova validação
- nova função
- novo fluxo
- novo campo
- nova coleção
- novo documento
- novo serviço

**Sem primeiro demonstrar:**

1. ✅ **Onde o dado atual falha**
   - Citar arquivo, função, linha
   - Mostrar a falha operacional
   - Exemplo: "evento_data não contém cliente_nome" (FALSO se verificado)

2. ✅ **Que o mecanismo existente não suporta o caso**
   - Verificar schema (suporta o campo?)
   - Verificar persistência (preserva o campo?)
   - Verificar salvamento (filtra o campo?)
   - Exemplo: "salvar_evento remove cliente_nome" (verificado? não)

3. ✅ **Que a solução não pode ser feita ajustando:**
   - prompt/manual do GPT
   - interpretação de dados
   - contexto passado ao GPT
   - configuração existente

Se essa evidência não existir: **não alterar arquitetura.**

---

**Razão:** No caso da "Suri", a arquitetura já suportava tudo:

```
cliente_nome (campo existente)
    ↓
add_evento_por_gpt (linha 496: dados.get("cliente_nome"))
    ↓
evento_data (linha 924: "cliente_nome": cliente_nome)
    ↓
salvar_evento (linha 137: await salvar_dado_em_path())
    ↓
Firestore (preservado sem filtro)
    ↓
agendamento (campo disponível)
```

**Nada estava quebrado.**

**O único problema era:**

```
fala humana ("corte cabelo da Suri")
    ↓
extração GPT ("profissional": "Suri") ← AQUI
    ↓
campo errado
```

**Solução:** Ajustar `prompts/manual_secretaria.py` (seção 7.5)

**NÃO:** Adicionar validação, persistência nova, ou mecanismo de deduplicação.

---

**Checklist antes de propor código:**

```
☐ Verifiquei se o campo já é suportado?
☐ Verifiquei se a persistência já preserva?
☐ Verifiquei se o problema é apenas interpretação?
☐ Tentei ajustar prompt/contexto antes de código?
☐ Posso demonstrar a evidência de falha real?

Se qualquer resposta for "não" ou "não sei":
→ NÃO propor alteração arquitetural
→ Fazer verificação primeiro
```

## 🐛 Debug

Antes de propor correção:
- localizar origem do erro
- identificar causa raiz
- mostrar arquivo e linha
- **Não corrigir sintomas** sem validar a causa raiz

Para bugs:
- mostrar evidência
- mostrar stack trace relevante
- mostrar local exato da falha

## 📅 NeoEve / Sistema de Agenda

### ⛔ GPT NUNCA deve decidir:
- disponibilidade
- conflito
- duração
- criação de evento

### ✅ GPT deve atuar apenas em:
- interpretação de linguagem
- extração de intenção
- humanização de mensagens

### 🔑 Toda lógica crítica deve permanecer **determinística**.

### ❌ Regra de Ouro da Agenda

- **Nunca criar um segundo fluxo de agendamento.**
- **Nunca criar um segundo mecanismo de confirmação.**
- **Nunca criar uma segunda fonte de verdade** para:
  - eventos
  - profissionais
  - serviços
  - disponibilidade

Antes de alterar o sistema de agenda, **mapear o fluxo atual completo**.

## 🧠 Aprendizados Obrigatórios

### Busca de Reutilização Antes de Criar Utils

**Antes de criar qualquer arquivo dentro de `utils/`:**

1. Listar TODO o conteúdo da pasta `utils/`
2. Identificar possíveis arquivos relacionados
3. Buscar funções equivalentes em TODO o projeto
4. Mostrar onde cada função semelhante foi encontrada
5. Justificar por que a reutilização não é possível

**Não criar novo util apenas porque é conveniente.**

**Antes de criar:**
- `utils/*.py`
- helpers
- formatters
- wrappers
- adapters

**Executar busca global por:**
- nome semelhante
- responsabilidade semelhante
- lógica semelhante

**A criação de novo util exige evidência de que não existe implementação equivalente reutilizável.**

### Firestore e Concorrência

**Padrão Read → Modify → Write (RMW) sem proteção é P0 crítico na NeoEve.**

Nunca propor solução baseada em:
```python
dado = ler()
alterar(dado)
salvar(dado)
```
sem análise de concorrência.

**Antes de alterar qualquer operação Firestore verificar:**
- risco de corrida
- múltiplas instâncias
- múltiplos usuários
- múltiplos webhooks
- múltiplos workers

**Para contadores, filas, estados compartilhados e reservas de horário:**
- preferir `transaction`
- preferir `atomic update`
- preferir `increment`
- preferir `compare-and-set`

**Se houver possibilidade de duas execuções simultâneas:**
- assumir concorrência
- justificar estratégia de consistência

**Nunca aprovar RMW simples em:**
- agenda
- disponibilidade
- reservas
- sessões
- notificações
- histórico
- controle de estado

**Sempre documentar:**
- onde está a atomicidade
- onde está a garantia de consistência
- o que acontece sob concorrência

### Aprendizado de Bugs

**Quando um bug for resolvido:**
- registrar a causa raiz
- registrar o padrão arquitetural envolvido
- atualizar o CLAUDE.md para evitar recorrência

Não tratar o bug apenas como caso isolado. **Transformar bugs recorrentes em regras permanentes do projeto.**

### 📋 Logs Antes de Concluir Refatorações

**Nenhuma refatoração é considerada concluída apenas porque compilou.**

**Após qualquer alteração estrutural:**
- verificar logs reais
- verificar execução completa do fluxo
- verificar persistência no Firestore
- verificar mensagem enviada ao usuário
- verificar limpeza de contexto

**Só considerar sucesso quando:**
```
entrada → processamento → persistência → resposta → limpeza
```
estiverem confirmados por log.

**Em fluxos P0 (agendamento, conflito, confirmação, cancelamento):**
- não confiar apenas em análise estática
- exigir evidência operacional nos logs

### 📋 Regra de Testes e Documentação

**Antes de criar qualquer arquivo de documentação:**

1. Verificar se já existe:
   - `README.md`
   - `CLAUDE.md`
   - `docs/*`
   - `TEST_*.md`
   - `DESIGN.md`
   - `ARCHITECTURE.md`
   - Documentação em GitHub Wiki

2. Se existir documentação adequada:
   - **atualizar documento existente**
   - **não criar novo arquivo**

3. **Plano de Testes — Antes de criar:**
   - `TEST_PLAN.md`
   - `EXECUTION_PLAN.md`
   - `TEST_REPORT.md`
   - `CHECKLIST.md`

   **Perguntar:** "Existe algum documento existente onde isso pode ser incorporado?"

### Regra Fundamental

**Documentação duplicada é dívida técnica.**

**Preferir:**
- atualizar documentação existente
- consolidar em um único arquivo authoritative

**Evitar:**
- criar novos arquivos para cada análise
- fragmentar conhecimento em múltiplos docs

### Exceção

Criar novo documento **apenas quando:**
1. não existe documento equivalente
2. o conteúdo excederia significativamente o documento atual (> 30% de aumento)
3. o usuário aprovou explicitamente a criação
4. a responsabilidade é claramente separada (ex: testes em docs/, CLAUDE.md para regras)

### ⚠️ P0 Não Possui Falha Esperada

**Se um teste P0 falhar:**
- documentar
- bloquear produção
- abrir item crítico

**Nunca classificar falha P0 como aceitável.**

Pode ser conhecida. Pode ser temporária. **Mas não é aceitável.**

### 📋 Evidência Antes de Documentar Arquitetura

**Nunca documentar:**
- paths Firestore
- coleções
- documentos
- índices
- locks
- transações

**sem localizar o código que implementa isso.**

**Toda documentação arquitetural deve citar:**
- arquivo
- função
- linha aproximada

que comprovam a afirmação.

**Exemplo correto:**
```
✅ "MemoriaTemporaria usa isolamento por user_id (utils/contexto_temporario.py:42-48)"

❌ "MemoriaTemporaria isolada por user_id" (sem evidência)
```

### 🧪 Todo Bug P0 Corrigido Gera Teste Permanente

**Após corrigir:**
- concorrência
- duplicação
- vazamento de contexto
- conflito de agenda
- race condition

**Criar teste automatizado correspondente.**

**Objetivo:** bug corrigido nunca voltar.

**Não confiar apenas em teste manual.**

---

## 📋 Processo Obrigatório

Antes de qualquer implementação responder:

1. ✅ **Arquivos encontrados** — listar candidatos existentes
2. ✅ **Fluxo atual identificado** — mapear entrada → processamento → saída
3. ✅ **Funções existentes reutilizáveis** — listar funções já disponíveis
4. ✅ **Menor alteração possível** — descrever mudança mínima
5. ✅ **Riscos identificados** — sinalizar impactos potenciais
6. ✅ **Diff proposto** — mostrar código antes/depois

**Somente depois gerar a alteração.**

---

## 📋 Extração Semântica — Antes de Propor Alteração

**Contexto:** Um campo pode estar sendo interpretado incorretamente pelo GPT sem que o código de persistência esteja errado.

**Método obrigatório antes de propor mudança:**

1. ✅ **Verificar se o schema já suporta o campo correto**
   - Procurar em evento_data, dados passados ao salvar_evento, etc.
   - Exemplo: `cliente_nome` já era suportado, apenas GPT não extraía

2. ✅ **Verificar se o salvamento já preserva o campo correto**
   - Procurar em salvar_evento, salvar_dado_em_path, etc.
   - Exemplo: salvar_evento já salvava `cliente_nome` no Firestore sem filtro

3. ✅ **Verificar se o problema está apenas na camada de interpretação GPT**
   - Se sim: ajustar prompt/manual, não código de persistência
   - Exemplo: adicionar seção 7.5 ao manual_secretaria.py

**NÃO propor alterações em:**
- Firestore (salvar, buscar, estrutura)
- Agenda (conflito, disponibilidade, expediente)
- Persistência (salvar_evento, salvar_contexto)

**Antes de concluir que a arquitetura está errada.**

**Exemplo real:** "Suri" interpretado como profissional
- ❌ PRIMEIRO IMPULSO: Adicionar validação de profissional em salvar_evento
- ✅ VERIFICAÇÃO: `cliente_nome` já era suportado e salvo
- ✅ SOLUÇÃO: Ajustar prompt GPT apenas (seção 7.5 do manual)

### Investigação de Bugs de IA

**Quando encontrar saída inesperada do GPT:**

**Processo obrigatório (em ordem):**

1. ✅ **Reproduzir a mensagem exata do usuário**
   - Exemplo: `"Olá boa tarde quero agendar corte cabelo da Suri quarta-feira dia 3 de Junho às 19:00"`

2. ✅ **Mostrar o JSON retornado pelo GPT**
   - Citar a resposta real
   - Exemplo: `{"profissional": "Suri", ...}`

3. ✅ **Mostrar o JSON esperado**
   - O que deveria ter sido retornado
   - Exemplo: `{"cliente_nome": "Suri", ...}`

4. ✅ **Identificar o primeiro ponto onde os dados divergem**
   - Não perseguir efeitos colaterais
   - Exemplo: Divergência está em `gpt_service.py:1015` (extração), não em `salvar_evento:137` (persistência)

5. ✅ **Corrigir no ponto mais próximo da origem**
   - Origem: prompt/manual do GPT
   - Não: validação, persistência, ou código downstream

6. ✅ **Extrair aprendizado e registrar como regra**
   - Após resolver o bug, não encerrar sem aprender
   - Identificar qual hipótese levou ao erro
   - Identificar qual evidência teria evitado o erro
   - Registrar a regra no CLAUDE.md para evitar recorrência

   **Exemplo real:**
   - Hipótese inicial: "Suri é inválido como profissional"
   - Evidência que evitaria: "Verificar se campo já é suportado antes de propor novo código"
   - Regra registrada: Seção "Extração Semântica" adicionada ao CLAUDE.md

**Regra Fundamental:**

Não corrigir efeitos colaterais quando a causa raiz está na interpretação.

**Objetivo:** 
Cada bug resolvido melhora o processo para que o mesmo erro não seja proposto novamente.

**Exemplo contraste:**
- ❌ BUG DETECTADO: Suri sendo salvo como profissional
- ❌ IMPULSO: Adicionar validação em salvar_evento
- ✅ CORRETO: O problema está em `manual_secretaria.py` (interpretação GPT), ajustar lá
- ✅ APRENDIZADO: Adicionar regra "Extração Semântica" ao CLAUDE.md

---

## 📊 Hierarquia de Impacto nas Regras (NeoEve)

**FUNDAÇÃO (Bloqueia suposições):**

0. **🚨 Regra Zero: Nunca Assumir**
   - Evita: Suposições sobre código vs documentação
   - Impacto: Previne toda uma categoria de erros

---

**Se você só pudesse seguir 13 regras, seriam estas:**

### NÍVEL MÁXIMO IMPACTO (Evita 80%+ dos erros)

1. **🚫 Proibição de Solução Antes do Diagnóstico**
   - Evita: Correções erradas, refatorações desnecessárias
   - Impacto: Elimina 70% dos erros de arquitetura

2. **🧠 Semântica Antes de Código** ← ESPECÍFICO NEOEVE
   - Evita: Correções no código quando erro está no GPT
   - Impacto: Reduz refatorações inúteis

3. **🎯 Confirmar Hipótese Dominante** ← ESPECÍFICO NEOEVE
   - Evita: Corrigir múltiplas categorias simultaneamente
   - Impacto: Isolamento claro de causa/efeito

4. **🔬 Evidência Mínima Obrigatória** ← NOVO
   - Evita: Suposições mesmo com hipótese escolhida
   - Impacto: Validação factual em cada camada

5. **🚨 Não Concluir Pela Primeira Evidência** ← NOVO
   - Evita: Parar investigação prematuramente, assumir causa antes de verificar alternativas
   - Impacto: Detecta raízes causas reais, não apenas sintomas

### NÍVEL ALTO IMPACTO (Evita 40%+ dos erros restantes)

6. **🧪 Teste de Ambiguidade Obrigatório** ← ESPECÍFICO NEOEVE
   - Evita: Bugs que aparecem em casos reais, não testes felizes
   - Impacto: Robustez em conversação

7. **🔍 Buscar Antes de Criar** (+ Ler candidatos)
   - Evita: Duplicação de código, confusão de qual usar
   - Impacto: Reduz complexidade, aumenta reusabilidade

8. **🚨 Evidência > Documentação**
   - Evita: Documentação em vão, planos prematuros
   - Impacto: Foca recursos onde importa

9. **🎯 Fonte Única de Verdade**
   - Evita: Divergência de dados, bugs de sincronização
   - Impacto: Elimina classe inteira de bugs

### NÍVEL MÉDIO IMPACTO (Evita 20%+ dos erros restantes)

10. **📐 Menor Camada**
    - Evita: Correções em camada errada
    - Impacto: Soluções elegantes, código simples

11. **🧪 Teste de Persona** (8 personas)
    - Evita: Interpretação semântica errada
    - Impacto: Casos reais cobertos

12. **🔄 Teste de Continuidade**
    - Evita: Loops de contexto (problema histórico NeoEve)
    - Impacto: Fluxos mais robustos, UX consistente

### NÍVEL ASSEGURAÇÃO (Confiabilidade)

13. **🧪 Regressão Obrigatória** ← NOVO
    - Evita: Quebras silenciosas em casos adjacentes
    - Impacto: Fase 2 (Confiabilidade vs Construção)

---

**Essas 13 juntas evitariam a maior parte dos erros dos últimos ciclos da NeoEve.**

**Se tiver que priorizar: 1, 2, 3, 4, 5 (primeiras 5 bloqueiam 80%+ sozinhas).**

**Regra crítica: Regressão (13) é mandatória agora que o projeto entrou em Fase 2 (Confiabilidade).**

---

**Última atualização:** 2026-06-02  
**Aprendizados adicionados:** 2026-06-02 (Reutilização de Utils, Firestore/Concorrência, Aprendizado de Bugs, Extração Semântica, Buscar Antes, P0 Fluxo, Impacto, Não Concluir Pela Primeira Evidência)

---

## 🔒 REGRAS CONGELADAS × TESTES EVOLUTIVOS

**Decisão crítica:**

```
REGRAS (CLAUDE.md): 🔒 CONGELADAS
    ├─ Regra Zero + 13 regras
    ├─ Mudança = mudança de filosofia
    ├─ Alto custo
    └─ Apenas com evidência forte

TESTES (TESTES_REGRESSAO_PERMANENTE.md): 📈 EVOLUTIVOS
    ├─ Crescem sempre que bug revela nova classe de erro
    ├─ Baixo custo
    ├─ Preferível a adicionar regra
    └─ Cria hierarquia saudável
```

**Por que essa separação importa:**

```
Padrão errado:
Bug novo → Nova regra → Documento maior → Ninguém consulta

Padrão correto:
Bug novo → Novo teste permanente → Rodar regressão → Bug não volta
```

---

## 🔒 CLAUDE.md CONGELADO PARA VALIDAÇÃO EMPÍRICA

**Decisão:** O documento CLAUDE.md com Regra Zero + 13 regras será congelado a partir de 2026-06-02.

**Razão:** O gargalo agora não é falta de regras. É **execução consistente** das regras que já existem.

**Perigo evitado:** Documento crescendo indefinidamente (5000+ linhas) com regra 14, 15, 16... que ninguém consulta.

**Permitido durante congelamento:**
- ✅ Melhorar explicação de regra existente
- ✅ Adicionar exemplo a regra existente
- ✅ Corrigir erro em regra existente

**Proibido durante congelamento:**
- ❌ Adicionar Regra 14
- ❌ Adicionar Regra 15
- ❌ Reorganizar estrutura fundamental

**Próximo passo:** Validação empírica.

---

## ⚠️ Métrica Crítica: Falha de Processo vs Falha de Framework

**Muita equipe confunde as duas.**

---

**CENÁRIO A: Falha de PROCESSO (regra não usada)**
```
Bug encontrado
    ↓
Investigação não consultou CLAUDE.md
    ↓
Regra 5 (verificar hipótese alternativa) não foi aplicada
    ↓
Conclusão: FALHA DE PROCESSO
    ↓
Ação: Treinar, lembrar, investir em adoção
```

**CENÁRIO B: Falha de FRAMEWORK (regra usada e falhou)**
```
Bug encontrado
    ↓
Investigação consultou CLAUDE.md
    ↓
Regra 5 foi aplicada corretamente
    ↓
Bug escapou mesmo assim
    ↓
Conclusão: FALHA GENUÍNA DA REGRA
    ↓
Ação: Refinar regra OU adicionar novo teste
```

---

**A métrica que importa:**

```
NÃO é: "Quantos bugs apareceram?"

É: "A regra foi USADA?"

Se usada: Por que escapou?
Se não usada: Por que não foi consultada?
```

**Essa distinção muda o diagnóstico inteiro.**

---

## 📊 Métricas a Acompanhar (Próximas 4-6 Semanas)

### Para cada bug encontrado, registrar:

1. **Regra Zero foi verificada?**
   - Investigador apontou arquivo/função/linha?
   - Ou assumiu algo sobre o código?

2. **Qual regra deveria ter evitado?**
   - Regra 5? Regra 13? Outra?

3. **A regra foi realmente aplicada?**
   - Há evidência no registro de investigação?
   - Ou foi pulada/ignorada?

4. **Resultado:**
   - ✅ Regra não usada → Falha de execução (treinar time)
   - ✅ Regra usada e bug escapou → Falha da regra (refinar)

---

### Métricas derivadas:

| Métrica | O que significa |
|---------|-----------------|
| **Taxa de conformidade Regra Zero** | % bugs que apontam arquivo/função/linha |
| **Taxa de regressão (Regra 13)** | % bugs que passaram por regressão |
| **Bugs escapando Regra Zero** | Suposições que viram bugs |
| **Bugs escapando Regra 5** | Alternativas não verificadas |

---

## ✅ Critérios de Descongelamento

**Após 4-6 semanas, o documento descongelará APENAS se:**

1. ✅ Dados mostram padrão recorrente de erro **não coberto** pelas Regra Zero + 13
2. ✅ E esse padrão **recidiva múltiplas vezes** (não foi caso único)
3. ✅ E uma **nova regra resolveria** ele

**Proibido adicionar regras baseado em:**
- ❌ Um bug único (pode ser outlier)
- ❌ Falta de execução das regras existentes (treinar, não criar regra)
- ❌ Intuição (apenas dados empíricos)

---

**O documento retornará do congelamento apenas com evidência forte de que:**
- Regra Zero + 13 não conseguem evitar uma classe de erro recorrente
- E uma nova regra 14 resolveria esse padrão genuinamente

---

## 🎓 Princípios Permanentes

Evidências, incidentes e investigações estão em: `docs/auditorias/`

### 1. Dados Explícitos > Contexto Antigo

Quando usuário fornece dado explícito, usar SEMPRE o novo. Nunca preservar antigo do contexto.

Ordem: `mensagem_atual > draft_agendamento > ultima_consulta > contexto_antigo`

---

### 2. Disponibilidade: Motor Determinístico, Não GPT

Consultas sobre disponibilidade ("quem tem disponível?") são respondidas pelo motor, nunca delegadas ao GPT. Motor é confiável e economiza tokens.

---

### 3. Verificar Semântica Antes de Alterar Código

Valor errado pode ser: interpretação (GPT/prompt) ou código (persistência). Sempre verificar origem antes de corrigir.

---

### 4. Multi-tenant: Sempre obter_id_dono(user_id)

`user_id` pode ser cliente, não dono. Resolver tenant corretamente para evitar misturar dados.

---

### 5. Fallback em 3 Níveis para Dados Opcionais

Ao buscar lista dinâmica: 1) Firestore (real), 2) Fallback padrão (corte, escova...), 3) Perguntar ao usuário. Nunca deixar vazio.

---

## 🔐 REGRA PERMANENTE: ClienteProfile Influencia, Não Decide

**Status:** OBRIGATÓRIA E PERMANENTE  
**Effective:** 2026-06-14  
**Escopo:** P1.1, P1.2, P1.3, P1.4 e todas as fases futuras envolvendo ClienteProfile  

### Hierarquia Inviolável

```
Mensagem atual > Histórico/Perfil > Defaults

ClienteProfile INFLUENCIA sugestões.
ClienteProfile NUNCA DECIDE criação de evento.
```

### Regra Central

**Nenhuma funcionalidade baseada em ClienteProfile pode:**

- ❌ Criar evento automaticamente
- ❌ Confirmar evento automaticamente
- ❌ Sobrescrever pedido explícito do cliente
- ❌ Ignorar conflito baseado em histórico
- ❌ Ignorar disponibilidade baseado em histórico
- ❌ Pular passo obrigatório do fluxo
- ❌ Sugerir sem exigir confirmação
- ❌ Auto-agendar recorrência sem autorização

### O que ClienteProfile PODE Fazer

- ✅ Sugerir profissional baseado em histórico (com confirmação)
- ✅ Preencher draft com valores do perfil (cliente pode alterar)
- ✅ Personalizar experiência ("Bem-vindo de volta, João")
- ✅ Informar contexto ao motor determinístico
- ✅ Reduzir perguntas se dados já disponíveis

### Code Review Obrigatório

**TODO PR que envolva ClienteProfile DEVE:**

1. ✅ Referenciar `SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md`
2. ✅ Incluir checklist de validação (10 itens)
3. ✅ Ser aprovado por revisor especializado
4. ✅ Incluir testes que validam segurança

**PRs são REJEITADAS se:**

- ❌ Checklist está incompleto
- ❌ Não cita SPEC_SEGURANCA
- ❌ Evento pode ser criado sem confirmação
- ❌ Histórico sobrescreve pedido explícito
- ❌ Qualquer passo obrigatório é pulado

**Referência:** `docs/policies/POLITICA_CODE_REVIEW_CLIENTEPROFILE.md`

---

**Última atualização:** 2026-06-14  
**Status:** Documento congelado até descongelamento comprovado
