import logging
import os
import smtplib
import imaplib
import json
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from handlers.task_handler import add_task, list_tasks, clear_tasks
from services.email_service import ler_emails, buscar_contatos_por_nome
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from services.firebase_service import salvar_cliente, buscar_cliente

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
        "/conectar_email - Conectar seu e-mail ao sistema\n"
    )

# ✅ Conectar email via OAuth 2.0
async def conectar_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    print(f"🔍 Iniciando conexão do email para o usuário {user_id}")

    try:
        # Pegando credenciais do ambiente
        credentials_json = os.getenv("OAUTH_CREDENTIALS")  # Pegando a variável correta do Render
        if not credentials_json:
            await update.message.reply_text("❌ Erro: Credenciais do Google não encontradas no ambiente!")
            return

        # Salvando credenciais temporariamente
        temp_credentials_path = "/tmp/google_credentials.json"
        try:
            creds_data = json.loads(credentials_json)  # Verifica se o JSON está válido
            with open(temp_credentials_path, "w") as cred_file:
                json.dump(creds_data, cred_file, indent=4)
        # Salva corretamente
        except json.JSONDecodeError:
            logger.error("❌ Erro ao decodificar JSON das credenciais do Google.")
            await update.message.reply_text("❌ Erro: Credenciais do Google inválidas.")
            return

        flow = InstalledAppFlow.from_client_secrets_file(
    temp_credentials_path,
    scopes=["https://www.googleapis.com/auth/gmail.readonly"
            "https://www.googleapis.com/auth/userinfo.email"
],
    redirect_uri="https://telegram-bot-a7a7.onrender.com/oauth2callback"
)

        auth_url, _ = flow.authorization_url(prompt="consent")
        context.user_data["flow"] = flow  
        # Salvando fluxo para uso no callback

        await update.message.reply_text(
            f"🔗 Para conectar seu e-mail, clique no link abaixo e autorize o acesso:\n\n{auth_url}"
        )

    except Exception as e:
        logger.error(f"❌ Erro ao conectar e-mail: {e}", exc_info=True)
        await update.message.reply_text("❌ Erro ao conectar o e-mail. Verifique as configurações.")

    if not os.path.exists(temp_credentials_path):
        logger.error(f"❌ O arquivo {temp_credentials_path} não foi criado corretamente!")
        await update.message.reply_text("❌ Erro: Credenciais não foram salvas corretamente.")
        return

# ✅ Callback para capturar o código e salvar o token
async def auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if "flow" not in context.user_data:
        await update.message.reply_text("❌ Erro: Nenhuma solicitação de autenticação encontrada.")
        return

    flow = context.user_data["flow"]
    query = context.args[0] if context.args else ""

    if "code=" not in query:
        await update.message.reply_text("❌ Erro ao obter o código de autorização.")
        return

    code = query.split("code=")[1].split("&")[0]

    flow.fetch_token(code=code)
    credentials = flow.credentials

    # 🔍 Recuperar o e-mail do usuário via Google API
    email_usuario = None
    try:
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        )
        if resp.status_code == 200:
            email_usuario = resp.json().get("email")
    except Exception as e:
        print(f"⚠️ Não foi possível recuperar o e-mail: {e}")

    # 🔐 Salvar credenciais + e-mail no Firebase
    salvar_cliente(user_id, {
        "email": email_usuario,  # ✅ se estiver disponível, salva
        "email_credentials": {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret
        }
    })

    await update.message.reply_text("✅ Seu e-mail foi conectado com sucesso!")

# ✅ Buscar emails prioritários
def buscar_emails_prioritarios():
    try:
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")
        remetentes_prioritarios = json.loads(os.getenv("REMETENTES_PRIORITARIOS", "[]"))

        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_password)
        mail.select("inbox")

        emails_prioritarios = []
        for remetente in remetentes_prioritarios:
            result, data = mail.search(None, f'FROM "{remetente}"')
            ids = data[0].split()
            emails_prioritarios.extend([f"Email de {remetente}" for _ in ids])

        return emails_prioritarios
    except Exception as e:
        logger.error(f"❌ Erro ao buscar emails prioritários: {e}", exc_info=True)
        return []

