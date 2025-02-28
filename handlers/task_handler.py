import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import salvar_tarefa

logger = logging.getLogger(__name__)

# ✅ Adicionar uma nova tarefa
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        descricao = ' '.join(context.args)
        if not descricao:
            await update.message.reply_text("⚠️ Você precisa informar uma descrição para a tarefa.")
            return
        
        salvar_tarefa(descricao)  # Função que salva no Firestore
        await update.message.reply_text(f"✅ Tarefa adicionada: {descricao}")

    except Exception as e:
        logger.error(f"Erro ao salvar tarefa: {e}", exc_info=True)
        await update.message.reply_text("❌ Erro ao salvar a tarefa. Tente novamente.")
