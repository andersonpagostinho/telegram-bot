# SPEC ONBOARDING DONO AUTOMÁTICO — Mapeamento Completo

**Status:** 📋 ESPECIFICAÇÃO (não implementado)  
**Data:** 2026-06-21  
**Versão:** 1.0  

---

## 🎯 Objetivo

Definir todos os cadastros e fluxo necessário para que NeoEve configure um novo negócio por conversa automática, sem formulário manual, habilitando o dono a agendar clientes imediatamente após conclusão do onboarding.

---

## 📋 Cadastros Obrigatórios

Mínimo necessário para funcionar:

| # | Cadastro | Descrição | Tipo | Exemplo |
|---|----------|-----------|------|---------|
| 1 | Negócio | Nome do salão/negócio | String | "Salão da Maria" |
| 2 | Tipo Negócio | Categoria | Enum | Salão, Spa, Clínica, etc |
| 3 | Dono | Nome do dono | String | "Maria Silva" |
| 4 | Email Dono | Contato | Email | maria@email.com |
| 5 | Horário Funcionamento | Expediente padrão | TimeRange | Seg-Sex: 9h-18h, Sab: 9h-14h |
| 6 | Profissionais | Pelo menos 1 | List | Bruna, Carla, João |
| 7 | Serviços | Pelo menos 1 | List | Corte, Escova, Hidratação |
| 8 | Duração Serviço | Tempo de atendimento | Minutes | Corte: 30min, Escova: 40min |
| 9 | Vínculo P-S | Profissional executa serviço | Relation | Bruna faz Corte e Escova |
| 10 | Regras de Agenda | Validação de agendamento | Rules | Conflito detectado, sugestão ativada |
| 11 | Notificações | Ativação de notifs | Config | Lembrete 30min antes |
| 12 | Mensagens Básicas | Respostas padrão | Template | "Bem-vindo ao Salão da Maria!" |

---

## 🎁 Cadastros Opcionais

Podem ser adicionados depois:

| # | Cadastro | Tipo | Exemplo | Fallback |
|---|----------|------|---------|----------|
| 1 | Preços | Decimal | Corte: R$ 50 | Sem preço (informação) |
| 2 | Endereço Completo | String | Rua X, 123, Apto 4 | Nenhum (usável assim) |
| 3 | Horários Individuais | TimeRange per profissional | Bruna: Seg-Qua 9-17 | Usa horário negócio |
| 4 | Política Cancelamento | Config | Mínimo 24h de aviso | Padrão (48h) |
| 5 | Exceções/Feriados | DateList | 25/12, 01/01, Carnaval | Nenhuma (dia normal) |
| 6 | Redes Sociais | URL | Instagram, WhatsApp | Nenhuma (não notifica) |
| 7 | Foto Negócio | Image | Logo ou foto salão | Avatar genérico |
| 8 | Descrição Negócio | Text | "Salão de cabelo há 10 anos" | Tipo de negócio |

---

## 🔄 Ordem do Onboarding

### Fluxo Conversacional (Usuário-Centrado)

```
1. Boas-vindas e contexto
   ↓
2. Nome do negócio?
   ↓
3. Que tipo de negócio?
   ↓
4. Horário de funcionamento?
   ↓
5. Profissionais (nomes)?
   ↓
6. Serviços que oferece?
   ↓
7. Duração de cada serviço?
   ↓
8. Qual profissional faz qual serviço?
   ↓
9. Preço dos serviços? (opcional)
   ↓
10. Confirmação de todos os dados
   ↓
11. Teste de agendamento (criar evento dummy)
   ↓
12. Ativação do negócio
   ↓
13. Próximos passos
```

### Fluxo Técnico (Motor Determinístico)

```
1. Validar tenant_id (criar se novo)
   ↓
2. Salvar Negócio em Configuracao
   ↓
3. Salvar Dono info
   ↓
4. Criar AgendaPadrao (horários)
   ↓
5. Salvar Profissionais list
   ↓
6. Salvar Serviços list
   ↓
7. Salvar Duração cada serviço
   ↓
8. Salvar Vínculos P-S
   ↓
9. Criar AgendaLocks (bloqueios iniciais)
   ↓
10. Ativar NotificacoesConfig
   ↓
11. Teste (agendar evento dummy)
   ↓
12. Marcar onboarding_status = completo
   ↓
13. Ativar tenant para uso
```

