import os
import json
import re
import logging
import base64
from datetime import datetime, timedelta, timezone
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
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Configuração de logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
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
    logger.error("❌ ERRO: TOKEN do Telegram não encontrado!")
    raise ValueError("TOKEN do Telegram não configurado!")

# Configuração do Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not credentials_json:
    logger.error("❌ ERRO: GOOGLE_CREDENTIALS_JSON não encontrado!")
    raise ValueError("GOOGLE_CREDENTIALS_JSON não configurado!")

def get_calendar_service():
    creds_info = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

# Inicializar Firebase
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_credentials_json:
    raise ValueError("❌ ERRO: FIREBASE_CREDENTIALS não encontrado!")

cred_info = json.loads(firebase_credentials_json)
cred = credentials.Certificate(cred_info)
firebase_admin.initialize_app(cred)
db = firestore.client()
logger.info("✅ Firebase inicializado!")

# Configuração de Email
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER")
EMAIL_IMAP_PORT = os.getenv("EMAIL_IMAP_PORT")

# Configurações de Prioridade
PALAVRAS_CHAVE = {
    "alta": ["urgente", "prazo", "vencimento", "importante", "confirmação"],
    "media": ["reunião", "atualização", "relatório", "cliente"],
    "baixa": ["newsletter", "promoção", "marketing", "atualizações"]
}

REMETENTES_PRIORITARIOS = json.loads(os.getenv("REMETENTES_PRIORITARIOS", "[]"))
HORARIO_COMERCIAL = (9, 18)

def obter_config_prioridade_usuario(chat_id):
    try:
        doc_ref = db.collection("UserPrioritySettings").document(str(chat_id))
        doc = doc_ref.get()
        return doc.to_dict() or {"remetentes": {}, "palavras": {}}
    except Exception as e:
        logger.error(f"❌ Erro ao obter configurações: {str(e)}")
        return {"remetentes": {}, "palavras": {}}

async def priorizar_email(update: Update, context: CallbackContext):
    """
    Comando: /priorizar_email <add/remove/list> [tipo] [valor] [prioridade]
    """
    try:
        chat_id = str(update.effective_chat.id)
        args = context.args
        
        if not args:
            await update.message.reply_text("⚠️ Formato incorreto!\nExemplos:\n"
                                           "/priorizar_email add remetente \"suporte@empresa.com\" alta\n"
                                           "/priorizar_email list")
            return

        action = args[0].lower()
        config = obter_config_prioridade_usuario(chat_id)

        if action == "add" and len(args) >= 4:
            tipo = args[1].lower()
            valor = ' '.join(args[2:-1]).strip('"')
            prioridade = args[-1].lower()

            if tipo not in ["remetente", "palavra"]:
                await update.message.reply_text("❌ Tipo inválido! Use 'remetente' ou 'palavra'")
                return

            chave = "remetentes" if tipo == "remetente" else "palavras"
            config[chave][valor.lower()] = prioridade
            
            db.collection("UserPrioritySettings").document(chat_id).set(config)
            await update.message.reply_text(f"✅ {tipo.capitalize()} '{valor}' definido como prioridade {prioridade}")

        elif action == "remove" and len(args) >= 3:
            tipo = args[1].lower()
            valor = ' '.join(args[2:]).strip('"')
            
            chave = "remetentes" if tipo == "remetente" else "palavras"
            if valor.lower() in config[chave]:
                del config[chave][valor.lower()]
                db.collection("UserPrioritySettings").document(chat_id).set(config)
                await update.message.reply_text(f"✅ Regra removida: {tipo} '{valor}'")
            else:
                await update.message.reply_text("❌ Regra não encontrada")

        elif action == "list":
            resposta = "⚙️ Suas Regras de Priorização:\n"
            for tipo in ["remetentes", "palavras"]:
                resposta += f"\n🔧 {tipo.capitalize()}:\n"
                for item, prio in config.get(tipo, {}).items():
                    resposta += f"   - {item}: {prio}\n"
            await update.message.reply_text(resposta[:4000])

        else:
            await update.message.reply_text("⚠️ Comando inválido! Use /priorizar_email help para ajuda")

    except Exception as e:
        logger.error(f"❌ Erro no priorizar_email: {str(e)}")
        await update.message.reply_text("❌ Erro ao processar comando")

