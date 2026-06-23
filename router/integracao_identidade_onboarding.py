# -*- coding: utf-8 -*-
# router/integracao_identidade_onboarding.py
"""
Integração de Identidade por Canal + Onboarding Automático

Responsabilidades:
1. Resolver ator por canal (dono, profissional, cliente)
2. Aplicar validações de guard forte (tenant_id, tipo_usuario, onboarding)
3. Direcionar para onboarding_dono se necessário
4. Criar cliente automático no primeiro contato

Não altera: motor de agenda, conflito, notificações, cancelamento
"""

from services.identidade_service import (
    normalizar_actor_id,
    resolver_ator_por_canal,
    criar_ator_cliente_automatico,
    criar_ator_dono,
    tenant_tem_dono,
    roteador_por_tipo_usuario,
)
from services.onboarding_dono_service import (
    validar_onboarding_minimo,
    pegar_etapa_onboarding,
    obter_pergunta_etapa,
)
from services.firebase_service_async import obter_id_dono
from utils.contexto_temporario import salvar_contexto_temporario_v2 as salvar_contexto_temporario


async def resolver_ator_e_validar_guard(
    user_id: str,
    tenant_id: str,
    canal: str = "whatsapp",
    identificador: str = None,
    ctx: dict = None,
) -> dict:
    """
    Resolve ator por canal e aplica validações de guard forte.

    Returns:
        {
            "sucesso": bool,
            "tipo_usuario": "dono" | "profissional" | "cliente" | None,
            "actor_id": str,
            "ator": dict (dados do ator),
            "requer_onboarding": bool,
            "erro": str (se sucesso=False),
            "proxima_acao": str ("onboarding" | "normal" | "criar_cliente")
        }
    """
    ctx = ctx or {}

    # Guard 1: tenant_id obrigatório
    if not tenant_id:
        return {
            "sucesso": False,
            "tipo_usuario": None,
            "error": "tenant_id ausente — falha segura",
            "proxima_acao": "falha_segura"
        }

    # Guard 2: Normalizar actor_id
    identificador = identificador or user_id
    try:
        actor_id = normalizar_actor_id(canal, identificador)
    except Exception as e:
        return {
            "sucesso": False,
            "tipo_usuario": None,
            "error": f"Erro ao normalizar actor_id: {e}",
            "proxima_acao": "falha_segura"
        }

    # Passo 1: Resolver ator existente
    ator_existente = await resolver_ator_por_canal(
        tenant_id=tenant_id,
        canal=canal,
        identificador=identificador
    )

    if ator_existente:
        # Ator encontrado — validar tipo_usuario
        tipo_usuario = ator_existente.get("tipo_usuario")
        permissoes = ator_existente.get("permissoes", [])

        # Guard 3: Se dono, validar onboarding
        if tipo_usuario == "dono":
            onboarding_status = ator_existente.get("onboarding_status", "nao_iniciado")

            # Validar onboarding mínimo
            try:
                validacao_onboarding = await validar_onboarding_minimo(tenant_id)
                onboarding_completo = validacao_onboarding.get("valido", False)
            except Exception as e:
                print(f"[AVISO] Erro ao validar onboarding mínimo: {e}", flush=True)
                onboarding_completo = False

            if not onboarding_completo:
                # Dono sem onboarding — obter próxima etapa
                try:
                    etapa_info = await pegar_etapa_onboarding(tenant_id)
                    proxima_etapa = etapa_info.get("etapa_atual", "nome_negocio") if etapa_info else "nome_negocio"
                    proxima_pergunta = obter_pergunta_etapa(proxima_etapa)
                except Exception as e:
                    print(f"[AVISO] Erro ao obter etapa: {e}", flush=True)
                    proxima_etapa = "nome_negocio"
                    proxima_pergunta = "Qual é o nome do seu negócio?"

                return {
                    "sucesso": True,
                    "tipo_usuario": "dono",
                    "actor_id": actor_id,
                    "ator": ator_existente,
                    "requer_onboarding": True,
                    "onboarding_etapa": proxima_etapa,
                    "onboarding_pergunta": proxima_pergunta,
                    "proxima_acao": "onboarding"
                }

        # Guard 4: Se profissional, confirmar permissões operacionais
        elif tipo_usuario == "profissional":
            if "operacional" not in permissoes:
                return {
                    "sucesso": False,
                    "tipo_usuario": "profissional",
                    "error": "Profissional sem permissão operacional",
                    "proxima_acao": "falha_segura"
                }

        # Ator válido — retornar sucesso
        return {
            "sucesso": True,
            "tipo_usuario": tipo_usuario,
            "actor_id": actor_id,
            "ator": ator_existente,
            "requer_onboarding": False,
            "permissoes": permissoes,
            "proxima_acao": "normal"
        }

    else:
        # Ator não encontrado — aplicar regra determinística
        # Se tenant NÃO tem dono: primeiro actor_id vira DONO
        # Se tenant TEM dono: actor_id vira CLIENTE automático

        # Verificar se tenant possui dono
        tem_dono = await tenant_tem_dono(tenant_id)

        if not tem_dono:
            # Primeiro acesso do tenant — criar DONO
            try:
                ator_novo = await criar_ator_dono(
                    tenant_id=tenant_id,
                    canal=canal,
                    identificador=identificador,
                    nome="Proprietário",  # Nome padrão até onboarding
                    email="nao_informado@sistema.local"
                )

                # Iniciar onboarding
                try:
                    etapa_info = await pegar_etapa_onboarding(tenant_id)
                    proxima_etapa = etapa_info.get("etapa_atual", "nome_negocio") if etapa_info else "nome_negocio"
                    proxima_pergunta = obter_pergunta_etapa(proxima_etapa)
                except Exception as e:
                    print(f"[AVISO] Erro ao iniciar onboarding: {e}", flush=True)
                    proxima_etapa = "nome_negocio"
                    proxima_pergunta = "Qual é o nome do seu negócio?"

                return {
                    "sucesso": True,
                    "tipo_usuario": "dono",
                    "actor_id": actor_id,
                    "ator": ator_novo,
                    "requer_onboarding": True,
                    "onboarding_etapa": proxima_etapa,
                    "onboarding_pergunta": proxima_pergunta,
                    "proxima_acao": "onboarding",
                    "note": "Primeiro acesso: DONO criado e onboarding iniciado"
                }
            except Exception as e:
                print(f"[ERRO] Falha ao criar dono: {e}", flush=True)
                return {
                    "sucesso": False,
                    "tipo_usuario": None,
                    "error": f"Falha ao criar dono: {e}",
                    "proxima_acao": "falha_segura"
                }
        else:
            # Tenant já tem dono — criar CLIENTE automático
            try:
                ator_novo = await criar_ator_cliente_automatico(
                    tenant_id=tenant_id,
                    canal=canal,
                    identificador=identificador,
                    nome_detectado=""  # Será preenchido durante onboarding
                )

                return {
                    "sucesso": True,
                    "tipo_usuario": "cliente",
                    "actor_id": actor_id,
                    "ator": ator_novo,
                    "requer_onboarding": False,
                    "proxima_acao": "normal",
                    "note": "Cliente criado automaticamente"
                }
            except Exception as e:
                print(f"[ERRO] Falha ao criar cliente automático: {e}", flush=True)
                return {
                    "sucesso": False,
                    "tipo_usuario": None,
                    "error": f"Falha ao criar cliente: {e}",
                    "proxima_acao": "falha_segura"
                }


