"""
Serviço de governança conversacional para NeoEve.

Responsável por:
- Carregar e salvar configurações de governança
- Registrar auditoria de decisões
- Validar tenant_id para isolamento multi-tenant

NOTA: Em Sprint 1, este serviço é criado mas não é chamado.
As decisões de bloqueio são implementadas em Sprint 2+.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from services.firestore_client import get_db


async def carregar_governanca(actor_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Carrega configurações de governança para um ator.

    Args:
        actor_id: Identificador do ator (whatsapp:5511999005)
        tenant_id: Identificador do tenant (dono_id)

    Returns:
        Dict com configurações de governança ou {} se não existe

    Exemplo:
        governanca = await carregar_governanca("whatsapp:5511999005", "tenant_abc")
        # {
        #   "responder_automaticamente": True,
        #   "modo_dono": "normal",
        #   "bloqueado_ate": None,
        #   "_tenant_id_guard": "tenant_abc"
        # }
    """
    db = get_db()

    # Validar tenant_id_guard
    if not tenant_id:
        raise ValueError("tenant_id obrigatório para isolamento multi-tenant")

    try:
        path = f"Clientes/{tenant_id}/Governanca/{actor_id}"
        doc = db.collection("Clientes").document(tenant_id).collection("Governanca").document(actor_id).get()

        if doc.exists:
            data = doc.to_dict()
            # Validar tenant_id_guard
            if data.get("_tenant_id_guard") != tenant_id:
                raise ValueError(f"Tenant mismatch: esperado {tenant_id}, encontrado {data.get('_tenant_id_guard')}")
            return data

        return {}

    except Exception as e:
        # Log erro mas não falha - retorna vazio (sem governanca)
        print(f"Erro ao carregar governanca {actor_id} em {tenant_id}: {e}")
        return {}


async def salvar_governanca(
    actor_id: str,
    tenant_id: str,
    responder_automaticamente: Optional[bool] = None,
    modo_dono: Optional[str] = None,
    bloqueado_ate: Optional[str] = None,
    motivo: Optional[str] = None,
    executor_id: Optional[str] = None
) -> bool:
    """
    Salva configurações de governança para um ator.

    Args:
        actor_id: Identificador do ator
        tenant_id: Identificador do tenant
        responder_automaticamente: Se bot responde automaticamente (bool)
        modo_dono: Modo do dono ('normal', 'admin', 'silencioso')
        bloqueado_ate: Até quando está bloqueado (ISO8601)
        motivo: Razão da alteração
        executor_id: Quem alterou (contato, dono, sistema)

    Returns:
        True se sucesso, False se erro
    """
    db = get_db()

    if not tenant_id:
        raise ValueError("tenant_id obrigatório")

    try:
        # Carregar governanca atual para saber valor anterior
        governanca_atual = await carregar_governanca(actor_id, tenant_id)

        # Preparar novo documento
        atualizado_em = datetime.now(timezone.utc).isoformat()
        novo_documento = {
            "actor_id": actor_id,
            "_tenant_id_guard": tenant_id,
            "atualizado_em": atualizado_em,
            "atualizado_por": executor_id or "sistema"
        }

        # Adicionar campos se fornecidos
        if responder_automaticamente is not None:
            novo_documento["responder_automaticamente"] = responder_automaticamente
        elif "responder_automaticamente" in governanca_atual:
            novo_documento["responder_automaticamente"] = governanca_atual["responder_automaticamente"]
        else:
            novo_documento["responder_automaticamente"] = True  # Default

        if modo_dono is not None:
            novo_documento["modo_dono"] = modo_dono
        elif "modo_dono" in governanca_atual:
            novo_documento["modo_dono"] = governanca_atual["modo_dono"]
        else:
            novo_documento["modo_dono"] = "normal"  # Default

        if bloqueado_ate is not None:
            novo_documento["bloqueado_ate"] = bloqueado_ate
        elif "bloqueado_ate" in governanca_atual:
            novo_documento["bloqueado_ate"] = governanca_atual["bloqueado_ate"]

        if motivo:
            novo_documento["motivo"] = motivo

        # Salvar em Firestore
        path = f"Clientes/{tenant_id}/Governanca/{actor_id}"
        db.collection("Clientes").document(tenant_id).collection("Governanca").document(actor_id).set(novo_documento)

        # Registrar auditoria se houve mudança
        if responder_automaticamente is not None:
            valor_anterior = governanca_atual.get("responder_automaticamente", True)
            if valor_anterior != responder_automaticamente:
                await registrar_auditoria(
                    actor_id_afetado=actor_id,
                    tenant_id=tenant_id,
                    campo_alterado="responder_automaticamente",
                    valor_anterior=valor_anterior,
                    valor_novo=responder_automaticamente,
                    executor_id=executor_id,
                    motivo=motivo
                )

        if modo_dono is not None:
            valor_anterior = governanca_atual.get("modo_dono", "normal")
            if valor_anterior != modo_dono:
                await registrar_auditoria(
                    actor_id_afetado=actor_id,
                    tenant_id=tenant_id,
                    campo_alterado="modo_dono",
                    valor_anterior=valor_anterior,
                    valor_novo=modo_dono,
                    executor_id=executor_id,
                    motivo=motivo
                )

        return True

    except Exception as e:
        print(f"Erro ao salvar governanca {actor_id} em {tenant_id}: {e}")
        return False


