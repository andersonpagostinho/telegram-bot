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
from rapidfuzz import fuzz

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
    /listar - Lista todas as tarefas
    /listar_prioridade - Lista tarefas ordenadas por prioridade
    /limpar - Remove todas as tarefas
    /agenda <título> <data-hora (YYYY-MM-DDTHH:MM:SS)> - Agenda um evento
    /eventos - Lista todos os eventos agendados
    /relatorio_diario - Gera um relatório diário
    /relatorio_semanal - Gera um relatório semanal
    /enviar_email <destinatário> <assunto> <mensagem> - Envia um e-mail
    /ler_emails [número] - Lê últimos e-mails (até 10)
    /emails_prioritarios - Lista e-mails de alta prioridade
    /priorizar_email - Configura priorização de e-mails
    /confirmar_reuniao <ID_Evento> - Confirma uma reunião e notifica os participantes
    /editar_tarefa <ID_ou_Descrição> -prioridade <prioridade> - Altera prioridade
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
        
        # Enviar para WhatsApp
        send_whatsapp_message(mensagem)
        
        # Enviar para Telegram (usuários cadastrados)
        usuarios = buscar_usuarios()
        for usuario in usuarios:
            context.bot.send_message(
                chat_id=usuario["chat_id"],
                text=mensagem
            )
        
        logger.info(f"✅ Reunião {evento_id} confirmada e notificada!")
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
            await update.message.reply_text("✅ Reunião confirmada e notificada aos participantes!")
        else:
            await update.message.reply_text("❌ Erro ao confirmar reunião. Verifique o ID.")
    except IndexError:
        await update.message.reply_text("⚠️ Formato correto: /confirmar_reuniao <ID_Evento>")

def salvar_tarefa(tarefa_data):
    try:
        if "data_vencimento" not in tarefa_data:
            tarefa_data["data_vencimento"] = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        
        if "lembrete" not in tarefa_data:
            tarefa_data["lembrete"] = 0
            
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
            evento_data["lembrete"] = 0
            
        evento_ref = db.collection("Eventos").document()
        evento_data["id"] = evento_ref.id
        evento_ref.set(evento_data)
        logger.info(f"✅ Evento salvo: {evento_data['titulo']}")
        return evento_ref.id
    except Exception as e:
        logger.error(f"❌ Erro ao salvar evento: {str(e)}")
        return None

def salvar_correspondencia(correspondencia_data):
    try:
        correspondencia_ref = db.collection("Correspondencias").document()
        correspondencia_data["id"] = correspondencia_ref.id
        correspondencia_data["data_recebimento"] = datetime.now(timezone.utc).isoformat()
        correspondencia_ref.set(correspondencia_data)
        logger.info(f"✅ Correspondência salva: {correspondencia_data['assunto']}")
        return correspondencia_ref.id
    except Exception as e:
        logger.error(f"❌ Erro ao salvar correspondência: {str(e)}")
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

def buscar_tarefa_por_descricao(descricao: str):
    """Busca tarefas com descrição semelhante usando fuzzy matching"""
    try:
        tarefas_ref = db.collection("Tarefas").stream()
        tarefas = [t for t in tarefas_ref]
        
        # Aplica fuzzy matching para encontrar a melhor correspondência
        melhor_tarefa = None
        melhor_pontuacao = 0
        
        for tarefa in tarefas:
            descricao_tarefa = tarefa.get("descricao", "").lower()
            pontuacao = fuzz.ratio(descricao.lower(), descricao_tarefa)
            
            if pontuacao > melhor_pontuacao and pontuacao >= 70:  # Limite de 70% de similaridade
                melhor_tarefa = tarefa
                melhor_pontuacao = pontuacao
        
        return melhor_tarefa  # Retorna a tarefa mais semelhante ou None
    
    except Exception as e:
        logger.error(f"❌ Erro ao buscar tarefa por descrição: {str(e)}")
        return None

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
        logger.info(f"✅ Mensagem enviada para {USER_WHATSAPP_NUMBER}: {message}")
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

def agendar_lembrete(context: CallbackContext, tipo, id, descricao, data, lembrete_minutos):
    try:
        data_lembrete = datetime.fromisoformat(data).replace(tzinfo=timezone.utc) - timedelta(minutes=lembrete_minutos)
        agora = datetime.now(timezone.utc)

        if data_lembrete > agora:
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

