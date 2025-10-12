# scheduler/notificacao_scheduler.py

from datetime import datetime
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.firebase_service_async import buscar_subcolecao, atualizar_dado_em_path
from services.recorrencia_service import checar_e_propor_recorrencias_todos
import logging
import os

logger = logging.getLogger(__name__)

FUSO_BR = timezone("America/Sao_Paulo")


def _parse_iso_br(dt_str: str):
    """
    Converte string ISO (com ou sem timezone) para datetime timezone-aware no fuso de São Paulo.
    - Se vier com 'Z', troca por '+00:00' para o fromisoformat aceitar.
    - Se vier naive (sem tz), assume America/Sao_Paulo.
    """
    try:
        s = (dt_str or "").replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return FUSO_BR.localize(dt)
        return dt.astimezone(FUSO_BR)
    except Exception as e:
        logger.error(f"_parse_iso_br: data_hora inválida: {dt_str} -> {e}")
        return None


async def _get_bot():
    """
    Tenta usar application.bot (quando o app está rodando).
    Se não conseguir, usa fallback com TOKEN do ambiente.
    """
    try:
        from main import application
        if getattr(application, "bot", None):
            return application.bot
        logger.warning("application.bot não encontrado; tentando fallback por TOKEN.")
    except Exception as e:
        logger.warning(f"Não consegui importar application.bot ({e}); tentando fallback por TOKEN.")

    from telegram import Bot
    token = os.getenv("TOKEN")
    if not token:
        logger.error("TOKEN ausente no ambiente; não é possível enviar notificações.")
        return None
    return Bot(token=token)


async def processar_notificacoes_agendadas():
    logger.info("⏰ processar_notificacoes_agendadas() iniciado...")

    try:
        bot = await _get_bot()
        if bot is None:
            return

        clientes = await buscar_subcolecao("Clientes") or {}
        agora = datetime.now(FUSO_BR)

        for user_id in clientes.keys():
            path = f"Clientes/{user_id}/NotificacoesAgendadas"
            notificacoes = await buscar_subcolecao(path) or {}

            for notif_id, notif in notificacoes.items():
                if not isinstance(notif, dict):
                    continue

                # já enviada?
                avisado = bool(notif.get("avisado"))
                status = (notif.get("status") or "").lower()
                if avisado or status == "enviado":
                    continue

                # quando disparar
                dt = _parse_iso_br(notif.get("data_hora", ""))
                if not dt:
                    await atualizar_dado_em_path(f"{path}/{notif_id}", {
                        "status": "erro",
                        "erro": "data_hora inválida",
                        "atualizado_em": agora.isoformat()
                    })
                    continue
                if dt > agora:
                    continue

                canal = (notif.get("canal") or "telegram").lower()

                # mensagem clara (fallback)
                mensagem = notif.get("mensagem")
                if not mensagem:
                    desc = (notif.get("descricao") or "compromisso").strip()
                    alvo = notif.get("alvo_evento") or {}
                    data_ev = (alvo.get("data") or "")
                    hora_ev = (alvo.get("hora_inicio") or "")
                    min_antes = int(notif.get("minutos_antes") or 30)

                    # tenta identificar reunião
                    desc_lower = desc.lower()
                    tipo_legivel = "reunião" if "reuni" in desc_lower else desc_lower

                    # hoje ou outra data
                    hoje_str = datetime.now(FUSO_BR).strftime("%Y-%m-%d")
                    quando = ""
                    if data_ev and hora_ev:
                        quando = f" — hoje às {hora_ev}" if data_ev == hoje_str else f" — {data_ev} às {hora_ev}"

                    sufixo_min = "minuto" if min_antes == 1 else "minutos"
                    mensagem = f"🔔 Não esqueça: sua {tipo_legivel} começa em {min_antes} {sufixo_min}{quando}."

                try:
                    if canal == "telegram":
                        await bot.send_message(chat_id=int(user_id), text=mensagem)
                    elif canal == "whatsapp":
                        from services.whatsapp_service import enviar_mensagem_whatsapp
                        await enviar_mensagem_whatsapp(user_id, mensagem)
                    else:
                        # canal desconhecido → tenta telegram
                        await bot.send_message(chat_id=int(user_id), text=mensagem)

                    await atualizar_dado_em_path(f"{path}/{notif_id}", {
                        "avisado": True,
                        "status": "enviado",
                        "enviado_em": agora.isoformat()
                    })
                    logger.info(f"✅ Notificação enviado [{user_id}] via {canal}: {mensagem}")

                except Exception as e:
                    logger.error(f"Erro ao enviar notificação para {user_id} via {canal}: {e}")
                    await atualizar_dado_em_path(f"{path}/{notif_id}", {
                        "status": "erro",
                        "erro": str(e),
                        "atualizado_em": agora.isoformat()
                    })

    except Exception as e:
        logger.error(f"❌ Erro na rotina de notificações: {e}")


