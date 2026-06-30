# handlers/lista_espera_handler.py
"""
F8 MVP — HANDLERS PARA LISTA DE ESPERA

Processa respostas do cliente:
1. Aceitar entrar na lista (resposta a conflito)
2. Confirmar encaixe (resposta a notificação)
3. Rejeitar encaixe (resposta a notificação)
"""

from __future__ import annotations

import logging
from datetime import datetime
from pytz import timezone

from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2,
    limpar_contexto_agendamento_v2,
)
from services.lista_espera_service import (
    criar_lista_espera,
    buscar_lista_espera_por_id,
    marcar_como_notificado,
    marcar_como_convertido,
    marcar_como_cancelado,
)
from services.firebase_service_async import obter_id_dono
from services.event_service_async import criar_evento_com_lock
from services.agenda_lock_service import tem_conflito_real
from services.firebase_service_async import buscar_dado_em_path

logger = logging.getLogger(__name__)
FUSO_BR = timezone("America/Sao_Paulo")


# =========================================================
# ACEITAR ENTRAR EM LISTA DE ESPERA (Fase B)
# =========================================================

async def aceitar_entrar_lista_espera(
    user_id: str,
    contexto: dict,
) -> str:
    """
    [F8-B] Cliente respondeu "sim" após ser oferecida lista de espera em conflito.

    Precondições no contexto:
    - "estado_fluxo": "aguardando_resposta_conflito_lista_espera"
    - "conflito_pendente": {
        "servico": str,
        "profissional": str,
        "data": YYYY-MM-DD,
        "hora_inicio": HH:MM,
        "duracao_minutos": int,
        "evento_id_conflitante": str
      }

    Fluxo:
    1. Extrair dados do conflito
    2. Obter tenant_id (via fallback auditado)
    3. Criar entrada em ListaEspera
    4. Responder ao cliente
    5. Limpar contexto de conflito, preparar para próxima ação

    Returns:
        Mensagem ao cliente
    """
    try:
        # Carregar contexto
        contexto = contexto or {}
        conflito_pendente = contexto.get("conflito_pendente") or {}

        # Validar precondições
        if not conflito_pendente:
            logger.warning(f"[LISTA_ESPERA_ERRO] contexto incompleto para user_id={user_id}")
            return "❌ Desculpa, não consegui anotar seu interesse. Pode tentar de novo?"

        servico = conflito_pendente.get("servico", "")
        profissional = conflito_pendente.get("profissional", "")
        data = conflito_pendente.get("data", "")
        hora_inicio = conflito_pendente.get("hora_inicio", "")
        duracao = conflito_pendente.get("duracao_minutos", 30)
        evento_conflitante_id = conflito_pendente.get("evento_id_conflitante", "")

        if not all([servico, profissional, data, hora_inicio]):
            logger.warning(
                f"[LISTA_ESPERA_ERRO] dados incompletos: "
                f"servico={servico} prof={profissional} data={data} hora={hora_inicio}"
            )
            return "❌ Desculpa, faltaram dados do horário. Pode tentar de novo?"

        # Obter tenant_id via fallback auditado
        # (Em operação crítica, seria obtido no contexto já resolvido)
        tenant_id = await obter_id_dono(user_id)
        if not tenant_id:
            tenant_id = str(user_id)
            logger.warning(f"[TENANT_FALLBACK] aceitar_entrar_lista_espera: user_id={user_id}")

        # Criar entrada em ListaEspera
        resultado = await criar_lista_espera(
            tenant_id=tenant_id,
            actor_id=f"whatsapp:{user_id}",
            cliente_id=user_id,
            cliente_nome=contexto.get("cliente_nome", "Cliente"),
            servico=servico,
            profissional_preferido=profissional,
            data_desejada=data,
            hora_desejada=hora_inicio,
            duracao_minutos=duracao,
            evento_conflitante_id=evento_conflitante_id,
        )

        if resultado.get("status") != "ok":
            logger.error(f"[LISTA_ESPERA_ERRO] criar_lista_espera falhou: {resultado}")
            return "❌ Desculpa, erro ao salvar sua entrada. Pode tentar de novo?"

        waitlist_id = resultado.get("waitlist_id")

        # Limpar contexto de conflito
        await limpar_contexto_agendamento_v2(user_id)

        # Preparar contexto para próxima interação
        await salvar_contexto_temporario_v2(user_id, {
            "estado_fluxo": "aguardando_notificacao_encaixe",
            "waitlist_id": waitlist_id,
        })

        msg = (
            f"✅ Anotei seu interesse! Quando o horário de {servico} com {profissional} "
            f"em {data} às {hora_inicio} vagar, te mando mensagem. "
            f"Fique atento! 🔔"
        )

        logger.info(
            f"[LISTA_ESPERA_ACEITA] user_id={user_id} | waitlist_id={waitlist_id} | "
            f"servico={servico} prof={profissional}"
        )

        return msg

    except Exception as e:
        logger.error(f"❌ aceitar_entrar_lista_espera: {e}", exc_info=True)
        return "❌ Desculpa, erro ao processar. Pode tentar de novo?"


