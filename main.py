# --- FIX TZ (Render/Linux) - TEM QUE SER A PRIMEIRA COISA DO ARQUIVO ---
import os as _os
import time as _time

_os.environ["TZ"] = "America/Sao_Paulo"
try:
    _time.tzset()  # funciona em Linux (Render)
except Exception:
    pass
# --- /FIX TZ ---
import os
import sys
import logging
import asyncio
import threading
import hmac
import hashlib
import json
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from pytz import timezone

# ✅ Importações de agendadores
from scheduler.notificacoes_scheduler import start_notificacao_scheduler
#from scheduler.followup_scheduler import start_followup_scheduler
from scheduler.daily_summary import start_daily_summary
#from scheduler.email_to_event_loop import loop_verificacao_emails
from handlers import register_handlers

# 💡 TENTAR importar a função que processa notificações diretamente
# (se não existir, a rota vai só dizer "não achei")
try:
    from scheduler.notificacoes_scheduler import processar_notificacoes_agendadas
except Exception:
    processar_notificacoes_agendadas = None

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
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")

# 🔐 token do cron externo
CRON_TOKEN = os.environ.get("CRON_TOKEN", "supersecreto123")

# 🌐 App Flask
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()
bot_loop = None  # loop global do bot
whatsapp_processed_ids = set()  # Dedupe em memória para message IDs

# Executor para rodar funções em segundo plano
executor = ThreadPoolExecutor()

# ✅ Handlers e Schedulers
logger.info("✅ Registrando handlers...")
register_handlers(application)
logger.info("✅ Handlers registrados!")

# ⏰ Agendadores que você já tinha
#start_followup_scheduler()
# PATCH: daily_summary movido para dentro de run_bot() após event loop ser criado
#start_daily_summary(application)
start_notificacao_scheduler()

# ⏰ Inicia verificação automática de e-mails a cada X minutos
#def iniciar_email_loop():
#    asyncio.run(loop_verificacao_emails())

#threading.Thread(
#    target=iniciar_email_loop,
#    daemon=True
#).start()

# 🔍 DEBUG: Verificar credenciais (remover após diagnosticar)
@app.route("/debug/creds", methods=["GET"])
def debug_creds():
    """Diagnosticar tamanho e validade de FIREBASE_CREDENTIALS_B64"""
    import base64

    b64 = os.getenv("FIREBASE_CREDENTIALS_B64", "")
    result = {
        "size": len(b64),
        "expected_size": 3224,
        "is_truncated": len(b64) < 3224,
        "first_50": b64[:50] if b64 else "EMPTY",
        "last_50": b64[-50:] if len(b64) > 50 else b64,
    }

    if b64:
        try:
            decoded = base64.b64decode(b64).decode('utf-8')
            result["decode_ok"] = True
            result["decoded_size"] = len(decoded)

            import json
            json_obj = json.loads(decoded)
            result["json_valid"] = True
            result["has_private_key"] = "private_key" in json_obj
            result["has_project_id"] = "project_id" in json_obj
        except Exception as e:
            result["decode_ok"] = False
            result["error"] = str(e)[:100]
    else:
        result["status"] = "NOT_DEFINED"

    return jsonify(result)

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

        future = asyncio.run_coroutine_threadsafe(webhook_process(update), bot_loop)
        future.result(timeout=60)

        return jsonify({"ok": True}), 200

    except Exception as e:
        logger.error(f"🔥 Erro no webhook: {e}", exc_info=True)
        return "Erro", 500

