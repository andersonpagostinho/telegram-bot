import os
import json
import re
import logging
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from twilio.rest import Client
from flask import Flask
import speech_recognition as sr
import subprocess
import dateparser
import subprocess
import sys

# Verifica se o apscheduler está instalado e instala se necessário
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ModuleNotFoundError:
    print("📌 'apscheduler' não encontrado. Instalando agora...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "apscheduler"])
    from apscheduler.schedulers.background import BackgroundScheduler

# Configuração de logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuração do Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
USER_WHATSAPP_NUMBER = "whatsapp:+5519990068427"  # Substitua pelo seu número
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Configuração do Telegram Bot
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.error("❌ ERRO: A variável de ambiente TOKEN do Telegram não foi encontrada!")
    raise ValueError("⚠️ ERRO: A variável de ambiente TOKEN do Telegram não foi encontrada!")

# Configuração do Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not credentials_json:
    logger.error("❌ ERRO: A variável de ambiente GOOGLE_CREDENTIALS_JSON não foi encontrada!")
    raise ValueError("⚠️ ERRO: GOOGLE_CREDENTIALS_JSON não foi encontrada!")

# Inicializar Firebase
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_credentials_json:
    raise ValueError("❌ ERRO: A variável de ambiente FIREBASE_CREDENTIALS não foi encontrada!")

cred_info = json.loads(firebase_credentials_json)
cred = credentials.Certificate(cred_info)
firebase_admin.initialize_app(cred)
db = firestore.client()
logger.info("✅ Firebase inicializado com sucesso!")

# Funções do Firebase
def salvar_tarefa(tarefa_data):
    try:
        if "data_vencimento" not in tarefa_data:
            tarefa_data["data_vencimento"] = (datetime.now() + timedelta(days=3)).isoformat()
            
        tarefa_ref = db.collection("Tarefas").document()
        tarefa_data["id"] = tarefa_ref.id
        tarefa_ref.set(tarefa_data)
        logger.info(f"✅ Tarefa salva: {tarefa_data['descricao']}")
        return tarefa_ref.id
    except Exception as e:
        logger.error(f"❌ Erro ao salvar tarefa: {str(e)}")
        return None

def buscar_tarefas():
    try:
        return [
            {**tarefa.to_dict(), "id": tarefa.id} 
            for tarefa in db.collection("Tarefas").stream()
        ]
    except Exception as e:
        logger.error(f"❌ Erro buscar tarefas: {str(e)}")
        return []

def buscar_eventos():
    try:
        return [
            {**evento.to_dict(), "id": evento.id}
            for evento in db.collection("Eventos").stream()
        ]
    except Exception as e:
        logger.error(f"❌ Erro buscar eventos: {str(e)}")
        return []

def salvar_usuario(chat_id):
    try:
        db.collection("Usuarios").document(str(chat_id)).set({
            "chat_id": chat_id,
            "ativo": True,
            "data_registro": datetime.now().isoformat()
        })
        logger.info(f"✅ Usuário registrado: {chat_id}")
    except Exception as e:
        logger.error(f"❌ Erro ao salvar usuário: {str(e)}")

def buscar_usuarios():
    try:
        return [user.to_dict() for user in db.collection("Usuarios").where("ativo", "==", True).stream()]
    except Exception as e:
        logger.error(f"❌ Erro ao buscar usuários: {str(e)}")
        return []

# Funções de notificação
def send_whatsapp_message(message: str):
    try:
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=USER_WHATSAPP_NUMBER
        )
        logger.info(f"✅ Mensagem enviada para {USER_WHATSAPP_NUMBER}: {message}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem pelo WhatsApp: {str(e)}")

