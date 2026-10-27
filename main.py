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

# 💡 TENTAR importar funções do scheduler
# (se não existirem, a rota vai só dizer "não achei")
try:
    from scheduler.notificacoes_scheduler import processar_notificacoes_agendadas
except Exception:
    processar_notificacoes_agendadas = None

try:
    from scheduler.notificacoes_scheduler import verificar_e_avisar_sessoes_expiradas
except Exception:
    verificar_e_avisar_sessoes_expiradas = None

# 🔒 FASE 4.1: Lock para execução única global
try:
    from services.cron_lock_service import tentar_claim_cron, liberar_cron_lock
except Exception as e:
    logger.error(f"❌ Erro ao importar cron_lock_service: {e}")
    tentar_claim_cron = None
    liberar_cron_lock = None

# 🔧 Setup inicial
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Forçar flush de logs para stdout (importante para Render)
for handler in logger.handlers:
    handler.flush()

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
                    from_number = msg.get("from")
                    text_body = msg.get("text", {}).get("body", "")

                    logger.info(f"📱 WhatsApp - De: {from_number}, Texto: {text_body[:50]}")
                    logger.info(f"📞 Endpoint: {phone_number_id}, msg_id: {msg_id}")

                    # ✅ PROCESSAMENTO: Resolver tenant e chamar router
                    if not phone_number_id or not from_number or not text_body or not msg_id:
                        logger.warning(f"[WA] Dados incompletos: phone_number_id={bool(phone_number_id)} from={bool(from_number)} text={bool(text_body)} msg_id={bool(msg_id)}")
                        continue

                    try:
                        # ✅ [WA-P0] FASE 1: Consultar Firestore (fonte de verdade)
                        from services.whatsapp_msg_state_service import consultar_status, marcar_processando, marcar_concluida, marcar_falha_permanente, marcar_falha_recuperavel, marcar_envio_desconhecido
                        import time

                        timestamp_webhook = time.time()

                        # Verificar se já foi processada (Firestore é verdade)
                        status_atual = None
                        if bot_loop is not None:
                            future_status = asyncio.run_coroutine_threadsafe(
                                consultar_status(phone_number_id, msg_id),
                                bot_loop
                            )
                            status_atual = future_status.result(timeout=5)
                        else:
                            try:
                                status_atual = asyncio.run(consultar_status(phone_number_id, msg_id))
                            except RuntimeError as e:
                                # Em testes com event loop já rodando, ignorar erro
                                if "cannot be called from a running event loop" in str(e):
                                    status_atual = None
                                else:
                                    raise

                        if status_atual == "CONCLUIDA":
                            logger.info(f"[WA-P0] Mensagem já processada (CONCLUIDA): {phone_number_id}/{msg_id}")
                            continue

                        # ✅ [WA-P0] FASE 2: Tentar marcar como PROCESSANDO (atomicamente)
                        try:
                            if bot_loop is not None:
                                future_mark = asyncio.run_coroutine_threadsafe(
                                    marcar_processando(phone_number_id, msg_id, timestamp_webhook),
                                    bot_loop
                                )
                                ganhou_disputa = future_mark.result(timeout=5)
                            else:
                                try:
                                    ganhou_disputa = asyncio.run(marcar_processando(phone_number_id, msg_id, timestamp_webhook))
                                except RuntimeError as e:
                                    # Em testes com event loop já rodando, ignorar erro
                                    if "cannot be called from a running event loop" in str(e):
                                        ganhou_disputa = True
                                    else:
                                        raise
                        except Exception as e:
                            # Outra instância já está processando (AlreadyExists)
                            if "AlreadyExists" in str(type(e).__name__):
                                logger.info(f"[WA-P0] Outra instância processando: {phone_number_id}/{msg_id}")
                                continue
                            # Quota ou erro de persistência: aceitar webhook, deixar Meta retentar
                            elif "429" in str(e) or "Quota" in str(e):
                                logger.error(f"[WA-P0] Quota ao adquirir msg: {e}")
                                return 200
                            # Outras falhas: aceitar webhook, deixar Meta retentar
                            else:
                                logger.error(f"[WA-P0] Erro ao adquirir msg: {e}")
                                return 200

                        if not ganhou_disputa:
                            logger.info(f"[WA-P0] Outra instância processando: {phone_number_id}/{msg_id}")
                            continue

                        # ✅ Resolver tenant pelo endpoint
                        from services.whatsapp_endpoint_service import resolver_tenant_por_endpoint
                        tenant_id = resolver_tenant_por_endpoint(phone_number_id)

                        if not tenant_id:
                            logger.warning(f"[WA] Endpoint {phone_number_id} não registrado ou inativo")
                            continue

                        # ✅ Chamar roteador
                        from router.principal_router import roteador_principal

                        # Usar bot_loop se disponível (thread-safe)
                        try:
                            if bot_loop is not None:
                                future = asyncio.run_coroutine_threadsafe(
                                    roteador_principal(
                                        user_id=from_number,
                                        mensagem=text_body,
                                        tenant_id=tenant_id,
                                        phone_number_id=phone_number_id,
                                        update=None,
                                        context=None
                                    ),
                                    bot_loop
                                )
                                try:
                                    resposta = future.result(timeout=30)
                                except Exception as router_e:
                                    logger.error(f"[WA] Erro no roteador: {router_e}")
                                    resposta = "Desculpa, ocorreu um erro ao processar sua mensagem."
                            else:
                                logger.warning("[WA] bot_loop não disponível, tentando asyncio.run()")
                                try:
                                    resposta = asyncio.run(
                                        roteador_principal(
                                            user_id=from_number,
                                            mensagem=text_body,
                                            tenant_id=tenant_id,
                                            phone_number_id=phone_number_id,
                                            update=None,
                                            context=None
                                        )
                                    )
                                except RuntimeError as e:
                                    # Em testes com event loop já rodando, executar a coroutine no loop atual
                                    if "cannot be called from a running event loop" in str(e):
                                        import threading
                                        import time

                                        # Solução: executar em thread separada com seu próprio loop
                                        result_box = [None]
                                        error_box = [None]

                                        def run_in_thread():
                                            try:
                                                result_box[0] = asyncio.run(
                                                    roteador_principal(
                                                        user_id=from_number,
                                                        mensagem=text_body,
                                                        tenant_id=tenant_id,
                                                        phone_number_id=phone_number_id,
                                                        update=None,
                                                        context=None
                                                    )
                                                )
                                            except Exception as e2:
                                                error_box[0] = e2

                                        thread = threading.Thread(target=run_in_thread, daemon=True)
                                        thread.start()
                                        thread.join(timeout=30)

                                        if error_box[0]:
                                            raise error_box[0]
                                        resposta = result_box[0] or "Desculpa, erro ao processar."
                                    else:
                                        raise
                        except Exception as router_error:
                            logger.error(f"[WA] Erro crítico no roteador: {router_error}")
                            # ✅ [WA-P0] Marcar como FALHA_RECUPERAVEL (router falhou ANTES de enviar)
                            if bot_loop is not None:
                                asyncio.run_coroutine_threadsafe(
                                    marcar_falha_recuperavel(phone_number_id, msg_id, str(router_error), timestamp_webhook),
                                    bot_loop
                                ).result(timeout=5)
                            else:
                                asyncio.run(marcar_falha_recuperavel(phone_number_id, msg_id, str(router_error), timestamp_webhook))
                            continue

                        # ✅ Enviar resposta via WhatsApp
                        if resposta:
                            # Extrair texto da resposta (pode ser dict ou str)
                            texto_resposta = None
                            if isinstance(resposta, dict):
                                texto_resposta = resposta.get("resposta")
                            elif isinstance(resposta, str):
                                texto_resposta = resposta

                            try:
                                from services.whatsapp_service import enviar_mensagem_whatsapp

                                # Só enviar se houver texto (não é "already_sent" ou ação interna)
                                if texto_resposta:
                                    resultado = asyncio.run(
                                        enviar_mensagem_whatsapp(
                                            destinatario_id=from_number,
                                            mensagem=texto_resposta,
                                            phone_number_id=phone_number_id
                                        )
                                    )

                                    # ✅ [WA-P0] FASE 3: Atualizar status baseado no resultado do envio
                                    if resultado.get("success"):
                                        logger.info(f"[WA] ✅ Resposta enviada: message_id={resultado.get('message_id')} to={from_number}")
                                        # [NOVO] try/except para persistência CONCLUIDA
                                        try:
                                            if bot_loop is not None:
                                                asyncio.run_coroutine_threadsafe(
                                                    marcar_concluida(phone_number_id, msg_id, resultado.get("message_id"), timestamp_webhook),
                                                    bot_loop
                                                ).result(timeout=5)
                                            else:
                                                asyncio.run(marcar_concluida(phone_number_id, msg_id, resultado.get("message_id"), timestamp_webhook))
                                            logger.info(f"[WA] Status CONCLUIDA persistido: {phone_number_id}/{msg_id}")
                                        except Exception as e:
                                            # Envio foi aceito por Meta, deixar PROCESSANDO
                                            logger.error(f"[WA] Falha ao persistir CONCLUIDA (envio OK): {e}")
                                            # Cleanup vai adiar lease, não vai reprocessar

                                    else:
                                        status_code = resultado.get("status_code", 500)
                                        erro = resultado.get("error", "Unknown error")

                                        logger.error(f"[WA] ❌ Falha ao enviar: {erro} status={status_code}")

                                        # Classificar erro
                                        if status_code in [400, 403, 404]:
                                            # Erro permanente
                                            logger.warning(f"[WA-P0] FALHA_PERMANENTE: {status_code} {erro}")
                                            if bot_loop is not None:
                                                asyncio.run_coroutine_threadsafe(
                                                    marcar_falha_permanente(phone_number_id, msg_id, erro, timestamp_webhook),
                                                    bot_loop
                                                ).result(timeout=5)
                                            else:
                                                asyncio.run(marcar_falha_permanente(phone_number_id, msg_id, erro, timestamp_webhook))

                                        elif status_code in [429, 500, 503]:
                                            # Erro recuperável
                                            logger.warning(f"[WA-P0] FALHA_RECUPERAVEL: {status_code} {erro}")
                                            if bot_loop is not None:
                                                asyncio.run_coroutine_threadsafe(
                                                    marcar_falha_recuperavel(phone_number_id, msg_id, erro, timestamp_webhook),
                                                    bot_loop
                                                ).result(timeout=5)
                                            else:
                                                asyncio.run(marcar_falha_recuperavel(phone_number_id, msg_id, erro, timestamp_webhook))

                                        elif status_code == 504:
                                            # Timeout - resultado desconhecido
                                            logger.warning(f"[WA-P0] ENVIO_DESCONHECIDO: timeout")
                                            if bot_loop is not None:
                                                asyncio.run_coroutine_threadsafe(
                                                    marcar_envio_desconhecido(phone_number_id, msg_id, "Timeout na Meta API", timestamp_webhook),
                                                    bot_loop
                                                ).result(timeout=5)
                                            else:
                                                asyncio.run(marcar_envio_desconhecido(phone_number_id, msg_id, "Timeout na Meta API", timestamp_webhook))

                                        else:
                                            # Erro indeterminado
                                            logger.warning(f"[WA-P0] ENVIO_DESCONHECIDO: {status_code} {erro}")
                                            if bot_loop is not None:
                                                asyncio.run_coroutine_threadsafe(
                                                    marcar_envio_desconhecido(phone_number_id, msg_id, erro, timestamp_webhook),
                                                    bot_loop
                                                ).result(timeout=5)
                                            else:
                                                asyncio.run(marcar_envio_desconhecido(phone_number_id, msg_id, erro, timestamp_webhook))
                                else:
                                    logger.debug(f"[WA] Resposta sem texto (já enviada por outro canal ou é ação interna): {resposta}")

                            except Exception as send_e:
                                logger.error(f"[WA] Exceção ao enviar resposta: {send_e}")
                                # Falha ao enviar - pode ser timeout
                                if bot_loop is not None:
                                    asyncio.run_coroutine_threadsafe(
                                        marcar_envio_desconhecido(phone_number_id, msg_id, str(send_e), timestamp_webhook),
                                        bot_loop
                                    ).result(timeout=5)
                                else:
                                    asyncio.run(marcar_envio_desconhecido(phone_number_id, msg_id, str(send_e), timestamp_webhook))

                        else:
                            logger.warning(f"[WA] Roteador retornou resposta vazia para {from_number}")

                        # ✅ [WA-P0] FASE 4: Adicionar à memória como cache (APÓS sucesso no Firestore)
                        whatsapp_processed_ids.add(msg_id)

                    except Exception as e:
                        logger.error(f"[WA] Erro ao processar mensagem de {from_number}: {e}", exc_info=True)

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