@app.route("/webhook/whatsapp", methods=["GET"])
def whatsapp_webhook_get():
    try:
        hub_mode = request.args.get("hub.mode")
        hub_verify_token = request.args.get("hub.verify_token")
        hub_challenge = request.args.get("hub.challenge")

        logger.debug(f"🔐 Validação WhatsApp - mode: {hub_mode}, token match: {hub_verify_token == WHATSAPP_VERIFY_TOKEN}")

        if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
            logger.info("✅ Webhook WhatsApp validado com sucesso")
            return hub_challenge, 200
        else:
            logger.warning("❌ Falha na validação do webhook WhatsApp")
            return "Forbidden", 403
    except Exception as e:
        logger.error(f"🔥 Erro na validação WhatsApp: {e}", exc_info=True)
        return "Error", 500

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook_post():
    try:
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = request.get_data(as_text=True)

        if not validate_whatsapp_signature(signature, body, META_APP_SECRET):
            logger.warning("❌ Assinatura HMAC inválida")
            return "Forbidden", 403

        data = request.get_json(force=True)
        logger.debug(f"📬 Webhook WhatsApp recebido: {data}")

        if "entry" in data and len(data["entry"]) > 0:
            entry = data["entry"][0]
            if "changes" in entry and len(entry["changes"]) > 0:
                changes = entry["changes"][0]
                value = changes.get("value", {})

                # FASE 4: Extrair identidade do endpoint (phone_number_id)
                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id")
                display_phone_number = metadata.get("display_phone_number", "")
                waba_id = metadata.get("business_account_id", "")

                if phone_number_id:
                    logger.debug(f"📞 Endpoint WhatsApp identificado: {phone_number_id}")

                messages = value.get("messages", [])

                for msg in messages:
                    msg_id = msg.get("id")

                    if msg_id and msg_id in whatsapp_processed_ids:
                        logger.debug(f"⏭️ Mensagem duplicada ignorada: {msg_id}")
                        continue

                    if msg_id:
                        whatsapp_processed_ids.add(msg_id)

                    from_number = msg.get("from")
                    text_body = msg.get("text", {}).get("body", "")

                    logger.info(f"📱 WhatsApp - De: {from_number}, Texto: {text_body}")
                    logger.info(f"📞 Endpoint: {phone_number_id}, Remetente: {from_number}")
                    # TODO: Integrar com o motor de agendamento
                    # TODO: Usar whatsapp_endpoint_service para resolver tenant_id

        return "OK", 200
    except json.JSONDecodeError as e:
        logger.error(f"🔥 Erro ao fazer parse do JSON: {e}")
        return "OK", 200
    except Exception as e:
        logger.error(f"🔥 Erro ao processar webhook WhatsApp: {e}", exc_info=True)
        return "OK", 200

def validate_whatsapp_signature(signature: str, body: str, secret: str) -> bool:
    try:
        if not signature.startswith("sha256="):
            return False

        hash_value = signature.split("=")[1]
        expected_hash = hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        return hash_value == expected_hash
    except Exception as e:
        logger.error(f"🔥 Erro ao validar assinatura: {e}")
        return False

@app.route("/", methods=["GET"])
def health_check():
    return "🤖 Bot Online!", 200

# ✅ ROTA PARA O CRON EXTERNO “ACORDAR” O APP
@app.route("/cron/ping", methods=["GET", "POST"])
def cron_ping():
    # 1) segurança simples
    token = request.args.get("token") or request.headers.get("X-CRON-TOKEN")
    if token != CRON_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    # 2) tenta rodar o processamento de notificações
    try:
        # se você tem a função direta
        if processar_notificacoes_agendadas is not None:
            # pode ser sync ou async
            if asyncio.iscoroutinefunction(processar_notificacoes_agendadas):
                # se o bot já tem loop rodando, usamos ele
                if bot_loop is not None:
                    fut = asyncio.run_coroutine_threadsafe(processar_notificacoes_agendadas(), bot_loop)
                    fut.result(timeout=30)
                else:
                    asyncio.run(processar_notificacoes_agendadas())
            else:
                # função normal
                processar_notificacoes_agendadas()
            return jsonify({"ok": True, "message": "notificacoes processadas"}), 200
        else:
            # fallback: pelo menos confirma que acordou
            logger.info("⚠️ /cron/ping chamado, mas não há processar_notificacoes_agendadas para rodar.")
            return jsonify({"ok": True, "message": "cron ping ok (sem processamento direto)"}), 200

    except Exception as e:
        logger.error(f"❌ Erro ao executar cron/ping: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500

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

        # ✅ PATCH: daily_summary inicializado após event loop existir
        start_daily_summary(application)

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
