import logging, dateparser
from datetime import datetime, time, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import salvar_cliente, buscar_cliente, buscar_dados, salvar_dado_em_path, buscar_subcolecao, salvar_evento
from config.google_config import get_calendar_service
from services.google_calendar_service import add_event
from utils.whatsapp_utils import send_whatsapp_message

logger = logging.getLogger(__name__)

# ✅ Configuração do serviço do Google Calendar
service = get_calendar_service()

# ✅ Comando para configurar o Google Calendar ID
async def configurar_google_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Você precisa fornecer um Google Calendar ID. Exemplo: /configurar_google_calendar <ID>")
        return

    user_id = str(update.message.from_user.id)
    calendar_id = context.args[0]

    sucesso = salvar_cliente(user_id, {"calendar_id": calendar_id})

    if sucesso:
        await update.message.reply_text(f"✅ Google Calendar ID configurado: {calendar_id}")
    else:
        await update.message.reply_text("❌ Erro ao salvar os dados no Firebase.")

# ✅ Criar um evento no Google Calendar
async def add_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text(
            "⚠️ Uso correto: /agenda <Descrição> <YYYY-MM-DD> <HH:MM início> <HH:MM fim>\n"
            "Exemplo: /agenda Reunião 2025-03-25 14:00 15:00"
        )
        return

    descricao = context.args[0]
    data = context.args[1]
    hora_inicio = context.args[2]
    hora_fim = context.args[3]

    user_id = str(update.message.from_user.id)
    cliente = buscar_cliente(user_id)
    calendar_id = cliente.get("calendar_id") if cliente else None

    if not calendar_id:
        await update.message.reply_text("❌ Google Calendar ID não configurado. Use /configurar_google_calendar <ID>")
        return

    try:
        start_time = datetime.fromisoformat(f"{data}T{hora_inicio}")
        end_time = datetime.fromisoformat(f"{data}T{hora_fim}")
    except ValueError:
        await update.message.reply_text("⚠️ Data/hora inválida. Verifique o formato e tente novamente.")
        return

    duration = end_time - start_time

    # 🔍 Verifica conflitos
    time_min = datetime.combine(start_time.date(), time(8, 0)).isoformat() + "Z"
    time_max = datetime.combine(start_time.date(), time(18, 0)).isoformat() + "Z"
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    eventos_do_dia = events_result.get("items", [])

    conflito = False
    ocupados = []

    for ev in eventos_do_dia:
        ev_start = datetime.fromisoformat(ev["start"]["dateTime"]).replace(tzinfo=None)
        ev_end = datetime.fromisoformat(ev["end"]["dateTime"]).replace(tzinfo=None)
        ocupados.append((ev_start, ev_end))

        if start_time < ev_end and end_time > ev_start:
            conflito = True

    if conflito:
        # 🔁 Gera sugestões alternativas no mesmo dia
        hora_comercial_inicio = datetime.combine(start_time.date(), time(8, 0))
        hora_comercial_fim = datetime.combine(start_time.date(), time(18, 0))
        sugestoes = []
        atual = hora_comercial_inicio

        while atual + duration <= hora_comercial_fim:
            conflito_local = False
            for ev_start, ev_end in ocupados:
                if atual < ev_end and (atual + duration) > ev_start:
                    conflito_local = True
                    break
            if not conflito_local:
                sugestoes.append(f"{atual.strftime('%H:%M')} - {(atual + duration).strftime('%H:%M')}")
                if len(sugestoes) == 3:
                    break
            atual += timedelta(minutes=15)

        resposta = "⚠️ Já existe um evento nesse horário.\n"
        if sugestoes:
            resposta += f"💡 Horários alternativos disponíveis para {data}:\n" + "\n".join(f"- {s}" for s in sugestoes)
        else:
            resposta += "❌ Não foi possível encontrar horários alternativos no mesmo dia."

        await update.message.reply_text(resposta)
        return

    # ✅ Sem conflito — criar evento
    event = {
        "summary": descricao,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "America/Sao_Paulo"},
    }

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    event_id = created_event["id"]
    event_link = created_event.get("htmlLink")

    evento_data = {
        "descricao": descricao,
        "event_id": event_id,
        "data": data,
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "confirmado": False,
        "link": event_link
    }

    salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento_data)

    await update.message.reply_text(
        f"📅 Evento adicionado ao Google Calendar:\n\n"
        f"**{descricao}**\n🗓️ Data: {data}\n⏰ Horário: {hora_inicio} às {hora_fim}\n\n"
        f"🔗 [Clique aqui para ver o evento]({event_link})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# ✅ Listar eventos do Google Calendar
async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cliente = buscar_cliente(user_id)
    calendar_id = cliente.get("calendar_id") if cliente else None
    
    if not calendar_id:
        await update.message.reply_text("❌ Google Calendar ID não configurado. Use /configurar_google_calendar <ID>")
        return

    now = datetime.utcnow().isoformat() + "Z"
    events_result = service.events().list(calendarId=calendar_id, timeMin=now, maxResults=5, singleEvents=True, orderBy="startTime").execute()
    events = events_result.get("items", [])

    if not events:
        await update.message.reply_text("📭 Nenhum evento encontrado.")
        return

    resposta = (
        "📅 Próximos eventos:\n"
        + "\n".join(f"- {event['summary']} ({event['start'].get('dateTime', 'Sem horário definido')})" for event in events)
    )
    await update.message.reply_text(resposta)

# 🔹 Confirmar um evento no Google Calendar
async def confirmar_reuniao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe a descrição do evento que deseja confirmar.")
        return
    
    user_id = str(update.message.from_user.id)
    eventos = buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado para confirmar.")
        return
    
    for event_id, evento in eventos.items():
        if (
            evento["descricao"].lower() == descricao.lower()
            or descricao.lower() in f"{evento['descricao']} {evento['data']} {evento['hora_inicio']} {evento['hora_fim']}".lower()
    ):
            cliente = buscar_cliente(user_id)
            calendar_id = cliente.get("calendar_id") if cliente else None
            if not calendar_id:
               await update.message.reply_text("❌ Google Calendar ID não configurado.")
               return

            updated_event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            updated_event["status"] = "confirmed"
            service.events().update(calendarId=calendar_id, eventId=event_id, body=updated_event).execute()

            evento["confirmado"] = True
            salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento)
            await update.message.reply_text(f"✅ Evento confirmado: {evento['descricao']}")
            return
    
    await update.message.reply_text("❌ Evento não encontrado.")

