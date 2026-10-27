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

## 📐 Auditoria de Estrutura Pré-Alteração

**OBRIGATÓRIO:** Antes de sugerir qualquer alteração de código, fazer auditoria visual da estrutura do projeto.

### Procedimento Obrigatório

Antes de alterar QUALQUER coisa:

1. ✅ **Mapear estrutura de diretórios**
   - Listar arquivos em `utils/`, `services/`, `handlers/`
   - Verificar padrões de nomenclatura
   - Procurar por utilitários relacionados ao problema

2. ✅ **Procurar por serviços/funções similares**
   - Se o problema é datetime → procurar `*datas*.py`, `*tempo*.py`, `*time*.py`
   - Se o problema é contexto → procurar `contexto*.py`, `session*.py`
   - Se o problema é Firebase → procurar `firebase*.py`, `firestore*.py`

3. ✅ **Ler o serviço/utilidade encontrado**
   - Entender contrato (imports, tipos, assinaturas)
   - Verificar se já resolve o problema
   - Identificar padrões e convenções estabelecidas

4. ✅ **Validar alinhamento**
   - A solução proposta usa as funções/padrões existentes?
   - Ou contradiz o que já está implementado?
   - Ou há outra abordagem já padronizada no projeto?

### Exemplo Real (Correção P0)

**❌ ERRADO (o que quase aconteceu):**
```
Problema: "Erro ao comparar datas"
Solução imediata: "Use datetime.fromisoformat()"
Sem verificar se já existe solução no projeto
```

**✅ CORRETO (o que deveria ter feito):**
```
Problema: "Erro ao comparar datas"
Estrutura: Procurar por *datas*.py, *time*.py
Encontrado: utils/interpretador_datas.py
Contrato: 
  - agora_br_aware() → datetime aware (Brasil)
  - dateutil.parser.isoparse() → parser tolerante
Decisão: Usar dateutil.parser.isoparse() + validação de tzinfo
```

### Por Que Essa Regra?

```
PADRÃO ERRADO:
Investigação → Sugerir alteração → Descobrir que já existe solução → Refazer

PADRÃO CORRETO:
Auditoria de estrutura → Entender padrões → Sugerir alteração alinhada
```

**Resultado:** economia de tempo de investigação, soluções alinhadas com o projeto, sem refatorações desnecessárias.

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

## ⚠️ Alterações em Componentes Críticos

Mudanças em componentes críticos (principal_router, event_handler, agenda_service, agenda_lock_service, session_service, firestore_service) exigem auditoria prévia de impacto, dependências e evidências.

**Procedimento completo:** `docs/procedimentos/PROCEDIMENTO_AUDITORIA_PRE_ALTERACAO.md`

---

## 🛡️ Regra de Ouro — Correções Pós-Baseline

**Princípio Fundamental:**  
Após checkpoints oficiais (ex.: baseline-216-pass), alterações devem ser incrementais, auditáveis e reversíveis.

### Fluxo Obrigatório Pós-Baseline

Toda correção funcional após um baseline validado deve seguir **obrigatoriamente** este fluxo:

1. ✅ **Auditar um único cenário ou problema**
   - Isolar o defeito específico
   - Não generalizar para múltiplos cenários
   - Criar teste de reprodução

2. ✅ **Identificar a causa raiz com evidências**
   - Arquivo + função + linha (Regra Zero)
   - Evidência operacional (log, teste, breakpoint)
   - Hipótese dominante confirmada

3. ✅ **Aplicar o menor patch possível**
   - Mudança mínima para corrigir a causa raiz
   - Não refatorar código adjacente
   - Não "melhorar" enquanto corrige

4. ✅ **Validar o cenário alvo**
   - Teste específico do defeito passa
   - Não assumir que o problema foi resolvido
   - Confirmar operacionalmente

5. ✅ **Executar regressão obrigatória**
   - P1 E2E completo (42/42 deve passar)
   - P0 Regressão completo (174/174 deve passar)
   - Nenhum novo timeout gRPC
   - Exit code 0 em todas as suites

6. ✅ **Somente após regressão verde: commit**
   - Escrever mensagem clara da correção
   - Referenciar causa raiz
   - Listar testes de validação

### Regras Invioláveis

```
❌ PROIBIDO durante correções pós-baseline:

1. Nunca corrigir múltiplos cenários na mesma alteração
   └─ Causa: Impossível determinar qual patch resolveu qual problema

2. Nunca aplicar refatorações amplas para resolver um único cenário
   └─ Causa: Aumenta risco de regressão desnecessariamente

3. Nunca prosseguir para o próximo cenário sem validar o anterior
   └─ Causa: Acumula defeitos em cascata

4. Nunca ignorar regressão em suítes estáveis
   └─ Causa: Quebra confiança no baseline

5. Nunca corrigir sem auditoria prévia
   └─ Causa: Sintomas vs. causas raiz

6. Nunca hipótese sem evidência operacional
   └─ Causa: Suposições viram bugs silenciosos
```

### Procedimento em Caso de Regressão

**Se qualquer suíte estável falhar durante regressão:**

1. ⛔ **INTERROMPER IMEDIATAMENTE**
   - Não commitar a mudança
   - Não prosseguir para próxima correção

2. 🔍 **Investigar regressão**
   - Qual teste falhou?
   - Em qual cenário?
   - Qual é a causa raiz da regressão?

