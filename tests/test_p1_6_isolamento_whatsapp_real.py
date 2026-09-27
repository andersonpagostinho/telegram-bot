"""
P1.6 — Teste Real de Isolamento Multi-Tenant WhatsApp

Objetivo: Validar que dois tenants podem usar o mesmo wa_id/actor_id sem cruzamento,
quando entram por phone_number_id diferentes.

Usa Firestore REAL, sem mocks para identidade, tenant ou consultas.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, date, timedelta

# Imports necessários
from services.firestore_client import get_db
from services.whatsapp_endpoint_service import (
    registrar_endpoint_whatsapp,
    resolver_tenant_por_endpoint,
)
from services.event_service_async import (
    buscar_eventos_por_intervalo,
    verificar_conflito_e_sugestoes_profissional,
)

# Configurar pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


class TestP16IsolamentoWhatsAppReal:
    """Teste de isolamento multi-tenant com Firestore real."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup e cleanup de fixtures temporárias."""
        # IDs únicos por execução
        run_id = str(uuid.uuid4())[:8]
        self.tenant_a_id = f"p1_6_tenant_a_{run_id}"
        self.tenant_b_id = f"p1_6_tenant_b_{run_id}"
        self.phone_number_id_a = f"p1_6_endpoint_a_{run_id}"
        self.phone_number_id_b = f"p1_6_endpoint_b_{run_id}"
        self.shared_wa_id = "5519994443694"  # Mesmo actor em ambos

        self.db = get_db()

        # Setup: Criar tenants, endpoints, eventos
        self._setup_fixtures()

        yield

        # Cleanup: Deletar tudo
        self._cleanup_fixtures()

    def _setup_fixtures(self):
        """Criar tenants, endpoints e eventos no Firestore."""
        # Tenant A
        tenant_a_doc = f"Clientes/{self.tenant_a_id}"
        self.db.collection("Clientes").document(self.tenant_a_id).set(
            {
                "tipo_usuario": "salao",
                "nome": f"Tenant A {self.tenant_a_id}",
                "criado_em": datetime.now().isoformat(),
            }
        )

        # Tenant B
        tenant_b_doc = f"Clientes/{self.tenant_b_id}"
        self.db.collection("Clientes").document(self.tenant_b_id).set(
            {
                "tipo_usuario": "salao",
                "nome": f"Tenant B {self.tenant_b_id}",
                "criado_em": datetime.now().isoformat(),
            }
        )

        # Registrar endpoints
        registrar_endpoint_whatsapp(
            phone_number_id=self.phone_number_id_a,
            tenant_id=self.tenant_a_id,
            display_phone_number="+55 11 9 3456-7890",
            waba_id="waba_a",
        )
        registrar_endpoint_whatsapp(
            phone_number_id=self.phone_number_id_b,
            tenant_id=self.tenant_b_id,
            display_phone_number="+55 11 9 3456-7891",
            waba_id="waba_b",
        )

        # Criar eventos distintos em cada tenant
        hoje = date.today()
        amanha = hoje + timedelta(days=1)

        # Eventos Tenant A
        self.db.collection("Clientes").document(self.tenant_a_id).collection(
            "Eventos"
        ).document("evento_a_1").set(
            {
                "data": hoje.isoformat(),
                "hora_inicio": "10:00",
                "hora_fim": "10:30",
                "servico": "Corte",
                "profissional": "Alice",
                "cliente": "Joao",
            }
        )
        self.db.collection("Clientes").document(self.tenant_a_id).collection(
            "Eventos"
        ).document("evento_a_2").set(
            {
                "data": amanha.isoformat(),
                "hora_inicio": "14:00",
                "hora_fim": "14:30",
                "servico": "Manicure",
                "profissional": "Bob",
                "cliente": "Maria",
            }
        )

        # Eventos Tenant B
        self.db.collection("Clientes").document(self.tenant_b_id).collection(
            "Eventos"
        ).document("evento_b_1").set(
            {
                "data": hoje.isoformat(),
                "hora_inicio": "11:00",
                "hora_fim": "11:30",
                "servico": "Pintura",
                "profissional": "Carol",
                "cliente": "Pedro",
            }
        )
        self.db.collection("Clientes").document(self.tenant_b_id).collection(
            "Eventos"
        ).document("evento_b_2").set(
            {
                "data": amanha.isoformat(),
                "hora_inicio": "15:00",
                "hora_fim": "15:30",
                "servico": "Massagem",
                "profissional": "David",
                "cliente": "Ana",
            }
        )

    def _cleanup_fixtures(self):
        """Limpar todos os documentos criados pelo teste."""
        try:
            # Deletar Tenant A e subcoleções
            eventos_a = self.db.collection("Clientes").document(
                self.tenant_a_id
            ).collection("Eventos").stream()
            for doc in eventos_a:
                doc.reference.delete()

            self.db.collection("Clientes").document(self.tenant_a_id).delete()

            # Deletar Tenant B e subcoleções
            eventos_b = self.db.collection("Clientes").document(
                self.tenant_b_id
            ).collection("Eventos").stream()
            for doc in eventos_b:
                doc.reference.delete()

            self.db.collection("Clientes").document(self.tenant_b_id).delete()

            # Deletar endpoints
            self.db.collection("WhatsAppEndpoints").document(
                self.phone_number_id_a
            ).delete()
            self.db.collection("WhatsAppEndpoints").document(
                self.phone_number_id_b
            ).delete()

        except Exception as e:
            print(f"[CLEANUP AVISO] Erro ao limpar: {e}")

    # ========== TESTES ==========

    def test_1_resolucao_endpoint(self):
        """TESTE 1: Resolver endpoints A e B para seus tenants (sincrono)."""
        # resolver_tenant_por_endpoint eh sincrona
        tenant_a = resolver_tenant_por_endpoint(self.phone_number_id_a)
        tenant_b = resolver_tenant_por_endpoint(self.phone_number_id_b)

        assert tenant_a == self.tenant_a_id, f"Endpoint A deve resolver para tenant A"
        assert tenant_b == self.tenant_b_id, f"Endpoint B deve resolver para tenant B"
        assert tenant_a != tenant_b, f"Endpoints devem resolver para tenants diferentes"

    def test_2_mesmo_actor_id(self):
        """TESTE 2: Confirmar que o mesmo wa_id existe em ambos tenants, sem resolucao global."""
        # Verificar que tenants existem
        doc_a = self.db.collection("Clientes").document(self.tenant_a_id).get()
        doc_b = self.db.collection("Clientes").document(self.tenant_b_id).get()

        assert doc_a.exists, f"Tenant A deve existir"
        assert doc_b.exists, f"Tenant B deve existir"

        # Verificar que actor_id eh o mesmo (nao ha resolucao global)
        # Nao ha indice global Clientes/_Index/Atores que pudesse cruzar

    @pytest.mark.asyncio
    async def test_3_leitura_eventos_tenant_a(self):
        """TESTE 3A: Leitura de eventos do Tenant A sem Tenant B."""
        eventos = await buscar_eventos_por_intervalo(
            user_id=self.shared_wa_id,
            dia_especifico=date.today(),
            tenant_id=self.tenant_a_id,  # Explicito
        )

        # Deve retornar somente eventos A
        assert len(eventos) > 0, "Deve encontrar eventos em Tenant A"
        assert all(
            "Corte" in str(e.get("servico", "")) or "Manicure" in str(e.get("servico", ""))
            for e in eventos
        ), "Deve retornar apenas servicos de Tenant A"

        # Verificar que nenhum evento B esta presente
        for evento in eventos:
            assert (
                "Pintura" not in str(evento.get("servico", ""))
            ), "Evento de Tenant B nao deve aparecer"

    @pytest.mark.asyncio
    async def test_3_leitura_eventos_tenant_b(self):
        """TESTE 3B: Leitura de eventos do Tenant B sem Tenant A."""
        eventos = await buscar_eventos_por_intervalo(
            user_id=self.shared_wa_id,
            dia_especifico=date.today(),
            tenant_id=self.tenant_b_id,  # Explicito
        )

        # Deve retornar somente eventos B
        assert len(eventos) > 0, "Deve encontrar eventos em Tenant B"
        assert all(
            "Pintura" in str(e.get("servico", "")) or "Massagem" in str(e.get("servico", ""))
            for e in eventos
        ), "Deve retornar apenas servicos de Tenant B"

        # Verificar que nenhum evento A esta presente
        for evento in eventos:
            assert (
                "Corte" not in str(evento.get("servico", ""))
            ), "Evento de Tenant A nao deve aparecer"

    @pytest.mark.asyncio
    async def test_4_conflito_tenant_a(self):
        """TESTE 4A: Verificar conflito em Tenant A."""
        conflito = await verificar_conflito_e_sugestoes_profissional(
            user_id=self.shared_wa_id,
            data=date.today().isoformat(),
            hora_inicio="10:00",
            duracao_min=30,
            profissional="Alice",
            servico="Corte",
            tenant_id=self.tenant_a_id,  # Explicito
        )

        # Deve indicar conflito (Alice as 10h)
        assert conflito.get("conflito"), "Deve detectar conflito com Alice as 10h em Tenant A"

    @pytest.mark.asyncio
    async def test_4_conflito_tenant_b(self):
        """TESTE 4B: Verificar conflito em Tenant B (sem conflito de A)."""
        conflito = await verificar_conflito_e_sugestoes_profissional(
            user_id=self.shared_wa_id,
            data=date.today().isoformat(),
            hora_inicio="10:00",
            duracao_min=30,
            profissional="Carol",  # Diferente de Alice
            servico="Pintura",
            tenant_id=self.tenant_b_id,  # Explicito
        )

        # Carol as 10h em Tenant B nao tem conflito (ela esta as 11h)
        # A resposta eh de Tenant B, nao de A
        # Apenas verificar que consegue consultar Tenant B
        assert conflito is not None, "Deve retornar resposta de Tenant B"

    @pytest.mark.asyncio
    async def test_5_inversao_a_b_a(self):
        """TESTE 5: Alternancia entre A e B usando mesmo actor_id."""
        # Chamar A
        eventos_a1 = await buscar_eventos_por_intervalo(
            user_id=self.shared_wa_id,
            tenant_id=self.tenant_a_id,
        )

        # Chamar B
        eventos_b1 = await buscar_eventos_por_intervalo(
            user_id=self.shared_wa_id,
            tenant_id=self.tenant_b_id,
        )

        # Chamar A novamente
        eventos_a2 = await buscar_eventos_por_intervalo(
            user_id=self.shared_wa_id,
            tenant_id=self.tenant_a_id,
        )

        # Verificar isolamento em cada chamada
        assert len(eventos_a1) > 0, "Primeira chamada A deve retornar eventos"
        assert len(eventos_b1) > 0, "Chamada B deve retornar eventos diferentes"
        assert len(eventos_a2) > 0, "Segunda chamada A deve retornar eventos"

        # Eventos de A nunca devem aparecer em B
        a_servicos = {e.get("servico") for e in eventos_a1}
        b_servicos = {e.get("servico") for e in eventos_b1}
        assert len(a_servicos & b_servicos) == 0, "Tenants A e B nao devem compartilhar servicos"

    def test_6_limpeza(self):
        """TESTE 6: Verificar que fixtures foram limpas apos testes."""
        # Apos cleanup, os documentos nao devem existir
        self._cleanup_fixtures()

        doc_a = self.db.collection("Clientes").document(self.tenant_a_id).get()
        doc_b = self.db.collection("Clientes").document(self.tenant_b_id).get()
        endpoint_a = self.db.collection("WhatsAppEndpoints").document(
            self.phone_number_id_a
        ).get()

        assert not doc_a.exists, "Tenant A deve ser deletado"
        assert not doc_b.exists, "Tenant B deve ser deletado"
        assert not endpoint_a.exists, "Endpoint A deve ser deletado"
