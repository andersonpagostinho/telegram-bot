# scheduler/followup_scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from handlers.followup_handler import rotina_lembrete_followups
from services.firebase_service_async import buscar_dados, buscar_dado_em_path
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

def start_followup_scheduler():
    scheduler = AsyncIOScheduler(timezone=timezone("America/Sao_Paulo"))

    async def configurar_agendamentos():
        print("🗓️ Buscando usuários para agendar follow-ups...")
        clientes = await buscar_dados("Usuarios") or []

        for cliente in clientes:
            user_id = str(cliente.get("id"))
            if not user_id:
                continue

            try:
                config = await buscar_dado_em_path(f"Usuarios/{user_id}/configuracoes/avisos")
                horarios = config.get("horarios", []) if config else []

                if not horarios:
                    horarios = ["09:00", "13:00", "17:00"]

                for idx, horario in enumerate(horarios):
                    try:
                        hora, minuto = map(int, horario.split(":"))
                        scheduler.add_job(
                            rotina_lembrete_followups,
                            "cron",
                            hour=hora,
                            minute=minuto,
                            id=f"lembrete_{user_id}_{idx}",
                            kwargs={"user_id": user_id},
                            replace_existing=True
                        )
                        print(f"✅ Agendado para {user_id} às {horario}")
                    except Exception as e:
                        logger.error(f"Erro ao agendar horário {horario} para {user_id}: {e}")

            except Exception as e:
                logger.error(f"❌ Erro ao buscar config para {user_id}: {e}")

    scheduler.start()
    asyncio.ensure_future(configurar_agendamentos())
    print("✅ Scheduler de follow-ups iniciado com configurações personalizadas.")
