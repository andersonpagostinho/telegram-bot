import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from handlers.task_handler import add_task  # Apenas o necessário para testar

logger = logging.getLogger(__name__)

# ✅ Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Bot funcionando!")

# ✅ Comando /ping
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong!")

# 🚀 Registra apenas os handlers necessários
def register_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("tarefa", add_task))  # Apenas este comando para testar
