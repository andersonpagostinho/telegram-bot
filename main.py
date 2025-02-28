import os
import logging
import asyncio
import threading
import sys
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
PORT = int(os.environ.get("PORT", 8080))
RENDER_SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "telegram-bot-a7a7")
WEBHOOK_URL = f"https://{RENDER_SERVICE_NAME}.onrender.com/webhook"

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# Registro de handlers
from handlers.bot import register_handlers

logger.info("✅ Registrando handlers...")
register_handlers(application)
logger.info("✅ Handlers registrados!")

async def webhook_process(update: Update):
    await application.process_update(update)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        logger.debug("📥 Webhook recebido")
        update = Update.de_json(request.get_json(force=True), application.bot)
        logger.debug(f"📩 Update recebido: {update}")

        # ✅ Corrigido: Usa o loop da aplicação corretamente
        future = asyncio.run_coroutine_threadsafe(
            webhook_process(update),
            application._loop
        )
        # Aguarda a conclusão e trata possíveis exceções
        future.result(timeout=10)
        
        return "OK", 200
    except Exception as e:
        logger.error(f"🔥 Erro no webhook: {e}", exc_info=True)
        return "Erro", 500

@app.route("/", methods=["GET"])
def health_check():
    return "🤖 Bot Online!", 200

async def setup_webhook():
    try:
        await application.bot.delete_webhook()
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook configurado em: {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ Erro ao configurar webhook: {e}")

def run_bot():
    try:
        # ✅ Loop principal da aplicação
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Inicialização assíncrona
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(setup_webhook())
        loop.run_until_complete(application.start())
        
        logger.info("🤖 Bot está rodando e processando atualizações...")
        loop.run_forever()
    except Exception as e:
        logger.error(f"❌ Erro fatal no bot: {e}", exc_info=True)
    finally:
        loop.run_until_complete(application.stop())
        loop.close()

if __name__ == "__main__":
    # Inicia o Flask em thread separada
    flask_thread = threading.Thread(
        target=app.run,
        kwargs={
            "host": "0.0.0.0",
            "port": PORT,
            "use_reloader": False,
            "debug": False
        },
        daemon=True
    )
    flask_thread.start()

    # Inicia o bot na thread principal
    run_bot()