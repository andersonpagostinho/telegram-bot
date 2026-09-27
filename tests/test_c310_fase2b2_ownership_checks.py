"""
C3.10 FASE 2B-2 — OWNERSHIP CHECKS

Valida que operações em eventos (cancelamento, alteração) respeitam
isolamento multi-tenant e autorização de ator.

Padrão: Firestore REAL (não mockado)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import pytz
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)
from services.event_service_async import cancelar_evento, alterar_agendamento
from services.identidade_service import (
    criar_ator_dono,
    criar_ator_cliente_automatico,
)


FUSO_BR = pytz.timezone("America/Sao_Paulo")


class TestC310Fase2b2Ownership:
    """
    Testes de ownership para operações multi-tenant.
    Validam que tenant_id é a fronteira de isolamento.
    """

    @pytest.mark.asyncio
    async def test_t1_cliente_cancela_evento_seu(self):
        """
        T1: Cliente de tenantA pode cancelar seu próprio evento.
        Esperado: Cancelamento bem-sucedido.
        """
        tenant_a = "tenant_teste_2b2_t1"
        cliente_a_id = "whatsapp:11988888881"

        try:
            # Setup: Criar cliente em tenantA
            await criar_ator_cliente_automatico(
                tenant_id=tenant_a,
                canal="whatsapp",
                identificador="11988888881",
                nome_detectado="Cliente A"
            )

            # Salvar cliente documento (necessário para buscar_cliente)
            await salvar_dado_em_path(
                f"Clientes/{tenant_a}/Clientes/{cliente_a_id}",
                {
                    "id_negocio": tenant_a,
                    "nome": "Cliente A",
                    "ativo": True,
                }
            )

            # Criar evento para o cliente em tenantA
            event_id = "evento_teste_2b2_t1"
            now_iso = datetime.now(FUSO_BR).isoformat()
            await salvar_dado_em_path(
                f"Clientes/{tenant_a}/Eventos/{event_id}",
                {
                    "event_id": event_id,
                    "status": "confirmado",
                    "cliente_id": cliente_a_id,
                    "data": "2026-10-15",
                    "hora_inicio": "14:00",
                    "hora_fim": "15:00",
                    "profissional": "Bruna",
                    "criado_em": now_iso,
                }
            )

            # Cliente A cancela seu próprio evento (deve funcionar)
            resultado = await cancelar_evento(
                user_id=cliente_a_id,
                event_id=event_id,
                tenant_id=tenant_a
            )

            assert resultado is True, f"Cliente de {tenant_a} não conseguiu cancelar seu próprio evento"

        finally:
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Eventos/evento_teste_2b2_t1")
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Clientes/{cliente_a_id}")
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Atores/{cliente_a_id}")

    @pytest.mark.asyncio
    async def test_t2_dono_nao_cancela_evento_outro_tenant(self):
        """
        T2: Dono de tenantA NÃO pode cancelar evento de tenantB.
        Esperado: Cancelamento bloqueado.
        """
        tenant_a = "tenant_teste_2b2_t2a"
        tenant_b = "tenant_teste_2b2_t2b"
        dono_a_id = "whatsapp:11999999992"
        cliente_b_id = "whatsapp:11988888882"

        try:
            # Setup: Criar tenantA com dono
            await criar_ator_dono(
                tenant_id=tenant_a,
                canal="whatsapp",
                identificador="11999999992",
                nome="Dono A",
                email="donoa2@teste.com"
            )

            # Setup: Criar tenantB com cliente
            await criar_ator_cliente_automatico(
                tenant_id=tenant_b,
                canal="whatsapp",
                identificador="11988888882",
                nome_detectado="Cliente B"
            )

            # Salvar cliente documento em tenantB
            await salvar_dado_em_path(
                f"Clientes/{tenant_b}/Clientes/{cliente_b_id}",
                {
                    "id_negocio": tenant_b,
                    "nome": "Cliente B",
                    "ativo": True,
                }
            )

            # Criar evento em tenantB
            event_id = "evento_teste_2b2_t2"
            now_iso = datetime.now(FUSO_BR).isoformat()
            await salvar_dado_em_path(
                f"Clientes/{tenant_b}/Eventos/{event_id}",
                {
                    "event_id": event_id,
                    "status": "confirmado",
                    "cliente_id": cliente_b_id,
                    "data": "2026-10-15",
                    "hora_inicio": "14:00",
                    "hora_fim": "15:00",
                    "profissional": "Bruna",
                    "criado_em": now_iso,
                }
            )

            # Dono A tenta cancelar evento em tenantB (deve falhar)
            # Passa tenant_b explicitamente para que a função saiba onde procurar o evento
            resultado = await cancelar_evento(
                user_id=dono_a_id,
                event_id=event_id,
                tenant_id=tenant_b
            )

            assert resultado is False, f"Dono de {tenant_a} conseguiu cancelar evento de {tenant_b} (cross-tenant!)"

        finally:
            await deletar_dado_em_path(f"Clientes/{tenant_b}/Eventos/evento_teste_2b2_t2")
            await deletar_dado_em_path(f"Clientes/{tenant_b}/Clientes/{cliente_b_id}")
            await deletar_dado_em_path(f"Clientes/{tenant_b}/Atores/{cliente_b_id}")
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Atores/{dono_a_id}")

    @pytest.mark.asyncio
    async def test_t3_dono_altera_evento_seu_tenant(self):
        """
        T3: Dono de tenantA pode alterar evento de tenantA.
        Esperado: Alteração bem-sucedida.
        """
        tenant_a = "tenant_teste_2b2_t3"
        dono_a_id = "whatsapp:11999999993"
        cliente_a_id = "whatsapp:11988888883"

        try:
            # Setup
            await criar_ator_dono(
                tenant_id=tenant_a,
                canal="whatsapp",
                identificador="11999999993",
                nome="Dono A",
                email="donoa3@teste.com"
            )

            await criar_ator_cliente_automatico(
                tenant_id=tenant_a,
                canal="whatsapp",
                identificador="11988888883",
                nome_detectado="Cliente A"
            )

            await salvar_dado_em_path(
                f"Clientes/{tenant_a}/Clientes/{cliente_a_id}",
                {
                    "id_negocio": tenant_a,
                    "nome": "Cliente A",
                    "ativo": True,
                }
            )

            # Criar evento
            event_id = "evento_teste_2b2_t3"
            now_iso = datetime.now(FUSO_BR).isoformat()
            await salvar_dado_em_path(
                f"Clientes/{tenant_a}/Eventos/{event_id}",
                {
                    "event_id": event_id,
                    "status": "confirmado",
                    "cliente_id": cliente_a_id,
                    "data": "2026-10-15",
                    "hora_inicio": "14:00",
                    "hora_fim": "15:00",
                    "profissional": "Bruna",
                    "criado_em": now_iso,
                }
            )

            # Dono A altera evento (deve funcionar)
            resultado = await alterar_agendamento(
                user_id=dono_a_id,
                event_id=event_id,
                nova_data="2026-10-16",
                nova_hora_inicio="15:00",
                nova_duracao_minutos=60,
                tenant_id=tenant_a
            )

            assert resultado.get("ok") is True, f"Dono de {tenant_a} não conseguiu alterar evento de {tenant_a}: {resultado}"

        finally:
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Eventos/evento_teste_2b2_t3")
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Clientes/{cliente_a_id}")
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Atores/{dono_a_id}")
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Atores/{cliente_a_id}")

    @pytest.mark.asyncio
    async def test_t4_dono_nao_altera_evento_outro_tenant(self):
        """
        T4: Dono de tenantA NÃO pode alterar evento de tenantB.
        Esperado: Alteração bloqueada.
        """
        tenant_a = "tenant_teste_2b2_t4a"
        tenant_b = "tenant_teste_2b2_t4b"
        dono_a_id = "whatsapp:11999999994"
        cliente_b_id = "whatsapp:11988888884"

        try:
            # Setup
            await criar_ator_dono(
                tenant_id=tenant_a,
                canal="whatsapp",
                identificador="11999999994",
                nome="Dono A",
                email="donoa4@teste.com"
            )

            await criar_ator_cliente_automatico(
                tenant_id=tenant_b,
                canal="whatsapp",
                identificador="11988888884",
                nome_detectado="Cliente B"
            )

            await salvar_dado_em_path(
                f"Clientes/{tenant_b}/Clientes/{cliente_b_id}",
                {
                    "id_negocio": tenant_b,
                    "nome": "Cliente B",
                    "ativo": True,
                }
            )

            # Criar evento em tenantB
            event_id = "evento_teste_2b2_t4"
            now_iso = datetime.now(FUSO_BR).isoformat()
            await salvar_dado_em_path(
                f"Clientes/{tenant_b}/Eventos/{event_id}",
                {
                    "event_id": event_id,
                    "status": "confirmado",
                    "cliente_id": cliente_b_id,
                    "data": "2026-10-15",
                    "hora_inicio": "14:00",
                    "hora_fim": "15:00",
                    "profissional": "Bruna",
                    "criado_em": now_iso,
                }
            )

            # Dono A tenta alterar evento em tenantB (deve falhar)
            resultado = await alterar_agendamento(
                user_id=dono_a_id,
                event_id=event_id,
                nova_data="2026-10-16",
                nova_hora_inicio="15:00",
                nova_duracao_minutos=60,
                tenant_id=tenant_b
            )

            assert resultado.get("ok") is False, f"Dono de {tenant_a} conseguiu alterar evento de {tenant_b} (cross-tenant!)"
            assert "outro tenant" in resultado.get("motivo", "").lower(), f"Mensagem de erro inadequada: {resultado}"

        finally:
            await deletar_dado_em_path(f"Clientes/{tenant_b}/Eventos/evento_teste_2b2_t4")
            await deletar_dado_em_path(f"Clientes/{tenant_b}/Clientes/{cliente_b_id}")
            await deletar_dado_em_path(f"Clientes/{tenant_b}/Atores/{cliente_b_id}")
            await deletar_dado_em_path(f"Clientes/{tenant_a}/Atores/{dono_a_id}")
