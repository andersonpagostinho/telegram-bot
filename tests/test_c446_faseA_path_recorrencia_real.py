"""
C4.4.6 — FASE A: Teste Real do PATH Corrigido da Recorrência

Validação que propostas de recorrência são criadas no PATH CORRETO
(Clientes/{DONO}/NotificacoesAgendadas) e não no PATH ERRADO
(Clientes/{CLIENTE}/NotificacoesAgendadas)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.recorrencia_service import checar_e_propor_recorrencias
from services.firestore_client import get_db
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    buscar_subcolecao,
)

FUSO_BR = pytz.timezone("America/Sao_Paulo")


class TestC446FaseAPathRecorrencia:
    """Testes de validação do PATH correto para propostas de recorrência"""

    def setup_method(self):
        """Setup: criar estrutura minima para teste"""
        self.db = get_db()
        self.tenant_id = f"c446_faseA_tenant_{uuid.uuid4().hex[:6]}"
        self.cliente_id = f"c446_faseA_cliente_{uuid.uuid4().hex[:6]}"

        # Criar tenant (dono)
        self.db.collection("Clientes").document(self.tenant_id).set({
            "tipo_usuario": "dono",
            "nome": f"Dono {self.tenant_id}",
        })

        # Criar cliente
        self.db.collection("Clientes").document(self.cliente_id).set({
            "tipo_usuario": "cliente",
            "nome": f"Cliente {self.cliente_id}",
            "id_negocio": self.tenant_id,
        })

    def teardown_method(self):
        """Cleanup"""
        try:
            self.db.collection("Clientes").document(self.tenant_id).delete()
            self.db.collection("Clientes").document(self.cliente_id).delete()
        except:
            pass

    async def _criar_eventos_padrao(self):
        """Helper: criar 3 eventos com padrao de recorrencia valido"""
        agora = datetime.now(FUSO_BR)
        evento_path = f"Clientes/{self.tenant_id}/Eventos"

        # Datas: 30, 20, 10 dias atras = intervalo de 10 dias (valido)
        # Ultimo evento: 10 dias atras (> 5 dias minimos)
        dias = [30, 20, 10]

        for i, dias_atras in enumerate(dias):
            await salvar_dado_em_path(
                f"{evento_path}/evento_{i}",
                {
                    "cliente_id": self.cliente_id,
                    "descricao": "corte cabelo",
                    "data": (agora - timedelta(days=dias_atras)).strftime("%Y-%m-%d"),
                    "hora_inicio": "10:00",
                    "hora_fim": "11:00",
                    "status": "confirmado",
                    "profissional": "Joao",
                }
            )

    @pytest.mark.asyncio
    async def test_T1_T2_T3_T4_criar_cenario_minimo(self):
        """T1-T4: Criar tenant, cliente, eventos que satisfazem recorrencia"""
        print("\n[T1-T4] Cenario minimo de recorrencia")

        await self._criar_eventos_padrao()

        # Validar que foram salvos
        eventos_salvos = await buscar_subcolecao(f"Clientes/{self.tenant_id}/Eventos")
        assert len(eventos_salvos) >= 3, f"[FAIL T4] Esperava 3+ eventos, encontrou {len(eventos_salvos)}"

        print(f"  [OK T1] Tenant criado: {self.tenant_id}")
        print(f"  [OK T2] Cliente criado: {self.cliente_id}")
        print(f"  [OK T3] {len(eventos_salvos)} eventos criados com padrao")
        print(f"  [OK T4] Eventos estao no formato correto")

    @pytest.mark.asyncio
    async def test_T5_proposta_nao_em_cliente_path(self):
        """T5: Verificar que proposta NAO existe em Clientes/{cliente_id}/NotificacoesAgendadas"""
        print("\n[T5] Validar que caminho ERRADO esta vazio")

        await self._criar_eventos_padrao()

        # Executar: checar_e_propor_recorrencias
        propostas = await checar_e_propor_recorrencias(self.tenant_id)

        # Validar: nenhuma proposta no PATH ERRADO
        notif_em_cliente = await buscar_subcolecao(
            f"Clientes/{self.cliente_id}/NotificacoesAgendadas"
        )

        assert notif_em_cliente is None or len(notif_em_cliente) == 0, \
            f"[FAIL T5] Encontrou {len(notif_em_cliente or {})} propostas no PATH ERRADO"

        print(f"  [OK T5] PATH ERRADO (Clientes/{self.cliente_id}/NotificacoesAgendadas) esta vazio")

    @pytest.mark.asyncio
    async def test_T6_proposta_em_tenant_path(self):
        """T6: Verificar que proposta EXISTE em Clientes/{tenant_id}/NotificacoesAgendadas"""
        print("\n[T6] Validar que caminho CORRETO contem proposta")

        await self._criar_eventos_padrao()

        # Executar: checar_e_propor_recorrencias
        propostas = await checar_e_propor_recorrencias(self.tenant_id)
        assert propostas > 0, "[FAIL T6] Nenhuma proposta foi criada"

        # Validar: propostas estao no PATH CORRETO
        notif_em_tenant = await buscar_subcolecao(
            f"Clientes/{self.tenant_id}/NotificacoesAgendadas"
        )

        assert notif_em_tenant is not None and len(notif_em_tenant) > 0, \
            "[FAIL T6] Nenhuma proposta encontrada em Clientes/{TENANT_ID}/NotificacoesAgendadas"

        print(f"  [OK T6] {len(notif_em_tenant)} proposta(s) encontrada(s) no PATH CORRETO")

    @pytest.mark.asyncio
    async def test_T7_destinatario_campo_correto(self):
        """T7: Verificar que campo 'destinatario' == cliente_id"""
        print("\n[T7] Validar campo destinatario")

        await self._criar_eventos_padrao()

        # Executar: checar_e_propor_recorrencias
        await checar_e_propor_recorrencias(self.tenant_id)

        # Validar: campo destinatario e o cliente
        notif_em_tenant = await buscar_subcolecao(
            f"Clientes/{self.tenant_id}/NotificacoesAgendadas"
        )

        assert len(notif_em_tenant) > 0, "[FAIL T7] Nenhuma proposta para inspecionar"

        primeira_proposta = list(notif_em_tenant.values())[0]
        assert primeira_proposta.get("destinatario") == str(self.cliente_id), \
            f"[FAIL T7] Campo destinatario={primeira_proposta.get('destinatario')}, esperado {self.cliente_id}"

        print(f"  [OK T7] Campo destinatario = {self.cliente_id}")

    @pytest.mark.asyncio
    async def test_T8_scheduler_encontra_proposta(self):
        """T8: Simular o que scheduler faz e verificar que encontra a proposta"""
        print("\n[T8] Validar que scheduler encontraria proposta")

        await self._criar_eventos_padrao()

        # Executar: checar_e_propor_recorrencias
        await checar_e_propor_recorrencias(self.tenant_id)

        # Simular o que scheduler faz:
        # 1. Valida tenant e dono
        tenant_doc = await buscar_dado_em_path(f"Clientes/{self.tenant_id}")
        assert tenant_doc.get("tipo_usuario") == "dono", \
            "[FAIL T8] Tenant nao e dono"

        # 2. Busca notificacoes em Clientes/{TENANT}/NotificacoesAgendadas
        notif_encontradas = await buscar_subcolecao(
            f"Clientes/{self.tenant_id}/NotificacoesAgendadas"
        )

        # 3. Filtra por tipo = proposta_recorrencia
        propostas_recorrencia = {
            notif_id: notif
            for notif_id, notif in (notif_encontradas or {}).items()
            if isinstance(notif, dict) and notif.get("tipo") == "proposta_recorrencia"
        }

        assert len(propostas_recorrencia) > 0, \
            "[FAIL T8] Scheduler nao encontraria nenhuma proposta de recorrencia"

        print(f"  [OK T8] Scheduler encontraria {len(propostas_recorrencia)} proposta(s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
