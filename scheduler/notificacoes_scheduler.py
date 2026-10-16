# scheduler/notificacao_scheduler.py

from datetime import datetime
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uuid
from services.firebase_service_async import (
    buscar_subcolecao,
    atualizar_dado_em_path,
    buscar_dado_em_path,
    buscar_notificacoes_pendentes,
    obter_id_dono,
)
from services.notificacoes_idempotencia_service import (
    tentar_claim_notificacao,
    confirmar_notificacao_processada,
    marcar_notificacao_erro,
)
from services.recorrencia_service import checar_e_propor_recorrencias_todos
import logging
import os

logger = logging.getLogger(__name__)

FUSO_BR = timezone("America/Sao_Paulo")

# 🕐 Atraso máximo permitido antes de marcar notificação como expirada
ATRASO_MAXIMO_NOTIFICACAO_MINUTOS = 15


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


async def _verificar_expiracao_notificacao(notif_id: str, path: str, dt: datetime, agora: datetime):
    """
    Verifica se notificação expirou (muito antiga).
    Se expirada, marca como tal e retorna True.
    Caso contrário, retorna False (pode processar).
    """
    if dt is None or agora is None:
        return False

    atraso = agora - dt
    atraso_minutos = int(atraso.total_seconds() // 60)

    if atraso_minutos > ATRASO_MAXIMO_NOTIFICACAO_MINUTOS:
        # Notificação expirou (muito antiga)
        await atualizar_dado_em_path(f"{path}/{notif_id}", {
            "avisado": True,
            "processada": True,
            "status": "expirada",
            "expirada_em": agora.isoformat(),
            "motivo_expiracao": "notificacao_atrasada",
            "atraso_minutos": atraso_minutos,
            "atualizado_em": agora.isoformat(),
        })
        logger.info(f"⏰ Notificação expirada: notif_id={notif_id} atraso={atraso_minutos}min")
        return True

    return False


async def processar_notificacoes_agendadas():
    logger.info("⏰ processar_notificacoes_agendadas() iniciado...")

    try:
        bot = await _get_bot()
        if bot is None:
            return

        # Identificador único para esta sessão de processamento
        # Usado para garantir idempotência em execuções concorrentes
        processo_id = str(uuid.uuid4())
        logger.info(f"[IDEMPOT] Sessão de processamento: {processo_id}")

        # aqui vêm TODOS os documentos de Clientes (dono + clientes)
        clientes = await buscar_subcolecao("Clientes") or {}
        agora = datetime.now(FUSO_BR)

        for user_id in clientes.keys():
            # 🔐 VALIDAÇÃO DE TENANT: processar apenas donos
            try:
                doc_cli = await buscar_dado_em_path(f"Clientes/{user_id}") or {}
                tipo_usuario = (doc_cli.get("tipo_usuario") or "").strip().lower()

                if tipo_usuario != "dono":
                    logger.info(f"[NOTIF] pulando user_id não-dono: {user_id} tipo_usuario={tipo_usuario}")
                    continue
            except Exception as e:
                logger.warning(f"[NOTIF] erro ao validar tenant {user_id}: {e}")
                continue

            path = f"Clientes/{user_id}/NotificacoesAgendadas"
            notificacoes = await buscar_notificacoes_pendentes(user_id)

            for notif_id, notif in notificacoes.items():
                if not isinstance(notif, dict):
                    continue

                # =========================================================
                # 🔒 IDEMPOTÊNCIA: Tentar obter claim exclusivo
                # =========================================================
                try:
                    sucesso_claim, _ = await tentar_claim_notificacao(
                        user_id, notif_id, processo_id
                    )
                    if not sucesso_claim:
                        logger.info(
                            f"[IDEMPOT] Notificação já está sendo processada: "
                            f"{user_id}/{notif_id}"
                        )
                        continue  # Outro processo tem o claim, pular
                except Exception as e:
                    logger.error(f"[IDEMPOT] Erro ao tentar claim: {user_id}/{notif_id}: {e}")
                    continue

                avisado = bool(notif.get("avisado"))
                status = (notif.get("status") or "").lower()
                if avisado or status == "enviado":
                    continue

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

                # 🕐 Verificar se notificação expirou (muito antiga)
                if await _verificar_expiracao_notificacao(notif_id, path, dt, agora):
                    continue

                canal = (notif.get("canal") or "telegram").lower()

                # 🔑 se o evento foi criado pelo dono, mas era para avisar o cliente,
                # vamos usar o destinatário salvo no documento
                destinatario_id = str(
                    notif.get("destinatario_user_id") or user_id
                )

                # =========================================================
                # ✅ PATCH: confirmação automática de reserva (fechamento)
                # descricao = "CONFIRMAR_RESERVA::<evento_id>"
                # Proteções: validação, reload antes de confirmar, rastreio
                # =========================================================
                try:
                    desc = (notif.get("descricao") or "").strip()
                    if desc.startswith("CONFIRMAR_RESERVA::"):
                        # 🔑 Validar evento_id antes de usar
                        evento_id = desc.split("::", 1)[1].strip() if "::" in desc else ""
                        if not evento_id:
                            # evento_id vazio → erro, não confirmar
                            await atualizar_dado_em_path(f"{path}/{notif_id}", {
                                "avisado": True,
                                "processada": True,
                                "status": "erro",
                                "erro": "CONFIRMAR_RESERVA: evento_id vazio ou inválido",
                                "atualizado_em": agora.isoformat()
                            })
                            logger.warning(f"⚠️ CONFIRMAR_RESERVA sem evento_id: notif_id={notif_id}")
                            continue

                        # Evento padrão salvo no "Clientes/{user_id}/Eventos/{evento_id}"
                        evento_path = f"Clientes/{user_id}/Eventos/{evento_id}"

                        # 🔒 RELOAD: recarregar evento imediatamente antes de confirmar
                        # Detecta race condition (outro scheduler ou operação concorrente)
                        evento = await buscar_dado_em_path(evento_path)
                        evento_status = evento.get("status") if isinstance(evento, dict) else None

                        # 🎯 Confirmar SOMENTE se ainda estiver "reservado"
                        # Preserva estado se já confirmado/cancelado/pendente
                        confirmou = False
                        if isinstance(evento, dict) and evento_status == "reservado":
                            # ✅ Confirmar: reload detectou que ainda está reservado
                            await atualizar_dado_em_path(evento_path, {
                                "status": "confirmado",
                                "confirmado": True,
                                "confirmado_em": agora.isoformat(),
                            })
                            confirmou = True
                            logger.info(f"✅ Reserva confirmada automaticamente: user={user_id} evento={evento_id}")

                        # 📋 Marca notificação com rastreio completo
                        # Sempre finalizar notificação com campos obrigatórios
                        await atualizar_dado_em_path(f"{path}/{notif_id}", {
                            "avisado": True,
                            "processada": True,
                            "status": "enviado",
                            "enviado_em": agora.isoformat(),
                            "tipo_processamento": "confirmacao_reserva",
                            "evento_status_observado": evento_status,
                            "atualizado_em": agora.isoformat()
                        })

                        # ✅ Confirmar que foi processada com sucesso
                        try:
                            await confirmar_notificacao_processada(
                                user_id, notif_id, processo_id
                            )
                        except Exception as confirm_e:
                            logger.warning(
                                f"[IDEMPOT] Erro ao confirmar CONFIRMAR_RESERVA: "
                                f"{user_id}/{notif_id}: {confirm_e}"
                            )

                        # IMPORTANTE: não envia mensagem para este tipo de notificação
                        continue

                except Exception as e:
                    logger.error(f"❌ Erro ao processar CONFIRMAR_RESERVA para {destinatario_id}: {e}")

                    # ❌ Erro em CONFIRMAR_RESERVA → liberar claim
                    try:
                        await marcar_notificacao_erro(
                            user_id, notif_id, processo_id,
                            f"CONFIRMAR_RESERVA: {str(e)}"
                        )
                    except Exception as mark_e:
                        logger.error(f"[IDEMPOT] Erro ao marcar erro: {mark_e}")
                    continue

                # =========================================================
                # ✅ Fluxo normal de lembrete/notificação
                # =========================================================
                mensagem = notif.get("mensagem")
                if not mensagem:
                    desc = (notif.get("descricao") or "compromisso").strip()
                    alvo = notif.get("alvo_evento") or {}
                    data_ev = (alvo.get("data") or "")
                    hora_ev = (alvo.get("hora_inicio") or "")
                    min_antes = int(notif.get("minutos_antes") or 30)

                    desc_lower = desc.lower()
                    tipo_legivel = "reunião" if "reuni" in desc_lower else desc_lower

                    hoje_str = datetime.now(FUSO_BR).strftime("%Y-%m-%d")
                    if data_ev and hora_ev:
                        quando = f" — hoje às {hora_ev}" if data_ev == hoje_str else f" — {data_ev} às {hora_ev}"
                    else:
                        quando = ""

                    sufixo_min = "minuto" if min_antes == 1 else "minutos"
                    mensagem = f"🔔 Não esqueça: sua {tipo_legivel} começa em {min_antes} {sufixo_min}{quando}."

                try:
                    if canal == "telegram":
                        await bot.send_message(chat_id=int(destinatario_id), text=mensagem)
                    elif canal == "whatsapp":
                        from services.whatsapp_service import enviar_mensagem_whatsapp
                        await enviar_mensagem_whatsapp(destinatario_id, mensagem)
                    else:
                        await bot.send_message(chat_id=int(destinatario_id), text=mensagem)

                    # ✅ Envio bem-sucedido → confirmar processamento
                    try:
                        await confirmar_notificacao_processada(
                            user_id, notif_id, processo_id
                        )
                    except Exception as confirm_e:
                        logger.error(
                            f"[IDEMPOT] Erro ao confirmar: {user_id}/{notif_id}: {confirm_e}"
                        )
                        # Continuamos mesmo com erro na confirmação (já foi enviada)
                        await atualizar_dado_em_path(f"{path}/{notif_id}", {
                            "avisado": True,
                            "status": "enviado",
                            "enviado_em": agora.isoformat(),
                            "confirmacao_erro": str(confirm_e)
                        })

                    logger.info(f"✅ Notificação enviada para {destinatario_id} via {canal}: {mensagem}")

                except Exception as e:
                    logger.error(f"Erro ao enviar notificação para {destinatario_id} via {canal}: {e}")

                    # ❌ Envio falhou → marcar erro e liberar claim
                    try:
                        await marcar_notificacao_erro(
                            user_id, notif_id, processo_id,
                            f"Envio {canal}: {str(e)}"
                        )
                    except Exception as mark_e:
                        logger.error(f"[IDEMPOT] Erro ao marcar erro: {mark_e}")

    except Exception as e:
        logger.error(f"❌ Erro na rotina de notificações: {e}")


async def enviar_resumo_diario():
    logger.info("📋 enviar_resumo_diario() iniciado...")
    try:
        bot = await _get_bot()
        if bot is None:
            return

        from services.event_service_async import buscar_eventos_por_intervalo
        from services.identidade_service import buscar_profissional_por_nome

        clientes = await buscar_subcolecao("Clientes") or {}
        hoje = datetime.now(FUSO_BR).date()
        hoje_str = hoje.strftime("%Y-%m-%d")

        # 🔒 IDEMPOTÊNCIA: ID único para esta execução do resumo
        processo_id = str(uuid.uuid4())
        logger.info(f"[RESUMO-IDEMPOT] Sessão: {processo_id}")

        for user_id in clientes.keys():
            try:
                doc_cli = await buscar_dado_em_path(f"Clientes/{user_id}") or {}
                tipo_usuario = (doc_cli or {}).get("tipo_usuario") or "cliente"

                # 🎯 ROTEAMENTO POR TIPO DE USUÁRIO
                if tipo_usuario == "dono":
                    # =========================================================
                    # 📋 RESUMO PARA DONO: eventos + tarefas + follow-ups
                    # =========================================================
                    tenant_id = user_id
                    notif_id = f"resumo_{user_id}_{hoje_str}"

                    # 🔒 IDEMPOTÊNCIA: Tentar claim
                    try:
                        sucesso_claim, _ = await tentar_claim_notificacao(
                            tenant_id, notif_id, processo_id
                        )
                        if not sucesso_claim:
                            logger.info(f"[RESUMO-IDEMPOT] Resumo já em processamento: {user_id}")
                            continue
                    except Exception as e:
                        logger.error(f"[RESUMO-IDEMPOT] Erro ao tentar claim DONO {user_id}: {e}")
                        continue

                    partes_resumo = []

                    # Eventos de hoje
                    eventos = await buscar_eventos_por_intervalo(user_id, dia_especifico=hoje)
                    if eventos:
                        partes_resumo.append("📅 *Eventos de hoje:*\n" + "\n".join(f"• {e}" for e in eventos))
                    else:
                        partes_resumo.append("📅 Nenhum evento agendado.")

                    # Tarefas pendentes
                    tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas") or {}
                    tarefas = [t["descricao"] for t in tarefas_dict.values() if isinstance(t, dict) and t.get("descricao")]
                    if tarefas:
                        partes_resumo.append("📝 *Tarefas pendentes:*\n" + "\n".join(f"• {t}" for t in tarefas))
                    else:
                        partes_resumo.append("📝 Nenhuma tarefa registrada.")

                    # Follow-ups de hoje
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

                        # ✅ Envio bem-sucedido → confirmar
                        try:
                            await confirmar_notificacao_processada(
                                tenant_id, notif_id, processo_id
                            )
                        except Exception as confirm_e:
                            logger.error(f"[RESUMO-IDEMPOT] Erro ao confirmar DONO {user_id}: {confirm_e}")

                        logger.info(f"✅ Resumo diário DONO enviado para {user_id}")
                    except Exception as e:
                        logger.error(f"Erro ao enviar resumo para DONO {user_id}: {e}")

                        # ❌ Envio falhou → marcar erro
                        try:
                            await marcar_notificacao_erro(
                                tenant_id, notif_id, processo_id,
                                f"Envio DONO: {str(e)}"
                            )
                        except Exception as mark_e:
                            logger.error(f"[RESUMO-IDEMPOT] Erro ao marcar erro DONO: {mark_e}")

                elif tipo_usuario == "cliente":
                    # =========================================================
                    # 📅 RESUMO PARA CLIENTE: apenas seus agendamentos
                    # =========================================================
                    dono_id = await obter_id_dono(user_id)
                    if not dono_id:
                        logger.warning(f"[RESUMO] Usuário {user_id} sem tenant vinculado; resumo ignorado")
                        continue

                    tenant_id = dono_id
                    notif_id = f"resumo_{user_id}_{hoje_str}"

                    # 🔒 IDEMPOTÊNCIA: Tentar claim
                    try:
                        sucesso_claim, _ = await tentar_claim_notificacao(
                            tenant_id, notif_id, processo_id
                        )
                        if not sucesso_claim:
                            logger.info(f"[RESUMO-IDEMPOT] Resumo já em processamento: {user_id}")
                            continue
                    except Exception as e:
                        logger.error(f"[RESUMO-IDEMPOT] Erro ao tentar claim CLIENTE {user_id}: {e}")
                        continue

                    eventos_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos") or {}

                    # Filtrar apenas eventos deste cliente
                    eventos_cliente = []
                    for evento_id, evento in eventos_dict.items():
                        if isinstance(evento, dict):
                            if evento.get("data") == hoje_str and evento.get("cliente_id") == user_id:
                                prof = evento.get("profissional", "profissional não confirmado")
                                hora = evento.get("hora_inicio", "horário não confirmado")
                                desc = evento.get("descricao", "serviço")
                                eventos_cliente.append(f"• {desc} com {prof} às {hora}")

                    if eventos_cliente:
                        texto = "📅 *Seus agendamentos de hoje:*\n" + "\n".join(eventos_cliente)
                    else:
                        texto = "📅 Você não tem agendamentos para hoje."

                    try:
                        await bot.send_message(chat_id=int(user_id), text=texto, parse_mode="Markdown")

                        # ✅ Envio bem-sucedido → confirmar
                        try:
                            await confirmar_notificacao_processada(
                                tenant_id, notif_id, processo_id
                            )
                        except Exception as confirm_e:
                            logger.error(f"[RESUMO-IDEMPOT] Erro ao confirmar CLIENTE {user_id}: {confirm_e}")

                        logger.info(f"✅ Resumo diário CLIENTE enviado para {user_id}")
                    except Exception as e:
                        logger.error(f"Erro ao enviar resumo para CLIENTE {user_id}: {e}")

                        # ❌ Envio falhou → marcar erro
                        try:
                            await marcar_notificacao_erro(
                                tenant_id, notif_id, processo_id,
                                f"Envio CLIENTE: {str(e)}"
                            )
                        except Exception as mark_e:
                            logger.error(f"[RESUMO-IDEMPOT] Erro ao marcar erro CLIENTE: {mark_e}")

                elif tipo_usuario == "profissional":
                    # =========================================================
                    # 📅 RESUMO PARA PROFISSIONAL: seus agendamentos de hoje
                    # =========================================================
                    dono_id = await obter_id_dono(user_id)
                    if not dono_id:
                        logger.warning(f"[RESUMO] Usuário {user_id} sem tenant vinculado; resumo ignorado")
                        continue

                    prof_nome = (doc_cli or {}).get("nome", "")

                    if not prof_nome:
                        logger.warning(f"[RESUMO_PROF] profissional {user_id} sem nome cadastrado, pulando")
                        continue

                    tenant_id = dono_id
                    notif_id = f"resumo_{user_id}_{hoje_str}"

                    # 🔒 IDEMPOTÊNCIA: Tentar claim
                    try:
                        sucesso_claim, _ = await tentar_claim_notificacao(
                            tenant_id, notif_id, processo_id
                        )
                        if not sucesso_claim:
                            logger.info(f"[RESUMO-IDEMPOT] Resumo já em processamento: {user_id}")
                            continue
                    except Exception as e:
                        logger.error(f"[RESUMO-IDEMPOT] Erro ao tentar claim PROFISSIONAL {user_id}: {e}")
                        continue

                    eventos_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos") or {}

                    # Filtrar apenas eventos deste profissional
                    eventos_prof = []
                    for evento_id, evento in eventos_dict.items():
                        if isinstance(evento, dict):
                            if evento.get("data") == hoje_str and \
                               str(evento.get("profissional", "")).lower() == prof_nome.lower():
                                cliente = evento.get("cliente_nome", "cliente")
                                hora = evento.get("hora_inicio", "horário não confirmado")
                                desc = evento.get("descricao", "serviço")
                                eventos_prof.append(f"• {desc} com {cliente} às {hora}")

                    if eventos_prof:
                        texto = f"📅 *Seus agendamentos de hoje ({prof_nome}):*\n" + "\n".join(eventos_prof)
                    else:
                        texto = f"📅 {prof_nome}, você não tem agendamentos para hoje."

                    try:
                        await bot.send_message(chat_id=int(user_id), text=texto, parse_mode="Markdown")

                        # ✅ Envio bem-sucedido → confirmar
                        try:
                            await confirmar_notificacao_processada(
                                tenant_id, notif_id, processo_id
                            )
                        except Exception as confirm_e:
                            logger.error(f"[RESUMO-IDEMPOT] Erro ao confirmar PROFISSIONAL {user_id}: {confirm_e}")

                        logger.info(f"✅ Resumo diário PROFISSIONAL enviado para {user_id} ({prof_nome})")
                    except Exception as e:
                        logger.error(f"Erro ao enviar resumo para PROFISSIONAL {user_id}: {e}")

                        # ❌ Envio falhou → marcar erro
                        try:
                            await marcar_notificacao_erro(
                                tenant_id, notif_id, processo_id,
                                f"Envio PROFISSIONAL: {str(e)}"
                            )
                        except Exception as mark_e:
                            logger.error(f"[RESUMO-IDEMPOT] Erro ao marcar erro PROFISSIONAL: {mark_e}")

                else:
                    logger.info(f"[RESUMO] tipo_usuario desconhecido: {tipo_usuario} para {user_id}, pulando")

            except Exception as e:
                logger.error(f"❌ Erro ao processar resumo para {user_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Erro ao gerar/enviar resumo diário: {e}")


# =========================================================
# 🕐 VERIFICAÇÃO DE SESSÕES EXPIRADAS (P0 PROATIVO)
# Reutiliza lógica de _validar_expiração_sessao do router
# =========================================================

async def verificar_e_avisar_sessoes_expiradas():
    """Verifica sessões de agendamento expiradas e envia aviso via WhatsApp/Telegram.

    Reutiliza a lógica de _validar_expiração_sessao() de router/principal_router.py
    para determinar elegibilidade de expiração.

    Estratégia de idempotência:
    - Flag _aviso_expiracao_enviado previne duplicação
    - Timestamp registra quando aviso foi enviado
    - Sem claim exclusivo (simples read-check-write)
    """
    from datetime import datetime, timezone
    import dateutil.parser
    from services.firebase_service_async import atualizar_dado_em_path, buscar_subcolecao

    TIMEOUT_SECONDS = 3600  # 60 minutos (sincronizado com principal_router.py:3857)

    logger.info("⏰ verificar_e_avisar_sessoes_expiradas() iniciado...")

    try:
        # 1️⃣ VARREDURA: Todos os tenants (donos)
        clientes = await buscar_subcolecao("Clientes") or {}
        agora = datetime.now(timezone.utc)

        sessoes_processadas = 0
        sessoes_expiradas = 0
        avisos_enviados = 0

        for tenant_id in clientes.keys():
            try:
                # Validação de tenant
                doc_cli = await buscar_dado_em_path(f"Clientes/{tenant_id}") or {}
                tipo_usuario = (doc_cli.get("tipo_usuario") or "").strip().lower()

                if tipo_usuario != "dono":
                    logger.debug(f"[EXPIR] Pulando não-dono: {tenant_id}")
                    continue

                # 2️⃣ SESSÕES: Todas as sessões deste tenant
                path_sessoes = f"Clientes/{tenant_id}/Sessoes"
                sessoes = await buscar_subcolecao(path_sessoes) or {}

                for actor_id, ctx in sessoes.items():
                    if not isinstance(ctx, dict):
                        continue

                    sessoes_processadas += 1

                    # 3️⃣ CRITÉRIO 1: Não processa se estado = idle
                    estado_fluxo = ctx.get("estado_fluxo", "idle").strip().lower()
                    if estado_fluxo == "idle":
                        continue

                    # 4️⃣ CRITÉRIO 2: Timestamp válido?
                    timestamp_atividade = ctx.get("_last_client_activity")
                    if not timestamp_atividade:
                        logger.debug(f"[EXPIR] Sessão sem timestamp: {tenant_id}/{actor_id}")
                        continue

                    # 5️⃣ VALIDAÇÃO DE TIMEZONE
                    try:
                        ts_atividade = dateutil.parser.isoparse(timestamp_atividade)

                        if ts_atividade.tzinfo is None or ts_atividade.utcoffset() is None:
                            logger.warning(f"[EXPIR-TZ] Timestamp sem fuso: {tenant_id}/{actor_id}")
                            continue

                        tempo_decorrido = (agora - ts_atividade).total_seconds()
                    except Exception as e:
                        logger.warning(f"[EXPIR-PARSE] Erro ao parsear timestamp: {e}")
                        continue

                    # 6️⃣ CRITÉRIO 3: Expirou por inatividade?
                    if tempo_decorrido < TIMEOUT_SECONDS:
                        continue

                    logger.info(f"[EXPIR-DETECTED] Sessão expirada: {tenant_id}/{actor_id} "
                               f"inatividade={tempo_decorrido/60:.1f}min")
                    sessoes_expiradas += 1

                    # 7️⃣ IDEMPOTÊNCIA: Já enviou aviso recentemente?
                    aviso_enviado = ctx.get("_aviso_expiracao_enviado")
                    if aviso_enviado:
                        try:
                            ts_aviso = dateutil.parser.isoparse(aviso_enviado)
                            tempo_desde_aviso = (agora - ts_aviso).total_seconds()

                            # Se aviso foi enviado há menos de 6 horas, não reenvia
                            if tempo_desde_aviso < 21600:  # 6 horas
                                logger.info(f"[EXPIR-SKIP] Aviso já enviado há {tempo_desde_aviso/60:.0f}min")
                                continue
                        except:
                            pass  # Flag inválida, reenviar

                    # 8️⃣ CHECK: Evento já foi criado? (proteção race condition)
                    draft = ctx.get("draft_agendamento", {})
                    cliente_id_draft = ctx.get("cliente_id") or actor_id
                    profissional = draft.get("profissional", "").strip()
                    data = draft.get("data", "").strip()
                    hora_inicio = draft.get("hora_inicio", "").strip()

                    evento_existe = False
                    if cliente_id_draft and profissional and data and hora_inicio:
                        try:
                            # Normalizar hora (mesmo algoritmo que salvar_evento)
                            h, m = map(int, str(hora_inicio).split(":"))
                            m = (m // 20) * 20
                            hora_normalizada = f"{h:02d}:{m:02d}"

                            base_id = f"{cliente_id_draft}_{profissional}_{data}_{hora_normalizada}"
                            event_id = base_id.replace(" ", "_").lower()

                            path_evento = f"Clientes/{tenant_id}/Eventos/{event_id}"
                            evento = await buscar_dado_em_path(path_evento)

                            if evento:
                                logger.info(f"[EXPIR-EVENTO-EXISTS] Evento já criado, pulando aviso")
                                evento_existe = True
                        except Exception as e:
                            logger.warning(f"[EXPIR-EVENTO-CHECK] Erro ao verificar evento: {e}")

                    if evento_existe:
                        # Não avisar se evento já foi criado
                        continue

                    # 9️⃣ COMPOSIÇÃO DA MENSAGEM
                    mensagem_timeout = (
                        "Oi! 😊 Como ficamos 1 hora sem atividade, encerrei esse atendimento como não concluído.\n\n"
                        "Não se preocupe: esse atendimento não gerou um novo agendamento, e nenhum agendamento já "
                        "confirmado foi cancelado.\n\n"
                        "Quando quiser, é só me chamar novamente para começarmos do zero. Estou à disposição! 💜"
                    )

                    # 🔟 ENVIO: Determinar canal e enviar
                    # Tentar extrair wa_id do actor_id (prefixo whatsapp:)
                    canal = "telegram"  # padrão
                    destinatario_id = actor_id

                    if actor_id.startswith("whatsapp:"):
                        canal = "whatsapp"
                        destinatario_id = actor_id.split(":")[-1]  # Extrair wa_id

                    sucesso_envio = False
                    try:
                        if canal == "whatsapp":
                            from services.whatsapp_service import enviar_mensagem_whatsapp
                            result = await enviar_mensagem_whatsapp(destinatario_id, mensagem_timeout)
                            sucesso_envio = result.get("success", False)

                            if sucesso_envio:
                                logger.info(f"[EXPIR-WA] WhatsApp enviado: {destinatario_id}")
                            else:
                                logger.error(f"[EXPIR-WA-FAIL] WhatsApp falhou: {result.get('error')}")
                        else:
                            # Telegram — tenta via bot se disponível
                            bot = await _get_bot()
                            if bot:
                                await bot.send_message(chat_id=int(actor_id), text=mensagem_timeout)
                                sucesso_envio = True
                                logger.info(f"[EXPIR-TG] Telegram enviado: {actor_id}")
                            else:
                                logger.warning(f"[EXPIR-TG-FAIL] Bot não disponível para {actor_id}")
                    except Exception as e:
                        logger.error(f"[EXPIR-SEND] Erro ao enviar para {destinatario_id}: {e}")

                    # 1️⃣1️⃣ LIMPEZA + MARCAÇÃO
                    try:
                        from utils.contexto_temporario import limpar_contexto_agendamento_v2_transacional

                        resultado_limpeza = await limpar_contexto_agendamento_v2_transacional(tenant_id, actor_id)

                        if resultado_limpeza:
                            # Adicionar flag de aviso enviado (para idempotência)
                            payload_aviso = {
                                "_aviso_expiracao_enviado": agora.isoformat(),
                                "_aviso_canal": canal,
                                "_aviso_destinatario": destinatario_id,
                                "_aviso_sucesso": sucesso_envio,
                            }

                            await atualizar_dado_em_path(
                                f"Clientes/{tenant_id}/Sessoes/{actor_id}",
                                payload_aviso
                            )

                            avisos_enviados += 1
                            logger.info(f"[EXPIR-OK] Sessão limpa e aviso marcado: {tenant_id}/{actor_id}")
                        else:
                            logger.warning(f"[EXPIR-LIMPEZA-FAIL] Limpeza falhou (evento pode ter sido criado)")

                    except Exception as e:
                        logger.error(f"[EXPIR-CLEANUP] Erro ao limpar contexto: {e}")

            except Exception as e:
                logger.error(f"[EXPIR] Erro processando tenant {tenant_id}: {e}")

        logger.info(f"✅ Varredura concluída: processadas={sessoes_processadas}, "
                   f"expiradas={sessoes_expiradas}, avisos_enviados={avisos_enviados}")

    except Exception as e:
        logger.error(f"❌ Erro geral em verificar_e_avisar_sessoes_expiradas(): {e}")


def start_notificacao_scheduler():
    scheduler = AsyncIOScheduler(timezone=FUSO_BR)

    # ⚠️ [REMOVIDO] Scheduler de notificações a cada 1 minuto
    # Motivo: Consumo excessivo de reads no Firestore (1440 execuções/dia)
    # Alternativa: /cron/ping (UptimeRobot) aciona processar_notificacoes_agendadas() 288 vezes/dia
    # A função processar_notificacoes_agendadas() continua acessível via /cron/ping

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