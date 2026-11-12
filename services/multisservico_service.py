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
    - "das 14 as 17" (sem acento)

    Returns:
        (hora_inicio, hora_fim) ou (None, None) se não encontrado

    Exemplo:
        >>> extrair_intervalo_horario("manicure das 14 às 17")
        (14, 17)
    """
    import re

    msg = mensagem.lower()

    # PADRÃO 1: "das 14 às 17" ou "de 14 a 17" (continuado)
    match = re.search(
        r"(?:das?|de)?\s*(\d{1,2})(?::00|h)?\s*(?:as?|às?)\s*(\d{1,2})(?::00|h)?",
        msg,
        re.IGNORECASE
    )
    if match:
        return int(match.group(1)), int(match.group(2))

    # PADRÃO 2: "a partir de" + "até" (separado)
    inicio = None
    fim = None

    match_inicio = re.search(r"a partir d(?:e|as?)\s*(\d{1,2})(?::00|h)?", msg)
    if match_inicio:
        inicio = int(match_inicio.group(1))

    match_fim = re.search(r"(?:até|ate)\s+[^0-9]*?(\d{1,2})(?::00|h)?", msg)
    if match_fim:
        fim = int(match_fim.group(1))

    if inicio is not None or fim is not None:
        return inicio, fim

    return None, None


def extrair_data_da_mensagem(mensagem: str) -> str | None:
    """
    Extrai data da mensagem em formato ISO (YYYY-MM-DD).

    Padrões suportados:
    - "amanhã" → próximo dia
    - "hoje" → dia atual
    - "segunda", "terça", ..., "domingo" → próximo dia com esse nome
    - "próxima segunda" → semana que vem
    - "dia 15" → dia 15 do mês atual ou próximo

    Returns:
        String no formato "YYYY-MM-DD" ou None se não encontrado

    Exemplo:
        >>> # Assumindo hoje = 2026-11-12 (quinta)
        >>> extrair_data_da_mensagem("manicure amanhã")
        "2026-11-13"
        >>> extrair_data_da_mensagem("manicure segunda")
        "2026-11-16"  # Próxima segunda
    """
    import re
    from datetime import datetime, timedelta

    msg = (mensagem or "").lower().strip()
    hoje = datetime.now().date()

    # 1. DATA NUMÉRICA EXPLÍCITA (PRECEDÊNCIA MÁXIMA)
    # Padrão: "13/11/2026" ou "13/11"
    match_data_completa = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", msg)
    if match_data_completa:
        dia = int(match_data_completa.group(1))
        mes = int(match_data_completa.group(2))
        ano = int(match_data_completa.group(3)) if match_data_completa.group(3) else hoje.year

        try:
            data = datetime(ano, mes, dia).date()
            if data >= hoje:
                return data.isoformat()
        except ValueError:
            pass

    # 2. "amanhã"
    if "amanhã" in msg or "amanha" in msg:
        data = hoje + timedelta(days=1)
        return data.isoformat()

    # 2. "hoje"
    if "hoje" in msg:
        return hoje.isoformat()

    # 3. Nomes de dias da semana (segunda=0, ..., domingo=6)
    # Mapa: português → número do dia (0=seg, 6=dom)
    dias_semana = {
        "segunda": 0, "segunda-feira": 0,
        "terça": 1, "terça-feira": 1,
        "quarta": 2, "quarta-feira": 2,
        "quinta": 3, "quinta-feira": 3,
        "sexta": 4, "sexta-feira": 4,
        "sábado": 5, "sabado": 5,
        "domingo": 6
    }

    # Detectar "próxima segunda" ou apenas "segunda"
    eh_proxima = "próxima" in msg or "proxima" in msg or "semana que vem" in msg

    for dia_nome, dia_num in dias_semana.items():
        if dia_nome in msg:
            # Calcular próxima ocorrência deste dia
            dias_para_proximo = (dia_num - hoje.weekday()) % 7

            # Se hoje É este dia e não houver "próxima", voltar 7 dias (próxima semana)
            if dias_para_proximo == 0 and not eh_proxima:
                dias_para_proximo = 7
            elif dias_para_proximo == 0 and eh_proxima:
                dias_para_proximo = 7
            elif eh_proxima:
                # "próxima segunda" = adiciona 7 dias
                dias_para_proximo += 7

            # Garantir que não volta para passado
            if dias_para_proximo <= 0:
                dias_para_proximo += 7

            data = hoje + timedelta(days=dias_para_proximo)
            return data.isoformat()

    # 4. "dia 15" (dia específico do mês)
    match_dia = re.search(r"dia\s+(\d{1,2})", msg)
    if match_dia:
        dia_alvo = int(match_dia.group(1))

        # Tentar mês atual
        try:
            data = datetime(hoje.year, hoje.month, dia_alvo).date()
            # Se data é no passado, tentar próximo mês
            if data < hoje:
                proximo_mes = hoje.month + 1
                proximo_ano = hoje.year
                if proximo_mes > 12:
                    proximo_mes = 1
                    proximo_ano += 1
                data = datetime(proximo_ano, proximo_mes, dia_alvo).date()
            return data.isoformat()
        except ValueError:
            # Dia inválido para o mês (ex: dia 31 em fevereiro)
            pass

    return None


def enriquecer_contexto_consulta(
    contexto_consulta: dict,
    mensagem: str
) -> dict:
    """
    Enriquecer contexto_consulta com campos adicionais:
    - intervalo_inicio, intervalo_fim (janela temporal)
    - data_hora (data solicitada em YYYY-MM-DD)

    Args:
        contexto_consulta: Dicionário base de contexto
        mensagem: Mensagem original do usuário

    Returns:
        contexto_consulta enriquecido
    """
    # Extrair intervalo horário
    hora_inicio, hora_fim = extrair_intervalo_horario(mensagem)
    if hora_inicio is not None:
        contexto_consulta["intervalo_inicio"] = hora_inicio
        contexto_consulta["intervalo_fim"] = hora_fim

    # Extrair data (se houver)
    data_extraida = extrair_data_da_mensagem(mensagem)
    if data_extraida:
        contexto_consulta["data_hora"] = data_extraida
        print(f"[P1-FIX] Data extraída: {data_extraida}", flush=True)

    return contexto_consulta