# ✅ FASE 1A: Rota de saúde independente (sem processar notificações)
@app.route("/health", methods=["GET", "POST"])
def health_check_cron():
    """Endpoint de saúde rápido - valida autenticação e retorna OK sem processar notificações."""
    token = request.args.get("token") or request.headers.get("X-CRON-TOKEN")
    if token != CRON_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    return jsonify({"ok": True, "message": "health ok"}), 200

# ✅ ROTA PARA O CRON EXTERNO "ACORDAR" O APP
@app.route("/cron/ping", methods=["GET", "POST"])
def cron_ping():
    # 1) segurança simples
    token = request.args.get("token") or request.headers.get("X-CRON-TOKEN")
    if token != CRON_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    # 2) FASE 4.1: Verificar lock global
    lock_id = None
    try:
        if tentar_claim_cron is not None and bot_loop is not None:
            # Tentar obter lock (assíncrono)
            lock_result = asyncio.run_coroutine_threadsafe(tentar_claim_cron(), bot_loop).result(timeout=5)
            lock_acquired, lock_info = lock_result

            if not lock_acquired:
                logger.warning(f"[CRON] Execução rejeitada: {lock_info}")
                return jsonify({
                    "ok": True,
                    "message": f"processing_in_progress ({lock_info})",
                    "skipped": True
                }), 200

            lock_id = lock_info
        else:
            logger.info("[CRON] Lock service não disponível, continuando sem proteção")
    except Exception as e:
        logger.warning(f"[CRON] Erro ao obter lock (continuando anyway): {e}")
        # Continuar mesmo se lock falhar

    # 3) tenta rodar o processamento de notificações
    try:
        # se você tem a função direta
        if processar_notificacoes_agendadas is not None:
            # pode ser sync ou async
            if asyncio.iscoroutinefunction(processar_notificacoes_agendadas):
                # se o bot já tem loop rodando, usamos ele
                if bot_loop is not None:
                    fut = asyncio.run_coroutine_threadsafe(processar_notificacoes_agendadas(), bot_loop)
                    try:
                        fut.result(timeout=30)
                    except asyncio.TimeoutError:
                        logger.error("[CRON] Timeout após 30s (coroutine continua em background)")
                        # NOTA: Coroutine continua rodando, não é cancelada
                        # Lock será liberado por expiração automática (120s)
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

    finally:
        # 4) Liberar lock após conclusão
        if lock_id is not None and liberar_cron_lock is not None and bot_loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(liberar_cron_lock(lock_id), bot_loop).result(timeout=5)
            except Exception as e:
                logger.warning(f"[CRON] Erro ao liberar lock: {e}")
                # Lock será expirado automaticamente de qualquer forma

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

        # ✅ C4.3.6: resumo diário unificado é gerenciado por notificacoes_scheduler.py
        # Removido start_daily_summary() para evitar duplicação com notificacoes_scheduler
        # (ambos disparavam às 08:00, agora há apenas uma implementação canônica)

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
    # Adicionar handler de stdout unbuffered para Render logs
    import sys
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(stdout_handler)

    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": PORT, "use_reloader": False, "threaded": True},
        daemon=True
    ).start()

    run_bot()