# Agendamento de lembretes
def inicializar_agendamento(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(verificar_lembretes, 'interval', minutes=5, args=[app])
    scheduler.start()
    logger.info("✅ Agendador de lembretes inicializado")

def verificar_lembretes(app):
    try:
        agora = datetime.now()
        enviar_lembretes_tarefas(app, agora)
        enviar_lembretes_eventos(app, agora)
    except Exception as e:
        logger.error(f"❌ Erro geral em verificar_lembretes: {str(e)}")

def enviar_lembretes_tarefas(app, agora):
    for tarefa in buscar_tarefas():
        try:
            if tarefa.get("lembrete_enviado", False):
                continue

            data_venc = datetime.fromisoformat(tarefa["data_vencimento"])
            dias_restantes = (data_venc - agora).days

            if dias_restantes in [1, 3]:
                mensagem = f"⏰ LEMBRETE TAREFA\n📝 {tarefa['descricao']}\n📅 Vence em {dias_restantes} dia(s)"
                enviar_notificacao(app, mensagem, tarefa)
                
        except Exception as e:
            logger.error(f"❌ Erro em tarefa {tarefa['id']}: {str(e)}")

def enviar_lembretes_eventos(app, agora):
    for evento in buscar_eventos():
        try:
            if evento.get("lembrete_enviado", False):
                continue

            data_hora = datetime.fromisoformat(f"{evento['data']}T{evento['hora']}")
            diff = (data_hora - agora).total_seconds() / 3600

            if 0.5 <= diff <= 24:
                horas_restantes = int(diff)
                mensagem = f"⏰ LEMBRETE EVENTO\n📌 {evento['titulo']}\n⏳ Começa em {horas_restantes} hora(s)"
                enviar_notificacao(app, mensagem, evento)

        except Exception as e:
            logger.error(f"❌ Erro em evento {evento['id']}: {str(e)}")

def enviar_notificacao(app, mensagem, item):
    try:
        chat_ids = [user["chat_id"] for user in buscar_usuarios()]
        for chat_id in chat_ids:
            app.bot.send_message(chat_id=chat_id, text=mensagem)
        
        send_whatsapp_message(mensagem)
        
        colecao = "Tarefas" if "descricao" in item else "Eventos"
        db.collection(colecao).document(item["id"]).update({"lembrete_enviado": True})
        
        logger.info(f"✅ Notificação enviada: {mensagem}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar notificação: {str(e)}")

# Handlers do Telegram
async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    salvar_usuario(chat_id)
    await update.message.reply_text("👋 Olá! Vou te enviar lembretes de tarefas e eventos importantes.")

async def add_task(update: Update, context: CallbackContext) -> None:
    try:
        args = context.args
        full_text = ' '.join(args)
        
        prioridade_match = re.search(r'-prioridade (\w+)', full_text)
        data_match = re.search(r'-data (.+?)(?= -|$)', full_text)
        
        prioridade = prioridade_match.group(1).lower() if prioridade_match else "baixa"
        data_vencimento = data_match.group(1) if data_match else None
        
        if data_vencimento:
            data_obj = dateparser.parse(data_vencimento, languages=['pt'])
            if not data_obj:
                await update.message.reply_text("❌ Data inválida! Use o formato: dd/mm/aaaa ou 'amanhã'")
                return
            data_iso = data_obj.isoformat()
        else:
            data_iso = (datetime.now() + timedelta(days=3)).isoformat()

        descricao = re.sub(r'(-prioridade \w+|-data .+?)', '', full_text).strip()

        if not descricao:
            await update.message.reply_text("⚠️ Formato correto:\n/tarefa Comprar leite -prioridade alta -data amanhã")
            return

        tarefa_data = {
            "descricao": descricao,
            "prioridade": prioridade,
            "data_criacao": datetime.now().isoformat(),
            "data_vencimento": data_iso,
            "lembrete_enviado": False
        }
        
        if salvar_tarefa(tarefa_data):
            await update.message.reply_text(f"✅ Tarefa adicionada:\n{descricao}\n📅 Vencimento: {data_obj.strftime('%d/%m/%Y')}")
    except Exception as e:
        logger.error(f"❌ Erro no comando /tarefa: {str(e)}")
        await update.message.reply_text("❌ Erro ao processar tarefa. Verifique o formato!")

async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"❌ Erro crítico: {context.error}")
    await update.message.reply_text("⚠️ Ocorreu um erro interno. Nossa equipe já foi notificada.")
    send_whatsapp_message(f"🚨 ERRO NO BOT: {context.error}")

# Configuração do Flask
app_web = Flask(__name__)
@app_web.route("/")
def home():
    return "Bot rodando!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# Função principal
def main():
    app = Application.builder().token(TOKEN).build()
    
    inicializar_agendamento(app)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tarefa", add_task))
    app.add_error_handler(error_handler)

    threading.Thread(target=run_flask, daemon=True).start()
    
    logger.info("🚀 Bot rodando com polling...")
    app.run_polling()

if __name__ == "__main__":
    main()