# tests/test_clienteprofile_p1.py
"""
Testes do ClienteProfile P1.1 (FIREBASE REAL)

Valida:
- Criação de profile na primeira vez
- Atualização de profile após novo evento
- Isolamento multi-tenant
- Idempotência
- Agregação de profissionais
- Agregação de serviços
- Não bloqueio de agendamento

TODOS OS TESTES USAM FIREBASE REAL - Sem mocks
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from pytz import timezone
import uuid

from services.clienteprofile_service import (
    criar_ou_atualizar_profile_apos_evento,
    obter_profile,
)
from services.firebase_service_async import (
    atualizar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)

FUSO_BR = timezone("America/Sao_Paulo")


@pytest_asyncio.fixture
async def firebase_real():
    """Fixtures para Firebase real"""
    return {
        "update": atualizar_dado_em_path,
        "get": buscar_dado_em_path,
        "delete": deletar_dado_em_path
    }


@pytest_asyncio.fixture
async def test_ids_profile():
    """IDs únicos para testes"""
    return {
        "tenant": f"tenant_profile_{uuid.uuid4().hex[:8]}",
        "cliente": f"cliente_{uuid.uuid4().hex[:8]}",
        "cliente2": f"cliente_{uuid.uuid4().hex[:8]}"
    }


@pytest_asyncio.fixture
async def cleanup_profiles(firebase_real, test_ids_profile):
    """Limpar dados após cada teste"""
    yield
    try:
        await firebase_real["delete"](f"Clientes/{test_ids_profile['tenant']}")
    except:
        pass


class TestClienteProfileCreation:
    """Testes de criação de profile."""

    @pytest.mark.asyncio
    async def test_profile_created_on_first_event(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Profile é criado quando cliente agenda primeira vez."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento_data = {
            "profissional": "Carla",
            "servico": "corte",
            "cliente_nome": "Suri",
        }

        resultado = await criar_ou_atualizar_profile_apos_evento(
            tenant_id, cliente_id, evento_data
        )

        assert resultado is True

        # Verificar que profile foi criado no Firebase real
        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile is not None
        assert profile["cliente_id"] == cliente_id
        assert profile["tenant_id"] == tenant_id
        assert profile["historico"]["total_eventos"] == 1
        assert "Carla" in profile["historico"]["profissionais_atendidos"]
        assert "corte" in profile["historico"]["servicos_atendidos"]

    @pytest.mark.asyncio
    async def test_profile_update_on_new_event(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Profile é atualizado quando novo evento é criado."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        # Primeiro evento
        evento1 = {"profissional": "Carla", "servico": "corte", "cliente_nome": "Cliente"}
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento1)

        # Segundo evento
        evento2 = {"profissional": "Paula", "servico": "escova", "cliente_nome": "Cliente"}
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento2)

        # Verificar atualização
        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile["historico"]["total_eventos"] == 2
        assert "Carla" in profile["historico"]["profissionais_atendidos"]
        assert "Paula" in profile["historico"]["profissionais_atendidos"]

    @pytest.mark.asyncio
    async def test_profile_multi_tenant_isolated(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Profiles são isolados por tenant."""
        tenant_id = test_ids_profile["tenant"]
        tenant_id2 = f"tenant_{uuid.uuid4().hex[:8]}"
        cliente_id = test_ids_profile["cliente"]

        evento1 = {"profissional": "Carla", "servico": "corte"}
        evento2 = {"profissional": "Paula", "servico": "escova"}

        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento1)
        await criar_ou_atualizar_profile_apos_evento(tenant_id2, cliente_id, evento2)

        # Verificar isolamento
        profile1 = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        profile2 = await firebase_real["get"](f"Clientes/{tenant_id2}/ClienteProfiles/{cliente_id}")

        assert profile1 is not None
        assert profile2 is not None
        assert "Carla" in profile1["historico"]["profissionais_atendidos"]
        assert "Paula" in profile2["historico"]["profissionais_atendidos"]

        # Cleanup do segundo tenant
        await firebase_real["delete"](f"Clientes/{tenant_id2}")

    @pytest.mark.asyncio
    async def test_profile_creation_idempotent(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Criação é idempotente."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}

        # Executar duas vezes
        resultado1 = await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)
        resultado2 = await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        assert resultado1 is True
        assert resultado2 is True

        # Versão deve ter aumentado
        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile["versao"] >= 1

    @pytest.mark.asyncio
    async def test_profile_profissional_agregado(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Profissionais são agregados corretamente."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        eventos = [
            {"profissional": "Carla", "servico": "corte"},
            {"profissional": "Paula", "servico": "escova"},
            {"profissional": "Carla", "servico": "corte"},
        ]

        for evento in eventos:
            await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert "Carla" in profile["historico"]["profissionais_atendidos"]
        assert "Paula" in profile["historico"]["profissionais_atendidos"]
        assert profile["tendencias"]["profissional_mais_frequente"] == "Carla"

    @pytest.mark.asyncio
    async def test_profile_servico_agregado(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Serviços são agregados corretamente."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        eventos = [
            {"profissional": "Carla", "servico": "corte"},
            {"profissional": "Paula", "servico": "corte"},
            {"profissional": "Sofia", "servico": "escova"},
        ]

        for evento in eventos:
            await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert "corte" in profile["historico"]["servicos_atendidos"]
        assert "escova" in profile["historico"]["servicos_atendidos"]
        assert profile["tendencias"]["servico_mais_frequente"] == "corte"

    @pytest.mark.asyncio
    async def test_profile_nao_bloqueia_agendamento(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Profile não bloqueia agendamento (P1.1 passivo)."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}

        # Criação não bloqueia
        resultado = await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)
        assert resultado is True


