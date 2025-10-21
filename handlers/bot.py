import logging
import urllib.parse
from telegram import Update
from telegram.ext import ApplicationHandlerStop
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from handlers.task_handler import add_task, list_tasks, list_tasks_by_priority, clear_tasks
from handlers.email_handler import ler_emails_command, listar_emails_prioritarios, conectar_email
from handlers.event_handler import add_agenda, list_events, confirmar_reuniao, confirmar_presenca, debug_eventos, cancelar_evento_cmd
from services.firebase_service_async import buscar_cliente, salvar_cliente, verificar_firebase, buscar_documento
from handlers.test_handler import testar_firebase, testar_avisos
from handlers.report_handler import relatorio_diario, relatorio_semanal, enviar_relatorio_email
from handlers.importacao_handler import importar_profissionais_handler
from handlers.event_handler import enviar_agenda_excel
from router.principal_router import roteador_principal
from services.event_service_async import cancelar_evento
from firebase_admin import firestore
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
from handlers.encaixe_handler import handle_pedido_encaixe
from handlers.reagendamento_handler import handle_resposta_reagendamento
logger = logging.getLogger(__name__)

async def tratar_mensagens_gerais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📥 Entrou no tratar_mensagens_gerais()")

    # --- atalho para concluir cancelamento pendente por número ---
    pend = context.user_data.get("cancelamento_pendente")
    msg_txt = (getattr(update.message, "text", "") or "").strip()
    if pend and msg_txt.isdigit():
        idx = int(msg_txt) - 1
        cands = pend.get("candidatos", [])
        user_id = str(pend.get("user_id") or update.effective_user.id)

        if 0 <= idx < len(cands):
            try:
                eid_escolhido = cands[idx]
                ok = await cancelar_evento(user_id, eid_escolhido)
                if ok:
                    await update.message.reply_text("✅ Cancelamento concluído. Horário liberado.")
                else:
                    await update.message.reply_text("❌ Não consegui cancelar. Pode tentar novamente?")
            finally:
                context.user_data.pop("cancelamento_pendente", None)

            # impede que outros handlers peguem essa mesma mensagem
            raise ApplicationHandlerStop
        else:
            await update.message.reply_text("⚠️ Número inválido. Envie apenas o número da opção listada.")
            raise DispatcherHandlerStop
    # --- fim do atalho ---

    user_id = str(update.message.from_user.id)
    mensagem = msg_txt

    # 🔁 Chamada para o roteador inteligente (segue fluxo normal)
    resposta = await roteador_principal(user_id, mensagem, update, context)
    if resposta and isinstance(resposta, dict) and resposta.get("resposta"):
        await update.message.reply_text(resposta["resposta"], parse_mode="Markdown")

# ✅ Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = str(user.id)

    cliente_existente = await buscar_cliente(user_id)

    if cliente_existente:
        tipo_usuario = cliente_existente.get("tipo_usuario") or "cliente"
        id_negocio = cliente_existente.get("id_negocio") or user_id
    else:
        tipo_usuario = "dono"
        id_negocio = user_id

    modo_uso = "interno" if tipo_usuario == "dono" else "atendimento_cliente"

    # 💾 Dados para salvar ou atualizar
    dados = {
        "nome": f"{user.first_name} {user.last_name or ''}".strip(),
        "email": "",
        "pagamentoAtivo": True,
        "dataAssinatura": datetime.now().strftime("%Y-%m-%d"),
        "proximoPagamento": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "planosAtivos": ["secretaria"],
        "tipo_usuario": tipo_usuario,
        "modo_uso": modo_uso,
        "id_negocio": id_negocio,
        "tipo_negocio": "",
        "estilo": ""
    }

    await salvar_cliente(user_id, dados)

    if tipo_usuario == "dono":
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
        mensagem = (
            f"👋 Olá, {user.first_name}! Sou *NeoEve*, sua secretária virtual com inteligência contextual.\n\n"
            f"📌 Você foi conectado ao sistema de atendimento do negócio.\n"
            f"A qualquer momento, pode fazer perguntas como:\n"
            f"• “Tem horário para corte amanhã?”\n"
            f"• “Quem faz escova?”\n"
            f"• “Quais horários disponíveis hoje?”\n\n"
            f"😉 Se precisar de algo mais, estou aqui!"
        )

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

