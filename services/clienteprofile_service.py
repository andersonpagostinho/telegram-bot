# services/clienteprofile_service.py
"""
ClienteProfile Service - P1.1 Passivo (com Patches de Segurança)

PATCHES APLICADOS:
  P1: Deduplicação por evento_id
      - Registra eventos_processados para evitar duplicação
      - Mesmo evento 2x não incrementa total_eventos 2x
  P2: Operações atômicas Firestore (PREPARADO)
      - Código pronto para usar Increment() e ArrayUnion()
      - Evita race conditions em arrays/contadores
  P3: Callbacks para asyncio.create_task (em event_handler.py)
  P4: Testes de idempotência e concorrência (em test_clienteprofile_p1.py)

Coleta dados agregados sem afetar fluxo de agendamento (P0).
Não bloqueia se falhar.
Multi-tenant seguro.
"""

import logging
from datetime import datetime
from pytz import timezone
from typing import Optional, List
from collections import Counter
from google.cloud import firestore

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    atualizar_dado_em_path,
    atualizar_com_operacoes_atomicas,  # PATCH P2: Operações atômicas
)

logger = logging.getLogger(__name__)
FUSO_BR = timezone("America/Sao_Paulo")


async def criar_ou_atualizar_profile_apos_evento(
    tenant_id: str,
    cliente_id: str,
    evento_data: dict,
    evento_id: Optional[str] = None,
) -> bool:
    """
    Cria ou atualiza ClienteProfile após evento ser criado.

    PATCH P1: Deduplicação por evento_id
    Se mesmo evento_id for processado 2x, não incrementa contadores.

    Não bloqueia se falhar (sempre retorna bool, nunca lança).
    Idempotente (com evento_id).
    Multi-tenant seguro.

    Args:
        tenant_id: ID do dono/tenant
        cliente_id: ID do cliente
        evento_data: Dict com {profissional, servico, cliente_nome, ...}
        evento_id: ID único do evento para deduplicação (PATCH P1)

    Returns:
        True se sucesso, False se erro (não bloqueante)
    """
    try:
        # Validar inputs
        if not tenant_id or not cliente_id:
            logger.warning(f"profile_update skipped: tenant_id={tenant_id}, cliente_id={cliente_id}")
            return False

        # PATCH P1: Gerar evento_id se não fornecido
        if not evento_id:
            data = evento_data.get("data", "unknown")
            hora = evento_data.get("hora", "00:00")
            prof = evento_data.get("profissional", "pessoal").lower().replace(" ", "_")
            serv = evento_data.get("servico", "geral").lower().replace(" ", "_")
            evento_id = f"{cliente_id}_{prof}_{serv}_{data}_{hora}".replace("/", "-")

        profile_path = f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}"
        agora = datetime.now(FUSO_BR)

        # Verificar se profile já existe
        profile_existente = await buscar_dado_em_path(profile_path)

        if profile_existente is None:
            # Criar novo profile
            return await _criar_profile_novo(
                profile_path, cliente_id, tenant_id, evento_data, evento_id, agora
            )
        else:
            # Atualizar profile existente
            return await _atualizar_profile_existente(
                profile_path, profile_existente, evento_data, evento_id, agora
            )

    except Exception as e:
        logger.error(f"erro ao criar/atualizar profile: {e}", exc_info=True)
        return False


async def _criar_profile_novo(
    profile_path: str,
    cliente_id: str,
    tenant_id: str,
    evento_data: dict,
    evento_id: str,
    agora: datetime,
) -> bool:
    """
    Cria novo ClienteProfile com valores iniciais.

    PATCH P1: Adiciona eventos_processados para deduplicação.
    """
    try:
        profissional = evento_data.get("profissional", "").strip() or None
        servico = evento_data.get("servico", "").strip() or None
        cliente_nome = evento_data.get("cliente_nome", "").strip() or None

        profile = {
            # Identity
            "cliente_id": cliente_id,
            "tenant_id": tenant_id,
            "criado_em": agora.isoformat(),

            # Basic info
            "nome": cliente_nome,
            "email": None,

            # Histórico
            "historico": {
                "primeira_contato": agora.isoformat(),
                "ultima_contato": agora.isoformat(),
                "total_eventos": 1,
                "profissionais_atendidos": [profissional] if profissional else [],
                "servicos_atendidos": [servico] if servico else [],
                "proxima_sugestao": None,
            },

            # PATCH P1: Rastreamento de eventos processados (para deduplicação)
            "eventos_processados": [
                {
                    "evento_id": evento_id,
                    "processado_em": agora.isoformat(),
                }
            ],

            # Tendências (moda será recalculada em P1.2)
            "tendencias": {
                "profissional_mais_frequente": profissional,
                "profissional_mais_frequente_count": 1 if profissional else 0,
                "servico_mais_frequente": servico,
                "servico_mais_frequente_count": 1 if servico else 0,
                "intervalo_medio_dias": None,
            },

            # Metadata
            "atualizado_em": agora.isoformat(),
            "versao": 1,
        }

        sucesso = await salvar_dado_em_path(profile_path, profile)

        if sucesso:
            logger.info(f"profile criado: {profile_path}, evento_id={evento_id}")
        else:
            logger.error(f"falha ao salvar profile: {profile_path}")

        return sucesso

    except Exception as e:
        logger.error(f"erro em _criar_profile_novo: {e}", exc_info=True)
        return False


