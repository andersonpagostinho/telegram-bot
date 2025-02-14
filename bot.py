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
from flask import Flask, jsonify
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

def get_calendar_service():
    creds_info = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

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
        
        if "lembrete" not in tarefa_data:
            tarefa_data["lembrete"] = 0  # Sem lembrete por padrão
            
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
        if "lembrete" not in evento_data:
            evento_data["lembrete"] = 0  # Sem lembrete por padrão
            
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

# Função para agendar lembretes
def agendar_lembrete(context: CallbackContext, tipo, id, descricao, data, lembrete_minutos):
    try:
        data_lembrete = datetime.fromisoformat(data) - timedelta(minutes=lembrete_minutos)
        if data_lembrete > datetime.now():
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                enviar_lembrete,
                trigger="date",
                run_date=data_lembrete,
                args=[context, tipo, id, descricao],
            )
            scheduler.start()
            logger.info(f"✅ Lembrete agendado para {data_lembrete}")
    except Exception as e:
        logger.error(f"❌ Erro ao agendar lembrete: {str(e)}")

# Função para enviar lembretes
async def enviar_lembrete(context: CallbackContext, tipo, id, descricao):
    try:
        usuarios = buscar_usuarios()
        for usuario in usuarios:
            chat_id = usuario["chat_id"]
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ Lembrete: {tipo} '{descricao}' está chegando!"
            )
        logger.info(f"✅ Lembrete enviado para {len(usuarios)} usuários.")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar lembrete: {str(e)}")

# Função para registrar métricas diárias
def registrar_metricas_diarias():
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        tarefas_concluidas = len([t for t in buscar_tarefas() if datetime.fromisoformat(t["data_vencimento"]) <= datetime.now()])
        lembretes_enviados = len([t for t in buscar_tarefas() if t.get("lembrete", 0) > 0])
        eventos_criados = len(buscar_eventos())
        usuarios_ativos = len(buscar_usuarios())

        relatorio_data = {
            "tarefas_concluidas": tarefas_concluidas,
            "lembretes_enviados": lembretes_enviados,
            "eventos_criados": eventos_criados,
            "usuarios_ativos": usuarios_ativos
        }

        db.collection("Relatorios").document(hoje).set(relatorio_data)
        logger.info(f"✅ Métricas diárias registradas para {hoje}")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar métricas diárias: {str(e)}")

# Função para agendar o registro diário de métricas
def agendar_registro_metricas():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        registrar_metricas_diarias,
        trigger="cron",
        hour=23,
        minute=59,
    )
    scheduler.start()
    logger.info("✅ Agendador de métricas diárias configurado.")

# API no Flask para acessar relatórios
app_web = Flask(__name__)

