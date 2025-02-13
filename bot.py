import os
import json
import threading
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from twilio.rest import Client
from flask import Flask
import speech_recognition as sr  # Biblioteca para transcrição de áudio
import subprocess  # Para usar FFmpeg
import dateparser  # Biblioteca para interpretar datas e horas

# Configuração de logs
def log(message):
    print(message)

# Configuração do Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
USER_WHATSAPP_NUMBER = "whatsapp:+5519990068427"  # Substitua pelo seu número
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Configuração do Telegram Bot
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    log("❌ ERRO: A variável de ambiente TOKEN do Telegram não foi encontrada!")
    raise ValueError("⚠️ ERRO: A variável de ambiente TOKEN do Telegram não foi encontrada!")

# Configuração do Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not credentials_json:
    log("❌ ERRO: A variável de ambiente GOOGLE_CREDENTIALS_JSON não foi encontrada!")
    raise ValueError("⚠️ ERRO: GOOGLE_CREDENTIALS_JSON não foi encontrada!")

def get_calendar_service():
    creds_info = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

# Inicializar Firebase diretamente da variável de ambiente
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_credentials_json:
    raise ValueError("❌ ERRO: A variável de ambiente FIREBASE_CREDENTIALS não foi encontrada!")

cred_info = json.loads(firebase_credentials_json)
cred = credentials.Certificate(cred_info)
firebase_admin.initialize_app(cred)
db = firestore.client()
print("✅ Firebase inicializado com sucesso!")

# Função para salvar eventos no Firebase
def salvar_evento(evento_data):
    try:
        evento_ref = db.collection("Eventos").document()
        evento_ref.set(evento_data)
        log(f"✅ Evento salvo no Firebase: {evento_data['titulo']}")
    except Exception as e:
        log(f"❌ Erro ao salvar evento no Firebase: {str(e)}")

# Função para buscar eventos no Firebase
def buscar_eventos():
    try:
        eventos_ref = db.collection("Eventos").stream()
        eventos = [evento.to_dict() for evento in eventos_ref]
        log("✅ Eventos buscados com sucesso!")
        return eventos
    except Exception as e:
        log(f"❌ Erro ao buscar eventos no Firebase: {str(e)}")
        return []

# Função para salvar tarefas no Firebase
def salvar_tarefa(tarefa_data):
    try:
        tarefa_ref = db.collection("Tarefas").document()
        tarefa_ref.set(tarefa_data)
        log(f"✅ Tarefa salva no Firebase: {tarefa_data['descricao']}")
    except Exception as e:
        log(f"❌ Erro ao salvar tarefa no Firebase: {str(e)}")

# Função para buscar tarefas no Firebase
def buscar_tarefas():
    try:
        tarefas_ref = db.collection("Tarefas").stream()
        tarefas = [tarefa.to_dict() for tarefa in tarefas_ref]
        log("✅ Tarefas buscadas com sucesso!")
        return tarefas
    except Exception as e:
        log(f"❌ Erro ao buscar tarefas no Firebase: {str(e)}")
        return []

# Função para salvar notificações no Firebase
def salvar_notificacao(mensagem):
    try:
        notificacao_data = {
            "mensagem": mensagem,
            "data_envio": datetime.now().isoformat()
        }
        notificacao_ref = db.collection("notificacoes").document()
        notificacao_ref.set(notificacao_data)
        log(f"✅ Notificação salva no Firebase: {mensagem}")
    except Exception as e:
        log(f"❌ Erro ao salvar notificação no Firebase: {str(e)}")

# Função para enviar mensagens via WhatsApp
def send_whatsapp_message(message: str):
    try:
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=USER_WHATSAPP_NUMBER
        )
        log(f"✅ Mensagem enviada para {USER_WHATSAPP_NUMBER}: {message}")
        salvar_notificacao(message)  # Salva a notificação no Firebase
    except Exception as e:
        log(f"❌ Erro ao enviar mensagem pelo WhatsApp: {str(e)}")

# Função para converter OGG → WAV usando FFmpeg
def converter_ogg_para_wav(ogg_path, wav_path):
    try:
        comando = [
            "ffmpeg", "-i", ogg_path,  # Arquivo de entrada (OGG)
            "-acodec", "pcm_s16le",    # Codec PCM 16-bit
            "-ar", "16000",            # Taxa de amostragem de 16 kHz
            "-ac", "1",                # Mono
            wav_path                   # Arquivo de saída (WAV)
        ]
        subprocess.run(comando, check=True)
        log(f"✅ Áudio convertido: {wav_path}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Erro ao converter áudio: {e}")
        return False

