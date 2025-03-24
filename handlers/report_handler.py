import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import buscar_dados, buscar_subcolecao, buscar_cliente
from handlers.email_handler import enviar_email  # Usa o que você já tem
from utils.plan_utils import verificar_acesso_modulo, verificar_pagamento  # ✅ NOVO

logger = logging.getLogger(__name__)

# ✅ Comando /relatorio_diario
async def relatorio_diario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    user_id = str(update.message.from_user.id)
    hoje = datetime.now().date().isoformat()

    tarefas = buscar_dados("Tarefas")
    tarefas_hoje = [t for t in tarefas if hoje in t.get("data", hoje)]  # adapta se tiver campo data

    eventos = buscar_subcolecao(f"Clientes/{user_id}/Eventos")
    eventos_hoje = [e for e in eventos.values() if e.get("data") == hoje]

    resposta = f"📊 *Relatório de Hoje ({hoje}):*\n\n"
    resposta += f"📝 Tarefas: {len(tarefas_hoje)}\n"
    resposta += f"📅 Eventos: {len(eventos_hoje)}\n"

    if tarefas_hoje:
        resposta += "\n📝 *Tarefas do dia:*\n" + "\n".join(f"- {t['descricao']}" for t in tarefas_hoje)
    if eventos_hoje:
        resposta += "\n\n📅 *Eventos do dia:*\n" + "\n".join(f"- {e['descricao']} ({e['hora_inicio']} - {e['hora_fim']})" for e in eventos_hoje)

    await update.message.reply_text(resposta, parse_mode="Markdown")

# ✅ Comando /relatorio_semanal
async def relatorio_semanal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return


    user_id = str(update.message.from_user.id)
    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())

    eventos = buscar_subcolecao(f"Clientes/{user_id}/Eventos")
    eventos_semana = [
        e for e in eventos.values()
        if "data" in e and inicio_semana <= datetime.fromisoformat(e["data"]).date() <= hoje
    ]

    tarefas = buscar_dados("Tarefas")  # Adaptar se quiser por usuário
    tarefas_semana = tarefas  # se quiser por data: [t for t in tarefas if ... ]

    resposta = f"📈 *Relatório Semanal ({inicio_semana} → {hoje}):*\n\n"
    resposta += f"📝 Tarefas registradas: {len(tarefas_semana)}\n"
    resposta += f"📅 Eventos registrados: {len(eventos_semana)}\n"

    await update.message.reply_text(resposta, parse_mode="Markdown")

# ✅ Comando /enviar_relatorio_email
async def enviar_relatorio_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    user_id = str(update.message.from_user.id)
    cliente_info = buscar_cliente(user_id)

    if not cliente_info or "email" not in cliente_info:
        await update.message.reply_text("⚠️ Nenhum e-mail configurado para sua conta.")
        return

    email_destino = cliente_info["email"]

    assunto = "📊 Seu Relatório de Produtividade"
    mensagem = (
        "Olá!\n\nSegue o resumo da sua semana:\n"
        "- X tarefas cadastradas\n"
        "- Y eventos no calendário\n\n"
        "Até logo!"
    )

    sucesso = enviar_email(email_destino, assunto, mensagem)

    if sucesso:
        await update.message.reply_text(f"📧 Relatório enviado com sucesso para {email_destino}")
    else:
        await update.message.reply_text("❌ Erro ao enviar o relatório por e-mail.")
