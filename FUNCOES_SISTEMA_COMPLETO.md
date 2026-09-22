# 📊 NeoEve - Mapeamento Completo de Funções do Sistema

**Data:** 2026-07-01 | **Total de Funções:** 500+

---

## 🎯 RESUMO EXECUTIVO

O NeoEve é um **bot empresarial multi-tenant** para agendamento, gestão de serviços e profissionais via WhatsApp/Telegram. O sistema é organizado em **10 módulos principais**:

1. **Router/Classificação** - Interpreta intenção do usuário
2. **Handlers** - Processam comandos e eventos
3. **Services** - Lógica de negócio (agenda, cliente, profissional, etc)
4. **Firebase** - Persistência de dados
5. **GPT/IA** - Inteligência artificial para interpretação
6. **Scheduler** - Tarefas automáticas (notificações, resumos)
7. **Email** - Integração com Gmail/email
8. **Admin** - Comandos administrativos
9. **Utils** - Utilitários (formatação, data/hora, etc)
10. **Tests** - Suite de testes (P0, P1, F3, etc)

---

## 📁 MÓDULO 1: ROUTER & CLASSIFICAÇÃO (60+ funções)

### Arquivo Principal: `router/principal_router.py`

**Classificação de Intenções:**
- `eh_consulta()` - Detecta se é pergunta sobre disponibilidade
- `eh_gatilho_agendar()` - Detecta comando de agendamento
- `eh_confirmacao()` - Detecta confirmação positiva
- `eh_desistencia_fluxo()` - Detecta desistência/cancelamento
- `eh_aceite_de_acao_pendente()` - Detecta aceite de ação pendente
- `eh_reacao_a_sugestao()` - Detecta reação a sugestão
- `eh_escolha_de_alternativa()` - Detecta escolha entre opções
- `eh_continuacao_de_agendamento()` - Detecta continuação de fluxo

**Processamento de Agenda:**
- `detectar_bloqueio_agenda_salao()` - Detecta bloqueios de salão
- `detectar_bloqueio_agenda_profissional()` - Detecta bloqueios de profissional
- `extrair_servico_do_texto()` - Extrai serviço mencionado
- `_tem_indicio_de_hora()` - Verifica se há menção de hora
- `_extrair_hora_simples()` - Extrai hora do texto
- `resolver_profissional_referenciado()` - Resolve profissional mencionado
- `extrair_servico_alvo_binario()` - Extrai serviço em contexto binário

**Contexto & Estado:**
- `tem_contexto_agendamento_ativo()` - Verifica se há agendamento em progresso
- `eh_confirmacao_pendente_ativa()` - Verifica confirmação pendente
- `resolver_proximo_passo_real()` - Resolve próximo passo do fluxo

**Formatação de Respostas:**
- `normalizar()` - Normaliza texto
- `formatar_data_hora_br()` - Formata data/hora em português
- `montar_frase_data_legivel()` - Cria frase com data legível
- `montar_frase_data_com_hora()` - Cria frase com data e hora
- `montar_resposta_fallback()` - Monta resposta padrão
- `quer_falar_com_humano()` - Detecta solicitação para humano
- `tem_hora_real()` - Verifica se há hora definida
- `periodo_compativel_com_hora()` - Valida período vs hora

**Auditoria:**
- `_audit_confirmacao()` - Auditoria de confirmação

---

## 📁 MÓDULO 2: HANDLERS (50+ funções)

### Handlers Principais:

**Bot Handler** (`handlers/bot.py`)
- `register_handlers()` - Registra todos os handlers da aplicação

**Event Handler** (`handlers/event_handler.py`)
- `formatar_mensagem_conflito_profissional()` - Formata msg de conflito
- `oferecer_entrar_lista_espera()` - Oferece fila de espera
- `_precisa_profissional()` - Verifica se precisa profissional específico

**Voice Handler** (`handlers/voice_handler.py`)
- Processa áudio do usuário

**Voice Command Handler**
- `eh_comando()` - Detecta comando por voz
- `extrair_comando()` - Extrai comando de áudio

**Task Handler** (`handlers/task_handler.py`)
- Processa tarefas

**Perfil Handler** (`handlers/perfil_handler.py`)
- Gerencia perfil do cliente