3. 🔧 **Opções:**
   - Ajustar o patch para evitar regressão
   - OU reverter a mudança e abordar diferente
   - OU expandir regressão para validar caso não coberto antes

4. ✅ **Re-validar após ajuste**
   - Cenário original + testes de regressão
   - Suítes completas novamente (P1 E2E + P0)

### Exemplo Correto

```
Cenário: "Conflito de horário não detectado em contexto específico"

✅ PROCESSO:
1. Auditar: Apenas este cenário de conflito
   └─ Teste isolado que reproduz: agendamento X para slot Y com profissional Z já ocupado
   
2. Causa raiz: verificar_conflito_agenda() não considera contexto_tenant
   └─ Arquivo: services/agenda_service.py:457-489
   └─ Função: verificar_conflito_agenda()
   └─ Evidência: Log mostra tenant_id=None na busca

3. Patch mínimo: Adicionar tenant_id à query (3 linhas)
   └─ services/agenda_service.py:462: adicionar where("tenant_id", "==", tenant_id)
   └─ Não refatorar a função inteira
   └─ Não reorganizar estrutura

4. Validar: Teste de cenário passa
   └─ agendamento X para slot Y agora bloqueia corretamente
   
5. Regressão (OBRIGATÓRIA):
   └─ P1 E2E: 42/42 PASS ✅
   └─ P0 Regressão: 174/174 PASS ✅
   └─ Sem novo timeout gRPC ✅
   
6. Commit apenas após regressão verde:
   └─ "Fix: Adicionar tenant_id à verificação de conflito em agenda_service.py:462
      Causa raiz: verificar_conflito_agenda() ignorava isolamento multi-tenant
      Validação: Cenário específico + P1 E2E (42/42) + P0 (174/174)"
```

### Exemplo Incorreto

```
❌ PROCESSO PROIBIDO:

"Conflito não detectado + notificação errada + contexto desatualizado"
    └─ Múltiplos cenários em um único patch (❌ PROIBIDO #1)
    
"Vamos refatorar toda a classe agenda_service para suportar isso"
    └─ Refatoração ampla para um problema (❌ PROIBIDO #2)
    
"Mudei agenda_service.py, vou seguir para confirmar o handler"
    └─ Sem validar regressão antes (❌ PROIBIDO #3)
    
"Falhou P0 teste 47, mas é um caso raro, vou commitar mesmo"
    └─ Ignorar regressão (❌ PROIBIDO #4)
    
"Acho que o problema é no GPT" [sem verificar código]
    └─ Suposição sem auditoria (❌ PROIBIDO #5)
```

### Métrica de Conformidade

Para cada correção pós-baseline, registrar:

```
[ ] Cenário único auditado?
[ ] Causa raiz identificada com evidência (arquivo+função+linha)?
[ ] Patch mínimo aplicado?
[ ] Cenário alvo validado?
[ ] P1 E2E: 42/42 PASS?
[ ] P0 Regressão: 174/174 PASS?
[ ] Nenhum novo timeout gRPC?
[ ] Commit com causa raiz + validação?

Se qualquer [ ] não marcado: ❌ NÃO COMMITAR
```

### Objetivo

🎯 Preservar o baseline validado (216/216 PASS)  
🎯 Impedir regressões silenciosas em componentes críticos  
🎯 Manter rastreabilidade de cada correção  
🎯 Garantir que código corrigido permaneça corrigido  
🎯 Facilitar reversão de mudanças se necessário  

---

## 🧠 REGRA FUNDAMENTAL: Inteligência e Humanidade, Não Rigidez

**Status:** OBRIGATÓRIA E PERMANENTE  
**Effective:** 2026-10-18  
**Escopo:** TODO código, arquitetura, fluxo, decisão  

### Princípio Central

```
Sistema inteligente ≠ Sistema com muitas regras
Sistema inteligente = Sistema que entende CONTEXTO e INTENÇÃO
```

**O que é PROIBIDO:**

```
❌ Soluções engessadas (funciona APENAS em cenário específico)
❌ Padrões que cobrem apenas "amanhã", não "próxima segunda"
❌ Código que assume uma situação única
❌ Validações que funcionam para um caso, quebram em variação
❌ Fluxos que rejeitam por estar "fora do padrão"
```

**Exemplo de ENGESSAMENTO:**

```
❌ FIX A3 na função pergunta_amanha_mesmo_horario() apenas
   └─ Bloqueia placeholder T00:00:00 APENAS quando usuário diz "amanhã"
   └─ Não bloqueia quando usuário diz "próxima quinta" (também T00:00:00)
   └─ Resultado: Sistema inteligente em um cenário, burro em outro
```

**Exemplo de INTELIGÊNCIA:**

```
✅ Bloquear placeholder T00:00:00 SEMPRE que aparecer
   └─ Independentemente se é "amanhã", "próxima quinta", "segunda"
   └─ Lógica genérica: se data não tem hora real, pedir horário
   └─ Resultado: Sistema se adapta a qualquer situação similar
```

### Regra Prática

**Sempre que codificar um fix:**

1. ❌ Perguntar: "Como faço para funcionar em [cenário X]?"
2. ✅ Perguntar: "Qual é a regra genérica que resolve isso?"

**Exemplo:**

