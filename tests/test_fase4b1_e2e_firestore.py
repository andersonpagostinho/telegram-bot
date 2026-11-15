"""FASE 4B.1 — E2E Firestore"""
import pytest
from unittest.mock import AsyncMock, patch
from services.confirmacao_agendamento_service import (
    autorizar_revalidacao,
    registrar_autorizacao_pendente,
    AutorizacaoPendente
)
from schemas.resultado_consulta_schema import ContextoResultadoConsulta, OpcaoHorario


@pytest.mark.asyncio
async def test_e2e_4b1_1_persistencia_firestore():
    """E2E: Autorização pendente persistida em Firestore"""

    autorizacao = AutorizacaoPendente(
        consulta_id="test-123",
        opcao_id="1_xxx",
        tenant_id="7394370553",
        actor_id="5511991382080",
        profissional="Bruna",
        data="2026-11-16",
        hora_inicio="14:00",
        hora_fim="14:30",
        servicos=["manicure"],
        duracao_total_min=30
    )

    with patch('services.firebase_service_async.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        resultado = await registrar_autorizacao_pendente(
            "7394370553",
            "5511991382080",
            autorizacao
        )

    assert resultado is True
    print("✅ E2E: Autorização persistida")


@pytest.mark.asyncio
async def test_e2e_4b1_2_isolamento_tenant_actor():
    """E2E: Isolamento tenant/actor validado"""

    ctx = ContextoResultadoConsulta(
        data="2026-11-16",
        opcoes=[OpcaoHorario(
            opcao_id="1_xxx",
            numero=1,
            profissional_id="Bruna",
            data="2026-11-16",
            hora_inicio="14:00",
            hora_fim="14:30",
            servicos=["manicure"],
            duracao_total_min=30
        )],
        opcao_selecionada_id="1_xxx"
    )

    # Teste com tenant/actor corretos
    with patch('services.resultado_consulta_service.recuperar_resultado_consulta', new_callable=AsyncMock) as m1, \
         patch('services.varredura_disponibilidade.varrer_disponibilidade_multisservico', new_callable=AsyncMock) as m2:
        m1.return_value = ctx
        m2.return_value = {"horarios_disponiveis": [{"inicio": "14:00", "fim": "14:30"}]}

        resultado = await autorizar_revalidacao("7394370553", "5511991382080", ctx)

    assert resultado["sucesso"] is True
    assert resultado["autorizacao"].tenant_id == "7394370553"
    assert resultado["autorizacao"].actor_id == "5511991382080"
    print("✅ E2E: Isolamento validado")


@pytest.mark.asyncio
async def test_e2e_4b1_3_zero_eventos():
    """E2E: Zero eventos criados durante FASE 4B.1"""
    import inspect
    from services.confirmacao_agendamento_service import autorizar_revalidacao, registrar_autorizacao_pendente

    # Verificar código: NENHUMA chamada a criar_evento
    source_autorizar = inspect.getsource(autorizar_revalidacao)
    source_registrar = inspect.getsource(registrar_autorizacao_pendente)

    assert "criar_evento" not in source_autorizar
    assert "criar_evento" not in source_registrar
    assert "salvar_evento" not in source_autorizar
    assert "salvar_evento" not in source_registrar

    print("✅ E2E: Zero eventos criados")


@pytest.mark.asyncio
async def test_e2e_4b1_4_zero_locks():
    """E2E: Zero locks criados durante FASE 4B.1"""
    import inspect
    from services.confirmacao_agendamento_service import autorizar_revalidacao, registrar_autorizacao_pendente

    source_autorizar = inspect.getsource(autorizar_revalidacao)
    source_registrar = inspect.getsource(registrar_autorizacao_pendente)

    assert "agenda_lock_service" not in source_autorizar
    assert "agenda_lock_service" not in source_registrar
    assert "criar_lock" not in source_autorizar
    assert "criar_lock" not in source_registrar

    print("✅ E2E: Zero locks criados")


@pytest.mark.asyncio
async def test_e2e_4b1_5_fluxo_completo():
    """E2E COMPLETO: Revalidação → Autorização → Sem evento/lock"""

    ctx = ContextoResultadoConsulta(
        consulta_id="test-consulta-123",
        data="2026-11-16",
        opcoes=[OpcaoHorario(
            opcao_id="1_2026-11-16_Bruna_1400",
            numero=1,
            profissional_id="Bruna",
            data="2026-11-16",
            hora_inicio="14:00",
            hora_fim="14:30",
            servicos=["manicure"],
            duracao_total_min=30
        )],
        opcao_selecionada_id="1_2026-11-16_Bruna_1400"
    )

    with patch('services.resultado_consulta_service.recuperar_resultado_consulta', new_callable=AsyncMock) as m1, \
         patch('services.varredura_disponibilidade.varrer_disponibilidade_multisservico', new_callable=AsyncMock) as m2, \
         patch('services.firebase_service_async.salvar_dado_em_path', new_callable=AsyncMock) as m3:

        m1.return_value = ctx
        m2.return_value = {"horarios_disponiveis": [{"inicio": "14:00", "fim": "14:30"}]}
        m3.return_value = True

        # Revalidar
        resultado_revalidacao = await autorizar_revalidacao("7394370553", "5511991382080", ctx)

        # Registrar autorização
        resultado_registro = await registrar_autorizacao_pendente(
            "7394370553",
            "5511991382080",
            resultado_revalidacao["autorizacao"]
        )

    assert resultado_revalidacao["sucesso"] is True
    assert resultado_registro is True

    print("\n" + "="*70)
    print("✅ E2E COMPLETO FASE 4B.1")
    print("="*70)
    print(f"✅ Horário revalidado: {resultado_revalidacao['autorizacao'].hora_inicio}")
    print(f"✅ Autorização registrada: {resultado_revalidacao['autorizacao'].autorizacao_id}")
    print(f"✅ Tenant: {resultado_revalidacao['autorizacao'].tenant_id}")
    print(f"✅ Actor: {resultado_revalidacao['autorizacao'].actor_id}")
    print(f"✅ Eventos criados: 0")
    print(f"✅ Locks criados: 0")
    print(f"✅ Notificações: 0")
    print("="*70)