async def enviar_lembrete(context: CallbackContext, tipo, id, descricao):
    try:
        logger.info(f"🚀 Enviando lembrete manualmente: {tipo} - {descricao}")
        usuarios = buscar_usuarios()
        for usuario in usuarios:
            chat_id = usuario["chat_id"]
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ Lembrete TESTE: {tipo} '{descricao}' está chegando!"
            )
        logger.info(f"✅ Lembrete TESTE enviado para {len(usuarios)} usuários.")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar lembrete: {str(e)}")

def registrar_metricas_diarias():
    try:
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tarefas_concluidas = len([t for t in buscar_tarefas() if datetime.fromisoformat(t["data_vencimento"]) <= datetime.now(timezone.utc)])
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
            logger.info("✅ Agendador de lembretes iniciado com sucesso!")
        else:
            logger.info("⏳ Agendador de lembretes já está rodando.")
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
        calendar_id = "andersonpagostinho@gmail.com"
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if events:
            logger.info(f"📅 Eventos encontrados ({len(events)}) entre {start_time} e {end_time}:")
            for event in events:
                logger.info(f"   🕒 {event['start']['dateTime']} - {event['end']['dateTime']} ({event.get('summary', 'Sem título')})")
        else:
            logger.info(f"✅ Nenhum evento encontrado entre {start_time} e {end_time}.")

        return events
    except Exception as e:
        logger.error(f"❌ Erro ao verificar horários ocupados: {str(e)}")
        return []

def sugerir_horarios_livres(start_time, end_time, duracao_minutos=60):
    try:
        inicio_periodo = datetime.fromisoformat(start_time).astimezone(timezone.utc)
        fim_periodo = datetime.fromisoformat(end_time).astimezone(timezone.utc)

        horario_comercial_inicio = max(inicio_periodo.replace(hour=9, minute=0, second=0, microsecond=0), inicio_periodo)
        horario_comercial_fim = min(inicio_periodo.replace(hour=18, minute=0, second=0, microsecond=0), fim_periodo)

        if horario_comercial_inicio >= horario_comercial_fim:
            logger.info("⛔ Nenhum horário comercial dentro do período solicitado.")
            return []

        eventos = verificar_horarios_ocupados(
            horario_comercial_inicio.isoformat(),
            horario_comercial_fim.isoformat()
        )
        horarios_ocupados = []

        for evento in eventos:
            inicio = datetime.fromisoformat(evento['start']['dateTime']).astimezone(timezone.utc)
            fim = datetime.fromisoformat(evento['end']['dateTime']).astimezone(timezone.utc)
            horarios_ocupados.append((inicio, fim))

        horarios_ocupados.sort()

        horarios_livres = []
        proximo_inicio = horario_comercial_inicio

        if not horarios_ocupados:
            horarios_livres.append((horario_comercial_inicio, horario_comercial_fim))
        else:
            for ocupado_inicio, ocupado_fim in horarios_ocupados:
                if proximo_inicio + timedelta(minutes=duracao_minutos) <= ocupado_inicio:
                    horarios_livres.append((proximo_inicio, ocupado_inicio))
                
                proximo_inicio = max(proximo_inicio, ocupado_fim)

            if proximo_inicio + timedelta(minutes=duracao_minutos) <= horario_comercial_fim:
                horarios_livres.append((proximo_inicio, horario_comercial_fim))

        logger.info(f"✅ Horários livres sugeridos: {horarios_livres}")
        return horarios_livres
    except Exception as e:
        logger.error(f"❌ Erro ao sugerir horários livres: {str(e)}")
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
            await update.message.reply_text("❌ Erro ao processar o áudio. Tente novamente.")
            return

        texto = transcrever_audio(wav_path)
        if not texto:
            await update.message.reply_text("❌ Não entendi o áudio. Pode repetir?")
            return

        await update.message.reply_text(f"🎤 Você disse: {texto}")
        await processar_comando_voz(update, context, texto)

    except Exception as e:
        logger.error(f"❌ Erro ao processar áudio: {str(e)}")
        await update.message.reply_text("❌ Ocorreu um erro ao processar o áudio. Tente novamente.")
    finally:
        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)
        logger.info("✅ Arquivos temporários removidos.")