---

## 💾 Estrutura Firestore Esperada

### Path Base
```
Clientes/{tenant_id}/
```

### Coleções Criadas Durante Onboarding

#### 1. Configuracao
```
Clientes/{tenant_id}/Configuracao/negocio
{
  "nome_negocio": "Salão da Maria",
  "tipo_negocio": "Salao",
  "descricao": "Salão de cabelo há 10 anos",
  "email_dono": "maria@email.com",
  "onboarding_status": "completo|em_progresso|nao_iniciado",
  "onboarding_etapa": 5,
  "criada_em": "2026-06-21T10:00:00",
  "ativada_em": "2026-06-21T10:30:00",
  "tenant_id": "{tenant_id}",
  "versao_onboarding": "1.0"
}
```

#### 2. Profissionais
```
Clientes/{tenant_id}/Profissionais/{prof_id}
{
  "nome": "Bruna",
  "email": "bruna@email.com",
  "telefone": "11999999999",
  "ativo": true,
  "criada_em": "2026-06-21T10:05:00",
  "tenant_id": "{tenant_id}",
  "onboarding": true  # Marcador de profissional criado no onboarding
}
```

#### 3. ServicosNegocio
```
Clientes/{tenant_id}/ServicosNegocio/{servico_id}
{
  "nome": "Corte",
  "descricao": "Corte de cabelo",
  "duracao_minutos": 30,
  "preco": 50.00,
  "ativo": true,
  "criada_em": "2026-06-21T10:10:00",
  "tenant_id": "{tenant_id}",
  "onboarding": true
}
```

#### 4. VinculosProfissionalServico
```
Clientes/{tenant_id}/VinculosProfissionalServico/{vinculo_id}
{
  "profissional_id": "bruna_id",
  "profissional_nome": "Bruna",
  "servico_id": "corte_id",
  "servico_nome": "Corte",
  "ativo": true,
  "criada_em": "2026-06-21T10:15:00",
  "tenant_id": "{tenant_id}",
  "onboarding": true
}
```

#### 5. AgendaPadrao
```
Clientes/{tenant_id}/AgendaPadrao/negocio
{
  "segunda": {
    "hora_inicio": "09:00",
    "hora_fim": "18:00",
    "ativo": true,
    "intervalo_minutos": 30
  },
  "terca": { ... },
  "quarta": { ... },
  "quinta": { ... },
  "sexta": { ... },
  "sabado": {
    "hora_inicio": "09:00",
    "hora_fim": "14:00",
    "ativo": true
  },
  "domingo": {
    "ativo": false
  },
  "criada_em": "2026-06-21T10:20:00",
  "tenant_id": "{tenant_id}",
  "onboarding": true
}
```

#### 6. AgendaPadraoIndividual (Opcional)
```
Clientes/{tenant_id}/AgendaPadraoIndividual/{prof_id}
{
  "profissional_id": "bruna_id",
  "segunda": { ... },  # Se diferente da agenda padrão
  "criada_em": "...",
  "tenant_id": "{tenant_id}"
}
```

#### 7. NotificacoesConfig
```
Clientes/{tenant_id}/NotificacoesConfig/negocio
{
  "lembrete_ativado": true,
  "minutos_antes_lembrete": 30,
  "tolerance_minutos": 5,
  "aging_tolerance_minutos": 10,
  "timezone": "America/Sao_Paulo",
  "criada_em": "2026-06-21T10:25:00",
  "tenant_id": "{tenant_id}",
  "onboarding": true
}
```

#### 8. MensagensBasicas (Opcional)
```
Clientes/{tenant_id}/MensagensBasicas/negocio
{
  "boas_vindas": "Bem-vindo ao Salão da Maria!",
  "confirmacao_agendamento": "Seu agendamento foi confirmado!",
  "cancelamento": "Seu agendamento foi cancelado.",
  "lembrete": "Não esqueça seu agendamento amanhã às 14h com Bruna.",
  "criada_em": "2026-06-21T10:30:00",
  "tenant_id": "{tenant_id}",
  "onboarding": true
}
```

#### 9. Sessoes (Criada Automaticamente)
```
Clientes/{tenant_id}/Sessoes/{user_id}
{
  "tenant_id": "{tenant_id}",
  "actor_id": "{dono_id}",
  "actor_tipo": "dono",
  "estado_fluxo": "onboarding_completo",
  "onboarding_status": "completo",
  "onboarding_etapa": 13,
  "timestamp": "2026-06-21T10:35:00"
}
```

