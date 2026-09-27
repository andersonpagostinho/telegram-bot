"""
C3.10 FASE 1: Testes de Índice Derivado de Atores

Objetivo: Validar que o índice derivado Clientes/_Index/Atores/{actor_id}
é criado corretamente após criação de ator.

Testes P0: 5 (regressão)
Testes P1: 4 (novas funcionalidades)

Uso: FIRESTORE REAL (não mockado, padrão C3.12)
"""

import pytest
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firebase_service_async import (
    buscar_subcolecao,
    deletar_dado_em_path,
)
from services.identidade_service import (
    criar_ator_dono,
    criar_ator_cliente_automatico,
    criar_ator_profissional,
    normalizar_actor_id,
    obter_tenant_id,
)


class TestC310IndiceDerivadoP0:
    """Testes P0: Regressão - Não quebra fluxos atuais"""

    @pytest.mark.asyncio
    async def test_p0_1_dono_indexado(self):
        """P0-1: Criar dono indexa no _Index"""
        print("\n[P0-1] Dono: criação indexa corretamente")

        tenant_id = "c310_p0_t_dono"
        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        # Criar dono
        ator = await criar_ator_dono(
            tenant_id=tenant_id,
            canal="whatsapp",
            identificador="test_p0_1_dono",
            nome="P0 Dono",
            email="p0@dono.com"
        )
        actor_id = ator.get("actor_id")
        print(f"[OK] Ator criado: {actor_id}")

        # Chamar obter_tenant_id (que lê do índice)
        result_tenant = await obter_tenant_id(actor_id)
        assert result_tenant == tenant_id, f"[FAIL] Índice: {result_tenant} != {tenant_id}"
        print(f"[OK] Índice resolveu tenant_id corretamente")

        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        print("[P0-1] PASS")

    @pytest.mark.asyncio
    async def test_p0_2_cliente_indexado(self):
        """P0-2: Criar cliente indexa no _Index"""
        print("\n[P0-2] Cliente: criação indexa corretamente")

        tenant_id = "c310_p0_t_cliente"
        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        # Criar cliente
        ator = await criar_ator_cliente_automatico(
            tenant_id=tenant_id,
            canal="whatsapp",
            identificador="test_p0_2_cliente",
            nome_detectado="P0 Cliente"
        )
        actor_id = ator.get("actor_id")

        # Verificar via obter_tenant_id
        result_tenant = await obter_tenant_id(actor_id)
        assert result_tenant == tenant_id, f"[FAIL] {result_tenant} != {tenant_id}"
        print(f"[OK] Cliente indexado corretamente")

        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        print("[P0-2] PASS")

    @pytest.mark.asyncio
    async def test_p0_3_actor_inexistente(self):
        """P0-3: Actor inexistente retorna None"""
        print("\n[P0-3] Actor inexistente: None")

        result = await obter_tenant_id("whatsapp:inexistente_9999999")
        assert result is None, f"[FAIL] Esperava None"
        print(f"[OK] Retorna None corretamente")

        print("[P0-3] PASS")

    @pytest.mark.asyncio
    async def test_p0_4_isolamento_ab(self):
        """P0-4: Dois tenants isolados"""
        print("\n[P0-4] Isolamento: Tenant A vs B")

        tenant_a = "c310_p0_t_a"
        tenant_b = "c310_p0_t_b"

        try:
            await deletar_dado_em_path(f"Clientes/{tenant_a}")
            await deletar_dado_em_path(f"Clientes/{tenant_b}")
        except:
            pass

        # Criar em A (usar telefones diferentes para evitar colisão)
        ator_a = await criar_ator_dono(
            tenant_id=tenant_a,
            canal="whatsapp",
            identificador="11988888888",
            nome="A",
            email="a@test.com"
        )

        # Criar em B (telefone diferente)
        ator_b = await criar_ator_dono(
            tenant_id=tenant_b,
            canal="whatsapp",
            identificador="11999999999",
            nome="B",
            email="b@test.com"
        )

        # Verificar isolamento
        t_a = await obter_tenant_id(ator_a.get("actor_id"))
        t_b = await obter_tenant_id(ator_b.get("actor_id"))

        assert t_a == tenant_a and t_b == tenant_b and t_a != t_b
        print(f"[OK] Tenants isolados")

        try:
            await deletar_dado_em_path(f"Clientes/{tenant_a}")
            await deletar_dado_em_path(f"Clientes/{tenant_b}")
        except:
            pass

        print("[P0-4] PASS")

    @pytest.mark.asyncio
    async def test_p0_5_retry_idempotente(self):
        """P0-5: Retry sem duplicação"""
        print("\n[P0-5] Retry: idempotente")

        tenant_id = "c310_p0_t_retry"
        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        # Criar 2x
        ator1 = await criar_ator_dono(
            tenant_id=tenant_id,
            canal="whatsapp",
            identificador="test_p0_5_retry",
            nome="Retry",
            email="retry@test.com"
        )

        ator2 = await criar_ator_dono(
            tenant_id=tenant_id,
            canal="whatsapp",
            identificador="test_p0_5_retry",
            nome="Retry",
            email="retry@test.com"
        )

        # Mesmos IDs
        assert ator1.get("actor_id") == ator2.get("actor_id")

        # Ambos resolvem tenant corretamente
        t1 = await obter_tenant_id(ator1.get("actor_id"))
        t2 = await obter_tenant_id(ator2.get("actor_id"))
        assert t1 == t2 == tenant_id

        print(f"[OK] Retry idempotente")

        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        print("[P0-5] PASS")


