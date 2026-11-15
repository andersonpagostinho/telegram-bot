"""
FASE 3 - Serviço de Reconhecimento de Opções

Reconhece referências naturais como "o primeiro", "a primeira", "opção 1", etc.
Recupera contexto com validação TTL.
Marca opcao_selecionada_id sem criar eventos/locks.
"""

import re
from datetime import datetime
from schemas.resultado_consulta_schema import ContextoResultadoConsulta


# ==============================================================================
# Parseamento de Referências
# ==============================================================================

async def parsear_referencia_opcao(mensagem: str, total_opcoes: int = None) -> int | None:
    """
    Parseia referência natural para número de opção.

    Reconhece:
    - "o primeiro", "a primeira" → 1
    - "o segundo", "a segunda" → 2
    - "o terceiro", "a terceira" → 3
    - "o último", "a última" → total_opcoes
    - "opção 1", "opção 2" → 1, 2

    Retorna:
    - int: número da opção (1-indexed)
    - None: referência ambígua ou inválida
    """

    msg_lower = mensagem.lower().strip()

    # Mapeamento de palavras ordinais
    ordinais = {
        "primeiro": 1, "primeira": 1,
        "segundo": 2, "segunda": 2,
        "terceiro": 3, "terceira": 3,
        "quarto": 4, "quarta": 4,
        "quinto": 5, "quinta": 5,
        "sexto": 6, "sexta": 6,
        "sétimo": 7, "sétima": 7,
        "oitavo": 8, "oitava": 8,
        "nono": 9, "nona": 9,
        "décimo": 10, "décima": 10,
        "último": -1, "última": -1,  # -1 = última
        "penúltimo": -2, "penúltima": -2,
    }

    # Tentar encontrar ordinal
    for palavra, numero in ordinais.items():
        if palavra in msg_lower:
            if numero == -1:  # último
                if total_opcoes is None:
                    return None  # Não sei quantas opções tem
                return total_opcoes
            elif numero == -2:  # penúltimo
                if total_opcoes is None:
                    return None
                return max(1, total_opcoes - 1)
            else:
                return numero

    # Tentar encontrar "opção N"
    match = re.search(r'opção\s+(\d+)', msg_lower)
    if match:
        return int(match.group(1))

    # Tentar encontrar número sozinho
    match = re.search(r'^(\d+)$', msg_lower)
    if match:
        return int(match.group(1))

    # Ambíguo ou não reconhecido
    return None


async def eh_referencia_opcao(mensagem: str) -> bool:
    """
    Verifica se a mensagem é uma referência a opção.

    Retorna True se parece ser "o primeiro", "opção 2", etc.
    Retorna False para outras intenções.
    """

    msg_lower = mensagem.lower().strip()

    # Palavras-chave que indicam referência
    palavras_opcao = [
        "primeiro", "primeira", "segundo", "segunda", "terceiro", "terceira",
        "quarto", "quarta", "quinto", "quinta", "sexto", "sexta",
        "sétimo", "sétima", "oitavo", "oitava", "nono", "nona",
        "décimo", "décima", "último", "última", "penúltimo", "penúltima",
        "opção", "primeira opção", "segunda opção",
    ]

    for palavra in palavras_opcao:
        if palavra in msg_lower:
            return True

    # Verificar se é um número puro
    if re.match(r'^\d+$', msg_lower.strip()):
        return True

    return False


# ==============================================================================
# Seleção de Opção
# ==============================================================================

async def selecionar_opcao(contexto: ContextoResultadoConsulta, numero: int) -> dict:
    """
    Seleciona uma opção do contexto.

    Retorna:
    {
        "sucesso": bool,
        "opcao_id": str (se sucesso),
        "mensagem": str,
    }

    Sem criar eventos, locks, ou alterar draft_agendamento.
    """

    if not contexto.opcoes:
        return {
            "sucesso": False,
            "mensagem": "Nenhuma opção disponível no contexto"
        }

    # Procurar opção com o número
    opcao_encontrada = None
    for opcao in contexto.opcoes:
        if opcao.numero == numero:
            opcao_encontrada = opcao
            break

    if not opcao_encontrada:
        return {
            "sucesso": False,
            "mensagem": f"Opção {numero} não existe (disponíveis: 1-{len(contexto.opcoes)})"
        }

    return {
        "sucesso": True,
        "opcao_id": opcao_encontrada.opcao_id,
        "opcao": {
            "numero": opcao_encontrada.numero,
            "hora_inicio": opcao_encontrada.hora_inicio,
            "hora_fim": opcao_encontrada.hora_fim,
            "profissional": opcao_encontrada.profissional_id,
            "servicos": opcao_encontrada.servicos,
            "duracao": opcao_encontrada.duracao_total_min,
        },
        "mensagem": f"✅ Você escolheu o {numero}º horário: {opcao_encontrada.hora_inicio} até {opcao_encontrada.hora_fim}"
    }


