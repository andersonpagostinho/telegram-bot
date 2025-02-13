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
from apscheduler.schedulers.background import BackgroundScheduler
import threading

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

# Funções de áudio
def converter_ogg_para_wav(ogg_path, wav_path):
    try:
        comando = [
            "ffmpeg", "-i", ogg_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            wav_path
        ]
        subprocess.run(comando, check=True)
        logger.info(f"✅ Áudio convertido: {wav_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erro ao converter áudio: {e}")
        return False

def transcrever_audio(wav_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
        try:
            texto = recognizer.recognize_google(audio, language="pt-BR")
            logger.info(f"✅ Áudio transcrito: {texto}")
            return texto
        except sr.UnknownValueError:
            logger.error("❌ Não foi possível transcrever o áudio.")
            return None
        except sr.RequestError as e:
            logger.error(f"❌ Erro na requisição ao Google Speech-to-Text: {e}")
            return None

# Handlers do Telegram
async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    salvar_usuario(chat_id)
    await update.message.reply_text("👋 Olá! Vou te enviar lembretes de tarefas e eventos importantes.")

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = """
    🛠 Comandos disponíveis:
    /start - Inicia o bot
    /help - Mostra esta ajuda
    /tarefa [descrição] - Adiciona uma tarefa
    /listar - Lista todas as tarefas
    /limpar - Remove todas as tarefas
    /agenda <título> <data-hora (YYYY-MM-DDTHH:MM:SS)> - Agenda um evento
    /eventos - Lista todos os eventos agendados
    """
    await update.message.reply_text(help_text)

async def handle_voice(update: Update, context: CallbackContext) -> None:
    voice_file = await update.message.voice.get_file()
    ogg_path = "temp_audio.ogg"
    await voice_file.download_to_drive(ogg_path)

    wav_path = "temp_audio.wav"
    if not converter_ogg_para_wav(ogg_path, wav_path):
        await update.message.reply_text("❌ Erro ao processar o áudio. Tente novamente.")
        return

    texto = transcrever_audio(wav_path)
    if not texto:
        await update.message.reply_text("❌ Não entendi o áudio. Pode repetir?")
        return

    await update.message.reply_text(f"🎤 Você disse: {texto}")
    await processar_comando_voz(update, texto)

    os.remove(ogg_path)
    os.remove(wav_path)
    logger.info("✅ Arquivos temporários removidos.")

async def processar_comando_voz(update: Update, texto: str):
    texto = texto.lower()

    if "adicionar tarefa" in texto:
        partes = texto.split(" com prioridade ")
        descricao = partes[0].replace("adicionar tarefa", "").strip()
        prioridade = partes[1].strip() if len(partes) > 1 else "baixa"

        prioridades_validas = ["alta", "média", "baixa"]
        if prioridade not in prioridades_validas:
            prioridade = "baixa"

        tarefa_data = {
            "descricao": descricao,
            "prioridade": prioridade,
            "data_criacao": datetime.now().isoformat()
        }
        salvar_tarefa(tarefa_data)
        await update.message.reply_text(f"✅ Tarefa adicionada: {descricao} (Prioridade: {prioridade})")
        send_whatsapp_message(f"✅ Tarefa adicionada: {descricao} (Prioridade: {prioridade})")

    elif "agendar" in texto:
        partes = texto.split(" às ")
        if len(partes) < 2:
            await update.message.reply_text("⚠️ Formato inválido. Use: Agendar [título] [data/hora]")
            return

        titulo = partes[0].replace("agendar", "").strip()
        data_hora_texto = partes[1].strip()

        data_hora = dateparser.parse(data_hora_texto, languages=["pt"])
        if not data_hora:
            await update.message.reply_text("❌ Não entendi a data/hora. Pode reformular?")
            return

        start_time = f"{data_hora.isoformat()}-03:00"
        end_time = f"{data_hora.isoformat()}-03:00"
        event_link = add_event(titulo, start_time, end_time)
        if event_link:
            evento_data = {
                "titulo": titulo,
                "data": data_hora.strftime("%Y-%m-%d"),
                "hora": data_hora.strftime("%H:%M:%S"),
                "link": event_link,
                "notificado": False
            }
            salvar_evento(evento_data)
            await update.message.reply_text(f"✅ Evento '{titulo}' agendado para {data_hora}.")
            send_whatsapp_message(f"✅ Evento '{titulo}' agendado para {data_hora}.")
        else:
            await update.message.reply_text("❌ Erro ao agendar evento!")
            send_whatsapp_message("❌ Erro ao agendar evento!")
    else:
        await update.message.reply_text("❌ Comando não reconhecido.")
        send_whatsapp_message("❌ Comando não reconhecido.")

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
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Iniciar Flask em uma thread separada
    threading.Thread(target=run_flask, daemon=True).start()

    # Iniciar bot
    logger.info("🚀 Bot rodando com polling...")
    app.run_polling()

if __name__ == "__main__":
    main()