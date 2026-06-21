# MATRIZ CERTIFICAÇÃO P1 — Próximas Prioridades

**Status:** 📋 PLANEJAMENTO  
**Data:** 2026-06-21  
**Versão:** 1.0  

---

## 🎯 Escopo P1

Após certificação P0 (174 cenários), as seguintes áreas estão qualificadas para investigação P1.

**Nota:** P1 itens são opcionais, baseados em prioridade de negócio e risco operacional.

---

## 📊 Matriz Geral

| # | Área | Implementado? | Testado? | Certificado? | Risco | Complexidade | Prioridade | Status |
|---|------|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 1 | ClienteProfile | ❓ | ❌ | ❌ | 🔴 ALTO | 🟢 MÉDIO | 🔴 P0 | Investigação |
| 2 | Memória Longa | ❌ | ❌ | ❌ | 🟡 MÉDIO | 🔴 ALTO | 🟡 P1 | Planejamento |
| 3 | Perfil Comportamental | ❌ | ❌ | ❌ | 🟡 MÉDIO | 🔴 ALTO | 🟡 P1 | Planejamento |
| 4 | Preferências Automáticas | ❌ | ❌ | ❌ | 🟢 BAIXO | 🟢 MÉDIO | 🟡 P1 | Planejamento |
| 5 | Histórico Inteligente | ❌ | ❌ | ❌ | 🟡 MÉDIO | 🔴 ALTO | 🟡 P1 | Planejamento |
| 6 | Recorrência | ❌ | ❌ | ❌ | 🟡 MÉDIO | 🟡 MÉDIO-ALTO | 🟡 P1 | Planejamento |
| 7 | Recovery Completo | ❌ | ❌ | ❌ | 🔴 ALTO | 🟡 MÉDIO-ALTO | 🔴 P0 | Investigação |
| 8 | Retenção/Follow-up P1/P2 | ❌ | ❌ | ❌ | 🟢 BAIXO | 🟢 MÉDIO | 🟢 P2 | Planejamento |
| 9 | Cancelamento Inteligente Avançado | ❌ | ❌ | ❌ | 🟡 MÉDIO | 🟡 MÉDIO-ALTO | 🟡 P1 | Planejamento |
| 10 | Onboarding Inteligente | ❌ | ❌ | ❌ | 🟢 BAIXO | 🟡 MÉDIO-ALTO | 🟡 P1 | Planejamento |

---

## 🔴 P0 — Crítico para Produção Robusta

### 1. ClienteProfile — Influencia Sem Decidir

**Risco:** 🔴 ALTO  
**Complexidade:** 🟢 MÉDIO  
**Status:** Necessário antes de qualquer funcionalidade que use histórico  

#### O que é?

Modelo de dados que captura preferências e padrões de um cliente:
- Profissional preferido
- Serviço mais comum
- Horário preferido
- Tipo de pagamento
- Notas/observações

#### Por que é P0?

ClienteProfile pode **influenciar** recomendações sem DECIDIR automaticamente.

**Exemplo perigoso:**
```
❌ Cliente: "Quero mudar de profissional desta vez"
   ClienteProfile: "Mas seu histórico mostra Bruna"
   Sistema: Ignora pedido, agenda com Bruna
   → ERRO CRÍTICO
```

**Exemplo correto:**
```
✅ Cliente: "Agende para mim"
   ClienteProfile: Bruna (profissional anterior)
   Sistema: "Última vez foi com Bruna. Confirma?"
   Cliente: "Sim" ou "Não"
   → Decisão é do cliente
```

#### O que precisa ser certificado?

- [ ] ClienteProfile não sobrescreve pedido explícito
- [ ] ClienteProfile preenche draft (cliente pode alterar)
- [ ] ClienteProfile informa disponibilidade à motor (não cria evento)
- [ ] ClienteProfile respeita conflito (não força agendamento)
- [ ] ClienteProfile não pula passo obrigatório do fluxo
- [ ] Permissões: apenas cliente pode ver seu profile
- [ ] Isolamento multi-tenant: profile não vaza entre clientes
- [ ] Atualização: profile evolui com cada agendamento
- [ ] Limpeza: profile removido quando cliente deletado
- [ ] Recovery: profile recuperado após restart

#### Risco de não certificar

