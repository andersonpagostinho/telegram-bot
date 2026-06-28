"""
F1-03: Retorno Pendente

Responsável por:
- Verificar se cliente atendido completou 15 dias sem novo agendamento
- Atualizar lead_status de "atendido" para "retorno_pendente"
- Usar APENAS dados de Clientes/{tenant_id}/Clientes/{cliente_actor_id}
- Determinístico (sem scheduler, sem IA, sem automações)
- Multi-tenant isolado

Regra:
  Se (hoje - ultimo_atendimento) >= dias_retorno
  E lead_status == "atendido"
  E total_agendamentos não aumentou desde ultimo_atendimento
  Então: lead_status = "retorno_pendente"
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from services.firestore_client import get_db
from services.lead_status_service import atualizar_lead_status
import asyncio


async def marcar_como_atendido(
    tenant_id: str,
    cliente_actor_id: str,
    data_atendimento: Optional[str] = None
) -> bool:
    """
    Marca cliente como atendido e registra timestamp.

    Args:
        tenant_id: ID do tenant
        cliente_actor_id: ID do cliente
        data_atendimento: ISO timestamp (padrão: agora)

    Returns:
        True se sucesso
    """
    if not tenant_id or not cliente_actor_id:
        return False

    try:
        db = get_db()
        now = data_atendimento or datetime.now(timezone.utc).isoformat()

        # Atualizar cliente com ultimo_atendimento
        atualizacao = {
            "lead_status": "atendido",
            "lead_status_updated_at": now,
            "ultimo_atendimento": now,
            "ultima_interacao": now
        }

        db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).document(cliente_actor_id).set(atualizacao, merge=True)

        print(f"[MEC-F1-03] Cliente marcado como atendido: {cliente_actor_id}")
        return True

    except Exception as e:
        print(f"[ERRO] marcar_como_atendido: {str(e)}")
        return False


async def verificar_retorno_pendente(
    tenant_id: str,
    cliente_actor_id: str,
    dias_retorno: int = 15
) -> bool:
    """
    Verifica se cliente atendido completou o período de retorno pendente.

    Args:
        tenant_id: ID do tenant
        cliente_actor_id: ID do cliente
        dias_retorno: Dias após atendimento para considerar retorno pendente (padrão: 15)

    Returns:
        True se deve transicionar para retorno_pendente
    """
    if not tenant_id or not cliente_actor_id:
        return False

    try:
        db = get_db()

        # Carregar cliente
        doc = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).document(cliente_actor_id).get()

        if not doc.exists:
            return False

        dados = doc.to_dict()

        # Validar precondições
        if dados.get("lead_status") != "atendido":
            return False

        ultimo_atendimento_str = dados.get("ultimo_atendimento")
        if not ultimo_atendimento_str:
            return False

        # Calcular diferença de dias
        try:
            ultimo_atendimento = datetime.fromisoformat(
                ultimo_atendimento_str.replace("Z", "+00:00")
            )
            agora = datetime.now(timezone.utc)
            dias_passados = (agora - ultimo_atendimento).days

            if dias_passados >= dias_retorno:
                print(
                    f"[MEC-F1-03] Cliente {cliente_actor_id} "
                    f"completou {dias_passados} dias desde atendimento"
                )
                return True

        except Exception as e:
            print(f"[AVISO] Erro ao calcular dias: {str(e)}")
            return False

        return False

    except Exception as e:
        print(f"[ERRO] verificar_retorno_pendente: {str(e)}")
        return False


async def atualizar_retorno_pendente_tenant(
    tenant_id: str,
    dias_retorno: int = 15
) -> Dict[str, Any]:
    """
    Verifica TODOS os clientes atendidos do tenant e transiciona os que
    completaram o período.

    Operação idempotente: pode ser executada múltiplas vezes sem efeito colateral.

    Args:
        tenant_id: ID do tenant
        dias_retorno: Dias para considerar retorno pendente

    Returns:
        Dicionário com resumo: {processados, atualizados, erros}
    """
    if not tenant_id:
        return {"processados": 0, "atualizados": 0, "erros": 0}

    try:
        db = get_db()
        resumo = {"processados": 0, "atualizados": 0, "erros": 0}

        # Buscar todos os clientes em status "atendido"
        docs = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).where("lead_status", "==", "atendido").stream()

        for doc in docs:
            cliente_actor_id = doc.id
            resumo["processados"] += 1

            try:
                # Verificar se completou o período
                deve_atualizar = await verificar_retorno_pendente(
                    tenant_id,
                    cliente_actor_id,
                    dias_retorno
                )

                if deve_atualizar:
                    # Atualizar para retorno_pendente
                    sucesso = await atualizar_lead_status(
                        cliente_actor_id=cliente_actor_id,
                        tenant_id=tenant_id,
                        novo_status="retorno_pendente",
                        motivo=f"regra_temporal_{dias_retorno}_dias",
                        executor_id="sistema_retorno_pendente"
                    )

                    if sucesso:
                        resumo["atualizados"] += 1

            except Exception as e:
                print(f"[ERRO] Processando cliente {cliente_actor_id}: {str(e)}")
                resumo["erros"] += 1

        print(
            f"[MEC-F1-03] Atualizacao tenant {tenant_id}: "
            f"{resumo['processados']} processados, "
            f"{resumo['atualizados']} atualizados, "
            f"{resumo['erros']} erros"
        )

        return resumo

    except Exception as e:
        print(f"[ERRO] atualizar_retorno_pendente_tenant: {str(e)}")
        return {"processados": 0, "atualizados": 0, "erros": 1}


async def listar_clientes_retorno_pendente(
    tenant_id: str,
    dias_retorno: int = 15
) -> List[Dict[str, Any]]:
    """
    Lista clientes que estão em retorno_pendente.

    Também verifica clientes em "atendido" e transiciona se necessário.

    Args:
        tenant_id: ID do tenant
        dias_retorno: Dias para considerar retorno pendente

    Returns:
        Lista de clientes em retorno_pendente
    """
    if not tenant_id:
        return []

    try:
        db = get_db()

        # Primeiro, atualizar clientes atendidos que completaram período
        await atualizar_retorno_pendente_tenant(tenant_id, dias_retorno)

        # Depois, buscar todos em retorno_pendente
        docs = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).where("lead_status", "==", "retorno_pendente").stream()

        clientes = []
        for doc in docs:
            cliente_dict = doc.to_dict()
            cliente_dict["actor_id"] = doc.id

            # Calcular dias desde atendimento
            ultimo_atendimento_str = cliente_dict.get("ultimo_atendimento")
            if ultimo_atendimento_str:
                try:
                    ultimo_atendimento = datetime.fromisoformat(
                        ultimo_atendimento_str.replace("Z", "+00:00")
                    )
                    agora = datetime.now(timezone.utc)
                    dias_passados = (agora - ultimo_atendimento).days
                    cliente_dict["dias_desde_atendimento"] = dias_passados
                except:
                    cliente_dict["dias_desde_atendimento"] = None

            clientes.append(cliente_dict)

        # Ordenar por tempo desde atendimento (mais urgentes primeiro)
        clientes.sort(
            key=lambda x: x.get("dias_desde_atendimento") or 0,
            reverse=True
        )

        return clientes

    except Exception as e:
        print(f"[ERRO] listar_clientes_retorno_pendente: {str(e)}")
        return []


async def recuperar_de_retorno_pendente(
    tenant_id: str,
    cliente_actor_id: str,
    novo_status: str = "agendado"
) -> bool:
    """
    Transiciona cliente de retorno_pendente para novo status.

    Usado quando cliente agenda novamente ou volta a conversar.

    Args:
        tenant_id: ID do tenant
        cliente_actor_id: ID do cliente
        novo_status: Status para o qual transicionar

    Returns:
        True se sucesso
    """
    if not tenant_id or not cliente_actor_id:
        return False

    try:
        db = get_db()

        # Verificar se está em retorno_pendente
        doc = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).document(cliente_actor_id).get()

        if not doc.exists:
            return False

        dados = doc.to_dict()
        if dados.get("lead_status") != "retorno_pendente":
            print(
                f"[AVISO] Cliente {cliente_actor_id} "
                f"nao esta em retorno_pendente, está em {dados.get('lead_status')}"
            )
            return False

        # Transicionar para novo status
        sucesso = await atualizar_lead_status(
            cliente_actor_id=cliente_actor_id,
            tenant_id=tenant_id,
            novo_status=novo_status,
            motivo="recuperacao_retorno_pendente",
            executor_id="sistema_retorno_pendente"
        )

        if sucesso:
            print(
                f"[MEC-F1-03] Cliente {cliente_actor_id} "
                f"recuperado de retorno_pendente para {novo_status}"
            )

        return sucesso

    except Exception as e:
        print(f"[ERRO] recuperar_de_retorno_pendente: {str(e)}")
        return False