# ✅ Comando /custosapi – uso total da API por todos os usuários (somente dono)
async def custos_api_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    db = firestore.client()

    # ✅ Verifique se é o dono (por ID fixo)
    ID_DONO = "7394370553"  # ⬅️ coloque aqui seu ID do Telegram

    if user_id != ID_DONO:
        await update.message.reply_text("⚠️ Este comando está disponível apenas para o administrador do sistema.")
        return

    try:
        docs = db.collection("custos_usuarios").stream()

        total_geral = 0
        por_usuario = {}

        for doc in docs:
            data = doc.to_dict()
            uid = data.get("user_id", "desconhecido")
            custo = data.get("custo_usd", 0)

            if uid not in por_usuario:
                por_usuario[uid] = {"custo": 0, "reqs": 0}

            por_usuario[uid]["custo"] += custo
            por_usuario[uid]["reqs"] += 1
            total_geral += custo

        if not por_usuario:
            await update.message.reply_text("🔍 Nenhum uso registrado da API ainda.")
            return

        # 🧾 Monta relatório
        linhas = [
            f"👤 {uid}: {info['reqs']} reqs – ${info['custo']:.4f}"
            for uid, info in por_usuario.items()
        ]
        texto = "\n".join(linhas)

        resposta = (
            f"📊 *Resumo total de uso da API (todos os usuários)*\n\n"
            f"{texto}\n\n"
            f"💰 *Total geral:* ${total_geral:.4f}"
        )
        await update.message.reply_text(resposta, parse_mode="Markdown")

    except Exception as e:
        print("❌ Erro ao consultar custos da API:", e)
        await update.message.reply_text("❌ Ocorreu um erro ao consultar os dados.")

# 🚀 Registra os handlers
def register_handlers(application: Application):
    try:
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("tarefa", add_task))
        application.add_handler(CommandHandler("listar", list_tasks))
        application.add_handler(CommandHandler("limpar", clear_tasks))

        application.add_handler(CommandHandler(["ler_emails", "leremails"], ler_emails_command))
        application.add_handler(CommandHandler(["emails_prioritarios", "emailsprioritarios"], listar_emails_prioritarios))
        application.add_handler(CommandHandler(["conectar_email", "conectaremail"], conectar_email))

        application.add_handler(CommandHandler("agenda", add_agenda))
        application.add_handler(CommandHandler("eventos", list_events))
        application.add_handler(CommandHandler(["confirmar_reuniao", "confirmarreuniao"], confirmar_reuniao))
        application.add_handler(CommandHandler(["confirmar_presenca", "confirmarpresenca"], confirmar_presenca))
        application.add_handler(CommandHandler(["debug_eventos"], debug_eventos))

        application.add_handler(CommandHandler(["relatorio_diario", "relatoriodiario"], relatorio_diario))
        application.add_handler(CommandHandler(["relatorio_semanal", "relatoriosemanal"], relatorio_semanal))
        application.add_handler(CommandHandler(["enviar_agenda_excel"], enviar_agenda_excel))

        application.add_handler(CommandHandler(["tipo_negocio", "tiponegocio"], set_tipo_negocio))
        application.add_handler(CommandHandler(["estilo"], set_estilo_mensagem))
        application.add_handler(CommandHandler(["nome_negocio", "nomenegocio"], set_nome_negocio))
        application.add_handler(CommandHandler(["meu_estilo", "meuestilo"], meu_estilo))
        application.add_handler(CommandHandler(["meu_email", "meuemail"], set_email))

        application.add_handler(MessageHandler(filters.VOICE, handle_voice))

        application.add_handler(CommandHandler("meuplano", meu_plano))
        application.add_handler(CommandHandler("followup", criar_followup))
        application.add_handler(CommandHandler("meusfollowups", listar_followups))
        application.add_handler(CommandHandler("verificaravisos", verificar_avisos))
        application.add_handler(CommandHandler("configuraravisos", configurar_avisos))
        application.add_handler(CommandHandler("testaravisos", testar_avisos))
        application.add_handler(CommandHandler(["meu_perfil", "meuperfil"], meu_perfil))
        application.add_handler(CommandHandler(["tipo_usuario", "tipousuario"], set_tipo_usuario))
        application.add_handler(CommandHandler(["modo_uso", "modouso"], set_modo_uso))
        application.add_handler(CommandHandler(["listar_profissionais", "listarprofissionais"], listar_profissionais))
        application.add_handler(CommandHandler("custosapi", custos_api_handler))
        application.add_handler(CommandHandler(["meus_dados", "meusdados"], meus_dados))

        # (opcional) filtro que evita números puros irem para handlers gerais
        so_texto_nao_num = filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^\d+$")

        # a ORDEM importa: geral primeiro
        application.add_handler(MessageHandler(so_texto_nao_num, tratar_mensagens_gerais))
        application.add_handler(MessageHandler(so_texto_nao_num, handle_pedido_encaixe))
        application.add_handler(MessageHandler(so_texto_nao_num, handle_resposta_reagendamento))

        application.add_handler(CommandHandler("cancelar", cancelar_evento_cmd))

        application.add_handler(MessageHandler(
            filters.Document.MimeType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            importar_profissionais_handler
        ))
        application.add_handler(MessageHandler(
            filters.Document.MimeType("text/csv"),
            importar_profissionais_handler
        ))

        # Comandos de teste do Firebase
        application.add_handler(CommandHandler("testar_firebase", testar_firebase))
        application.add_handler(CommandHandler("verificar_firebase", verificar_firebase))

        print("📌 Handlers do bot.py carregados")
        logger.info("✅ Handlers registrados com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)