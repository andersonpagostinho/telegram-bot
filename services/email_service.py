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
            emails.append(email_data)

        mail.close()
        mail.logout()
        return emails

    except Exception as e:
        logger.error(f"❌ Erro ao ler e-mails: {str(e)}")
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
