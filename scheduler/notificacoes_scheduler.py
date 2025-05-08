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
                            bot = Bot(token=os.getenv("TOKEN"))
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

async def enviar_resumo_diario():
    print("📋 Enviando resumo diário completo...")

    try:
        from services.event_service_async import buscar_eventos_por_intervalo
        from services.firebase_service_async import buscar_dado_em_path, buscar_subcolecao
        clientes = await buscar_subcolecao("Clientes")
        hoje = datetime.now(FUSO_BR).date()
        hoje_str = hoje.strftime("%Y-%m-%d")

        for user_id in clientes.keys():
            partes_resumo = []

            # 🎯 Eventos do dia
            eventos = await buscar_eventos_por_intervalo(user_id, dia_especifico=hoje)
            if eventos:
                partes_resumo.append("📅 *Eventos de hoje:*\n" + "\n".join(f"• {e}" for e in eventos))
            else:
                partes_resumo.append("📅 Nenhum evento agendado.")

            # 📌 Tarefas
            tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas") or {}
            tarefas = [t["descricao"] for t in tarefas_dict.values() if isinstance(t, dict)]
            if tarefas:
                partes_resumo.append("📝 *Tarefas pendentes:*\n" + "\n".join(f"• {t}" for t in tarefas))
            else:
                partes_resumo.append("📝 Nenhuma tarefa registrada.")

            # 📞 Follow-ups
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

            # 📨 Envia tudo junto
            texto = "\n\n".join(partes_resumo)

            try:
                bot = Bot(token=os.getenv("TOKEN"))
                await bot.send_message(chat_id=int(user_id), text=texto, parse_mode="Markdown")
                print(f"✅ Resumo diário enviado para {user_id}")
            except Exception as e:
                logger.error(f"Erro ao enviar resumo diário para {user_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Erro ao gerar resumo diário: {e}")

def start_notificacao_scheduler():
    scheduler = AsyncIOScheduler(timezone=FUSO_BR)
    scheduler.add_job(processar_notificacoes_agendadas, "interval", minutes=15)

    # 🕗 Agenda o envio diário da agenda às 08:00
    scheduler.add_job(enviar_resumo_diario, "cron", hour=8, minute=0)

    scheduler.start()
    print("✅ Scheduler de notificações iniciado com envio diário às 08:00.")