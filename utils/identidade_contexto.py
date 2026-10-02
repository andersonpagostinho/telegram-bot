# -*- coding: utf-8 -*-
# utils/identidade_contexto.py

"""
Contexto normalizado de identidade, agnóstico de canal.

Define como o sistema identifica:
- user_id: Identificador do usuário no canal (telegram_id ou wa_id)
- tenant_id: ID da organização/proprietário
- actor_id: Identificador canônico do ator
- canal: Tipo de canal ("telegram" ou "whatsapp")
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class IdentidadeContexto:
    """
    Contexto normalizado de identidade, canal-agnóstico.

    Campos obrigatórios:
    - user_id: ID do usuário no canal (telegram_id ou wa_id)
    - tenant_id: ID da organização
    - actor_id: ID canônico do ator (whatsapp:5511... ou tg:123...)
    - canal: "telegram" ou "whatsapp"

    Campos opcionais:
    - actor_tipo: "dono", "cliente", "profissional" (resolvido após identidade)
    - actor_nome: Nome do ator (para logs)
    - tenant_nome: Nome da organização (para logs)
    """

    user_id: str
    tenant_id: str
    actor_id: str
    canal: str
    actor_tipo: Optional[str] = None
    actor_nome: Optional[str] = None
    tenant_nome: Optional[str] = None

    def __post_init__(self):
        """Validar campos obrigatórios."""
        if not self.user_id:
            raise ValueError("user_id é obrigatório e não pode estar vazio")
        if not self.tenant_id:
            raise ValueError("tenant_id é obrigatório e não pode estar vazio")
        if not self.actor_id:
            raise ValueError("actor_id é obrigatório e não pode estar vazio")
        if self.canal not in ("telegram", "whatsapp"):
            raise ValueError(f"canal deve ser 'telegram' ou 'whatsapp', recebido: {self.canal}")

    def __repr__(self) -> str:
        return (
            f"IdentidadeContexto("
            f"user_id={self.user_id}, "
            f"tenant_id={self.tenant_id}, "
            f"actor_id={self.actor_id}, "
            f"canal={self.canal}"
            f")"
        )


def criar_identidade_whatsapp(
    wa_id: str,
    phone_number_id: str,
    tenant_id: str,
) -> IdentidadeContexto:
    """
    Factory para criar IdentidadeContexto do WhatsApp.

    Args:
        wa_id: Identificador do usuário no WhatsApp (número de telefone)
        phone_number_id: ID do endpoint WhatsApp (usado para resolver tenant)
        tenant_id: ID da organização/proprietário (resolvido via phone_number_id)

    Returns:
        IdentidadeContexto normalizado

    Raises:
        ValueError: Se algum campo obrigatório for inválido
    """
    if not wa_id:
        raise ValueError("wa_id é obrigatório para WhatsApp")
    if not phone_number_id:
        raise ValueError("phone_number_id é obrigatório para WhatsApp")
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório para WhatsApp")

    actor_id = f"whatsapp:{wa_id}"

    return IdentidadeContexto(
        user_id=wa_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        canal="whatsapp",
    )


def criar_identidade_telegram(
    telegram_id: str,
    canal_tenant_id: Optional[str] = None,
) -> IdentidadeContexto:
    """
    Factory para criar IdentidadeContexto do Telegram.

    Args:
        telegram_id: ID do usuário no Telegram
        canal_tenant_id: ID do tenant (opcional, pode ser resolvido depois)

    Returns:
        IdentidadeContexto normalizado

    Raises:
        ValueError: Se telegram_id for inválido
    """
    if not telegram_id:
        raise ValueError("telegram_id é obrigatório para Telegram")

    actor_id = f"tg:{telegram_id}"

    # Para Telegram, tenant_id pode vir como parâmetro ou ser resolvido depois
    # Se não vier, usar um valor placeholder que será resolvido no router
    tenant_id = canal_tenant_id or f"telegram_user_{telegram_id}"

    return IdentidadeContexto(
        user_id=telegram_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        canal="telegram",
    )


def validar_identidade_whatsapp(identidade: IdentidadeContexto) -> bool:
    """
    Validar que uma identidade WhatsApp tem tenant_id correto.

    Regra P0: tenant_id NUNCA deve ser wa_id para WhatsApp.

    Args:
        identidade: IdentidadeContexto a validar

    Returns:
        True se válida, False caso contrário
    """
    if identidade.canal != "whatsapp":
        return True  # Validação só para WhatsApp

    # Regra crítica: tenant_id NUNCA deve ser wa_id
    if identidade.tenant_id == identidade.user_id:
        print(
            f"[ERRO_P0] WhatsApp tenant_id é wa_id (FALLBACK INCORRETO): "
            f"wa_id={identidade.user_id}, tenant_id={identidade.tenant_id}",
            flush=True
        )
        return False

    return True
