"""
Gerenciamento de OperacaoEmAndamento com lease/timeout.

Implementa recuperação segura de operações interrompidas usando:
- Propriedade de lease com expiração
- Transferência automática de propriedade após expiração
- Verificação atomic de evento antes de duplicar
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    atualizar_dado_em_path,
)
from services.firestore_client import get_db
from firebase_admin import firestore

logger = logging.getLogger(__name__)


def gerar_proprietario_id() -> str:
    """Gera identificador único para proprietário de operação."""
    return f"proc_{uuid.uuid4().hex[:16]}"


async def criar_operacao_em_andamento(
    tenant_id: str,
    operacao_id: str,
    actor_id: str,
    tipo: str,
    dados_confirmados: dict,
    proprietario_id: str,
    lease_ttl_minutos: int = 5
) -> Dict[str, Any]:
    """
    Cria OperacaoEmAndamento atomicamente com @transactional.

    Transação Firestore valida:
    - Operação não existe já (prevent duplicate creation)
    - Se existe: proprietario válido? Lease expirado?
    - REJEITAR se proprietario válido
    - PERMITIR recuperação se lease expirado
    - GRAVAR proprietario + lease_token ATOMICAMENTE

    Falha antes de persistência = sem side effects
    Falha após persistência = operação recuperável
    """

    def transacao_criar_operacao():
        """Transação Firestore para criar operação atomicamente."""
        db = get_db()

        @firestore.transactional
        def callback(transaction):
            agora = datetime.now()
            expira_em = agora + timedelta(minutes=lease_ttl_minutos)
            lease_token = str(uuid.uuid4())  # Token único para esta aquisição

            operacao_ref = (
                db.collection("Clientes")
                .document(tenant_id)
                .collection("OperacoesEmAndamento")
                .document(operacao_id)
            )

            # (1) LER documento atual (se existe)
            operacao_docs = list(transaction.get(operacao_ref))

            if operacao_docs:
                # Operação já existe — validar se proprietário ainda é válido
                operacao_data = operacao_docs[0].to_dict()
                if operacao_data:
                    # Verificar lease
                    lease_expira_em_str = operacao_data.get("lease_expira_em")
                    if lease_expira_em_str:
                        try:
                            lease_expira_em = datetime.fromisoformat(lease_expira_em_str)
                            if agora < lease_expira_em:
                                # Lease ainda válido — rejeitar
                                return {
                                    "ok": False,
                                    "motivo": "operacao_existe_com_proprietario_valido",
                                    "proprietario_ativo": operacao_data.get("proprietario_id"),
                                    "expira_em": lease_expira_em_str
                                }
                        except:
                            pass  # Falha parsing: trata como expirado, continua

            # (2) Operação não existe OU lease expirado: CRIAR/ATUALIZAR
            doc = {
                "operacao_id": operacao_id,
                "tenant_id": tenant_id,
                "actor_id": actor_id,
                "tipo": tipo,
                "status": "em_andamento",
                "evento_id": None,
                "dados_confirmados": dados_confirmados,
                "proprietario_id": proprietario_id,
                "lease_token": lease_token,
                "lease_adquirido_em": agora.isoformat(),
                "lease_expira_em": expira_em.isoformat(),
                "criada_em": agora.isoformat(),
                "atualizada_em": agora.isoformat()
            }

            # (3) GRAVAR ATOMICAMENTE
            transaction.set(operacao_ref, doc)

            return {
                "ok": True,
                "doc": doc,
                "lease_token": lease_token,
                "status": "em_andamento"
            }

        transaction = db.transaction()
        return callback(transaction)

    result = await asyncio.to_thread(transacao_criar_operacao)
    logger.info(f"OperacaoEmAndamento criada: {operacao_id} (prop={proprietario_id}) - {result.get('motivo', 'ok')}")
    return result


async def adquirir_lease_operacao(
    tenant_id: str,
    operacao_id: str,
    proprietario_id: str,
    lease_ttl_minutos: int = 5
) -> Dict[str, Any]:
    """
    Adquire lease exclusivo sobre operação.

    Se lease expirou: novo proprietario_id pode adquirir
    Se ainda válido: rejeita com dados de proprietário ativo
    """

    def transacao_adquirir_lease():
        """Transação Firestore para adquirir lease atomicamente."""
        db = get_db()

        @firestore.transactional
        def callback(transaction):
            operacao_path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
            operacao_ref = (
                db.collection("Clientes")
                .document(tenant_id)
                .collection("OperacoesEmAndamento")
                .document(operacao_id)
            )

            # (1) LER estado atual
            operacao_docs = list(transaction.get(operacao_ref))

            if not operacao_docs:
                # Não existe: não pode adquirir
                return {
                    "ok": False,
                    "motivo": "operacao_nao_existe"
                }

            operacao_data = operacao_docs[0].to_dict()
            if not operacao_data:
                # Documento vazio ou corrompido
                return {
                    "ok": False,
                    "motivo": "operacao_nao_existe"
                }
            agora = datetime.now()

            # (2) VERIFICAR se lease ainda é válido
            lease_expira_em_str = operacao_data.get("lease_expira_em")
            if lease_expira_em_str:
                try:
                    lease_expira_em = datetime.fromisoformat(lease_expira_em_str)
                    if agora < lease_expira_em:
                        # Lease ainda válido: rejeita
                        return {
                            "ok": False,
                            "motivo": "lease_ainda_valido",
                            "proprietario_ativo": operacao_data.get("proprietario_id"),
                            "expira_em": lease_expira_em_str
                        }
                except:
                    pass  # Falha no parsing: trata como expirado

            # (3) LEASE EXPIRADO OU NÃO EXISTE: transferir propriedade
            expira_em = agora + timedelta(minutes=lease_ttl_minutos)
            lease_token = str(uuid.uuid4())  # Token único para esta aquisição
            transaction.update(operacao_ref, {
                "proprietario_id": proprietario_id,
                "lease_token": lease_token,
                "lease_adquirido_em": agora.isoformat(),
                "lease_expira_em": expira_em.isoformat(),
                "atualizada_em": agora.isoformat()
            })

            return {
                "ok": True,
                "motivo": "lease_adquirido",
                "lease_token": lease_token,
                "operacao_data": operacao_data
            }

        transaction = db.transaction()
        result = callback(transaction)
        return result

    result = await asyncio.to_thread(transacao_adquirir_lease)
    return result


async def verificar_proprietario_valido(
    tenant_id: str,
    operacao_id: str,
    proprietario_id: str
) -> bool:
    """Verifica se proprietario_id ainda tem lease válido."""
    path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
    doc = await buscar_dado_em_path(path)

    if not doc:
        return False

    if doc.get("proprietario_id") != proprietario_id:
        return False

    lease_expira_em_str = doc.get("lease_expira_em")
    if not lease_expira_em_str:
        return False

    try:
        lease_expira_em = datetime.fromisoformat(lease_expira_em_str)
        return datetime.now() < lease_expira_em
    except:
        return False


async def atualizar_operacao_status(
    tenant_id: str,
    operacao_id: str,
    novo_status: str,
    proprietario_id: str,
    lease_token: str,
    evento_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Atualiza status de operação.

    Validação e atualização DENTRO da mesma transação Firestore.
    Impede atualização por proprietário antigo com lease_token obsoleto.
    """

    def transacao_atualizar_status():
        """Transação Firestore — validação + atualização atômicas."""
        db = get_db()

        @firestore.transactional
        def callback(transaction):
            operacao_ref = (
                db.collection("Clientes")
                .document(tenant_id)
                .collection("OperacoesEmAndamento")
                .document(operacao_id)
            )

            # LER documento
            docs_list = list(transaction.get(operacao_ref))
            if not docs_list:
                return {"ok": False, "motivo": "operacao_nao_existe"}

            doc = docs_list[0].to_dict()
            if not doc:
                return {"ok": False, "motivo": "operacao_nao_existe"}
            agora = datetime.now()

            # VALIDAÇÃO 1: Proprietário correto?
            if doc.get("proprietario_id") != proprietario_id:
                return {
                    "ok": False,
                    "motivo": "proprietario_mismatch",
                    "proprietario_esperado": proprietario_id,
                    "proprietario_efetivo": doc.get("proprietario_id")
                }

            # VALIDAÇÃO 2: Lease token válido?
            if doc.get("lease_token") != lease_token:
                return {
                    "ok": False,
                    "motivo": "lease_token_invalido",
                    "causa": "lease_token_obsoleto_ou_transfer ido"
                }

            # VALIDAÇÃO 3: Lease não expirou?
            lease_expira_em_str = doc.get("lease_expira_em")
            if lease_expira_em_str:
                try:
                    lease_expira_em = datetime.fromisoformat(lease_expira_em_str)
                    if agora >= lease_expira_em:
                        return {
                            "ok": False,
                            "motivo": "lease_expirado",
                            "expira_em": lease_expira_em_str
                        }
                except:
                    pass

            # VALIDAÇÃO 4: Transição válida?
            status_atual = doc.get("status", "")
            transicoes_validas = {
                "em_andamento": ["evento_persistido", "erro_recuperavel"],
                "evento_persistido": ["concluida"],
                "concluida": [],
            }

            if novo_status not in transicoes_validas.get(status_atual, []):
                return {
                    "ok": False,
                    "motivo": f"transicao_invalida_{status_atual}_para_{novo_status}"
                }

            # ATUALIZAR (dentro da mesma transação)
            update = {
                "status": novo_status,
                "atualizada_em": agora.isoformat()
            }
            if evento_id:
                update["evento_id"] = evento_id

            transaction.update(operacao_ref, update)
            return {"ok": True, "status_novo": novo_status}

        transaction = db.transaction()
        return callback(transaction)

    result = await asyncio.to_thread(transacao_atualizar_status)
    return result