@app_web.route("/relatorios")
def listar_relatorios():
    try:
        relatorios = db.collection("Relatorios").stream()
        relatorios_data = {doc.id: doc.to_dict() for doc in relatorios}
        return jsonify(relatorios_data)
    except Exception as e:
        logger.error(f"❌ Erro ao buscar relatórios: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app_web.route("/relatorios/<data>")
def buscar_relatorio_por_data(data):
    try:
        relatorio = db.collection("Relatorios").document(data).get()
        if relatorio.exists:
            return jsonify(relatorio.to_dict())
        else:
            return jsonify({"erro": "Relatório não encontrado"}), 404
    except Exception as e:
        logger.error(f"❌ Erro ao buscar relatório: {str(e)}")
        return jsonify({"erro": str(e)}), 500

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

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
    /listar_prioridade - Lista tarefas ordenadas por prioridade
    /limpar - Remove todas as tarefas
    /agenda <título> <data-hora (YYYY-MM-DDTHH:MM:SS)> - Agenda um evento
    /eventos - Lista todos os eventos agendados
    /relatorio_diario - Gera um relatório diário
    /relatorio_semanal - Gera um relatório semanal
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

# Comandos adicionais
async def add_task(update: Update, context: CallbackContext) -> None:
    args = context.args
    full_text = ' '.join(args)
    
    prioridade_match = re.search(r'-prioridade (\w+)', full_text)
    data_match = re.search(r'-data (.+?)(?= -|$)', full_text)
    lembrete_match = re.search(r'-lembrete (\d+)', full_text)
    
    prioridade = prioridade_match.group(1).lower() if prioridade_match else "baixa"
    data_vencimento = data_match.group(1) if data_match else None
    lembrete = int(lembrete_match.group(1)) if lembrete_match else 0
    
    if data_vencimento:
        data_obj = dateparser.parse(data_vencimento, languages=['pt'])
        if not data_obj:
            await update.message.reply_text("❌ Data inválida! Use o formato: dd/mm/aaaa ou 'amanhã'")
            return
        data_iso = data_obj.isoformat()
    else:
        data_iso = (datetime.now() + timedelta(days=3)).isoformat()

    descricao = re.sub(r'(-prioridade \w+|-data .+?|-lembrete \d+)', '', full_text).strip()

    if not descricao:
        await update.message.reply_text("⚠️ Formato correto:\n/tarefa Comprar leite -prioridade alta -data amanhã -lembrete 30")
        return

    tarefa_data = {
        "descricao": descricao,
        "prioridade": prioridade,
        "data_criacao": datetime.now().isoformat(),
        "data_vencimento": data_iso,
        "lembrete": lembrete
    }
    
    if salvar_tarefa(tarefa_data):
        await update.message.reply_text(f"✅ Tarefa adicionada:\n{descricao}\n📅 Vencimento: {data_obj.strftime('%d/%m/%Y')}\n⏰ Lembrete: {lembrete} minutos antes")
        if lembrete > 0:
            agendar_lembrete(context, "Tarefa", tarefa_data["id"], descricao, data_iso, lembrete)
    else:
        await update.message.reply_text("❌ Erro ao adicionar tarefa.")

async def list_tasks(update: Update, context: CallbackContext) -> None:
    tarefas = buscar_tarefas()
    if tarefas:
        task_list = "\n".join([f"- {tarefa['descricao']}" for tarefa in tarefas])
        await update.message.reply_text(f"📌 Suas tarefas:\n{task_list}")
        send_whatsapp_message(f"📌 Suas tarefas:\n{task_list}")
    else:
        await update.message.reply_text("📭 Nenhuma tarefa adicionada.")
        send_whatsapp_message("📭 Nenhuma tarefa adicionada.")

async def list_tasks_by_priority(update: Update, context: CallbackContext) -> None:
    tarefas = buscar_tarefas()
    if tarefas:
        prioridade_ordem = {"alta": 1, "média": 2, "baixa": 3}
        tarefas_ordenadas = sorted(tarefas, key=lambda x: prioridade_ordem.get(x.get("prioridade", "baixa"), 3))
        task_list = "\n".join([f"- {tarefa['descricao']} (Prioridade: {tarefa.get('prioridade', 'baixa')})" for tarefa in tarefas_ordenadas])
        await update.message.reply_text(f"📌 Suas tarefas ordenadas por prioridade:\n{task_list}")
        send_whatsapp_message(f"📌 Suas tarefas ordenadas por prioridade:\n{task_list}")
    else:
        await update.message.reply_text("📭 Nenhuma tarefa adicionada.")
        send_whatsapp_message("📭 Nenhuma tarefa adicionada.")

async def clear_tasks(update: Update, context: CallbackContext) -> None:
    try:
        tarefas_ref = db.collection("Tarefas").stream()
        for tarefa in tarefas_ref:
            tarefa.reference.delete()
        await update.message.reply_text("🗑️ Todas as tarefas foram removidas.")
        send_whatsapp_message("🗑️ Todas as tarefas foram removidas.")
    except Exception as e:
        logger.error(f"❌ Erro ao limpar tarefas: {str(e)}")
        await update.message.reply_text("❌ Erro ao limpar tarefas.")
        send_whatsapp_message("❌ Erro ao limpar tarefas.")

async def list_events(update: Update, context: CallbackContext) -> None:
    eventos = buscar_eventos()
    if eventos:
        eventos_list = "\n".join([f"🔹 {evento['titulo']} - {evento['data']} às {evento['hora']}\n🔗 {evento['link']}" for evento in eventos])
        await update.message.reply_text(f"📅 Eventos agendados:\n{eventos_list}")
        send_whatsapp_message(f"📅 Eventos agendados:\n{eventos_list}")
    else:
        await update.message.reply_text("📭 Nenhum evento agendado.")
        send_whatsapp_message("📭 Nenhum evento agendado.")

async def add_agenda(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Use: /agenda <título> <data-hora (YYYY-MM-DDTHH:MM:SS)> -lembrete <minutos>")
        send_whatsapp_message("⚠️ Use: /agenda <título> <data-hora (YYYY-MM-DDTHH:MM:SS)> -lembrete <minutos>")
        return
    titulo = context.args[0]
    data_hora = context.args[1]
    lembrete_match = re.search(r'-lembrete (\d+)', ' '.join(context.args))
    lembrete = int(lembrete_match.group(1)) if lembrete_match else 0

    start_time = f"{data_hora}-03:00"
    end_time = f"{data_hora}-03:00"
    event_link = add_event(titulo, start_time, end_time)
    if event_link:
        evento_data = {
            "titulo": titulo,
            "data": data_hora.split("T")[0],
            "hora": data_hora.split("T")[1],
            "link": event_link,
            "notificado": False,
            "lembrete": lembrete
        }
        salvar_evento(evento_data)
        await update.message.reply_text(f"✅ Evento '{titulo}' adicionado: {event_link}\n⏰ Lembrete: {lembrete} minutos antes")
        if lembrete > 0:
            agendar_lembrete(context, "Evento", evento_data["id"], titulo, start_time, lembrete)
    else:
        await update.message.reply_text("❌ Erro ao adicionar evento!")
        send_whatsapp_message("❌ Erro ao adicionar evento!")

def add_event(summary, start_time, end_time):
    try:
        service = get_calendar_service()
        calendar_id = "andersonpagostinho@gmail.com"  # Substitua pelo seu calendar_id
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'},
        }
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        event_link = created_event.get('htmlLink')
        logger.info(f"✅ Evento Criado: {event_link}")
        return event_link
    except Exception as e:
        logger.error(f"❌ Erro ao criar evento no Google Calendar: {str(e)}")
        return None

# Função principal
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tarefa", add_task))
    app.add_handler(CommandHandler("listar", list_tasks))
    app.add_handler(CommandHandler("listar_prioridade", list_tasks_by_priority))
    app.add_handler(CommandHandler("limpar", clear_tasks))
    app.add_handler(CommandHandler("agenda", add_agenda))
    app.add_handler(CommandHandler("eventos", list_events))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Iniciar Flask em uma thread separada
    threading.Thread(target=run_flask, daemon=True).start()

    # Agendar registro diário de métricas
    agendar_registro_metricas()

    # Iniciar bot
    logger.info("🚀 Bot rodando com polling...")
    app.run_polling()

if __name__ == "__main__":
    main()