async def processar_comando_voz(update: Update, context: CallbackContext, texto: str):
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
            "data_criacao": datetime.now(timezone.utc).isoformat()
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

    elif "ler e-mails" in texto or "verificar e-mails" in texto:
        num_emails = 5
        if "últimos" in texto:
            try:
                num_emails = int(re.search(r'\d+', texto).group())
                if num_emails > 10:
                    num_emails = 10
            except:
                pass

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

    elif "listar tarefas" in texto:
        await list_tasks(update, context)

    elif "listar tarefas por prioridade" in texto:
        await list_tasks_by_priority(update, context)

    elif "limpar todas as tarefas" in texto:
        await update.message.reply_text("⚠️ Tem certeza que deseja apagar TODAS as tarefas? Responda 'sim' para confirmar.")
        context.user_data['aguardando_confirmacao'] = True

    elif "listar eventos" in texto:
        await list_events(update, context)

    elif "gerar relatório diário" in texto:
        await relatorio_diario(update, context)

    elif "gerar relatório semanal" in texto:
        await relatorio_semanal(update, context)

    elif re.search(r'editar (prioridade|importância) (da tarefa|do compromisso) (.+?) para (alta|média|baixa)', texto):
        match = re.search(r'editar (prioridade|importância) (da tarefa|do compromisso) (.+?) para (alta|média|baixa)', texto)
        descricao_tarefa = match.group(3).strip()
        nova_prioridade = match.group(4).lower()
        
        # Buscar tarefa por descrição
        tarefas_ref = db.collection("Tarefas")
        tarefas = tarefas_ref.where("descricao", "==", descricao_tarefa).stream()
        
        tarefas_list = list(tarefas)
        if not tarefas_list:
            await update.message.reply_text(f"❌ Nenhuma tarefa encontrada com a descrição: '{descricao_tarefa}'")
            return
            
        if len(tarefas_list) > 1:
            ids = "\n".join([f"- ID: {t.id}" for t in tarefas_list])
            await update.message.reply_text(
                f"⚠️ Várias tarefas encontradas. Especifique o ID:\n{ids}\n"
                f"Exemplo por voz: 'Editar prioridade da tarefa ID ABC123 para alta'"
            )
            return
            
        # Atualizar se encontrou apenas uma
        tarefa_ref = tarefas_list[0].reference
        tarefa_ref.update({"prioridade": nova_prioridade})
        await update.message.reply_text(
            f"✅ Prioridade da tarefa '{descricao_tarefa}' "
            f"atualizada para {nova_prioridade.capitalize()}!"
        )
        send_whatsapp_message(
            f"📝 Tarefa atualizada por voz:\n"
            f"'{descricao_tarefa}'\n"
            f"Nova prioridade: {nova_prioridade}"
        )


    elif "enviar e-mail para" in texto:
        try:
            match = re.search(r'para (.+?) assunto (.+?) mensagem (.+)', texto)
            if match:
                destinatario = match.group(1).strip()
                assunto = match.group(2).strip()
                mensagem = match.group(3).strip()
                
                if enviar_email(destinatario, assunto, mensagem):
                    await update.message.reply_text(f"✅ E-mail enviado para {destinatario}!")
                else:
                    await update.message.reply_text("❌ Falha ao enviar e-mail.")
            else:
                await update.message.reply_text("❌ Formato inválido. Use: 'Enviar e-mail para [email] assunto [texto] mensagem [texto]'")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail por voz: {str(e)}")
            await update.message.reply_text("❌ Erro ao processar comando de e-mail.")

    elif "priorizar e-mail do" in texto and "como" in texto:
        try:
            partes = re.split(r' do | como ', texto)
            remetente = partes[1].strip()
            prioridade = partes[2].strip()
            
            context.args = ["add", "remetente", remetente, prioridade]
            await priorizar_email(update, context)
        except Exception as e:
            logger.error(f"Erro priorização por voz: {str(e)}")
            await update.message.reply_text("❌ Formato inválido. Use: 'Priorizar e-mail do [email] como [prioridade]'")

    elif "mostrar e-mails prioritários" in texto or "listar e-mails importantes" in texto:
        await listar_emails_prioritarios(update, context)

    elif re.search(r'editar (prioridade|importância) (da tarefa|do compromisso) (.+?) para (alta|média|baixa)', texto):
        match = re.search(r'editar (prioridade|importância) (da tarefa|do compromisso) (.+?) para (alta|média|baixa)', texto)
        descricao_tarefa = match.group(3).strip()
        nova_prioridade = match.group(4).lower()
        
        # Buscar tarefa por descrição aproximada
        tarefa = buscar_tarefa_por_descricao(descricao_tarefa)
        
        if not tarefa:
            await update.message.reply_text(
                f"❌ Nenhuma tarefa encontrada com descrição semelhante a: '{descricao_tarefa}'"
            )
            return
            
        # Atualizar prioridade
        tarefa.reference.update({"prioridade": nova_prioridade})
        await update.message.reply_text(
            f"✅ Prioridade da tarefa '{tarefa.get('descricao')}' "
            f"atualizada para {nova_prioridade.capitalize()}!"
        )
        send_whatsapp_message(
            f"📝 Tarefa atualizada por voz:\n"
            f"'{tarefa.get('descricao')}'\n"
            f"Nova prioridade: {nova_prioridade}"
        )

    elif context.user_data.get('aguardando_confirmacao') and "sim" in texto:
        await clear_tasks(update, context)
        context.user_data['aguardando_confirmacao'] = False

    else:
        await update.message.reply_text("❌ Comando não reconhecido. Diga 'ajuda' para ver os comandos disponíveis.")