```
❌ ERRADO:
"Como faço para bloquear '00:00' quando é 'amanhã'?"
→ Código específico para 'amanhã'
→ Outros cenários com placeholder não funcionam

✅ CORRETO:
"Qual é a regra: Quando deve pedir horário?"
→ "Quando data não tem hora real (T00:00:00)"
→ Vale para QUALQUER data: amanhã, quinta, próxima semana
```

### Impacto no Código

**Quando implementar:**

1. ✅ Procurar por TODOS os lugares onde problema pode ocorrer
   - Não apenas o fluxo "amanhã"
   - Todos os fluxos que calculam data sem hora

2. ✅ Implementar solução genérica que funciona em TODOS
   - Não código duplicado para cada fluxo
   - Uma validação que cobre todos os casos

3. ✅ Validar que a solução é realmente genérica
   - Teste com "amanhã" → deve funcionar
   - Teste com "próxima segunda" → deve funcionar  
   - Teste com "semana que vem" → deve funcionar
   - Teste com "próxima quinta" → deve funcionar

### Quando uma Regra Está ENGESSADA

Sinais de que você caiu no engessamento:

```
🔴 "Isso funciona para cenário A"
   └─ Pergunta: e cenário B?
   
🔴 "Eu coloquei um if específico para 'amanhã'"
   └─ Pergunta: e se o usuário disser 'semana que vem'?
   
🔴 "O código assume estado_fluxo == 'agendando'"
   └─ Pergunta: e se esse estado mudar?
   
🔴 "A validação funciona apenas nessa função"
   └─ Pergunta: por que não funcionaria em outra função?
   
🔴 "Se o usuário disser X, faz Y"
   └─ Pergunta: e se o usuário disser X2 ou X3 (similar)?
```

### Teste de Generalidade

**Após escrever código, validar:**

```
Código atual funciona em:
☐ Cenário 1 (especificado)
☐ Cenário 2 (variação menor)
☐ Cenário 3 (variação maior)
☐ Cenário 4 (limite)
☐ Cenário 5 (exceção)

Se menos de 5 cenários cobertos: ⚠️ ENGESSADO
```

### Contraste: Rigidez vs Inteligência

```
RIGIDEZ:
- "Se message == 'para amanhã': fazer X"
- "Se state == 'agendando': fazer X"
- "Se horário está missing: fazer X, mas APENAS em função Z"

INTELIGÊNCIA:
- "Se data não tem hora real: pedir hora (funciona em qualquer fluxo, qualquer entrada)"
- "Se há placeholder em contexto de agendamento: solicitar clarificação (genérico)"
- "Se usuário não confirma: validar independentemente do estado (ubíquo)"
```

### Aplicação Ao FIX A3 (Exemplo Real)

```
❌ ENGESSADO:
    if state == "pergunta_amanha_mesmo_horario":
        if nova_iso.endswith("T00:00:00"):
            pedir_horario()

✅ INTELIGENTE:
    if not tem_hora_real(nova_iso):
        # funciona em QUALQUER fluxo, QUALQUER contexto
        pedir_horario()
```

### Valor da Inteligência

Quando você implementa genérico:

```
+Código menor
+Menos bugs (uma validação, não múltiplas)
+Adaptável (novo fluxo herdaa a inteligência)
+Testável (testa uma regra, não 10 cenários)
+Inteligível (quem lê sabe qual é a REGRA, não o code smell)
```

### Checklist Pré-Commit

**Antes de fazer commit, validar:**

```
[ ] Código é específico para um cenário?
    └─ Se SIM: ❌ Refatore para ser genérico
    
[ ] Validação funciona em múltiplos fluxos?
    └─ Se NÃO: ❌ Estenda para cobrir todos
    
[ ] Se mesmo padrão ocorre 3+ vezes: centralizei?
    └─ Se NÃO: ❌ Crie validação reutilizável
    
[ ] Posso descrever a REGRA geral (não apenas o caso)?
    └─ Se NÃO: ❌ Estou sendo muito específico
    
[ ] Nova pessoa entenderia por que o código existe?
    └─ Se NÃO: ❌ Documentação ou nome precisa mudar
```

---

## 🧪 PADRÃO MODELO: Testes E2E Com Webhook Real

**Status:** OBRIGATÓRIO E PERMANENTE  
**Effective:** 2026-10-19  
**Escopo:** TODO teste E2E que valida fluxo de webhook + Firestore

### Filosofia

**Testes que usam mock ou chamam handler diretamente NÃO REPRODUZEM o erro real do usuário.**

A única forma de validar fluxo real é:
1. ✅ Webhook REAL (Flask endpoint `/webhook/whatsapp`)
2. ✅ Firebase REAL (não mockar Firestore)
3. ✅ Cliente REAL (com histórico em Firestore)
4. ✅ Contexto INTACTO (não limpar prior state)
5. ✅ Fluxo COMPLETO (até o erro/resultado final)

### Arquivo Modelo

**Localização:** `tests/_modelo/test_e2e_webhook_modelo.py`

**Qualquer novo teste E2E DEVE:**
- Copiar exatamente a estrutura do modelo
- Adaptar APENAS: mensagens, cliente, validações
- Manter INTACTO: Firebase real, webhook real, patch HMAC

### Por Que Este Padrão?

**Testes mock escondem erros reais:**

```
❌ TESTE COM MOCK:
Chama handler diretamente
    ↓
Fluxo reto (sem webhook)
    ↓
Contexto limpo (sem prior state)
    ↓
Resultado: PASS (mas erro real não aparece)

✅ TESTE MODELO:
Webhook Flask real
    ↓
Firestore real é consultado/escrito
    ↓
Contexto anterior intacto
    ↓
Resultado: FAIL (reproduz erro do usuário fielmente)
```

