"""
Token de Ativação Telegram com HMAC-SHA256

Formato: opaco, autenticado, expiável, single-use

Payload: tenant_id, actor_id, token_id, exp
Verificação: HMAC-SHA256 com chave secreta
Armazenamento: Firestore scoped a Clientes/{tenant_id}/TokensAtivacao/{token_id}
"""

import os
import json
import hmac
import hashlib
import uuid
import time
from datetime import datetime, timedelta
import pytz
import base64
from dotenv import load_dotenv

load_dotenv()

ACTIVATION_SECRET = os.getenv("ACTIVATION_TOKEN_SECRET")
TOKEN_VALIDITY_HOURS = 24


def gerar_activation_token(tenant_id: str, actor_id: str, validity_hours: int = TOKEN_VALIDITY_HOURS) -> str:
    """
    Gera token HMAC de ativação.

    Args:
        tenant_id: ID do tenant
        actor_id: ID do ator (owner ou profissional)
        validity_hours: horas até expiração

    Returns:
        Token opaco, autenticado, base64-encoded

    Raises:
        ValueError se ACTIVATION_TOKEN_SECRET não estiver configurado
    """
    if not ACTIVATION_SECRET:
        raise ValueError("ACTIVATION_TOKEN_SECRET não configurado")

    now = datetime.now(pytz.UTC)
    token_id = str(uuid.uuid4())
    expires_at = now + timedelta(hours=validity_hours)

    payload = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "token_id": token_id,
        "issued_at": now.timestamp(),
        "expires_at": expires_at.timestamp()
    }

    payload_json = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(
        ACTIVATION_SECRET.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).digest()

    token_bytes = payload_json.encode() + signature
    token = base64.urlsafe_b64encode(token_bytes).decode().rstrip('=')

    return token


def validar_activation_token(token: str) -> tuple[str, str, str] | None:
    """
    Valida e descodifica token HMAC.

    Args:
        token: Token base64-encoded

    Returns:
        (tenant_id, actor_id, token_id) ou None se inválido/expirado
    """
    if not ACTIVATION_SECRET or not token:
        return None

    try:
        token_bytes = base64.urlsafe_b64decode(token + '==')

        payload_json = token_bytes[:-32].decode()
        signature_received = token_bytes[-32:]

        signature_expected = hmac.new(
            ACTIVATION_SECRET.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(signature_received, signature_expected):
            return None

        payload = json.loads(payload_json)

        now = datetime.now(pytz.UTC).timestamp()
        if now > payload.get("expires_at", 0):
            return None

        return (
            payload.get("tenant_id"),
            payload.get("actor_id"),
            payload.get("token_id")
        )
    except Exception:
        return None
