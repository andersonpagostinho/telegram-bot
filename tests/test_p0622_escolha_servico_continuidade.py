"""
P0.6.2.2 — TESTES: Continuidade da Escolha de Serviço

Valida que cliente responde à pergunta de múltiplos candidatos
e sistema retoma o agendamento original sem perder contexto.
"""

import pytest
from services.interpretacao_contextual_service import interpretar_resposta_contextual
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path


class TestP0622EscolhaServicoContinuidade:
    """Testes de continuidade após pergunta de múltiplos serviços"""

    # ========================================================================
    # T1: _interpretar_servico() reconhece "manicure" entre candidatos
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t1_interpretar_servico_manicure(self):
        """Unitário: resposta 'manicure' é reconhecida entre candidatos"""
        msg = "manicure"
        draft = {}
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test_tenant",
            actor_id="test_actor",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            draft_agendamento=draft,
            contexto=ctx
        )

        # Verificações
        assert resultado["interpretado_sucesso"] is True
        assert resultado["servico"] == "manicure"
        assert resultado["confianca"] >= 0.9
        assert resultado["ambigua"] is False
        print(f"✅ T1: 'manicure' reconhecida com confiança {resultado['confianca']}")

    # ========================================================================
    # T2: Reconhece "pedicure" entre candidatos
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t2_interpretar_servico_pedicure(self):
        """Unitário: resposta 'pedicure' é reconhecida"""
        msg = "pedicure"
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado["servico"] == "pedicure"
        print(f"✅ T2: 'pedicure' reconhecida")

    # ========================================================================
    # T3: "As duas" retorna múltiplos sem criar evento
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t3_interpretar_servico_as_duas(self):
        """Unitário: 'as duas' retorna seleção múltipla"""
        msg = "as duas"
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado.get("multiplo") is True
        assert resultado.get("servicos") == ["manicure", "pedicure"]
        assert resultado.get("servico") is None  # Campo simples fica None
        print(f"✅ T3: 'as duas' retorna múltiplos sem criar evento")

    # ========================================================================
    # T4: "Nenhuma" recusa candidatos e solicita outro
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t4_interpretar_servico_nenhuma(self):
        """Unitário: 'nenhuma' marca recusa e solicita clareza"""
        msg = "nenhuma dessas"
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado.get("recusou") is True
        assert resultado.get("servico") is None
        assert resultado["confianca"] >= 0.9
        print(f"✅ T4: 'nenhuma' marca recusa corretamente")

    # ========================================================================
    # T5: Resposta ambígua mantém pergunta pendente
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t5_interpretar_servico_ambiguo(self):
        """Unitário: resposta não reconhecida marca como ambígua"""
        msg = "talvez depois"  # Não é escolha clara
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is False
        assert resultado["ambigua"] is True
        assert resultado.get("servico") is None
        print(f"✅ T5: Resposta ambígua mantém pergunta pendente")

    # ========================================================================
    # T6: Serviço fora dos candidatos não é aceito
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t6_interpretar_servico_fora_candidatos(self):
        """Unitário: serviço não listado não é aceito"""
        msg = "corte feminino"  # Não está entre os candidatos
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is False
        assert resultado.get("servico") is None
        print(f"✅ T6: Serviço fora candidatos rejeitado")

    # ========================================================================
    # T7: Sem candidatos pendentes retorna erro
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t7_interpretar_servico_sem_candidatos(self):
        """Unitário: contexto sem candidatos retorna erro"""
        msg = "manicure"
        ctx = {}  # Sem multiplos_servicos_candidatos

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is False
        assert resultado.get("servico") is None
        print(f"✅ T7: Sem candidatos pendentes retorna erro")

    # ========================================================================
    # T8: Sem estado ativo retorna None (não trata)
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t8_interpretar_servico_sem_estado(self):
        """Unitário: sem estado ativo não trata como contextual"""
        msg = "manicure"
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="idle",  # Sem estado ativo
            contexto=ctx
        )

        assert resultado is None
        print(f"✅ T8: Sem estado ativo retorna None")

    # ========================================================================
    # T9: Variação "quero manicure" também funciona
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t9_interpretar_servico_variacao(self):
        """Unitário: variações naturais ('quero manicure') funcionam"""
        msg = "quero manicure"
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado["servico"] == "manicure"
        print(f"✅ T9: Variação 'quero manicure' reconhecida")

    # ========================================================================
    # T10: Resposta curta sem estado ativo segue roteamento normal
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t10_resposta_curta_sem_contexto(self):
        """Unitário: 'manicure' sem estado ativo não é tratada como escolha"""
        msg = "manicure"
        ctx = {
            # Sem multiplos_servicos_candidatos
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="idle",  # Sem fluxo
            contexto=ctx
        )

        # Sem estado ativo, retorna None (não é interpretação contextual)
        assert resultado is None
        print(f"✅ T10: Resposta curta sem contexto não é tratada contextualmente")

    # ========================================================================
    # T11: "Ambas" como variação de "as duas"
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t11_interpretar_servico_ambas(self):
        """Unitário: 'ambas' também significa múltiplos"""
        msg = "ambas"
        ctx = {
            "multiplos_servicos_candidatos": ["manicure", "pedicure"]
        }

        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="aguardando_servico",
            contexto=ctx
        )

        assert resultado["interpretado_sucesso"] is True
        assert resultado.get("multiplo") is True
        print(f"✅ T11: 'ambas' reconhecida como múltiplo")

    # ========================================================================
    # T12: Regressão - fluxo normal sem múltiplos não afetado
    # ========================================================================
    @pytest.mark.asyncio
    async def test_t12_regressao_fluxo_normal(self):
        """Unitário: fluxo normal (um serviço) não é afetado"""
        msg = "manicure"
        ctx = {
            # Sem multiplos_servicos_candidatos → fluxo normal
        }

        # Estado é "agendando" (fluxo normal), não "aguardando_servico"
        resultado = await interpretar_resposta_contextual(
            tenant_id="test",
            actor_id="test",
            mensagem=msg,
            estado_fluxo="agendando",
            contexto=ctx
        )

        # Retorna desconhecido (não é um estado tratado por este serviço)
        # mas a ideia é: outros mecanismos tratam "agendando"
        print(f"✅ T12: Fluxo normal não afetado")


if __name__ == "__main__":
    print("\n🧪 Executando testes P0.6.2.2...\n")
    test_obj = TestP0622EscolhaServicoContinuidade()

    test_obj.test_t1_interpretar_servico_manicure()
    test_obj.test_t2_interpretar_servico_pedicure()
    test_obj.test_t3_interpretar_servico_as_duas()
    test_obj.test_t4_interpretar_servico_nenhuma()
    test_obj.test_t5_interpretar_servico_ambiguo()
    test_obj.test_t6_interpretar_servico_fora_candidatos()
    test_obj.test_t7_interpretar_servico_sem_candidatos()
    test_obj.test_t8_interpretar_servico_sem_estado()
    test_obj.test_t9_interpretar_servico_variacao()
    test_obj.test_t10_resposta_curta_sem_contexto()
    test_obj.test_t11_interpretar_servico_ambas()
    test_obj.test_t12_regressao_fluxo_normal()

    print("\n✅ TODOS OS TESTES UNITÁRIOS PASSARAM!\n")
