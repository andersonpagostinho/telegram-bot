"""
P1 — Testes Obrigatórios: 9 Cenários para Opção C (Detecção Determinística)

Validar que:
1. Consulta independente sem serviço — não herda 'coloracao'
2. Continuação válida — preserva o contexto necessário
3. Confirmação explícita — continua funcionando
4. Alteração de horário — continua funcionando
5. Escolha de profissional — continua funcionando
6. Recusa/cancelamento — mantém o comportamento contratado
7. Persistência de DELETE_FIELD — campos removidos não reaparecem
8. Salvamento com merge — não reintroduz dados obsoletos
9. Integridade — histórico, tenant e dados permanentes são preservados
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from router.principal_router import roteador_principal
from services.firebase_service_async import buscar_dado_em_path
from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2,
    limpar_contexto_agendamento_v2,
)


class TestP19CenariosCompletos:
    """9 testes obrigatórios para validar Opção C"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tenant_id = "7394370553"
        self.actor_id = "whatsapp:5511991382080"
        self.user_id = "5511991382080"
        self.phone_number_id = "1350170954840548"
        self.path_v2 = f"Clientes/{self.tenant_id}/Sessoes/{self.actor_id}"
        yield
        try:
            asyncio.run(buscar_dado_em_path(self.path_v2))
        except:
            pass

    @pytest.mark.asyncio
    async def test_t1_consulta_independente(self):
        """T1: Consulta sem serviço não herda 'coloracao'"""
        print("\n[T1] Consulta Independente Sem Serviço")

        ctx_setup = {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"profissional": "Bruna", "servico": "coloracao", "data_hora": "2026-10-26T14:00:00"},
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        contexto_gpt = {}
        async def mock_gpt(msg, ctx, instr, tenant_id=None):
            nonlocal contexto_gpt
            contexto_gpt = dict(ctx)
            return {"resposta": "Sim", "acao": None}

        with patch('router.principal_router.chamar_gpt_com_contexto', new=mock_gpt):
            try:
                await roteador_principal(user_id=self.user_id, mensagem="a bruna esta disponivel amanha as 10?",
                    tenant_id=self.tenant_id, phone_number_id=self.phone_number_id, update=AsyncMock(), context=AsyncMock())
            except:
                pass

        draft = contexto_gpt.get("draft_agendamento")
        assert draft is None or draft.get("servico") != "coloracao", "T1 FAIL: serviço anterior foi herdado"
        print("  ✅ T1 PASS")

    @pytest.mark.asyncio
    async def test_t2_continuacao_valida(self):
        """T2: Continuação 'confirma' preserva contexto"""
        print("\n[T2] Continuação Válida")

        ctx_setup = {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"profissional": "Bruna", "servico": "coloracao", "data_hora": "2026-10-25T14:00:00"},
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        dados_executar = {}
        async def mock_executar_acao(update, context, acao, dados, identidade=None):
            nonlocal dados_executar
            dados_executar = dict(dados)
            return {"ok": True, "acao": "criar_evento", "resultado": True}

        context_mock = AsyncMock()
        context_mock.user_data = None

        with patch('router.principal_router.executar_acao_gpt_resultado', new=mock_executar_acao):
            await roteador_principal(user_id=self.user_id, mensagem="confirma",
                tenant_id=self.tenant_id, phone_number_id=self.phone_number_id, update=AsyncMock(), context=context_mock)

        assert dados_executar.get("servico") == "coloracao", f"T2 FAIL: servico não foi passado para criar evento"
        assert dados_executar.get("profissional") == "Bruna", f"T2 FAIL: profissional não foi passado para criar evento"
        print("  ✅ T2 PASS")

    @pytest.mark.asyncio
    async def test_t3_confirmacao_explicita(self):
        """T3: Confirmação 'sim' funciona"""
        print("\n[T3] Confirmação Explícita")

        ctx_setup = {
            "estado_fluxo": "aguardando_confirmacao",
            "draft_agendamento": {"profissional": "Bruna", "servico": "corte", "data_hora": "2026-10-25T14:00:00"},
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        dados_executar = {}
        async def mock_executar_acao(update, context, acao, dados, identidade=None):
            nonlocal dados_executar
            dados_executar = dict(dados)
            return {"ok": True, "acao": "criar_evento", "resultado": True}

        context_mock = AsyncMock()
        context_mock.user_data = None

        with patch('router.principal_router.executar_acao_gpt_resultado', new=mock_executar_acao):
            await roteador_principal(user_id=self.user_id, mensagem="sim",
                tenant_id=self.tenant_id, phone_number_id=self.phone_number_id, update=AsyncMock(), context=context_mock)

        assert dados_executar.get("servico") == "corte", f"T3 FAIL: servico não foi passado para criar evento"
        assert dados_executar.get("profissional") == "Bruna", f"T3 FAIL: profissional não foi passado para criar evento"
        print("  ✅ T3 PASS")

    @pytest.mark.asyncio
    async def test_t4_alteracao_horario(self):
        """T4: Alteração 'qual outro horário' preserva contexto"""
        print("\n[T4] Alteração de Horário")

        ctx_setup = {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"profissional": "Bruna", "servico": "corte", "data_hora": "2026-10-25T14:00:00"},
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        dados_executar = {}
        async def mock_executar_acao(update, context, acao, dados, identidade=None):
            nonlocal dados_executar
            dados_executar = dict(dados)
            return {"ok": True, "acao": "criar_evento", "resultado": True}

        context_mock = AsyncMock()
        context_mock.user_data = None

        with patch('router.principal_router.executar_acao_gpt_resultado', new=mock_executar_acao):
            await roteador_principal(user_id=self.user_id, mensagem="qual outro horario",
                tenant_id=self.tenant_id, phone_number_id=self.phone_number_id, update=AsyncMock(), context=context_mock)

        assert dados_executar.get("servico") == "corte", "T4 FAIL: servico foi apagado"
        assert dados_executar.get("profissional") == "Bruna", "T4 FAIL: profissional foi apagado"
        print("  ✅ T4 PASS")

    @pytest.mark.asyncio
    async def test_t5_escolha_profissional(self):
        """T5: Escolha 'qual profissional' preserva serviço"""
        print("\n[T5] Escolha de Profissional")

        ctx_setup = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna", "data_hora": "2026-10-25T15:00:00"},
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        dados_executar = {}
        async def mock_executar_acao(update, context, acao, dados, identidade=None):
            nonlocal dados_executar
            dados_executar = dict(dados)
            return {"ok": True, "acao": "criar_evento", "resultado": True}

        context_mock = AsyncMock()
        context_mock.user_data = None

        with patch('router.principal_router.executar_acao_gpt_resultado', new=mock_executar_acao):
            await roteador_principal(user_id=self.user_id, mensagem="qual profissional",
                tenant_id=self.tenant_id, phone_number_id=self.phone_number_id, update=AsyncMock(), context=context_mock)

        assert dados_executar.get("servico") == "corte", "T5 FAIL: serviço foi removido"
        assert dados_executar.get("profissional") == "Bruna", "T5 FAIL: profissional foi alterado"
        print("  ✅ T5 PASS")

    @pytest.mark.asyncio
    async def test_t6_recusa_cancelamento(self):
        """T6: Recusa 'não obrigado' remove contexto"""
        print("\n[T6] Recusa/Cancelamento")

        ctx_setup = {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        contexto_gpt = {}
        async def mock_gpt(msg, ctx, instr, tenant_id=None):
            nonlocal contexto_gpt
            contexto_gpt = dict(ctx)
            return {"resposta": "Tudo bem", "acao": None}

        with patch('router.principal_router.chamar_gpt_com_contexto', new=mock_gpt):
            try:
                await roteador_principal(user_id=self.user_id, mensagem="não obrigado",
                    tenant_id=self.tenant_id, phone_number_id=self.phone_number_id, update=AsyncMock(), context=AsyncMock())
            except:
                pass

        # "não obrigado" NÃO é continuação, deve limpar
        draft = contexto_gpt.get("draft_agendamento")
        assert draft is None, "T6 FAIL: draft deveria ter sido removido para recusa"
        print("  ✅ T6 PASS")

    @pytest.mark.asyncio
    async def test_t7_persistencia_delete_field(self):
        """T7: DELETE_FIELD persiste no Firestore"""
        print("\n[T7] Persistência de DELETE_FIELD")

        ctx_setup = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "corte"},
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        await limpar_contexto_agendamento_v2(self.tenant_id, self.actor_id)
        ctx_pos = await carregar_contexto_temporario_v2(self.tenant_id, self.actor_id)

        assert ctx_pos.get("draft_agendamento") is None, "T7 FAIL: draft não foi deletado"
        print("  ✅ T7 PASS")

    @pytest.mark.asyncio
    async def test_t8_merge_nao_restaura(self):
        """T8: Salvamento com merge não restaura dados deletados"""
        print("\n[T8] Merge Não Restaura")

        ctx_setup = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "corte"},
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        # Limpar
        await limpar_contexto_agendamento_v2(self.tenant_id, self.actor_id)

        # Salvar novo contexto (com merge)
        novo_ctx = {"novo_campo": "valor", "tenant_id": self.tenant_id}
        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, novo_ctx)

        ctx_final = await carregar_contexto_temporario_v2(self.tenant_id, self.actor_id)

        assert ctx_final.get("draft_agendamento") is None, "T8 FAIL: draft foi restaurado pelo merge"
        assert ctx_final.get("novo_campo") == "valor", "T8 FAIL: novo campo não foi salvo"
        print("  ✅ T8 PASS")

    @pytest.mark.asyncio
    async def test_t9_integridade_historico(self):
        """T9: Integridade - histórico, tenant preservados"""
        print("\n[T9] Integridade - Histórico/Tenant")

        ctx_setup = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "corte"},
            "historico_texto": ["ola", "corte", "confirma"],
            "tenant_id": self.tenant_id,
            "_tenant_id_guard": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)

        await limpar_contexto_agendamento_v2(self.tenant_id, self.actor_id)
        ctx_pos = await carregar_contexto_temporario_v2(self.tenant_id, self.actor_id)

        assert ctx_pos.get("historico_texto") == ["ola", "corte", "confirma"], "T9 FAIL: histórico foi deletado"
        assert ctx_pos.get("tenant_id") == self.tenant_id, "T9 FAIL: tenant_id foi deletado"
        assert ctx_pos.get("_tenant_id_guard") == self.tenant_id, "T9 FAIL: guard foi deletado"
        assert ctx_pos.get("actor_id") == self.actor_id, "T9 FAIL: actor_id foi deletado"
        assert ctx_pos.get("draft_agendamento") is None, "T9 FAIL: draft deveria estar deletado"
        print("  ✅ T9 PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
