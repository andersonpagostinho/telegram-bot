import os
import logging
import asyncio
import threading
import sys
from flask import Flask, request
from telegram import Update
from telegram.ext import Application
from dotenv import load_dotenv
from handlers.bot import register_handlers

# 🔑 Carregar variáveis de ambiente
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# 📝 Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 🌐 Variáveis de ambiente
TOKEN = os.getenv("TOKEN")
PORT = int(os.environ.get("PORT", 8080))
RENDER_SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "telegram-bot-a7a7")
WEBHOOK_URL = f"https://{RENDER_SERVICE_NAME}.onrender.com/webhook"

# 🏗️ Inicialização do Flask
app = Flask(__name__)

# 🏗️ Inicialização do Telegram
application = Application.builder().token(TOKEN).build()

# ✅ Registra os handlers logo após criar a aplicação
register_handlers(application)

# ✅ Processa o update recebido
async def webhook_process(update: Update):
    await application.process_update(update)

# 🔄 Rota do webhook (Flask recebe e repassa para o bot)
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        logger.debug("📥 Webhook recebido")
        update = Update.de_json(request.get_json(force=True), application.bot)
        logger.debug(f"📩 Update recebido: {update}")

        # ✅ Usa o loop do bot corretamente
        if application.running:
            asyncio.run_coroutine_threadsafe(webhook_process(update), application.event_loop)
        else:
            logger.error("❌ Loop do bot não está rodando!")

        return "OK", 200
    except Exception as e:
        logger.error(f"🔥 Erro no webhook: {e}", exc_info=True)
        return "Erro", 500

# 🏠 Health check
@app.route("/", methods=["GET"])
def health_check():
    return "🤖 Bot Online!", 200

# 🌐 Configura o webhook no Telegram
async def set_webhook():
    try:
        await application.bot.delete_webhook()
        success = await application.bot.set_webhook(WEBHOOK_URL)
        if success:
            logger.info(f"✅ Webhook configurado em: {WEBHOOK_URL}")
        else:
            logger.error("❌ Falha ao configurar webhook!")
    except Exception as e:
        logger.error(f"❌ Erro ao configurar webhook: {e}")

# 🚀 Inicialização do bot
def run_bot():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # ✅ Inicializa e inicia o bot explicitamente
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(set_webhook())
        loop.run_until_complete(application.start())

        logger.info("🤖 Bot está rodando e processando atualizações...")
        loop.run_forever()
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar o bot: {e}", exc_info=True)

# 🚀 Inicialização
if __name__ == "__main__":
    threading.Thread(
        target=app.run, 
        kwargs={"host": "0.0.0.0", "port": PORT, "use_reloader": False}
    ).start()
    run_bot()