async def registrar_auditoria(
    actor_id_afetado: str,
    tenant_id: str,
    campo_alterado: str,
    valor_anterior: Any,
    valor_novo: Any,
    executor_id: Optional[str] = None,
    motivo: Optional[str] = None,
    comando: Optional[str] = None
) -> bool:
    """
    Registra auditoria de alteração de governanca.

    Args:
        actor_id_afetado: Quem foi afetado
        tenant_id: Identificador do tenant
        campo_alterado: Qual campo foi alterado
        valor_anterior: Valor antes
        valor_novo: Valor depois
        executor_id: Quem executou
        motivo: Por que foi alterado
        comando: Comando executado (/pausar, /retomar, etc)

    Returns:
        True se sucesso, False se erro
    """
    db = get_db()

    if not tenant_id:
        raise ValueError("tenant_id obrigatório")

    try:
        # Gerar evento_id único
        timestamp_now = datetime.now(timezone.utc)
        evento_id = f"audit_gov_{timestamp_now.strftime('%Y%m%d_%H%M%S')}_{actor_id_afetado.replace(':', '_')}"

        documento = {
            "evento_id": evento_id,
            "timestamp": timestamp_now.isoformat(),
            "actor_id_afetado": actor_id_afetado,
            "campo_alterado": campo_alterado,
            "valor_anterior": valor_anterior,
            "valor_novo": valor_novo,
            "_tenant_id_guard": tenant_id,
            "_schema_version": 1
        }

        if executor_id:
            documento["executor_id"] = executor_id

        if motivo:
            documento["motivo"] = motivo

        if comando:
            documento["comando"] = comando

        # Salvar em AuditoriaGovernanca
        path = f"Clientes/{tenant_id}/AuditoriaGovernanca/{evento_id}"
        db.collection("Clientes").document(tenant_id).collection("AuditoriaGovernanca").document(evento_id).set(documento)

        return True

    except Exception as e:
        print(f"Erro ao registrar auditoria em {tenant_id}: {e}")
        return False


async def obter_auditoria_ator(actor_id: str, tenant_id: str, limit: int = 10) -> list:
    """
    Obtém histórico de auditoria para um ator.

    Args:
        actor_id: Identificador do ator
        tenant_id: Identificador do tenant
        limit: Número máximo de registros

    Returns:
        Lista de documentos de auditoria
    """
    db = get_db()

    if not tenant_id:
        return []

    try:
        path = f"Clientes/{tenant_id}/AuditoriaGovernanca"
        docs = db.collection("Clientes").document(tenant_id).collection("AuditoriaGovernanca")\
            .where("actor_id_afetado", "==", actor_id)\
            .order_by("timestamp", direction="DESCENDING")\
            .limit(limit)\
            .stream()

        auditoria = []
        for doc in docs:
            auditoria.append(doc.to_dict())

        return auditoria

    except Exception as e:
        print(f"Erro ao obter auditoria de {actor_id} em {tenant_id}: {e}")
        return []