# ✅ Listar emails prioritários
async def listar_emails_prioritarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emails = buscar_emails_prioritarios()
    if emails:
        resposta = "📧 Emails prioritários:\n" + "\n".join(emails)
    else:
        resposta = "📭 Nenhum email prioritário encontrado."
    await update.message.reply_text(resposta)

# ✅ Comando para ler emails
async def ler_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    emails = ler_emails(user_id=user_id)
    if emails:
        resposta = "📧 Emails:\n" + "\n".join(
            f"- De: {email.get('remetente', 'Desconhecido')}\n  Assunto: {email.get('assunto', 'Sem assunto')}\n  Mensagem: {email.get('corpo', email.get('preview', 'Sem conteúdo'))[:300]}..." 
            for email in emails
        )
    else:
        resposta = "📭 Nenhum email encontrado."
    
    await update.message.reply_text(resposta)

# ✅ Enviar email
async def enviar_email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    # Se usuário estiver respondendo com a opção (ex: "1")
    if context.user_data.get("contatos_em_espera"):
        escolha = update.message.text.strip()
        if escolha.isdigit():
            escolha_idx = int(escolha) - 1
            contatos = context.user_data["contatos_em_espera"]
            if 0 <= escolha_idx < len(contatos):
                escolhido = contatos[escolha_idx]
                destinatario = escolhido["email"]
                assunto = context.user_data["assunto_em_espera"]
                mensagem = context.user_data["mensagem_em_espera"]

                sucesso = enviar_email(destinatario, assunto, mensagem)
                del context.user_data["contatos_em_espera"]
                await update.message.reply_text("✅ E-mail enviado para: " + destinatario if sucesso else "❌ Erro ao enviar e-mail.")
                return

        await update.message.reply_text("❌ Opção inválida. Tente novamente.")
        return

    # Primeiro uso do comando
    if len(context.args) < 3:
        await update.message.reply_text("⚠️ Uso correto: /enviar_email <nome ou email> <assunto> <mensagem>")
        return

    entrada = context.args[0]
    assunto = context.args[1]
    mensagem = " ".join(context.args[2:])

    if "@" in entrada:
        # E-mail direto
        sucesso = enviar_email(entrada, assunto, mensagem)
        await update.message.reply_text("✅ E-mail enviado com sucesso!" if sucesso else "❌ Erro ao enviar e-mail.")
    else:
        # Nome — buscar no Gmail via API
        contatos = buscar_contatos_por_nome(user_id, entrada)
        if not contatos:
            await update.message.reply_text("❌ Nenhum contato encontrado com esse nome.")
            return

        if len(contatos) == 1:
            sucesso = enviar_email(contatos[0]["email"], assunto, mensagem)
            await update.message.reply_text(f"✅ E-mail enviado para {contatos[0]['email']}" if sucesso else "❌ Erro ao enviar e-mail.")
        else:
            # Salva no contexto e pede confirmação
            context.user_data["contatos_em_espera"] = contatos
            context.user_data["assunto_em_espera"] = assunto
            context.user_data["mensagem_em_espera"] = mensagem

            opcoes = "\n".join([f"{i+1}. {c['nome']} - {c['email']}" for i, c in enumerate(contatos)])
            await update.message.reply_text(
                f"📩 Achei mais de um contato com esse nome:\n\n{opcoes}\n\nResponda com o número do contato desejado."
            )

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
        logger.error(f"❌ Erro ao enviar email: {e}", exc_info=True)
        return False

# 🚀 Registra os handlers
def register_handlers(application: Application):
    try:
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("conectar_email", conectar_email))
        application.add_handler(CommandHandler("auth_callback", auth_callback))
        logger.info("✅ Handlers registrados com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)
