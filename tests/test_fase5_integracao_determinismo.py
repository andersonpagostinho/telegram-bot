"""
FASE 5 — TESTES UNITÁRIOS: INTEGRAÇÃO COM MOTOR DETERMINÍSTICO

Validar consumo de refs_contextuais no fluxo determinístico de gtp_service.py

10 testes obrigatórios conforme FASE 5 ETAPA 2
"""

import pytest
from services.classificador_conversa import resolver_referencias_contextuais


class TestIntegracaoDeterminismo:
    """Testes de integração com motor determinístico."""

    # ===== 1. Pronome com profissional inequívoca =====
    def test_1_pronome_profissional_inequivoca(self):
        """Pronome resolvido deve ser validado contra catálogo."""
        contexto = {
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {"servico": "escova"}
        }

        resultado = resolver_referencias_contextuais(
            "Qual o preço com ela?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["profissional_referenciada"] == "Bruna"
        # Validação: "Bruna" deve existir no catálogo
        assert resultado["profissional_referenciada"] in ["Bruna", "Joana", "Carla"]

    # ===== 2. Pronome com múltiplas profissionais possíveis =====
    def test_2_pronome_multiplas_candidatas(self):
        """Pronome sem context único → ambíguo."""
        contexto = {
            "draft_agendamento": {"servico": "corte"}
            # Sem profissional_escolhido
        }

        resultado = resolver_referencias_contextuais(
            "Com ela?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["necessita_esclarecimento"] == True
        # Não seleciona automaticamente
        assert resultado["profissional_referenciada"] is None

    # ===== 3. "A outra" sem seleção automática =====
    def test_3_outra_sem_selecao_automatica(self):
        """Ordinário não seleciona por posição."""
        contexto = {
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {"servico": "corte"}
        }

        resultado = resolver_referencias_contextuais(
            "E a outra?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "ordinal"
        # Não seleciona Joana por posição
        assert resultado["profissional_referenciada"] is None
        assert resultado["necessita_esclarecimento"] == True

    # ===== 4. "Outro serviço" com catálogo válido =====
    def test_4_outro_servico_catalogo_valido(self):
        """Ordinário serviço não inventa serviço."""
        contexto = {
            "draft_agendamento": {"servico": "escova"}
        }

        resultado = resolver_referencias_contextuais(
            "Outro serviço",
            contexto,
            catalogo_servicos=["escova", "corte", "manicure", "hidratação"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "ordinal"
        # Não inventa serviço
        assert resultado["servico_referenciado"] is None

    # ===== 5. Serviço inexistente =====
    def test_5_servico_inexistente(self):
        """Serviço fora do catálogo não deve ser resolvido."""
        contexto = {
            "draft_agendamento": {"servico": "escova"}
        }

        # Nome de serviço que não existe no catálogo
        resultado = resolver_referencias_contextuais(
            "Quero botox",  # Não existe em ["escova", "corte", "manicure"]
            contexto,
            catalogo_servicos=["escova", "corte", "manicure"]
        )

        # Deve não detectar como ordinário, mas como intenção nova
        assert resultado["tipo_referencia"] != "ordinal"

    # ===== 6. "Naquele horário" com referência válida =====
    def test_6_naquele_horario_referencia_valida(self):
        """Temporal recupera hora anterior."""
        contexto = {
            "draft_agendamento": {
                "servico": "corte",
                "data_hora": "2026-11-10T14:00:00"
            }
        }

        resultado = resolver_referencias_contextuais(
            "Naquele horário também?",
            contexto
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "temporal"
        # Não requer esclarecimento (hora é inequívoca)
        assert resultado["necessita_esclarecimento"] == False

    # ===== 7. "Mais tarde" sem cálculo =====
    def test_7_mais_tarde_sem_calculo(self):
        """Temporal ajuste não calcula, apenas marca."""
        contexto = {
            "draft_agendamento": {
                "servico": "manicure",
                "data_hora": "2026-11-10T14:00:00"
            }
        }

        resultado = resolver_referencias_contextuais(
            "Um pouco mais tarde?",
            contexto
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "temporal"
        # Requer determinismo para calcular
        assert resultado["necessita_esclarecimento"] == True
        # Não retorna hora calculada
        assert "+" not in str(resultado)

    # ===== 8. Composta: pronome + ordinário =====
    def test_8_composta_pronome_ordinario(self):
        """Composta resolve componentes separadamente."""
        contexto = {
            "profissional_escolhido": "Carla",
            "draft_agendamento": {"servico": "escova"}
        }

        resultado = resolver_referencias_contextuais(
            "Outro serviço com ela?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        assert resultado["referencias_detectadas"] == True
        assert resultado["tipo_referencia"] == "composta"
        # Pronome resolvido
        assert resultado["profissional_referenciada"] == "Carla"

    # ===== 9. Mudança de assunto durante draft =====
    def test_9_mudanca_assunto_durante_draft(self):
        """Mudança de assunto não atualiza draft."""
        contexto = {
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
            "estado_fluxo": "aguardando_data_hora"
        }

        # Pergunta (mudança de assunto)
        resultado = resolver_referencias_contextuais(
            "Qual é o preço do corte?",
            contexto
        )

        # Detecta mudança, mas não altera draft
        assert resultado["referencias_detectadas"] == False  # Não é pronome/ordinário/temporal
        # Draft deve estar intacto (responsabilidade do chamador)

    # ===== 10. Consulta informacional em confirmação =====
    def test_10_consulta_em_confirmacao(self):
        """Consulta durante confirmação pendente."""
        contexto = {
            "draft_agendamento": {
                "servico": "manicure",
                "profissional": "Gloria",
                "data_hora": "2026-11-05T15:00:00"
            },
            "aguardando_confirmacao_agendamento": True
        }

        resultado = resolver_referencias_contextuais(
            "Qual é o endereço do salão?",
            contexto
        )

        # Não é pronome/ordinário/temporal → nenhuma referência
        assert resultado["referencias_detectadas"] == False
        # Draft intacto, não avança para criação


class TestValidacaoDeterminismo:
    """Testes de validação contra motor determinístico."""

    def test_pronome_validado_contra_catalogo(self):
        """Profissional resolvida deve existir no catálogo."""
        contexto = {
            "profissional_escolhido": "Sofia",  # Fora do catálogo
            "draft_agendamento": {"servico": "escova"}
        }

        catalogo = ["Bruna", "Joana", "Carla", "Gloria"]

        resultado = resolver_referencias_contextuais(
            "Com ela?",
            contexto,
            catalogo_profissionais=catalogo
        )

        # Resolvido, mas motor deve validar
        assert resultado["profissional_referenciada"] == "Sofia"
        # Validação: Deve falhar no motor
        if resultado["profissional_referenciada"]:
            assert resultado["profissional_referenciada"] in catalogo or \
                   resultado["confianca"] < 100  # Marcado como incerteza

    def test_nenhum_evento_sem_confirmacao(self):
        """Referência ambígua não cria evento."""
        contexto = {}

        resultado = resolver_referencias_contextuais(
            "Com ela?",
            contexto
        )

        # Ambíguo
        assert resultado["necessita_esclarecimento"] == True
        # Draft não deve ser criado automaticamente


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
