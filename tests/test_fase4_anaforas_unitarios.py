"""
FASE 4 — TESTES UNITÁRIOS: RESOLUÇÃO DE ANÁFORAS

Validar função resolver_referencias_contextuais() com 10 cenários obrigatórios.
"""

import pytest
from services.classificador_conversa import resolver_referencias_contextuais


class TestAnáforasUnitários:
    """Testes unitários para resolução de referências contextuais."""

    # ===== 1. "Com ela" com uma única profissional =====
    def test_1_com_ela_referencia_unica(self):
        """Pronome 'ela' resolvido para profissional anterior."""
        contexto = {
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {"servico": "escova"}
        }

        resultado = resolver_referencias_contextuais(
            "com ela",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["profissional_referenciada"] == "Bruna"
        assert resultado["tipo_referencia"] == "pronome"
        assert resultado["confianca"] >= 90

    # ===== 2. "Com ela" ambíguo (sem profissional anterior) =====
    def test_2_com_ela_ambiguo(self):
        """Pronome sem referência anterior → ambíguo."""
        contexto = {
            "draft_agendamento": {"servico": "escova"},
            "estado_fluxo": "aguardando_profissional"
        }

        resultado = resolver_referencias_contextuais(
            "com ela",
            contexto,
            catalogo_profissionais=["Bruna", "Joana"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["necessita_esclarecimento"] == True
        assert resultado["tipo_referencia"] == "pronome"
        assert resultado["confianca"] < 50

    # ===== 3. "A outra" com candidatos elegíveis =====
    def test_3_a_outra_ordinario(self):
        """Ordinário 'outra' detectado."""
        contexto = {
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {"servico": "corte"}
        }

        resultado = resolver_referencias_contextuais(
            "a outra",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "ordinal"
        assert resultado["necessita_esclarecimento"] == True
        assert resultado["profissional_referenciada"] is None  # Não seleciona por posição

    # ===== 4. "Outro serviço" com catálogo =====
    def test_4_outro_servico(self):
        """Ordinário 'outro serviço' detectado."""
        contexto = {
            "draft_agendamento": {"servico": "escova"}
        }

        resultado = resolver_referencias_contextuais(
            "outro serviço",
            contexto,
            catalogo_servicos=["escova", "corte", "manicure"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "ordinal"

    # ===== 5. "Naquele horário" com hora anterior =====
    def test_5_naquele_horario(self):
        """Referência temporal à hora anterior."""
        contexto = {
            "draft_agendamento": {
                "servico": "corte",
                "data_hora": "2026-11-05T14:00:00"
            }
        }

        resultado = resolver_referencias_contextuais(
            "naquele horário",
            contexto
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "temporal"
        assert resultado["confianca"] >= 75
        assert resultado["necessita_esclarecimento"] == False

    # ===== 6. "Um pouco mais tarde" (ajuste temporal) =====
    def test_6_mais_tarde(self):
        """Ajuste temporal detectado."""
        contexto = {
            "draft_agendamento": {
                "servico": "manicure",
                "data_hora": "2026-11-05T14:00:00"
            }
        }

        resultado = resolver_referencias_contextuais(
            "um pouco mais tarde",
            contexto
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "temporal"
        # Mais tarde requer cálculo determinístico
        assert resultado["necessita_esclarecimento"] == True

    # ===== 7. "Outro serviço com ela" (composta) =====
    def test_7_outro_servico_com_ela(self):
        """Referência composta: serviço + profissional."""
        contexto = {
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {"servico": "escova"}
        }

        resultado = resolver_referencias_contextuais(
            "outro serviço com ela",
            contexto,
            catalogo_profissionais=["Bruna", "Joana"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "composta"
        assert resultado["profissional_referenciada"] == "Bruna"

    # ===== 8. "O mesmo serviço com outra" (composta) =====
    def test_8_mesmo_servico_outra(self):
        """Referência composta: mesmo serviço + outra profissional."""
        contexto = {
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {"servico": "manicure"}
        }

        resultado = resolver_referencias_contextuais(
            "o mesmo serviço com outra",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "composta"

    # ===== 9. Sem referências (texto normal) =====
    def test_9_sem_referencias(self):
        """Nenhuma referência contextual."""
        contexto = {
            "draft_agendamento": {"servico": "corte"}
        }

        resultado = resolver_referencias_contextuais(
            "Quero escova terça",
            contexto,
            catalogo_profissionais=["Bruna", "Joana"]
        )

        assert resultado["referencias_detectadas"] == False
        assert resultado["tipo_referencia"] == "nenhuma"
        assert resultado["confianca"] == 0

    # ===== 10. Contexto vazio (isolamento) =====
    def test_10_contexto_vazio(self):
        """Referência com contexto vazio → ambígua."""
        resultado = resolver_referencias_contextuais(
            "com ela",
            {},
            catalogo_profissionais=["Bruna", "Joana"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["necessita_esclarecimento"] == True
        assert resultado["profissional_referenciada"] is None


class TestAnáforasEdgeCases:
    """Testes de edge cases e proteção."""

    def test_edge_pronome_em_texto_longo(self):
        """Pronome em mensagem com múltiplas partes."""
        contexto = {
            "profissional_escolhido": "Carla",
            "draft_agendamento": {"servico": "hidratação"}
        }

        resultado = resolver_referencias_contextuais(
            "Gostaria de fazer outro serviço com ela, pode ser na segunda?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["profissional_referenciada"] == "Carla"

    def test_edge_pronome_tipo_ele(self):
        """Pronome 'ele' (profissional masculino)."""
        contexto = {
            "profissional_escolhido": "João",
            "draft_agendamento": {"servico": "barba"}
        }

        resultado = resolver_referencias_contextuais(
            "com ele de novo",
            contexto,
            catalogo_profissionais=["João", "Pedro"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["profissional_referenciada"] == "João"

    def test_edge_draft_anterior_supersede(self):
        """Draft antigo vs profissional_escolhido atual."""
        contexto = {
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {
                "servico": "escova",
                "profissional": "Joana"  # Antigo
            }
        }

        resultado = resolver_referencias_contextuais(
            "com ela",
            contexto,
            catalogo_profissionais=["Bruna", "Joana"]
        )

        # profissional_escolhido tem prioridade
        assert resultado["profissional_referenciada"] == "Bruna"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
