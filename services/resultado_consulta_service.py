"""
Serviço de Persistência para Resultado de Consulta Multisserviço

Responsabilidade:
- Persistir resultado da consulta no Firestore
- Recuperar com validação de TTL
- Limpar APENAS contexto_resultado_consulta (preservar resto da sessão)
- Garantir isolamento tenant/actor
"""

from schemas.resultado_consulta_schema import ContextoResultadoConsulta
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
)
from datetime import datetime
from typing import Optional
from google.cloud import firestore


async def persistir_resultado_consulta(
    tenant_id: str,
    actor_id: str,
    contexto: ContextoResultadoConsulta
) -> bool:
    """
    Persistir resultado da consulta em Firestore.

    Path: Clientes/{tenant_id}/Sessoes/{actor_id}
    Campo: contexto_resultado_consulta

    Requerimentos de segurança:
    - Rejeitar se tenant_id vazio
    - Rejeitar se actor_id vazio
    - Não aceitar fallback para valores legados
    - Nova consulta substitui a anterior

    Returns:
        True se sucesso, False se falha
    """

    # Validação de segurança: tenant_id obrigatório
    if not tenant_id or not isinstance(tenant_id, str) or tenant_id.strip() == "":
        print(f"[PERSIST_RESULTADO] ❌ SEGURANÇA: tenant_id inválido (vazio ou tipo incorreto)", flush=True)
        return False

    # Validação de segurança: actor_id obrigatório
    if not actor_id or not isinstance(actor_id, str) or actor_id.strip() == "":
        print(f"[PERSIST_RESULTADO] ❌ SEGURANÇA: actor_id inválido (vazio ou tipo incorreto)", flush=True)
        return False

    try:
        # Path para sessão
        path = f"Clientes/{tenant_id.strip()}/Sessoes/{actor_id.strip()}"

        # Dados a persistir (merge: atualiza apenas este campo)
        data_to_save = {
            "contexto_resultado_consulta": contexto.to_dict()
        }

        print(f"[PERSIST_RESULTADO] 💾 Persistindo resultado", flush=True)
        print(f"   - Tenant: {tenant_id}", flush=True)
        print(f"   - Actor: {actor_id}", flush=True)
        print(f"   - Opções: {len(contexto.opcoes)}", flush=True)
        print(f"   - TTL: {contexto.expira_em}", flush=True)

        # Usar merge=True para não sobrescrever outros campos da sessão
        resultado = await salvar_dado_em_path(path, data_to_save)

        if resultado:
            print(f"[PERSIST_RESULTADO] ✅ Resultado persistido com sucesso", flush=True)
            return True
        else:
            print(f"[PERSIST_RESULTADO] ❌ Falha ao persistir (salvar_dado_em_path retornou False)", flush=True)
            return False

    except Exception as e:
        print(f"[PERSIST_RESULTADO] ❌ EXCEÇÃO: {type(e).__name__}: {str(e)[:100]}", flush=True)
        return False