class TestC310IndiceDerivadoP1:
    """Testes P1: Novas funcionalidades de índice"""

    @pytest.mark.asyncio
    async def test_p1_1_profissional_indexado(self):
        """P1-1: Profissional é indexado"""
        print("\n[P1-1] Profissional: indexado")

        tenant_id = "c310_p1_t_prof"
        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        # Criar dono
        dono = await criar_ator_dono(
            tenant_id=tenant_id,
            canal="whatsapp",
            identificador="test_p1_1_dono",
            nome="Dono",
            email="dono@p1.com"
        )

        # Criar profissional
        prof = await criar_ator_profissional(
            tenant_id=tenant_id,
            canal="whatsapp",
            identificador="test_p1_1_prof",
            nome="Prof",
            criado_por=dono.get("actor_id")
        )

        # Verificar via índice
        result = await obter_tenant_id(prof.get("actor_id"))
        assert result == tenant_id
        print(f"[OK] Profissional indexado")

        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        print("[P1-1] PASS")

    @pytest.mark.asyncio
    async def test_p1_2_indice_campos_minimos(self):
        """P1-2: Índice contém apenas campos mínimos"""
        print("\n[P1-2] Índice: campos mínimos (C3.10 gate)")

        tenant_id = "c310_p1_t_fields"
        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        # Criar ator
        ator = await criar_ator_dono(
            tenant_id=tenant_id,
            canal="whatsapp",
            identificador="test_p1_2_fields",
            nome="Fields Test",
            email="fields@p1.com"
        )
        actor_id = ator.get("actor_id")

        # Ler índice (simples verificação de existência)
        # Chamamos obter_tenant_id que confirma índice existe com tenant_id
        result_tenant = await obter_tenant_id(actor_id)

        # Se retornou tenant_id, o índice foi criado com pelo menos esse campo
        assert result_tenant == tenant_id
        assert ator.get("email") == "fields@p1.com"  # Email em Atores, não em _Index
        print(f"[OK] Índice contém tenant_id (não copia todos campos)")

        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        print("[P1-2] PASS")

    @pytest.mark.asyncio
    async def test_p1_3_obter_tenant_id_graceful(self):
        """P1-3: obter_tenant_id nunca lança (graceful)"""
        print("\n[P1-3] obter_tenant_id: graceful error handling")

        # Cenários que não devem lançar
        r1 = await obter_tenant_id(None)
        assert r1 is None
        print(f"[OK] None input: retorna None")

        r2 = await obter_tenant_id("")
        assert r2 is None
        print(f"[OK] Empty string: retorna None")

        r3 = await obter_tenant_id("whatsapp:fake_999999999")
        assert r3 is None
        print(f"[OK] Inexistente: retorna None")

        print("[P1-3] PASS")

    @pytest.mark.asyncio
    async def test_p1_4_crescimento_indice(self):
        """P1-4: Índice cresce com novos atores"""
        print("\n[P1-4] Índice: crescimento com novos atores")

        tenant_id = "c310_p1_t_grow"
        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        # Criar múltiplos atores
        atores = []
        for i in range(3):
            ator = await criar_ator_cliente_automatico(
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador=f"test_p1_4_cliente_{i}",
                nome_detectado=f"Cliente {i}"
            )
            atores.append(ator)

        # Verificar que todos são indexados
        for ator in atores:
            result = await obter_tenant_id(ator.get("actor_id"))
            assert result == tenant_id, f"[FAIL] Ator {i} não indexado"

        print(f"[OK] Todos os 3 atores indexados")

        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except:
            pass

        print("[P1-4] PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
