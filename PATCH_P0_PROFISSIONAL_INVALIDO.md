# 🔧 PATCH P0: Profissional Explícito Que Não Atende Serviço

**Data:** 2026-06-16  
**Status:** ✅ IMPLEMENTADO E TESTADO  
**Prioridade:** P0 (comportamento esperado)

---

## 📋 Resumo

**Problema:** Usuário menciona profissional que não atende o serviço solicitado.
- Entrada: "Quero agendar corte com Carla"
- Carla não atende corte
- Comportamento anterior: ❌ Pergunta genérica "Qual profissional você prefere?"
- Comportamento novo: ✅ Informa "Carla não atende corte. Com quem você prefere?"

**Solução:** Detecção de profissional inválido antes de resposta genérica.

---

## 🔧 Alteração de Código

### Arquivo: `handlers/acao_handler.py`
**Localização:** Linhas 382-396 (estado `aguardando_profissional`)  
**Tipo:** Adição de lógica

#### Código Original (ANTES)
```python
# 🎯 Identifica profissional com base na mensagem original
profissional_escolhido = None
for nome in disponiveis:  # ❌ Procura APENAS em disponiveis
    if unidecode(nome.lower()) in texto_normalizado:
        profissional_escolhido = nome
        break

# ✅ Se não encontrou profissional, pede para informar
if not profissional_escolhido:
    return "Qual profissional você prefere? (ex: Joana, Bruna, Carla...)"
```

#### Código Novo (DEPOIS)
```python
# 🎯 Identifica profissional com base na mensagem original
profissional_escolhido = None
for nome in disponiveis:
    if unidecode(nome.lower()) in texto_normalizado:
        profissional_escolhido = nome
        break

# 🔍 PATCH P0: Se não encontrou em disponiveis, procura em TODOS os profissionais
# para detectar se foi mencionado mas não atende o serviço
if not profissional_escolhido:
    print("🔎 [PATCH] Procurando profissional em TODOS os cadastrados...")
    tenant_id = await obter_id_dono(user_id)
    todos_profissionais = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    servico = sessao.get("servico")
    servicos_busca = servico if isinstance(servico, list) else [servico] if servico else []

    # Busca quem atende o serviço
    prof_que_atendem = await buscar_profissionais_por_servico(servicos_busca, user_id) if servicos_busca else {}

    # Procura nome mencionado em TODOS os profissionais
    profissional_mencionado = None
    for nome in todos_profissionais.keys():
        if unidecode(nome.lower()) in texto_normalizado:
            profissional_mencionado = nome
            break

    # Se encontrou um profissional mencionado
    if profissional_mencionado:
        print(f"✅ [PATCH] Profissional mencionado encontrado: {profissional_mencionado}")

        # Verifica se atende o serviço
        if profissional_mencionado not in prof_que_atendem:
            print(f"❌ [PATCH] {profissional_mencionado} não atende {servico}")

            # Monta resposta informando que não atende
            servico_atual = sessao.get("servico", "esse serviço")
            lista = ", ".join(disponiveis) if disponiveis else "ninguém"

            return (
                f"*{profissional_mencionado}* não atende {servico_atual}.\n"
                f"Para *{servico_atual}*, posso verificar com: {lista}.\n"
                f"Qual você prefere?"
            )

# ✅ Se não encontrou profissional, pede para informar
if not profissional_escolhido:
    return "Qual profissional você prefere? (ex: Joana, Bruna, Carla...)"
```

---

## 📊 Mudanças Detalhadas

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Busca de profissional** | Apenas em `disponiveis` | Primeiro em `disponiveis`, depois em todos |
| **Detecção de profissional inválido** | ❌ Não detecta | ✅ Detecta e informa |
| **Resposta ao usuário** | Genérica | Específica com motivo |
| **Preservação de contexto** | Sim | Sim (sem mudança) |
| **Estado do fluxo** | Permanece `aguardando_profissional` | Permanece `aguardando_profissional` |

---

## ✅ Teste Implementado

**Arquivo:** `tests/test_profissional_explicito_nao_atende_servico.py`

### Estrutura do Teste
```python
test_profissional_explicito_nao_atende_servico()
  → Simula usuário mencionando "Carla"
  → Carla não atende "corte"
  → Bruna, Gloria, Joana atendem "corte"
  → Verifica resposta e contexto
```

### Validações (10 assertions)
- ✅ Resposta menciona "Carla"
- ✅ Resposta informa que "não atende"
- ✅ Resposta menciona "corte"
- ✅ Resposta lista profissionais válidos (Bruna/Gloria/Joana)
- ✅ Draft preservou serviço
- ✅ Draft preservou data
- ✅ Draft preservou hora
- ✅ Draft preservou lista de disponíveis
- ✅ Estado permanece `aguardando_profissional`
- ✅ Profissional não foi preenchido (ainda aguardando)

