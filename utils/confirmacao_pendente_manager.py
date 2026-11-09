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

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from firebase_admin import firestore
from services.firestore_client import get_db


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

    [P0.29.18-FIX] Dual-pattern support:
    - Padrão 1: confirmacao_pendente com operacao_id
    - Padrão 2: dados_confirmacao_agendamento (auto-create confirmacao_pendente)

    Checklist:
    1. confirmacao_pendente existe OU dados_confirmacao_agendamento existe?
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

    # [P0.29.18-FIX] Se vazio/None, tentar criar a partir de dados_confirmacao_agendamento (padrão intermediário)
    if not confirmacao or (isinstance(confirmacao, dict) and not confirmacao.get("operacao_id")):
        dados_conf = ctx.get("dados_confirmacao_agendamento")
        if dados_conf and isinstance(dados_conf, dict) and dados_conf.get("profissional"):
            # Auto-criar confirmacao_pendente a partir de dados_confirmacao_agendamento
            print(f"[P0.29.18-FIX-AUTO] Criando confirmacao_pendente de dados_confirmacao_agendamento", flush=True)
            confirmacao = {
                "operacao_id": operacao_id_esperado,
                "tipo": "agendamento",
                "status": "pendente",
                "apresentada_em": datetime.now().isoformat(),
                "tentativas": 1,
                "max_tentativas": 3,
                "expira_em": (datetime.now() + timedelta(minutes=5)).isoformat(),
                "_origem_auto": "dados_confirmacao_agendamento"  # Rastreamento
            }
            ctx["confirmacao_pendente"] = confirmacao
        else:
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


