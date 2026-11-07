"""
TESTES P0 — Mensagens neutras com draft antigo não devem ser classificadas como ajuste

Contexto da correção:
- Mensagem "desculpe, nao era com voce, enviei errado" foi classificada como ajuste_incremental
- Causado por regex genérico: r"\b(com\s+[a-zA-ZÀ-ÿ]+|...)\b" que detecta "com voce"
- Resultado: draft antigo foi preservado, GPT foi chamado desnecessariamente

Objetivo: Garantir que mensagens neutras permaneçam neutras mesmo com draft.
"""

import pytest
from services.classificador_conversa import classificar_intencao_conversacional


class TestMensagensNeutraComDraft:
    """Testes para validar que mensagens neutras não são reclassificadas por draft antigo"""

    def test_desculpe_enviei_errado_com_draft(self):
        """
        RED: Mensagem de desculpa pessoal com draft ativo
        NÃO deve ser classificada como ajuste_incremental

        Caso original da auditoria.
        """
        draft_antigo = {
            "servico": "corte feminino",
            "profissional": "Bruna",
            "data_hora": "2026-11-03T09:00:00"
        }

        resultado = classificar_intencao_conversacional(
            "desculpe, nao era com voce, enviei errado.",
            {
                "draft_agendamento": draft_antigo,
                "estado_fluxo": "agendando",
                "profissional_escolhido": "Bruna"
            },
            catalogo_servicos=["corte feminino", "manicure"],
            catalogo_profissionais=["Bruna", "Gloria", "Joana", "Carla"]
        )

        # ❌ FALHA ESPERADA: Retorna ajuste_incremental (INCORRETO)
        # ✅ ESPERADO: Retorna indefinida ou outro valor neutro (CORRETO)
        assert resultado["intencao_conversacional"] != "ajuste_incremental", \
            f"Mensagem neutra NÃO deve ser ajuste_incremental, mas recebeu: {resultado}"
        print(f"✅ T1: Desculpe com draft → {resultado['intencao_conversacional']}", flush=True)

    def test_nao_era_com_voce_com_draft(self):
        """
        RED: Variante de mensagem neutra
        Teste que "com voce" não é detectado como referência a profissional
        """
        draft_antigo = {
            "servico": "manicure",
            "profissional": "Gloria",
            "data_hora": "2026-11-03T15:00:00"
        }

        resultado = classificar_intencao_conversacional(
            "não era com você, foi erro meu",
            {
                "draft_agendamento": draft_antigo,
                "estado_fluxo": "agendando"
            },
            catalogo_servicos=["corte feminino", "manicure"],
            catalogo_profissionais=["Bruna", "Gloria", "Joana", "Carla"]
        )

        assert resultado["intencao_conversacional"] != "ajuste_incremental", \
            f"'com voce' não deve ser interpretado como referência profissional: {resultado}"
        print(f"✅ T2: Não era com você → {resultado['intencao_conversacional']}", flush=True)

    def test_obrigado_com_draft(self):
        """
        RED: Agradecimento com draft ativo
        Não deve ser reclassificado como operacional
        """
        draft_antigo = {
            "servico": "corte feminino",
            "profissional": "Joana",
            "data_hora": "2026-11-04T10:00:00"
        }

        resultado = classificar_intencao_conversacional(
            "obrigado!",
            {
                "draft_agendamento": draft_antigo,
                "estado_fluxo": "agendando"
            },
            catalogo_servicos=["corte feminino", "manicure"],
            catalogo_profissionais=["Bruna", "Gloria", "Joana", "Carla"]
        )

        # Agradecimento é social, não operacional
        assert resultado["intencao_conversacional"] not in ["ajuste_incremental", "agendamento_direto"], \
            f"Agradecimento não deve ser operacional: {resultado}"
        print(f"✅ T3: Obrigado com draft → {resultado['intencao_conversacional']}", flush=True)

    def test_deixa_para_la_com_draft(self):
        """
        RED: Cancelamento com draft ativo
        Deve ser detectado como cancelamento, não ajuste
        """
        draft_antigo = {
            "servico": "manicure",
            "profissional": "Carla",
            "data_hora": "2026-11-05T14:00:00"
        }

        resultado = classificar_intencao_conversacional(
            "deixa pra la",  # Forma reconhecida pelo regex (com "pra" abreviado)
            {
                "draft_agendamento": draft_antigo,
                "estado_fluxo": "agendando"
            },
            catalogo_servicos=["corte feminino", "manicure"],
            catalogo_profissionais=["Bruna", "Gloria", "Joana", "Carla"]
        )

        # Deve detectar cancelamento, não ajuste
        assert resultado["intencao_conversacional"] == "cancelamento", \
            f"Deve detectar cancelamento: {resultado}"
        print(f"✅ T4: Deixa pra la → {resultado['intencao_conversacional']}", flush=True)

    def test_com_profissional_real_com_draft(self):
        """
        GREEN: Ajuste legítimo com nome real de profissional
        Deve ser detectado como ajuste_incremental (CORRETO)
        """
        draft_antigo = {
            "servico": "corte feminino",
            "profissional": "Bruna",
            "data_hora": "2026-11-06T09:00:00"
        }

        resultado = classificar_intencao_conversacional(
            "quero trocar para Carla",
            {
                "draft_agendamento": draft_antigo,
                "estado_fluxo": "agendando"
            },
            catalogo_servicos=["corte feminino", "manicure"],
            catalogo_profissionais=["Bruna", "Gloria", "Joana", "Carla"]
        )

        # Ajuste legítimo DEVE ser detectado
        assert resultado["intencao_conversacional"] == "ajuste_incremental", \
            f"Ajuste legítimo deve ser detectado: {resultado}"
        assert resultado.get("tipo_ajuste_incremental") == "profissional", \
            f"Tipo do ajuste deve ser 'profissional': {resultado}"
        print(f"✅ T5: Trocar para Carla → {resultado['intencao_conversacional']} (tipo={resultado.get('tipo_ajuste_incremental')})", flush=True)

    def test_com_profissional_nao_no_catalogo(self):
        """
        RED: Mensagem com nome não presente no catálogo
        Não deve ser interpretada como referência profissional
        """
        draft_antigo = {
            "servico": "corte feminino",
            "profissional": "Bruna",
            "data_hora": "2026-11-03T09:00:00"
        }

        resultado = classificar_intencao_conversacional(
            "com você não funciona",
            {
                "draft_agendamento": draft_antigo,
                "estado_fluxo": "agendando"
            },
            catalogo_servicos=["corte feminino", "manicure"],
            catalogo_profissionais=["Bruna", "Gloria", "Joana", "Carla"]
        )

        # "você" não está no catálogo
        assert resultado["intencao_conversacional"] != "ajuste_incremental", \
            f"'com' + não-profissional não deve ser ajuste: {resultado}"
        print(f"✅ T6: Com você (não no catálogo) → {resultado['intencao_conversacional']}", flush=True)

    def test_mensagem_neutra_sem_draft(self):
        """
        CONTROL: Mensagem neutra SEM draft
        Deve retornar indefinida ou similar
        """
        resultado = classificar_intencao_conversacional(
            "desculpe, enviei errado",
            {},  # SEM draft
            catalogo_servicos=["corte feminino", "manicure"],
            catalogo_profissionais=["Bruna", "Gloria", "Joana", "Carla"]
        )

        # Sem contexto operacional, deve ser indefinida ou neutra
        assert resultado["intencao_conversacional"] in ["indefinida", "mensagem_pessoal"], \
            f"Mensagem neutra sem draft deve ser indefinida: {resultado}"
        print(f"✅ T7: Desculpe sem draft → {resultado['intencao_conversacional']}", flush=True)

    def test_com_calma_com_draft(self):
        """
        RED: Mensagem com "com [advérbio]"
        Não deve ser interpretada como referência profissional
        """
        draft_antigo = {
            "servico": "corte feminino",
            "profissional": "Gloria",
            "data_hora": "2026-11-03T10:00:00"
        }

        resultado = classificar_intencao_conversacional(
            "com calma, sem pressa",
            {
                "draft_agendamento": draft_antigo,
                "estado_fluxo": "agendando"
            },
            catalogo_servicos=["corte feminino", "manicure"],
            catalogo_profissionais=["Bruna", "Gloria", "Joana", "Carla"]
        )

        # "calma" não é profissional
        assert resultado["intencao_conversacional"] != "ajuste_incremental", \
            f"'com calma' não deve ser ajuste de profissional: {resultado}"
        print(f"✅ T8: Com calma → {resultado['intencao_conversacional']}", flush=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
