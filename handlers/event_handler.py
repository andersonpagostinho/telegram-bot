# handlers/event_handler.py 

import logging
import dateparser
import re
import io
from openpyxl import Workbook
from telegram import InputFile
from datetime import datetime, time, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from utils.tts_utils import responder_em_audio
from utils.formatters import formatar_horario_atual, gerar_sugestoes_de_horario
from services.excel_service import gerar_excel_agenda
from services.notificacao_service import criar_notificacao_agendada

from services.firebase_service_async import (
    salvar_cliente,
    buscar_cliente,
    buscar_dados,
    salvar_dado_em_path,
    buscar_subcolecao,
    salvar_dados,
    atualizar_dado_em_path,
    buscar_dado_em_path
)
from services.event_service_async import salvar_evento, buscar_eventos_por_intervalo
from utils.plan_utils import verificar_acesso_modulo, verificar_pagamento 

logger = logging.getLogger(__name__)

async def add_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    if len(context.args) < 4:
        await update.message.reply_text(
            "⚠️ Uso correto: /agenda <Descrição> <AAAA-MM-DD> <HH:MM início> <HH:MM fim>\n"
            "Exemplo: /agenda Reunião 2025-03-25 14:00 15:00"
        )
        return

    descricao = context.args[0]
    data = context.args[1]
    hora_inicio = context.args[2]
    hora_fim = context.args[3]
    user_id = str(update.message.from_user.id)

    try:
        inicio = datetime.fromisoformat(f"{data}T{hora_inicio}")
        fim = datetime.fromisoformat(f"{data}T{hora_fim}")
        duracao = fim - inicio
        duracao_minutos = int(duracao.total_seconds() / 60)
    except Exception:
        await update.message.reply_text("⚠️ Data ou hora em formato inválido. Use o formato 2025-03-25 14:00.")
        return

    # 🔍 Buscar eventos do dia
    eventos_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=inicio.date())

    # 🔄 Verificar conflitos com base nos horários
    conflitos = []
    for ev in eventos_dia:
        match = re.search(r"em \d{2}/\d{2} às (\d{2}:\d{2})", ev)
        if not match:
            continue

        hora_ev = match.group(1)
        inicio_existente = datetime.fromisoformat(f"{data}T{hora_ev}")
        fim_existente = inicio_existente + timedelta(minutes=duracao_minutos)

        if inicio < fim_existente and fim > inicio_existente:
            conflitos.append((inicio_existente, fim_existente))

    if conflitos:
        sugestoes = []
        atual = datetime.combine(inicio.date(), time(8, 0))
        limite = datetime.combine(inicio.date(), time(18, 0))

        while atual + duracao <= limite:
            livre = all(not (atual < f and atual + duracao > i) for i, f in conflitos)
            if livre:
                sugestoes.append(f"{atual.strftime('%H:%M')} - {(atual + duracao).strftime('%H:%M')}")
                if len(sugestoes) >= 3:
                    break
            atual += timedelta(minutes=15)

        resposta = "⚠️ Já existe um evento nesse horário.\n"
        resposta += "\n".join(f"🔄 Alternativa: {s}" for s in sugestoes) if sugestoes else "❌ Nenhum horário alternativo disponível."
        await update.message.reply_text(resposta)
        return

    # ✅ Salvar evento no Firebase
    evento = {
        "descricao": descricao,
        "data": data,
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "duracao": duracao_minutos,
        "confirmado": False,
        "link": ""
    }

    sucesso = await salvar_evento(user_id, evento)
    if sucesso:
        await update.message.reply_text(
            f"📅 Evento criado com sucesso!\n🗓️ {data} ⏰ {hora_inicio} às {hora_fim}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Ocorreu um erro ao tentar salvar o evento.")

async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    hoje = datetime.now().date()

    eventos = await buscar_eventos_por_intervalo(user_id, dia_especifico=hoje)

    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado para hoje.")
        return

    resposta = "📅 Eventos de hoje:\n" + "\n".join(f"- {ev}" for ev in eventos)
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
        texto_evento = f"{evento.get('descricao', '')} {evento.get('data', '')} {evento.get('hora_inicio', '')} {evento.get('hora_fim', '')}".lower()
        if descricao.lower() in texto_evento:
            evento["confirmado"] = True
            await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento)
            await responder_em_audio(update, context, f"✅ Reunião confirmada: {evento['descricao']}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")

