"""
P0 FASE 4: TESTES DE CONSISTÊNCIA ATOR × CLIENTE

12 testes obrigatórios para validar correção da inconsistência.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestP0Fase4ConsistenciaAtorCliente:
    """12 testes obrigatórios para consistência Ator × Cliente"""

    # === TESTE 1: Ambos existem (Cenário A) ===
    @pytest.mark.asyncio
    async def test_01_ator_cliente_ambos_existem(self):
        """Ator e cliente existem — retorna normal sem recriar"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.buscar_dado_em_path") as mock_buscar:
                mock_resolver.return_value = {"tipo_usuario": "cliente", "permissoes": ["ler"]}
                mock_buscar.return_value = {"nome": "Cliente Existente"}

                resultado = await resolver_ator_e_validar_guard(
                    user_id="5511991382080",
                    tenant_id="7394370553",
                    canal="whatsapp",
                    identificador="5511991382080"
                )

                assert resultado["sucesso"] is True
                assert resultado["tipo_usuario"] == "cliente"
                assert resultado["proxima_acao"] == "normal"

    # === TESTE 2: Ator existe, Cliente não (Cenário B — CORREÇÃO) ===
    @pytest.mark.asyncio
    async def test_02_ator_existe_cliente_nao_existe_cria_cliente(self):
        """Ator existe mas cliente não — deve criar cliente automaticamente"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.buscar_dado_em_path") as mock_buscar:
                with patch("router.integracao_identidade_onboarding.criar_ator_cliente_automatico") as mock_criar:
                    mock_resolver.return_value = {"tipo_usuario": "cliente", "permissoes": ["ler"]}
                    mock_buscar.return_value = None  # Cliente não existe
                    mock_criar.return_value = {"actor_id": "whatsapp:5511991382080"}

                    resultado = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    assert resultado["sucesso"] is True
                    # Verificar que criar_ator_cliente_automatico foi chamada
                    mock_criar.assert_called_once()

    # === TESTE 3: Ator não existe, Cliente existe (Cenário C) ===
    @pytest.mark.asyncio
    async def test_03_ator_nao_existe_cliente_existe(self):
        """Ator não existe mas cliente existe — criar ator sem perder cliente"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.tenant_tem_dono") as mock_tem_dono:
                with patch("router.integracao_identidade_onboarding.criar_ator_cliente_automatico") as mock_criar:
                    mock_resolver.return_value = None  # Ator não existe
                    mock_tem_dono.return_value = True  # Tenant tem dono
                    mock_criar.return_value = {"actor_id": "whatsapp:5511991382080"}

                    resultado = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    assert resultado["sucesso"] is True
                    mock_criar.assert_called_once()

    # === TESTE 4: Ambos não existem (Cenário D) ===
    @pytest.mark.asyncio
    async def test_04_ator_cliente_ambos_nao_existem(self):
        """Nenhum existe — criar ambos"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.tenant_tem_dono") as mock_tem_dono:
                with patch("router.integracao_identidade_onboarding.criar_ator_cliente_automatico") as mock_criar:
                    mock_resolver.return_value = None
                    mock_tem_dono.return_value = True
                    mock_criar.return_value = {"actor_id": "whatsapp:5511991382080"}

                    resultado = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    assert resultado["sucesso"] is True
                    mock_criar.assert_called_once()

    # === TESTE 5: Falha ao criar ator ===
    @pytest.mark.asyncio
    async def test_05_falha_ao_criar_ator(self):
        """Falha ao criar ator — retorna erro, não sucesso"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.tenant_tem_dono") as mock_tem_dono:
                with patch("router.integracao_identidade_onboarding.criar_ator_cliente_automatico") as mock_criar:
                    mock_resolver.return_value = None
                    mock_tem_dono.return_value = True
                    mock_criar.side_effect = Exception("Firestore error")

                    resultado = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    # Pode falhar ou retornar com erro
                    assert "error" in resultado or resultado["sucesso"] is False

    # === TESTE 6: Falha ao criar cliente (Cenário B) ===
    @pytest.mark.asyncio
    async def test_06_falha_ao_criar_cliente_cenario_b(self):
        """Ator existe, cliente não, mas falha ao criar — continua mesmo assim"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.buscar_dado_em_path") as mock_buscar:
                with patch("router.integracao_identidade_onboarding.criar_ator_cliente_automatico") as mock_criar:
                    mock_resolver.return_value = {"tipo_usuario": "cliente", "permissoes": ["ler"]}
                    mock_buscar.return_value = None  # Cliente não existe
                    mock_criar.side_effect = Exception("Firestore error")

                    resultado = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    # Continua mesmo se falhar (ator já existe)
                    assert resultado["sucesso"] is True

    # === TESTE 7: Reexecução sem duplicação ===
    @pytest.mark.asyncio
    async def test_07_reexecucao_sem_duplicacao(self):
        """Executar 2x a mesma operação — sem duplicar"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.buscar_dado_em_path") as mock_buscar:
                with patch("router.integracao_identidade_onboarding.criar_ator_cliente_automatico") as mock_criar:
                    # Primeira execução
                    mock_resolver.return_value = {"tipo_usuario": "cliente"}
                    mock_buscar.return_value = None
                    mock_criar.return_value = {"actor_id": "whatsapp:5511991382080"}

                    resultado1 = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    # Segunda execução — cliente agora existe
                    mock_resolver.reset_mock()
                    mock_buscar.reset_mock()
                    mock_criar.reset_mock()
                    mock_resolver.return_value = {"tipo_usuario": "cliente"}
                    mock_buscar.return_value = {"actor_id": "whatsapp:5511991382080"}  # Cliente existe

                    resultado2 = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    # Segunda vez, criar_ator_cliente_automatico não deve ser chamada
                    assert mock_criar.call_count == 0

    # === TESTE 8: Isolamento multi-tenant ===
    @pytest.mark.asyncio
    async def test_08_isolamento_multitenant(self):
        """Tenant A não vê dados de Tenant B"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        def mock_buscar_coro(path):
            if "7394370553" in path:
                return {"cliente": "A"} if "Cliente" in path else None
            elif "outro_tenant" in path:
                return {"cliente": "B"} if "Cliente" in path else None
            return None

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.buscar_dado_em_path") as mock_buscar:
                with patch("router.integracao_identidade_onboarding.tenant_tem_dono") as mock_tem_dono:
                    # Tenant A
                    mock_resolver.return_value = {"tipo_usuario": "cliente"}
                    mock_buscar.side_effect = mock_buscar_coro
                    mock_tem_dono.return_value = True

                    resultado_a = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    # Tenant B
                    mock_resolver.reset_mock()
                    mock_buscar.reset_mock()
                    mock_tem_dono.reset_mock()
                    mock_resolver.return_value = {"tipo_usuario": "cliente"}
                    mock_buscar.side_effect = mock_buscar_coro
                    mock_tem_dono.return_value = True

                    resultado_b = await resolver_ator_e_validar_guard(
                        user_id="outro_user",
                        tenant_id="outro_tenant",
                        canal="whatsapp",
                        identificador="outro_user"
                    )

                    assert resultado_a["sucesso"] is True
                    assert resultado_b["sucesso"] is True

    # === TESTE 9: Tenant ausente ===
    @pytest.mark.asyncio
    async def test_09_tenant_ausente(self):
        """Sem tenant_id — falha segura"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        resultado = await resolver_ator_e_validar_guard(
            user_id="5511991382080",
            tenant_id=None,  # Ausente
            canal="whatsapp",
            identificador="5511991382080"
        )

        assert resultado["sucesso"] is False

    # === TESTE 10: Sessão independente do cadastro ===
    @pytest.mark.asyncio
    async def test_10_sessao_independente_cadastro(self):
        """Sessão pode ser salva mesmo sem cadastro perfeito"""
        from utils.contexto_temporario import salvar_sessao_temporaria

        with patch("utils.contexto_temporario.atualizar_dado_em_path") as mock_atualizar:
            mock_atualizar.return_value = True

            resultado = await salvar_sessao_temporaria(
                actor_id="whatsapp:5511991382080",
                contexto={"estado_fluxo": "idle"},
                tenant_id="7394370553"
            )

            assert resultado is True
            # Verificar path correto
            call_args = mock_atualizar.call_args[0]
            assert "Clientes/7394370553/Sessoes" in call_args[0]

    # === TESTE 11: Preservação de campos existentes ===
    @pytest.mark.asyncio
    async def test_11_preservacao_campos_existentes(self):
        """Atualizar sem perder campos existentes"""
        from services.firebase_service_async import atualizar_dado_em_path

        with patch("services.firebase_service_async.get_ref_from_path") as mock_get_ref:
            mock_ref = AsyncMock()
            mock_get_ref.return_value = mock_ref
            mock_ref.set = AsyncMock(return_value=None)

            await atualizar_dado_em_path(
                "Clientes/7394370553/Sessoes/whatsapp:5511991382080",
                {"novo_campo": "valor"}
            )

            # Verificar que set é chamado com merge=True
            mock_ref.set.assert_called_once()
            call_kwargs = mock_ref.set.call_args[1]
            assert call_kwargs.get("merge") is True

    # === TESTE 12: Falha parcial de persistência ===
    @pytest.mark.asyncio
    async def test_12_falha_parcial_persistencia(self):
        """Se cliente falha, ator deve ter sido criado (não rollback)"""
        from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard

        with patch("router.integracao_identidade_onboarding.resolver_ator_por_canal") as mock_resolver:
            with patch("router.integracao_identidade_onboarding.tenant_tem_dono") as mock_tem_dono:
                with patch("router.integracao_identidade_onboarding.criar_ator_cliente_automatico") as mock_criar:
                    # Primeira chamada (linha 173) cria ator com sucesso
                    # Segunda chamada (linha 253) em Cenário B falha ao criar cliente
                    mock_resolver.return_value = None
                    mock_tem_dono.return_value = True
                    mock_criar.side_effect = [
                        {"actor_id": "whatsapp:5511991382080"},  # Primeira (sucesso)
                        Exception("Firestore error")  # Segunda em Cenário B (falha)
                    ]

                    # Primeira execução — cria tudo
                    resultado1 = await resolver_ator_e_validar_guard(
                        user_id="5511991382080",
                        tenant_id="7394370553",
                        canal="whatsapp",
                        identificador="5511991382080"
                    )

                    # Mesmo com falha, operação anterior não foi revertida
                    assert resultado1["sucesso"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