async def enviar_resumo_diario():
    logger.info("📋 enviar_resumo_diario() iniciado...")
    try:
        bot = await _get_bot()
        if bot is None:
            return

        from services.event_service_async import buscar_eventos_por_intervalo
        from services.firebase_service_async import buscar_subcolecao

        clientes = await buscar_subcolecao("Clientes") or {}
        hoje = datetime.now(FUSO_BR).date()
        hoje_str = hoje.strftime("%Y-%m-%d")

        for user_id in clientes.keys():
            partes_resumo = []

            # eventos do dia
            eventos = await buscar_eventos_por_intervalo(user_id, dia_especifico=hoje)
            if eventos:
                partes_resumo.append("📅 *Eventos de hoje:*\n" + "\n".join(f"• {e}" for e in eventos))
            else:
                partes_resumo.append("📅 Nenhum evento agendado.")

            # tarefas
            tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas") or {}
            tarefas = [t["descricao"] for t in tarefas_dict.values() if isinstance(t, dict) and t.get("descricao")]
            if tarefas:
                partes_resumo.append("📝 *Tarefas pendentes:*\n" + "\n".join(f"• {t}" for t in tarefas))
            else:
                partes_resumo.append("📝 Nenhuma tarefa registrada.")

            # follow-ups (coleção antiga/legada)
            followups_dict = await buscar_subcolecao(f"Usuarios/{user_id}/FollowUps") or {}
            pendentes = []
            for f in followups_dict.values():
                if f.get("status") == "pendente":
                    nome = f.get("nome_cliente", "Sem nome")
                    data = f.get("data", hoje_str)
                    if data == hoje_str:
                        hora = f.get("hora", "08:00")
                        pendentes.append(f"{nome} às {hora}")

            if pendentes:
                partes_resumo.append("📌 *Follow-ups de hoje:*\n" + "\n".join(f"• {p}" for p in pendentes))
            else:
                partes_resumo.append("📌 Nenhum follow-up para hoje.")

            texto = "\n\n".join(partes_resumo)

            try:
                await bot.send_message(chat_id=int(user_id), text=texto, parse_mode="Markdown")
                logger.info(f"✅ Resumo diário enviado para {user_id}")
            except Exception as e:
                logger.error(f"Erro ao enviar resumo diário para {user_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Erro ao gerar/enviar resumo diário: {e}")


def start_notificacao_scheduler():
    scheduler = AsyncIOScheduler(timezone=FUSO_BR)

    # 🔔 Notificações a cada 1 minuto (coalesce + tolerância a misfire)
    scheduler.add_job(
        processar_notificacoes_agendadas,
        "interval",
        seconds=60,
        coalesce=True,
        misfire_grace_time=120,
        id="notificacoes_intervalo_1min",
        replace_existing=True,
    )

    # 📨 Resumo diário às 08:00
    scheduler.add_job(
        enviar_resumo_diario,
        "cron",
        hour=8,
        minute=0,
        id="resumo_diario_08h",
        replace_existing=True,
    )

    # 🤖 Recorrência inteligente às 08:00
    scheduler.add_job(
        checar_e_propor_recorrencias_todos,
        "cron",
        hour=8,
        minute=0,
        id="recorrencia_diaria_08h",
        replace_existing=True,
    )

    scheduler.start()
    print("✅ Scheduler de notificações iniciado (loop a cada 1 min, resumo 08:00, recorrência 08:00).")
    logger.info("✅ Scheduler de notificações iniciado (loop a cada 1 min, resumo 08:00, recorrência 08:00).")
