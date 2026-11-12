"""
Serviço de Duração de Serviços.

Responsabilidade: Encapsular a lookup de profissional + extração de duração,
com tratamento explícito de None (sem fallback silencioso para 60).

Protege isolamento multi-tenant e fornece interface limpa para obter duração de
um serviço específico para um profissional específico.
"""

import re
import unidecode
from services.identidade_service import buscar_profissional_por_nome


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
