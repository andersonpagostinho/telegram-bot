"""
Serviço de Idempotência para Notificações (C4.2.5 — Lock Atômico)
Path: Clientes/{tenant_id}/NotificacoesAgendadas/{notif_id}/locks/{notif_id}
"""

from datetime import datetime, timedelta
import pytz
import logging
import asyncio
from typing import Optional, Tuple

from services.firebase_service_async import (
    buscar_dado_em_path,
    atualizar_dado_em_path,
    get_ref_from_path,
)

logger = logging.getLogger(__name__)
FUSO_BR = pytz.timezone("America/Sao_Paulo")
CLAIM_TIMEOUT_MINUTOS = 1


async def tentar_claim_notificacao(
    tenant_id: str,
    notif_id: str,
    processo_id: str,
    max_tentativas: int = 5
) -> Tuple[bool, Optional[dict]]:
    """Tenta assumir (claim) notificação com lock document atômico."""

    from google.api_core import exceptions

    notif_path = f"Clientes/{tenant_id}/NotificacoesAgendadas/{notif_id}"
    lock_path = f"{notif_path}/locks/{notif_id}"
    agora = datetime.now(FUSO_BR)

    for tentativa in range(max_tentativas):
        try:
            notif = await buscar_dado_em_path(notif_path)

            if notif is None:
                return (False, None)

            if notif.get("avisado") or notif.get("status") in ["avisado", "expirada"]:
                return (False, notif)

            if notif.get("status") == "processando":
                processando_em = notif.get("processando_em")
                if processando_em:
                    try:
                        claim_dt = datetime.fromisoformat(processando_em)
                        if claim_dt.tzinfo is None:
                            claim_dt = FUSO_BR.localize(claim_dt)
                        else:
                            claim_dt = claim_dt.astimezone(FUSO_BR)

                        tempo_decorrido = agora - claim_dt
                        if tempo_decorrido < timedelta(minutes=CLAIM_TIMEOUT_MINUTOS):
                            return (False, notif)
                    except:
                        pass

            lock_data = {
                "processo_id": processo_id,
                "claimed_at": agora.isoformat(),
                "expires_at": (agora + timedelta(minutes=CLAIM_TIMEOUT_MINUTOS)).isoformat(),
                "status": "ACTIVE"
            }

            lock_ref = get_ref_from_path(lock_path)
            await lock_ref.create(lock_data)

            await atualizar_dado_em_path(notif_path, {
                "status": "processando",
                "avisado": False,
                "processando_em": agora.isoformat(),
                "processo_id": processo_id,
                "atualizado_em": agora.isoformat(),
            })

            logger.info(f"[CLAIM] Lock obtido: {tenant_id}/{notif_id}")
            return (True, notif)

        except exceptions.AlreadyExists:
            logger.info(f"[CLAIM] Lock existe: {tenant_id}/{notif_id}")
            return (False, notif if 'notif' in locals() else None)

        except Exception as e:
            if tentativa < max_tentativas - 1:
                await asyncio.sleep(0.01 * (2 ** tentativa))
            else:
                logger.error(f"[CLAIM] Erro: {tenant_id}/{notif_id}: {e}")
                return (False, None)

    return (False, None)


async def confirmar_notificacao_processada(
    tenant_id: str,
    notif_id: str,
    processo_id: str,
    enviado_em: Optional[datetime] = None
) -> bool:
    """Marca notificação como processada com sucesso."""

    if enviado_em is None:
        enviado_em = datetime.now(FUSO_BR)

    path = f"Clientes/{tenant_id}/NotificacoesAgendadas/{notif_id}"

    try:
        notif = await buscar_dado_em_path(path)

        if notif is None:
            return False

        processo_id_atual = notif.get("processo_id")
        if processo_id_atual and processo_id_atual != processo_id:
            logger.warning(f"[CONFIRM] Processo {processo_id} vs {processo_id_atual}")
            return False

        await atualizar_dado_em_path(path, {
            "avisado": True,
            "status": "enviado",
            "enviado_em": enviado_em.isoformat(),
            "processo_id": None,
            "processando_em": None,
            "atualizado_em": datetime.now(FUSO_BR).isoformat(),
        })

        logger.info(f"[CONFIRM] OK: {tenant_id}/{notif_id}")
        return True

    except Exception as e:
        logger.error(f"[CONFIRM] Erro: {tenant_id}/{notif_id}: {e}")
        return False


async def marcar_notificacao_erro(
    tenant_id: str,
    notif_id: str,
    processo_id: str,
    erro_msg: str
) -> bool:
    """Marca notificação com erro e deleta lock para permitir retry."""

    path = f"Clientes/{tenant_id}/NotificacoesAgendadas/{notif_id}"
    lock_path = f"{path}/locks/{notif_id}"
    agora = datetime.now(FUSO_BR)

    try:
        await atualizar_dado_em_path(path, {
            "status": "erro",
            "erro": erro_msg,
            "avisado": False,
            "processo_id": None,
            "processando_em": None,
            "atualizado_em": agora.isoformat(),
        })

        try:
            lock_ref = get_ref_from_path(lock_path)
            await lock_ref.delete()
        except:
            pass

        logger.warning(f"[ERROR] {tenant_id}/{notif_id}: {erro_msg}")
        return True

    except Exception as e:
        logger.error(f"[ERROR] Erro ao marcar: {tenant_id}/{notif_id}: {e}")
        return False


async def liberar_claim_abandonado(
    tenant_id: str,
    notif_id: str,
    timeout_minutos: int = CLAIM_TIMEOUT_MINUTOS
) -> bool:
    """Compatibilidade: lock document expira naturalmente."""

    path = f"Clientes/{tenant_id}/NotificacoesAgendadas/{notif_id}"
    agora = datetime.now(FUSO_BR)

    try:
        notif = await buscar_dado_em_path(path)

        if notif is None or notif.get("status") != "processando":
            return False

        claim_em = notif.get("processando_em")
        if not claim_em:
            return False

        try:
            claim_datetime = datetime.fromisoformat(claim_em)
            if claim_datetime.tzinfo is None:
                claim_datetime = FUSO_BR.localize(claim_datetime)
            else:
                claim_datetime = claim_datetime.astimezone(FUSO_BR)

            tempo_decorrido = agora - claim_datetime
            timeout = timedelta(minutes=timeout_minutos)

            if tempo_decorrido >= timeout:
                await atualizar_dado_em_path(path, {
                    "status": "pendente",
                    "processo_id": None,
                    "processando_em": None,
                    "atualizado_em": agora.isoformat(),
                })
                logger.info(f"[RECOVER] OK: {tenant_id}/{notif_id}")
                return True
            else:
                return False
        except:
            return False

    except Exception as e:
        logger.error(f"[RECOVER] Erro: {tenant_id}/{notif_id}: {e}")
        return False