# ✅ Confirmar presença em um evento
async def confirmar_presenca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe o nome do evento para confirmar presença.")
        return

    user_id = str(update.message.from_user.id)
    eventos = buscar_dados(f"Clientes/{user_id}/Eventos")

    for event_id, evento in eventos.items():
        if evento["descricao"].lower() == descricao.lower():
            evento["confirmado"] = True
            salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento)
            await update.message.reply_text(f"✅ Presença confirmada no evento: {descricao}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")

# ✅ Comando para testar o Firebase via bot
async def debug_eventos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    # 🔹 Salvar evento de teste
    event_id = "evento_debug"
    evento_data = {
        "descricao": "Evento de Teste via Bot",
        "data": "2025-03-30",
        "hora_inicio": "12:00",
        "hora_fim": "13:00",
        "confirmado": False,
        "link": "https://exemplo.com/evento-debug"
    }

    sucesso = salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento_data)

    if sucesso:
        await update.message.reply_text("✅ Evento de teste salvo com sucesso no Firebase.")
    else:
        await update.message.reply_text("❌ Erro ao salvar o evento de teste.")

    # 🔍 Buscar todos os eventos do usuário
    eventos = buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado no Firebase.")
        return

    resposta = "📂 Eventos encontrados no Firebase:\n"
    for eid, ev in eventos.items():
        resposta += f"\n📌 {eid}: {ev.get('descricao')} ({ev.get('data')} {ev.get('hora_inicio')} - {ev.get('hora_fim')})"

    await update.message.reply_text(resposta)

async def add_evento_por_voz(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    try:
        texto = texto.lower().replace("marcar reunião", "").replace("agendar reunião", "").strip()
        data_hora = dateparser.parse(texto, languages=["pt"])

        if not data_hora:
            await update.message.reply_text("❌ Não entendi a data e hora. Pode tentar de outra forma?")
            return

        data_str = data_hora.strftime("%Y-%m-%d")
        hora_str = data_hora.strftime("%H:%M:%S")

        start_time = data_hora.isoformat()
        end_time = (data_hora + timedelta(hours=1)).isoformat()

        titulo = "Reunião agendada por voz"

        link = add_event(titulo, start_time, end_time)
        if not link:
            await update.message.reply_text("❌ Falha ao criar evento no Google Calendar.")
            return

        evento_data = {
            "titulo": titulo,
            "data": data_str,
            "hora": hora_str,
            "link": link,
            "notificado": False,
            "lembrete": 30
        }

        salvar_evento(evento_data)

        msg = f"✅ Reunião marcada!\n📅 {data_str} às {hora_str}\n🔗 {link}"
        await update.message.reply_text(msg)
        send_whatsapp_message(msg)

    except Exception as e:
        await update.message.reply_text("❌ Erro ao processar o agendamento.")
        print("Erro agendar por voz:", e)



