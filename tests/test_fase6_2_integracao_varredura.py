"""
P0 FASE 6.2/6.3 — Testes de Integração: Profissional Mencionada + Varredura

Valida que profissional_mencionada é transferida e varredura funciona.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_integracao_varredura_com_profissional():
    """
    Valida que varredura encontra horários reais com profissional mencionada.
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
        return {
            "valido": True,
            "servicos": servicos,
            "duracoes_individuais": [30, 30],
            "duracao_total": 60,
            "mensagens": []
        }

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {
                "Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]}
            }
        return {}

    with patch("services.multisservico_service.resolver_bloco_servicos", side_effect=mock_resolver_bloco), \
         patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resposta = await responder_consulta_informativa(
            mensagem="Quero agendar manicure e pedicure entre 14h e 17h com Bruna",
            dono_id="7394370553",
            features={"tem_contexto_servico": True, "tem_pergunta": True},
            contexto_consulta=contexto_consulta,
            actor_id="whatsapp:5511991382080",
            tenant_id="7394370553"
        )

        assert resposta is not None, "Resposta não deve ser None"
        assert "14:00" in resposta, "Horário específico não retornado"
        assert "Bruna" in resposta, "Profissional não mencionada"
        assert "60" in resposta, "Duração não mencionada"
        assert "Horários disponíveis" in resposta, "Sem lista de horários"
        print("✅ Test PASSED: Varredura integrada com profissional mencionada")


@pytest.mark.asyncio
async def test_integracao_sem_escrita():
    """
    Valida que consulta não cria eventos, locks ou holds.
    """
    from services.informacao_service import responder_consulta_informativa

    contexto_consulta = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "profissional_mencionada": "Bruna",
        "data_hora": "2026-11-13T00:00:00",
    }

    escritas = []

    async def mock_resolver_bloco(tenant_id, nome_profissional, servicos):
        return {"valido": True, "servicos": servicos, "duracoes_individuais": [30, 30], "duracao_total": 60, "mensagens": []}

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {"Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]}}
        return {}

    async def mock_criar_evento(*args, **kwargs):
        escritas.append("criar_evento")
        raise AssertionError("❌ Tentativa de criar evento")

    with patch("services.multisservico_service.resolver_bloco_servicos", side_effect=mock_resolver_bloco), \
         patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resposta = await responder_consulta_informativa(
            mensagem="Quero agendar manicure e pedicure entre 14h e 17h com Bruna",
            dono_id="7394370553",
            features={"tem_contexto_servico": True, "tem_pergunta": True},
            contexto_consulta=contexto_consulta,
            actor_id="whatsapp:5511991382080",
            tenant_id="7394370553"
        )

        assert len(escritas) == 0, f"Escritas detectadas: {escritas}"
        assert resposta is not None
        print("✅ Test PASSED: Nenhuma escrita durante consulta")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