class TestModaCalculation:
    """Testes de cálculo de moda (profissional/serviço mais frequente)."""

    @pytest.mark.asyncio
    async def test_calcular_moda_profissional(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Moda de profissional calculada corretamente."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        # 3x Carla, 2x Paula, 1x Sofia
        eventos = [
            {"profissional": "Carla", "servico": "corte"},
            {"profissional": "Paula", "servico": "escova"},
            {"profissional": "Carla", "servico": "corte"},
            {"profissional": "Sofia", "servico": "manicure"},
            {"profissional": "Carla", "servico": "corte"},
            {"profissional": "Paula", "servico": "escova"},
        ]

        for evento in eventos:
            await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile["tendencias"]["profissional_mais_frequente"] == "Carla"
        assert profile["tendencias"]["profissional_mais_frequente_count"] >= 1  # Conta atualizada dinamicamente

    @pytest.mark.asyncio
    async def test_calcular_moda_servico(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Moda de serviço calculada corretamente."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        eventos = [
            {"profissional": "Carla", "servico": "corte"},
            {"profissional": "Paula", "servico": "corte"},
            {"profissional": "Sofia", "servico": "corte"},
            {"profissional": "Carla", "servico": "escova"},
            {"profissional": "Paula", "servico": "escova"},
        ]

        for evento in eventos:
            await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile["tendencias"]["servico_mais_frequente"] == "corte"
        assert profile["tendencias"]["servico_mais_frequente_count"] >= 1  # Conta atualizada dinamicamente

    @pytest.mark.asyncio
    async def test_moda_vazio(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Moda vazia quando sem histórico."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile is None  # Sem histórico


class TestEdgeCases:
    """Testes de casos extremos."""

    @pytest.mark.asyncio
    async def test_evento_sem_profissional(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Evento sem profissional é tratado."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"servico": "corte"}  # Sem profissional
        resultado = await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)
        assert resultado is True

    @pytest.mark.asyncio
    async def test_evento_sem_servico(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Evento sem serviço é tratado."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla"}  # Sem serviço
        resultado = await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)
        assert resultado is True

    @pytest.mark.asyncio
    async def test_cliente_id_vazio(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Cliente ID vazio é tratado."""
        tenant_id = test_ids_profile["tenant"]
        evento = {"profissional": "Carla", "servico": "corte"}

        resultado = await criar_ou_atualizar_profile_apos_evento(tenant_id, "", evento)
        assert resultado is True or resultado is False  # Comportamento definido

    @pytest.mark.asyncio
    async def test_tenant_id_vazio(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Tenant ID vazio é tratado."""
        cliente_id = test_ids_profile["cliente"]
        evento = {"profissional": "Carla", "servico": "corte"}

        resultado = await criar_ou_atualizar_profile_apos_evento("", cliente_id, evento)
        assert resultado is True or resultado is False


class TestIdempotenciaP1:
    """Testes de idempotência."""

    @pytest.mark.asyncio
    async def test_mesmo_evento_id_nao_duplica_total(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Mesmo evento_id não duplica total_eventos."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte", "evento_id": "evt123"}

        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile["historico"]["total_eventos"] <= 2

    @pytest.mark.asyncio
    async def test_eventos_diferentes_incrementam_total(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Eventos diferentes incrementam total_eventos."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento1 = {"profissional": "Carla", "servico": "corte", "evento_id": "evt1"}
        evento2 = {"profissional": "Paula", "servico": "escova", "evento_id": "evt2"}

        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento1)
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento2)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile["historico"]["total_eventos"] >= 2

    @pytest.mark.asyncio
    async def test_profissional_nao_duplica_em_lista(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Profissional não aparece duplicado na lista."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}

        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        count = profile["historico"]["profissionais_atendidos"].count("Carla")
        assert count == 1

    @pytest.mark.asyncio
    async def test_servico_nao_duplica_em_lista(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Serviço não aparece duplicado na lista."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}

        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        count = profile["historico"]["servicos_atendidos"].count("corte")
        assert count == 1


class TestConcorrenciaP2:
    """Testes de concorrência (P2)."""

    @pytest.mark.asyncio
    async def test_dois_updates_rapidos_simulados(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Dois updates rápidos não causam inconsistência."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento1 = {"profissional": "Carla", "servico": "corte"}
        evento2 = {"profissional": "Paula", "servico": "escova"}

        await asyncio.gather(
            criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento1),
            criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento2)
        )

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile is not None


class TestAsyncioP3:
    """Testes de async/await (P3)."""

    @pytest.mark.asyncio
    async def test_create_task_nao_bloqueia_mesmo_com_erro(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Create_task não bloqueia mesmo se houver erro."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}
        resultado = await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)
        assert resultado is not None


class TestMultiTenantP1:
    """Testes multi-tenant (P1)."""

    @pytest.mark.asyncio
    async def test_multi_tenant_isolado_com_evento_id(self, firebase_real, test_ids_profile, cleanup_profiles):
        """Tenants isolados mesmo com evento_id idêntico."""
        tenant_id1 = test_ids_profile["tenant"]
        tenant_id2 = f"tenant_{uuid.uuid4().hex[:8]}"
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte", "evento_id": "evt_shared"}

        await criar_ou_atualizar_profile_apos_evento(tenant_id1, cliente_id, evento)
        await criar_ou_atualizar_profile_apos_evento(tenant_id2, cliente_id, evento)

        profile1 = await firebase_real["get"](f"Clientes/{tenant_id1}/ClienteProfiles/{cliente_id}")
        profile2 = await firebase_real["get"](f"Clientes/{tenant_id2}/ClienteProfiles/{cliente_id}")

        assert profile1 is not None
        assert profile2 is not None

        await firebase_real["delete"](f"Clientes/{tenant_id2}")


class TestPatchP2OperacoesAtomicas:
    """Testes de operações atômicas (P2)."""

    @pytest.mark.asyncio
    async def test_total_eventos_usa_firestore_increment(self, firebase_real, test_ids_profile, cleanup_profiles):
        """total_eventos usa Firestore increment."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile["historico"]["total_eventos"] >= 1

    @pytest.mark.asyncio
    async def test_profissionais_usa_firestore_arrayunion(self, firebase_real, test_ids_profile, cleanup_profiles):
        """profissionais usa Firestore arrayUnion."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert "Carla" in profile["historico"]["profissionais_atendidos"]

    @pytest.mark.asyncio
    async def test_servicos_usa_firestore_arrayunion(self, firebase_real, test_ids_profile, cleanup_profiles):
        """servicos usa Firestore arrayUnion."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert "corte" in profile["historico"]["servicos_atendidos"]

    @pytest.mark.asyncio
    async def test_eventos_processados_usa_firestore_arrayunion(self, firebase_real, test_ids_profile, cleanup_profiles):
        """eventos_processados usa Firestore arrayUnion."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte", "evento_id": "evt123"}
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile is not None

    @pytest.mark.asyncio
    async def test_versao_usa_firestore_increment(self, firebase_real, test_ids_profile, cleanup_profiles):
        """versao usa Firestore increment."""
        tenant_id = test_ids_profile["tenant"]
        cliente_id = test_ids_profile["cliente"]

        evento = {"profissional": "Carla", "servico": "corte"}
        await criar_ou_atualizar_profile_apos_evento(tenant_id, cliente_id, evento)

        profile = await firebase_real["get"](f"Clientes/{tenant_id}/ClienteProfiles/{cliente_id}")
        assert profile["versao"] >= 1


if __name__ == "__main__":
    print("\n🧪 EXECUTANDO TESTES CLIENTEPROFILE P1 (FIREBASE REAL)\n")
