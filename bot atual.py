import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Log crítico para confirmar execução
        logger.info("🚀 /start executado! Respondendo ao usuário...")
        await update.message.reply_text("👋 Olá! Bot funcionando via Webhooks!")
    except Exception as e:
        logger.error(f"Erro no /start: {e}", exc_info=True)

def register_handlers(application: Application):
    try:
        # Limpa handlers existentes (evitar duplicação)
        application.handlers.clear()
        
        # Adiciona handlers
        application.add_handler(CommandHandler("start", start))
        logger.info("✅ Handlers registrados: /start")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)