async def add_task(update: Update, context: CallbackContext) -> None:
    args = context.args
    full_text = ' '.join(args)
    
    prioridade_match = re.search(r'-prioridade (\w+)', full_text)
    data_match = re.search(r'-data (.+?)(?= -|$)', full_text)
    lembrete_match = re.search(r'-lembrete (\d+)', full_text)
    
    prioridade = prioridade_match.group(1).lower() if prioridade_match else "baixa"
    data_vencimento = data_match.group(1) if data_match else None
    lembrete = int(lembrete_match.group(1)) if lembrete_match else 0
    
    data_obj = datetime.now(timezone.utc) + timedelta(days=3)
    
    if data_vencimento:
        data_obj = dateparser.parse(data_vencimento, languages=['pt'])
        if not data_obj:
            await update.message.reply_text("❌ Data inválida! Use o formato: dd/mm/aaaa ou 'amanhã'")
            return
        data_iso = data_obj.isoformat()
    else:
        data_iso = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    descricao = re.sub(r'(-prioridade \w+|-data .+?|-lembrete \d+)', '', full_text).strip()

    if not descricao:
        await update.message.reply_text("⚠️ Formato correto:\n/tarefa Comprar leite -prioridade alta -data amanhã -lembrete 30")
        return

    tarefa_data = {
        "descricao": descricao,
        "prioridade": prioridade,
        "data_criacao": datetime.now(timezone.utc).isoformat(),
        "data_vencimento": data_iso,
        "lembrete": lembrete
    }
    
    tarefa_id = salvar_tarefa(tarefa_data)
    if tarefa_id:
        msg = f"✅ Tarefa adicionada:\n{descricao}\n📅 Vencimento: {data_obj.strftime('%d/%m/%Y')}\n⏰ Lembrete: {lembrete} minutos antes"
        await update.message.reply_text(msg)
        
        if lembrete > 0:
            agendar_lembrete(context, "Tarefa", tarefa_id, descricao, data_iso, lembrete)
    else:
        await update.message.reply_text("❌ Erro ao adicionar tarefa.")

async def list_tasks(update: Update, context: CallbackContext) -> None:
    tarefas = buscar_tarefas()
    if tarefas:
        task_list = "\n".join([f"🆔 {tarefa['id']}\n- {tarefa['descricao']}\nPrioridade: {tarefa.get('prioridade', 'baixa')}\n" 
                      for tarefa in tarefas])
        await update.message.reply_text(f"📌 Suas tarefas:\n{task_list}")
        send_whatsapp_message(f"📌 Suas tarefas:\n{task_list[:1500]}")  # Limite do WhatsApp
    else:
        await update.message.reply_text("📭 Nenhuma tarefa adicionada.")

