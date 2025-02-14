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
import threading

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ModuleNotFoundError:
    print("📌 'apscheduler' não encontrado. Instalando agora...")
    subprocess.check_call(["pip", "install", "apscheduler"])
    from apscheduler.schedulers.background import BackgroundScheduler

# Configuração de logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuração do Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
USER_WHATSAPP_NUMBER = "whatsapp:+5519990068427"
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Configuração do Telegram Bot
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.error("❌ ERRO: Variável TOKEN não encontrada!")
    raise ValueError("Token do Telegram não configurado!")

# Configuração do Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Tenta carregar as credenciais do ambiente ou do arquivo local
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not credentials_json:
    logger.error("❌ ERRO: Variável GOOGLE_CREDENTIALS_JSON não foi encontrada!")
    raise ValueError("Credenciais do Google não configuradas!")

# Converte JSON string para dicionário
credentials_json = json.loads(credentials_json)

def get_calendar_service():
    try:
        creds = service_account.Credentials.from_service_account_info(credentials_json, scopes=SCOPES)
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao Google Calendar: {str(e)}")
        return None

# Inicializar Firebase
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_credentials_json:
    raise ValueError("❌ ERRO: FIREBASE_CREDENTIALS não encontrado!")

try:
    cred_info = json.loads(firebase_credentials_json)
    cred = credentials.Certificate(cred_info)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("✅ Firebase inicializado com sucesso!")
except Exception as e:
    logger.error(f"❌ Erro ao inicializar Firebase: {str(e)}")
    raise

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

def salvar_evento(evento_data):
    try:
        evento_ref = db.collection("Eventos").document()
        evento_data["id"] = evento_ref.id
        evento_ref.set(evento_data)
        logger.info(f"✅ Evento salvo: {evento_data['titulo']}")
        return evento_ref.id
    except Exception as e:
        logger.error(f"❌ Erro ao salvar evento: {str(e)}")
        return None

def buscar_tarefas():
    try:
        return [{**doc.to_dict(), "id": doc.id} for doc in db.collection("Tarefas").stream()]
    except Exception as e:
        logger.error(f"❌ Erro ao buscar tarefas: {str(e)}")
        return []

def buscar_eventos():
    try:
        return [{**doc.to_dict(), "id": doc.id} for doc in db.collection("Eventos").stream()]
    except Exception as e:
        logger.error(f"❌ Erro ao buscar eventos: {str(e)}")
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
        logger.info(f"✅ Mensagem enviada para {USER_WHATSAPP_NUMBER}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar WhatsApp: {str(e)}")

