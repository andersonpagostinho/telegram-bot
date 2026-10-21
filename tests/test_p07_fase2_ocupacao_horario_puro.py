"""
[P0.7 FASE 2] Testes de Consulta de Ocupação SEM Duração
Valida que a função consultar_ocupacao_horario_exato() verifica
se um horário específico está ocupado, sem presumir duração.

Restrições:
- Sem estimar_duracao(None)
- Sem aritmética com duração presumida
- Cancelados não bloqueiam
- Isolamento multi-tenant
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.event_service_async import (
    consultar_ocupacao_horario_exato,
    evento_deve_entrar_na_agenda
)


class TestP07Fase2OcupacaoHorarioPuro:
    """FASE 2: Consulta de ocupação sem duração"""

    @pytest.mark.asyncio
    async def test_f2_01_horario_livre_nao_ocupado(self):
        """
        F2.01 — Horário livre não está ocupado

        Cenário: Bruna não tem eventos em 15:00 no dia
        Esperado: ocupado=False, evento=None
        """
        print("\n[F2.01] Horário livre — não ocupado")

        with patch('services.event_service_async.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar_doc:
            with patch('services.event_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar_eventos:

                # Mock: usuário é cliente com id_negocio
                mock_buscar_doc.return_value = {"id_negocio": "tenant_123"}

                # Mock: sem eventos
                mock_buscar_eventos.return_value = {}

                resultado = await consultar_ocupacao_horario_exato(
                    user_id="user_cliente",
                    data="2026-12-19",
                    horario="15:00",
                    profissional="Bruna"
                )

                assert resultado["ocupado"] == False
                assert resultado["evento"] is None
                assert resultado["profissional_normalizado"] == "bruna"

                print("  ✅ F2.01 PASS: Horário livre não está ocupado")

    @pytest.mark.asyncio
    async def test_f2_02_horario_ocupado_detectado(self):
        """
        F2.02 — Horário ocupado por evento existente

        Cenário: Bruna tem evento de 15:00-16:00 em 19/12
        Consulta: 15:00
        Esperado: ocupado=True, evento={...}
        """
        print("\n[F2.02] Horário ocupado — evento encontrado")

        with patch('services.event_service_async.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar_doc:
            with patch('services.event_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar_eventos:

                # Mock: tenant
                mock_buscar_doc.return_value = {"id_negocio": "tenant_123"}

                # Mock: evento de Bruna 15:00-16:00
                mock_buscar_eventos.return_value = {
                    "evt_001": {
                        "data": "2026-12-19",
                        "hora_inicio": "15:00",
                        "hora_fim": "16:00",
                        "profissional": "Bruna",
                        "status": "confirmado",
                        "servico": "corte feminino",
                        "cliente_id": "cliente_123"
                    }
                }

                resultado = await consultar_ocupacao_horario_exato(
                    user_id="user_cliente",
                    data="2026-12-19",
                    horario="15:00",
                    profissional="Bruna"
                )

                assert resultado["ocupado"] == True
                assert resultado["evento"] is not None
                assert resultado["evento"]["hora_inicio"] == "15:00"

                print("  ✅ F2.02 PASS: Horário ocupado detectado")

    @pytest.mark.asyncio
    async def test_f2_03_evento_cancelado_nao_bloqueia(self):
        """
        F2.03 — Evento cancelado não bloqueia horário

        Cenário: Bruna tinha evento 15:00-16:00 mas foi cancelado
        Consulta: 15:00
        Esperado: ocupado=False (evento_deve_entrar_na_agenda filtra)
        """
        print("\n[F2.03] Evento cancelado — não bloqueia")

        with patch('services.event_service_async.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar_doc:
            with patch('services.event_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar_eventos:

                mock_buscar_doc.return_value = {"id_negocio": "tenant_123"}

                # Evento cancelado
                mock_buscar_eventos.return_value = {
                    "evt_001": {
                        "data": "2026-12-19",
                        "hora_inicio": "15:00",
                        "hora_fim": "16:00",
                        "profissional": "Bruna",
                        "status": "cancelado",  # CANCELADO
                        "servico": "corte feminino"
                    }
                }

                resultado = await consultar_ocupacao_horario_exato(
                    user_id="user_cliente",
                    data="2026-12-19",
                    horario="15:00",
                    profissional="Bruna"
                )

                assert resultado["ocupado"] == False
                assert resultado["evento"] is None

                print("  ✅ F2.03 PASS: Cancelado não bloqueia")

    @pytest.mark.asyncio
    async def test_f2_04_profissional_diferente_nao_bloqueia(self):
        """
        F2.04 — Evento de outra profissional não bloqueia

        Cenário: Gloria tem evento 15:00-16:00, consulta é para Bruna
        Esperado: ocupado=False (profissional não match)
        """
        print("\n[F2.04] Profissional diferente — não bloqueia")

        with patch('services.event_service_async.buscar_dado_em_path', new_callable=AsyncMock):
            with patch('services.event_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar_eventos:

                # Evento de Gloria
                mock_buscar_eventos.return_value = {
                    "evt_001": {
                        "data": "2026-12-19",
                        "hora_inicio": "15:00",
                        "hora_fim": "16:00",
                        "profissional": "Gloria",  # DIFERENTE
                        "status": "confirmado",
                        "servico": "corte feminino"
                    }
                }

                resultado = await consultar_ocupacao_horario_exato(
                    user_id="user_cliente",
                    data="2026-12-19",
                    horario="15:00",
                    profissional="Bruna"
                )

                assert resultado["ocupado"] == False
                assert resultado["evento"] is None

                print("  ✅ F2.04 PASS: Profissional diferente não bloqueia")

    @pytest.mark.asyncio
    async def test_f2_05_sem_estimacao_duracao(self):
        """
        F2.05 — Verificar que estimar_duracao() NÃO é chamado

        Usa mocking para garantir que a função não chama estimar_duracao(None)
        """
        print("\n[F2.05] Sem estimação de duração")

        with patch('services.event_service_async.buscar_dado_em_path', new_callable=AsyncMock):
            with patch('services.event_service_async.buscar_subcolecao', new_callable=AsyncMock):
                with patch('utils.gpt_utils.estimar_duracao') as mock_estimar:

                    # Se estimar_duracao for chamado, teste falha
                    mock_estimar.side_effect = Exception("estimar_duracao não deve ser chamado!")

                    resultado = await consultar_ocupacao_horario_exato(
                        user_id="user_cliente",
                        data="2026-12-19",
                        horario="15:00",
                        profissional="Bruna"
                    )

                    # Se chegou aqui, estimar_duracao não foi chamado ✅
                    assert resultado is not None

                    print("  ✅ F2.05 PASS: estimar_duracao() não foi chamado")

    def test_f2_06_evento_deve_entrar_na_agenda_cancelado(self):
        """
        F2.06 — evento_deve_entrar_na_agenda filtra cancelados

        Regra já confirmada na auditoria
        """
        print("\n[F2.06] evento_deve_entrar_na_agenda() filtra cancelados")

        evento_cancelado = {
            "data": "2026-12-19",
            "hora_inicio": "15:00",
            "hora_fim": "16:00",
            "profissional": "Bruna",
            "status": "cancelado"
        }

        resultado = evento_deve_entrar_na_agenda("evt_001", evento_cancelado, "2026-12-19")
        assert resultado == False

        print("  ✅ F2.06 PASS: Cancelado é descartado")

    def test_f2_07_evento_deve_entrar_confirmado(self):
        """
        F2.07 — evento_deve_entrar_na_agenda aceita confirmado
        """
        print("\n[F2.07] evento_deve_entrar_na_agenda() aceita confirmado")

        evento_confirmado = {
            "data": "2026-12-19",
            "hora_inicio": "15:00",
            "hora_fim": "16:00",
            "profissional": "Bruna",
            "status": "confirmado"
        }

        resultado = evento_deve_entrar_na_agenda("evt_001", evento_confirmado, "2026-12-19")
        assert resultado == True

        print("  ✅ F2.07 PASS: Confirmado é aceito")

    @pytest.mark.asyncio
    async def test_f2_08_isolamento_multitenant(self):
        """
        F2.08 — Consulta de tenant A não vê eventos de tenant B

        Cenário: tenant_A consulta Bruna 15:00
                 tenant_B tem evento 15:00
        Esperado: ocupado=False (isolation)
        """
        print("\n[F2.08] Isolamento multi-tenant")

        with patch('services.event_service_async.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar_doc:
            with patch('services.event_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar_eventos:

                # Mock: tenant_A
                mock_buscar_doc.return_value = {"id_negocio": "tenant_A"}

                # Path será: Clientes/tenant_A/Eventos
                # Retorna vazio (tenant_A não tem eventos)
                mock_buscar_eventos.return_value = {}

                resultado = await consultar_ocupacao_horario_exato(
                    user_id="user_tenant_A",
                    data="2026-12-19",
                    horario="15:00",
                    profissional="Bruna"
                )

                # Verifica que buscou no path correto (tenant_A)
                mock_buscar_eventos.assert_called_with("Clientes/tenant_A/Eventos")

                assert resultado["ocupado"] == False

                print("  ✅ F2.08 PASS: Isolamento multi-tenant funciona")

    @pytest.mark.asyncio
    async def test_f2_09_horario_final_nao_bloqueado(self):
        """
        F2.09 — Horário final do intervalo não está ocupado

        Convenção: evento 15:00-15:30 bloqueia 15:00, 15:15
                   mas NÃO bloqueia 15:30 (início do próximo slot)

        Cenário: evento 15:00-15:30, consulta 15:30
        Esperado: ocupado=False
        """
        print("\n[F2.09] Horário final não bloqueado (intervalo [ini, fim))")

        with patch('services.event_service_async.buscar_dado_em_path', new_callable=AsyncMock):
            with patch('services.event_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar_eventos:

                mock_buscar_eventos.return_value = {
                    "evt_001": {
                        "data": "2026-12-19",
                        "hora_inicio": "15:00",
                        "hora_fim": "15:30",
                        "profissional": "Bruna",
                        "status": "confirmado",
                        "servico": "corte"
                    }
                }

                # Consulta exatamente no horário final (15:30)
                resultado = await consultar_ocupacao_horario_exato(
                    user_id="user_cliente",
                    data="2026-12-19",
                    horario="15:30",
                    profissional="Bruna"
                )

                # Não deve estar bloqueado (15:30 é [15:00, 15:30) exclusivo no fim)
                assert resultado["ocupado"] == False

                print("  ✅ F2.09 PASS: Horário final não bloqueado")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