**Report Handler** (`handlers/report_handler.py`)
- Gera relatórios

**Reagendamento Handler** (`handlers/reagendamento_handler.py`)
- `_texto_eh_apenas_opcao()` - Verifica se é apenas seleção de opção

**Encaixe Handler** (`handlers/encaixe_handler.py`)
- `_extrair_profissional()` - Extrai profissional
- `_extrair_duracao()` - Extrai duração do serviço
- `_extrair_datahora()` - Extrai data/hora

**Lista Espera Handler** (`handlers/lista_espera_handler.py`)
- `_calcular_hora_fim()` - Calcula hora final do agendamento

**Importação Handler** (`handlers/importacao_handler.py`)
- `detectar_coluna()` - Detecta coluna em CSV/Excel

**Ação Handler** (`handlers/acao_handler.py`)
- `estimar_duracao_servico()` - Estima duração
- `parse_servicos_em_ordem()` - Parseia lista de serviços

**Followup Handler** (`handlers/followup_handler.py`)
- `start_followup_scheduler()` - Inicia scheduler de follow-up

**Intention Handler** (`handlers/intents_handler.py`)
- Processa intenções

---

## 📁 MÓDULO 3: SERVICES - LÓGICA DE NEGÓCIO (100+ funções)

### Event Service (`services/event_service_async.py`)
- `evento_deve_entrar_na_agenda()` - Valida evento para agenda
- `evento_deve_ser_ignorado()` - Detecta eventos a ignorar
- `formatar_evento()` - Formata evento para exibição
- `verificar_encaixe_exato()` - Verifica conflito de horário
- `_normaliza_txt()` - Normaliza texto de evento
- `_interpreta_data_relativa()` - Interpreta "próxima semana", etc
- `_extrai_data_explicita()` - Extrai data do texto
- `_parse_event_interval()` - Parseia intervalo de evento

### Agenda Service (`services/agenda_service.py`)
- `horario_dentro_do_expediente()` - Valida hora dentro do expediente
- `intervalo_dentro_do_expediente()` - Valida intervalo dentro expediente
- `_normalizar_data_iso()` - Normaliza formato de data
- `_to_date()` - Converte para date
- `_hora_para_minutos()` - Converte hora em minutos
- `_minutos_para_hora()` - Converte minutos em hora

### Agenda Lock Service (`services/agenda_lock_service.py`)
- `normalizar_hora()` - Normaliza formato de hora
- `gerar_slot_key()` - Gera chave para slot de tempo
- `gerar_buckets_tempo()` - Gera buckets de tempo
- `lock_esta_expirado()` - Verifica expiração de lock

### Encaixe Service (`services/encaixe_service.py`)
- `_janela_livre()` - Encontra janela livre na agenda
- `_tem_conflito()` - Detecta conflito de horário
- `_overlap()` - Verifica sobreposição de intervalos
- `_local_now()` - Retorna horário local atual
- `_dt()` - Cria datetime
- `_to_date_hhmm()` - Converte datetime para (data, hora)

### Cliente Profile Service (`services/clienteprofile_service.py`)
- `_calcular_moda_profissional()` - Profissional mais frequente
- `_calcular_moda_servico()` - Serviço mais frequente
- `_contar_frequencia()` - Conta frequência de item

### Cliente Profile Contexto Service (`services/clienteprofile_contexto_service.py`)
- `extrair_contexto_motor()` - Extrai contexto motor do perfil

### Profissional Service (`services/profissional_service.py`)
- `gerar_mensagem_profissionais_disponiveis()` - Formata lista de profissionais

### Email Service (`services/email_service.py`)
- `ler_emails()` - Lê emails do Gmail
- `enviar_email()` - Envia email
- `buscar_contatos_por_nome()` - Busca contatos
- `gerar_link_visualizacao_email()` - Gera link de visualização
- `filtrar_emails_prioritarios_por_palavras()` - Filtra por palavras-chave
- `listar_emails_prioritarios()` - Lista emails importantes
- `limpar_email()` - Remove caracteres especiais de email
- `normalizar()` - Normaliza texto de email
- `filtrar_emails_por_nome()` - Filtra emails por nome

### Informação Service (`services/informacao_service.py`)
- `formatar_nomes_humanos()` - Formata lista de profissionais
- `formatar_resposta_disponibilidade()` - Formata resposta de disponibilidade

