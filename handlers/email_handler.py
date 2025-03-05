import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from handlers.task_handler import add_task, list_tasks, clear_tasks
from services.email_service import ler_emails, enviar_email

logger = logging.getLogger(__name__)

# ✅ Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("🚀 Comando /start recebido!")
        await update.message.reply_text("👋 Olá! Bot funcionando via Webhooks!")
    except Exception as e:
        logger.error(f"Erro no /start: {e}", exc_info=True)

# ✅ Comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📖 Comando /help recebido!")
    await update.message.reply_text(
        "ℹ️ Comandos disponíveis:\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/tarefa - Adiciona uma tarefa\n"
        "/listar - Lista todas as tarefas\n"
        "/limpar - Remove todas as tarefas\n"
        "/ler_emails - Lê os últimos e-mails\n"
        "/emails_prioritarios - Lista e-mails importantes\n"
        "/enviar_email - Envia um e-mail\n"
    )

# ✅ comando ler email
async def ler_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emails = ler_emails()
    if emails:
        resposta = "📧 Emails:\n" + "\n".join(
    f"- De: {email.get('remetente', 'Desconhecido')}\n  Assunto: {email.get('assunto', 'Sem assunto')}\n  Mensagem: {email.get('corpo', 'Sem conteúdo')[:100]}..." 
    for email in emails
)

    else:
        resposta = "📭 Nenhum email encontrado."
    
    await update.message.reply_text(resposta)

# ✅ comando listar email
async def listar_emails_prioritarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emails = buscar_emails_prioritarios()
    if emails:
        resposta = "📧 Emails prioritários:\n" + "\n".join(emails)
    else:
        resposta = "📭 Nenhum email prioritário encontrado."

    await update.message.reply_text(resposta)

def buscar_emails_prioritarios():
    try:
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")
        remetentes_prioritarios = os.getenv("REMETENTES_PRIORITARIOS", "[]")

        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_password)
        mail.select("inbox")

        # Filtra e-mails apenas dos remetentes prioritários
        result, data = mail.search(None, 'FROM', remetentes_prioritarios)
        ids = data[0].split()

        return [f"Email {i+1}" for i in range(len(ids))]  # Simulação de e-mails retornados
    except Exception as e:
        print(f"❌ Erro ao buscar emails prioritários: {e}")
        return []

# ✅ comando enviar email
async def enviar_email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Use: /enviar_email destinatario@exemplo.com Assunto Mensagem")
        return

    destinatario = context.args[0]
    assunto = context.args[1]
    mensagem = " ".join(context.args[2:]) if len(context.args) > 2 else ""

    if enviar_email(destinatario, assunto, mensagem):
        await update.message.reply_text(f"✅ Email enviado para {destinatario}!")
    else:
        await update.message.reply_text("❌ Erro ao enviar email.")

def enviar_email(destinatario, assunto, mensagem):
    try:
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")

        msg = f"Subject: {assunto}\n\n{mensagem}"
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email_user, email_password)
        server.sendmail(email_user, destinatario, msg)
        server.quit()
        print(f"✅ Email enviado para {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False

# 🚀 Registra os handlers
def register_handlers(application: Application):
    try:
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("tarefa", add_task))
        application.add_handler(CommandHandler("listar", list_tasks))
        application.add_handler(CommandHandler("limpar", clear_tasks))
        application.add_handler(CommandHandler("ler_emails", ler_emails_command))
        application.add_handler(CommandHandler("emails_prioritarios", listar_emails_prioritarios))
        application.add_handler(CommandHandler("enviar_email", enviar_email_command))
        
        logger.info("✅ Handlers registrados com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)