async def liberar_lease_operacao(
    tenant_id: str,
    operacao_id: str,
    proprietario_id: str
) -> Dict[str, Any]:
    """Libera lease. Falha se não é proprietário."""
    path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
    doc = await buscar_dado_em_path(path)

    if not doc:
        return {"ok": False, "motivo": "operacao_nao_existe"}

    if doc.get("proprietario_id") != proprietario_id:
        return {
            "ok": False,
            "motivo": "nao_eh_proprietario",
            "proprietario_esperado": doc.get("proprietario_id")
        }

    # Limpar lease (mas manter operação)
    agora = datetime.now()
    await atualizar_dado_em_path(path, {
        "proprietario_id": None,
        "lease_expira_em": agora.isoformat(),  # Já expirou
        "atualizada_em": agora.isoformat()
    })

    logger.info(f"Lease liberado: {operacao_id}")
    return {"ok": True}


async def recuperar_operacao_em_andamento(
    tenant_id: str,
    operacao_id: str
) -> Optional[Dict[str, Any]]:
    """Recupera operação em andamento para retomar execução."""
    path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
    return await buscar_dado_em_path(path)


async def verificar_evento_existe(
    tenant_id: str,
    evento_id: str
) -> bool:
    """Verifica se evento foi realmente persistido em Firestore."""
    try:
        path = f"Clientes/{tenant_id}/Eventos/{evento_id}"
        doc = await buscar_dado_em_path(path)
        return doc is not None
    except:
        return False