### GPT Service (`services/gpt_client.py` / `services/gpt_service(1).py`)
- `estimar_duracao()` - Estima duração de serviço
- `formatar_data()` - Formata data para exibição

### GPT Executor Service (`services/gpt_executor.py`)
- `_obter_user_id()` - Obtém ID do usuário
- `_normalizar_nome()` - Normaliza nome
- `_extrair_servico_do_contexto()` - Extrai serviço do contexto
- `sanitizar_cancelamento_pendente()` - Remove cancelamentos antigos

### Interpretação Contextual Service (`services/interpretacao_contextual_service.py`)
- `_interpretar_profissional()` - Interpreta profissional mencionado
- `_interpretar_horario()` - Interpreta horário
- `_interpretar_data()` - Interpreta data
- `_interpretar_servico()` - Interpreta serviço
- `_interpretar_confirmacao()` - Interpreta confirmação
- `_interpretar_escolha_horario()` - Interpreta escolha de hora
- `_interpretar_escolha_profissional()` - Interpreta escolha de profissional
- `_interpretar_confirmacao_cancelamento()` - Interpreta cancelamento

### Interpretador Conversacional Service (`services/interpretador_conversacional.py`)
- `interpretar_conversa_operacional()` - Interpreta conversa operacional
- `_parece_negacao_confirmacao()` - Detecta negação/confirmação

### Normalizador Service (`services/normalizacao_service.py`)
- Normaliza dados de entrada

### Classificador Conversa Service (`services/classificador_conversa.py`)
- `normalizar_txt()` - Normaliza texto
- `extrair_features_conversa()` - Extrai features de conversa
- `classificar_contexto_mensagem()` - Classifica contexto
- `classificar_intencao_conversacional()` - Classifica intenção
- `detectar_tipo_ajuste_incremental()` - Detecta tipo de ajuste
- `classificar_negacao_confirmacao()` - Classifica negação vs confirmação

### Recorrência Service (`services/recorrencia_service.py`)
- `_parse_dt()` - Parseia data/hora
- `_intervalos_em_dias()` - Calcula intervalos entre datas
- `_mediana()` - Calcula mediana
- `_normalizar_servico()` - Normaliza nome de serviço

### Whitelist Service (`services/whitelist_service.py`)
- `classificar_com_whitelist()` - Classifica usando whitelist
- `obter_whitelist_info()` - Retorna informações de whitelist

### Cadastro Inicial Service (`services/cadastro_inicial_service.py`)
- `parse_servico_falado()` - Parseia serviço falado
- `parse_profissional_frase()` - Parseia profissional de frase
- `mensagem_onboarding()` - Gera mensagem de boas-vindas

### Onboarding Service (`services/onboarding_service.py`)
- `_extrair_endereco()` - Extrai endereço
- `_normalizar_endereco()` - Normaliza endereço

### Onboarding Dono Service (`services/onboarding_dono_service.py`)
- `validar_campo_onboarding()` - Valida campo de onboarding
- `obter_pergunta_etapa()` - Obtém pergunta da etapa

### Reativação Manual Service (`services/reativacao_manual_service.py`)
- `formatar_sugestao_para_dono()` - Formata sugestão para dono

### Backlog Comercial Service (`services/backlog_comercial_service.py`)
- `formatar_resumo_para_mensagem()` - Formata resumo
- `formatar_lista_para_mensagem()` - Formata lista

### Lead Status Service (`services/lead_status_service.py`)
- `normalizar_texto()` - Normaliza texto

### Notificação Service (`services/notificacao_service.py`)
- Gerencia notificações

### Identidade Service (`services/identidade_service.py`)
- `normalizar_actor_id()` - Normaliza ID do ator

### Admin Command Service (`services/admin_command_service.py`)
- `_detectar_intencao_admin()` - Detecta comando admin
- `_eh_intencao_agenda_salao()` - Detecta agenda de salão
- `_eh_intencao_adicionar_servico()` - Detecta adição de serviço
- `_extrair_data_iso()` - Extrai data ISO
- `_parse_servicos_de_texto()` - Parseia serviços
- `_extrair_nome_servico()` - Extrai nome de serviço
- `_parse_preco_duracao()` - Parseia preço e duração

