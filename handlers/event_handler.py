import logging
import os
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import salvar_dados, buscar_dados

logger = logging.getLogger(__name__)

# Configuração do Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

if not GOOGLE_CREDENTIALS_JSON or not CALENDAR_ID:
    raise ValueError("❌ Credenciais do Google Calendar não encontradas!")

creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_JSON, scopes=SCOPES)
service = build("calendar", "v3", credentials=creds)

# ✅ Criar um evento no Google Calendar
async def add_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Você precisa informar uma descrição para o evento.")
        return
    
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    event = {
        "summary": descricao,
        "start": {"dateTime": start_time.isoformat() + "Z", "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat() + "Z", "timeZone": "UTC"},
    }
    created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    event_id = created_event["id"]
    
    evento_data = {"descricao": descricao, "event_id": event_id, "confirmado": False}
    salvar_dados("Eventos", evento_data)
    await update.message.reply_text(f"📅 Evento adicionado ao Google Calendar: {descricao}")

# ✅ Listar eventos do Google Calendar
async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.utcnow().isoformat() + "Z"
    events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=now, maxResults=5, singleEvents=True, orderBy="startTime").execute()
    events = events_result.get("items", [])
    
    if not events:
        await update.message.reply_text("📭 Nenhum evento encontrado.")
        return
    
    resposta = "📅 Próximos eventos:
" + "\n".join(f"- {event['summary']} ({event['start'].get('dateTime', 'Sem horário definido')})" for event in events)
    await update.message.reply_text(resposta)

# ✅ Confirmar um evento no Google Calendar
async def confirmar_reuniao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe a descrição do evento que deseja confirmar.")
        return
    
    eventos = buscar_dados("Eventos")
    for evento in eventos:
        if evento["descricao"].lower() == descricao.lower():
            event_id = evento.get("event_id")
            if event_id:
                updated_event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
                updated_event["status"] = "confirmed"
                service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=updated_event).execute()
            
            evento["confirmado"] = True
            salvar_dados("Eventos", evento)
            await update.message.reply_text(f"✅ Evento confirmado: {descricao}")
            return
    
    await update.message.reply_text("❌ Evento não encontrado.")


# ✅ Adicionar um evento à agenda
async def add_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Você precisa informar uma descrição para o evento.")
        return

    evento_data = {"descricao": descricao, "confirmado": False}
    salvar_dados("Eventos", evento_data)
    await update.message.reply_text(f"📅 Evento adicionado: {descricao}")

# ✅ Listar eventos agendados
async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eventos = buscar_dados("Eventos")
    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado.")
        return
    
    resposta = "📅 Eventos agendados:\n" + "\n".join(f"- {e['descricao']} ({'✅ Confirmado' if e.get('confirmado') else '❌ Pendente'})" for e in eventos)
    await update.message.reply_text(resposta)

# ✅ Confirmar um evento agendado
async def confirmar_reuniao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe a descrição do evento que deseja confirmar.")
        return

    eventos = buscar_dados("Eventos")
    for evento in eventos:
        if evento["descricao"].lower() == descricao.lower():
            evento["confirmado"] = True
            salvar_dados("Eventos", evento)
            await update.message.reply_text(f"✅ Evento confirmado: {descricao}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")

# ✅ Confirmar presença em um evento
async def confirmar_presenca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe o nome do evento para confirmar presença.")
        return

    eventos = buscar_dados("Eventos")
    for evento in eventos:
        if evento["descricao"].lower() == descricao.lower():
            evento["confirmado"] = True
            salvar_dados("Eventos", evento)
            await update.message.reply_text(f"✅ Presença confirmada no evento: {descricao}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")
