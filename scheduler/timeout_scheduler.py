# -*- coding: utf-8 -*-
"""
FASE 3.3: Scheduler de Timeout de Sessão

Encerra automaticamente sessões inativas por mais de 60 minutos.

Padrão de execução: Via /cron/ping com lock global (evita múltiplas instâncias).
Chamada: UptimeRobot (ou similar) aciona /cron/ping a cada 5-10 minutos.
"""

from datetime import datetime, timezone, timedelta
from services.firebase_service_async import (
    get_async_client,
    buscar_dado_em_path,
    atualizar_dado_em_path,
)
from utils.contexto_temporario import limpar_contexto_agendamento_v2_transacional
import logging

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 3600  # 60 minutos


async def processar_timeouts_sessoes():
    """
    [TIMEOUT-SCHEDULER] Verificar e encerrar automaticamente sessões inativas > 60 min.

    Algoritmo (com proteção contra race conditions):
    1. Iterar todos os tenants (donos)
    2. Para cada tenant: iterar sessões ativas (estado_fluxo != "idle")
    3. Para cada sessão:
       a. Ler _last_client_activity (T1)
       b. Calcular tempo_decorrido = agora - T1
       c. Se < 60 min: skip (ainda válida)
       d. Se >= 60 min:
          i. RE-READ documento (revalidação antes de encerrar)
          ii. Verificar se _last_client_activity mudou (T2)
          iii. Se T2 > T1: cliente enviou msg, skip
          iv. Se T2 == T1: chamar limpar_contexto_agendamento_v2_transacional()
          v. Se abortou (evento criado): log, skip

    Proteções:
    - Revalidação transacional antes de encerrar
    - Verifica se cliente enviou msg entre verificações
    - Isolamento por tenant_id
    - Usar transação de limpeza existente (já validada)

    Retorna:
    - dict com estatísticas {"sessoes_checadas": N, "sessoes_encerradas": N, "erros": N}
    """
    print(f"[TIMEOUT-SCHEDULER] Iniciando verificação de timeouts...", flush=True)
    logger.info("[TIMEOUT-SCHEDULER] Iniciando verificação de timeouts...")

    stats = {
        "tenants_processados": 0,
        "sessoes_checadas": 0,
        "sessoes_encerradas": 0,
        "sessoes_skipped": 0,
        "revalidacoes": 0,
        "transacoes_abortadas": 0,
        "erros": 0,
    }

    agora = datetime.now(timezone.utc)

    try:
        # 1️⃣ ITERAR TODOS OS TENANTS
        db = get_async_client()
        tenants = {}

        # Carregar apenas documentos de "dono" (tenant_id = dono_id)
        try:
            query = db.collection("Clientes").where("tipo_usuario", "==", "dono")
            async for doc in query.stream():
                tenants[doc.id] = doc.to_dict() or {}
        except Exception as e:
            logger.warning(f"[TIMEOUT-SCHEDULER-LOAD-TENANTS] Erro ao carregar tenants: {e}")
            stats["erros"] += 1
            return stats

        stats["tenants_processados"] = len(tenants)
        print(
            f"[TIMEOUT-SCHEDULER] {len(tenants)} tenants carregados",
            flush=True
        )

        # 2️⃣ PROCESSAR CADA TENANT
        for tenant_id in tenants.keys():
            try:
                # Carregar sessões deste tenant
                sessoes_path = f"Clientes/{tenant_id}/Sessoes"
                try:
                    sessoes = {}
                    query = db.collection(sessoes_path)
                    async for doc in query.stream():
                        sessoes[doc.id] = doc.to_dict() or {}
                except Exception as e:
                    logger.debug(
                        f"[TIMEOUT-SCHEDULER-LOAD-SESSOES] Erro ao carregar sessões de {tenant_id}: {e}"
                    )
                    # Continuar com próximo tenant
                    continue

                # 3️⃣ PROCESSAR CADA SESSÃO
                for cliente_id, sessao_data in sessoes.items():
                    try:
                        stats["sessoes_checadas"] += 1

                        # Extrair estado e timestamp
                        estado_fluxo = (
                            sessao_data.get("estado_fluxo") or "idle"
                        ).strip().lower()
                        ts_atividade_str = sessao_data.get("_last_client_activity")

                        # Se em idle, skip (não é fluxo ativo)
                        if estado_fluxo == "idle":
                            print(
                                f"[TIMEOUT-SCHEDULER-SKIP-IDLE] {tenant_id}/{cliente_id}",
                                flush=True
                            )
                            stats["sessoes_skipped"] += 1
                            continue

                        # Se sem timestamp, skip (não é possível validar)
                        if not ts_atividade_str:
                            print(
                                f"[TIMEOUT-SCHEDULER-SKIP-NO-TS] {tenant_id}/{cliente_id}",
                                flush=True
                            )
                            stats["sessoes_skipped"] += 1
                            continue

                        # Parsear timestamp
                        try:
                            import dateutil.parser
                            ts_atividade = dateutil.parser.isoparse(ts_atividade_str)
                        except Exception as e:
                            logger.warning(
                                f"[TIMEOUT-SCHEDULER-PARSE-TS-ERROR] {tenant_id}/{cliente_id}: {e}"
                            )
                            stats["sessoes_skipped"] += 1
                            continue

                        # Calcular tempo decorrido
                        tempo_decorrido = (agora - ts_atividade).total_seconds()
                        minutos_decorridos = tempo_decorrido / 60

                        # Se < 60 min, ainda válida
                        if tempo_decorrido < TIMEOUT_SECONDS:
                            print(
                                f"[TIMEOUT-SCHEDULER-VALID] {tenant_id}/{cliente_id} | "
                                f"tempo={minutos_decorridos:.1f}min < 60min",
                                flush=True
                            )
                            stats["sessoes_skipped"] += 1
                            continue

                        # >= 60 MIN: REVALIDAR ANTES DE ENCERRAR
                        print(
                            f"[TIMEOUT-SCHEDULER-EXPIRATION-DETECTED] {tenant_id}/{cliente_id} | "
                            f"tempo={minutos_decorridos:.1f}min >= 60min",
                            flush=True
                        )

                        # RE-READ documento (revalidação T2)
                        stats["revalidacoes"] += 1
                        try:
                            sessao_path = f"Clientes/{tenant_id}/Sessoes/{cliente_id}"
                            sessao_reread = await buscar_dado_em_path(sessao_path)

                            if not sessao_reread:
                                print(
                                    f"[TIMEOUT-SCHEDULER-REVALIDATE-GONE] {tenant_id}/{cliente_id} | "
                                    f"sessão foi deletada",
                                    flush=True
                                )
                                continue

                            ts_reread_str = sessao_reread.get("_last_client_activity")

                            # Comparar T2 com T1 (revalidação)
                            if ts_reread_str != ts_atividade_str:
                                print(
                                    f"[TIMEOUT-SCHEDULER-REVALIDATE-CHANGED] {tenant_id}/{cliente_id} | "
                                    f"timestamp mudou (cliente enviou msg), skip",
                                    flush=True
                                )
                                stats["sessoes_skipped"] += 1
                                continue

                            # Timestamp == T1: pode encerrar
                            print(
                                f"[TIMEOUT-SCHEDULER-TERMINATE] {tenant_id}/{cliente_id} | "
                                f"revalidação OK, iniciando limpeza",
                                flush=True
                            )

                        except Exception as e:
                            logger.warning(
                                f"[TIMEOUT-SCHEDULER-REVALIDATE-ERROR] {tenant_id}/{cliente_id}: {e}"
                            )
                            stats["sessoes_skipped"] += 1
                            continue

                        # ⚡ ENCERRAR SESSÃO (COM PROTEÇÃO TRANSACIONAL)
                        try:
                            resultado = await limpar_contexto_agendamento_v2_transacional(
                                tenant_id,
                                cliente_id
                            )

                            if resultado:
                                print(
                                    f"[TIMEOUT-SCHEDULER-TERMINATED] {tenant_id}/{cliente_id} | "
                                    f"sessão encerrada com sucesso",
                                    flush=True
                                )
                                stats["sessoes_encerradas"] += 1
                            else:
                                print(
                                    f"[TIMEOUT-SCHEDULER-ABORT] {tenant_id}/{cliente_id} | "
                                    f"transação abortou (evento criado durante limpeza)",
                                    flush=True
                                )
                                stats["transacoes_abortadas"] += 1

                        except Exception as e:
                            logger.error(
                                f"[TIMEOUT-SCHEDULER-CLEANUP-ERROR] {tenant_id}/{cliente_id}: {e}"
                            )
                            stats["erros"] += 1

                    except Exception as e:
                        logger.error(
                            f"[TIMEOUT-SCHEDULER-SESSION-ERROR] {tenant_id}/{cliente_id}: {e}"
                        )
                        stats["erros"] += 1

            except Exception as e:
                logger.error(f"[TIMEOUT-SCHEDULER-TENANT-ERROR] {tenant_id}: {e}")
                stats["erros"] += 1

    except Exception as e:
        logger.error(f"[TIMEOUT-SCHEDULER-FATAL] Erro geral: {e}")
        stats["erros"] += 1

    # 📊 RESUMO
    print(
        f"[TIMEOUT-SCHEDULER-SUMMARY] "
        f"tenants={stats['tenants_processados']} | "
        f"sessoes_checadas={stats['sessoes_checadas']} | "
        f"encerradas={stats['sessoes_encerradas']} | "
        f"skipped={stats['sessoes_skipped']} | "
        f"revalidacoes={stats['revalidacoes']} | "
        f"transacoes_abortadas={stats['transacoes_abortadas']} | "
        f"erros={stats['erros']}",
        flush=True
    )
    logger.info(f"[TIMEOUT-SCHEDULER-SUMMARY] {stats}")

    return stats


# Exportar para main.py
__all__ = ["processar_timeouts_sessoes"]