Se ClienteProfile não for certificado primeiro:
- Todas as funcionalidades P1 que o usam ficarão inseguras
- Risco de histórico sobrescrever pedido explícito
- Risco de agendamento automático sem autorização
- Risco de cliente descobrir evento criado sem confirmar

---

### 2. Recovery Completo Após Restart

**Risco:** 🔴 ALTO  
**Complexidade:** 🟡 MÉDIO-ALTO  
**Status:** Necessário para produção confiável  

#### O que é?

Garantia de que após reinicialização do sistema:
- Contextos temporários são recuperados
- Eventos em processamento são completados
- Notificações pendentes são disparadas
- Sessões expiradas são limpas
- Estado é consistente

#### Por que é P0?

Produção pode reiniciar a qualquer momento:
- Deploy
- Crash
- Manutenção
- Atualização

Sem recovery, usuários perdem agendamentos em progresso.

#### O que precisa ser certificado?

- [ ] Contexto em processo: recuperado e continuável
- [ ] Evento pendente: criação completada ou revertida
- [ ] Notificação pendente: recuperada e disparada
- [ ] Draft agendamento: preservado ou limpo conforme regra
- [ ] Sessão expirada: limpeza automática
- [ ] Lock de evento: liberado após timeout
- [ ] Transação incompleta: finalizada atomicamente
- [ ] Auditoria: registra recovery como evento
- [ ] Retry: falhas são reprocessadas com backoff
- [ ] Logs: rastreamento completo de recuperação

#### Risco de não certificar

Se recovery não for testado:
- Usuários podem perder agendamentos
- Sistema pode ficar em estado inconsistente
- Eventos podem duplicar
- Notificações podem ser perdidas

---

## 🟡 P1 — Aprimoramento de Experiência

### 3. Memória Longa — Histórico Conversacional

**Risco:** 🟡 MÉDIO  
**Complexidade:** 🔴 ALTO  
**Status:** Melhor experiência, não essencial para funcionalidade  

#### O que é?

Capacidade de conversa a conversa de lembrar:
- Conversas anteriores (não apenas agendamentos)
- Preferências mencionadas (mas não anotadas)
- Comportamentos do cliente
- Padrões de uso

#### Exemplo

```
Conversa 1:
Cliente: "Gosto de cabelo comprido, mas cortei pra fim de ano"
(Memória longa nota: cliente gosta de cabelo comprido)

Conversa 2 (mês depois):
IA: "Vejo que você gosta de cabelo comprido... vamos deixar crescer?"
(Referência à preferência anterior)
```

#### Desafios

- Implementação: Onde armazenar conversas?
- Privacidade: Que dados guardar?
- Relevância: Como saber qual contexto é importante?
- Expiração: Quando esquecer informações antigas?

#### Risco de não certificar

Sem certificação:
- Conversas podem ser perdidas
- Informações sensíveis podem vazar
- Memória pode ficar corrompida
- Sistema pode gerar contextos falsos

---

### 4. Perfil Comportamental — Padrões de Cliente

**Risco:** 🟡 MÉDIO  
**Complexidade:** 🔴 ALTO  
**Status:** Insights úteis, não essencial  

#### O que é?

Análise de padrões no histórico do cliente:
- Frequência de agendamento
- Horários preferidos
- Duração típica
- Profissionais comuns
- Sazonalidade

#### Exemplo

```
Perfil de João:
- Frequência: A cada 3 semanas (segunda-feira, 14:00)
- Profissional: Bruna (80%), Carla (20%)
- Serviço: Corte + Barba (sempre 40min)
- Nota: Não agenda em julho/dezembro (férias)

IA usa: "João, sua próxima manutenção é semana que vem. Mesmo horário?"
```

#### Desafios

- Coleta: Qual dado é relevante?
- Análise: Como identificar padrão de ruído?
- Viés: Perfil pode ser enviesado (poucas amostras)?
- Atualização: Quando esquecer padrão antigo?

#### Risco de não certificar

Sem certificação:
- Padrões podem ser incorretos
- Previsões podem falhar
- Pode gerar contextos enviesados
- Usuário pode se sentir stalked

---

### 5. Preferências Automáticas — Defaults Inteligentes

**Risco:** 🟢 BAIXO  
**Complexidade:** 🟢 MÉDIO  
**Status:** Melhora UX, baixo risco  

