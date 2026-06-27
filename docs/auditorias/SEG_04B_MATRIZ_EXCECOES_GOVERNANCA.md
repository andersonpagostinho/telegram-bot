# SEG-04B — MATRIZ DE EXCEÇÕES DA GOVERNANÇA
## Whitelist e Blacklist Operacional

**Status:** Documentação Formal (Sem Implementação)  
**Data:** 2026-06-23  
**Baseline:** 216/216 PASS (Congelado)  
**Referência para:** SEG-05 (Implementação Sprint 1)  

---

## RESUMO EXECUTIVO

### Princípio Fundamental

```
Governança (MEC-03 + MEC-04) respeita precedência:

1. Operações Críticas (CLASSE A) — Nunca bloqueiam
2. Operações Operacionais (CLASSE B) — Podem bloquear
3. Operações Administrativas (CLASSE C) — Regras próprias

Precedência: A > B > C > Fluxo Normal
```

---

## CLASSIFICAÇÃO: 21 OPERAÇÕES

### CLASSE A: Nunca Bloqueiam (9 operações)

Operações que **sempre** executam, independente de governança.

#### A-01: Confirmação Positiva ("sim")

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato confirma agendamento: "sim" |
| **Contexto** | estado_fluxo = "aguardando_confirmacao" |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | Confirmação é resposta a ação sistema já aceitou; bloquear = agendamento travado |
| **Risco se Bloquear** | 🔴 CRÍTICO — Agendamento fica pendente indefinidamente |
| **Risco se Não Bloquear** | ✅ NENHUM — Confirmação é legítima |
| **Precedência** | Vence: responder_automaticamente = false |
| **Implementação** | Whitelist: Se aguardando_confirmacao AND msg="sim" → sempre processa |

---

#### A-02: Confirmação Negativa ("não")

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato nega agendamento: "não" |
| **Contexto** | estado_fluxo = "aguardando_confirmacao" |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | Negação é resposta a ação sistema já aceitou; contato tem direito de recusar |
| **Risco se Bloquear** | 🔴 CRÍTICO — Agendamento fica pendente; contato sem opcao de recusar |
| **Risco se Não Bloquear** | ✅ NENHUM — Negação é legítima |
| **Precedência** | Vence: responder_automaticamente = false |
| **Implementação** | Whitelist: Se aguardando_confirmacao AND msg="não" → sempre processa |

---

#### A-03: Cancelamento

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato cancela agendamento: "cancelar horário" ou similar |
| **Contexto** | Qualquer estado_fluxo |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | Cancelamento é direito inalienável do cliente; pausado não nega direito |
| **Risco se Bloquear** | 🔴 CRÍTICO — Cliente fica preso a agendamento contra vontade |
| **Risco se Não Bloquear** | ✅ NENHUM — Cancelamento é legítimo |
| **Precedência** | Vence: responder_automaticamente = false |
| **Implementação** | Whitelist: Se eh_cancelamento(msg) → sempre processa |

---

#### A-04: Refinamento de Cancelamento

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato detalha cancelamento: "cancelar, mas deixar proxima semana" |
| **Contexto** | Durante processamento de cancelamento |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | É continuação de ação cancelamento (A-03), que é protegida |
| **Risco se Bloquear** | 🔴 CRÍTICO — Refinamento perdido, cliente fica sem opcao |
| **Risco se Não Bloquear** | ✅ NENHUM — Refinamento é legítimo |
| **Precedência** | Vence: responder_automaticamente = false |
| **Implementação** | Whitelist: Se estado_fluxo = "cancelando" AND msg relacionada → processa |

---

#### A-05: Onboarding

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Sistema ativa onboarding para novo dono |
| **Contexto** | Dono novo (primeiro acesso) |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | Onboarding é pré-requisito; dono novo não pode estar pausado antes de onboarding |
| **Risco se Bloquear** | 🔴 CRÍTICO — Dono não consegue ativar negócio |
| **Risco se Não Bloquear** | ✅ NENHUM — Onboarding é necessário |
| **Precedência** | Vence: responder_automaticamente = false, modo_dono = qualquer |
| **Implementação** | Sem verificação: onboarding sempre executa |