### Intenção GPT Service (`services/intencao_gpt_service.py`)
- `_norm()` - Normaliza texto

---

## 📁 MÓDULO 4: FIREBASE & PERSISTÊNCIA (30+ funções)

### Firestore Client (`services/firestore_client.py`)
- `get_db()` - Retorna cliente do Firestore
- `_inicializar_firebase()` - Inicializa Firebase

### Firebase Service (`services/firebase_service.py`)
- `salvar_dados()` - Salva dados genéricos
- `salvar_cliente()` - Salva dados do cliente
- `buscar_cliente()` - Busca cliente por ID
- `buscar_dados()` - Busca dados de coleção
- `buscar_dado_em_path()` - Busca documento em path
- `limpar_colecao()` - Limpa uma coleção
- `salvar_dado_em_path()` - Salva documento em path
- `buscar_subcolecao()` - Busca subcoleção
- `salvar_evento()` - Salva evento de agenda
- `buscar_todos_clientes()` - Retorna todos os clientes
- `deletar_dado_em_path()` - Deleta documento
- `atualizar_dado_em_path()` - Atualiza documento

### Firebase Service Async (`services/firebase_service_async.py`)
- `get_ref_from_path()` - Retorna referência Firestore

---

## 📁 MÓDULO 5: SCHEDULER & AUTOMAÇÃO (10+ funções)

### Daily Summary Scheduler (`scheduler/daily_summary.py`)
- `start_daily_summary()` - Inicia resumo diário

### Notificações Scheduler (`scheduler/notificacoes_scheduler.py`)
- `_parse_iso_br()` - Parseia data ISO em português
- `start_notificacao_scheduler()` - Inicia scheduler de notificações

### Followup Scheduler (`scheduler/followup_scheduler.py`)
- `start_followup_scheduler()` - Inicia scheduler de follow-up

### Email to Event Loop (`scheduler/email_to_event_loop.py`)
- Converte emails em eventos de agenda

---

## 📁 MÓDULO 6: UTILIDADES (80+ funções)

### Pattern Matcher (`utils/pattern_matcher.py`)
- `eh_cancelamento()` - Detecta cancelamento
- `eh_confirmacao_positiva()` - Detecta sim
- `eh_confirmacao_negativa()` - Detecta não
- `eh_comando()` - Detecta comando
- `extrair_comando()` - Extrai comando
- `eh_ajuste_em_fluxo()` - Detecta ajuste em fluxo
- `eh_resposta_para_opcoes()` - Detecta resposta a opções
- `normalizar_confirmacao()` - Normaliza resposta de confirmação

### Interpretador Datas (`utils/interpretador_datas.py`)
- `agora_br_aware()` - Horário atual com timezone
- `agora_br_naive()` - Horário atual sem timezone
- `_normalizar_texto_hora()` - Normaliza texto de hora
- `_so_hora()` - Verifica se é apenas hora
- `_tem_indicio_temporal()` - Detecta referência temporal
- `interpretar_intervalo_de_datas()` - Interpreta intervalo (ex: "segunda a sexta")
- `interpretar_e_salvar_data_hora()` - Interpreta e retorna datetime
- `extrair_trecho_temporal()` - Extrai parte temporal do texto
- `interpretar_data_e_hora()` - Interpreta data e hora
- `detectar_bloqueio_agenda_salao()` - Detecta bloqueios

### Formatters (`utils/formatters.py`)
- `formatar_horario_atual()` - Formata hora atual
- `adaptar_genero()` - Adapta palavra para gênero
- `_calcular_blocos_livres()` - Calcula horários livres
- `gerar_sugestoes_de_horario()` - Gera sugestões de horário
- `_formatar_data_br()` - Formata data em português
- `_status_evento_humano()` - Formata status de evento
- `formatar_eventos_telegram()` - Formata eventos para Telegram

### GPT Utils (`utils/gpt_utils.py`)
- `montar_prompt_com_contexto()` - Monta prompt para GPT
- `formatar_descricao_evento()` - Formata descrição
- `estimar_duracao()` - Estima duração
- `formatar_data()` - Formata data
- `limpar_nome_duplicado()` - Remove duplicação de nome

