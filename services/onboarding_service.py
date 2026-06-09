#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Serviço de Onboarding — Coleta de dados obrigatórios no primeiro acesso
"""

import re
import json
from utils.contexto_temporario import salvar_contexto_temporario

# Simulação de Firestore (será mockado nos testes)
_firestore_data = {}


async def processar_onboarding_endereco_dono(
    user_id: str,
    dono_id: str,
    texto_usuario: str,
    ctx: dict,
    context
):
    """
    Coleta endereço do dono na primeira interação.

    Verifica se:
    1. user_id == dono_id (é dono) — garantido pelo router
    2. Tenant não tem endereço salvo
    3. Se sim, pergunta e salva

    Retorna: dict compatível com router (deve chamar _send_and_stop) ou None
    """

    print(f"🚀 [ONBOARDING] processar_onboarding_endereco_dono chamado | user_id={user_id}, dono_id={dono_id}", flush=True)

    # Verificar se já tem endereço salvo no Firestore
    endereco_existente = await buscar_endereco_negocio(dono_id)
    print(f"🚀 [ONBOARDING] endereco_existente={endereco_existente}", flush=True)
    if endereco_existente:
        # Já tem endereço, não perguntar de novo
        return None

    # Estado: aguardando resposta com endereço?
    if ctx.get("estado_fluxo") == "aguardando_endereco_negocio":
        # Dono respondeu à pergunta anterior
        endereco_parsed = _extrair_endereco(texto_usuario)

        if not endereco_parsed.get("rua"):
            # Não encontrou rua
            resposta = "Me envie a rua e o número do negócio."
            # Retornar para router chamar _send_and_stop
            return {
                "handled": True,
                "acao": "send_stop",
                "resposta": resposta
            }

        if not endereco_parsed.get("numero"):
            # Não encontrou número
            resposta = "Me envie também o número do endereço."
            return {
                "handled": True,
                "acao": "send_stop",
                "resposta": resposta
            }

        # Temos rua e número, salvar em Firestore
        endereco = {
            "rua": endereco_parsed["rua"],
            "numero": endereco_parsed["numero"],
            "completo": endereco_parsed["completo"]
        }

        sucesso = await salvar_endereco_negocio(dono_id, endereco)

        if not sucesso:
            resposta = "Erro ao salvar endereço. Tente novamente."
            return {
                "handled": True,
                "acao": "send_stop",
                "resposta": resposta
            }

        # Limpar estado — volta ao fluxo normal (agendamento)
        ctx.pop("estado_fluxo", None)
        ctx.pop("aguardando_endereco_negocio", None)
        ctx["estado_fluxo"] = "agendando"  # Retorna ao estado normal
        await salvar_contexto_temporario(user_id, ctx)

        resposta = f"Perfeito. Endereço salvo: {endereco['completo']}."
        return {
            "handled": True,
            "acao": "send_stop",
            "resposta": resposta
        }

    # Primeira vez: não tem endereço, não perguntamos ainda → perguntar agora
    ctx["estado_fluxo"] = "aguardando_endereco_negocio"
    ctx["aguardando_endereco_negocio"] = True
    await salvar_contexto_temporario(user_id, ctx)

    resposta = "Qual é o endereço do negócio? Pode me mandar rua e número."
    return {
        "handled": True,
        "acao": "send_stop",
        "resposta": resposta
    }


def _extrair_endereco(texto: str) -> dict:
    """
    Extrai rua e número de forma determinística.

    Exemplos:
    - "Rua João Baroni número 550"
    - "Rua João Baroni, 550"
    - "Rua João Baroni 550"
    - "Avenida Paulista 1000"

    Retorna:
    {
        "rua": "Rua João Baroni",
        "numero": "550",
        "completo": "Rua João Baroni, 550"
    }
    """

    resultado = {
        "rua": None,
        "numero": None,
        "completo": None
    }

    texto = texto.strip()

    # Padrão 1: "Rua ... número N"
    match = re.search(r"((?:rua|avenida|avenue|av|r\.)\s+[\w\s]+?)\s+(?:número|nº|n\.?|,)\s*(\d+)",
                     texto, re.IGNORECASE)
    if match:
        resultado["rua"] = match.group(1).strip()
        resultado["numero"] = match.group(2).strip()

    # Padrão 2: "Rua ... , N"
    if not resultado["numero"]:
        match = re.search(r"((?:rua|avenida|avenue|av|r\.)\s+[\w\s]+?),\s*(\d+)",
                         texto, re.IGNORECASE)
        if match:
            resultado["rua"] = match.group(1).strip()
            resultado["numero"] = match.group(2).strip()

    # Padrão 3: "Rua ... N" (última palavra é número)
    if not resultado["numero"]:
        match = re.search(r"((?:rua|avenida|avenue|av|r\.)\s+[\w\s]+?)\s+(\d+)\s*$",
                         texto, re.IGNORECASE)
        if match:
            resultado["rua"] = match.group(1).strip()
            resultado["numero"] = match.group(2).strip()

    # Normalizar rua (capitalizar primeira letra de cada palavra)
    if resultado["rua"]:
        resultado["rua"] = _normalizar_endereco(resultado["rua"])

    # Montar completo
    if resultado["rua"] and resultado["numero"]:
        resultado["completo"] = f"{resultado['rua']}, {resultado['numero']}"

    return resultado


def _normalizar_endereco(texto: str) -> str:
    """Normaliza endereço: capitaliza corretamente"""

    # Se começa com "rua" ou "avenida", manter como está
    if texto.lower().startswith(("rua", "avenida", "avenue", "av.", "av", "r.")):
        # Manter primeira letra maiúscula e resto como foi
        return texto[0].upper() + texto[1:] if texto else texto

    return texto.strip()


# =========================================================
# 🔗 HELPER FUNCTIONS — Firestore integration
# =========================================================

async def buscar_endereco_negocio(tenant_id: str):
    """Busca endereço salvo em Clientes/{tenant_id}/configuracao/dados_negocio"""
    try:
        from services.firebase_service_async import buscar_dado_em_path

        path = f"Clientes/{tenant_id}/configuracao/dados_negocio"
        dados = await buscar_dado_em_path(path)

        if dados and isinstance(dados, dict):
            return dados.get("endereco")

        return None
    except Exception as e:
        print(f"️ [ONBOARDING] Erro ao buscar endereço: {e}", flush=True)
        return None


async def salvar_endereco_negocio(tenant_id: str, endereco: dict):
    """Salva endereço em Clientes/{tenant_id}/configuracao/dados_negocio"""
    try:
        from services.firebase_service_async import salvar_dado_em_path

        path = f"Clientes/{tenant_id}/configuracao/dados_negocio"
        dados = {
            "endereco": endereco
        }

        await salvar_dado_em_path(path, dados)
        return True
    except Exception as e:
        print(f"️ [ONBOARDING] Erro ao salvar endereço: {e}", flush=True)
        return False