#### O que é?

Sistema aprende preferências do cliente e preenche defaults:
- Profissional padrão
- Serviço padrão
- Horário padrão
- Duração padrão
- Notas padrão

#### Exemplo

```
Cliente comum tem: Corte de cabelo com Bruna, segunda-feira às 14h, 30 min

Novo agendamento:
IA: "Cortinho de sempre? [Bruna, seg 14h, 30min] Ou quer mudar?"
Cliente: "Sim, de boa" ou "Não, dessa vez quero com Carla"
```

#### Desafios

- Consentimento: Explicar ao cliente que sistema "aprendeu" preferências
- Controle: Cliente pode optar por NÃO ter defaults
- Atualização: Quando preferências mudam?
- Fallback: E se cliente não tem histórico?

#### Risco de não certificar

Sem certificação:
- Defaults podem ser impostos contra vontade
- Cliente pode se sentir monitorado
- Não há controle de desabilitar
- Pode pular confirmação importante

---

### 6. Histórico Inteligente — Sugestões Contextuais

**Risco:** 🟡 MÉDIO  
**Complexidade:** 🔴 ALTO  
**Status:** Experiência aprimorada, complexidade significativa  

#### O que é?

Sistema oferece sugestões baseado em histórico do cliente:
- "Você agendou com Bruna em maio, quer de novo?"
- "Sua última manutenção foi há 3 semanas"
- "Primeira vez há 6 meses? Pode ser hora de novo corte"
- "Domingo passado você mencionou querer testar novo serviço"

#### Desafios

- Contexto: Quando é relevante trazer histórico?
- Frequência: Com que intervalo fazer sugestões?
- Privacidade: Qual informação expor?
- Rejeição: Como cliente diz "não me sugira mais"?

#### Risco de não certificar

Sem certificação:
- Sugestões podem ser intrusivas
- Contexto errado levando a sugestões irrelevantes
- Privacidade comprometida

---

### 7. Recorrência — Agendamentos Repetitivos

**Risco:** 🟡 MÉDIO  
**Complexidade:** 🟡 MÉDIO-ALTO  
**Status:** Reduz atrito para agendamentos frequentes  

#### O que é?

Cliente agenda de forma recorrente:
- "Manicure toda segunda-feira às 10h"
- "Cabelo a cada 3 semanas"
- "Hidratação primeira segunda do mês"

Sistema:
- Cria eventos futuros automaticamente (com confirmação)
- Notifica cliente antes de cada
- Permite exceções ("pule essa semana")

#### Desafios

- Autorização: Cliente autoriza recorrência?
- Exceções: Como lidar com "pule essa semana"?
- Profissional indisponível: O que faz?
- Fim: Como cliente cancela recorrência?

#### Risco de não certificar

Sem certificação:
- Eventos podem ser criados sem autorização
- Exceções podem não ser respeitadas
- Recorrência pode não parar

---

### 8. Cancelamento Inteligente Avançado

**Risco:** 🟡 MÉDIO  
**Complexidade:** 🟡 MÉDIO-ALTO  
**Status:** Aprimoramento, não essencial  

#### O que é?

Sistema detecta sinais de cancelamento mais sutis:
- "Hmmm, talvez não..."
- "Tô pensando se..." (hesitação)
- "Deixa marcar pra semana que vem" (adiamento genuíno)
- "Talvez com outro profissional" (cancelamento implícito)

#### Desafios

- Detecção: Diferença entre hesitação e cancelamento real
- Falso positivo: Interromper fluxo baseado em "hmm" errado
- Confiança: Quando certeza é alta o suficiente?
- Recuperação: Se errou, como recuperar?

#### Risco de não certificar

Sem certificação:
- Falsos positivos cancelam agendamentos reais
- Falsos negativos perdem sinais de cancelamento
- Usuário frustrado

---

### 9. Onboarding Inteligente

**Risco:** 🟢 BAIXO  
**Complexidade:** 🟡 MÉDIO-ALTO  
**Status:** Melhora primeira experiência  

#### O que é?

Primeira conversa guida e adaptativa:
- Identificar tipo de cliente (novo, recorrente, referência)
- Explicar como funciona o sistema
- Coletar informações básicas
- Oferecer promoção ou boas-vindas
- Criar ClienteProfile inicial

#### Exemplo

