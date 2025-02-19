import os
import json
import re
import logging
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

# ========== FUNÇÕES DE PRIORIZAÇÃO MANUAL ==========
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

        # Verificar regras manuais primeiro
        for r, p in user_config['remetentes'].items():
            if r in remetente:
                return p

        for palavra, p in user_config['palavras'].items():
            if palavra in assunto or palavra in corpo:
                return p

        # Regras automáticas
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

# ========== FUNÇÕES DE GERENCIAMENTO DE EMAIL ==========
def salvar_email_classificado(email_data):
    """Salva e-mail no Firebase com classificação de prioridade"""
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
        mail.select("INBOX")

        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
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
                    if part.get_content_type() == "text/plain":
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

# ========== FUNÇÕES DE TAREFAS E EVENTOS ==========
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

# ========== FUNÇÕES DE NOTIFICAÇÃO ==========
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

# ========== FUNÇÕES DE ÁUDIO ==========
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
        logger.error(f"❌ Erro ao converter áudio: {e}")
        return False

def transcrever_audio(wav_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio, language="pt-BR")
        except sr.UnknownValueError:
            logger.error("❌ Não foi possível transcrever o áudio.")
            return None
        except sr.RequestError as e:
            logger.error(f"❌ Erro na requisição: {e}")
            return None

# ========== FUNÇÕES DE AGENDAMENTO ==========
def agendar_lembrete(context: CallbackContext, tipo, id, descricao, data, lembrete_minutos):
    try:
        data_lembrete = datetime.fromisoformat(data).replace(tzinfo=timezone.utc) - timedelta(minutes=lembrete_minutos)
        if data_lembrete > datetime.now(timezone.utc):
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                enviar_lembrete,
                trigger="date",
                run_date=data_lembrete,
                args=[context, tipo, id, descricao],
            )
            scheduler.start()
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
    except Exception as e:
        logger.error(f"❌ Erro ao enviar lembrete: {str(e)}")

# ========== FUNÇÕES DE RELATÓRIO ==========
def registrar_metricas_diarias():
    try:
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        relatorio_data = {
            "tarefas_concluidas": len([t for t in buscar_tarefas() if datetime.fromisoformat(t["data_vencimento"]) <= datetime.now(timezone.utc)]),
            "lembretes_enviados": len([t for t in buscar_tarefas() if t.get("lembrete", 0) > 0]),
            "eventos_criados": len(buscar_eventos()),
            "usuarios_ativos": len(buscar_usuarios())
        }
        db.collection("Relatorios").document(hoje).set(relatorio_data)
    except Exception as e:
        logger.error(f"❌ Erro ao registrar métricas: {str(e)}")

scheduler = BackgroundScheduler()

def agendar_registro_metricas():
    try:
        if scheduler.state == 0:
            scheduler.add_job(
                registrar_metricas_diarias,
                trigger="cron",
                hour=23,
                minute=59,
            )
            scheduler.start()
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar agendador: {str(e)}")

# ========== HANDLERS DO TELEGRAM ==========
async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    db.collection("Usuarios").document(str(chat_id)).set({
        "chat_id": chat_id,
        "ativo": True,
        "data_registro": datetime.now(timezone.utc).isoformat()
    })
    await update.message.reply_text("👋 Olá! Vou te ajudar a gerenciar tarefas e e-mails.")

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = """
    🎤 Comandos de Voz:
    - "Enviar email para [destinatário] assunto [assunto] mensagem [texto]"
    - "Definir prioridade para remetente/palavra [valor] como [alta/média/baixa]"
    - "Adicionar tarefa [descrição] com prioridade [alta/média/baixa]"
    - "Agendar [evento] para [data/hora]"
    - "Listar tarefas", "Apagar tarefas", "Relatórios"

    ⌨️ Comandos de Texto:
    /tarefa [descrição] - Adiciona nova tarefa
    /listar - Lista todas as tarefas
    /agenda [título] [data] - Agenda evento
    /eventos - Lista eventos agendados
    /priorizar_email - Gerencia prioridades
    /ler_emails [número] - Lê últimos e-mails
    /emails_prioritarios - Lista e-mails importantes
    /relatorio_diario - Relatório diário
    /relatorio_semanal - Relatório semanal
    """
    await update.message.reply_text(help_text)

async def handle_voice(update: Update, context: CallbackContext) -> None:
    try:
        voice_file = await update.message.voice.get_file()
        ogg_path = "temp_audio.ogg"
        await voice_file.download_to_drive(ogg_path)

        wav_path = "temp_audio.wav"
        if not converter_ogg_para_wav(ogg_path, wav_path):
            await update.message.reply_text("❌ Erro ao processar áudio")
            return

        texto = transcrever_audio(wav_path)
        if not texto:
            await update.message.reply_text("❌ Não entendi o áudio")
            return

        await update.message.reply_text(f"🎤 Você disse: {texto}")
        await processar_comando_voz(update, texto)

    except Exception as e:
        logger.error(f"❌ Erro no processamento de voz: {str(e)}")
        await update.message.reply_text("❌ Erro ao processar comando de voz")
    finally:
        if os.path.exists(ogg_path): os.remove(ogg_path)
        if os.path.exists(wav_path): os.remove(wav_path)