---

#### A-06: Comando Administrativo

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato/Dono executa comando: /pausar, /retomar, /status, /silencioso, /admin, /normal |
| **Contexto** | Qualquer estado_fluxo |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | Comandos são meta-operações que controlam governança; devem funcionar sempre |
| **Risco se Bloquear** | 🔴 CRÍTICO — Pausado não consegue se despauzar; silencioso não consegue volta ao normal |
| **Risco se Não Bloquear** | ✅ NENHUM — Comandos são controle |
| **Precedência** | Vence: responder_automaticamente = false, modo_dono = qualquer |
| **Implementação** | Whitelist: Se eh_comando_admin(msg) → sempre processa |

---

#### A-07: Retorno de Cliente

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Cliente que foi desagendado volta após dias |
| **Contexto** | Nova sessão (sem contexto anterior) |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | Nova sessão não herda pausa anterior (sem Governanca doc); cliente recomeça fresco |
| **Risco se Bloquear** | ⚠️ MÉDIO — Cliente volta mas fica travado |
| **Risco se Não Bloquear** | ✅ NENHUM — Retorno é novo fluxo |
| **Precedência** | Vence: Nenhuma (Governanca não existe em nova sessão) |
| **Implementação** | Sem verificação: nova sessão não carrega Governanca anterior |

---

#### A-08: Cancelamento em Silencioso

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Dono em modo silencioso cancela seu agendamento |
| **Contexto** | modo_dono = "silencioso" AND eh_cancelamento(msg) |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | Cancelamento (A-03) vence qualquer modo |
| **Risco se Bloquear** | 🔴 CRÍTICO — Dono fica preso a agendamento |
| **Risco se Não Bloquear** | ✅ NENHUM — Dono tem direito |
| **Precedência** | Vence: modo_dono = "silencioso" |
| **Implementação** | Whitelist: Cancelamento sempre vence modo |

---

#### A-09: Contacto Profile

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Sistema carrega perfil do contato (nome, histórico) |
| **Contexto** | Qualquer operação |
| **Classe** | **A** — Nunca bloqueia |
| **Bloqueável?** | ❌ NÃO |
| **Justificativa** | Carregamento de dados é operação interna de sistema, não bloqueia por governança |
| **Risco se Bloquear** | 🔴 CRÍTICO — Sistema não consegue processar nada |
| **Risco se Não Bloquear** | ✅ NENHUM — É operação técnica |
| **Precedência** | N/A (Executado antes de verificar governanca) |
| **Implementação** | Sem verificação: sempre carrega contexto |

---

### CLASSE B: Podem Bloquear (10 operações)

Operações que **podem** ser bloqueadas por governança, sendo respeitados os defaults.

#### B-01: Agendamento Novo

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato solicita novo agendamento: "Agende corte com Bruna amanhã" |
| **Contexto** | Fora de fluxo confirmacao |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM |
| **Justificativa** | É ação ativa; pausado quer pausar automação |
| **Risco se Bloquear** | ✅ BAIXO — Coerente com intenção de pausa |
| **Risco se Não Bloquear** | ⚠️ MÉDIO — Pausado recebe resposta quando não quer |
| **Precedência** | Bloqueia: responder_automaticamente = false |
| **Implementação** | Verificar: If pausado AND eh_agendamento_novo(msg) → Bloquear |
| **Default** | Sem Governanca → Permite (responder_automaticamente = true implícito) |

---