---

## 🔄 Estados de Sessão (Estado Fluxo)

```
onboarding_inicio
    ↓
aguardando_nome_negocio
    ↓
aguardando_tipo_negocio
    ↓
aguardando_horario_funcionamento
    ↓
aguardando_profissionais
    ↓
aguardando_servicos
    ↓
aguardando_duracoes
    ↓
aguardando_vinculos
    ↓
aguardando_confirmacao_onboarding
    ↓
validando_dados_onboarding
    ↓
criando_estrutura_firestore
    ↓
testando_agendamento
    ↓
onboarding_completo
    ↓
negocio_ativado
```

### Estados Especiais

```
onboarding_erro                    # Algo deu errado
    → mostrar erro
    → oferecer retry
    → manter dados coletados

onboarding_aguardando_revisao      # Antes de final
    → mostrar resumo
    → pedir confirmação
    → permitir voltar e alterar
```

---

## 🧠 Regra Central — Arquitetura de Decisão

### Hierarquia de Responsabilidade

```
GPT (Camada 1 — Interpretação)
├─ Extrai: nome_negocio, tipo, horários, nomes
├─ Normaliza: "seg-sex 9-18" → formato estruturado
├─ Pergunta: "Qual tipo de negócio?"
└─ NÃO cria evento, NÃO altera Firestore, NÃO avança etapa

Motor Determinístico (Camada 2 — Validação)
├─ Valida: formato, conflito, completude
├─ Transforma: dados extraídos em schema Firestore
├─ Persiste: salva em coleções corretas
├─ Avança etapa: muda estado_fluxo
└─ Garante: atomicidade, consistência, isolamento

Firestore Real (Camada 3 — Persistência)
├─ Schema validado
├─ Transações atomicamente garantidas
├─ Multi-tenant isolado
└─ Recovery possível após restart
```

### Nunca Delegado ao GPT

```
❌ GPT NÃO decide qual etapa prosseguir
❌ GPT NÃO altera estado_fluxo
❌ GPT NÃO cria documento em Firestore
❌ GPT NÃO avalia se onboarding está completo
❌ GPT NÃO autoriza ativação de tenant
```

### Sempre Determinístico

```
✅ Motor valida segundo regra explícita
✅ Firestore é fonte única de verdade
✅ Estados são máquina de estados rigorosa
✅ Transições só ocorrem com validação
✅ Rollback automático se erro
```

---

## ✅ Critério de Conclusão do Onboarding

Onboarding é considerado **COMPLETO** quando:

```
ESTADO FIRESTORE:
✅ onboarding_status = "completo"
✅ onboarding_etapa = 13

DADOS OBRIGATÓRIOS PRESENTES:
✅ Configuracao/negocio.nome_negocio (string não vazio)
✅ Configuracao/negocio.tipo_negocio (enum válido)
✅ Configuracao/negocio.email_dono (email válido)
✅ Profissionais/ (pelo menos 1 documento)
✅ ServicosNegocio/ (pelo menos 1 documento)
✅ VinculosProfissionalServico/ (pelo menos 1 vínculo)
✅ AgendaPadrao/negocio (horários para todos os 7 dias)
✅ NotificacoesConfig/negocio (configuração presente)

VALIDAÇÕES:
✅ Nenhum profissional sem serviço
✅ Nenhum serviço sem profissional
✅ Todos os serviços têm duração > 0
✅ Horários não contêm conflitos (ex: fim < início)
✅ Pelo menos 1 dia com horário ativo

ATIVAÇÃO:
✅ Tenant criado e isolado
✅ Sessão inicial criada com estado onboarding_completo
✅ Primeiro agendamento foi testado com sucesso
✅ Dono pode fazer login e usar sistema

RESULTADO:
✅ Dono pode agendar clientes imediatamente
✅ Sem dependência de formulário manual
✅ Sistema totalmente funcional
```

---

## 📊 Matriz Completa de Campos

