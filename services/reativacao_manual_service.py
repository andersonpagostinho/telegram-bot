"""
F1-04: Reativação Manual

Responsável por:
- Listar clientes inativos para possível reativação
- Gerar sugestões de reativação (SEM enviar mensagens)
- Apenas leitura de dados existentes
- NÃO envia WhatsApp, email ou notificação
- NÃO cria FollowUps ou campanhas
- Decisão humana permanece no dono

Fonte única: Clientes/{tenant_id}/Clientes/{cliente_actor_id}
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from services.firestore_client import get_db


async def listar_clientes_inativos(
    tenant_id: str,
    dias_inatividade: int = 30
) -> List[Dict[str, Any]]:
    """
    Lista clientes inativos (sem interação por 30+ dias).

    Args:
        tenant_id: ID do tenant
        dias_inatividade: Dias para considerar inativo (padrão: 30)

    Returns:
        Lista de clientes inativos ordenados por urgência
    """
    if not tenant_id:
        return []

    try:
        db = get_db()
        agora = datetime.now(timezone.utc)
        data_limite = (agora - timedelta(days=dias_inatividade)).isoformat()

        # Listar clientes com lead_status == "inativo"
        docs = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).where("lead_status", "==", "inativo").stream()

        clientes = []
        for doc in docs:
            cliente_dict = doc.to_dict()
            cliente_dict["actor_id"] = doc.id

            # Calcular dias de inatividade
            ultima_interacao_str = cliente_dict.get("ultima_interacao")
            if ultima_interacao_str:
                try:
                    ultima_interacao = datetime.fromisoformat(
                        ultima_interacao_str.replace("Z", "+00:00")
                    )
                    dias_inativo = (agora - ultima_interacao).days
                    cliente_dict["dias_inativo"] = dias_inativo
                except:
                    cliente_dict["dias_inativo"] = None

            clientes.append(cliente_dict)

        # Ordenar por dias de inatividade (mais urgentes primeiro)
        clientes.sort(
            key=lambda x: x.get("dias_inativo") or 0,
            reverse=True
        )

        return clientes

    except Exception as e:
        print(f"[ERRO] listar_clientes_inativos: {str(e)}")
        return []


async def listar_clientes_retorno_pendente(
    tenant_id: str
) -> List[Dict[str, Any]]:
    """
    Lista clientes em status retorno_pendente.

    Args:
        tenant_id: ID do tenant

    Returns:
        Lista de clientes em retorno_pendente
    """
    if not tenant_id:
        return []

    try:
        db = get_db()
        agora = datetime.now(timezone.utc)

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
                    dias_desde_atendimento = (agora - ultimo_atendimento).days
                    cliente_dict["dias_desde_atendimento"] = dias_desde_atendimento
                except:
                    cliente_dict["dias_desde_atendimento"] = None

            clientes.append(cliente_dict)

        # Ordenar por urgência (mais dias = mais urgente)
        clientes.sort(
            key=lambda x: x.get("dias_desde_atendimento") or 0,
            reverse=True
        )

        return clientes

    except Exception as e:
        print(f"[ERRO] listar_clientes_retorno_pendente: {str(e)}")
        return []


async def gerar_sugestao_reativacao(cliente: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gera sugestão determinística de reativação para um cliente.

    Apenas informa dados, não decide nada.

    Args:
        cliente: Documento de cliente

    Returns:
        Dicionário com sugestão estruturada
    """
    if not cliente:
        return {}

    try:
        actor_id = cliente.get("actor_id")
        nome = cliente.get("nome_detectado", "Cliente")
        ultima_interacao_str = cliente.get("ultima_interacao")
        ultimo_atendimento_str = cliente.get("ultimo_atendimento")
        lead_status = cliente.get("lead_status")
        total_agendamentos = cliente.get("total_agendamentos", 0)

        sugestao = {
            "actor_id": actor_id,
            "nome": nome,
            "lead_status": lead_status,
            "total_agendamentos": total_agendamentos,
            "dias_inativo": cliente.get("dias_inativo"),
            "dias_desde_atendimento": cliente.get("dias_desde_atendimento")
        }

        # Motivo determinístico
        if lead_status == "retorno_pendente":
            dias = cliente.get("dias_desde_atendimento", 0)
            sugestao["motivo"] = f"Não agendou há {dias} dias após atendimento"
            sugestao["acao_sugerida"] = "Verificar interesse em retornar"

        elif lead_status == "inativo":
            dias = cliente.get("dias_inativo", 0)
            sugestao["motivo"] = f"Sem interação há {dias} dias"
            sugestao["acao_sugerida"] = "Retomar contato"

        else:
            sugestao["motivo"] = f"Status: {lead_status}"
            sugestao["acao_sugerida"] = None

        return sugestao

    except Exception as e:
        print(f"[ERRO] gerar_sugestao_reativacao: {str(e)}")
        return {}