#### B-02: Consulta de Disponibilidade

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato pergunta disponibilidade: "Quando tem horário disponível?" |
| **Contexto** | Fora de fluxo confirmacao |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM |
| **Justificativa** | É ação ativa que leva a agendamento |
| **Risco se Bloquear** | ✅ BAIXO — Coerente com pausa |
| **Risco se Não Bloquear** | ⚠️ MÉDIO — Pausado recebe sugestão quando não quer |
| **Precedência** | Bloqueia: responder_automaticamente = false |
| **Implementação** | Verificar: If pausado AND eh_consulta_disponibilidade(msg) → Bloquear |
| **Default** | Sem Governanca → Permite |

---

#### B-03: Consulta de Agenda

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Cliente/Dono pergunta sua agenda: "Qual é meu horário?" |
| **Contexto** | Qualquer estado |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM (com ressalva para dono) |
| **Justificativa** | É consulta que pode levar a ajustes |
| **Risco se Bloquear** | ⚠️ MÉDIO (cliente) — Coerente / 🔴 CRÍTICO (dono) — Sem acesso |
| **Risco se Não Bloquear** | ✅ BAIXO — Informação é legítima |
| **Precedência** | Bloqueia: responder_automaticamente = false (cliente) |
| **Implementação** | Cliente pausado: Bloqueia / Dono silencioso: Permite (DECISÃO FUTURA) |
| **Default** | Sem Governanca → Permite |

---

#### B-04: Follow-up

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Sistema oferece follow-up: "Quer marcar próximo corte?" |
| **Contexto** | Após agendamento confirmado |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM |
| **Justificativa** | É ação ativa de sistema |
| **Risco se Bloquear** | ✅ BAIXO — Coerente com pausa |
| **Risco se Não Bloquear** | ⚠️ MÉDIO — Pausado recebe follow-up quando não quer |
| **Precedência** | Bloqueia: responder_automaticamente = false |
| **Implementação** | Verificar: If pausado → Não envia follow-up |
| **Default** | Sem Governanca → Permite |

---

#### B-05: Ajuste Incremental

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato altera agendamento durante fluxo: "Mas prefiro 16h ao invés de 15h" |
| **Contexto** | Dentro de fluxo agendamento (estado_fluxo != "vazio") |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM (com ressalva) |
| **Justificativa** | É ação que muda agendamento proposto |
| **Risco se Bloquear** | ⚠️ MÉDIO — Interrompe fluxo ativo |
| **Risco se Não Bloquear** | ✅ BAIXO — Ajuste é legítimo |
| **Precedência** | Whitelist: Se dentro de fluxo ativo → Permite mesmo pausado |
| **Implementação** | If pausado AND estado_fluxo = vazio → Bloqueia / If estado_fluxo != vazio → Permite |
| **Default** | Sem Governanca → Permite |

---

#### B-06: Conflito + Alternativa

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Sistema detecta conflito e oferece alternativas: "Bruna não tem, mas Maria está disponível" |
| **Contexto** | Dentro de fluxo agendamento |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM (com ressalva) |
| **Justificativa** | É resposta a agendamento que pode ser bloqueado |
| **Risco se Bloquear** | ⚠️ MÉDIO — Interrompe fluxo ativo |
| **Risco se Não Bloquear** | ✅ BAIXO — Alternativa é ajuda |
| **Precedência** | Whitelist: Se dentro de fluxo ativo → Permite mesmo pausado |
| **Implementação** | If pausado AND estado_fluxo != vazio → Permitir sugestão (continuidade) |
| **Default** | Sem Governanca → Permite |

---

#### B-07: Reagendamento

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato quer mudar agendamento existente: "Quero marcar outro dia" |
| **Contexto** | Com agendamento anterior |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM |
| **Justificativa** | É ação ativa que cria novo agendamento |
| **Risco se Bloquear** | ✅ BAIXO — Pausado quer pausa |
| **Risco se Não Bloquear** | ⚠️ MÉDIO — Pausado reagenda |
| **Precedência** | Bloqueia: responder_automaticamente = false |
| **Implementação** | Verificar: If pausado AND eh_reagendamento(msg) → Bloquear |
| **Default** | Sem Governanca → Permite |

