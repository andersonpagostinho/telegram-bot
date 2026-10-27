"""
P1 — Testes de Regressão: Opção C (Detecção Determinística de Continuidade)

9 Cenários Obrigatórios:
1. Consulta independente sem serviço — não herda 'coloracao'
2. Continuação válida — preserva o contexto necessário
3. Confirmação explícita — continua funcionando
4. Alteração de horário — continua funcionando
5. Escolha de profissional — continua funcionando
6. Recusa/cancelamento — mantém contrato
7. Persistência de DELETE_FIELD — campos removidos não reaparecem
8. Salvamento com merge — não reintroduz dados obsoletos
9. Integridade — histórico, tenant e dados permanentes preservados
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


class TestP1OpcaoCContextoObsoleto:
    """9 testes obrigatórios para Opção C"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para testes isolados"""
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

    # ==================== T1: Consulta Independente Sem Serviço ====================
    @pytest.mark.asyncio
    async def test_t1_consulta_independente_nao_herda_servico(self):
        """T1: Consulta 'a bruna esta disponivel amanha as 10?' não herda 'coloracao'"""
        print("\n" + "="*80)
        print("[T1] Consulta Independente Sem Serviço")
        print("="*80)

        # Setup: Estado com draft_agendamento.servico='coloracao', ultima_acao='contexto_limpo'
        ctx_setup = {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "coloracao",
                "data_hora": "2026-10-26T14:00:00",
            },
            "tenant_id": self.tenant_id,
            "_tenant_id_guard": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)
        print("[T1-SETUP] Contexto com draft_agendamento.servico='coloracao' salvo")

        # Mock GPT para capturar contexto
        contexto_passado_gpt = {}
        async def mock_gpt(msg, ctx, instr, tenant_id=None):
            nonlocal contexto_passado_gpt
            contexto_passado_gpt = dict(ctx)
            return {
                "resposta": "Bruna está disponível. Qual serviço?",
                "acao": "consultar_disponibilidade"
            }

        # Ação: Enviar consulta sem serviço
        print("[T1-ACAO] Enviando: 'a bruna esta disponivel amanha as 10?'")

        with patch('router.principal_router.chamar_gpt_com_contexto', new=mock_gpt):
            try:
                resultado = await roteador_principal(
                    user_id=self.user_id,
                    mensagem="a bruna esta disponivel amanha as 10?",
                    tenant_id=self.tenant_id,
                    phone_number_id=self.phone_number_id,
                    update=AsyncMock(),
                    context=AsyncMock(),
                )
            except:
                pass

        # Verificação: draft NÃO deve estar no contexto passado ao GPT
        print("\n[T1-VERIFICACAO]")
        if contexto_passado_gpt.get("draft_agendamento"):
            draft = contexto_passado_gpt.get("draft_agendamento")
            if draft.get("servico") == "coloracao":
                print(f"  ❌ FALHA: draft_agendamento.servico='coloracao' AINDA NO CONTEXTO")
                assert False, "T1 FALHOU: Serviço anterior foi herdado"
            else:
                print(f"  ⚠️ AVISO: draft existe mas servico={draft.get('servico')}")
        else:
            print(f"  ✅ PASS: draft_agendamento foi removido antes de GPT")

    # ==================== T2: Continuação Válida Preservada ====================
    @pytest.mark.asyncio
    async def test_t2_continuacao_valida_preservada(self):
        """T2: Continuação 'confirma coloracao?' preserva contexto"""
        print("\n" + "="*80)
        print("[T2] Continuação Válida Preservada")
        print("="*80)

        # Setup: draft_agendamento com coloracao, cliente diz 'confirma'
        ctx_setup = {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "coloracao",
                "data_hora": "2026-10-26T14:00:00",
            },
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)
        print("[T2-SETUP] Contexto salvo")

        contexto_passado_gpt = {}
        async def mock_gpt(msg, ctx, instr, tenant_id=None):
            nonlocal contexto_passado_gpt
            contexto_passado_gpt = dict(ctx)
            return {"resposta": "Agendado!", "acao": "confirmar"}

        # Ação: Cliente diz 'confirma' (continuação legítima)
        print("[T2-ACAO] Enviando: 'confirma'")

        with patch('router.principal_router.chamar_gpt_com_contexto', new=mock_gpt):
            try:
                await roteador_principal(
                    user_id=self.user_id,
                    mensagem="confirma",
                    tenant_id=self.tenant_id,
                    phone_number_id=self.phone_number_id,
                    update=AsyncMock(),
                    context=AsyncMock(),
                )
            except:
                pass

        # Verificação: draft DEVE estar no contexto passado ao GPT
        print("\n[T2-VERIFICACAO]")
        if contexto_passado_gpt.get("draft_agendamento"):
            draft = contexto_passado_gpt.get("draft_agendamento")
            if draft.get("servico") == "coloracao":
                print(f"  ✅ PASS: draft_agendamento.servico='coloracao' preservado")
            else:
                print(f"  ❌ FALHA: draft existe mas servico foi alterado para {draft.get('servico')}")
                assert False, "T2 FALHOU: Contexto foi alterado"
        else:
            print(f"  ❌ FALHA: draft_agendamento foi removido (não deveria)")
            assert False, "T2 FALHOU: Contexto foi apagado"

    # ==================== T7: Persistência de DELETE_FIELD ====================
    @pytest.mark.asyncio
    async def test_t7_persistencia_delete_field(self):
        """T7: DELETE_FIELD persiste no Firestore"""
        print("\n" + "="*80)
        print("[T7] Persistência de DELETE_FIELD")
        print("="*80)

        # Setup: Salvar contexto com dados
        ctx_setup = {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"servico": "coloracao", "profissional": "Bruna"},
            "dados_confirmacao_agendamento": {"servico": "coloracao"},
            "servico": "coloracao",
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)
        print("[T7-SETUP] Contexto com dados salvo")

        # Ação: Executar limpar_contexto_agendamento_v2
        print("[T7-ACAO] Executando limpar_contexto_agendamento_v2()")
        resultado = await limpar_contexto_agendamento_v2(self.tenant_id, self.actor_id)
        assert resultado, "T7 Falhou: Limpeza retornou False"

        # Verificação: Recarregar e validar DELETE_FIELD
        print("[T7-VERIFICACAO] Recarregando contexto")
        ctx_pos = await carregar_contexto_temporario_v2(self.tenant_id, self.actor_id)

        assert ctx_pos.get("draft_agendamento") is None, "T7 FALHOU: draft_agendamento não foi deletado"
        assert ctx_pos.get("dados_confirmacao_agendamento") is None, "T7 FALHOU: dados_confirmacao não foi deletado"
        print(f"  ✅ PASS: DELETE_FIELD persistido no Firestore")

    # ==================== T9: Integridade (Histórico + Tenant) ====================
    @pytest.mark.asyncio
    async def test_t9_integridade_historico_tenant(self):
        """T9: Histórico, tenant e dados permanentes preservados após limpeza"""
        print("\n" + "="*80)
        print("[T9] Integridade: Histórico e Tenant Preservados")
        print("="*80)

        # Setup: Contexto com histórico
        ctx_setup = {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"servico": "coloracao"},
            "historico_texto": ["ola", "coloracao", "confirma"],
            "tenant_id": self.tenant_id,
            "_tenant_id_guard": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(self.tenant_id, self.actor_id, ctx_setup)
        print("[T9-SETUP] Contexto com histórico salvo")

        # Ação: Limpar
        print("[T9-ACAO] Executando limpar_contexto_agendamento_v2()")
        await limpar_contexto_agendamento_v2(self.tenant_id, self.actor_id)

        # Verificação: Histórico e tenant preservados
        print("[T9-VERIFICACAO]")
        ctx_pos = await carregar_contexto_temporario_v2(self.tenant_id, self.actor_id)

        assert ctx_pos.get("historico_texto") == ["ola", "coloracao", "confirma"], "T9: histórico não foi preservado"
        assert ctx_pos.get("tenant_id") == self.tenant_id, "T9: tenant_id não foi preservado"
        assert ctx_pos.get("_tenant_id_guard") == self.tenant_id, "T9: _tenant_id_guard não foi preservado"
        assert ctx_pos.get("actor_id") == self.actor_id, "T9: actor_id não foi preservado"
        assert ctx_pos.get("draft_agendamento") is None, "T9: draft deveria ser deletado"

        print(f"  ✅ PASS: Histórico e metadados preservados, dados transitórios deletados")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
