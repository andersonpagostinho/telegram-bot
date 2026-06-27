"""
Serviço de Whitelist para MEC-03 (responder_automaticamente).

Responsável por:
- Verificar se mensagem está em Whitelist Classe A
- Permitir resposta automática para mensagens permitidas
- Bloquear mensagens fora da whitelist quando responder_automaticamente == False
- Registrar auditoria de bloqueios

Whitelist Classe A:
- A-01: Confirmação positiva (sim, confirmo, ok)
- A-02: Confirmação negativa (não, cancelo)
- A-03: Cancelamento (cancelar)
- A-04: Refinamento de cancelamento
- A-05: Onboarding (primeiro contato)
- A-06: Comandos administrativos
"""

import re
from typing import Dict, List, Optional, Tuple
from services.governanca_service import carregar_governanca, registrar_auditoria


# Padrões Whitelist Classe A
WHITELIST_PATTERNS = {
    "A-01": {  # Confirmação positiva
        "name": "Confirmação Positiva",
        "patterns": [
            r"^\s*(sim|yes|ok|okay|certo|confirmo|confirmado|ok tudo bem|pode ir|pode prosseguir)\s*$",
            r"^\s*👍\s*$",
            r"^\s*(isso|isso mesmo|exato|verdade)\s*$"
        ]
    },
    "A-02": {  # Confirmação negativa
        "name": "Confirmação Negativa",
        "patterns": [
            r"^\s*(não|nao|no|nope|nunca|jamais|não mesmo)\s*$",
            r"^\s*👎\s*$",
        ]
    },
    "A-03": {  # Cancelamento
        "name": "Cancelamento",
        "patterns": [
            r"^\s*(cancelar|cancela|cancelado|cancele|anular|anule)\s*$",
            r"^\s*(para|stop|parar|pare)\s*$"
        ]
    },
    "A-04": {  # Refinamento de cancelamento
        "name": "Refinamento de Cancelamento",
        "patterns": [
            r"cancelar.*agendamento",
            r"não.*quero.*agendamento",
            r"desmarcar"
        ]
    },
    "A-05": {  # Onboarding
        "name": "Onboarding",
        "patterns": [
            r"^\s*(olá|ola|oi|opa|e aí|eai|tudo bem|tudo certo|opa e aí)\s*$",
            r"^(teste|testing|test)$",
        ]
    },
    "A-06": {  # Comandos administrativos
        "name": "Comandos Administrativos",
        "patterns": [
            r"^/(help|ajuda|menu|pausar|retomar|status|debug).*$",
        ]
    }
}


def classificar_com_whitelist(
    mensagem: str,
    actor_id: str
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Classifica mensagem na Whitelist Classe A.

    Args:
        mensagem: Texto da mensagem
        actor_id: ID do ator (para auditoria)

    Returns:
        (está_na_whitelist, categoria, nome_categoria)
        - está_na_whitelist: bool
        - categoria: str (A-01, A-02, etc) ou None
        - nome_categoria: str legível ou None
    """
    if not mensagem or not isinstance(mensagem, str):
        return False, None, None

    mensagem_limpa = mensagem.strip().lower()

    for categoria, info in WHITELIST_PATTERNS.items():
        for pattern in info["patterns"]:
            if re.match(pattern, mensagem_limpa, re.IGNORECASE):
                return True, categoria, info["name"]

    return False, None, None


async def verificar_com_whitelist(
    mensagem: str,
    actor_id: str,
    tenant_id: str,
    registrar_bloqueio: bool = True
) -> Tuple[bool, Optional[Dict]]:
    """
    Verifica se mensagem pode ser respondida automaticamente.

    Fluxo:
    1. Carregar responder_automaticamente de Governanca
    2. Se True: permite qualquer mensagem
    3. Se False: verifica Whitelist Classe A
       - Se na whitelist: permite
       - Se não: bloqueia e registra auditoria

    Args:
        mensagem: Texto da mensagem
        actor_id: ID do ator
        tenant_id: ID do tenant
        registrar_bloqueio: Se deve registrar bloqueio em auditoria

    Returns:
        (permitida, detalhes_bloqueio)
        - permitida: bool (True = processar, False = bloquear)
        - detalhes_bloqueio: dict com informações do bloqueio ou None
    """
    # Carregar governanca
    governanca = await carregar_governanca(actor_id, tenant_id)
    responder_automaticamente = governanca.get("responder_automaticamente", True)

    # Se responder_automaticamente == True, sempre permitir
    if responder_automaticamente:
        return True, None

    # responder_automaticamente == False: verificar whitelist
    esta_na_whitelist, categoria, nome_categoria = classificar_com_whitelist(
        mensagem, actor_id
    )

    if esta_na_whitelist:
        # Mensagem está na whitelist: permitir
        return True, None
    else:
        # Mensagem não está na whitelist: bloquear
        detalhes_bloqueio = {
            "motivo": "responder_automaticamente=False e mensagem fora de Whitelist Classe A",
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "categoria_esperada": "Whitelist Classe A (A-01 a A-06)",
            "registrado": False
        }

        # Registrar auditoria se autorizado
        if registrar_bloqueio:
            await registrar_auditoria(
                actor_id_afetado=actor_id,
                tenant_id=tenant_id,
                campo_alterado="whitelist_check",
                valor_anterior=None,
                valor_novo="bloqueado_por_whitelist",
                executor_id="sistema",
                motivo=f"Mensagem fora de whitelist: '{mensagem[:50]}...'"
            )
            detalhes_bloqueio["registrado"] = True

        return False, detalhes_bloqueio


def obter_whitelist_info() -> Dict[str, Dict]:
    """Retorna informações completas da Whitelist Classe A."""
    return WHITELIST_PATTERNS
