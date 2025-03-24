# handlers/event_handler.py

import logging
import dateparser
from datetime import datetime, time, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from services.firebase_service import (
    salvar_cliente,
    buscar_cliente,
    buscar_dados,
    salvar_dado_em_path,
    buscar_subcolecao,
    salvar_dados,
)
from config.google_config import get_calendar_service
from utils.plan_utils import verificar_acesso_modulo, verificar_pagamento  # ✅ Verifica acesso ao módulo

logger = logging.getLogger(__name__)

service = get_calendar_service()


async def configurar_google_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Use: /configurar_google_calendar <ID>")
        return

    user_id = str(update.message.from_user.id)
    calendar_id = context.args[0]
    sucesso = salvar_cliente(user_id, {"calendar_id": calendar_id})

    if sucesso:
        await update.message.reply_text(f"✅ Google Calendar ID configurado: {calendar_id}")
    else:
        await update.message.reply_text("❌ Erro ao salvar o ID no Firebase.")


async def add_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    if len(context.args) < 4:
        await update.message.reply_text(
            "⚠️ Uso correto: /agenda <Descrição> <AAAA-MM-DD> <HH:MM início> <HH:MM fim>\n"
            "Exemplo: /agenda Reunião 2025-03-25 14:00 15:00"
        )
        return

    descricao, data, hora_inicio, hora_fim = context.args[0], context.args[1], context.args[2], context.args[3]
    user_id = str(update.message.from_user.id)
    cliente = buscar_cliente(user_id)
    calendar_id = cliente.get("calendar_id") if cliente else None

    if not calendar_id:
        await update.message.reply_text("❌ Google Calendar ID não configurado.")
        return

    try:
        start_time = datetime.fromisoformat(f"{data}T{hora_inicio}")
        end_time = datetime.fromisoformat(f"{data}T{hora_fim}")
    except ValueError:
        await update.message.reply_text("⚠️ Data/hora inválida. Tente novamente.")
        return

    duration = end_time - start_time
    time_min = datetime.combine(start_time.date(), time(8, 0)).isoformat() + "Z"
    time_max = datetime.combine(start_time.date(), time(18, 0)).isoformat() + "Z"

    eventos = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime"
    ).execute().get("items", [])

    conflito = False
    ocupados = []

    for ev in eventos:
        ev_start = datetime.fromisoformat(ev["start"]["dateTime"]).replace(tzinfo=None)
        ev_end = datetime.fromisoformat(ev["end"]["dateTime"]).replace(tzinfo=None)
        ocupados.append((ev_start, ev_end))
        if start_time < ev_end and end_time > ev_start:
            conflito = True

    if conflito:
        sugestoes = []
        atual = datetime.combine(start_time.date(), time(8, 0))
        while atual + duration <= datetime.combine(start_time.date(), time(18, 0)):
            if all(not (atual < ev_end and (atual + duration) > ev_start) for ev_start, ev_end in ocupados):
                sugestoes.append(f"{atual.strftime('%H:%M')} - {(atual + duration).strftime('%H:%M')}")
                if len(sugestoes) == 3:
                    break
            atual += timedelta(minutes=15)

        resposta = "⚠️ Já existe um evento nesse horário.\n"
        resposta += "\n".join(f"🔄 Alternativa: {s}" for s in sugestoes) if sugestoes else "❌ Nenhum horário alternativo disponível."
        await update.message.reply_text(resposta)
        return

    event = {
        "summary": descricao,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "America/Sao_Paulo"},
    }

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    event_id = created_event["id"]
    event_link = created_event.get("htmlLink")

    salvar_dado_em_path(
        f"Clientes/{user_id}/Eventos/{event_id}",
        {
            "descricao": descricao,
            "event_id": event_id,
            "data": data,
            "hora_inicio": hora_inicio,
            "hora_fim": hora_fim,
            "confirmado": False,
            "link": event_link
        }
    )

    await update.message.reply_text(
        f"📅 Evento criado!\n\n**{descricao}**\n🗓️ {data} ⏰ {hora_inicio} às {hora_fim}\n🔗 [Abrir no Google Calendar]({event_link})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    user_id = str(update.message.from_user.id)
    cliente = buscar_cliente(user_id)
    calendar_id = cliente.get("calendar_id") if cliente else None

    if not calendar_id:
        await update.message.reply_text("❌ Google Calendar ID não configurado.")
        return

    now = datetime.utcnow().isoformat() + "Z"
    events = service.events().list(
        calendarId=calendar_id,
        timeMin=now,
        maxResults=5,
        singleEvents=True,
        orderBy="startTime"
    ).execute().get("items", [])

    if not events:
        await update.message.reply_text("📭 Nenhum evento encontrado.")
        return

    resposta = "📅 Próximos eventos:\n" + "\n".join(
        f"- {e['summary']} ({e['start'].get('dateTime', 'Sem horário')})" for e in events
    )
    await update.message.reply_text(resposta)


async def confirmar_reuniao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe a descrição do evento para confirmar.")
        return

    user_id = str(update.message.from_user.id)
    eventos = buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    for event_id, evento in eventos.items():
        if descricao.lower() in f"{evento['descricao']} {evento['data']} {evento['hora_inicio']} {evento['hora_fim']}".lower():
            cliente = buscar_cliente(user_id)
            calendar_id = cliente.get("calendar_id")
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


async def confirmar_presenca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe o nome do evento para confirmar presença.")
        return

    user_id = str(update.message.from_user.id)
    eventos = buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    for event_id, evento in eventos.items():
        if evento["descricao"].lower() == descricao.lower():
            evento["confirmado"] = True
            salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento)
            await update.message.reply_text(f"✅ Presença confirmada: {descricao}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")


