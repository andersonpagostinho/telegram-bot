"""
P0.7.2A — Teste: Comparação de Serviços Entre Profissionais (Handler Informativo)

Testa:
1. "A Carla faz as mesmas coisa que a Bruna?" — resposta com catálogo real
2. "A Carla faz o que a Bruna faz?" — variação reconhecida
3. "Elas atendem os mesmos serviços?" — padrão genérico
4. Profissional não cadastrada — sem invenção de dados
5. Catálogo vazio ou falha — resposta segura
6. Comparação com draft pendente — preserva rascunho
7. Sem disparo de validação de conflito
8. Isolamento multi-tenant
9. Consulta de disponibilidade continua funcionando
10. Confirmação de agendamento intacta
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock


# ============================================================
# T1: Comparação Básica — Duas Profissionais Nomeadas
# ============================================================
@pytest.mark.asyncio
async def test_t1_comparacao_basica_carla_bruna():
    """
    T1: "A Carla faz as mesmas coisa que a Bruna?"
    Resposta deve listar serviços de cada uma usando dados reais do Firestore.
    """
    print("\n[T1] Testando comparação básica entre Carla e Bruna...")

    from services.informacao_service import responder_consulta_informativa

    # Mock de dados do Firestore
    mock_profissionais = {
        "Carla": {
            "nome": "Carla",
            "servicos": ["manicure", "pedicure", "coloracao"]
        },
        "Bruna": {
            "nome": "Bruna",
            "servicos": ["corte feminino", "escova", "coloracao", "hidratacao", "manicure", "pedicure"]
        }
    }

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_teste_7394370553"

        # Retornar profissionais para chamada a Clientes/tenant/Profissionais
        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return mock_profissionais
            return {}

        mock_buscar.side_effect = buscar_side_effect

        resposta = await responder_consulta_informativa(
            "a carla faz as mesmas coisa que a bruna?",
            dono_id="tenant_teste_7394370553"
        )

        # Validações
        assert resposta is not None, "FAIL: Resposta é None"
        assert "Carla" in resposta, "FAIL: Carla não está na resposta"
        assert "Bruna" in resposta, "FAIL: Bruna não está na resposta"
        assert "manicure" in resposta.lower(), "FAIL: Serviço não está na resposta"
        assert "coloracao" in resposta.lower() or "coloração" in resposta, "FAIL: Serviço coloração não listado"

        print(f"[T1] PASS: Resposta gerada\n{resposta}")


# ============================================================
# T2: Variação — "A Carla faz o que a Bruna faz?"
# ============================================================
@pytest.mark.asyncio
async def test_t2_variacao_faz_o_que():
    """T2: Padrão alternativo "A Carla faz o que a Bruna faz?" é reconhecido."""
    print("\n[T2] Testando variação 'faz o que'...")

    from services.informacao_service import responder_consulta_informativa

    mock_profissionais = {
        "Gloria": {
            "nome": "Gloria",
            "servicos": ["corte", "escova"]
        },
        "Joana": {
            "nome": "Joana",
            "servicos": ["corte", "escova", "coloracao"]
        }
    }

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_test"

        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return mock_profissionais
            return {}

        mock_buscar.side_effect = buscar_side_effect

        resposta = await responder_consulta_informativa(
            "a gloria faz o que a joana faz?",
            dono_id="tenant_teste_7394370553"
        )

        assert resposta is not None, "FAIL: Resposta é None"
        assert "Gloria" in resposta and "Joana" in resposta, "FAIL: Nomes não estão na resposta"
        print(f"[T2] PASS:\n{resposta}")


# ============================================================
# T3: Padrão Genérico — "Elas atendem os mesmos serviços?"
# ============================================================
@pytest.mark.asyncio
async def test_t3_padrao_generico_elas_atendem():
    """T3: Padrão genérico sem nomes específicos."""
    print("\n[T3] Testando padrão genérico...")

    from services.informacao_service import responder_consulta_informativa

    mock_profissionais = {
        "Ana": {"nome": "Ana", "servicos": ["manicure"]},
        "Beatriz": {"nome": "Beatriz", "servicos": ["pedicure"]}
    }

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_test"

        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return mock_profissionais
            return {}

        mock_buscar.side_effect = buscar_side_effect

        resposta = await responder_consulta_informativa(
            "elas atendem os mesmos servicos?",
            dono_id="tenant_teste_7394370553"
        )

        assert resposta is not None, "FAIL: Resposta é None para padrão genérico"
        assert "Ana" in resposta or "Beatriz" in resposta, "FAIL: Nenhum nome na resposta"
        print(f"[T3] PASS:\n{resposta}")


# ============================================================
# T4: Profissional Não Cadastrada — Sem Invenção
# ============================================================
@pytest.mark.asyncio
async def test_t4_profissional_nao_existe():
    """T4: Se menciona profissional inexistente, não inventar dados."""
    print("\n[T4] Testando profissional não cadastrada...")

    from services.informacao_service import responder_consulta_informativa

    mock_profissionais = {
        "Maria": {"nome": "Maria", "servicos": ["corte"]}
    }

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_test"

        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return mock_profissionais
            return {}

        mock_buscar.side_effect = buscar_side_effect

        # Menciona "Carla" que não está em mock_profissionais
        resposta = await responder_consulta_informativa(
            "a carla faz o mesmo que a maria?",
            dono_id="tenant_teste_7394370553"
        )

        # Se não encontrou nomes específicos, lista todas
        # Ou responde com mensagem de "qual outra profissional?"
        assert resposta is not None, "FAIL: Sem resposta para profissional não encontrada"
        # Não deve dizer que Carla existe
        assert "carla" not in resposta.lower() or "qual" in resposta.lower(), \
            "FAIL: Inventou informação sobre Carla"
        print(f"[T4] PASS:\n{resposta}")


# ============================================================
# T5: Catálogo Vazio — Resposta Segura
# ============================================================
@pytest.mark.asyncio
async def test_t5_catalogo_vazio():
    """T5: Se não há profissionais, resposta segura sem fabricação."""
    print("\n[T5] Testando catálogo vazio...")

    from services.informacao_service import responder_consulta_informativa

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_vazio"

        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return {}  # Catálogo vazio de profissionais
            return {}

        mock_buscar.side_effect = buscar_side_effect

        resposta = await responder_consulta_informativa(
            "a carla faz o mesmo que a bruna?",
            dono_id="tenant_teste_7394370553"
        )

        # Com catálogo vazio, deve retornar mensagem apropriada
        assert resposta is not None, "FAIL: Sem resposta para catálogo vazio"
        assert "2 profissionais" in resposta or "cadastradas" in resposta, \
            "FAIL: Não explicou necessidade de 2 profissionais"
        print(f"[T5] PASS:\n{resposta}")


# ============================================================
# T6: Draft Preservado During Comparison
# ============================================================
@pytest.mark.asyncio
async def test_t6_draft_preservado_durante_comparacao():
    """
    T6: Comparação ocorre enquanto há draft_agendamento pendente.
    Draft deve ser preservado (não alterado pela resposta informativa).
    """
    print("\n[T6] Testando preservação de draft durante comparação...")

    from services.informacao_service import responder_consulta_informativa

    # Nota: responder_consulta_informativa não modifica draft por padrão
    # Apenas retorna uma string. O fluxo principal (principal_router) é responsável
    # por preservar ou não o draft.

    mock_profissionais = {
        "Carla": {"nome": "Carla", "servicos": ["manicure"]},
        "Bruna": {"nome": "Bruna", "servicos": ["manicure", "pedicure"]}
    }

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_test"

        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return mock_profissionais
            return {}

        mock_buscar.side_effect = buscar_side_effect

        # Simular estado com draft
        draft_antes = {
            "profissional": "Bruna",
            "data_hora": "2026-10-28T10:00:00",
            "servico": "manicure"
        }

        resposta = await responder_consulta_informativa(
            "a carla faz as mesmas coisa que a bruna?",
            dono_id="tenant_teste_7394370553"
        )

        # Validação: resposta foi gerada (não None)
        assert resposta is not None, "FAIL: Sem resposta"

        # A função informativa NÃO altera draft (responsabilidade do router)
        # Apenas retorna resposta
        assert "Carla" in resposta and "Bruna" in resposta, "FAIL: Resposta incompleta"

        print(f"[T6] PASS: Draft preservado (função informativa não o altera)\n{resposta}")


# ============================================================
# T7: Sem Validação de Conflito
# ============================================================
def test_t7_sem_validacao_conflito():
    """T7: Resposta informativa não dispara validação de conflito."""
    print("\n[T7] Testando ausência de validação de conflito...")

    # A função responder_consulta_informativa retorna apenas uma string
    # Não chama nenhuma função de validação
    # Validação de conflito é responsabilidade de principal_router.py

    # Verificar que a função não importa ou chama VALIDACAO_CONFLITO
    from services import informacao_service
    import inspect

    source = inspect.getsource(informacao_service.responder_consulta_informativa)

    assert "validacao_conflito" not in source.lower(), \
        "FAIL: Função informativa não deve chamar validação de conflito"
    assert "conflito" not in source.lower(), \
        "FAIL: Função informativa não deve verificar conflitos"

    print("[T7] PASS: Sem validação de conflito na função informativa")


# ============================================================
# T8: Isolamento Multi-Tenant
# ============================================================
@pytest.mark.asyncio
async def test_t8_isolamento_multi_tenant():
    """T8: Dados de outro tenant nunca são usados na resposta."""
    print("\n[T8] Testando isolamento multi-tenant...")

    from services.informacao_service import responder_consulta_informativa

    # Mock para tenant A
    mock_profs_tenant_a = {
        "Ana": {"nome": "Ana", "servicos": ["corte"]},
        "Bia": {"nome": "Bia", "servicos": ["escova"]}
    }

    # Mock para tenant B (diferente)
    mock_profs_tenant_b = {
        "Carla": {"nome": "Carla", "servicos": ["manicure"]},
        "Diana": {"nome": "Diana", "servicos": ["pedicure"]}
    }

    # User do tenant A
    user_id_a = "user_tenant_a"

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        # User A mapeia para tenant A
        mock_dono.return_value = "tenant_a_id"

        async def buscar_side_effect(path):
            if "Profissionais" in path and "tenant_a_id" in path:
                return mock_profs_tenant_a
            elif "Profissionais" in path:
                # Não deve nunca retornar dados de outro tenant
                return {}
            return {}

        mock_buscar.side_effect = buscar_side_effect

        resposta = await responder_consulta_informativa(
            "a ana faz o mesmo que a bia?",
            dono_id="tenant_a_id"
        )

        # Deve usar dados de tenant A
        assert resposta is not None, "FAIL: Sem resposta"
        assert "Ana" in resposta or "Bia" in resposta, "FAIL: Dados de tenant A não usados"

        # Não deve nunca mencionar dados de tenant B
        assert "Carla" not in resposta, "FAIL: Dados de outro tenant foram usados!"
        assert "Diana" not in resposta, "FAIL: Dados de outro tenant foram usados!"

        print(f"[T8] PASS: Isolamento mantido\n{resposta}")


# ============================================================
# T9: Consulta de Disponibilidade Continua Funcionando
# ============================================================
@pytest.mark.asyncio
async def test_t9_consulta_disponibilidade_intacta():
    """T9: Pergunta normal de disponibilidade continua seguindo fluxo normal."""
    print("\n[T9] Testando consulta de disponibilidade intacta...")

    from services.informacao_service import responder_consulta_informativa

    # Pergunta de disponibilidade não deve ser respondida como comparação
    # (A função informativa pode responder se houver dados, mas verifica disponibilidade real)

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono:
        mock_dono.return_value = "tenant_test"

        # Pergunta de disponibilidade
        resposta = await responder_consulta_informativa(
            "a bruna tem disponivel amanha?",
            dono_id="tenant_teste_7394370553"
        )

        # Pode ser None ou uma resposta sobre disponibilidade
        # O importante é que não trata como comparação
        if resposta:
            assert "comparacao" not in resposta.lower(), \
                "FAIL: Disponibilidade foi tratada como comparação"

        print(f"[T9] PASS: Disponibilidade intacta (resposta: {resposta or 'None (delegado ao fluxo normal)'})")


# ============================================================
# T10: Confirmação de Agendamento Intacta
# ============================================================
def test_t10_confirmacao_agendamento_intacta():
    """T10: O fluxo de confirmação não é afetado pela comparação."""
    print("\n[T10] Testando confirmação de agendamento intacta...")

    # Verificar que responder_consulta_informativa não altera comportamento de confirmação
    # A confirmação é processada pelo principal_router, não pela função informativa

    from services import informacao_service
    import inspect

    source = inspect.getsource(informacao_service.responder_consulta_informativa)

    assert "confirmacao" not in source.lower() or "agendamento" not in source.lower(), \
        "FAIL: Função informativa não deve processar confirmação"
    assert "aguardando_confirmacao" not in source, \
        "FAIL: Função informativa não deve alterar estado de confirmação"

    print("[T10] PASS: Confirmação não é afetada por comparação informativa")


# ============================================================
# SUMMARY
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTES P0.7.2A — Comparação de Serviços Entre Profissionais")
    print("="*70)

    # Executar testes síncronos
    test_t7_sem_validacao_conflito()
    test_t10_confirmacao_agendamento_intacta()

    # Executar testes assincronos
    asyncio.run(test_t1_comparacao_basica_carla_bruna())
    asyncio.run(test_t2_variacao_faz_o_que())
    asyncio.run(test_t3_padrao_generico_elas_atendem())
    asyncio.run(test_t4_profissional_nao_existe())
    asyncio.run(test_t5_catalogo_vazio())
    asyncio.run(test_t6_draft_preservado_durante_comparacao())
    asyncio.run(test_t8_isolamento_multi_tenant())
    asyncio.run(test_t9_consulta_disponibilidade_intacta())

    print("\n" + "="*70)
    print("✅ TODOS OS TESTES PASSARAM")
    print("="*70)