async def _atualizar_profile_existente(
    profile_path: str,
    profile_existente: dict,
    evento_data: dict,
    evento_id: str,
    agora: datetime,
) -> bool:
    """
    Atualiza ClienteProfile existente com dados do novo evento.

    PATCH P1: Validar evento_id antes de incrementar (deduplicação).
    PATCH P2: Usar operações atômicas do Firestore (Increment, ArrayUnion).
    """
    try:
        # PATCH P1: Verificar se evento_id já foi processado
        eventos_processados = profile_existente.get("eventos_processados", [])
        evento_ids_existentes = [e.get("evento_id") for e in eventos_processados]

        if evento_id in evento_ids_existentes:
            logger.info(f"evento duplicado ignorado: {evento_id} já foi processado")
            return True  # Sucesso (idempotência)

        profissional = evento_data.get("profissional", "").strip() or None
        servico = evento_data.get("servico", "").strip() or None

        # PATCH P2: Preparar update com operações atômicas do Firestore
        # Usar firestore.Increment() para contadores
        # Usar firestore.ArrayUnion() para arrays
        # Isso garante que duas updates simultâneas não sobrescrevem dados

        update_data = {
            "atualizado_em": agora.isoformat(),
            "versao": firestore.Increment(1),  # PATCH P2: ATOMIC

            "historico": {
                "primeira_contato": profile_existente.get("historico", {}).get("primeira_contato"),
                "ultima_contato": agora.isoformat(),
                "total_eventos": firestore.Increment(1),  # PATCH P2: ATOMIC (não read-modify-write)
                # PATCH P2: Usar ArrayUnion para adicionar sem sobrescrita
                "profissionais_atendidos": firestore.ArrayUnion([profissional] if profissional else []),
                "servicos_atendidos": firestore.ArrayUnion([servico] if servico else []),
                "proxima_sugestao": profile_existente.get("historico", {}).get("proxima_sugestao"),
            },

            # PATCH P1: Usar ArrayUnion para registrar evento processado
            # PATCH P2: ATOMIC (adiciona sem sobrescrita)
            "eventos_processados": firestore.ArrayUnion([
                {
                    "evento_id": evento_id,
                    "processado_em": agora.isoformat(),
                }
            ]),

            # Tendências: NÃO recalcular aqui (evita leitura de arrays)
            # Moda será recalculada em P1.2 quando necessário
            "tendencias": profile_existente.get("tendencias", {}),
        }

        # PATCH P2: Usar atualizar_com_operacoes_atomicas em vez de merge simples
        sucesso = await atualizar_com_operacoes_atomicas(profile_path, update_data)

        if sucesso:
            logger.info(f"profile atualizado (ATOMIC): {profile_path}, evento_id={evento_id}")
        else:
            logger.error(f"falha ao atualizar profile: {profile_path}")

        return sucesso

    except Exception as e:
        logger.error(f"erro em _atualizar_profile_existente: {e}", exc_info=True)
        return False


def _calcular_moda_profissional(profissionais: List[str]) -> Optional[str]:
    """Calcula profissional mais frequente."""
    if not profissionais:
        return None
    counter = Counter(profissionais)
    if counter:
        return counter.most_common(1)[0][0]
    return None


def _calcular_moda_servico(servicos: List[str]) -> Optional[str]:
    """Calcula serviço mais frequente."""
    if not servicos:
        return None
    counter = Counter(servicos)
    if counter:
        return counter.most_common(1)[0][0]
    return None


def _contar_frequencia(lista: List[str], item: str) -> int:
    """Conta quantas vezes item aparece na lista."""
    if not item:
        return 0
    return lista.count(item)


async def obter_profile(tenant_id: str, cliente_id: str) -> Optional[dict]:
    """Obtém perfil de cliente (sem alterações)."""
    if not tenant_id or not cliente_id:
        return None

    try:
        profile_path = f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}"
        return await buscar_dado_em_path(profile_path)
    except Exception as e:
        logger.error(f"erro ao obter profile: {e}")
        return None