async def recuperar_resultado_consulta(
    tenant_id: str,
    actor_id: str
) -> Optional[ContextoResultadoConsulta]:
    """
    Recuperar resultado da consulta do Firestore.

    Valida TTL automaticamente durante leitura (não aguarda limpeza agendada).

    Path: Clientes/{tenant_id}/Sessoes/{actor_id}
    Campo: contexto_resultado_consulta

    Requerimentos de segurança:
    - Rejeitar se tenant_id vazio
    - Rejeitar se actor_id vazio
    - Não aceitar fallback
    - Retornar None se expirado (não recuperar)

    Returns:
        ContextoResultadoConsulta se válido e dentro de TTL
        None se não existe, expirado, ou erro
    """

    # Validação de segurança: tenant_id obrigatório
    if not tenant_id or not isinstance(tenant_id, str) or tenant_id.strip() == "":
        print(f"[RECUPERAR_RESULTADO] ❌ SEGURANÇA: tenant_id inválido (vazio ou tipo incorreto)", flush=True)
        return None

    # Validação de segurança: actor_id obrigatório
    if not actor_id or not isinstance(actor_id, str) or actor_id.strip() == "":
        print(f"[RECUPERAR_RESULTADO] ❌ SEGURANÇA: actor_id inválido (vazio ou tipo incorreto)", flush=True)
        return None

    try:
        path = f"Clientes/{tenant_id.strip()}/Sessoes/{actor_id.strip()}"

        print(f"[RECUPERAR_RESULTADO] 📖 Recuperando resultado", flush=True)
        print(f"   - Tenant: {tenant_id}", flush=True)
        print(f"   - Actor: {actor_id}", flush=True)

        # Recuperar documento
        data = await buscar_dado_em_path(path)

        if data is None:
            print(f"[RECUPERAR_RESULTADO] ℹ️  Documento não encontrado", flush=True)
            return None

        if "contexto_resultado_consulta" not in data:
            print(f"[RECUPERAR_RESULTADO] ℹ️  Campo contexto_resultado_consulta não existe (primeira vez)", flush=True)
            return None

        ctx_dict = data["contexto_resultado_consulta"]

        # Desserializar
        contexto = ContextoResultadoConsulta.from_dict(ctx_dict)

        # Validar TTL (crítico: fazer durante leitura)
        if contexto.esta_expirado():
            print(f"[RECUPERAR_RESULTADO] ⚠️  Contexto expirado (criado em {contexto.criado_em})", flush=True)
            # Não recuperar contexto expirado
            # Nota: limpeza é responsabilidade da próxima persistência ou cron
            return None

        print(f"[RECUPERAR_RESULTADO] ✅ Contexto recuperado ({len(contexto.opcoes)} opções válidas)", flush=True)
        print(f"   - Profissional: {contexto.profissional_id}", flush=True)
        print(f"   - Serviços: {', '.join(contexto.servicos)}", flush=True)
        print(f"   - Expira em: {contexto.expira_em}", flush=True)

        return contexto

    except Exception as e:
        print(f"[RECUPERAR_RESULTADO] ❌ EXCEÇÃO: {type(e).__name__}: {str(e)[:100]}", flush=True)
        return None


async def limpar_resultado_consulta(
    tenant_id: str,
    actor_id: str
) -> bool:
    """
    Remover APENAS campo contexto_resultado_consulta, preservando resto da sessão.

    Usa DELETE_FIELD do Firestore para remover atomicamente apenas este campo.

    Path: Clientes/{tenant_id}/Sessoes/{actor_id}
    Campo: contexto_resultado_consulta

    Requerimentos de segurança:
    - Rejeitar se tenant_id vazio
    - Rejeitar se actor_id vazio
    - NUNCA limpar toda a sessão (usar DELETE_FIELD em vez de delete documento)

    Returns:
        True se sucesso ou campo já não existia
        False se falha real
    """

    # Validação de segurança
    if not tenant_id or not isinstance(tenant_id, str) or tenant_id.strip() == "":
        print(f"[LIMPAR_RESULTADO] ❌ SEGURANÇA: tenant_id inválido", flush=True)
        return False

    if not actor_id or not isinstance(actor_id, str) or actor_id.strip() == "":
        print(f"[LIMPAR_RESULTADO] ❌ SEGURANÇA: actor_id inválido", flush=True)
        return False

    try:
        from services.firebase_service_async import get_async_client

        path = f"Clientes/{tenant_id.strip()}/Sessoes/{actor_id.strip()}"

        print(f"[LIMPAR_RESULTADO] 🗑️  Removendo apenas contexto_resultado_consulta", flush=True)
        print(f"   - Tenant: {tenant_id}", flush=True)
        print(f"   - Actor: {actor_id}", flush=True)
        print(f"   - Preservando: resto dos campos da sessão", flush=True)

        # Obter referência ao documento
        ref = get_async_client().document(path)

        # Usar DELETE_FIELD para remover APENAS este campo
        await ref.update({
            "contexto_resultado_consulta": firestore.DELETE_FIELD
        })

        print(f"[LIMPAR_RESULTADO] ✅ Removido com sucesso (DELETE_FIELD)", flush=True)
        return True

    except Exception as e:
        print(f"[LIMPAR_RESULTADO] ❌ EXCEÇÃO: {type(e).__name__}: {str(e)[:100]}", flush=True)
        return False


async def invalidar_resultado_consulta_se_novo_agendamento(
    tenant_id: str,
    actor_id: str
) -> None:
    """
    Helper: Limpar resultado quando novo agendamento iniciado.

    Garante que seleção anterior ("o primeiro") não se aplica a novo contexto.
    """
    await limpar_resultado_consulta(tenant_id, actor_id)

