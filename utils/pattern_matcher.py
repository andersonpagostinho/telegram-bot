"""
Pattern matcher para detecção de operações conversacionais.

Centraliza regex e lógica de detecção de padrões para:
- Cancelamento
- Confirmação (sim/não)
- Comandos administrativos
- Ajustes incrementais
- Profissionais
- Horários

Usado por verificar_com_whitelist() para detectar
se uma mensagem deve ser protegida por whitelist.

NOTA: Em Sprint 1, estas funções são criadas mas não são chamadas.
A integração no router acontece em Sprint 2+.
"""

import re
from typing import Optional, List


# Padrões de Cancelamento
PATTERNS_CANCELAMENTO = [
    r"cancelar",
    r"desmarcar",
    r"desfazer",
    r"eliminar.*horário",
    r"deletar.*agendamento",
    r"tirar.*agenda",
    r"remover.*compromisso",
    r"não vou mais",
    r"cancela",
    r"desfaz",
]

# Padrões de Confirmação Positiva
PATTERNS_CONFIRMACAO_POSITIVA = [
    r"\bsim\b",
    r"\bs\b",
    r"\byes\b",
    r"\bopa\b",
    r"\bclaro\b",
    r"\btá certo\b",
    r"\btá bom\b",
    r"\bconfirma\b",
    r"\bconfirmado\b",
    r"\bagreed\b",
    r"\bde acordo\b",
    r"\bucet\b",  # Português informal
    r"\bfaz\b",
]

# Padrões de Confirmação Negativa
PATTERNS_CONFIRMACAO_NEGATIVA = [
    r"\bnão\b",
    r"\bn\b",
    r"\bno\b",
    r"\bnope\b",
    r"\bnao\b",  # Sem acento
    r"\bnenhum\b",
    r"\blado nenhum\b",
    r"\bdecline\b",
    r"\bnega\b",
    r"\brecusa\b",
    r"\bnem sempre\b",
]

# Padrões de Comando Administrativo
PATTERNS_COMANDO = [
    r"^/pausar",
    r"^/retomar",
    r"^/status",
    r"^/silencioso",
    r"^/admin",
    r"^/normal",
]


def eh_cancelamento(msg: str) -> bool:
    """
    Verifica se mensagem é cancelamento de agendamento.

    Args:
        msg: Mensagem do usuário

    Returns:
        True se detecta padrão de cancelamento

    Exemplo:
        eh_cancelamento("Cancelar meu horário")  # True
        eh_cancelamento("Agende corte")  # False
    """
    if not msg or not isinstance(msg, str):
        return False

    msg_lower = msg.lower().strip()

    for pattern in PATTERNS_CANCELAMENTO:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return True

    return False


def eh_confirmacao_positiva(msg: str) -> bool:
    """
    Verifica se mensagem é confirmação positiva (sim/yes/ok).

    Args:
        msg: Mensagem do usuário

    Returns:
        True se detecta padrão de confirmação positiva

    Exemplo:
        eh_confirmacao_positiva("sim")  # True
        eh_confirmacao_positiva("Yes, please")  # True
        eh_confirmacao_positiva("não")  # False
    """
    if not msg or not isinstance(msg, str):
        return False

    msg_lower = msg.lower().strip()

    for pattern in PATTERNS_CONFIRMACAO_POSITIVA:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return True

    return False


def eh_confirmacao_negativa(msg: str) -> bool:
    """
    Verifica se mensagem é confirmação negativa (não/no/nope).

    Args:
        msg: Mensagem do usuário

    Returns:
        True se detecta padrão de confirmação negativa

    Exemplo:
        eh_confirmacao_negativa("não")  # True
        eh_confirmacao_negativa("nope")  # True
        eh_confirmacao_negativa("sim")  # False
    """
    if not msg or not isinstance(msg, str):
        return False

    msg_lower = msg.lower().strip()

    for pattern in PATTERNS_CONFIRMACAO_NEGATIVA:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return True

    return False


def eh_comando(msg: str) -> bool:
    """
    Verifica se mensagem é comando administrativo.

    Comandos válidos:
    - /pausar: Pausar respostas automáticas
    - /retomar: Retomar respostas automáticas
    - /status: Ver status de governança
    - /silencioso: Ativar modo silencioso (dono)
    - /admin: Ativar modo admin (dono)
    - /normal: Desativar modo especial (dono)

    Args:
        msg: Mensagem do usuário

    Returns:
        True se detecta padrão de comando

    Exemplo:
        eh_comando("/pausar")  # True
        eh_comando("pausar meu bot")  # False
        eh_comando("/status")  # True
    """
    if not msg or not isinstance(msg, str):
        return False

    msg_stripped = msg.strip()

    for pattern in PATTERNS_COMANDO:
        if re.match(pattern, msg_stripped, re.IGNORECASE):
            return True

    return False