```
Novo cliente:
IA: "Bem-vindo! Sou a NeoEve. Como posso ajudar?"
Cliente: "Quero cortar cabelo"
IA: "Primeira vez aqui? Deixa me te apresentar..."
(Explica fluxo, serviços disponíveis)
```

#### Desafios

- Detecção: Como saber se é novo?
- Customização: Mensagens variam por tipo de cliente?
- Duração: Quanto de onboarding é demais?
- Conversão: Onboarding leva a agendamento?

#### Risco de não certificar

Sem certificação:
- Novos clientes não entendem como funciona
- Fluxo pode confundir
- Taxa de abandono alta

---

### 10. Retenção e Follow-up P1/P2

**Risco:** 🟢 BAIXO  
**Complexidade:** 🟢 MÉDIO  
**Status:** Engajamento, não essencial  

#### O que é?

Estratégia de retenção e follow-up:
- **P1:** Após agendamento ("Como foi?")
- **P2:** Semanas depois ("Hora de manutenção?")
- Reengajamento: Cliente inativo há 6 meses

#### Exemplo

```
P1 (1-2 dias após): "João, como foi com a Bruna? Sua próxima?"
P2 (3 semanas): "Hora de refresh! Mesmo horário?"
P3 (6 meses): "Você está sumindo! Vem fazer manutenção?"
```

#### Desafios

- Timing: Quando exatamente enviar mensagem?
- Frequência: Não bombardear cliente
- Consentimento: Cliente optou por receber?
- Personalização: Mensagens variam por cliente?

#### Risco de não certificar

Sem certificação:
- Mensagens podem ser intrusivas
- Spam pode levar a bloqueio
- Cliente pode se sentir assediado

---

## 📋 Metodologia de Certificação P1

Cada item P1 segue o mesmo rigor que P0:

1. ✅ **Criação de bateria de testes**
   - N cenários (depende de complexidade)
   - Ambiente: Firestore Real
   - Mocks: Nenhum

2. ✅ **Execução contra sistema real**
   - Descoberta de comportamento (não assunção)
   - Identificação de não-implementado
   - Bugs encontrados e corrigidos

3. ✅ **Auditoria formal**
   - Resultados consolidados
   - Matriz de validações
   - Status de certificação

4. ✅ **Commit e documentação**
   - Código de teste
   - Arquivo de auditoria
   - Referência de commit

---

## 🎯 Roadmap Sugerido

### Trim 1 — Fundação Crítica

```
Semana 1-2:  ClienteProfile (segurança)
Semana 3-4:  Recovery Completo (confiabilidade)
Semana 5-6:  Refinamento + testes P1
```

**Objetivo:** Ter P0 + ClienteProfile + Recovery formalmente certificados

---

### Trim 2 — Inteligência

```
Semana 1-2:  Memória Longa (exploração)
Semana 3-4:  Perfil Comportamental
Semana 5-6:  Histórico Inteligente
Semana 7-8:  Refinamento
```

**Objetivo:** Sistema aprender sobre clientes de forma segura

---

### Trim 3 — Automação

```
Semana 1-2:  Preferências Automáticas
Semana 3-4:  Recorrência
Semana 5-6:  Cancelamento Avançado
Semana 7-8:  Refinamento
```

**Objetivo:** Reduzir atrito para casos comuns

---

### Trim 4+ — Engajamento

```
Sequencial:  Onboarding
             Retenção/Follow-up
             Refinamentos finais
```

**Objetivo:** Crescimento de base de clientes

---

## 🔗 Relações de Dependência

```
ClienteProfile [CRÍTICO]
    ↓ (precisa de)
    ├─ Recovery Completo [CRÍTICO]
    └─ Firestore Schema v2 (suportar novos campos)
    ↓ (habilitador para)
    ├─ Preferências Automáticas [P1]
    ├─ Memória Longa [P1]
    ├─ Perfil Comportamental [P1]
    └─ Histórico Inteligente [P1]
        ↓ (habilitador para)
        ├─ Recorrência [P1]
        ├─ Onboarding [P1]
        └─ Retenção [P1]
            ↓ (habilitador para)
            └─ Cancelamento Avançado [P1]
```

**Implicação:** Não há paralelo. ClienteProfile → Recovery → resto.

---

## 💾 Estrutura de Testes P1

