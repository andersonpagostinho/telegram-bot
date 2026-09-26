# Serviço: Identidade do Endpoint WhatsApp
# Responsabilidade: Mapear phone_number_id → tenant_id
# Padrão: Firestore real, determinístico, idempotente, falha segura

from datetime import datetime
import pytz
from services.firestore_client import get_db

FUSO_BR = pytz.timezone("America/Sao_Paulo")


def registrar_endpoint_whatsapp(
    phone_number_id: str,
    tenant_id: str,
    display_phone_number: str = "",
    waba_id: str = ""
) -> dict:
    """
    Registra ou valida um endpoint WhatsApp para um tenant.

    Path: WhatsAppEndpoints/{phone_number_id}

    Validações:
    - Determinístico: mesmo endpoint sempre mapeia ao mesmo tenant
    - Idempotente: registrar 2x não causa inconsistência
    - Colisão: endpoint já associado a outro tenant é rejeitado

    Args:
        phone_number_id: ID único do endpoint (fornecido por Meta)
        tenant_id: Tenant que possui esse endpoint
        display_phone_number: Número formatado (ex: "55 11 93456-7890")
        waba_id: WhatsApp Business Account ID

    Returns:
        {"ok": True, "phone_number_id": ..., "tenant_id": ...}
        ou {"ok": False, "motivo": "..."}
    """
    if not phone_number_id or not tenant_id:
        return {"ok": False, "motivo": "phone_number_id e tenant_id são obrigatórios"}

    try:
        # Buscar documento existente (síncrono)
        doc = get_db().collection("WhatsAppEndpoints").document(phone_number_id).get()

        if doc.exists:
            # Endpoint já existe
            doc_data = doc.to_dict()
            tenant_existente = doc_data.get("tenant_id")

            if tenant_existente == tenant_id:
                # Idempotência: mesmo tenant, mesma operação
                print(
                    f"[INFO] Endpoint {phone_number_id} já registrado para {tenant_id} (idempotente)"
                )
                return {"ok": True, "phone_number_id": phone_number_id, "tenant_id": tenant_id, "ja_existia": True}

            else:
                # Colisão: outro tenant tentando usar esse endpoint
                print(
                    f"[ERRO] Endpoint {phone_number_id} já registrado para {tenant_existente}, "
                    f"não pode ser reassociado a {tenant_id}"
                )
                return {
                    "ok": False,
                    "motivo": f"Endpoint já registrado para outro tenant ({tenant_existente})",
                    "phone_number_id": phone_number_id,
                    "tenant_existente": tenant_existente

                }

        # Criar novo registro
        now = datetime.now(FUSO_BR).isoformat()
        endpoint_data = {
            "phone_number_id": phone_number_id,
            "tenant_id": tenant_id,
            "display_phone_number": display_phone_number or "",
            "waba_id": waba_id or "",
            "criado_em": now,
            "status": "ativo",
            "validado": True
        }

        get_db().collection("WhatsAppEndpoints").document(phone_number_id).set(endpoint_data)

        print(f"[OK] Endpoint {phone_number_id} registrado para {tenant_id}")
        return {"ok": True, "phone_number_id": phone_number_id, "tenant_id": tenant_id, "ja_existia": False}

    except Exception as e:
        print(f"[ERRO] registrar_endpoint_whatsapp: {e}")
        return {"ok": False, "motivo": f"Erro ao registrar: {str(e)}"}


def resolver_tenant_por_endpoint(phone_number_id: str) -> str | None:
    """
    Resolve tenant_id para um phone_number_id.

    Determinístico: mesmo phone_number_id sempre retorna mesmo tenant_id.
    Falha segura: endpoint desconhecido retorna None, não inferência.

    Path: WhatsAppEndpoints/{phone_number_id}

    Args:
        phone_number_id: ID do endpoint WhatsApp

    Returns:
        tenant_id string, ou None se endpoint desconhecido
    """
    if not phone_number_id:
        return None

    try:
        doc = get_db().collection("WhatsAppEndpoints").document(phone_number_id).get()

        if doc.exists:
            doc_data = doc.to_dict()
            if doc_data.get("status") == "ativo":
                tenant_id = doc_data.get("tenant_id")
                print(f"[OK] resolver_tenant_por_endpoint({phone_number_id}): {tenant_id}")
                return tenant_id

        print(f"[AVISO] Endpoint {phone_number_id} desconhecido ou inativo")
        return None

    except Exception as e:
        print(f"[AVISO] resolver_tenant_por_endpoint({phone_number_id}): {str(e)[:50]}")
        return None


def validar_endpoint_para_tenant(phone_number_id: str, tenant_id: str) -> bool:
    """
    Valida se um endpoint pertence a um tenant específico.

    Args:
        phone_number_id: ID do endpoint
        tenant_id: ID esperado do tenant

    Returns:
        True se válido, False caso contrário
    """
    if not phone_number_id or not tenant_id:
        return False

    try:
        tenant_resolvido = resolver_tenant_por_endpoint(phone_number_id)

        if tenant_resolvido == tenant_id:
            print(f"[DEBUG] Endpoint {phone_number_id} validado para {tenant_id}")
            return True

        print(
            f"[AVISO] Endpoint {phone_number_id} não pertence a {tenant_id} "
            f"(pertence a {tenant_resolvido})"
        )
        return False

    except Exception as e:
        print(f"[AVISO] validar_endpoint_para_tenant: {e}")
        return False


def listar_endpoints_do_tenant(tenant_id: str) -> list:
    """
    Lista todos os endpoints registrados de um tenant.

    Apenas para auditoria/administração.

    Args:
        tenant_id: ID do tenant

    Returns:
        Lista de documentos endpoint
    """
    if not tenant_id:
        return []

    try:
        docs = list(
            get_db()
            .collection("WhatsAppEndpoints")
            .where("tenant_id", "==", tenant_id)
            .where("status", "==", "ativo")
            .stream()
        )

        return [doc.to_dict() for doc in docs]

    except Exception as e:
        print(f"[AVISO] listar_endpoints_do_tenant: {e}")
        return []