async def list_tasks_by_priority(update: Update, context: CallbackContext) -> None:
    tarefas = buscar_tarefas()
    if tarefas:
        prioridade_ordem = {"alta": 1, "média": 2, "baixa": 3}
        tarefas_ordenadas = sorted(tarefas, key=lambda x: prioridade_ordem.get(x.get("prioridade", "baixa"), 3))
        task_list = "\n".join([f"- {tarefa['descricao']} (Prioridade: {tarefa.get('prioridade', 'baixa')}" for tarefa in tarefas_ordenadas])
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

    try:
        data_hora_obj = datetime.fromisoformat(data_hora)
        if not data_hora_obj.tzinfo:
            data_hora_obj = data_hora_obj.replace(tzinfo=timezone(timedelta(hours=-3)))
        start_time = data_hora_obj.isoformat()
        end_time = (data_hora_obj + timedelta(hours=1)).isoformat()
    except ValueError:
        await update.message.reply_text("❌ Formato de data/hora inválido. Use o formato: YYYY-MM-DDTHH:MM:SS")
        return

    eventos_ocupados = verificar_horarios_ocupados(start_time, end_time)
    if eventos_ocupados:
        await update.message.reply_text("❌ Horário ocupado. Sugerindo horários livres...")
        horarios_livres = sugerir_horarios_livres(start_time, end_time)
        if horarios_livres:
            mensagem = "📅 Horários livres sugeridos:\n"
            for inicio, fim in horarios_livres:
                mensagem += f"- {inicio.strftime('%Y-%m-%d %H:%M')} às {fim.strftime('%H:%M')}\n"
            await update.message.reply_text(mensagem)
            send_whatsapp_message(mensagem)
        else:
            await update.message.reply_text("❌ Nenhum horário livre encontrado.")
            send_whatsapp_message("❌ Nenhum horário livre encontrado.")
        return
    
    event_link = add_event(titulo, start_time, end_time)
    if event_link:
        evento_data = {
            "titulo": titulo,
            "data": data_hora_obj.strftime("%Y-%m-%d"),
            "hora": data_hora_obj.strftime("%H:%M:%S"),
            "link": event_link,
            "notificado": False,
            "lembrete": lembrete
        }
        salvar_evento(evento_data)
        await update.message.reply_text(f"✅ Evento '{titulo}' agendado para {data_hora_obj.strftime('%Y-%m-%d %H:%M')}.\n🔗 {event_link}")
        send_whatsapp_message(f"✅ Evento '{titulo}' agendado para {data_hora_obj.strftime('%Y-%m-%d %H:%M')}.\n🔗 {event_link}")
        
        if lembrete > 0:
            agendar_lembrete(context, "Evento", evento_data["id"], titulo, start_time, lembrete)
    else:
        await update.message.reply_text("❌ Erro ao adicionar evento!")
        send_whatsapp_message("❌ Erro ao adicionar evento!")

def add_event(summary, start_time, end_time):
    try:
        service = get_calendar_service()
        calendar_id = "andersonpagostinho@gmail.com"
        
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'},
            'conferenceData': {  # Adiciona Google Meet automaticamente
                'createRequest': {'requestId': 'sample123', 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}
            }
        }
        
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event,
            conferenceDataVersion=1
        ).execute()
        
        event_link = created_event.get('hangoutLink', created_event['htmlLink'])
        
        # Salvar no Firebase com status pendente
        evento_data = {
            "titulo": summary,
            "data": datetime.fromisoformat(start_time).strftime("%Y-%m-%d"),
            "hora": datetime.fromisoformat(start_time).strftime("%H:%M:%S"),
            "link": event_link,
            "status": "pendente",
            "participantes": []  # Adicione participantes se necessário
        }
        evento_ref = db.collection("Eventos").document()
        evento_ref.set(evento_data)
        
        logger.info(f"✅ Evento Criado: {event_link}")
        return event_link
    
    except Exception as e:
        logger.error(f"❌ Erro ao criar evento: {str(e)}")
        return None