| Campo | Obrigatório? | Onde Salva | Pergunta ao Dono | Fallback | Validação |
|-------|:---:|---|---|---|---|
| **nome_negocio** | ✅ | Configuracao/negocio | "Qual é o nome do seu negócio?" | Erro (obrigatório) | Não vazio, < 100 chars |
| **tipo_negocio** | ✅ | Configuracao/negocio | "Que tipo? [Salão/Spa/Clínica/...]" | Erro (obrigatório) | Enum válido |
| **email_dono** | ✅ | Configuracao/negocio | "Seu email?" | Erro (obrigatório) | Regex email |
| **nome_dono** | ✅ | Configuracao/negocio | "Seu nome?" | Erro (obrigatório) | Não vazio |
| **segunda.inicio** | ✅ | AgendaPadrao/negocio | "Que horas abre na segunda?" | 9:00 | HH:MM, 0-23:59 |
| **segunda.fim** | ✅ | AgendaPadrao/negocio | "Que horas fecha?" | 18:00 | HH:MM, > início |
| **profissional_1.nome** | ✅ | Profissionais/{id} | "Nome do primeiro profissional?" | Erro (obrigatório) | Não vazio |
| **profissional_n.nome** | ✅ | Profissionais/{id} | "Próximo profissional? (ou 'pronto')" | Pronto | Não vazio |
| **servico_1.nome** | ✅ | ServicosNegocio/{id} | "Qual serviço oferece?" | Erro (obrigatório) | Não vazio |
| **servico_n.nome** | ✅ | ServicosNegocio/{id} | "Próximo serviço? (ou 'pronto')" | Pronto | Não vazio |
| **servico.duracao_minutos** | ✅ | ServicosNegocio/{id} | "Quanto tempo leva [Corte]?" | 30 | > 0, ≤ 480 |
| **vinculo.prof-servico** | ✅ | VinculosProfissionalServico/{id} | "[Bruna] faz [Corte]?" | "Sim" (assume sim) | Prof existe AND Serviço existe |
| **servico.preco** | ❌ | ServicosNegocio/{id} | "Preço do [Corte]?" | Nenhum (sem preço) | ≥ 0, ≤ 9999 |
| **horario_individual** | ❌ | AgendaPadraoIndividual/{prof_id} | "[Bruna] tem horário diferente?" | Usa agenda padrão | Não vazio se fornecido |
| **politica_cancelamento** | ❌ | PoliticaCancelamento/negocio | "Prazo mínimo de cancelamento?" | 48 horas | > 0 horas |
| **feriados** | ❌ | AgendaExcecoes/negocio | "Qual dia o negócio fecha?" | Nenhum (funciona normal) | Data válida |
| **endereco_completo** | ❌ | Configuracao/negocio | "Qual é o endereço?" | Nenhum | Não vazio se fornecido |
| **instagram** | ❌ | RedesSociais/negocio | "Instagram do negócio?" | Nenhum | URL válido se fornecido |
| **whatsapp** | ❌ | RedesSociais/negocio | "WhatsApp para contato?" | Nenhum | Número válido se fornecido |
| **foto_negocio** | ❌ | Configuracao/negocio (URL) | "Logo ou foto do negócio?" | Avatar genérico | URL válido se fornecido |

---

## 🧪 Teste de Agendamento Dummy

Após conclusão do onboarding, sistema executa teste de agendamento:

```
TESTE AUTOMÁTICO:

1. Criar evento dummy
   - Cliente: "Cliente Teste"
   - Profissional: primeiro da lista
   - Serviço: primeiro da lista
   - Data: hoje + 7 dias (segunda-feira)
   - Hora: primeiro horário disponível
   - Status: "pendente"

2. Validar regras
   - Conflito detectado? (não deve haver)
   - Disponibilidade ok? (deve estar disponível)
   - Duração respeitada? (deve ser a correta)

3. Se bem-sucedido
   - Remover evento dummy
   - Marcar onboarding_status = "completo"
   - Prosseguir com ativação

4. Se falhar
   - Mostrar erro específico
   - Oferecer revisar dados
   - Manter onboarding_status = "aguardando_revisao"
   - NÃO ativar tenant
```

---

## 🚀 Próximos Passos Após Onboarding

Depois que onboarding é completo:

1. ✅ **Enviar resumo**
   - "Seu salão está configurado!"
   - Listagem de profissionais e serviços
   - Horários de funcionamento

2. ✅ **Oferecer ações imediatas**
   - "Agendar seu primeiro cliente?"
   - "Adicionar mais profissionais?"
   - "Ajustar preços?"

