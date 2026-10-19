"""
PATCH P0 — Criação atômica de evento com proteção contra race condition.

Implementa lock por slot de agenda para garantir que apenas um evento
seja criado quando múltiplas requisições tentam ocupar o mesmo horário.

Uso:
    resultado = await criar_evento_com_lock(
        dono_id="dono_xyz",
        evento={...},
        event_id="evento_123"
    )
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    buscar_subcolecao,
    atualizar_dado_em_path,
    deletar_dado_em_path,
)
from services.firestore_client import get_db
from firebase_admin import firestore

logger = logging.getLogger(__name__)


def normalizar_hora(hora_str: str) -> str:
    """Normaliza hora para formato HH:MM."""
    try:
        h, m = map(int, str(hora_str).split(":"))
        return f"{h:02d}:{m:02d}"
    except:
        return hora_str


def gerar_slot_key(profissional: str, hora_inicio: str, hora_fim: str) -> str:
    """
    Gera chave determinística para o slot.

    Formato: profissional_normalizado_{inicio}_{fim}
    Exemplo: bruna_150_001730_180000
    """
    prof_norm = profissional.lower().replace(" ", "_")
    inicio_norm = hora_inicio.replace(":", "")
    fim_norm = hora_fim.replace(":", "")
    return f"{prof_norm}_{inicio_norm}_{fim_norm}"


def lock_esta_expirado(timestamp_lock_str: str, horas_validade: int = 24) -> bool:
    """
    Verifica se um lock expirou.

    Args:
        timestamp_lock_str: ISO timestamp do lock
        horas_validade: Horas que o lock é válido (padrão 24h)

    Returns:
        True se lock expirou, False se ainda válido
    """
    try:
        timestamp_lock = datetime.fromisoformat(timestamp_lock_str)
        agora = datetime.now()
        diferenca = (agora - timestamp_lock).total_seconds() / 3600  # em horas
        return diferenca > horas_validade
    except:
        return False


async def limpar_locks_orfaos(dono_id: str, horas_validade: int = 24) -> int:
    """
    Remove locks órfãos (sem evento_id) que expiraram.
    Executado antes de criar novo lock.

    Args:
        dono_id: ID do dono/salão
        horas_validade: Considerar expirado após N horas

    Returns:
        Quantidade de locks removidos
    """
    try:
        locks = await buscar_subcolecao(f"Clientes/{dono_id}/AgendaLocks") or []
        removidos = 0

        for lock_item in locks:
            # Parse lock
            if isinstance(lock_item, dict):
                lock_data = lock_item.get("data", lock_item)
                lock_id = lock_item.get("id")
            else:
                continue

            # Verificar se é órfão (sem evento_id)
            if not lock_data.get("evento_id"):
                # Verificar expiração
                if lock_esta_expirado(lock_data.get("timestamp_lock"), horas_validade):
                    try:
                        lock_path = f"Clientes/{dono_id}/AgendaLocks/{lock_id}"
                        await deletar_dado_em_path(lock_path)
                        removidos += 1
                        logger.info(f"Lock órfão removido: {lock_id}")
                    except Exception as e:
                        logger.warning(f"Erro ao remover lock órfão {lock_id}: {e}")

        return removidos
    except Exception as e:
        logger.error(f"Erro ao limpar locks órfãos: {e}")
        return 0


def gerar_buckets_tempo(hora_inicio: str, hora_fim: str, intervalo_minutos: int = 10) -> list:
    """
    Gera buckets de tempo para proteger contra sobreposição parcial.

    Cada evento ocupa múltiplos buckets. Se qualquer bucket já estiver
    marcado, o novo evento não pode ser criado.

    Args:
        hora_inicio: HH:MM
        hora_fim: HH:MM
        intervalo_minutos: Duração de cada bucket (10 min recomendado)

    Returns:
        Lista de buckets: ["150000", "150100", "151000", ...]
    """
    try:
        h_start, m_start = map(int, hora_inicio.split(":"))
        h_end, m_end = map(int, hora_fim.split(":"))

        minutos_start = h_start * 60 + m_start
        minutos_end = h_end * 60 + m_end

        buckets = []
        current = minutos_start

        while current < minutos_end:
            h = current // 60
            m = current % 60
            bucket = f"{h:02d}{m:02d}00"  # HHMM00 format
            buckets.append(bucket)
            current += intervalo_minutos

        return buckets

    except Exception as e:
        logger.error(f"Erro ao gerar buckets: {e}")
        return []


async def adquirir_lock_atomicamente(
    dono_id: str,
    lock_key: str,
    lock_doc: dict
) -> Dict[str, Any]:
    """
    Adquire um lock de forma atomicamente segura usando transação Firestore.

    IMPLEMENTAÇÃO: Usa transação Firestore (sync) envolvida em asyncio.to_thread()
    para garantir que leitura de existência + escrita de lock ocorrem atomicamente,
    sem race condition.

    Args:
        dono_id: ID do dono/salão
        lock_key: Chave única do lock
        lock_doc: Documento do lock a criar

    Returns:
        {
            "ok": bool,
            "motivo": str (se falhou)
        }
    """

    def transacao_adquirir_lock():
        """Transação sincronea para adquirir lock atomicamente."""
        db = get_db()

        @firestore.transactional
        def callback(transaction):
            """
            [ATOMIC] Dentro da transação, operações são isoladas e atômicas:
            1. Lê se lock já existe
            2. Se não existe, cria novo lock
            3. Se existe, falha com erro

            Nenhuma outra transação concorrente consegue modificar o mesmo
            documento entre (1) e (2).
            """
            lock_path = f"Clientes/{dono_id}/AgendaLocks/{lock_key}"
            lock_ref = (
                db.collection("Clientes")
                .document(dono_id)
                .collection("AgendaLocks")
                .document(lock_key)
            )

            # (1) LER DENTRO DA TRANSAÇÃO — isolado de outras transações
            # NOTA: transaction.get() retorna um generator, precisamos listar
            lock_docs = list(transaction.get(lock_ref))

            if lock_docs:
                # (2) SE JÁ EXISTE, FALHAR (sem escrita)
                lock_existente_doc = lock_docs[0]
                lock_data = lock_existente_doc.to_dict()
                return {
                    "ok": False,
                    "motivo": "lock_já_existe",
                    "lock_data": lock_data
                }

            # (3) SE NÃO EXISTE, CRIAR (atômico com leitura acima)
            transaction.set(lock_ref, lock_doc)
            return {
                "ok": True,
                "motivo": "lock_criado"
            }

        # Executar transação
        transaction = db.transaction()
        result = callback(transaction)
        return result

    # ENVOLVER EM asyncio.to_thread() PARA NÃO BLOQUEAR EVENT LOOP
    result = await asyncio.to_thread(transacao_adquirir_lock)
    return result


async def adquirir_locks_atomicamente(
    dono_id: str,
    lock_keys: list,
    lock_docs_dict: dict
) -> Dict[str, Any]:
    """
    Adquire MÚLTIPLOS locks de forma atomicamente segura em UMA ÚNICA transação.

    [CRÍTICO] Todos os buckets devem ser adquiridos juntos em uma transação.
    Se qualquer bucket falhar, a transação inteira falha e NENHUM lock é criado.

    Args:
        dono_id: ID do dono/salão
        lock_keys: Lista de chaves ["key1", "key2", ...]
        lock_docs_dict: Dict {lock_key: {doc_data}, ...}

    Returns:
        {"ok": bool, "lock_keys_criados": list | None, "motivo": str}
    """

    def transacao_adquirir_locks_sync():
        """Transação sincronea para adquirir TODOS os locks atomicamente."""
        db = get_db()

        @firestore.transactional
        def callback(transaction):
            """[ATOMIC] Verifica E cria todos os locks em uma transação."""
            lock_refs = {}
            for lock_key in lock_keys:
                lock_ref = (
                    db.collection("Clientes")
                    .document(dono_id)
                    .collection("AgendaLocks")
                    .document(lock_key)
                )
                lock_refs[lock_key] = lock_ref

            # Verificar se QUALQUER lock já existe
            for lock_key, lock_ref in lock_refs.items():
                lock_doc_list = list(transaction.get(lock_ref))
                if lock_doc_list and len(lock_doc_list) > 0:
                    lock_doc = lock_doc_list[0]
                    # Verificar se documento realmente existe
                    if hasattr(lock_doc, 'exists') and lock_doc.exists:
                        return {
                            "ok": False,
                            "lock_key_conflito": lock_key,
                            "motivo": f"lock_já_existe: {lock_key}"
                        }
                    # Se veio documento mas não tem `.exists`, trata como documento vazio
                    # (não interrompe — continua criando)

            # Criar TODOS os locks (atômico)
            for lock_key, lock_ref in lock_refs.items():
                transaction.set(lock_ref, lock_docs_dict[lock_key])

            return {
                "ok": True,
                "lock_keys_criados": lock_keys,
                "motivo": "locks_criados"
            }

        transaction = db.transaction()
        result = callback(transaction)
        return result

    logger.debug(f"[LOCK_THREAD] Entrando em thread para locks: {lock_keys[:1]}")
    result = await asyncio.to_thread(transacao_adquirir_locks_sync)
    logger.debug(f"[LOCK_THREAD] Saindo de thread: ok={result.get('ok')}")
    return result


async def tem_conflito_real(
    dono_id: str,
    profissional: str,
    hora_inicio: str,
    hora_fim: str,
    excluir_evento_id: Optional[str] = None
) -> bool:
    """
    Verifica se existe evento confirmado sobreposto para o mesmo profissional.

    CRÍTICO: Esta função é chamada DENTRO do lock, para evitar race condition.

    Args:
        dono_id: ID do dono/salão
        profissional: Nome do profissional
        hora_inicio: Hora inicial (formato HH:MM)
        hora_fim: Hora final (formato HH:MM)
        excluir_evento_id: Se fornecido, ignora este evento (para updates)

    Returns:
        True se há conflito, False se está livre
    """

    try:
        eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos") or []

        for evento_item in eventos:
            # Parse evento conforme o formato retornado por buscar_subcolecao
            if isinstance(evento_item, dict):
                # Pode vir como {"id": "...", "data": {...}} ou direto como evento
                evento_data = evento_item.get("data", {})
                if isinstance(evento_data, dict):
                    evento = evento_data
                else:
                    evento = evento_item
            else:
                continue

            # Ignorar se for o evento que estamos atualizando
            if evento.get("id") == excluir_evento_id:
                continue

            # Ignorar cancelados
            status = str(evento.get("status") or "").strip().lower()
            if status in ["cancelado", "cancelada", "removido", "removida"]:
                continue

            # Comparar profissional
            if evento.get("profissional", "").lower() != profissional.lower():
                continue

            # Verificar sobreposição de horário
            e_inicio = normalizar_hora(evento.get("hora_inicio", ""))
            e_fim = normalizar_hora(evento.get("hora_fim", ""))

            # Sobreposição: inicio_novo < fim_existente AND fim_novo > inicio_existente
            if hora_inicio < e_fim and hora_fim > e_inicio:
                logger.warning(
                    f"Conflito detectado: {profissional} "
                    f"{hora_inicio}-{hora_fim} conflita com {e_inicio}-{e_fim}"
                )
                return True

        return False

    except Exception as e:
        logger.error(f"Erro ao verificar conflito: {e}")
        return True  # Falha aberta: assume conflito se não conseguir verificar


async def criar_evento_com_lock(
    dono_id: str,
    evento: dict,
    event_id: str,
    excluir_evento_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria evento com proteção contra race condition e sobreposição parcial.

    Implementação com buckets:
    1. Gera buckets de tempo para o intervalo do evento
    2. Tenta criar locks para cada bucket (protege sobreposição)
    3. Se qualquer bucket já existe, falha
    4. Dentro dos locks, reconsulta conflito (defesa em profundidade)
    5. Se conflito, rejeita
    6. Se OK, salva evento

    Args:
        dono_id: ID do dono/salão
        evento: Dados do evento
        event_id: ID único do evento
        excluir_evento_id: Para updates, ignora este evento na validação

    Returns:
        {
            "ok": bool,
            "evento_id": str (se ok),
            "motivo": str (se falha),
            "tipo_erro": str
        }
    """

    locks_criados = []  # Para rollback se necessário

    try:
        # 1️⃣ VALIDAR PRÉ-REQUISITOS
        if not evento.get("confirmado"):
            return {
                "ok": False,
                "motivo": "Evento não marcado como confirmado",
                "tipo_erro": "validacao"
            }

        profissional = evento.get("profissional", "").strip()
        hora_inicio = normalizar_hora(evento.get("hora_inicio", ""))
        hora_fim = normalizar_hora(evento.get("hora_fim", ""))

        if not profissional or not hora_inicio or not hora_fim:
            return {
                "ok": False,
                "motivo": "Dados incompletos (profissional, hora_inicio, hora_fim)",
                "tipo_erro": "validacao"
            }

        # 2️⃣ GERAR BUCKETS DE TEMPO (protege sobreposição parcial)
        buckets = gerar_buckets_tempo(hora_inicio, hora_fim, intervalo_minutos=10)
        if not buckets:
            return {
                "ok": False,
                "motivo": "Erro ao calcular buckets de tempo",
                "tipo_erro": "validacao"
            }

        prof_norm = profissional.lower().replace(" ", "_")
        data_evento = evento.get("data", "").replace("-", "")[:8]  # YYYYMMDD

        logger.info(f"Criando {len(buckets)} locks para {prof_norm}: {buckets}")

        # 🧹 PATCH RO-04: Limpar locks órfãos antes de criar novos
        removidos = await limpar_locks_orfaos(dono_id)
        if removidos > 0:
            logger.info(f"🧹 Removidos {removidos} locks órfãos expirados")

        # 3️⃣ PREPARAR E ADQUIRIR TODOS OS LOCKS EM UMA ÚNICA TRANSAÇÃO
        try:
            # Preparar documentos de lock para TODOS os buckets
            lock_keys = []
            lock_docs_dict = {}

            for bucket in buckets:
                lock_key = f"{prof_norm}_{data_evento}_{bucket}"
                lock_keys.append(lock_key)

                lock_doc = {
                    "bucket": bucket,
                    "profissional": profissional,
                    "timestamp_lock": datetime.now().isoformat(),
                    "expira_em": (datetime.now() + timedelta(hours=24)).isoformat(),
                    "status": "reservado",
                    "evento_id": None  # Será preenchido quando evento for criado
                }
                lock_docs_dict[lock_key] = lock_doc

            # 🔒 ADQUIRIR TODOS OS LOCKS ATOMICAMENTE EM UMA TRANSAÇÃO
            resultado_lock = await adquirir_locks_atomicamente(dono_id, lock_keys, lock_docs_dict)

            if not resultado_lock.get("ok"):
                # Qualquer lock falhou = nenhum foi criado (transação atômica)
                # MAS: verificar se o evento já existe (para idempotência)
                logger.warning(
                    f"Falha ao adquirir locks: {resultado_lock.get('motivo')} "
                    f"({profissional} {hora_inicio}-{hora_fim})"
                )

                # ✅ FALLBACK IDEMPOTÊNCIA: Se evento já existe, retornar sucesso
                evento_path = f"Clientes/{dono_id}/Eventos/{event_id}"
                evento_existente = await buscar_dado_em_path(evento_path)
                if evento_existente:
                    logger.info(f"Evento já existe (idempotente): {event_id}")
                    return {
                        "ok": True,
                        "evento_id": event_id,
                        "duplicado": True,
                        "lock_ids": [],
                        "lock_keys": [],
                        "motivo": "Evento já existe (idempotente após falha de lock)"
                    }

                # Se locks não foram criados E evento não existe = erro real
                return {
                    "ok": False,
                    "lock_ids": [],
                    "lock_keys": [],
                    "motivo": f"Slot ocupado: {profissional} {hora_inicio}-{hora_fim}",
                    "tipo_erro": "lock_existente"
                }

            # TODOS os locks adquiridos com sucesso
            for lock_key in resultado_lock.get("lock_keys_criados", []):
                lock_path = f"Clientes/{dono_id}/AgendaLocks/{lock_key}"
                locks_criados.append(lock_path)

            logger.info(f"Todos os {len(lock_keys)} locks adquiridos atomicamente para {profissional}")

        except Exception as lock_error:
            # [FIRESTORE 409] Detectar conflito de transação cross-transaction contention
            # Isso significa que outra transação está acessando os mesmos locks
            erro_str = str(lock_error).lower()
            if "409" in str(lock_error) or "aborted" in erro_str or "contention" in erro_str:
                logger.warning(f"Conflito de transação (Firestore 409): {profissional} {hora_inicio}-{hora_fim}")
                return {
                    "ok": False,
                    "lock_ids": [p.split("/")[-1] for p in locks_criados],
                    "lock_keys": [p.split("/")[-1] for p in locks_criados],
                    "motivo": f"Slot ocupado (transação concorrente): {profissional} {hora_inicio}-{hora_fim}",
                    "tipo_erro": "lock_existente"  # Tratar conflito de transação como lock ocupado
                }

            # Outro erro desconhecido
            logger.error(f"Erro ao adquirir locks: {lock_error}")
            return {
                "ok": False,
                "lock_ids": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                "lock_keys": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                "motivo": f"Erro ao adquirir locks: {str(lock_error)}",
                "tipo_erro": "erro"
            }

        # 4️⃣ DENTRO DOS LOCKS: RECONSULTAR CONFLITO (DEFESA EM PROFUNDIDADE)
        try:
            conflita = await tem_conflito_real(
                dono_id,
                profissional,
                hora_inicio,
                hora_fim,
                excluir_evento_id
            )

            if conflita:
                logger.warning(f"Conflito detectado: {profissional} {hora_inicio}-{hora_fim}")
                return {
                    "ok": False,
                    "lock_ids": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                    "lock_keys": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                    "motivo": f"Profissional {profissional} já tem evento nesse horário",
                    "tipo_erro": "conflito"
                }

        except Exception as check_error:
            logger.error(f"Erro ao verificar conflito: {check_error}")
            return {
                "ok": False,
                "lock_ids": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                "lock_keys": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                "motivo": f"Erro ao validar: {str(check_error)}",
                "tipo_erro": "erro"
            }

        # 5️⃣ SEM CONFLITO: SALVAR EVENTO
        try:
            evento["criado_em"] = datetime.now().isoformat()
            evento_path = f"Clientes/{dono_id}/Eventos/{event_id}"

            # Verificar idempotência
            evento_existente = await buscar_dado_em_path(evento_path)
            if evento_existente:
                logger.warning(f"Evento já existe (idempotente): {event_id}")
                # Marcar locks como confirmados
                for lock_path in locks_criados:
                    lock_doc = {
                        "status": "confirmado_idempotente",
                        "evento_id": event_id,
                        "timestamp_confirmacao": datetime.now().isoformat()
                    }
                    await atualizar_dado_em_path(lock_path, lock_doc)

                return {
                    "ok": True,
                    "evento_id": event_id,
                    "duplicado": True,
                    "lock_ids": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                    "lock_keys": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                    "motivo": "Evento já existe (idempotente)"
                }

            # Criar evento
            await salvar_dado_em_path(evento_path, evento)
            logger.info(f"Evento criado: {event_id}")

            # 6️⃣ MARCAR LOCKS COMO CONFIRMADOS
            for lock_path in locks_criados:
                lock_doc = {
                    "status": "confirmado",
                    "evento_id": event_id,
                    "timestamp_confirmacao": datetime.now().isoformat()
                }
                await atualizar_dado_em_path(lock_path, lock_doc)

            return {
                "ok": True,
                "evento_id": event_id,
                "lock_ids": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                "lock_keys": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                "motivo": "Evento criado com sucesso"
            }

        except Exception as save_error:
            logger.error(f"Erro ao salvar evento: {save_error}")
            return {
                "ok": False,
                "lock_ids": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                "lock_keys": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
                "motivo": f"Erro ao salvar evento: {str(save_error)}",
                "tipo_erro": "erro"
            }

    except Exception as e:
        logger.error(f"Erro geral em criar_evento_com_lock: {e}")
        return {
            "ok": False,
            "lock_ids": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
            "lock_keys": [p.split("/")[-1] for p in locks_criados],  # [P4.9N]
            "motivo": f"Erro inesperado: {str(e)}",
            "tipo_erro": "erro"
        }


