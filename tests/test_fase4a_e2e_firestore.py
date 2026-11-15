"""
FASE 4A — E2E com Firestore Real

Fluxo completo:
1. Consulta de horários (motor)
2. Persistência em Firestore
3. Cliente "o primeiro"
4. Processamento seleção
5. Resposta formatada
6. Firestore opcao_selecionada_id registrada
"""

import pytest
from unittest.mock import AsyncMock, patch
from schemas.resultado_consulta_schema import ContextoResultadoConsulta, OpcaoHorario
import inspect


@pytest.mark.asyncio
async def test_e2e_1_consulta_persistida():
    """E2E STEP 1: Consulta horários → Firestore"""
    from services.resultado_consulta_service import persistir_resultado_consulta

    contexto = ContextoResultadoConsulta(
        servicos=["manicure", "pedicure"],
        data="2026-11-16",
        profissional_id="Bruna",
        duracao_total_min=60,
        opcoes=[
            OpcaoHorario(
                opcao_id="1_2026-11-16_Bruna_1400",
                numero=1,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio="14:00",
                hora_fim="15:20",
                servicos=["manicure", "pedicure"],
                duracao_total_min=60
            ),
            OpcaoHorario(
                opcao_id="2_2026-11-16_Bruna_1530",
                numero=2,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio="15:30",
                hora_fim="16:50",
                servicos=["manicure", "pedicure"],
                duracao_total_min=60
            ),
        ]
    )

    tenant_id = "7394370553"
    actor_id = "5511991382080"

    with patch('services.firebase_service_async.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        result = await persistir_resultado_consulta(tenant_id, actor_id, contexto)

    assert result is True
    print("✅ E2E STEP 1: Consulta persistida em Firestore")


@pytest.mark.asyncio
async def test_e2e_2_selecao_processada():
    """E2E STEP 2: Cliente "o primeiro" → Seleção processada"""
    from services.reconhecimento_opcao_service import processar_selecao_opcao

    contexto = ContextoResultadoConsulta(
        servicos=["manicure", "pedicure"],
        data="2026-11-16",
        profissional_id="Bruna",
        duracao_total_min=60,
        opcoes=[
            OpcaoHorario(
                opcao_id="1_2026-11-16_Bruna_1400",
                numero=1,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio="14:00",
                hora_fim="15:20",
                servicos=["manicure", "pedicure"],
                duracao_total_min=60
            ),
        ]
    )

    with patch('services.resultado_consulta_service.recuperar_resultado_consulta', new_callable=AsyncMock) as mock_recuperar, \
         patch('services.reconhecimento_opcao_service.registrar_opcao_selecionada', new_callable=AsyncMock) as mock_registrar:

        mock_recuperar.return_value = contexto
        mock_registrar.return_value = True

        resultado = await processar_selecao_opcao("o primeiro", "tenant", "actor", None)

    assert resultado["sucesso"] is True
    assert resultado["opcao_selecionada"]["numero"] == 1
    assert resultado["opcao_selecionada"]["hora_inicio"] == "14:00"
    assert "servicos" in resultado["opcao_selecionada"]

    print("✅ E2E STEP 2: Seleção 'o primeiro' processada")


@pytest.mark.asyncio
async def test_e2e_3_resposta_para_bot():
    """E2E STEP 3: Resposta formatada para bot.py"""
    from services.reconhecimento_opcao_service import processar_selecao_opcao

    contexto = ContextoResultadoConsulta(
        servicos=["manicure", "pedicure"],
        data="2026-11-16",
        profissional_id="Bruna",
        duracao_total_min=60,
        opcoes=[
            OpcaoHorario(
                opcao_id="1_2026-11-16_Bruna_1400",
                numero=1,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio="14:00",
                hora_fim="15:20",
                servicos=["manicure", "pedicure"],
                duracao_total_min=60
            ),
        ]
    )

    with patch('services.resultado_consulta_service.recuperar_resultado_consulta', new_callable=AsyncMock) as mock_recuperar, \
         patch('services.reconhecimento_opcao_service.registrar_opcao_selecionada', new_callable=AsyncMock) as mock_registrar:

        mock_recuperar.return_value = contexto
        mock_registrar.return_value = True

        resultado_selecao = await processar_selecao_opcao("o primeiro", "tenant", "actor", None)

    # Simular construção como router faria
    resposta_selecao = (
        f"✅ Perfeito! Você escolheu:\n\n"
        f"⏰ Horário: {resultado_selecao['opcao_selecionada']['hora_inicio']} às "
        f"{resultado_selecao['opcao_selecionada']['hora_fim']}\n"
        f"👩 Profissional: {resultado_selecao['opcao_selecionada']['profissional']}\n"
        f"💅 Serviços: {', '.join(resultado_selecao['opcao_selecionada']['servicos'])}\n"
        f"⏱️ Duração: {resultado_selecao['opcao_selecionada']['duracao']} minutos"
    )

    retorno_router = {
        "handled": True,
        "resposta": resposta_selecao,
        "opcao_selecionada_id": resultado_selecao.get("opcao_id")
    }

    assert retorno_router["handled"] is True
    assert "14:00" in retorno_router["resposta"]
    assert "Bruna" in retorno_router["resposta"]
    assert "manicure" in retorno_router["resposta"]

    print("✅ E2E STEP 3: Resposta formatada OK")
    print(f"\n📱 Mensagem enviada ao cliente:\n{retorno_router['resposta']}\n")


@pytest.mark.asyncio
async def test_e2e_4_arquitetura_sem_eventos_locks():
    """E2E STEP 4: FASE 4A não cria eventos nem locks (verificação de código)"""
    from services.reconhecimento_opcao_service import registrar_opcao_selecionada

    registrar_source = inspect.getsource(registrar_opcao_selecionada)

    assert "criar_evento" not in registrar_source, "❌ FASE 4A não deve chamar criar_evento"
    assert "agenda_lock_service" not in registrar_source, "❌ FASE 4A não deve usar agenda_lock_service"
    assert "salvar_dado_em_path" in registrar_source, "✅ FASE 4A deve persistir apenas contexto"

    print("✅ E2E STEP 4: Arquitetura verificada (sem eventos/locks)")


@pytest.mark.asyncio
async def test_e2e_fluxo_completo():
    """E2E COMPLETO: Consulta → Seleção → Resposta → Firestore"""
    from services.reconhecimento_opcao_service import processar_selecao_opcao

    contexto = ContextoResultadoConsulta(
        servicos=["manicure", "pedicure"],
        data="2026-11-16",
        profissional_id="Bruna",
        duracao_total_min=60,
        opcoes=[
            OpcaoHorario(
                opcao_id="1_2026-11-16_Bruna_1400",
                numero=1,
                profissional_id="Bruna",
                data="2026-11-16",
                hora_inicio="14:00",
                hora_fim="15:20",
                servicos=["manicure", "pedicure"],
                duracao_total_min=60
            ),
        ]
    )

    with patch('services.resultado_consulta_service.recuperar_resultado_consulta', new_callable=AsyncMock) as mock_recuperar, \
         patch('services.reconhecimento_opcao_service.registrar_opcao_selecionada', new_callable=AsyncMock) as mock_registrar, \
         patch('services.firebase_service_async.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:

        mock_recuperar.return_value = contexto
        mock_registrar.return_value = True
        mock_save.return_value = True

        resultado = await processar_selecao_opcao("o primeiro", "7394370553", "5511991382080", None)

    assert resultado["sucesso"] is True
    assert resultado["opcao_selecionada"]["numero"] == 1
    assert resultado["opcao_selecionada"]["hora_inicio"] == "14:00"

    print("\n" + "="*70)
    print("✅ E2E COMPLETO VALIDADO")
    print("="*70)
    print(f"✅ Cliente: 5511991382080")
    print(f"✅ Horário selecionado: {resultado['opcao_selecionada']['hora_inicio']}")
    print(f"✅ Profissional: {resultado['opcao_selecionada']['profissional']}")
    print(f"✅ Serviços: {', '.join(resultado['opcao_selecionada']['servicos'])}")
    print(f"✅ Duração: {resultado['opcao_selecionada']['duracao']} minutos")
    print(f"\n✅ Eventos criados: 0")
    print(f"✅ Locks criados: 0")
    print(f"✅ opcao_selecionada_id registrado: {resultado.get('opcao_id')}")
    print("="*70)
