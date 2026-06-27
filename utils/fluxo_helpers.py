"""
Helpers para gerenciar estado de fluxo conversacional.

Centraliza lógica de:
- Obtenção de estado_fluxo
- Atualização de estado_fluxo
- Verificação de fluxo ativo
- Verificação de whitelists

NOTA: Em Sprint 1, estas funções são criadas mas não são chamadas.
A integração no router acontece em Sprint 2+.
"""

from typing import Dict, Any, Optional


def obter_estado_fluxo(sessao: Dict[str, Any]) -> str:
    """
    Obtém estado_fluxo de uma sessão de forma segura.

    Args:
        sessao: Documento de sessão do Firestore

    Returns:
        Estado do fluxo ou "vazio" se não definido

    Estados possíveis:
    - "vazio": Sem fluxo ativo
    - "agendando": Agendando novo
    - "aguardando_confirmacao": Aguardando sim/não
    - "cancelando": Cancelando agendamento
    - "oferecendo_opcoes": Oferecendo alternativas
    - "escolhendo_profissional": Escolhendo profissional
    - "escolhendo_horario": Escolhendo horário
    - [outros]: Fluxos customizados

    Exemplo:
        sessao = {"estado_fluxo": "agendando"}
        obter_estado_fluxo(sessao)  # "agendando"

        sessao = {}
        obter_estado_fluxo(sessao)  # "vazio"
    """
    if not sessao or not isinstance(sessao, dict):
        return "vazio"

    return sessao.get("estado_fluxo", "vazio")


def em_fluxo_ativo(sessao: Dict[str, Any]) -> bool:
    """
    Verifica se há fluxo conversacional ativo.

    Um fluxo ativo significa que o sistema está processando
    uma sequência de mensagens (agendando, confirmando, etc),
    e ajustes incrementais devem ser processados.

    Args:
        sessao: Documento de sessão do Firestore

    Returns:
        True se estado_fluxo != "vazio"

    Exemplo:
        sessao = {"estado_fluxo": "agendando"}
        em_fluxo_ativo(sessao)  # True

        sessao = {"estado_fluxo": "vazio"}
        em_fluxo_ativo(sessao)  # False
    """
    estado = obter_estado_fluxo(sessao)
    return estado != "vazio"


def aguardando_confirmacao(sessao: Dict[str, Any]) -> bool:
    """
    Verifica se está aguardando confirmação (sim/não).

    Args:
        sessao: Documento de sessão do Firestore

    Returns:
        True se estado_fluxo == "aguardando_confirmacao"

    Exemplo:
        sessao = {"estado_fluxo": "aguardando_confirmacao"}
        aguardando_confirmacao(sessao)  # True
    """
    estado = obter_estado_fluxo(sessao)
    return estado == "aguardando_confirmacao"


def aguardando_escolha_opcoes(sessao: Dict[str, Any]) -> bool:
    """
    Verifica se está aguardando escolha entre opções.

    Estados cobertos:
    - "oferecendo_opcoes": Aguardando escolha de alternativa
    - "escolhendo_profissional": Aguardando escolha de profissional
    - "escolhendo_horario": Aguardando escolha de horário

    Args:
        sessao: Documento de sessão do Firestore

    Returns:
        True se aguardando qualquer tipo de escolha

    Exemplo:
        sessao = {"estado_fluxo": "oferecendo_opcoes"}
        aguardando_escolha_opcoes(sessao)  # True
    """
    estado = obter_estado_fluxo(sessao)
    return estado in ["oferecendo_opcoes", "escolhendo_profissional", "escolhendo_horario"]


def obter_proposta_agendamento(contexto: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Obtém proposta de agendamento do contexto.

    Args:
        contexto: Contexto de roteador

    Returns:
        Dict com proposta ou None se não existe

    Exemplo:
        contexto = {"proposta_agendamento": {"horario": "15h"}}
        obter_proposta_agendamento(contexto)  # {"horario": "15h"}
    """
    if not contexto:
        return None

    proposta = contexto.get("proposta_agendamento")
    if not proposta or not isinstance(proposta, dict):
        return None

    return proposta


def obter_opcoes_disponiveis(contexto: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtém opções disponíveis do contexto.

    Retorna dict com:
    - opcoes_horario: Lista de horários
    - profissionais: Lista de profissionais
    - etc

    Args:
        contexto: Contexto de roteador

    Returns:
        Dict com opções disponíveis

    Exemplo:
        contexto = {
            "opcoes_horario": ["15h", "16h"],
            "profissionais": [{"nome": "Bruna"}, {"nome": "Maria"}]
        }
        obter_opcoes_disponiveis(contexto)
        # {
        #   "opcoes_horario": [...],
        #   "profissionais": [...]
        # }
    """
    return {
        "opcoes_horario": contexto.get("opcoes_horario", []),
        "profissionais": contexto.get("profissionais", [])
    }


def validar_estado_fluxo(estado: str) -> bool:
    """
    Valida se estado_fluxo é um valor reconhecido.

    Estados válidos:
    - "vazio"
    - "agendando"
    - "aguardando_confirmacao"
    - "cancelando"
    - "oferecendo_opcoes"
    - "escolhendo_profissional"
    - "escolhendo_horario"

    Args:
        estado: Estado a validar

    Returns:
        True se estado é válido

    Exemplo:
        validar_estado_fluxo("agendando")  # True
        validar_estado_fluxo("inexistente")  # False
    """
    estados_validos = [
        "vazio",
        "agendando",
        "aguardando_confirmacao",
        "cancelando",
        "oferecendo_opcoes",
        "escolhendo_profissional",
        "escolhendo_horario"
    ]

    return estado in estados_validos
