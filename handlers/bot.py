import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

# ✅ Função para o comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"🚀 Comando /start recebido de {update.effective_user.id}")
    await update.message.reply_text("👋 Olá! Eu sou o seu assistente virtual!")

# ✅ Função para o comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📖 Comando /help recebido!")
    await update.message.reply_text(
        "ℹ️ Comandos disponíveis:\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/ping - Testa se o bot está ativo"
    )

# ✅ Função para o comando /ping
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🏓 Comando /ping recebido!")
    await update.message.reply_text("Pong!")

# 🚀 Função para registrar handlers (chamada pelo main.py)
def register_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))  # Adicionado
    application.add_handler(CommandHandler("ping", ping))
    logger.info("✅ Handlers registrados: /start, /help, /ping")
