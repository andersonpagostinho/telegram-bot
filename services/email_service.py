import base64
import json
import os
import logging
import unicodedata
import re
import imaplib
import email
import smtplib
from email.header import decode_header
from email.message import EmailMessage
from utils.priority_utils import classificar_prioridade_email
from services.firebase_service_async import buscar_cliente
from email.mime.text import MIMEText
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

REMETENTES_PRIORITARIOS = json.loads(os.getenv("REMETENTES_PRIORITARIOS", "[]"))
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# 🔧 Função auxiliar para limpar dados do e-mail
def limpar_email(email):
    return {
        "remetente": email.get("remetente", "").strip(),
        "assunto": email.get("assunto", "").strip(),
        "corpo": email.get("corpo", "").strip()[:300],
        "prioridade": email.get("prioridade", "baixa"),
        "link": email.get("link", ""),
        "data": email.get("data")
    }

# ✅ Filtrar e-mails prioritários
async def listar_emails_prioritarios(user_id):
    emails = await ler_emails_google(user_id=user_id)
    return [email for email in emails if any(prior in email["remetente"] for prior in REMETENTES_PRIORITARIOS)]

# 📥 Ler e-mails via IMAP (com senha de app)
async def ler_emails_google(user_id, num_emails=5):
    try:
        cliente = await buscar_cliente(user_id)
        creds = cliente.get("email_config")  # novo padrão no Firestore

        if not creds:
            print("❌ Nenhuma configuração de e-mail encontrada.")
            return []

        imap_host = creds.get("imap_host", "imap.gmail.com")
        email_user = creds.get("email")
        senha_app = creds.get("senha_app")  # senha de app do Gmail

        if not all([imap_host, email_user, senha_app]):
            print("❌ Dados de conexão IMAP incompletos.")
            return []

        # 📡 Conectar ao servidor IMAP
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(email_user, senha_app)
        mail.select("inbox")

        # 🔎 Buscar todos os e-mails
        status, messages = mail.search(None, 'ALL')
        mail_ids = messages[0].split()
        emails_lidos = []

        for i in reversed(mail_ids[-num_emails * 3:]):  # lê mais para poder filtrar por data
            status, msg_data = mail.fetch(i, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            assunto = decode_header(msg["Subject"])[0][0]
            if isinstance(assunto, bytes):
                assunto = assunto.decode(errors="replace")

            remetente = msg.get("From")
            data_email_raw = msg.get("Date")

            try:
                data_email = email.utils.parsedate_to_datetime(data_email_raw)
                if not data_email:
                    continue
                if data_email < datetime.now() - timedelta(days=3):
                    continue  # ⏳ ignora e-mails antigos
                data_str = data_email.strftime('%Y-%m-%d %H:%M')
            except:
                continue  # ignora se a data for inválida

            # 📨 Extrair o corpo do e-mail
            corpo = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/plain":
                        corpo = part.get_payload(decode=True).decode(errors="replace")
                        break
            else:
                corpo = msg.get_payload(decode=True).decode(errors="replace")

            email_data = {
                "remetente": remetente,
                "assunto": assunto,
                "corpo": corpo[:500] + ("..." if len(corpo) > 500 else ""),
                "data": data_str,
                "link": "",  # IMAP não permite link direto
            }

            # 🧠 Classificar prioridade
            prioridade = classificar_prioridade_email(email_data, user_id)
            email_data["prioridade"] = prioridade

            # 🧹 Limpeza final e adição à lista
            emails_lidos.append(limpar_email(email_data))

            # Limita ao máximo solicitado
            if len(emails_lidos) >= num_emails:
                break

        mail.logout()
        print(f"📧 Emails lidos via IMAP: {len(emails_lidos)}")
        return emails_lidos

    except Exception as e:
        print(f"❌ Erro ao ler e-mails via IMAP: {e}")
        return []

# ✅ Função auxiliar para normalizar textos
def normalizar(txt):
    return unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode('utf-8').lower()

# ✅ Filtrar e-mails por nome citado no texto
def filtrar_emails_por_nome(texto, emails):
    genericos = {
        "me", "de", "para", "um", "uma", "o", "a", "e", "com", "sem", "da", "do",
        "tem", "tenho", "algum", "nenhum", "recebi", "mensagem", "email", "enviou"
    }

    palavras = re.findall(r"\b[\w\.-]{3,}@[\w\.-]+\.\w{2,}|\b[\wÀ-ÿ]{3,}\b", texto, re.IGNORECASE)
    palavras_filtradas = [normalizar(p) for p in palavras if normalizar(p) not in genericos]

    nome_mencionado = None
    emails_filtrados = []

    for termo in palavras_filtradas:
        for e in emails:
            remetente_raw = e.get("remetente", "")
            remetente_nome = re.sub(r"<.*?>", "", remetente_raw).strip()
            remetente_email_match = re.search(r"<(.+?)>", remetente_raw)
            remetente_email = remetente_email_match.group(1) if remetente_email_match else ""
            remetente_dominio = remetente_email.split("@")[1] if "@" in remetente_email else ""

            todos_dados = " ".join([
                remetente_nome,
                remetente_email,
                remetente_dominio,
                remetente_raw
            ])
            normalizado = normalizar(todos_dados)

            # 🔍 Procura todos os pedaços do termo no texto completo
            if all(p in normalizado for p in termo.split()) or termo in normalizado:
                nome_mencionado = termo
                emails_filtrados = [
                    em for em in emails if all(p in normalizar(em.get("remetente", "")) for p in termo.split())
                ]
                break
        if nome_mencionado:
            break

    return emails_filtrados, nome_mencionado

# 🔍 Buscar contatos por nome via IMAP
async def buscar_contatos_por_nome(user_id, nome):
    try:
        cliente = await buscar_cliente(user_id)
        creds = cliente.get("email_config")

        if not creds:
            print("❌ Nenhuma configuração de e-mail encontrada.")
            return []

        imap_host = creds.get("imap_host", "imap.gmail.com")
        email_user = creds.get("email")
        senha_app = creds.get("senha_app")

        if not all([imap_host, email_user, senha_app]):
            print("❌ Dados de conexão IMAP incompletos.")
            return []

        # Conecta via IMAP
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(email_user, senha_app)
        mail.select("inbox")

        # Pega as últimas 50 mensagens para busca (pode ajustar)
        status, messages = mail.search(None, "ALL")
        mail_ids = messages[0].split()

        contatos_encontrados = {}

        for i in reversed(mail_ids[-50:]):  # Limita a 50 mensagens
            status, msg_data = mail.fetch(i, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            remetente_raw = msg.get("From", "")
            remetente_decod = decode_header(remetente_raw)[0][0]
            remetente_decod = remetente_decod.decode() if isinstance(remetente_decod, bytes) else remetente_decod

            if "<" in remetente_decod:
                nome_contato, email_addr = remetente_decod.split("<")
                email_addr = email_addr.strip(">").strip()
                nome_contato = nome_contato.strip()
            else:
                nome_contato = email_addr = remetente_decod.strip()

            if nome.lower() in nome_contato.lower() or nome.lower() in email_addr.lower():
                contatos_encontrados[email_addr] = nome_contato

        mail.logout()

        return [{"email": k, "nome": v} for k, v in contatos_encontrados.items()]

    except Exception as e:
        print(f"❌ Erro ao buscar contatos via IMAP: {e}")
        return []

# 🔍 Filtrar por palavras-chave
def filtrar_emails_prioritarios_por_palavras(emails, palavras_chave):
    return [
        email for email in emails
        if any(palavra.lower() in email.get("assunto", "").lower() for palavra in palavras_chave)
    ]

# ✅ Enviar e-mail via SMTP com senha de app
async def enviar_email_google(user_id, destinatario, assunto, corpo):
    try:
        cliente = await buscar_cliente(user_id)
        creds = cliente.get("email_config")  # deve conter email, senha_app e host SMTP

        if not creds:
            print("❌ Nenhuma configuração de e-mail encontrada.")
            return False

        email_user = creds.get("email")
        senha_app = creds.get("senha_app")
        smtp_host = creds.get("smtp_host", "smtp.gmail.com")
        smtp_port = creds.get("smtp_port", 587)

        if not all([email_user, senha_app, smtp_host, smtp_port]):
            print("❌ Dados de envio de e-mail incompletos.")
            return False

        # ✉️ Monta a mensagem
        msg = MIMEText(corpo, "plain", "utf-8")
        msg["Subject"] = assunto
        msg["From"] = email_user
        msg["To"] = destinatario

        # 📡 Envia via SMTP
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(email_user, senha_app)
        server.send_message(msg)
        server.quit()

        print(f"✅ E-mail enviado via SMTP para {destinatario}")
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar e-mail via SMTP: {e}")
        return False