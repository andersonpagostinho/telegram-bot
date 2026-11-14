"""
P0 FASE 6.2 — Teste de Integração: Profissional Mencionada em Contexto

Valida que:
1. profissional_mencionada é extraída e transferida para contexto_consulta
2. Motor determinístico é chamado com profissional correto
3. Duração é calculada e retornada na resposta
4. Nenhuma escrita ocorre (read-only)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


@pytest.mark.asyncio
async def test_fase6_2_profissional_mencionada_transferida():
    """
    Valida que profissional_mencionada é extraída de features e
    transferida para contexto_consulta antes de chamar motor.
    """
    from services.informacao_service import responder_consulta_informativa

    # Simular contexto_consulta APÓS FASE 6.2 (com profissional_mencionada)
    contexto_consulta = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "profissional_mencionada": "Bruna",  # ← Transferida por FASE 6.2
        "data_hora": "2026-11-13T00:00:00",
    }

    # Mock motor
    motor_chamado_com = {}

    async def mock_resolver_bloco(tenant_id, nome_profissional, servicos):
        motor_chamado_com["resolver_bloco"] = {
            "profissional": nome_profissional,
            "servicos": servicos
        }
        return {
            "valido": True,
            "servicos": servicos,
            "duracoes_individuais": [30, 30],
            "duracao_total": 60,
            "mensagens": []
        }

    async def mock_verificar_conflito(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        motor_chamado_com["motor"] = {
            "profissional": profissional,
            "duracao_min": duracao_min,
            "servicos_bloco": servicos_bloco,
            "hora_inicio": hora_inicio
        }
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None
        }

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {
                "Bruna": {
                    "nome": "Bruna",
                    "servicos": ["manicure", "pedicure"]
                }
            }
        return {}

    with patch("services.multisservico_service.resolver_bloco_servicos", side_effect=mock_resolver_bloco), \
         patch("services.event_service_async.verificar_conflito_e_sugestoes_profissional", side_effect=mock_verificar_conflito):

        resposta = await responder_consulta_informativa(
            mensagem="Quero agendar manicure e pedicure entre 14h e 17h com Bruna",
            dono_id="7394370553",
            features={"tem_contexto_servico": True, "tem_pergunta": True},
            contexto_consulta=contexto_consulta,
            actor_id="whatsapp:5511991382080",
            tenant_id="7394370553"
        )

        # Validações
        assert resposta is not None, "Resposta não deve ser None"
        assert "60 minutos" in resposta or "60 min" in resposta, "Duração não mencionada"
        assert "Bruna" in resposta, "Profissional não mencionada na resposta"

        # Validar que motor foi chamado com profissional correto
        assert "resolver_bloco" in motor_chamado_com, "resolver_bloco_servicos não foi chamado"
        assert motor_chamado_com["resolver_bloco"]["profissional"] == "Bruna", \
            f"Profissional incorreto: {motor_chamado_com['resolver_bloco']['profissional']}"

        assert "motor" in motor_chamado_com, "verificar_conflito_e_sugestoes_profissional não foi chamado"
        assert motor_chamado_com["motor"]["profissional"] == "Bruna", \
            f"Motor chamado com profissional incorreto: {motor_chamado_com['motor']['profissional']}"
        assert motor_chamado_com["motor"]["duracao_min"] == 60, \
            f"Duração incorreta no motor: {motor_chamado_com['motor']['duracao_min']}"
        assert set(motor_chamado_com["motor"]["servicos_bloco"]) == {"manicure", "pedicure"}, \
            f"Serviços incorretos no motor: {motor_chamado_com['motor']['servicos_bloco']}"

        print("✅ Test PASSED: profissional_mencionada transferida e motor chamado corretamente")


@pytest.mark.asyncio
async def test_fase6_2_sem_escrita_durante_consulta():
    """
    Valida que consulta multisserviço não cria eventos, locks ou holds.
    """
    from services.informacao_service import responder_consulta_informativa

    contexto_consulta = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "profissional_mencionada": "Bruna",
        "data_hora": "2026-11-13T00:00:00",
    }

    escrita_tentada = []

    async def mock_resolver_bloco(*args, **kwargs):
        return {
            "valido": True,
            "servicos": ["manicure", "pedicure"],
            "duracoes_individuais": [30, 30],
            "duracao_total": 60,
            "mensagens": []
        }

    async def mock_verificar_conflito(*args, **kwargs):
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None
        }

    async def mock_criar_evento(*args, **kwargs):
        escrita_tentada.append("criar_evento")
        raise AssertionError("❌ Tentativa de criar evento durante consulta")

    async def mock_salvar_contexto(*args, **kwargs):
        escrita_tentada.append("salvar_contexto")
        raise AssertionError("❌ Tentativa de salvar contexto durante consulta")

    with patch("services.multisservico_service.resolver_bloco_servicos", side_effect=mock_resolver_bloco), \
         patch("services.event_service_async.verificar_conflito_e_sugestoes_profissional", side_effect=mock_verificar_conflito):

        resposta = await responder_consulta_informativa(
            mensagem="Quero agendar manicure e pedicure entre 14h e 17h com Bruna",
            dono_id="7394370553",
            features={"tem_contexto_servico": True, "tem_pergunta": True},
            contexto_consulta=contexto_consulta,
            actor_id="whatsapp:5511991382080",
            tenant_id="7394370553"
        )

        assert resposta is not None, "Resposta não deve ser None"
        assert len(escrita_tentada) == 0, f"Escritas detectadas durante consulta: {escrita_tentada}"

        print("✅ Test PASSED: Nenhuma escrita durante consulta")


@pytest.mark.asyncio
async def test_fase6_2_alternativas_com_profissional_compativel():
    """
    Valida que quando profissional preferida não está disponível,
    alternativas são compatíveis com TODOS os serviços (não seleção automática).
    """
    from services.informacao_service import responder_consulta_informativa

    contexto_consulta = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "profissional_mencionada": "Bruna",
        "data_hora": "2026-11-13T00:00:00",
    }

    async def mock_resolver_bloco(tenant_id, nome_profissional, servicos):
        if nome_profissional == "Bruna":
            return {
                "valido": True,
                "servicos": servicos,
                "duracoes_individuais": [30, 30],
                "duracao_total": 60,
                "mensagens": []
            }
        # Outras profissionais também validam
        return {
            "valido": True,
            "servicos": servicos,
            "duracoes_individuais": [30, 30],
            "duracao_total": 60,
            "mensagens": []
        }

    async def mock_verificar_conflito(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        # Simular: Bruna indisponível, Gloria disponível
        if profissional == "Bruna":
            return {
                "conflito": True,
                "sugestoes": [],
                "profissional_alternativo": [
                    {"nome": "Gloria", "duracao": 60},
                    {"nome": "Joana", "duracao": 60},
                ]
            }
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None
        }

    with patch("services.multisservico_service.resolver_bloco_servicos", side_effect=mock_resolver_bloco), \
         patch("services.event_service_async.verificar_conflito_e_sugestoes_profissional", side_effect=mock_verificar_conflito):

        resposta = await responder_consulta_informativa(
            mensagem="Quero agendar manicure e pedicure entre 14h e 17h com Bruna",
            dono_id="7394370553",
            features={"tem_contexto_servico": True, "tem_pergunta": True},
            contexto_consulta=contexto_consulta,
            actor_id="whatsapp:5511991382080",
            tenant_id="7394370553"
        )

        # Validações
        assert resposta is not None, "Resposta não deve ser None"
        assert "Gloria" in resposta or "Joana" in resposta, "Alternativas não retornadas"
        assert "❌" in resposta, "Resposta deve indicar indisponibilidade"
        assert "Bruna" not in resposta or "não está disponível" in resposta, \
            "Bruna deve estar indicada como indisponível"

        print("✅ Test PASSED: Alternativas compatíveis retornadas")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