# =========================================================
# CONFIRMAR ENCAIXE APÓS NOTIFICAÇÃO (Fase E-F-G)
# =========================================================

async def confirmar_encaixe_apos_notificacao(
    user_id: str,
    tenant_id: str,
    waitlist_id: str,
) -> dict:
    """
    [F8-E/F/G] Cliente respondeu "sim" após ser notificado de vaga.

    Fluxo:
    1. Buscar doc de ListaEspera
    2. Validar status (deve ser "notificado")
    3. Revalidar disponibilidade com lock
    4. Criar evento com lock (atomicamente)
    5. Marcar waitlist como "convertido"
    6. Resposta ao cliente

    Returns:
        {
            "status": "ok" | "erro",
            "mensagem": str,
            "evento_id": str (if ok)
        }
    """
    try:
        # 1. Buscar ListaEspera
        waitlist_doc = await buscar_lista_espera_por_id(tenant_id, waitlist_id)

        if not waitlist_doc:
            logger.warning(
                f"[ENCAIXE_ERRO] waitlist não encontrada: tenant={tenant_id} waitlist={waitlist_id}"
            )
            return {
                "status": "erro",
                "mensagem": "❌ Desculpa, não encontrei seu registro. Pode tentar de novo?",
            }

        # 2. Validar status
        status_atual = waitlist_doc.get("status")
        if status_atual != "notificado":
            logger.warning(
                f"[ENCAIXE_ERRO] status inválido: esperado 'notificado', got '{status_atual}'"
            )
            return {
                "status": "erro",
                "mensagem": "❌ Desculpa, esse encaixe expirou. Pode tentar de novo?",
            }

        # 3. Extrair dados necessários
        servico_des = waitlist_doc.get("servico_desejado") or {}
        profissional = servico_des.get("profissional_preferido", "")
        data = servico_des.get("data_desejada", "")
        hora_inicio = servico_des.get("hora_desejada", "")
        duracao = servico_des.get("duracao_minutos", 30)
        servico = servico_des.get("servico", "")

        if not all([profissional, data, hora_inicio]):
            logger.error(
                f"[ENCAIXE_ERRO] dados incompletos: prof={profissional} data={data} hora={hora_inicio}"
            )
            return {
                "status": "erro",
                "mensagem": "❌ Desculpa, faltaram dados do encaixe. Pode contatar o salão?",
            }

        # 4. Revalidar disponibilidade com lock
        # (Usa tema_conflito_real que verifica dentro do sistema de locks)
        conflito_agora = await tem_conflito_real(
            dono_id=tenant_id,
            profissional=profissional,
            hora_inicio=hora_inicio,
            hora_fim=_calcular_hora_fim(hora_inicio, duracao),
            excluir_evento_id=None,
        )

        if conflito_agora:
            # Marcar waitlist como cancelado (expirou)
            await marcar_como_cancelado(tenant_id, waitlist_id)
            logger.warning(
                f"[ENCAIXE_ERRO] conflito detectado na confirmação: prof={profissional} "
                f"data={data} hora={hora_inicio}"
            )
            return {
                "status": "erro",
                "mensagem": (
                    "❌ Desculpa, alguém confirmou esse horário nesse meio tempo. "
                    "Pode tentar outro?"
                ),
            }

        # 5. Criar evento com lock (atomicamente)
        cliente_nome = waitlist_doc.get("cliente", {}).get("cliente_nome", "Cliente")
        evento = {
            "cliente_id": user_id,
            "cliente_nome": cliente_nome,
            "servico": servico,
            "profissional": profissional,
            "data": data,
            "hora_inicio": hora_inicio,
            "hora_fim": _calcular_hora_fim(hora_inicio, duracao),
            "duracao": duracao,
            "confirmado": True,
            "status": "confirmado",
            "origem": "encaixe_lista_espera",
            "waitlist_id_origem": waitlist_id,
            "criado_em": datetime.now(FUSO_BR).isoformat(),
        }

        resultado_lock = await criar_evento_com_lock(
            dono_id=tenant_id,
            evento=evento,
            event_id=f"{user_id}_{profissional}_{data}_{hora_inicio}",
        )

        if not resultado_lock.get("ok"):
            await marcar_como_cancelado(tenant_id, waitlist_id)
            logger.error(
                f"[ENCAIXE_ERRO] criar_evento_com_lock falhou: {resultado_lock}"
            )
            return {
                "status": "erro",
                "mensagem": (
                    f"❌ Desculpa, erro ao confirmar. {resultado_lock.get('motivo', 'Tente de novo.')}"
                ),
            }

        evento_id = resultado_lock.get("evento_id")

        # 6. Marcar ListaEspera como "convertido"
        await marcar_como_convertido(tenant_id, waitlist_id, evento_id)

        # 7. Limpar contexto
        await limpar_contexto_agendamento_v2(user_id)

        msg = (
            f"✅ Pronto! Seu horário de {servico} com {profissional} "
            f"está confirmado para {data} às {hora_inicio}. "
            f"Te mandamos um lembrete antes! 📅"
        )

        logger.info(
            f"[ENCAIXE_CONFIRMADO] waitlist={waitlist_id} | evento={evento_id} | "
            f"servico={servico} prof={profissional}"
        )

        return {
            "status": "ok",
            "mensagem": msg,
            "evento_id": evento_id,
        }

    except Exception as e:
        logger.error(f"❌ confirmar_encaixe_apos_notificacao: {e}", exc_info=True)
        return {
            "status": "erro",
            "mensagem": "❌ Desculpa, erro ao confirmar. Pode tentar de novo?",
        }