def classificar_prioridade(email_data):
    """Classificação híbrida: manual + automática"""
    try:
        chat_id = str(email_data.get('chat_id', ''))
        user_config = obter_config_prioridade_usuario(chat_id)
        
        remetente = email_data['de'].lower()
        assunto = email_data['assunto'].lower()
        corpo = email_data['corpo'].lower()

        for r, p in user_config['remetentes'].items():
            if r in remetente:
                return p

        for palavra, p in user_config['palavras'].items():
            if palavra in assunto or palavra in corpo:
                return p

        for prioridade, palavras in PALAVRAS_CHAVE.items():
            if any(p in assunto or p in corpo for p in palavras):
                return prioridade

        if any(rem in remetente for rem in REMETENTES_PRIORITARIOS):
            return "alta"

        if not (HORARIO_COMERCIAL[0] <= datetime.now(timezone.utc).hour < HORARIO_COMERCIAL[1]):
            return "media"

        return "baixa"

    except Exception as e:
        logger.error(f"❌ Erro na classificação: {str(e)}")
        return "baixa"

def salvar_email_classificado(email_data):
    try:
        email_data['prioridade'] = classificar_prioridade(email_data)
        email_data['data_recebimento'] = datetime.now(timezone.utc).isoformat()
        
        doc_ref = db.collection("Emails").document()
        doc_ref.set(email_data)
        logger.info(f"📩 E-mail salvo: {email_data['assunto']} - Prioridade: {email_data['prioridade']}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"❌ Erro ao salvar e-mail: {str(e)}")
        return None

def ler_emails(num_emails=5):
    try:
        if not all([EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT, EMAIL_USER, EMAIL_PASSWORD]):
            logger.error("❌ Variáveis de ambiente IMAP não configuradas")
            return []

        mail = imaplib.IMAP4_SSL(EMAIL_IMAP_SERVER, int(EMAIL_IMAP_PORT))
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select("inbox")

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
            salvar_email_classificado(email_data)
            emails.append(email_data)

        mail.close()
        mail.logout()
        return emails

    except Exception as e:
        logger.error(f"❌ Erro ao ler e-mails: {str(e)}")
        return []

async def listar_emails_prioritarios(update: Update, context: CallbackContext):
    try:
        emails = db.collection("Emails").where("prioridade", "==", "alta").stream()
        
        resposta = "📨 E-mails prioritários:\n\n"
        for idx, email in enumerate(emails, 1):
            data = email.to_dict()
            resposta += (
                f"{idx}. {data['assunto']}\n"
                f"📩 De: {data['de']}\n"
                f"⏰ Recebido em: {data['data_recebimento'][:16]}\n\n"
            )

        await update.message.reply_text(resposta[:4000])
    except Exception as e:
        logger.error(f"❌ Erro no comando listar_emails_prioritarios: {str(e)}")
        await update.message.reply_text("❌ Erro ao listar e-mails prioritários.")

async def ler_emails_command(update: Update, context: CallbackContext):
    try:
        num_emails = int(context.args[0]) if context.args else 5
        if num_emails > 10:
            num_emails = 10
            
        emails = ler_emails(num_emails)
        
        if not emails:
            await update.message.reply_text("📭 Nenhum e-mail novo encontrado.")
            return

        response = "📬 Últimos e-mails:\n\n"
        for idx, email_msg in enumerate(emails, 1):
            response += (
                f"📌 E-mail {idx}:\n"
                f"De: {email_msg['de']}\n"
                f"Assunto: {email_msg['assunto']}\n"
                f"Conteúdo: {email_msg['corpo']}\n\n"
            )

        await update.message.reply_text(response[:4000])
        send_whatsapp_message(response[:1600])

    except Exception as e:
        logger.error(f"❌ Erro no comando ler_emails: {str(e)}")
        await update.message.reply_text("❌ Erro ao ler e-mails.")

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = """
    🛠 Comandos disponíveis:
    /start - Inicia o bot
    /help - Mostra esta ajuda
    /tarefa [descrição] - Adiciona uma tarefa
    /editar_tarefa <ID> <prioridade> - Altera prioridade
    /listar - Lista todas as tarefas
    /listar_prioridade - Lista tarefas por prioridade
    /limpar - Remove todas as tarefas
    /agenda <título> <data-hora> - Agenda evento
    /eventos - Lista eventos agendados
    /relatorio_diario [-pdf] - Relatório diário (opcional PDF)
    /relatorio_semanal - Relatório semanal
    /enviar_email <destinatário> <assunto> <mensagem> [-anexo URL]
    /ler_emails [número] - Lê últimos e-mails
    /emails_prioritarios - Lista e-mails prioritários
    /priorizar_email - Configura priorização
    /confirmar_reuniao <ID_Evento> - Confirma reunião
    /enviar_convites <ID_Evento> - Envia convites
    """
    await update.message.reply_text(help_text)

def confirmar_reuniao(evento_id: str):
    try:
        evento_ref = db.collection("Eventos").document(evento_id)
        evento_ref.update({"status": "confirmado"})
        
        evento = evento_ref.get().to_dict()
        mensagem = (
            f"✅ Reunião Confirmada!\n"
            f"📌 Título: {evento['titulo']}\n"
            f"📅 Data: {evento['data']}\n"
            f"🕒 Hora: {evento['hora']}\n"
            f"🔗 Link: {evento.get('link', 'N/A')}"
        )
        
        send_whatsapp_message(mensagem)
        
        usuarios = buscar_usuarios()
        for usuario in usuarios:
            context.bot.send_message(
                chat_id=usuario["chat_id"],
                text=mensagem
            )
        
        logger.info(f"✅ Reunião {evento_id} confirmada!")
        return True
    
    except Exception as e:
        logger.error(f"❌ Erro ao confirmar reunião: {str(e)}")
        return False

def verificar_confirmacoes_pendentes():
    try:
        eventos = db.collection("Eventos").where("status", "==", "pendente").stream()
        agora = datetime.now(timezone.utc)
        
        for evento in eventos:
            dados = evento.to_dict()
            data_evento = datetime.fromisoformat(f"{dados['data']}T{dados['hora']}")
            
            if (data_evento - agora) < timedelta(hours=24):
                confirmar_reuniao(evento.id)
                logger.info(f"⚠️ Reunião {evento.id} confirmada automaticamente!")
    
    except Exception as e:
        logger.error(f"❌ Erro na verificação automática: {str(e)}")

async def comando_confirmar_reuniao(update: Update, context: CallbackContext):
    try:
        evento_id = context.args[0]
        if confirmar_reuniao(evento_id):
            await update.message.reply_text("✅ Reunião confirmada e notificada!")
        else:
            await update.message.reply_text("❌ Erro ao confirmar reunião.")
    except IndexError:
        await update.message.reply_text("⚠️ Formato correto: /confirmar_reuniao <ID_Evento>")

def salvar_tarefa(tarefa_data):
    try:
        if "data_vencimento" not in tarefa_data:
            tarefa_data["data_vencimento"] = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        
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
            "data_registro": datetime.now(timezone.utc).isoformat()
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

def send_whatsapp_message(message: str):
    try:
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=USER_WHATSAPP_NUMBER
        )
        logger.info(f"✅ Mensagem enviada para {USER_WHATSAPP_NUMBER}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem pelo WhatsApp: {str(e)}")

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