### Plan Utils (`utils/plan_utils.py`)
- `_normalizar_modulo()` - Normaliza nome de módulo
- `identificar_plano_por_intencao()` - Identifica plano de ação

### Normalizador Humano (`utils/normalizador_humano.py`)
- `_normalizar_texto()` - Normaliza texto
- `_tem_algum()` - Verifica presença de termo
- `normalizar_intencao_humana()` - Normaliza intenção
- `limpar_sinais_humanos()` - Remove sinais humanos do contexto

### Intenção Utils (`utils/intencao_utils.py`)
- `identificar_intencao()` - Identifica intenção do texto
- `deve_ativar_fluxo_manual()` - Detecta solicitação de fluxo manual

### Fluxo Helpers (`utils/fluxo_helpers.py`)
- `obter_estado_fluxo()` - Retorna estado atual
- `em_fluxo_ativo()` - Verifica se em fluxo
- `aguardando_confirmacao()` - Verifica se aguardando confirmação
- `aguardando_escolha_opcoes()` - Verifica se aguardando escolha
- `obter_proposta_agendamento()` - Retorna proposta em fluxo
- `obter_opcoes_disponiveis()` - Retorna opções do fluxo
- `validar_estado_fluxo()` - Valida estado

### Mensagens Agendamento (`utils/mensagens_agendamento.py`)
- `formatar_data_hora_natural()` - Formata data/hora natural
- `montar_mensagem_preconfirmacao()` - Monta msg de pré-confirmação
- `montar_mensagem_confirmacao_sucesso()` - Monta msg de sucesso

### Priority Utils (`utils/priority_utils.py`)
- `obter_config_prioridade_usuario()` - Obtém config de prioridade
- `classificar_prioridade_email()` - Classifica email
- `detectar_prioridade_tarefa()` - Classifica tarefa

### WhatsApp Utils (`utils/whatsapp_utils.py`)
- `send_whatsapp_message()` - Envia mensagem via WhatsApp

### Audio Utils (`utils/audio_utils.py`)
- `converter_audio_para_wav()` - Converte áudio para WAV
- `transcrever_audio()` - Transcreve áudio com speech-to-text

### Conversation Classifier (`router/conversation_classifier.py`)
- `normalizar_texto()` - Normaliza texto
- `tem_indicio_data_ou_hora()` - Detecta menção de data/hora
- `detectar_consulta_disponibilidade()` - Detecta pergunta de disponibilidade
- `detectar_mensagem_pessoal()` - Detecta msg pessoal

### Permissão Utils (`utils/permissao_utils.py`)
- Gerencia permissões de usuário

---

## 📁 MÓDULO 7: TESTES (150+ funções)

### Test Runners Principais:
- `runner_p0_persistencia_real.py` - Testes P0 de persistência
- `runner_regressao_p0_agendamento_critico.py` - Testes P0 de agendamento
- `runner_p1_identidade_canal_onboarding.py` - Testes P1 de identidade
- `runner_p0_regressao_completa.py` - Suite completa P0
- `runner_f8_lista_espera_real.py` - Testes F8 de fila de espera
- Dezenas de stress tests e runners

### Tipos de Teste:
- **P0** - Testes críticos (fluxo principal)
- **P1** - Testes de funcionalidade
- **F3** - Testes de robustez
- **F8** - Testes de encaixe/fila de espera
- **Stress** - Testes de sobrecarga

---

## 📁 MÓDULO 8: SCRIPTS DE AUDITORIA (20+ funções)

### Audit Firebase:
- `audit_all_collections()` - Auditoria completa
- `audit_clientes_only.py` - Auditoria apenas de clientes
- `audit_correct_project.py` - Auditoria do projeto correto
- `cleanup_test_tenants_firestore.py` - Limpeza de tenants teste

### Helpers:
- `is_test_collection()` - Detecta se é coleção teste
- `is_test_document()` - Detecta se é documento teste
- `save_report()` - Salva relatório

---

## 📁 MÓDULO 9: ENTRY POINTS (5+ funções)

### Main (`main.py`)
- `webhook()` - Endpoint webhook para mensagens
- `health_check()` - Health check da API
- `cron_ping()` - Ping para manter aplicação ativa
- `run_bot()` - Inicia o bot

