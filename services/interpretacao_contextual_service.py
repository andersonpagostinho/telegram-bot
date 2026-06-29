#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Serviço de Interpretação Contextual

Interpreta respostas do usuário DENTRO de um fluxo ativo.
Nunca retorna "contexto_neutro" quando há estado_fluxo ativo.

Regra: estado_fluxo + draft_agendamento + mensagem
       → estrutura interpretada
       → código valida
       → motor determinístico executa
"""

async def interpretar_resposta_contextual(
    tenant_id: str,
    actor_id: str,
    mensagem: str,
    estado_fluxo: str,
    draft_agendamento: dict = None,
    contexto: dict = None
) -> dict:
    """
    Interpreta resposta do usuário no contexto do fluxo ativo.

    Args:
        tenant_id: ID do negócio
        actor_id: ID do ator
        mensagem: Texto da resposta do usuário
        estado_fluxo: Estado atual (aguardando_profissional, aguardando_horario, etc)
        draft_agendamento: Dados parciais do agendamento em progresso
        contexto: Contexto da sessão

    Returns:
        dict com interpretação estruturada:
        {
            "tipo_resposta": str,
            "interpretado_sucesso": bool,
            "confianca": float,  # 0.0-1.0
            "ambigua": bool,
            ... (campos específicos por tipo)
        }
    """
    ctx = contexto or {}
    draft = draft_agendamento or {}
    msg = (mensagem or "").strip().lower()

    # Guard: se não há fluxo ativo, retornar None (não é interpretação contextual)
    if not estado_fluxo or estado_fluxo == "idle":
        return None

    # Despachar por tipo de fluxo
    if estado_fluxo == "aguardando_profissional":
        return _interpretar_profissional(msg, draft, ctx)

    elif estado_fluxo == "aguardando_horario":
        return _interpretar_horario(msg, draft, ctx)

    elif estado_fluxo == "aguardando_data":
        return _interpretar_data(msg, draft, ctx)

    elif estado_fluxo == "aguardando_servico":
        return _interpretar_servico(msg, draft, ctx)

    elif estado_fluxo == "aguardando_confirmacao_agendamento":
        return _interpretar_confirmacao(msg, draft, ctx)

    elif estado_fluxo == "aguardando_escolha_horario":
        return _interpretar_escolha_horario(msg, draft, ctx)

    elif estado_fluxo == "aguardando_escolha_profissional":
        return _interpretar_escolha_profissional(msg, draft, ctx)

    elif estado_fluxo == "cancelamento_pendente":
        return _interpretar_confirmacao_cancelamento(msg, draft, ctx)

    else:
        # Fluxo desconhecido, mas ativo → não cair em neutro
        return {
            "tipo_resposta": "desconhecido",
            "interpretado_sucesso": False,
            "confianca": 0.0,
            "ambigua": True,
            "mensagem_original": mensagem,
            "estado_fluxo": estado_fluxo
        }


def _interpretar_profissional(msg: str, draft: dict, ctx: dict) -> dict:
    """Interpreta resposta quando aguardando_profissional"""

    # Palavras-chave de indiferença
    indiferenca = [
        "não tenho preferência", "sem preferência", "qualquer uma",
        "qualquer", "tanto faz", "a que puder", "não ligo",
        "não importa", "qualquer profissional", "você escolhe",
        "indiferente", "a disponível", "quem tiver", "próxima"
    ]

    # Verificar indiferença
    if any(palavra in msg for palavra in indiferenca):
        return {
            "tipo_resposta": "preferencia_profissional",
            "profissional_indiferente": True,
            "profissional_nome": None,
            "ambigua": False,
            "confianca": 0.95,
            "interpretado_sucesso": True
        }

    # Procurar nome (pode ser profissional específico)
    # Estratégia simples: se tem nome, tentar extrair
    palavras = msg.split()
    if len(palavras) <= 3:  # Resposta curta, provavelmente um nome
        return {
            "tipo_resposta": "preferencia_profissional",
            "profissional_indiferente": False,
            "profissional_nome": msg,
            "ambigua": len(palavras) > 1,  # Múltiplas palavras = ambíguo
            "confianca": 0.7 if len(palavras) == 1 else 0.5,
            "interpretado_sucesso": True
        }

    # Resposta longa demais para ser só nome
    return {
        "tipo_resposta": "preferencia_profissional",
        "profissional_indiferente": False,
        "profissional_nome": None,
        "ambigua": True,
        "confianca": 0.3,
        "interpretado_sucesso": False,
        "nota": "Resposta ambígua, não parece ser nome de profissional"
    }


def _interpretar_horario(msg: str, draft: dict, ctx: dict) -> dict:
    """Interpreta resposta quando aguardando_horario"""

    # Procurar padrões de horário (HH:MM)
    import re
    match_hora = re.search(r"(\d{1,2}):(\d{2})", msg)

    if match_hora:
        hora_str = match_hora.group(0)
        return {
            "tipo_resposta": "preferencia_horario",
            "horario": hora_str,
            "periodo": None,
            "horario_indiferente": False,
            "ambigua": False,
            "confianca": 0.9,
            "interpretado_sucesso": True
        }

    # Palavras de período
    periodos_map = {
        ("manhã", "cedo", "madrugada"): "manha",
        ("tarde", "à tarde"): "tarde",
        ("noite", "noitinha"): "noite",
        ("dia", "durante dia"): "manha"  # Padrão: manhã
    }

    for palavras, periodo in periodos_map.items():
        if any(p in msg for p in palavras):
            return {
                "tipo_resposta": "preferencia_horario",
                "horario": None,
                "periodo": periodo,
                "horario_indiferente": False,
                "ambigua": True,
                "confianca": 0.6,
                "interpretado_sucesso": True
            }

    # Indiferença de horário
    if any(p in msg for p in ["qualquer hora", "não importa", "tanto faz", "indiferente"]):
        return {
            "tipo_resposta": "preferencia_horario",
            "horario": None,
            "periodo": None,
            "horario_indiferente": True,
            "ambigua": False,
            "confianca": 0.85,
            "interpretado_sucesso": True
        }

    # Não conseguiu interpretar
    return {
        "tipo_resposta": "preferencia_horario",
        "horario": None,
        "periodo": None,
        "horario_indiferente": False,
        "ambigua": True,
        "confianca": 0.2,
        "interpretado_sucesso": False
    }


def _interpretar_data(msg: str, draft: dict, ctx: dict) -> dict:
    """Interpreta resposta quando aguardando_data"""
    # Implementação simplificada
    return {
        "tipo_resposta": "preferencia_data",
        "data_relativa": None,
        "data_iso": None,
        "ambigua": True,
        "confianca": 0.5,
        "interpretado_sucesso": False,
        "nota": "Extração de data requer parser mais sofisticado"
    }


def _interpretar_servico(msg: str, draft: dict, ctx: dict) -> dict:
    """Interpreta resposta quando aguardando_servico"""
    # Implementação simplificada
    return {
        "tipo_resposta": "preferencia_servico",
        "servico": None,
        "ambigua": True,
        "confianca": 0.5,
        "interpretado_sucesso": False
    }


def _interpretar_confirmacao(msg: str, draft: dict, ctx: dict) -> dict:
    """Interpreta resposta quando aguardando_confirmacao_agendamento"""

    msg_lower = msg.lower()

    # Confirmação positiva
    confirmacao_sim = ["sim", "okay", "ok", "certo", "tudo bem", "confirmo", "é", "vai"]
    if any(p in msg_lower for p in confirmacao_sim):
        return {
            "tipo_resposta": "confirmacao",
            "confirmado": True,
            "ambigua": False,
            "confianca": 0.9,
            "interpretado_sucesso": True
        }

    # Confirmação negativa
    confirmacao_nao = ["não", "nega", "negado", "cancela", "não quero", "para"]
    if any(p in msg_lower for p in confirmacao_nao):
        return {
            "tipo_resposta": "confirmacao",
            "confirmado": False,
            "ambigua": False,
            "confianca": 0.9,
            "interpretado_sucesso": True
        }

    # Ambíguo
    return {
        "tipo_resposta": "confirmacao",
        "confirmado": None,
        "ambigua": True,
        "confianca": 0.2,
        "interpretado_sucesso": False
    }


def _interpretar_escolha_horario(msg: str, draft: dict, ctx: dict) -> dict:
    """Interpreta resposta quando aguardando_escolha_horario (múltiplas opções)"""
    # Procurar número de índice
    import re
    match_num = re.search(r"^(\d+)", msg.strip())

    if match_num:
        indice = int(match_num.group(1)) - 1  # Converter para índice 0-based
        return {
            "tipo_resposta": "escolha_horario",
            "indice": indice,
            "horario": None,
            "ambigua": False,
            "confianca": 0.95,
            "interpretado_sucesso": True
        }

    return {
        "tipo_resposta": "escolha_horario",
        "indice": None,
        "horario": None,
        "ambigua": True,
        "confianca": 0.2,
        "interpretado_sucesso": False
    }


def _interpretar_escolha_profissional(msg: str, draft: dict, ctx: dict) -> dict:
    """Interpreta resposta quando aguardando_escolha_profissional"""
    # Procurar número
    import re
    match_num = re.search(r"^(\d+)", msg.strip())

    if match_num:
        return {
            "tipo_resposta": "escolha_profissional",
            "indice": int(match_num.group(1)) - 1,
            "profissional_nome": None,
            "ambigua": False,
            "confianca": 0.95,
            "interpretado_sucesso": True
        }

    # Ou pode ser indiferença
    if any(p in msg.lower() for p in ["indiferente", "tanto faz", "qualquer"]):
        return {
            "tipo_resposta": "escolha_profissional",
            "indice": None,
            "profissional_indiferente": True,
            "ambigua": False,
            "confianca": 0.8,
            "interpretado_sucesso": True
        }

    return {
        "tipo_resposta": "escolha_profissional",
        "indice": None,
        "profissional_nome": None,
        "ambigua": True,
        "confianca": 0.2,
        "interpretado_sucesso": False
    }


def _interpretar_confirmacao_cancelamento(msg: str, draft: dict, ctx: dict) -> dict:
    """Interpreta resposta quando cancelamento_pendente"""
    # Mesma lógica que confirmação normal
    return _interpretar_confirmacao(msg, draft, ctx)
