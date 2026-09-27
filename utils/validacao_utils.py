"""
Validação centralizada de constantes de domínio.
"""

TIPOS_USUARIO_VALIDOS = {
    "dono",
    "profissional",
    "cliente",
}


def validar_tipo_usuario(valor: str) -> bool:
    """
    Valida se um valor é um tipo_usuario válido.

    Args:
        valor: string a validar

    Returns:
        True se válido, False caso contrário
    """
    if not valor or not isinstance(valor, str):
        return False

    return valor.strip().lower() in TIPOS_USUARIO_VALIDOS


def normalizar_tipo_usuario(valor: str) -> str | None:
    """
    Normaliza um tipo_usuario (lowercase, strip).

    Retorna None se inválido.
    """
    if not valor or not isinstance(valor, str):
        return None

    normalizado = valor.strip().lower()
    return normalizado if normalizado in TIPOS_USUARIO_VALIDOS else None
