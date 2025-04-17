import os
import sys
import logging
import asyncio
import threading
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# 🔧 Setup inicial
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 🔑 Variáveis de ambiente
TOKEN = os.getenv("TOKEN")
PORT = int(os.environ.get("PORT", 8080))
RENDER_SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "telegram-bot-a7a7")
WEBHOOK_URL = f"https://{RENDER_SERVICE_NAME}.onrender.com/webhook"

# 🌐 App Flask
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()
bot_loop = None  # loop global do bot

# Executor para rodar funções em segundo plano
executor = ThreadPoolExecutor()

# ✅ Handlers e Schedulers
from handlers import register_handlers
from scheduler.followup_scheduler import start_followup_scheduler
from scheduler.daily_summary import start_daily_summary

logger.info("✅ Registrando handlers...")
register_handlers(application)
logger.info("✅ Handlers registrados!")

# ⏰ Agendadores
start_followup_scheduler()
start_daily_summary(application)

# 🔄 Webhook endpoint
async def webhook_process(update: Update):
    await application.process_update(update)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        logger.debug("📥 Webhook recebido")
        update = Update.de_json(request.get_json(force=True), application.bot)
        logger.debug(f"📩 Update recebido: {update}")

        if bot_loop is None:
            raise RuntimeError("❌ Loop do bot não inicializado")

        # Processa o update no loop principal
        future = asyncio.run_coroutine_threadsafe(webhook_process(update), bot_loop)
        future.result(timeout=20)

        return jsonify({"ok": True}), 200

    except Exception as e:
        logger.error(f"🔥 Erro no webhook: {e}", exc_info=True)
        return "Erro", 500

@app.route("/", methods=["GET"])
def health_check():
    return "🤖 Bot Online!", 200

# 🔗 Configura webhook no Telegram
async def setup_webhook():
    try:
        await application.bot.delete_webhook()
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook configurado com sucesso: {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ Erro ao configurar webhook: {e}", exc_info=True)

# 🚀 Loop principal do bot
def run_bot():
    global bot_loop
    try:
        bot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(bot_loop)

        bot_loop.run_until_complete(application.initialize())
        bot_loop.run_until_complete(setup_webhook())
        bot_loop.run_until_complete(application.start())

        logger.info("🤖 Bot iniciado com sucesso e aguardando atualizações...")
        bot_loop.run_forever()
    except Exception as e:
        logger.error(f"❌ Erro crítico ao iniciar bot: {e}", exc_info=True)
    finally:
        bot_loop.run_until_complete(application.stop())
        bot_loop.close()

# 🧵 Inicia Flask + Bot em paralelo
if __name__ == "__main__":
    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": PORT, "use_reloader": False},
        daemon=True
    ).start()

    run_bot()