async def gerar_resumo_reativacao(tenant_id: str) -> Dict[str, Any]:
    """
    Gera resumo de clientes que poderiam ser reativados.

    Args:
        tenant_id: ID do tenant

    Returns:
        Dicionário com resumo consolidado
    """
    if not tenant_id:
        return {"erro": "tenant_id ausente"}

    try:
        # Listar inativos e retorno_pendente
        inativos = await listar_clientes_inativos(tenant_id)
        retorno_pendente = await listar_clientes_retorno_pendente(tenant_id)

        resumo = {
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "total_inativos": len(inativos),
            "total_retorno_pendente": len(retorno_pendente),
            "total_para_reativar": len(inativos) + len(retorno_pendente),
            "clientes_inativos": inativos,
            "clientes_retorno_pendente": retorno_pendente
        }

        return resumo

    except Exception as e:
        print(f"[ERRO] gerar_resumo_reativacao: {str(e)}")
        return {"erro": str(e)}


def formatar_sugestao_para_dono(cliente: Dict[str, Any]) -> str:
    """
    Formata sugestão em mensagem legível para o dono.

    Apenas formatação de dados existentes, sem decisão.

    Args:
        cliente: Documento de cliente com campos calculados

    Returns:
        String formatada
    """
    nome = cliente.get("nome_detectado", "Cliente")
    dias_inativo = cliente.get("dias_inativo")
    dias_desde_atendimento = cliente.get("dias_desde_atendimento")
    lead_status = cliente.get("lead_status")
    total_agendamentos = cliente.get("total_agendamentos", 0)

    if lead_status == "retorno_pendente":
        mensagem = (
            f"🔄 *{nome}*\n"
            f"Último atendimento: {dias_desde_atendimento} dias atrás\n"
            f"Total de agendamentos: {total_agendamentos}\n"
            f"_Pode estar interessado em retornar_"
        )

    elif lead_status == "inativo":
        mensagem = (
            f"😴 *{nome}*\n"
            f"Sem contato: {dias_inativo} dias\n"
            f"Total de agendamentos: {total_agendamentos}\n"
            f"_Pode estar perdendo interesse_"
        )

    else:
        mensagem = f"ℹ️ *{nome}* (Status: {lead_status})"

    return mensagem


async def gerar_lista_reativacao_formatada(tenant_id: str) -> str:
    """
    Gera lista formatada de clientes para reativação.

    Args:
        tenant_id: ID do tenant

    Returns:
        Mensagem formatada para enviar ao dono (ação manual)
    """
    if not tenant_id:
        return "❌ tenant_id ausente"

    try:
        # Listar inativos e retorno_pendente
        inativos = await listar_clientes_inativos(tenant_id)
        retorno_pendente = await listar_clientes_retorno_pendente(tenant_id)

        total = len(inativos) + len(retorno_pendente)

        if total == 0:
            return "✅ Todos os seus clientes estão ativos!"

        mensagem = f"📋 *Clientes para Reativar* ({total})\n\n"

        if retorno_pendente:
            mensagem += "🔄 *Retorno Pendente*\n"
            for cliente in retorno_pendente[:5]:  # Limitar a 5
                mensagem += f"• {formatar_sugestao_para_dono(cliente)}\n\n"

            if len(retorno_pendente) > 5:
                mensagem += f"... e mais {len(retorno_pendente) - 5}\n\n"

        if inativos:
            mensagem += "😴 *Inativos*\n"
            for cliente in inativos[:5]:  # Limitar a 5
                mensagem += f"• {formatar_sugestao_para_dono(cliente)}\n\n"

            if len(inativos) > 5:
                mensagem += f"... e mais {len(inativos) - 5}\n\n"

        mensagem += "_Escolha manualmente quem você gostaria de contatare._"

        return mensagem

    except Exception as e:
        print(f"[ERRO] gerar_lista_reativacao_formatada: {str(e)}")
        return f"❌ Erro: {str(e)}"