def agendar_lembrete(context: CallbackContext, tipo, id, descricao, data, lembretes):
    try:
        if isinstance(lembretes, int):
            lembretes = [lembretes]
            
        for minutos in lembretes:
            data_lembrete = datetime.fromisoformat(data).replace(tzinfo=timezone.utc) - timedelta(minutes=minutos)
            agora = datetime.now(timezone.utc)

            if data_lembrete > agora:
                scheduler.add_job(
                    enviar_lembrete,
                    trigger="date",
                    run_date=data_lembrete,
                    args=[context, tipo, id, descricao],
                )
                logger.info(f"✅ Lembrete agendado para {data_lembrete}")
    except Exception as e:
        logger.error(f"❌ Erro ao agendar lembrete: {str(e)}")

async def enviar_lembrete(context: CallbackContext, tipo, id, descricao):
    try:
        usuarios = buscar_usuarios()
        for usuario in usuarios:
            await context.bot.send_message(
                chat_id=usuario["chat_id"],
                text=f"⏰ Lembrete: {tipo} '{descricao}' está chegando!"
            )
        logger.info(f"✅ Lembrete enviado para {len(usuarios)} usuários.")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar lembrete: {str(e)}")

def registrar_metricas_diarias():
    try:
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tarefas_concluidas = len([t for t in buscar_tarefas() if datetime.fromisoformat(t["data_vencimento"]) <= datetime.now(timezone.utc)])
        lembretes_enviados = len([t for t in buscar_tarefas() if t.get("lembrete")])
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

scheduler = BackgroundScheduler()

def agendar_registro_metricas():
    try:
        if not scheduler.running:
            scheduler.add_job(
                registrar_metricas_diarias,
                trigger="cron",
                hour=23,
                minute=59,
            )
            scheduler.start()
            logger.info("✅ Agendador de métricas iniciado!")
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar o agendador: {str(e)}")