async def processar_fluxo_identidade_onboarding(
    user_id: str,
    mensagem: str,
    tenant_id: str,
    ctx: dict = None,
    context=None,
) -> dict | None:
    """
    Processa fluxo de identidade e onboarding.

    Se retornar dict, significa que a mensagem foi processada e não deve
    continuar no fluxo P0.

    Se retornar None, continua no fluxo P0 normal.
    """
    ctx = ctx or {}

    # Resolver ator e validar guard
    resultado_guard = await resolver_ator_e_validar_guard(
        user_id=user_id,
        tenant_id=tenant_id,
        canal="whatsapp",
        identificador=user_id,
        ctx=ctx
    )

    if not resultado_guard.get("sucesso"):
        # Falha segura
        error_msg = resultado_guard.get("error", "Erro ao resolver identidade")
        print(f"[ERRO] {error_msg}", flush=True)

        return {
            "handled": True,
            "resposta": f"❌ Erro ao processar sua identidade. Por favor, tente novamente.",
            "motivo": "falha_identidade"
        }

    # Atualizar contexto com informações do ator
    ctx.update({
        "actor_id": resultado_guard.get("actor_id"),
        "tipo_usuario": resultado_guard.get("tipo_usuario"),
        "permissoes": resultado_guard.get("permissoes", []),
        "tenant_id": tenant_id,
    })

    # Passo 1: Se dono sem onboarding, direcionar para onboarding_dono
    if resultado_guard.get("proxima_acao") == "onboarding":
        ctx.update({
            "estado_fluxo": "onboarding_dono",
            "onboarding_etapa": resultado_guard.get("onboarding_etapa"),
        })

        await salvar_contexto_temporario(tenant_id, user_id, ctx)

        proxima_pergunta = resultado_guard.get("onboarding_pergunta", "Qual é o nome do seu negócio?")

        return {
            "handled": True,
            "resposta": f"🎯 Vamos completar o cadastro do seu negócio?\n\n{proxima_pergunta}",
            "motivo": "onboarding_iniciado"
        }

    # Passo 2: Se cliente novo, confirmar criação
    if resultado_guard.get("note") == "Cliente criado automaticamente":
        ctx.update({
            "tipo_usuario": "cliente",
            "estado_fluxo": "idle"
        })

        await salvar_contexto_temporario(tenant_id, user_id, ctx)

        print(f"[OK] Cliente criado automaticamente: {resultado_guard.get('actor_id')}", flush=True)

    # Passo 3: Continuar no fluxo P0 normal
    await salvar_contexto_temporario(tenant_id, user_id, ctx)
    return None
