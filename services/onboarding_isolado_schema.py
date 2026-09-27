#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Schema e Helpers para Onboarding Isolado por Actor

Responsabilidades:
1. Definir schema para novo path: Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo
2. Constructores de document
3. Validadores de schema
4. Conversor de legacy para novo
5. Path builders (referência para C3.15+)

IMPORTANTE: Este arquivo NÃO altera comportamento existente.
Ele apenas define estrutura e helpers para o novo modelo.
"""

from datetime import datetime
import pytz
from typing import Tuple, Dict, Any, Optional


# ==============================================================================
# SCHEMA CONSTANTS
# ==============================================================================

ETAPAS_ONBOARDING = [
    "nome_negocio",
    "segmento",
    "endereco",
    "agenda_padrao",
    "primeiro_profissional",
    "canal_primeiro_profissional",
    "primeiro_servico",
    "duracao_primeiro_servico",
    "confirmacao_dados",
    "teste_agendamento",
    "completo"
]

STATUS_ONBOARDING = ["em_progresso", "completo", "parado"]


# ==============================================================================
# CONSTRUCTORES
# ==============================================================================

def criar_documento_onboarding_isolado(
    tenant_id: str,
    actor_id: str,
    dono_nome: str,
    dono_email: str,
    etapa_inicial: str = "nome_negocio"
) -> Dict[str, Any]:
    """
    Cria novo documento para path Donos/{actor_id}/onboarding/ativo

    Retorna dicionário pronto para .set() no Firestore.

    Args:
        tenant_id: ID do tenant
        actor_id: ID do ator (normalizado)
        dono_nome: Nome do dono
        dono_email: Email do dono
        etapa_inicial: Etapa inicial (default: "nome_negocio")

    Returns:
        dict com schema completo
    """

    now = datetime.now(pytz.UTC).isoformat()

    return {
        # === IDENTIDADE ===
        "tenant_id": tenant_id,
        "actor_id": actor_id,

        # === ESTADO DE ONBOARDING ===
        "onboarding_status": "em_progresso",
        "onboarding_etapa_atual": etapa_inicial,
        "onboarding_indice": 0,

        # === RASTREABILIDADE ===
        "criado_em": now,
        "criado_por": actor_id,
        "atualizado_em": now,

        # === INFORMAÇÕES DO ATOR ===
        "dono_nome": dono_nome,
        "dono_email": dono_email,

        # === CAMPOS DE COLETA (preenchidos durante onboarding) ===
        "nome_negocio": None,
        "segmento": None,
        "endereco": None,
        "agenda_padrao": None,
        "primeiro_profissional": None,
        "canal_primeiro_profissional": None,
        "primeiro_servico": None,
        "duracao_primeiro_servico": None,

        # === IDEMPOTÊNCIA (C3.15+) ===
        "idempotencia_key": None,

        # === RETRY/TRACKING ===
        "ultima_tentativa": now,
        "tentativas": 0
    }


# ==============================================================================
# VALIDADORES
# ==============================================================================

def validar_documento_onboarding_isolado(
    doc: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Valida documento contra schema.

    Args:
        doc: Documento a validar

    Returns:
        Tuple (valido: bool, motivo: str)
    """

    # === CAMPOS OBRIGATÓRIOS ===
    campos_obrigatorios = [
        "tenant_id",
        "actor_id",
        "onboarding_status",
        "onboarding_etapa_atual",
        "onboarding_indice",
        "criado_em",
        "criado_por",
        "atualizado_em"
    ]

    for campo in campos_obrigatorios:
        if campo not in doc:
            return False, f"Campo obrigatório faltando: {campo}"

    # === VALIDAR TENANT_ID ===
    if not isinstance(doc.get("tenant_id"), str) or not doc["tenant_id"]:
        return False, "tenant_id deve ser string não-vazia"

    # === VALIDAR ACTOR_ID ===
    if not isinstance(doc.get("actor_id"), str) or not doc["actor_id"]:
        return False, "actor_id deve ser string não-vazia"

    # === VALIDAR STATUS ===
    if doc.get("onboarding_status") not in STATUS_ONBOARDING:
        return False, f"onboarding_status inválido: {doc.get('onboarding_status')}"

    # === VALIDAR ETAPA ===
    if doc.get("onboarding_etapa_atual") not in ETAPAS_ONBOARDING + ["completo"]:
        return False, f"onboarding_etapa_atual inválida: {doc.get('onboarding_etapa_atual')}"

    # === VALIDAR ÍNDICE ===
    if not isinstance(doc.get("onboarding_indice"), int):
        return False, "onboarding_indice deve ser inteiro"

    if not (0 <= doc["onboarding_indice"] <= len(ETAPAS_ONBOARDING)):
        return False, f"onboarding_indice fora do intervalo: {doc['onboarding_indice']}"

    # === VALIDAR TIMESTAMPS ===
    try:
        criado_em = doc.get("criado_em")
        if isinstance(criado_em, str):
            datetime.fromisoformat(criado_em.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False, "criado_em não é timestamp ISO 8601 válido"

    try:
        atualizado_em = doc.get("atualizado_em")
        if isinstance(atualizado_em, str):
            datetime.fromisoformat(atualizado_em.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False, "atualizado_em não é timestamp ISO 8601 válido"

    # === VALIDAR COERÊNCIA ===
    if doc.get("criado_por") != doc.get("actor_id"):
        return False, "criado_por deve ser igual a actor_id"

    return True, "OK"


def validar_isolamento(
    doc_a: Dict[str, Any],
    doc_b: Dict[str, Any]
) -> bool:
    """
    Verifica que dois documentos não se sobrepõem (isolamento).

    Args:
        doc_a: Primeiro documento
        doc_b: Segundo documento

    Returns:
        True se isolados, False se relacionados
    """

    # Mesmos tenant e actor = mesma entidade (não isolado)
    if doc_a.get("tenant_id") == doc_b.get("tenant_id") and \
       doc_a.get("actor_id") == doc_b.get("actor_id"):
        return False

    # Caso contrário, isolado
    return True


# ==============================================================================
# PATH BUILDERS (para C3.15+)
# ==============================================================================

def obter_ref_onboarding_isolado(
    db,  # Firestore client
    tenant_id: str,
    actor_id: str
):
    """
    Retorna referência do documento novo (isolado).

    Path: Clientes/{tenant_id}/Donos/{actor_id}/onboarding/ativo

    NOTA: Use apenas em C3.15.2+ após aprovação.

    Args:
        db: Firestore client (firebase_admin.firestore)
        tenant_id: ID do tenant
        actor_id: ID do ator

    Returns:
        DocumentReference para o documento de onboarding isolado
    """

    return (
        db.collection("Clientes").document(tenant_id)
        .collection("Donos").document(actor_id)
        .collection("onboarding").document("ativo")
    )


# ==============================================================================
# CONVERSÃO DE LEGACY (para C3.15.6)
# ==============================================================================

def converter_legacy_para_isolado(
    legacy_doc: Dict[str, Any],
    tenant_id: str,
    actor_id: str
) -> Dict[str, Any]:
    """
    Converte documento legacy (Configuracao/negocio) para novo formato isolado.

    Aplicável quando:
    1. Legacy existe em Configuracao/negocio
    2. Legacy.dono_actor_id == actor_id (ownership validado)
    3. Precisa migrar para Donos/{actor_id}/onboarding/ativo

    IMPORTANTE: Use apenas em C3.15.6 após aprovação de migração.

    Args:
        legacy_doc: Documento legacy (Configuracao/negocio)
        tenant_id: ID do tenant
        actor_id: ID do ator (deve ser igual a legacy.dono_actor_id)

    Returns:
        Novo documento no formato isolado

    Raises:
        ValueError: Se legacy não pertence ao ator
    """

    # Validar ownership
    if legacy_doc.get("dono_actor_id") != actor_id:
        raise ValueError(
            f"Legacy não pertence a este ator. "
            f"Legacy.dono_actor_id={legacy_doc.get('dono_actor_id')}, "
            f"actor_id={actor_id}"
        )

    # Criar documento novo com base no legacy
    novo_doc = criar_documento_onboarding_isolado(
        tenant_id=tenant_id,
        actor_id=actor_id,
        dono_nome=legacy_doc.get("dono_nome", ""),
        dono_email=legacy_doc.get("dono_email", ""),
        etapa_inicial=legacy_doc.get("onboarding_etapa_atual", "nome_negocio")
    )

    # Sobrescrever com dados do legacy
    novo_doc.update({
        "onboarding_status": legacy_doc.get("onboarding_status", "em_progresso"),
        "onboarding_indice": legacy_doc.get("onboarding_indice", 0),
        "criado_em": legacy_doc.get("criado_em", novo_doc["criado_em"]),
        "criado_por": legacy_doc.get("criado_por", actor_id),
        "atualizado_em": legacy_doc.get("atualizado_em", novo_doc["atualizado_em"]),

        # Campos de coleta
        "nome_negocio": legacy_doc.get("nome_negocio"),
        "segmento": legacy_doc.get("segmento"),
        "endereco": legacy_doc.get("endereco"),
        "agenda_padrao": legacy_doc.get("agenda_padrao"),
        "primeiro_profissional": legacy_doc.get("primeiro_profissional"),
        "canal_primeiro_profissional": legacy_doc.get("canal_primeiro_profissional"),
        "primeiro_servico": legacy_doc.get("primeiro_servico"),
        "duracao_primeiro_servico": legacy_doc.get("duracao_primeiro_servico"),

        # Marca como migrado
        "migrado_de_legacy": True,
        "migrado_em": datetime.now(pytz.UTC).isoformat()
    })

    return novo_doc