async def confirmar_presenca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    descricao = ' '.join(context.args).lower()
    if not descricao:
        await update.message.reply_text("⚠️ Informe o nome do evento para confirmar presença.")
        return

    user_id = str(update.message.from_user.id)
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    for event_id, evento in eventos.items():
        if descricao in evento.get("descricao", "").lower():
            evento["confirmado"] = True
            await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}", evento)
            await responder_em_audio(update, context, f"✅ Presença confirmada para: {evento['descricao']}")
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
    if not await verificar_acesso_modulo(update, context): return

    if context.chat_data.get("evento_via_gpt"):
        return  # evitar duplicação

    try:
        texto = texto.lower().replace("marcar reunião", "").replace("agendar reunião", "").replace("às", "as").strip()
        data_hora = dateparser.parse(texto, languages=["pt"])
        if not data_hora:
            await update.message.reply_text("❌ Não entendi a data e hora. Pode tentar de outra forma?")
            return

        user_id = str(update.message.from_user.id)
        start_time = data_hora
        end_time = start_time + timedelta(hours=1)
        duracao = 60
        titulo = "Reunião agendada por voz"

        # 🔍 Verifica conflitos usando eventos do Firebase
        eventos = await buscar_eventos_por_intervalo(user_id, dia_especifico=start_time.date())
        ocupados = []

        for ev in eventos:
            try:
                ev_data = datetime.strptime(ev.get("data"), "%Y-%m-%d").date()
                ev_inicio = datetime.strptime(f"{ev['data']} {ev['hora_inicio']}", "%Y-%m-%d %H:%M")
                ev_fim = datetime.strptime(f"{ev['data']} {ev['hora_fim']}", "%Y-%m-%d %H:%M")
                ocupados.append((ev_inicio, ev_fim))
            except:
                continue

        conflito = any(start_time < fim and end_time > inicio for inicio, fim in ocupados)

        if conflito:
            sugestoes = gerar_sugestoes_de_horario(start_time, ocupados)
            resposta = "⚠️ Já existe um evento nesse horário.\n"
            if sugestoes:
                resposta += "\nSugestões de horário:\n" + "\n".join([f"🔄 {s}" for s in sugestoes])
            else:
                resposta += "\n❌ Nenhum horário alternativo disponível."
            await update.message.reply_text(resposta)
            return

        # ✅ Salva o evento no Firebase
        evento_data = {
            "descricao": titulo,
            "data": start_time.strftime("%Y-%m-%d"),
            "hora_inicio": start_time.strftime("%H:%M"),
            "hora_fim": end_time.strftime("%H:%M"),
            "duracao": duracao,
            "confirmado": False,
            "link": ""
        }

        sucesso = await salvar_evento(user_id, evento_data)
        if sucesso:
            msg = f"✅ Reunião marcada para {start_time.strftime('%d/%m/%Y')} às {start_time.strftime('%H:%M')}."
            await responder_em_audio(update, context, msg)
        else:
            await update.message.reply_text("❌ Não foi possível salvar o evento.")

    except Exception as e:
        print(f"❌ Erro ao agendar por voz: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao tentar agendar a reunião.")

    finally:
        context.chat_data.pop("evento_via_gpt", None)

# ✅ definição de duração de eventos
async def detectar_e_definir_duracao(update: Update, context: ContextTypes.DEFAULT_TYPE, mensagem: str):
    match = re.search(r'(\d{1,3})\s*(min|minuto|minutos)', mensagem.lower())

    if match:
        minutos = int(match.group(1))

        if 15 <= minutos <= 180:
            user_id = str(update.message.from_user.id)
            await atualizar_dado_em_path(f"Clientes/{user_id}/configuracoes", {"duracao_padrao_evento": minutos})

            await update.message.reply_text(f"✅ Duração dos eventos ajustada para {minutos} minutos.")
            return True

        else:
            await update.message.reply_text("⚠️ Por favor, escolha uma duração entre 15 e 180 minutos.")
            return True

    return False

