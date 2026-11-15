"""
Testes de Integração: Persistência em Firestore

Testa:
1. Persistência e recuperação
2. Expiração validada na leitura
3. Isolamento entre actors
4. Isolamento entre tenants
5. Limpeza sem apagar outros campos
6. Falha de escrita
7. Falha de leitura
8. Validações de segurança (tenant/actor vazio)

Nota: Estes testes requerem Firestore funcional ou mock.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from schemas.resultado_consulta_schema import (
    ContextoResultadoConsulta,
    OpcaoHorario
)
from services.resultado_consulta_service import (
    persistir_resultado_consulta,
    recuperar_resultado_consulta,
    limpar_resultado_consulta
)


@pytest.fixture
def contexto_teste():
    """Criar contexto para teste"""
    opcoes = [
        OpcaoHorario(
            opcao_id="opt_1",
            numero=1,
            profissional_id="Bruna",
            data="2026-11-16",
            hora_inicio="14:00",
            hora_fim="15:20",
            servicos=["manicure", "pedicure"],
            duracao_total_min=80
        ),
        OpcaoHorario(
            opcao_id="opt_2",
            numero=2,
            profissional_id="Bruna",
            data="2026-11-16",
            hora_inicio="15:30",
            hora_fim="16:50",
            servicos=["manicure", "pedicure"],
            duracao_total_min=80
        ),
    ]

    return ContextoResultadoConsulta(
        servicos=["manicure", "pedicure"],
        data="2026-11-16",
        duracao_total_min=80,
        profissional_id="Bruna",
        opcoes=opcoes
    )


# ============================================================================
# Test 1: Persistência e Recuperação (com mock)
# ============================================================================

@pytest.mark.asyncio
async def test_persistir_recuperar_mock(contexto_teste):
    """Test 1: Persistir e recuperar com mock Firestore"""

    tenant_id = "tenant_test_1"
    actor_id = "actor_test_1"

    # Mock salvar_dado_em_path para retornar True
    with patch('services.resultado_consulta_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        resultado = await persistir_resultado_consulta(tenant_id, actor_id, contexto_teste)
        assert resultado is True

        # Verificar chamada
        mock_save.assert_called_once()
        call_args = mock_save.call_args
        path = call_args[0][0]  # Primeiro argumento posicional
        assert path == f"Clientes/{tenant_id}/Sessoes/{actor_id}"
        assert "contexto_resultado_consulta" in call_args[0][1]

    print("✅ Test 1: Persistência com mock OK")


@pytest.mark.asyncio
async def test_recuperar_valido_mock(contexto_teste):
    """Test 2: Recuperar contexto válido com mock"""

    tenant_id = "tenant_test_1"
    actor_id = "actor_test_1"

    # Mock buscar_dado_em_path para retornar documento com contexto
    with patch('services.resultado_consulta_service.buscar_dado_em_path', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "contexto_resultado_consulta": contexto_teste.to_dict()
        }

        resultado = await recuperar_resultado_consulta(tenant_id, actor_id)
        assert resultado is not None
        assert resultado.profissional_id == "Bruna"
        assert len(resultado.opcoes) == 2

    print("✅ Test 2: Recuperação válida com mock OK")


# ============================================================================
# Test 3: Expiração Validada na Leitura
# ============================================================================

@pytest.mark.asyncio
async def test_recuperar_expirado_mock():
    """Test 3: Não recuperar contexto expirado"""

    tenant_id = "tenant_test_1"
    actor_id = "actor_test_1"

    # Criar contexto expirado
    agora = datetime.utcnow()
    uma_hora_atras = (agora - timedelta(hours=1)).isoformat()

    contexto_expirado_dict = {
        "consulta_id": "query_1",
        "criado_em": (agora - timedelta(hours=2)).isoformat(),
        "expira_em": uma_hora_atras,
        "servicos": ["test"],
        "data": "2026-11-16",
        "duracao_total_min": 60,
        "profissional_id": "Test",
        "opcoes": [],
        "opcao_selecionada_id": None
    }

    with patch('services.resultado_consulta_service.buscar_dado_em_path', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "contexto_resultado_consulta": contexto_expirado_dict
        }

        resultado = await recuperar_resultado_consulta(tenant_id, actor_id)
        assert resultado is None  # Deve retornar None porque expirado

    print("✅ Test 3: Expiração na leitura OK (contexto expirado rejeitado)")


# ============================================================================
# Test 4: Isolamento entre Actors
# ============================================================================

@pytest.mark.asyncio
async def test_isolamento_actors():
    """Test 4: Actor A não vê resultado de Actor B"""

    tenant_id = "tenant_shared"
    actor_a = "actor_a"
    actor_b = "actor_b"

    contexto_a = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna",
    )

    with patch('services.resultado_consulta_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        # Actor A salva seu contexto
        await persistir_resultado_consulta(tenant_id, actor_a, contexto_a)

        # Verificar que path de A é diferente de B
        calls = mock_save.call_args_list
        path_a = calls[0][0][0]

        assert actor_a in path_a
        assert actor_b not in path_a
        assert f"Clientes/{tenant_id}/Sessoes/{actor_a}" == path_a

    print("✅ Test 4: Isolamento entre actors OK")


# ============================================================================
# Test 5: Isolamento entre Tenants
# ============================================================================

@pytest.mark.asyncio
async def test_isolamento_tenants():
    """Test 5: Tenant A não vê resultado de Tenant B"""

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    actor_id = "actor_shared"

    contexto = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna",
    )

    with patch('services.resultado_consulta_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        # Tenant A salva seu contexto
        await persistir_resultado_consulta(tenant_a, actor_id, contexto)

        calls = mock_save.call_args_list
        path_a = calls[0][0][0]

        assert tenant_a in path_a
        assert tenant_b not in path_a
        assert f"Clientes/{tenant_a}/Sessoes/{actor_id}" == path_a

    print("✅ Test 5: Isolamento entre tenants OK")


# ============================================================================
# Test 6: Limpeza sem Apagar Outros Campos
# ============================================================================

@pytest.mark.asyncio
async def test_limpeza_preserva_resto():
    """Test 6: DELETE_FIELD remove APENAS contexto_resultado_consulta"""

    tenant_id = "tenant_test"
    actor_id = "actor_test"

    with patch('services.firebase_service_async.get_async_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_doc_ref = AsyncMock()
        mock_client.document.return_value = mock_doc_ref

        resultado = await limpar_resultado_consulta(tenant_id, actor_id)
        assert resultado is True

        # Verificar que update foi chamado com DELETE_FIELD
        mock_doc_ref.update.assert_called_once()
        update_data = mock_doc_ref.update.call_args[0][0]
        assert "contexto_resultado_consulta" in update_data

        # Verificar que nenhum outro campo foi passado
        assert len(update_data) == 1

    print("✅ Test 6: Limpeza preserva outros campos OK (DELETE_FIELD)")


# ============================================================================
# Test 7: Falha de Escrita
# ============================================================================

@pytest.mark.asyncio
async def test_falha_escrita():
    """Test 7: Falha de persistência é reportada"""

    tenant_id = "tenant_test"
    actor_id = "actor_test"
    contexto = ContextoResultadoConsulta(
        servicos=["test"],
        data="2026-11-16",
        duracao_total_min=60,
        profissional_id="Test",
    )

    with patch('services.resultado_consulta_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = False  # Falha

        resultado = await persistir_resultado_consulta(tenant_id, actor_id, contexto)
        assert resultado is False

    print("✅ Test 7: Falha de escrita detectada OK")


# ============================================================================
# Test 8: Falha de Leitura
# ============================================================================

@pytest.mark.asyncio
async def test_falha_leitura():
    """Test 8: Falha de leitura retorna None"""

    tenant_id = "tenant_test"
    actor_id = "actor_test"

    with patch('services.resultado_consulta_service.buscar_dado_em_path', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Firestore error")

        resultado = await recuperar_resultado_consulta(tenant_id, actor_id)
        assert resultado is None

    print("✅ Test 8: Falha de leitura tratada OK (retorna None)")


# ============================================================================
# Test 9: Validação Tenant Vazio
# ============================================================================

@pytest.mark.asyncio
async def test_rejeitar_tenant_vazio():
    """Test 9: Rejeitar tenant_id vazio na persistência"""

    contexto = ContextoResultadoConsulta(
        servicos=["test"],
        data="2026-11-16",
        duracao_total_min=60,
        profissional_id="Test",
    )

    resultado = await persistir_resultado_consulta("", "actor_test", contexto)
    assert resultado is False

    resultado = await persistir_resultado_consulta(None, "actor_test", contexto)
    assert resultado is False

    print("✅ Test 9: Rejeição de tenant vazio OK")


# ============================================================================
# Test 10: Validação Actor Vazio
# ============================================================================

@pytest.mark.asyncio
async def test_rejeitar_actor_vazio():
    """Test 10: Rejeitar actor_id vazio na persistência"""

    contexto = ContextoResultadoConsulta(
        servicos=["test"],
        data="2026-11-16",
        duracao_total_min=60,
        profissional_id="Test",
    )

    resultado = await persistir_resultado_consulta("tenant_test", "", contexto)
    assert resultado is False

    resultado = await persistir_resultado_consulta("tenant_test", None, contexto)
    assert resultado is False

    print("✅ Test 10: Rejeição de actor vazio OK")


# ============================================================================
# Test 11: Documento Não Encontrado
# ============================================================================

@pytest.mark.asyncio
async def test_documento_nao_encontrado():
    """Test 11: Recuperar de documento que não existe"""

    tenant_id = "tenant_test"
    actor_id = "actor_nao_existe"

    with patch('services.resultado_consulta_service.buscar_dado_em_path', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None  # Documento não existe

        resultado = await recuperar_resultado_consulta(tenant_id, actor_id)
        assert resultado is None

    print("✅ Test 11: Documento não encontrado OK")


# ============================================================================
# Test 12: Substituição por Nova Consulta
# ============================================================================

@pytest.mark.asyncio
async def test_substituicao_consulta():
    """Test 12: Nova consulta substitui anterior"""

    tenant_id = "tenant_test"
    actor_id = "actor_test"

    contexto1 = ContextoResultadoConsulta(
        servicos=["manicure"],
        data="2026-11-16",
        duracao_total_min=30,
        profissional_id="Bruna",
        opcoes=[]
    )

    contexto2 = ContextoResultadoConsulta(
        servicos=["pedicure"],
        data="2026-11-17",
        duracao_total_min=30,
        profissional_id="Gloria",
        opcoes=[]
    )

    with patch('services.resultado_consulta_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        # Salvar primeira consulta
        await persistir_resultado_consulta(tenant_id, actor_id, contexto1)

        # Salvar segunda consulta (deve substituir)
        await persistir_resultado_consulta(tenant_id, actor_id, contexto2)

        # Ambas chamadas ao mesmo path
        calls = mock_save.call_args_list
        assert len(calls) == 2

        path1 = calls[0][0][0]
        path2 = calls[1][0][0]

        assert path1 == path2
        assert path1 == f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    print("✅ Test 12: Substituição por nova consulta OK")

