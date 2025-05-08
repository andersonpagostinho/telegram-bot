import os
import asyncio
from telegram import Update, Bot
from telegram.ext import ContextTypes
from datetime import datetime, time
from uuid import uuid4
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.formatters import formatar_horario_atual
from pytz import timezone
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_subcolecao,
    buscar_dados,
    deletar_dado_em_path,
    buscar_dado_em_path,
    atualizar_dado_em_path
)
from utils.plan_utils import verificar_pagamento, verificar_acesso_modulo
from utils.tts_utils import responder_em_audio

FUSO_BR = timezone("America/Sao_Paulo")

# ✅ /followup Fulano da Loja X
async def criar_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    if not context.args:
        await update.message.reply_text("⚠️ Informe o nome do cliente para o follow-up.\nEx: /followup Fulano da Loja X")
        return

    nome_cliente = ' '.join(context.args)
    user_id = str(update.message.from_user.id)
    followup_id = str(uuid4())

    dados = {
        "nome_cliente": nome_cliente,
        "status": "pendente",
        "criado_em": datetime.now(FUSO_BR).isoformat()
    }

    sucesso = await salvar_dado_em_path(f"Usuarios/{user_id}/FollowUps/{followup_id}", dados)

    if sucesso:
        await update.message.reply_text(f"📌 Follow-up com *{nome_cliente}* foi registrado com sucesso!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Erro ao salvar o follow-up.")

# ✅ /meusfollowups
async def listar_followups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    followups = await buscar_subcolecao(f"Usuarios/{user_id}/FollowUps")

    if not followups:
        await update.message.reply_text("📭 Nenhum follow-up encontrado.")
        return

    resposta = "📋 *Seus Follow-ups:*\n\n"
    for item in followups.values():
        nome = item.get("nome_cliente", "Sem nome")
        status = item.get("status", "pendente")
        criado = item.get("criado_em", "")[:16].replace("T", " ")
        resposta += f"🔹 *{nome}* — _{status}_\n🕓 Criado: {criado}\n\n"

    await update.message.reply_text(resposta, parse_mode="Markdown")

# ✅ /concluirfollowup Fulano da Loja X
async def concluir_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    if not context.args:
        await update.message.reply_text("⚠️ Informe o nome do cliente para concluir o follow-up.\nEx: /concluirfollowup Fulano da Loja X")
        return

    nome_cliente = ' '.join(context.args).lower()
    user_id = str(update.message.from_user.id)
    followups = await buscar_subcolecao(f"Usuarios/{user_id}/FollowUps")

    for fid, item in followups.items():
        if nome_cliente in item.get("nome_cliente", "").lower():
            await deletar_dado_em_path(f"Usuarios/{user_id}/FollowUps/{fid}")
            await update.message.reply_text(f"✅ Follow-up com *{item['nome_cliente']}* concluído e removido!", parse_mode="Markdown")
            return

    await update.message.reply_text("❌ Nenhum follow-up encontrado com esse nome.")

# ✅ Criar follow-up via GPT com data/hora opcional
async def criar_followup_por_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, dados: dict):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    from services.notificacao_service import criar_notificacao_agendada
    from datetime import datetime

    nome_cliente = dados.get("nome_cliente") or dados.get("nome") or dados.get("cliente")
    data = dados.get("data")  # formato esperado: YYYY-MM-DD
    hora = dados.get("hora")  # formato esperado: HH:MM

    if not nome_cliente:
        await update.message.reply_text("❌ Não entendi o nome do cliente para o follow-up.")
        return

    user_id = str(update.message.from_user.id)
    followup_id = str(uuid4())

    dados_followup = {
        "nome_cliente": nome_cliente,
        "status": "pendente",
        "criado_em": datetime.now(FUSO_BR).isoformat()
    }

    if data and hora:
        dados_followup["data"] = data
        dados_followup["hora"] = hora

    # 🔔 Agendar notificação, se data e hora forem válidas
    if data and hora:
        try:
            await criar_notificacao_agendada(
                user_id=user_id,
                descricao=f"Follow-up com {nome_cliente}",
                data=data,
                hora_inicio=hora,
                canal="telegram",
                minutos_antes=30
            )
        except Exception as e:
            print(f"⚠️ Erro ao agendar follow-up: {e}")

    sucesso = await salvar_dado_em_path(f"Usuarios/{user_id}/FollowUps/{followup_id}", dados_followup)

    if sucesso:
        await update.message.reply_text(
            f"📌 Follow-up com *{nome_cliente}* foi registrado com sucesso!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Erro ao salvar o follow-up.")

