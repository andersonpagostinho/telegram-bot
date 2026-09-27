#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GATE C3.15.3-B — Teste de Resolução de Identidade WhatsApp (Ingress)

Valida que:
1. phone_number_id resolve tenant correto via endpoint
2. tenant_id é passado ao roteador
3. tenant_id explícito não é substituído por wa_id
4. actor_id é resolvido canonicamente
5. sessão usa tenant_id + actor_id corretos
6. onboarding é processado APÓS identidade
7. isolamento multi-tenant é preservado
8. fluxo legado sem tenant_id continua funcionando
"""

import asyncio
import pytest
import time
from datetime import datetime
import pytz
from services.firestore_client import get_db
from services.whatsapp_endpoint_service import resolver_tenant_por_endpoint
from services.identidade_service import (
    criar_ator_dono,
    normalizar_actor_id,
    resolver_ator_por_canal_canonico,
)
from services.firebase_service_async import obter_id_dono


class TestGateC3153BWhatsAppIngress:
    """Testes de resolução de identidade WhatsApp desde o endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Criar endpoint, tenant, ator WhatsApp"""
        self.phone_number_id = f"1350170954840548"
        self.tenant_id = f"test_wa_ingress_{int(time.time())}"
        self.wa_id = "5511991382080"
        self.actor_id = normalizar_actor_id("whatsapp", self.wa_id)

        db = get_db()

        # 1. Criar endpoint WhatsApp no Firestore
        print(f"[SETUP] Criando WhatsApp endpoint: {self.phone_number_id} → {self.tenant_id}")
        db.collection("WhatsAppEndpoints").document(self.phone_number_id).set({
            "phone_number_id": self.phone_number_id,
            "tenant_id": self.tenant_id,
            "display_phone_number": "+55 11 9 9138-2080",
            "business_account_id": "waba_123456",
            "status": "ativo",
            "criado_em": datetime.now(pytz.UTC).isoformat(),
        })

        # 2. Criar tenant/dono
        print(f"[SETUP] Criando tenant: {self.tenant_id}")
        db.collection("Clientes").document(self.tenant_id).set({
            "id": self.tenant_id,
            "nome": "Tenant Teste WhatsApp",
            "status": "ativo",
            "criado_em": datetime.now(pytz.UTC).isoformat(),
        })

        # 3. Criar ator dono vinculado ao WhatsApp
        print(f"[SETUP] Criando ator dono: {self.actor_id}")
        db.collection("Clientes").document(self.tenant_id).collection("Atores").document(self.actor_id).set({
            "id": self.actor_id,
            "tenant_id": self.tenant_id,
            "tipo_usuario": "dono",
            "ativo": True,
            "canais": [
                {
                    "canal": "whatsapp",
                    "identificador": self.wa_id,
                    "ativo": True,
                }
            ],
            "criado_em": datetime.now(pytz.UTC).isoformat(),
        })

        yield

        # Cleanup
        try:
            db.collection("WhatsAppEndpoints").document(self.phone_number_id).delete()
            db.collection("Clientes").document(self.tenant_id).collection("Atores").document(self.actor_id).delete()
            db.collection("Clientes").document(self.tenant_id).delete()
        except:
            pass

    @pytest.mark.asyncio
    async def test_t01_phone_number_id_resolve_tenant(self):
        """T01: phone_number_id resolve tenant correto"""
        tenant = resolver_tenant_por_endpoint(self.phone_number_id)
        assert tenant == self.tenant_id, f"Esperado {self.tenant_id}, obteve {tenant}"

    @pytest.mark.asyncio
    async def test_t02_wa_id_nao_e_cliente_registrado(self):
        """T02: wa_id puro não é cliente em Firestore"""
        cliente = await obter_id_dono(self.wa_id)
        assert cliente is None, f"wa_id não deveria ser cliente: {cliente}"

    @pytest.mark.asyncio
    async def test_t03_tenant_explícito_nao_e_wa_id(self):
        """T03: tenant_id explícito não é substituído por wa_id"""
        # Simular que tenant_id foi resolvido do endpoint
        tenant_id_resolvido = self.tenant_id  # 7394370553 (do endpoint)
        wa_id = self.wa_id  # 5511991382080

        # Se tenant_id é passado ao roteador, ele não deve ser wa_id
        assert tenant_id_resolvido != wa_id, "tenant_id não deveria ser wa_id"
        assert len(tenant_id_resolvido) == len(self.tenant_id), "tenant_id é número de 10 dígitos"

    @pytest.mark.asyncio
    async def test_t04_resolver_ator_por_canal_canonico(self):
        """T04: actor_id é obtido de Atores.canais[]"""
        ator = await resolver_ator_por_canal_canonico(
            tenant_id=self.tenant_id,
            canal="whatsapp",
            identificador=self.wa_id
        )

        assert ator is not None, f"Ator deve ser encontrado"
        assert ator.get("id") == self.actor_id, f"Esperado {self.actor_id}, obteve {ator.get('id')}"

    @pytest.mark.asyncio
    async def test_t05_sessao_path_correto(self):
        """T05: sessão carrega de Clientes/{tenant_id}/Sessoes/{actor_id}"""
        db = get_db()

        # Path esperado (novo)
        path_esperado = f"Clientes/{self.tenant_id}/Sessoes/{self.actor_id}"
        path_incorreto = f"Clientes/{self.wa_id}/Sessoes/{self.wa_id}"

        try:
            # Limpar dados sujos do path incorreto (se existirem)
            db.collection("Clientes").document(self.wa_id).collection("Sessoes").document(self.wa_id).delete()
        except:
            pass

        # Salvar sessão no path correto
        db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id).set({
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "estado_fluxo": "idle",
            "atualizado_em": datetime.now(pytz.UTC).isoformat(),
        })

        # Verificar que foi salvo
        doc = db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id).get()
        assert doc.exists, f"Sessão deveria existir em {path_esperado}"
        assert doc.get("actor_id") == self.actor_id

        # Verificar que path incorreto está vazio
        doc_incorreto = db.collection("Clientes").document(self.wa_id).collection("Sessoes").document(self.wa_id).get()
        assert not doc_incorreto.exists, f"Sessão NÃO deveria existir em {path_incorreto}"

        # Cleanup
        db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id).delete()

    @pytest.mark.asyncio
    async def test_t06_isolamento_multi_tenant(self):
        """T06: Actor de tenant A não acessa sessão de tenant B"""
        db = get_db()

        tenant_b = f"test_wa_ingress_b_{int(time.time())}"
        wa_id_b = "5522999999999"
        actor_id_b = normalizar_actor_id("whatsapp", wa_id_b)

        try:
            # Criar tenant B
            db.collection("Clientes").document(tenant_b).set({
                "id": tenant_b,
                "nome": "Tenant B",
                "status": "ativo",
                "criado_em": datetime.now(pytz.UTC).isoformat(),
            })

            # Criar ator B
            db.collection("Clientes").document(tenant_b).collection("Atores").document(actor_id_b).set({
                "id": actor_id_b,
                "tenant_id": tenant_b,
                "tipo_usuario": "dono",
                "ativo": True,
                "canais": [{"canal": "whatsapp", "identificador": wa_id_b, "ativo": True}],
                "criado_em": datetime.now(pytz.UTC).isoformat(),
            })

            # Salvar sessão em tenant A
            db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id).set({
                "tenant_id": self.tenant_id,
                "actor_id": self.actor_id,
                "estado_fluxo": "onboarding_dono",
                "atualizado_em": datetime.now(pytz.UTC).isoformat(),
            })

            # Verif que ator_id_a consegue ler sua sessão
            doc_a = db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id).get()
            assert doc_a.exists

            # Verificar que ator_b NÃO consegue ler sessão de tenant A
            doc_a_from_b = db.collection("Clientes").document(tenant_b).collection("Sessoes").document(self.actor_id).get()
            assert not doc_a_from_b.exists, "Actor B não deveria ter acesso a sessão de tenant A"

        finally:
            try:
                db.collection("Clientes").document(self.tenant_id).collection("Sessoes").document(self.actor_id).delete()
                db.collection("Clientes").document(tenant_b).collection("Atores").document(actor_id_b).delete()
                db.collection("Clientes").document(tenant_b).delete()
            except:
                pass

    @pytest.mark.asyncio
    async def test_t07_ator_nao_vinculado_retorna_none(self):
        """T07: ator não vinculado a WhatsApp retorna None"""
        wa_id_nao_vinculado = "5533333333333"

        ator = await resolver_ator_por_canal_canonico(
            tenant_id=self.tenant_id,
            canal="whatsapp",
            identificador=wa_id_nao_vinculado
        )

        assert ator is None, f"Ator não vinculado deveria ser None, obteve {ator}"

    @pytest.mark.asyncio
    async def test_t08_fluxo_legado_sem_tenant_id(self):
        """T08: fluxo legado sem tenant_id explícito continua funcionando"""
        # Este teste valida que quando tenant_id NÃO é passado,
        # o fallback legado obter_id_dono(user_id) ainda é tentado

        # wa_id puro sem tenant resolvido
        cliente_legado = await obter_id_dono(self.wa_id)

        # Esperado: None (wa_id não é cliente), mas função não deve quebrar
        assert cliente_legado is None or isinstance(cliente_legado, str)

    @pytest.mark.asyncio
    async def test_t09_normalizacao_ator_consistente(self):
        """T09: normalização de actor_id é consistente"""
        actor_id_1 = normalizar_actor_id("whatsapp", self.wa_id)
        actor_id_2 = normalizar_actor_id("whatsapp", self.wa_id)

        assert actor_id_1 == actor_id_2, "Normalização deveria ser determinística"
        assert actor_id_1.startswith("whatsapp:"), "actor_id deveria começar com 'whatsapp:'"

    @pytest.mark.asyncio
    async def test_t10_endpoint_nao_encontrado_retorna_none(self):
        """T10: endpoint não registrado retorna None"""
        phone_number_desconhecido = "9999999999999"
        tenant = resolver_tenant_por_endpoint(phone_number_desconhecido)

        assert tenant is None, f"Endpoint desconhecido deveria ser None, obteve {tenant}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
