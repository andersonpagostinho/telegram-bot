"""
FASE 7: Validação determinística de retomada após 24h

Função pura (sem I/O direto) que valida se um draft pode ser retomado.
Critérios:
  - data_hora não está no passado
  - profissional existe em catálogo
  - serviço existe em catálogo
  - estado_fluxo é válido
"""

from datetime import datetime


def validar_retomada_draft(
    draft: dict | None,
    profissionais_catalogo: list[str] | None = None,
    servicos_catalogo: list[str] | None = None,
    agora: datetime | None = None
) -> dict:
    """
    Valida se um draft pode ser retomado após 24h.

    Entrada:
    - draft: draft_agendamento da sessão (ou None)
    - profissionais_catalogo: lista de nomes válidos
    - servicos_catalogo: lista de serviços válidos
    - agora: datetime atual (para testes, default=now())

    Saída:
    {
        "valido": bool,
        "motivo": str,
        "problemas": list[str],
        "pode_retomar": bool,
        "precisa_esclarecimento": bool
    }
    """
    if agora is None:
        agora = datetime.now()

    resultado = {
        "valido": True,
        "motivo": "Draft válido para retomada",
        "problemas": [],
        "pode_retomar": True,
        "precisa_esclarecimento": False
    }

    # Se draft não existe, não há retomada (novo fluxo)
    if not draft:
        resultado["valido"] = False
        resultado["pode_retomar"] = False
        resultado["motivo"] = "Sem draft anterior"
        return resultado

    # Validação 1: data_hora não está no passado
    data_hora_str = draft.get("data_hora")
    if data_hora_str:
        try:
            data_obj = datetime.fromisoformat(data_hora_str)
            if data_obj < agora:
                resultado["valido"] = False
                resultado["problemas"].append(f"Data {data_hora_str} está no passado")
                resultado["motivo"] = "Horário expirado"
        except (ValueError, TypeError):
            resultado["precisa_esclarecimento"] = True
            resultado["problemas"].append(f"Data_hora inválida: {data_hora_str}")
    else:
        resultado["precisa_esclarecimento"] = True
        resultado["problemas"].append("Data_hora ausente")

    # Validação 2: profissional existe em catálogo
    prof = draft.get("profissional")
    if prof:
        if profissionais_catalogo is not None:
            if prof not in profissionais_catalogo:
                resultado["valido"] = False
                resultado["problemas"].append(f"Profissional '{prof}' não encontrado")
                resultado["motivo"] = "Profissional inválido ou removido"
    else:
        resultado["precisa_esclarecimento"] = True
        resultado["problemas"].append("Profissional ausente")

    # Validação 3: serviço existe em catálogo
    servico = draft.get("serviço")
    if servico:
        if servicos_catalogo is not None:
            if servico not in servicos_catalogo:
                resultado["valido"] = False
                resultado["problemas"].append(f"Serviço '{servico}' não encontrado")
                resultado["motivo"] = "Serviço inválido ou removido"
    else:
        resultado["precisa_esclarecimento"] = True
        resultado["problemas"].append("Serviço ausente")

    # Validação 4: estado_fluxo
    estado = draft.get("estado_fluxo")
    if estado not in ["aguardando_profissional", "aguardando_servico", "aguardando_confirmacao", "aguardando_hora"]:
        resultado["precisa_esclarecimento"] = True
        resultado["problemas"].append(f"Estado fluxo inválido: {estado}")

    # Se há problemas, não pode retomar
    if resultado["problemas"]:
        resultado["pode_retomar"] = False

    return resultado


def formatar_rejeicao_retomada(validacao: dict) -> str:
    """Formata mensagem amigável para rejeição de retomada."""
    if validacao["pode_retomar"]:
        return "Draft válido para retomada"

    problemas = validacao["problemas"]
    if not problemas:
        return validacao["motivo"]

    # Mensagem específica por tipo de problema
    if any("Data" in p or "Horário" in p for p in problemas):
        return "O horário de seu agendamento anterior expirou. Vamos agendar novamente?"

    if any("Profissional" in p for p in problemas):
        return f"Infelizmente, {validacao['motivo'].lower()}. Qual profissional você prefere?"

    if any("Serviço" in p for p in problemas):
        return f"Infelizmente, {validacao['motivo'].lower()}. Qual serviço você prefere?"

    # Genérico
    return "Vamos começar um novo agendamento?"