### Estrutura Obrigatória

Cada teste modelo deve ter:

```python
# 1. Setup com cliente real
TENANT_TESTE = "7394370553"
USUARIO_NUMERO = "5511991382080"  # Cliente com histórico real

# 2. Cliente Flask (test_client)
client = app.test_client()

# 3. Patch HMAC (permite teste sem chave real)
with patch("main.validate_whatsapp_signature", return_value=True):

# 4. Payload REAL WhatsApp (não simplificado)
payload = {
    "object": "whatsapp_business_account",
    "entry": [{
        "changes": [{
            "value": {
                "metadata": {...},
                "messages": [{...}]
            }
        }]
    }]
}

# 5. POST ao endpoint real
response = client.post("/webhook/whatsapp", json=payload)

# 6. Firebase REAL (carregar contexto pós-webhook)
ctx = await carregar_contexto_temporario_v2(TENANT_TESTE, actor_id)

# 7. Validação documentada
print(f"[MSG 1] Estado: {ctx.get('estado_fluxo')}")
print(f"[MSG 1] Serviço: {ctx.get('servico')}")
```

### Checklist de Validação

Antes de considerar teste pronto:

```
☐ Usa Firebase REAL (não mocka Firestore)
☐ Usa `/webhook/whatsapp` endpoint (Flask test_client)
☐ Cliente tem histórico em Firestore
☐ NÃO limpa contexto anterior
☐ Patch HMAC está presente
☐ Fluxo vai até o fim (erro/resultado)
☐ Validações documentadas com print
☐ Async/await correto (pytest.mark.asyncio)
☐ Teste reproduz cenário do usuário fielmente
☐ Segue estrutura do modelo exatamente
```

### Exemplos de Uso

**Para criar novo teste:**

```bash
cp tests/_modelo/test_e2e_webhook_modelo.py tests/test_seu_novo_fluxo.py
```

**Adaptar APENAS:**
- Nome da função
- Mensagens do fluxo
- Validações esperadas

**MANTER IDÊNTICO:**
- Estrutura webhook
- Patch HMAC
- Acesso Firebase REAL
- Payload formato

### O Que Este Padrão Evita

```
❌ Testes que passam mas erro real ocorre
❌ Mock que mascara problemas Firestore
❌ Contexto limpo que ignora prior state
❌ Fluxo interrompido no meio
❌ Validação apenas de resposta HTTP
```

### Referência

Documentação detalhada em: `tests/_modelo/README.md`

---

## 🧪 PADRÃO OBRIGATÓRIO: Testes E2E Com Firebase Real (FASE 2)

**Status:** OBRIGATÓRIO E PERMANENTE  
**Effective:** 2026-10-20  
**Escopo:** Todos os 10+ testes P0 durante FASE 2 (Testes em Escala Real)  
**Razão:** Testes com mocks não detectam bugs reais que só aparecem com Firestore real + contexto propagado

### Regra Fundamental

```
❌ PROIBIDO em FASE 2:
- Mock de Firebase
- Confiança APENAS em return de função
- Validação que não consulta Firestore

✅ OBRIGATÓRIO em FASE 2:
- Firebase real (Firestore production-like)
- Validação até Firestore (não confiar em status code)
- Contexto carregado com carregar_contexto_temporario_v2()
- Evento encontrado no Firestore (buscar_subcolecao verificado)
- Tenant_id isolado (não vaza entre tenants)
- actor_id correto (whatsapp:{wa_id})
```

### Padrão Obrigatório para Cada Teste

**Estrutura base em 7 passos:**

```python
@pytest.mark.asyncio
async def test_p0_cenario_descricao():
    """
    [FASE 2] Teste E2E REAL até Firestore
    
    Valida:
    - Entrada → Processamento → Firestore
    - Serviço preservado (não trocado)
    - Duração do catálogo (não fallback 60 min)
    - Tenant isolado (não vaza)
    - actor_id propagado
    """
    
    # PASSO 1: Preparar (limpar contexto, definir dados únicos)
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)
    print("✓ Contexto limpo")
    
    # PASSO 2: Carregar contexto E2E (simular fluxo anterior)
    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA) or {}
    ctx["servico"] = "corte feminino"
    ctx["profissional_escolhido"] = "Gloria"
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)
    print(f"✓ Contexto preenchido: {ctx.keys()}")
    
    # PASSO 3: Processar (chamar função real, NÃO mocka)
    dados_evento = {
        "profissional": "Gloria",
        "servico": "corte feminino",
        "data_hora": "2026-12-19T08:00:00",
        "duracao": 40,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }
    resultado = await add_evento_por_gpt(None, None, dados_evento)
    print(f"✓ add_evento_por_gpt retornou: {resultado}")
    
    # PASSO 4: Validar retorno (necessário mas não suficiente)
    assert resultado is True, "Função deveria retornar True"
    print("✓ Função retornou True")
    
    # PASSO 5: Procurar NO FIRESTORE (validação crítica)
    eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
    print(f"✓ Total eventos em Firestore: {len(eventos)}")
    
    # PASSO 6: Encontrar evento (busca flexível, não assume timestamp)
    evento_encontrado = None
    for evento_id, evento_data in eventos.items():
        prof = evento_data.get("profissional", "").lower()
        serv = evento_data.get("servico", "").lower()
        if prof == "gloria" and serv == "corte feminino":
            evento_encontrado = evento_data
            evento_id_encontrado = evento_id
            break
    
    # PASSO 7: Asserção crítica (até Firestore)
    assert evento_encontrado is not None, \
        f"Evento NÃO foi criado em Firestore! Total: {len(eventos)}"
    assert evento_encontrado["servico"] == "corte feminino", \
        f"Serviço divergiu: {evento_encontrado.get('servico')}"
    assert evento_encontrado["profissional"].lower() == "gloria"
    assert evento_encontrado["tenant_id"] == TENANT_TEST
    assert evento_encontrado["duracao"] == 40, \
        f"Duração incorreta: {evento_encontrado.get('duracao')} (esperado 40)"
    
    print(f"✅ TESTE PASSOU")
    print(f"   - Evento criado: Gloria + corte feminino")
    print(f"   - Firestore confirmado")
```

