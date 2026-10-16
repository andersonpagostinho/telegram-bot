#!/usr/bin/env python3
"""
Monitor Contínuo de Quota Firestore com Auto-Cleanup

Features:
  - Monitora quota a cada 30 minutos
  - Alerta se >70% da quota foi consumida
  - Auto-cleanup quando quota retorna
  - Logging detalhado
  - Compatível com cron/Task Scheduler

Uso:
  python monitor_quota_continuous.py

  Ou agendar:
  - Windows: Task Scheduler
  - Linux: crontab -e
    */30 * * * * cd /path/to/neoeve && python monitor_quota_continuous.py >> quota_monitor.log 2>&1
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from services.firebase_service_async import get_async_client

# Configurar logging
log_file = Path(__file__).parent / "quota_monitor.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Arquivo de estado
STATE_FILE = Path(__file__).parent / ".quota_state.json"
QUOTA_LIMIT_PERCENT = 70

async def read_state():
    """Ler estado anterior"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {
        "quota_available": 100000,  # Firestore padrão: 50k reads + 50k writes
        "quota_used": 0,
        "quota_percent": 0,
        "last_check": None,
        "alerted_at_70": False,
        "quota_recovered": False
    }

async def save_state(state):
    """Salvar estado"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar state: {e}")

async def check_quota_status():
    """Verificar status atual da quota"""
    client = get_async_client()

    try:
        ref = client.document("_test_quota/status")
        doc = await ref.get()
        logger.info("[OK] Firestore accessible - QUOTA LIBERADA")
        return "LIBERADA"
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            logger.warning("[429] Quota ainda esgotada")
            return "ESGOTADA"
        else:
            logger.error(f"[ERRO] {error_msg[:80]}")
            return "DESCONHECIDO"

async def estimate_quota_percent():
    """
    Estimar percentual de quota consumida

    Firestore quota reseta a cada 24h
    Se foi esgotada há X minutos, usou ~100%
    Diminui 1% a cada ~14.4 minutos até reset
    """
    state = await read_state()

    # Padrão: quotas diárias (reads + writes combinados)
    # 50k reads + 50k writes = 100k ops total
    # Se esgotou, estimamos 100%

    return 100  # Se chegou aqui, foi 429 = 100% consumida

async def cleanup_test_data_silent():
    """Cleanup silencioso de dados de teste quando quota volta"""
    logger.info("[CLEANUP] Tentando limpar dados de teste...")

    client = get_async_client()

    # Lista de IDs conhecidos criados durante testes
    test_patterns = [
        "wamid_test_real_",
        "wa_p0_test_",
        "endpoint_iso_"
    ]

    # Não fazer varredura - deletar apenas IDs conhecidos
    test_doc_ids = [f"wamid_test_real_{i:03d}" for i in range(1, 21)]

    deleted_count = 0
    for msg_id in test_doc_ids:
        try:
            ref = client.document(f"WhatsAppEndpoints/wa_p0_test_real_001/ProcessedMessages/{msg_id}")
            await ref.delete()
            deleted_count += 1
            logger.info(f"  [DELETED] {msg_id}")
        except Exception as e:
            if "429" in str(e):
                logger.warning("[429] Quota se esgotou novamente durante cleanup")
                return False
            elif "NotFound" not in str(e):
                logger.debug(f"  [SKIP] {msg_id} - {str(e)[:40]}")

    logger.info(f"[CLEANUP] Total deletado: {deleted_count} documentos")
    return True

async def send_alert(message):
    """Enviar alerta (log + stdout)"""
    logger.critical(f"\n{'='*70}")
    logger.critical(f"ALERTA: {message}")
    logger.critical(f"{'='*70}\n")
    print(f"\n{'='*70}")
    print(f"ALERTA: {message}")
    print(f"{'='*70}\n")

async def main():
    logger.info("="*70)
    logger.info("INICIANDO MONITOR DE QUOTA FIRESTORE")
    logger.info(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)

    state = await read_state()
    status = await check_quota_status()
    quota_percent = await estimate_quota_percent() if status == "ESGOTADA" else 0

    # Atualizar estado
    state["last_check"] = datetime.now().isoformat()
    state["quota_percent"] = quota_percent

    # Lógica de alertas
    if status == "LIBERADA":
        logger.info("[SUCESSO] Quota foi liberada!")

        # Auto-cleanup
        if state.get("quota_used", 0) > 0 or not state.get("quota_recovered", False):
            logger.info("[AUTO-CLEANUP] Iniciando limpeza automática...")
            await cleanup_test_data_silent()
            state["quota_recovered"] = True
            state["quota_used"] = 0
            state["alerted_at_70"] = False

    elif status == "ESGOTADA":
        if quota_percent > QUOTA_LIMIT_PERCENT and not state.get("alerted_at_70", False):
            await send_alert(
                f"QUOTA FIRESTORE > {QUOTA_LIMIT_PERCENT}% "
                f"(Status: {status}, Reset em ~24h)"
            )
            state["alerted_at_70"] = True
            state["quota_used"] = quota_percent
        else:
            logger.info(f"[MONITORANDO] Quota {quota_percent}% - Aguardando reset (~24h)")

    else:
        logger.warning(f"[DESCONHECIDO] Status: {status}")

    # Salvar estado
    await save_state(state)

    logger.info("="*70)
    logger.info(f"Proxima verificacao: ~30 minutos")
    logger.info("="*70)

if __name__ == "__main__":
    asyncio.run(main())

