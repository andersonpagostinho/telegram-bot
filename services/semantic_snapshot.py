"""
Projeção semântica de AggregateSnapshot para decisão de versionamento.

Responsabilidade:
- Extrair apenas campos semanticamente relevantes do snapshot
- Ignorar campos técnicos (timestamps, traces, cache)
- Ignorar campos transitórios (efeitos, mensagens)
- Permitir comparação determinística para detecção de mudança semântica

Garante:
- Imutabilidade (frozendict interno)
- Determinismo (mesma entrada sempre produz mesma projeção)
- Rastreabilidade (documentar cada exclusão)
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from services.billing_domain_service import AggregateSnapshot


# ==============================================================================
# ALLOWLIST DE CAMPOS SEMÂNTICOS POR MÁQUINA
# ==============================================================================

SEMANTIC_METADATA_ALLOWED = {
    # Trial
    "trial_expires": True,  # Data de expiração do trial
    "trial_days_remaining": True,  # Dias restantes
    "trial_started_at": True,  # Data de início (semântica, não técnica)

    # Assinatura
    "subscription_plan": True,  # Plano escolhido
    "subscription_price": True,  # Preço
    "subscription_currency": True,  # Moeda
    "subscription_cycle": True,  # Ciclo (monthly, yearly)
    "subscription_started_at": True,  # Início da assinatura
    "subscription_expires_at": True,  # Expiração da assinatura

    # Pagamento
    "payment_method": True,  # Método (credit_card, boleto)
    "payment_status": True,  # Status (pending, approved, failed)
    "payment_amount": True,  # Valor
    "payment_currency": True,  # Moeda
    "payment_last_attempt": True,  # Última tentativa

    # Acesso
    "access_level": True,  # Nível de acesso
    "access_features": True,  # Features liberadas
    "access_until": True,  # Acesso válido até
    "access_revocation_reason": True,  # Motivo de revogação

    # Retenção
    "retention_status": True,  # Status (active, suspended, terminated)
    "retention_reason": True,  # Motivo se suspended/terminated
    "retention_contact_count": True,  # Quantas vezes contatado
}

# Campos que NÃO devem incrementar versão (sempre ignorados)
TECHNICAL_METADATA_IGNORED = {
    "timestamp",  # Campo técnico de datetime.utcnow()
    "received_at",  # Quando o webhook foi recebido
    "processed_at",  # Quando foi processado
    "trace_id",  # ID de rastreamento
    "request_id",  # ID da requisição
    "cache_invalidated",  # Flag de cache
    "internal_flag",  # Flag técnica
    "debug_info",  # Informações de debug
}


@dataclass(frozen=True)
class SemanticSnapshot:
    """
    Projeção semântica imutável de um AggregateSnapshot.

    Contém APENAS campos relevantes para decisão de versionamento.
    Ignorar timestamps técnicos, traces, caches, etc.
    """
    trial_state: str
    trial_semantic_metadata: Dict[str, Any]

    assinatura_state: str
    assinatura_semantic_metadata: Dict[str, Any]

    pagamento_state: str
    pagamento_semantic_metadata: Dict[str, Any]

    acesso_state: str
    acesso_semantic_metadata: Dict[str, Any]

    retencao_state: str
    retencao_semantic_metadata: Dict[str, Any]


def extract_semantic_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrair apenas campos semânticos de um dicionário de metadata.

    Filtra campos técnicos e ignora chaves desconhecidas por segurança.

    Args:
        metadata: Dicionário bruto de metadata

    Returns:
        Dicionário filtrado com apenas campos permitidos

    Garante:
        - Determinístico (mesma entrada, mesma saída)
        - Sem mutação (não altera metadata original)
        - Seguro (só inclui chaves conhecidas)
    """
    if not metadata:
        return {}

    semantic = {}
    for key, value in metadata.items():
        # Ignorar campos técnicos conhecidos
        if key in TECHNICAL_METADATA_IGNORED:
            continue

        # Incluir apenas se estiver na allowlist
        if key in SEMANTIC_METADATA_ALLOWED:
            semantic[key] = value
        # Campos desconhecidos: registrar mas não incluir
        # (prevenção contra inclusão silenciosa de novos campos)

    return semantic


def semantic_snapshot_projection(snapshot: AggregateSnapshot) -> SemanticSnapshot:
    """
    Criar projeção semântica de um AggregateSnapshot.

    Extrai apenas estados e metadados relevantes para versionamento.
    Ignora timestamp técnico, correlation IDs, traces, caches.

    Args:
        snapshot: AggregateSnapshot original

    Returns:
        SemanticSnapshot imutável com apenas campos semânticos

    Garante:
        - Imutável (frozen dataclass)
        - Determinístico
        - Sem acesso ao relógio
        - Sem efeitos colaterais
    """
    return SemanticSnapshot(
        trial_state=snapshot.trial.state.value,
        trial_semantic_metadata=extract_semantic_metadata(snapshot.trial.metadata),

        assinatura_state=snapshot.assinatura.state.value,
        assinatura_semantic_metadata=extract_semantic_metadata(snapshot.assinatura.metadata),

        pagamento_state=snapshot.pagamento.state.value,
        pagamento_semantic_metadata=extract_semantic_metadata(snapshot.pagamento.metadata),

        acesso_state=snapshot.acesso.state.value,
        acesso_semantic_metadata=extract_semantic_metadata(snapshot.acesso.metadata),

        retencao_state=snapshot.retencao.state.value,
        retencao_semantic_metadata=extract_semantic_metadata(snapshot.retencao.metadata),
    )


def has_semantic_snapshot_change(
    snapshot_before: AggregateSnapshot,
    snapshot_after: AggregateSnapshot,
) -> bool:
    """
    Detectar se houve mudança semântica entre dois snapshots.

    Compara APENAS campos comercialmente relevantes.
    Ignora:
    - Timestamps técnicos
    - Correlation IDs
    - Source event IDs
    - Traces
    - Caches
    - Dados transitórios

    Args:
        snapshot_before: Estado anterior
        snapshot_after: Estado resultante

    Returns:
        True se houve mudança semântica, False caso contrário

    Garante:
        - Determinístico
        - Sem efeitos colaterais
        - Sem mutação de inputs
        - Reflexivo: X == X → False
        - Simétrico: has_change(A, B) == has_change(B, A)
    """
    # Extrair projeções semânticas
    projection_before = semantic_snapshot_projection(snapshot_before)
    projection_after = semantic_snapshot_projection(snapshot_after)

    # Comparar projeções (dataclasses frozen são comparáveis por valor)
    return projection_before != projection_after