### Checklist Obrigatório para Cada Teste FASE 2

**Estrutura:**
- ✅ Usa `await add_evento_por_gpt()` ou função real equivalente
- ✅ Carrega contexto com `await carregar_contexto_temporario_v2()`
- ✅ Valida NO FIRESTORE (`buscar_subcolecao()`) — NÃO apenas return
- ✅ Procura flexível (não assume timestamp específico exato)

**Campos validados:**
- ✅ `evento["servico"]` preservado (não trocado)
- ✅ `evento["profissional"]` correto
- ✅ `evento["duracao"]` do catálogo (não fallback)
- ✅ `evento["tenant_id"]` isolado e correto
- ✅ `evento["cliente_id"]` formatado com prefixo `whatsapp:`
- ✅ `evento["confirmado"]` = True

**Sem:**
- ❌ Mocks de Firebase
- ❌ Assumptions sobre timestamp
- ❌ Validação apenas de `resultado is True`

### Anti-Padrões Proibidos em FASE 2

❌ **Confiar apenas em return de função:**

```python
# ERRADO:
resultado = await add_evento_por_gpt(...)
assert resultado is True
# E se Firestore falhou? Teste passa, erro real não aparece.
```

❌ **Assumir timestamp conhecido:**

```python
# ERRADO:
evento_id = "whatsapp:5511991382080_gloria_2026-12-19_08:00"
evento = await buscar_documento(f".../Eventos/{evento_id}")
assert evento is not None
# E se timestamp variou? Teste falha mesmo com evento criado.
```

❌ **Mockar Firebase:**

```python
# ERRADO:
@patch("firebase_admin.firestore")
def test_xxx(mock_firestore):
    # REALMENTE testando Firestore? Não. Teste ilusório.
```

❌ **Limpar contexto anterior:**

```python
# ERRADO:
await limpar_contexto_agendamento(TENANT, ACTOR)  # Perde estado anterior
# FASE 2 valida fluxo CONTÍNUO, não isolado.
```

### Regras Específicas por Campo

#### Serviço
- ✅ Preservado EXATAMENTE como entrada
- ✅ NÃO trocado para outro (bug que encontramos: "corte feminino" → "coloracao")
- ✅ Salvo em campo `evento["servico"]`
- ✅ Validado que **existe no Firestore**

#### Duração
- ✅ Obtida via `listar_servicos_negocio(id_dono)` (catálogo)
- ✅ Se não em catálogo → usar `estimar_duracao()` como fallback
- ✅ NÃO hardcoded em função
- ✅ Validada em **minutos inteiros** (40, 60, 90, etc)

#### Tenant Isolation (CRÍTICO)
- ✅ Eventos de tenant A isolados de tenant B
- ✅ Validar: `evento["tenant_id"] == TENANT_TEST`
- ✅ Usar path `Clientes/{TENANT_TEST}/Eventos` (nunca path genérico)
- ✅ Query deve filtrar por tenant

#### Actor Propagation (CRÍTICO)
- ✅ `user_id` = número wa_id sem prefixo (ex: "5511991382080")
- ✅ `cliente_id` = "whatsapp:{wa_id}" com prefixo
- ✅ `tenant_id` = id resolução via `obter_id_dono(user_id)`
- ✅ Todos 3 presentes e corretos no evento Firestore

### Diferença: FASE 1 vs FASE 2

**FASE 1 (testes anteriores):**
- Focava em funcionalidade ("funciona?")
- Podia mockar Firebase
- Validava apenas return de função
- Teste isolado, não fluxo contínuo

**FASE 2 (agora):**
- Foca em confiabilidade ("funciona CORRETAMENTE?")
- Firebase REAL obrigatório
- Validação até Firestore obrigatória
- Fluxo contínuo (contexto anterior intacto)

**Transição:** Testes precisam ser reescritos para novo padrão (não backwards-compatible).

### Quando Está Pronto para FASE 3?

**Critério de liberação:**

```
✅ Todos os 10 testes P0 rodando com Firebase real
✅ ~196 cenários cobertos (todos PASS)
✅ Nenhum teste usa mock
✅ Nenhum teste assume timestamp
✅ Regressão validada (sem quebrar testes anteriores)
✅ Bugs encontrados documentados
```

---