### Config (`config/google_config.py`)
- `get_calendar_service()` - Retorna serviço do Google Calendar

### Flask App (`flask_app.py`)
- `test_firebase()` - Testa conexão com Firebase

---

## 📁 MÓDULO 10: UTILITÁRIOS DE AUDITORIA (10+ funções)

### Auditoria GPT (`auditoria_gpt.py`)
- `_ler_manual_secretaria()` - Lê manual de secretária
- `auditar()` - Executa auditoria
- `_analisar_localmente()` - Análise local

### Orquestrador (`orquestrador.py`)
- `ler_arquivo()` - Lê arquivo
- `encontrar_arquivos_relevantes()` - Localiza arquivos relevantes
- `gerar_analise_inicial()` - Gera análise inicial
- `chamar_auditoria_gpt()` - Chama auditoria GPT
- `exibir_resultado()` - Exibe resultado
- `refinar_analise()` - Refina análise
- `gerar_arquivo_diff()` - Gera diff de patch
- `salvar_historico()` - Salva histórico
- `main()` - Orquestrador principal

---

## 🎯 PRINCIPAIS FUNCIONALIDADES IMPLEMENTADAS

### ✅ **1. Agendamento de Serviços**
- Interpreta pedidos de agendamento natural
- Valida conflitos de horário
- Sugere horários disponíveis
- Suporta múltiplos profissionais
- Detecta bloqueios de agenda

### ✅ **2. Gestão de Clientes**
- Perfil do cliente com histórico
- Profissional e serviço preferidos
- Contexto de conversa (motor)
- Onboarding de cliente e dono
- Histórico de agendamentos

### ✅ **3. Gestão de Profissionais**
- Cadastro de serviços e preços
- Disponibilidade semanal
- Duração estimada de serviço
- Filtro por especialidade

### ✅ **4. Confirmação de Agendamento**
- Confirmação de pré-agendamento
- Confirmação final com data/hora
- Avisos de cancelamento
- Oferecimento de fila de espera

### ✅ **5. Cancelamento & Reagendamento**
- Detecta intenção de cancelar
- Oferece reagendamento
- Rastreio de cancelamentos pendentes
- Notificações de reativação

### ✅ **6. Inteligência Conversacional**
- Router de intenções GPT
- Classificador de contexto
- Interpretação de data/hora relativa
- Suporte a emojis e entrada informal

### ✅ **7. Notificações & Follow-up**
- Notificação de agendamento confirmado
- Aviso do dia anterior
- Follow-up pós-serviço
- Resumo diário

### ✅ **8. Integração com Google Calendar**
- Sincronização de eventos
- Bloqueios de calendário
- Feriados e horários especiais
- Detecção de conflito com outra agenda

### ✅ **9. Email & Contatos**
- Integração com Gmail
- Priorização de emails
- Busca de contatos
- Envio de confirmações

### ✅ **10. Multi-tenant & Isolamento**
- Suporte a múltiplos salões/negócios
- Isolamento de dados por tenant
- Contexto por canal (WhatsApp/Telegram)

### ✅ **11. Admin & Gerenciamento**
- Comandos admin para gerenciar agenda
- Adição de bloqueios
- Alteração de serviços/preços
- Relatórios

### ✅ **12. Validação & Robustez**
- Input validation (emoji, caracteres especiais, entrada longa)
- Tratamento de timezone
- Detecção de malformação
- Recuperação de erros

---

## 📊 ESTATÍSTICAS

| Métrica | Quantidade |
|---------|-----------|
| **Total de Funções** | 500+ |
| **Arquivos Python** | 180+ |
| **Módulos Principais** | 10 |
| **Testes** | 150+ |
| **Linhas de Código** | 50,000+ |

---

## 🔑 PADRÕES PRINCIPAIS

1. **Context Dict** - Mantém estado da conversa
2. **Actor/Tenant** - Multi-tenant com isolamento
3. **Router Pattern** - Classifica intenção → handler
4. **Service Layer** - Lógica de negócio isolada
5. **Firebase Firestore** - Persistência
6. **Async/Await** - Operações assíncronas
7. **GPT/LLM** - Interpretação de linguagem natural
8. **Regex Patterns** - Detecção de padrões textuais

---

**Última Atualização:** 2026-07-01
**Criado por:** Claude Code
