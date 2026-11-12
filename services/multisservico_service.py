"""
Serviço Multisserviço — BLOCO SEQUENCIAL DE SERVIÇOS.

Responsabilidade: Resolver, validar e processar blocos de múltiplos serviços
como unidade atômica, preservando sequência, duração total, e restrições
temporais.

Arquitetura:
- Entrada: tenant_id, profissional, [servicos], intervalo_temporal (opcional)
- Processamento: Validação + Resolução de durações + Cálculo de total
- Saída: Estrutura com validação, durações individuais, total, mensagens
"""

from services.duracao_service import obter_duracao_por_profissional_bridge


async def resolver_bloco_servicos(
    tenant_id: str,
    nome_profissional: str,
    servicos: list[str]
) -> dict:
    """
    Resolve duração para bloco completo de serviços sequenciais.

    Args:
        tenant_id: ID do tenant
        nome_profissional: Nome do profissional
        servicos: Lista de serviços em sequência

    Returns:
        {
            "valido": bool,
            "servicos": list[str],
            "duracoes_individuais": list[int],
            "duracao_total": int,
            "mensagens": list[str],
        }

    Exemplo:
        >>> resultado = await resolver_bloco_servicos(
        ...     "tenant1", "Bruna", ["manicure", "pedicure"]
        ... )
        >>> resultado["duracao_total"]
        65

    Validações:
    1. Cada serviço deve estar no catálogo do profissional
    2. Cada serviço deve ter duração configurada (sem fallback)
    3. Durações são somadas sequencialmente
    """

    if not servicos:
        return {
            "valido": False,
            "servicos": [],
            "duracoes_individuais": [],
            "duracao_total": 0,
            "mensagens": ["Lista de serviços vazia"],
        }

    duracoes_individuais = []
    mensagens = []

    # Resolver cada serviço
    for servico in servicos:
        duracao = await obter_duracao_por_profissional_bridge(
            tenant_id=tenant_id,
            nome_profissional=nome_profissional,
            nome_servico=servico
        )

        if duracao is None:
            mensagens.append(
                f"Serviço '{servico}' não disponível ou sem duração configurada"
            )
            return {
                "valido": False,
                "servicos": servicos,
                "duracoes_individuais": duracoes_individuais,
                "duracao_total": 0,
                "mensagens": mensagens,
            }

        duracoes_individuais.append(duracao)

    duracao_total = sum(duracoes_individuais)

    return {
        "valido": True,
        "servicos": servicos,
        "duracoes_individuais": duracoes_individuais,
        "duracao_total": duracao_total,
        "mensagens": [],
    }


def validar_horario_em_janela(
    hora_inicio_bloqueio: int | float,
    duracao_min: int,
    janela_minima: int | None,
    janela_maxima: int | None
) -> bool:
    """
    Valida se horário de início + duração cabem na janela temporal.

    Args:
        hora_inicio_bloqueio: Hora de início do bloqueio (0-23)
        duracao_min: Duração em minutos
        janela_minima: Hora mínima da janela (0-23), None = sem restrição
        janela_maxima: Hora máxima da janela (0-23), None = sem restrição

    Returns:
        True se o bloqueio cabe na janela, False caso contrário

    Exemplo:
        >>> validar_horario_em_janela(14, 65, 14, 17)
        True
        # 14h + 65min = 15:05, que é <= 17h

        >>> validar_horario_em_janela(14, 200, 14, 17)
        False
        # 14h + 200min = 17:20, que ultrapassa 17h
    """

    # Se sem restrição de janela, aceita
    if janela_minima is None and janela_maxima is None:
        return True

    if janela_minima is None:
        janela_minima = 0
    if janela_maxima is None:
        janela_maxima = 24

    # Validar que hora_inicio está dentro da janela
    if hora_inicio_bloqueio < janela_minima:
        return False

    # Calcular hora de fim (converter minutos em horas)
    hora_fim_bloqueio = hora_inicio_bloqueio + (duracao_min / 60)

    # Validar que hora_fim não ultrapassa janela máxima
    return hora_fim_bloqueio <= janela_maxima


def extrair_intervalo_horario(mensagem: str) -> tuple[int | None, int | None]:
    """
    Extrai horário mínimo e máximo de mensagem.

    Padrões suportados:
    - "das 14 às 17"
    - "de 14:00 a 17:00"
    - "14h às 17h"

    Returns:
        (hora_inicio, hora_fim) ou (None, None) se não encontrado

    Exemplo:
        >>> extrair_intervalo_horario("manicure das 14 às 17")
        (14, 17)
    """
    import re

    match = re.search(
        r"(?:das?|de)?\s*(\d{1,2})(?::00|h)?\s*(?:às?|a)\s*(\d{1,2})(?::00|h)?",
        mensagem,
        re.IGNORECASE
    )

    if match:
        return int(match.group(1)), int(match.group(2))

    return None, None


def enriquecer_contexto_consulta(
    contexto_consulta: dict,
    mensagem: str
) -> dict:
    """
    Enriquecer contexto_consulta com campos adicionais:
    - intervalo_inicio, intervalo_fim (janela temporal)

    Args:
        contexto_consulta: Dicionário base de contexto
        mensagem: Mensagem original do usuário

    Returns:
        contexto_consulta enriquecido
    """
    # Extrair intervalo
    hora_inicio, hora_fim = extrair_intervalo_horario(mensagem)
    if hora_inicio is not None:
        contexto_consulta["intervalo_inicio"] = hora_inicio
        contexto_consulta["intervalo_fim"] = hora_fim

    return contexto_consulta