**Última atualização:** 2026-06-23  
**Status:** Documento congelado até descongelamento comprovado  
**Adição:** Regra de Ouro — Correções Pós-Baseline (2026-06-23)  
**Adição:** Regra Fundamental — Inteligência e Humanidade, Não Rigidez (2026-10-18)  
**Adição:** Padrão Modelo — Testes E2E Com Webhook Real (2026-10-19)  
**Adição:** Padrão E2E Firebase Real — FASE 2 (2026-10-20)

---

## 🔄 P0 — ROTEAMENTO CONVERSACIONAL E RECUPERAÇÃO DE CONTEXTO

**Status:** ARQUITETURA OBRIGATÓRIA E PERMANENTE  
**Effective:** 2026-10-27  
**Escopo:** TODO roteamento de mensagens conversacionais, interpretação de intenção, gerenciamento de contexto  

### 1. OBJETIVO

Evoluir a NeoEve de um sistema que executa fluxos previamente projetados para uma secretária virtual capaz de compreender mensagens em linguagem natural, inclusive quando a conversa sai do fluxo esperado.

A evolução deve preservar integralmente os comportamentos já validados de agendamento, disponibilidade, confirmação, criação de eventos, histórico, notificações e isolamento entre tenants.

O objetivo não é cadastrar todas as frases que um cliente pode escrever. É reconhecer a intenção da mensagem atual, identificar a operação necessária e encaminhá-la para a capacidade correta do sistema.

### 2. REGRA ARQUITETURAL OBRIGATÓRIA

**A intenção da mensagem atual governa o roteamento. O estado anterior da sessão fornece contexto, mas não pode sequestrar a conversa.**

Toda mensagem recebida deve ser interpretada considerando:

1. O conteúdo da mensagem atual.
2. O contexto anterior relevante para resolver referências e ambiguidades.
3. O estado da sessão, incluindo confirmações ou operações pendentes.
4. A capacidade do sistema necessária para atender à solicitação.

O estado anterior NÃO deve determinar automaticamente que a nova mensagem pertence ao mesmo fluxo.

Uma nova mensagem pode representar:
- Continuação do atendimento atual.
- Confirmação ou rejeição de uma opção pendente.
- Correção de dados previamente informados.
- Alteração de data, horário, serviço ou profissional.
- Pergunta informativa sobre o negócio.
- Consulta ao catálogo, preços ou profissionais.
- Comparação entre serviços ou profissionais.
- Mudança de assunto.
- Cancelamento, desistência ou solicitação ambígua.

A classificação deve distinguir esses cenários antes de executar uma operação incompatível com a intenção atual.

**Exceção controlada:** mensagens curtas como "sim", "esse", "pode ser" e "com ela" podem depender do estado anterior. Nesse caso, o contexto deve ser utilizado para interpretar a mensagem, sem assumir uma confirmação quando houver ambiguidade.

### 3. SEPARAÇÃO DE RESPONSABILIDADES

#### 3.1 GPT — interpretação de linguagem

O GPT pode:
- Interpretar mensagens livres, variações linguísticas, erros ortográficos e expressões informais.
- Identificar a intenção atual.
- Extrair serviços, profissionais, datas, horários e referências contextuais.
- Distinguir uma pergunta informativa de uma solicitação operacional.
- Solicitar esclarecimento quando a intenção ou as entidades necessárias forem ambíguas.
- Produzir uma interpretação estruturada para o código consumir.

O GPT NÃO pode:
- Decidir a disponibilidade real de horários.
- Calcular duração ou conflitos.
- Inventar serviços, profissionais, preços ou dados do negócio.
- Escolher arbitrariamente um profissional quando a solicitação não permitir essa conclusão.
- Criar, alterar ou cancelar eventos diretamente.
- Substituir as validações determinísticas do sistema.

#### 3.2 Código determinístico — execução e integridade

O código continua responsável por:
- Resolver o tenant e o ator.
- Consultar o catálogo e os dados reais do Firestore.
- Determinar a duração dos serviços.
- Validar profissionais habilitados para os serviços.
- Calcular disponibilidade e detectar conflitos.
- Sugerir horários válidos.
- Validar confirmações e executar operações de agenda.
- Criar, alterar ou cancelar eventos.
- Registrar histórico e executar notificações conforme as regras existentes.

Nenhuma interpretação do GPT substitui essas validações.

#### 3.3 Resposta — resultado da operação

A resposta deve atender à intenção atual usando informações reais obtidas pelo sistema.

Perguntas informativas não devem ser convertidas artificialmente em agendamentos. Respostas de disponibilidade anteriores não devem ser repetidas quando a nova mensagem solicita outra informação.

### 4. ORDEM OBRIGATÓRIA DE DIAGNÓSTICO DO ROTEAMENTO

Antes de modificar qualquer código relacionado ao problema, reconstruir o fluxo real da mensagem.

Investigar, nesta ordem:

1. Recepção e normalização da mensagem.
2. Resolução de `tenant_id` e `actor_id`.
3. Carregamento do contexto e da sessão.
4. Classificação da intenção conversacional.
5. Regras de prioridade, validações antecipadas e bloqueios.
6. Detecção de confirmação, continuidade e ajuste incremental.
7. Chamadas ao GPT e reutilização de interpretações anteriores.
8. Seleção do handler ou serviço executor.
9. Consultas ao Firestore.
10. Montagem e envio da resposta.
11. Alterações de estado e persistência.

Identificar o primeiro ponto em que o fluxo diverge do comportamento esperado.

