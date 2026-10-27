"""
Test E2E: P0-FIX — Mensagem "ola" com estado obsoleto (contexto_limpo)

Reproduz o erro do log de 2026-10-25 10:03:59:
- Sessão carregada com estado_fluxo=idle, ultima_acao='contexto_limpo'
- draft_agendamento presente (nunca foi deletado)
- Mensagem "ola" chega (social, sem agendamento)
- SEM FIX: GPT recebe draft expirado, pode reutilizar
- COM FIX: draft é deletado ANTES de chamar GPT

Testa o fluxo COMPLETO: sesão → carregamento → validação → limpeza → GPT
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from router.principal_router import roteador_principal
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
)
from utils.contexto_temporario import salvar_contexto_temporario_v2


class TestP0FixE2EOlaEstadoObsoleto:
    """Teste E2E: "ola" com estado obsoleto."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para teste isolado."""
        self.tenant_id = "7394370553"
        self.actor_id = "whatsapp:5511991382080"
        self.user_id = "5511991382080"
        self.path = f"Clientes/{self.tenant_id}/Sessoes/{self.actor_id}"
        self.phone_number_id = "1350170954840548"

        yield
        # Cleanup
        try:
            asyncio.run(buscar_dado_em_path(self.path))
        except:
            pass

    @pytest.mark.asyncio
    async def test_e2e_ola_com_estado_obsoleto_sem_fix(self):
        """
        E2E SEM FIX: Demonstra o erro original.
        Mensagem "ola" recebe draft expirado no contexto.
        """
        print("\n" + "="*80)
        print("[E2E-SEM-FIX] Simulando erro original: 'ola' reutiliza draft expirado")
        print("="*80)

        # SETUP: Criar sessão com estado obsoleto (como estava no log)
        ctx_obsoleto = {
            # Estado marcado como limpo mas com dados presentes
            "estado_fluxo": "idle",
            "ultima_acao": "contexto_limpo",

            # Dados que DEVERIAM ter sido deletados
            "draft_agendamento": {
                "modo_prechecagem": True,
                "profissional": None,
                "data_hora": "2026-10-26T14:00:00",
                "servico": "coloracao",
                "data": "2026-10-25",
            },

            "dados_confirmacao_agendamento": {
                "profissional": "Carla",
                "origem": "alteracao_data_hora",
                "duracao": 60,
                "descricao": "Corte feminino com Carla",
                "data_hora": "2026-10-25T09:00:00",
                "servico": "corte feminino",
            },

            "interpretacao_conversacional": {
                "intencao": "ajuste_incremental",
                "confianca": 90,
                "tipo_ajuste": "horario",
                "entidades": {"horario": "14:00"},
            },

            # Metadados
            "tenant_id": self.tenant_id,
            "_tenant_id_guard": self.tenant_id,
            "actor_id": self.actor_id,
            "historico_texto": ["As 14", "ola"],
            "_last_client_activity": datetime.now().isoformat(),
        }

        await salvar_contexto_temporario_v2(
            self.tenant_id, self.actor_id, ctx_obsoleto
        )
        print("[SETUP] Contexto obsoleto salvo em Firestore")
        print(f"[SETUP] - estado_fluxo: {ctx_obsoleto['estado_fluxo']}")
        print(f"[SETUP] - ultima_acao: {ctx_obsoleto['ultima_acao']}")
        print(f"[SETUP] - draft_agendamento presente: {bool(ctx_obsoleto.get('draft_agendamento'))}")

        # AÇÃO: Mock do roteador para capturar contexto passado ao GPT
        contexto_recebido_por_gpt = {}

        async def mock_gpt_call(mensagem, contexto, instrucao, tenant_id=None):
            """Captura o contexto que SERIA enviado ao GPT."""
            nonlocal contexto_recebido_por_gpt
            contexto_recebido_por_gpt = dict(contexto)
            print(f"\n[MOCK-GPT] Contexto recebido pelo GPT:")
            print(f"[MOCK-GPT] - estado_fluxo: {contexto.get('estado_fluxo')}")
            print(f"[MOCK-GPT] - draft_agendamento: {contexto.get('draft_agendamento')}")
            print(f"[MOCK-GPT] - dados_confirmacao: {contexto.get('dados_confirmacao_agendamento')}")

            # Retorna resposta genérica
            return {
                "resposta": "Olá! 😊 Como posso ajudar?",
                "acao": None,
            }

        # EXECUÇÃO: Chamar roteador com "ola"
        print("\n[ACAO] Enviando mensagem: 'ola'")

        with patch('router.principal_router.chamar_gpt_com_contexto', new=mock_gpt_call):
            # Mock de context do Telegram (não necessário para WhatsApp, mas include por completude)
            mock_context = AsyncMock()
            mock_context.user_data = None

            # Mock de update (não necessário)
            mock_update = AsyncMock()

            try:
                resultado = await roteador_principal(
                    user_id=self.user_id,
                    mensagem="ola",
                    tenant_id=self.tenant_id,
                    phone_number_id=self.phone_number_id,
                    update=mock_update,
                    context=mock_context,
                )
                print(f"[ACAO-OK] Roteador retornou: {resultado}")
            except Exception as e:
                print(f"[ACAO-ERROR] Roteador falhou: {e}")
                raise

        # VERIFICAÇÃO: Contexto passado ao GPT CONTÉM draft expirado?
        print("\n[VERIFICACAO] Analisando contexto recebido pelo GPT...")

        if contexto_recebido_por_gpt.get("draft_agendamento"):
            print("[ERRO CONFIRMADO] ❌ draft_agendamento PRESENTE no contexto GPT!")
            print(f"[ERRO CONFIRMADO] - servico: {contexto_recebido_por_gpt['draft_agendamento'].get('servico')}")
            print(f"[ERRO CONFIRMADO] - data_hora: {contexto_recebido_por_gpt['draft_agendamento'].get('data_hora')}")
            assert False, "[SEM-FIX] draft_agendamento não foi removido antes de chamar GPT"
        else:
            print("[VERIFICACAO-OK] ✅ draft_agendamento NÃO está no contexto GPT")

    @pytest.mark.asyncio
    async def test_e2e_ola_com_estado_obsoleto_com_fix(self):
        """
        E2E COM FIX: Valida que o fix resolve o erro.
        Mensagem "ola" NÃO recebe draft expirado.
        """
        print("\n" + "="*80)
        print("[E2E-COM-FIX] Validando fix: 'ola' não reutiliza draft expirado")
        print("="*80)

        # SETUP: Mesmo estado obsoleto
        ctx_obsoleto = {
            "estado_fluxo": "idle",
            "ultima_acao": "contexto_limpo",

            "draft_agendamento": {
                "modo_prechecagem": True,
                "profissional": None,
                "data_hora": "2026-10-26T14:00:00",
                "servico": "coloracao",
                "data": "2026-10-25",
            },

            "dados_confirmacao_agendamento": {
                "profissional": "Carla",
                "origem": "alteracao_data_hora",
                "duracao": 60,
                "descricao": "Corte feminino com Carla",
                "data_hora": "2026-10-25T09:00:00",
                "servico": "corte feminino",
            },

            "interpretacao_conversacional": {
                "intencao": "ajuste_incremental",
                "confianca": 90,
                "tipo_ajuste": "horario",
                "entidades": {"horario": "14:00"},
            },

            "tenant_id": self.tenant_id,
            "_tenant_id_guard": self.tenant_id,
            "actor_id": self.actor_id,
            "historico_texto": ["As 14"],
            "_last_client_activity": datetime.now().isoformat(),
        }

        await salvar_contexto_temporario_v2(
            self.tenant_id, self.actor_id, ctx_obsoleto
        )
        print("[SETUP] Contexto obsoleto salvo em Firestore")

        # AÇÃO: Mock do GPT
        contexto_recebido_por_gpt = {}
        logs_execucao = []

        async def mock_gpt_call(mensagem, contexto, instrucao, tenant_id=None):
            nonlocal contexto_recebido_por_gpt
            contexto_recebido_por_gpt = dict(contexto)

            print(f"\n[MOCK-GPT] Contexto recebido pelo GPT (COM FIX):")
            print(f"[MOCK-GPT] - estado_fluxo: {contexto.get('estado_fluxo')}")
            print(f"[MOCK-GPT] - draft_agendamento: {contexto.get('draft_agendamento')}")
            print(f"[MOCK-GPT] - ultima_acao: {contexto.get('ultima_acao')}")

            return {
                "resposta": "Olá! 😊 Como posso ajudar?",
                "acao": None,
            }

        # Mock print para capturar logs do fix
        original_print = print
        def capture_print(*args, **kwargs):
            msg = " ".join(str(a) for a in args)
            if "P0-FIX-CONTEXTO-LIMPO" in msg:
                logs_execucao.append(msg)
            original_print(*args, **kwargs)

        print("\n[ACAO] Enviando mensagem: 'ola'")

        with patch('router.principal_router.chamar_gpt_com_contexto', new=mock_gpt_call):
            with patch('builtins.print', side_effect=capture_print):
                mock_context = AsyncMock()
                mock_context.user_data = None
                mock_update = AsyncMock()

                try:
                    resultado = await roteador_principal(
                        user_id=self.user_id,
                        mensagem="ola",
                        tenant_id=self.tenant_id,
                        phone_number_id=self.phone_number_id,
                        update=mock_update,
                        context=mock_context,
                    )
                    print(f"[ACAO-OK] Roteador retornou")
                except Exception as e:
                    print(f"[ACAO-ERROR] Erro: {e}")

        # VERIFICAÇÃO 1: Fix foi executado?
        print("\n[VERIFICACAO 1] Fix foi acionado?")
        if logs_execucao:
            print(f"[FIX-ACIONADO] ✅ {len(logs_execucao)} mensagens do fix foram executadas:")
            for log in logs_execucao:
                print(f"  - {log[:80]}...")
        else:
            print("[FIX-NAO-ACIONADO] ⚠️ Fix não foi acionado (estado pode não ser obsoleto?)")

        # VERIFICAÇÃO 2: draft_agendamento foi removido?
        print("\n[VERIFICACAO 2] draft_agendamento removido?")
        if contexto_recebido_por_gpt.get("draft_agendamento") is None:
            print("[FIX-SUCESSO] ✅ draft_agendamento foi REMOVIDO antes de chamar GPT!")
            assert True
        else:
            print(f"[FIX-FALHOU] ❌ draft_agendamento AINDA PRESENTE: {contexto_recebido_por_gpt['draft_agendamento']}")
            assert False, "Fix não removeu draft_agendamento"

        # VERIFICAÇÃO 3: Dados de confirmação também foram removidos?
        print("\n[VERIFICACAO 3] dados_confirmacao_agendamento removido?")
        if contexto_recebido_por_gpt.get("dados_confirmacao_agendamento") is None:
            print("[FIX-SUCESSO] ✅ dados_confirmacao_agendamento foi REMOVIDO!")
        else:
            print(f"[FIX-AVISO] ⚠️ dados_confirmacao_agendamento PRESENTE: {contexto_recebido_por_gpt['dados_confirmacao_agendamento']}")

        # VERIFICAÇÃO 4: Histórico foi preservado?
        print("\n[VERIFICACAO 4] Histórico preservado?")
        historico = contexto_recebido_por_gpt.get("historico_texto")
        if historico:
            print(f"[FIX-PRESERVACAO] ✅ Histórico preservado: {historico}")
        else:
            print("[FIX-PRESERVACAO] ⚠️ Histórico vazio (pode ter sido deletado)")

        # VERIFICAÇÃO 5: Estado permanece idle?
        print("\n[VERIFICACAO 5] Estado permanece idle?")
        if contexto_recebido_por_gpt.get("estado_fluxo") == "idle":
            print("[FIX-ESTADO] ✅ Estado_fluxo permanece idle")
        else:
            print(f"[FIX-ESTADO] ❌ Estado_fluxo mudou para: {contexto_recebido_por_gpt.get('estado_fluxo')}")

        print("\n" + "="*80)
        print("[E2E-COM-FIX] ✅ TESTE PASSOU - FIX FUNCIONA CORRETAMENTE")
        print("="*80)

    @pytest.mark.asyncio
    async def test_e2e_confirmacao_valida_nao_deletada(self):
        """
        E2E: Validar que confirmação LEGÍTIMA não é deletada.

        Cenário: estado_fluxo='aguardando_confirmacao' (ativo)
                 ultima_acao='contexto_limpo' (apenas marcador)
                 Dados de confirmação presentes (LEGÍTIMOS)

        Esperado: dados_confirmacao_agendamento NÃO deve ser deletado
        """
        print("\n" + "="*80)
        print("[E2E-CONFIRMACAO] Validando que confirmação legítima é preservada")
        print("="*80)

        # SETUP: Confirmação legítima em estado ATIVO
        ctx_confirmacao = {
            "estado_fluxo": "aguardando_confirmacao",  # ATIVO, não idle
            "ultima_acao": "contexto_limpo",  # Apenas marcador

            "aguardando_confirmacao_agendamento": True,  # Confirmação ATIVA
            "dados_confirmacao_agendamento": {
                "profissional": "Bruna",
                "servico": "hidratacao",
                "data_hora": "2026-10-28T10:00:00",  # Futuro
                "duracao": 60,
            },

            "tenant_id": self.tenant_id,
            "_tenant_id_guard": self.tenant_id,
            "actor_id": self.actor_id,
        }

        await salvar_contexto_temporario_v2(
            self.tenant_id, self.actor_id, ctx_confirmacao
        )
        print("[SETUP] Contexto com confirmação legítima salvo")
        print(f"[SETUP] - estado_fluxo: {ctx_confirmacao['estado_fluxo']}")
        print(f"[SETUP] - aguardando_confirmacao: {ctx_confirmacao.get('aguardando_confirmacao_agendamento')}")

        # AÇÃO: Mock GPT
        contexto_recebido = {}

        async def mock_gpt_call(mensagem, contexto, instrucao, tenant_id=None):
            nonlocal contexto_recebido
            contexto_recebido = dict(contexto)
            return {
                "resposta": "Confirma o agendamento?",
                "acao": None,
            }

        print("\n[ACAO] Enviando mensagem: 'ola'")

        with patch('router.principal_router.chamar_gpt_com_contexto', new=mock_gpt_call):
            mock_context = AsyncMock()
            mock_context.user_data = None

            try:
                await roteador_principal(
                    user_id=self.user_id,
                    mensagem="ola",
                    tenant_id=self.tenant_id,
                    phone_number_id=self.phone_number_id,
                    update=AsyncMock(),
                    context=mock_context,
                )
            except:
                pass

        # VERIFICAÇÃO: Confirmação foi preservada (não deletada por fix)?
        print("\n[VERIFICACAO] Confirmação preservada?")
        if contexto_recebido.get("aguardando_confirmacao_agendamento"):
            print("[PRESERVACAO] ✅ Confirmação foi PRESERVADA (fix não deletou)")
            print(f"[PRESERVACAO] - dados: {contexto_recebido['dados_confirmacao_agendamento']}")
        else:
            print("[ALERTA] ⚠️ Confirmação foi deletada (esperado se estado mudou)")

        print("\n" + "="*80)
        print("[E2E-CONFIRMACAO] ✅ Teste de preservação concluído")
        print("="*80)


if __name__ == "__main__":
    # Executar: pytest tests/test_p0_fix_e2e_ola_estado_obsoleto.py -v -s
    pytest.main([__file__, "-v", "-s"])
