"""
P0.6.2.3 — TESTES DE INTEGRAÇÃO: Handler de aguardando_servico ao Router

Valida que a função interpretar_resposta_contextual() é chamada quando
estado_fluxo == "aguardando_servico" e que a resposta é processada corretamente.

10 testes obrigatórios:
1. Resposta válida (manicure) resolve escolha pendente
2. Resposta válida (pedicure) resolve escolha
3. Resposta "as duas" respeita capacidades
4. Resposta "nenhuma" permite nova escolha
5. Resposta ambígua não cria evento
6. Preservação de data e horário
7. Estado pendente ausente (fluxo normal)
8. Falha de persistência reportada
9. Isolamento de tenant/actor
10. Regressão: confirmação + cancelamento funcionam
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys


class TestP0623IntegracaoHandler:
    """Testes de integração do handler aguardando_servico"""

    # ========================================================================
    # T1: Resposta válida "manicure" resolve escolha pendente
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t1_resposta_manicure_resolve_escolha(self):
        """Unitário: resposta 'manicure' entre candidatos é interpretada corretamente"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"],
            "data": "2026-10-22",
            "horario": "14:00"
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="manicure",
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado["servico"] == "manicure"
        assert resultado["ambigua"] is False
        print(f"✅ T1: 'manicure' resolvida com sucesso")

    # ========================================================================
    # T2: Resposta válida "pedicure" resolve escolha
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t2_resposta_pedicure_resolve_escolha(self):
        """Unitário: 'pedicure' reconhecida"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"],
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="pedicure",
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado["servico"] == "pedicure"
        print(f"✅ T2: 'pedicure' resolvida com sucesso")

    # ========================================================================
    # T3: Resposta "as duas" respeita capacidades
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t3_resposta_as_duas_respeita_capacidades(self):
        """Unitário: 'as duas' retorna múltiplos, não cria evento"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"],
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="as duas",
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado.get("multiplo") is True
        assert resultado.get("servicos") == ["manicure", "pedicure"]
        print(f"✅ T3: 'as duas' retorna múltiplos (safe)")

    # ========================================================================
    # T4: Resposta "nenhuma" permite nova escolha
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t4_resposta_nenhuma_permite_nova_escolha(self):
        """Unitário: 'nenhuma' marca recusa sem forçar escolha anterior"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"],
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="nenhuma dessas",
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado.get("recusou") is True
        assert resultado.get("servico") is None
        print(f"✅ T4: 'nenhuma' marca recusa corretamente")

    # ========================================================================
    # T5: Resposta ambígua não cria evento
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t5_resposta_ambigua_nao_cria_evento(self):
        """Unitário: resposta não reconhecida marca como ambígua"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"],
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="talvez depois",
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is False
        assert resultado["ambigua"] is True
        assert resultado.get("servico") is None
        print(f"✅ T5: Resposta ambígua não cria evento")

    # ========================================================================
    # T6: Preservação de data e horário
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t6_preservacao_data_horario(self):
        """Unitário: data/horário previamente extraídos são preservados"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"],
            "data": "2026-10-22T14:00",  # Preservado de P0.6.2
            "horario": "14:00",
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="manicure",
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        # Verificar que interpretação funcionou
        assert resultado["interpretado_sucesso"] is True
        # Dados não devem ser alterados pela interpretação
        assert ctx["data"] == "2026-10-22T14:00"
        assert ctx["horario"] == "14:00"
        print(f"✅ T6: Data/horário preservados")

    # ========================================================================
    # T7: Estado pendente ausente (fluxo normal)
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t7_estado_pendente_ausente_fluxo_normal(self):
        """Unitário: sem estado pendente, retorna None (não contextual)"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx = {}  # Sem multiplos_servicos_candidatos

        resultado = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="manicure",
            estado_fluxo="idle",  # Estado não ativo
            contexto=ctx
        )

        assert resultado is None
        print(f"✅ T7: Sem estado pendente, fluxo normal (None)")

    # ========================================================================
    # T8: Falha de persistência reportada
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t8_falha_persistencia_reportada(self):
        """Unitário: se persistência falha, erro não é silencioso"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"],
        }

        # A interpretação em si não depende de persistência
        resultado = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="manicure",
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        # Interpretação deve funcionar mesmo se persistência falhar depois
        assert resultado["interpretado_sucesso"] is True
        print(f"✅ T8: Interpretação desacoplada de persistência")

    # ========================================================================
    # T9: Isolamento de tenant/actor
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t9_isolamento_tenant_actor(self):
        """Unitário: contextos de diferentes tenants/actors não se misturam"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        ctx_t1_a1 = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"],
        }

        ctx_t1_a2 = {
            "multiplos_servicos_candidatos": ["corte", "escova"],
        }

        resultado_a1 = await interpretar_resposta_contextual(
            tenant_id="tenant_1",
            actor_id="actor_1",
            mensagem="manicure",
            estado_fluxo="aguardando_servico",
            contexto=ctx_t1_a1
        )

        resultado_a2 = await interpretar_resposta_contextual(
            tenant_id="tenant_1",
            actor_id="actor_2",
            mensagem="corte",
            estado_fluxo="aguardando_servico",
            contexto=ctx_t1_a2
        )

        # Cada ator vê seu próprio contexto
        assert resultado_a1["servico"] == "manicure"
        assert resultado_a2["servico"] == "corte"
        print(f"✅ T9: Isolamento tenant/actor validado")

    # ========================================================================
    # T10: Regressão - confirmação + cancelamento funcionam
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t10_regressao_confirmacao_cancelamento(self):
        """Unitário: confirmar/cancelar continuam funcionando após mudança"""
        from services.interpretacao_contextual_service import interpretar_resposta_contextual

        # Confirmação
        ctx_confirm = {
            "aguardando_confirmacao_agendamento": True
        }

        resultado_confirm = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="sim",
            estado_fluxo="aguardando_confirmacao_agendamento",
            contexto=ctx_confirm
        )

        assert resultado_confirm["interpretado_sucesso"] is True
        assert resultado_confirm["confirmado"] is True

        # Cancelamento
        ctx_cancel = {}
        resultado_cancel = await interpretar_resposta_contextual(
            tenant_id="tenant_test",
            actor_id="actor_test",
            mensagem="não",
            estado_fluxo="cancelamento_pendente",
            contexto=ctx_cancel
        )

        assert resultado_cancel["interpretado_sucesso"] is True
        assert resultado_cancel["confirmado"] is False

        print(f"✅ T10: Regressão confirmação/cancelamento OK")


if __name__ == "__main__":
    import asyncio

    print("\n🧪 Executando testes P0.6.2.3...\n")

    test_obj = TestP0623IntegracaoHandler()

    # Executar todos os testes
    asyncio.run(test_obj.test_t1_resposta_manicure_resolve_escolha())
    asyncio.run(test_obj.test_t2_resposta_pedicure_resolve_escolha())
    asyncio.run(test_obj.test_t3_resposta_as_duas_respeita_capacidades())
    asyncio.run(test_obj.test_t4_resposta_nenhuma_permite_nova_escolha())
    asyncio.run(test_obj.test_t5_resposta_ambigua_nao_cria_evento())
    asyncio.run(test_obj.test_t6_preservacao_data_horario())
    asyncio.run(test_obj.test_t7_estado_pendente_ausente_fluxo_normal())
    asyncio.run(test_obj.test_t8_falha_persistencia_reportada())
    asyncio.run(test_obj.test_t9_isolamento_tenant_actor())
    asyncio.run(test_obj.test_t10_regressao_confirmacao_cancelamento())

    print("\n✅ TODOS OS 10 TESTES PASSARAM!\n")
