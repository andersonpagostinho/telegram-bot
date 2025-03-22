import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Senha de aplicativo

print(f"📩 EMAIL_USER: {EMAIL_USER}")
print(f"🔑 EMAIL_PASSWORD: {'EXISTS' if EMAIL_PASSWORD else 'MISSING'}")  # Evita exibir senha real

def enviar_email(destinatario, assunto, mensagem):
    try:
        # Verificar se as credenciais não estão vazias
        if not EMAIL_USER or not EMAIL_PASSWORD:
            raise ValueError("❌ Erro: EMAIL_USER ou EMAIL_PASSWORD estão vazios!")

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)

        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.attach(MIMEText(mensagem, "plain"))

        server.sendmail(EMAIL_USER, destinatario, msg.as_string())
        server.quit()

        print(f"✅ E-mail enviado para {destinatario}!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        return False

# 🔹 Teste de envio
destinatario = "andersonpagostinho@gmail.com"
assunto = "Teste de envio"
mensagem = "Este é um e-mail de teste enviado pelo bot."
enviar_email(destinatario, assunto, mensagem)
