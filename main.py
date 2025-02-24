import os
import logging
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from handlers import register_handlers

# 🔑 Carregar variáveis de ambiente
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

# ✅ Comando /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"🚀 Comando /start recebido de {update.effective_user.id}")
        await update.message.reply_text("👋 Olá! Bot funcionando com Webhooks!")
    except Exception as e:
        logger.error(f"❌ Erro no comando /start: {e}")

# 🔄 Rota do webhook (Flask recebe e repassa para o bot)
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        logger.debug("📥 Webhook recebido")
        update = Update.de_json(request.get_json(force=True), application.bot)
        
        # Coloca a atualização na fila de processamento
        application.update_queue.put_nowait(update)
        
        return "OK", 200
    except Exception as e:
        logger.error(f"🔥 Erro no webhook: {e}")
        return "Erro", 500

# 🏠 Health check
@app.route("/", methods=["GET"])
def health_check():
    logger.info("🩺 Health check recebido")
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
        # Cria um novo loop assíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Configura o webhook
        loop.run_until_complete(set_webhook())
        
        # Inicializa o Application
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(application.start())
        
        # Inicia o processamento de atualizações
        loop.run_forever()
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar o bot: {e}")

# 🚀 Inicialização
if __name__ == "__main__":
    # 📦 Registra handlers
    register_handlers(application)

    # 🚀 Inicia o servidor Flask em uma thread separada
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": PORT}).start()

    # 🚀 Inicia o bot
    run_bot()