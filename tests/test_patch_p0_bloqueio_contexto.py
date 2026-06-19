"""
PATCH P0 — Bloqueio de Contexto Legado Sem Tenant

10 testes obrigatórios validando isolamento multi-tenant.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime


@pytest.mark.asyncio
class TestBloqueioContextoSemTenant:
    """Testes para Patch P0 — bloqueio de contexto sem tenant_id"""

    async def test_01_carregar_sem_tenant_id_retorna_vazio(self):
        """
        TEST 1: carregar sem tenant_id retorna {}
        Entrada: actor_id="user_123", tenant_id=None
        Esperado: {} (vazio)
        """
        from utils.contexto_temporario import carregar_contexto_temporario

        with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
            mock_buscar.return_value = {"draft_agendamento": {"servico": "corte"}}

            resultado = await carregar_contexto_temporario(
                user_id="user_123",
                tenant_id=None  # ← SEM TENANT
            )

        # Validar: retorna {} bloqueado
        assert resultado == {}, f"Esperava {{}}, obtive {resultado}"

    async def test_02_salvar_sem_tenant_id_retorna_false(self):
        """
        TEST 2: salvar sem tenant_id retorna False
        Entrada: user_id="user_123", contexto={...}, tenant_id=None
        Esperado: False (não salva)
        """
        from utils.contexto_temporario import salvar_contexto_temporario

        resultado = await salvar_contexto_temporario(
            user_id="user_123",
            contexto={"draft_agendamento": {"servico": "corte"}},
            tenant_id=None  # ← SEM TENANT
        )

        # Validar: retorna False
        assert resultado == False or resultado is False, \
            f"Esperava False, obtive {resultado}"

    async def test_03_salvar_com_tenant_grava_no_novo_path(self):
        """
        TEST 3: salvar com tenant_id grava em Clientes/{tenant_id}/Sessoes/{actor_id}
        Entrada: actor_id="user_123", contexto={...}, tenant_id="dono_456"
        Esperado: gravado em path novo
        """
        from utils.contexto_temporario import salvar_sessao_temporaria

        with patch("utils.contexto_temporario.atualizar_dado_em_path") as mock_salvar, \
             patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:

            mock_buscar.return_value = {}
            mock_salvar.return_value = True

            resultado = await salvar_sessao_temporaria(
                actor_id="user_123",
                contexto={"draft_agendamento": {"servico": "corte"}},
                tenant_id="dono_456"
            )

        # Validar: chamou atualizar_dado_em_path com path correto
        assert mock_salvar.called, "Não chamou atualizar_dado_em_path"
        call_path = mock_salvar.call_args[0][0]
        assert "dono_456" in call_path, f"Path não contém tenant: {call_path}"
        assert "Sessoes" in call_path, f"Path não usa Sessoes: {call_path}"

    async def test_04_carregar_com_tenant_le_do_novo_path(self):
        """
        TEST 4: carregar com tenant_id lê do path novo
        Entrada: actor_id="user_123", tenant_id="dono_456"
        Esperado: lê de Clientes/{tenant_id}/Sessoes/{actor_id}
        """
        from utils.contexto_temporario import carregar_sessao_temporaria

        contexto_esperado = {
            "draft_agendamento": {"servico": "corte"},
            "_tenant_id_guard": "dono_456"
        }

        with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
            mock_buscar.return_value = contexto_esperado

            resultado = await carregar_sessao_temporaria(
                actor_id="user_123",
                tenant_id="dono_456"
            )

        # Validar: retorna contexto do novo path
        assert resultado == contexto_esperado, \
            f"Esperava {contexto_esperado}, obtive {resultado}"

    async def test_05_legado_sem_guard_tenant_nao_retorna(self):
        """
        TEST 5: legado sem guard_tenant não é retornado
        Entrada: contexto legado SEM _tenant_id_guard
        Esperado: retorna {} (bloqueado)
        """
        from utils.contexto_temporario import carregar_contexto_temporario

        contexto_legado_sem_guard = {"draft_agendamento": {"servico": "corte"}}

        with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
            mock_buscar.return_value = contexto_legado_sem_guard

            resultado = await carregar_contexto_temporario(
                user_id="user_123",
                tenant_id="dono_456"
            )

        # Validar: retorna {} (bloqueado)
        assert resultado == {}, \
            f"Esperava bloqueio {{}} para legado sem guard, obtive {resultado}"

    async def test_06_legado_com_guard_diferente_nao_retorna(self):
        """
        TEST 6: legado com guard_tenant diferente não é retornado
        Entrada: contexto com guard_tenant="dono_OUTRO"
        Esperado: retorna {} (bloqueado)
        """
        from utils.contexto_temporario import carregar_contexto_temporario

        contexto_legado_outro_tenant = {
            "draft_agendamento": {"servico": "corte"},
            "_tenant_id_guard": "dono_OUTRO"
        }

        with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
            mock_buscar.return_value = contexto_legado_outro_tenant

            resultado = await carregar_contexto_temporario(
                user_id="user_123",
                tenant_id="dono_456"
            )

        # Validar: retorna {} (bloqueado por mismatch)
        assert resultado == {}, \
            f"Esperava bloqueio {{}} para tenant mismatch, obtive {resultado}"

    async def test_07_legado_com_guard_igual_migrado(self):
        """
        TEST 7: legado com guard_tenant igual é migrado para V2
        Entrada: contexto legado com guard_tenant == tenant_id
        Esperado: copiado para Clientes/{tenant_id}/Sessoes/{actor_id}
        """
        from utils.contexto_temporario import carregar_sessao_temporaria

        contexto_legado_valido = {
            "draft_agendamento": {"servico": "corte"},
            "_tenant_id_guard": "dono_456"
        }

        with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar, \
             patch("utils.contexto_temporario.atualizar_dado_em_path") as mock_salvar:

            # Primeiro retorna vazio no novo, depois retorna legado
            mock_buscar.side_effect = [None, contexto_legado_valido]
            mock_salvar.return_value = True

            resultado = await carregar_sessao_temporaria(
                actor_id="user_123",
                tenant_id="dono_456"
            )

        # Validar: chamou atualizar para migrar
        assert mock_salvar.called, "Não migrou contexto legado"
        assert resultado is not None, "Deve retornar contexto migrado"

    async def test_08_actor_id_igual_dois_tenants_diferentes_nao_mistura(self):
        """
        TEST 8: actor_id igual em dois tenants diferentes não mistura sessão
        Cenário:
        - Cliente A (dono_A) com actor_id = 7371670478
        - Cliente B (dono_B) com actor_id = 7371670478
        Esperado: contextos isolados por tenant
        """
        from utils.contexto_temporario import carregar_sessao_temporaria

        contexto_a = {"telefone": "123", "endereco": "Rua A"}
        contexto_b = {"telefone": "456", "endereco": "Rua B"}

        # Mock retorna contextos diferentes para cada tenant
        async def mock_buscar_isolado(path):
            if "dono_A" in path:
                return contexto_a
            elif "dono_B" in path:
                return contexto_b
            return None

        with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
            mock_buscar.side_effect = mock_buscar_isolado

            # Lê para cliente A
            resultado_a = await carregar_sessao_temporaria(
                actor_id="7371670478",
                tenant_id="dono_A"
            )

            # Lés para cliente B
            resultado_b = await carregar_sessao_temporaria(
                actor_id="7371670478",
                tenant_id="dono_B"
            )

        # Validar: não misturam
        assert resultado_a != resultado_b, \
            "CRITÉRIO P0 FALHOU: clientes A e B estão vendo dados um do outro!"

    async def test_09_fluxo_cancelamento_continua_lendo_estado(self):
        """
        TEST 9: fluxo cancelamento continua lendo estado correto
        Simula: User carrega contexto com state "aguardando_confirmacao_cancelamento"
        Esperado: lê e retorna estado com sucesso
        """
        from utils.contexto_temporario import carregar_sessao_temporaria

        contexto_cancelamento = {
            "estado_fluxo": "aguardando_confirmacao_cancelamento",
            "cancelamento_pendente": {"evento_id": "ev_001"},
            "_tenant_id_guard": "dono_456"
        }

        with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
            mock_buscar.return_value = contexto_cancelamento

            resultado = await carregar_sessao_temporaria(
                actor_id="user_123",
                tenant_id="dono_456"
            )

        # Validar: fluxo de cancelamento funciona
        assert resultado.get("estado_fluxo") == "aguardando_confirmacao_cancelamento", \
            "Não retornou estado de cancelamento"
        assert resultado.get("cancelamento_pendente") is not None, \
            "Não retornou cancelamento_pendente"

    async def test_10_fluxo_agendamento_continua_lendo_draft(self):
        """
        TEST 10: fluxo agendamento continua lendo draft correto
        Simula: User carrega contexto com draft_agendamento
        Esperado: lê e retorna draft com sucesso
        """
        from utils.contexto_temporario import carregar_sessao_temporaria

        contexto_agendamento = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-06-20T14:00:00"
            },
            "_tenant_id_guard": "dono_456"
        }

        with patch("utils.contexto_temporario.buscar_dado_em_path") as mock_buscar:
            mock_buscar.return_value = contexto_agendamento

            resultado = await carregar_sessao_temporaria(
                actor_id="user_123",
                tenant_id="dono_456"
            )

        # Validar: fluxo de agendamento funciona
        assert resultado.get("draft_agendamento") is not None, \
            "Não retornou draft_agendamento"
        assert resultado["draft_agendamento"]["profissional"] == "Bruna", \
            "Draft corrompido"
        assert resultado["draft_agendamento"]["servico"] == "Corte", \
            "Draft corrompido"
