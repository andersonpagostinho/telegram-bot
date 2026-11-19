"""PHASE 6 — Sincronização automática de catálogo no onboarding

Testes de validação da implementação de sincronização.
"""
import pytest


@pytest.mark.asyncio
async def test_phase6_funcoes_importaveis():
    """Verificar que funções necessárias existem"""
    from services.cadastro_inicial_service import (
        processar_texto_cadastro,
        salvar_servico_negocio,
        listar_servicos_negocio,
        salvar_profissional
    )

    # Todas as funções devem ser callable
    assert callable(processar_texto_cadastro)
    assert callable(salvar_servico_negocio)
    assert callable(listar_servicos_negocio)
    assert callable(salvar_profissional)

    print("✅ Todas as funções necessárias estão disponíveis")


@pytest.mark.asyncio
async def test_phase6_salvar_servico_estrutura():
    """Verificar que salvar_servico_negocio retorna estrutura correta"""
    from services.cadastro_inicial_service import salvar_servico_negocio
    from unittest.mock import patch, AsyncMock

    with patch('services.firebase_service_async.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        # Chamar salvar_servico_negocio
        resultado = await salvar_servico_negocio(
            user_id="test_tenant",
            nome="TestService",
            preco=50.0,
            duracao=40
        )

        # Verificar estrutura do resultado
        assert isinstance(resultado, dict)
        assert 'nome' in resultado
        assert 'preco' in resultado
        assert 'duracao' in resultado
        assert resultado['preco'] == 50.0
        assert resultado['duracao'] == 40

        print("✅ salvar_servico_negocio retorna estrutura correta")


@pytest.mark.asyncio
async def test_phase6_salvar_profissional_preserva_precos():
    """Verificar que profissional preserva preços do catálogo"""
    from services.cadastro_inicial_service import salvar_profissional
    from unittest.mock import patch, AsyncMock

    with patch('services.firebase_service_async.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
        mock_save.return_value = True

        # Dados do profissional
        servicos = {
            'manicure': {'preco': 40.0, 'duracao': 30},
            'pedicure': {'preco': 45.0, 'duracao': 35}
        }

        resultado = await salvar_profissional(
            user_id="test_tenant",
            nome="TestProf",
            servicos=servicos
        )

        # Verificar que preços foram preservados
        detalhe = resultado.get('servicos_detalhe', {})
        assert 'manicure' in detalhe
        assert 'pedicure' in detalhe
        assert detalhe['manicure']['preco'] == 40.0
        assert detalhe['pedicure']['preco'] == 45.0

        print("✅ salvar_profissional preserva preços")


@pytest.mark.asyncio
async def test_phase6_listar_servicos_retorna_dict():
    """Verificar que listar_servicos_negocio retorna estrutura correta"""
    from services.cadastro_inicial_service import listar_servicos_negocio
    from unittest.mock import patch, AsyncMock

    with patch('services.firebase_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = {
            'manicure': {'nome': 'Manicure', 'preco': 40.0, 'duracao': 30},
            'pedicure': {'nome': 'Pedicure', 'preco': 40.0, 'duracao': 30}
        }

        resultado = await listar_servicos_negocio("test_tenant")

        # Verificar estrutura
        assert isinstance(resultado, dict)
        assert 'manicure' in resultado
        assert 'pedicure' in resultado

        print("✅ listar_servicos_negocio retorna estrutura correta")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
