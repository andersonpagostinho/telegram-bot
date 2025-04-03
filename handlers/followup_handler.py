import os
import asyncio
from telegram import Update, Bot
from telegram.ext import ContextTypes
from datetime import datetime, time
from uuid import uuid4
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from services.firebase_service import (
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

    sucesso = salvar_dado_em_path(f"Usuarios/{user_id}/FollowUps/{followup_id}", dados)

    if sucesso:
        await update.message.reply_text(f"📌 Follow-up com *{nome_cliente}* foi registrado com sucesso!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Erro ao salvar o follow-up.")

# ✅ /meusfollowups
async def listar_followups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[DEBUG] Entrou na função listar_followups")

    if not await verificar_pagamento(update, context):
        print("[DEBUG] Entrou na função listar_followups")
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        print("[DEBUG] Entrou na função listar_followups")
        return

    user_id = str(update.message.from_user.id)
    followups = buscar_subcolecao(f"Usuarios/{user_id}/FollowUps")

    print(f"[DEBUG] followups recebidos: {followups}")

    if not followups or len(followups) == 0:
        await update.message.reply_text("📭 Nenhum follow-up encontrado.")
        print(f"[DEBUG] Nenhum follow-up encontrado para o usuário {user_id}")
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
    followups = buscar_subcolecao(f"Usuarios/{user_id}/FollowUps")

    encontrado = False
    for fid, item in followups.items():
        if nome_cliente in item.get("nome_cliente", "").lower():
            deletar_dado_em_path(f"Usuarios/{user_id}/FollowUps/{fid}")
            await update.message.reply_text(f"✅ Follow-up com *{item['nome_cliente']}* concluído e removido!", parse_mode="Markdown")
            encontrado = True
            break

    if not encontrado:
        await update.message.reply_text("❌ Nenhum follow-up encontrado com esse nome.")

# ✅ Rotina para lembrar follow-ups pendentes (todos os usuários)
async def rotina_lembrete_followups(user_id=None):
    print("⏰ Executando lembrete de follow-ups...")

    user_ids = [user_id] if user_id else [str(c["id"]) for c in buscar_dados("Usuarios") or [] if c.get("id")]

    for uid in user_ids:
        followups = buscar_subcolecao(f"Usuarios/{uid}/FollowUps")
        pendentes = [f for f in followups.values() if f.get("status") == "pendente"]

        if not pendentes:
            continue

        mensagem = f"📌 Você tem {len(pendentes)} follow-up(s) pendente(s):\n"
        for f in pendentes[:3]:
            mensagem += f"- {f.get('nome_cliente')}\n"

        try:
            bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
            await bot.send_message(chat_id=int(uid), text=mensagem)
            await responder_em_audio_fake(uid, mensagem)
        except Exception as e:
            print(f"❌ Erro ao notificar {uid}: {e}")

# ✅ /configuraravisos 09:00 13:00 17:00
async def configurar_avisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    if not context.args or len(context.args) > 3:
        await update.message.reply_text("⚠️ Use: /configuraravisos HH:MM HH:MM HH:MM\nEx: /configuraravisos 09:00 13:00 17:00")
        return

    horarios = context.args
    user_id = str(update.message.from_user.id)

    for h in horarios:
        try:
            datetime.strptime(h, "%H:%M")
        except ValueError:
            await update.message.reply_text(f"❌ Horário inválido: {h}. Use o formato HH:MM.")
            return

    path = f"Usuarios/{user_id}/configuracoes/avisos"
    dados = {"horarios": horarios}

    print(f"[DEBUG] Salvando horários personalizados para {user_id}")
    sucesso = atualizar_dado_em_path(path, dados)

    if sucesso:
        await update.message.reply_text(
            "✅ Horários de aviso atualizados com sucesso:\n\n" + "\n".join(f"• {h}" for h in horarios),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Ocorreu um erro ao salvar os horários. Tente novamente.")

# ✅ /verificaravisos
async def verificar_avisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    try:
        print(f"🔍 [DEBUG] Buscando configurações em: Usuarios/{user_id}/configuracoes")
        config = buscar_dado_em_path(f"Usuarios/{user_id}/configuracoes")
        print(f"📦 [DEBUG] Config retornada: {config}")

        horarios = config.get("avisos", {}).get("horarios", []) if config else []

        if horarios:
            msg = "⏰ Seus lembretes estão configurados para:\n\n" + "\n".join(f"• {h}" for h in horarios)
        else:
            msg = "⏰ Você está usando os horários *padrão* de lembretes:\n\n• 09:00\n• 13:00\n• 17:00"

        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("❌ Erro ao verificar os horários de aviso.")
        print(f"[❌ ERRO EM /verificaravisos] {e}")

# ✅ Envia áudio mesmo sem Update real
async def responder_em_audio_fake(user_id, texto):
    class FakeUpdate:
        def __init__(self, uid): self.message = type("msg", (), {"from_user": type("user", (), {"id": uid})})()
    class FakeContext: user_data = {}
    await responder_em_audio(FakeUpdate(user_id), FakeContext(), texto)
