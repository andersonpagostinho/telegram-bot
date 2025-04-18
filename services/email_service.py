import imaplib
import smtplib
import email
from email.message import EmailMessage
import os
import json
import logging
from email.header import decode_header
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from utils.priority_utils import classificar_prioridade_email
from services.firebase_service import buscar_cliente

# ✅ Configurações de e-mail do .env
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
EMAIL_IMAP_PORT = os.getenv("EMAIL_IMAP_PORT", "993")
EMAIL_FOLDER = os.getenv("EMAIL_FOLDER", "INBOX")
REMETENTES_PRIORITARIOS = json.loads(os.getenv("REMETENTES_PRIORITARIOS", "[]"))

# ✅ Função para ler e-mails
def ler_emails(user_id=None, num_emails=5):
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
                "remetente": from_,
                "assunto": subject,
                "corpo": body
            }
            # 🔍 Adiciona prioridade se o user_id for fornecido
            if user_id:
                prioridade = classificar_prioridade_email(email_data, user_id)
                email_data["prioridade"] = prioridade
            else:
                email_data["prioridade"] = "baixa"  # ou use heurística simples

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

# 🔍 Buscar contatos por nome usando histórico de e-mails
def buscar_contatos_por_nome(user_id, nome):
    try:
        cliente = buscar_cliente(user_id)
        creds_info = cliente.get("email_credentials")
        if not creds_info:
            print("❌ Nenhuma credencial de e-mail encontrada.")
            return []

        creds = Credentials(
            token=creds_info["token"],
            refresh_token=creds_info["refresh_token"],
            token_uri=creds_info["token_uri"],
            client_id=creds_info["client_id"],
            client_secret=creds_info["client_secret"]
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", maxResults=30).execute()
        mensagens = results.get("messages", [])
        contatos_encontrados = {}

        for msg in mensagens:
            msg_data = service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From"]).execute()
            headers = msg_data["payload"]["headers"]
            for h in headers:
                if h["name"] == "From":
                    from_raw = h["value"]
                    if "<" in from_raw:
                        nome_contato, email = from_raw.split("<")
                        email = email.strip(">")
                        nome_contato = nome_contato.strip()
                    else:
                        nome_contato = email = from_raw.strip()

                    if nome.lower() in nome_contato.lower() or nome.lower() in email.lower():
                        contatos_encontrados[email] = nome_contato

        return [{"email": k, "nome": v} for k, v in contatos_encontrados.items()]
    
    except Exception as e:
        print(f"❌ Erro ao buscar contatos: {e}")
        return []

def filtrar_emails_prioritarios_por_palavras(emails, palavras_chave):
    return [
        email for email in emails
        if any(palavra.lower() in email.get("assunto", "").lower() for palavra in palavras_chave)
    ]
