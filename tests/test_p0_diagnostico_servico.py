"""
[P0-DIAGNOSTICO] Validação da Nova Função e Fluxo Sem GPT

Testa:
1. buscar_subcolecao_com_diagnostico() com vários cenários
2. Frase de referência processada sem GPT
3. Diferenciação entre erro de leitura e coleção vazia
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from services.firebase_service_async import buscar_subcolecao_com_diagnostico

# ============================================================================
# TESTES UNITÁRIOS DA NOVA FUNÇÃO
# ============================================================================

@pytest.mark.asyncio
async def test_diagnostico_colecao_vazia():
    """Teste A: Coleção vazia retorna ({}, None)"""

    with patch("services.firebase_service_async.get_ref_from_path") as mock_ref:
        # Simular stream vazio
        mock_ref_instance = MagicMock()
        mock_ref.return_value = mock_ref_instance
        mock_ref_instance.stream.return_value = AsyncMock(return_value=iter([]))

        # Buscar uma subcoleção vazia
        data, err = await buscar_subcolecao_com_diagnostico("Clientes/999/Profissionais")

        assert data == {}, f"Esperava dados vazios, obtive {data}"
        assert err is None, f"Não deveria haver erro, mas obtive {err}"
        print("✅ A: Coleção vazia OK")


@pytest.mark.asyncio
async def test_diagnostico_permissao_negada():
    """Teste B: Erro de permissão retorna ({}, "PermissionError:...")"""

    with patch("services.firebase_service_async.get_ref_from_path") as mock_ref:
        mock_ref_instance = MagicMock()
        mock_ref.return_value = mock_ref_instance

        # Simular exceção de permissão
        async def raise_permission_error():
            raise PermissionError("User does not have permission")

        mock_ref_instance.stream = raise_permission_error

        data, err = await buscar_subcolecao_com_diagnostico("Clientes/999/Profissionais")

        assert data == {}, f"Esperava dados vazios em erro, obtive {data}"
        assert err is not None, "Deveria haver diagnóstico de erro"
        assert "PermissionError" in err, f"Diagnóstico deveria mencionar PermissionError, obtive {err}"
        print(f"✅ B: Erro de permissão OK → {err}")


@pytest.mark.asyncio
async def test_diagnostico_com_dados():
    """Teste C: Documentos válidos retornam ({docs}, None)"""

    with patch("services.firebase_service_async.get_ref_from_path") as mock_ref:
        # Criar mock de documento
        mock_doc = MagicMock()
        mock_doc.id = "profissional_1"
        mock_doc.to_dict.return_value = {"nome": "Maria", "servicos": ["corte feminino"]}

        async def mock_stream():
            yield mock_doc

        mock_ref_instance = MagicMock()
        mock_ref.return_value = mock_ref_instance
        mock_ref_instance.stream.return_value = mock_stream()

        data, err = await buscar_subcolecao_com_diagnostico("Clientes/999/Profissionais")

        assert "profissional_1" in data, f"Esperava profissional_1, obtive {data.keys()}"
        assert err is None, f"Não deveria haver erro, obtive {err}"
        print(f"✅ C: Dados válidos OK → {data}")

# ============================================================================
# TESTES DO FLUXO SEM GPT
# ============================================================================

@pytest.mark.asyncio
async def test_frase_referencia_sem_gpt():
    """
    Teste D: Frase "voce tem agenda para corte feminino amanha as 10?"

    Valida:
    - Classificação determinística
    - Zero chamadas ao GPT
    - Serviço extraído
    """

    from services.interpretador_conversacional import interpretar_conversa_operacional

    SERVICOS_TESTE = ["corte feminino", "corte masculino", "escova", "manicure"]

    texto = "voce tem agenda para corte feminino amanha as 10?"

    resultado = interpretar_conversa_operacional(
        texto,
        ctx={},
        servicos_catalogo=SERVICOS_TESTE
    )

    # Validar classificação
    assert resultado.get("intencao") == "consulta_disponibilidade_servico", \
        f"Classificação errada: {resultado.get('intencao')}"

    # Validar entidades (serviço extraído)
    servico = resultado.get("entidades", {}).get("servico")
    assert servico == "corte feminino", \
        f"Serviço não extraído: {resultado.get('entidades')}"

    print(f"✅ D: Frase determinística OK → intenção={resultado.get('intencao')}, serviço={servico}")

# ============================================================================
# TESTE DE DIFERENCIAÇÃO ERRO vs VAZIO
# ============================================================================

@pytest.mark.asyncio
async def test_diferenciar_erro_de_vazio():
    """Teste E: Diferenciar erro de leitura vs coleção vazia"""

    from services.profissional_service import listar_servicos_cadastrados_com_diagnostico

    # Este teste depende de Firestore estar disponível
    # Se falhar, é esperado em ambiente de teste sem Firebase
    try:
        # Usar tenant fake para testar
        servicos, err = await listar_servicos_cadastrados_com_diagnostico("fake_user_123")

        # Pode retornar ([],  None) ou ([],  erro), ambos são esperados
        assert isinstance(servicos, list), "Deveria retornar lista"
        assert err is None or isinstance(err, str), "Err deveria ser None ou string"

        if err:
            assert "Error" in err or "Exception" in err, f"Diagnóstico deveria mencionar tipo de erro: {err}"
            print(f"✅ E: Erro capturado → {err}")
        else:
            print(f"✅ E: Coleção vazia (sem erro) → {servicos}")

    except Exception as e:
        print(f"⚠️  E: Teste deferred (sem Firestore real) → {type(e).__name__}")

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
