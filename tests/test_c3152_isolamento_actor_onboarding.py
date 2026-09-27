#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GATE C3.15.2-B — Teste de Isolamento de Onboarding por Actor

Valida que o estado de onboarding de ATOR A não é acessível por ATOR B
quando ambos estão no mesmo tenant.
"""

import asyncio
import pytest
import time
from datetime import datetime
import pytz
from services.onboarding_dono_service import pegar_etapa_onboarding
from services.firestore_client import get_db


class TestIsolamentoActorOnboarding:
    """Testes de isolamento de onboarding por actor"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Criar tenant e documentos de teste"""
        self.tenant_id = f"test_iso_actor_{int(time.time())}"
        self.actor_a = "whatsapp:5521111111111"
        self.actor_b = "whatsapp:5522222222222"

        db = get_db()
        legacy_ref = db.collection("Clientes").document(self.tenant_id)\
            .collection("Configuracao").document("negocio")

        legacy_ref.set({
            "tenant_id": self.tenant_id,
            "dono_actor_id": self.actor_a,
            "onboarding_status": "em_progresso",
            "onboarding_etapa_atual": "agenda_padrao",
            "onboarding_indice": 3,
            "dono_nome": "Ator A",
            "dono_email": "ator_a@test.local",
            "criado_em": datetime.now(pytz.UTC).isoformat(),
            "nome_negocio": "Negócio A",
            "segmento": "Salão de Beleza",
            "endereco": "Rua A, 123"
        })

        self.legacy_ref = legacy_ref
        yield

        try:
            legacy_ref.delete()
            novo_ref_a = db.collection("Clientes").document(self.tenant_id)\
                .collection("Donos").document(self.actor_a)\
                .collection("onboarding").document("ativo")
            novo_ref_a.delete()
            novo_ref_b = db.collection("Clientes").document(self.tenant_id)\
                .collection("Donos").document(self.actor_b)\
                .collection("onboarding").document("ativo")
            novo_ref_b.delete()
        except:
            pass

    @pytest.mark.asyncio
    async def test_t01_actor_a_recebe_seu_estado(self):
        """T01: Actor A recebe seu próprio estado de onboarding"""
        etapa_info = await pegar_etapa_onboarding(self.tenant_id, self.actor_a)

        assert etapa_info is not None
        assert etapa_info.get("etapa_atual") == "agenda_padrao"
        assert etapa_info.get("indice") == 3

    @pytest.mark.asyncio
    async def test_t02_actor_b_nao_herda_estado_de_actor_a(self):
        """T02: Actor B do mesmo tenant NÃO recebe estado de Actor A — CRITICAL BUG FIX"""
        etapa_info = await pegar_etapa_onboarding(self.tenant_id, self.actor_b)

        assert etapa_info is None, \
            f"Bug: Actor B herdou estado de A! Obteve: {etapa_info}"

    @pytest.mark.asyncio
    async def test_t04_actor_novo_sem_estado_retorna_none(self):
        """T04: Actor novo sem onboarding iniciado retorna None"""
        actor_novo = "whatsapp:5533333333333"
        etapa_info = await pegar_etapa_onboarding(self.tenant_id, actor_novo)

        assert etapa_info is None

    @pytest.mark.asyncio
    async def test_t05_backward_compatibility_sem_actor_id(self):
        """T05: Sem actor_id fornecido, retorna legacy (backward-compatible)"""
        etapa_info = await pegar_etapa_onboarding(self.tenant_id)

        assert etapa_info is not None
        assert etapa_info.get("etapa_atual") == "agenda_padrao"

    @pytest.mark.asyncio
    async def test_t06_legacy_com_dono_incorreto_bloqueado(self):
        """T06: Legacy com dono_actor_id != actor_id é bloqueado"""
        actor_c = "whatsapp:5544444444444"
        etapa_info = await pegar_etapa_onboarding(self.tenant_id, actor_c)

        assert etapa_info is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
