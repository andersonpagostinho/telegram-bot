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

def _parse_iso_br(dt_str: str):
    """Aceita ISO com/sem timezone. Se vier naive, assume FUSO_BR."""
    try:
        # remove Z -> +00:00 para fromisoformat entender
        s = (dt_str or "").replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            # assume horário de São Paulo quando for naive
            return FUSO_BR.localize(dt)
        return dt.astimezone(FUSO_BR)
    except Exception as e:
        logger.error(f"parse data_hora inválida: {dt_str} -> {e}")
        return None

async def processar_notificacoes_agendadas():
    print("⏰ Verificando notificações agendadas...")

    try:
        clientes = await buscar_subcolecao("Clientes") or {}
        agora = datetime.now(FUSO_BR)

        # usa a instância do bot já criada em main (evita depender de env TOKEN aqui)
        try:
            from main import application
            bot = application.bot
        except Exception as e:
            logger.error(f"Não consegui obter application.bot: {e}")
            return

        for user_id in clientes.keys():
            path = f"Clientes/{user_id}/NotificacoesAgendadas"
            notificacoes = await buscar_subcolecao(path) or {}

            for notif_id, notif in notificacoes.items():
                if not isinstance(notif, dict):
                    continue

                # compat: considerado “já enviado” se avisado=True OU status='enviado'
                avisado = bool(notif.get("avisado"))
                status = (notif.get("status") or "").lower()
                if avisado or status == "enviado":
                    continue

                dt = _parse_iso_br(notif.get("data_hora", ""))
                if not dt:
                    # marca erro para não ficar reprocessando sempre
                    await atualizar_dado_em_path(f"{path}/{notif_id}", {
                        "status": "erro",
                        "erro": "data_hora inválida",
                        "atualizado_em": agora.isoformat()
                    })
                    continue

                # só dispara se já passou da hora no fuso BR
                if dt > agora:
                    continue

                # monta mensagem (fallbacks)
                mensagem = notif.get("mensagem")
                if not mensagem:
                    desc = notif.get("descricao", "Lembrete")
                    alvo = notif.get("alvo_evento") or {}
                    quando = ""
                    if alvo.get("data") and alvo.get("hora_inicio"):
                        quando = f"\n🗓️ {alvo['data']} às {alvo['hora_inicio']}"
                    mensagem = f"⏰ {desc}{quando}"

                canal = (notif.get("canal") or "telegram").lower()

                try:
                    if canal == "telegram":
                        await bot.send_message(chat_id=int(user_id), text=mensagem)
                    elif canal == "whatsapp":
                        from services.whatsapp_service import enviar_mensagem_whatsapp
                        await enviar_mensagem_whatsapp(user_id, mensagem)
                    else:
                        # canal desconhecido → tenta telegram
                        await bot.send_message(chat_id=int(user_id), text=mensagem)

                    # marca como enviado (compat com ambos esquemas)
                    await atualizar_dado_em_path(f"{path}/{notif_id}", {
                        "avisado": True,
                        "status": "enviado",
                        "enviado_em": agora.isoformat()
                    })
                    print(f"✅ Notificação enviada para {user_id} via {canal}: {mensagem}")

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

    # ✅ verificação a cada 15 minuto
    scheduler.add_job(processar_notificacoes_agendadas, "interval", minutes=15)

    # 🕗 resumo diário às 08:00
    scheduler.add_job(enviar_resumo_diario, "cron", hour=8, minute=0)

    scheduler.start()
    print("✅ Scheduler de notificações iniciado (loop a cada 15 minuto, resumo 08:00).")