# Funções de áudio
def converter_ogg_para_wav(ogg_path, wav_path):
    try:
        subprocess.run([
            "ffmpeg", "-i", ogg_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            wav_path
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erro na conversão de áudio: {e}")
        return False

def transcrever_audio(wav_path):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            texto = recognizer.recognize_google(audio, language="pt-BR")
            logger.info(f"✅ Transcrição: {texto}")
            return texto
    except sr.UnknownValueError:
        logger.error("❌ Áudio não reconhecido")
    except sr.RequestError as e:
        logger.error(f"❌ Erro no serviço de reconhecimento: {e}")
    return None

# Handlers do Telegram
async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    salvar_usuario(chat_id)
    await update.message.reply_text("👋 Olá! Vou gerenciar seus lembretes e eventos!")

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = """
    🛠 Comandos disponíveis:
    /start - Inicia o bot
    /help - Mostra ajuda
    /tarefa [descrição] - Adiciona tarefa
    /listar - Lista tarefas
    /listar_prioridade - Ordena por prioridade
    /limpar - Remove todas tarefas
    /agenda <título> <data-hora> - Agenda evento
    /eventos - Lista eventos
    """
    await update.message.reply_text(help_text)

async def handle_voice(update: Update, context: CallbackContext) -> None:
    try:
        voice_file = await update.message.voice.get_file()
        ogg_path = "temp_audio.ogg"
        await voice_file.download_to_drive(ogg_path)
        
        wav_path = "temp_audio.wav"
        if not converter_ogg_para_wav(ogg_path, wav_path):
            await update.message.reply_text("❌ Falha no processamento do áudio")
            return
            
        texto = transcrever_audio(wav_path)
        if texto:
            await update.message.reply_text(f"🎤 Você disse: {texto}")
            await processar_comando_voz(update, texto)
        else:
            await update.message.reply_text("❌ Não entendi o áudio")
            
        os.remove(ogg_path)
        os.remove(wav_path)
    except Exception as e:
        logger.error(f"❌ Erro no processamento de voz: {str(e)}")
        await update.message.reply_text("❌ Erro ao processar áudio")

async def processar_comando_voz(update: Update, texto: str):
    try:
        texto = texto.lower()
        
        if "adicionar tarefa" in texto:
            partes = texto.split(" com prioridade ")
            descricao = partes[0].replace("adicionar tarefa", "").strip()
            prioridade = partes[1].strip() if len(partes) > 1 else "baixa"
            
            prioridades_validas = {"alta", "média", "baixa"}
            prioridade = prioridade if prioridade in prioridades_validas else "baixa"
            
            tarefa_data = {
                "descricao": descricao,
                "prioridade": prioridade,
                "data_criacao": datetime.now().isoformat()
            }
            if salvar_tarefa(tarefa_data):
                msg = f"✅ Tarefa adicionada: {descricao} (Prioridade: {prioridade})"
                await update.message.reply_text(msg)
                send_whatsapp_message(msg)
                
        elif "agendar" in texto:
            partes = texto.split(" às ")
            if len(partes) != 2:
                await update.message.reply_text("⚠️ Formato: Agendar [título] às [data/hora]")
                return
                
            titulo = partes[0].replace("agendar", "").strip()
            data_hora = dateparser.parse(partes[1].strip(), languages=["pt"])
            
            if not data_hora:
                await update.message.reply_text("❌ Data/hora inválida")
                return
                
            start_time = data_hora.isoformat()
            end_time = (data_hora + timedelta(hours=1)).isoformat()
            
            event_link = add_event(titulo, start_time, end_time)
            if event_link:
                evento_data = {
                    "titulo": titulo,
                    "data": data_hora.strftime("%Y-%m-%d"),
                    "hora": data_hora.strftime("%H:%M:%S"),
                    "link": event_link,
                    "notificado": False
                }
                if salvar_evento(evento_data):
                    msg = f"✅ Evento '{titulo}' agendado para {data_hora.strftime('%d/%m/%Y %H:%M')}"
                    await update.message.reply_text(msg)
                    send_whatsapp_message(msg)
            else:
                await update.message.reply_text("❌ Falha ao criar evento")
                
        else:
            await update.message.reply_text("❌ Comando não reconhecido")
            
    except Exception as e:
        logger.error(f"❌ Erro no processamento de comando: {str(e)}")
        await update.message.reply_text("❌ Erro ao processar comando")

# Comandos de tarefas
async def add_task(update: Update, context: CallbackContext) -> None:
    try:
        args = context.args
        full_text = ' '.join(args)
        
        prioridade_match = re.search(r'-prioridade (\w+)', full_text)
        data_match = re.search(r'-data (.+?)(?= -|$)', full_text)
        
        prioridade = prioridade_match.group(1).lower() if prioridade_match else "baixa"
        data_vencimento = data_match.group(1) if data_match else None
        
        # Verifica se a data foi fornecida e é válida
        data_obj = None
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
            "data_vencimento": data_iso
        }
        
        if salvar_tarefa(tarefa_data):
            msg = f"✅ Tarefa adicionada:\n{descricao}\n📅 Vencimento: {data_obj.strftime('%d/%m/%Y') if data_obj else 'Sem data'}"
            await update.message.reply_text(msg)
            send_whatsapp_message(msg)
        else:
            await update.message.reply_text("❌ Erro ao adicionar tarefa.")
            
    except Exception as e:
        logger.error(f"❌ Erro ao adicionar tarefa: {str(e)}")
        await update.message.reply_text("❌ Erro ao processar tarefa")

async def list_tasks(update: Update, context: CallbackContext) -> None:
    try:
        tarefas = buscar_tarefas()
        if tarefas:
            task_list = "\n".join([f"• {t['descricao']}" for t in tarefas])
            msg = f"📋 Suas tarefas:\n{task_list}"
        else:
            msg = "📭 Nenhuma tarefa encontrada"
            
        await update.message.reply_text(msg)
        send_whatsapp_message(msg)
    except Exception as e:
        logger.error(f"❌ Erro ao listar tarefas: {str(e)}")
        await update.message.reply_text("❌ Erro ao buscar tarefas")

async def list_tasks_by_priority(update: Update, context: CallbackContext) -> None:
    try:
        tarefas = buscar_tarefas()
        if tarefas:
            prioridade_ordem = {"alta": 1, "média": 2, "baixa": 3}
            tarefas_ordenadas = sorted(tarefas, key=lambda x: prioridade_ordem[x.get("prioridade", "baixa")])
            task_list = "\n".join([f"• {t['descricao']} ({t['prioridade']})" for t in tarefas_ordenadas])
            msg = f"📌 Tarefas por prioridade:\n{task_list}"
        else:
            msg = "📭 Nenhuma tarefa encontrada"
            
        await update.message.reply_text(msg)
        send_whatsapp_message(msg)
    except Exception as e:
        logger.error(f"❌ Erro ao ordenar tarefas: {str(e)}")
        await update.message.reply_text("❌ Erro ao ordenar tarefas")

async def clear_tasks(update: Update, context: CallbackContext) -> None:
    try:
        batch = db.batch()
        tarefas_ref = db.collection("Tarefas").stream()
        
        for tarefa in tarefas_ref:
            batch.delete(tarefa.reference)
            
        batch.commit()
        msg = "🗑️ Todas as tarefas foram removidas"
        await update.message.reply_text(msg)
        send_whatsapp_message(msg)
    except Exception as e:
        logger.error(f"❌ Erro ao limpar tarefas: {str(e)}")
        await update.message.reply_text("❌ Erro ao limpar tarefas")

# Comandos de eventos
async def add_agenda(update: Update, context: CallbackContext) -> None:
    try:
        if len(context.args) < 2:
            msg = "⚠️ Use: /agenda <Título> <YYYY-MM-DDTHH:MM:SS>"
            await update.message.reply_text(msg)
            return
            
        titulo = context.args[0]
        data_hora = context.args[1]

        try:
            # Converte a string de data/hora para um objeto datetime
            dt = datetime.fromisoformat(data_hora)
        except ValueError:
            await update.message.reply_text("❌ Formato de data/hora inválido! Use: YYYY-MM-DDTHH:MM:SS")
            return
            
        # Define o horário de início e término do evento
        start_time = dt.isoformat()
        end_time = (dt + timedelta(hours=1)).isoformat()
        
        # Adiciona o evento ao Google Calendar
        event_link = add_event(titulo, start_time, end_time)
        if event_link:
            evento_data = {
                "titulo": titulo,
                "data": dt.strftime("%Y-%m-%d"),
                "hora": dt.strftime("%H:%M:%S"),
                "link": event_link,
                "notificado": False
            }
            if salvar_evento(evento_data):
                msg = f"✅ Evento '{titulo}' agendado para {dt.strftime('%d/%m/%Y %H:%M')}\n🔗 {event_link}"
                await update.message.reply_text(msg)
                send_whatsapp_message(msg)
            else:
                await update.message.reply_text("❌ Erro ao salvar evento no banco de dados.")
        else:
            await update.message.reply_text("❌ Erro ao criar evento no Google Calendar.")
            
    except Exception as e:
        logger.error(f"❌ Erro ao agendar evento: {str(e)}")
        await update.message.reply_text("❌ Erro ao agendar evento.")

async def list_events(update: Update, context: CallbackContext) -> None:
    try:
        eventos = buscar_eventos()
        if eventos:
            event_list = []
            for evento in eventos:
                event_list.append(
                    f"• {evento['titulo']}\n"
                    f"📅 {evento['data']} às {evento['hora']}\n"
                    f"🔗 {evento['link']}"
                )
            msg = "\n\n".join(event_list)
            await update.message.reply_text(f"📅 Eventos agendados:\n\n{msg}")
            send_whatsapp_message(f"📅 Eventos agendados:\n\n{msg}")
        else:
            msg = "📭 Nenhum evento agendado"
            await update.message.reply_text(msg)
            send_whatsapp_message(msg)
    except Exception as e:
        logger.error(f"❌ Erro ao listar eventos: {str(e)}")
        await update.message.reply_text("❌ Erro ao buscar eventos")

# Configuração do Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# 📌 Carrega as credenciais do ambiente (Render)
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not credentials_json:
    logger.error("❌ ERRO: Variável GOOGLE_CREDENTIALS_JSON não foi encontrada!")
    raise ValueError("Credenciais do Google não configuradas!")

# Converte JSON string para dicionário
try:
    credentials_json = json.loads(credentials_json)
except json.JSONDecodeError:
    logger.error("❌ ERRO: O formato das credenciais do Google está inválido!")
    raise ValueError("Erro ao decodificar JSON das credenciais do Google!")

def get_calendar_service():
    try:
        creds = service_account.Credentials.from_service_account_info(credentials_json, scopes=SCOPES)
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao Google Calendar: {str(e)}")
        return None

# Configuração do Flask
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "🤖 Bot em funcionamento!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port, use_reloader=False)

# Função principal
def main():
    try:
        app = Application.builder().token(TOKEN).build()
        
        # Registro de handlers
        handlers = [
            CommandHandler("start", start),
            CommandHandler("help", help_command),
            CommandHandler("tarefa", add_task),
            CommandHandler("listar", list_tasks),
            CommandHandler("listar_prioridade", list_tasks_by_priority),
            CommandHandler("limpar", clear_tasks),
            CommandHandler("agenda", add_agenda),
            CommandHandler("eventos", list_events),
            MessageHandler(filters.VOICE, handle_voice)
        ]
        
        app.add_handlers(handlers)
        
        # Iniciar Flask em thread separada
        threading.Thread(target=run_flask, daemon=True).start()
        
        logger.info("🚀 Iniciando bot...")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {str(e)}")
        raise

if __name__ == "__main__":
    main()