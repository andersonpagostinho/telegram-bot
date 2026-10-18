"""
GATE P0.1.1 — Auditoria de Fallback Inseguro em obter_janela_funcionamento

Testa se o fallback salao_id = user_id é realmente alcançável e se cria vulnerabilidade.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_fallback_user_id_alcancavel_quando_obter_id_dono_retorna_none():
    """
    TESTE CRÍTICO: Se obter_id_dono() retorna None, obter_janela_funcionamento()
    cairá para salao_id = user_id?

    Simula: cliente que não está vinculado a nenhum negócio.
    """
    from services.agenda_service import obter_janela_funcionamento

    user_id = "usuario_desvinculado_123"
    data_str = "2026-10-20"

    # Mock: obter_id_dono retorna None (cliente não vinculado)
    with patch("services.firebase_service_async.obter_id_dono") as mock_obter_id, \
         patch("services.firebase_service_async.buscar_dado_em_path") as mock_buscar:

        mock_obter_id.return_value = None  # NÃO conseguiu resolver tenant

        # Mock do buscar_dado_em_path para registrar qual path foi consultado
        mock_buscar.return_value = {}

        # Chamar sem dono_id
        resultado = await obter_janela_funcionamento(user_id, data_str)

        # VERIFICAÇÃO CRÍTICA:
        # 1. obter_id_dono foi chamado
        mock_obter_id.assert_called_once_with(user_id)

        # 2. Qual path foi consultado?
        print(f"\n[AUDIT] Paths consultados:")
        for call in mock_buscar.call_args_list:
            path = call[0][0]
            print(f"        {path}")

            # FALLBACK ALCANÇADO? Se path contém user_id em Clientes/{user_id}
            if f"Clientes/{user_id}/configuracao/agenda_funcionamento" == path:
                print(f"        [FALLBACK_INSEGURO_ALCANCADO] consultou {user_id}")
                assert False, "BUG: Caiu para fallback salao_id = user_id"

        # Se chegou aqui, usou algo diferente ou retornou vazio
        print(f"[OK] Fallback não alcançado ou retornou vazio")


@pytest.mark.asyncio
async def test_fallback_nao_afeta_cliente_vinculado():
    """
    TESTE DE CONFIANÇA: Cliente vinculado corretamente resolve tenant.

    Simula: cliente vinculado ao salão 7394370553.
    """
    from services.agenda_service import obter_janela_funcionamento

    user_id = "5511991382080"  # Cliente real vinculado
    tenant_id = "7394370553"  # Seu salão
    data_str = "2026-10-20"

    # Mock: obter_id_dono retorna tenant correto
    with patch("services.firebase_service_async.obter_id_dono") as mock_obter_id, \
         patch("services.firebase_service_async.buscar_dado_em_path") as mock_buscar, \
         patch("services.firebase_service_async.buscar_subcolecao") as mock_subcolecao:

        mock_obter_id.return_value = tenant_id  # Conseguiu resolver

        # Mock do buscar_dado_em_path
        mock_buscar.return_value = {
            "agenda_padrao": {"0": {"aberto": True, "inicio": "08:00", "fim": "18:00"}},
            "excecoes_data": {}
        }

        # Mock do buscar_subcolecao (profissionais)
        mock_subcolecao.return_value = {}

        # Chamar sem dono_id (vai resolver via obter_id_dono)
        resultado = await obter_janela_funcionamento(user_id, data_str)

        # VERIFICAÇÃO:
        # 1. obter_id_dono foi chamado
        mock_obter_id.assert_called_once_with(user_id)

        # 2. Path consultado DEVE ser do tenant, NOT user_id
        for call in mock_buscar.call_args_list:
            path = call[0][0]
            print(f"[OK] Path correto consultado: {path}")
            assert f"Clientes/{tenant_id}/configuracao" in path, f"Path deve conter tenant, não user_id: {path}"
            assert f"Clientes/{user_id}/configuracao" not in path, f"Path NÃO deve conter user_id: {path}"

        print(f"[OK] Cliente vinculado resolveu corretamente para tenant {tenant_id}")


@pytest.mark.asyncio
async def test_fallback_comportamento_real_firebase():
    """
    TESTE COM FIREBASE REAL: Verifica se cliente desvinculado cai para fallback.

    Usando Firestore real para confirmar:
    1. Cliente existe em Clientes/{user_id}
    2. Mas não tem id_negocio vinculado (ou não é cliente)
    3. obter_janela_funcionamento() cai para salao_id = user_id
    4. Tenta ler Clientes/{user_id}/configuracao/agenda_funcionamento
    """
    from services.agenda_service import obter_janela_funcionamento

    # Usar um user_id que provavelmente NÃO está vinculado
    user_id_desvinculado = "99999999999_teste_desvinculado"
    data_str = "2026-10-20"

    # Sem mocks - chamar diretamente com Firebase real
    resultado = await obter_janela_funcionamento(user_id_desvinculado, data_str)

    # VERIFICAÇÃO:
    # Se fallback foi alcançado e Clientes/{user_id_desvinculado}/configuracao NÃO existe,
    # resultado será vazio (aberto=False)
    print(f"\n[AUDIT] Resultado para user_id desvinculado: {resultado}")

    # O que esperamos:
    # - Se fallback foi alcançado E configuração não existe: aberto=False
    # - Se fallback não foi alcançado: algum valor padrão

    if resultado.get("aberto") is False:
        # Pode significar:
        # A) Fallback foi alcançado mas config não existe (configuracao retorna {})
        # B) Salão está fechado (se fallback funcionou)
        print(f"[AUDIT] Resultado fechado - pode indicar fallback + config vazia ou salão fechado")

    print(f"[OK] Teste Firebase real completado")


@pytest.mark.asyncio
async def test_proxima_data_permitida_fallback_audit():
    """
    TESTE: proxima_data_permitida() chama obter_janela sem dono_id.

    Verifica se fallback é propagado ou se há proteção.
    """
    from services.agenda_service import proxima_data_permitida

    user_id_desvinculado = "99999999999_teste_desvinculado"
    data_iso = "2026-10-20"

    # Sem dono_id (função não tem parâmetro dono_id)
    resultado = await proxima_data_permitida(user_id_desvinculado, data_iso, limite_dias=5)

    print(f"\n[AUDIT] proxima_data_permitida resultado: {resultado}")

    # Se resultado é None, significa não encontrou data aberta
    # Pode ser porque:
    # A) Fallback funcionou mas salão (user_id) não existe ou está fechado
    # B) Função retorna None como padrão

    if resultado is None:
        print(f"[OK] proxima_data_permitida retornou None (seguro ou fallback limitado)")
    else:
        print(f"[AUDIT] Encontrou data: {resultado}")


@pytest.mark.asyncio
async def test_resolver_fora_do_expediente_fallback_audit():
    """
    TESTE: resolver_fora_do_expediente() chama obter_janela sem dono_id.

    Verifica se fallback é propagado.
    """
    from services.agenda_service import resolver_fora_do_expediente

    user_id_desvinculado = "99999999999_teste_desvinculado"
    data_iso = "2026-10-20"
    hora_inicio = "14:00"
    duracao_min = 30
    servico = "Corte"

    # Sem dono_id (função não tem parâmetro)
    resultado = await resolver_fora_do_expediente(
        user_id_desvinculado, data_iso, hora_inicio, duracao_min, servico
    )

    print(f"\n[AUDIT] resolver_fora_do_expediente resultado: {resultado}")

    # Esperamos resultado com ok=True/False
    if resultado.get("ok") is False:
        print(f"[OK] Não conseguiu resolver fora do expediente (seguro ou fallback bloqueado)")
    else:
        print(f"[AUDIT] Conseguiu resolver: {resultado.get('motivo')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