---

#### B-08: Escolha de Horário Sugerido

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato escolhe entre opções de horário oferecidas: "Prefiro 15h" |
| **Contexto** | Após sistema ofertar opções |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM (com ressalva) |
| **Justificativa** | É resposta a agendamento em fluxo ativo |
| **Risco se Bloquear** | ⚠️ MÉDIO — Interrompe fluxo |
| **Risco se Não Bloquear** | ✅ BAIXO — Escolha é legítima |
| **Precedência** | Whitelist: Se dentro de fluxo ativo → Permite mesmo pausado |
| **Implementação** | If pausado AND estado_fluxo = "oferecendo_opcoes" → Permite (continuidade) |
| **Default** | Sem Governanca → Permite |

---

#### B-09: Escolha de Profissional Sugerido

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Contato escolhe entre profissionais sugeridos: "Prefiro a Bruna" |
| **Contexto** | Após sistema oferecer profissionais |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM (com ressalva) |
| **Justificativa** | É resposta a agendamento em fluxo ativo |
| **Risco se Bloquear** | ⚠️ MÉDIO — Interrompe fluxo |
| **Risco se Não Bloquear** | ✅ BAIXO — Escolha é legítima |
| **Precedência** | Whitelist: Se dentro de fluxo ativo → Permite mesmo pausado |
| **Implementação** | If pausado AND estado_fluxo = "escolhendo_profissional" → Permite |
| **Default** | Sem Governanca → Permite |

---

#### B-10: Histórico

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Cliente pede histórico de agendamentos: "Quais foram meus agendamentos anteriores?" |
| **Contexto** | Qualquer estado |
| **Classe** | **B** — Pode bloquear |
| **Bloqueável?** | ✅ SIM (recomendado: permitir) |
| **Justificativa** | É consulta leitura, não ação |
| **Risco se Bloquear** | ⚠️ MÉDIO — Cliente sem acesso a histórico |
| **Risco se Não Bloquear** | ✅ BAIXO — Histórico é informação passada |
| **Precedência** | Recomendação: Permitir histórico (informação passiva) |
| **Implementação** | If pausado AND eh_consulta_historico(msg) → Permitir (não é ação) |
| **Default** | Sem Governanca → Permite |

---

### CLASSE C: Regras Próprias (2 operações)

Operações que têm regras especiais, não seguindo A nem B.

#### C-01: Cadastro Profissional

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Admin/Dono cadastra novo profissional |
| **Contexto** | Operação administrativa |
| **Classe** | **C** — Regras próprias |
| **Bloqueável?** | ⚠️ DEPENDE DO MODO |
| **Justificativa** | Dono silencioso = sem IA, mas cadastro administrativo? |
| **Risco se Bloquear** | ⚠️ MÉDIO — Dono não consegue cadastrar |
| **Risco se Não Bloquear** | ✅ BAIXO — Cadastro é operacional |
| **Precedência** | DECISÃO: Modo silencioso = sem IA, mas admin manual funciona? |
| **Implementação** | ADIAR para Sprint 2+ — Detalhar se modo afeta cadastro |
| **Default** | Sem Governanca → Permite |

---

#### C-02: Lembrete Automático

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Sistema envia lembrete: "Lembrança: seu agendamento é amanhã" |
| **Contexto** | Sistema, não conversacional |
| **Classe** | **C** — Regras próprias |
| **Bloqueável?** | 🔴 CRÍTICO — SEPARAR CANAIS |
| **Justificativa** | Lembrete é notificação de negócio, não automação IA |
| **Risco se Bloquear** | 🔴 CRÍTICO — Cliente perde confirmação |
| **Risco se Não Bloquear** | ✅ NENHUM — Cliente recebe informação |
| **Precedência** | Notificação > Governanca (DECISÃO: Sprint 3+) |
| **Implementação** | ADIAR para Sprint 3+ — Implementar canal notificação separado |
| **Default** | Sem Governanca → Sempre envia |

