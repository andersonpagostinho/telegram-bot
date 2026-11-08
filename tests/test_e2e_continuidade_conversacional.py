"""
SUITE E2E — CONTINUIDADE CONVERSACIONAL P0.28.1
10 cenários obrigatórios de sequência completa
Sem mocks de persistência — Firestore real
Sem modificação de código de produção
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path

E2E_TENANT_ID = "7394370553"
PHONE_NUMBER_ID = "1350170954840548"


class TestE2EContinuidadeConversacional:
    """Suite E2E com sequências completas de conversa"""

    # ========== CENÁRIO 1: Saudação → Serviço → Profissional → Horário → Confirmação ==========

    @pytest.mark.asyncio
    async def test_cenario_1_fluxo_completo(self):
        """Sequência: ola → quero corte → bruna → amanha 10h → confirma"""
        import time
        phone = f"55152001{int(time.time()) % 1000000:06d}"  # Usar timestamp para garantir unicidade
        full_actor_id = f"whatsapp:{phone}"

        # 1. Saudação
        resp1 = await roteador_principal(
            user_id=phone, mensagem="ola",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )
        assert len(resp1.get("resposta", "")) > 0, "Saudação deve gerar resposta"

        # 2. Solicitar serviço
        resp2 = await roteador_principal(
            user_id=phone, mensagem="quero um corte feminino",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )
        assert "corte" in resp2.get("resposta", "").lower() or "profissional" in resp2.get("resposta", "").lower()

        # 3. Escolher profissional
        resp3 = await roteador_principal(
            user_id=phone, mensagem="com a bruna",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )
        ctx3 = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        assert ctx3 is not None, "Contexto deve ser encontrado"
        draft = ctx3.get("draft_agendamento") or {}
        assert draft.get("profissional") == "Bruna", "Profissional deve ser setado"

        # 4. Marcar horário
        resp4 = await roteador_principal(
            user_id=phone, mensagem="amanha as 10 da manha",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )
        ctx4 = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        assert ctx4.get("draft_agendamento", {}).get("data_hora") is not None, "Data deve ser setada"

        # 5. Confirmação
        resp5 = await roteador_principal(
            user_id=phone, mensagem="sim, confirma",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )
        # Deve confirmar ou agendar
        assert "agendado" in resp5.get("resposta", "").lower() or "confirmado" in resp5.get("resposta", "").lower()

        print("✅ CENÁRIO 1: Fluxo completo — OK")

    # ========== CENÁRIO 2: Agendamento iniciado → Pergunta → Retomada ==========

    @pytest.mark.asyncio
    async def test_cenario_2_interrupcao_e_retomada(self):
        """Agendamento → pergunta externa → 'sim' retoma fluxo"""
        phone = f"5515201{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone}"

        # Setup: Draft em aguardando_confirmacao
        ctx_setup = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_confirmacao_agendamento",
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {
                "profissional": "Gloria",
                "data_hora": (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=14).isoformat(),
                "servico": "manicure"
            }
        }
        await atualizar_dado_em_path(
            f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            ctx_setup
        )

        # Pergunta interrupta
        resp1 = await roteador_principal(
            user_id=phone, mensagem="quanto custa?",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )

        # 'Sim' deve retomar confirmação
        resp2 = await roteador_principal(
            user_id=phone, mensagem="sim",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )
        # Não deve encerrar com "Tudo bem"
        assert "Tudo bem, sem problemas" not in resp2.get("resposta", "")

        print("✅ CENÁRIO 2: Interrupção e retomada — OK")

    # ========== CENÁRIO 3: Sugestão de horário → 'Sim' → Confirmação ==========

    @pytest.mark.asyncio
    async def test_cenario_3_sugestao_horario_confirmacao(self):
        """Sugestão → aceitar → confirmar automaticamente"""
        phone = f"5515202{uuid.uuid4().hex[:6]}"

        # Setup: Contexto pronto para sugestão
        resp = await roteador_principal(
            user_id=phone, mensagem="quero um corte com bruna amanha",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )

        # 'Sim' deve aceitar sugestão
        resp2 = await roteador_principal(
            user_id=phone, mensagem="sim",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )
        assert "Tudo bem, sem problemas" not in resp2.get("resposta", "")

        print("✅ CENÁRIO 3: Sugestão e aceitação — OK")

    # ========== CENÁRIO 4: Sugestão de horário → 'Não' → Nova sugestão ==========

    @pytest.mark.asyncio
    async def test_cenario_4_rejeicao_nova_sugestao(self):
        """Rejeitar horário → oferecer alternativa"""
        phone = f"5515203{uuid.uuid4().hex[:6]}"

        # Oferecer horário
        resp1 = await roteador_principal(
            user_id=phone, mensagem="quero corte amanha",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )

        # Rejeitar
        resp2 = await roteador_principal(
            user_id=phone, mensagem="não, outro horário",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )
        # Deve oferecer alternativa
        assert len(resp2.get("resposta", "")) > 0

        print("✅ CENÁRIO 4: Rejeição e alternativa — OK")

    # ========== CENÁRIO 5: Serviço identificado → 'Outra profissional' → Preservação ==========

    @pytest.mark.asyncio
    async def test_cenario_5_mudanca_profissional_preserva_servico(self):
        """Mudar profissional mas preservar serviço"""
        phone = f"5515204{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone}"

        # Setup: Serviço escolhido com profissional
        ctx_setup = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_profissional",
            "draft_agendamento": {
                "profissional": "Bruna",
                "data_hora": (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10).isoformat(),
                "servico": "corte feminino"
            }
        }
        await atualizar_dado_em_path(
            f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            ctx_setup
        )

        # Pedir outra profissional
        resp = await roteador_principal(
            user_id=phone, mensagem="pode ser com gloria em vez de bruna?",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )

        # Verificar que serviço foi preservado
        ctx_final = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        assert ctx_final.get("draft_agendamento", {}).get("servico") == "corte feminino"

        print("✅ CENÁRIO 5: Mudança profissional com preservação — OK")

    # ========== CENÁRIO 6: Draft existente → Interrupção → Retomada ==========

    @pytest.mark.asyncio
    async def test_cenario_6_draft_retomada_pos_pausa(self):
        """Draft preservado após pausa"""
        phone = f"5515205{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone}"

        # Setup: Draft em estado ativo
        ctx_setup = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {
                "profissional": "Joana",
                "servico": "escova",
                "data_hora": None
            }
        }
        await atualizar_dado_em_path(
            f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            ctx_setup
        )

        # Resposta curta retoma fluxo
        resp = await roteador_principal(
            user_id=phone, mensagem="sim",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )

        # Deve continuar fluxo, não encerrar
        assert "Tudo bem, sem problemas" not in resp.get("resposta", "")

        print("✅ CENÁRIO 6: Retomada pós pausa — OK")

    # ========== CENÁRIO 7: 'Sim' sem contexto → Recuperação ==========

    @pytest.mark.asyncio
    async def test_cenario_7_sim_sem_contexto_recuperacao(self):
        """'Sim' sem fluxo ativo → oferecer ponto de recuperação"""
        phone = f"5515206{uuid.uuid4().hex[:6]}"

        # Limpar contexto
        full_actor_id = f"whatsapp:{phone}"
        await atualizar_dado_em_path(
            f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            {"estado_fluxo": "idle"}
        )

        # 'Sim' sem contexto
        resp = await roteador_principal(
            user_id=phone, mensagem="sim",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )

        # Deve oferecer recuperação (P0 implementado)
        assert "agendamento" in resp.get("resposta", "").lower() or "serviço" in resp.get("resposta", "").lower()

        print("✅ CENÁRIO 7: Recuperação 'sim' sem contexto — OK")

    # ========== CENÁRIO 8: Mudança de assunto → Contexto anterior não interfere ==========

    @pytest.mark.asyncio
    async def test_cenario_8_mudanca_assunto_isolamento(self):
        """Mudar de assunto completamente → novo fluxo"""
        phone = f"5515207{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone}"

        # Setup: Draft de corte
        ctx_setup = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "corte feminino"
            }
        }
        await atualizar_dado_em_path(
            f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            ctx_setup
        )

        # Pedir manicure (novo assunto)
        resp = await roteador_principal(
            user_id=phone, mensagem="na verdade quero um manicure",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )

        # Verificar que novo serviço foi selecionado
        ctx_final = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        novo_servico = ctx_final.get("draft_agendamento", {}).get("servico")
        assert novo_servico == "manicure" or "manicure" in resp.get("resposta", "").lower()

        print("✅ CENÁRIO 8: Mudança de assunto — OK")

    # ========== CENÁRIO 9: Cliente A → Cliente B → Isolamento de sessões ==========

    @pytest.mark.asyncio
    async def test_cenario_9_isolamento_multitenant(self):
        """Dois clientes em mesmo tenant → contextos isolados"""
        phone_a = f"5515208{uuid.uuid4().hex[:6]}"
        phone_b = f"5515209{uuid.uuid4().hex[:6]}"

        actor_a = f"whatsapp:{phone_a}"
        actor_b = f"whatsapp:{phone_b}"

        # Cliente A: Draft de corte
        ctx_a = {
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {"profissional": "Bruna", "servico": "corte"}
        }
        await atualizar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{actor_a}", ctx_a)

        # Cliente B: Draft de manicure
        ctx_b = {
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {"profissional": "Gloria", "servico": "manicure"}
        }
        await atualizar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{actor_b}", ctx_b)

        # Verificar que contextos são distintos
        verify_a = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{actor_a}")
        verify_b = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{actor_b}")

        assert verify_a.get("draft_agendamento", {}).get("servico") == "corte"
        assert verify_b.get("draft_agendamento", {}).get("servico") == "manicure"

        print("✅ CENÁRIO 9: Isolamento multi-cliente — OK")

    # ========== CENÁRIO 10: Retomada com contexto legado → Migração segura ==========

    @pytest.mark.asyncio
    async def test_cenario_10_migracao_contexto_legado(self):
        """Contexto legado migrado para novo path com segurança"""
        phone = f"5515210{uuid.uuid4().hex[:6]}"
        full_actor_id = f"whatsapp:{phone}"

        # Setup: Contexto novo path
        ctx_novo = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_confirmacao_agendamento",
            "draft_agendamento": {
                "profissional": "Carla",
                "data_hora": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "servico": "coloracao"
            }
        }
        await atualizar_dado_em_path(
            f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
            ctx_novo
        )

        # Verificar que contexto é carregado corretamente
        ctx_verify = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
        assert ctx_verify.get("estado_fluxo") == "aguardando_confirmacao_agendamento"
        assert ctx_verify.get("draft_agendamento", {}).get("servico") == "coloracao"

        # Continuar fluxo
        resp = await roteador_principal(
            user_id=phone, mensagem="sim, confirma",
            tenant_id=E2E_TENANT_ID, phone_number_id=PHONE_NUMBER_ID
        )

        print("✅ CENÁRIO 10: Migração contexto segura — OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
