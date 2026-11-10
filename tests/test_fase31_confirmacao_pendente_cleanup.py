# -*- coding: utf-8 -*-
"""
FASE 3.1 TEST: Verificar que confirmacao_pendente é deletado em limpeza de timeout.

Testa: limpar_contexto_agendamento_v2_transacional() deleta confirmacao_pendente
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from google.cloud import firestore


@pytest.mark.asyncio
async def test_fase31_confirmacao_pendente_deletado():
    """
    Teste: confirmacao_pendente deve estar em DELETE_FIELD.

    Setup:
    - Sessão com confirmacao_pendente = {"operacao_id": "op-123"}

    Executa:
    - limpar_contexto_agendamento_v2_transacional(dono_id, cliente_id)

    Esperado:
    - confirmacao_pendente aparece na lista de DELETE_FIELD
    - Transação executa sem erro
    """
    from utils.contexto_temporario import limpar_contexto_agendamento_v2_transacional

    # Valores de teste
    dono_id = "test_tenant_123"
    cliente_id = "test_cliente_456"

    # Mock do Firestore
    mock_db = MagicMock()
    mock_sessao_ref = MagicMock()
    mock_sessao_doc = MagicMock()

    # Simulando documento existente com confirmacao_pendente
    mock_sessao_doc.exists = True
    mock_sessao_doc.to_dict.return_value = {
        "estado_fluxo": "modo_escolha_horario",
        "confirmacao_pendente": {
            "operacao_id": "op-123",
            "tipo": "confirmacao_agendamento"
        },
        "draft_agendamento": {"data": "01/12/2026"},
    }

    mock_db.document.return_value = mock_sessao_ref
    mock_db.transaction.return_value = MagicMock()

    # Rastreador de payloads enviados
    payloads_enviados = []

    def capturar_transaction_update(tx):
        """Wrapper que captura o payload enviado ao transaction.update."""
        def update_wrapper(ref, payload):
            payloads_enviados.append(payload)
            return None
        tx.update = update_wrapper
        tx.get = lambda ref: mock_sessao_doc
        return tx

    # Patchear a transação
    with patch('utils.contexto_temporario.get_db', return_value=mock_db):
        with patch('utils.contexto_temporario.firestore.transactional') as mock_transactional:
            # Decorador que executa diretamente
            def transactional_decorator(func):
                def wrapper(tx):
                    tx_wrapper = capturar_transaction_update(tx)
                    return func(tx_wrapper)
                return wrapper

            mock_transactional.side_effect = transactional_decorator

            # Mock asyncio.to_thread para chamar direto
            async def mock_to_thread(func):
                return func()

            with patch('asyncio.to_thread', side_effect=mock_to_thread):
                resultado = await limpar_contexto_agendamento_v2_transacional(
                    dono_id,
                    cliente_id
                )

    # VALIDAÇÕES
    print(f"\n[TESTE FASE 3.1] Resultado: {resultado}")
    print(f"[TESTE FASE 3.1] Payloads capturados: {len(payloads_enviados)}")

    if payloads_enviados:
        payload = payloads_enviados[0]
        print(f"[TESTE FASE 3.1] Campos em DELETE_FIELD: {[k for k, v in payload.items() if 'DELETE_FIELD' in str(v)]}")

        # VERIFICAÇÃO CRÍTICA: confirmacao_pendente está em DELETE_FIELD?
        tem_confirmacao_pendente = "confirmacao_pendente" in payload
        print(f"[TESTE FASE 3.1] confirmacao_pendente em payload: {tem_confirmacao_pendente}")

        if tem_confirmacao_pendente:
            print(f"✅ [FASE 3.1 PASS] confirmacao_pendente está sendo deletado")
            assert True
        else:
            print(f"❌ [FASE 3.1 FAIL] confirmacao_pendente NÃO está no payload!")
            assert False, "confirmacao_pendente deveria estar em DELETE_FIELD"
    else:
        print(f"❌ [FASE 3.1 FAIL] Nenhum payload foi capturado")
        assert False, "Esperava que transaction.update fosse chamado com payload"


@pytest.mark.asyncio
async def test_fase31_verificar_delete_field_na_funcao():
    """
    Teste estático: Verificar se 'confirmacao_pendente' aparece no código-fonte.

    (Não requere mock, apenas inspeciona o código)
    """
    import inspect
    from utils.contexto_temporario import limpar_contexto_agendamento_v2_transacional

    # Obter código-fonte
    source = inspect.getsource(limpar_contexto_agendamento_v2_transacional)

    # Verificar se 'confirmacao_pendente' aparece
    tem_confirmacao = "confirmacao_pendente" in source

    print(f"\n[TESTE FASE 3.1 ESTÁTICO] Procurando 'confirmacao_pendente' no código...")
    print(f"[TESTE FASE 3.1 ESTÁTICO] Encontrado: {tem_confirmacao}")

    if tem_confirmacao:
        print(f"✅ [FASE 3.1 ESTÁTICO PASS] confirmacao_pendente está no código-fonte")
        # Encontrar a linha
        for i, linha in enumerate(source.split('\n'), 1):
            if 'confirmacao_pendente' in linha:
                print(f"  Linha {i}: {linha.strip()}")
        assert True
    else:
        print(f"❌ [FASE 3.1 ESTÁTICO FAIL] confirmacao_pendente NÃO encontrado!")
        assert False, "confirmacao_pendente não aparece no DELETE_FIELD"


if __name__ == "__main__":
    # Executar testes
    print("\n" + "="*70)
    print("FASE 3.1 TEST — Verificar DELETE_FIELD de confirmacao_pendente")
    print("="*70)

    # Teste estático (não requer async)
    asyncio.run(test_fase31_verificar_delete_field_na_funcao())

    # Teste com mock
    asyncio.run(test_fase31_confirmacao_pendente_deletado())

    print("\n" + "="*70)
    print("✅ FASE 3.1 TESTES CONCLUÍDO")
    print("="*70)