# Função para transcrever áudio
def transcrever_audio(wav_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
        try:
            texto = recognizer.recognize_google(audio, language="pt-BR")
            log(f"✅ Áudio transcrito: {texto}")
            return texto
        except sr.UnknownValueError:
            log("❌ Não foi possível transcrever o áudio.")
            return None
        except sr.RequestError as e:
            log(f"❌ Erro na requisição ao Google Speech-to-Text: {e}")
            return None

# Função para interpretar datas e horas
def interpretar_data_hora(texto):
    try:
        # Extrai a data e hora usando dateparser
        data_hora = dateparser.parse(texto, languages=["pt"])
        if not data_hora:
            return None

        # Formata a data e hora no formato ISO
        return data_hora.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception as e:
        log(f"❌ Erro ao interpretar data e hora: {e}")
        return None

# Função para processar comandos de voz
async def processar_comando_voz(update: Update, texto: str):
    texto = texto.lower()

    if "agendar" in texto:
        # Extrai o título e a data/hora do comando
        partes = texto.split(" às ")
        if len(partes) < 2:
            await update.message.reply_text("⚠️ Formato inválido. Use: Agendar [título] [data/hora]")
            return

        titulo = partes[0].replace("agendar", "").strip()
        data_hora_texto = partes[1].strip()

        # Interpreta a data e hora
        data_hora = interpretar_data_hora(data_hora_texto)
        if not data_hora:
            await update.message.reply_text("❌ Não entendi a data/hora. Pode reformular?")
            return

        # Agenda o evento
        start_time = f"{data_hora}-03:00"
        end_time = f"{data_hora}-03:00"
        event_link = add_event(titulo, start_time, end_time)
        if event_link:
            evento_data = {
                "titulo": titulo,
                "data": data_hora.split("T")[0],
                "hora": data_hora.split("T")[1],
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

# Handler para mensagens de voz
async def handle_voice(update: Update, context: CallbackContext) -> None:
    # Baixa o arquivo de áudio (OGG)
    voice_file = await update.message.voice.get_file()
    ogg_path = "temp_audio.ogg"
    await voice_file.download_to_drive(ogg_path)

    # Converte OGG → WAV
    wav_path = "temp_audio.wav"
    if not converter_ogg_para_wav(ogg_path, wav_path):
        await update.message.reply_text("❌ Erro ao processar o áudio. Tente novamente.")
        return

    # Transcreve o áudio
    texto = transcrever_audio(wav_path)
    if not texto:
        await update.message.reply_text("❌ Não entendi o áudio. Pode repetir?")
        return

    # Responde no Telegram com o texto transcrito
    await update.message.reply_text(f"🎤 Você disse: {texto}")

    # Processa o comando de voz
    await processar_comando_voz(update, texto)

    # Remove os arquivos temporários
    os.remove(ogg_path)
    os.remove(wav_path)
    log("✅ Arquivos temporários removidos.")

# Comando /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("👋 Olá! Sou seu assistente de produtividade. Use /help para ver os comandos disponíveis.")
    send_whatsapp_message("👋 Olá! Sou seu assistente de produtividade. Use /help para ver os comandos disponíveis.")

# Comando /help
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
    """
    await update.message.reply_text(help_text)
    send_whatsapp_message(help_text)

# Comando /tarefa atualizado para suportar prioridade
async def add_task(update: Update, context: CallbackContext) -> None:
    args = " ".join(context.args).split(" -prioridade ")
    task = args[0].strip()
    prioridade = args[1].strip().lower() if len(args) > 1 else "baixa"

    if task:
        tarefa_data = {
            "descricao": task,
            "prioridade": prioridade,
            "data_criacao": datetime.now().isoformat()
        }
        salvar_tarefa(tarefa_data)
        await update.message.reply_text(f"✅ Tarefa adicionada: {task} (Prioridade: {prioridade})")
        send_whatsapp_message(f"✅ Tarefa adicionada: {task} (Prioridade: {prioridade})")
    else:
        await update.message.reply_text("⚠️ Você precisa fornecer uma descrição. Exemplo: /tarefa Comprar pão -prioridade alta")
        send_whatsapp_message("⚠️ Você precisa fornecer uma descrição. Exemplo: /tarefa Comprar pão -prioridade alta")

# Comando /listar
async def list_tasks(update: Update, context: CallbackContext) -> None:
    tarefas = buscar_tarefas()
    if tarefas:
        task_list = "\n".join([f"- {tarefa['descricao']}" for tarefa in tarefas])
        await update.message.reply_text(f"📌 Suas tarefas:\n{task_list}")
        send_whatsapp_message(f"📌 Suas tarefas:\n{task_list}")
    else:
        await update.message.reply_text("📭 Nenhuma tarefa adicionada.")
        send_whatsapp_message("📭 Nenhuma tarefa adicionada.")

# Comando /listar_prioridade
async def list_tasks_by_priority(update: Update, context: CallbackContext) -> None:
    tarefas = buscar_tarefas()
    if tarefas:
        # Ordenar tarefas por prioridade (alta > média > baixa)
        prioridade_ordem = {"alta": 1, "média": 2, "baixa": 3}
        tarefas_ordenadas = sorted(tarefas, key=lambda x: prioridade_ordem.get(x.get("prioridade", "baixa"), 3))

        task_list = "\n".join([f"- {tarefa['descricao']} (Prioridade: {tarefa.get('prioridade', 'baixa')})" for tarefa in tarefas_ordenadas])
        await update.message.reply_text(f"📌 Suas tarefas ordenadas por prioridade:\n{task_list}")
        send_whatsapp_message(f"📌 Suas tarefas ordenadas por prioridade:\n{task_list}")
    else:
        await update.message.reply_text("📭 Nenhuma tarefa adicionada.")
        send_whatsapp_message("📭 Nenhuma tarefa adicionada.")

# Comando /limpar
async def clear_tasks(update: Update, context: CallbackContext) -> None:
    try:
        tarefas_ref = db.collection("Tarefas").stream()
        for tarefa in tarefas_ref:
            tarefa.reference.delete()
        await update.message.reply_text("🗑️ Todas as tarefas foram removidas.")
        send_whatsapp_message("🗑️ Todas as tarefas foram removidas.")
    except Exception as e:
        log(f"❌ Erro ao limpar tarefas: {str(e)}")
        await update.message.reply_text("❌ Erro ao limpar tarefas.")
        send_whatsapp_message("❌ Erro ao limpar tarefas.")

# Comando /agenda
async def add_agenda(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Use: /agenda <título> <data-hora (YYYY-MM-DDTHH:MM:SS)>")
        send_whatsapp_message("⚠️ Use: /agenda <título> <data-hora (YYYY-MM-DDTHH:MM:SS)>")
        return
    titulo = context.args[0]
    data_hora = context.args[1]

    # Formatar data e hora para o Google Calendar
    start_time = f"{data_hora}-03:00"  # Ajuste o fuso horário conforme necessário
    end_time = f"{data_hora}-03:00"

    # Adicionar evento ao Google Calendar
    event_link = add_event(titulo, start_time, end_time)
    if event_link:
        evento_data = {
            "titulo": titulo,
            "data": data_hora.split("T")[0],
            "hora": data_hora.split("T")[1],
            "link": event_link,
            "notificado": False
        }
        salvar_evento(evento_data)
        await update.message.reply_text(f"✅ Evento '{titulo}' adicionado: {event_link}")
        send_whatsapp_message(f"✅ Evento '{titulo}' adicionado: {event_link}")
    else:
        await update.message.reply_text("❌ Erro ao adicionar evento!")
        send_whatsapp_message("❌ Erro ao adicionar evento!")

# Comando /eventos
async def list_events(update: Update, context: CallbackContext) -> None:
    eventos = buscar_eventos()
    if eventos:
        eventos_list = "\n".join([f"🔹 {evento['titulo']} - {evento['data']} às {evento['hora']}\n🔗 {evento['link']}" for evento in eventos])
        await update.message.reply_text(f"📅 Eventos agendados:\n{eventos_list}")
        send_whatsapp_message(f"📅 Eventos agendados:\n{eventos_list}")
    else:
        await update.message.reply_text("📭 Nenhum evento agendado.")
        send_whatsapp_message("📭 Nenhum evento agendado.")

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
        log(f"✅ Evento Criado: {event_link}")
        return event_link
    except Exception as e:
        log(f"❌ Erro ao criar evento no Google Calendar: {str(e)}")
        return None

# Handler para encaminhar todas as mensagens para o WhatsApp
async def forward_to_whatsapp(update: Update, context: CallbackContext) -> None:
    message = update.message.text
    send_whatsapp_message(f"📨 Mensagem recebida no Telegram: {message}")

# Configuração do Flask
app_web = Flask(__name__)
@app_web.route("/")
def home():
    return "Bot rodando!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

def main():
    app_telegram = Application.builder().token(TOKEN).build()

    # Registro de handlers
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("help", help_command))
    app_telegram.add_handler(CommandHandler("tarefa", add_task))
    app_telegram.add_handler(CommandHandler("listar", list_tasks))
    app_telegram.add_handler(CommandHandler("listar_prioridade", list_tasks_by_priority))
    app_telegram.add_handler(CommandHandler("limpar", clear_tasks))
    app_telegram.add_handler(CommandHandler("agenda", add_agenda))
    app_telegram.add_handler(CommandHandler("eventos", list_events))

    # Handler para mensagens de voz
    app_telegram.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Handler para encaminhar todas as mensagens para o WhatsApp
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_whatsapp))

    # Iniciar o Flask em uma thread separada
    threading.Thread(target=run_flask, daemon=True).start()

    # Iniciar o bot do Telegram
    log("🚀 Bot rodando com polling...")
    app_telegram.run_polling()

if __name__ == "__main__":
    main()