scheduler.add_job(
    verificar_confirmacoes_pendentes,
    trigger="cron",
    hour=8,
    minute=0
)

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

def verificar_horarios_ocupados(start_time, end_time):
    try:
        service = get_calendar_service()
        calendar_id = "primary"
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except Exception as e:
        logger.error(f"❌ Erro ao verificar horários: {str(e)}")
        return []

def sugerir_horarios_livres(start_time, end_time, duracao_minutos=60):
    try:
        inicio_periodo = datetime.fromisoformat(start_time)
        fim_periodo = datetime.fromisoformat(end_time)

        eventos = verificar_horarios_ocupados(start_time, end_time)
        horarios_ocupados = [(datetime.fromisoformat(e['start']['dateTime']), datetime.fromisoformat(e['end']['dateTime'])) for e in eventos]

        horarios_livres = []
        tempo_atual = inicio_periodo
        
        while tempo_atual < fim_periodo:
            tempo_fim = tempo_atual + timedelta(minutes=duracao_minutos)
            conflito = False
            
            for inicio, fim in horarios_ocupados:
                if (tempo_atual < fim) and (tempo_fim > inicio):
                    conflito = True
                    tempo_atual = fim
                    break
                    
            if not conflito:
                horarios_livres.append((tempo_atual, tempo_fim))
                tempo_atual = tempo_fim
            else:
                tempo_atual += timedelta(minutes=15)

        return horarios_livres[:5]  # Retorna os 5 primeiros horários
    except Exception as e:
        logger.error(f"❌ Erro ao sugerir horários: {str(e)}")
        return []

async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    salvar_usuario(chat_id)
    await update.message.reply_text("👋 Olá! Vou te enviar lembretes de tarefas e eventos importantes.")

async def handle_voice(update: Update, context: CallbackContext) -> None:
    try:
        voice_file = await update.message.voice.get_file()
        ogg_path = "temp_audio.ogg"
        await voice_file.download_to_drive(ogg_path)

        wav_path = "temp_audio.wav"
        if not converter_ogg_para_wav(ogg_path, wav_path):
            await update.message.reply_text("❌ Erro ao processar o áudio.")
            return

        texto = transcrever_audio(wav_path)
        if not texto:
            await update.message.reply_text("❌ Não entendi o áudio.")
            return

        await processar_comando_voz(update, context, texto)

    except Exception as e:
        logger.error(f"❌ Erro ao processar áudio: {str(e)}")
        await update.message.reply_text("❌ Erro ao processar áudio.")
    finally:
        for path in [ogg_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)

async def processar_comando_voz(update: Update, context: CallbackContext, texto: str):
    texto = texto.lower()

    if "adicionar tarefa" in texto:
        partes = texto.split(" com prioridade ")
        descricao = partes[0].replace("adicionar tarefa", "").strip()
        prioridade = partes[1].strip() if len(partes) > 1 else "baixa"

        tarefa_data = {
            "descricao": descricao,
            "prioridade": prioridade,
            "data_criacao": datetime.now(timezone.utc).isoformat()
        }
        salvar_tarefa(tarefa_data)
        await update.message.reply_text(f"✅ Tarefa adicionada: {descricao}")

    elif "agendar" in texto:
        partes = texto.split(" às ")
        if len(partes) < 2:
            await update.message.reply_text("⚠️ Formato inválido.")
            return

        titulo = partes[0].replace("agendar", "").strip()
        data_hora = dateparser.parse(partes[1].strip(), languages=["pt"])
        
        if not data_hora:
            await update.message.reply_text("❌ Data/hora inválida.")
            return

        start_time = data_hora.isoformat()
        end_time = (data_hora + timedelta(hours=1)).isoformat()
        
        event_link = add_event(titulo, start_time, end_time)
        if event_link:
            await update.message.reply_text(f"✅ Evento '{titulo}' agendado!")
        else:
            await update.message.reply_text("❌ Erro ao agendar evento.")

    # [Outros comandos por voz...]