# =========================================================
# REJEITAR ENCAIXE (Fase E fallback)
# =========================================================

async def rejeitar_encaixe_apos_notificacao(
    tenant_id: str,
    waitlist_id: str,
) -> dict:
    """
    [F8-E fallback] Cliente respondeu "não" após ser notificado de vaga.

    Fluxo:
    1. Marcar ListaEspera como "cancelado"
    2. Responder ao cliente

    Returns:
        {"status": "ok", "mensagem": str}
    """
    try:
        await marcar_como_cancelado(tenant_id, waitlist_id)

        logger.info(f"[ENCAIXE_REJEITADO] waitlist={waitlist_id}")

        return {
            "status": "ok",
            "mensagem": "Sem problemas! Fica de olho em nossa agenda. Qualquer coisa, é só chamar! 👋",
        }

    except Exception as e:
        logger.error(f"❌ rejeitar_encaixe_apos_notificacao: {e}", exc_info=True)
        return {
            "status": "erro",
            "mensagem": "❌ Erro ao processar sua resposta.",
        }


# =========================================================
# UTILIDADES INTERNAS
# =========================================================

def _calcular_hora_fim(hora_inicio: str, duracao_minutos: int) -> str:
    """
    Calcula hora_fim a partir de hora_inicio + duração.
    hora_inicio: "HH:MM"
    duracao_minutos: int

    Returns:
        "HH:MM"
    """
    try:
        from datetime import datetime, timedelta

        h, m = map(int, hora_inicio.split(":"))
        dt_inicio = datetime.combine(datetime.today().date(), __import__("datetime").time(h, m))
        dt_fim = dt_inicio + timedelta(minutes=duracao_minutos)
        return dt_fim.strftime("%H:%M")
    except Exception:
        return hora_inicio
