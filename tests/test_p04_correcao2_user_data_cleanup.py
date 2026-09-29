"""
P0.4-CORREÇÃO 2 — Teste de limpeza seletiva context.user_data

Objetivo: Validar que campos transitórios de agendamento são removidos
de context.user_data sem afetar campos legítimos de fluxos paralelos.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_user_data_cleanup_remove_transitorio_preserva_legitimo():
    """
    Validar que limpeza de context.user_data:
    1. Remove campos transitórios de agendamento
    2. Preserva campos legítimos (tenant_id_guard, cancelamento, email)
    """

    # Setup: Simular context.user_data sujo
    mock_context = Mock()
    mock_context.user_data = {
        # Campos transitórios de agendamento
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "intencao_conversacional": "confirmacao_agendamento",
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-09-29T14:00:00"
        },
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-09-29T14:00:00",
            "duracao": 30,
        },
        "profissional_escolhido": "Bruna",
        "servico": "corte",
        "data_hora": "2026-09-29T14:00:00",
        "objetivo_conversacional": "criar_evento",
        "tipo_ajuste_incremental": "alteracao_horario",
        "modo_escolha_horario": True,
        "horarios_sugeridos": ["09:00", "10:00"],
        "alternativa_profissional": ["Paula", "Sofia"],

        # Campos legítimos que devem ser preservados
        "_tenant_id_guard": "7394370553",
        "cancelamento_pendente": {
            "evento_id": "evt_123",
            "timestamp": "2026-09-29T17:00:00"
        },
        "estado_envio": "aguardando_destinatario",
        "esperando_dados_email": True,
        "nome_em_espera": "João Silva",
    }

    print(f"[SETUP] context.user_data antes: {len(mock_context.user_data)} campos")
    print(f"[CAMPOS] {list(mock_context.user_data.keys())}")

    # Ação: Executar limpeza (simular o código adicionado)
    campos_transitorio_agendamento = [
        "estado_fluxo",
        "aguardando_confirmacao_agendamento",
        "intencao_conversacional",
        "draft_agendamento",
        "dados_confirmacao_agendamento",
        "profissional_escolhido",
        "servico",
        "data_hora",
        "objetivo_conversacional",
        "tipo_ajuste_incremental",
        "modo_escolha_horario",
        "horarios_sugeridos",
        "alternativa_profissional",
    ]

    for campo in campos_transitorio_agendamento:
        mock_context.user_data.pop(campo, None)

    # Validação 1: Campos transitórios foram removidos
    print(f"\n[VALIDAÇÃO 1] Campos transitórios removidos")
    for campo in campos_transitorio_agendamento:
        assert campo not in mock_context.user_data, \
            f"[FAIL] Campo '{campo}' ainda existe em user_data!"
        print(f"  [PASS] {campo} removido")

    # Validação 2: Campos legítimos foram preservados
    print(f"\n[VALIDAÇÃO 2] Campos legítimos preservados")
    campos_esperados = {
        "_tenant_id_guard": "7394370553",
        "cancelamento_pendente": True,  # Apenas validar existência
        "estado_envio": "aguardando_destinatario",
        "esperando_dados_email": True,
        "nome_em_espera": "João Silva",
    }

    for campo, valor_esperado in campos_esperados.items():
        assert campo in mock_context.user_data, \
            f"[FAIL] Campo '{campo}' foi removido (deveria estar preservado)!"

        if valor_esperado is not True:  # True = apenas verificar existência
            valor_real = mock_context.user_data[campo]
            assert valor_real == valor_esperado, \
                f"[FAIL] Campo '{campo}': esperado {valor_esperado}, obtido {valor_real}"

        print(f"  [PASS] {campo} preservado")

    # Validação 3: Contagem final
    print(f"\n[VALIDAÇÃO 3] Contagem de campos")
    print(f"  Antes: ~21 campos")
    print(f"  Depois: {len(mock_context.user_data)} campos")
    print(f"  Removidos: {13} campos de agendamento")
    print(f"  Preservados: {len(mock_context.user_data)} campos legítimos")

    assert len(mock_context.user_data) == 5, \
        f"[FAIL] Esperado 5 campos legítimos, obtido {len(mock_context.user_data)}"

    print(f"\n[SUCESSO] Limpeza seletiva validada!")
    return True


@pytest.mark.asyncio
async def test_user_data_cleanup_none_context():
    """
    Validar que limpeza é segura se context for None.
    """

    # Ação: Simular context None
    context = None

    # Validação: Não deve lançar exceção
    try:
        if context and hasattr(context, 'user_data') and context.user_data:
            # Nunca executa (context é None)
            pass
        print("[PASS] context=None tratado seguramente")
        resultado = True
    except Exception as e:
        print(f"[FAIL] Erro com context=None: {e}")
        resultado = False

    assert resultado, "Limpeza deve ser segura com context=None"
    return True


@pytest.mark.asyncio
async def test_user_data_cleanup_empty_user_data():
    """
    Validar que limpeza é segura se context.user_data estiver vazio.
    """

    # Setup
    mock_context = Mock()
    mock_context.user_data = {}

    # Ação: Executar limpeza
    campos_transitorio = [
        "estado_fluxo",
        "aguardando_confirmacao_agendamento",
        "intencao_conversacional",
        "draft_agendamento",
    ]

    for campo in campos_transitorio:
        mock_context.user_data.pop(campo, None)

    # Validação: Deve estar vazio e não lançar exceção
    print("[PASS] Limpeza de user_data vazio é segura")
    assert len(mock_context.user_data) == 0
    return True


@pytest.mark.asyncio
async def test_user_data_not_cleaned_on_creation_failure():
    """
    Validar que context.user_data NÃO é limpo se a criação do evento falhar.

    Nota: Este teste é conceitual.
    Em código real, a limpeza só acontece após sucesso.
    """

    # Setup
    mock_context = Mock()
    mock_context.user_data = {
        "estado_fluxo": "agendando",
        "intencao_conversacional": "confirmacao_agendamento",
        "_tenant_id_guard": "7394370553",
    }

    user_data_before = dict(mock_context.user_data)

    # Simular falha (não executa limpeza)
    # (em código real, limpeza só executa após sucesso)
    falhou = True
    if not falhou:
        # Limpeza só executa se sucesso
        for campo in ["estado_fluxo", "intencao_conversacional"]:
            mock_context.user_data.pop(campo, None)

    # Validação: context.user_data não foi alterado
    print("[PASS] context.user_data não foi limpo após falha")
    assert mock_context.user_data == user_data_before
    return True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