### Resultado do Teste
```
================================================================================
TESTE: Profissional Explícito Que Não Atende Serviço
================================================================================

📨 Entrada: Carla

📤 Resposta obtida:
*Carla* não atende corte.
Para *corte*, posso verificar com: Bruna, Gloria, Joana.
Qual você prefere?

✅ Resposta menciona 'Carla'
✅ Resposta informa que Carla não atende o serviço
✅ Resposta menciona 'corte'
✅ Resposta lista profissionais que atendem corte
✅ Draft preservou serviço
✅ Draft preservou data
✅ Draft preservou hora
✅ Draft preservou lista de disponíveis
✅ Estado continua aguardando_profissional
✅ Profissional não foi preenchido (aguardando escolha)

Resultado: 10/10 validações passaram

✅ TESTE PASSOU!
```

---

## 🔄 Regressão

O patch não modifica:
- ✅ Fluxo normal quando profissional existe em `disponiveis`
- ✅ Fluxo normal quando não há profissional mencionado
- ✅ Preservação de contexto (serviço, data, hora)
- ✅ Continuidade do atendimento
- ✅ Estados da máquina (permanecem iguais)

---

## 📚 Funções Reutilizadas

Nenhuma função nova foi criada. O patch usa:

1. **`buscar_subcolecao()`** — Já importada, já usada
   - Localização: linha 3
   - Uso: buscar todos os profissionais do tenant

2. **`obter_id_dono()`** — Já importada, já usada
   - Localização: linha 3
   - Uso: resolver tenant_id

3. **`buscar_profissionais_por_servico()`** — Já importada, já usada
   - Localização: linha 5-9
   - Uso: validar profissional × serviço

4. **`unidecode()`** — Já importada, já usada
   - Localização: linha 11
   - Uso: normalizar nomes para comparação

---

## 🎯 Aplicabilidade em Runners

O cenário de "profissional explícito inválido" ainda não estava coberto pelos runners existentes:

- ❌ `runner_stress_profissional_alternativo_completo.py` — Cobre profissional alternativo por conflito, não por serviço inválido
- ❌ `runner_stress_multientidades_agendamento.py` — Cobre multitenant, não este caso
- ❌ Outros runners — Não cobrem este cenário específico

**Recomendação:** Adicionar este cenário em um dos runners existentes ou criar novo runner dedicado.

---

## 🔐 Segurança

### Validações de Entrada
- ✅ Normalização com `unidecode` (já usada no projeto)
- ✅ Busca em chaves do dicionário (não em valores)
- ✅ Comparação case-insensitive
- ✅ Nenhum input é diretamente executado

### Proteção contra RMW
- ✅ Sem modificação de Firestore
- ✅ Sem atualização de sessão
- ✅ Apenas leitura e resposta

---

## 📈 Impacto

### Complexidade
- ⬆️ Ligeiro aumento (1 busca adicional em alguns casos)
- ✅ Boundado: máximo `len(todos_profissionais)` iterações

### Performance
- ⬇️ Apenas quando profissional não encontrado em `disponiveis`
- ⬇️ Uma única busca em Firestore (já feita em paralelo em `buscar_profissionais_por_servico`)

### UX
- ⬆️ Melhor: usuário entende por que profissional não foi aceito
- ⬆️ Mais contextual: mensagem específica ao invés de genérica

---

## ✅ Checklist de Conclusão

- [x] Código implementado
- [x] Teste escrito e passando
- [x] Sem funções helpers novos
- [x] Sem breaking changes
- [x] Sem regressão
- [x] Validações de segurança
- [x] Documentação completa
- [ ] Adicionado em runner (opcional - pode ser feito depois)

---

## 📝 Próximos Passos

1. **Integração em CI/CD** — Adicionar teste em pipeline
2. **Coverage em runners** — Adicionar cenário a um runner existente
3. **Teste manual** — Validar com dados reais
4. **Monitoramento** — Rastrear se cenário ocorre em produção

---

## 📞 Referência

**Auditoria:** `AUDITORIA_CAUSA_RAIZ_PROFISSIONAL_INVALIDO.md`  
**Manual (regra violada):** `prompts/manual_secretaria.py` seção 7.4  
**Regra CLAUDE.md:** Semântica Antes de Código

---

**Implementado por:** Claude Code  
**Data:** 2026-06-16  
**Versão:** 1.0