async def relatorio_diario(update: Update, context: CallbackContext) -> None:
    try:
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        relatorio = db.collection("Relatorios").document(hoje).get()
        
        if relatorio.exists:
            relatorio_data = relatorio.to_dict()
            msg = f"📊 Relatório Diário ({hoje}):\n"
            msg += f"✅ Tarefas Concluídas: {relatorio_data.get('tarefas_concluidas', 0)}\n"
            msg += f"🔔 Lembretes Enviados: {relatorio_data.get('lembretes_enviados', 0)}\n"
            msg += f"📅 Eventos Criados: {relatorio_data.get('eventos_criados', 0)}\n"
            msg += f"👤 Usuários Ativos: {relatorio_data.get('usuarios_ativos', 0)}"
            await update.message.reply_text(msg)
            send_whatsapp_message(msg)
        else:
            await update.message.reply_text(f"📭 Nenhum relatório encontrado para {hoje}.")
            send_whatsapp_message(f"📭 Nenhum relatório encontrado para {hoje}.")
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório diário: {str(e)}")
        await update.message.reply_text("❌ Erro ao gerar relatório diário.")
        send_whatsapp_message("❌ Erro ao gerar relatório diário.")

async def relatorio_semanal(update: Update, context: CallbackContext) -> None:
    try:
        hoje = datetime.now(timezone.utc)
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        relatorios_semana = db.collection("Relatorios").where("__name__", ">=", inicio_semana.strftime("%Y-%m-%d")).where("__name__", "<=", fim_semana.strftime("%Y-%m-%d")).stream()
        
        relatorios_data = [doc.to_dict() for doc in relatorios_semana]
        
        if relatorios_data:
            tarefas_concluidas = sum(relatorio.get("tarefas_concluidas", 0) for relatorio in relatorios_data)
            lembretes_enviados = sum(relatorio.get("lembretes_enviados", 0) for relatorio in relatorios_data)
            eventos_criados = sum(relatorio.get("eventos_criados", 0) for relatorio in relatorios_data)
            usuarios_ativos = sum(relatorio.get("usuarios_ativos", 0) for relatorio in relatorios_data)
            
            msg = f"📊 Relatório Semanal ({inicio_semana.strftime('%Y-%m-%d')} a {fim_semana.strftime('%Y-%m-%d')}):\n"
            msg += f"✅ Tarefas Concluídas: {tarefas_concluidas}\n"
            msg += f"🔔 Lembretes Enviados: {lembretes_enviados}\n"
            msg += f"📅 Eventos Criados: {eventos_criados}\n"
            msg += f"👤 Usuários Ativos: {usuarios_ativos}"
            await update.message.reply_text(msg)
            send_whatsapp_message(msg)
        else:
            await update.message.reply_text(f"📭 Nenhum relatório encontrado para a semana de {inicio_semana.strftime('%Y-%m-%d')} a {fim_semana.strftime('%Y-%m-%d')}.")
            send_whatsapp_message(f"📭 Nenhum relatório encontrado para a semana de {inicio_semana.strftime('%Y-%m-%d')} a {fim_semana.strftime('%Y-%m-%d')}.")
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório semanal: {str(e)}")
        await update.message.reply_text("❌ Erro ao gerar relatório semanal.")
        send_whatsapp_message("❌ Erro ao gerar relatório semanal.")

async def enviar_email_command(update: Update, context: CallbackContext) -> None:
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("⚠️ Formato correto: /enviar_email <destinatário> <assunto> <mensagem>")
            return

        destinatario = args[0]
        assunto = args[1]
        mensagem = ' '.join(args[2:])

        if enviar_email(destinatario, assunto, mensagem):
            await update.message.reply_text(f"✅ E-mail enviado para {destinatario} com sucesso!")
            send_whatsapp_message(f"✅ E-mail enviado para {destinatario} com sucesso!")
        else:
            await update.message.reply_text("❌ Erro ao enviar e-mail.")
            send_whatsapp_message("❌ Erro ao enviar e-mail.")
    except Exception as e:
        logger.error(f"❌ Erro ao processar comando de e-mail: {str(e)}")
        await update.message.reply_text("❌ Erro ao enviar e-mail.")
        send_whatsapp_message("❌ Erro ao enviar e-mail.")
def enviar_convite(destinatario: str, assunto: str, mensagem: str, evento_link: str):
    try:
        service = build('gmail', 'v1', credentials=get_calendar_service()._credentials)
        
        email_msg = MIMEText(f"{mensagem}\n\n🔗 Link do Evento: {evento_link}")
        email_msg['To'] = destinatario
        email_msg['From'] = EMAIL_USER
        email_msg['Subject'] = assunto

        raw_message = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()
        message = {'raw': raw_message}

        service.users().messages().send(userId='me', body=message).execute()
        logger.info(f"✅ Convite enviado para {destinatario}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao enviar convite: {str(e)}")
        return False

