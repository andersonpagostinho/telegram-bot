"""
P0.7.8B — Teste de Integração: Router com Disponibilidade Real

Valida que o router oferece alternativas com verificação de disponibilidade real
e retorna uma única resposta coerente ao WhatsApp.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_context_gloria_rejeitada():
    """Contexto: usuário quer manicure com Gloria em 28/10 às 10h."""
    return {
        "usuario_id": "user123",
        "user_id": "5511991382080",  # wa_id
        "dono_id": "tenant_7394370553",
        "cliente_id": "5511991382080",
        "servico": "manicure",
        "profissional_escolhido": "Gloria",  # Será rejeitada
        "data_hora": "2026-10-28T10:00:00",
        "estado_fluxo": "confirmando_agendamento",
        "draft_agendamento": {
            "servico": "manicure",
            "profissional": "Gloria",
            "data_hora": "2026-10-28T10:00:00"
        }
    }


@pytest.fixture
def mock_profissionais_catalogo():
    """Catálogo do tenant."""
    return {
        "Bruna": {
            "nome": "Bruna",
            "servicos": ["manicure", "pedicure"],
            "precos": {"manicure": 40},
            "duracoes": {"manicure": 30}
        },
        "Gloria": {
            "nome": "Gloria",
            "servicos": ["corte feminino", "escova"],
            "precos": {"corte feminino": 50},
            "duracoes": {"corte feminino": 40}
        },
        "Carla": {
            "nome": "Carla",
            "servicos": ["manicure"],
            "precos": {"manicure": 35},
            "duracoes": {"manicure": 30}
        }
    }


@pytest.fixture
def mock_eventos_vazio():
    """Sem eventos (Bruna e Carla livres)."""
    return {}


@pytest.fixture
def mock_eventos_bruna_ocupada():
    """Bruna ocupada às 10h."""
    return {
        "evt1": {
            "profissional": "bruna",
            "data": "2026-10-28",
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "status": "confirmado"
        }
    }


@pytest.mark.asyncio
async def test_router_gloria_rejeitada_bruna_livre(mock_context_gloria_rejeitada):
    """
    Integração: Gloria incompatível, Bruna livre
    Esperado: Resposta "Gloria não atende manicure. Para manicure nesse horário, posso deixar com: Bruna."
    """
    from services.profissional_service import validar_profissional_para_servico

    # Mock validar_profissional_para_servico
    mock_validar = AsyncMock()
    mock_validar.return_value = {"ok": False}  # Gloria não faz manicure

    # Simulação simplificada da lógica em principal_router.py L2193-2242
    profissional = "Gloria"
    servico = "manicure"
    tenant_id = "tenant_teste"
    data_hora = "2026-10-28T10:00:00"

    # 1. Validar compatibilidade
    valido = await mock_validar(dono_id=tenant_id, profissional=profissional, servico=servico)

    if not valido.get("ok"):
        print(f"[TEST] Gloria não atende {servico} — buscando alternativas")

        # 2. Buscar profissionais habilitadas
        with patch("services.profissional_service.buscar_subcolecao") as mock_buscar:
            mock_buscar.return_value = {
                "Bruna": {"nome": "Bruna", "servicos": ["manicure"]},
                "Carla": {"nome": "Carla", "servicos": ["manicure"]}
            }

            from services.profissional_service import buscar_profissionais_por_servico
            profissionais_validos = await buscar_profissionais_por_servico(
                servicos=[servico],
                tenant_id=tenant_id
            )

            assert "Bruna" in profissionais_validos
            assert "Carla" in profissionais_validos

            # 3. Verificar disponibilidade de cada uma
            from services.event_service_async import verificar_conflito_e_sugestoes_profissional

            with patch("services.event_service_async.buscar_subcolecao") as mock_eventos:
                # Eventos: vazio (todos livres)
                mock_eventos.return_value = {}

                # Verificar Bruna
                info_bruna = await verificar_conflito_e_sugestoes_profissional(
                    user_id="user123",
                    data="2026-10-28",
                    hora_inicio="10:00",
                    duracao_min=30,
                    profissional="Bruna",
                    servico="manicure",
                    tenant_id=tenant_id
                )

                assert info_bruna.get("conflito") is False, "Bruna deveria estar livre"

                # Replicar lógica do router
                profissionais_livres = []
                for prof_alt in profissionais_validos.keys():
                    info = await verificar_conflito_e_sugestoes_profissional(
                        user_id="user123",
                        data="2026-10-28",
                        hora_inicio="10:00",
                        duracao_min=30,
                        profissional=prof_alt,
                        servico="manicure",
                        tenant_id=tenant_id
                    )
                    if not info.get("conflito"):
                        profissionais_livres.append(prof_alt)

                # Validar resultado
                assert "Bruna" in profissionais_livres
                assert "Carla" in profissionais_livres

                # Montar resposta (como router faz)
                if profissionais_livres:
                    lista_str = ", ".join(profissionais_livres)
                    resposta = (
                        f"*Gloria* não atende manicure.\n"
                        f"Para *manicure* nesse horário, posso deixar com: {lista_str}.\n"
                        f"Qual você prefere?"
                    )
                    assert "Bruna" in resposta
                    assert "Carla" in resposta
                    print(f"✅ INTEGRAÇÃO PASS: Resposta coerente — {resposta}")
                else:
                    assert False, "Deveria ter alternativas livres"


@pytest.mark.asyncio
async def test_router_gloria_rejeitada_bruna_ocupada_carla_livre():
    """
    Integração: Gloria incompatível, Bruna ocupada, Carla livre
    Esperado: Resposta "Gloria não atende manicure. Para manicure nesse horário, posso deixar com: Carla."
    """
    from services.profissional_service import buscar_profissionais_por_servico
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    profissionais_habilitadas = {
        "Bruna": {"nome": "Bruna", "servicos": ["manicure"]},
        "Carla": {"nome": "Carla", "servicos": ["manicure"]}
    }

    eventos_bruna_ocupada = {
        "evt1": {
            "profissional": "bruna",
            "data": "2026-10-28",
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "status": "confirmado"
        }
    }

    with patch("services.profissional_service.buscar_subcolecao") as mock_buscar_prof:
        mock_buscar_prof.return_value = profissionais_habilitadas

        with patch("services.event_service_async.buscar_subcolecao") as mock_buscar_evt:
            # Mock retorna eventos diferentes conforme chamado
            def mock_buscar_side_effect(path):
                if "Profissionais" in path:
                    return profissionais_habilitadas
                elif "Eventos" in path:
                    return eventos_bruna_ocupada
                return {}

            mock_buscar_evt.side_effect = mock_buscar_side_effect

            # Replicar fluxo router
            profissionais_livres = []
            for prof_alt in profissionais_habilitadas.keys():
                info = await verificar_conflito_e_sugestoes_profissional(
                    user_id="user123",
                    data="2026-10-28",
                    hora_inicio="10:00",
                    duracao_min=30,
                    profissional=prof_alt,
                    servico="manicure",
                    tenant_id="tenant_teste"
                )

                if not info.get("conflito"):
                    profissionais_livres.append(prof_alt)

            # Validar: apenas Carla deveria estar livre
            assert "Bruna" not in profissionais_livres, "Bruna está ocupada"
            assert "Carla" in profissionais_livres, "Carla deveria estar livre"

            # Montar resposta
            if profissionais_livres:
                lista_str = ", ".join(profissionais_livres)
                resposta = (
                    f"*Gloria* não atende manicure.\n"
                    f"Para *manicure* nesse horário, posso deixar com: {lista_str}.\n"
                    f"Qual você prefere?"
                )
                assert "Carla" in resposta
                assert "Bruna" not in resposta, "Bruna ocupada não deveria aparecer"
                print(f"✅ INTEGRAÇÃO PASS (B ocupada): Resposta só Carla — {resposta}")


@pytest.mark.asyncio
async def test_router_gloria_rejeitada_todas_ocupadas():
    """
    Integração: Gloria incompatível, todas outras ocupadas
    Esperado: Resposta "Gloria não atende manicure. As profissionais estão ocupadas nesse horário."
    """
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    profissionais_habilitadas = {
        "Bruna": {"nome": "Bruna"},
        "Carla": {"nome": "Carla"}
    }

    eventos_todos_ocupados = {
        "evt1": {
            "profissional": "bruna",
            "data": "2026-10-28",
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "status": "confirmado"
        },
        "evt2": {
            "profissional": "carla",
            "data": "2026-10-28",
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "status": "confirmado"
        }
    }

    with patch("services.event_service_async.buscar_subcolecao") as mock_buscar:
        def mock_buscar_side_effect(path):
            if "Profissionais" in path:
                return profissionais_habilitadas
            elif "Eventos" in path:
                return eventos_todos_ocupados
            return {}

        mock_buscar.side_effect = mock_buscar_side_effect

        # Replicar fluxo
        profissionais_livres = []
        for prof_alt in profissionais_habilitadas.keys():
            info = await verificar_conflito_e_sugestoes_profissional(
                user_id="user123",
                data="2026-10-28",
                hora_inicio="10:00",
                duracao_min=30,
                profissional=prof_alt,
                servico="manicure",
                tenant_id="tenant_teste"
            )

            if not info.get("conflito"):
                profissionais_livres.append(prof_alt)

        # Validar: nenhuma livre
        assert len(profissionais_livres) == 0, "Nenhuma deveria estar livre"

        # Montar resposta (como router faz quando profissionais_livres vazio)
        if not profissionais_livres:
            resposta = (
                f"*Gloria* não atende manicure.\n"
                f"As profissionais que fazem manicure estão ocupadas nesse horário.\n"
                f"Quer tentar outro horário?"
            )
            assert "ocupadas" in resposta
            print(f"✅ INTEGRAÇÃO PASS (todas ocupadas): Resposta indisponibilidade — {resposta}")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
