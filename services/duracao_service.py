"""
Serviço de Duração de Serviços — BRIDGE MULTI-FONTE.

Responsabilidade: Encapsular a lookup de profissional + extração de duração,
com tratamento explícito de None (sem fallback silencioso para 60).

ARQUITETURA:
- Atores/{actor_id}: Fonte canônica de identidade
- Profissionais/{nome}: Fonte operacional de configurações (duracoes, servicos, precos)
- Bridge: Conecta as duas, valida isolamento multi-tenant

Protege isolamento multi-tenant e fornece interface limpa para obter duração de
um serviço específico para um profissional específico.
"""

import re
import unidecode
from services.identidade_service import buscar_profissional_por_nome
from services.firebase_service_async import buscar_subcolecao


async def obter_duracao_por_profissional_bridge(
    tenant_id: str,
    nome_profissional: str,
    nome_servico: str
) -> int | None:
    """
    Bridge: Conecta Atores (identidade) com Profissionais (operações).

    Fluxo:
    1. Resolve identidade no Atores/{tenant_id}
    2. Localiza configuração em Profissionais/{tenant_id}
    3. Valida associação (mesmo tenant)
    4. Extrai duração validada

    Args:
        tenant_id: ID do tenant (obrigatório)
        nome_profissional: Nome do profissional
        nome_servico: Nome do serviço

    Returns:
        Duração em minutos se encontrada, None caso contrário.
        Sem fallback silencioso.

    Raises:
        ValueError: Se tenant_id vazio ou nome ambíguo.
    """
    if not tenant_id or not nome_profissional or not nome_servico:
        raise ValueError("tenant_id, nome_profissional e nome_servico são obrigatórios")

    # Step 1: Resolver identidade no Atores (validar tenant)
    prof_ator = await buscar_profissional_por_nome(tenant_id, nome_profissional)
    if prof_ator is None:
        return None

    # Step 2: Localizar configuração operacional em Profissionais
    prof_config = await _buscar_profissional_operacional(tenant_id, nome_profissional)
    if prof_config is None:
        return None

    # Step 3: Extrair duração da configuração operacional
    return obter_duracao_servico_validada(prof_config, nome_servico)


async def _buscar_profissional_operacional(tenant_id: str, nome_profissional: str) -> dict | None:
    """
    Busca profissional em Profissionais/{tenant_id} com matching case-insensitive.

    Valida:
    - Mesma tenant
    - Unicidade (não aceita match ambíguo)
    - Normalização (acentos, caixa)

    Returns:
        Dicionário do profissional ou None se não encontrado/ambíguo.
    """
    profissionais = await buscar_subcolecao(f"Clientes/{tenant_id}/Profissionais") or {}

    nome_norm = _normalizar_nome(nome_profissional)
    matches = []

    for chave, prof_data in profissionais.items():
        prof_nome = prof_data.get("nome") or chave
        if _normalizar_nome(prof_nome) == nome_norm:
            matches.append(prof_data)

    # Rejeitar match ambíguo (múltiplas correspondências)
    if len(matches) == 0:
        return None
    if len(matches) > 1:
        # Ambíguo: múltiplos profissionais com mesmo nome normalizado
        return None

    return matches[0]


def obter_duracao_servico_validada(prof_data: dict, nome_servico: str) -> int | None:
    """
    Obtém duração VALIDADA de um serviço a partir de dados do profissional.

    Esta é a função de validação mínima, pura, sem I/O.
    Use quando prof_data já está disponível (not None).

    Args:
        prof_data: Dicionário do profissional
        nome_servico: Nome do serviço

    Returns:
        Duração em minutos se encontrada, None caso contrário.
        Sem fallback silencioso.
    """
    return _extrair_duracao_do_profissional(prof_data, nome_servico)


async def obter_duracao_por_profissional_nome(
    tenant_id: str,
    nome_profissional: str,
    nome_servico: str
) -> int | None:
    """
    Obtém a duração (em minutos) de um serviço oferecido por um profissional.

    Args:
        tenant_id: ID do tenant (dono)
        nome_profissional: Nome do profissional
        nome_servico: Nome do serviço

    Returns:
        Duração em minutos se encontrada, None caso contrário.
        IMPORTANTE: Não há fallback silencioso para 60.
        Se duração não estiver explicitamente configurada, retorna None.

    Raises:
        ValueError: Se tenant_id, nome_profissional ou nome_servico forem vazios.
    """
    if not tenant_id or not nome_profissional or not nome_servico:
        raise ValueError("tenant_id, nome_profissional e nome_servico são obrigatórios")

    # Step 1: Buscar o profissional
    prof_data = await buscar_profissional_por_nome(tenant_id, nome_profissional)

    if prof_data is None:
        return None

    # Step 2: Extrair duração do profissional
    return _extrair_duracao_do_profissional(prof_data, nome_servico)


def _extrair_duracao_do_profissional(prof_data: dict, nome_servico: str) -> int | None:
    """
    Helper puro que extrai duração de um dicionário de profissional.

    Tenta múltiplas chaves de duração e faz matching case-insensitive.

    Args:
        prof_data: Dicionário do profissional (resultado de buscar_profissional_por_nome)
        nome_servico: Nome do serviço a buscar

    Returns:
        Duração em minutos ou None se não encontrada.
    """
    if not prof_data or not isinstance(prof_data, dict):
        return None

    servico_norm = _normalizar_nome(nome_servico)

    # Tenta múltiplas chaves onde duração pode estar armazenada
    for chave_duracao in ("duracoes", "duracao_servicos", "duracao_por_servico"):
        duracao_map = prof_data.get(chave_duracao)

        if isinstance(duracao_map, dict):
            for chave_servico, duracao in duracao_map.items():
                if _normalizar_nome(chave_servico) == servico_norm:
                    try:
                        return int(duracao)
                    except (ValueError, TypeError):
                        continue

    # Se não encontrou em nenhum lugar, retorna None (não há fallback para 60)
    return None


def _normalizar_nome(nome: str) -> str:
    """
    Normaliza nome para comparação: lowercase, remove acentos e caracteres especiais.
    """
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(nome).lower())
    ).strip()


# ============================================================================
# PUBLIC WRAPPER: Validação com Duração (para PRE-CHECK e CONFIRMAÇÃO)
# ============================================================================

async def validar_profissional_com_duracao(
    tenant_id: str,
    nome_profissional: str,
    nome_servico: str
) -> dict:
    """
    Valida se profissional pode fazer o serviço E retorna duração.

    Interface para USO 1 (PRE-CHECK) e USO 4 (CONFIRMAÇÃO).

    Returns:
        {
            "valido": bool,
            "duracao": int | None,
            "motivo": str | None
        }

    Motivos possíveis:
    - "profissional_inexistente"
    - "duracao_nao_configurada"
    - "valido"
    """
    if not tenant_id or not nome_profissional or not nome_servico:
        raise ValueError("tenant_id, nome_profissional e nome_servico são obrigatórios")

    # Step 1: Buscar profissional
    duracao = await obter_duracao_por_profissional_bridge(
        tenant_id, nome_profissional, nome_servico
    )

    if duracao is None:
        # Try to distinguish: not found vs duration not configured
        prof_ator = await buscar_profissional_por_nome(tenant_id, nome_profissional)

        if prof_ator is None:
            return {
                "valido": False,
                "duracao": None,
                "motivo": "profissional_inexistente"
            }
        else:
            return {
                "valido": False,
                "duracao": None,
                "motivo": "duracao_nao_configurada"
            }

    return {
        "valido": True,
        "duracao": duracao,
        "motivo": None
    }
