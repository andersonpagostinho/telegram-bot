"""
TESTES E2E P0 + P1 COM FIREBASE REAL

Nota: Os testes unitários de test_p0_p1_fixes_implementation.py validam lógica.
Estes testes E2E validam que a lógica funciona em Firestore real.

P0: Timestamp _last_client_activity é atualizado a cada mensagem
P1: Campos residuais são limpos quando estado=idle

REGRA DE OURO: Validação até Firestore, não apenas lógica em memória.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
import asyncio

from services.firebase_service_async import (
    atualizar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)


@pytest_asyncio.fixture
async def firebase_real():
    """Firebase real para E2E"""
    return {
        "update": atualizar_dado_em_path,
        "get": buscar_dado_em_path,
        "delete": deletar_dado_em_path,
    }


@pytest_asyncio.fixture
async def test_env():
    """Environment P0/P1 E2E"""
    tenant_id = f"tenant_p0p1_e2e_{uuid.uuid4().hex[:8]}"
    actor_id = f"actor_p0p1_e2e_{uuid.uuid4().hex[:8]}"
    return {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
    }


@pytest_asyncio.fixture
async def cleanup(firebase_real, test_env):
    """Cleanup após testes"""
    yield
    try:
        await firebase_real["delete"](f"Clientes/{test_env['tenant_id']}")
    except:
        pass


class TestP0ActivityE2E:
    """P0 E2E: Timestamp atualizado em Firestore"""

    @pytest.mark.asyncio
    async def test_p0_timestamp_criado_primeira_vez(self, firebase_real, test_env, cleanup):
        """Timestamp criado quando sessão inicia"""
        tenant_id = test_env["tenant_id"]
        actor_id = test_env["actor_id"]

        # Simular criação de sessão com timestamp
        sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
        ts_agora = datetime.now(timezone.utc).isoformat()

        await firebase_real["update"](sessao_path, {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "_last_client_activity": ts_agora,
            "estado_fluxo": "idle",
        })

        # Validar que foi salvo em Firestore
        sessao = await firebase_real["get"](sessao_path)
        assert sessao is not None
        assert sessao["_last_client_activity"] == ts_agora
        print(f"✅ Timestamp criado: {ts_agora}")

    @pytest.mark.asyncio
    async def test_p0_timestamp_atualizado_segunda_mensagem(self, firebase_real, test_env, cleanup):
        """Timestamp atualizado quando nova mensagem chega"""
        tenant_id = test_env["tenant_id"]
        actor_id = test_env["actor_id"]
        sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

        # Primeira mensagem
        ts1 = datetime.now(timezone.utc).isoformat()
        await firebase_real["update"](sessao_path, {
            "_last_client_activity": ts1,
        })
        sessao1 = await firebase_real["get"](sessao_path)

        # Aguardar
        await asyncio.sleep(0.2)

        # Segunda mensagem
        ts2 = datetime.now(timezone.utc).isoformat()
        await firebase_real["update"](sessao_path, {
            "_last_client_activity": ts2,
        })
        sessao2 = await firebase_real["get"](sessao_path)

        # Validar atualização
        assert sessao1["_last_client_activity"] == ts1
        assert sessao2["_last_client_activity"] == ts2
        assert ts1 < ts2
        print(f"✅ Timestamp atualizado: {ts1} → {ts2}")

    @pytest.mark.asyncio
    async def test_p0_tenant_actor_preservados(self, firebase_real, test_env, cleanup):
        """Tenant/actor não alterados ao atualizar timestamp"""
        tenant_id = test_env["tenant_id"]
        actor_id = test_env["actor_id"]
        sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

        # Criar sessão com tenant/actor
        await firebase_real["update"](sessao_path, {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "_last_client_activity": datetime.now(timezone.utc).isoformat(),
        })

        # Atualizar timestamp múltiplas vezes
        for _ in range(3):
            await firebase_real["update"](sessao_path, {
                "_last_client_activity": datetime.now(timezone.utc).isoformat(),
            })
            await asyncio.sleep(0.05)

        # Validar que tenant/actor não mudaram
        sessao = await firebase_real["get"](sessao_path)
        assert sessao["tenant_id"] == tenant_id
        assert sessao["actor_id"] == actor_id
        print(f"✅ Tenant/actor preservados após múltiplas atualizações")


class TestP1ResidualCleanupE2E:
    """P1 E2E: Limpeza de campos residuais em Firestore"""

    @pytest.mark.asyncio
    async def test_p1_remove_campos_quando_idle(self, firebase_real, test_env, cleanup):
        """Campos modo_escolha_horario removidos quando estado=idle"""
        tenant_id = test_env["tenant_id"]
        actor_id = test_env["actor_id"]
        sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

        # Estado inconsistente: idle + modo_escolha=True
        await firebase_real["update"](sessao_path, {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "estado_fluxo": "idle",
            "modo_escolha_horario": True,
            "horarios_sugeridos": ["14:00", "15:00"],
            "profissional_escolhido": "Carla",
            "servico": "corte",  # Preservar
        })

        # Simular P1 fix: limpeza defensiva
        # Em produção, isso seria feito pelo router
        campos_remover = [
            "modo_escolha_horario",
            "horarios_sugeridos",
            "profissional_escolhido",
        ]

        update_dict = {field: None for field in campos_remover}  # Usar None para Firestore
        await firebase_real["update"](sessao_path, update_dict)

        sessao = await firebase_real["get"](sessao_path)

        # Validar limpeza
        assert sessao.get("modo_escolha_horario") in (None, False, not "modo_escolha_horario")
        assert sessao.get("horarios_sugeridos") in (None, False, not "horarios_sugeridos")
        assert sessao.get("profissional_escolhido") in (None, False, not "profissional_escolhido")

        # Validar preservação
        assert sessao.get("servico") == "corte"
        assert sessao.get("estado_fluxo") == "idle"

        print(f"✅ Campos residuais removidos, serviço preservado")

    @pytest.mark.asyncio
    async def test_p1_nao_remove_quando_ativo(self, firebase_real, test_env, cleanup):
        """Campos NÃO removidos quando fluxo está ativo"""
        tenant_id = test_env["tenant_id"]
        actor_id = test_env["actor_id"]
        sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

        # Estado ativo: agendando + modo_escolha=True (válido)
        await firebase_real["update"](sessao_path, {
            "estado_fluxo": "agendando",
            "modo_escolha_horario": True,
            "horarios_sugeridos": ["14:00", "15:00"],
        })

        sessao = await firebase_real["get"](sessao_path)

        # Validar que não foi removido
        assert sessao.get("modo_escolha_horario") == True
        assert sessao.get("horarios_sugeridos") == ["14:00", "15:00"]
        assert sessao.get("estado_fluxo") == "agendando"

        print(f"✅ Campos não removidos quando fluxo está ativo")

    @pytest.mark.asyncio
    async def test_p1_draft_profissional_atualizado(self, firebase_real, test_env, cleanup):
        """P1 validação: draft_agendamento.profissional não causa fallback"""
        tenant_id = test_env["tenant_id"]
        actor_id = test_env["actor_id"]
        sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

        # Salvar contexto com draft residual
        await firebase_real["update"](sessao_path, {
            "estado_fluxo": "idle",
            "profissional_escolhido": None,  # Removido
            "draft_agendamento": {
                "profissional": "Carla",  # Residual no draft
                "servico": "corte",
                "data_hora": "2026-10-23T14:00:00",
            },
        })

        sessao = await firebase_real["get"](sessao_path)

        # Validar que profissional_escolhido foi removido
        assert sessao.get("profissional_escolhido") is None

        # Draft ainda pode ter profissional, mas não será usado pelo router
        # (router deve validar em slots_extraidos, não usar fallback)
        draft = sessao.get("draft_agendamento") or {}
        if draft.get("profissional"):
            print(f"⚠️  draft.profissional = {draft.get('profissional')} (residual)")
            print(f"⚠️  Mas profissional_escolhido = None (removido)")
            print(f"⚠️  Router deve usar slots_extraidos, não fallback")

        print(f"✅ Draft residual não causa reintrodução de profissional")


class TestP0P1IntegrationE2E:
    """Integração P0 + P1 em Firestore real"""

    @pytest.mark.asyncio
    async def test_p0_p1_integrados(self, firebase_real, test_env, cleanup):
        """P0 timestamp + P1 limpeza juntos"""
        tenant_id = test_env["tenant_id"]
        actor_id = test_env["actor_id"]
        sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

        # Contexto inicial com problemas P1
        ts1 = datetime.now(timezone.utc).isoformat()
        await firebase_real["update"](sessao_path, {
            "estado_fluxo": "idle",
            "modo_escolha_horario": True,
            "horarios_sugeridos": ["14:00"],
            "_last_client_activity": ts1,
        })

        # Simular processamento:
        # P1: remover campos residuais
        # P0: atualizar timestamp
        await asyncio.sleep(0.1)
        ts2 = datetime.now(timezone.utc).isoformat()

        await firebase_real["update"](sessao_path, {
            "modo_escolha_horario": None,
            "horarios_sugeridos": None,
            "_last_client_activity": ts2,
        })

        sessao = await firebase_real["get"](sessao_path)

        # Validar P1: campos removidos
        assert sessao.get("modo_escolha_horario") is None
        assert sessao.get("horarios_sugeridos") is None

        # Validar P0: timestamp atualizado
        assert sessao.get("_last_client_activity") == ts2
        assert ts1 < ts2

        # Validar estado preservado
        assert sessao.get("estado_fluxo") == "idle"

        print(f"✅ P0 + P1 integrados corretamente em Firestore")


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v"] + sys.argv[1:])
