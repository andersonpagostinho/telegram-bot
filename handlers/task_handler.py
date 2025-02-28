import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import salvar_tarefa

logger = logging.getLogger(__name__)

# ✅ Comando /tarefa - Adicionar uma nova tarefa
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    
    if not descricao:
        await update.message.reply_text("⚠️ Você precisa informar uma descrição para a tarefa.\nExemplo: /tarefa Comprar pão")
        return
    
    sucesso = salvar_tarefa(descricao)

    if sucesso:
        await update.message.reply_text(f"✅ Tarefa adicionada: {descricao}")
    else:
        await update.message.reply_text("❌ Erro ao salvar a tarefa. Tente novamente.")