Não presumir que o último componente que registrou um log é a causa raiz.

Não concluir que existe um defeito no GPT, na sessão ou no validador sem evidência de execução que sustente a hipótese.

### 5. PROTOCOLO OBRIGATÓRIO: AUDITORIA ANTES DE ALTERAÇÃO

Para todo defeito de roteamento conversacional:

**Etapa A — Auditoria somente de leitura**
- Inspecionar o código existente e os testes relacionados.
- Reconstruir o caminho real da mensagem.
- Identificar as condições que determinam o fluxo escolhido.
- Examinar logs, estados da sessão e chamadas efetivamente executadas.
- Diferenciar fatos comprovados de hipóteses.
- Localizar o primeiro desvio de execução.

**Etapa B — Diagnóstico**
Apresentar:
- Sintoma observado.
- Comportamento esperado.
- Evidências do código e dos logs.
- Causa raiz comprovada ou hipóteses ainda pendentes.
- Arquivos e funções envolvidos.
- Risco de regressão.
- Menor correção tecnicamente suficiente.

**Etapa C — Autorização e implementação**
- Não alterar arquivos durante uma auditoria solicitada como somente de leitura.
- Quando houver autorização para corrigir, implementar a menor alteração necessária.
- Não fazer refatorações amplas como consequência incidental de um defeito pontual.
- Não remover validações de segurança para fazer uma mensagem passar.
- Não modificar contratos existentes sem demonstrar necessidade.

**Etapa D — Validação**
- Executar primeiro os testes diretamente relacionados à alteração.
- Executar os testes de regressão dos fluxos afetados.
- Executar testes adicionais de isolamento entre tenants e integridade da agenda quando aplicáveis.
- Interromper a sequência diante de falha, investigar e reportar; não declarar sucesso parcial como sucesso total.
- Não realizar deploy sem autorização e sem os critérios de aceite atendidos.

### 6. CASO DE REFERÊNCIA: PERGUNTA INFORMATIVA DURANTE UM FLUXO DE AGENDA

Mensagem anterior: consulta de disponibilidade com conflito de horário.

Mensagem atual:
"A Carla faz as mesmas coisas que a Bruna?"

Comportamento esperado:
1. Identificar uma comparação entre profissionais.
2. Consultar o catálogo real do tenant atual.
3. Comparar os serviços cadastrados de cada profissional.
4. Responder às diferenças e semelhanças encontradas.
5. Não repetir a resposta anterior de conflito.
6. Não criar nem modificar eventos.
7. Não descartar automaticamente o contexto de um agendamento pendente.
8. Não permitir que um estado de ajuste incremental force a execução de uma operação de agenda incompatível com a pergunta.

O exemplo deve servir como teste de comportamento, não como uma regra textual exclusiva para essa frase.

### 7. REGRA PARA ESTADO E SESSÃO

A sessão representa o estado temporário da conversa; não representa o catálogo, a agenda ou a fonte de verdade do negócio.

O contexto anterior pode ajudar a resolver referências, como:
- "E com ela?"
- "Pode ser esse."
- "Na sexta, então."
- "Faz o mesmo serviço?"

Entretanto:
- Um estado pendente não prova, por si só, que a mensagem atual é uma confirmação.
- Uma pergunta informativa não deve ser forçada para o fluxo de confirmação ou ajuste.
- Uma mudança de assunto não deve apagar dados válidos sem necessidade.
- Responder a uma pergunta lateral não deve concluir, cancelar ou alterar um agendamento pendente.
- A retomada do fluxo anterior deve respeitar o estado persistido e as regras de validade existentes.

Preservar a estrutura multi-tenant e o caminho canônico de sessão já estabelecido no projeto. Nunca utilizar dados de outro tenant para completar uma interpretação.

### 8. POLÍTICA DE USO DO GPT

Manter a classificação determinística quando ela for suficiente e confiável.

Acionar o GPT quando a interpretação de linguagem natural for necessária, especialmente diante de:
- Intenção não reconhecida.
- Pergunta informativa fora do fluxo previsto.
- Comparação ou consulta expressa de maneira não padronizada.
- Referências contextuais que exijam interpretação.
- Mensagens que não possam ser classificadas com segurança pelas regras determinísticas existentes.

Não chamar o GPT indiscriminadamente em todas as mensagens.

Não criar uma lista infinita de frases ou palavras-chave como solução principal.

Não reutilizar uma interpretação anterior quando ela não representar a mensagem atual. Reutilização de classificação deve ser justificada pela implementação e validada por testes.

Quando a interpretação continuar ambígua, solicitar esclarecimento. Nunca executar uma operação crítica com base em suposição.

### 9. TESTES DE REGRESSÃO OBRIGATÓRIOS

Para mudanças no roteamento conversacional, validar os cenários aplicáveis:

1. Consulta informativa independente.
2. Pergunta informativa durante conflito de agenda.
3. Comparação entre profissionais com catálogos diferentes.
4. Consulta de disponibilidade.
5. Confirmação explícita de agendamento pendente.
6. Rejeição de confirmação pendente.
7. Alteração de data ou horário durante um fluxo.
8. Referência contextual ambígua.
9. Mudança de assunto seguida de retomada do atendimento.
10. Mensagem com serviço inexistente no catálogo.
11. Ausência de criação ou alteração de evento em consultas informativas.
12. Isolamento entre tenants e identidade correta do ator.

