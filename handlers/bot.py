import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

# ✅ Função para o comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"🚀 Comando /start recebido de {update.effective_user.id}")
    await update.message.reply_text("👋 Olá! Eu sou o seu assistente virtual!")

# 🚀 Função para registrar handlers (chamada pelo main.py)
def register_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    logger.info("✅ Handlers /start e /ping registrados!")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🏓 Comando /ping recebido!")
    await update.message.reply_text("Pong!")

def setup_bot_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    logger.info("✅ Handlers /start e /ping registrados!")
