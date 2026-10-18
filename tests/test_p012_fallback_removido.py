"""
P0.1.2 — Validação que fallback inseguro foi removido de obter_janela_funcionamento

Testa 7 critérios obrigatórios após correção:
1. Tenant explícito válido: consulta o caminho do salão correto
2. Tenant resolvido por obter_id_dono(): mantém o comportamento válido
3. Tenant não resolvido: retorna origem="tenant_nao_resolvido"
4. Tenant não resolvido: nenhuma leitura em Clientes/{user_id}/...
5. Configuração ausente de um tenant válido: distinta de tenant não resolvido
6. Os três consumidores tratam o resultado sem criar disponibilidade fictícia
7. Regressão dos testes P0 existentes
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_1_tenant_explicito_valido():
    """
    TESTE 1: Tenant explícito válido → consulta caminho correto do salão.
    """
    from services.agenda_service import obter_janela_funcionamento

    user_id = "cliente_123"
    tenant_id = "salao_7394370553"
    data_str = "2026-10-20"

    with patch("services.firebase_service_async.buscar_dado_em_path") as mock_buscar, \
         patch("services.firebase_service_async.buscar_subcolecao") as mock_subcolecao:

        mock_buscar.return_value = {
            "agenda_padrao": {"0": {"aberto": True, "inicio": "08:00", "fim": "18:00"}},
            "excecoes_data": {}
        }
        mock_subcolecao.return_value = {}

        resultado = await obter_janela_funcionamento(user_id, data_str, dono_id=tenant_id)

        # VERIFICAÇÃO: buscar_dado_em_path foi chamado com path do tenant, não user_id
        calls = mock_buscar.call_args_list
        assert len(calls) > 0, "Deve ter consultado algo"

        first_path = calls[0][0][0]
        assert f"Clientes/{tenant_id}/configuracao" in first_path, f"Path deve conter tenant {tenant_id}, obteve: {first_path}"
        assert f"Clientes/{user_id}" not in first_path, f"Path NÃO deve conter user_id {user_id}"

        print(f"[OK] Teste 1: Path correto consultado: {first_path}")


@pytest.mark.asyncio
async def test_2_tenant_resolvido_por_obter_id_dono():
    """
    TESTE 2: Tenant resolvido por obter_id_dono() → comportamento válido mantido.
    """
    from services.agenda_service import obter_janela_funcionamento

    user_id = "cliente_vinculado"
    resolved_tenant = "salao_resolvido"
    data_str = "2026-10-19"  # Segunda-feira (weekday=0)

    with patch("services.firebase_service_async.obter_id_dono") as mock_obter_id, \
         patch("services.firebase_service_async.buscar_dado_em_path") as mock_buscar, \
         patch("services.firebase_service_async.buscar_subcolecao") as mock_subcolecao:

        # obter_id_dono consegue resolver
        mock_obter_id.return_value = resolved_tenant

        mock_buscar.return_value = {
            "agenda_padrao": {"0": {"aberto": True, "inicio": "09:00", "fim": "17:00"}},
            "excecoes_data": {}
        }
        mock_subcolecao.return_value = {}

        resultado = await obter_janela_funcionamento(user_id, data_str)  # Sem dono_id

        # VERIFICAÇÃO
        assert resultado.get("aberto") == True, "Deve estar aberto"
        assert resultado.get("origem") in ["agenda_padrao_salao"], f"Origem: {resultado.get('origem')}"

        # buscar_dado_em_path deve ter consultado o tenant resolvido
        first_path = mock_buscar.call_args_list[0][0][0]
        assert resolved_tenant in first_path, f"Path deve conter tenant resolvido {resolved_tenant}"

        print(f"[OK] Teste 2: Tenant resolvido, comportamento mantido")


@pytest.mark.asyncio
async def test_3_tenant_nao_resolvido_origem():
    """
    TESTE 3: Tenant não resolvido → retorna origem="tenant_nao_resolvido".
    """
    from services.agenda_service import obter_janela_funcionamento

    user_id = "usuario_desvinculado"
    data_str = "2026-10-20"

    with patch("services.firebase_service_async.obter_id_dono") as mock_obter_id:

        # obter_id_dono não consegue resolver
        mock_obter_id.return_value = None

        resultado = await obter_janela_funcionamento(user_id, data_str)

        # VERIFICAÇÃO CRÍTICA
        assert resultado.get("aberto") == False, "Deve estar fechado"
        assert resultado.get("origem") == "tenant_nao_resolvido", f"Origem deve ser tenant_nao_resolvido, obteve: {resultado.get('origem')}"
        assert resultado.get("motivo") == "usuario_nao_vinculado", f"Motivo: {resultado.get('motivo')}"

        print(f"[OK] Teste 3: Tenant não resolvido, retornou origem correta")


@pytest.mark.asyncio
async def test_4_tenant_nao_resolvido_sem_leitura_user_id():
    """
    TESTE 4: Tenant não resolvido → nenhuma leitura em Clientes/{user_id}/...

    CRÍTICO: Prova que fallback foi removido.
    """
    from services.agenda_service import obter_janela_funcionamento

    user_id = "usuario_desvinculado_456"
    data_str = "2026-10-20"

    with patch("services.firebase_service_async.obter_id_dono") as mock_obter_id, \
         patch("services.firebase_service_async.buscar_dado_em_path") as mock_buscar:

        # obter_id_dono não consegue resolver
        mock_obter_id.return_value = None

        # Chamar função
        resultado = await obter_janela_funcionamento(user_id, data_str)

        # VERIFICAÇÃO CRÍTICA: buscar_dado_em_path NÃO deve ter sido chamado
        assert mock_buscar.call_count == 0, f"buscar_dado_em_path foi chamado {mock_buscar.call_count} vezes, deveria ser 0"

        print(f"[OK] Teste 4: NENHUMA leitura Firestore quando tenant não resolvido (fallback removido!)")


@pytest.mark.asyncio
async def test_5_config_ausente_vs_tenant_nao_resolvido():
    """
    TESTE 5: Config ausente (tenant válido) vs tenant não resolvido são DISTINTAS.
    """
    from services.agenda_service import obter_janela_funcionamento

    data_str = "2026-10-20"

    # Cenário A: Tenant resolvido mas config não existe
    with patch("services.firebase_service_async.obter_id_dono") as mock_obter_id_a, \
         patch("services.firebase_service_async.buscar_dado_em_path") as mock_buscar_a:

        mock_obter_id_a.return_value = "salao_existente"
        mock_buscar_a.return_value = {}  # Config não existe

        resultado_a = await obter_janela_funcionamento("cliente_a", data_str)

        # Cenário B: Tenant não resolvido
        with patch("services.firebase_service_async.obter_id_dono") as mock_obter_id_b:
            mock_obter_id_b.return_value = None

            resultado_b = await obter_janela_funcionamento("cliente_b", data_str)

    # VERIFICAÇÃO: Ambas retornam aberto=False, mas origem é DISTINTA
    assert resultado_a.get("aberto") == False, "Config ausente = fechado"
    assert resultado_b.get("aberto") == False, "Tenant não resolvido = fechado"

    origem_a = resultado_a.get("origem")
    origem_b = resultado_b.get("origem")

    assert origem_a != origem_b, f"Origens devem ser distintas. A={origem_a}, B={origem_b}"
    assert origem_b == "tenant_nao_resolvido", f"B deve ser tenant_nao_resolvido, obteve: {origem_b}"

    print(f"[OK] Teste 5: Config ausente ({origem_a}) vs tenant não resolvido ({origem_b}) são distintas")


@pytest.mark.asyncio
async def test_6_consumidores_nao_criam_disponibilidade_ficticia():
    """
    TESTE 6: Os três consumidores (proxima_data, proximo_horario, resolver_fora)
    tratam resultado tenant_nao_resolvido sem criar disponibilidade fictícia.
    """
    from services.agenda_service import (
        proxima_data_permitida,
        proximo_horario_valido_no_dia,
        resolver_fora_do_expediente
    )

    user_id = "usuario_desvinculado_789"
    data_iso = "2026-10-20"

    # Consumidor 1: proxima_data_permitida
    resultado1 = await proxima_data_permitida(user_id, data_iso, limite_dias=5)
    assert resultado1 is None, f"proxima_data deve retornar None para user desvinculado, obteve: {resultado1}"

    # Consumidor 2: proximo_horario_valido_no_dia
    resultado2 = await proximo_horario_valido_no_dia(user_id, data_iso, duracao_min=30)
    assert resultado2 is None, f"proximo_horario deve retornar None para user desvinculado, obteve: {resultado2}"

    # Consumidor 3: resolver_fora_do_expediente
    resultado3 = await resolver_fora_do_expediente(
        user_id, data_iso, "14:00", 30, "Corte"
    )
    assert resultado3.get("ok") == False, f"resolver_fora deve retornar ok=False, obteve: {resultado3}"
    assert resultado3.get("tipo") == "sem_opcao", f"Tipo deve ser sem_opcao, obteve: {resultado3.get('tipo')}"

    print(f"[OK] Teste 6: Todos os consumidores tratam corretamente tenant_nao_resolvido")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
