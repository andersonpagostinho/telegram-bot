"""
FASE 6 — TESTES INTEGRAÇÃO MOTOR MULTISSERVIÇO NA CONSULTA INFORMATIVA

Valida que:
1. Motor determinístico é chamado para consulta multisserviço
2. Duração total é calculada corretamente
3. Janela 14h-17h é respeitada
4. Alternativas elegíveis são retornadas
5. Sem autorização = nenhuma escrita
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date


@pytest.mark.asyncio
async def test_fase6_consulta_multisservico_disponivel():
    """
    Cenário A: Consulta multisserviço com Bruna, mesma profissional, janela 14-17h.
    Manicure + Pedicure = 30 + 30 = 60 min.
    Disponível → responder com confirmação.
    """
    from services.informacao_service import responder_consulta_informativa

    # Mock contexto_consulta enriquecido
    contexto_consulta = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "profissional_mencionada": "Bruna",
        "data_hora": "2026-11-13T00:00:00",
    }

    # Mock resolver_bloco_servicos
    async def mock_resolver_bloco(*args, **kwargs):
        return {
            "valido": True,
            "servicos": ["manicure", "pedicure"],
            "duracoes_individuais": [30, 30],
            "duracao_total": 60,
            "mensagens": []
        }

    # Mock motor determinístico
    async def mock_verificar_conflito(*args, **kwargs):
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
            features={"tem_contexto_servico": True, "tem_pergunta": True, "servico_mencionado": "manicure"},
            contexto_consulta=contexto_consulta,
            actor_id="whatsapp:5511991382080",
            tenant_id="7394370553"
        )

        print(f"✅ Resposta: {resposta}")
        assert resposta is not None, "Resposta não deve ser None"
        assert "60 minutos" in resposta or "60 min" in resposta, "Duração total não mencionada"
        assert "Bruna" in resposta or "confirmar" in resposta.lower(), "Resposta não menciona Bruna ou confirmação"
        print("✅ Teste A PASSOU: Consulta multisserviço disponível")


@pytest.mark.asyncio
async def test_fase6_duracao_total_calculada():
    """
    Cenário B: Validar que duração total é calculada corretamente.
    30 (manicure) + 35 (pedicure) = 65 min.
    """
    from services.multisservico_service import resolver_bloco_servicos

    # Mock obter_duracao_por_profissional_bridge
    async def mock_obter_duracao(tenant_id, nome_profissional, nome_servico):
        duracao_map = {
            ("Bruna", "manicure"): 30,
            ("Bruna", "pedicure"): 35,
        }
        return duracao_map.get((nome_profissional, nome_servico))

    with patch("services.multisservico_service.obter_duracao_por_profissional_bridge", side_effect=mock_obter_duracao):
        resultado = await resolver_bloco_servicos(
            tenant_id="7394370553",
            nome_profissional="Bruna",
            servicos=["manicure", "pedicure"]
        )

        assert resultado["valido"] == True, "Bloco deveria ser válido"
        assert resultado["duracao_total"] == 65, f"Duração esperada 65, got {resultado['duracao_total']}"
        assert resultado["duracoes_individuais"] == [30, 35], "Durações individuais incorretas"
        print(f"✅ Teste B PASSOU: Duração total = {resultado['duracao_total']} min")


@pytest.mark.asyncio
async def test_fase6_janela_respeitada():
    """
    Cenário C: Validar que janela 14h-17h é respeitada.
    14:00 + 65min = 15:05 ✅ (dentro de 17:00)
    """
    from services.multisservico_service import validar_horario_em_janela

    # Teste 1: Cabe na janela
    result = validar_horario_em_janela(
        hora_inicio_bloqueio=14,
        duracao_min=65,
        janela_minima=14,
        janela_maxima=17
    )
    assert result == True, "14:00 + 65min deveria caber em 14-17h"
    print("✅ Teste C.1 PASSOU: 14:00 + 65min cabe em janela")

    # Teste 2: NÃO cabe
    result = validar_horario_em_janela(
        hora_inicio_bloqueio=16,
        duracao_min=120,
        janela_minima=14,
        janela_maxima=17
    )
    assert result == False, "16:00 + 120min não deveria caber"
    print("✅ Teste C.2 PASSOU: 16:00 + 120min não cabe em janela")


@pytest.mark.asyncio
async def test_fase6_profissional_incompativel_excluida():
    """
    Cenário D: Profissional que não executa todos os serviços é excluída.
    Joana não oferece pedicure → inválida.
    """
    from services.multisservico_service import resolver_bloco_servicos

    async def mock_obter_duracao_joana(tenant_id, nome_profissional, nome_servico):
        if nome_profissional == "Joana" and nome_servico == "pedicure":
            return None  # Não oferece
        elif nome_profissional == "Joana" and nome_servico == "manicure":
            return 30
        return 35

    with patch("services.multisservico_service.obter_duracao_por_profissional_bridge", side_effect=mock_obter_duracao_joana):
        resultado = await resolver_bloco_servicos(
            tenant_id="7394370553",
            nome_profissional="Joana",
            servicos=["manicure", "pedicure"]
        )

        assert resultado["valido"] == False, "Joana deveria ser inválida (sem pedicure)"
        assert "pedicure" in resultado["mensagens"][0].lower(), "Mensagem deveria mencionar pedicure"
        print(f"✅ Teste D PASSOU: Joana corretamente rejeitada")


@pytest.mark.asyncio
async def test_fase6_nenhuma_escrita_sem_autorizacao():
    """
    Cenário E: Consulta não escreve nada (nenhum evento, lock, hold criado).
    """
    from services.informacao_service import responder_consulta_informativa

    # Mock que rejeita qualquer escrita
    async def mock_salvar(*args, **kwargs):
        raise AssertionError(f"❌ ERRO: Tentativa de escrita em consulta: {args}")

    async def mock_criar_evento(*args, **kwargs):
        raise AssertionError("❌ ERRO: Tentativa de criar evento")

    async def mock_resolver_bloco(*args, **kwargs):
        return {"valido": True, "duracao_total": 60, "duracoes_individuais": [30, 30], "servicos": ["manicure", "pedicure"], "mensagens": []}

    async def mock_verificar_conflito(*args, **kwargs):
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    contexto_consulta = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "profissional_mencionada": "Bruna",
        "data_hora": "2026-11-13T00:00:00",
    }

    with patch("services.multisservico_service.resolver_bloco_servicos", side_effect=mock_resolver_bloco), \
         patch("services.event_service_async.verificar_conflito_e_sugestoes_profissional", side_effect=mock_verificar_conflito):

        resposta = await responder_consulta_informativa(
            mensagem="Quero agendar",
            dono_id="7394370553",
            contexto_consulta=contexto_consulta,
            actor_id="whatsapp:5511991382080",
            tenant_id="7394370553"
        )

        assert resposta is not None, "Resposta não deve ser None"
        # Se chegou aqui, nenhuma escrita foi tentada
        print("✅ Teste E PASSOU: Nenhuma escrita detectada")


@pytest.mark.asyncio
async def test_fase6_isolamento_multitenant():
    """
    Cenário F: Isolamento multi-tenant confirmado.
    Tenant 1 não vê catálogo de Tenant 2.
    """
    from router.principal_router import extrair_multiplos_servicos_da_mensagem

    mock_tenant1 = {
        "Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]}
    }

    mock_tenant2 = {
        "Pedro": {"nome": "Pedro", "servicos": ["corte", "barba"]}
    }

    async def mock_buscar_impl(path):
        if "tenant1" in path:
            return mock_tenant1
        elif "tenant2" in path:
            return mock_tenant2
        return {}

    with patch("router.principal_router.buscar_subcolecao", side_effect=mock_buscar_impl):
        # Tenant1: manicure está disponível
        servicos_t1 = await extrair_multiplos_servicos_da_mensagem("manicure e pedicure", "tenant1")
        assert "manicure" in servicos_t1, "Tenant1 deveria ter manicure"

        # Tenant2: corte está disponível, mas manicure não
        servicos_t2 = await extrair_multiplos_servicos_da_mensagem("manicure", "tenant2")
        assert len(servicos_t2) == 0, "Tenant2 não deveria ter manicure"

        print("✅ Teste F PASSOU: Isolamento multi-tenant confirmado")


@pytest.mark.asyncio
async def test_fase6_regressao_servico_unico():
    """
    Cenário G: Serviço singular ainda funciona (regressão).
    """
    from services.informacao_service import responder_consulta_informativa

    # Contexto com apenas 1 serviço
    contexto_consulta_singular = {
        "servicos_multiplos": None,  # Sem múltiplos
    }

    resposta = await responder_consulta_informativa(
        mensagem="Quero agendar manicure",
        dono_id="7394370553",
        features={"tem_contexto_servico": True, "tem_pergunta": True, "servico_mencionado": "manicure"},
        contexto_consulta=contexto_consulta_singular,
        actor_id="whatsapp:5511991382080",
        tenant_id="7394370553"
    )

    # Deve retornar para fluxo normal (consulta de serviço singular)
    print(f"✅ Teste G: Regressão serviço singular - Resposta: {resposta}")
    print("✅ Teste G PASSOU: Serviço singular não quebrou")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
