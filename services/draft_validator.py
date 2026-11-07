"""
Validação de Draft — Ciclo de Vida
Determina se um draft está válido para retomar fluxo conversacional.
"""

from datetime import datetime, timezone
import dateutil.parser


def eh_draft_valido_para_retomar(draft: dict, estado_fluxo: str) -> bool:
    """
    Valida se draft está em estado válido para retomar/usar em fluxo conversacional.

    Respeitaciclo de vida real: um draft é válido APENAS se:
    1. Existe e não é None/vazio
    2. Tem 2+ campos de {profissional, data_hora, servico} preenchidos
    3. data_hora (se presente) é válida e NÃO expirou
    4. estado_fluxo está em ESTADO OPERACIONAL (não "idle")

    Args:
        draft: dict com {profissional, data_hora, servico} ou None
        estado_fluxo: string com estado atual ("idle", "aguardando_servico", etc)

    Returns:
        True se draft é válido para retomar, False caso contrário
    """

    # Validação 1: Draft deve existir
    if not draft or not isinstance(draft, dict):
        return False

    # Validação 2: Estado_fluxo deve estar ATIVO (não "idle")
    # Draft em "idle" é sempre residual, nunca retomável
    if not estado_fluxo or estado_fluxo.strip().lower() == "idle":
        return False

    # Validação 3: Contar campos preenchidos
    campos_preenchidos = sum([
        bool(draft.get("profissional")),
        bool(draft.get("data_hora")),
        bool(draft.get("servico"))
    ])

    if campos_preenchidos < 2:
        return False  # Precisa de pelo menos 2 campos

    # Validação 4: Se data_hora está presente, deve ser válida e não expirada
    if draft.get("data_hora"):
        try:
            data_draft = dateutil.parser.isoparse(draft["data_hora"])
            agora = datetime.now(timezone.utc)

            # Data já passou? (expirada)
            if data_draft <= agora:
                return False

        except (ValueError, TypeError):
            # data_hora inválida (não é ISO válido)
            return False

    # Passou em todas as validações
    return True