# ==============================================================================
# Registro de Seleção
# ==============================================================================

async def registrar_opcao_selecionada(
    tenant_id: str,
    actor_id: str,
    opcao_id: str
) -> bool:
    """
    Registra a opção selecionada no contexto.

    Atualiza contexto_resultado_consulta.opcao_selecionada_id.
    Preserva todos os outros campos (merge=True).

    Retorna: True se sucesso, False se falha.

    NÃO cria evento, NÃO cria lock, NÃO altera draft_agendamento.
    """

    if not tenant_id or not actor_id:
        print(f"[REGISTRAR_SELECAO] ❌ tenant_id ou actor_id vazio")
        return False

    from services.firebase_service_async import get_async_client
    from services.resultado_consulta_service import recuperar_resultado_consulta

    try:
        # Recuperar contexto atual
        contexto = await recuperar_resultado_consulta(tenant_id, actor_id)

        if not contexto:
            print(f"[REGISTRAR_SELECAO] ❌ Contexto não encontrado")
            return False

        # Atualizar opcao_selecionada_id
        contexto.opcao_selecionada_id = opcao_id

        # Salvar (merge=True preserva draft_agendamento e outros campos)
        path = f"Clientes/{tenant_id.strip()}/Sessoes/{actor_id.strip()}"

        from services.firebase_service_async import salvar_dado_em_path

        resultado = await salvar_dado_em_path(
            path,
            {
                "contexto_resultado_consulta": contexto.to_dict()
            }
        )

        if resultado:
            print(f"[REGISTRAR_SELECAO] ✅ Opção {opcao_id} registrada")
            return True
        else:
            print(f"[REGISTRAR_SELECAO] ❌ Falha ao salvar")
            return False

    except Exception as e:
        print(f"[REGISTRAR_SELECAO] ❌ Erro: {str(e)[:100]}")
        return False


# ==============================================================================
# Fluxo Completo: Reconhecer + Selecionar + Registrar
# ==============================================================================

async def processar_selecao_opcao(
    mensagem: str,
    tenant_id: str,
    actor_id: str,
    contexto: ContextoResultadoConsulta = None
) -> dict:
    """
    Fluxo completo de reconhecimento e seleção.

    1. Verifica se é referência
    2. Parseia referência
    3. Recupera contexto (se não fornecido)
    4. Valida TTL
    5. Seleciona opção
    6. Registra seleção

    Retorna:
    {
        "sucesso": bool,
        "mensagem": str,
        "opcao_selecionada": dict (se sucesso),
    }
    """

    # 1. Verifica se é referência
    if not await eh_referencia_opcao(mensagem):
        return {
            "sucesso": False,
            "mensagem": "Não reconheço isso como seleção de opção",
            "eh_referencia": False
        }

    # 2. Recupera contexto
    if contexto is None:
        from services.resultado_consulta_service import recuperar_resultado_consulta
        contexto = await recuperar_resultado_consulta(tenant_id, actor_id)

    if not contexto:
        return {
            "sucesso": False,
            "mensagem": "Nenhuma consulta ativa. Faça uma pergunta sobre serviços primeiro."
        }

    # 3. Valida TTL
    if contexto.esta_expirado():
        return {
            "sucesso": False,
            "mensagem": "A lista de horários expirou. Por favor, faça uma nova busca."
        }

    # 4. Parseia referência
    numero = await parsear_referencia_opcao(mensagem, total_opcoes=len(contexto.opcoes))

    if numero is None:
        return {
            "sucesso": False,
            "mensagem": "Qual opção você quer? Digite 'a primeira', 'o segundo', 'a última', ou um número."
        }

    # 5. Seleciona
    resultado_selecao = await selecionar_opcao(contexto, numero)

    if not resultado_selecao["sucesso"]:
        return resultado_selecao

    # 6. Registra seleção
    opcao_id = resultado_selecao["opcao_id"]
    registrado = await registrar_opcao_selecionada(tenant_id, actor_id, opcao_id)

    if not registrado:
        return {
            "sucesso": False,
            "mensagem": "Erro ao registrar seleção. Tente novamente."
        }

    return {
        "sucesso": True,
        "mensagem": resultado_selecao["mensagem"],
        "opcao_selecionada": resultado_selecao["opcao"],
        "opcao_id": resultado_selecao["opcao_id"],
        "proximo_passo": "Confirme este horário para iniciar o agendamento?"
    }
