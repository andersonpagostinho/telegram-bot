import imaplib
import smtplib
import email
from email.message import EmailMessage
import os
import json

# Configurações de e-mail do .env
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FOLDER = os.getenv("EMAIL_FOLDER", "INBOX")
REMETENTES_PRIORITARIOS = json.loads(os.getenv("REMETENTES_PRIORITARIOS", "[]"))

# ✅ Função para ler e-mails
def ler_emails():
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_HOST)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select(EMAIL_FOLDER)
        
        _, data = mail.search(None, "ALL")
        email_ids = data[0].split()
        emails = []
        
        for e_id in email_ids[-5:]:  # Lê os últimos 5 e-mails
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    remetente = msg["From"]
                    assunto = msg["Subject"]
                    emails.append({"remetente": remetente, "assunto": assunto})
        
        mail.logout()
        return emails
    except Exception as e:
        print(f"❌ Erro ao ler e-mails: {e}")
        return []

# ✅ Função para filtrar e-mails prioritários
def listar_emails_prioritarios():
    emails = ler_emails()
    return [email for email in emails if any(prior in email["remetente"] for prior in REMETENTES_PRIORITARIOS)]

# ✅ Função para enviar e-mails
def enviar_email(destinatario, assunto, corpo):
    try:
        msg = EmailMessage()
        msg["From"] = EMAIL_USER
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.set_content(corpo)
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ E-mail enviado para {destinatario}!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        return False
