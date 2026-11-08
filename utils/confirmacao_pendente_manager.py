# -*- coding: utf-8 -*-
"""
Manager para confirmacao_pendente estruturada.

Responsabilidade: Criar, validar, consumir, invalidar confirmacao_pendente
com operacao_id vinculado a um agendamento específico.

Requisitos:
1. Criar SOMENTE quando Eve apresenta confirmação (não quando draft existe)
2. Persistir em Firestore em Clientes/{tenant_id}/Sessoes/{actor_id}
3. Recuperar após restart
4. Não autorizar "sim" apenas por draft existir — validar operacao_id match
5. Não autorizar "sim" apenas por palavra — validar operacao_id + confirmacao_pendente
6. Invalidar quando draft substitui, cancela ou expira
7. Validar tipo e status da pendência
8. Consumir (pop) APÓS criar_evento sucesso
9. Preservar evento se resposta falha após consumo
10. Isolamento multi-tenant: validar tenant_id em todas operações
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional


def gerar_operacao_id(actor_id: str, tipo: str, dados: dict) -> str:
    """
    Gera operacao_id determinístico e imutável.

    Formato: {tipo}_{actor_id}_{profissional}_{data}_{hora}

    Args:
        actor_id: ID do cliente/usuário
        tipo: "agendamento" | "alteracao" | "consulta"
        dados: Dict com profissional, data, hora

    Returns:
        String com operacao_id determinístico

    Exemplo:
        agendamento_5511991382080_bruna_20261106_1500
    """
    profissional = (dados.get("profissional") or "").lower().replace(" ", "_")
    data = (dados.get("data") or "").replace("-", "")[:8]  # YYYYMMDD
    hora = (dados.get("hora") or "").replace(":", "")[:4]  # HHMM

    return f"{tipo}_{actor_id}_{profissional}_{data}_{hora}"


def criar_confirmacao_pendente(
    operacao_id: str,
    tipo: str = "agendamento",
    max_tentativas: int = 3
) -> dict:
    """
    Cria estrutura confirmacao_pendente para ser persistida.

    Args:
        operacao_id: ID único da operação (gerado por gerar_operacao_id)
        tipo: "agendamento" | "alteracao" | "consulta"
        max_tentativas: Máximo de vezes que pode pedir confirmação (default 3)

    Returns:
        Dict pronto para persistir em ctx["confirmacao_pendente"]
    """
    agora = datetime.now()
    return {
        "operacao_id": operacao_id,
        "tipo": tipo,
        "status": "pendente",  # pendente | consumida | expirada | invalidada
        "apresentada_em": agora.isoformat(),
        "tentativas": 1,
        "max_tentativas": max_tentativas,
        "expira_em": (agora + timedelta(minutes=5)).isoformat(),  # 5 min timeout
    }


def validar_confirmacao_pendente(
    ctx: dict,
    operacao_id_esperado: str,
) -> Dict[str, Any]:
    """
    Valida se confirmacao_pendente ativa matches operacao_id esperado.

    Checklist:
    1. confirmacao_pendente existe?
    2. Status == "pendente"?
    3. operacao_id == operacao_id_esperado?
    4. Não expirou (expira_em > agora)?
    5. tentativas < max_tentativas?

    Args:
        ctx: Contexto da sessão
        operacao_id_esperado: ID que se espera estar pendente

    Returns:
        {
            "valida": bool,
            "motivo": str,
            "confirmacao_pendente": dict or None
        }
    """
    confirmacao = ctx.get("confirmacao_pendente")

    if not confirmacao:
        return {
            "valida": False,
            "motivo": "sem_confirmacao_pendente",
            "confirmacao_pendente": None
        }

    # Verificar status
    if confirmacao.get("status") != "pendente":
        return {
            "valida": False,
            "motivo": f"status_invalido: {confirmacao.get('status')}",
            "confirmacao_pendente": None
        }

    # Verificar operacao_id match (CRÍTICO para evitar C5)
    if confirmacao.get("operacao_id") != operacao_id_esperado:
        return {
            "valida": False,
            "motivo": f"operacao_id_mismatch: esperado {operacao_id_esperado}, "
                      f"pendente {confirmacao.get('operacao_id')}",
            "confirmacao_pendente": None
        }

    # Verificar expiração
    try:
        expira_em = datetime.fromisoformat(confirmacao.get("expira_em", ""))
        if datetime.now() > expira_em:
            return {
                "valida": False,
                "motivo": "expirada",
                "confirmacao_pendente": None
            }
    except:
        return {
            "valida": False,
            "motivo": "erro_ao_verificar_expiracao",
            "confirmacao_pendente": None
        }

    # Verificar tentativas
    tentativas = confirmacao.get("tentativas", 0)
    max_tentativas = confirmacao.get("max_tentativas", 3)
    if tentativas >= max_tentativas:
        return {
            "valida": False,
            "motivo": f"max_tentativas_excedido ({tentativas}/{max_tentativas})",
            "confirmacao_pendente": None
        }

    return {
        "valida": True,
        "motivo": "confirmacao_valida",
        "confirmacao_pendente": confirmacao
    }


def incrementar_tentativa(confirmacao_pendente: dict) -> dict:
    """
    Incrementa contador de tentativas de confirmação.

    Chamado quando usuário vê pergunta novamente mas ainda não respondeu.
    """
    confirmacao_pendente = confirmacao_pendente or {}
    confirmacao_pendente["tentativas"] = confirmacao_pendente.get("tentativas", 1) + 1
    return confirmacao_pendente


def consumir_confirmacao_pendente(confirmacao_pendente: dict) -> dict:
    """
    Marca confirmacao_pendente como consumida.

    Chamado APÓS criar_evento sucesso para que "sim" repetido não
    crie novo evento (idempotência).

    Args:
        confirmacao_pendente: Estrutura a ser marcada como consumida

    Returns:
        Cópia com status="consumida" e consumida_em timestamp
    """
    confirmacao_pendente = confirmacao_pendente or {}
    confirmacao_pendente["status"] = "consumida"
    confirmacao_pendente["consumida_em"] = datetime.now().isoformat()
    return confirmacao_pendente


def invalidar_confirmacao_pendente(ctx: dict, motivo: str = "cancelamento") -> dict:
    """
    Invalida confirmacao_pendente sem consumir.

    Usado quando:
    - Draft muda de horário/profissional
    - Draft é cancelado
    - Nova consulta é feita

    Args:
        ctx: Contexto
        motivo: "mudanca_draft" | "cancelamento" | "nova_consulta" | "timeout"

    Returns:
        Cópia de ctx com confirmacao_pendente invalidada
    """
    ctx = ctx or {}
    confirmacao = ctx.get("confirmacao_pendente", {})

    if confirmacao:
        confirmacao["status"] = "invalidada"
        confirmacao["invalidada_em"] = datetime.now().isoformat()
        confirmacao["motivo_invalidacao"] = motivo
        ctx["confirmacao_pendente"] = confirmacao

    return ctx


async def persistir_confirmacao_pendente(
    tenant_id: str,
    actor_id: str,
    confirmacao_pendente: dict,
    atualizar_dado_em_path_func
) -> bool:
    """
    Persiste confirmacao_pendente em Firestore.

    Path: Clientes/{tenant_id}/Sessoes/{actor_id}
    Field: confirmacao_pendente

    Args:
        tenant_id: ID do cliente/salão (CRÍTICO para multi-tenant)
        actor_id: ID do usuário/cliente
        confirmacao_pendente: Dict estruturado
        atualizar_dado_em_path_func: Função de persistência (injetada)

    Returns:
        True se persistiu, False se erro
    """
    if not tenant_id or not actor_id:
        raise ValueError("tenant_id e actor_id são obrigatórios")

    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    try:
        await atualizar_dado_em_path_func(path, {
            "confirmacao_pendente": confirmacao_pendente
        })
        return True
    except Exception as e:
        print(f"[ERROR] Falha ao persistir confirmacao_pendente: {e}", flush=True)
        return False


async def carregar_confirmacao_pendente(
    tenant_id: str,
    actor_id: str,
    buscar_dado_em_path_func
) -> Optional[dict]:
    """
    Carrega confirmacao_pendente de Firestore.

    Args:
        tenant_id: ID do cliente/salão
        actor_id: ID do usuário
        buscar_dado_em_path_func: Função de leitura (injetada)

    Returns:
        Dict com confirmacao_pendente ou None se não existe
    """
    if not tenant_id or not actor_id:
        return None

    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    try:
        sessao = await buscar_dado_em_path_func(path)
        if sessao:
            return sessao.get("confirmacao_pendente")
    except:
        pass

    return None


def consumir_confirmacao_pendente_com_fencing(
    confirmacao_pendente: dict,
    tenant_id: str,
    actor_id: str,
    operacao_doc: dict,
    lease_token: str = "",
    proprietario_id: str = ""
) -> Dict[str, Any]:
    """
    [P0.29.13] Consome confirmacao_pendente COM VALIDAÇÃO DE FENCING.

    Validações OBRIGATÓRIAS (todos devem passar):
    1. tenant_id match
    2. actor_id match
    3. operacao_id match
    4. confirmacao.status == "pendente" (CRÍTICO)
    5. status operacao = "EVENTO_PERSISTIDO" (CRÍTICO)
    6. lease_token = token atual (CRÍTICO para rejeitar proprietario antigo)
    7. lease_expira_em não expirado (CRÍTICO)
    8. proprietario_id válido (CRÍTICO)
    9. evento persistido

    Args:
        confirmacao_pendente: Dict com confirmacao pendente
        tenant_id: ID do cliente/salão (para validação multi-tenant)
        actor_id: ID do usuário (para validação multi-tenant)
        operacao_doc: Documento OperacaoEmAndamento do Firestore
        lease_token: Token esperado (para validar proprietário)
        proprietario_id: ID do proprietário esperado (para validar proprietário)

    Returns:
        {
            "ok": bool,
            "motivo": str,
            "confirmacao_consumida": dict or None
        }
    """
    if not confirmacao_pendente:
        return {
            "ok": False,
            "motivo": "confirmacao_pendente_vazia",
            "confirmacao_consumida": None
        }

    if not operacao_doc:
        return {
            "ok": False,
            "motivo": "operacao_doc_nao_existe",
            "confirmacao_consumida": None
        }

    # VALIDAÇÃO 1: tenant_id match
    if operacao_doc.get("tenant_id") != tenant_id:
        return {
            "ok": False,
            "motivo": "tenant_id_mismatch",
            "confirmacao_consumida": None
        }

    # VALIDAÇÃO 2: actor_id match
    if operacao_doc.get("actor_id") != actor_id:
        return {
            "ok": False,
            "motivo": "actor_id_mismatch",
            "confirmacao_consumida": None
        }

    # VALIDAÇÃO 3: operacao_id match
    if operacao_doc.get("operacao_id") != confirmacao_pendente.get("operacao_id"):
        return {
            "ok": False,
            "motivo": "operacao_id_mismatch",
            "operacao_id_esperado": confirmacao_pendente.get("operacao_id"),
            "operacao_id_efetivo": operacao_doc.get("operacao_id"),
            "confirmacao_consumida": None
        }

    # VALIDAÇÃO 4: confirmacao.status == "pendente" (CRÍTICO)
    confirmacao_status = confirmacao_pendente.get("status")
    if confirmacao_status != "pendente":
        return {
            "ok": False,
            "motivo": f"confirmacao_status_invalido: {confirmacao_status}",
            "esperado": "pendente",
            "confirmacao_consumida": None
        }

    # VALIDAÇÃO 5: status operacao = "EVENTO_PERSISTIDO" (CRÍTICO)
    status_operacao = operacao_doc.get("status")
    if status_operacao != "evento_persistido":
        return {
            "ok": False,
            "motivo": f"status_operacao_invalido: {status_operacao}",
            "esperado": "evento_persistido",
            "confirmacao_consumida": None
        }

    # VALIDAÇÃO 6: lease_token = token atual (FENCING)
    doc_lease_token = operacao_doc.get("lease_token")
    if not lease_token:
        # Se lease_token não foi fornecido, validar que documento tem um válido
        if not doc_lease_token:
            return {
                "ok": False,
                "motivo": "lease_token_ausente_no_documento",
                "confirmacao_consumida": None
            }
    else:
        # Se lease_token foi fornecido, validar correspondência
        if doc_lease_token != lease_token:
            return {
                "ok": False,
                "motivo": "lease_token_invalido",
                "causa": "proprietario_antigo_ou_transferido",
                "confirmacao_consumida": None
            }

    # VALIDAÇÃO 7: lease_expira_em não expirado (FENCING)
    lease_expira_em_str = operacao_doc.get("lease_expira_em")
    if lease_expira_em_str:
        try:
            lease_expira_em = datetime.fromisoformat(lease_expira_em_str)
            if datetime.now() > lease_expira_em:
                return {
                    "ok": False,
                    "motivo": "lease_expirado",
                    "expira_em": lease_expira_em_str,
                    "confirmacao_consumida": None
                }
        except Exception as e:
            return {
                "ok": False,
                "motivo": "erro_ao_validar_lease_expiracao",
                "confirmacao_consumida": None
            }

    # VALIDAÇÃO 8: proprietario_id válido (FENCING)
    doc_proprietario_id = operacao_doc.get("proprietario_id")
    if proprietario_id:
        # Se proprietario_id foi fornecido, validar correspondência
        if doc_proprietario_id != proprietario_id:
            return {
                "ok": False,
                "motivo": "proprietario_mismatch",
                "proprietario_esperado": proprietario_id,
                "proprietario_efetivo": doc_proprietario_id,
                "confirmacao_consumida": None
            }
    else:
        # Se proprietario_id não foi fornecido, apenas validar que existe
        if not doc_proprietario_id:
            return {
                "ok": False,
                "motivo": "proprietario_id_ausente",
                "confirmacao_consumida": None
            }

    # VALIDAÇÃO 9: evento foi persistido
    evento_id = operacao_doc.get("evento_id")
    if not evento_id:
        return {
            "ok": False,
            "motivo": "evento_id_nao_existe",
            "confirmacao_consumida": None
        }

    # Se todas as validações passaram: consumir
    confirmacao_consumida = confirmacao_pendente.copy()
    confirmacao_consumida["status"] = "consumida"
    confirmacao_consumida["consumida_em"] = datetime.now().isoformat()

    return {
        "ok": True,
        "motivo": "confirmacao_consumida_com_sucesso",
        "confirmacao_consumida": confirmacao_consumida
    }