def extrair_comando(msg: str) -> Optional[str]:
    """
    Extrai nome do comando de uma mensagem.

    Args:
        msg: Mensagem do usuário

    Returns:
        Nome do comando (sem /) ou None

    Exemplo:
        extrair_comando("/pausar por favor")  # "pausar"
        extrair_comando("/retomar")  # "retomar"
        extrair_comando("oi")  # None
    """
    if not eh_comando(msg):
        return None

    # Extrair primeiro token que começa com /
    tokens = msg.strip().split()
    if tokens and tokens[0].startswith("/"):
        return tokens[0][1:].lower()  # Remove /

    return None


def eh_ajuste_em_fluxo(msg: str, contexto: dict) -> bool:
    """
    Verifica se mensagem é ajuste dentro de fluxo ativo.

    Ajustes são mensagens que modificam uma proposta já existente,
    diferente de iniciar novo agendamento.

    Exemplos de ajuste:
    - "Mas prefiro 16h" (fluxo ativo, propõe 15h)
    - "Com a Bruna ao invés" (fluxo ativo, propõe Maria)
    - "Próxima semana melhor" (em fluxo de agenda)

    Args:
        msg: Mensagem do usuário
        contexto: Contexto de sessão (contém estado_fluxo, proposta, etc)

    Returns:
        True se parece ser ajuste (heurística)

    Exemplo:
        contexto = {"estado_fluxo": "agendando", "proposta": {...}}
        eh_ajuste_em_fluxo("Mas 16h", contexto)  # True

        contexto = {"estado_fluxo": "vazio"}
        eh_ajuste_em_fluxo("Agende corte", contexto)  # False
    """
    if not msg or not isinstance(msg, str):
        return False

    # Se fora de fluxo ativo, não é ajuste
    estado_fluxo = contexto.get("estado_fluxo", "vazio")
    if estado_fluxo == "vazio":
        return False

    # Se em fluxo ativo, verificar marcadores de ajuste
    msg_lower = msg.lower().strip()

    ajuste_patterns = [
        r"mas ",
        r"mas prefiro",
        r"melhor",
        r"ao invés",
        r"em vez de",
        r"trocar",
        r"mudar",
        r"alterar",
        r"deixar",
        r"deixa",
        r"só que",
        r"porém",
        r"contudo",
    ]

    for pattern in ajuste_patterns:
        if re.search(pattern, msg_lower):
            return True

    return False


def eh_resposta_para_opcoes(msg: str, contexto: dict) -> bool:
    """
    Verifica se mensagem é resposta a múltiplas opções.

    Contexto contém:
    - estado_fluxo = "oferecendo_opcoes" ou "escolhendo_profissional"
    - opcoes_horario ou profissionais

    Args:
        msg: Mensagem do usuário
        contexto: Contexto de sessão

    Returns:
        True se parece ser resposta a opções oferecidas

    Exemplo:
        contexto = {
            "estado_fluxo": "oferecendo_opcoes",
            "opcoes_horario": ["15h", "16h", "17h"]
        }
        eh_resposta_para_opcoes("16h", contexto)  # True
    """
    if not msg or not isinstance(msg, str):
        return False

    estado_fluxo = contexto.get("estado_fluxo", "vazio")

    # Oferecendo opções de horário
    if estado_fluxo == "oferecendo_opcoes":
        opcoes = contexto.get("opcoes_horario", [])
        for opcao in opcoes:
            if str(opcao).lower() in msg.lower():
                return True

    # Escolhendo profissional
    if estado_fluxo == "escolhendo_profissional":
        profissionais = contexto.get("profissionais", [])
        for prof in profissionais:
            if isinstance(prof, dict):
                nome = prof.get("nome", "")
                if nome.lower() in msg.lower():
                    return True
            else:
                if str(prof).lower() in msg.lower():
                    return True

    return False


def normalizar_confirmacao(msg: str) -> Optional[str]:
    """
    Normaliza resposta de confirmação para 'sim' ou 'não'.

    Args:
        msg: Mensagem do usuário

    Returns:
        'sim', 'não', ou None se ambíguo

    Exemplo:
        normalizar_confirmacao("sim")  # "sim"
        normalizar_confirmacao("yes")  # "sim"
        normalizar_confirmacao("no")  # "não"
        normalizar_confirmacao("não sei")  # None
    """
    if eh_confirmacao_positiva(msg):
        return "sim"
    elif eh_confirmacao_negativa(msg):
        return "não"
    else:
        return None
