"""
Serviço de Lock para /cron/ping - Execução Única Global
Usa Firestore com expiração para prevenir sobreposição entre instâncias
"""

from datetime import datetime, timedelta
import pytz
import logging
import uuid
from typing import Tuple, Optional

from services.firebase_service_async import (
    get_ref_from_path,
)

logger = logging.getLogger(__name__)
FUSO_BR = pytz.timezone("America/Sao_Paulo")

# Lock válido por 120 segundos (timeout HTTP + buffer)
CRON_LOCK_TIMEOUT_SEGUNDOS = 120
CRON_LOCK_PATH = "Sistema/CronLocks/processar_notificacoes"


async def tentar_claim_cron() -> Tuple[bool, str]:
    """
    Tenta reivindicar (claim) lock global para /cron/ping.

    Retorna:
        (True, lock_id) se conseguiu lock
        (False, motivo) se já há execução ativa
    """
    from google.api_core import exceptions

    try:
        agora = datetime.now(FUSO_BR)
        lock_id = str(uuid.uuid4())

        lock_data = {
            "lock_id": lock_id,
            "iniciado_em": agora.isoformat(),
            "expira_em": (agora + timedelta(seconds=CRON_LOCK_TIMEOUT_SEGUNDOS)).isoformat(),
            "status": "ACTIVE",
        }

        lock_ref = get_ref_from_path(CRON_LOCK_PATH)

        # Tentar criar: se já existe, AlreadyExists é lançado
        await lock_ref.create(lock_data)

        logger.info(f"[CRON-LOCK] Lock obtido (ID: {lock_id})")
        return (True, lock_id)

    except exceptions.AlreadyExists:
        # Lock já existe - verificar se expirou
        try:
            lock_ref = get_ref_from_path(CRON_LOCK_PATH)
            doc = await lock_ref.get()

            if doc.exists:
                data = doc.to_dict()
                expira_em_str = data.get("expira_em", "")

                try:
                    expira_em = datetime.fromisoformat(expira_em_str)
                    if expira_em.tzinfo is None:
                        expira_em = FUSO_BR.localize(expira_em)
                    else:
                        expira_em = expira_em.astimezone(FUSO_BR)

                    agora = datetime.now(FUSO_BR)
                    if agora >= expira_em:
                        # Lock expirou - deletar e tentar novamente
                        logger.warning(f"[CRON-LOCK] Lock expirado, removendo")
                        await lock_ref.delete()
                        # Recursar uma vez
                        return await tentar_claim_cron()
                    else:
                        # Lock ativo
                        tempo_restante = (expira_em - agora).total_seconds()
                        logger.warning(f"[CRON-LOCK] Execução já ativa ({tempo_restante:.0f}s restantes)")
                        return (False, f"already_processing_{tempo_restante:.0f}s")
                except Exception as e:
                    logger.warning(f"[CRON-LOCK] Erro ao parse de expiração: {e}")
                    return (False, "lock_exists_parse_error")
            else:
                # Doc não existe mais (race condition)
                return (False, "lock_race_condition")
        except Exception as e:
            logger.error(f"[CRON-LOCK] Erro ao verificar lock: {e}")
            return (False, f"lock_check_error_{str(e)[:30]}")

    except Exception as e:
        logger.error(f"[CRON-LOCK] Erro ao reivindicar lock: {e}")
        return (False, f"lock_claim_error_{str(e)[:30]}")


async def liberar_cron_lock(lock_id: str) -> bool:
    """
    Libera lock global após conclusão ou erro.

    Args:
        lock_id: ID do lock a liberar

    Returns:
        True se liberou, False se houve erro
    """
    try:
        lock_ref = get_ref_from_path(CRON_LOCK_PATH)
        doc = await lock_ref.get()

        if not doc.exists:
            logger.warning(f"[CRON-LOCK] Lock já foi removido ({lock_id})")
            return True

        data = doc.to_dict()
        if data.get("lock_id") != lock_id:
            logger.warning(f"[CRON-LOCK] Lock_id mismatch: esperado {lock_id}, encontrado {data.get('lock_id')}")
            return False

        # Deletar lock
        await lock_ref.delete()
        logger.info(f"[CRON-LOCK] Lock liberado ({lock_id})")
        return True

    except Exception as e:
        logger.error(f"[CRON-LOCK] Erro ao liberar lock: {e}")
        return False
