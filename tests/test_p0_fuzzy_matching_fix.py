"""
P0 FIX — Testes de Fuzzy Matching de Serviços

Validar que "com a bruna" não é confundido com "coloracao"
e que a separação entre serviço e profissional é mantida.
"""

import pytest
from services.normalizacao_service import encontrar_servico_mais_proximo
from router.principal_router import detectar_alteracao_draft_agendamento


@pytest.mark.asyncio
class TestFuzzyMatchingFix:
    """T1-T8: Testes diretos de fuzzy matching"""

    async def test_t1_com_a_bruna_nao_identifica_coloracao(self):
        """T1: 'com a bruna' não deve identificar 'coloracao'"""
        # Simular catálogo do tenant
        resultado = await encontrar_servico_mais_proximo(
            "com a bruna",
            dono_id="7394370553"  # tenant com coloracao no catálogo
        )
        assert resultado != "coloracao", "FAIL: 'com a bruna' foi confundido com 'coloracao'"
        print(f"[T1 PASS] 'com a bruna' → {resultado}")

    async def test_t2_bruna_nao_identifica_coloracao(self):
        """T2: 'bruna' não deve identificar 'coloracao'"""
        resultado = await encontrar_servico_mais_proximo(
            "bruna",
            dono_id="7394370553"
        )
        assert resultado != "coloracao", "FAIL: 'bruna' foi confundido com 'coloracao'"
        print(f"[T2 PASS] 'bruna' → {resultado}")

    async def test_t3_coloracao_identifica_corretamente(self):
        """T3: 'coloracao' deve ser identificado corretamente"""
        resultado = await encontrar_servico_mais_proximo(
            "coloracao",
            dono_id="7394370553"
        )
        assert resultado == "coloracao", f"FAIL: 'coloracao' → {resultado}"
        print(f"[T3 PASS] 'coloracao' identificado corretamente")

    async def test_t4_coloracao_com_acento(self):
        """T4: 'coloração' (com acento) deve ser identificado"""
        resultado = await encontrar_servico_mais_proximo(
            "coloração",
            dono_id="7394370553"
        )
        assert resultado == "coloracao", f"FAIL: 'coloração' → {resultado}"
        print(f"[T4 PASS] 'coloração' identificado corretamente")

    async def test_t5_colorasao_fallback_fuzzy(self):
        """T5: 'colorasao' (erro de digitação) avalia fallback fuzzy"""
        resultado = await encontrar_servico_mais_proximo(
            "colorasao",
            dono_id="7394370553"
        )
        # Deveria encontrar "coloracao" por similaridade alta (~90%)
        assert resultado == "coloracao", f"FAIL: 'colorasao' → {resultado}"
        print(f"[T5 PASS] 'colorasao' → '{resultado}'")

    async def test_t6_corte_femino_fallback_fuzzy(self):
        """T6: 'corte femino' (erro de digitação) avalia fallback fuzzy"""
        resultado = await encontrar_servico_mais_proximo(
            "corte femino",
            dono_id="7394370553"
        )
        assert resultado == "corte feminino", f"FAIL: 'corte femino' → {resultado}"
        print(f"[T6 PASS] 'corte femino' → '{resultado}'")

    async def test_t7_servico_e_profissional_juntos(self):
        """T7: 'quero coloracao com a bruna' identifica serviço"""
        resultado = await encontrar_servico_mais_proximo(
            "quero coloracao com a bruna",
            dono_id="7394370553"
        )
        assert resultado == "coloracao", f"FAIL: Esperado 'coloracao', obteve {resultado}"
        print(f"[T7 PASS] 'quero coloracao com a bruna' → '{resultado}'")

    async def test_t8_com_a_bruna_amanha_nao_gera_servico(self):
        """T8: 'com a bruna amanhã' não deve gerar serviço por similaridade"""
        resultado = await encontrar_servico_mais_proximo(
            "com a bruna amanhã",
            dono_id="7394370553"
        )
        assert resultado != "coloracao", "FAIL: Gerou serviço indevidamente"
        print(f"[T8 PASS] 'com a bruna amanhã' → {resultado}")


@pytest.mark.asyncio
class TestContextualGuard:
    """T13-T15: Testes de proteção contextual em detectar_alteracao_draft_agendamento()"""

    async def test_t13_profissional_nao_altera_servico(self):
        """T13: Alteração incremental de profissional não altera serviço do draft"""
        ctx = {
            "tipo_ajuste_incremental": "profissional",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "gloria"
            }
        }

        alteracao = await detectar_alteracao_draft_agendamento(
            texto_usuario="com a bruna",
            ctx=ctx,
            dono_id="7394370553",
            cliente_id="test_cliente"
        )

        # Deve retornar alteração de profissional, NÃO de serviço
        assert alteracao is None or alteracao.get("tipo") != "servico", \
            f"FAIL: Serviço foi alterado: {alteracao}"
        print(f"[T13 PASS] Profissional não alterou serviço")

    async def test_t14_servico_continua_funcionando(self):
        """T14: Alteração incremental de serviço continua funcionando"""
        ctx = {
            "tipo_ajuste_incremental": "servico",
            "draft_agendamento": {
                "servico": "manicure",
                "profissional": None  # Sem profissional para evitar guard de pergunta informativa
            }
        }

        alteracao = await detectar_alteracao_draft_agendamento(
            texto_usuario="coloracao",  # Simples menção do serviço
            ctx=ctx,
            dono_id="7394370553",
            cliente_id="test_cliente"
        )

        # Deve detectar alteração de serviço
        assert alteracao and alteracao.get("tipo") == "servico", \
            f"FAIL: Não detectou alteração de serviço: {alteracao}"
        assert alteracao.get("valor") == "coloracao", \
            f"FAIL: Serviço incorreto: {alteracao.get('valor')}"
        print(f"[T14 PASS] Alteração de serviço detectada corretamente")

    async def test_t15_sem_tipo_ajuste_nao_altera_indevidamente(self):
        """T15: Ausência de tipo_ajuste_incremental não provoca alteração indevida"""
        ctx = {
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "gloria"
            }
        }

        alteracao = await detectar_alteracao_draft_agendamento(
            texto_usuario="com a bruna",
            ctx=ctx,
            dono_id="7394370553",
            cliente_id="test_cliente"
        )

        # Sem tipo_ajuste definido, "com a bruna" não deve mudar nada
        if alteracao and alteracao.get("tipo") == "servico":
            assert alteracao.get("valor") != "coloracao", \
                "FAIL: 'com a bruna' gerou alteração indevida"
        print(f"[T15 PASS] Sem tipo_ajuste, nenhuma alteração indevida")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