async def debug_eventos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    user_id = str(update.message.from_user.id)
    event_id = "evento_debug"
    evento_data = {
        "descricao": "Evento de Teste via Bot",
        "data": "2025-03-30",
        "hora_inicio": "12:00",
        "hora_fim": "13:00",
        "confirmado": False,
        "link": "https://exemplo.com/evento-debug"
    }

    if salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento_data):
        await update.message.reply_text("✅ Evento de teste salvo com sucesso.")
    else:
        await update.message.reply_text("❌ Erro ao salvar evento de teste.")

    eventos = buscar_subcolecao(f"Clientes/{user_id}/Eventos")
    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado.")
        return

    resposta = "📂 Eventos salvos:\n"
    for eid, ev in eventos.items():
        resposta += f"\n📌 {eid}: {ev.get('descricao')} ({ev.get('data')} {ev.get('hora_inicio')} - {ev.get('hora_fim')})"

    await update.message.reply_text(resposta)


async def add_evento_por_voz(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    try:
        texto = texto.lower()
        texto = texto.replace("marcar reunião", "")
        texto = texto.replace("agendar reunião", "")
        texto = texto.replace("às", "as")
        texto = texto.strip()

        print(f"[DEBUG] Texto tratado para dateparser: {texto}")

        data_hora = dateparser.parse(texto, languages=["pt"])

        if not data_hora:
            await update.message.reply_text("❌ Não entendi a data e hora. Pode tentar de outra forma?")
            return

        data_str = data_hora.strftime("%Y-%m-%d")
        hora_str = data_hora.strftime("%H:%M")
        start_time = data_hora.isoformat()
        end_time = (data_hora + timedelta(hours=1)).isoformat()
        titulo = "Reunião agendada por voz"

        from config.google_config import get_calendar_service
        service = get_calendar_service()

        user_id = str(update.message.from_user.id)
        cliente = buscar_cliente(user_id)
        calendar_id = cliente.get("calendar_id") if cliente else None

        if not calendar_id:
            await update.message.reply_text("❌ Google Calendar ID não configurado.")
            return

        event = {
            "summary": titulo,
            "start": {"dateTime": start_time, "timeZone": "America/Sao_Paulo"},
            "end": {"dateTime": end_time, "timeZone": "America/Sao_Paulo"},
        }

        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        link = created_event.get("htmlLink")

        evento_data = {
            "descricao": titulo,
            "data": data_str,
            "hora_inicio": hora_str,
            "hora_fim": (data_hora + timedelta(hours=1)).strftime("%H:%M"),
            "confirmado": False,
            "link": link
        }

        salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{created_event['id']}", evento_data)

        msg = f"✅ Reunião marcada!\n📅 {data_str} às {hora_str}\n🔗 {link}"
        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text("❌ Erro ao processar o agendamento por voz.")
        print("Erro ao agendar por voz:", e)