async def processar_comando_voz(update: Update, texto: str):
    texto = texto.lower()
    padrao_email = r"(enviar email|mandar mensagem) para (.+?) assunto (.+?) mensagem (.+)"
    padrao_prioridade = r"(definir prioridade|priorizar) (remetente|palavra) (.+?) como (alta|média|baixa)"
    padrao_tarefa = r"(adicionar tarefa|nova tarefa) (.+?) (com prioridade (.+))?$"
    padrao_evento = r"(agendar|marcar) (.+?) (para|às) (.+)"

    try:
        # Comando: Enviar Email
        if match := re.search(padrao_email, texto):
            destinatario = match.group(2).strip()
            assunto = match.group(3).strip()
            mensagem = match.group(4).strip()
            
            if enviar_email(destinatario, assunto, mensagem):
                await update.message.reply_text(f"✅ E-mail enviado para {destinatario}")
            else:
                await update.message.reply_text("❌ Falha ao enviar e-mail")

        # Comando: Definir Prioridade
        elif match := re.search(padrao_prioridade, texto):
            tipo = match.group(2).lower()
            valor = match.group(3).strip()
            prioridade = match.group(4).lower()
            
            context = CallbackContext()
            context.args = ["add", tipo, f'"{valor}"', prioridade]
            await priorizar_email(update, context)

        # Comando: Adicionar Tarefa
        elif match := re.search(padrao_tarefa, texto):
            descricao = match.group(2).strip()
            prioridade = match.group(4).lower() if match.group(4) else "baixa"

            tarefa_data = {
                "descricao": descricao,
                "prioridade": prioridade,
                "data_criacao": datetime.now(timezone.utc).isoformat()
            }
            salvar_tarefa(tarefa_data)
            await update.message.reply_text(f"✅ Tarefa adicionada: {descricao}")

        # Comando: Agendar Evento
        elif match := re.search(padrao_evento, texto):
            titulo = match.group(2).strip()
            data_hora_texto = match.group(4).strip()
            
            data_hora = dateparser.parse(data_hora_texto, languages=["pt"])
            if not data_hora:
                await update.message.reply_text("❌ Data/hora inválida")
                return

            start_time = f"{data_hora.isoformat()}-03:00"
            end_time = f"{data_hora.isoformat()}-03:00"
            event_link = add_event(titulo, start_time, end_time)
            
            if event_link:
                evento_data = {
                    "titulo": titulo,
                    "data": data_hora.strftime("%Y-%m-%d"),
                    "hora": data_hora.strftime("%H:%M:%S"),
                    "link": event_link
                }
                salvar_evento(evento_data)
                await update.message.reply_text(f"✅ Evento agendado: {titulo}")
            else:
                await update.message.reply_text("❌ Erro ao agendar evento")

        # Comandos Simples
        elif "listar tarefas" in texto:
            await list_tasks(update, CallbackContext())

        elif "apagar todas as tarefas" in texto:
            await clear_tasks(update, CallbackContext())

        elif "relatório diário" in texto:
            await relatorio_diario(update, CallbackContext())

        elif "e-mails prioritários" in texto:
            await listar_emails_prioritarios(update, CallbackContext())

        else:
            await update.message.reply_text("❌ Comando não reconhecido")

    except Exception as e:
        logger.error(f"❌ Erro no processamento de voz: {str(e)}")
        await update.message.reply_text("❌ Erro ao processar comando")

# ========== COMANDOS ADICIONAIS ==========
async def list_tasks(update: Update, context: CallbackContext) -> None:
    tarefas = buscar_tarefas()
    if tarefas:
        response = "\n".join([f"- {t['descricao']} ({t.get('prioridade', 'baixa')})" for t in tarefas])
        await update.message.reply_text(f"📌 Tarefas:\n{response}")
    else:
        await update.message.reply_text("📭 Nenhuma tarefa encontrada")

async def clear_tasks(update: Update, context: CallbackContext) -> None:
    try:
        for tarefa in db.collection("Tarefas").stream():
            tarefa.reference.delete()
        await update.message.reply_text("🗑️ Todas as tarefas foram removidas")
    except Exception as e:
        logger.error(f"❌ Erro ao limpar tarefas: {str(e)}")
        await update.message.reply_text("❌ Erro ao limpar tarefas")

async def listar_emails_prioritarios(update: Update, context: CallbackContext):
    try:
        emails = db.collection("Emails").where("prioridade", "==", "alta").stream()
        response = "\n".join([f"- {e.to_dict()['assunto']}" for e in emails])
        await update.message.reply_text(f"📨 E-mails prioritários:\n{response}")
    except Exception as e:
        logger.error(f"❌ Erro ao listar e-mails: {str(e)}")
        await update.message.reply_text("❌ Erro ao listar e-mails")

async def relatorio_diario(update: Update, context: CallbackContext) -> None:
    try:
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        relatorio = db.collection("Relatorios").document(hoje).get().to_dict()
        response = (
            f"📊 Relatório Diário ({hoje}):\n"
            f"Tarefas Concluídas: {relatorio.get('tarefas_concluidas', 0)}\n"
            f"Lembretes Enviados: {relatorio.get('lembretes_enviados', 0)}\n"
            f"Eventos Criados: {relatorio.get('eventos_criados', 0)}"
        )
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório: {str(e)}")
        await update.message.reply_text("❌ Erro ao gerar relatório")

# ========== FUNÇÃO PRINCIPAL ==========
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tarefa", add_task))
    app.add_handler(CommandHandler("listar", list_tasks))
    app.add_handler(CommandHandler("limpar", clear_tasks))
    app.add_handler(CommandHandler("agenda", add_agenda))
    app.add_handler(CommandHandler("eventos", list_events))
    app.add_handler(CommandHandler("priorizar_email", priorizar_email))
    app.add_handler(CommandHandler("ler_emails", ler_emails_command))
    app.add_handler(CommandHandler("emails_prioritarios", listar_emails_prioritarios))
    app.add_handler(CommandHandler("relatorio_diario", relatorio_diario))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    threading.Thread(target=run_flask, daemon=True).start()
    agendar_registro_metricas()

    logger.info("🚀 Bot iniciado com sucesso!")
    app.run_polling()

if __name__ == "__main__":
    main()