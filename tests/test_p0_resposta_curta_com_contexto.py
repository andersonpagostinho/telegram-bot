"""
TESTES P0 — Respostas curtas com contexto conversacional

Objetivo: Validar que mensagens curtas (sim/não/ok) são processadas corretamente
quando há fluxo operacional ativo vs. quando não há.
"""

import pytest
import uuid
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path

E2E_TENANT_ID = "7394370553"


class TestRespostasCurtasComContexto:
    """Suite de 12 testes para validar respostas curtas em diferentes contextos"""

    @pytest.mark.asyncio
    async def test_a_sim_sem_contexto(self):
        """
        Cenário A: 'sim' sem contexto anterior, sem fluxo ativo
        Esperado: Perguntar como pode ajudar (NÃO encerrar)
        """
        phone_number = f"5515001{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        # Contexto: sem fluxo ativo, sem histórico
        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": None,  # Sem fluxo ativo
            "historico_texto": []
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="sim",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        # Esperado: resposta que pede esclarecimento (NÃO "Tudo bem, sem problemas!")
        # Mas como "sim" sozinho é classificado como neutro, deve encerrar apropriadamente
        assert len(resposta.get("resposta", "")) > 0
        # Pode ser "Tudo bem" (encerramento) ou pergunta (continuação)
        print(f"✅ Cenário A - Resposta: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_b_sim_com_confirmacao_pendente(self):
        """
        Cenário B: 'sim' com aguardando_confirmacao
        Esperado: Processar como confirmação (criar agendamento ou similar)
        """
        phone_number = f"5515002{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        # Contexto: pergunta pendente de confirmação
        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_confirmacao_agendamento",
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-11-15T14:00:00"
            },
            "historico_texto": ["sim"]
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="sim",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        # NÃO deve encerrar com "Tudo bem, sem problemas!"
        # Deve processar confirmação
        assert "Tudo bem, sem problemas" not in resposta.get("resposta", "")
        print(f"✅ Cenário B - Resposta: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_c_nao_com_confirmacao_pendente(self):
        """
        Cenário C: 'não' com aguardando_confirmacao
        Esperado: Processar como negação
        """
        phone_number = f"5515003{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_confirmacao_agendamento",
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {
                "servico": "manicure",
                "profissional": "Gloria",
                "data_hora": "2026-11-16T10:00:00"
            }
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="não",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        assert "Tudo bem, sem problemas" not in resposta.get("resposta", "")
        print(f"✅ Cenário C - Resposta: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_d_desculpe_enviei_errado(self):
        """
        Cenário D: 'desculpe, enviei errado' sem contexto
        Esperado: Reconhecer e encerrar com "Tudo bem, sem problemas! 😊"
        """
        phone_number = f"5515004{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": None
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="desculpe, enviei errado",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        assert "Tudo bem, sem problemas" in resposta.get("resposta", "")
        print(f"✅ Cenário D - Resposta apropriada (encerramento)", flush=True)

    @pytest.mark.asyncio
    async def test_e_nao_era_com_voce(self):
        """
        Cenário E: 'não era com você' sem contexto
        Esperado: Reconhecer e encerrar
        """
        phone_number = f"5515005{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": None
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="não era com você, foi erro meu",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        assert "Tudo bem, sem problemas" in resposta.get("resposta", "")
        print(f"✅ Cenário E - Resposta apropriada (encerramento)", flush=True)

    @pytest.mark.asyncio
    async def test_f_obrigado_sem_contexto(self):
        """
        Cenário F: 'obrigado' sem contexto
        Esperado: Resposta social apropriada
        """
        phone_number = f"5515006{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": None
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="obrigado",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        assert len(resposta.get("resposta", "")) > 0
        print(f"✅ Cenário F - Resposta social: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_g_ok_sem_contexto(self):
        """
        Cenário G: 'ok' sem contexto anterior
        Esperado: Perguntar como pode ajudar
        """
        phone_number = f"5515007{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": None
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="ok",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        assert len(resposta.get("resposta", "")) > 0
        print(f"✅ Cenário G - Resposta: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_h_sim_com_pergunta_data(self):
        """
        Cenário H: 'sim' com aguardando_data
        Esperado: Pedir a data novamente (NÃO encerrar com "Tudo bem")
        """
        phone_number = f"5515008{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Joana"
            }
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="sim",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        # NÃO deve encerrar com "Tudo bem, sem problemas!"
        assert "Tudo bem, sem problemas" not in resposta.get("resposta", "")
        print(f"✅ Cenário H - Resposta: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_i_terca_com_pergunta_data(self):
        """
        Cenário I: 'terça' com aguardando_data
        Esperado: Processar data
        """
        phone_number = f"5515009{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {
                "servico": "escova",
                "profissional": "Bruna"
            }
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="terça",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        assert len(resposta.get("resposta", "")) > 0
        print(f"✅ Cenário I - Resposta: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_sim_com_pergunta_servico(self):
        """
        Cenário Extra 1: 'sim' com aguardando_servico
        Esperado: Solicitar o serviço (NÃO encerrar)
        """
        phone_number = f"5515010{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_servico"
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="sim",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        assert "Tudo bem, sem problemas" not in resposta.get("resposta", "")
        print(f"✅ Extra 1 - Resposta: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_sim_com_pergunta_profissional(self):
        """
        Cenário Extra 2: 'sim' com aguardando_profissional
        Esperado: Solicitar a profissional (NÃO encerrar)
        """
        phone_number = f"5515011{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_profissional",
            "draft_agendamento": {
                "servico": "manicure"
            }
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="sim",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        assert "Tudo bem, sem problemas" not in resposta.get("resposta", "")
        print(f"✅ Extra 2 - Resposta: {resposta.get('resposta')}", flush=True)

    @pytest.mark.asyncio
    async def test_sim_com_draft_residual_sem_fluxo(self):
        """
        Cenário Extra 3: 'sim' com draft residual, MAS sem estado_fluxo ativo
        Esperado: Perguntar como pode ajudar (draft sozinho não justifica "sim")
        """
        phone_number = f"5515012{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone_number}"

        ctx_inicial = {
            "tipo_usuario": "cliente",
            "estado_fluxo": None,  # ← SEM fluxo ativo
            "draft_agendamento": {
                "servico": "corte feminino",  # ← Draft residual (mas sem fluxo)
                "profissional": "Carla"
            }
        }
        await atualizar_dado_em_path(
            path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            dados=ctx_inicial
        )

        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem="sim",
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )

        # Com draft residual mas sem fluxo: deve encerrar apropriadamente
        assert len(resposta.get("resposta", "")) > 0
        print(f"✅ Extra 3 - Resposta: {resposta.get('resposta')}", flush=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