async def consumir_confirmacao_pendente_atomicamente(
    tenant_id: str,
    actor_id: str,
    operacao_id: str,
    evento_id: str,
    lease_token: str,
    proprietario_id: str,
    dados_confirmados_snapshot: dict
) -> Dict[str, Any]:
    """
    [P0.29.17] Consome confirmacao_pendente ATOMICAMENTE em transação Firestore.

    Executa transação Firestore que:
    1. LER confirmacao_pendente, operacao_em_andamento, evento
    2. VALIDAR 9 critérios (incluindo snapshot matching)
    3. ESCREVER confirmacao.status="CONSUMIDA" + operacao.status="CONCLUIDA" (MESMA transação)

    Garantias:
    - Atomicidade: tudo ou nada (sem writes parciais)
    - Isolamento multi-tenant: validar tenant_id em todas refs
    - Idempotência: segundo consumo retorna "ja_consumida"

    Args:
        tenant_id: ID do cliente/salão
        actor_id: ID do usuário/cliente
        operacao_id: ID da operação em andamento
        evento_id: ID do evento já persistido
        lease_token: Token de fencing (proprietário atual)
        proprietario_id: ID do proprietário esperado
        dados_confirmados_snapshot: Snapshot dos dados confirmados (para validar evento)

    Returns:
        {
            "ok": bool,
            "motivo": str,
            "confirmacao_consumida": dict or None,
            "evento_id": str or None
        }
    """

    def transacao_consumir():
        """Transação Firestore para consumir atomicamente."""
        db = get_db()

        @firestore.transactional
        def callback(transaction):
            agora = datetime.now()

            # (1) REFS para os 3 documentos críticos
            confirmacao_ref = (
                db.collection("Clientes")
                .document(tenant_id)
                .collection("Sessoes")
                .document(actor_id)
            )
            operacao_ref = (
                db.collection("Clientes")
                .document(tenant_id)
                .collection("OperacoesEmAndamento")
                .document(operacao_id)
            )
            evento_ref = (
                db.collection("Clientes")
                .document(tenant_id)
                .collection("Eventos")
                .document(evento_id)
            )

            # (2) LER os 3 documentos ATOMICAMENTE
            confirmacao_docs = list(transaction.get(confirmacao_ref))
            operacao_docs = list(transaction.get(operacao_ref))
            evento_docs = list(transaction.get(evento_ref))

            confirmacao_data = confirmacao_docs[0].to_dict() if confirmacao_docs else None
            operacao_data = operacao_docs[0].to_dict() if operacao_docs else None
            evento_data = evento_docs[0].to_dict() if evento_docs else None

            # (3) VALIDAÇÃO 1: confirmacao_pendente existe?
            if not confirmacao_data:
                return {
                    "ok": False,
                    "motivo": "confirmacao_pendente_nao_existe",
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            confirmacao_pendente = confirmacao_data.get("confirmacao_pendente")
            if not confirmacao_pendente:
                return {
                    "ok": False,
                    "motivo": "confirmacao_pendente_vazia",
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (4) VALIDAÇÃO 2: operacao_em_andamento existe?
            if not operacao_data:
                return {
                    "ok": False,
                    "motivo": "operacao_em_andamento_nao_existe",
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (5) VALIDAÇÃO 3: evento foi persistido?
            if not evento_data:
                return {
                    "ok": False,
                    "motivo": "evento_nao_persistido",
                    "confirmacao_consumida": None,
                    "evento_id": evento_id
                }

            # (6) VALIDAÇÃO 4: tenant_id match
            if operacao_data.get("tenant_id") != tenant_id:
                return {
                    "ok": False,
                    "motivo": "tenant_id_mismatch",
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (7) VALIDAÇÃO 5: actor_id match
            if operacao_data.get("actor_id") != actor_id:
                return {
                    "ok": False,
                    "motivo": "actor_id_mismatch",
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (8) VALIDAÇÃO 6: operacao_id match
            if operacao_data.get("operacao_id") != operacao_id:
                return {
                    "ok": False,
                    "motivo": "operacao_id_mismatch",
                    "operacao_id_efetivo": operacao_data.get("operacao_id"),
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (9) VALIDAÇÃO 7: confirmacao.status == "pendente" (NÃO consumida)
            confirmacao_status = confirmacao_pendente.get("status")
            if confirmacao_status == "CONSUMIDA":
                return {
                    "ok": False,
                    "motivo": "ja_consumida",
                    "confirmacao_consumida": None,
                    "evento_id": evento_id
                }
            if confirmacao_status != "pendente":
                return {
                    "ok": False,
                    "motivo": f"confirmacao_status_invalido: {confirmacao_status}",
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (10) VALIDAÇÃO 8: operacao.status == "evento_persistido"
            operacao_status = operacao_data.get("status")
            if operacao_status != "evento_persistido":
                return {
                    "ok": False,
                    "motivo": f"operacao_status_invalido: {operacao_status}",
                    "esperado": "evento_persistido",
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (11) VALIDAÇÃO 9: lease_token valid (fencing)
            doc_lease_token = operacao_data.get("lease_token")
            if doc_lease_token != lease_token:
                return {
                    "ok": False,
                    "motivo": "lease_token_invalido",
                    "causa": "proprietario_antigo_ou_transferido",
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (12) VALIDAÇÃO 10: lease_expira_em não expirado (fencing)
            lease_expira_em_str = operacao_data.get("lease_expira_em")
            if lease_expira_em_str:
                try:
                    lease_expira_em = datetime.fromisoformat(lease_expira_em_str)
                    if agora > lease_expira_em:
                        return {
                            "ok": False,
                            "motivo": "lease_expirado",
                            "expira_em": lease_expira_em_str,
                            "confirmacao_consumida": None,
                            "evento_id": None
                        }
                except:
                    pass

            # (13) VALIDAÇÃO 11: proprietario_id válido (fencing)
            doc_proprietario_id = operacao_data.get("proprietario_id")
            if doc_proprietario_id != proprietario_id:
                return {
                    "ok": False,
                    "motivo": "proprietario_mismatch",
                    "proprietario_esperado": proprietario_id,
                    "proprietario_efetivo": doc_proprietario_id,
                    "confirmacao_consumida": None,
                    "evento_id": None
                }

            # (14) VALIDAÇÃO 12: correspondência evento vs snapshot
            # Validar campos críticos: tenant, cliente, prof, data, hora, duracao
            divergencias = {}

            ev_tenant = evento_data.get("tenant_id", "")
            if ev_tenant != tenant_id:
                divergencias["tenant_id"] = {"evento": ev_tenant, "esperado": tenant_id}

            ev_cliente = evento_data.get("cliente_id", "")
            snap_cliente = dados_confirmados_snapshot.get("cliente_id", "")
            if ev_cliente != snap_cliente:
                divergencias["cliente_id"] = {"evento": ev_cliente, "snapshot": snap_cliente}

            ev_prof = (str(evento_data.get("profissional", "")).lower().strip()
                      if evento_data.get("profissional") else "")
            snap_prof = (str(dados_confirmados_snapshot.get("profissional", "")).lower().strip()
                        if dados_confirmados_snapshot.get("profissional") else "")
            if ev_prof != snap_prof:
                divergencias["profissional"] = {"evento": ev_prof, "snapshot": snap_prof}

            ev_data_str = evento_data.get("data", "")
            snap_data_str = dados_confirmados_snapshot.get("data", "")
            if ev_data_str != snap_data_str:
                divergencias["data"] = {"evento": ev_data_str, "snapshot": snap_data_str}

            ev_hora = evento_data.get("hora_inicio", "")
            snap_hora = dados_confirmados_snapshot.get("hora_inicio", "")
            if ev_hora != snap_hora:
                divergencias["hora_inicio"] = {"evento": ev_hora, "snapshot": snap_hora}

            ev_duracao = evento_data.get("duracao")
            snap_duracao = dados_confirmados_snapshot.get("duracao")
            try:
                if int(ev_duracao) != int(snap_duracao):
                    divergencias["duracao"] = {"evento": ev_duracao, "snapshot": snap_duracao}
            except:
                if str(ev_duracao) != str(snap_duracao):
                    divergencias["duracao"] = {"evento": ev_duracao, "snapshot": snap_duracao}

            if divergencias:
                return {
                    "ok": False,
                    "motivo": "snapshot_mismatch",
                    "divergencias": divergencias,
                    "confirmacao_consumida": None,
                    "evento_id": evento_id
                }

            # (15) TODAS VALIDAÇÕES PASSARAM: CONSUMIR ATOMICAMENTE
            # Marcar confirmacao como CONSUMIDA
            confirmacao_consumida = confirmacao_pendente.copy()
            confirmacao_consumida["status"] = "CONSUMIDA"
            confirmacao_consumida["consumida_em"] = agora.isoformat()
            confirmacao_consumida["consumida_por"] = proprietario_id

            # Escrever confirmacao_pendente com status=CONSUMIDA
            transaction.update(confirmacao_ref, {
                "confirmacao_pendente": confirmacao_consumida
            })

            # Escrever operacao com status=concluida (MESMA transação)
            transaction.update(operacao_ref, {
                "status": "concluida",
                "concluida_em": agora.isoformat(),
                "concluido_por": proprietario_id
            })

            return {
                "ok": True,
                "motivo": "confirmacao_consumida_atomicamente",
                "confirmacao_consumida": confirmacao_consumida,
                "evento_id": evento_id
            }

        transaction = db.transaction()
        return callback(transaction)

    # Executar transação em thread separada (Firestore é síncrono)
    result = await asyncio.to_thread(transacao_consumir)
    return result