---

#### C-03: Notificação Automática

| Aspecto | Definição |
|---------|-----------|
| **Operação** | Sistema notifica: "Seu profissional confirmou para amanhã" |
| **Contexto** | Sistema, não conversacional |
| **Classe** | **C** — Regras próprias |
| **Bloqueável?** | 🔴 CRÍTICO — SEPARAR CANAIS |
| **Justificativa** | Notificação é alerta de status, não automação IA |
| **Risco se Bloquear** | 🔴 CRÍTICO — Cliente não sabe status |
| **Risco se Não Bloquear** | ✅ NENHUM — Cliente recebe alerta |
| **Precedência** | Notificação > Governanca (DECISÃO: Sprint 3+) |
| **Implementação** | ADIAR para Sprint 3+ — Implementar canal notificação separado |
| **Default** | Sem Governanca → Sempre envia |

---

## RESUMO OPERACIONAL

### Tabela de Bloqueabilidade

| # | Operação | Classe | Bloqueável | Pausado | Silencioso | Notas |
|---|----------|--------|-----------|---------|------------|-------|
| A-01 | Confirmação positiva ("sim") | **A** | ❌ | ✅ Processa | ✅ Processa | Whitelist obrigatória |
| A-02 | Confirmação negativa ("não") | **A** | ❌ | ✅ Processa | ✅ Processa | Whitelist obrigatória |
| A-03 | Cancelamento | **A** | ❌ | ✅ Processa | ✅ Processa | Whitelist obrigatória |
| A-04 | Refinamento cancelamento | **A** | ❌ | ✅ Processa | ✅ Processa | Whitelist obrigatória |
| A-05 | Onboarding | **A** | ❌ | ✅ Processa | ✅ Processa | Sem verificação |
| A-06 | Comando administrativo | **A** | ❌ | ✅ Processa | ✅ Processa | Whitelist obrigatória |
| A-07 | Retorno cliente | **A** | ❌ | ✅ Processa | ✅ Processa | Sem Governanca nova sessão |
| A-08 | Cancelamento em silencioso | **A** | ❌ | ✅ Processa | ✅ Processa | Vence modo |
| A-09 | Carregamento contexto | **A** | ❌ | ✅ Processa | ✅ Processa | Antes de verificar |
| B-01 | Agendamento novo | **B** | ✅ | ❌ Bloqueia | ❌ Bloqueia | Esperado |
| B-02 | Consulta disponibilidade | **B** | ✅ | ❌ Bloqueia | ❌ Bloqueia | Esperado |
| B-03 | Consulta agenda | **B** | ✅ | ❌ Bloqueia | ⚠️ DECISÃO | Ressalva dono |
| B-04 | Follow-up | **B** | ✅ | ❌ Bloqueia | ❌ Bloqueia | Não envia |
| B-05 | Ajuste incremental | **B** | ✅ | ⚠️ Whitelist | ⚠️ Whitelist | Se fluxo ativo |
| B-06 | Conflito + alternativa | **B** | ✅ | ⚠️ Whitelist | ⚠️ Whitelist | Se fluxo ativo |
| B-07 | Reagendamento | **B** | ✅ | ❌ Bloqueia | ❌ Bloqueia | Esperado |
| B-08 | Escolha horário | **B** | ✅ | ⚠️ Whitelist | ⚠️ Whitelist | Se fluxo ativo |
| B-09 | Escolha profissional | **B** | ✅ | ⚠️ Whitelist | ⚠️ Whitelist | Se fluxo ativo |
| B-10 | Histórico | **B** | ✅ | ⚠️ Permitir | ⚠️ Permitir | Informação passiva |
| C-01 | Cadastro profissional | **C** | ⚠️ | ⚠️ DECISÃO | ⚠️ DECISÃO | Sprint 2+ |
| C-02 | Lembrete automático | **C** | 🔴 | SEPARAR CANAL | SEPARAR CANAL | Sprint 3+ |
| C-03 | Notificação automática | **C** | 🔴 | SEPARAR CANAL | SEPARAR CANAL | Sprint 3+ |