async def confirmar_presenca(update: Update, context: CallbackContext):
    try:
        evento_id = context.args[0]
        chat_id = str(update.effective_chat.id)
        
        evento_ref = db.collection("Eventos").document(evento_id)
        evento = evento_ref.get().to_dict()
        
        if not evento:
            await update.message.reply_text("❌ Evento não encontrado.")
            return
        
        participantes = evento.get("participantes", [])
        if chat_id not in participantes:
            participantes.append(chat_id)
            evento_ref.update({"participantes": participantes})
            await update.message.reply_text("✅ Presença confirmada!")
        else:
            await update.message.reply_text("⚠️ Você já confirmou presença.")
    except IndexError:
        await update.message.reply_text("⚠️ Formato correto: /confirmar_presenca <ID_Evento>")
    except Exception as e:
        logger.error(f"❌ Erro ao confirmar presença: {str(e)}")
        await update.message.reply_text("❌ Erro ao confirmar presença.")

async def editar_tarefa(update: Update, context: CallbackContext) -> None:
    """Edita a prioridade de uma tarefa existente por ID ou Descrição"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("⚠️ Formato correto:\n/editar_tarefa <ID_ou_Descrição> -prioridade <nova_prioridade>")
            return

        # Extrair prioridade e critério de busca
        prioridade = args[-1].lower()
        criterio_busca = ' '.join(args[:-2]).strip('"')  # Suporta descrições com espaços

        if prioridade not in ["alta", "média", "baixa"]:
            await update.message.reply_text("❌ Prioridade inválida! Use: alta, média ou baixa")
            return

        # Buscar por ID ou Descrição
        tarefas_ref = db.collection("Tarefas")
        if criterio_busca.startswith("id:"):
            tarefa_id = criterio_busca[3:].strip()
            tarefa_ref = tarefas_ref.document(tarefa_id)
        else:
            # Busca por descrição exata (case-insensitive)
            tarefas = tarefas_ref.where("descricao", "==", criterio_busca).stream()
            tarefas_list = list(tarefas)
            
            if not tarefas_list:
                await update.message.reply_text("❌ Nenhuma tarefa encontrada com essa descrição!")
                return
            if len(tarefas_list) > 1:
                await update.message.reply_text("⚠️ Várias tarefas encontradas. Use o ID:\n" + 
                                               "\n".join([f"- {t.id}: {t.get('descricao')}" for t in tarefas_list]))
                return
            tarefa_ref = tarefas_list[0].reference

        # Atualizar prioridade
        tarefa_ref.update({"prioridade": prioridade})
        await update.message.reply_text(f"✅ Prioridade atualizada para {prioridade.capitalize()}!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao editar tarefa: {str(e)}")
        await update.message.reply_text("❌ Erro ao atualizar tarefa. Verifique os dados.")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tarefa", add_task))
    app.add_handler(CommandHandler("listar", list_tasks))
    app.add_handler(CommandHandler("listar_prioridade", list_tasks_by_priority))
    app.add_handler(CommandHandler("limpar", clear_tasks))
    app.add_handler(CommandHandler("agenda", add_agenda))
    app.add_handler(CommandHandler("eventos", list_events))
    app.add_handler(CommandHandler("relatorio_diario", relatorio_diario))
    app.add_handler(CommandHandler("relatorio_semanal", relatorio_semanal))
    app.add_handler(CommandHandler("enviar_email", enviar_email_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CommandHandler("ler_emails", ler_emails_command))
    app.add_handler(CommandHandler("priorizar_email", priorizar_email))
    app.add_handler(CommandHandler("emails_prioritarios", listar_emails_prioritarios))
    app.add_handler(CommandHandler("confirmar_reuniao", comando_confirmar_reuniao))
    app.add_handler(CommandHandler("confirmar_presenca", confirmar_presenca))  
    app.add_handler(CommandHandler("editar_tarefa", editar_tarefa))

    threading.Thread(target=run_flask, daemon=True).start()

    agendar_registro_metricas()

    logger.info("🚀 Bot rodando com polling...")
    app.run_polling()

if __name__ == "__main__":
    main()