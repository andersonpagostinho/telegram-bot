import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from handlers.task_handler import add_task, list_tasks, list_tasks_by_priority, clear_tasks
from handlers.email_handler import ler_emails_command, listar_emails_prioritarios, enviar_email_command, conectar_email, auth_callback
from handlers.event_handler import add_agenda, list_events, confirmar_reuniao, confirmar_presenca, debug_eventos
from services.firebase_service_async import buscar_cliente, salvar_cliente, verificar_firebase, buscar_documento
from handlers.test_handler import testar_firebase, testar_avisos
from handlers.report_handler import relatorio_diario, relatorio_semanal, enviar_relatorio_email
from handlers.perfil_handler import (
    set_tipo_negocio,
    set_estilo_mensagem,
    set_nome_negocio,
    meu_estilo,
    set_email,
    meu_plano,
    meu_perfil,
    set_tipo_usuario,  # ✅ CORRETO
    set_modo_uso,       # ✅ CORRETO
    listar_profissionais
)
from handlers.voice_handler import handle_voice
from handlers.followup_handler import criar_followup, listar_followups, verificar_avisos, configurar_avisos
from handlers.test_handler import testar_avisos
from handlers.gpt_text_handler import processar_texto
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)

# ✅ Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = str(user.id)

    # 👇 Verifica se o ID está listado como dono no Firebase
    config = await buscar_documento("configuracoes/admin_config")
    donos = config.get("donos", []) if config else []

    if user_id in donos:
        tipo_usuario = "dono"
        modo_uso = "interno"
        mensagem = (
            f"👋 Olá, {user.first_name}! Detectei que você é o *dono* do negócio.\n\n"
            f"🎯 O modo *interno* já foi ativado automaticamente.\n"
            f"✅ Agora é só começar a usar! Você pode digitar /help para ver tudo que posso fazer.\n\n"
            f"✨ Dica: personalize como quiser com os comandos:\n"
            f"/tipo_negocio – ex: salão, clínica, etc.\n"
            f"/estilo – formal ou casual\n"
            f"/meu_email – para envio de mensagens\n"
            f"/profissional – para cadastrar sua equipe"
        )
    else:
        tipo_usuario = "cliente"
        modo_uso = "atendimento_cliente"
        mensagem = (
            f"👋 Olá, {user.first_name}! Sou *NeoEve*, sua secretária virtual com inteligência contextual.\n\n"
            f"🛠️ Para começarmos do jeito certo, preciso saber como serei usada:\n"
            f"1️⃣ *Sou para você ou para seus clientes?*\n"
            f"→ Use o comando /tipo_usuario e escolha entre `dono` ou `cliente`\n\n"
            f"2️⃣ *Quem vai me acessar?*\n"
            f"→ Use o comando /modo_uso e escolha entre `interno` ou `atendimento_cliente`\n\n"
            f"3️⃣ *Qual é o seu tipo de negócio?*\n"
            f"→ Use /tipo_negocio (ex: salão de beleza, clínica, tech...)\n\n"
            f"4️⃣ *Como prefere que eu me comunique?*\n"
            f"→ Use /estilo e escolha `formal` ou `casual`\n\n"
            f"5️⃣ *Qual e-mail devo usar para enviar mensagens por você?*\n"
            f"→ Use /meu_email e informe seu e-mail\n\n"
            f"6️⃣ *Você tem profissionais que devemos cadastrar?*\n"
            f"→ Use o comando /profissional (ex: /profissional Joana corte,escova)\n\n"
            f"📌 Quando terminar, digite /help para ver tudo que posso fazer por você!"
        )

    dados = {
        "nome": f"{user.first_name} {user.last_name or ''}".strip(),
        "email": "",
        "pagamentoAtivo": True,
        "dataAssinatura": datetime.now().strftime("%Y-%m-%d"),
        "proximoPagamento": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "planosAtivos": ["secretaria"],
        "tipo_usuario": tipo_usuario,
        "modo_uso": modo_uso,
        "tipo_negocio": "",
        "estilo": ""
    }

    await salvar_cliente(user_id, dados)
    await update.message.reply_text(mensagem, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📖 Comando /help recebido!")
    await update.message.reply_text(
        "ℹ️ *Comandos disponíveis:*\n\n"

        "🟢 *Básico*\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/meus_dados - Ver seus dados cadastrados\n"
        "/meu_estilo - Ver estilo e tipo de negócio salvos\n"
        "/meuplano - Ver informações do seu plano atual\n\n"

        "📝 *Tarefas*\n"
        "/tarefa - Adiciona uma nova tarefa\n"
        "/listar - Lista todas as tarefas\n"
        "/listar_prioridade - Lista tarefas por prioridade\n"
        "/limpar - Remove todas as tarefas\n\n"

        "📅 *Agenda e Eventos*\n"
        "/agenda - Adiciona um novo evento\n"
        "/eventos - Lista eventos agendados\n"
        "/confirmar_reuniao - Confirma uma reunião\n"
        "/confirmar_presenca - Confirma presença em um evento\n"
        "/debug_eventos - Verifica eventos internos\n\n"

        "📧 *E-mails*\n"
        "/conectar_email - Conectar seu e-mail (Google)\n"
        "/auth_callback - Finaliza autenticação de e-mail\n"
        "/ler_emails - Lê os últimos e-mails\n"
        "/emails_prioritarios - Lista e-mails importantes\n"
        "/enviar_email - Envia um e-mail (por nome ou e-mail)\n"
        "/meu_email - Define o e-mail de envio manual\n\n"

        "📊 *Relatórios*\n"
        "/relatorio_diario - Gera relatório diário\n"
        "/relatorio_semanal - Gera relatório semanal\n"
        "/enviar_relatorio_email - Envia relatório por e-mail\n\n"

        "🗣️ *Comando por voz*\n"
        "Você pode usar comandos de voz diretamente no chat\n"
        "Ex: envie áudio dizendo *“nova tarefa lavar roupa”* ou *“me avise às 08:00, 12:00 e 18:00”*\n\n"

        "🔁 *Avisos e Lembretes*\n"
        "/configuraravisos - Define até 3 horários de lembrete\n"
        "/verificaravisos - Ver seus horários de lembrete atuais\n\n"

        "📌 *Follow-ups*\n"
        "/followup Nome do cliente - Registra um follow-up\n"
        "/meusfollowups - Lista seus follow-ups pendentes\n"
        "/concluirfollowup Nome do cliente - Conclui e remove\n\n"

        "🎯 *Personalização*\n"
        "/tipo_negocio - Define o tipo de negócio\n"
        "/estilo - Define o estilo de mensagens\n"
        "/nome_negocio - Define o nome do seu negócio\n"
        "/profissional - Cadastra profissional com suas atividades (ex: /profissional Ana corte,escova)\n",
        parse_mode='Markdown'
    )

# ✅ Comando /meus_dados
async def meus_dados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if cliente:
        dados_cliente = "\n".join(f"{key}: {value}" for key, value in cliente.items())
        await update.message.reply_text(f"📂 Seus dados:\n{dados_cliente}")
    else:
        await update.message.reply_text("⚠️ Nenhum dado encontrado para sua conta.")

# 🚀 Registra os handlers
def register_handlers(application: Application):
    try:
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("tarefa", add_task))
        application.add_handler(CommandHandler("listar", list_tasks))
        application.add_handler(CommandHandler("limpar", clear_tasks))
        application.add_handler(CommandHandler("ler_emails","leremails", ler_emails_command))
        application.add_handler(CommandHandler("emails_prioritarios","emailsprioritarios", listar_emails_prioritarios))
        application.add_handler(CommandHandler("enviar_email","enviaremail", enviar_email_command))
        application.add_handler(CommandHandler("agenda", add_agenda))
        application.add_handler(CommandHandler("eventos", list_events))
        application.add_handler(CommandHandler("confirmar_reuniao","confirmarreuniao", confirmar_reuniao))
        application.add_handler(CommandHandler("confirmar_presenca","confirmarpresenca", confirmar_presenca))
        application.add_handler(CommandHandler("meus_dados", meus_dados, "meusdados"))
        application.add_handler(CommandHandler("conectar_email","conectaremail", conectar_email))
        application.add_handler(CommandHandler("auth_callback", auth_callback))
        application.add_handler(CommandHandler("debug_eventos", debug_eventos))
        application.add_handler(CommandHandler("relatorio_diario", "relatoriodiario", relatorio_diario))
        application.add_handler(CommandHandler("relatorio_semanal", "relatoriosemanal", relatorio_semanal))
        application.add_handler(CommandHandler("enviar_relatorio_email", "enviarrelatorioemail", enviar_relatorio_email))
        application.add_handler(CommandHandler("tipo_negocio", set_tipo_negocio))
        application.add_handler(CommandHandler("estilo", set_estilo_mensagem))
        application.add_handler(CommandHandler("nome_negocio", set_nome_negocio))
        application.add_handler(CommandHandler("meu_estilo", meu_estilo))
        application.add_handler(CommandHandler("meu_email", set_email))
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        application.add_handler(CommandHandler("meuplano", meu_plano))
        application.add_handler(CommandHandler("followup", criar_followup))
        application.add_handler(CommandHandler("meusfollowups", listar_followups))
        application.add_handler(CommandHandler("verificaravisos", verificar_avisos))
        application.add_handler(CommandHandler("configuraravisos", configurar_avisos))
        application.add_handler(CommandHandler("testaravisos", testar_avisos))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_texto))
        application.add_handler(CommandHandler("meu_perfil", meu_perfil))
        application.add_handler(CommandHandler("tipo_usuario", set_tipo_usuario))
        application.add_handler(CommandHandler("modo_uso", set_modo_uso))
        application.add_handler(CommandHandler("profissional", adicionar_profissional))
        application.add_handler(CommandHandler("listar_profissionais", listar_profissionais))
        

        # 🚀 Adicionando os comandos de teste do Firebase
        application.add_handler(CommandHandler("testar_firebase", testar_firebase))
        application.add_handler(CommandHandler("verificar_firebase", verificar_firebase))

        logger.info("✅ Handlers registrados com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)