---

## WHITELIST DEFINITIVA (Sprint 1)

### Operações que SEMPRE Executam

```python
WHITELIST_SEMPRE = [
    "confirmacao_positiva",      # "sim"
    "confirmacao_negativa",      # "não"
    "cancelamento",              # Cancelar agendamento
    "refinamento_cancelamento",  # Detalhe de cancelamento
    "onboarding",                # Novo dono
    "comando_administrativo",    # /pausar, /retomar, etc
    "carregamento_contexto",     # Perfil, histórico
]
```

### Operações que Respeitam Fluxo Ativo

```python
WHITELIST_FLUXO_ATIVO = [
    "ajuste_incremental",        # Se estado_fluxo != vazio
    "conflito_alternativa",      # Se estado_fluxo != vazio
    "escolha_horario",           # Se estado_fluxo = oferecendo_opcoes
    "escolha_profissional",      # Se estado_fluxo = escolhendo_profissional
]
```

### Operações que Respeitam Tipo de Consulta

```python
WHITELIST_CONSULTA_LEITURA = [
    "consulta_agenda",           # Leitura (permitir para dono)
    "historico",                 # Informação passada
]
```

---

## BLACKLIST DEFINITIVA (Sprint 1)

### Operações que SEMPRE Bloqueiam se Pausado

```python
BLACKLIST_PAUSADO = [
    "agendamento_novo",          # Nova ação
    "consulta_disponibilidade",  # Leva a agendamento
    "reagendamento",             # Altera agendamento
    "follow_up",                 # Ação de sistema
]
```

### Operações que SEMPRE Bloqueiam se Silencioso

```python
BLACKLIST_SILENCIOSO = [
    "agendamento_novo",          # Ação ativa
    "consulta_disponibilidade",  # Leva a agendamento
    "resposta_ia",               # Qualquer IA
    "follow_up",                 # Ação de sistema
]
```

---

## ORDEM DE PRECEDÊNCIA

### Hierarquia de Decisão

```
1. Classe A (Whitelist)
   └─ Sem exceção, sempre executa

2. Whitelist Fluxo Ativo
   └─ Se estado_fluxo != vazio, permite continuidade

3. Whitelist Consulta Leitura
   └─ Se tipo_consulta = "leitura", permite informação

4. Blacklist Pausado
   └─ Se responder_automaticamente = false, bloqueia

5. Blacklist Silencioso
   └─ Se modo_dono = "silencioso", bloqueia

6. Padrão Governanca
   └─ Respeita governanca se nenhuma whitelist aplica
```

### Pseudocódigo de Decisão

```python
def verificar_bloqueio(msg, estado_fluxo, governanca, user_id, dono_id):
    operacao = classificar_operacao(msg)
    
    # 1. Classe A (nunca bloqueia)
    if operacao in WHITELIST_SEMPRE:
        return Permitir(operacao)
    
    # 2. Whitelist Fluxo Ativo
    if operacao in WHITELIST_FLUXO_ATIVO:
        if estado_fluxo != "vazio":
            return Permitir(operacao)
    
    # 3. Whitelist Consulta Leitura
    if operacao in WHITELIST_CONSULTA_LEITURA:
        if eh_consulta_leitura(msg):
            return Permitir(operacao)
    
    # 4. Governanca
    if user_id != dono_id:  # Cliente normal
        if governanca.get("responder_automaticamente") == False:
            if operacao in BLACKLIST_PAUSADO:
                return Bloquear(operacao, "Estou pausado")
    
    elif user_id == dono_id:  # Dono
        modo = governanca.get("modo_dono", "normal")
        if modo == "silencioso":
            if operacao in BLACKLIST_SILENCIOSO:
                return Bloquear(operacao, "Modo silencioso")
        elif modo == "admin":
            if not eh_comando_admin(msg):
                return Bloquear(operacao, "Modo admin")
    
    # Padrão: permitir
    return Permitir(operacao)
```