Cada área P1 terá:

```
tests/p1_<area>_completo.py
├─ 15-30 cenários (depende de complexidade)
├─ Firestore real
├─ Descoberta de comportamento
└─ Resultado: resultado_p1_<area>.json

docs/auditorias/P1_<AREA>_REAL.md
├─ Objetivo
├─ Resultados (tabela)
├─ Validações críticas
├─ Bugs encontrados
├─ Status de certificação
└─ Data
```

---

## 📊 Critério de Sucesso P1

Cada area P1 é certificada apenas quando:

```
✅ Bateria 100% PASS (não há "parcialmente implementado")
✅ Nenhum vazamento multi-tenant
✅ Nenhuma sobrescrita de pedido explícito
✅ Nenhum passo obrigatório pulado
✅ Nenhuma inconsistência de estado
✅ Auditoria completa registra ações
✅ Recovery funciona após restart
✅ Zero bugs remanescentes
✅ Testes cobrindo: feliz + ambíguo + persona + continuidade
✅ Integração com P0 não quebrada (regressão 174/174 PASS)
```

---

## 🚀 Implementação Imediata

### Fase 1 — ClienteProfile Safety Spec

**Antes de qualquer código:**

Criar: `docs/policies/SPEC_SEGURANCA_CLIENTEPROFILE_NAO_DECIDE.md`

Conteúdo obrigatório:
- [ ] Regra: "ClienteProfile influencia, não decide"
- [ ] 10 cenários proibidos (automação sem confirmação)
- [ ] Checklist de code review
- [ ] Exemplos de código ✅ e ❌
- [ ] Testes que validam a regra

**Objetivo:** Evitar implementação errada (automação perigosa) desde o início.

---

### Fase 2 — Recovery Design

**Antes de qualquer código:**

Criar: `docs/design/DESIGN_RECOVERY_COMPLETO.md`

Conteúdo obrigatório:
- [ ] Scenarios recovery (restart, crash, timeout)
- [ ] Estados que precisam ser recuperados
- [ ] Garantias de atomicidade
- [ ] Timeout/retry strategy
- [ ] Exemplos arquiteturais
- [ ] Testes de simulação

---

## 📈 Priorização Dinâmica

**Conforme baterias P1 forem executadas:**

Se ClienteProfile revelar novos bugs: → Priorizar Recovery  
Se Recovery ficar complexo: → Simplificar escopo  
Se tempo permitir: → Começar Memória Longa  

**Decisão de priorização: Quinzenal com dados de testes reais**

---

## 📋 Checklist de Lançamento P1

Antes de considerar qualquer área P1 como "certificada para produção":

- [ ] 100% dos testes passaram
- [ ] Auditoria formal completada
- [ ] Zero regressões em P0 (174/174 PASS)
- [ ] Documentação descreve comportamento observado
- [ ] Bugs encontrados foram corrigidos ou documentados
- [ ] Code review aprovado
- [ ] Deploy plan documentado
- [ ] Rollback plan documentado
- [ ] Monitoramento definido
- [ ] Commit feito com referência completa

---

## 🎓 Aprendizados P0 Aplicáveis a P1

1. **Firestore Real é mandatório** — Sem testes reais, bugs escapam
2. **Determinismo antes de IA** — Lógica crítica nunca delega ao GPT
3. **Descoberta bate Assunção** — Sempre validar comportamento real
4. **Regressão é obrigatória** — Toda correção pode quebrar algo
5. **Multi-tenant é invariante** — Isolamento não é negociável
6. **Auditoria rastreia tudo** — Sem logs, não é certificado

---

## 🔐 Política de P1

**Nenhuma funcionalidade P1 é liberada sem:**

1. ✅ Bateria de testes própria (20+ cenários)
2. ✅ Auditoria formal documentada
3. ✅ Regressão P0 confirmada (174/174 PASS)
4. ✅ Bugs encontrados corrigidos
5. ✅ Security review (especialmente se cliente-facing)
6. ✅ Monitoramento definido
7. ✅ Rollback plan documentado

**Falha em qualquer critério: P1 retorna ao planejamento**

---

**Status:** 📋 MATRIZ CRIADA  
**Próximo passo:** ClienteProfile Investigation  
**Data:** 2026-06-21  

Pronto para Fase P1 - Maturação de Funcionalidades.