# ✅ Criar evento via GPT com verificação de conflito
async def add_evento_por_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, dados: dict):
    if not await verificar_pagamento(update, context): return False
    if not await verificar_acesso_modulo(update, context, "secretaria"): return False

    if context.chat_data.get("evento_via_gpt"):
        return False  # evitar duplicação
    context.chat_data["evento_via_gpt"] = True

    try:
        descricao = dados.get("descricao", "Evento sem título")
        data_hora_str = dados.get("data_hora")  # ISO string
        duracao_minutos = dados.get("duracao", 60)

        if not descricao or not data_hora_str:
            await update.message.reply_text("❌ Dados insuficientes para criar o evento.")
            return False

        try:
            start_time = datetime.fromisoformat(data_hora_str)
        except ValueError:
            await update.message.reply_text("❌ Formato de data/hora inválido.")
            return False

        end_time = start_time + timedelta(minutes=duracao_minutos)
        user_id = str(update.message.from_user.id)

        # 🔍 Buscar eventos existentes do dia
        eventos_do_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=start_time.date())

        # ⛔ Verificar conflitos
        ocupados = []
        for ev_texto in eventos_do_dia:
            match = re.search(r"em (\d{2}/\d{2}) às (\d{2}:\d{2})", ev_texto)
            if not match:
                continue
            hora = match.group(2)
            inicio = datetime.strptime(f"{start_time.date()} {hora}", "%Y-%m-%d %H:%M")
            fim = inicio + timedelta(minutes=duracao_minutos)
            ocupados.append((inicio, fim))

        conflito = any(start_time < fim and end_time > inicio for inicio, fim in ocupados)

        if conflito:
            sugestoes = gerar_sugestoes_de_horario(start_time, ocupados, max_sugestoes=3)
            if sugestoes:
                sugestoes_formatadas = '\n'.join([f"🔄 {s}" for s in sugestoes])
                await update.message.reply_text(
                    f"⚠️ Já existe um evento nesse horário.\n\nSugestões de horários alternativos:\n{sugestoes_formatadas}"
                )
            else:
                await update.message.reply_text("⚠️ Já existe um evento nesse horário e não há horários livres disponíveis.")
            return False

        evento_data = {
            "descricao": descricao,
            "data": start_time.strftime("%Y-%m-%d"),
            "hora_inicio": start_time.strftime("%H:%M"),
            "hora_fim": end_time.strftime("%H:%M"),
            "duracao": duracao_minutos,
            "confirmado": False,
            "link": ""
        }

        await salvar_evento(user_id, evento_data)

        mensagem = (
            f"📝 {descricao.capitalize()}\n"
            f"📅 {start_time.strftime('%d/%m/%Y')} às {start_time.strftime('%H:%M')}"
       )

        # Adiciona cabeçalho só se for de e-mail
        if context.user_data.get("origem_email_detectado"):
            mensagem = "📬 Um novo evento foi criado com base em um e-mail importante:\n\n" + mensagem

        context.user_data.pop("origem_email_detectado", None)

        # Telegram
        try:
            from main import application
            await application.bot.send_message(chat_id=user_id, text=mensagem)
        except Exception as e:
            print(f"❌ Erro ao enviar notificação Telegram: {e}")

        # WhatsApp (se houver)
        try:
            from utils.whatsapp_utils import enviar_mensagem_whatsapp
            await enviar_mensagem_whatsapp(user_id, mensagem)
        except Exception as e:
            print(f"❌ Erro ao enviar WhatsApp: {e}")

        mensagem_gpt = f"{descricao.capitalize()} marcada com sucesso para {start_time.strftime('%d/%m/%Y')} às {start_time.strftime('%H:%M')}."

        # 🔊 Limpeza segura para TTS
        mensagem_gpt_limpa = re.sub(r"[^\w\s,.:áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]", "", mensagem_gpt)

        await responder_em_audio(update, context, mensagem_gpt_limpa)
        await update.message.reply_text(mensagem_gpt)

        return True

    except Exception as e:
        print(f"❌ Erro inesperado em add_evento_por_gpt: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao tentar criar o evento.")
        return False

    finally:
        context.chat_data.pop("evento_via_gpt", None)

async def enviar_agenda_excel(update: Update, context: ContextTypes.DEFAULT_TYPE, intervalo: str = "hoje"):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)

    if intervalo == "hoje":
        eventos = await buscar_eventos_por_intervalo(user_id, dias=0)
    elif intervalo == "amanha":
        eventos = await buscar_eventos_por_intervalo(user_id, dias=1)
    elif intervalo == "semana":
        eventos = await buscar_eventos_por_intervalo(user_id, semana=True)
    else:
        eventos = await buscar_eventos_por_intervalo(user_id, dias=-365)

    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado para gerar a agenda.")
        await responder_em_audio(update, context, "Nenhum evento disponível para gerar a agenda.")
        return

    # 🧾 Gera planilha em memória
    excel_stream = await gerar_excel_agenda(user_id, eventos)

    await update.message.reply_document(
        document=InputFile(excel_stream, filename="agenda_neoagenda.xlsx"),
        caption="📎 Aqui está sua agenda exportada com sucesso."
    )

    await responder_em_audio(update, context, "Sua agenda em Excel foi gerada e enviada.")
