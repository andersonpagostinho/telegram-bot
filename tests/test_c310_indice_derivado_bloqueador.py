"""
C3.10 — Testes Bloqueador: Índice Derivado Necessário

Reproduz o bloqueador identificado em FASE 2B-2:
`obter_tenant_id()` falha porque `Clientes/_Index/Atores/{actor_id}`
não está sendo criado durante criação de ator.

Estes testes DEVEM falhar antes da implementação.
Após implementação, devem PASSAR.

Padrão: Firestore REAL
"""

import pytest
from datetime import datetime
import pytz
from services.firebase_service_async import (
    salvar_dado_em_path,
    deletar_dado_em_path,
)
from services.identidade_service import (
    criar_ator_dono,
    criar_ator_cliente_automatico,
    criar_ator_profissional,
    obter_tenant_id,
)


FUSO_BR = pytz.timezone("America/Sao_Paulo")


class TestC310IndiceDerivadobloqueador:
    """
    Testes que falham agora, passarão após implementação do índice.
    """

    @pytest.mark.asyncio
    async def test_bloqueador_t1_cliente_resolve_tenant(self):
        """
        T1 BLOQUEADOR: Cliente criado deve resolver tenant via obter_tenant_id

        ESTÁ FALHANDO AGORA: obter_tenant_id() retorna None
        DEVE PASSAR após indexação
        """
        tenant_id = "indice_bloqueador_t1"
        cliente_id = "whatsapp:bloq_t1_cliente"

        try:
            # Criar cliente
            ator = await criar_ator_cliente_automatico(
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador="bloq_t1_cliente",
                nome_detectado="Cliente Bloqueador T1"
            )

            actor_id = ator.get("actor_id")
            print(f"\n[T1] Ator criado: {actor_id}")

            # Tentar resolver tenant via índice
            result_tenant = await obter_tenant_id(actor_id)

            # TESTE: Deve retornar o tenant_id, não None
            assert result_tenant == tenant_id, \
                f"[FAIL] obter_tenant_id({actor_id}) retornou {result_tenant}, esperava {tenant_id}"

            print(f"[PASS] Índice resolveu tenant corretamente")

        finally:
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}")
            except:
                pass

    @pytest.mark.asyncio
    async def test_bloqueador_t2_dono_resolve_tenant(self):
        """
        T2 BLOQUEADOR: Dono criado deve resolver tenant via obter_tenant_id
        """
        tenant_id = "indice_bloqueador_t2"

        try:
            # Criar dono
            ator = await criar_ator_dono(
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador="bloq_t2_dono",
                nome="Dono Bloqueador T2",
                email="donot2@teste.com"
            )

            actor_id = ator.get("actor_id")
            print(f"\n[T2] Dono criado: {actor_id}")

            # Tentar resolver tenant via índice
            result_tenant = await obter_tenant_id(actor_id)

            # TESTE: Deve retornar o tenant_id
            assert result_tenant == tenant_id, \
                f"[FAIL] Dono: obter_tenant_id() retornou {result_tenant}, esperava {tenant_id}"

            print(f"[PASS] Dono indexado corretamente")

        finally:
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}")
            except:
                pass

    @pytest.mark.asyncio
    async def test_bloqueador_t3_profissional_resolve_tenant(self):
        """
        T3 BLOQUEADOR: Profissional criado deve resolver tenant via obter_tenant_id
        """
        tenant_id = "indice_bloqueador_t3"
        dono_id = "whatsapp:bloq_t3_dono"

        try:
            # Criar dono primeiro (necessário para criar profissional)
            dono = await criar_ator_dono(
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador="bloq_t3_dono",
                nome="Dono T3",
                email="donot3@teste.com"
            )
            dono_actor_id = dono.get("actor_id")

            # Criar profissional
            prof = await criar_ator_profissional(
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador="bloq_t3_prof",
                nome="Profissional Bloqueador T3",
                criado_por=dono_actor_id
            )

            prof_actor_id = prof.get("actor_id")
            print(f"\n[T3] Profissional criado: {prof_actor_id}")

            # Tentar resolver tenant via índice
            result_tenant = await obter_tenant_id(prof_actor_id)

            # TESTE: Deve retornar o tenant_id
            assert result_tenant == tenant_id, \
                f"[FAIL] Prof: obter_tenant_id() retornou {result_tenant}, esperava {tenant_id}"

            print(f"[PASS] Profissional indexado corretamente")

        finally:
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}")
            except:
                pass

    @pytest.mark.asyncio
    async def test_bloqueador_t4_idempotencia_indexacao(self):
        """
        T4 BLOQUEADOR: Indexação deve ser idempotente
        Chamar múltiplas vezes não deve quebrar
        """
        tenant_id = "indice_bloqueador_t4"

        try:
            # Criar cliente
            ator = await criar_ator_cliente_automatico(
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador="bloq_t4_cliente",
                nome_detectado="Cliente T4"
            )

            actor_id = ator.get("actor_id")

            # Chamar obter_tenant_id múltiplas vezes
            r1 = await obter_tenant_id(actor_id)
            r2 = await obter_tenant_id(actor_id)
            r3 = await obter_tenant_id(actor_id)

            # TESTE: Todos devem retornar o mesmo tenant_id
            assert r1 == r2 == r3 == tenant_id, \
                f"[FAIL] Idempotência: {r1}, {r2}, {r3} deveriam ser iguais"

            print(f"[PASS] Indexação é idempotente")

        finally:
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}")
            except:
                pass

    @pytest.mark.asyncio
    async def test_bloqueador_t5_isolamento_tenant_cross(self):
        """
        T5 BLOQUEADOR: Ator de tenantA não pode ter tenant B no índice
        Garante isolamento multi-tenant
        """
        tenant_a = "indice_bloqueador_t5a"
        tenant_b = "indice_bloqueador_t5b"

        try:
            # Criar cliente em A
            ator_a = await criar_ator_cliente_automatico(
                tenant_id=tenant_a,
                canal="whatsapp",
                identificador="bloq_t5_cli_a",
                nome_detectado="Cliente A"
            )

            # Criar cliente em B
            ator_b = await criar_ator_cliente_automatico(
                tenant_id=tenant_b,
                canal="whatsapp",
                identificador="bloq_t5_cli_b",
                nome_detectado="Cliente B"
            )

            actor_id_a = ator_a.get("actor_id")
            actor_id_b = ator_b.get("actor_id")

            # Resolver tenants
            resolved_a = await obter_tenant_id(actor_id_a)
            resolved_b = await obter_tenant_id(actor_id_b)

            # TESTES:
            # 1. Cliente A resolve para tenant A
            assert resolved_a == tenant_a, \
                f"[FAIL] Cliente A resolveu para {resolved_a}, esperava {tenant_a}"

            # 2. Cliente B resolve para tenant B
            assert resolved_b == tenant_b, \
                f"[FAIL] Cliente B resolveu para {resolved_b}, esperava {tenant_b}"

            # 3. Não são iguais (isolamento)
            assert resolved_a != resolved_b, \
                f"[FAIL] Clientes de tenants diferentes resolveram para o mesmo tenant!"

            print(f"[PASS] Isolamento multi-tenant garantido")

        finally:
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_a}")
                await deletar_dado_em_path(f"Clientes/{tenant_b}")
            except:
                pass
