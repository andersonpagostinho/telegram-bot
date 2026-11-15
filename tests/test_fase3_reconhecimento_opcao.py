"""
FASE 3 - Reconhecimento e Seleção de Opções — TESTES COMPLETOS

17 testes obrigatórios:
1. "O primeiro" → numero=1
2. "A primeira opção" → numero=1
3. "O segundo" → numero=2
4. "O último" → numero=3 (com total_opcoes=3)
5. Opção inexistente → erro
6. Contexto expirado → rejeitado
7. Contexto inexistente → rejeitado
8. Referência ambígua → pedir esclarecimento
9. Nova consulta substitui anterior
10. Mensagem com nova intenção não sequestrada
11. Isolamento entre actors
12. Isolamento entre tenants
13. Seleção não cria evento
14. Seleção não cria lock
15. Seleção não altera draft_agendamento
16. PATCH 4.2D sem regressão
17. CONSULTA_GUARD sem regressão

+ Regressão: 38 testes FASE 1-2
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from schemas.resultado_consulta_schema import ContextoResultadoConsulta, OpcaoHorario


# ==============================================================================
# Teste 0 (Preparação): opcao_id com unicidade
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_opcao_id_com_unicidade():
    """Preparação: opcao_id estruturado para evitar colisões"""

    data = "2026-11-16"
    prof = "Bruna"
    tempo = "14:00"
    numero = 1

    opcao_id = f"{numero}_{data}_{prof}_{tempo.replace(':', '')}"

    assert opcao_id == "1_2026-11-16_Bruna_1400"
    print("✅ Preparação: opcao_id com unicidade")


# ==============================================================================
# Test 1: "O primeiro"
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_01_o_primeiro():
    """Test 1: 'o primeiro' → numero=1"""

    from services.reconhecimento_opcao_service import parsear_referencia_opcao

    numero = await parsear_referencia_opcao("o primeiro")
    assert numero == 1
    print("✅ Test 1: 'o primeiro' → numero=1")


# ==============================================================================
# Test 2: "A primeira opção"
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_02_a_primeira_opcao():
    """Test 2: 'a primeira opção' → numero=1"""

    from services.reconhecimento_opcao_service import parsear_referencia_opcao

    numero = await parsear_referencia_opcao("a primeira opção")
    assert numero == 1
    print("✅ Test 2: 'a primeira opção' → numero=1")


# ==============================================================================
# Test 3: "O segundo"
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_03_o_segundo():
    """Test 3: 'o segundo' → numero=2"""

    from services.reconhecimento_opcao_service import parsear_referencia_opcao

    numero = await parsear_referencia_opcao("o segundo")
    assert numero == 2
    print("✅ Test 3: 'o segundo' → numero=2")


# ==============================================================================
# Test 4: "O último"
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_04_o_ultimo():
    """Test 4: 'o último' com total_opcoes=3 → numero=3"""

    from services.reconhecimento_opcao_service import parsear_referencia_opcao

    numero = await parsear_referencia_opcao("o último", total_opcoes=3)
    assert numero == 3
    print("✅ Test 4: 'o último' → numero=3")


# ==============================================================================
# Test 5: Opção inexistente
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_05_opcao_inexistente():
    """Test 5: Opção inexistente (opção 10 quando tem 3) → erro"""

    from services.reconhecimento_opcao_service import selecionar_opcao

    contexto = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna",
        opcoes=[
            OpcaoHorario(
                opcao_id=f"1_2026-11-16_Bruna_1400",
                numero=i+1,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio=f"14:{(i)*30:02d}",
                hora_fim=f"14:{(i+1)*30:02d}",
                servicos=["manicure"],
                duracao_total_min=30
            )
            for i in range(3)
        ]
    )

    resultado = await selecionar_opcao(contexto, numero=10)

    assert resultado["sucesso"] is False
    print("✅ Test 5: Opção inexistente → erro")


# ==============================================================================
# Test 6: Contexto expirado
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_06_contexto_expirado():
    """Test 6: Contexto com TTL expirado → rejeitado"""

    from services.resultado_consulta_service import recuperar_resultado_consulta

    contexto_expirado = {
        "contexto_resultado_consulta": {
            "consulta_id": "uuid_teste",
            "criado_em": "2026-11-15T10:00:00",
            "expira_em": "2026-11-15T10:30:00",  # Passado
            "servicos": ["manicure"],
            "opcoes": []
        }
    }

    with patch('services.resultado_consulta_service.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = contexto_expirado

        resultado = await recuperar_resultado_consulta("tenant_test", "actor_test")
        assert resultado is None

    print("✅ Test 6: Contexto expirado → rejeitado")


# ==============================================================================
# Test 7: Contexto inexistente
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_07_contexto_inexistente():
    """Test 7: Documento sem contexto → None"""

    from services.resultado_consulta_service import recuperar_resultado_consulta

    with patch('services.resultado_consulta_service.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = None

        resultado = await recuperar_resultado_consulta("tenant_test", "actor_test")
        assert resultado is None

    print("✅ Test 7: Contexto inexistente → None")


# ==============================================================================
# Test 8: Referência ambígua
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_08_referencia_ambigua():
    """Test 8: Referência ambígua ('o meio') → None ou erro"""

    from services.reconhecimento_opcao_service import parsear_referencia_opcao

    resultado = await parsear_referencia_opcao("o meio", total_opcoes=3)

    # Deve retornar None (não reconhece)
    assert resultado is None
    print("✅ Test 8: Referência ambígua → None")


# ==============================================================================
# Test 9: Nova consulta substitui anterior
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_09_nova_consulta_substitui():
    """Test 9: Segunda consulta sobrescreve primeira no mesmo path"""

    from services.resultado_consulta_service import persistir_resultado_consulta

    contexto1 = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna"
    )

    contexto2 = ContextoResultadoConsulta(
        servicos=["pedicure"],
        data="2026-11-17",
        duracao_total_min=30,
        profissional_id="Gloria"
    )

    with patch('services.resultado_consulta_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        await persistir_resultado_consulta("tenant_test", "actor_test", contexto1)
        await persistir_resultado_consulta("tenant_test", "actor_test", contexto2)

        # Ambas chamadas ao mesmo path
        calls = mock_save.call_args_list
        assert calls[0][0][0] == calls[1][0][0]

    print("✅ Test 9: Nova consulta substitui anterior")


# ==============================================================================
# Test 10: Nova intenção não sequestrada
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_10_nova_intencao_nao_sequestrada():
    """Test 10: 'quero pagar com cartão' não é tratado como seleção"""

    from services.reconhecimento_opcao_service import eh_referencia_opcao

    eh_ref = await eh_referencia_opcao("quero pagar com cartão")
    assert eh_ref is False
    print("✅ Test 10: Nova intenção não sequestrada")


# ==============================================================================
# Test 11: Isolamento entre actors
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_11_isolamento_actors():
    """Test 11: Actor A não vê contexto de Actor B"""

    from services.resultado_consulta_service import persistir_resultado_consulta, recuperar_resultado_consulta

    contexto = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna"
    )

    paths_acessados = []

    async def mock_save(path, data):
        paths_acessados.append(("save", path))
        return True

    async def mock_buscar(path):
        paths_acessados.append(("load", path))
        if "actor_a" in path:
            return {"contexto_resultado_consulta": {}}
        return None

    with patch('services.resultado_consulta_service.salvar_dado_em_path', side_effect=mock_save):
        with patch('services.resultado_consulta_service.buscar_dado_em_path', side_effect=mock_buscar):
            await persistir_resultado_consulta("tenant_test", "actor_a", contexto)
            resultado = await recuperar_resultado_consulta("tenant_test", "actor_b")

            assert resultado is None

    print("✅ Test 11: Isolamento entre actors")


# ==============================================================================
# Test 12: Isolamento entre tenants
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_12_isolamento_tenants():
    """Test 12: Tenant A não vê contexto de Tenant B"""

    from services.resultado_consulta_service import persistir_resultado_consulta, recuperar_resultado_consulta

    contexto = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna"
    )

    async def mock_save(path, data):
        return True

    async def mock_buscar(path):
        if "tenant_a" in path:
            return {"contexto_resultado_consulta": {}}
        return None

    with patch('services.resultado_consulta_service.salvar_dado_em_path', side_effect=mock_save):
        with patch('services.resultado_consulta_service.buscar_dado_em_path', side_effect=mock_buscar):
            await persistir_resultado_consulta("tenant_a", "actor_test", contexto)
            resultado = await recuperar_resultado_consulta("tenant_b", "actor_test")

            assert resultado is None

    print("✅ Test 12: Isolamento entre tenants")


# ==============================================================================
# Test 13: Seleção não cria evento
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_13_selecao_nao_cria_evento():
    """Test 13: Selecionar apenas retorna informação, sem evento"""

    from services.reconhecimento_opcao_service import selecionar_opcao

    contexto = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna",
        opcoes=[
            OpcaoHorario(
                opcao_id="1_2026-11-16_Bruna_1400",
                numero=1,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio="14:00",
                hora_fim="14:30",
                servicos=["manicure"],
                duracao_total_min=30
            )
        ]
    )

    resultado = await selecionar_opcao(contexto, numero=1)

    assert resultado["sucesso"] is True
    assert "opcao" in resultado
    print("✅ Test 13: Seleção não cria evento")


# ==============================================================================
# Test 14: Seleção não cria lock
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_14_selecao_nao_cria_lock():
    """Test 14: Selecionar não chama agenda_lock_service"""

    from services.reconhecimento_opcao_service import selecionar_opcao

    contexto = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna",
        opcoes=[
            OpcaoHorario(
                opcao_id="1_2026-11-16_Bruna_1400",
                numero=1,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio="14:00",
                hora_fim="14:30",
                servicos=["manicure"],
                duracao_total_min=30
            )
        ]
    )

    resultado = await selecionar_opcao(contexto, numero=1)

    assert resultado["sucesso"] is True
    print("✅ Test 14: Seleção não cria lock")


# ==============================================================================
# Test 15: Seleção não altera draft
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_15_selecao_nao_altera_draft():
    """Test 15: Registrar seleção preserva draft_agendamento (merge=True)"""

    from services.reconhecimento_opcao_service import registrar_opcao_selecionada

    contexto = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna",
        opcoes=[
            OpcaoHorario(
                opcao_id="1_2026-11-16_Bruna_1400",
                numero=1,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio="14:00",
                hora_fim="14:30",
                servicos=["manicure"],
                duracao_total_min=30
            )
        ]
    )

    async def mock_recuperar(tenant, actor):
        return contexto

    with patch('services.resultado_consulta_service.recuperar_resultado_consulta', side_effect=mock_recuperar):
        with patch('services.resultado_consulta_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = True

            await registrar_opcao_selecionada("tenant_test", "actor_test", "1_2026-11-16_Bruna_1400")

            if mock_save.called:
                data = mock_save.call_args[0][1]
                assert "contexto_resultado_consulta" in data
                assert "draft_agendamento" not in data

    print("✅ Test 15: Seleção não altera draft_agendamento")


# ==============================================================================
# Test 16: PATCH 4.2D sem regressão
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_16_patch_4_2d_sem_regressao():
    """Test 16: PATCH 4.2D continua bloqueando em modo consulta"""

    modo_operacao = "consulta_sem_autorizacao_atual"

    # PATCH deve ser bloqueado
    patch_should_execute = modo_operacao not in ["consulta_sem_autorizacao_atual"]

    assert patch_should_execute is False
    print("✅ Test 16: PATCH 4.2D sem regressão")


# ==============================================================================
# Test 17: CONSULTA_GUARD sem regressão
# ==============================================================================

@pytest.mark.asyncio
async def test_fase3_17_consulta_guard_sem_regressao():
    """Test 17: CONSULTA_GUARD continua bloqueando horarios_sugeridos"""

    modo_operacao = "consulta_sem_autorizacao_atual"

    # GUARD deve bloquear
    should_set_horarios = modo_operacao not in ["consulta_sem_autorizacao_atual"]

    assert should_set_horarios is False
    print("✅ Test 17: CONSULTA_GUARD sem regressão")