---

## REGRA ESPECIAL: CONTATO PAUSADO

### Validação Formal

**Cenário:** Contato pausado durante confirmação

#### Caso 1: Mensagem "sim"

```
Contato: pausado (responder_automaticamente = false)
Contexto: estado_fluxo = "aguardando_confirmacao"
Mensagem: "sim"

Decisão: ✅ PROCESSAR
Justificativa: A-01 (Confirmação Positiva) em WHITELIST_SEMPRE
Precedência: Whitelist A > Governanca MEC-03
```

#### Caso 2: Mensagem "não"

```
Contato: pausado (responder_automaticamente = false)
Contexto: estado_fluxo = "aguardando_confirmacao"
Mensagem: "não"

Decisão: ✅ PROCESSAR
Justificativa: A-02 (Confirmação Negativa) em WHITELIST_SEMPRE
Precedência: Whitelist A > Governanca MEC-03
```

#### Caso 3: Mensagem "cancelar meu horário"

```
Contato: pausado (responder_automaticamente = false)
Contexto: Qualquer estado_fluxo
Mensagem: "cancelar meu horário"

Decisão: ✅ PROCESSAR
Justificativa: A-03 (Cancelamento) em WHITELIST_SEMPRE
Precedência: Whitelist A > Governanca MEC-03
```

#### Caso 4: Mensagem "quero marcar horário"

```
Contato: pausado (responder_automaticamente = false)
Contexto: estado_fluxo = "vazio" (fora de fluxo)
Mensagem: "quero marcar horário"

Decisão: ❌ BLOQUEAR
Justificativa: B-01 (Agendamento Novo) em BLACKLIST_PAUSADO
Precedência: Governanca MEC-03 > Operação B
Resposta: "Estou pausado no momento"
```

---

### Formalização

**REGRA ESPECIAL CONFIRMADA:**

```
┌─────────────────────────────────────────┐
│ Pausado durante Confirmação             │
├─────────────────────────────────────────┤
│ "sim"          → ✅ PROCESSAR (A-01)   │
│ "não"          → ✅ PROCESSAR (A-02)   │
│ "cancelar"     → ✅ PROCESSAR (A-03)   │
│ "novo horário" → ❌ BLOQUEAR (B-01)    │
└─────────────────────────────────────────┘
```

---

## DECISÕES PENDENTES

### Sprint 1 (Implementação)

✅ **CONFIRMADO:**
- Whitelist A (9 operações) — Sempre permitir
- Whitelist Fluxo Ativo — Continuidade em fluxo
- Blacklist Pausado — Operações B bloqueadas
- Blacklist Silencioso — Operações B bloqueadas

### Sprint 2+ (Refinamento)

⚠️ **ADIAR:**
- Diferenciação Dono Leitura/Ação (B-03)
- Cadastro em Silencioso (C-01)

### Sprint 3+ (Separação)

🔴 **CRÍTICO:**
- Canal Notificação vs Automação (C-02, C-03)

---

## PARECER FINAL

### Matriz de Exceções Validada

**Status:** ✅ PRONTA PARA IMPLEMENTAÇÃO

**Conformidade:**
- ✅ 21 operações classificadas
- ✅ Whitelist e Blacklist definidas
- ✅ Ordem de precedência explícita
- ✅ Regra especial confirmada
- ✅ Decisões futuras documentadas

**Risco Sprint 1:**
- ✅ BAIXO (whitelists garantem compatibilidade)

**Baseline Impact:**
- ✅ ZERO (nenhuma mudança sem Governanca ativa)

---

**Matriz:** SEG-04B  
**Referência para:** SEG-05 (Implementação)  
**Status:** ✅ Documentação Formal Concluída

**⏹️ PARAR AQUI — Sem código, sem patch, sem teste.**
