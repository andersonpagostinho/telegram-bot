# handlers/event_handler.py 

import logging
import dateparser
import re
from datetime import datetime, time, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from utils.tts_utils import responder_em_audio
from utils.formatters import formatar_horario_atual, gerar_sugestoes_de_horario

from services.firebase_service_async import (
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
    sucesso = await salvar_cliente(user_id, {"calendar_id": calendar_id})

    if sucesso:
        await responder_em_audio(update, context, f"✅ Google Calendar configurado com sucesso.")
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
    cliente = await buscar_cliente(user_id)
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
    time_min = datetime.combine(start_time.date(), time(8, 0)).isoformat() + "-03:00"
    time_max = datetime.combine(start_time.date(), time(18, 0)).isoformat() + "-03:00"

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

    await salvar_dado_em_path(
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

    await update.message.reply_text(f"📅 Evento criado com sucesso!\n🗓️ {data} ⏰ {hora_inicio} às {hora_fim}\n🔗 {event_link}")


async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)
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
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe a descrição do evento para confirmar.")
        return

    user_id = str(update.message.from_user.id)
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    for event_id, evento in eventos.items():
        if descricao.lower() in f"{evento['descricao']} {evento['data']} {evento['hora_inicio']} {evento['hora_fim']}".lower():
            cliente = await buscar_cliente(user_id)
            calendar_id = cliente.get("calendar_id")
            if not calendar_id:
                await update.message.reply_text("❌ Google Calendar ID não configurado.")
                return

            updated_event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            updated_event["status"] = "confirmed"
            service.events().update(calendarId=calendar_id, eventId=event_id, body=updated_event).execute()

            evento["confirmado"] = True
            await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento)
            await responder_em_audio(update, context, f"✅ Reunião confirmada: {evento['descricao']}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")


async def confirmar_presenca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe o nome do evento para confirmar presença.")
        return

    user_id = str(update.message.from_user.id)
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    for event_id, evento in eventos.items():
        if evento["descricao"].lower() == descricao.lower():
            evento["confirmado"] = True
            await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento)
            await responder_em_audio(update, context, f"✅ Presença confirmada para: {descricao}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")


async def debug_eventos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

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

    if await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento_data):
        await responder_em_audio(update, context, "✅ Evento de teste salvo com sucesso.")
    else:
        await update.message.reply_text("❌ Erro ao salvar evento de teste.")

    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")
    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado.")
        return

    resposta = "📂 Eventos salvos:\n"
    for eid, ev in eventos.items():
        resposta += f"\n📌 {eid}: {ev.get('descricao')} ({ev.get('data')} {ev.get('hora_inicio')} - {ev.get('hora_fim')})"

    await responder_em_audio(update, context, resposta)


async def add_evento_por_voz(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    try:
        texto = texto.lower()
        texto = texto.replace("marcar reunião", "")
        texto = texto.replace("agendar reunião", "")
        texto = texto.replace("às", "as").strip()

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

        user_id = str(update.message.from_user.id)
        cliente = await buscar_cliente(user_id)
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

        await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{created_event['id']}", evento_data)
        msg = f"✅ Reunião marcada para {data_str} às {hora_str}."
        await responder_em_audio(update, context, msg)

    except Exception as e:
        await update.message.reply_text("❌ Erro ao processar o agendamento por voz.")
        print("Erro ao agendar por voz:", e)

from utils.formatters import gerar_sugestoes_de_horario  # Criaremos esse utilitário

# ✅ Cdefinição de duração de eventos
async def detectar_e_definir_duracao(update: Update, context: ContextTypes.DEFAULT_TYPE, mensagem: str):
    match = re.search(r'(\d{1,3})\s*(min|minuto|minutos)', mensagem.lower())

    if match:
        minutos = int(match.group(1))

        if 15 <= minutos <= 180:
            user_id = str(update.message.from_user.id)
            await salvar_dado_em_path(f"Clientes/{user_id}/configuracoes", {"duracao_padrao_evento": minutos})

            await update.message.reply_text(f"✅ Duração dos eventos ajustada para {minutos} minutos.")
            return True  # sinaliza que tratou

        else:
            await update.message.reply_text("⚠️ Por favor, escolha uma duração entre 15 e 180 minutos.")
            return True

    return False  # sinaliza que não detectou comando

# ✅ Criar evento via GPT com dados estruturados
async def add_evento_por_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, dados: dict):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)

    try:  # 👈 Começa aqui o try

        # --- Tudo o que vem depois vai dentro do try ---
        descricao = dados.get("descricao", "Evento sem título")
        data_hora_str = dados.get("data_hora")

        if not descricao or not data_hora_str:
            await update.message.reply_text("❌ Dados insuficientes para criar o evento.")
            return

        try:
            data_hora = datetime.fromisoformat(data_hora_str)
        except ValueError:
            await update.message.reply_text("❌ Formato de data/hora inválido.")
            return

        # Buscar duração configurada
        config = await buscar_dados(f"Clientes/{user_id}/configuracoes")
        duracao = config.get("duracao_padrao_evento", 60)

        start_time = data_hora
        end_time = start_time + timedelta(minutes=duracao)
        data = start_time.strftime("%Y-%m-%d")
        hora_inicio = start_time.strftime("%H:%M")
        hora_fim = end_time.strftime("%H:%M")

        cliente = await buscar_cliente(user_id)
        calendar_id = cliente.get("calendar_id") if cliente else None

        if not calendar_id:
            await update.message.reply_text("❌ Google Calendar ID não configurado.")
            return

        # Verificar conflitos
        time_min = datetime.combine(start_time.date(), time(8, 0)).isoformat() + "-03:00"
        time_max = datetime.combine(start_time.date(), time(18, 0)).isoformat() + "-03:00"
        eventos = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime"
        ).execute().get("items", [])

        ocupados = [(datetime.fromisoformat(ev["start"]["dateTime"]).replace(tzinfo=None),
                     datetime.fromisoformat(ev["end"]["dateTime"]).replace(tzinfo=None))
                    for ev in eventos]

        conflito = any(start_time < fim and end_time > inicio for inicio, fim in ocupados)

        if conflito:
            sugestoes = gerar_sugestoes_de_horario(start_time, ocupados, duracao_evento_minutos=duracao)
            if sugestoes:
                sugestoes_formatadas = '\n'.join([f"🔄 {s}" for s in sugestoes])
                await update.message.reply_text(
                    f"⚠️ Já existe um evento nesse horário.\n\nSugestões de horários alternativos:\n{sugestoes_formatadas}\n\nResponda com um desses horários para reagendar."
                )
            else:
                await update.message.reply_text("⚠️ Já existe um evento nesse horário e não há horários livres disponíveis hoje.")
            return  # ⛔️ Sai daqui e não continua

        # Criar evento
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

        await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento_data)

        mensagem_gpt = f"{descricao.capitalize()} marcada com sucesso para {data} às {hora_inicio}."
        await responder_em_audio(update, context, mensagem_gpt)
        await update.message.reply_text(f"{mensagem_gpt}\n🔗 {event_link}")

    except Exception as e:
        print("[GPT Evento] Erro:", e)
        import traceback
        print(traceback.format_exc())
        await update.message.reply_text("❌ Erro inesperado ao processar o evento.")
