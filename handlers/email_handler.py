import logging
import os
import re
import smtplib
import imaplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from handlers.task_handler import add_task, list_tasks, clear_tasks
from services.email_service import ler_emails

logger = logging.getLogger(__name__)

# Configuração de Email
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER")
EMAIL_IMAP_PORT = os.getenv("EMAIL_IMAP_PORT")

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
def ler_emails(num_emails=5):
    try:
        if not all([EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT, EMAIL_USER, EMAIL_PASSWORD]):
            logger.error("❌ Variáveis de ambiente IMAP não configuradas")
            return []

        mail = imaplib.IMAP4_SSL(EMAIL_IMAP_SERVER, int(EMAIL_IMAP_PORT))
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select(EMAIL_FOLDER)

        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            logger.info("📭 Nenhum e-mail novo encontrado.")
            return []

        email_ids = messages[0].split()[-num_emails:]

        emails = []
        for e_id in email_ids:
            _, msg_data = mail.fetch(e_id, '(RFC822)')
            raw_email = msg_data[0][1]
            
            msg = email.message_from_bytes(raw_email)
            
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8', errors='replace')
            
            from_, encoding = decode_header(msg.get("From"))[0]
            if isinstance(from_, bytes):
                from_ = from_.decode(encoding or 'utf-8', errors='replace')

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        try:
                            body = payload.decode('utf-8', errors='replace')
                        except UnicodeDecodeError:
                            body = payload.decode('latin-1', errors='replace')
                        break
            else:
                payload = msg.get_payload(decode=True)
                try:
                    body = payload.decode('utf-8', errors='replace')
                except UnicodeDecodeError:
                    body = payload.decode('latin-1', errors='replace')

            if len(body) > 500:
                body = body[:500] + "..."

            email_data = {
                "de": from_,
                "assunto": subject,
                "corpo": body
            }
            salvar_email_classificado(email_data)
            emails.append(email_data)

        mail.close()
        mail.logout()
        return emails

    except Exception as e:
        logger.error(f"❌ Erro ao ler e-mails: {str(e)}")
        return []

# ✅ Buscar emails prioritários
def buscar_emails_prioritarios():
    try:
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")
        remetentes_prioritarios = os.getenv("REMETENTES_PRIORITARIOS", "[]")

        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_password)
        mail.select("inbox")

        result, data = mail.search(None, 'FROM', remetentes_prioritarios)
        ids = data[0].split()
        return [f"Email {i+1}" for i in range(len(ids))]  # Simulação de e-mails retornados
    except Exception as e:
        print(f"❌ Erro ao buscar emails prioritários: {e}")
        return []

# ✅ Enviar email
async def enviar_email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 3:
            await update.message.reply_text("⚠️ Uso correto: /enviar_email <destinatário> <assunto> <mensagem>")
            return

        destinatario = context.args[0]
        assunto = context.args[1]
        mensagem = " ".join(context.args[2:])

        if enviar_email(destinatario, assunto, mensagem):
            await update.message.reply_text(f"📧 Email enviado para {destinatario} com sucesso!")
        else:
            await update.message.reply_text("❌ Erro ao enviar email.")

    except Exception as e:
        logger.error(f"Erro ao enviar email: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Erro ao enviar email: {e}")

# ✅ Função de envio de email
def enviar_email(destinatario, assunto, mensagem):
    try:
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")
        email_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
        email_port = int(os.getenv("EMAIL_PORT", 587))
        
        if not email_user or not email_password:
            raise ValueError("❌ EMAIL_USER ou EMAIL_PASSWORD não foram carregados corretamente!")

        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(mensagem, 'plain'))

        server = smtplib.SMTP(email_host, email_port)
        server.starttls()
        server.login(email_user, email_password)
        server.sendmail(email_user, destinatario, msg.as_string())
        server.quit()
        
        print(f"✅ Email enviado para {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False

# ✅ Função de listar email
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
        remetentes_prioritarios = json.loads(os.getenv("REMETENTES_PRIORITARIOS", "[]"))

        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_password)
        mail.select("inbox")

        # Buscar emails apenas dos remetentes prioritários
        emails_prioritarios = []
        for remetente in remetentes_prioritarios:
            result, data = mail.search(None, f'FROM "{remetente}"')
            ids = data[0].split()
            emails_prioritarios.extend([f"Email de {remetente}" for _ in ids])

        return emails_prioritarios
    except Exception as e:
        print(f"❌ Erro ao buscar emails prioritários: {e}")
        return []

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
