from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.firebase_service_async import buscar_todos_clientes, buscar_subcolecao, buscar_dados
from telegram import Bot
from datetime import datetime
import logging
from pytz import timezone

logger = logging.getLogger(__name__)

# 🔄 Agendador principal com fuso horário de Brasília
def start_daily_summary(application):
    scheduler = AsyncIOScheduler(timezone=timezone("America/Sao_Paulo"))

    @scheduler.scheduled_job('cron', hour=8, minute=0)
    async def enviar_resumo_diario():
        logger.info("⏰ Executando rotina de resumo diário...")

        try:
            clientes = await buscar_todos_clientes()
        except Exception as e:
            logger.error(f"❌ Erro ao buscar clientes: {e}")
            return

        for user_id, dados in clientes.items():
            if dados.get("pagamentoAtivo"):
                try:
                    await enviar_resumo_para_usuario(application.bot, user_id, dados)
                except Exception as e:
                    logger.error(f"🔥 Erro no resumo do usuário {user_id}: {e}")

    scheduler.start()
    logger.info("✅ Scheduler de resumo diário iniciado com sucesso!")

# 📬 Função para enviar resumo individual
async def enviar_resumo_para_usuario(bot: Bot, user_id: str, dados_usuario: dict):
    try:
        hoje = datetime.now(timezone("America/Sao_Paulo")).date().isoformat()
        nome = dados_usuario.get("nome", "Empreendedor")

        # Busca tarefas do próprio usuário (se estiver salvando com user_id dentro de "Tarefas")
        todas_tarefas = await buscar_dados("Tarefas") or []
        tarefas_hoje = [t for t in todas_tarefas if t.get("user_id") == user_id and hoje in t.get("data", "")]

        # Busca eventos desse usuário
        eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
        eventos_hoje = [e for e in eventos.values() if e.get("data") == hoje]

        mensagem = (
            f"☀️ Bom dia, *{nome}*!\n\n"
            f"Aqui está o seu resumo de hoje:\n"
            f"📝 Tarefas: *{len(tarefas_hoje)}*\n"
            f"📅 Reuniões/Eventos: *{len(eventos_hoje)}*\n\n"
            f"Tenha um dia incrível! 💪🚀"
        )

        await bot.send_message(chat_id=int(user_id), text=mensagem, parse_mode="Markdown")
        logger.info(f"✅ Resumo diário enviado para {user_id}")

    except Exception as e:
        logger.error(f"❌ Erro ao enviar resumo para {user_id}: {e}")