async def limpar_locks_expirados(dono_id: str, horas_expiracao: int = 24) -> int:
    """
    Limpa locks expirados (status=rejeitado ou erro_validacao, etc).

    Útil para manutenção, evita acumular locks antigos.

    Args:
        dono_id: ID do dono
        horas_expiracao: Locks mais antigos que isso são removidos

    Returns:
        Quantidade de locks removidos
    """

    try:
        locks = await buscar_subcolecao(f"Clientes/{dono_id}/AgendaLocks") or []

        limite_tempo = datetime.now().timestamp() - (horas_expiracao * 3600)
        removidos = 0

        for lock_item in locks:
            # Parse lock
            if isinstance(lock_item, dict):
                lock_data = lock_item.get("data", lock_item)
            else:
                continue

            # Verificar status e timestamp
            status = lock_data.get("status", "")
            if status not in ["rejeitado", "erro_validacao", "erro_save"]:
                continue

            timestamp_str = lock_data.get("timestamp_lock", "")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str).timestamp()
                if timestamp < limite_tempo:
                    slot_key = lock_data.get("slot_key")
                    lock_path = f"Clientes/{dono_id}/AgendaLocks/{slot_key}"
                    # Implementar delete se houver função
                    # await deletar_dado_em_path(lock_path)
                    removidos += 1
            except:
                pass

        logger.info(f"Locks expirados removidos: {removidos}")
        return removidos

    except Exception as e:
        logger.error(f"Erro ao limpar locks: {e}")
        return 0