3. ✅ **Documentação**
   - Link para guia rápido
   - FAQ sobre sistema
   - Suporte

4. ✅ **Agendar seguimento**
   - "Posso te ajudar com mais algo?"
   - Lembrete em 24h: "Como está funcionando?"

---

## ⚠️ Cenários de Erro e Recovery

### Erro Durante Coleta

```
Dono: "Bruna e Carla"
Motor: ✅ Extrai 2 profissionais

Dono: [silêncio por 1h]
Motor: ⚠️ Sessão expirou
       → Salvar contexto em draft
       → Mostrar resumo do que coletou
       → Perguntar "Continuar daqui?"
```

### Erro Durante Persistência

```
Motor: Tentando salvar em Firestore
       ❌ Erro de transação
       → Rollback automático
       → Mostrar erro ao dono
       → Oferecer tentar novamente
       → Manter onboarding_status = "aguardando_revisao"
```

### Erro Durante Teste

```
Motor: Testando agendamento
       ❌ Conflito detectado
       (Não deveria haver, dados estão errados)
       → Cancelar teste
       → Mostrar problema específico
       → Permitir voltar e corrigir dados
       → NÃO ativar tenant
```

---

## 📐 Integração com P0

Onboarding criar estrutura que P0 espera:

```
P0 Assume (Garantido pelo Onboarding):
✅ tenant_id existe e isolado
✅ Profissionais existem
✅ Serviços existem com durações
✅ Vínculos P-S existem
✅ AgendaPadrao definida
✅ NotificacoesConfig ativa
✅ Sessão de dono existe

P0 Fluxo de Agendamento:
Cliente (novo) → pedir dados → motor valida → criar evento → persistir
(Mesmo fluxo, mas dono já está setup)
```

---

## 📋 Checklist de Implementação Futura

Antes de implementar este onboarding, validar:

- [ ] CLAUDE.md: Regra Zero aplicada (arquivo + função + linha)
- [ ] CLAUDE.md: Buscar antes de criar (equivalentes existem?)
- [ ] CLAUDE.md: Fonte única de verdade (onde está?)
- [ ] Recovery completo especificado
- [ ] ClienteProfile safety garantida
- [ ] Schema Firestore validado por revisor
- [ ] Testes P0 ainda passam (174/174)
- [ ] Estados de sessão implementáveis
- [ ] Rollback strategy clara
- [ ] Monitoramento definido
- [ ] Documentação de usuário pronta

---

## 🎓 Aprendizados Aplicáveis

Do caso "Suri" e bugs P0:

1. **Semântica Antes de Código**
   - Validar que GPT entendeu corretamente
   - Motor determina se é válido

2. **Menor Camada**
   - Erro na coleta? Corrigir interpretação (GPT)
   - Erro na persistência? Corrigir motor
   - Erro no Firestore? Corrigir transação

3. **Determinismo**
   - Nenhuma "decisão automática"
   - Cada transição tem regra explícita

4. **Regressão**
   - Após onboarding, P0 deve continuar 174/174 PASS
   - Novos campos não quebram fluxo cliente

---

## 🔐 Segurança e Isolamento

Garantias obrigatórias:

```
✅ Multi-tenant: tenant_id em TODOS os query paths
✅ Permissões: Apenas dono acessa seus dados
✅ Acesso: Cliente não vê config onboarding do dono
✅ Profissional: Não vê config de preço/agendas
✅ Isolamento: Dados de Tenant A não vazam para B
✅ Auditoria: Onboarding registra cada passo
✅ Recovery: Dados não são corrompidos em restart
```

---

## 📊 Métricas de Sucesso Futuro

Quando implementado, validar:

```
Taxa de Conclusão: % donos que completam onboarding
Taxa de Erro: % de falhas durante processo
Taxa de Retenção: % que fazem primeiro agendamento
Tempo Médio: Quanto leva completar onboarding
Satisfação: NPS de donos após onboarding
```

---

## ✅ Status

**Documento:** ESPECIFICAÇÃO COMPLETA  
**Implementação:** ❌ Não iniciada  
**Próximo passo:** Aprovação da especificação  
**Depois:** Implementação batch  
**Testes:** Criar bateria P1 correspondente  

---

**Versão:** 1.0  
**Data:** 2026-06-21  
**Escopo:** Mapeamento de requisitos apenas (sem código)  
**Pronto para:** Design review → Implementation → Testing