Os testes devem verificar não apenas a resposta textual, mas também:
- Qual handler foi executado.
- Se o GPT foi chamado quando necessário.
- Se a interpretação correta chegou ao executor.
- Se o estado da sessão foi preservado corretamente.
- Se houve leituras ou escritas indevidas no Firestore.
- Se eventos foram criados, alterados ou cancelados indevidamente.

Preferir testes integrados ao fluxo real e Firestore real conforme a infraestrutura de testes já estabelecida no projeto. Não substituir testes reais por mocks quando isso ocultar o comportamento que se pretende validar.

### 10. CRITÉRIOS DE ACEITE

Uma correção de roteamento só pode ser considerada concluída quando:

- A mensagem atual chega ao fluxo correspondente à sua intenção.
- O contexto anterior é utilizado sem impor uma operação incompatível.
- As consultas informativas retornam dados reais do tenant correto.
- As operações críticas continuam sob validação determinística.
- Os estados pendentes são preservados ou alterados conforme as regras existentes.
- Os testes relacionados passam.
- Os testes de regressão relevantes passam.
- Não existem efeitos colaterais indevidos na agenda.
- O resultado e as limitações restantes são reportados explicitamente.

Não declarar a NeoEve pronta para deploy apenas porque o caso que originou a correção passou.

### 11. RESTRIÇÕES PERMANENTES

- Não reescrever o roteador inteiro para corrigir um caso específico.
- Não adicionar exceções textuais isoladas quando a causa for arquitetural.
- Não remover gates ou validações sem comprovar sua incompatibilidade com o contrato correto.
- Não permitir que o GPT controle disponibilidade, conflitos ou criação de eventos.
- Não alterar identificadores, caminhos de sessão ou contratos multi-tenant sem necessidade comprovada.
- Não esconder falhas de teste com `try/except` abrangente, mocks inadequados ou asserções enfraquecidas.
- Não alterar testes para fazê-los passar sem confirmar o comportamento esperado.
- Não executar operações críticas quando a intenção estiver ambígua.
- Não presumir que uma pergunta nova sempre encerra o fluxo anterior.
- Não presumir que toda mensagem pertence ao fluxo anterior.

### 12. PRINCÍPIO FINAL

**A linguagem do cliente é aberta. As capacidades do sistema são explícitas. A execução é determinística. A agenda é protegida.**

A NeoEve deve compreender formas variadas de comunicação sem exigir uma regra para cada frase. O GPT interpreta; o código valida, decide e executa; a sessão preserva o contexto necessário; o sistema responde à intenção atual.

Toda evolução deve aproximar a NeoEve de uma secretária virtual confiável, preservando os comportamentos já validados e priorizando a correção de ponta a ponta.

---

## 🚨 OBRIGATÓRIO: Monitoramento de Quota Firebase — Executar Diariamente

**REGRA CRÍTICA:** Executar monitoramento de quota Firestore **TODO DIA** no início da sessão.

**Por que:** Free tier Firebase limita 50k reads + 50k writes/dia. Sem monitoramento:
- Quota esgota silenciosamente
- Testes começam a falhar (429 error)
- Perdemos horas de testes sem saber por quê
- Credenciais podem ser rejeitadas

**Lições Históricas (2026-10-20):**
- 2026-10-17 10:31: Quota liberada, auto-cleanup executado (20 docs deletados)
- 2026-10-18-2026-10-20: Monitor **NÃO foi executado** (ficou parado 3 DIAS)
- Resultado: Quota esgotada novamente em 2026-10-20, testes bloqueados
- **Causa raiz:** Monitor não foi programado para rodar automaticamente após último check

**Comando obrigatório (INÍCIO DE CADA SESSÃO):**

```bash
cd C:\dev\neoeve
python .claude/worktrees/agent-a4cb4b1d484d31804/monitor_firebase_quota.py
```

**Saída esperada:**

```
[OK] QUOTA LIBERADA → Seguro rodar testes
[ESGOTADA] Quota ainda esgotada (429) → Aguarde ~24h
```

**Se ESGOTADA:**
- ❌ NÃO rodar testes (consomem quota desnecessariamente)
- ✅ Registrar bloqueio
- ✅ Aguardar ~24h para reset automático
- ✅ Monitor contínuo atualizará automaticamente

**Para Monitoramento Contínuo (Opcional — se configurar CI/CD):**

```bash
# Rodar background task a cada 30 minutos
python .claude/worktrees/agent-a4cb4b1d484d31804/monitor_quota_continuous.py

# Logs salvos em:
# - C:\dev\neoeve\quota_monitor.log
# - C:\dev\neoeve\.quota_state.json
```

**Checklist Pré-Testes (OBRIGATÓRIO):**

```
☐ Rodei monitor_firebase_quota.py?
☐ Status é LIBERADA?
☐ Último check foi TODAY (não data antigo)?
  
Se qualquer resposta for NÃO:
❌ Não rodar testes de migração (consomem muita quota)
✅ Verificar arquivo .quota_state.json
✅ Aguardar próximo reset automático
```

**Impacto:** Evita 6-8 horas perdidas esperando quota ser liberada, sem saber o que estava errado.

**Regra Permanente:** Esta regra não será removida até que:
1. Firebase quota seja aumentada para pagar tier, OU
2. Projeto migrate para Emulator (zero quota), OU
3. Quota seja monitorada automaticamente em CI/CD

---

