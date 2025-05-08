# scheduler/notificacao_scheduler.py

from datetime import datetime
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.firebase_service_async import buscar_subcolecao, atualizar_dado_em_path
from telegram import Bot
import os
import logging

logger = logging.getLogger(__name__)

FUSO_BR = timezone("America/Sao_Paulo")

async def processar_notificacoes_agendadas():
    print("⏰ Verificando notificações agendadas...")

    try:
        # 🔍 Itera por todos os usuários
        clientes = await buscar_subcolecao("Clientes")
        agora = datetime.now(FUSO_BR)

        for user_id in clientes.keys():
            path = f"Clientes/{user_id}/NotificacoesAgendadas"
            notificacoes = await buscar_subcolecao(path)

            if not notificacoes:
                continue

            for notif_id, notif in notificacoes.items():
                if notif.get("avisado"):
                    continue

                data_hora_str = notif.get("data_hora")
                canal = notif.get("canal", "telegram")
                mensagem = notif.get("mensagem", "📌 Lembrete")

                try:
                    data_hora = datetime.fromisoformat(data_hora_str).astimezone(FUSO_BR)
                except Exception as e:
                    logger.error(f"Erro ao converter data_hora da notificação: {e}")
                    continue

                if data_hora <= agora:
                    try:
                        if canal == "telegram":
                            bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
                            await bot.send_message(chat_id=int(user_id), text=mensagem)

                        elif canal == "whatsapp":
                            from services.whatsapp_service import enviar_mensagem_whatsapp
                            await enviar_mensagem_whatsapp(user_id, mensagem)

                        else:
                            logger.warning(f"🔁 Canal desconhecido '{canal}' para {user_id}")

                        # 🔁 Marca como avisado
                        await atualizar_dado_em_path(f"{path}/{notif_id}", {"avisado": True})
                        print(f"✅ Notificação enviada para {user_id} via {canal}: {mensagem}")

                    except Exception as e:
                        logger.error(f"Erro ao enviar notificação para {user_id} via {canal}: {e}")

    except Exception as e:
        logger.error(f"❌ Erro na rotina de notificações: {e}")

def start_notificacao_scheduler():
    scheduler = AsyncIOScheduler(timezone=FUSO_BR)
    scheduler.add_job(processar_notificacoes_agendadas, "interval", minutes=2)
    scheduler.start()
    print("✅ Scheduler de notificações iniciado a cada 15 minutos.")