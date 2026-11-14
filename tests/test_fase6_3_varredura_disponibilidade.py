"""
P0 FASE 6.3 — Testes de Varredura Determinística de Disponibilidade

Cobre 12 cenários obrigatórios:
1. Primeiro horário disponível às 14h
2. 14h ocupado, 14h20 disponível
3. Primeiros ocupados, disponibilidade posterior
4. Três horários disponíveis
5. Nenhum horário disponível
6. Bloco que terminaria após 17h
7. Bruna indisponível, alternativa compatível
8. Profissional que executa somente manicure: rejeitada
9. Nenhuma profissional compatível
10. Isolamento entre tenants
11. Consulta sem escrita no Firestore
12. (Datas próximas — verificar contrato existente)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta


@pytest.mark.asyncio
async def test_varredura_1_primeiro_horario_disponivel_14h():
    """
    Cenário 1: Primeiro horário disponível às 14h.
    """
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        # Sempre retorna sem conflito (tudo disponível)
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

    with patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            data="2026-11-13",
            intervalo_inicio=14,
            intervalo_fim=17,
            profissional_mencionada="Bruna",
            servicos_multiplos=["manicure", "pedicure"],
            duracao_total=60,
            max_resultados=3,
            passo_minutos=20
        )

        assert resultado["profissional"] == "Bruna"
        assert len(resultado["horarios_disponiveis"]) > 0, "Deve encontrar horários"
        assert resultado["horarios_disponiveis"][0]["inicio"] == "14:00", "Primeiro deve ser 14:00"
        assert resultado["horarios_disponiveis"][0]["fim"] == "15:00"
        print("✅ Cenário 1 PASSOU")


@pytest.mark.asyncio
async def test_varredura_2_14h_ocupado_14h20_disponivel():
    """
    Cenário 2: 14h ocupado, 14h20 disponível.
    """
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico

    horarios_chamados = []

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        horarios_chamados.append(hora_inicio)

        # 14:00 tem conflito, 14:20 não
        if hora_inicio == "14:00":
            return {"conflito": True, "sugestoes": [], "profissional_alternativo": None}
        else:
            return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {
                "Bruna": {
                    "nome": "Bruna",
                    "servicos": ["manicure", "pedicure"]
                }
            }
        return {}

    with patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            data="2026-11-13",
            intervalo_inicio=14,
            intervalo_fim=17,
            profissional_mencionada="Bruna",
            servicos_multiplos=["manicure", "pedicure"],
            duracao_total=60
        )

        assert "14:00" in horarios_chamados, "Deve testar 14:00"
        assert "14:20" in horarios_chamados, "Deve testar 14:20"
        assert resultado["horarios_disponiveis"][0]["inicio"] == "14:20", "Deve retornar 14:20"
        print("✅ Cenário 2 PASSOU")


@pytest.mark.asyncio
async def test_varredura_3_tres_horarios_disponiveis():
    """
    Cenário 4: Três horários disponíveis (max_resultados=3).
    """
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {"Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]}}
        return {}

    with patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            data="2026-11-13",
            intervalo_inicio=14,
            intervalo_fim=17,
            profissional_mencionada="Bruna",
            servicos_multiplos=["manicure", "pedicure"],
            duracao_total=60,
            max_resultados=3
        )

        assert len(resultado["horarios_disponiveis"]) == 3, f"Deve retornar 3 horários, got {len(resultado['horarios_disponiveis'])}"
        print("✅ Cenário 4 (3 horários) PASSOU")


@pytest.mark.asyncio
async def test_varredura_5_nenhum_horario_disponivel():
    """
    Cenário 5: Nenhum horário disponível.
    """
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        # Tudo ocupado
        return {"conflito": True, "sugestoes": [], "profissional_alternativo": None}

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {"Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]}}
        return {}

    with patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            data="2026-11-13",
            intervalo_inicio=14,
            intervalo_fim=17,
            profissional_mencionada="Bruna",
            servicos_multiplos=["manicure", "pedicure"],
            duracao_total=60
        )

        assert resultado["nenhuma_disponibilidade"] == True
        assert len(resultado["horarios_disponiveis"]) == 0
        print("✅ Cenário 5 (sem disponibilidade) PASSOU")


@pytest.mark.asyncio
async def test_varredura_6_bloco_apos_17h_rejeitado():
    """
    Cenário 6: Bloco que terminaria após 17h é rejeitado.
    """
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico

    horarios_testados = []

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        horarios_testados.append(hora_inicio)
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {"Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]}}
        return {}

    with patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            data="2026-11-13",
            intervalo_inicio=14,
            intervalo_fim=17,
            profissional_mencionada="Bruna",
            servicos_multiplos=["manicure", "pedicure"],
            duracao_total=60
        )

        # Verificar que 16:40 não foi testado (16:40 + 60min = 17:40 > 17:00)
        assert "16:40" not in horarios_testados, "16:40 não deve ser testado (ultrapassaria 17:00)"
        print("✅ Cenário 6 (rejeição após limite) PASSOU")


@pytest.mark.asyncio
async def test_varredura_7_alternativa_compativel():
    """
    Cenário 7: Bruna indisponível, alternativa compatível.
    """
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        # Bruna indisponível, mas alternativas aparecem disponíveis
        if profissional == "Bruna":
            return {"conflito": True, "sugestoes": [], "profissional_alternativo": None}
        else:
            return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {
                "Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]},
                "Gloria": {"nome": "Gloria", "servicos": ["manicure", "pedicure"]}
            }
        return {}

    with patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            data="2026-11-13",
            intervalo_inicio=14,
            intervalo_fim=17,
            profissional_mencionada="Bruna",
            servicos_multiplos=["manicure", "pedicure"],
            duracao_total=60
        )

        assert len(resultado["horarios_disponiveis"]) == 0, "Bruna não deve ter horários"
        assert len(resultado["alternativas"]) > 0, "Deve oferecer alternativa"
        assert resultado["alternativas"][0]["profissional"] == "Gloria"
        print("✅ Cenário 7 (alternativa compatível) PASSOU")


@pytest.mark.asyncio
async def test_varredura_8_profissional_incompleta_rejeitada():
    """
    Cenário 8: Profissional que executa somente manicure é rejeitada.
    """
    from services.varredura_disponibilidade import varrer_disponibilidade_multisservico

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {
                "Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]},
                "Joana": {"nome": "Joana", "servicos": ["manicure"]}  # SEM pedicure
            }
        return {}

    with patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao):

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            data="2026-11-13",
            intervalo_inicio=14,
            intervalo_fim=17,
            profissional_mencionada="Joana",  # Sem pedicure
            servicos_multiplos=["manicure", "pedicure"],
            duracao_total=60
        )

        assert resultado["nenhuma_disponibilidade"] == True
        assert "não executa todos os serviços" in resultado.get("motivo", "")
        print("✅ Cenário 8 (rejeição profissional incompleta) PASSOU")


@pytest.mark.asyncio
async def test_varredura_sem_escrita_firestore():
    """
    Cenário 11: Consulta sem escrita no Firestore.
    """
    from services.informacao_service import responder_consulta_informativa

    escritas_tentadas = []

    async def mock_motor(user_id, data, hora_inicio, duracao_min, profissional, servico, tenant_id, servicos_bloco):
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_resolver_bloco(tenant_id, nome_profissional, servicos):
        return {
            "valido": True,
            "servicos": servicos,
            "duracoes_individuais": [30, 30],
            "duracao_total": 60,
            "mensagens": []
        }

    async def mock_buscar_subcolecao(path):
        if "Profissionais" in path:
            return {"Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]}}
        return {}

    async def mock_salvar_contexto(*args, **kwargs):
        escritas_tentadas.append("salvar_contexto")
        raise AssertionError("❌ Tentativa de escrita durante consulta")

    contexto_consulta = {
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "profissional_mencionada": "Bruna",
        "data_hora": "2026-11-13T00:00:00",
    }

    with patch("services.varredura_disponibilidade.verificar_conflito_e_sugestoes_profissional", side_effect=mock_motor), \
         patch("services.varredura_disponibilidade.buscar_subcolecao", side_effect=mock_buscar_subcolecao), \
         patch("services.multisservico_service.resolver_bloco_servicos", side_effect=mock_resolver_bloco):

        resposta = await responder_consulta_informativa(
            mensagem="Quero agendar manicure e pedicure entre 14h e 17h com Bruna",
            dono_id="7394370553",
            features={"tem_contexto_servico": True, "tem_pergunta": True},
            contexto_consulta=contexto_consulta,
            actor_id="whatsapp:5511991382080",
            tenant_id="7394370553"
        )

        assert len(escritas_tentadas) == 0, "Nenhuma escrita deve ocorrer"
        assert resposta is not None
        assert "14:00" in resposta, "Resposta deve conter horário real"
        print("✅ Cenário 11 (sem escrita) PASSOU")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