async def add_task(update: Update, context: CallbackContext) -> None:
    args = context.args
    full_text = ' '.join(args)
    
    prioridade_match = re.search(r'-prioridade (\w+)', full_text)
    data_match = re.search(r'-data (.+?)(?= -|$)', full_text)
    lembrete_match = re.findall(r'-lembrete (\d+)', full_text)
    
    prioridade = prioridade_match.group(1).lower() if prioridade_match else "baixa"
    data_vencimento = data_match.group(1) if data_match else None
    lembretes = [int(m) for m in lembrete_match] if lembrete_match else []
    
    data_obj = datetime.now(timezone.utc) + timedelta(days=3)
    
    if data_vencimento:
        data_obj = dateparser.parse(data_vencimento, languages=['pt'])
        if not data_obj:
            await update.message.reply_text("❌ Data inválida!")
            return
        data_iso = data_obj.isoformat()
    else:
        data_iso = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    descricao = re.sub(r'(-prioridade \w+|-data .+?|-lembrete \d+)', '', full_text).strip()

    if not descricao:
        await update.message.reply_text("⚠️ Formato incorreto!")
        return

    tarefa_data = {
        "descricao": descricao,
        "prioridade": prioridade,
        "data_criacao": datetime.now(timezone.utc).isoformat(),
        "data_vencimento": data_iso,
        "lembrete": lembretes
    }
    
    tarefa_id = salvar_tarefa(tarefa_data)
    if tarefa_id:
        msg = f"✅ Tarefa adicionada:\n{descricao}"
        if lembretes:
            msg += f"\n⏰ Lembretes: {', '.join(map(str, lembretes))} minutos antes"
        await update.message.reply_text(msg)
        
        if lembretes:
            agendar_lembrete(context, "Tarefa", tarefa_id, descricao, data_iso, lembretes)
    else:
        await update.message.reply_text("❌ Erro ao adicionar tarefa.")

async def editar_tarefa(update: Update, context: CallbackContext) -> None:
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("⚠️ Formato: /editar_tarefa <ID> <prioridade>")
            return

        task_id, nova_prioridade = args[0], args[1].lower()
        
        if nova_prioridade not in ["alta", "média", "baixa"]:
            await update.message.reply_text("❌ Prioridade inválida!")
            return

        task_ref = db.collection("Tarefas").document(task_id)
        if task_ref.get().exists:
            task_ref.update({"prioridade": nova_prioridade})
            await update.message.reply_text(f"✅ Prioridade atualizada para {nova_prioridade}!")
        else:
            await update.message.reply_text("❌ Tarefa não encontrada!")
    except Exception as e:
        logger.error(f"❌ Erro ao editar tarefa: {str(e)}")
        await update.message.reply_text("❌ Erro ao editar tarefa.")

async def list_tasks(update: Update, context: CallbackContext) -> None:
    tarefas = buscar_tarefas()
    if tarefas:
        response = "📋 Suas tarefas:\n\n" + "\n".join(
            [f"{idx+1}. {t['descricao']} ({t.get('prioridade', 'baixa'})" 
             for idx, t in enumerate(tarefas)]
        )
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("📭 Nenhuma tarefa encontrada.")

async def list_events(update: Update, context: CallbackContext) -> None:
    eventos = buscar_eventos()
    if eventos:
        response = "📅 Eventos agendados:\n\n" + "\n".join(
            [f"{idx+1}. {e['titulo']} - {e['data']} {e['hora']}" 
             for idx, e in enumerate(eventos)]
        )
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("📭 Nenhum evento agendado.")

async def add_agenda(update: Update, context: CallbackContext) -> None:
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("⚠️ Use: /agenda <título> <data-hora>")
            return

        titulo = args[0]
        data_hora = dateparser.parse(' '.join(args[1:]), languages=['pt'])
        
        if not data_hora:
            await update.message.reply_text("❌ Data/hora inválida!")
            return

        start_time = data_hora.isoformat()
        end_time = (data_hora + timedelta(hours=1)).isoformat()
        
        event_link = add_event(titulo, start_time, end_time)
        if event_link:
            await update.message.reply_text(f"✅ Evento '{titulo}' agendado!\n🔗 {event_link}")
        else:
            await update.message.reply_text("❌ Erro ao agendar evento.")
    except Exception as e:
        logger.error(f"❌ Erro ao agendar: {str(e)}")
        await update.message.reply_text("❌ Erro ao agendar evento.")

def add_event(summary, start_time, end_time, participantes=None):
    try:
        service = get_calendar_service()
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'},
            'conferenceData': {
                'createRequest': {'requestId': 'sample123', 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}
        }
        
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()
        
        evento_data = {
            "titulo": summary,
            "data": datetime.fromisoformat(start_time).strftime("%Y-%m-%d"),
            "hora": datetime.fromisoformat(start_time).strftime("%H:%M:%S"),
            "link": created_event.get('hangoutLink', created_event['htmlLink']),
            "participantes": participantes or []
        }
        db.collection("Eventos").add(evento_data)
        
        return evento_data['link']
    except Exception as e:
        logger.error(f"❌ Erro ao criar evento: {str(e)}")
        return None

