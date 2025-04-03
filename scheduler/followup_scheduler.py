# scheduler/followup_scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from pytz import timezone
from handlers.followup_handler import rotina_lembrete_followups
from services.firebase_service import buscar_dados
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def start_followup_scheduler():
    scheduler = AsyncIOScheduler(timezone=timezone("America/Sao_Paulo"))

    async def configurar_agendamentos():
        print("🗓️ Buscando usuários para agendar follow-ups...")
        clientes = buscar_dados("Usuarios") or []

        for cliente in clientes:
            user_id = str(cliente.get("id"))
            if not user_id:
                continue

            try:
                config = buscar_dados(f"Usuarios/{user_id}/configuracoes")
                horarios = config.get("avisos", {}).get("horarios", [])

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

    # Inicia scheduler e configura os jobs após iniciar
    scheduler.start()
    import asyncio
    asyncio.get_event_loop().create_task(configurar_agendamentos())
    print("✅ Scheduler de follow-ups iniciado com configurações personalizadas.")
