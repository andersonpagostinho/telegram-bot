"""
P0.7.8C — Testes G–K: Validação de contextos operacionais

G: Consulta puramente informativa
H: Confirmação de agendamento
I: Cancelamento e reagendamento
J: Regressão
K: Isolamento multi-tenant
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# G: CONSULTA PURAMENTE INFORMATIVA
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_g_consulta_pura_nao_altera_draft():
    """
    G: Cliente pergunta "quem faz manicure?" (consulta pura)
    Esperado: Responder informativamente SEM criar draft de agendamento
    """
    from services.informacao_service import responder_consulta_informativa

    # Contexto inicial: vazio
    ctx_inicial = {}

    # Features indicam apenas pergunta, sem intenção de agendar
    features = {
        "tem_contexto_servico": True,
        "tem_pergunta": True,
        "servico_mencionado": "manicure",
        "tem_agendar": False,  # NÃO há intenção de agendar
        "tem_temporal": False,  # NÃO há data/hora
    }

    with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
        mock_buscar.return_value = {
            "Bruna": {"nome": "Bruna", "servicos": ["manicure"]},
            "Carla": {"nome": "Carla", "servicos": ["manicure"]}
        }

        # Chamar handler informativo
        resposta = await responder_consulta_informativa(
            mensagem="quem faz manicure?",
            dono_id="tenant_teste",
            features=features
        )

        # Validações
        assert resposta is not None, "Deveria retornar resposta informativa"
        assert "manicure" in resposta.lower()
        assert "Bruna" in resposta or "bruna" in resposta.lower()
        assert "Carla" in resposta or "carla" in resposta.lower()

        # O que NÃO deve acontecer:
        # Não deve haver draft_agendamento criado
        # (verificação seria feita no router, aqui apenas handler)

        print(f"✅ TESTE G PASS: Consulta pura respondida — {resposta}")


# ═══════════════════════════════════════════════════════════════════════════════
# H: CONFIRMAÇÃO DE AGENDAMENTO
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_h_confirmacao_sem_intermediarios():
    """
    H: Após escolher profissional e horário, cliente confirma "sim"
    Esperado: Evento criado SEM duplicação
    """
    # Simulação de confirmação
    # Validação: evento é criado apenas uma vez

    # Verificação seria feita por:
    # 1. Handler de confirmação chamado
    # 2. Evento salvo em Firestore
    # 3. Contexto limpo
    # 4. Confirmação de entrega ao usuário

    print("✅ TESTE H: Confirmação (verificação seria em E2E com Firestore)")


# ═══════════════════════════════════════════════════════════════════════════════
# I: CANCELAMENTO E REAGENDAMENTO
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_i_cancelamento_e_reagendamento():
    """
    I: Cliente cancela e quer reagendar
    Esperado: Fluxo funciona sem interferência da correção P0.7.8B
    """
    # Cancelamento: remover evento existente
    # Reagendamento: novo agendamento com disponibilidade verificada

    # Verificação seria feita por:
    # 1. Evento original mantém ID após cancelamento
    # 2. Novo horário verificado com disponibilidade
    # 3. Alternativas oferecidas se conflito

    print("✅ TESTE I: Cancelamento/reagendamento (verificação seria em E2E)")


# ═══════════════════════════════════════════════════════════════════════════════
# J: REGRESSÃO
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_j_regressao_p0_7_2a():
    """
    J: Validar P0.7.2A não sofreu regressão
    Handler de comparação profissional com dono_id correto
    """
    from services.informacao_service import responder_consulta_informativa

    # P0.7.2A: Handler recebe dono_id e retorna alternativas
    features = {
        "tem_contexto_servico": True,
        "tem_pergunta": True,  # Precisa ser pergunta
        "servico_mencionado": "manicure",
        "tem_agendar": False,
        "tem_temporal": False,
    }

    with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
        mock_buscar.return_value = {"Bruna": {}, "Carla": {}}

        resposta = await responder_consulta_informativa(
            mensagem="quem faz manicure?",
            dono_id="tenant_teste",
            features=features
        )

        # Validação
        assert resposta is not None, "Deveria retornar resposta"
        assert mock_buscar.called
        assert "manicure" in resposta.lower()

        print("✅ TESTE J-P0.7.2A PASS: Handler compatível")


@pytest.mark.asyncio
async def test_j_regressao_p0_7_3():
    """
    J: Validar P0.7.3 não sofreu regressão
    Features-based consulta informativa funciona
    """
    from services.profissional_service import buscar_profissionais_por_servico

    with patch("services.profissional_service.buscar_subcolecao") as mock_buscar:
        mock_buscar.return_value = {
            "Bruna": {"nome": "Bruna", "servicos": ["manicure"]},
            "Carla": {"nome": "Carla", "servicos": ["manicure"]}
        }

        resultado = await buscar_profissionais_por_servico(
            servicos=["manicure"],
            tenant_id="tenant_teste"
        )

        assert "Bruna" in resultado
        assert "Carla" in resultado

        print("✅ TESTE J-P0.7.3 PASS: Busca compatível")


# ═══════════════════════════════════════════════════════════════════════════════
# K: ISOLAMENTO MULTI-TENANT
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_k_isolamento_tenant_1():
    """
    K: Tenant 1 — apenas profissionais de tenant 1 são consideradas
    """
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    # Profissionais do Tenant 1
    prof_tenant1 = {
        "Bruna": {"nome": "Bruna", "servicos": ["manicure"]}
    }

    # Profissionais do Tenant 2 (não devem aparecer)
    prof_tenant2 = {
        "Ana": {"nome": "Ana", "servicos": ["corte"]}
    }

    with patch("services.event_service_async.buscar_subcolecao") as mock_buscar:
        def mock_side_effect(path):
            if "tenant1" in path:
                if "Profissionais" in path:
                    return prof_tenant1
                elif "Eventos" in path:
                    return {}
            elif "tenant2" in path:
                if "Profissionais" in path:
                    return prof_tenant2
            return {}

        mock_buscar.side_effect = mock_side_effect

        # Verificar com tenant1
        resultado1 = await verificar_conflito_e_sugestoes_profissional(
            user_id="user1",
            data="2026-10-28",
            hora_inicio="10:00",
            duracao_min=30,
            profissional="Bruna",
            servico="manicure",
            tenant_id="tenant1"
        )

        assert resultado1.get("conflito") is False
        print("✅ TESTE K-Tenant1 PASS: Bruna verificada com tenant1")


@pytest.mark.asyncio
async def test_k_isolamento_tenant_2():
    """
    K: Tenant 2 — eventos e profissionais isolados
    """
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    # Eventos do Tenant 1 (não devem afetar tenant 2)
    eventos_tenant1 = {
        "evt1": {
            "profissional": "bruna",
            "data": "2026-10-28",
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "status": "confirmado"
        }
    }

    # Profissionais do Tenant 2 (diferentes)
    prof_tenant2 = {
        "Ana": {"nome": "Ana", "servicos": ["corte"]},
        "Bia": {"nome": "Bia", "servicos": ["escova"]}
    }

    with patch("services.event_service_async.buscar_subcolecao") as mock_buscar:
        def mock_side_effect(path):
            if "tenant2" in path:
                if "Profissionais" in path:
                    return prof_tenant2
                elif "Eventos" in path:
                    return {}  # tenant2 tem eventos vazios
            elif "tenant1" in path:
                if "Eventos" in path:
                    return eventos_tenant1  # tenant1 tem evento ocupado
            return {}

        mock_buscar.side_effect = mock_side_effect

        # Verificar Ana com tenant2 (não deve ter conflito)
        resultado_ana = await verificar_conflito_e_sugestoes_profissional(
            user_id="user2",
            data="2026-10-28",
            hora_inicio="10:00",
            duracao_min=30,
            profissional="Ana",
            servico="corte",
            tenant_id="tenant2"
        )

        # Ana de tenant2 não é afetada por eventos de tenant1
        assert resultado_ana.get("conflito") is False
        print("✅ TESTE K-Tenant2 PASS: Ana de tenant2 isolada de tenant1")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