# ✅ Concluir follow-up via GPT
async def concluir_followup_por_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, dados: dict):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    nome_cliente = dados.get("nome_cliente") or dados.get("nome") or dados.get("cliente")
    if not nome_cliente:
        await update.message.reply_text("❌ Não entendi o nome do cliente para concluir o follow-up.")
        return

    nome_cliente = nome_cliente.lower()
    user_id = str(update.message.from_user.id)
    followups = await buscar_subcolecao(f"Usuarios/{user_id}/FollowUps")

    for fid, item in followups.items():
        if nome_cliente in item.get("nome_cliente", "").lower():
            await deletar_dado_em_path(f"Usuarios/{user_id}/FollowUps/{fid}")
            await update.message.reply_text(f"✅ Follow-up com *{item['nome_cliente']}* foi concluído e removido!", parse_mode="Markdown")
            return

    await update.message.reply_text("❌ Nenhum follow-up encontrado com esse nome.")

# ✅ Verificar horários configurados
async def verificar_avisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    config = await buscar_dado_em_path(f"Usuarios/{user_id}/configuracoes/avisos")
    horarios = config.get("horarios", []) if config else []

    if horarios:
        msg = "⏰ Seus lembretes estão configurados para:\n\n" + "\n".join(f"• {h}" for h in horarios)
    else:
        msg = "⏰ Você está usando os horários *padrão* de lembretes:\n\n• 09:00\n• 13:00\n• 17:00"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ✅ Atualizar horários de lembrete
async def configurar_avisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    if not context.args or len(context.args) > 3:
        await update.message.reply_text("⚠️ Use: /configuraravisos HH:MM HH:MM HH:MM")
        return

    horarios = context.args
    for h in horarios:
        try:
            datetime.strptime(h, "%H:%M")
        except ValueError:
            await update.message.reply_text(f"❌ Horário inválido: {h}")
            return

    path = f"Usuarios/{update.message.from_user.id}/configuracoes/avisos"
    sucesso = await atualizar_dado_em_path(path, {"horarios": horarios})

    if sucesso:
        await update.message.reply_text("✅ Horários de aviso atualizados com sucesso:\n\n" + "\n".join(f"• {h}" for h in horarios), parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Ocorreu um erro ao salvar os horários.")

# ✅ Lembrar follow-ups pendentes
async def rotina_lembrete_followups(user_id=None):
    user_ids = [user_id] if user_id else [str(u["id"]) for u in await buscar_dados("Usuarios") if u.get("id")]

    for uid in user_ids:
        followups = await buscar_subcolecao(f"Usuarios/{uid}/FollowUps")
        pendentes = [f for f in followups.values() if f.get("status") == "pendente"]

        if pendentes:
            mensagem = f"📌 Você tem {len(pendentes)} follow-up(s) pendente(s):\n"
            for f in pendentes[:3]:
                mensagem += f"- {f.get('nome_cliente')}\n"

            try:
                bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
                await bot.send_message(chat_id=int(uid), text=mensagem)
                await responder_em_audio_fake(uid, mensagem)
            except Exception as e:
                print(f"❌ Erro ao notificar {uid}: {e}")

# ✅ Simula resposta em áudio (sem update real)
async def responder_em_audio_fake(user_id, texto):
    class FakeUpdate:
        def __init__(self, uid): self.message = type("msg", (), {"from_user": type("user", (), {"id": uid})})()
    class FakeContext: user_data = {}
    await responder_em_audio(FakeUpdate(user_id), FakeContext(), texto)

# ✅ Inicializa o agendador de follow-ups
def start_followup_scheduler():
    scheduler = AsyncIOScheduler(timezone=FUSO_BR)

    async def configurar_agendamentos():
        usuarios = await buscar_dados("Usuarios")
        user_ids = [str(u["id"]) for u in usuarios if u.get("id")]

        for uid in user_ids:
            for hora in ["09:00", "13:00", "17:00"]:
                h, m = map(int, hora.split(":"))
                scheduler.add_job(
                    rotina_lembrete_followups,
                    "cron",
                    args=[uid],
                    hour=h,
                    minute=m,
                    id=f"followup_{uid}_{hora}",
                    replace_existing=True
                )

    asyncio.get_event_loop().create_task(configurar_agendamentos())
    scheduler.start()