async def relatorio_diario(update: Update, context: CallbackContext) -> None:
    try:
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        relatorio = db.collection("Relatorios").document(hoje).get()
        
        if not relatorio.exists:
            await update.message.reply_text(f"📭 Nenhum relatório para {hoje}")
            return

        data = relatorio.to_dict()
        if '-pdf' in context.args:
            filename = f"relatorio_{hoje}.pdf"
            if gerar_pdf(data, filename):
                with open(filename, 'rb') as f:
                    await update.message.reply_document(f)
                os.remove(filename)
            else:
                await update.message.reply_text("❌ Erro ao gerar PDF")
        else:
            texto = f"📊 Relatório Diário ({hoje})\n\n"
            texto += f"✅ Tarefas Concluídas: {data['tarefas_concluidas']}\n"
            texto += f"🔔 Lembretes Enviados: {data['lembretes_enviados']}\n"
            texto += f"📅 Eventos Criados: {data['eventos_criados']}\n"
            texto += f"👤 Usuários Ativos: {data['usuarios_ativos']}"
            await update.message.reply_text(texto)
    except Exception as e:
        logger.error(f"❌ Erro no relatório: {str(e)}")
        await update.message.reply_text("❌ Erro ao gerar relatório")

def gerar_pdf(data, filename):
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        y = 750
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "Relatório de Produtividade")
        y -= 40
        
        c.setFont("Helvetica", 12)
        for key, value in data.items():
            c.drawString(50, y, f"{key.replace('_', ' ').title()}: {value}")
            y -= 20
            if y < 50:
                c.showPage()
                y = 750
        c.save()
        return True
    except Exception as e:
        logger.error(f"❌ Erro no PDF: {str(e)}")
        return False

async def enviar_convites(update: Update, context: CallbackContext):
    try:
        evento_id = context.args[0]
        evento_ref = db.collection("Eventos").document(evento_id)
        evento = evento_ref.get().to_dict()
        
        if not evento:
            await update.message.reply_text("❌ Evento não encontrado!")
            return

        for participante in evento.get('participantes', []):
            enviar_email(
                participante,
                f"Convite para {evento['titulo']}",
                f"Participe do evento: {evento['titulo']}\nData: {evento['data']}\nHora: {evento['hora']}\nLink: {evento['link']}"
            )
        
        await update.message.reply_text("✅ Convites enviados!")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar convites: {str(e)}")
        await update.message.reply_text("❌ Erro ao enviar convites.")

def enviar_email(destinatario, assunto, mensagem, anexos=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(mensagem, 'plain'))

        if anexos:
            for anexo in anexos:
                with open(anexo, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(anexo)}"')
                    msg.attach(part)

        with smtplib.SMTP(EMAIL_HOST, int(EMAIL_PORT)) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao enviar e-mail: {str(e)}")
        return False

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tarefa", add_task))
    app.add_handler(CommandHandler("editar_tarefa", editar_tarefa))
    app.add_handler(CommandHandler("listar", list_tasks))
    app.add_handler(CommandHandler("listar_prioridade", list_tasks_by_priority))
    app.add_handler(CommandHandler("limpar", clear_tasks))
    app.add_handler(CommandHandler("agenda", add_agenda))
    app.add_handler(CommandHandler("eventos", list_events))
    app.add_handler(CommandHandler("relatorio_diario", relatorio_diario))
    app.add_handler(CommandHandler("relatorio_semanal", relatorio_semanal))
    app.add_handler(CommandHandler("enviar_email", enviar_email_command))
    app.add_handler(CommandHandler("ler_emails", ler_emails_command))
    app.add_handler(CommandHandler("emails_prioritarios", listar_emails_prioritarios))
    app.add_handler(CommandHandler("priorizar_email", priorizar_email))
    app.add_handler(CommandHandler("confirmar_reuniao", comando_confirmar_reuniao))
    app.add_handler(CommandHandler("enviar_convites", enviar_convites))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    threading.Thread(target=run_flask, daemon=True).start()
    agendar_registro_metricas()

    logger.info("🚀 Bot iniciado!")
    app.run_polling()

if __name__ == "__main__":
    main()